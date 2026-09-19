"""Unit tests for the pure simulation engine (no server involved)."""

import pytest

from server import sim_engine as sim

BARS = [{"day": i + 1, "o": 100 + i, "h": 102 + i, "l": 98 + i, "c": 101 + i} for i in range(5)]


def limit(side, price, created_bar=0, oid=1):
    return {"id": oid, "type": "LIMIT", "side": side, "limit_price": price, "status": "OPEN", "created_bar": created_bar}


def stop(price, created_bar=0, oid=1, safety_net=False):
    return {"id": oid, "type": "STOP", "side": "SELL", "stop_price": price, "status": "OPEN",
            "created_bar": created_bar, "safety_net": safety_net}


def test_price_at_clamps_and_reports_the_day():
    assert sim.price_at(BARS, 2)["c"] == 103
    assert sim.price_at(BARS, -5)["i"] == 0
    assert sim.price_at(BARS, 99)["i"] == 4 and sim.price_at(BARS, 99)["day"] == 5


def test_advance_clamps():
    assert sim.advance(3, 1, 89) == 4
    assert sim.advance(85, 30, 89) == 89
    assert sim.advance(1, -5, 89) == 0


def test_buy_updates_cash_and_weighted_average():
    cash, pos, realized = sim.apply_fill(10_000, None, "BUY", 10, 150.0)
    assert (cash, pos, realized) == (8_500.0, {"qty": 10, "avg_price": 150.0}, 0.0)
    cash, pos, _ = sim.apply_fill(cash, pos, "BUY", 10, 130.0)
    assert cash == 7_200.0 and pos == {"qty": 20, "avg_price": 140.0}


def test_sell_realizes_pnl_and_closes_the_position():
    cash, pos, realized = sim.apply_fill(8_500, {"qty": 10, "avg_price": 150.0}, "SELL", 4, 135.0)
    assert (cash, realized, pos["qty"]) == (9_040.0, -60.0, 6)
    cash, pos, realized = sim.apply_fill(cash, pos, "SELL", 6, 135.0)
    assert pos is None and realized == -90.0 and cash == 9_850.0


def test_fills_refuse_impossible_trades():
    with pytest.raises(sim.SimError) as e:
        sim.apply_fill(100, None, "BUY", 10, 150.0)
    assert e.value.code == "INSUFFICIENT_FUNDS"
    with pytest.raises(sim.SimError) as e:
        sim.apply_fill(100, {"qty": 2, "avg_price": 10.0}, "SELL", 3, 10.0)
    assert e.value.code == "INSUFFICIENT_SHARES"


@pytest.mark.parametrize("order, code", [
    ({"side": "BUY", "type": "MARKET", "qty": 1, "limit_price": 5.0}, "INVALID_ORDER"),
    ({"side": "BUY", "type": "LIMIT", "qty": 1}, "INVALID_ORDER"),
    ({"side": "BUY", "type": "STOP", "qty": 1, "stop_price": 90.0}, "UNSUPPORTED_ORDER"),
    ({"side": "SELL", "type": "STOP", "qty": 1, "stop_price": 120.0}, "STOP_NOT_BELOW_MARKET"),
    ({"side": "SELL", "type": "MARKET", "qty": 5}, "INSUFFICIENT_SHARES"),
    ({"side": "BUY", "type": "MARKET", "qty": 100}, "INSUFFICIENT_FUNDS"),
    ({"side": "BUY", "type": "MARKET", "qty": True}, "INVALID_ORDER"),
    ({"side": "BUY", "type": "MARKET", "qty": 0}, "INVALID_ORDER"),
])
def test_validate_order_rejections(order, code):
    with pytest.raises(sim.SimError) as e:
        sim.validate_order(order, price=100.0, cash=1_000.0, position_qty=2)
    assert e.value.code == code


def test_validate_order_accepts_a_good_stop():
    sim.validate_order({"side": "SELL", "type": "STOP", "qty": 2, "stop_price": 90.0}, 100.0, 0, 2)


def test_market_and_marketable_limit_fill_at_the_close():
    bar = {"o": 99.0, "h": 103.0, "l": 98.0, "c": 101.0}
    assert sim.immediate_fill_price({"type": "MARKET", "side": "BUY"}, bar) == 101.0
    assert sim.immediate_fill_price(limit("BUY", 105.0), bar) == 101.0     # never worse than the limit
    assert sim.immediate_fill_price(limit("BUY", 100.0), bar) is None      # rests
    assert sim.immediate_fill_price(limit("SELL", 100.0), bar) == 101.0
    assert sim.immediate_fill_price(stop(90.0), bar) is None


def test_limit_orders_fill_at_the_limit_or_better():
    hit = sim.check_open_orders_for_bar([limit("BUY", 95.0)], 1, {"o": 99.0, "h": 100.0, "l": 94.0, "c": 96.0})
    assert hit == [{"order_id": 1, "price": 95.0, "reason": "LIMIT"}]
    better = sim.check_open_orders_for_bar([limit("BUY", 95.0)], 1, {"o": 93.0, "h": 96.0, "l": 92.0, "c": 95.5})
    assert better[0]["price"] == 93.0                                      # opened below the limit
    sell = sim.check_open_orders_for_bar([limit("SELL", 105.0)], 1, {"o": 104.0, "h": 106.0, "l": 103.0, "c": 105.5})
    assert sell[0]["price"] == 105.0
    miss = sim.check_open_orders_for_bar([limit("BUY", 95.0)], 1, {"o": 99.0, "h": 100.0, "l": 96.0, "c": 98.0})
    assert miss == []


def test_stop_fills_at_the_stop_but_at_the_open_when_the_price_gaps_through():
    normal = sim.check_open_orders_for_bar([stop(90.0)], 1, {"o": 92.0, "h": 93.0, "l": 89.0, "c": 90.5})
    assert normal[0]["price"] == 90.0
    gap = sim.check_open_orders_for_bar([stop(90.0)], 1, {"o": 85.0, "h": 86.0, "l": 83.0, "c": 84.0})
    assert gap[0]["price"] == 85.0                                         # the honest downside of a stop


def test_orders_wait_a_bar_and_report_safety_net_fills():
    bar = {"o": 80.0, "h": 81.0, "l": 79.0, "c": 80.0}
    assert sim.check_open_orders_for_bar([stop(90.0, created_bar=3)], 3, bar) == []
    hit = sim.check_open_orders_for_bar([stop(90.0, created_bar=3, safety_net=True)], 4, bar)
    assert hit[0]["reason"] == "SAFETY_NET"


def test_open_orders_trigger_in_id_order_and_skip_finished_ones():
    done = {**stop(90.0, oid=1), "status": "FILLED"}
    a, b = stop(90.0, oid=3), stop(91.0, oid=2)
    hits = sim.check_open_orders_for_bar([a, done, b], 1, {"o": 89.0, "h": 90.0, "l": 88.0, "c": 89.0})
    assert [h["order_id"] for h in hits] == [2, 3]


POS = {"HLX": {"qty": 10, "avg_price": 150.0}}


def test_safety_net_prompt_fires_at_exactly_minus_8_percent():
    assert sim.check_safety_net_candidates(POS, 145.0, [], set()) == []           # -3.33%
    [c] = sim.check_safety_net_candidates(POS, 138.0, [], set())                  # -8.00%
    assert (c["loss_pct"], c["loss_dollars"], c["stop_price"], c["stop_loss_dollars"], c["can_protect"]) == (
        -8.0, -120.0, 135.0, -150.0, True)


def test_safety_net_prompt_respects_dismissal_and_existing_protection():
    assert sim.check_safety_net_candidates(POS, 138.0, [], {"HLX"}) == []
    net = {**stop(135.0, safety_net=True), "symbol": "HLX", "qty": 10}
    assert sim.check_safety_net_candidates(POS, 138.0, [net], set()) == []
    half = {**net, "qty": 4}                                                       # covers only part
    assert len(sim.check_safety_net_candidates(POS, 138.0, [half], set())) == 1


def test_prompt_admits_when_the_stop_can_no_longer_protect():
    [c] = sim.check_safety_net_candidates(POS, 133.0, [], set())                  # already through -10%
    assert c["can_protect"] is False


def test_shadow_benchmark_measures_what_ignoring_the_safety_net_would_have_done():
    lots = [{"qty": 10, "fill_price": 151.20}]
    assert sim.shadow_delta(lots, 132.96) == -182.40      # the net saved you $182.40
    assert sim.shadow_delta(lots, 158.00) == 68.00        # ...and cost you $68 in hindsight
    assert sim.shadow_delta([], 158.00) == 0.0


def test_portfolio_summary():
    s = sim.portfolio_summary(8_500.0, POS, 138.0)
    assert s == {"market_value": 1_380.0, "equity": 9_880.0, "unrealized_pnl": -120.0, "unrealized_pnl_pct": -8.0}
    assert sim.portfolio_summary(10_000.0, {}, 100.0)["unrealized_pnl_pct"] == 0.0


def test_stop_price_for():
    assert sim.stop_price_for(168.0) == 151.2
    assert sim.stop_price_for(150.0, -5) == 142.5
