# Spec 3 (draft): The Coached Beginner Track

**Status:** input to SPEC.md v4. Supersedes the tier/safety-net framing of SPEC.md v3.0.
**Scope:** the beginner track only. Intermediate and advanced are stubbed, not built.

---

## 0. The thesis correction (read this first)

The brain dump contains a better thesis than the one the repo is currently built on, and the two
contradict each other.

| | Old (SPEC v3.0) | New |
|---|---|---|
| Thesis | "Teach them how not to lose it." | Hesitation, not ignorance, is the barrier. |
| Design rule | Downside first, always. | No wrong answers, no escape hatch, no score. |
| Enforced by | `test_content.py` fails the build if a hint does not lead with a loss. | *(to be written)* |

**These cannot both be true.** If hesitation is the barrier, then leading every single interaction
with what she could lose *manufactures the hesitation the product exists to remove*. The repo
currently has an automated test enforcing the thing the research says causes the problem.

**Resolution — the new principle set:**

| # | Principle | Enforced by |
|---|---|---|
| 1 | **No dead ends.** Every question is answerable. There is no "I don't know" option, ever. | Content lint: any question with a skip/DK/unsure option fails the build. |
| 2 | **No score.** Nothing is graded, ranked, or subtracted. Progress only accumulates. | No score field exists in the state model. |
| 3 | **Honest, and actionable.** Losses are named in plain dollars and always paired with a next action. Never a loss on its own. | Content lint: every `loss` field requires a sibling `next` field. |
| 4 | **Real data, honestly labelled.** Real historical bars from a real company, with the ticker and dates hidden so the ending cannot be looked up. Never presented as live. | Fixture metadata carries `source: historical`, `ticker_hidden: true`. |
| 5 | **One new thing at a time.** Never more than three new controls per chapter. | Chapter manifest caps `new_controls`. |
| 6 | **Never end on the low.** No scene closes on a drawdown without showing what came next. | Scene lint: a scene with `drawdown: true` requires a `recovery_shown` scene after it. |

Principle 1 is the product. Everything else serves it.

---

## 1. Why this is for women (the answer to the judge's question)

Nothing in a coached trading tutorial is inherently female-specific, and "we used female avatars"
is not an answer. The real answer is in the research: the product removes the four conditions that
produce the confidence gap.

| Condition that drives opt-out | What we remove |
|---|---|
| An "I don't know" escape hatch | Removed entirely (Principle 1) |
| Visible scoring / evaluation | No score anywhere (Principle 2) |
| Time pressure | No timers on any decision |
| Jargon-gated entry | Coach introduces every term before any control that uses it |

**Everyone benefits; women benefit most, because they are the ones the escape hatch was costing.**
That is slide 2 of the deck, and it is a stronger claim than a demographic assertion.

### The statistic — unresolved, and load-bearing

The cited figures ("63% of women select don't know vs 43% of men... correct answers rise 14% when
the option is removed") appear to trace to the *Fearless Woman* line of research on financial
literacy and stock market participation (Bucher-Koenen, Alessie, Lusardi & van Rooij, NBER). The
broad finding — that women disproportionately answer "do not know," and that a large share of them
answer correctly when that option is removed — is well established.

**The exact numbers above are not verified.** Do not put them on a slide until V2 has the primary
source open and the figures match. Citing a wrong statistic in a pitch about women's financial
literacy is the most damaging own-goal available in this room. Owner: V2. Deadline: before any
deck draft.

---

## 2. Loophole audit

### Contradictions

| # | Loophole | Fix (as a design decision) |
|---|---|---|
| L1 | Downside-first vs. hesitation-is-the-barrier. | Principle 3 replaces Principle 1 of v3.0. Rewrite the content lint. |
| L2 | "Historical data to pretend it's live" vs. v3.0's "prices are synthetic and labelled." | **DECIDED: stay synthetic** (AJ, this session). The fixtures are already built, deterministic and seed-searched, and there is no licensing question. Keep the `"synthetic": true` label and the honest framing — "these prices are made up, the behaviour is not." Do **not** pretend it is live. See section 2.5 for the gap this leaves. |
| L3 | A 50% drop vs. "beginners must not be overloaded." | Sequence drawdowns: -5% then -12% then -25%+ only in an optional module, recovery always shown in the same scene (Principle 6). A 50% first loss teaches "markets are terrifying," which is the opposite of the goal. |
| L4 | "The coach explains each button" vs. TradingView's ~40 on-screen controls. | **The coach pops out from the control itself** (section 5.1), so explanation is on-demand rather than a 20-minute front-loaded tour. Combined with progressive disclosure: the chart starts with a line and two axes, three new controls per chapter maximum. Auto-pop once on unlock, on-demand forever after. |
| L5 | In-session tier unlocking (v3.0) vs. "just build beginner." | Tiers become **entry-point difficulty selection**, not in-session progression. Within beginner, progression is by **chapter**. |

### Missing pieces

| # | Gap | Fix |
|---|---|---|
| M1 | No content model for the coach. A 13-minute coached tutorial is 150-300 dialogue beats and nobody owns it. | Define `scenes.json` (schema in section 5) in week 1. Owner: V1. Cap the beginner track at 60 nodes. |
| M2 | "She responds" — how? Free text needs an LLM, which needs network, which kills the offline demo. | Multiple choice for everything evaluated, **plus one ungraded free-text reflection box per act** that is never read by the system. She responds; nothing grades her. |
| M3 | The welcome screen collects a name, but the server has one global in-memory session. Two users collide; a restart erases her. | Session keyed by a `player_id` in localStorage. ~40 lines against the existing `SESSION` global, and it also fixes the shared-session limitation already flagged in SPEC v3.0 section 13. |
| M4 | "Mini games" — which, teaching what, won how, built by whom? | Exactly four, defined in section 4, each capped at 60 seconds and mapped to one misconception. |
| M5 | No avatar art pipeline; the reference set is commercial. | Open-licensed avatars rendered as inline SVG (no network). Owner: F. |
| M6 | The coach has no name, face, or bio. An unnamed coach is a UI element; a named one is a relationship. | Name her, write a one-paragraph bio, give her a Personas screen (screenshot 2 pattern). |
| M7 | No success metric matching the new thesis. The old metric measures comprehension; the thesis is about confidence. | Confidence self-rating 1-5 before and after (section 6). Trivially instrumentable, and it *is* the pitch line. |

### Feasibility

| # | Risk | Fix |
|---|---|---|
| F1 | TradingView-grade charting is a multi-day build on its own. | Use **Lightweight Charts** — TradingView's own open-source library, Apache-2.0, ~45KB, vendorable as one file for offline. Literal TradingView look, one day of work. Breaks the repo's current "zero dependencies" rule; worth it, and offline survives because it is vendored. |
| F2 | The existing repo is roughly 60% wrong-shaped for this. | Honest accounting in section 7: the engine survives, the experience layer is a rewrite. Say so out loud so nobody plans a refactor and discovers a rebuild. |
| F3 | "Minute by minute" replay — a -5% move takes days in real markets, and minute bars over a real drawdown are tens of thousands of rows. | **Daily bars auto-played at ~200ms each.** A 90-day arc runs in 18 seconds and *feels* live. This is an auto-play timer on the existing `advance`, not a new data model. |

### Strategic

| # | Blind spot | Fix |
|---|---|---|
| S1 | The reference UI has a **Score** button. | Do not copy it. Scoring reintroduces the evaluation anxiety the thesis targets. Replace with a **"What you've learned"** journal that only accumulates. |
| S2 | The screenshots are a copyrighted commercial product (McGraw Hill). | Take the *pattern* — persona intro, dialogue bubble + stage, Continue-driven pacing — never the skin, chrome, or assets. |
| S3 | Investopedia Simulator, Stock Trainer, Webull paper trading and Robinhood Learn all exist. | The wedge: none of them is a *coached narrative for hesitant beginners*. They all assume you already decided to trade. Have this line ready. |

### Execution

| # | Risk |
|---|---|
| E1 | V2 is still unassigned, and the statistic — now load-bearing for the entire thesis — sits there. |
| E2 | Dialogue writing has no owner and no word budget. |
| E3 | Avatar and stage art has no owner. |

---

## 2.5 BLOCKER: every fixture only ever loses money

Measured across all five shipped fixtures, from each one's own `start_cursor` entry:

| Symbol | Entry | Peak | Trough | Ends | Ever reaches +5%? |
|---|---|---|---|---|---|
| HLX | $168.00 (bar 40) | +2.38% | **-20.86%** | -5.95% | **No** |
| BRW | $63.51 (bar 30) | +3.92% | -0.52% | **+3.92%** | **No** |
| KIN | $99.17 (bar 25) | 0.00% | -13.95% | -4.20% | **No** |
| BRD | $492.00 (bar 30) | +3.21% | -1.63% | +2.64% | **No** |
| VLT | $262.00 (bar 15) | +1.85% | **-27.29%** | -17.94% | **No** |

**Not one of the five ever gains 5%. Three of the five end down. The best available outcome in the
entire product is +3.92%.**

This is not a bug — it is the old thesis, fossilised. The fixtures were seed-searched to *guarantee
a drawdown*, because v3.0 existed to teach loss. Under the new thesis it is actively harmful: a
beginner simulator in which **every possible outcome is a loss** teaches "investing loses money,"
which is the strongest imaginable reinforcement of the hesitation the product exists to remove.

It also means **the "+5% increase" scenario from the brain dump cannot be built on current data at
all.**

**Fix (B, before the dry run):** generate one more fixture, seed-searched for the opposite shape —
a -5% dip early, recovery through breakeven, and a finish at **+12% to +18%**. Same generator, same
`--check` discipline, one new anchor set. Until it exists, Act 4 runs on HLX and the upside beat is
cut, not faked.

**Interim mitigation, available today at zero cost:** HLX ends at **-5.95%** and BRW ends at
**+3.92%**, and both are already built. That contrast *is* diversification, demonstrated with
shipped data. Use it as the Act 5 diversification beat: one exciting stock that lost her money, one
boring one that did not. That was always the lesson, and the fixtures already prove it.

---

## 3. Proposed user flow

Full playthrough ~13 minutes. The 2:15 demo is a cut of it (section 6).

### Act 0 — Entry (0:30)

1. **Welcome.** Name (25 char max, live counter) + avatar grid (12, arrow-key navigable, Enter to
   select) + Continue. No email, no password, no account. `player_id` to localStorage.
2. **Meet the cast** (screenshot 2 pattern). The coach, with a name and a one-paragraph bio. Your
   $10,000 in practice dollars, stated plainly as pretend. One sentence on the data rule: *"These
   are real prices from a real company. We've hidden which one, so you can't look up the ending."*
3. **Confidence check (pre).** *"Before we start — how confident do you feel about investing?"*
   1-5 slider. No right answer. The first thing the product does is ask her opinion, not test her.
   This sets the tone, and it is the baseline for the only metric that matters.

### Act 1 — What is a stock? (2:00) — Chapter 1

4. Coach: a stock is a slice of a company. One concrete company, no tickers yet.
5. **Mini-game 1 — "Own a slice."** She picks how much of a company she wants; the app shows what
   that costs. Teaches share = fractional ownership, price = cost of one slice. 45s.
6. Coach: prices move because people buy and sell. Three lines, maximum.
7. **Mini-game 2 — "Set the price."** A two-sided order-book toy: she drags buyers and sellers,
   the price moves. 45s. *This is the highest-value mini-game in the product* — it kills the number
   one beginner misconception, that the company sets the price.

### Act 2 — Reading the chart (2:00) — Chapter 2

8. The chart appears for the first time: **a line and two axes, nothing else.** Coach names them —
   time across, price up.
9. Three controls unlock: timeframe, crosshair/tooltip, candlestick toggle. Each **auto-pops the
   coach once** as it appears (section 5.1), then she steps back and the badge remains. Never a
   fourth control in this chapter.
10. **Mini-game 3 — "Which way did it go?"** Four chart snippets, she picks the one that ended
    higher. Instant feedback, no score. Chart literacy in 30s.

### Act 3 — Your first trade (3:00) — Chapter 3

11. Symbol list (5 curated, real-but-anonymised). Coach: *"Pick one. There's no wrong pick."*
12. **Mini-game 4 — symbol matching.** Placed *here* deliberately, as a fluency beat and a
    palate-cleanser — **not** as the opening gate. Matching tickers to names teaches vocabulary,
    which is the thing that *looks* like the barrier but is not. Leading with it teaches her that
    the barrier is memorisation.
13. Order ticket. Coach explains a market order in two lines. She buys.
14. **The fill scene.** Coach narrates in dollars, not jargon: *"You own 10 slices of this company.
    You spent $1,680. You have $8,320 left."*
15. **Reflection box** (free text, never graded, never read by the system): *"How did that feel?"*
    Stored locally, shown back to her in her journal at the end.

### Act 4 — The market moves (4:00) — Chapter 4, the core

16. **Auto-play.** The chart animates forward at ~200ms per bar. The coach is silent. Let it breathe.
17. **Scenario A: -5%.** Auto-pause. Coach names the dollar amount, calmly. Then the question:

    > Your $1,680 is now $1,596. What do you want to do?
    > **[Sell — take the $84 loss]**  **[Hold — stay in]**  **[Buy more at the lower price]**

    No "I don't know." No timer. No score. Every option gets a respectful explanation.
18. **Consequence + counterfactual.** She sees what her choice did *and* what the other two would
    have done, side by side. The repo's `shadow_delta()` already computes exactly this — reuse it.
    Honest in both directions, including when holding was the wrong call.
19. **Scenario B: +5%.** Same three-option structure. Teaches that the same framework applies on the
    way up, and that selling winners early has a cost too.
20. **Scenario C: the deep drop (-20 to -30%).** The most important line in the product lands here:
    *"This is the part where most people sell and never come back. Let's look at what happened next."*
    Then show the recovery. **Never end on the low** (Principle 6).

### Act 5 — The lesson lands (2:00) — Chapter 5

21. Buy-and-hold vs. picking, diversification, emotions, when to exit — each as **one dialogue beat
    attached to something she already did**, never as a lecture. *"Remember when it dropped 5% and
    you held? That's what patience costs, and what it pays."*
22. **The diversification beat — the closing move of the whole product.** This is the exact concept
    where the research says women answer "don't know" most. So: ask it **with no "I don't know"
    option**, and after she answers, show her the statistic.

    > *"Most women say they don't know this one. When you take away the option to say 'I don't
    > know,' they get it right just as often as men. You just did."*

    This makes the thesis **experiential instead of a slide**. It is the demo's closing beat and the
    single best moment in the product.
23. **Confidence check (post).** Same 1-5 slider. Show her the delta. That is the metric and the
    pitch line in one move.
24. **Her journal.** Everything she learned, her own reflection notes, her trades. Downloadable.
    Nothing scored, nothing subtracted.

### Act 6 — Exit

25. "You're ready for Intermediate" card — stubbed. The architecture story without the build.
26. Optional bridge: one screen on what opening a real brokerage account looks like. No affiliate
    links. No advice.

---

## 4. The four mini-games

| # | Name | Kills this misconception | Where | Cap |
|---|---|---|---|---|
| 1 | Own a slice | "A share is an abstract financial instrument" | Act 1 | 45s |
| 2 | Set the price | "The company decides the price" | Act 1 | 45s |
| 3 | Which way did it go? | "Charts are for experts" | Act 2 | 30s |
| 4 | Symbol match | (fluency beat, not a concept) | Act 3 | 45s |

Every mini-game: no score, no timer, no fail state. Wrong answers get an explanation and another go.

---

## 5. Screen architecture

Three zones, identical in every scene, mapping the reference layout with the stock photo replaced by
an interactive stage.

```
+----------------------------------------------------------------+
| Product name      * * o o o  (chapter dots)          ?     [ ]  |  <- NO score
+----------------------+-----------------------------------------+
|  [avatar chips]      |                                         |
|  Coach Name          |              STAGE                      |
|  +----------------+  |   chart | mini-game | order ticket      |
|  | dialogue, with |  |         one thing at a time             |
|  | her name in it |  |                                         |
|  +----------------+  |  (Lightweight Charts, TradingView look) |
|    [ Continue ]      |                                         |
|  or [A] [B] [C]      |                                         |
+----------------------+-----------------------------------------+
|  Cash $8,320   |   10 shares   |   -$84 today                   |  <- once she owns something
+----------------------------------------------------------------+
```

### 5.1 The coach pop-out (the core interaction)

The coach is **not** a fixed left panel. She is a component that anchors to whatever is being
explained. Two modes:

| Mode | When | Looks like |
|---|---|---|
| **Narrating** | Story beats, scenarios, chapter transitions | Anchored in the left rail, full bubble, Continue / choice buttons |
| **Popped out** | Explaining one control | A small bubble anchored to that control, with a tail pointing at it. Non-modal: the rest of the screen stays live. |

**Every interactive element carries a coach id.** This is already the pattern in the current
`hint.js` (`data-hint="<actionId>"` plus `attachHintButtons`) — keep the mechanism, replace the copy
model and the visual.

```html
<button data-coach="chart.timeframe">1D</button>
<button data-coach="ticket.buy">Buy</button>
<select data-coach="ticket.qty">...</select>
```

**Trigger rules:**

1. **First time a control appears, the coach pops out automatically, once.** She explains it, the
   bubble stays until dismissed or until the control is used. This satisfies "every button is
   explained" without a front-loaded tour.
2. **After that, on demand.** Every coached control keeps a small coach badge. Tap it, she comes
   back. She never nags.
3. **Never hover-only.** Hover is unreachable on touch and invisible to keyboards. The badge is a
   real focusable button; the pop-out is reachable by keyboard and announced to screen readers
   (`aria-describedby` on the control, `role="tooltip"` on the bubble).
4. **Never blocking.** The pop-out is a popover, not a modal. She can ignore it and keep going.
   Escape closes it. This matters: a modal explanation of a button is a dead end, and dead ends are
   Principle 1.
5. **One at a time.** Opening a pop-out closes any other. The narrating bubble dims but stays.

**Why this is the right call:** it is what makes the whole thing scale. Without it you either
front-load a 20-minute tour nobody finishes, or you ship unexplained controls. With it, the product
can expose as much of a TradingView-like surface as you want, because nothing is ever unexplained
*and* nothing is ever explained before it matters. It also collapses the Act 2 chart tutorial from a
scripted sequence into three auto-pops, which buys back roughly a minute of demo time.

**Content cost:** one short entry per control, 2-3 sentences. Budget ~25 controls for the beginner
build = ~25 entries. That is a `coach.json` file, separate from `scenes.json`, and it is V1's second
deliverable after Act 4.

```jsonc
// coach.json
{
  "chart.timeframe": {
    "lines": ["This changes how much history you see at once."],
    "next": "Try 1 month - the shape gets easier to read.",
    "auto_pop": true
  },
  "ticket.buy": {
    "lines": ["This spends your practice money on shares.", "Nothing here is real money."],
    "next": "You'll see exactly what it costs before anything happens.",
    "auto_pop": true
  }
}
```

### `scenes.json` schema (V1 owns the content, B owns the schema)

```jsonc
{
  "id": "act4.drop5",
  "chapter": 4,
  "speaker": "coach",
  "stage": "chart",                    // chart | minigame:<id> | ticket | symbols
  "lines": ["Your $1,680 is now $1,596."],
  "loss": "$84",                       // Principle 3: a loss always needs a `next`
  "next": "You have three choices, and none of them is wrong.",
  "respond": {
    "type": "choice",                  // choice | reflection | confidence | continue
    "options": [
      { "id": "sell", "label": "Sell - take the $84 loss",     "goto": "act4.sold" },
      { "id": "hold", "label": "Hold - stay in",               "goto": "act4.held" },
      { "id": "more", "label": "Buy more at the lower price",  "goto": "act4.added" }
    ]
  },
  "drawdown": true,
  "recovery_shown": "act4.recovery"    // Principle 6: required when drawdown is true
}
```

Lint rules over this file are what make the principles real rather than aspirational.

---

## 6. Metrics

| Metric | Target | Measured by |
|---|---|---|
| **Confidence delta** (1-5, pre vs post) | **+1.0 mean** | The two sliders. This is the thesis metric. |
| Completion rate | >= 80% reach Act 5 | Chapter events |
| Time to first answer, Act 4 Scenario A | < 15s median | Hesitation proxy |
| Questions answered without re-prompt | 100% (there is no skip) | Structural |
| Demo length | <= 2:30 | Rehearsal |

**Demo cut (2:15):** Act 0 (fast) then Act 3 buy, Act 4 Scenario A + counterfactual, Act 5
diversification beat, confidence delta. Everything else is depth for the judges who click around.

---

## 7. What survives from the current repo

**Keep as-is.** `sim_engine.py` — `apply_fill`, `check_open_orders_for_bar`, `shadow_delta`,
`portfolio_summary`, `price_at`, `advance`. The fixture generator and its `--check`. The
advance-stops-on-event pattern. The `as_of` staleness guard. The replay log. Snapshot-is-truth.

**Change.** Session keyed by `player_id`, not a module global. Tiers to chapters. Hints to the
dialogue graph. The safety-net modal to the scenario decision modal (same mechanics, new framing).
The content lint's rule. Fixtures to real historical bars with ticker and dates stripped.

**Cut from the beginner build.** The automatic -8% safety-net prompt (an intermediate concept).
Stop and limit orders. The tier scrub.

Plan for this honestly: **the engine survives, the experience layer is a rewrite.**

---

## 8. Risk register

| Risk | Likelihood | Impact | Mitigation | Contingency |
|---|---|---|---|---|
| The statistic is misquoted on a slide | Medium | **Critical** - destroys credibility on the exact topic | V2 opens the primary source before any deck draft | Cite the qualitative finding only, no numbers |
| Dialogue writing overruns | **High** | High - it is the product | Cap at 60 nodes; write Act 4 first, it is the demo | Ship Acts 0/3/4/5 only; cut Acts 1-2 to two beats each |
| Lightweight Charts integration eats a day | Medium | Medium | Spike it in week 1, vendored and offline, before committing | Fall back to the existing hand-rolled `chart.js` |
| Real historical data licensing | Medium | Medium | Use end-of-day data from a source whose terms permit redistribution; strip ticker and dates | Fall back to the existing synthetic generator, labelled honestly |
| No V2 named | **High** | High | AJ assigns this week | Team lead absorbs deck + Devpost; QA is cut |
| Scope creep back to three tiers | Medium | High | Intermediate/advanced are a stub card, in writing, in this spec | - |

---

## 9. Next five actions

| # | Action | Owner | Deadline |
|---|---|---|---|
| 1 | **Name V2** and hand them the statistic verification as their first task | AJ | 3 days |
| 2 | Write **Act 4 only** as `scenes.json` - the demo spine, ~15 nodes; then `coach.json` for the ~8 controls the demo touches | V1 | 1 week |
| 3 | Spike **Lightweight Charts** vendored and offline in the existing `web/` | F | 1 week |
| 4 | Re-key the session on `player_id`; delete the `SESSION` global | B | 1 week |
| 5 | Source one **real historical drawdown** (-5%, -12%, -25% in sequence) and build the ticker-stripped fixture | B | 1 week |

---

## 10. Open decisions

| Decision | Who | Status |
|---|---|---|
| Real historical data vs. synthetic | AJ | **CLOSED — synthetic.** Principle 4 below is amended accordingly. |
| The coach's name and bio | AJ | **CLOSED — Nia Okafor.** Shipped in `web/coach.json`. |
| A fixture where patience is rewarded | B | **OPEN, blocking.** See section 2.5. Nothing in the product currently ends in profit. |
| Does the pre/post confidence slider ship, or is it demo-only instrumentation? | AJ | Open. It is the thesis metric; it should ship. |
| Free-text reflection stored locally only, or sent to the server? | B + V1 | Open. Local-only is the privacy-safe default and keeps the offline promise. |

### Amendment to Principle 4 (synthetic decided)

> **Real data, honestly labelled** becomes: **synthetic data, honestly labelled.** Every fixture
> keeps `"synthetic": true`, and the coach says so in Act 0 in her own words: *"These prices are
> made up. What they do to your stomach is not."* The product never claims the data is live or
> historical. This is weaker as a pitch line than real-but-hidden and stronger as an ethics
> position, and it removes a licensing dependency from the critical path.

---

## 11. Shipped in this pass

| File | What it is | Tests |
|---|---|---|
| `web/coach.json` | Coach Nia Okafor: persona, bio, voice rules, and pop-out copy for 12 controls | 25 |
| `web/scenes/act4.json` | Act 4 dialogue graph, 12 nodes, pinned to HLX bars 40-89 | 74 |
| `server/tests/test_scenes.py` | Principle lint + fixture fact-check | 111 total, all green |

`test_scenes.py` fails the build if: an "I don't know" option appears anywhere; a scoring field
appears anywhere; a named loss has no `next`; a drawdown scene has no recovery scene; a node is a
dead end; a `goto` dangles; the coach breaks her own voice rules; or **any dollar figure the coach
quotes drifts from what the fixture actually produces at that bar.**

That last one is the important one. The coach quotes exact numbers ("$1,590", "$350.40",
"$520.80 apart"). If anyone regenerates the fixtures, those numbers move and the demo breaks in
front of judges. Now it breaks in CI instead. Each of the five rules was verified to fail when
deliberately violated.
