"""The fixtures are generated, reproducible, synthetic, and AAPL's dip is guaranteed."""

import json
from pathlib import Path

import pytest

from scripts import build_fixtures

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures"
SYMBOLS = ["AAPL", "SPY", "NKE", "TSLA", "KO"]


def load(symbol):
    return json.loads((FIXTURE_DIR / f"{symbol}.json").read_text(encoding="utf-8"))


def test_the_five_curated_symbols_exist():
    assert sorted(p.stem for p in FIXTURE_DIR.glob("*.json")) == sorted(SYMBOLS)


def test_files_match_a_fresh_build_so_nobody_hand_edited_them():
    for name, text in build_fixtures.build_all().items():
        assert (FIXTURE_DIR / name).read_text(encoding="utf-8") == text, f"{name} is stale: rerun scripts/build_fixtures.py"


@pytest.mark.parametrize("symbol", SYMBOLS)
def test_each_fixture_is_90_valid_synthetic_bars(symbol):
    fx = load(symbol)
    assert fx["synthetic"] is True and len(fx["bars"]) == 90
    assert [b["day"] for b in fx["bars"]] == list(range(1, 91))
    for b in fx["bars"]:
        assert b["h"] >= max(b["o"], b["c"]) and b["l"] <= min(b["o"], b["c"]) and b["l"] > 0
    assert 0 < fx["start_cursor"] < 60


def worst_drawdown(closes):
    peak_i, worst = 0, (0.0, 0, 0)
    for i, c in enumerate(closes):
        peak_i = i if c > closes[peak_i] else peak_i
        dd = (c - closes[peak_i]) / closes[peak_i] * 100
        worst = (dd, peak_i, i) if dd < worst[0] else worst
    return worst


def test_aapl_has_the_verified_22_7_percent_drawdown_in_bars_45_to_60():
    closes = [b["c"] for b in load("AAPL")["bars"]]
    dd, peak, trough = worst_drawdown(closes)
    assert (round(dd, 1), peak, trough) == (-22.7, 45, 60)
    assert closes.index(max(closes)) == 45 and closes.index(min(closes)) == 60


def test_aapl_demo_beats_are_recorded_and_true():
    fx = load("AAPL")
    demo, bars = fx["meta"]["demo"], fx["bars"]
    assert demo["entry_bar"] == fx["start_cursor"] == 40 and demo["entry_price"] == 168.0
    assert demo["prompt_bar"] == 53 and demo["prompt_price"] == bars[53]["c"] == 154.17
    assert demo["stop_price"] == 151.2 and demo["stop_bar"] == 54 and demo["stop_fill_price"] == 151.2
    assert all(b["c"] > 168.0 * 0.92 for b in bars[41:53])       # nothing fires early
    assert bars[54]["o"] >= 151.2 >= bars[54]["l"]               # no gap: the stop fills at exactly $151.20


def test_ma_crossover_signals_are_precomputed_ordered_and_alternate():
    strat = load("AAPL")["strategy"]
    sigs = strat["signals"]
    assert strat["fast"] == 5 and strat["slow"] == 20 and sigs
    assert [s["bar"] for s in sigs] == sorted(s["bar"] for s in sigs) and sigs[0]["bar"] >= 20
    assert all(a["side"] != b["side"] for a, b in zip(sigs, sigs[1:]))
