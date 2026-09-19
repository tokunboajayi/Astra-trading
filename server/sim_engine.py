"""
server/sim_engine.py

Pure, deterministic simulation engine for Rich-HER / Astra Trading.
No FastAPI, no I/O, no clock, no randomness: every function maps inputs to outputs, so the
rules are unit-tested without a server and can be ported to another language unchanged.
Owned by B (Backend). Contract: SPEC.md section 5.

Prices are per-bar OHLC dicts {"o", "h", "l", "c"}. Orders and positions are plain dicts.
"""

STARTING_CASH = 10_000.00
PROMPT_PCT = -8.0        # unrealized loss that fires the safety-net prompt
STOP_PCT = -10.0         # loss at which the safety-net stop sells
MAX_QTY = 10_000
ORDER_TYPES = ("MARKET", "LIMIT", "STOP")
EPS = 1e-9


class SimError(Exception):
    """A rule violation. `code` is stable and machine-readable; `extra` rides along to the API."""

    def __init__(self, code, message, **extra):
        super().__init__(message)
        self.code, self.message, self.extra = code, message, extra


def _usd(x):
    return f"${x:,.2f}"


def price_at(bars, cursor):
    """The bar at `cursor`, clamped to the fixture. Returns o/h/l/c, its index `i`, its
    calendar `day`/`time` label, and `n` - the ambient volatility at this tick, which the
    slippage model reads (how fast the market is moving right now, independent of the
    scripted price path)."""
    if not bars:
        raise SimError("NO_DATA", "The fixture has no bars.")
    i = max(0, min(int(cursor), len(bars) - 1))
    b = bars[i]
    return {"i": i, "day": b["day"], "time": b.get("time"), "o": b["o"], "h": b["h"],
            "l": b["l"], "c": b["c"], "n": b.get("n", 0.0)}


def advance(cursor, n, last_bar):
    """Moves the cursor forward n bars, clamped to [0, last_bar]."""
    return max(0, min(cursor + n, last_bar))


def stop_price_for(avg_price, pct=STOP_PCT):
    """Price at which a safety net set `pct` percent below entry (pct is negative) would sell."""
    return round(avg_price * (1 + pct / 100), 2)


def validate_order(order, price, cash, position_qty):
    """Raises SimError if the order is malformed, unaffordable, or would sell shares you lack."""
    side, otype, qty = order["side"], order["type"], order["qty"]
    limit, stop = order.get("limit_price"), order.get("stop_price")
    if side not in ("BUY", "SELL"):
        raise SimError("INVALID_ORDER", "Side must be BUY or SELL.")
    if otype not in ORDER_TYPES:
        raise SimError("INVALID_ORDER", "Type must be MARKET, LIMIT or STOP.")
    if isinstance(qty, bool) or not isinstance(qty, int) or not 1 <= qty <= MAX_QTY:
        raise SimError("INVALID_ORDER", f"Quantity must be a whole number from 1 to {MAX_QTY:,}.")
    if otype == "MARKET" and (limit is not None or stop is not None):
        raise SimError("INVALID_ORDER", "Market orders take no price.")
    if otype == "LIMIT" and (limit is None or limit <= 0 or stop is not None):
        raise SimError("INVALID_ORDER", "Limit orders need a positive limit_price and no stop_price.")
    if otype == "STOP":
        if side != "SELL":
            raise SimError("UNSUPPORTED_ORDER", "Only sell-stops (stop-losses) are supported.")
        if stop is None or stop <= 0 or limit is not None:
            raise SimError("INVALID_ORDER", "Stop orders need a positive stop_price and no limit_price.")
        if stop >= price:
            raise SimError("STOP_NOT_BELOW_MARKET",
                           f"A stop-loss must sit below the current price ({_usd(price)}), "
                           "or it would sell immediately.", price=price)
    if side == "SELL" and qty > position_qty:
        raise SimError("INSUFFICIENT_SHARES", f"You hold {position_qty} shares, not {qty}.",
                       requested=qty, available=position_qty)
    if side == "BUY":
        need = round(qty * (limit if otype == "LIMIT" else price), 2)
        if need > cash + EPS:
            raise SimError("INSUFFICIENT_FUNDS",
                           f"This order needs {_usd(need)} but you have {_usd(cash)}.",
                           required=need, available=round(cash, 2))


MAX_SLIPPAGE = 0.012           # 1.2% cap, however fast the market is moving
SLIPPAGE_PER_VOL = 0.45        # slippage grows with the bar's ambient volatility (n)


def slippage_fill_price(bar, side):
    """A market order never fills at the quote: the price moves against the trader by an
    amount proportional to how fast the market is moving right now (`bar["n"]`), capped at
    MAX_SLIPPAGE. Calm markets cost pennies; a fast-moving one costs real money - which is
    exactly when a new investor is most likely to be pressing the button. Returns
    (fill_price, slip_fraction, quote) so the response can show the gap, not just the fill."""
    slip = min(MAX_SLIPPAGE, bar["n"] * SLIPPAGE_PER_VOL)
    signed = slip if side == "BUY" else -slip
    return round(bar["c"] * (1 + signed), 2), slip, bar["c"]


def immediate_fill_price(order, bar):
    """Market orders fill against the trader, nudged by slippage (see slippage_fill_price).
    A limit that is already marketable fills at the close (never worse than the limit, and
    never slipped - the limit is the guarantee). Everything else rests and returns None."""
    if order["type"] == "MARKET":
        return slippage_fill_price(bar, order["side"])[0]
    if order["type"] == "LIMIT":
        c, limit = bar["c"], order["limit_price"]
        if (order["side"] == "BUY" and c <= limit) or (order["side"] == "SELL" and c >= limit):
            return c
    return None


def apply_fill(cash, position, side, qty, price):
    """Applies one fill. position is {"qty", "avg_price"} or None.
    Returns (new_cash, new_position_or_None, realized_pnl). Raises SimError if it can't happen."""
    total = round(qty * price, 2)
    if side == "BUY":
        if total > cash + EPS:
            raise SimError("INSUFFICIENT_FUNDS", f"This fill needs {_usd(total)} but you have {_usd(cash)}.",
                           required=total, available=round(cash, 2))
        old_qty = position["qty"] if position else 0
        old_avg = position["avg_price"] if position else 0.0
        new_qty = old_qty + qty
        avg = round((old_qty * old_avg + qty * price) / new_qty, 4)
        return round(cash - total, 2), {"qty": new_qty, "avg_price": avg}, 0.0
    if not position or position["qty"] < qty:
        raise SimError("INSUFFICIENT_SHARES", "You do not hold enough shares to sell.",
                       requested=qty, available=position["qty"] if position else 0)
    realized = round((price - position["avg_price"]) * qty, 2)
    left = position["qty"] - qty
    new_position = {"qty": left, "avg_price": position["avg_price"]} if left else None
    return round(cash + total, 2), new_position, realized


def check_open_orders_for_bar(orders, bar_index, bar):
    """Which resting orders trigger on this bar? Returns [{"order_id", "price", "reason"}] in
    order-id order. Orders only trigger on bars after the one they were placed on.
    A limit fills at the limit or better; a stop that gaps through fills at the open (worse)."""
    hits = []
    for o in sorted(orders, key=lambda o: o["id"]):
        if o["status"] != "OPEN" or o["created_bar"] >= bar_index:
            continue
        price = None
        if o["type"] == "LIMIT":
            if o["side"] == "BUY" and bar["l"] <= o["limit_price"]:
                price = min(o["limit_price"], bar["o"])
            elif o["side"] == "SELL" and bar["h"] >= o["limit_price"]:
                price = max(o["limit_price"], bar["o"])
        elif o["type"] == "STOP" and bar["l"] <= o["stop_price"]:
            price = min(o["stop_price"], bar["o"])
        if price is not None:
            reason = "SAFETY_NET" if o.get("safety_net") else o["type"]
            hits.append({"order_id": o["id"], "price": price, "reason": reason})
    return hits


def protected_qty(open_orders, symbol):
    """Shares of `symbol` currently covered by an open safety-net stop."""
    return sum(o["qty"] for o in open_orders
               if o["status"] == "OPEN" and o.get("safety_net") and o["symbol"] == symbol)


def check_safety_net_candidates(positions, price, open_orders, dismissed):
    """Positions down 8% or more (at this bar's close) that have no safety net and were not
    waved away. Each candidate carries every number the prompt needs, so the copy is never
    hard-coded. `can_protect` is False when the price is already through the -10% stop."""
    out = []
    for symbol, pos in sorted(positions.items()):
        if symbol in dismissed or protected_qty(open_orders, symbol) >= pos["qty"]:
            continue
        loss_pct = (price - pos["avg_price"]) / pos["avg_price"] * 100
        if loss_pct > PROMPT_PCT + EPS:
            continue
        stop = stop_price_for(pos["avg_price"])
        out.append({
            "symbol": symbol, "qty": pos["qty"], "avg_price": pos["avg_price"], "price": price,
            "loss_pct": round(loss_pct, 2), "loss_dollars": round((price - pos["avg_price"]) * pos["qty"], 2),
            "stop_price": stop, "stop_pct": STOP_PCT,
            "stop_loss_dollars": round((stop - pos["avg_price"]) * pos["qty"], 2),
            "can_protect": stop < price,
        })
    return out


def shadow_delta(kept_lots, price):
    """Shadow benchmark: how much better (+) or worse (-) off you would be had you ignored your
    safety net and kept every share it sold. Each lot is {"qty", "fill_price"}."""
    return round(sum(lot["qty"] * (price - lot["fill_price"]) for lot in kept_lots), 2)


def portfolio_summary(cash, positions, prices):
    """Equity and unrealized P&L across positions that may span more than one symbol.

    `prices` is {symbol: current_price} - a session can hold several symbols at once from
    one shared cash balance (the trading floor lets you buy anything on the watchlist), so
    each position must be marked at its OWN price, never a single shared one."""
    value = sum(p["qty"] * prices[sym] for sym, p in positions.items())
    cost = sum(p["qty"] * p["avg_price"] for p in positions.values())
    pnl = value - cost
    return {"market_value": round(value, 2), "equity": round(cash + value, 2),
            "unrealized_pnl": round(pnl, 2),
            "unrealized_pnl_pct": round(pnl / cost * 100, 2) if cost else 0.0}
