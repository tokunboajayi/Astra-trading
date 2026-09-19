# Rich-HER / Astra Trading: White Paper

> **ARCHIVED.** Written against the v3.0 thesis. The current thesis is in
> [SPEC_3.md](../SPEC_3.md). Useful for the pitch narrative; check any claim against the
> current spec before using it.

**Empowering Financial Autonomy Through Downside-First Risk Literacy and Progressive Simulation**

---

## Executive Summary

Traditional retail brokerage and "gamified" trading platforms suffer from a fundamental design flaw: they optimize for transaction volume and dopamine-driven upside bias. For beginners, disproportionately women and historically underserved investors, this creates a dangerous dichotomy between intimidating complexity and reckless speculation.

**Rich-HER** (code-named **Astra Trading**) is a pedagogical trading interface built for HackHERS. Instead of enticing users with uncalibrated promises of wealth, Rich-HER pioneers **downside-first risk literacy**. It couples an interactive price replay ("walk into the dip") with progressive complexity tiers and a proactive safety net, turning market intimidation into risk-aware confidence.

---

## 1. The Core Problem: The Risk-Literacy and Confidence Gap

1. **The asymmetric learning curve.** Novices are routinely introduced to markets during bull runs or through oversimplified interfaces that obscure mechanics like slippage, volatility and capital preservation.
2. **Upside-biased framing.** Standard interfaces describe a "Buy" order in terms of ownership and upside while burying downside risk in legal disclaimers. When a correction arrives, beginners panic-sell at local bottoms.
3. **Interface overload versus toy simulators.** Existing tools offer either wall-of-numbers terminal software (which induces paralysis) or fantasy paper trading in disconnected live time, with no teachable moments on demand.

---

## 2. The Rich-HER Solution: Four Foundational Pillars

### Pillar 1: Downside-first pedagogy
Every order type, indicator and action leads with its loss profile. Before explaining how an instrument generates return, Rich-HER says what capital is at risk and how the order can fail.
* *Instead of* "Buy: own shares of Apple and grow your portfolio", *Rich-HER says:* "If the price falls, your shares are worth less right away, and you could lose some or all of the money you put in. Buying swaps your cash for shares."
* The rule is enforced, not just intended: a test fails if any hint's first field is not the downside or if its downside line names no loss.

### Pillar 2: Deterministic replay ("walk into the dip")
Live paper trading means weeks of waiting for a meaningful move and an unpredictable demo. Rich-HER replays **deterministic 90-day price paths** that a user advances one day at a time, with the future hidden, so a pullback takes minutes to experience in a safe, guided sandbox.

The paths are **synthetic**. A seeded script generates them, pinned to chosen anchor prices, and the HLX path carries a built-in **−22.7% drawdown** so the teaching moment is guaranteed rather than hoped for. The product labels the data as synthetic everywhere it appears. Fast-forward stops the instant something happens, so a fill or the safety-net prompt can never be skipped.

### Pillar 3: Structural progressive complexity (tiers)
Complex tools are neither hidden nor dumped on day one. Tiers unlock by demonstrating understanding, not by trading more.

| Tier | Orders | Chart | Unlocked by |
|---|---|---|---|
| **1 Foundation** | Market | Clean line | Everyone starts here |
| **2 Tactical Protection** | + Limit; choose your own safety-net distance | Line with the high and low so far | A correct answer to the downside check after your first trade |
| **3 Strategic Mastery** | + Stop orders | Candlesticks and moving-average signals | A correct answer to the stop-loss check after your first safety net |

Beginners can use the **tier scrub** to *preview* what they unlock. It is a read-only look at the next tier, not a shortcut past it. Someone who has traded before can start at Tier 2.

### Pillar 4: The proactive safety net
When a position is down 8%, Rich-HER intervenes with a one-tap prompt built from the user's own numbers:

> *"Your HLX position is down 8.2%. You bought 10 at $168.00; it is now $154.17, so you are down $138.30. If it falls to $151.20 your shares are sold automatically. If it dips there and bounces back, you will have sold at the bottom."*

The safety net is a **guardrail available at every tier**. Tiers unlock *control over* protection, never the protection itself. After it acts, a **shadow benchmark** compares the outcome with ignoring the net. In the demo replay it saves $182.40 at the trough; if the replay runs on to Day 90 the price recovers and the net has cost $68.00. Showing both is the point: protection has a price.

---

## 3. Measurable Impact and Validation Strategy

Rich-HER measures success by **demonstrated comprehension**, not by trading volume.

* **Two built-in checks.** After the first trade: "$1,000 falls 10%; what is it worth?" After the first safety net: "What does a stop-loss do?" Every attempt is logged.
* **Stranger-QA.** Before judging, 3–5 non-finance people run through the flow. The target is **at least 4 of 5 answering the stop-loss check correctly on the first try**, reported as a pitch line generated from the log: *"4 of 5 first-time users explained how a stop-loss works."*
* **Zero-jargon order tickets.** 100% of tickets require a Tap-to-Explain review (the downside first, and Confirm locked for 1.5 seconds) before an order can be sent.

---

## 4. Technical Architecture Overview

Rich-HER runs entirely on one laptop, with no internet, to keep a live demo from depending on venue Wi-Fi.

* **Client (vanilla JS, SVG, CSS).** No build step and no dependencies; system fonts, nothing loaded from the network.
* **Server (Python, FastAPI).** One process serves the API and the app. It is the source of truth: every action returns the full new state, and the browser never computes a fill.
* **Simulation engine (`server/sim_engine.py`).** Pure, deterministic rules for fills, stops and the safety-net trigger, unit-tested without a server and portable to another language.
* **Recovery.** The browser keeps the server's action log; after a restart it replays the log through the normal routes and the session returns exactly.

Full contract: [SPEC.md](SPEC_v3.0.md).

---

## 5. Honest Limitations

A tool that teaches risk should be candid about its own.

* **Synthetic prices.** The replay is not real market history, and real markets are messier.
* **Idealized fills.** Market orders fill at the day's close. Stops fill at the stop price unless the price gaps through it, and then they fill worse. Real fills also have spreads and slippage.
* **A small sample.** Three to five testers is a sanity check on whether the teaching works, not a study.
* **The safety net is not free.** It can sell you out at the bottom, which is why the shadow benchmark reports the cost as honestly as the benefit.
* **Educational only.** Nothing here is financial advice.
* **One demo session.** The server keeps a single in-memory session, so a shared hosted link is a place to look around, not a multi-user service.

---

## 6. Vision Beyond HackHERS

Rich-HER points toward **protective fintech**: graduating users from a curated sandbox to real market participation with risk habits already built in. The architecture leaves room for Alpaca paper trading and live data; neither is built. The next step is measuring whether the habits transfer.
