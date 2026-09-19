"""
server/main.py

FastAPI app for Rich-HER / Astra Trading. Mock mode only: no Alpaca, no live data.
Session-authoritative: an in-memory session per browser (rh_sid cookie) holds the truth, and
the browser renders whatever /api/state says. The rules live in server/sim_engine.py; this file is the session,
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

from fastapi import FastAPI, Query, Request
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
DEFAULT_STOP_PERCENT = 10.0
DEFAULT_SYMBOL = "VOLT"        # the featured stock: what a fresh session is focused on
DEFAULT_START_CASH = 100.00    # every fixture agrees on this now (one shared account, six symbols)


def _load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Missing {path.relative_to(ROOT)}. Fixtures come from: python scripts/build_fixtures.py")


# VOLT sorts first: it is the featured stock and what the ticket opens on. Everything
# else follows alphabetically. All six symbols are loaded and tradeable at once - the
# floor is a single shared account with a watchlist, not one onboarded symbol.
FIXTURES = {p.stem: _load(p) for p in sorted(FIXTURE_DIR.glob("*.json"), key=lambda p: (p.stem != DEFAULT_SYMBOL, p.stem))}
if not FIXTURES:
    raise SystemExit("No fixtures in fixtures/. Run: python scripts/build_fixtures.py")
if DEFAULT_SYMBOL not in FIXTURES:
    raise SystemExit(f"Missing the featured fixture {DEFAULT_SYMBOL}.json in fixtures/.")
TIERS = _load(WEB_DIR / "tiers.json")
CHECKS = _load(WEB_DIR / "checks.json")
COACH = _load(WEB_DIR / "coach.json")
SCENES = {p.stem: _load(p) for p in sorted((WEB_DIR / "scenes").glob("*.json")) if p.stem != "endings"}
ENDINGS = _load(WEB_DIR / "scenes" / "endings.json")
TIER_IDS = [t["id"] for t in TIERS]
# Every fixture shares one clock (see scripts/build_fixtures.py): reading the tick count
# off any one of them is reading it off all of them.
LAST_TICK = len(next(iter(FIXTURES.values()))["bars"]) - 1
SYMBOL_META = {f["symbol"]: {k: f[k] for k in
                              ("symbol", "name", "blurb", "sector", "kind", "volatility", "featured", "fund")}
               for f in FIXTURES.values()}
SYMBOLS = list(SYMBOL_META.values())            # static metadata only; snapshot() adds live prices


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
    """One shared floor: a single cash balance and tick cursor across all six symbols,
    so a position in more than one of them at once is normal, not a special case."""

    participant: int
    onboarded: bool = False
    symbol: Optional[str] = None           # the WATCHED symbol (the ticket/chart's focus) - never a trading lock
    cursor: int = 0                        # one clock for every symbol (see LAST_TICK)
    tier: str = "beginner"                 # highest unlocked tier
    cash: float = DEFAULT_START_CASH
    starting_cash: float = DEFAULT_START_CASH
    positions: dict = field(default_factory=dict)     # {symbol: {"qty", "avg_price"}} - may hold several at once
    orders: list = field(default_factory=list)        # every order ever placed; id == index + 1
    trades: list = field(default_factory=list)
    realized: float = 0.0
    dismissed: set = field(default_factory=set)       # symbols whose safety-net prompt was waved away
    kept_lots: list = field(default_factory=list)     # shares a safety net sold, for the shadow benchmark
    events: list = field(default_factory=list)
    checks_passed: set = field(default_factory=set)
    check_attempts: dict = field(default_factory=dict)
    first_buy_done: bool = False
    safety_net_used: bool = False
    replay_log: list = field(default_factory=list)    # accepted actions; replaying them rebuilds the session
    scene: Optional[str] = None                       # current story scene id, e.g. "act4.drop5"
    act: Optional[str] = None                         # which file `scene` lives in, e.g. "act4"
    flags: set = field(default_factory=set)           # narrative flags set by choices
    worst_equity: float = DEFAULT_START_CASH           # lowest equity ever seen, for panicked_at_trough


SESSIONS = {}        # one Session per browser, keyed by the rh_sid cookie
SID_COOKIE = "rh_sid"
MAX_SESSIONS = 200   # a hosted URL runs for weeks; without a cap the dict grows forever
QA_LOG = []          # survives /api/reset so V2 can total up stranger-QA across participants
BOOT_ID = uuid.uuid4().hex[:8]   # new on every server start: tells the browser "I restarted" from "I was reset"


def sid_of(request):
    return request.cookies.get(SID_COOKIE) or request.scope["rh_sid"]


def session_for(request):
    """This browser's own session. One global session was right for a laptop at a demo
    table; a hosted URL gets several visitors at once and they must never share a portfolio."""
    sid = sid_of(request)
    if sid not in SESSIONS:
        if len(SESSIONS) >= MAX_SESSIONS:
            SESSIONS.pop(next(iter(SESSIONS)))   # dicts keep insertion order, so this drops the oldest
        SESSIONS[sid] = Session(participant=len(SESSIONS) + 1)
    return SESSIONS[sid]


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
    day, time = tick_label(session.cursor)
    session.events.append({"seq": len(session.events) + 1, "bar": session.cursor, "day": day, "time": time,
                           "type": kind, "message": message, **data})


def require_onboarded(session):
    """Guard for every route that needs a running replay. Raises 409 if there isn't one."""
    if not session.onboarded:
        raise ApiError(409, "NOT_ONBOARDED", "Start a replay first: POST /api/onboarding.")


def current_bar(session, symbol):
    """`symbol`'s bar at this session's shared tick cursor: {i, day, time, o, h, l, c, n}.
    Every symbol is read from FIXTURES at the same cursor - there is one clock, not one
    per position - so this never needs the session to have "chosen" a symbol first."""
    return sim.price_at(FIXTURES[symbol]["bars"], session.cursor)


def tick_label(cursor):
    """The calendar day/time label for a tick, read off any fixture (they all share the
    same clock, so any one of them gives the same answer)."""
    bar = sim.price_at(FIXTURES[DEFAULT_SYMBOL]["bars"], cursor)
    return bar["day"], bar["time"]


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
    """Disabled for the trading floor: richher.html paces itself with six scripted coach
    halts at fixed ticks, not a reactive "you're down 8%" interruption, and has no UI for
    one. sim.check_safety_net_candidates still exists (and is still unit-tested) as a pure
    function - a future flow could call it - but nothing here does, so /api/advance can
    never surprise the floor with a stop it has no card for. `prompts` stays in the
    snapshot, always empty, so the response shape does not change underneath the browser.
    """
    return []


def describe(order):
    """Turn an order dict into a phrase for the activity feed, e.g. "market buy order for 10 HLX"."""
    o = order
    if o.get("safety_net"):
        return f"safety net on {o['qty']} {o['symbol']}"
    return f"{o['type'].lower()} {o['side'].lower()} order for {o['qty']} {o['symbol']}"


def cancel(session, order, code, why=None):
    """Mark a resting order cancelled and tell the user why, in plain English."""
    order.update(status="CANCELLED", reason=code)
    day, _ = tick_label(session.cursor)
    add_event(session, "CANCEL", f"Day {day}: cancelled your {describe(order)}" + (f": {why}" if why else "."))


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


def execute(session, order, price, bar_index, reason, quote=None, slip=None):
    """Fills an order: updates cash, position, trades and the shadow benchmark.

    `quote`/`slip` are only meaningful for a MARKET fill (see sim.slippage_fill_price):
    the trade record carries them so the ticket can show the gap between the quoted price
    and what actually filled, instead of recomputing it client-side."""
    sym = order["symbol"]
    cash, position, realized = sim.apply_fill(session.cash, session.positions.get(sym), order["side"], order["qty"], price)
    session.cash, session.realized = cash, round(session.realized + realized, 2)
    if position:
        session.positions[sym] = position
    else:
        session.positions.pop(sym, None)
        session.dismissed.discard(sym)
    order.update(status="FILLED", filled_bar=bar_index, fill_price=price, reason=reason)
    day, time = tick_label(bar_index)
    trade = {"order_id": order["id"], "bar": bar_index, "day": day, "time": time, "symbol": sym,
             "side": order["side"], "qty": order["qty"], "price": price, "reason": reason,
             "quote": quote, "slip": slip, "realized_pnl": realized}
    session.trades.append(trade)
    if order["side"] == "BUY":
        session.first_buy_done = True
        session.dismissed.discard(sym)
    if reason == "SAFETY_NET":
        session.kept_lots.append({"qty": order["qty"], "fill_price": price, "bar": bar_index})
    verb = "bought" if order["side"] == "BUY" else "sold"
    add_event(session, "FILL", f"Day {day}: {verb} {order['qty']} {sym} at {usd(price)}"
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

def watchlist_for(cursor):
    """Live price and change-since-the-tape-opened for every symbol, at one shared tick.
    Computed fresh every call (never stored) so it can never drift from the fixtures.
    Meaningful even before onboarding (cursor is 0), so the browser can paint the floor's
    watchlist before a replay has started."""
    out = []
    for sym, meta in SYMBOL_META.items():
        bars = FIXTURES[sym]["bars"]
        first, price = bars[0]["c"], sim.price_at(bars, cursor)["c"]
        out.append({"symbol": sym, "name": meta["name"],
                    "price": price, "change_pct": round((price - first) / first * 100, 4)})
    return out


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

    The "no look-ahead" rule lives here: every price comes from `session.cursor` alone,
    so the response physically cannot contain tomorrow's price for any of the six symbols.
    """
    out = {
        "boot_id": BOOT_ID, "onboarded": session.onboarded, "participant": session.participant,
        "action_seq": len(session.replay_log),
        "starting_cash": session.starting_cash, "symbols": SYMBOLS, "symbol": session.symbol,
        "watchlist": watchlist_for(session.cursor),
        "tier": session.tier, "tiers_unlocked": TIER_IDS[:TIER_IDS.index(session.tier) + 1],
        "cursor": session.cursor, "day": None, "time": None, "total_ticks": LAST_TICK + 1, "finished": False,
        "price": None, "bars": [],
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
    watched = current_bar(session, session.symbol)
    prices = {sym: current_bar(session, sym)["c"] for sym in session.positions}
    summ = sim.portfolio_summary(session.cash, session.positions, prices)
    stops = {o["symbol"]: o["stop_price"] for o in session.orders if o["status"] == "OPEN" and o.get("safety_net")}
    positions = [{
        "symbol": sym, "qty": p["qty"], "avg_price": p["avg_price"], "price": prices[sym],
        "market_value": round(p["qty"] * prices[sym], 2),
        "unrealized_pnl": round((prices[sym] - p["avg_price"]) * p["qty"], 2),
        "unrealized_pnl_pct": round((prices[sym] / p["avg_price"] - 1) * 100, 2),
        "protected": sim.protected_qty(session.orders, sym) >= p["qty"], "stop_price": stops.get(sym),
    } for sym, p in sorted(session.positions.items())]
    # The shadow benchmark only ever has something to say about the symbol a safety net
    # actually sold, which - now that positions can span several symbols - may not be the
    # one currently on screen. It stays scoped to `session.symbol` deliberately, same as before.
    delta = sim.shadow_delta(session.kept_lots, watched["c"])
    total = round(summ["equity"] - session.starting_cash, 2)
    finished = session.cursor >= LAST_TICK
    out.update(
        day=watched["day"], time=watched["time"], finished=finished, price=watched["c"],
        bars=FIXTURES[session.symbol]["bars"][:session.cursor + 1],
        positions=positions, equity=summ["equity"], market_value=summ["market_value"],
        unrealized_pnl=summ["unrealized_pnl"], unrealized_pnl_pct=summ["unrealized_pnl_pct"],
        total_pnl=total, total_pnl_pct=round(total / session.starting_cash * 100, 2),
        shadow={"active": bool(session.kept_lots), "kept_qty": sum(l["qty"] for l in session.kept_lots),
                "equity": round(summ["equity"] + delta, 2), "delta_vs_you": delta,
                "saved_by_safety_net": round(-delta, 2)},
        prompts=find_prompts(session), pending_check=pending_check(session),
        fixture_meta={"max_drawdown_pct": FIXTURES[session.symbol]["meta"]["max_drawdown_pct"], "synthetic": True}
        if finished else None,
    )
    return out


# --------------------------------------------------------------------------- request models

class OnboardingReq(BaseModel):
    tier: Literal["beginner", "intermediate", "advanced"] = "beginner"     # set directly by richher's quiz
    symbol: str = DEFAULT_SYMBOL       # which watchlist row the ticket/chart opens focused on


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


@app.middleware("http")
async def _session_cookie(request: Request, call_next):
    """Hand every new browser its own session id and remember it in a cookie."""
    sid = request.cookies.get(SID_COOKIE)
    request.scope["rh_sid"] = sid or uuid.uuid4().hex
    response = await call_next(request)
    if not sid:
        response.set_cookie(SID_COOKIE, request.scope["rh_sid"], max_age=86400, httponly=True,
                            samesite="lax", secure=request.url.scheme == "https")
    return response


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
async def get_state(request: Request):
    return snapshot(session_for(request))


@app.post("/api/onboarding")
async def post_onboarding(request: Request, req: OnboardingReq):
    session = session_for(request)
    if session.onboarded:
        raise ApiError(409, "ALREADY_ONBOARDED", "A replay is already running. Reset the demo to start over.")
    fx = FIXTURES.get(req.symbol.upper())
    if not fx:
        raise ApiError(404, "UNKNOWN_SYMBOL", f"Choose one of: {', '.join(FIXTURES)}.")
    # Every fixture starts the floor the same way (cursor 0, one shared cash balance) -
    # `req.symbol` only decides which watchlist row is focused when the floor opens.
    session.onboarded, session.symbol, session.cursor = True, fx["symbol"], fx["start_cursor"]
    session.cash = session.starting_cash = fx.get("start_cash", DEFAULT_START_CASH)
    session.worst_equity = session.starting_cash
    session.tier = req.tier
    day, _ = tick_label(session.cursor)
    add_event(session, "START", f"Day {day}: the floor opens with {usd(session.cash)} in cash. "
                       "The future is hidden.")
    record(session, "POST", "/api/onboarding", {"tier": req.tier, "symbol": session.symbol})
    return {"state": snapshot(session)}


@app.post("/api/advance")
async def post_advance(request: Request, req: AdvanceReq):
    session = session_for(request)
    require_onboarded(session)
    if session.cursor >= LAST_TICK:
        raise ApiError(409, "REPLAY_FINISHED", "You have reached the last tick of the replay.")
    # Step one tick at a time - never jump straight to cursor + n - so we can stop the
    # instant something happens. That is what makes fast-forward safe: a fill can never
    # be skipped over. Open orders can sit on more than one symbol at once, so every tick
    # checks each symbol that actually has one, not just the watched symbol.
    first_event, steps = len(session.events), 0
    while steps < req.n and session.cursor < LAST_TICK:
        session.cursor = sim.advance(session.cursor, 1, LAST_TICK)
        steps += 1
        stop_here = False
        pending_symbols = {o["symbol"] for o in session.orders if o["status"] == "OPEN"}
        for sym in sorted(pending_symbols):
            bar = current_bar(session, sym)
            same_symbol = [o for o in session.orders if o["symbol"] == sym]
            for hit in sim.check_open_orders_for_bar(same_symbol, session.cursor, bar):
                order = session.orders[hit["order_id"] - 1]
                try:
                    execute(session, order, hit["price"], session.cursor, hit["reason"])
                except sim.SimError as e:
                    cancel(session, order, e.code, e.message)
                stop_here = True
        if stop_here:
            break
    if session.cursor >= LAST_TICK:
        day, _ = tick_label(session.cursor)
        add_event(session, "END", f"Day {day}: the replay is over.")
    record(session, "POST", "/api/advance", {"n": req.n})
    return {"advanced": steps, "events": session.events[first_event:], "state": snapshot(session)}


@app.post("/api/reset")
async def post_reset(request: Request):
    fresh = Session(participant=session_for(request).participant + 1)
    SESSIONS[sid_of(request)] = fresh
    return {"state": snapshot(fresh)}


# ---- market data

@app.get("/api/quote")
async def get_quote(request: Request, symbol: Optional[str] = None, as_of: Optional[int] = Query(None, ge=0)):
    session = session_for(request)
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
async def post_order(request: Request, req: OrderReq):
    session = session_for(request)
    require_onboarded(session)
    sym = req.symbol.upper()
    if sym not in FIXTURES:
        raise ApiError(404, "UNKNOWN_SYMBOL", f"Choose one of: {', '.join(FIXTURES)}.")
    if req.as_of is not None and req.as_of != session.cursor:
        raise ApiError(409, "STALE_CURSOR", f"Your screen is on tick {req.as_of} but the floor is on tick {session.cursor}.",
                       cursor=session.cursor)
    if req.type not in caps(session.tier)["order_types"]:
        need = next(t for t in TIERS if req.type in t["unlocks"]["order_types"])
        raise ApiError(403, "TIER_LOCKED", f"{req.type.title()} orders unlock at {need['title']}. {need['how_to_unlock']}",
                       required_tier=need["id"], tier=session.tier)
    bar, pos = current_bar(session, sym), session.positions.get(sym)
    order = {"id": len(session.orders) + 1, "symbol": sym, "side": req.side, "type": req.type, "qty": req.qty,
             "limit_price": req.limit_price, "stop_price": req.stop_price, "status": "OPEN", "safety_net": False,
             "created_bar": session.cursor, "filled_bar": None, "fill_price": None, "reason": None}
    try:
        sim.validate_order(order, bar["c"], session.cash, pos["qty"] if pos else 0)
    except sim.SimError as e:
        raise sim_error(e)
    session.orders.append(order)
    fills = []
    if order["type"] == "MARKET":
        price, slip, quote = sim.slippage_fill_price(bar, order["side"])
        fills.append(execute(session, order, price, session.cursor, order["type"], quote=quote, slip=slip))
    else:
        price = sim.immediate_fill_price(order, bar)          # a marketable limit: no slippage, see sim_engine
        if price is not None:
            fills.append(execute(session, order, price, session.cursor, order["type"]))
        else:
            level = usd(order["limit_price"] if order["type"] == "LIMIT" else order["stop_price"])
            add_event(session, "ORDER", f"Day {bar['day']}: placed a {describe(order)} at {level}. It waits until the price reaches it.")
    session.symbol = sym                    # trading a symbol also focuses the ticket/chart on it
    record(session, "POST", "/api/orders", req.model_dump(exclude_none=True))
    return {"order": order, "fills": fills, "state": snapshot(session)}


@app.delete("/api/orders/{order_id}")
async def delete_order(request: Request, order_id: int):
    session = session_for(request)
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
async def get_portfolio(request: Request):
    session = session_for(request)
    require_onboarded(session)
    st = snapshot(session)
    return {"as_of": session.cursor, **{k: st[k] for k in (
        "cash", "positions", "equity", "market_value", "unrealized_pnl", "unrealized_pnl_pct",
        "realized_pnl", "open_orders")}}


@app.post("/api/safety-net")
async def post_safety_net(request: Request, req: SafetyNetReq):
    session = session_for(request)
    require_onboarded(session)
    sym = req.symbol.upper()
    pos = session.positions.get(sym)
    if not pos:
        raise ApiError(404, "NO_POSITION", f"You do not hold any {sym}.")
    if req.decision == "dismiss":
        session.dismissed.add(sym)
        day, _ = tick_label(session.cursor)
        add_event(session, "SAFETY_NET_DISMISSED", f"Day {day}: you chose to keep holding {sym} without a safety net.")
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
    bar = current_bar(session, sym)
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
async def get_tiers(request: Request):
    session = session_for(request)
    return {"tiers": TIERS, "active": session.tier, "unlocked": TIER_IDS[:TIER_IDS.index(session.tier) + 1]}


@app.post("/api/comprehension")
async def post_comprehension(request: Request, req: ComprehensionReq):
    session = session_for(request)
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
            day, _ = tick_label(session.cursor)
            add_event(session, "UNLOCK", f"Day {day}: unlocked {tier_title(target)}.")
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
        prices = {sym: current_bar(session, sym)["c"] for sym in session.positions}
        summary = sim.portfolio_summary(session.cash, session.positions, prices)
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
        day, _ = tick_label(session.cursor)
        add_event(session, "WITHDRAW", f"Day {day}: took {usd(amount)} out of the account.")

    amount = effect.get("deposit")
    if amount is not None:
        session.cash = round(session.cash + amount, 2)
        day, _ = tick_label(session.cursor)
        add_event(session, "DEPOSIT", f"Day {day}: put {usd(amount)} into the account.")


def _graph(act_id):
    graph = SCENES.get(act_id)
    if graph is None:
        raise ApiError(404, "UNKNOWN_ACT", f"No such act. Choose one of: {', '.join(SCENES)}.")
    return graph


@app.get("/api/story")
async def get_story(request: Request):
    """The current scene, the computed state and the narrative flags."""
    session = session_for(request)
    computed, flags = story_state(session)
    scene = None
    if session.scene and session.act:
        scene = story.visible(_graph(session.act)["nodes"][session.scene], computed, flags)
        scene["id"] = session.scene
    return {"act": session.act, "scene": scene, "computed": computed,
            "flags": sorted(flags),
            "acts": sorted(SCENES)}


@app.post("/api/story/start")
async def post_story_start(request: Request, act_id: str = Query("act4")):
    """Jump to the start of an act. The frontend calls this once per chapter."""
    session = session_for(request)
    graph = _graph(act_id)
    session.act, session.scene = act_id, graph["start"]
    record(session, "POST", f"/api/story/start?act_id={act_id}")
    return await get_story(request)


@app.post("/api/story/advance")
async def post_story_advance(request: Request, req: SceneReq):
    """Move to the next scene, applying whatever the chosen option sets."""
    session = session_for(request)
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
    return await get_story(request)


@app.get("/api/story/ending")
async def get_story_ending(request: Request):
    """Which ending she has earned, evaluated server-side. Never decided by the browser."""
    session = session_for(request)
    computed, flags = story_state(session)
    try:
        ending = story.choose_ending(ENDINGS["endings"], computed, flags)
    except story.StoryError as e:
        raise ApiError(500, e.code, e.message, **e.extra)
    return {"ending": ending, "computed": computed, "flags": sorted(flags)}


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
