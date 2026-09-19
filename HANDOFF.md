# Handoff — merge the Astra-trading backend into `richher.html`

**Goal:** make `web/richher.html` the real frontend of the FastAPI backend in
`Astra-trading/`, so the six-tab session runs against server-owned money maths
instead of computing prices, fills, P&L and endings in the browser.

**Read first, in this order:** `Astra-trading/CLAUDE.md` (project rules),
`Astra-trading/API.md` (the 19 routes and the `state` snapshot), `web/RICHHER.md`
(what `richher.html` promises and why). Those three explain nearly every
constraint below.

---

## 1. What exists on each side

| Side | File | What it owns today |
|---|---|---|
| Frontend | `web/richher.html` (2,989 lines, self-contained) | 6 tabs, the 390-tick intraday tape, 6 fictional companies, order fills **with slippage**, 6 coach halts, 5 endings, 10 in-browser self-checks |
| Backend | `Astra-trading/server/main.py` (766 lines) | session, 17 live routes + 2 stubs, `snapshot()` |
| Backend | `Astra-trading/server/sim_engine.py` | pure market maths: validate, fill, positions, safety net, shadow benchmark |
| Backend | `Astra-trading/server/story_engine.py` | pure scene graph, declarative conditions, flags, endings |
| Backend | `Astra-trading/web/` | the *existing* ES-module frontend (`app.js` + 8 components) that already speaks to the API |
| Content | `Astra-trading/web/scenes/*.json`, `coach.json`, `tiers.json`, `checks.json` | words and rules, shared by server and browser |
| Data | `Astra-trading/fixtures/*.json` | 6 generated daily-bar fixtures, 90 bars each |

There is already a working reference implementation of "browser talks to this
API": `Astra-trading/web/app.js`. Steal its `call()` / `act()` pattern
(`app.js:41-70`) rather than inventing a new one.

`Astra-trading` is a git repo; the outer `investment-sim` folder is not.

---

## 2. The decision that gates everything — read before writing code

`richher.html` exists because it opens by double-click with **no server**.
`web/RICHHER.md` states this as the reason the file is one piece: `fetch()` and
ES modules both fail under `file://`, and the venue demo runs with Wi-Fi off.
Serving it from FastAPI removes that property.

Three ways to go:

**A. Hybrid (recommended).** Keep the local engine as a fallback. On boot, try
`GET /api/state`; if it answers, the server is the source of truth for every
number. If it does not, fall back to the in-page tape and say so in the badge
that already reads `dataSource`. Costs: the money maths exists twice and must be
kept in step — which is exactly the arrangement `web/story.html:531-540` already
documents ("a faithful JS MIRROR of `server/story_engine.py`"), so there is
precedent in this codebase for doing it deliberately.

**B. Server-only.** Delete the in-page engine, serve `richher.html` from
FastAPI, follow `CLAUDE.md` to the letter. Cleanest code, loses the
double-click demo.

**C. Backend-only-for-content.** Server supplies scenes, coach copy and tiers;
browser keeps the maths. Violates the project's central rule and gains little.

**Everything below assumes A or B.** If the answer is C, most of section 4 does
not apply. Confirm the choice with the project owner before starting — this is
not a detail that can be reversed cheaply.

---

## 3. What has to move to the server

`CLAUDE.md`: *"The browser never calculates anything about money. If you are
about to write `price * quantity` in a `.js` file — stop."*

| In `richher.html` | Line | Must become |
|---|---|---|
| `buildTape()` — the 390-tick price series | 1245 | a generated fixture (`scripts/build_fixtures.py`) |
| `fillPrice()` — slippage against the trader | 2319 | a pure function in `sim_engine.py` |
| `placeOrder()` — cash, basis, position maths | 2325 | `POST /api/orders` |
| `equity()` / `invested()` / `markEquity()` | 1426-1441 | `snapshot()` fields already exist |
| `HALTS[]` — 6 coach halts | 2422 | `web/scenes/*.json` |
| `ENDINGS[]` — 5 endings with JS predicates | 2676 | `web/scenes/endings.json` with **declarative** `when` |
| `runChecks()` — 10 self-checks | 2792 | mostly pytest; the survivors fetch from the API |
| `START_CASH = 100` | 1397 | read `state.starting_cash` — never hardcode |

The quiz, the slice figure, the order-book toy, the symbol-matching game and the
tab spine involve no money and can stay in the browser as-is.

---

## 4. The five real mismatches

### 4.1 Intraday ticks vs daily bars

`richher.html` runs 390 five-minute ticks over 5 days (`TICKS_PER_DAY = 78`,
`TAPE_LEN = 390`, `richher.html:1231`). The backend is daily: 90 bars,
`sim_engine.price_at(bars, cursor)`, `snapshot()` slices `bars[:cursor+1]`.

Nothing in `sim_engine.py` actually cares what a "bar" *means* — it is an index
into a list of `{o,h,l,c}`. So the cheapest route is to generate a
390-row intraday fixture and let `cursor` mean "tick". You will need to add:

- a tick-aware clock (port `tapeClock()`, `richher.html:1353`) so `day`/`time`
  come from the server, not the browser;
- `n` in each bar (ambient volatility) — the slippage model needs it;
- the AR(1) + anchor-taper generator from `buildTape()` ported into
  `scripts/build_fixtures.py`. **Never hand-edit `fixtures/*.json`.**

Watch the `/api/advance` cap: `AdvanceReq.n` is `1..30` and the loop steps one
bar at a time so a fill or prompt can never be skipped (`main.py:404-440`).
390 ticks at 185 ms each is ~5.4 requests/second if you advance one at a time.
**Recommended:** advance in one call to the next halt tick and let the browser
animate through the bars the response returned. That keeps the no-look-ahead
rule intact (the server still never sends past the halt) and costs six round
trips instead of 390.

### 4.2 The symbol universes are different — and two names collide

| `richher.html` | Backend fixture |
|---|---|
| VOLT · Voltaic Cell Co. | VLT · Voltaic Motors |
| ORB · Orbit 500 Fund | BRD · Broadline 500 Fund |
| KIN · **Kindred Grocers** | KIN · **Kinetic Apparel** |
| HLX · **Helix Biolabs** | HLX · **Helix Devices** |
| MERI · Meridian Power | — |
| CASA · Casa Coffee Group | BRW · Brightwater Coffee |
| — | NVX · Novexa Systems |

`KIN` and `HLX` are the same ticker for different fictional companies. Pick one
naming set and change the other end — do not let both live. Self-check 9 in
`richher.html` ("Every symbol maps to exactly one company") will catch it if you
forget, and so will `test_content.py`.

Also: backend starting cash is per-symbol — NVX is $100, everything else
$10,000 (`build_fixtures.py:69`, `API.md`). `richher.html` starts at $100 with a
$10,000 goal. Whichever fixture becomes the featured one needs
`"start_cash": 100.00` in its config.

### 4.3 Slippage does not exist server-side

`sim_engine.immediate_fill_price()` (line 85) fills market orders at the bar's
close. `richher.html:2319` fills at `close × (1 ± min(0.012, bar.n × 0.45))`,
always against the trader. `RICHHER.md` quotes the resulting numbers as
teaching content — 0.20% in the calm, 0.86% at the trough, and the money-flow
line names the gap in dollars the first time it exceeds 50¢.

Port that into `sim_engine.py` as a pure function beside `immediate_fill_price`,
return the quote and the fill separately so the response can show both, and add
the slippage figures to the fill event. Self-check 8 ("Market-order slippage
never favours the trader") becomes a pytest assertion.

### 4.4 The flag vocabularies do not overlap

`story_engine.KNOWN_FLAGS` (line 26) is a closed set of eight, and an unknown
flag raises rather than being ignored — deliberately, so a typo cannot silently
make an ending unreachable. `richher.html` uses a different set:
`panicked_at_the_bottom`, `held_the_slide`, `averaged_down`, `bought_the_dip`,
`stock_picker`, `took_the_profit`, `sold_half`, `held_to_close`,
`felt_slippage`, `diversified`.

Only `diversified` is shared. Extend `KNOWN_FLAGS` deliberately, and note that
some richher flags are derivable from the portfolio rather than set by content
(`derive_flags`, `story_engine.py:83`) — prefer derived, because a derived flag
cannot drift from what actually happened.

Endings must also be rewritten from JS predicates (`when: f => f.has(...)`) into
the declarative `{all/any/not/flag/computed + operator}` form
(`endings.json`, `story_engine.matches()`). Conditions are data on purpose so a
writer can edit content without being able to execute code. Keep the priority
ordering and keep the catch-all (`started` in richher, `steady_hand` in the
backend) last.

### 4.5 A story choice cannot buy or sell

`story_engine.KNOWN_EFFECTS` is `{"withdraw", "deposit"}` only (line 41), and
`main.py:apply_effect()` (line 637) handles just those two. But richher's halt
options carry `buy: n`, `sellAll: true`, `sellHalf: true`
(`richher.html:2443-2575`).

Two options:
- **Browser sequences it** — `POST /api/orders` then `POST /api/story/advance`.
  No backend change, but two non-atomic calls; if the order fails
  (`INSUFFICIENT_FUNDS`) you must not advance the scene.
- **Extend the effect vocabulary** — add `buy`/`sell_all`/`sell_half` to
  `KNOWN_EFFECTS` and apply them in `apply_effect()`. Atomic, and it keeps the
  content declarative. **Recommended.** Note `apply_effect` already models the
  failure case well (`CANNOT_WITHDRAW` with a plain-English message) — follow
  that shape.

---

## 5. Suggested order of work

Each phase should end green on `python dev.py check`.

0. **Decide section 2.** Write the answer at the top of this file.
1. **Fixture first.** Port `buildTape()` into `scripts/build_fixtures.py`, emit
   the intraday fixture with `n` per bar, run `python dev.py fixtures`. Assert
   the arc in `test_fixtures.py`: peak, −50.0% at the trough, close above start,
   and the fund falling less than the single company (that is richher's
   self-check 6, and `RICHHER.md` cites −11.2% vs −50.1%).
2. **Slippage into `sim_engine.py`** + unit tests. Pure, no I/O.
3. **Content into JSON.** Halts → a scene graph; endings → declarative `when`.
   Extend `KNOWN_FLAGS`/`KNOWN_EFFECTS`. `test_scenes.py` will fail loudly on
   any dollar figure that does not match the fixture — that is the point.
4. **Wire tab 6 (the floor) to the API.** Biggest single chunk. Replace
   `placeOrder`/`equity`/`fillPrice` calls with `act()`-style requests and
   re-render from `state`. Delete nothing until its replacement is green.
5. **Wire the debrief** to `GET /api/story/ending`. The ending is decided
   server-side, never in the browser.
6. **Onboarding.** Map quiz question 1 (`beginner`/`intermediate`/`advanced`,
   `richher.html:1535`) onto `POST /api/onboarding`
   (`experience: "new" | "experienced"`) + `tiers.json`. Three quiz answers
   against two onboarding values is a real mismatch — either widen the enum or
   fold `advanced` into `experienced` and let the tier picker do the rest.
   `instinct` and `fear` are display-only and can stay client-side.
7. **Move the self-checks.** Anything asserting the price arrays becomes pytest.
   Keep the in-browser panel — it is a demo asset — but have it read the API.

---

## 6. Traps

- **The route table is frozen.** `test_route_table_is_frozen_at_17_live_plus_2_stubs`
  (`test_api.py:22`) fails if you add a route. Update the set on purpose.
- **Content tests are strict on words**, not just on code: no "I don't know"
  option anywhere, no scoring field anywhere, no named loss without a next step,
  no drawdown without a recovery scene, no dead ends, no `goto` into nothing, no
  dollar figure that drifts from the fixture. Fix the content, not the test.
- **Offline is enforced by CI.** `scripts/e2e-browser.mjs` fails the build on any
  CDN, web font or external request, or any 404. It also needs ports 8000 and
  5500 free and Edge or Chrome installed. If `richher.html` becomes the served
  page, that script needs updating — it currently drives `index.html`.
- **Never bare `pytest` or `uvicorn`.** Use `python dev.py …`; it uses `.venv`.
- **`CLAUDE.md` says files under 800 lines, functions under 50, ES modules.**
  `richher.html` is 2,989 lines in one file. If you go server-only (option B),
  splitting it is implied. If hybrid (option A), the single file is the whole
  point — say so in a comment at the top so the next reader knows it is a
  deliberate exception, not drift.
- **Use `tokens.css` variables, never raw hex** in anything served.
  `richher.html` currently inlines its palette; keep the blue `#3987e5` / red
  `#e66767` data pair whatever happens — green/red is the colourblindness
  failure both READMEs call out, and the values are validated against the
  surface.
- **Pure engines stay pure.** No file read, no clock, no `random` in
  `sim_engine.py` or `story_engine.py`.

---

## 7. Verify

```bash
cd Astra-trading
python dev.py setup                       # once
python dev.py test                        # 197 tests
python dev.py fixtures                    # regenerate, then --check
python dev.py check                       # tests + fixtures + browser; run before committing
```

Manual pass: the featured stock still halves off its peak and still finishes
above its start; the fund still falls less; the coach still stops the market at
all six halts; no score appears anywhere; every dollar figure the coach speaks
matches what the chart draws.

Commit style: conventional commits, on a branch, never straight to `main`.

---

## 8. Do not

- Compute a price, a fill, a P&L or an ending in the browser (unless you chose
  option A, and then only in the clearly-marked offline fallback).
- Hand-edit anything in `fixtures/`.
- Hardcode `$100` — read `state.starting_cash`.
- Add a scoring field, a countdown, or an "I don't know" option. All three are
  product rules enforced by tests, and all three are explained in `RICHHER.md`.
- Add an internet dependency of any kind.
- Weaken a failing content test to make a sentence pass.

---

## 9. Open questions for the owner

1. Section 2 — hybrid, server-only, or content-only?
2. Which symbol set wins, richher's or the fixtures'? (`KIN` and `HLX` collide.)
3. Does the intraday tape replace the 90-day fixtures, or live alongside them as
   a seventh? Alongside means `sim_engine` must handle both bar meanings.
4. Three quiz tiers vs two onboarding values — widen the enum, or fold
   `advanced` into `experienced`?
