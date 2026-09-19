"""The fixtures are generated, reproducible, synthetic intraday tapes, and VOLT's arc
(peak, a -50%-ish trough, a finish above the start) is guaranteed, with the fund (ORB)
falling less than the single company over the same window."""

import json
from pathlib import Path

import pytest

from scripts import build_fixtures

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures"
SYMBOLS = ["VOLT", "ORB", "KIN", "HLX", "MERI", "CASA"]


def load(symbol):
    return json.loads((FIXTURE_DIR / f"{symbol}.json").read_text(encoding="utf-8"))


def test_the_six_curated_symbols_exist():
    assert sorted(p.stem for p in FIXTURE_DIR.glob("*.json")) == sorted(SYMBOLS)


def test_files_match_a_fresh_build_so_nobody_hand_edited_them():
    for name, text in build_fixtures.build_all().items():
        assert (FIXTURE_DIR / name).read_text(encoding="utf-8") == text, f"{name} is stale: rerun scripts/build_fixtures.py"


@pytest.mark.parametrize("symbol", SYMBOLS)
def test_each_fixture_is_390_valid_synthetic_ticks(symbol):
    fx = load(symbol)
    assert fx["synthetic"] is True and len(fx["bars"]) == build_fixtures.TAPE_LEN
    assert [b["i"] for b in fx["bars"]] == list(range(build_fixtures.TAPE_LEN))
    for b in fx["bars"]:
        assert b["h"] >= max(b["o"], b["c"]) and b["l"] <= min(b["o"], b["c"]) and b["l"] > 0
        assert 1 <= b["day"] <= 5 and len(b["time"]) == 5 and b["time"][2] == ":"


@pytest.mark.parametrize("symbol", SYMBOLS)
def test_every_symbol_starts_the_same_way(symbol):
    """One shared account across all six: nothing may need more than the others to start."""
    fx = load(symbol)
    assert fx["start_cursor"] == 0
    assert fx["start_cash"] == 100.00


def worst_drawdown(closes):
    peak_i, worst = 0, (0.0, 0, 0)
    for i, c in enumerate(closes):
        peak_i = i if c > closes[peak_i] else peak_i
        dd = (c - closes[peak_i]) / closes[peak_i] * 100
        worst = (dd, peak_i, i) if dd < worst[0] else worst
    return worst


def test_volt_is_the_featured_stock_and_halves_off_its_peak_then_finishes_above_start():
    fx = load("VOLT")
    assert fx["featured"] is True
    closes = [b["c"] for b in fx["bars"]]
    dd, peak_i, trough_i = worst_drawdown(closes)
    assert -51.0 < dd < -49.0                     # "exactly 50%" off the peak, allowing for AR(1) noise
    assert peak_i < trough_i                       # the peak comes before the trough
    assert closes[-1] > closes[0]                   # finishes above where it started
    assert fx["meta"]["max_drawdown_pct"] == round(dd, 1)


def test_orb_is_the_fund_and_falls_less_than_volt_over_the_same_window():
    volt_dd = load("VOLT")["meta"]["max_drawdown_pct"]
    orb = load("ORB")
    assert orb["fund"] is True
    orb_dd = orb["meta"]["max_drawdown_pct"]
    assert orb_dd > volt_dd                         # a smaller drop (both are negative numbers)
    assert abs(orb_dd) < abs(volt_dd) / 2            # "small swings" versus "large swings", not just "less"


def test_anchor_prices_land_on_the_cent_regardless_of_noise():
    """The coach quotes exact dollar figures; the scripted waypoints must never drift."""
    fx = load("VOLT")
    assert fx["bars"][0]["c"] == 48.00
    assert fx["bars"][-1]["c"] == 56.80
