#!/usr/bin/env python3
"""
scripts/build_fixtures.py

Generates the deterministic, SYNTHETIC OHLC replay fixtures in fixtures/*.json.
Owned by B (Backend). Fixtures are generated, never hand-edited.

The prices are not real market data. Each path is pinned to hand-chosen anchor
closes and filled in with seeded noise (a Brownian bridge between anchors), so
every run on every machine produces byte-identical files.

AAPL is the guided-demo symbol. Its generator keeps searching seeds until the
path has a -22.7% max drawdown between bars 45 and 60 AND the demo beats in
SPEC.md section 12 hold (safety-net prompt, then the stop fill at its stop price).

Run:    python scripts/build_fixtures.py           # (re)write fixtures/
Check:  python scripts/build_fixtures.py --check   # exit 1 if files differ from a fresh build
"""

import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "fixtures"

N_BARS = 90
GENERATOR_VERSION = 1
DRAWDOWN_TARGET_PCT = -22.7           # AAPL, bars 45 -> 60
FAST, SLOW = 5, 20                    # MA-crossover windows
PROMPT_PCT, STOP_PCT = -8.0, -10.0    # mirrors server/sim_engine.py
SEED_SEARCH_LIMIT = 20000

SYMBOLS = [
    {
        "symbol": "AAPL", "name": "Apple (synthetic replay)", "volatility": "medium",
        "blurb": "A steady climb, then a sharp pullback. The guided demo runs on this one.",
        "start_cursor": 40, "seed": 1000, "sigma": 0.009, "gap": 0.003, "wick": 0.004,
        "anchors": [(0, 150.00), (40, 168.00), (45, 172.00), (60, 132.96), (89, 158.00)],
    },
    {
        "symbol": "SPY", "name": "S&P 500 ETF (synthetic replay)", "volatility": "low",
        "blurb": "A broad index: gentle moves and shallow dips.",
        "start_cursor": 30, "seed": 2000, "sigma": 0.0045, "gap": 0.0015, "wick": 0.0015,
        "anchors": [(0, 480.00), (30, 492.00), (60, 486.00), (89, 505.00)],
    },
    {
        "symbol": "NKE", "name": "Nike (synthetic replay)", "volatility": "medium",
        "blurb": "A choppy consumer stock that drifts sideways with a mid-sized dip.",
        "start_cursor": 25, "seed": 3000, "sigma": 0.011, "gap": 0.004, "wick": 0.005,
        "anchors": [(0, 92.00), (20, 98.00), (50, 88.00), (70, 90.00), (89, 95.00)],
    },
    {
        "symbol": "TSLA", "name": "Tesla (synthetic replay)", "volatility": "high",
        "blurb": "Big swings both ways: the same time window, a much larger potential loss.",
        "start_cursor": 15, "seed": 4000, "sigma": 0.02, "gap": 0.008, "wick": 0.010,
        "anchors": [(0, 240.00), (15, 262.00), (35, 196.00), (60, 228.00), (89, 215.00)],
    },
    {
        "symbol": "KO", "name": "Coca-Cola (synthetic replay)", "volatility": "low",
        "blurb": "Slow and steady: small moves, small dips.",
        "start_cursor": 30, "seed": 5000, "sigma": 0.0035, "gap": 0.0012, "wick": 0.0012,
        "anchors": [(0, 62.00), (45, 64.50), (89, 66.00)],
    },
]


def _normal(rng):
    """Standard normal via Box-Muller on rng.random() (stable across Python versions)."""
    u1 = 1.0 - rng.random()
    u2 = rng.random()
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def build_closes(cfg, rng):
    """Noisy closes that hit every anchor exactly (noise is re-centred per segment)."""
    anchors = cfg["anchors"]
    closes = [0.0] * N_BARS
    closes[0] = anchors[0][1]
    for (a, pa), (b, pb) in zip(anchors, anchors[1:]):
        n = b - a
        raw = [cfg["sigma"] * _normal(rng) for _ in range(n)]
        shift = (math.log(pb / pa) - sum(raw)) / n
        price = pa
        for k in range(n):
            price *= math.exp(raw[k] + shift)
            closes[a + 1 + k] = round(price, 2)
        closes[b] = pb
    return closes


def build_bars(cfg, closes, rng):
    bars = []
    for i, c in enumerate(closes):
        prev = closes[i - 1] if i else c
        o = round(prev * (1 + cfg["gap"] * _normal(rng)), 2)
        h = round(max(o, c) * (1 + abs(_normal(rng)) * cfg["wick"]), 2)
        l = round(min(o, c) * (1 - abs(_normal(rng)) * cfg["wick"]), 2)
        bars.append({"day": i + 1, "o": o, "h": max(h, o, c), "l": min(l, o, c), "c": c})
    return bars


def max_drawdown(closes):
    """Returns (pct, peak_index, trough_index) of the worst close-to-close drawdown."""
    peak_i, worst = 0, (0.0, 0, 0)
    for i, c in enumerate(closes):
        if c > closes[peak_i]:
            peak_i = i
        dd = (c - closes[peak_i]) / closes[peak_i] * 100
        if dd < worst[0]:
            worst = (dd, peak_i, i)
    return worst


def ma_signals(closes):
    """Precomputed MA-crossover signals (fast SMA crossing the slow SMA)."""
    signals, prev = [], None
    for i in range(SLOW - 1, len(closes)):
        fast = sum(closes[i - FAST + 1:i + 1]) / FAST
        slow = sum(closes[i - SLOW + 1:i + 1]) / SLOW
        state = "UP" if fast > slow else "DOWN"
        if prev is not None and state != prev:
            signals.append({"bar": i, "day": i + 1,
                            "side": "BUY" if state == "UP" else "SELL", "price": closes[i]})
        prev = state
    return signals


def demo_beats(bars, entry_bar):
    """Where the guided demo's key moments fall for a buy at entry_bar's close, or None."""
    entry = bars[entry_bar]["c"]
    prompt_price = entry * (1 + PROMPT_PCT / 100)
    stop = round(entry * (1 + STOP_PCT / 100), 2)
    prompt_bar = next((i for i in range(entry_bar + 1, len(bars))
                       if bars[i]["c"] <= prompt_price + 1e-9), None)
    stop_bar = next((i for i in range(entry_bar + 1, len(bars)) if bars[i]["l"] <= stop), None)
    if prompt_bar is None or stop_bar is None:
        return None
    return {"entry_bar": entry_bar, "entry_price": entry, "prompt_bar": prompt_bar,
            "prompt_price": bars[prompt_bar]["c"], "stop_price": stop, "stop_bar": stop_bar,
            "stop_fill_price": min(stop, bars[stop_bar]["o"])}


def problems_common(bars):
    out = []
    if len(bars) != N_BARS:
        out.append(f"expected {N_BARS} bars, got {len(bars)}")
    for b in bars:
        if not (b["h"] >= max(b["o"], b["c"]) and b["l"] <= min(b["o"], b["c"]) and b["l"] > 0):
            out.append(f"day {b['day']}: OHLC out of order")
            break
    return out


def problems_aapl(cfg, bars):
    """The guarantees behind 'the walk-into-the-dip beat is guaranteed, not hoped for'."""
    closes = [b["c"] for b in bars]
    dd, peak_i, trough_i = max_drawdown(closes)
    out = []
    if (peak_i, trough_i) != (45, 60):
        out.append(f"worst drawdown spans bars {peak_i}->{trough_i}, need 45->60")
    if round(dd, 1) != DRAWDOWN_TARGET_PCT:
        out.append(f"max drawdown {dd:.2f}%, need {DRAWDOWN_TARGET_PCT}%")
    if closes.index(max(closes)) != 45 or closes.index(min(closes)) != 60:
        out.append("bar 45 must be the highest close and bar 60 the lowest")
    beats = demo_beats(bars, cfg["start_cursor"])
    if beats is None:
        return out + ["demo beats not reachable"]
    if not 46 <= beats["prompt_bar"] <= 56:
        out.append(f"prompt bar {beats['prompt_bar']} outside the decline (46-56)")
    if beats["prompt_price"] <= beats["stop_price"]:
        out.append("prompt fires below the stop price, so the safety net cannot protect")
    if beats["stop_bar"] <= beats["prompt_bar"]:
        out.append("stop would trigger before or on the prompt bar")
    if beats["stop_fill_price"] != beats["stop_price"]:
        out.append("stop bar gaps below the stop price, so the fill would not be round")
    return out


def build_symbol(cfg):
    """Searches seeds from cfg['seed'] upward until every guarantee holds."""
    for seed in range(cfg["seed"], cfg["seed"] + SEED_SEARCH_LIMIT):
        rng = random.Random(seed)
        closes = build_closes(cfg, rng)
        bars = build_bars(cfg, closes, rng)
        problems = problems_common(bars)
        if cfg["symbol"] == "AAPL":
            problems += problems_aapl(cfg, bars)
        if not problems:
            return seed, bars
    raise RuntimeError(f"{cfg['symbol']}: no seed satisfied the constraints")


def build_fixture(cfg):
    seed, bars = build_symbol(cfg)
    closes = [b["c"] for b in bars]
    dd, peak_i, trough_i = max_drawdown(closes)
    meta = {"max_drawdown_pct": round(dd, 1), "peak_bar": peak_i, "trough_bar": trough_i,
            "first_close": closes[0], "last_close": closes[-1]}
    if cfg["symbol"] == "AAPL":
        meta["demo"] = demo_beats(bars, cfg["start_cursor"])
    return {
        "symbol": cfg["symbol"], "name": cfg["name"], "blurb": cfg["blurb"],
        "volatility": cfg["volatility"], "synthetic": True,
        "generator": {"script": "scripts/build_fixtures.py", "seed": seed,
                      "version": GENERATOR_VERSION},
        "start_cursor": cfg["start_cursor"], "meta": meta,
        "strategy": {"name": f"MA crossover ({FAST}/{SLOW})", "fast": FAST, "slow": SLOW,
                     "signals": ma_signals(closes)},
        "bars": bars,
    }


def dump(fixture):
    """Pretty header, one bar per line: keeps diffs readable."""
    head = json.dumps({k: v for k, v in fixture.items() if k != "bars"}, indent=2)
    rows = ",\n    ".join(json.dumps(b, separators=(", ", ": ")) for b in fixture["bars"])
    return head[:-2] + ',\n  "bars": [\n    ' + rows + "\n  ]\n}\n"


def build_all():
    """{filename: text} for every fixture. Imported by the tests."""
    return {f"{cfg['symbol']}.json": dump(build_fixture(cfg)) for cfg in SYMBOLS}


def main(argv):
    built = build_all()
    if "--check" in argv:
        stale = [n for n, text in built.items()
                 if not (OUT_DIR / n).exists() or (OUT_DIR / n).read_text(encoding="utf-8") != text]
        if stale:
            print("fixtures out of date or hand-edited:", ", ".join(stale))
            return 1
        print(f"fixtures OK ({len(built)} files match a fresh build)")
        return 0
    OUT_DIR.mkdir(exist_ok=True)
    for name, text in built.items():
        (OUT_DIR / name).write_text(text, encoding="utf-8", newline="\n")
        fx = json.loads(text)
        m = fx["meta"]
        print(f"{name:11} seed={fx['generator']['seed']:<5} max drawdown {m['max_drawdown_pct']:>6}% "
              f"(bars {m['peak_bar']}->{m['trough_bar']})  start bar {fx['start_cursor']}")
    demo = json.loads(built["AAPL.json"])["meta"]["demo"]
    print("AAPL demo beats:", json.dumps(demo))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
