# Rich-HER: Full User Workflow

**Starting account: $100.** Three main lessons ("pillars"), one per act, with the basics woven in as they come up.
**Read this before doing any further build work.**

---

## The three pillars, and where each one is taught

| Pillar | Mainly taught in | Reinforced again in |
|---|---|---|
| **Market analysis** | Act 2 — Reading the chart | Act 3 (picking a company), Act 4 (reading a dip) |
| **Risk management** | Act 3 — How much? | Act 4 (the payoff), Act 5 (diversifying) |
| **Emotional control** | Act 4 — It drops | Act 5 (selling a winner), Act 6 (the confidence change) |

The basics — what a stock is, what a price is, market orders, buying and selling — are taught **exactly when they're needed**, never dumped all at once as a glossary.

### The one idea that ties all three pillars together

> **How much a stock's price moves around decides how much of your $100 belongs in it.**

Volatility (analysis) → how much you invest (risk) → how much a drop actually hurts (emotion). That single chain of cause and effect is the spine of the whole product. Every act builds on it.

---

## Why starting with $100 changes everything about the design

At $10,000, buying 10 shares of a $168 stock put 17% of the account at risk — but that was an arbitrary number she never actually chose and never really felt. The decision of how much to invest was basically invisible to her.

At $100, **how much to invest becomes the one decision that actually matters**, and she has to make it explicitly. This is the single biggest benefit of switching to a $100 account, and the whole flow is designed around it.

### Two structural changes this required

**1. Share prices need to fall in an $8–$35 range.** At $168 a share, $100 doesn't even buy one share. Since the price data is made up anyway, we're free to pick whatever price level we want — so we rescaled the same price patterns to a range where $100 buys 3–12 shares, making the sizing decision feel real. We kept whole-number shares only, so no extra "fractional share" engineering work is needed.

**2. Rename the companies to fictional ones.** Since the price data is already made up, calling one of them "AAPL" while quoting a $21 price would invite a judge to fact-check a number that was never real in the first place. Fictional company names are actually **more honest, not less** — they remove any risk of that fact-check entirely, and they let each company's name reinforce its lesson.

| Ticker | Company | Personality | Average daily price move | What happens |
|---|---|---|---|---|
| **NVX** | Novexa Systems | Exciting tech company, the story fixture | 1.02% | dips −10%, ends **+25%** |
| **BRW** | Brightwater Coffee | Familiar, steady | 0.27% | dips −0.5%, ends +3.9% |
| **BRD** | Broadline 500 Fund | Boring, defensive index fund | 0.33% | dips −1.6%, ends +2.6% |
| **KIN** | Kinetic Apparel | Medium volatility | 0.88% | dips −14.0%, ends −4.2% |
| **VLT** | Voltaic Motors | A hype stock | 1.40% | dips −27.3%, ends −17.9% |
| **HLX** | Helix Devices | A sharp pullback, used for the tier demo | 1.02% | dips −22.7%, ends −6.0% |

Five different scenarios teaching five different lessons. She doesn't see all five in one sitting — she works through them over time, and the "average daily move" column is exactly what the coach teaches her to read and understand.

---

## Act 0 — Getting started

**Teaches:** nothing yet. Establishes that this is a safe space.

1. **Welcome screen.** Enter a name (25 characters max, live counter) and pick an avatar from a grid of 12 (navigable with arrow keys). Then Continue. No email, no password, no account needed.
2. **Meet Nia.** Coach Nia Okafor, with her bio. She says the two lines that set the whole tone:
   - *"You have $100. It is not real, and it cannot follow you home."*
   - *"These prices are made up. What they do to your stomach is not."*
3. **Confidence check (before).** *"Before we start — how confident do you feel about investing?"* A 1–5 slider, no right answer. **The first thing the product does is ask her opinion — not test her knowledge.**

---

## Act 1 — What a stock is

**Pillar:** the basics. **Teaches:** what ownership means, and where a stock's price actually comes from.

4. Nia explains: a share is a small slice of a company. Uses one concrete company (BRW), no ticker symbols yet.
5. **Mini-game: "Own a slice."** She drags a slider to choose how much of Brightwater she wants to own, and the app shows what that would cost. Teaches: a share = a fraction of ownership, and price = the cost of one share.
6. Nia: *"Nobody sets that price. It's just the last number a buyer and a seller agreed on."*
7. **Mini-game: "Set the price."** A simple buyer/seller toy — she adds buyers and the price goes up, adds sellers and it goes down. **The single most valuable mini-game in the product** — it corrects the #1 beginner misconception, that a company decides its own stock price.
8. **First real numbers, low stakes:** BRW costs $12.00 a share. Her $100 could buy 8 shares, with $4 left over. She doesn't actually buy anything yet — she just sees that $100 is enough to get started.

---

## Act 2 — Reading the chart

**Pillar: MARKET ANALYSIS.**

9. The price chart appears for the first time: **just a line and two axes, nothing else.** Nia names the parts — time goes across, price goes up.
10. Three controls unlock one at a time, each one **popping up Nia automatically the first time** (then leaving a small badge behind): timeframe → crosshair → candlesticks.
11. **Trend vs. noise.** Nia shows the same chart zoomed in (looks chaotic and jagged) and zoomed out (looks like a smooth line going up). *"Both of these are the same company. A 2% wiggle isn't a direction."*
12. **Volatility — the concept the whole product hangs on.** Two charts side by side:
    - BRW moves about **0.27%** a day.
    - VLT moves about **1.40%** a day — five times as much.

    Nia: *"Neither one is better. But they don't deserve the same amount of your $100. Remember that — it's the whole thing."*
13. **Mini-game: "Which one is calmer?"** Four unlabeled charts, she ranks two of them by how much they jump around. No score. Teaches basic chart-reading and the volatility concept together, in about 30 seconds.

---

## Act 3 — Your first position

**Pillar: RISK MANAGEMENT.** **Teaches:** market orders, buying, and — most importantly — *how much to invest*.

14. **Pick a company.** Five cards, each showing the name, the price, and the **average daily price move** — so her choice is already an analytical decision. Nia: *"There's no wrong pick. There's only how much."*
15. She picks NVX ($21.00, moves about 1% a day, the exciting-sounding one — most people pick it, and that's fine).
16. Nia explains a market order in two sentences. The order form opens.
17. **The key decision — this is what the whole act is building toward.** Nia asks the central question of the entire product:

    > **How much of your $100 goes into Novexa?**
    >
    > | | | |
    > |---|---|---|
    > | **All of it** | 4 shares, $84 | $16 left in cash |
    > | **About half** | 2 shares, $42 | $58 left in cash |
    > | **Just a toe in** | 1 share, $21 | $79 left in cash |

    No option is labeled as wrong. No timer.
18. Nia explains the trade-off honestly, in both directions:
    *"More shares means more of everything — more if it rises, more if it falls. Cash isn't doing nothing. Cash is the part that can't be hurt."*
19. **The fill.** Explained in plain dollars: *"You own 2 shares of Novexa. You spent $42. You have $58."*
20. **A reflection box** (free text, never graded, never read by the system): *"Why that amount?"* Shown back to her in Act 6.

---

## Act 4 — It drops

**Pillar: EMOTIONAL CONTROL.** **Teaches:** what to actually do when the number turns red.

21. **Auto-play.** The chart animates forward at about 200ms per day. Nia stays quiet. Let this moment breathe.
22. **The dip.** NVX falls to **$19.88** (down 5.4%). Auto-pause. Nia states the dollar amount lost on *her specific position*, then asks:

    > **[Sell — take the loss]**  **[Hold — stay in]**  **[Buy more, it's cheaper now]**

    No "I don't know" option. No timer. No score. Every choice gets a respectful explanation afterward.
23. **It keeps falling.** Down to **$16.62** — a 20.9% drop from where she bought in. Nia's most important line in the whole product:
    *"This is the part where most people sell and never come back."*
    The same three choices appear again. Still no wrong answer.
24. **The payoff — where sizing and emotion meet.** Nia shows her what this exact market drop did to all three versions of her Act 3 decision:

    | Her Act 3 choice | Value at the worst point |
    |---|---|
    | All in (4 shares) | **−$17.52** |
    | Half in (2 shares) | −$8.76 |
    | A toe in (1 share) | **−$4.38** |

    > *"The market did the exact same thing to all three of them. Four times the pain — and it was already decided back in Act 3, before anything even happened. That's what risk management really is. It isn't predicting the future. It's deciding in advance how much a bad day is allowed to hurt."*

    **This is the best moment in the whole product,** and it only works because the account is small enough for the difference to be felt.
25. **Play to the end.** NVX recovers to **$19.75** — still below where she bought in, but well off the bottom. Nia: *"The panic was louder than the loss."*

---

## Act 5 — Two is safer than one

**Pillar: RISK MANAGEMENT, part two.** **Teaches:** diversification, and selling.

26. She still has cash left (unless she went all-in — and if she did, **that itself is the lesson**, and Nia says so without any scolding: *"You don't have any dry powder left. That's not a failure — it's the trade you made. Now you know what it costs."*).
27. **The choice:** put the remaining cash into more NVX, or into BRW — the boring coffee company, moving only 0.27% a day, the one she probably would have skipped back in Act 3.
28. **Play to the end.** BRW ends up **+3.9%**. NVX ends up **−6.0%**. The steady, boring one quietly offsets part of the exciting one's loss.
29. **The diversification beat — and the closing moment of the entire product.** This is the exact concept the research says women most often answer "I don't know" to. So Nia asks it **with no "I don't know" option available**, lets her answer, and *then* shows her the statistic:

    > *"Most women say they don't know this one. Take away the option to say 'I don't know,' and they get it right just as often as men. You just did."*

    The whole thesis of the product turns into something that actually happened to her, not just a claim printed on a slide.

---

## Act 6 — What you learned

30. **Confidence check (after).** The same 1–5 slider as before. Show her the change. This is both the success metric and the pitch line, in a single moment.
31. **Her journal.** Her reasons for how much she invested, in her own words, her trades, and the three pillars written out as three sentences she can actually use going forward. Downloadable. Nothing scored, nothing subtracted.
32. **Play another scenario.** Five companies, five different price patterns to explore. The "average daily move" number she learned to read back in Act 2 is what she now uses to pick her next one. VLT (−27.3%) is the one to try once she's ready for it.
33. An optional extra screen on what opening a real brokerage account actually looks like. No affiliate links, no financial advice given.

---

## Full playthrough: about 14 minutes. The 2:15 demo cut:

Act 0 (sped up) → **the Act 3 sizing decision** → Act 4's drop, plus the three-way sizing comparison table → the Act 5 diversification beat → the confidence-change reveal.

The sizing comparison table in Act 4 is the centerpiece of the demo — it's the single moment a judge will actually understand what the product does.

---

## What this needs that doesn't exist yet

| # | Work needed | Owner | Note |
|---|---|---|---|
| 1 | Rescale the price data to the $8–$35 range and rename companies to fictional ones | B | Same generator script, same `--check` verification. The shapes of the price paths stay the same. |
| 2 | Turn the position-sizing decision into its own proper scene type | B + V1 | Needs a new `respond.type: "sizing"` |
| 3 | Support for holding multiple positions at once, on the frontend | F | The engine already supports this; `app.js` currently assumes there's only ever one position |
| 4 | Write dialogue for Acts 1, 2, 3, 5, and 6 | V1 | Act 4 already exists and is fact-checked |
| 5 | Surface the "average daily move" number in the fixture data and on the company-picker cards | B | Just one calculated field |

## What already exists and can be kept

`sim_engine.py` in full · the fixture generator and its `--check` verification · fast-forward that stops automatically at important events · the `as_of` staleness check · the replay log · the rule that the server's snapshot is always the source of truth · `web/coach.json` (Nia) · `web/scenes/act4.json` (12 scenes) · `server/tests/test_scenes.py` (111 checks).

**Act 4's dialogue is already written and fact-checked, but its numbers are currently based on the $10,000 account.** Rescaling to a $100 account means rewriting its `facts` data — the automated checks will catch every single number that ends up wrong, which is exactly what they were built for.
