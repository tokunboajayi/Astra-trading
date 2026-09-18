"""
server/main.py

FastAPI app for Rich-HER / Astra Trading. Mock mode only: no Alpaca, no live data.
Session-authoritative: one in-memory demo session holds the truth, and the browser renders
whatever /api/state says. The rules live in server/sim_engine.py; this file is the session,
the tier gates and the HTTP layer. Owned by B (Backend). Contract: SPEC.md section 8.

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


FIXTURES = {p.stem: _load(p) for p in sorted(FIXTURE_DIR.glob("*.json"), key=lambda p: (p.stem != "AAPL", p.stem))}
if not FIXTURES:
    raise SystemExit("No fixtures in fixtures/. Run: python scripts/build_fixtures.py")
TIERS = _load(WEB_DIR / "tiers.json")
CHECKS = _load(WEB_DIR / "checks.json")
TIER_IDS = [t["id"] for t in TIERS]
SYMBOLS = [{k: f[k] for k in ("symbol", "name", "blurb", "volatility", "start_cursor")} for f in FIXTURES.values()]


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


SESSION = Session(participant=1)
QA_LOG = []          # survives /api/reset so V2 can total up stranger-QA across participants
BOOT_ID = uuid.uuid4().hex[:8]   # new on every server start: tells the browser "I restarted" from "I was reset"


def record(s, method, path, body=None):
    s.replay_log.append({"method": method, "path": path, "body": body})


def add_event(s, kind, message, **data):
    s.events.append({"seq": len(s.events) + 1, "bar": s.cursor, "day": s.cursor + 1,
                     "type": kind, "message": message, **data})


def require_onboarded(s):
    if not s.onboarded:
        raise ApiError(409, "NOT_ONBOARDED", "Start a replay first: POST /api/onboarding.")


def current_bar(s):
    return sim.price_at(s.bars, s.cursor)


def caps(tier):
    return next(t for t in TIERS if t["id"] == tier)["unlocks"]


def tier_title(tier):
    return next(t for t in TIERS if t["id"] == tier)["title"]


def find_prompts(s):
    if not s.onboarded:
        return []
    return sim.check_safety_net_candidates(s.positions, current_bar(s)["c"], s.orders, s.dismissed)


def describe(o):
    if o.get("safety_net"):
        return f"safety net on {o['qty']} {o['symbol']}"
    return f"{o['type'].lower()} {o['side'].lower()} order for {o['qty']} {o['symbol']}"


def cancel(s, order, code, why=None):
    order.update(status="CANCELLED", reason=code)
    add_event(s, "CANCEL", f"Day {s.cursor + 1}: cancelled your {describe(order)}" + (f": {why}" if why else "."))


def sync_stops(s, symbol):
    """After a position changes: cancel sells for a closed position, shrink a too-big safety net."""
    pos = s.positions.get(symbol)
    for o in s.orders:
        if o["status"] == "OPEN" and o["symbol"] == symbol and o["side"] == "SELL":
            if not pos:
                cancel(s, o, "POSITION_CLOSED", "you no longer hold those shares.")
            elif o.get("safety_net") and o["qty"] > pos["qty"]:
                o["qty"] = pos["qty"]


SOURCE_LABEL = {"MARKET": "", "LIMIT": " (limit order)", "STOP": " (stop order)", "SAFETY_NET": " (your safety net)"}


def execute(s, order, price, bar_index, reason):
    """Fills an order: updates cash, position, trades and the shadow benchmark."""
    sym = order["symbol"]
    cash, position, realized = sim.apply_fill(s.cash, s.positions.get(sym), order["side"], order["qty"], price)
    s.cash, s.realized = cash, round(s.realized + realized, 2)
    if position:
        s.positions[sym] = position
    else:
        s.positions.pop(sym, None)
        s.dismissed.discard(sym)
    order.update(status="FILLED", filled_bar=bar_index, fill_price=price, reason=reason)
    trade = {"order_id": order["id"], "bar": bar_index, "day": bar_index + 1, "symbol": sym,
             "side": order["side"], "qty": order["qty"], "price": price, "reason": reason,
             "realized_pnl": realized}
    s.trades.append(trade)
    if order["side"] == "BUY":
        s.first_buy_done = True
        s.dismissed.discard(sym)
    if reason == "SAFETY_NET":
        s.kept_lots.append({"qty": order["qty"], "fill_price": price, "bar": bar_index})
    verb = "bought" if order["side"] == "BUY" else "sold"
    add_event(s, "FILL", f"Day {bar_index + 1}: {verb} {order['qty']} {sym} at {usd(price)}"
                         f"{SOURCE_LABEL[reason]}.", order_id=order["id"])
    sync_stops(s, sym)
    return trade


# --------------------------------------------------------------------------- checks / QA

def trigger_met(s, trigger):
    return {"first_buy": s.first_buy_done, "safety_net_active": s.safety_net_used}[trigger]


def pending_check(s):
    for cid, chk in CHECKS.items():
        if cid not in s.checks_passed and trigger_met(s, chk["trigger"]):
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

def snapshot(s):
    """Everything the browser needs to render, in one object. Never contains a future bar."""
    out = {
        "boot_id": BOOT_ID, "onboarded": s.onboarded, "participant": s.participant,
        "action_seq": len(s.replay_log),
        "starting_cash": sim.STARTING_CASH, "symbols": SYMBOLS, "symbol": s.symbol,
        "tier": s.tier, "tiers_unlocked": TIER_IDS[:TIER_IDS.index(s.tier) + 1],
        "cursor": s.cursor, "day": None, "total_days": len(s.bars) or None, "finished": False,
        "price": None, "bars": [], "strategy": None,
        "cash": round(s.cash, 2), "positions": [],
        "open_orders": [o for o in s.orders if o["status"] == "OPEN"], "trades": s.trades,
        "equity": round(s.cash, 2), "market_value": 0.0, "unrealized_pnl": 0.0,
        "unrealized_pnl_pct": 0.0, "realized_pnl": s.realized, "total_pnl": 0.0, "total_pnl_pct": 0.0,
        "shadow": {"active": False, "kept_qty": 0, "equity": round(s.cash, 2),
                   "delta_vs_you": 0.0, "saved_by_safety_net": 0.0},
        "prompts": [], "pending_check": None, "checks_passed": sorted(s.checks_passed),
        "events": s.events[-30:], "replay_log": s.replay_log, "fixture_meta": None,
    }
    if not s.onboarded:
        return out
    bar = current_bar(s)
    price = bar["c"]
    summ = sim.portfolio_summary(s.cash, s.positions, price)
    stops = {o["symbol"]: o["stop_price"] for o in s.orders if o["status"] == "OPEN" and o.get("safety_net")}
    positions = [{
        "symbol": sym, "qty": p["qty"], "avg_price": p["avg_price"], "price": price,
        "market_value": round(p["qty"] * price, 2),
        "unrealized_pnl": round((price - p["avg_price"]) * p["qty"], 2),
        "unrealized_pnl_pct": round((price / p["avg_price"] - 1) * 100, 2),
        "protected": sim.protected_qty(s.orders, sym) >= p["qty"], "stop_price": stops.get(sym),
    } for sym, p in sorted(s.positions.items())]
    delta = sim.shadow_delta(s.kept_lots, price)
    total = round(summ["equity"] - sim.STARTING_CASH, 2)
    fx = FIXTURES[s.symbol]
    finished = s.cursor >= len(s.bars) - 1
    out.update(
        day=bar["day"], finished=finished, price=price,
        bars=s.bars[:s.cursor + 1],
        strategy={"name": fx["strategy"]["name"], "fast": fx["strategy"]["fast"], "slow": fx["strategy"]["slow"],
                  "signals": [g for g in fx["strategy"]["signals"] if g["bar"] <= s.cursor]},
        positions=positions, equity=summ["equity"], market_value=summ["market_value"],
        unrealized_pnl=summ["unrealized_pnl"], unrealized_pnl_pct=summ["unrealized_pnl_pct"],
        total_pnl=total, total_pnl_pct=round(total / sim.STARTING_CASH * 100, 2),
        shadow={"active": bool(s.kept_lots), "kept_qty": sum(l["qty"] for l in s.kept_lots),
                "equity": round(summ["equity"] + delta, 2), "delta_vs_you": delta,
                "saved_by_safety_net": round(-delta, 2)},
        prompts=find_prompts(s), pending_check=pending_check(s),
        fixture_meta={"max_drawdown_pct": fx["meta"]["max_drawdown_pct"], "synthetic": True} if finished else None,
    )
    return out


# --------------------------------------------------------------------------- request models

class OnboardingReq(BaseModel):
    experience: Literal["new", "experienced"]
    symbol: str = "AAPL"


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
    s = SESSION
    if s.onboarded:
        raise ApiError(409, "ALREADY_ONBOARDED", "A replay is already running. Reset the demo to start over.")
    fx = FIXTURES.get(req.symbol.upper())
    if not fx:
        raise ApiError(404, "UNKNOWN_SYMBOL", f"Choose one of: {', '.join(FIXTURES)}.")
    s.onboarded, s.symbol, s.bars, s.cursor = True, fx["symbol"], fx["bars"], fx["start_cursor"]
    s.tier = START_TIER[req.experience]
    add_event(s, "START", f"Day {s.cursor + 1}: replay starts on {s.symbol} with {usd(s.cash)} in cash. "
                          "The future is hidden.")
    record(s, "POST", "/api/onboarding", {"experience": req.experience, "symbol": s.symbol})
    return {"state": snapshot(s)}


@app.post("/api/advance")
async def post_advance(req: AdvanceReq):
    s = SESSION
    require_onboarded(s)
    last = len(s.bars) - 1
    if s.cursor >= last:
        raise ApiError(409, "REPLAY_FINISHED", "You have reached the last day of the replay.")
    pending = find_prompts(s)
    if pending:
        raise ApiError(409, "PROMPT_PENDING", "Answer the safety-net prompt before moving on.", prompts=pending)
    first_event, steps = len(s.events), 0
    while steps < req.n and s.cursor < last:
        s.cursor = sim.advance(s.cursor, 1, last)
        steps += 1
        bar = current_bar(s)
        stop_here = False
        for hit in sim.check_open_orders_for_bar(s.orders, s.cursor, bar):
            order = s.orders[hit["order_id"] - 1]
            try:
                execute(s, order, hit["price"], s.cursor, hit["reason"])
            except sim.SimError as e:
                cancel(s, order, e.code, e.message)
            stop_here = True
        found = find_prompts(s)
        if found:
            c = found[0]
            add_event(s, "SAFETY_NET_PROMPT", f"Day {bar['day']}: {c['symbol']} is down {abs(c['loss_pct']):.1f}% "
                                              f"from your entry ({usd(c['avg_price'])}).")
            stop_here = True
        if stop_here:
            break
    if s.cursor >= last:
        add_event(s, "END", f"Day {s.cursor + 1}: the replay is over.")
    record(s, "POST", "/api/advance", {"n": req.n})
    return {"advanced": steps, "events": s.events[first_event:], "state": snapshot(s)}


@app.post("/api/reset")
async def post_reset():
    global SESSION
    SESSION = Session(participant=SESSION.participant + 1)
    return {"state": snapshot(SESSION)}


# ---- market data

@app.get("/api/quote")
async def get_quote(symbol: Optional[str] = None, as_of: Optional[int] = Query(None, ge=0)):
    s = SESSION
    require_onboarded(s)
    sym = (symbol or s.symbol).upper()
    fx = FIXTURES.get(sym)
    if not fx:
        raise ApiError(404, "UNKNOWN_SYMBOL", f"Choose one of: {', '.join(FIXTURES)}.")
    bar_index = s.cursor if as_of is None else as_of
    if bar_index > s.cursor:
        raise ApiError(400, "FUTURE_BAR", "You cannot see a bar that has not happened yet.", cursor=s.cursor)
    bar = sim.price_at(fx["bars"], bar_index)
    return {"symbol": sym, "as_of": bar["i"], "price": bar["c"],
            "bar": {k: bar[k] for k in ("day", "o", "h", "l", "c")}}


# ---- trading

@app.post("/api/orders")
async def post_order(req: OrderReq):
    s = SESSION
    require_onboarded(s)
    if req.symbol.upper() != s.symbol:
        raise ApiError(400, "SYMBOL_MISMATCH", f"This replay trades {s.symbol}.")
    if req.as_of is not None and req.as_of != s.cursor:
        raise ApiError(409, "STALE_CURSOR", f"Your screen is on bar {req.as_of} but the replay is on bar {s.cursor}.",
                       cursor=s.cursor)
    if req.type not in caps(s.tier)["order_types"]:
        need = next(t for t in TIERS if req.type in t["unlocks"]["order_types"])
        raise ApiError(403, "TIER_LOCKED", f"{req.type.title()} orders unlock at {need['title']}. {need['how_to_unlock']}",
                       required_tier=need["id"], tier=s.tier)
    bar, pos = current_bar(s), s.positions.get(s.symbol)
    order = {"id": len(s.orders) + 1, "symbol": s.symbol, "side": req.side, "type": req.type, "qty": req.qty,
             "limit_price": req.limit_price, "stop_price": req.stop_price, "status": "OPEN", "safety_net": False,
             "created_bar": s.cursor, "filled_bar": None, "fill_price": None, "reason": None}
    try:
        sim.validate_order(order, bar["c"], s.cash, pos["qty"] if pos else 0)
    except sim.SimError as e:
        raise sim_error(e)
    s.orders.append(order)
    fills = []
    price = sim.immediate_fill_price(order, bar)
    if price is not None:
        fills.append(execute(s, order, price, s.cursor, order["type"]))
    else:
        level = usd(order["limit_price"] if order["type"] == "LIMIT" else order["stop_price"])
        add_event(s, "ORDER", f"Day {bar['day']}: placed a {describe(order)} at {level}. It waits until the price reaches it.")
    record(s, "POST", "/api/orders", req.model_dump(exclude_none=True))
    return {"order": order, "fills": fills, "state": snapshot(s)}


@app.delete("/api/orders/{order_id}")
async def delete_order(order_id: int):
    s = SESSION
    require_onboarded(s)
    if not 1 <= order_id <= len(s.orders):
        raise ApiError(404, "ORDER_NOT_FOUND", f"There is no order {order_id}.")
    order = s.orders[order_id - 1]
    if order["status"] != "OPEN":
        raise ApiError(409, "ORDER_NOT_OPEN", f"Order {order_id} is already {order['status'].lower()}.")
    cancel(s, order, "USER")
    record(s, "DELETE", f"/api/orders/{order_id}")
    return {"order": order, "state": snapshot(s)}


@app.get("/api/portfolio")
async def get_portfolio():
    s = SESSION
    require_onboarded(s)
    st = snapshot(s)
    return {"as_of": s.cursor, **{k: st[k] for k in (
        "cash", "positions", "equity", "market_value", "unrealized_pnl", "unrealized_pnl_pct",
        "realized_pnl", "open_orders")}}


@app.post("/api/safety-net")
async def post_safety_net(req: SafetyNetReq):
    s = SESSION
    require_onboarded(s)
    sym = req.symbol.upper()
    pos = s.positions.get(sym)
    if not pos:
        raise ApiError(404, "NO_POSITION", f"You do not hold any {sym}.")
    if req.decision == "dismiss":
        s.dismissed.add(sym)
        add_event(s, "SAFETY_NET_DISMISSED", f"Day {s.cursor + 1}: you chose to keep holding {sym} without a safety net.")
        record(s, "POST", "/api/safety-net", req.model_dump(exclude_none=True))
        return {"state": snapshot(s)}
    percent = DEFAULT_STOP_PERCENT if req.percent is None else req.percent
    if (req.stop_price is not None or abs(percent - DEFAULT_STOP_PERCENT) > 1e-9) and not caps(s.tier)["custom_safety_net"]:
        need = next(t for t in TIERS if t["unlocks"]["custom_safety_net"])
        raise ApiError(403, "TIER_LOCKED", f"Choosing your own safety net unlocks at {need['title']}. {need['how_to_unlock']}",
                       required_tier=need["id"], tier=s.tier)
    if sim.protected_qty(s.orders, sym) >= pos["qty"]:
        raise ApiError(409, "ALREADY_PROTECTED", f"Your {sym} position already has a safety net.")
    stop = req.stop_price if req.stop_price is not None else sim.stop_price_for(pos["avg_price"], -percent)
    bar = current_bar(s)
    order = {"id": len(s.orders) + 1, "symbol": sym, "side": "SELL", "type": "STOP", "qty": pos["qty"],
             "limit_price": None, "stop_price": stop, "status": "OPEN", "safety_net": True,
             "created_bar": s.cursor, "filled_bar": None, "fill_price": None, "reason": None}
    try:
        sim.validate_order(order, bar["c"], s.cash, pos["qty"])
    except sim.SimError as e:
        raise sim_error(e)
    s.orders.append(order)
    s.safety_net_used = True
    add_event(s, "SAFETY_NET_ON", f"Day {bar['day']}: safety net set. It sells {pos['qty']} {sym} if the price "
                                  f"falls to {usd(stop)}.")
    record(s, "POST", "/api/safety-net", req.model_dump(exclude_none=True))
    return {"order": order, "state": snapshot(s)}


# ---- teaching

@app.get("/api/tiers")
async def get_tiers():
    s = SESSION
    return {"tiers": TIERS, "active": s.tier, "unlocked": TIER_IDS[:TIER_IDS.index(s.tier) + 1]}


@app.post("/api/comprehension")
async def post_comprehension(req: ComprehensionReq):
    s = SESSION
    require_onboarded(s)
    chk = CHECKS.get(req.check_id)
    if not chk:
        raise ApiError(404, "UNKNOWN_CHECK", f"Unknown check. Choose one of: {', '.join(CHECKS)}.")
    if not trigger_met(s, chk["trigger"]) or req.check_id in s.checks_passed:
        raise ApiError(409, "CHECK_NOT_AVAILABLE", "This check is not waiting for an answer.")
    if req.choice >= len(chk["options"]):
        raise ApiError(400, "INVALID_CHOICE", f"Choose an option from 0 to {len(chk['options']) - 1}.")
    attempt = s.check_attempts.get(req.check_id, 0) + 1
    s.check_attempts[req.check_id] = attempt
    correct = req.choice == chk["answer"]
    QA_LOG.append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "participant": s.participant,
                   "check_id": req.check_id, "choice": req.choice, "correct": correct, "attempt": attempt,
                   "tier": s.tier, "symbol": s.symbol})
    unlocked = None
    if correct:
        s.checks_passed.add(req.check_id)
        target = chk.get("unlocks")
        if target and TIER_IDS.index(target) > TIER_IDS.index(s.tier):
            s.tier = unlocked = target
            add_event(s, "UNLOCK", f"Day {s.cursor + 1}: unlocked {tier_title(target)}.")
    record(s, "POST", "/api/comprehension", {"check_id": req.check_id, "choice": req.choice})
    return {"correct": correct, "attempt": attempt, "unlocked_tier": unlocked,
            "explanation": chk["explain_correct"] if correct else chk["explain_wrong"], "state": snapshot(s)}


@app.get("/api/qa-log")
async def get_qa_log():
    return qa_summary()


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
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
