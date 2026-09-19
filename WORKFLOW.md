# Rich-HER: Full User Workflow

**Account: $100.** Three pillars, one per act, with the basics woven through.
**Review this before any further build.**

---

## The three pillars, and where each is taught

| Pillar | Primary act | Reinforced in |
|---|---|---|
| **Market analysis** | Act 2 — Reading the chart | Act 3 (picking), Act 4 (reading a dip) |
| **Risk management** | Act 3 — How much? | Act 4 (the payoff), Act 5 (diversifying) |
| **Emotional control** | Act 4 — It drops | Act 5 (selling a winner), Act 6 (the delta) |

Basics — what a stock is, what a price is, market orders, buy and sell — are taught **at the moment
they are needed**, never as a glossary.

### The one idea that connects all three

> **How much a stock moves decides how much of your $100 belongs in it.**

Volatility (analysis) → position size (risk) → how much a drop hurts (emotion). That single chain is
the spine of the product. Every act advances it.

---

## Why $100 changes the design

At $10,000, buying 10 shares of a $168 stock put 17% of the account at risk — an arbitrary number
she never chose and never felt. Position sizing was invisible.

At $100, **sizing is the only decision that matters**, and she makes it explicitly. This is the
single best consequence of the $100 constraint and the flow is built around it.

### Two structural changes this forces

**1. Share prices must fall into an $8–$35 band.** At $168 a share, $100 buys nothing. The fixtures
are synthetic, so the price level is a free parameter — rescale the same arcs to a band where $100
buys 3–12 shares and sizing choices are legible. Integer shares are kept; no fractional-share engine
work is needed.

**2. Rename the symbols to fictional companies.** The fixtures are already synthetic, so calling one
"AAPL" while quoting a $21 price invites a judge to fact-check a number that was never real. Fictional
names are **more honest, not less**, they remove the fact-check risk entirely, and they let each
company's name carry its lesson.

| Ticker | Company | Character | Avg daily move | Arc |
|---|---|---|---|---|
| **NVX** | Novexa Systems | Exciting tech, the story fixture | 1.02% | dips −10%, ends **+25%** |
| **BRW** | Brightwater Coffee | Familiar, steady | 0.27% | trough −0.5%, ends +3.9% |
| **BRD** | Broadline 500 Fund | Boring, defensive index | 0.33% | trough −1.6%, ends +2.6% |
| **KIN** | Kinetic Apparel | Mid-volatility | 0.88% | trough −14.0%, ends −4.2% |
| **VLT** | Voltaic Motors | Hype stock | 1.40% | trough −27.3%, ends −17.9% |
| **HLX** | Helix Devices | Sharp pullback, the tier demo | 1.02% | trough −22.7%, ends −6.0% |

Five scenarios, five different lessons. She does not see all five in one sitting — she works through
them, and the volatility column is what the coach teaches her to read.

---

## Act 0 — Entry

**Teaches:** nothing yet. Establishes safety.

1. **Welcome.** Name (25 char max, live counter) + avatar grid (12, arrow-key navigable). Continue.
   No email, no password, no account.
2. **Meet Nia.** Coach Nia Okafor, with her bio. She says the two things that set the tone:
   - *"You have $100. It is not real, and it cannot follow you home."*
   - *"These prices are made up. What they do to your stomach is not."*
3. **Confidence check (pre).** *"Before we start — how confident do you feel about investing?"*
   1–5 slider. No right answer. **The first thing the product does is ask her opinion, not test her.**

---

## Act 1 — What a stock is

**Pillar:** basics. **Teaches:** ownership, and where a price comes from.

4. Nia: a share is a slice of a company. One concrete company (BRW), no tickers yet.
5. **Mini-game: "Own a slice."** She drags to choose how much of Brightwater she wants; the app shows
   what it costs. Teaches share = fractional ownership, price = cost of one slice.
6. Nia: *"Nobody sets that price. It's just the last number a buyer and a seller agreed on."*
7. **Mini-game: "Set the price."** A two-sided order book. She adds buyers, the price rises; adds
   sellers, it falls. **The highest-value mini-game in the product** — it kills the number one
   beginner misconception, that the company decides the price.
8. **First basics beat:** BRW is $12.00. Her $100 buys 8 shares, with $4 left over. She doesn't buy
   yet. She just sees that $100 is enough.

---

## Act 2 — Reading the chart

**Pillar: MARKET ANALYSIS.**

9. The chart appears: **a line and two axes, nothing else.** Nia names them — time across, price up.
10. Three controls unlock, each **auto-popping Nia once** (then a badge remains):
    timeframe → crosshair → candlesticks.
11. **Trend vs noise.** Nia shows the same chart zoomed in (looks chaotic) and zoomed out (looks like
    a line going up). *"Both of these are the same company. A 2% wiggle is not a direction."*
12. **Volatility — the concept the whole product hangs on.** Two charts side by side:
    - BRW moves about **0.27%** a day.
    - VLT moves about **1.40%** a day — five times as much.

    Nia: *"Neither one is better. But they don't deserve the same amount of your $100. Remember that,
    it's the whole thing."*
13. **Mini-game: "Which one is calmer?"** Four unlabelled charts, she ranks two of them by how much
    they jump. No score. Chart literacy plus the volatility concept in 30 seconds.

---

## Act 3 — Your first position

**Pillar: RISK MANAGEMENT.** **Teaches:** market orders, buy, and *how much*.

14. **Pick a company.** Five cards, each showing name, price, and the **average daily move** — so her
    pick is already an analysis decision. Nia: *"There's no wrong pick. There's only how much."*
15. She picks NVX ($21.00, moves ~1% a day, the exciting one — most people pick it, and that is fine).
16. Nia explains a market order in two lines. Ticket opens.
17. **THE DECISION — this is the act.** Nia asks the question the whole product is built around:

    > **How much of your $100 goes into Novexa?**
    >
    > | | | |
    > |---|---|---|
    > | **All of it** | 4 shares, $84 | $16 left in cash |
    > | **About half** | 2 shares, $42 | $58 left in cash |
    > | **Just a toe in** | 1 share, $21 | $79 left in cash |

    No option is labelled wrong. No timer.
18. Nia names the trade-off honestly, both directions:
    *"More shares means more of everything — more if it rises, more if it falls. Cash is not doing
    nothing. Cash is the part that can't be hurt."*
19. **The fill.** Plain dollars: *"You own 2 shares of Novexa. You spent $42. You have $58."*
20. **Reflection box** (free text, never graded, never read by the system): *"Why that amount?"*
    Shown back to her in Act 6.

---

## Act 4 — It drops

**Pillar: EMOTIONAL CONTROL.** **Teaches:** what to do when the number goes red.

21. **Auto-play.** Chart animates ~200ms per bar. Nia is silent. Let it breathe.
22. **The dip.** NVX falls to **$19.88** (−5.4%). Auto-pause. Nia names the dollar loss for *her*
    actual position, then:

    > **[Sell — take the loss]**  **[Hold — stay in]**  **[Buy more, it's cheaper]**

    No "I don't know." No timer. No score. Every option gets a respectful explanation.
23. **It keeps falling.** To **$16.62** — down **20.9%** from her entry. Nia's most important line:
    *"This is the part where most people sell and never come back."*
    Same three choices. Still no wrong answer.
24. **The payoff — sizing meets emotion.** Nia shows what this exact market did to all three versions
    of her Act 3 decision:

    | Her Act 3 choice | At the worst moment |
    |---|---|
    | All in (4 shares) | **−$17.52** |
    | Half in (2 shares) | −$8.76 |
    | A toe in (1 share) | **−$4.38** |

    > *"The market did the same thing to all three of them. Four times the pain, and it was decided
    > back in Act 3, before anything happened. That's what risk management is. It isn't predicting.
    > It's deciding in advance how much a bad day is allowed to hurt."*

    **This is the best beat in the product.** It only works at $100.
25. **Run to the end.** NVX recovers to **$19.75** — still down, but well off the bottom. Nia:
    *"The panic was louder than the loss."*

---

## Act 5 — Two is safer than one

**Pillar: RISK MANAGEMENT, part two.** **Teaches:** diversification, and selling.

26. She still has cash (unless she went all in — and if she did, **that is the lesson**, and Nia says
    so without scolding: *"You don't have any dry powder. That's not a failure, it's the trade you
    made. Now you know what it costs."*).
27. **The choice:** put the remaining cash into more NVX, or into BRW — boring coffee, moves 0.27% a
    day, the one she'd have skipped in Act 3.
28. **Run to the end.** BRW ends **+3.9%**. NVX ends **−6.0%**. The steady one quietly offsets part of
    the exciting one's loss.
29. **The diversification beat — and the closing move of the product.** This is the exact concept where
    the research says women answer "don't know" most often. So Nia asks it **with no "I don't know"
    option**, she answers, and *then* Nia shows her the statistic:

    > *"Most women say they don't know this one. Take away the option to say 'I don't know,' and they
    > get it right just as often as men. You just did."*

    The thesis becomes something that happened to her, not a claim on a slide.

---

## Act 6 — What you learned

30. **Confidence check (post).** Same 1–5 slider. Show her the delta. Metric and pitch line in one move.
31. **Her journal.** Her sizing reasons in her own words, her trades, the three pillars written as
    three sentences she can actually use. Downloadable. Nothing scored, nothing subtracted.
32. **Play another scenario.** Five companies, five shapes. The volatility number she learned to read
    in Act 2 is how she picks the next one. VLT (−27.3%) is the one to try when she's ready.
33. Optional bridge: what opening a real brokerage account looks like. No affiliate links, no advice.

---

## Full playthrough: ~14 minutes. The 2:15 demo cut:

Act 0 (fast) → **Act 3 sizing decision** → Act 4 drop + the three-way sizing table →
Act 5 diversification beat → confidence delta.

The sizing table in Act 4 is the demo's centrepiece. It is the moment a judge understands the product.

---

## What this needs that does not exist yet

| # | Work | Owner | Note |
|---|---|---|---|
| 1 | Rescale fixtures to the $8–$35 band and rename to fictional companies | B | Same generator, same `--check`. Arcs unchanged. |
| 2 | Position-size decision as a first-class scene type | B + V1 | New `respond.type: "sizing"` |
| 3 | Multi-position frontend | F | Engine already supports it; `app.js` assumes `positions[0]` |
| 4 | Acts 1, 2, 3, 5, 6 dialogue | V1 | Act 4 exists and is fact-checked |
| 5 | Volatility (avg daily move) surfaced in fixture meta and on the pick cards | B | One computed field |

## What already exists and survives

`sim_engine.py` in full · the fixture generator and its `--check` · `advance`-stops-on-event ·
`as_of` guard · replay log · snapshot-is-truth · `web/coach.json` (Nia) ·
`web/scenes/act4.json` (12 nodes) · `server/tests/test_scenes.py` (111 assertions).

**Act 4's dialogue is written and fact-checked, but its numbers are pinned to the $10,000 account.**
Rescaling to $100 means rewriting its `facts` blocks — the lint will catch every one that drifts,
which is exactly what it was built for.
