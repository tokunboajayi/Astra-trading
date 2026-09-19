"""
server/main.py

FastAPI app for Rich-HER / Astra Trading. Mock mode only: no Alpaca, no live data.
Session-authoritative: one in-memory demo session holds the truth, and the browser renders
whatever /api/state says. The rules live in server/sim_engine.py; this file is the session,
the tier gates and the HTTP layer. Owned by B (Backend). Contract: docs/archive/SPEC_v3.0.md section 8.

Run from the repo root:  uvicorn server.main:app --port 8000
Handlers are `async def` with no awaits on purpose: each request then runs to completion on
the event loop, so two requests can never interleave writes to the session.
"""

import json
import mimetypes
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import sim_engine as sim
from . import story_engine as story

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
FIXTURE_DIR = ROOT / "fixtures"
START_TIER = {"new": "beginner", "experienced": "intermediate"}
DEFAULT_STOP_PERCENT = 10.0


def _load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Missing {path.relative_to(ROOT)}. Fixtures come from: python scripts/build_fixtures.py")


# NVX sorts first: it is the guided demo, the $100 story account, and the option the
# onboarding card recommends. Everything else follows alphabetically.
FIXTURES = {p.stem: _load(p) for p in sorted(FIXTURE_DIR.glob("*.json"), key=lambda p: (p.stem != "NVX", p.stem))}
if not FIXTURES:
    raise SystemExit("No fixtures in fixtures/. Run: python scripts/build_fixtures.py")
TIERS = _load(WEB_DIR / "tiers.json")
CHECKS = _load(WEB_DIR / "checks.json")
COACH = _load(WEB_DIR / "coach.json")
SCENES = {p.stem: _load(p) for p in sorted((WEB_DIR / "scenes").glob("*.json")) if p.stem != "endings"}
ENDINGS = _load(WEB_DIR / "scenes" / "endings.json")
TIER_IDS = [t["id"] for t in TIERS]
SYMBOLS = [{**{k: f[k] for k in ("symbol", "name", "blurb", "volatility", "start_cursor")},
            "start_cash": f.get("start_cash", sim.STARTING_CASH)} for f in FIXTURES.values()]


def usd(x):
    return f"${x:,.2f}"


# --------------------------------------------------------------------------- errors

class ApiError(Exception):
    def __init__(self, status, code, message, **extra):
        super().__init__(message)
        self.status, self.code, self.message, self.extra = status, code, message, extra


def sim_error(e):
    return ApiError(400, e.code, e.message, **e.extra)


# --------------------------------------------------------------------------- session

@dataclass
class Session:
    participant: int
    onboarded: bool = False
    symbol: Optional[str] = None
    bars: list = field(default_factory=list)
    cursor: int = 0
    tier: str = "beginner"                 # highest unlocked tier
    cash: float = sim.STARTING_CASH
    starting_cash: float = sim.STARTING_CASH       # from the fixture; $10,000 or the story's $100
    positions: dict = field(default_factory=dict)
    orders: list = field(default_factory=list)       # every order ever placed; id == index + 1
    trades: list = field(default_factory=list)
    realized: float = 0.0
    dismissed: set = field(default_factory=set)      # symbols whose safety-net prompt was waved away
    kept_lots: list = field(default_factory=list)    # shares a safety net sold, for the shadow benchmark
    events: list = field(default_factory=list)
    checks_passed: set = field(default_factory=set)
    check_attempts: dict = field(default_factory=dict)
    first_buy_done: bool = False
    safety_net_used: bool = False
    replay_log: list = field(default_factory=list)   # accepted actions; replaying them rebuilds the session
    scene: Optional[str] = None                      # current story scene id, e.g. "act4.drop5"
    act: Optional[str] = None                        # which file `scene` lives in, e.g. "act4"
    flags: set = field(default_factory=set)          # narrative flags set by choices
    worst_equity: float = sim.STARTING_CASH          # lowest equity ever seen, for panicked_at_trough


SESSION = Session(participant=1)
QA_LOG = []          # survives /api/reset so V2 can total up stranger-QA across participants
BOOT_ID = uuid.uuid4().hex[:8]   # new on every server start: tells the browser "I restarted" from "I was reset"


def record(session, method, path, body=None):
    """Remember one accepted request so a restarted server can rebuild this session.

    The browser keeps a copy of this log in localStorage. If the server restarts, the
    browser replays it through the normal routes and the session comes back identical
    (the simulation is deterministic). See docs/archive/SPEC_v3.0.md section 6.
    """
    session.replay_log.append({"method": method, "path": path, "body": body})


def add_event(session, kind, message, **data):
    """Append one line to the activity feed the browser shows under the chart.

    `kind` is a machine-readable type (FILL, CANCEL, UNLOCK...) the frontend styles on;
    `message` is the plain-English sentence the user actually reads.
    """
    session.events.append({"seq": len(session.events) + 1, "bar": session.cursor, "day": session.cursor + 1,
                           "type": kind, "message": message, **data})


def require_onboarded(session):
    """Guard for every route that needs a running replay. Raises 409 if there isn't one."""
    if not session.onboarded:
        raise ApiError(409, "NOT_ONBOARDED", "Start a replay first: POST /api/onboarding.")


def current_bar(session):
    """Today's OHLC bar: {i, day, o, h, l, c}. `cursor` is the index of the day we're on."""
    return sim.price_at(session.bars, session.cursor)


def caps(tier):
    """What this tier is allowed to do, straight from web/tiers.json.

    Returns e.g. {"order_types": ["MARKET"], "chart": "line", "custom_safety_net": false}.
    `next(t for t in TIERS if ...)` is Python's "find the first match" - the JS equivalent
    is TIERS.find(t => t.id === tier).
    """
    return next(t for t in TIERS if t["id"] == tier)["unlocks"]


def tier_title(tier):
    """The human-readable name of a tier, e.g. "2. Tactical Protection"."""
    return next(t for t in TIERS if t["id"] == tier)["title"]


def find_prompts(session):
    """Any position currently down 8% or more that still has no safety net.

    A non-empty list here blocks /api/advance: the user must answer the prompt before
    time can move again, so fast-forward can never skip past it.
    """
    if not session.onboarded:
        return []
    return sim.check_safety_net_candidates(session.positions, current_bar(session)["c"], session.orders, session.dismissed)


def describe(order):
    """Turn an order dict into a phrase for the activity feed, e.g. "market buy order for 10 HLX"."""
    o = order
    if o.get("safety_net"):
        return f"safety net on {o['qty']} {o['symbol']}"
    return f"{o['type'].lower()} {o['side'].lower()} order for {o['qty']} {o['symbol']}"


def cancel(session, order, code, why=None):
    """Mark a resting order cancelled and tell the user why, in plain English."""
    order.update(status="CANCELLED", reason=code)
    add_event(session, "CANCEL", f"Day {session.cursor + 1}: cancelled your {describe(order)}" + (f": {why}" if why else "."))


def sync_stops(session, symbol):
    """After a position changes: cancel sells for a closed position, shrink a too-big safety net."""
    pos = session.positions.get(symbol)
    for o in session.orders:
        if o["status"] == "OPEN" and o["symbol"] == symbol and o["side"] == "SELL":
            if not pos:
                cancel(session, o, "POSITION_CLOSED", "you no longer hold those shares.")
            elif o.get("safety_net") and o["qty"] > pos["qty"]:
                o["qty"] = pos["qty"]


SOURCE_LABEL = {"MARKET": "", "LIMIT": " (limit order)", "STOP": " (stop order)", "SAFETY_NET": " (your safety net)"}


def execute(session, order, price, bar_index, reason):
    """Fills an order: updates cash, position, trades and the shadow benchmark."""
    sym = order["symbol"]
    cash, position, realized = sim.apply_fill(session.cash, session.positions.get(sym), order["side"], order["qty"], price)
    session.cash, session.realized = cash, round(session.realized + realized, 2)
    if position:
        session.positions[sym] = position
    else:
        session.positions.pop(sym, None)
        session.dismissed.discard(sym)
    order.update(status="FILLED", filled_bar=bar_index, fill_price=price, reason=reason)
    trade = {"order_id": order["id"], "bar": bar_index, "day": bar_index + 1, "symbol": sym,
             "side": order["side"], "qty": order["qty"], "price": price, "reason": reason,
             "realized_pnl": realized}
    session.trades.append(trade)
    if order["side"] == "BUY":
        session.first_buy_done = True
        session.dismissed.discard(sym)
    if reason == "SAFETY_NET":
        session.kept_lots.append({"qty": order["qty"], "fill_price": price, "bar": bar_index})
    verb = "bought" if order["side"] == "BUY" else "sold"
    add_event(session, "FILL", f"Day {bar_index + 1}: {verb} {order['qty']} {sym} at {usd(price)}"
                       f"{SOURCE_LABEL[reason]}.", order_id=order["id"])
    sync_stops(session, sym)
    return trade


# --------------------------------------------------------------------------- checks / QA

def trigger_met(session, trigger):
    return {"first_buy": session.first_buy_done, "safety_net_active": session.safety_net_used}[trigger]


def pending_check(session):
    for cid, chk in CHECKS.items():
        if cid not in session.checks_passed and trigger_met(session, chk["trigger"]):
            return cid
    return None


def qa_summary():
    per_check = {}
    for cid in CHECKS:
        first = {e["participant"]: e["correct"] for e in QA_LOG if e["check_id"] == cid and e["attempt"] == 1}
        per_check[cid] = {"participants": len(first), "first_try_correct": sum(first.values())}
    headline = next((cid for cid in ("safety_net", "downside") if per_check[cid]["participants"]), None)
    pitch = None
    if headline:
        c = per_check[headline]
        pitch = f"{c['first_try_correct']} of {c['participants']} first-time users {CHECKS[headline]['pitch_label']}."
    return {"participants": len({e["participant"] for e in QA_LOG}), "per_check": per_check,
            "pitch_line": pitch, "entries": QA_LOG}


# --------------------------------------------------------------------------- snapshot

def snapshot(session):
    """Everything the browser needs to render, in one object. Never contains a future bar.

    This is THE most important function in the file. Every mutating route returns
    {"state": snapshot(session)}, and the browser throws away its own state and re-renders
    from whatever this returns. The frontend never computes a price, a fill or a P&L -
    it only displays what this built.

    Two halves:
      1. `out` starts with safe defaults, so every key exists even before onboarding
         (the browser can render an empty shell without null-checking everything).
      2. If a replay IS running, `out.update(...)` fills in the live numbers.

    The "no look-ahead" rule lives here: `bars` is sliced to [0 .. cursor], so the
    response physically cannot contain tomorrow's price.
    """
    out = {
        "boot_id": BOOT_ID, "onboarded": session.onboarded, "participant": session.participant,
        "action_seq": len(session.replay_log),
        "starting_cash": session.starting_cash, "symbols": SYMBOLS, "symbol": session.symbol,
        "tier": session.tier, "tiers_unlocked": TIER_IDS[:TIER_IDS.index(session.tier) + 1],
        "cursor": session.cursor, "day": None, "total_days": len(session.bars) or None, "finished": False,
        "price": None, "bars": [], "strategy": None,
        "cash": round(session.cash, 2), "positions": [],
        "open_orders": [o for o in session.orders if o["status"] == "OPEN"], "trades": session.trades,
        "equity": round(session.cash, 2), "market_value": 0.0, "unrealized_pnl": 0.0,
        "unrealized_pnl_pct": 0.0, "realized_pnl": session.realized, "total_pnl": 0.0, "total_pnl_pct": 0.0,
        "shadow": {"active": False, "kept_qty": 0, "equity": round(session.cash, 2),
                   "delta_vs_you": 0.0, "saved_by_safety_net": 0.0},
        "prompts": [], "pending_check": None, "checks_passed": sorted(session.checks_passed),
        "events": session.events[-30:], "replay_log": session.replay_log, "fixture_meta": None,
    }
    if not session.onboarded:
        return out
    bar = current_bar(session)
    price = bar["c"]
    summ = sim.portfolio_summary(session.cash, session.positions, price)
    stops = {o["symbol"]: o["stop_price"] for o in session.orders if o["status"] == "OPEN" and o.get("safety_net")}
    positions = [{
        "symbol": sym, "qty": p["qty"], "avg_price": p["avg_price"], "price": price,
        "market_value": round(p["qty"] * price, 2),
        "unrealized_pnl": round((price - p["avg_price"]) * p["qty"], 2),
        "unrealized_pnl_pct": round((price / p["avg_price"] - 1) * 100, 2),
        "protected": sim.protected_qty(session.orders, sym) >= p["qty"], "stop_price": stops.get(sym),
    } for sym, p in sorted(session.positions.items())]
    delta = sim.shadow_delta(session.kept_lots, price)
    total = round(summ["equity"] - session.starting_cash, 2)
    fx = FIXTURES[session.symbol]
    finished = session.cursor >= len(session.bars) - 1
    out.update(
        day=bar["day"], finished=finished, price=price,
        bars=session.bars[:session.cursor + 1],
        strategy={"name": fx["strategy"]["name"], "fast": fx["strategy"]["fast"], "slow": fx["strategy"]["slow"],
                  "signals": [g for g in fx["strategy"]["signals"] if g["bar"] <= session.cursor]},
        positions=positions, equity=summ["equity"], market_value=summ["market_value"],
        unrealized_pnl=summ["unrealized_pnl"], unrealized_pnl_pct=summ["unrealized_pnl_pct"],
        total_pnl=total, total_pnl_pct=round(total / session.starting_cash * 100, 2),
        shadow={"active": bool(session.kept_lots), "kept_qty": sum(l["qty"] for l in session.kept_lots),
                "equity": round(summ["equity"] + delta, 2), "delta_vs_you": delta,
                "saved_by_safety_net": round(-delta, 2)},
        prompts=find_prompts(session), pending_check=pending_check(session),
        fixture_meta={"max_drawdown_pct": fx["meta"]["max_drawdown_pct"], "synthetic": True} if finished else None,
    )
    return out


# --------------------------------------------------------------------------- request models

class OnboardingReq(BaseModel):
    experience: Literal["new", "experienced"]
    symbol: str = "NVX"


class AdvanceReq(BaseModel):
    n: int = Field(1, ge=1, le=30)


class OrderReq(BaseModel):
    symbol: str = Field(..., min_length=1)
    side: Literal["BUY", "SELL"]
    type: Literal["MARKET", "LIMIT", "STOP"] = "MARKET"
    qty: int = Field(..., ge=1, le=sim.MAX_QTY)
    limit_price: Optional[float] = Field(None, gt=0)
    stop_price: Optional[float] = Field(None, gt=0)
    as_of: Optional[int] = Field(None, ge=0)

    @field_validator("side", "type", mode="before")
    @classmethod
    def _upper(cls, v):
        return v.upper() if isinstance(v, str) else v


class SafetyNetReq(BaseModel):
    symbol: str = Field(..., min_length=1)
    decision: Literal["accept", "dismiss"] = "accept"
    percent: Optional[float] = Field(None, gt=0, lt=100)
    stop_price: Optional[float] = Field(None, gt=0)


class ComprehensionReq(BaseModel):
    check_id: str
    choice: int = Field(..., ge=0)


# --------------------------------------------------------------------------- app

app = FastAPI(title="Rich-HER / Astra Trading (mock mode)", version="3.0")
app.add_middleware(
    CORSMiddleware, allow_methods=["*"], allow_headers=["*"],
    allow_origins=[o.strip() for o in os.getenv("RICHHER_CORS_ORIGINS", "*").split(",") if o.strip()],
)


@app.exception_handler(ApiError)
async def _api_error(_, exc: ApiError):
    return JSONResponse(status_code=exc.status, content={"error": exc.code, "message": exc.message, **exc.extra})


@app.exception_handler(RequestValidationError)
async def _validation_error(_, exc: RequestValidationError):
    details = [{"field": ".".join(str(p) for p in e["loc"][1:]) or str(e["loc"][0]), "message": e["msg"]}
               for e in exc.errors()]
    return JSONResponse(status_code=422, content={"error": "VALIDATION", "message": "The request is invalid.",
                                                  "details": details})


# ---- session & replay

@app.get("/api/state")
async def get_state():
    return snapshot(SESSION)


@app.post("/api/onboarding")
async def post_onboarding(req: OnboardingReq):
    session = SESSION
    if session.onboarded:
        raise ApiError(409, "ALREADY_ONBOARDED", "A replay is already running. Reset the demo to start over.")
    fx = FIXTURES.get(req.symbol.upper())
    if not fx:
        raise ApiError(404, "UNKNOWN_SYMBOL", f"Choose one of: {', '.join(FIXTURES)}.")
    session.onboarded, session.symbol, session.bars, session.cursor = True, fx["symbol"], fx["bars"], fx["start_cursor"]
    # Each fixture declares the practice account it is priced for: HLX's $168 shares need
    # $10,000, NVX's $21 shares are built for the $100 story (STORY.md section 2).
    session.cash = session.starting_cash = fx.get("start_cash", sim.STARTING_CASH)
    session.worst_equity = session.starting_cash
    session.tier = START_TIER[req.experience]
    add_event(session, "START", f"Day {session.cursor + 1}: replay starts on {session.symbol} with {usd(session.cash)} in cash. "
                       "The future is hidden.")
    record(session, "POST", "/api/onboarding", {"experience": req.experience, "symbol": session.symbol})
    return {"state": snapshot(session)}


@app.post("/api/advance")
async def post_advance(req: AdvanceReq):
    session = SESSION
    require_onboarded(session)
    last = len(session.bars) - 1
    if session.cursor >= last:
        raise ApiError(409, "REPLAY_FINISHED", "You have reached the last day of the replay.")
    pending = find_prompts(session)
    if pending:
        raise ApiError(409, "PROMPT_PENDING", "Answer the safety-net prompt before moving on.", prompts=pending)
    # Step one day at a time - never jump straight to cursor + n - so we can stop the
    # instant something happens. That is what makes fast-forward safe: a fill or a
    # safety-net prompt can never be skipped over.
    first_event, steps = len(session.events), 0
    while steps < req.n and session.cursor < last:
        session.cursor = sim.advance(session.cursor, 1, last)
        steps += 1
        bar = current_bar(session)
        stop_here = False
        for hit in sim.check_open_orders_for_bar(session.orders, session.cursor, bar):
            order = session.orders[hit["order_id"] - 1]
            try:
                execute(session, order, hit["price"], session.cursor, hit["reason"])
            except sim.SimError as e:
                cancel(session, order, e.code, e.message)
            stop_here = True
        found = find_prompts(session)
        if found:
            c = found[0]
            add_event(session, "SAFETY_NET_PROMPT", f"Day {bar['day']}: {c['symbol']} is down {abs(c['loss_pct']):.1f}% "
                               f"from your entry ({usd(c['avg_price'])}).")
            stop_here = True
        if stop_here:
            break
    if session.cursor >= last:
        add_event(session, "END", f"Day {session.cursor + 1}: the replay is over.")
    record(session, "POST", "/api/advance", {"n": req.n})
    return {"advanced": steps, "events": session.events[first_event:], "state": snapshot(session)}


@app.post("/api/reset")
async def post_reset():
    global SESSION
    SESSION = Session(participant=SESSION.participant + 1)
    return {"state": snapshot(SESSION)}


# ---- market data

@app.get("/api/quote")
async def get_quote(symbol: Optional[str] = None, as_of: Optional[int] = Query(None, ge=0)):
    session = SESSION
    require_onboarded(session)
    sym = (symbol or session.symbol).upper()
    fx = FIXTURES.get(sym)
    if not fx:
        raise ApiError(404, "UNKNOWN_SYMBOL", f"Choose one of: {', '.join(FIXTURES)}.")
    bar_index = session.cursor if as_of is None else as_of
    if bar_index > session.cursor:
        raise ApiError(400, "FUTURE_BAR", "You cannot see a bar that has not happened yet.", cursor=session.cursor)
    bar = sim.price_at(fx["bars"], bar_index)
    return {"symbol": sym, "as_of": bar["i"], "price": bar["c"],
            "bar": {k: bar[k] for k in ("day", "o", "h", "l", "c")}}


# ---- trading

@app.post("/api/orders")
async def post_order(req: OrderReq):
    session = SESSION
    require_onboarded(session)
    if req.symbol.upper() != session.symbol:
        raise ApiError(400, "SYMBOL_MISMATCH", f"This replay trades {session.symbol}.")
    if req.as_of is not None and req.as_of != session.cursor:
        raise ApiError(409, "STALE_CURSOR", f"Your screen is on bar {req.as_of} but the replay is on bar {session.cursor}.",
                       cursor=session.cursor)
    if req.type not in caps(session.tier)["order_types"]:
        need = next(t for t in TIERS if req.type in t["unlocks"]["order_types"])
        raise ApiError(403, "TIER_LOCKED", f"{req.type.title()} orders unlock at {need['title']}. {need['how_to_unlock']}",
                       required_tier=need["id"], tier=session.tier)
    bar, pos = current_bar(session), session.positions.get(session.symbol)
    order = {"id": len(session.orders) + 1, "symbol": session.symbol, "side": req.side, "type": req.type, "qty": req.qty,
             "limit_price": req.limit_price, "stop_price": req.stop_price, "status": "OPEN", "safety_net": False,
             "created_bar": session.cursor, "filled_bar": None, "fill_price": None, "reason": None}
    try:
        sim.validate_order(order, bar["c"], session.cash, pos["qty"] if pos else 0)
    except sim.SimError as e:
        raise sim_error(e)
    session.orders.append(order)
    fills = []
    price = sim.immediate_fill_price(order, bar)
    if price is not None:
        fills.append(execute(session, order, price, session.cursor, order["type"]))
    else:
        level = usd(order["limit_price"] if order["type"] == "LIMIT" else order["stop_price"])
        add_event(session, "ORDER", f"Day {bar['day']}: placed a {describe(order)} at {level}. It waits until the price reaches it.")
    record(session, "POST", "/api/orders", req.model_dump(exclude_none=True))
    return {"order": order, "fills": fills, "state": snapshot(session)}


@app.delete("/api/orders/{order_id}")
async def delete_order(order_id: int):
    session = SESSION
    require_onboarded(session)
    if not 1 <= order_id <= len(session.orders):
        raise ApiError(404, "ORDER_NOT_FOUND", f"There is no order {order_id}.")
    order = session.orders[order_id - 1]
    if order["status"] != "OPEN":
        raise ApiError(409, "ORDER_NOT_OPEN", f"Order {order_id} is already {order['status'].lower()}.")
    cancel(session, order, "USER")
    record(session, "DELETE", f"/api/orders/{order_id}")
    return {"order": order, "state": snapshot(session)}


@app.get("/api/portfolio")
async def get_portfolio():
    session = SESSION
    require_onboarded(session)
    st = snapshot(session)
    return {"as_of": session.cursor, **{k: st[k] for k in (
        "cash", "positions", "equity", "market_value", "unrealized_pnl", "unrealized_pnl_pct",
        "realized_pnl", "open_orders")}}


@app.post("/api/safety-net")
async def post_safety_net(req: SafetyNetReq):
    session = SESSION
    require_onboarded(session)
    sym = req.symbol.upper()
    pos = session.positions.get(sym)
    if not pos:
        raise ApiError(404, "NO_POSITION", f"You do not hold any {sym}.")
    if req.decision == "dismiss":
        session.dismissed.add(sym)
        add_event(session, "SAFETY_NET_DISMISSED", f"Day {session.cursor + 1}: you chose to keep holding {sym} without a safety net.")
        record(session, "POST", "/api/safety-net", req.model_dump(exclude_none=True))
        return {"state": snapshot(session)}
    percent = DEFAULT_STOP_PERCENT if req.percent is None else req.percent
    if (req.stop_price is not None or abs(percent - DEFAULT_STOP_PERCENT) > 1e-9) and not caps(session.tier)["custom_safety_net"]:
        need = next(t for t in TIERS if t["unlocks"]["custom_safety_net"])
        raise ApiError(403, "TIER_LOCKED", f"Choosing your own safety net unlocks at {need['title']}. {need['how_to_unlock']}",
                       required_tier=need["id"], tier=session.tier)
    if sim.protected_qty(session.orders, sym) >= pos["qty"]:
        raise ApiError(409, "ALREADY_PROTECTED", f"Your {sym} position already has a safety net.")
    stop = req.stop_price if req.stop_price is not None else sim.stop_price_for(pos["avg_price"], -percent)
    bar = current_bar(session)
    order = {"id": len(session.orders) + 1, "symbol": sym, "side": "SELL", "type": "STOP", "qty": pos["qty"],
             "limit_price": None, "stop_price": stop, "status": "OPEN", "safety_net": True,
             "created_bar": session.cursor, "filled_bar": None, "fill_price": None, "reason": None}
    try:
        sim.validate_order(order, bar["c"], session.cash, pos["qty"])
    except sim.SimError as e:
        raise sim_error(e)
    session.orders.append(order)
    session.safety_net_used = True
    add_event(session, "SAFETY_NET_ON", f"Day {bar['day']}: safety net set. It sells {pos['qty']} {sym} if the price "
                       f"falls to {usd(stop)}.")
    record(session, "POST", "/api/safety-net", req.model_dump(exclude_none=True))
    return {"order": order, "state": snapshot(session)}


# ---- teaching

@app.get("/api/tiers")
async def get_tiers():
    session = SESSION
    return {"tiers": TIERS, "active": session.tier, "unlocked": TIER_IDS[:TIER_IDS.index(session.tier) + 1]}


@app.post("/api/comprehension")
async def post_comprehension(req: ComprehensionReq):
    session = SESSION
    require_onboarded(session)
    chk = CHECKS.get(req.check_id)
    if not chk:
        raise ApiError(404, "UNKNOWN_CHECK", f"Unknown check. Choose one of: {', '.join(CHECKS)}.")
    if not trigger_met(session, chk["trigger"]) or req.check_id in session.checks_passed:
        raise ApiError(409, "CHECK_NOT_AVAILABLE", "This check is not waiting for an answer.")
    if req.choice >= len(chk["options"]):
        raise ApiError(400, "INVALID_CHOICE", f"Choose an option from 0 to {len(chk['options']) - 1}.")
    attempt = session.check_attempts.get(req.check_id, 0) + 1
    session.check_attempts[req.check_id] = attempt
    correct = req.choice == chk["answer"]
    QA_LOG.append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "participant": session.participant,
                   "check_id": req.check_id, "choice": req.choice, "correct": correct, "attempt": attempt,
                   "tier": session.tier, "symbol": session.symbol})
    unlocked = None
    if correct:
        session.checks_passed.add(req.check_id)
        target = chk.get("unlocks")
        if target and TIER_IDS.index(target) > TIER_IDS.index(session.tier):
            session.tier = unlocked = target
            add_event(session, "UNLOCK", f"Day {session.cursor + 1}: unlocked {tier_title(target)}.")
    record(session, "POST", "/api/comprehension", {"check_id": req.check_id, "choice": req.choice})
    return {"correct": correct, "attempt": attempt, "unlocked_tier": unlocked,
            "explanation": chk["explain_correct"] if correct else chk["explain_wrong"], "state": snapshot(session)}


@app.get("/api/qa-log")
async def get_qa_log():
    return qa_summary()


# ---- story (STORY.md). The browser renders scenes; the server owns which one is current.

class SceneReq(BaseModel):
    scene_id: str = Field(..., min_length=1)
    option_id: Optional[str] = None


def story_state(session):
    """Computed state + flags, rebuilt from the portfolio on every call so it cannot drift."""
    if session.onboarded:
        summary = sim.portfolio_summary(session.cash, session.positions, current_bar(session)["c"])
        equity = summary["equity"]
        positions = [{"symbol": sym, "cost": round(p["qty"] * p["avg_price"], 2)}
                     for sym, p in session.positions.items()]
    else:
        equity, positions = session.cash, []
    computed = story.compute(equity, session.cash, session.trades, positions,
                             session.worst_equity, session.starting_cash)
    session.worst_equity = computed["worst_equity_seen"]
    flags = story.derive_flags(computed, session.trades, positions, _sold_at_worst(session, computed))
    return computed, flags | session.flags


def _sold_at_worst(session, computed):
    """Did she sell everything at the lowest equity she ever saw? That is the panic flag."""
    if session.positions or not session.trades:
        return False
    return any(t["side"] == "SELL" for t in session.trades) and         computed["equity"] <= computed["worst_equity_seen"] + 0.01


def apply_effect(session, effect):
    """Move real money for a story choice, e.g. a pressure event's {"withdraw": 40}.

    story_engine names the effect but never applies it - touching the portfolio is I/O and
    that module stays pure. Unknown keys are rejected there, so anything arriving here is
    a real effect.
    """
    amount = effect.get("withdraw")
    if amount is not None:
        if amount > session.cash + sim.EPS:
            raise ApiError(409, "CANNOT_WITHDRAW",
                           f"That takes {usd(amount)} but only {usd(session.cash)} is in cash. "
                           "Sell something first, or choose the other option.",
                           required=amount, available=round(session.cash, 2))
        session.cash = round(session.cash - amount, 2)
        add_event(session, "WITHDRAW", f"Day {session.cursor + 1}: took {usd(amount)} out of the account.")

    amount = effect.get("deposit")
    if amount is not None:
        session.cash = round(session.cash + amount, 2)
        add_event(session, "DEPOSIT", f"Day {session.cursor + 1}: put {usd(amount)} into the account.")


def _graph(act_id):
    graph = SCENES.get(act_id)
    if graph is None:
        raise ApiError(404, "UNKNOWN_ACT", f"No such act. Choose one of: {', '.join(SCENES)}.")
    return graph


@app.get("/api/story")
async def get_story():
    """The current scene, the computed state, the flags, and where she stands with Vela."""
    session = SESSION
    computed, flags = story_state(session)
    scene = None
    if session.scene and session.act:
        scene = story.visible(_graph(session.act)["nodes"][session.scene], computed, flags)
        scene["id"] = session.scene
    return {"act": session.act, "scene": scene, "computed": computed,
            "flags": sorted(flags), "wager": story.wager_state(computed),
            "acts": sorted(SCENES)}


@app.post("/api/story/start")
async def post_story_start(act_id: str = Query("act4")):
    """Jump to the start of an act. The frontend calls this once per chapter."""
    session = SESSION
    graph = _graph(act_id)
    session.act, session.scene = act_id, graph["start"]
    record(session, "POST", f"/api/story/start?act_id={act_id}")
    return await get_story()


@app.post("/api/story/advance")
async def post_story_advance(req: SceneReq):
    """Move to the next scene, applying whatever the chosen option sets."""
    session = SESSION
    if not session.act:
        raise ApiError(409, "NO_STORY", "Start an act first: POST /api/story/start.")
    graph = _graph(session.act)
    if req.scene_id != session.scene:
        raise ApiError(409, "STALE_SCENE", f"Your screen is on {req.scene_id} but the story is on "
                       f"{session.scene}.", scene=session.scene)
    try:
        if req.option_id is not None:
            session.flags, effect = story.apply_choice(graph, req.scene_id, req.option_id, session.flags)
            apply_effect(session, effect)
        session.scene = story.next_scene(graph, req.scene_id, req.option_id)
    except story.StoryError as e:
        raise ApiError(400, e.code, e.message, **e.extra)
    record(session, "POST", "/api/story/advance", req.model_dump(exclude_none=True))
    return await get_story()


@app.get("/api/story/ending")
async def get_story_ending():
    """Which ending she has earned, evaluated server-side. Never decided by the browser."""
    session = SESSION
    computed, flags = story_state(session)
    try:
        ending = story.choose_ending(ENDINGS["endings"], computed, flags)
    except story.StoryError as e:
        raise ApiError(500, e.code, e.message, **e.extra)
    return {"ending": ending, "computed": computed, "flags": sorted(flags),
            "wager": story.wager_state(computed)}


@app.get("/api/coach")
async def get_coach():
    """Nia's persona and the pop-out copy for every coached control."""
    return COACH


# ---- mock-only stubs (exist so the contract is complete; not wired into the UI)

@app.get("/api/news")
async def get_news(symbol: Optional[str] = None):
    return {"stub": True, "symbol": symbol, "items": [], "notice": "News is stubbed in mock mode."}


@app.get("/api/fundamentals")
async def get_fundamentals(symbol: Optional[str] = None):
    return {"stub": True, "symbol": symbol, "fundamentals": None,
            "notice": "Fundamentals are stubbed in mock mode."}


# ---- the browser app, so one process serves everything (`uvicorn server.main:app`)

for _ext, _type in ((".js", "application/javascript"), (".mjs", "application/javascript"),
                    (".css", "text/css"), (".json", "application/json")):
    mimetypes.add_type(_type, _ext)   # Windows registries sometimes map .js to text/plain, which breaks ES modules
class NoCacheStatic(StaticFiles):
    """Serve web/ with caching off.

    Without this the browser keeps its own copy of app.js and friends, so you edit a file,
    refresh, and see the OLD code - with no error to tell you why. ES modules are cached
    especially stubbornly, and a "hard" reload does not reliably clear them.

    The whole app is a handful of small files served from localhost, so there is nothing to
    gain from caching here and a great deal of confusion to lose.
    """

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, must-revalidate"
        return response


app.mount("/", NoCacheStatic(directory=str(WEB_DIR), html=True), name="web")
