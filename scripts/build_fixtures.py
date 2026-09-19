#!/usr/bin/env python3
"""
scripts/build_fixtures.py

Generates the deterministic, SYNTHETIC intraday replay fixtures in fixtures/*.json.
Owned by B (Backend). Fixtures are generated, never hand-edited.

This is a faithful Python port of the tape generator that used to live in richher.html's
buildTape() (mulberry32 PRNG + AR(1) noise + anchor taper), so the six companies, their
seeds and their scripted arc (a buy invitation, a peak, a slide to a -50% trough, two
scares on the way back, an exit, a finish above the start) produce byte-identical prices
to what the offline demo already showed. Every dollar figure the coach speaks was tuned
against this exact output; changing the algorithm or a seed changes what she can truthfully
say. Ported and cross-checked bar-for-bar against the original JS (o/h/l/c/v/n, all 390
bars, all six symbols) before this file replaced the old daily-bar generator.

390 five-minute bars = one trading week (78 bars/day * 5 days). "i" is the tick index into
the tape; "day"/"time" are the wall-clock label the frontend shows. All six symbols share
one clock: the trading floor lets a session hold positions in more than one of them at once
from a single cash balance, so they must all be addressable at the same tick.

Run:    python scripts/build_fixtures.py           # (re)write fixtures/
Check:  python scripts/build_fixtures.py --check   # exit 1 if files differ from a fresh build
"""

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "fixtures"

GENERATOR_VERSION = 2
TICKS_PER_DAY = 78          # 6.5 trading hours of 5-minute bars
TAPE_LEN = 390               # 5 trading days
LAST_T = TAPE_LEN - 1
MASK = 0xFFFFFFFF

# The scripted arc, in tick indices. Chosen so the featured stock peaks just after the
# invitation to buy, falls exactly 50% off that peak, scares twice on the way back, and
# finishes above where it started. Losses first, long-term profit second.
T_BUY, T_PEAK, T_SLIDE, T_TROUGH, T_SCARE, T_EXIT = 60, 95, 150, 215, 280, 330

SYMBOLS = [
    {
        "symbol": "VOLT", "name": "Voltaic Cell Co.", "kind": "Stock",
        "sector": "Battery cells for cars and grids", "volatility": "large swings",
        "featured": True, "vol_base": 210e3,
        "blurb": "One company, one industry. Swings hardest in both directions.",
        "seed": 90210, "start_cash": 100.00,
        "anchors": [
            (0, 48.00, 0.0045), (T_BUY, 50.20, 0.0050), (T_PEAK, 52.40, 0.0055),
            (T_SLIDE, 42.80, 0.0110), (T_TROUGH, 26.20, 0.0190), (250, 31.50, 0.0150),
            (T_SCARE, 27.90, 0.0165), (T_EXIT, 41.00, 0.0105), (LAST_T, 56.80, 0.0070)],
    },
    {
        "symbol": "ORB", "name": "Orbit 500 Fund", "kind": "Fund",
        "sector": "Five hundred companies in one purchase", "volatility": "small swings",
        "fund": True, "vol_base": 88e3,
        "blurb": "Not a company. One purchase that owns a slice of five hundred of them.",
        "seed": 5150, "start_cash": 100.00,
        "anchors": [
            (0, 100.00, 0.0013), (T_BUY, 101.60, 0.0014), (T_PEAK, 104.20, 0.0016),
            (T_SLIDE, 99.50, 0.0028), (T_TROUGH, 92.60, 0.0040), (250, 95.10, 0.0032),
            (T_SCARE, 93.80, 0.0034), (T_EXIT, 101.30, 0.0024), (LAST_T, 109.40, 0.0018)],
    },
    {
        "symbol": "KIN", "name": "Kindred Grocers", "kind": "Stock",
        "sector": "Supermarkets", "volatility": "small swings", "vol_base": 31e3,
        "blurb": "People buy food in every kind of week. It moves slowly.",
        "seed": 4242, "start_cash": 100.00,
        "anchors": [
            (0, 31.00, 0.0016), (T_PEAK, 31.90, 0.0018), (T_SLIDE, 30.60, 0.0026),
            (T_TROUGH, 29.40, 0.0034), (T_SCARE, 30.20, 0.0028), (LAST_T, 33.20, 0.0020)],
    },
    {
        "symbol": "HLX", "name": "Helix Biolabs", "kind": "Stock",
        "sector": "Experimental medicines", "volatility": "large swings", "vol_base": 74e3,
        "blurb": "Moves on its own news, on its own days. Rarely in step with the rest.",
        "seed": 1337, "start_cash": 100.00,
        "anchors": [
            (0, 88.00, 0.0060), (50, 72.40, 0.0120), (T_PEAK, 80.10, 0.0090),
            (T_SLIDE, 96.30, 0.0075), (T_TROUGH, 88.20, 0.0100), (T_SCARE, 103.50, 0.0080),
            (LAST_T, 94.60, 0.0090)],
    },
    {
        "symbol": "MERI", "name": "Meridian Power", "kind": "Stock",
        "sector": "Electricity utility", "volatility": "small swings", "vol_base": 22e3,
        "blurb": "A utility. Dull on purpose, which is a feature and not a flaw.",
        "seed": 606, "start_cash": 100.00,
        "anchors": [
            (0, 62.00, 0.0011), (T_SLIDE, 61.20, 0.0016), (T_TROUGH, 60.10, 0.0022),
            (LAST_T, 64.40, 0.0013)],
    },
    {
        "symbol": "CASA", "name": "Casa Coffee Group", "kind": "Stock",
        "sector": "Coffee shops", "volatility": "medium swings", "vol_base": 45e3,
        "blurb": "Enough shops to be steady, small enough to still get knocked about.",
        "seed": 8899, "start_cash": 100.00,
        "anchors": [
            (0, 19.00, 0.0030), (T_PEAK, 20.80, 0.0034), (T_SLIDE, 18.10, 0.0055),
            (T_TROUGH, 15.30, 0.0080), (T_SCARE, 16.90, 0.0060), (LAST_T, 21.60, 0.0038)],
    },
]


# --------------------------------------------------------------------------- the PRNG

def _mulberry32(seed):
    """Same generator as web/index.html's mulberry32(), reproduced with unsigned 32-bit
    modular arithmetic throughout. Addition, XOR, OR and multiplication mod 2**32 are all
    representation-agnostic (the bit pattern is the same whether you call it signed or
    unsigned), so keeping every intermediate value in [0, 2**32) and only interpreting it
    as unsigned at the final division reproduces JS's Math.imul / >>> / |0 exactly without
    needing a separate signed representation anywhere."""
    state = seed & MASK

    def rand():
        nonlocal state
        state = (state + 0x6D2B79F5) & MASK
        t = state
        a = (t ^ (t >> 15)) & MASK
        b = (1 | t) & MASK
        t = (a * b) & MASK                       # Math.imul(seed ^ seed>>>15, 1|seed)
        c = (t ^ (t >> 7)) & MASK
        d = (61 | t) & MASK
        e = (c * d) & MASK                       # Math.imul(t ^ t>>>7, 61|t)
        t2 = ((t + e) & MASK) ^ t                 # t + Math.imul(...) ^ t
        return ((t2 ^ (t2 >> 14)) & MASK) / 4294967296

    return rand


def _js_round(x):
    """JS Math.round: round half toward +Infinity (not Python's round-half-to-even)."""
    return math.floor(x + 0.5)


def _r2(n):
    return _js_round(n * 100) / 100


def _clamp(n, lo, hi):
    return max(lo, min(hi, n))


# --------------------------------------------------------------------------- the tape

def build_bars(anchors, seed, vol_base):
    """anchors: [(tick, price, ambient_noise), ...]. Returns TAPE_LEN bars, each
    {i, o, h, l, c, v, n}. `n` is the ambient volatility at that tick (how fast the market
    is moving, independent of the scripted price path) - sim_engine's slippage model reads
    it. Anchor prices land exactly on the cent; only the path between them is randomised,
    so every dollar figure the coach quotes stays exact on every rebuild."""
    rand = _mulberry32(seed)

    def gauss():
        r1 = rand() or 1e-9
        r2v = rand()
        return math.sqrt(-2 * math.log(r1)) * math.cos(2 * math.pi * r2v)

    bars = []
    e = 0.0
    a = 0
    prev_close = anchors[0][1]

    for i in range(TAPE_LEN):
        while a < len(anchors) - 2 and i > anchors[a + 1][0]:
            a += 1
        t0, p0, n0 = anchors[a]
        t1, p1, n1 = anchors[a + 1]
        u = _clamp((i - t0) / (t1 - t0), 0, 1)
        ease = (1 - math.cos(math.pi * u)) / 2      # smooth between anchors
        taper = math.sin(math.pi * u)                # 0 at both anchors
        base = p0 + (p1 - p0) * ease
        # Ambient volatility is interpolated but never tapered: the market keeps moving
        # even at the ticks the coach stops on, which is where the slippage lesson bites.
        ambient = n0 + (n1 - n0) * ease
        noise = ambient * taper                       # the displacement IS tapered

        e = e * 0.72 + gauss() * 0.46                 # AR(1): autocorrelated wiggle
        close = max(0.5, base * (1 + e * noise))

        open_ = prev_close
        lo, hi = min(open_, close), max(open_, close)
        wick = max(hi * noise * 0.55, (hi - lo) * 0.3)
        move = abs(close - open_) / (open_ or 1)
        bars.append({
            "i": i,
            "o": _r2(open_),
            "h": _r2(hi + abs(gauss()) * wick),
            "l": _r2(max(0.25, lo - abs(gauss()) * wick)),
            "c": _r2(close),
            "v": _js_round(vol_base * (0.5 + move * 90 + rand() * 0.7)),
            "n": round(ambient, 6),
        })
        prev_close = close

    for t, p, _n in anchors:
        if t <= LAST_T:
            bars[t]["c"] = _r2(p)
            bars[t]["h"] = max(bars[t]["h"], _r2(p))
            bars[t]["l"] = min(bars[t]["l"], _r2(p))
    return bars


def _clock(i):
    day = i // TICKS_PER_DAY + 1
    mins = 9 * 60 + 30 + (i % TICKS_PER_DAY) * 5
    return day, f"{mins // 60:02d}:{mins % 60:02d}"


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


def build_fixture(cfg):
    bars = build_bars(cfg["anchors"], cfg["seed"], cfg["vol_base"])
    for b in bars:
        b["day"], b["time"] = _clock(b["i"])
    closes = [b["c"] for b in bars]
    dd, peak_i, trough_i = max_drawdown(closes)
    meta = {"max_drawdown_pct": round(dd, 1), "peak_tick": peak_i, "trough_tick": trough_i,
            "first_close": closes[0], "last_close": closes[-1]}
    return {
        "symbol": cfg["symbol"], "name": cfg["name"], "kind": cfg["kind"],
        "sector": cfg["sector"], "blurb": cfg["blurb"], "volatility": cfg["volatility"],
        "featured": cfg.get("featured", False), "fund": cfg.get("fund", False),
        "synthetic": True,
        "generator": {"script": "scripts/build_fixtures.py", "seed": cfg["seed"],
                      "version": GENERATOR_VERSION},
        "ticks_per_day": TICKS_PER_DAY, "tape_len": TAPE_LEN,
        "start_cursor": 0, "start_cash": cfg["start_cash"], "meta": meta,
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
    for old in OUT_DIR.glob("*.json"):
        if old.name not in built:
            old.unlink()
    for name, text in built.items():
        (OUT_DIR / name).write_text(text, encoding="utf-8", newline="\n")
        fx = json.loads(text)
        m = fx["meta"]
        print(f"{name:10} seed={fx['generator']['seed']:<6} max drawdown {m['max_drawdown_pct']:>6}% "
              f"(ticks {m['peak_tick']}->{m['trough_tick']})  {fx['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
