# Rich-HER (Astra Trading): Deliverables and Checklist

The master inventory of what has to exist for a winning HackHERS submission. Boxes track the **dry-run repo**: `[x]` means built and covered by a passing test in this repo. The event build is a separate, later exercise; see the pre-work note below.

> **Pre-work rule (unconfirmed).** Most hackathons (MLH rules) require code to be written during the event but allow planning, design and research beforehand. Until V2 confirms HackHERS's rule, treat this code as a dry run to *learn from*, not to reuse. What carries over regardless: [SPEC.md](SPEC.md) (the contract), the timings, and the lessons.

---

## 1. Code deliverables (dry-run repo)

| Done | Path | Owner | Contract |
|---|---|---|---|
| [x] | `server/sim_engine.py` | B | Pure rules: fills, stops, safety-net trigger, shadow benchmark ([SPEC §5](SPEC.md#5-simulation-engine-serversim_enginepy)) |
| [x] | `server/main.py` | B | FastAPI session, tier gates, 12 live routes + 2 stubs ([SPEC §8](SPEC.md#8-api-contract)) |
| [x] | `server/tests/`, `pytest.ini` | B | 60 tests: engine, fixtures, API and flows, content lint |
| [x] | `server/smoke-test.sh` | B | Sanity-checks every route on a running server |
| [x] | `scripts/build_fixtures.py`, `fixtures/*.json` | B | 5 symbols x 90 synthetic bars; AAPL has the −22.7% drawdown |
| [x] | `scripts/e2e-browser.mjs` | B | Optional headless-browser run of the whole flow |
| [x] | `web/index.html`, `index.css`, `app.js`, `format.js` | F | Shell, styles, state, rendering; phone layout |
| [x] | `web/chart.js` | F | Line, line + highs/lows, candlesticks; the future stays hidden |
| [x] | `web/order-ticket.js` | F | Tap-to-Explain ticket, 1.5 s Confirm lock |
| [x] | `web/hint.js`, `hints.json`, `checks.json` | V1 | Downside-first hints and two comprehension checks (**first draft**) |
| [x] | `web/money-flow.js`, `safety-net.js` | V1 | Plain-English money line; the −8% prompt with dynamic numbers |
| [x] | `web/tier-picker.js`, `tiers.json` | V2 | Onboarding, tier scrub, tier gating rules |

## 2. Content deliverables (people, not code)

- [ ] **V1: reread `hints.json` and `checks.json` line by line** against the downside-first rule and rewrite anything that still leads with upside. The lint only proves the *structure*; wording is a human call.
- [ ] **V1: read every hint aloud to someone with no finance background.** Fix the jargon they trip on.
- [ ] **V2: source the statistic** the pitch cites about the investing confidence gap.

## 3. Pre-event actions

| # | Action | Owner | Deadline |
|---|---|---|---|
| 1 | Confirm HackHERS 2027 dates, tracks, judging criteria and **pre-work rules** | V2 | This week |
| 2 | Resolve team composition (one or two frontend devs; **who is V2**) and lock file ownership | Team lead (AJ) | This week |
| 3 | Review `hints.json` downside-first, keyed by tier | V1 | 2 weeks |
| 4 | Confirm the demo symbol: AAPL's −22.7% drawdown is built in and verified (`scripts/build_fixtures.py --check`) | B | Done; re-verify if fixtures change |
| 5 | Schedule the full 24-hour dry-run build, ~3–4 weeks before the event, and time each phase against the 24-hour budget | Team lead | Date set this week |
| 6 | Confirm how the `.tech` domain is claimed (sponsor form vs self-purchase) and who owns DNS | V2 | This week |
| 7 | Pick the deploy targets (frontend host + backend host) so B and F are not guessing mid-event | Team lead (AJ) | 2 weeks |
| 8 | Decide whether the engine stays Python/FastAPI or is ported to Go/C++ (the four engine functions are what is worth porting) | B | Before the dry run |
| 9 | Do a visual design pass; `web/` is functional, not final | F | Before the event |

## 4. Presentation and demo

- [ ] **100% offline.** Run the demo with Wi-Fi off, three times. (`e2e-browser.mjs` already asserts no external requests and zero console errors.) **Owner: B + F**
- [ ] **3 of 3 clean rehearsals under 2:30.** The scripted demo budget is 2:15 ([SPEC §12](SPEC.md#12-demo-script-215)). **Owner: V2 + Team lead**
- [ ] **Stranger-QA with 3–5 non-finance people**, run in person, one **Reset demo** between each. The pitch line comes from `GET /api/qa-log`. Target: at least 4 of 5 correct on the stop-loss check first try. **Owner: V2**
- [ ] **5-slide deck.** **Owner: V2**
  1. The problem: the confidence and downside-literacy gap.
  2. The solution: downside-first + a replay where the future is hidden.
  3. Live demo (2 minutes).
  4. Stranger-QA results.
  5. Architecture and roadmap (one line: "architecture supports Alpaca paper trading").
- [ ] **Devpost writeup**, submitted by **H+22**, not H+23:59. Draft it before the event. **Owner: V2**
- [ ] **Say the tier-scrub sentence out loud:** "This previews what she unlocks. It isn't a shortcut."
- [ ] **Know the honest ending.** If a judge asks to keep going to Day 90, the shadow line flips (the net cost $68.00). That is the price of protection; say so.
- [ ] **Backup screen recording** of the 2:15 demo, saved locally on the presenting laptop.

## 5. Hosting: the `.tech` domain

The domain reintroduces the deployment dependency the review cut, so sequence it carefully ([SPEC §13](SPEC.md#13-hosting-and-the-tech-domain)):

- [ ] Claim the domain **before** the event.
- [ ] Deploy **once, near the end**, as a Devpost/judge follow-up link only.
- [ ] Present from **localhost, offline**, never the hosted URL.
- [ ] Frontend on Vercel/Netlify, backend on Render/Fly.io; set `RICHHER_CORS_ORIGINS` on the backend and `window.RICHHER_API` (or `?api=`) on the frontend.
- [ ] Remember the hosted server has **one shared demo session**.

## 6. Hardware and environment

- [ ] Python 3.10+ on the presenting laptop, with `pip install -r server/requirements.txt` done **before** the event (no network at the venue).
- [ ] Edge or Chrome, plus a second browser window tested for screen mirroring.
- [ ] The server started and a clean **Reset demo** done just before each presentation.
- [ ] A team channel (Slack/Discord/WhatsApp) with pinned links to the repo and docs.

## 7. Open decisions

| Decision | Who | Why it is open |
|---|---|---|
| Who is **V2**? | AJ | The deck, Devpost, QA, domain and HackHERS-rules work has no named owner. |
| One frontend dev or two? | AJ | The old README listed two co-leads; the ownership map assumes one F. |
| Who owns `tiers.json` and `tier-picker.js`? | AJ | The old README gave `tiers.json` to Collaborator 3; the prototype README gives it to V2, who is unassigned. |
| Keep Python or port to Go/C++? | B | Roles say Go/C++; the dry run is Python. |
| `LICENSE` file | AJ | `package.json` declared MIT; that file is gone and no `LICENSE` exists. |
