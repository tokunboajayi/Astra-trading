# Spec 3 (draft): The Coached Beginner Track

**Status:** input to SPEC.md v4. Replaces the tier/safety-net framing from SPEC.md v3.0.
**Scope:** the beginner track only. Intermediate and advanced tracks are described but not built yet.

> **Role key:** **B** = backend developer, **F** = frontend developer, **V1** = dialogue/copy writer, **V2** = pitch, deck, and user-testing owner, **AJ** = team lead.

---

## 0. Fixing the thesis (read this section first)

An earlier brainstorming document contains a better core idea than the one this repo was originally built around — and the two contradict each other.

| | Old (SPEC v3.0) | New |
|---|---|---|
| Core idea | "Teach them how not to lose money." | Hesitation, not lack of knowledge, is the real barrier. |
| Design rule that follows | Always lead with the downside. | No wrong answers, no "I don't know" option, no score. |
| Enforced by | `test_content.py` fails the build if a hint doesn't lead with a possible loss. | *(rule below, to be written into a new test)* |

**These two ideas can't both be true at once.** If hesitation is the real barrier, then leading every single interaction with "here's what you could lose" actually *creates* the hesitation the product is trying to remove. Right now, this repo has an automated test enforcing the exact thing the research says causes the problem.

**Resolution — the new set of design principles:**

| # | Principle | Enforced by |
|---|---|---|
| 1 | **No dead ends.** Every question has an answer she can pick. There is no "I don't know" option, ever. | An automated content check: any question with a skip/"don't know"/unsure option fails the build. |
| 2 | **No score.** Nothing is graded, ranked, or subtracted. Progress only ever adds up. | No score field exists anywhere in the app's data model. |
| 3 | **Honest, and always paired with a next step.** Losses are named in plain dollar amounts, and always come with a suggested next action — never a loss mentioned on its own. | A content check: every `loss` field must have a matching `next` field next to it. |
| 4 | **Real data, honestly labeled.** Real historical prices from a real company, with the ticker symbol and dates hidden so the ending can't be looked up in advance. Never presented as if it were live. | Each fixture file's metadata carries `source: historical`, `ticker_hidden: true`. |
| 5 | **One new thing at a time.** Never introduce more than three new controls in a single chapter. | The chapter's data caps a field called `new_controls`. |
| 6 | **Never end on a low point.** No scene ends on a price drop without also showing what happened after it. | A content check: any scene marked `drawdown: true` requires a `recovery_shown` scene to follow it. |

Principle 1 is really the whole product. Everything else exists to support it.

---

## 1. Why this product is aimed at women (in case a judge asks)

Nothing about a coached trading tutorial is inherently specific to women, and "we used female avatars" isn't a real answer to that question. The actual answer is in the research: this product removes four specific conditions that the research links to women opting out of investing.

| Condition that drives people away | What we remove |
|---|---|
| An "I don't know" escape hatch | Removed entirely (Principle 1) |
| Visible scoring or evaluation | No score anywhere (Principle 2) |
| Time pressure | No timers on any decision |
| Jargon that gates entry | The coach explains every term before any control that uses it |

**This benefits everyone, but it benefits women the most, because they're the ones the "I don't know" option was costing the most.** That's slide 2 of the pitch deck, and it's a stronger, more specific claim than "we made it pink."

### The statistic — still unverified, and important

The commonly cited figures ("63% of women pick 'don't know' vs. 43% of men, and correct answers rise 14% when that option is removed") appear to trace back to the *Fearless Woman* research on financial literacy and stock market participation (Bucher-Koenen, Alessie, Lusardi & van Rooij, NBER). The broad finding — that women disproportionately answer "I don't know," and that a large share of them actually answer correctly once that option is taken away — is well established research.

**But the exact numbers above haven't been double-checked yet.** Don't put them on a slide until V2 has pulled up the original source and confirmed the figures match. Citing a wrong statistic in a pitch about women's financial literacy would be a very damaging mistake to make in this specific room. Owner: V2. Deadline: before any slide deck draft.

---

## 2. Auditing the plan for contradictions and gaps

### Contradictions we found

| # | The contradiction | How we're fixing it (as a design decision) |
|---|---|---|
| L1 | Leading with downside vs. "hesitation is the barrier." | Principle 3 replaces the old Principle 1. The content check needs to be rewritten. |
| L2 | "Use historical data but pretend it's live" vs. the old plan's "prices are synthetic and clearly labeled as such." | **Decided: stay with synthetic data** (AJ made this call). The made-up price data is already built, is exactly reproducible, and avoids any question about data licensing. Keep the `"synthetic": true` label and the honest framing — "these prices are made up, but how they'd make you feel is not." Don't pretend it's live data. (Section 2.5 explains a gap this leaves.) |
| L3 | A 50% price drop vs. "don't overload beginners." | Sequence the drops: −5%, then −12%, then −25%+ — and only in an optional later module, always followed by a recovery shown in the same scene (Principle 6). A 50% loss as someone's *first* experience teaches "the market is terrifying," the opposite of the goal. |
| L4 | "The coach explains every button" vs. professional trading software's roughly 40 on-screen controls. | **The coach pops up right from the control itself** (see section 5.1), so explanations happen on-demand instead of as a 20-minute tour up front. Combined with gradually revealing controls: the chart starts as just a line with two axes, and never more than three new controls appear per chapter. The coach appears automatically the first time, then only when tapped after that. |
| L5 | Unlocking difficulty tiers mid-session (the old plan) vs. "just build the beginner track first." | Tiers become a **starting difficulty choice**, not something you unlock while playing. Within the beginner track, progress happens by **chapter** instead. |

### Things the plan didn't cover yet

| # | Gap | How we're filling it |
|---|---|---|
| M1 | There's no content model for what the coach actually says. A 13-minute coached tutorial needs 150–300 individual lines of dialogue, and nobody currently owns writing them. | Define a `scenes.json` format (see section 5) in week 1. Owner: V1. Cap the beginner track at 60 scenes total. |
| M2 | "She responds" to the coach — but how? Free-text responses would need an AI model, which needs an internet connection, which breaks the offline demo requirement. | Use multiple choice for anything that gets evaluated, plus **one ungraded free-text box per act** that the system never actually reads. She can write whatever she wants; nothing grades it. |
| M3 | The welcome screen asks for a name, but the server only keeps one shared session in memory. Two people using it at once would collide, and restarting the server would erase everything. | Key each session by a `player_id` saved in the browser's local storage. About 40 lines of code change to the existing shared-session setup — this also fixes a known limitation flagged earlier. |
| M4 | "Mini-games" were mentioned, but not which ones, what they teach, how you win, or who builds them. | Exactly four, defined in section 4, each capped at 60 seconds and tied to one specific misconception. |
| M5 | There's no pipeline for avatar artwork, and the reference images we have are from a commercial product we can't use. | Use openly licensed avatars, drawn as inline SVG code (no network request needed). Owner: F. |
| M6 | The coach has no name, face, or backstory. An unnamed coach is just a UI element; a named one feels like a relationship. | Give her a name, write a short bio, and give her an introduction screen. |
| M7 | There's no success metric that actually matches the new thesis. The old metric measured comprehension; the new thesis is about confidence. | A self-reported confidence rating (1–5) taken before and after the experience (section 6). Easy to measure, and it *is* the pitch line. |

### Feasibility concerns

| # | Risk | How we're addressing it |
|---|---|---|
| F1 | Building professional-grade charting from scratch is a multi-day project on its own. | Use **Lightweight Charts**, TradingView's own open-source charting library (free to use, about 45KB, can be bundled as one file for offline use). Gets a professional look in about a day of work. This does add a dependency, breaking our "zero dependencies" rule, but it's worth it — offline still works because the library is bundled directly into the project, not loaded from the internet. |
| F2 | Roughly 60% of the existing repo doesn't fit this new direction. | Being honest about this in section 7: the underlying engine survives, but the whole user-facing experience needs to be rebuilt. Saying so clearly now avoids someone planning a small refactor and discovering it's actually a rebuild. |
| F3 | A "minute by minute" replay would be unusable — a 5% price move takes real markets days to happen, and minute-by-minute data over a real drop would be tens of thousands of data points. | **Show one day per frame, auto-playing at about 200 milliseconds each.** A 90-day story runs in about 18 seconds and *feels* like it's happening live. This is just a timer added to the existing "advance" function — not a new way of storing data. |

### Bigger-picture concerns

| # | Concern | How we're addressing it |
|---|---|---|
| S1 | The reference product we looked at (a commercial finance app) has a **Score** button. | Don't copy it. Scoring reintroduces the exact evaluation anxiety this product is trying to remove. Replace it with a **"What you've learned" journal** that only ever adds to itself, never subtracts. |
| S2 | The reference screenshots are from a copyrighted commercial product (McGraw Hill). | Take the *pattern* — a coach with dialogue, a stage area, moving forward by clicking "Continue" — never the actual visual look, branding, or images. |
| S3 | Similar products already exist: Investopedia Simulator, Stock Trainer, Webull paper trading, Robinhood Learn. | Our angle: none of them is a *coached story built for someone who's hesitant to start*. They all assume you've already decided to trade. Have this comparison ready if asked. |

### Execution risks

| # | Risk |
|---|---|
| E1 | Nobody has taken on the V2 role yet, and the statistic — now central to the whole pitch — is sitting unverified. |
| E2 | Nobody owns writing the dialogue, and there's no word-count budget for it. |
| E3 | Nobody owns the avatar and scene artwork. |

---

## 2.5 Current blocker: every existing fixture only ever loses money

Measured across all five currently shipped fixtures, from each one's own starting point:

| Symbol | Entry price | Best point reached | Worst point reached | Ends at | Does it ever reach +5%? |
|---|---|---|---|---|---|
| HLX | $168.00 (day 40) | +2.38% | **-20.86%** | -5.95% | **No** |
| BRW | $63.51 (day 30) | +3.92% | -0.52% | **+3.92%** | **No** |
| KIN | $99.17 (day 25) | 0.00% | -13.95% | -4.20% | **No** |
| BRD | $492.00 (day 30) | +3.21% | -1.63% | +2.64% | **No** |
| VLT | $262.00 (day 15) | +1.85% | **-27.29%** | -17.94% | **No** |

**Not one of the five ever gains as much as 5%. Three of the five end up down overall. The best possible outcome anywhere in the current product is +3.92%.**

This isn't a bug — it's a leftover from the old design. These price paths were deliberately built to guarantee a big drop, because the earlier version of this product existed specifically to teach people about loss. Under the new thesis, that's actually harmful: a beginner simulator where **every single possible outcome loses money** teaches "investing loses money" — which reinforces the exact hesitation this product is supposed to remove.

It also means **the "price goes up 5%" scenario mentioned in early planning simply can't be built with the current data at all.**

**Fix (owned by B, needed before the practice run):** generate one more fixture, specifically designed for the opposite shape — an early dip of about −5%, a recovery back through breakeven, and a finish somewhere around **+12% to +18%**. Same generator script, same verification step, just one new set of target prices.

**A free, immediate partial fix:** HLX already ends at **-5.95%** and BRW already ends at **+3.92%**, and both already exist. That contrast *is* a diversification lesson, using data we already have. Use it for the Act 5 diversification scene: one exciting stock that lost money, one boring one that didn't. That was always the intended lesson, and the existing data already demonstrates it.

---

## 3. Proposed user flow

A full playthrough takes about 13 minutes. The 2:15 demo version is a shortened cut of it (see section 6).

### Act 0 — Getting started (0:30)

1. **Welcome screen.** Enter a name (25 characters max, with a live counter) and pick an avatar from a grid of 12 (navigable with arrow keys, select with Enter), then Continue. No email, no password, no account creation. A `player_id` gets saved to the browser.
2. **Meet the coach** (an introduction screen). The coach, with a name and a short bio. Explain that the $10,000 is practice money, stated plainly as not real. One sentence about the data: *"These are real prices from a real company. We've hidden which one, so you can't look up how the story ends."*
3. **Confidence check (before).** *"Before we start — how confident do you feel about investing?"* A 1–5 slider, with no right answer. The very first thing the product does is ask her opinion, not test her knowledge. This sets the tone, and gives us a baseline for the only metric that really matters here.

### Act 1 — What is a stock? (2:00) — Chapter 1

4. Coach explains: a stock is a small slice of ownership in a company. Uses one concrete example company, no ticker symbols introduced yet.
5. **Mini-game 1 — "Own a slice."** She picks how much of a company she wants to own, and the app shows what that would cost. Teaches that a share = a fraction of ownership, and price = the cost of one share. 45 seconds.
6. Coach explains: prices move because people are buying and selling. Kept to three sentences maximum.
7. **Mini-game 2 — "Set the price."** A simple buyers-and-sellers toy: she drags buyers and sellers around, and watches the price move in response. 45 seconds. *This is the single most valuable mini-game in the product* — it corrects the most common beginner misconception, that a company decides its own stock price.

### Act 2 — Reading the chart (2:00) — Chapter 2

8. The price chart appears for the first time: **just a line and two axes, nothing else.** The coach names the parts — time goes across, price goes up.
9. Three controls unlock, one at a time: choosing a timeframe, a crosshair/tooltip, and a candlestick view toggle. Each one **triggers the coach automatically the first time it appears** (see section 5.1), then she steps back and just leaves a small badge behind. Never more than three controls introduced in this chapter.
10. **Mini-game 3 — "Which way did it go?"** Four small chart snippets — she picks the one that ended higher than it started. Instant feedback, no score. Teaches basic chart-reading in about 30 seconds.

### Act 3 — Your first trade (3:00) — Chapter 3

11. A list of 5 curated companies (real, but with names hidden). Coach: *"Pick one. There's no wrong pick."*
12. **Mini-game 4 — matching ticker symbols to company names.** Placed here on purpose, as a lighter, fun beat — **not** as a gate you have to pass through first. Matching tickers to names teaches vocabulary, which *feels* like the barrier to entry but actually isn't. Putting this first would have wrongly taught her that the barrier is just memorization.
13. The order ticket appears. Coach explains a "market order" in two sentences. She buys.
14. **The fill scene** (what happens after the trade goes through). The coach narrates it in plain dollars, no jargon: *"You own 10 slices of this company. You spent $1,680. You have $8,320 left."*
15. **A reflection box** (free text, never graded, never actually read by the system): *"How did that feel?"* Saved locally and shown back to her in her journal at the end.

### Act 4 — The market moves (4:00) — Chapter 4, the emotional core

16. **Auto-play.** The chart animates forward at about 200ms per day. The coach stays quiet. Let this moment breathe.
17. **Scenario A: a 5% drop.** The chart auto-pauses. The coach calmly states the dollar amount, then asks:

    > Your $1,680 is now $1,596. What do you want to do?
    > **[Sell — take the $84 loss]**  **[Hold — stay in]**  **[Buy more at the lower price]**

    No "I don't know" option. No timer. No score. Every choice gets a respectful explanation afterward.
18. **The outcome, plus what-if comparisons.** She sees what her actual choice did, *and* what the other two choices would have done, side by side. The app's existing `shadow_delta()` function already calculates exactly this — we just reuse it. It's honest in both directions, including the times when holding on turns out to have been the wrong call.
19. **Scenario B: a 5% gain.** The same three-choice structure. Teaches that the same decision-making framework applies on the way up too, and that selling a winner too early has a cost as well.
20. **Scenario C: a deep drop (-20% to -30%).** The single most important line in the whole product lands here: *"This is the part where most people sell and never come back. Let's look at what happened next."* Then it shows the recovery. **Never end on the low point** (Principle 6).

### Act 5 — What it all means (2:00) — Chapter 5

21. Buy-and-hold vs. picking individual stocks, diversification, managing emotions, when to sell — each one delivered as **one line of dialogue tied to something she already did**, never as a lecture. *"Remember when it dropped 5% and you held on? That's what patience costs, and what it pays off."*
22. **The diversification beat — the final and most important moment of the whole product.** This is the exact concept the research says women most often answer "I don't know" to. So: ask the question **with no "I don't know" option available**, let her answer, and only *then* show her the statistic:

    > *"Most women say they don't know this one. When you take away the option to say 'I don't know,' they get it right just as often as men do. You just did."*

    This turns the whole thesis into something she personally experienced, rather than something she just read on a slide. It's the closing beat of the demo, and the single best moment in the product.
23. **Confidence check (after).** The same 1–5 slider from the start. Show her the difference. That's both the success metric and the pitch line, in one move.
24. **Her journal.** Everything she learned, her own reflections, her trades. Downloadable. Nothing is scored, nothing is subtracted.

### Act 6 — Wrapping up

25. A "You're ready for the Intermediate track" card — a placeholder for now, showing the direction without needing to build it yet.
26. An optional extra screen on what opening a real brokerage account looks like. No affiliate links, no financial advice given.

---

## 4. The four mini-games

| # | Name | Misconception it corrects | Where it appears | Time limit |
|---|---|---|---|---|
| 1 | Own a slice | "A share is some abstract financial thing" | Act 1 | 45s |
| 2 | Set the price | "The company decides its own stock price" | Act 1 | 45s |
| 3 | Which way did it go? | "Charts are only for experts" | Act 2 | 30s |
| 4 | Symbol match | (a fun break, not really teaching a concept) | Act 3 | 45s |

Every mini-game: no score, no timer pressure, no way to actually fail. A wrong answer just gets an explanation and another try.

---

## 5. Screen layout

Three zones, the same in every scene, based on the reference layout but with the stock photo replaced by an actual interactive stage.

```
+----------------------------------------------------------------+
| Product name      * * o o o  (chapter dots)          ?     [ ]  |  <- NO score anywhere
+----------------------+-----------------------------------------+
|  [avatar chips]      |                                         |
|  Coach Name          |              STAGE                      |
|  +----------------+  |   chart | mini-game | order ticket      |
|  | dialogue, with |  |         one thing at a time             |
|  | her name in it |  |                                         |
|  +----------------+  |  (Lightweight Charts, professional look)|
|    [ Continue ]      |                                         |
|  or [A] [B] [C]      |                                         |
+----------------------+-----------------------------------------+
|  Cash $8,320   |   10 shares   |   -$84 today                   |  <- appears once she owns something
+----------------------------------------------------------------+
```

### 5.1 The coach pop-out (the core interaction pattern)

The coach isn't a fixed panel that stays in one place. She's a component that can anchor itself to whatever's currently being explained. She has two modes:

| Mode | When it's used | What it looks like |
|---|---|---|
| **Narrating** | Story beats, scenarios, moving between chapters | A full dialogue bubble anchored in the left panel, with Continue/choice buttons |
| **Popped out** | Explaining a single control | A small bubble that points at the specific control, without blocking anything else on screen |

**Every interactive element gets a coach ID.** This is already the pattern used in the current hint system — we just keep the underlying mechanism and replace the visual design and the writing style.

```html
<button data-coach="chart.timeframe">1D</button>
<button data-coach="ticket.buy">Buy</button>
<select data-coach="ticket.qty">...</select>
```

**Rules for when the coach appears:**

1. **The first time a control appears on screen, the coach pops up automatically, once.** She explains it, and the bubble stays until it's dismissed or the control gets used. This satisfies "every button gets explained" without needing a boring front-loaded tour.
2. **After that first time, it's on-demand only.** Every coached control keeps a small badge next to it. Tap the badge, and she comes back. She never interrupts on her own after the first time.
3. **Never hover-only.** Hovering doesn't work on touchscreens and isn't accessible to keyboard or screen-reader users. The badge is a real, focusable button, and the pop-out itself is reachable by keyboard and properly announced to screen readers.
4. **Never blocking.** The pop-out never covers the whole screen or stops you from doing anything else — you can ignore it and keep going. Pressing Escape closes it. This matters: a blocking explanation of a button is a dead end, and avoiding dead ends is our first design principle.
5. **Only one at a time.** Opening a new pop-out closes any other one that's open. The main narrating bubble dims but stays visible.

**Why this approach is worth the effort:** it's what lets the whole thing scale. Without it, you either need a 20-minute tour nobody actually finishes, or you ship a product with unexplained buttons. With it, the app can expose as much of a professional-trading-software-style interface as needed, because nothing is ever left unexplained — but also nothing is explained before it's actually relevant. It also turns the entire Act 2 chart tutorial from a long scripted walkthrough into three quick automatic pop-ups, saving roughly a minute of demo time.

**How much writing this needs:** a short entry per control, 2–3 sentences each. Budgeting for about 25 controls in the beginner build means about 25 short entries total — a separate file from the main scene content, and it's V1's second writing task after Act 4.

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

### `scenes.json` format (B owns the format, V1 owns the actual writing that goes in it)

```jsonc
{
  "id": "act4.drop5",
  "chapter": 4,
  "speaker": "coach",
  "stage": "chart",                    // chart | minigame:<id> | ticket | symbols
  "lines": ["Your $1,680 is now $1,596."],
  "loss": "$84",                       // Principle 3: any loss mentioned needs a `next` alongside it
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
  "recovery_shown": "act4.recovery"    // Principle 6: required whenever drawdown is true
}
```

Automated checks against this file are what actually make these principles real, instead of just good intentions written in a document.

---

## 6. Success metrics

| Metric | Target | How it's measured |
|---|---|---|
| **Confidence change** (1–5 scale, before vs. after) | **+1.0 average increase** | The two sliders. This is the main metric for the whole thesis. |
| Completion rate | 80% or more reach Act 5 | Chapter-completion events |
| Time to first answer, Act 4 Scenario A | Under 15 seconds, on average | A stand-in for measuring hesitation |
| Questions answered without needing a re-prompt | 100% (there's no way to skip) | Built into the structure |
| Demo length | 2:30 or under | Timed in rehearsal |

**The 2:15 demo cut:** Act 0 (sped up), then the Act 3 sizing decision, the Act 4 Scenario A drop plus the what-if comparison, the Act 5 diversification beat, and the confidence-change reveal. Everything else is extra depth for judges who want to explore further on their own.

---

## 7. What we're keeping from the current repo

**Keeping as-is:** `sim_engine.py` — `apply_fill`, `check_open_orders_for_bar`, `shadow_delta`, `portfolio_summary`, `price_at`, `advance`. The fixture generator and its `--check` verification. The pattern where fast-forward stops automatically at important events. The `as_of` staleness check. The replay log. The rule that the server's snapshot is always the source of truth.

**Changing:** Sessions will be keyed by `player_id` instead of one shared global session. Difficulty tiers become chapters. Hints become a full dialogue tree. The safety-net popup becomes the scenario decision popup (same underlying logic, new visual framing). The content-checking rules get updated. Fixtures move from made-up data to real historical prices with the ticker symbol and dates stripped out.

**Cutting from the beginner build (for now):** The automatic −8% safety-net prompt (that's a more advanced, intermediate-level concept). Stop and limit order types. The tier preview feature.

Being honest about the scope: **the underlying engine survives as-is; the entire user-facing experience is a rebuild.**

---

## 8. Risk register

| Risk | How likely | How bad if it happens | How we're reducing it | Backup plan |
|---|---|---|---|---|
| The statistic gets misquoted on a slide | Medium | **Very bad** — undermines our credibility on the exact topic we're pitching | V2 checks the original source before any slide deck draft | Cite only the general finding, no specific numbers |
| Writing all the dialogue takes longer than planned | **High** | High — the dialogue basically *is* the product | Cap it at 60 scenes total; write Act 4 first since it's the demo | Only ship Acts 0, 3, 4, and 5; cut Acts 1–2 down to two scenes each |
| Integrating the charting library eats a whole day | Medium | Medium | Try it out in week 1, bundled and working offline, before committing to it | Fall back to the existing hand-built chart |
| Licensing issues with real historical data | Medium | Medium | Use end-of-day data from a source whose terms allow us to redistribute it; strip out ticker symbols and dates | Fall back to the existing made-up price generator, clearly labeled |
| Nobody takes the V2 role | **High** | High | AJ assigns someone this week | Team lead absorbs the deck + testing work; user testing gets cut |
| Scope creeps back to building all three difficulty tiers | Medium | High | Intermediate/advanced tracks are explicitly written as placeholders only, in this document | — |

---

## 9. Next five things to do

| # | Action | Owner | Deadline |
|---|---|---|---|
| 1 | **Assign someone to the V2 role** and give them statistic verification as their first task | AJ | 3 days |
| 2 | Write **Act 4 only** as `scenes.json` — the demo's spine, about 15 scenes — then `coach.json` for the roughly 8 controls the demo touches | V1 | 1 week |
| 3 | Try out **Lightweight Charts**, bundled and working offline, in the existing `web/` folder | F | 1 week |
| 4 | Switch sessions to being keyed by `player_id`; remove the shared global session | B | 1 week |
| 5 | Find one **real historical price drop** (−5%, then −12%, then −25%, in sequence) and build the ticker-stripped fixture from it | B | 1 week |

---

## 10. Still-open decisions

| Decision | Who decides | Status |
|---|---|---|
| Real historical data vs. made-up data | AJ | **Decided — synthetic (made-up) data.** Principle 4 above has been updated to reflect this. |
| The coach's name and backstory | AJ | **Decided — Nia Okafor.** Already in `web/coach.json`. |
| A fixture where patience actually pays off | B | **Still open, and blocking other work.** See section 2.5 — nothing in the product currently ends up profitable. |
| Does the before/after confidence slider ship in the real product, or is it just for the demo? | AJ | Open. It's the main metric for the whole thesis — it probably should ship. |
| Is the free-text reflection box saved locally only, or sent to the server? | B + V1 | Open. Keeping it local-only is more private and keeps the offline promise intact. |

### A note on Principle 4 (now that synthetic data has been decided)

> **"Real data, honestly labeled"** now becomes: **"synthetic data, honestly labeled."** Every fixture keeps the `"synthetic": true` label, and the coach says so herself in Act 0, in her own words: *"These prices are made up. What they do to your stomach is not."* The product never claims the data is live or historical. This is a weaker pitch line than "real data, just hidden," but it's a stronger ethical position, and it removes a licensing dependency from our critical path.

---

## 11. What's already built as of this document

| File | What it is | Number of tests |
|---|---|---|
| `web/coach.json` | Coach Nia Okafor: her persona, bio, voice guidelines, and pop-out copy for 12 controls | 25 |
| `web/scenes/act4.json` | Act 4's dialogue, 12 scenes, tied to HLX's price data on days 40–89 | 74 |
| `server/tests/test_scenes.py` | Automated checks for our principles, plus fact-checking against the fixture data | 111 total, all passing |

`test_scenes.py` fails the build if: an "I don't know" option appears anywhere; a scoring field appears anywhere; a mentioned loss has no `next` field; a drawdown scene has no recovery scene after it; a scene is a dead end; a `goto` points nowhere; the coach's dialogue breaks her own voice guidelines; or **any dollar figure the coach quotes doesn't match what the fixture data actually produces at that point.**

That last check matters most. The coach quotes exact numbers ("$1,590", "$350.40", "$520.80 apart"). If anyone regenerates the fixture data, those numbers can shift — and if that happens during a live demo, it's a disaster in front of judges. Catching it automatically means it happens in our tests instead. Each of these five rules was tested by deliberately breaking it once, to confirm the check actually catches the problem.
