# API reference

Everything the frontend needs to talk to the server.

**19 routes total: 17 live + 2 stubs** (a "stub" is a route that exists and responds, but isn't wired into anything real yet). This count is frozen by a test called `test_route_table_is_frozen_at_17_live_plus_2_stubs` — if you add a route, you need to update that test on purpose, so nobody adds one by accident.

## Getting it running

```bash
python -m venv .venv && .venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r server/requirements.txt
python -m uvicorn server.main:app --port 8000
```

`http://127.0.0.1:8000` serves both the API and the page. **Change a `.js`/`.css`/`.json` file → just refresh your browser. Change a `.py` file → restart the server.**

---

## The one rule

**Every route that changes something returns the complete new state.** Throw away what you had on the frontend and re-render from what comes back. Never compute a price, a fill, a profit/loss number, or a story ending in the browser — that math belongs on the server.

```js
const res = await fetch('/api/orders', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ symbol: 'NVX', side: 'BUY', qty: 2, as_of: 20 }),
});
const data = await res.json();
if (!res.ok) return showError(data.message);   // every error has a plain-English message
render(data.state);                             // redraw from the WHOLE world the server sent back
```

---

## Two account sizes, depending on which company you pick

Each symbol (ticker) is tied to a specific starting cash amount. **Always read `state.starting_cash` from the response — never hardcode a number in your code.**

| Symbol | Company | Starting cash | Entry price | What happens | Use for |
|---|---|---|---|---|---|
| **NVX** | Novexa Systems | **$100.00** | $21.00 | dips −10%, ends **+25%** | **the story / the demo** |
| HLX | Helix Devices | $10,000.00 | $168.00 | −22.7% drawdown | the tier demo |
| BRW | Brightwater Coffee | $10,000.00 | $63.51 | slow, ends +3.9% | patience, gently |
| BRD | Broadline 500 Fund | $10,000.00 | $492.00 | shallow dips | what an index fund does |
| KIN | Kinetic Apparel | $10,000.00 | $99.17 | −14% mid dip | choppy price action |
| VLT | Voltaic Motors | $10,000.00 | $262.00 | −27.3% | how bad it can get |

**Every company here is fictional.** The prices are synthetic (computer-generated), and every fixture file carries `"synthetic": true`. Nothing refers to a real listed company, so there's no number a judge could fact-check against a real market.

---

## Trading routes

| # | Route | Body / query | Returns |
|---|---|---|---|
| 1 | `GET /api/state` | — | the full snapshot |
| 2 | `POST /api/onboarding` | `{experience: "new"\|"experienced", symbol?}` | `{state}` |
| 3 | `POST /api/advance` | `{n: 1..30}` | `{advanced, events[], state}` — stops early if a fill happens or a prompt appears |
| 4 | `POST /api/orders` | `{symbol, side, type?, qty, limit_price?, stop_price?, as_of?}` | `{order, fills[], state}` |
| 5 | `DELETE /api/orders/{id}` | — | `{order, state}` |
| 6 | `POST /api/safety-net` | `{symbol, decision?: "accept"\|"dismiss", percent?, stop_price?}` | `{order?, state}` |
| 7 | `POST /api/comprehension` | `{check_id, choice}` | `{correct, attempt, explanation, unlocked_tier, state}` |
| 8 | `POST /api/reset` | — | `{state}` — starts a new participant; the QA log is kept |
| 9 | `GET /api/quote` | `?symbol=&as_of=` | `{symbol, as_of, price, bar}` |
| 10 | `GET /api/portfolio` | — | cash, positions, equity, profit/loss, open orders |
| 11 | `GET /api/tiers` | — | `{tiers[], active, unlocked[]}` |
| 12 | `GET /api/qa-log` | — | `{participants, per_check, pitch_line, entries[]}` |

## Story routes

| # | Route | Body / query | Returns |
|---|---|---|---|
| 13 | `GET /api/story` | — | `{act, scene, computed, flags[], wager, acts[]}` |
| 14 | `POST /api/story/start` | `?act_id=act4` | same shape — jumps to that act's first scene |
| 15 | `POST /api/story/advance` | `{scene_id, option_id?}` | same shape — the next scene |
| 16 | `GET /api/story/ending` | — | `{ending, computed, flags[], wager}` |
| 17 | `GET /api/coach` | — | Nia's persona and pop-out copy for 12 controls |

## Stubs (mock mode — not wired into the UI yet)

`GET /api/news`, `GET /api/fundamentals` → `{stub: true, ...}`

---

## The snapshot (`state`)

This object is present on every route that changes something, and on `GET /api/state`. **Every key exists even before onboarding**, with empty defaults — so you can render an empty shell of the page without checking for `null` everywhere.

```jsonc
{
  "boot_id": "a3f1c2d9",      // changes when the server restarts — see the Recovery section below
  "onboarded": true,
  "starting_cash": 100.0,     // READ THIS, don't hardcode
  "symbol": "NVX",
  "symbols": [ { "symbol": "NVX", "name": "...", "blurb": "...", "volatility": "medium" } ],
  "tier": "beginner",
  "tiers_unlocked": ["beginner"],

  "cursor": 20, "day": 21, "total_days": 90, "finished": false,
  "price": 21.0,
  "bars": [ { "day": 1, "o": 18.4, "h": 18.7, "l": 18.3, "c": 18.5 } ],  // only days [0..cursor] — nothing beyond today
  // a "bar" is one day's price data: o = open, h = high, l = low, c = close

  "cash": 58.0, "equity": 100.0, "market_value": 42.0,
  "total_pnl": 0.0, "total_pnl_pct": 0.0,
  "unrealized_pnl": 0.0, "unrealized_pnl_pct": 0.0, "realized_pnl": 0.0,

  "positions": [ { "symbol": "NVX", "qty": 2, "avg_price": 21.0, "price": 21.0,
                   "market_value": 42.0, "unrealized_pnl": 0.0, "unrealized_pnl_pct": 0.0,
                   "protected": false, "stop_price": null } ],
  "open_orders": [], "trades": [],

  "shadow": { "active": false, "kept_qty": 0, "equity": 100.0,
              "delta_vs_you": 0.0, "saved_by_safety_net": 0.0 },

  "prompts": [],              // if non-empty, this BLOCKS /api/advance — show the modal first
  "pending_check": null,
  "events": [ { "seq": 2, "day": 21, "type": "FILL", "message": "Day 21: bought 2 NVX at $21.00." } ],
  "replay_log": [ ... ],      // store this in localStorage — see Recovery
  "fixture_meta": null        // filled in with { max_drawdown_pct, synthetic } only once the replay finishes
}
```

**`bars` only ever contains days `[0..cursor]`.** The response physically can't include tomorrow's price — there's no way to peek ahead, because the server doesn't send it.

---

## Story shape

`GET /api/story` and both of the story `POST` routes return this shape:

```jsonc
{
  "act": "act4",
  "scene": {
    "id": "act4.drop5",
    "speaker": "coach",              // "coach" (Nia) | "vela" | "narrator"
    "stage": "chart.paused",         // chart.autoplay | chart.paused | chart.compare | ticket | minigame:<id>
    "media": null,                   // an opaque slot name, e.g. "slot:int-aftermath" — see below
    "skippable": true,
    "duration_hint_ms": null,
    "lines": ["Alright — it dipped.", "Your 2 shares were worth $42.00..."],
    "loss": "$2.38",                 // whenever this is present, ALWAYS render `next` alongside it
    "next": "That's a paper loss — it isn't real until you decide it is...",
    "facts": { "price": 19.81, "pnl": -2.38 },   // checked against the fixture data by CI, so it can never go stale
    "respond": {
      "type": "choice",              // choice | continue | reflection
      "prompt": "What do you want to do?",
      "options": [
        { "id": "sell", "label": "Sell — take the $2.38 loss", "goto": "act4.chose.sell" },
        { "id": "hold", "label": "Hold — stay in", "goto": "act4.chose.hold" },
        { "id": "more", "label": "Buy 1 more at $19.81", "goto": "act4.chose.more" }
      ]
    }
  },
  "computed": { "equity": 100.0, "equity_pct": 0.0, "cash": 58.0, "trade_count": 1,
                "position_count": 1, "worst_equity_seen": 100.0,
                "vs_wish": -10.0, "vs_bust": 10.0, "start_capital": 100.0 },
  "flags": [],
  "wager": { "wish_line": 110.0, "bust_line": 90.0, "equity": 100.0,
             "above_wish": false, "below_bust": false, "verdict": "open" },
  "acts": ["act4"]
}
```

### Driving the story forward

```js
await fetch('/api/story/start?act_id=act4', { method: 'POST' });   // call once per chapter

// a plain "continue" scene
await post('/api/story/advance', { scene_id: 'act4.open' });

// a choice scene — option_id is REQUIRED, or you'll get a 400 CHOICE_REQUIRED error
await post('/api/story/advance', { scene_id: 'act4.drop5', option_id: 'hold' });
```

If you get `409 STALE_SCENE`, it means your screen is out of date. Re-fetch `GET /api/story` and re-render from that.

### `media` is just an opaque name

The backend never knows what an animation actually looks like — it just passes the slot name through as a string, and the browser decides what to do with it.

```js
const ANIMATIONS = { 'slot:int-aftermath': AftermathSequence };
const Anim = ANIMATIONS[scene.media];          // undefined is fine here — just render nothing
```

**Every interstitial (a between-scenes beat) is `skippable: true`.** Always give the user a way out — a cutscene she can't leave is a dead end.

### Endings

`GET /api/story/ending` decides the ending **on the server**, never in the browser. There are six endings, checked in priority order (first match wins), and they are **deliberately not ranked by how much money you made**:

`hollow_wish` · `wish_granted` · `the_panic` · `untouched_hundred` · `cost_of_certainty` ·
`steady_hand` (the catch-all ending, and the one written to be the best one)

Each ending carries `lines[]` plus `next` (from Vela) and `coach_coda` (from Nia). Render both — Vela is the one judging the outcome, and Nia is the one reframing it.

---

## Errors

Every error comes back as `{"error": CODE, "message": "plain English", ...extra}`. **Show `message` directly to the user** — it's already written in plain English for them, not for you as a developer.

| Status | Codes |
|---|---|
| 400 (bad request) | `INVALID_ORDER`, `UNSUPPORTED_ORDER`, `INSUFFICIENT_FUNDS`, `INSUFFICIENT_SHARES`, `STOP_NOT_BELOW_MARKET`, `SYMBOL_MISMATCH`, `FUTURE_BAR`, `INVALID_CHOICE`, `CHOICE_REQUIRED`, `UNKNOWN_OPTION`, `UNKNOWN_SCENE` |
| 403 (forbidden) | `TIER_LOCKED` — carries `required_tier` |
| 404 (not found) | `UNKNOWN_SYMBOL`, `ORDER_NOT_FOUND`, `NO_POSITION`, `UNKNOWN_CHECK`, `UNKNOWN_ACT` |
| 409 (conflict — the request doesn't match the server's current state) | `NOT_ONBOARDED`, `ALREADY_ONBOARDED`, `REPLAY_FINISHED`, `PROMPT_PENDING`, `STALE_CURSOR`, `STALE_SCENE`, `NO_STORY`, `ORDER_NOT_OPEN`, `ALREADY_PROTECTED`, `CHECK_NOT_AVAILABLE` |
| 422 (validation failed) | `VALIDATION` — `details[]` lists `{field, message}` for each problem |

**`409 PROMPT_PENDING`** is the one you have to handle carefully: it means a position is down 8% and the user has to respond to that before time can move forward. It carries `prompts[]` with every number the modal needs to display.

---

## Recovery after a server restart

```js
const state = await get('/api/state');
const saved = JSON.parse(localStorage.getItem('richher.session.v1') || 'null');
if (!state.onboarded && saved?.log?.length && saved.boot_id !== state.boot_id) {
  for (const step of saved.log) await fetch(step.path, { method: step.method, ... });
}
```

If `boot_id` is different from what you saved, the server restarted — replay the saved log and the session rebuilds itself exactly, because the simulation is deterministic (same inputs always produce the same outputs). If `boot_id` is the *same*, it means someone did an intentional reset — **don't replay the log in that case.**

---

## Design tokens

`web/tokens.css` loads before `index.css`. **Use its variables — never a raw hex color code.**

| Group | Tokens |
|---|---|
| Room | `--paper-0..4` |
| Market stage | `--ink-0..3` |
| Vela | `--vela-0..3`, `--vela-gold`, `--vela-cream` |
| Brand | `--clay`, `--clay-deep`, `--clay-tint`, `--clay-edge` |
| Semantic | `--gain`, `--loss`, `--gain-on-ink`, `--loss-on-ink`, `--cash` |
| Text | `--text`, `--text-2`, `--text-on-ink`(`-2`,`-3`), `--text-on-vela`(`-2`) |
| Scale | `--fs-xs..--fs-display`, `--r-sm/md/lg/pill`, `--s-1..--s-8` |

**There are two visual surfaces:** the warm "paper" colors are the room where Nia (the coach) lives; `--ink-*` is the dark market stage. Text colors are paired to whichever background they sit on — `--text-on-ink` on the dark surface, `--text` on paper. Every pairing has a contrast ratio of at least 4.5:1 (readable for people with low vision); the exact ratios are noted in the code comments.

**Offline access is enforced by our tests.** No CDN, no web fonts, no requests to outside servers — `scripts/e2e-browser.mjs` fails the build if it detects any of those, because the venue demo runs with Wi-Fi off.

---

## Verify before you push

```bash
python -m pytest                          # 197 tests
python scripts/build_fixtures.py --check  # confirms fixtures match a fresh build
node scripts/e2e-browser.mjs              # 59 browser checks (needs Edge or Chrome, and ports 8000 + 5500 free)
```

The content checks are strict on purpose. They fail the build on: an "I don't know" option anywhere, any kind of scoring field, a mentioned loss with no next step alongside it, a scene that's a dead end, a `goto` pointing nowhere, or any dollar figure that doesn't match what the fixture data actually produces. If a test complains about your sentence, it's doing its job.
