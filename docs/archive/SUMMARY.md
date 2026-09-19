# Rich-HER refactor: summary of work

> **This document is archived.** It's a changelog for the v3.0 refactor (a large rewrite of the codebase), kept here for the history.

**Date:** 2026-09-18 · **Base commit:** `501d6eb` · **Current state:** the refactor was committed as `5ff9f7f` ("Migrate to Python backend, modular JS frontend, add tests and fixtures"), then merged with a collaborator's commit as `8632996`, and `origin/main` points to that same merged commit. This summary, and its link in the README, are the only changes made after that.

## 1. What was asked for

1. Read the README, SPEC, and WHITE_PAPER, and list out every deliverable for the project.
2. Fix the issues found during that review.
3. Replace `SPEC.md`, based on the prototype README that was shared (a FastAPI backend, five sample datasets, a `web/` folder split into separate modules).
4. Refactor the whole project, using an earlier "Optimization Pass 2" review as the reference for what to fix.

## 2. What came out of it

`SPEC.md` is now at version 3.0, and describes a rebuilt platform: a FastAPI server with a pure simulation engine (a "pure" function has no side effects — no file access, no randomness, just input in and output out), five sets of deterministic made-up price data, and a plain-JavaScript frontend split up according to the team's ownership map. The old Node.js version of the build is gone. The README, WHITE_PAPER, and NEEDED docs were all rewritten to match. `OPTIMIZATION_PASS_2.md` itself wasn't touched, and `SPEC.md`'s Appendix A maps each of its 14 findings to wherever it got resolved.

## 3. The original review

**Deliverables** fell into three groups: code and data files (the engine, server, price data, tests, frontend modules, hints, tiers), features that have to work during the demo (the replay, difficulty tiers, the Tap-to-Explain ticket, downside-first wording, the safety net, working offline, showing recovery), and pitch/validation work (testing with strangers, a 5-slide deck, submitting to Devpost by hour 22, rehearsals). The maintained checklist for all of this is [NEEDED.md](NEEDED.md).

**Five issues were flagged in the original review, and here's what happened to each:**

| Issue | What was done about it |
|---|---|
| Three frontend files were missing (`chart.js`, `ticket.js`, `safety-net.js`) | They were built, as `chart.js`, `order-ticket.js`, and `safety-net.js`. The frontend is a flat `web/` folder, with no separate `components/` subfolder. |
| The safety-net wording said "−$80" while the actual demo math produced −$120; the button also had three different labels in different places | Every number is now pulled directly from the user's actual position (the prompt now reads "down $138.30"). There's one consistent label everywhere: "Protect my position (sell at $151.20)". |
| The safety net used to fire at Tier 1, but the white paper described stops as a Tier 2 feature | The safety net now works at **every** tier. Tiers unlock control *over* it (setting your own percentage, using stop orders), not the protection itself. |
| The white paper described the price dip as "authentic" and "real market volatility" | The price data is synthetic (made up), and the app says so everywhere — in the UI, in the fixture files, and in every doc. `WHITE_PAPER.md` also gained a section honestly listing the product's limitations. |
| Nobody was named as the owner of pitch, testing, and Devpost work | **This one wasn't actually fixed** — nobody else can decide who that person is. It's now an explicit role called V2, but it's still unassigned. |

## 4. What was built

| Area | Files | Notes |
|---|---|---|
| **Price data** | `scripts/build_fixtures.py`, `fixtures/{HLX,BRD,KIN,VLT,BRW}.json` | 90 days of made-up prices each. The generator uses a fixed random seed and fixed anchor prices, so it produces byte-identical files on every machine. `--check` fails if any file is out of date or was hand-edited. |
| **Engine** | `server/sim_engine.py` | The pure trading rules, no imports. Handles market/limit/stop order fills, the safety-net trigger, and the shadow benchmark. |
| **API** | `server/main.py` | 12 live routes + 2 stubs (`/api/news`, `/api/fundamentals`). One shared in-memory session. Error codes are documented in SPEC §8.3. |
| **Content** | `web/hints.json`, `checks.json`, `tiers.json` | 23 downside-first hints, 2 comprehension questions, 3 difficulty tiers. The server reads the exact same tier and check files the browser does. |
| **Frontend** | `web/app.js`, `chart.js`, `order-ticket.js`, `hint.js`, `money-flow.js`, `safety-net.js`, `tier-picker.js`, `format.js`, `index.html`, `index.css` | No build step, no requests to outside servers, works on phone screens. |
| **Tests and tooling** | `server/tests/` (4 files), `pytest.ini`, `server/smoke-test.sh`, `scripts/e2e-browser.mjs`, `.gitignore` | See section 7 below. |
| **Docs** | `SPEC.md`, `README.md`, `WHITE_PAPER.md`, `NEEDED.md`, `docs/*.png` | All rewritten. Links and section anchors were checked. |

## 5. Design decisions worth knowing about

- **The future stays hidden.** The server only ever sends price data for `bars[0..today]`, and `/api/quote` refuses to return a future day's price. The chart's vertical axis only ever fits what's currently visible.
- **Fast-forward stops automatically for important events.** It moves one day at a time and pauses the instant an order fills or the safety net prompts. While a prompt is showing, `/api/advance` returns a `409 PROMPT_PENDING` error.
- **Stops are honest about their limits.** A stop order normally fills at the stop price, but if the price jumps past it overnight (a "gap"), it fills at the worse opening price instead — matching how real stop orders actually behave.
- **The shadow benchmark.** It compares your actual result against what would have happened if you'd ignored the safety net, and reports it honestly in both directions.
- **Difficulty tier unlocks.** Passing the downside-loss question unlocks Tier 2. Passing the stop-loss question unlocks Tier 3. Choosing "I've traded before" during onboarding starts you at Tier 2 automatically. The tier preview is read-only — you can look, but can't act, until you actually unlock it.
- **Recovery after a restart.** The browser keeps a saved log of the server's own action history. If the server restarts, the browser replays that log and the session comes back exactly as it was. A `boot_id` value tells the difference between an actual restart and an intentional reset — a reset is never automatically replayed back.
- **Testing with strangers.** `GET /api/qa-log` totals up first-try correctness for each comprehension question and generates the pitch line automatically.

**The guided demo, step by step (every number here is checked by an automated test):**

| Day | What happens | Number |
|---|---|---|
| 41 | Buy 10 HLX | $168.00; cash drops to $8,320.00 |
| 54 | Safety-net prompt appears | Price is $154.17, down $138.30 (−8.2%) |
| 55 | The stop order fills | $151.20; locks in a −$168.00 loss; cash rises to $9,832.00 |
| 61 | The lowest point | Price is $132.96; the safety net ended up saving **$182.40** ($18.24 per share) |
| 90 | Recovery | Price is $158.00; if she'd kept the shares, she'd actually be **$68.00 ahead** |

The demo's exact numbers **are different from the older docs** ($150 → $138 → $120, "a $15 loss per share") because the price data now follows the prototype README's spec: the −22.7% drop happens between days 45 and 60.

## 6. Bugs found in the old build (all now fixed)

- `index.html` was loading Google Fonts, which broke the "must work fully offline" rule. It now uses only fonts already built into the operating system.
- The chart used to draw all 90 days of data at once, so the whole future price dip was visible before it should have been. The scrubber also let you jump ahead to any day.
- The old SPEC's demo script said the price dropped to $138 by day 15, but the actual price data hit $138 on day 13 instead — they didn't match.
- The frontend used to keep its own separate copy of the portfolio and would compute fallback trades locally, which went against the "the backend is the single source of truth" rule. It also used blocking `alert()` popups, which freeze the whole page.
- README links used absolute file paths like `file:///c:/Users/...`, which only worked on the one machine that created them.

**Bugs found while testing this new build:**

- A JavaScript function called `replaceChildren` doesn't automatically flatten arrays, and prints the literal word "null" when given empty content. This meant the tier chips never actually rendered, and optional hints would have shown stray leftover text. Fixed with a shared helper function called `mount()`. Only running the full browser test caught this — it wasn't visible just from reading the code.
- The content-checking system rejected four hints for not naming a specific loss: the advanced limit-order hint, the line-chart hint, the strategy hint, and the shadow-benchmark hint. The actual wording was rewritten to fix this — the check itself wasn't loosened.
- The phone layout wasted about half the screen on the header, wrapped the "Fast-forward" label awkwardly, and shrank the chart's labels down to an unreadable size.

## 7. Verification

| Check | Result | What it covers |
|---|---|---|
| `python -m pytest` | **60 passed** (25 engine, 21 API/flow, 10 fixture, 4 content) | Order fill rules, gap-through stops, the −8% boundary, tier gating, the full demo sequence, the QA log, that the replay log rebuilds sessions exactly, that the route table is frozen at 14, hint content checks, that fixtures are reproducible |
| `bash server/smoke-test.sh` | **52 passed** | Every route against a live server, static file serving, CORS settings, then the unit tests |
| `python scripts/build_fixtures.py --check` | OK | Confirms the five fixture files match what a fresh build would produce |
| `node scripts/e2e-browser.mjs` | **59 passed** | Drove the real UI in a headless copy of Edge: onboarding, buying, both comprehension questions, the tier preview, fast-forward, the safety net, confirming a server restart restores the session, confirming a reset does NOT get resurrected, two-server mode, the "server is down" message, and zero console errors |
| Checked every doc's links and anchors | All good | README, SPEC, WHITE_PAPER, NEEDED, OPTIMIZATION_PASS_2 |
| Reviewed screenshots | Desktop and phone | Layout, chart labels, the prompt modal, the header |

**Not verified yet:** macOS or Linux (only tested on the current setup); Chrome, Firefox, or Safari (only Edge was actually driven by the automated test); an actual Wi-Fi-off test (the browser test confirms no external requests and no console errors, but the network wasn't physically disconnected during testing); running the README's quickstart instructions from a completely fresh clone with a brand-new virtual environment. The "zero console errors" result ignores one expected "connection refused" message that appears when the test intentionally stops the server.

## 8. What changed, file by file

- **Added:** `.gitignore`, `pytest.ini`, `docs/` (2 screenshots), `fixtures/` (5 files), `scripts/` (`build_fixtures.py`, `e2e-browser.mjs`), `server/` (`__init__.py`, `main.py`, `sim_engine.py`, `requirements.txt`, `smoke-test.sh`, `tests/`), and inside `web/`: `chart.js`, `checks.json`, `format.js`, `hint.js`, `hints.json`, `money-flow.js`, `order-ticket.js`, `safety-net.js`, `tier-picker.js`, `tiers.json`.
- **Rewritten:** `SPEC.md`, `README.md`, `WHITE_PAPER.md`, `NEEDED.md`, `web/app.js`, `web/index.html`, `web/index.css`.
- **Deleted (still recoverable from git history if needed):** `server/index.js`, `web/sim-engine.js`, `test/smoke-test.js`, `data/hints.json`, `data/tiers.json`, `data/fixtures/drawdown.json`, `package.json`.
- **Left untouched:** `OPTIMIZATION_PASS_2.md`, `GBM.py` (a collaborator's early numpy experiment, now superseded by `build_fixtures.py`), and `Demo - Line Graph` (added by Anusha Kumar in commit `86765cf` while the refactor was already underway — not reviewed as part of this work).

## 9. Decisions that need your input

**Interpretations made where the prototype README was vague** (see SPEC Appendix B): there was no `API_CONTRACT.md` file in the folder, so the API contract described here was derived from context; what "shadow benchmark" and "money-flow line" actually mean; what each comprehension check should unlock; that "alternate onboarding branch" means starting directly at Tier 2; that stops fill at the opening price when the price gaps past them; and the decision to use synthetic (made-up), anchor-pinned price data.

**Still-open decisions** ([NEEDED.md §7](NEEDED.md#7-open-decisions)):

- Who takes the V2 role? The deck, Devpost, testing, domain, and HackHERS-rules work currently has no owner.
- One frontend developer, or two?
- Who owns `tiers.json` and `tier-picker.js`? The old README assigned this to a third collaborator; the prototype README assigns it to V2, who's unassigned.
- Keep the engine in Python, or port it to Go/C++?
- Add a `LICENSE` file — the deleted `package.json` used to declare the project as MIT-licensed.

**Things to be careful about:**

- The refactor rewrote nearly every file and is already on `origin/main`, so anyone with local uncommitted work should pull first and check carefully for conflicts.
- HackHERS's rules about work done before the event are still unconfirmed, so this dry-run code isn't cleared yet for reuse at the actual event.
- `hints.json` and `checks.json` are a first draft — V1 still needs to reread them.
- The hosted server only supports one shared demo session at a time.

## 10. How to run it

```bash
pip install -r server/requirements.txt
python -m uvicorn server.main:app --port 8000     # open http://127.0.0.1:8000
python -m pytest                                  # 60 tests
```

Full setup instructions and troubleshooting are in the [README](../../README.md).
