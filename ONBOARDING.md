# Onboarding

Two tracks. Find yours, follow it in order, then do the task at the end. Each track takes about an hour.

**The whole project is ~3,600 lines.** You can read all of it in an afternoon. Nothing here is magic and there is no framework hiding things from you.

---

## Step 0 — everyone does this first (5 minutes)

Open a terminal **in the project folder** and run:

```bash
python dev.py setup
python dev.py test
python dev.py run
```

Then open <http://127.0.0.1:8000>. You should see the app. Press **Ctrl+C** in the terminal to stop it.

**Use `python dev.py <command>` for everything.** You never need to "activate" a virtual environment — `dev.py` finds the right Python for you. This matters: the single most common way to lose an hour on this project is running `pytest` with the wrong Python and getting 20 errors that look like real bugs but are not.

| Command | What it does |
|---|---|
| `python dev.py setup` | Install everything. Once. |
| `python dev.py run` | Start the app. Auto-reloads when you save a `.py` file. |
| `python dev.py test` | 192 tests, under a second. |
| `python dev.py check` | Everything the build checks. **Run before you commit.** |
| `python dev.py fixtures` | Regenerate the market data. |
| `python dev.py reset` | Something broke badly? Wipe it and `setup` again. |

### If something goes wrong

| It says | What happened | Do this |
|---|---|---|
| `STOPPED: The virtual environment does not exist` | You skipped setup | `python dev.py setup` |
| `Address already in use` / port 8000 busy | The app is already running somewhere | Ctrl+C in that terminal, or close it |
| `Client.__init__() got an unexpected keyword argument 'app'` | You ran `pytest` directly with system Python | `python dev.py test` |
| `ModuleNotFoundError: No module named 'server'` | You are in the wrong folder | `cd` to the project root (where `dev.py` is) |
| Page loads but is blank | Look at the terminal for a red error | Fix that — the page reloads itself |

---

## The one rule, before either track

**The browser never calculates anything about money.**

Not the price, not the fill, not the profit, not the loss. Every button click sends a request, the server works out the new truth, and sends back **the entire state**. The browser throws away what it had and redraws.

```
click  →  POST /api/something  →  server recalculates EVERYTHING
       →  server returns the complete new state
       →  browser throws away what it had and redraws
```

There are no partial updates anywhere. If you catch yourself writing `price * quantity` in a `.js` file — stop. That number should have come from the server.

---

## Track A — Backend

**For the developer who knows Go, C++, and Python.**

Your Go/C++ instincts are mostly right here, with three differences worth knowing up front:

| You expect | Python does this instead |
|---|---|
| A compiler catching type errors | Nothing checks types at runtime. **The tests are your compiler.** Run them constantly. |
| Structs with declared fields | Plain `dict`s, passed around freely. A bar is `{"o":…, "h":…, "l":…, "c":…}`. |
| Interfaces / templates | Duck typing: if it has the method, it works. No declaration needed. |
| Header files / packages | One file per concern. `import` pulls names in directly. |
| Pointers and ownership | Everything is a reference, garbage-collected. No `new`, no `delete`, no `&`. |

**The good news:** the request/response types *are* statically declared, via Pydantic (`class OrderReq(BaseModel)` in `main.py`). That is the closest thing here to a struct definition, and it validates at the boundary automatically. If a request does not match, the client gets a 422 before your code ever runs.

### Read in this order

**1. `server/sim_engine.py`** (182 lines) — **start here.**

Pure functions. No web framework, no file reading, no clock, no randomness. It imports *nothing*. This is the file that would port to Go or C++ almost line for line.

Run it with no server at all:

```bash
.venv/Scripts/python -c "from server import sim_engine as s; print(s.apply_fill(100, None, 'BUY', 2, 21.0))"
```

Four functions carry the whole simulation:

| Function | Answers |
|---|---|
| `apply_fill()` | "I bought 2 shares — what is my new cash and position?" |
| `check_open_orders_for_bar()` | "Did any waiting order trigger on this day?" |
| `check_safety_net_candidates()` | "Is anything down 8% and unprotected?" |
| `shadow_delta()` | "What if I had ignored the safety net and held?" |

11 of its 13 functions have docstrings. It is the best-explained file in the repo.

**2. `server/story_engine.py`** (238 lines) — same contract, for the narrative. Walks a scene graph, evaluates conditions, picks an ending. Also pure, also testable with no server.

Note how conditions are **data, not code**:

```python
{"all": [{"computed": "equity", "gte": 110}, {"flag": "went_all_in"}]}
```

Nothing is ever `eval`'d. A writer can edit content files without being able to execute code. An unknown flag name raises immediately rather than silently failing — a typo would otherwise make an ending permanently unreachable.

**3. `fixtures/NVX.json`** — just data. 90 days of `{day, o, h, l, c}`. Open it, scroll it, 30 seconds. Every price is invented; every file carries `"synthetic": true`.

**4. `server/main.py`** (725 lines) — the HTTP layer. Big, but **13 labelled sections**:

```bash
grep -n "^# ---" server/main.py
```

Read it in three passes:

- **The `Session` dataclass** (~line 78). One object holding everything about one user's session. This is your struct. Read the field names; that is the vocabulary for the rest.
- **`snapshot()`** (~line 251). The most important function in the file. Packs the whole world into one JSON object. Every route ends by calling it. Long docstring — read it.
- **The routes.** 21 of them, all the same shape. Read two and you have read all of them:

```python
@app.post("/api/orders")                       # decorator = route registration
async def post_order(req: OrderReq):           # OrderReq is the validated request type
    session = SESSION                          # 1. get the session
    require_onboarded(session)                 # 2. check preconditions
    ...                                        # 3. do the thing, via sim_engine
    record(session, "POST", "/api/orders", …)  # 4. log it for restart recovery
    return {"order": order, "state": snapshot(session)}   # 5. return the WHOLE world
```

`async def` with no `await` inside is deliberate: each request runs to completion on the event loop, so two requests can never interleave writes to the shared session. It is the cheapest possible mutex. There is a comment saying so at the top of the file.

### Your first task

Add a `GET /api/health` route returning `{"ok": True, "symbols": len(FIXTURES)}`.

1. Open `server/main.py`, find `# ---- mock-only stubs`, add your route above it.
2. `python dev.py test` — **it will fail.** `test_route_table_is_frozen_at_17_live_plus_2_stubs` guards the API surface so nobody adds a route by accident.
3. Add `("GET", "/api/health")` to `EXPECTED_ROUTES` in `server/tests/test_api.py` and bump the count from 19 to 20.
4. `python dev.py test` — green.
5. `python dev.py run`, then visit <http://127.0.0.1:8000/api/health>.

That failing test is the point. Now you know the API surface is protected.

---

## Track B — Frontend

**For the developer who knows HTML, JavaScript, and Python.**

This stack is exactly yours. **No TypeScript, no React, no build step, no bundler, no `node_modules`.** Plain ES modules the browser loads directly. If you can read `document.getElementById`, you can read all of it.

**Change a `.js`, `.css`, or `.json` file → just refresh the browser.** No compile step.

### Read in this order

**1. `web/index.html`** (74 lines). The whole page. Plain HTML, no templates. Every element the JS touches has an `id`. Skim it so the names in `app.js` mean something.

**2. `web/format.js`** (31 lines). Start here — it's tiny and everything else uses it.

It defines `h()` — a helper for making DOM elements:

```js
h('button', { class: 'btn', onclick: save }, 'Save')
// same as document.createElement('button'), set className, addEventListener, append text
```

**Text set through `h()` is never parsed as HTML**, so user input cannot inject markup. Use it instead of `innerHTML`.

**3. `web/app.js`** (319 lines). The coordinator. Read two functions:

- **`act(method, path, body)`** — every user action goes through here. Sends the request, takes the state that comes back, redraws.
- **`render()`** — redraws *everything* from the current state.

Yes, it redraws the whole screen on every change. That is deliberate, and at this size it is instant. **Do not optimize it.**

**4. The components.** Small, one job each:

| File | Job |
|---|---|
| `chart.js` | Draws the SVG price chart |
| `order-ticket.js` | The buy/sell form, and the 1.5s Confirm lock |
| `safety-net.js` | The "you are down 8%" modal |
| `money-flow.js` | The plain-English sentence under the chart |
| `hint.js` | The little (i) explanation popups |
| `tier-picker.js` | The welcome card and tier preview |

**5. `web/tokens.css`** — the design system. **Use the variables, never a raw hex.**

Two surfaces, and the split carries meaning: warm `--paper-*` is the room where the coach lives; dark `--ink-*` is the market stage. Text colors are paired to their background — `--text` on paper, `--text-on-ink` on the stage. Every pair is checked for readability, and the ratio is in a comment next to it.

### Python you will meet (and its JS equivalent)

You know Python, but this code is terse. These five patterns cover most of it:

```python
next(t for t in TIERS if t["id"] == tier)          # Python: find first match
TIERS.find(t => t.id === tier)                     // JavaScript
# Difference: Python THROWS if nothing matches; JS gives you undefined.

[p["qty"] for p in positions]                      # Python: list comprehension
positions.map(p => p.qty)                          // JavaScript

session.cash, session.realized = cash, total       # two assignments on one line

f"Day {day}: bought {qty} shares"                  # Python f-string
`Day ${day}: bought ${qty} shares`                 // JavaScript template literal

@app.post("/api/orders")                           # decorator: registers the route below it
app.post('/api/orders', handler)                   // Express equivalent
```

`dict.get(key)` returns `None` if missing; `dict[key]` throws.

### Your first task

Change something the user reads, and watch a test catch you.

1. Open `web/coach.json`. Change any `"next"` line under `controls`.
2. `python dev.py test` — green. Refresh the browser, no restart needed.
3. Now **deliberately break a rule**: put the word `just ` in that same line.
4. `python dev.py test` — **it fails**, naming your file, the rule, and the word.
5. Undo it.

That round trip — edit, test, see the guardrail fire — is the whole workflow here.

---

## Why the tests care about wording

Some tests check the *words*, not the code. The build fails if:

- an "I don't know" / skip / unsure option appears anywhere
- any scoring field appears anywhere
- a named loss has no next step beside it
- a drawdown scene has no recovery scene after it
- **any dollar figure drifts from what the fixture actually produces**

That last one matters most. The coach quotes exact numbers on screen. If someone regenerates the market data those numbers move, and the demo breaks in front of judges. Now it breaks in CI instead.

**If a test complains about your sentence, it is doing its job. Fix the sentence, not the test.**

---

## Five things that will surprise you

1. **There is one global session.** `SESSION` is a module-level variable. Two people sharing a server share a session. Fine for a demo, wrong for production, and known.
2. **The server tells the browser when it restarted.** `BOOT_ID` changes on every start. If the browser sees a new one and has a saved action log, it replays the log to rebuild the session. The simulation is deterministic, so it comes back identical.
3. **Fast-forward moves one day at a time**, even when you ask for 30, so it can stop the instant a trade fills or a warning fires.
4. **Never hand-edit `fixtures/`.** They are generated. Change `scripts/build_fixtures.py`, then `python dev.py fixtures`.
5. **No internet, ever.** No CDN, no web fonts. A browser test fails the build if anything tries to load from the network, because the demo runs with Wi-Fi off.

---

## Before you commit

```bash
python dev.py check
```

Tests, fixtures, and the browser run. If all three pass, commit on a branch — never straight to `main`.

## Where to go next

| You want | Read |
|---|---|
| Every API route and response shape | [API.md](API.md) |
| The story, characters, endings | [STORY.md](STORY.md) |
| What we are building and why | [docs/SPEC_3.md](docs/SPEC_3.md) |
| The full user flow, act by act | [docs/WORKFLOW.md](docs/WORKFLOW.md) |
