# Rich-HER (Astra Trading): Deliverables and Checklist

> **This document is archived.** It's the old v3.0 deliverables checklist. Current open items are in the [README](../../README.md) instead.

The master list of what needs to exist for a winning HackHERS submission. A checked box `[x]` means it's built and covered by a passing test *in this repo*. The actual event build is a separate, later exercise — see the note below.

> **Pre-work rule (unconfirmed).** Most hackathons (following MLH's standard rules) require code to be written *during* the event, but usually allow planning, design, and research to happen beforehand. Until V2 confirms HackHERS's specific rule, treat the code in this repo as a dry run to *learn from*, not something to reuse directly. What carries over regardless: [SPEC.md](SPEC_v3.0.md) (the contract this repo follows), the timing estimates, and the lessons learned.

---

## 1. Code deliverables (in this dry-run repo)

| Done | Path | Owner | What it covers |
|---|---|---|---|
| [x] | `server/sim_engine.py` | B | The pure trading rules: fills, stops, the safety-net trigger, the shadow benchmark ([SPEC §5](SPEC_v3.0.md#5-simulation-engine-serversim_enginepy)) |
| [x] | `server/main.py` | B | The FastAPI session, tier gates, 12 live routes + 2 stubs ([SPEC §8](SPEC_v3.0.md#8-api-contract)) |
| [x] | `server/tests/`, `pytest.ini` | B | 60 tests covering the engine, fixtures, API, flows, and content checks |
| [x] | `server/smoke-test.sh` | B | Sanity-checks every route against a running server |
| [x] | `scripts/build_fixtures.py`, `fixtures/*.json` | B | 5 companies × 90 days of made-up price data; HLX has the built-in −22.7% drop |
| [x] | `scripts/e2e-browser.mjs` | B | An optional full run-through of the app in a headless browser |
| [x] | `web/index.html`, `index.css`, `app.js`, `format.js` | F | The page shell, styles, state management, and rendering; works on phone screens too |
| [x] | `web/chart.js` | F | Line chart, line + high/low chart, candlesticks; future prices stay hidden |
| [x] | `web/order-ticket.js` | F | The Tap-to-Explain order ticket, with a 1.5-second Confirm lock |
| [x] | `web/hint.js`, `hints.json`, `checks.json` | V1 | Downside-focused hints and two comprehension questions (**first draft**) |
| [x] | `web/money-flow.js`, `safety-net.js` | V1 | The plain-English money summary line; the −8% safety-net prompt with numbers computed live |
| [x] | `web/tier-picker.js`, `tiers.json` | V2 | Onboarding flow, tier preview, tier-gating rules |

## 2. Content deliverables (needs a person, not code)

- [ ] **V1: reread `hints.json` and `checks.json` line by line** against the "lead with the downside" rule, and rewrite anything that still leads with the upside instead. The automated check only proves the *structure* is right — whether the wording actually does this is a human judgment call.
- [ ] **V1: read every hint out loud to someone with no finance background.** Fix whatever jargon they get tripped up on.
- [ ] **V2: find the source** for the statistic the pitch cites about the investing confidence gap.

## 3. Things to do before the event

| # | Action | Owner | Deadline |
|---|---|---|---|
| 1 | Confirm HackHERS 2027's dates, tracks, judging criteria, and **pre-work rules** | V2 | This week |
| 2 | Decide on team composition (one or two frontend developers; **who is taking the V2 role**) and lock in who owns which files | Team lead (AJ) | This week |
| 3 | Review `hints.json`, checking it leads with the downside, organized by tier | V1 | 2 weeks |
| 4 | Confirm the demo symbol: HLX's −22.7% drop is built in and verified (`scripts/build_fixtures.py --check`) | B | Already done; re-verify if the fixtures change |
| 5 | Schedule a full 24-hour practice build, about 3–4 weeks before the event, and time each phase against the real 24-hour budget | Team lead | Date to be set this week |
| 6 | Confirm how the `.tech` domain gets claimed (through a sponsor form, or self-purchased) and who owns the DNS settings | V2 | This week |
| 7 | Pick where to deploy (a host for the frontend, a host for the backend), so B and F aren't guessing mid-event | Team lead (AJ) | 2 weeks |
| 8 | Decide whether the engine stays in Python/FastAPI or gets ported to Go/C++ (the four core engine functions are what's worth porting) | B | Before the practice run |
| 9 | Do a real visual design pass — `web/` currently works, but isn't a finished look | F | Before the event |

## 4. Presentation and demo

- [ ] **Run 100% offline.** Do the demo with Wi-Fi off, three separate times, to be sure. (`e2e-browser.mjs` already checks for zero requests to outside servers and zero console errors.) **Owner: B + F**
- [ ] **3 out of 3 clean rehearsals, each under 2:30.** The scripted demo is budgeted at 2:15 ([SPEC §12](SPEC_v3.0.md#12-demo-script-215)). **Owner: V2 + Team lead**
- [ ] **Test with 3–5 strangers who aren't finance people**, done in person, resetting the demo between each one. The pitch line comes from `GET /api/qa-log`. Target: at least 4 out of 5 getting the stop-loss question right on the first try. **Owner: V2**
- [ ] **A 5-slide deck.** **Owner: V2**
  1. The problem: the confidence gap and lack of downside literacy.
  2. The solution: leading with the downside, plus a replay where the future stays hidden.
  3. Live demo (2 minutes).
  4. Results from testing with strangers.
  5. Architecture and roadmap (one line: "the architecture supports adding real paper trading through Alpaca").
- [ ] **Submit the Devpost writeup** by **hour 22**, not right at the hour-24 deadline. Draft it before the event starts. **Owner: V2**
- [ ] **Practice saying the tier-preview sentence out loud:** "This previews what she unlocks. It isn't a shortcut."
- [ ] **Know the honest ending by heart.** If a judge asks what happens if you keep going to Day 90, the shadow-benchmark line flips (the safety net ends up costing $68.00 net). That's the price of protection — say so plainly.
- [ ] **Record a backup screen recording** of the 2:15 demo, saved locally on the presenting laptop, just in case.

## 5. Hosting: the `.tech` domain

Adding a hosted domain reintroduces a dependency on the internet that the review process specifically cut, so sequence this carefully ([SPEC §13](SPEC_v3.0.md#13-hosting-and-the-tech-domain)):

- [ ] Claim the domain **before** the event.
- [ ] Deploy it **once, near the end**, purely as a follow-up link for judges on Devpost.
- [ ] Present from **localhost, with Wi-Fi off**, never from the hosted URL.
- [ ] Frontend on Vercel or Netlify, backend on Render or Fly.io; set `RICHHER_CORS_ORIGINS` on the backend and `window.RICHHER_API` (or a `?api=` query parameter) on the frontend.
- [ ] Remember: the hosted server has **one shared session** — it's not built for multiple people using it at once.

## 6. Hardware and environment

- [ ] Python 3.10+ installed on the presenting laptop, with `pip install -r server/requirements.txt` already run **before** the event (there's no internet access at the venue).
- [ ] Edge or Chrome ready, plus a second browser window tested for screen mirroring.
- [ ] The server started, and a clean **Reset demo** run, right before each presentation.
- [ ] A team channel (Slack/Discord/WhatsApp) with pinned links to the repo and these docs.

## 7. Still-open decisions

| Decision | Who decides | Why it's still open |
|---|---|---|
| Who takes the **V2** role? | AJ | The deck, Devpost, testing, domain, and HackHERS-rules work currently has no named owner. |
| One frontend developer, or two? | AJ | The old README listed two co-leads; the current ownership plan assumes just one. |
| Who owns `tiers.json` and `tier-picker.js`? | AJ | The old README assigned this to a third collaborator; the prototype README assigns it to V2, who's unassigned. |
| Keep the engine in Python, or port it to Go/C++? | B | The team's role descriptions mention Go/C++; the actual dry run is in Python. |
| A `LICENSE` file | AJ | `package.json` used to declare MIT, but that file is gone and there's no `LICENSE` file to replace it. |
