# Rich-HER / Astra Trading: White Paper

> **This document is archived.** It was written to support the older v3.0 version of the product's thesis. The current thesis is in [SPEC_3.md](../SPEC_3.md) — check any claim here against that current spec before using it in a pitch. This is still useful for the overall narrative.

**Empowering Financial Autonomy Through Downside-First Risk Literacy and Progressive Simulation**

---

## Executive Summary

Most retail trading apps — including "gamified" ones aimed at beginners — share a fundamental design flaw: they're built to maximize how often people trade, using upside-focused, dopamine-driven design. For beginners, and disproportionately for women and other historically underserved investors, this creates a frustrating choice between two bad options: intimidating complexity, or reckless speculation.

**Rich-HER** (code-named **Astra Trading**) is an educational trading interface built for the HackHERS hackathon. Instead of luring people in with unrealistic promises of wealth, Rich-HER is built around **downside-first risk literacy** — leading with what you could lose, not what you could gain. It combines an interactive price replay ("walk into the dip") with a system of gradually unlocking complexity and a safety net that steps in proactively, turning intimidation about the market into risk-aware confidence.

---

## 1. The core problem: the risk-literacy and confidence gap

1. **An uneven learning curve.** Beginners are usually introduced to markets either during a bull run (when everything looks easy) or through oversimplified interfaces that hide real mechanics like slippage, volatility, and protecting your capital.
2. **Framing that leads with upside.** Most trading interfaces describe a "Buy" order purely in terms of ownership and potential gains, burying any mention of downside risk in legal fine print. When a real market correction happens, beginners often panic and sell right at the bottom.
3. **A gap between overwhelming tools and toy simulators.** Existing options tend to be either professional terminal software (packed with numbers and hard to approach) or disconnected paper-trading apps that run in real time, with no way to create a teachable moment on demand.

---

## 2. The Rich-HER solution: four foundational ideas

### Idea 1: Lead with the downside
Every order type, indicator, and action leads by explaining what could be lost. Before explaining how something might generate a return, Rich-HER first says what capital is actually at risk, and how the order could go wrong.
* *Instead of* "Buy: own shares of Apple and grow your portfolio," *Rich-HER says:* "If the price falls, your shares are worth less right away, and you could lose some or all of the money you put in. Buying trades your cash for shares."
* This rule is actually enforced by our tests, not just something we intend to follow: a build fails automatically if any hint's first line doesn't lead with the downside, or if that line doesn't name a real loss.

### Idea 2: A deterministic replay ("walk into the dip")
Real-time paper trading means waiting weeks for a meaningful price move to happen, and it makes for an unpredictable demo. Instead, Rich-HER replays **fixed, repeatable 90-day price histories** that the user steps through one day at a time, with the future always hidden — so experiencing a real pullback only takes a few minutes, inside a safe, guided environment.

These price paths are **entirely made up.** A script with a fixed random seed generates them, anchored to specific chosen prices, and the HLX path in particular is built to always include a **−22.7% drop**, so the teaching moment is guaranteed rather than hoped for. The product labels this data as synthetic everywhere it shows up on screen. Fast-forward always stops the instant something important happens, so a fill or a safety-net prompt can never accidentally get skipped over.

### Idea 3: Gradually unlocking complexity (tiers)
Advanced trading tools aren't hidden entirely, but they also aren't dumped on the user all at once on day one. Instead, more complex features unlock by demonstrating understanding — not just by trading more.

| Tier | Order types available | Chart shown | How you unlock it |
|---|---|---|---|
| **1 Foundation** | Market orders only | A simple line | Everyone starts here |
| **2 Tactical Protection** | + Limit orders; choose your own safety-net distance | Line with the highest and lowest points so far | Answering the downside comprehension question correctly, after your first trade |
| **3 Strategic Mastery** | + Stop orders | Candlesticks, plus moving-average signal lines | Answering the stop-loss comprehension question correctly, after your first safety-net trigger |

Beginners can use the **tier preview** to look ahead at what they'll eventually unlock — but it's read-only, a preview, not a shortcut past it. Someone who says they've traded before can start directly at Tier 2.

### Idea 4: A safety net that steps in proactively
When a position drops 8% in value, Rich-HER steps in with a one-tap prompt, built entirely from the user's own real numbers:

> *"Your HLX position is down 8.2%. You bought 10 at $168.00; it is now $154.17, so you are down $138.30. If it falls to $151.20 your shares are sold automatically. If it dips there and bounces back, you will have sold at the bottom."*

The safety net is a **protection available at every tier** — what tiers actually unlock is *control over* that protection (like setting your own percentage), never the protection itself. After it triggers, a **shadow benchmark** shows how the outcome compares to what would have happened if the user had ignored the safety net entirely. In the demo's price data, this saves $182.40 at the lowest point — but if the replay continues all the way to Day 90, the price recovers and the safety net ends up costing $68.00 net instead. Showing both outcomes honestly is the whole point: protection isn't free.

---

## 3. Measuring impact, and how we'd validate it

Rich-HER measures success by **demonstrated understanding**, not by how much someone trades.

* **Two built-in comprehension questions.** After the first trade: "$1,000 falls 10%; what is it worth?" After the first safety-net trigger: "What does a stop-loss do?" Every attempt at answering gets logged.
* **Testing with strangers.** Before judging, 3–5 people with no finance background go through the whole flow. The target: **at least 4 of 5 correctly explain how a stop-loss works on their first try**, which becomes a pitch line generated automatically from the log: *"4 of 5 first-time users explained how a stop-loss works."*
* **Zero-jargon order confirmations.** 100% of order tickets require a Tap-to-Explain review (leading with the downside, with the Confirm button locked for 1.5 seconds) before an order can actually be placed.

---

## 4. A quick technical overview

Rich-HER runs entirely on one laptop, with no internet connection needed, so a live demo never depends on venue Wi-Fi working.

* **Client (plain JavaScript, SVG graphics, CSS).** No build step, no external dependencies; uses fonts already on the computer, loads nothing from the network.
* **Server (Python, FastAPI).** One process handles both the API and serving the app itself. It's the single source of truth — every action returns the complete new state, and the browser never calculates a trade fill on its own.
* **Simulation engine (`server/sim_engine.py`).** Pure, deterministic rules for fills, stops, and the safety-net trigger — tested without needing a server running at all, and portable to another programming language if needed.
* **Recovery.** The browser keeps the server's own log of past actions. After a restart, it replays that log through the normal routes, and the session comes back exactly as it was.

Full technical contract: [SPEC.md](SPEC_v3.0.md).

---

## 5. Being honest about our limitations

A tool that teaches about risk should also be upfront about its own.

* **Made-up prices.** The replay isn't real market history, and real markets are messier and less predictable than this.
* **Simplified order fills.** Market orders fill at the day's closing price. Stop orders fill at the stop price, unless the price jumps past it overnight — in which case they fill worse than expected. Real trades also involve spreads and slippage that this doesn't model.
* **A small sample size.** Testing with three to five people is a basic sanity check on whether the teaching approach works, not a rigorous study.
* **The safety net isn't free.** It can sell you out right at the bottom of a dip, which is exactly why the shadow benchmark reports the cost as honestly as it reports the benefit.
* **Educational only.** Nothing in this product is financial advice.
* **One shared session.** The server keeps a single session in memory, so a hosted link is meant for looking around, not for multiple people using it at once.

---

## 6. Where this could go beyond HackHERS

Rich-HER points toward a broader idea: **protective fintech** — helping people graduate from a guided practice environment to real market participation, with good risk habits already built in. The architecture leaves room for adding real paper trading (through a service like Alpaca) and live market data, though neither is built yet. The next real step would be measuring whether the habits learned here actually carry over.
