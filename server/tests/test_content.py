"""Lint for the V1/V2 content files: the downside-first rule is enforced, not just hoped for."""

import json
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[2] / "web"
TIERS = ["beginner", "intermediate", "advanced"]
LOSS_WORDS = re.compile(r"\b(lose|loss|losses|lost|fall|falls|drop|dip|down|miss|never|shrink|shrinks|worse|risk|cost|fail|wrong|negative|sold out)\b", re.I)

REQUIRED_HINTS = {
    "order.buy": TIERS, "order.sell": TIERS, "order.limit": TIERS[1:], "order.stop": TIERS[2:],
    "safety_net.prompt": TIERS, "safety_net.stop_loss": TIERS,
    "chart.line": TIERS[:1], "chart.levels": TIERS[1:2], "chart.candlestick": TIERS[2:], "chart.strategy": TIERS[2:],
    "portfolio.cash": TIERS[:1], "portfolio.position": TIERS[:1], "portfolio.pnl": TIERS[:1], "portfolio.shadow": TIERS[:1],
}


def load(name):
    return json.loads((WEB / name).read_text(encoding="utf-8"))


def test_every_action_has_a_hint_for_every_tier_it_exists_in():
    hints = load("hints.json")
    missing = [f"{a}.{t}" for a, tiers in REQUIRED_HINTS.items() for t in tiers if f"{a}.{t}" not in hints]
    assert missing == []


def test_every_hint_leads_with_the_downside_and_names_a_loss():
    entries = {k: v for k, v in load("hints.json").items() if not k.startswith("_")}
    for key, hint in entries.items():
        assert list(hint)[0] == "downside", f"{key}: downside must be the first field"
        assert set(hint) <= {"downside", "text", "more"} and hint["text"], f"{key}: needs downside + text"
        assert LOSS_WORDS.search(hint["downside"]), f"{key}: the downside line never names a loss"


def test_tiers_only_ever_add_capabilities():
    tiers = load("tiers.json")
    assert [t["id"] for t in tiers] == TIERS
    orders = [t["unlocks"]["order_types"] for t in tiers]
    assert orders[0] == ["MARKET"] and all(set(a) < set(b) for a, b in zip(orders, orders[1:]))
    assert [t["unlocks"]["chart"] for t in tiers] == ["line", "line_levels", "candles"]
    assert all(t["how_to_unlock"] and t["features"] and t["badge"] for t in tiers)
    assert tiers[2]["unlocks"]["strategy_overlay"] and not tiers[0]["unlocks"]["custom_safety_net"]


def test_checks_are_answerable_and_unlock_real_tiers():
    checks = load("checks.json")
    assert set(checks) == {"downside", "safety_net"}
    for cid, c in checks.items():
        assert 0 <= c["answer"] < len(c["options"]) >= 3, cid
        assert c["unlocks"] in TIERS and c["trigger"] in {"first_buy", "safety_net_active"}, cid
        assert all(c[k] for k in ("prompt", "explain_correct", "explain_wrong", "pitch_label", "title")), cid
    assert checks["downside"]["answer"] != checks["safety_net"]["answer"]      # the right answer is not always the same slot
