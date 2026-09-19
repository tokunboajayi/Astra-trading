"""API contract and flow tests (SPEC.md section 8). Run against the in-process app."""

import json
from pathlib import Path

from server import main
from server.tests.conftest import onboard, order

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_ROUTES = {
    ("GET", "/api/state"), ("POST", "/api/onboarding"), ("POST", "/api/advance"), ("POST", "/api/reset"),
    ("GET", "/api/quote"), ("POST", "/api/orders"), ("DELETE", "/api/orders/{order_id}"),
    ("GET", "/api/portfolio"), ("POST", "/api/safety-net"), ("GET", "/api/tiers"),
    ("POST", "/api/comprehension"), ("GET", "/api/qa-log"),
    ("GET", "/api/story"), ("POST", "/api/story/start"), ("POST", "/api/story/advance"),
    ("GET", "/api/story/ending"), ("GET", "/api/coach"),          # the story layer (STORY.md)
    ("GET", "/api/news"), ("GET", "/api/fundamentals"),          # the two mock-only stubs
}


def test_route_table_is_frozen_at_17_live_plus_2_stubs():
    """The API surface is frozen. Adding a route means updating this set on purpose."""
    actual = {(m, r.path) for r in main.app.routes if getattr(r, "path", "").startswith("/api")
              for m in r.methods if m not in ("HEAD", "OPTIONS")}
    assert actual == EXPECTED_ROUTES and len(actual) == 19


def test_fresh_state_has_no_bars_and_lists_every_symbol(client):
    st = client.get("/api/state").json()
    assert st["onboarded"] is False and st["bars"] == [] and st["cash"] == 100.0
    assert [s["symbol"] for s in st["symbols"]] == ["VOLT", "CASA", "HLX", "KIN", "MERI", "ORB"]


def test_everything_that_needs_a_replay_says_not_onboarded(client):
    calls = [client.get("/api/quote"), client.get("/api/portfolio"), client.post("/api/advance", json={"n": 1}),
             client.post("/api/orders", json={"symbol": "HLX", "side": "BUY", "qty": 1}),
             client.delete("/api/orders/1"), client.post("/api/safety-net", json={"symbol": "HLX"}),
             client.post("/api/comprehension", json={"check_id": "downside", "choice": 0})]
    assert all(r.status_code == 409 and r.json()["error"] == "NOT_ONBOARDED" for r in calls)


def test_onboarding_branches_and_errors(client):
    st = onboard(client, "beginner")
    assert (st["tier"], st["tiers_unlocked"], st["cursor"]) == ("beginner", ["beginner"], 0)
    assert st["price"] == 88.0 and st["day"] == 1
    assert client.post("/api/onboarding", json={"tier": "beginner"}).json()["error"] == "ALREADY_ONBOARDED"
    client.post("/api/reset")
    st = onboard(client, "intermediate", "VOLT")
    assert (st["tier"], st["tiers_unlocked"], st["symbol"], st["cursor"]) == ("intermediate", ["beginner", "intermediate"], "VOLT", 0)
    client.post("/api/reset")
    assert client.post("/api/onboarding", json={"tier": "beginner", "symbol": "ZZZ"}).status_code == 404
    bad = client.post("/api/onboarding", json={"tier": "wizard"})
    assert bad.status_code == 422 and bad.json()["error"] == "VALIDATION" and bad.json()["details"][0]["field"] == "tier"


def test_the_future_is_never_exposed(client):
    st = onboard(client)
    assert len(st["bars"]) == st["cursor"] + 1 and st["bars"][-1]["c"] == st["price"]
    assert client.get("/api/quote", params={"as_of": 1}).json()["error"] == "FUTURE_BAR"
    assert client.get("/api/quote", params={"as_of": 0}).json()["as_of"] == 0
    assert client.get("/api/quote").json()["price"] == 88.0
    assert client.get("/api/quote", params={"symbol": "NOPE"}).status_code == 404
    assert client.get("/api/state").json()["fixture_meta"] is None          # the dip size stays hidden until the end


def test_market_buy_fills_with_slippage_and_updates_the_portfolio(client):
    onboard(client)
    r = order(client, "BUY", 1).json()
    assert r["fills"][0]["price"] == 88.24 and r["state"]["cash"] == 11.76
    pos = r["state"]["positions"][0]
    assert (pos["qty"], pos["avg_price"], pos["protected"]) == (1, 88.24, False)
    pf = client.get("/api/portfolio").json()
    assert pf["as_of"] == 0 and pf["cash"] == 11.76


def test_order_validation_errors(client):
    onboard(client)
    body = {"symbol": "HLX", "side": "buy", "qty": 1}
    assert client.post("/api/orders", json=body).status_code == 200                       # lowercase is fine
    assert client.post("/api/orders", json={**body, "as_of": 3}).json() == {
        "error": "STALE_CURSOR", "cursor": 0, "message": "Your screen is on tick 3 but the floor is on tick 0."}
    assert client.post("/api/orders", json={**body, "symbol": "NOPE"}).json()["error"] == "UNKNOWN_SYMBOL"
    assert client.post("/api/orders", json={**body, "qty": 100}).json()["error"] == "INSUFFICIENT_FUNDS"
    assert client.post("/api/orders", json={**body, "side": "SELL", "qty": 5}).json()["error"] == "INSUFFICIENT_SHARES"
    assert client.post("/api/orders", json={**body, "qty": 0}).status_code == 422


def test_tier_gating_is_enforced_by_the_server(client):
    onboard(client, "beginner")
    r = order(client, "BUY", 1, type="LIMIT", limit_price=80.0)
    assert r.status_code == 403 and r.json()["error"] == "TIER_LOCKED" and r.json()["required_tier"] == "intermediate"
    r = order(client, "SELL", 1, type="STOP", stop_price=80.0)
    assert r.status_code == 403 and r.json()["required_tier"] == "advanced"
    custom = client.post("/api/safety-net", json={"symbol": "HLX", "percent": 5})
    assert custom.status_code == 404                                            # no position yet: checked first
    order(client, "BUY", 1)
    custom = client.post("/api/safety-net", json={"symbol": "HLX", "percent": 5})
    assert custom.status_code == 403 and custom.json()["required_tier"] == "intermediate"


def test_limit_orders_rest_fill_later_and_can_be_cancelled(client):
    onboard(client, "intermediate")
    r = order(client, "BUY", 1, type="LIMIT", limit_price=85.0).json()          # below the 88 close: rests
    assert r["fills"] == [] and r["order"]["status"] == "OPEN" and len(r["state"]["open_orders"]) == 1
    assert client.delete("/api/orders/1").json()["order"]["status"] == "CANCELLED"
    assert client.delete("/api/orders/1").json()["error"] == "ORDER_NOT_OPEN"
    assert client.delete("/api/orders/9").json()["error"] == "ORDER_NOT_FOUND"
    order(client, "BUY", 1, type="LIMIT", limit_price=85.0)
    st = client.post("/api/advance", json={"n": 30}).json()["state"]             # stops when the limit fills
    fill = st["trades"][0]
    assert fill["reason"] == "LIMIT" and fill["price"] <= 85.0 and st["positions"][0]["qty"] == 1


def test_safety_net_flow_end_to_end(client):
    """Buy, set a safety net manually, advance until the stop fills, check shadow benchmark."""
    onboard(client, "intermediate")
    order(client, "BUY", 1)

    # Manually set a safety net (prompts are disabled for the trading floor)
    net = client.post("/api/safety-net", json={"symbol": "HLX", "decision": "accept"}).json()
    assert net["order"]["stop_price"] == 79.42 and net["state"]["positions"][0]["protected"] is True

    # Advance until the stop fills
    r = client.post("/api/advance", json={"n": 30}).json()
    st = r["state"]
    assert st["positions"] == []     # the stop sold everything
    assert st["trades"][-1]["reason"] == "SAFETY_NET" and st["trades"][-1]["price"] == 79.42
    assert st["shadow"]["kept_qty"] == 1


def test_dismissing_the_safety_net_lets_the_position_ride(client):
    onboard(client, "intermediate")
    order(client, "BUY", 1)
    st = client.post("/api/safety-net", json={"symbol": "HLX", "decision": "dismiss"}).json()["state"]
    assert st["positions"][0]["protected"] is False
    st = client.post("/api/advance", json={"n": 30}).json()["state"]
    assert st["positions"][0]["qty"] == 1                                          # no stop, no fill


def test_intermediate_can_choose_a_wider_safety_net_and_cannot_double_up(client):
    onboard(client, "intermediate")
    order(client, "BUY", 1)
    net = client.post("/api/safety-net", json={"symbol": "HLX", "percent": 15})
    sp = net.json()["order"]["stop_price"]
    assert sp == round(88.24 * (1 + (-15.0) / 100), 2)
    assert client.post("/api/safety-net", json={"symbol": "HLX"}).json()["error"] == "ALREADY_PROTECTED"


def test_a_stop_above_the_market_is_refused(client):
    onboard(client, "intermediate")
    order(client, "BUY", 1)
    # Advance to get the price closer to entry so a 3% stop would be above current market
    client.post("/api/advance", json={"n": 20})
    r = client.post("/api/safety-net", json={"symbol": "HLX", "percent": 3})
    assert r.status_code == 400 and r.json()["error"] == "STOP_NOT_BELOW_MARKET"


def test_comprehension_checks_unlock_tiers_and_feed_the_qa_log(client):
    onboard(client)
    assert client.get("/api/state").json()["pending_check"] is None
    assert client.post("/api/comprehension", json={"check_id": "downside", "choice": 2}).json()["error"] == "CHECK_NOT_AVAILABLE"
    order(client, "BUY", 1)
    assert client.get("/api/state").json()["pending_check"] == "downside"

    wrong = client.post("/api/comprehension", json={"check_id": "downside", "choice": 0}).json()
    assert (wrong["correct"], wrong["attempt"], wrong["unlocked_tier"], wrong["state"]["tier"]) == (False, 1, None, "beginner")
    right = client.post("/api/comprehension", json={"check_id": "downside", "choice": 2}).json()
    assert (right["correct"], right["attempt"], right["unlocked_tier"]) == (True, 2, "intermediate")
    assert right["state"]["tiers_unlocked"] == ["beginner", "intermediate"] and right["state"]["pending_check"] is None
    assert client.post("/api/comprehension", json={"check_id": "nope", "choice": 0}).status_code == 404
    assert client.post("/api/comprehension", json={"check_id": "downside", "choice": 9}).status_code == 409   # already passed

    # Trigger safety_net check: set up a safety net manually
    net = client.post("/api/safety-net", json={"symbol": "HLX", "decision": "accept"})
    assert client.get("/api/state").json()["pending_check"] == "safety_net"
    res = client.post("/api/comprehension", json={"check_id": "safety_net", "choice": 1}).json()
    assert res["unlocked_tier"] == "advanced" and res["state"]["tiers_unlocked"] == ["beginner", "intermediate", "advanced"]

    log = client.get("/api/qa-log").json()
    assert [(e["check_id"], e["correct"], e["attempt"]) for e in log["entries"]] == [
        ("downside", False, 1), ("downside", True, 2), ("safety_net", True, 1)]
    assert log["per_check"]["downside"] == {"participants": 1, "first_try_correct": 0}   # first try was wrong
    assert log["pitch_line"] == "1 of 1 first-time users explained how a stop-loss works."


def test_qa_log_survives_reset_and_counts_participants(client):
    onboard(client)
    order(client, "BUY", 1)
    client.post("/api/comprehension", json={"check_id": "downside", "choice": 2})
    client.post("/api/reset")
    onboard(client)
    order(client, "BUY", 1)
    client.post("/api/comprehension", json={"check_id": "downside", "choice": 0})
    log = client.get("/api/qa-log").json()
    assert log["participants"] == 2 and log["per_check"]["downside"] == {"participants": 2, "first_try_correct": 1}
    assert log["pitch_line"] == "1 of 2 first-time users worked out their downside after one simulated trade."


def test_reset_starts_over_but_moves_to_the_next_participant(client):
    onboard(client)
    order(client, "BUY", 1)
    st = client.post("/api/reset").json()["state"]
    assert (st["onboarded"], st["cash"], st["positions"], st["participant"], st["action_seq"]) == (False, 100.0, [], 2, 0)


def test_replaying_the_action_log_rebuilds_the_exact_session(client):
    """This is how the browser recovers after a server restart (SPEC.md section 6)."""
    onboard(client)
    order(client, "BUY", 1)
    client.post("/api/comprehension", json={"check_id": "downside", "choice": 2})
    client.post("/api/advance", json={"n": 10})
    client.post("/api/safety-net", json={"symbol": "HLX", "decision": "accept"})
    client.post("/api/advance", json={"n": 30})          # AdvanceReq caps n at 30
    before = client.get("/api/state").json()
    assert before["action_seq"] == 6

    main.SESSIONS.clear()                                                         # "the server restarted"
    assert client.get("/api/state").json()["onboarded"] is False
    for step in before["replay_log"]:
        r = client.request(step["method"], step["path"], json=step["body"])
        assert r.status_code == 200, (step, r.text)
    after = client.get("/api/state").json()
    assert after == before


def test_running_to_the_end_reveals_the_fixture_facts_and_stops(client):
    onboard(client)
    st = {}
    while not st.get("finished"):
        st = client.post("/api/advance", json={"n": 30}).json()["state"]
    assert st["cursor"] == 389 and st["fixture_meta"] == {"max_drawdown_pct": -17.9, "synthetic": True}
    assert client.post("/api/advance", json={"n": 1}).json()["error"] == "REPLAY_FINISHED"


def test_tiers_and_stubs(client):
    t = client.get("/api/tiers").json()
    assert [x["id"] for x in t["tiers"]] == ["beginner", "intermediate", "advanced"] and t["active"] == "beginner"
    assert client.get("/api/news", params={"symbol": "HLX"}).json()["stub"] is True
    assert client.get("/api/fundamentals").json()["fundamentals"] is None


def test_cors_is_open_for_local_dev(client):
    r = client.get("/api/state", headers={"Origin": "http://127.0.0.1:5500"})
    assert r.headers["access-control-allow-origin"] == "*"


def test_one_process_also_serves_the_web_app(client):
    page = client.get("/")
    assert page.status_code == 200 and "text/html" in page.headers["content-type"]


def test_a_story_choice_actually_moves_the_money(client, monkeypatch):
    """A pressure event's {"withdraw": N} must reduce real cash, not just set a flag."""
    onboard(client, symbol="VOLT")
    before = client.get("/api/state").json()["cash"]

    graph = {"start": "p1", "nodes": {
        "p1": {"speaker": "narrator", "lines": ["Someone you love needs $40."],
               "respond": {"type": "choice", "options": [
                   {"id": "send", "label": "Send the $40", "goto": "p2",
                    "sets": ["took_money_out"], "effect": {"withdraw": 40}},
                   {"id": "keep", "label": "Say you can't right now", "goto": "p2",
                    "sets": ["held_the_line"]}]}},
        "p2": {"speaker": "narrator", "lines": ["Okay."],
               "respond": {"type": "continue", "goto": "act5.open"}}}}
    monkeypatch.setitem(main.SCENES, "pressure", graph)

    client.post("/api/story/start", params={"act_id": "pressure"})
    r = client.post("/api/story/advance", json={"scene_id": "p1", "option_id": "send"})
    assert r.status_code == 200, r.text

    after = client.get("/api/state").json()["cash"]
    assert after == round(before - 40, 2), "the withdraw effect did not move the money"
    assert "took_money_out" in r.json()["flags"]
    assert any(e["type"] == "WITHDRAW" for e in client.get("/api/state").json()["events"])


def test_withdrawing_more_than_the_cash_is_refused_kindly(client, monkeypatch):
    onboard(client, symbol="VOLT")
    graph = {"start": "p1", "nodes": {
        "p1": {"speaker": "narrator", "lines": ["A very large bill."],
               "respond": {"type": "choice", "options": [
                   {"id": "pay", "label": "Pay it", "goto": "p2", "effect": {"withdraw": 9999}}]}},
        "p2": {"speaker": "narrator", "lines": ["."], "respond": {"type": "continue", "goto": "act5.open"}}}}
    monkeypatch.setitem(main.SCENES, "pressure", graph)

    client.post("/api/story/start", params={"act_id": "pressure"})
    r = client.post("/api/story/advance", json={"scene_id": "p1", "option_id": "pay"})
    assert r.status_code == 409
    body = r.json()
    assert body["error"] == "CANNOT_WITHDRAW"
    assert "$100.00" in body["message"]        # tells her what she actually has


def test_two_browsers_do_not_share_a_portfolio(client):
    """The hosted URL gets more than one visitor at a time (README, "Known open items")."""
    from fastapi.testclient import TestClient

    onboard(client)                      # first visitor buys
    order(client, "BUY", 1)
    mine = client.get("/api/state").json()

    other = TestClient(main.app)         # second visitor: no cookie, so a session of her own
    hers = other.get("/api/state").json()
    assert hers["onboarded"] is False, "a new visitor must not inherit someone else's replay"
    assert hers["participant"] != mine["participant"]

    onboard(other, symbol="VOLT")        # and her replay must not disturb the first
    assert client.get("/api/state").json()["symbol"] == mine["symbol"] == "HLX"
