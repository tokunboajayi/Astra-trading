# Rich-HER refactor: summary of work

> **ARCHIVED.** A changelog for the v3.0 refactor, kept for history.

**Date:** 2026-09-18 · **Base commit:** `501d6eb` · **State:** the refactor is committed as `5ff9f7f` ("Migrate to Python backend, modular JS frontend, add tests and fixtures"), then merged with a collaborator's commit as `8632996`, and the local `origin/main` ref points at that same commit. This summary and its README link are the only changes made after that.

## 1. What was asked

1. Read the README, SPEC and WHITE_PAPER and list every project deliverable.
2. Fix the issues found in that review.
3. Replace `SPEC.md`, based on the prototype README you pasted (FastAPI backend, five fixtures, split `web/` modules).
4. Refactor the whole project, using Optimization Pass 2 as the reference.

## 2. Outcome

`SPEC.md` is now v3.0 and describes a rebuilt platform: a FastAPI server with a pure simulation engine, five deterministic synthetic fixtures, and a vanilla-JS frontend split by your ownership map. The old Node build is gone. README, WHITE_PAPER and NEEDED were rewritten to match. `OPTIMIZATION_PASS_2.md` is untouched, and `SPEC.md` Appendix A maps each of its 14 findings to where it is resolved.

## 3. The original review

**Deliverables** fall into three groups: code and data files (engine, server, fixtures, tests, frontend modules, hints, tiers), features that must work in the demo (replay, tiers, Tap-to-Explain, downside-first copy, safety net, offline, recovery), and pitch and validation work (stranger-QA, 5-slide deck, Devpost by H+22, rehearsals). The maintained checklist is [NEEDED.md](NEEDED.md).

**Five issues were flagged, and what became of each:**

| Issue | Resolution |
|---|---|
| Three frontend files missing (`chart.js`, `ticket.js`, `safety-net.js`) | Built, as `chart.js`, `order-ticket.js`, `safety-net.js`. The frontend is a flat `web/` folder with no `components/` subfolder. |
| Safety-net copy said "−$80" while the demo math gave −$120; the button had three labels | Every number now comes from the position (the prompt reads "down $138.30"). One label everywhere: "Protect my position (sell at $151.20)". |
| Safety net fired at Tier 1, but the white paper put stops at Tier 2 | The safety net works at **every** tier. Tiers unlock control over it (your own percentage, stop orders), not the protection. |
| White paper called the dip "authentic" and "real market volatility" | The data is synthetic and says so in the UI, the fixtures and every doc. `WHITE_PAPER.md` gained an honest-limitations section. |
| No named owner for pitch, QA and Devpost | **Not fixed**: no person can be named for you. It is now the explicit V2 role, still unassigned. |

## 4. What was built

| Area | Files | Notes |
|---|---|---|
| **Fixtures** | `scripts/build_fixtures.py`, `fixtures/{HLX,BRD,KIN,VLT,BRW}.json` | 90 synthetic bars each. Seeded and anchor-pinned, so byte-identical on every machine. `--check` fails if a file is stale or hand-edited. |
| **Engine** | `server/sim_engine.py` | Pure rules, no imports. Market/limit/stop fills, safety-net trigger, shadow benchmark. |
| **API** | `server/main.py` | 12 live routes + 2 stubs (`/api/news`, `/api/fundamentals`). One in-memory session. Error codes documented in SPEC §8.3. |
| **Content** | `web/hints.json`, `checks.json`, `tiers.json` | 23 downside-first hints, 2 comprehension checks, 3 tiers. The server reads the same tier and check files the browser does. |
| **Frontend** | `web/app.js`, `chart.js`, `order-ticket.js`, `hint.js`, `money-flow.js`, `safety-net.js`, `tier-picker.js`, `format.js`, `index.html`, `index.css` | No build step, no external requests, phone layout. |
| **Tests and tooling** | `server/tests/` (4 files), `pytest.ini`, `server/smoke-test.sh`, `scripts/e2e-browser.mjs`, `.gitignore` | See section 7. |
| **Docs** | `SPEC.md`, `README.md`, `WHITE_PAPER.md`, `NEEDED.md`, `docs/*.png` | Rewritten. Links and anchors checked. |

## 5. Design decisions worth knowing

- **Future is hidden.** The server only ever sends `bars[0..today]`, and `/api/quote` refuses a future bar. The y-axis fits only what is visible.
- **Fast-forward stops for events.** It steps one day at a time and halts at the first fill or safety-net prompt. While a prompt is open, `/api/advance` returns `409 PROMPT_PENDING`.
- **Stops are honest.** A stop fills at the stop price, but at the open when the price gaps through it.
- **Shadow benchmark.** It compares your result with ignoring the safety net, in both directions.
- **Tier unlocks.** Passing the downside check unlocks Tier 2. Passing the stop-loss check unlocks Tier 3. "I've traded before" starts at Tier 2. The tier scrub is a read-only preview.
- **Recovery.** The browser stores the server's action log. After a server restart it replays the log and the session returns exactly. A server `boot_id` tells a restart from an intentional reset, which is never resurrected.
- **Stranger-QA.** `GET /api/qa-log` totals first-try correctness per check and produces the pitch line.

**The guided demo (all asserted by a test):**

| Day | Event | Number |
|---|---|---|
| 41 | Buy 10 HLX | $168.00; cash $8,320.00 |
| 54 | Safety-net prompt | $154.17, down $138.30 (−8.2%) |
| 55 | Stop fills | $151.20; locks in −$168.00; cash $9,832.00 |
| 61 | Trough | $132.96; the net saved **$182.40** ($18.24 a share) |
| 90 | Recovery | $158.00; keeping the shares would have been **$68.00 ahead** |

The demo numbers **differ from the old docs** ($150 → $138 → $120, "$15 a share") because the fixture now follows your prototype README: the −22.7% drawdown sits in bars 45–60.

## 6. Defects found in the old build (all fixed)

- `index.html` loaded Google Fonts, breaking the offline rule. Now system fonts only.
- The chart drew all 90 bars, so the whole dip was visible up front. The scrubber also let you jump to any bar.
- The old SPEC's demo script (bar 15 → $138) didn't match the old fixture (bar 13 → $138).
- The client kept its own portfolio copy with a local fill fallback, against "backend is authoritative". It also used blocking `alert()` popups.
- README links were absolute `file:///c:/Users/...` paths that only worked on one machine.

**Bugs found by testing this build:**

- `replaceChildren` doesn't flatten arrays and prints the word "null" for empty children. The tier chips never rendered and optional hints would have shown stray text. Fixed with a shared `mount()` helper. Only the browser run caught this.
- The hint lint rejected four hints that named no loss: the advanced limit-order hint, the line-chart hint, the strategy hint and the shadow hint. The copy was rewritten, not the lint.
- The phone layout wasted half the screen on the header, wrapped the Fast-forward label and shrank chart labels to unreadable size.

## 7. Verification

| Check | Result | Covers |
|---|---|---|
| `python -m pytest` | **60 passed** (25 engine, 21 API/flow, 10 fixtures, 4 content) | Fill rules, gap-through stops, the −8% boundary, tier gating, the full demo beat, QA log, replay-log determinism, route table frozen at 14, hint lint, fixtures reproducible |
| `bash server/smoke-test.sh` | **52 passed** | Every route on a live server, static serving, CORS, then the unit tests |
| `python scripts/build_fixtures.py --check` | OK | The five fixture files match a fresh build |
| `node scripts/e2e-browser.mjs` | **59 passed** | Real UI in headless Edge: onboarding, buy, both checks, tier preview, fast-forward, safety net, server restart restored, reset not resurrected, two-server mode, server-down card, zero console errors |
| Doc link and anchor check | All good | README, SPEC, WHITE_PAPER, NEEDED, OPTIMIZATION_PASS_2 |
| Screenshots reviewed | Desktop and phone | Layout, chart labels, prompt, header |

**Not verified:** macOS or Linux; Chrome, Firefox or Safari (only Edge was driven); a literal Wi-Fi-off run (the browser test asserts no external references and no console errors, but the network wasn't physically disabled); the README quickstart from a fresh clone with a new virtualenv. The "zero console errors" result ignores the one expected connection-refused line when the test stops the server on purpose.

## 8. File changes

- **Added:** `.gitignore`, `pytest.ini`, `docs/` (2 screenshots), `fixtures/` (5), `scripts/` (`build_fixtures.py`, `e2e-browser.mjs`), `server/` (`__init__.py`, `main.py`, `sim_engine.py`, `requirements.txt`, `smoke-test.sh`, `tests/`), and in `web/`: `chart.js`, `checks.json`, `format.js`, `hint.js`, `hints.json`, `money-flow.js`, `order-ticket.js`, `safety-net.js`, `tier-picker.js`, `tiers.json`.
- **Rewritten:** `SPEC.md`, `README.md`, `WHITE_PAPER.md`, `NEEDED.md`, `web/app.js`, `web/index.html`, `web/index.css`.
- **Deleted (recoverable from git):** `server/index.js`, `web/sim-engine.js`, `test/smoke-test.js`, `data/hints.json`, `data/tiers.json`, `data/fixtures/drawdown.json`, `package.json`.
- **Untouched:** `OPTIMIZATION_PASS_2.md`, `GBM.py` (a collaborator's numpy sketch, superseded by `build_fixtures.py`), and `Demo - Line Graph` (added by Anusha Kumar in `86765cf` while the refactor was underway; not reviewed here).

## 9. Needs your decision

**Interpretations made where the prototype README was terse** (SPEC Appendix B): `API_CONTRACT.md` wasn't in the folder, so the API contract is derived; what "shadow benchmark" and "money-flow line" mean; what each check unlocks; that "alternate onboarding branch" means starting at Tier 2; stops filling at the open on a gap; synthetic anchor-pinned fixtures.

**Open decisions** ([NEEDED.md §7](NEEDED.md#7-open-decisions)):

- Who is V2? The deck, Devpost, QA, domain and HackHERS-rules work has no owner.
- One frontend dev or two?
- Who owns `tiers.json` and `tier-picker.js`? The old README said Collaborator 3; the prototype README says V2.
- Keep Python or port to Go/C++?
- Add a `LICENSE` file. The deleted `package.json` declared MIT.

**Cautions:**

- The refactor rewrote nearly every file and is already on `origin/main`, so any collaborator with local work should pull and check for conflicts.
- HackHERS's pre-work rules are unconfirmed, so this dry-run code is not cleared for reuse at the event.
- `hints.json` and `checks.json` are a first draft for V1 to reread.
- The hosted server has one shared demo session.

## 10. Run it

```bash
pip install -r server/requirements.txt
python -m uvicorn server.main:app --port 8000     # open http://127.0.0.1:8000
python -m pytest                                  # 60 tests
```

Full instructions and troubleshooting are in the [README](../../README.md).
