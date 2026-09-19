# API reference

Everything the frontend needs. **19 routes: 17 live + 2 stubs.** Frozen by
`test_route_table_is_frozen_at_17_live_plus_2_stubs` — adding one means updating that test
on purpose.

```bash
python -m venv .venv && .venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r server/requirements.txt
python -m uvicorn server.main:app --port 8000
```

`http://127.0.0.1:8000` serves both the API and the page. **Change a `.js`/`.css`/`.json` →
refresh. Change a `.py` → restart.**

---

## The one rule

**Every mutating route returns the complete new state.** Throw yours away and re-render from
what comes back. Never compute a price, a fill, a P&L, or an ending in the browser.

```js
const res = await fetch('/api/orders', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ symbol: 'NVX', side: 'BUY', qty: 2, as_of: 20 }),
});
const data = await res.json();
if (!res.ok) return showError(data.message);   // every error has a plain-English message
render(data.state);                             // the WHOLE world
```

---

## Two accounts, by fixture

Each symbol declares the practice account it is priced for. **Read `state.starting_cash`,
never hardcode a number.**

| Symbol | Company | Starting cash | Entry | Arc | Use for |
|---|---|---|---|---|---|
| **NVX** | Novexa Systems | **$100.00** | $21.00 | dips −10%, ends **+25%** | **the story / the demo** |
| HLX | Helix Devices | $10,000.00 | $168.00 | −22.7% drawdown | the tier demo |
| BRW | Brightwater Coffee | $10,000.00 | $63.51 | slow, ends +3.9% | patience, gently |
| BRD | Broadline 500 Fund | $10,000.00 | $492.00 | shallow dips | what an index does |
| KIN | Kinetic Apparel | $10,000.00 | $99.17 | −14% mid dip | choppy |
| VLT | Voltaic Motors | $10,000.00 | $262.00 | −27.3% | how bad it gets |

**Every company is fictional.** The prices are synthetic and every fixture carries
`"synthetic": true`. Nothing here refers to a real listed company, so there is no number a
judge can fact-check against a real market.

---

## Trading routes

| # | Route | Body / query | Returns |
|---|---|---|---|
| 1 | `GET /api/state` | — | the full snapshot |
| 2 | `POST /api/onboarding` | `{experience: "new"\|"experienced", symbol?}` | `{state}` |
| 3 | `POST /api/advance` | `{n: 1..30}` | `{advanced, events[], state}` — stops early on a fill or a prompt |
| 4 | `POST /api/orders` | `{symbol, side, type?, qty, limit_price?, stop_price?, as_of?}` | `{order, fills[], state}` |
| 5 | `DELETE /api/orders/{id}` | — | `{order, state}` |
| 6 | `POST /api/safety-net` | `{symbol, decision?: "accept"\|"dismiss", percent?, stop_price?}` | `{order?, state}` |
| 7 | `POST /api/comprehension` | `{check_id, choice}` | `{correct, attempt, explanation, unlocked_tier, state}` |
| 8 | `POST /api/reset` | — | `{state}` — new participant, QA log survives |
| 9 | `GET /api/quote` | `?symbol=&as_of=` | `{symbol, as_of, price, bar}` |
| 10 | `GET /api/portfolio` | — | cash, positions, equity, P&L, open orders |
| 11 | `GET /api/tiers` | — | `{tiers[], active, unlocked[]}` |
| 12 | `GET /api/qa-log` | — | `{participants, per_check, pitch_line, entries[]}` |

## Story routes

| # | Route | Body / query | Returns |
|---|---|---|---|
| 13 | `GET /api/story` | — | `{act, scene, computed, flags[], wager, acts[]}` |
| 14 | `POST /api/story/start` | `?act_id=act4` | same shape — jumps to the act's first scene |
| 15 | `POST /api/story/advance` | `{scene_id, option_id?}` | same shape — the next scene |
| 16 | `GET /api/story/ending` | — | `{ending, computed, flags[], wager}` |
| 17 | `GET /api/coach` | — | Nia's persona + pop-out copy for 12 controls |

## Stubs (mock mode, not wired into the UI)

`GET /api/news`, `GET /api/fundamentals` → `{stub: true, ...}`

---

## The snapshot (`state`)

Present on every mutating response and on `GET /api/state`. **Every key exists before
onboarding**, with empty defaults, so you can render a shell without null-checking.

```jsonc
{
  "boot_id": "a3f1c2d9",      // changes on server restart — see Recovery
  "onboarded": true,
  "starting_cash": 100.0,     // READ THIS, don't hardcode
  "symbol": "NVX",
  "symbols": [ { "symbol": "NVX", "name": "...", "blurb": "...", "volatility": "medium" } ],
  "tier": "beginner",
  "tiers_unlocked": ["beginner"],

  "cursor": 20, "day": 21, "total_days": 90, "finished": false,
  "price": 21.0,
  "bars": [ { "day": 1, "o": 18.4, "h": 18.7, "l": 18.3, "c": 18.5 } ],  // [0..cursor] ONLY

  "cash": 58.0, "equity": 100.0, "market_value": 42.0,
  "total_pnl": 0.0, "total_pnl_pct": 0.0,
  "unrealized_pnl": 0.0, "unrealized_pnl_pct": 0.0, "realized_pnl": 0.0,

  "positions": [ { "symbol": "NVX", "qty": 2, "avg_price": 21.0, "price": 21.0,
                   "market_value": 42.0, "unrealized_pnl": 0.0, "unrealized_pnl_pct": 0.0,
                   "protected": false, "stop_price": null } ],
  "open_orders": [], "trades": [],

  "shadow": { "active": false, "kept_qty": 0, "equity": 100.0,
              "delta_vs_you": 0.0, "saved_by_safety_net": 0.0 },

  "prompts": [],              // non-empty BLOCKS /api/advance — show the modal
  "pending_check": null,
  "events": [ { "seq": 2, "day": 21, "type": "FILL", "message": "Day 21: bought 2 NVX at $21.00." } ],
  "replay_log": [ ... ],      // store in localStorage — see Recovery
  "fixture_meta": null        // { max_drawdown_pct, synthetic } only once finished
}
```

**`bars` is sliced to `[0..cursor]`.** The response physically cannot contain tomorrow's
price. Don't try to look ahead; it isn't there.

---

## Story shape

`GET /api/story` and both story POSTs return:

```jsonc
{
  "act": "act4",
  "scene": {
    "id": "act4.drop5",
    "speaker": "coach",              // "coach" (Nia) | "vela" | "narrator"
    "stage": "chart.paused",         // chart.autoplay | chart.paused | chart.compare | ticket | minigame:<id>
    "media": null,                   // OPAQUE SLOT NAME, e.g. "slot:int-aftermath" — see below
    "skippable": true,
    "duration_hint_ms": null,
    "lines": ["Alright — it dipped.", "Your 2 shares were worth $42.00..."],
    "loss": "$2.38",                 // when present, ALWAYS render `next` with it
    "next": "That's a paper loss — it isn't real until you decide it is...",
    "facts": { "price": 19.81, "pnl": -2.38 },   // fact-checked against the fixture by CI
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

### Driving the story

```js
await fetch('/api/story/start?act_id=act4', { method: 'POST' });   // once per chapter

// continue scene
await post('/api/story/advance', { scene_id: 'act4.open' });

// choice scene — option_id is REQUIRED or you get 400 CHOICE_REQUIRED
await post('/api/story/advance', { scene_id: 'act4.drop5', option_id: 'hold' });
```

`409 STALE_SCENE` means your screen is behind. Re-fetch `GET /api/story` and re-render.

### `media` is an opaque slot

The backend never knows what an animation looks like. It passes the string through.

```js
const ANIMATIONS = { 'slot:int-aftermath': AftermathSequence };
const Anim = ANIMATIONS[scene.media];          // undefined is fine — render nothing
```

**Every interstitial is `skippable: true`.** Always give her a way out; a cutscene she can't
leave is a dead end.

### Endings

`GET /api/story/ending` decides **server-side**, never in the browser. Six endings, evaluated
in priority order, **deliberately not ranked by money**:

`hollow_wish` · `wish_granted` · `the_panic` · `untouched_hundred` · `cost_of_certainty` ·
`steady_hand` (the catch-all, and the one written as the best)

Each carries `lines[]` + `next` (Vela) and `coach_coda` (Nia). Render both — Vela judges,
Nia reframes.

---

## Errors

Every error is `{"error": CODE, "message": "plain English", ...extra}`. **Show `message`
directly** — it is written for the user, not for you.

| Status | Codes |
|---|---|
| 400 | `INVALID_ORDER`, `UNSUPPORTED_ORDER`, `INSUFFICIENT_FUNDS`, `INSUFFICIENT_SHARES`, `STOP_NOT_BELOW_MARKET`, `SYMBOL_MISMATCH`, `FUTURE_BAR`, `INVALID_CHOICE`, `CHOICE_REQUIRED`, `UNKNOWN_OPTION`, `UNKNOWN_SCENE` |
| 403 | `TIER_LOCKED` — carries `required_tier` |
| 404 | `UNKNOWN_SYMBOL`, `ORDER_NOT_FOUND`, `NO_POSITION`, `UNKNOWN_CHECK`, `UNKNOWN_ACT` |
| 409 | `NOT_ONBOARDED`, `ALREADY_ONBOARDED`, `REPLAY_FINISHED`, `PROMPT_PENDING`, `STALE_CURSOR`, `STALE_SCENE`, `NO_STORY`, `ORDER_NOT_OPEN`, `ALREADY_PROTECTED`, `CHECK_NOT_AVAILABLE` |
| 422 | `VALIDATION` — `details[]` lists `{field, message}` |

**`409 PROMPT_PENDING`** is the one you must handle: a position is down 8% and she has to
answer before time moves. It carries `prompts[]` with every number the modal needs.

---

## Recovery after a restart

```js
const state = await get('/api/state');
const saved = JSON.parse(localStorage.getItem('richher.session.v1') || 'null');
if (!state.onboarded && saved?.log?.length && saved.boot_id !== state.boot_id) {
  for (const step of saved.log) await fetch(step.path, { method: step.method, ... });
}
```

`boot_id` differs → the server restarted → replay the log, the session rebuilds exactly
(the sim is deterministic). Same `boot_id` → intentional reset → **do not resurrect it**.

---

## Design tokens

`web/tokens.css` loads before `index.css`. **Use the variables; never a raw hex.**

| Group | Tokens |
|---|---|
| Room | `--paper-0..4` |
| Market stage | `--ink-0..3` |
| Vela | `--vela-0..3`, `--vela-gold`, `--vela-cream` |
| Brand | `--clay`, `--clay-deep`, `--clay-tint`, `--clay-edge` |
| Semantic | `--gain`, `--loss`, `--gain-on-ink`, `--loss-on-ink`, `--cash` |
| Text | `--text`, `--text-2`, `--text-on-ink`(`-2`,`-3`), `--text-on-vela`(`-2`) |
| Scale | `--fs-xs..--fs-display`, `--r-sm/md/lg/pill`, `--s-1..--s-8` |

**Two surfaces:** warm paper is the room where Nia lives; `--ink-*` is the market stage.
Text colors are paired to their ground — `--text-on-ink` on ink, `--text` on paper. Every
pair is verified ≥ 4.5:1; the ratios are in the comments.

**Offline is enforced.** No CDN, no web fonts, no remote requests —
`scripts/e2e-browser.mjs` fails the build on any of them, and the venue demo runs with
Wi-Fi off.

---

## Verify before you push

```bash
python -m pytest                          # 192 tests
python scripts/build_fixtures.py --check  # fixtures match a fresh build
node scripts/e2e-browser.mjs              # 59 browser checks (needs Edge/Chrome, ports 8000+5500 free)
```

The content lints are strict on purpose: they fail on an "I don't know" option, any scoring
field, a loss with no next step, a dead-end scene, a dangling `goto`, and **any dollar
figure that drifts from what the fixture produces.** If a test complains about your
sentence, it is doing its job.
