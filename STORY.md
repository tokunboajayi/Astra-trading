# Story architecture

How the narrative layer works, what the backend must implement, and where the storyboard
plugs in. **Written so backend work and storyboarding can happen in parallel.**

---

## 0. The architectural promise

The backend never needs to know what an animation looks like. It only needs to know that a
beat exists, when it plays, and what it can branch on.

```
sim_engine.py     (exists)   the market maths      - pure, no I/O
story_engine.py   (NEW)      scenes, flags, branching, endings - pure, no I/O
main.py           (exists)   session + HTTP, now also drives the story
story/*.json      (NEW)      the actual words and branches
```

`story_engine.py` follows the same rule as `sim_engine.py`: **no I/O, no clock, no
randomness, no framework.** Plain dicts in, plain dicts out, unit-testable without a server.

**This means the backend can be finished before a single frame of animation exists.**
Every interstitial declares a `media` slot by name (`"media": "slot:wizard-arrives"`). The
backend passes the slot name through to the browser. The browser renders whatever is
registered under that name — an SVG, a Lottie file, a CSS sequence, or nothing at all
during development. Storyboarding fills the slots later without touching a `.py` file.

---

## 1. Characters

### Nia Okafor — the coach
Exists in `web/coach.json`. Warm, plain-spoken, on her side. Explains, never judges.
**Nia is safety.**

### Vela — the wizard
The one who gifts the $100 and sets the wager. **Vela is a woman.**

That is a deliberate call. This product exists because women opt out of investing. A story
where a *man* hands a woman money and then judges how she manages it reproduces the exact
dynamic we are trying to dissolve. A powerful, enigmatic woman who sets hard terms and
respects her enough to let her fail is a better fit, and it gives us two female characters
in two different registers:

| | Nia | Vela |
|---|---|---|
| Register | warm, present, patient | cool, intermittent, transactional |
| Function | teaches | tests |
| Speaks in | plain dollars | terms and conditions |
| Wants | that she understands | that she performs |
| Right about | almost everything | the one thing she's wrong about (below) |

**Vela is an unreliable narrator, and that is the engine of the whole story.**

She frames investing as a wager: beat +10% and win a wish, lose 10% and forfeit. That
framing is *wrong*, and the endings are built to reveal it. The best ending is not the
richest one. Vela believes the money is the point. By the end, the player knows better.

This is what keeps the wager from becoming a scoreboard — and a scoreboard is precisely the
thing the research says drives women out.

---

## 2. The wager

> "One hundred dollars. It was never yours, so you cannot truly lose it.
> Grow it by a tenth and I grant you one wish. Lose a tenth and I take it back,
> and you keep nothing but what you learned. Which, I suspect, you will undervalue."
> — Vela, Prologue

| Threshold | Value | Meaning |
|---|---|---|
| Wish line | **$110.00** | +10% — Vela grants a wish |
| Bust line | **$90.00** | −10% — Vela reclaims the money |
| Between | $90.01–$109.99 | Vela calls it nothing. **The story calls it the real win.** |

### When Vela evaluates — and why it matters

Vela checks at **checkpoints**, not continuously. Checkpoint placement is a design weapon:

Measured against the shipped NVX arc ($21.00 entry, $100 account):

| Her Chapter 3 sizing | At the trough (Ch4) | At the end |
|---|---|---|
| All in — 4 shares, $84 | **$82.48 — BUSTS** | $95.00 |
| Half in — 2 shares, $42 | $91.24 — survives | $97.50 |
| A toe in — 1 share, $21 | $95.62 — survives | $98.75 |

**Vela appears at the trough.** That is the emotional-control test in one move: the
all-in player is *below the bust line at the moment the wizard is standing there*, and the
price recovers afterwards. The question the whole product asks — do you act on the worst
moment? — becomes a scene.

Sizing decided the outcome before the scene began. That is the risk-management lesson, and
it is now load-bearing plot.

---

## 3. BLOCKER: the wish is currently unreachable

| Fixture | $100 fully invested ends at |
|---|---|
| BRW | **$103.92** ← best in the repo |
| BRD | $102.64 |
| KIN | $95.80 |
| HLX | $94.05 |
| VLT | $82.06 |

**The ceiling is $103.92. The wish needs $110.00.** No path through the current data
reaches it. Every player loses Vela's wager, which makes the wager a rigged game and the
product a lesson in futility.

### Required fixture (B, blocking)

One new synthetic symbol, same generator, same `--check` discipline:

| Property | Target |
|---|---|
| Entry price | $18.00–$25.00 (so $100 buys 4–5 shares) |
| Early dip | −6% to −9% around bar 10–15 (the lesson still happens) |
| Recovery | crosses breakeven by ~bar 45 |
| Finish | **+22% to +28%** |

At +25%, a half-in player ($50) reaches $112.50 — clears the wish line with sizing that
also survives the trough. **That is the tuning target: the wish should be reachable by
good process, not only by going all-in.** If all-in is the only way to win, the story
teaches gambling.

Until this fixture exists, build everything else and treat "The Wish Granted" as an ending
that cannot yet fire.

---

## 4. Screen order (revised opening)

The opening now leads with the statistic. Rationale: it does the work of *"this is for you,
and here is why you were held back"* **before** asking her for anything. A person who has
just read that hesitation — not ability — is the barrier answers the experience question
differently.

| # | Screen | Job |
|---|---|---|
| 1 | **The statistic** | The hook. One number, minimal chrome. She clicks to continue. |
| 2 | **Experience** | new / some / confident. Sets starting tone, never gates content. |
| 3 | **Name + avatar** | Now she is invested enough to personalise. |
| 4 | **Vela arrives** | The gift, the wager, the terms. Journey begins. |

Note the reorder: name was first, now it is third. Asking for a name before giving a reason
to care is the weakest possible opening.

---

## 5. Chapter spine with interstitials

Every chapter boundary carries a beat. `int*` entries are the animation slots.

```
S1  stat  ->  S2 experience  ->  S3 name  ->  int:arrival  ->  Vela: the wager
ch1  what a stock is
     int:first-light          slot:int-first-light
ch2  reading the chart                                      [CHECKPOINT: Vela, light touch]
     int:the-offer            slot:int-the-offer
ch3  how much of your $100                                  [CHECKPOINT: Vela sees the size]
     int:waiting              slot:int-waiting
ch4  the drop                                    [CHECKPOINT AT TROUGH - the big one]
     int:aftermath            slot:int-aftermath
ch5  diversification                                        [PRESSURE EVENT fires here]
     int:reckoning            slot:int-reckoning
ch6  endings
```

### Interstitial contract

An interstitial is a scene with a media slot, optional narration, and **no branching**.

```jsonc
{
  "id": "int.aftermath",
  "kind": "interstitial",
  "media": "slot:int-aftermath",      // browser resolves; backend passes through
  "duration_hint_ms": 6000,           // storyboard's estimate; browser may ignore
  "skippable": true,                  // always true - never trap her in a cutscene
  "speaker": "narrator",
  "lines": ["The price stopped falling. Nobody rang a bell."],
  "respond": { "type": "continue", "label": "Go on", "goto": "ch5.open" }
}
```

**Backend treats `media` as an opaque string.** Storyboard can rename, replace or leave
slots empty; nothing server-side changes. `skippable: true` is mandatory — a cutscene you
cannot leave is a dead end, and dead ends are Principle 1.

---

## 6. State model

Two kinds of state, and the split matters.

### Computed — derived from the sim, never stored

Recomputed on every request from the existing portfolio. Cannot drift.

```python
{"equity": 91.24, "equity_pct": -8.76, "cash": 58.0,
 "trade_count": 3, "position_count": 1, "worst_equity_seen": 82.48,
 "vs_wish": -18.76, "vs_bust": 1.24}
```

### Flags — set by choices, stored on the session

Only genuinely narrative facts. If it can be computed, it is not a flag.

| Flag | Set when |
|---|---|
| `panicked_at_trough` | sold while equity was at its lowest point |
| `held_through_drop` | reached ch5 still holding the ch3 position |
| `overtraded` | trade_count > 6 |
| `went_all_in` | any single position > 75% of account |
| `diversified` | held 2+ symbols at once |
| `took_money_out` | accepted the pressure-event withdrawal |
| `refused_the_wish` | declined Vela's wish in the final scene |

### Conditions as data

```jsonc
"when": { "all": [
  { "computed": "equity", "lte": 90 },
  { "flag": "panicked_at_trough", "is": true }
]}
```

Operators: `lt lte gt gte eq neq`. Combinators: `all any not`. **No expressions in JSON** —
a string is never `eval`'d. This keeps content files safe to hand to a writer.

---

## 7. Pressure events

An event that injects a real financial choice at an emotional moment. Fires once, after a
named chapter.

```jsonc
{
  "id": "pressure.request",
  "after_chapter": "ch4",
  "speaker": "narrator",
  "lines": ["Your phone buzzes. Someone you love needs $40, this week."],
  "respond": { "type": "choice", "options": [
    { "id": "send", "label": "Send the $40",
      "effect": { "withdraw": 40 }, "sets": ["took_money_out"], "goto": "pressure.sent" },
    { "id": "keep", "label": "Say you can't right now",
      "sets": ["held_the_line"], "goto": "pressure.kept" }
  ]}
}
```

Withdrawing $40 makes the wish arithmetically much harder and may push her under the bust
line. That is the point: **money has calls on it that have nothing to do with the market.**

### On the hospital storyline — one flag, then your call

The brief suggests a parent in hospital. That produces the strongest pressure, and it
carries two specific costs worth naming once:

1. **It can land on a real wound.** A meaningful share of any audience currently has a
   seriously ill parent. For a product whose entire thesis is *lowering* emotional barriers
   to engagement, a sick-parent scene can do the opposite — and she cannot opt out of it.
2. **It muddies the lesson.** "Should I pull money out for my mother's care?" has an
   obvious correct answer that is not a *trading* answer. The scene stops teaching risk
   management and starts testing whether she is a good daughter.

Alternatives that create the same *"do I break my plan?"* pressure without either cost:

| Option | Pressure | Clean lesson |
|---|---|---|
| A friend asks to borrow $40 | social obligation | liquidity vs. commitment |
| A deposit is due on something she's been saving for | self-directed want | opportunity cost |
| Her car needs a repair to keep working | necessity | emergency fund |
| Vela offers to double it on one coin flip | greed | **process vs. gambling** |

**The default shipped in the schema is the neutral "someone you love needs $40."** It is
one string. Swap it for whatever you decide — no code changes.

That last option (Vela's coin flip) is worth real consideration: it tempts her to reach the
wish by pure chance, and taking it can set `went_all_in`, routing her to *The Hollow Wish*.
It tests the exact thing the product teaches.

---

## 8. Endings

Six endings. **Deliberately not ranked by money.** Vela thinks the money is the score; the
endings prove otherwise. This is how a wager mechanic survives inside a no-score product.

Evaluated in priority order; first match wins.

| # | Ending | Fires when | Vela's closing note |
|---|---|---|---|
| 1 | **The Hollow Wish** | equity ≥ 110 **and** (`went_all_in` or `overtraded`) | Grants it — and it's ash. "You got lucky. Luck is not a method, and it does not come twice." |
| 2 | **The Wish Granted** | equity ≥ 110 | Grants it properly. The wish she asks for is small, because she already got the thing. |
| 3 | **The Panic** | `panicked_at_trough` | Takes the money. Then shows the recovery she sold before. Nia closes it, gently. |
| 4 | **The Untouched Hundred** | `trade_count == 0` | "You kept every dollar and learned nothing. That is the only way to truly lose here." |
| 5 | **The Cost of Certainty** | equity ≤ 90 | Takes it back. Nia's coda: the money was never hers; what she knows now is. |
| 6 | **The Steady Hand** | otherwise (between the lines) | "You did not win my wager. You did something harder. You did not flinch." **The true good ending.** |

Ending 6 is the modal outcome and it is written as the best one. That is the thesis in
structural form: she was never being graded, and the person who told her she was is the one
character in the story who turns out to be wrong.

---

## 9. Backend contract

Three new routes. Everything else is unchanged.

| Route | Body | Returns |
|---|---|---|
| `GET /api/story` | — | `{scene, chapter, computed, flags, media, can_skip}` |
| `POST /api/story/advance` | `{scene_id}` | `{scene, state}` — next beat |
| `POST /api/story/choice` | `{scene_id, option_id}` | `{scene, state, effects_applied}` |

Rules that mirror the existing architecture:

- **Every response carries the full snapshot**, same as the trading routes. The browser
  still never computes anything.
- **Scene transitions are recorded in `replay_log`**, so restart-recovery keeps working.
- **Checkpoints evaluate server-side.** The browser never decides whether she busted.
- **`story_engine.py` stays pure.** `main.py` owns the session; the engine owns the rules.

### Files to add

```
server/story_engine.py        pure: resolve conditions, pick next scene, evaluate endings
story/prologue.json           screens 1-4 and Vela's arrival
story/interstitials.json      the between-chapter beats + media slots
story/checkpoints.json        Vela's appearances and what she evaluates
story/pressure.json           the pressure events
story/endings.json            the six endings and their conditions
server/tests/test_story.py    lint + reachability
```

### Tests the story layer needs

Extending the pattern already in `test_scenes.py`:

1. **Every ending is reachable** — at least one flag/equity combination routes to each.
2. **No unreachable scene** — every scene is the target of some `goto`.
3. **No dead ends** — every scene has a way out (Principle 1).
4. **Every `media` slot is declared once** and named consistently.
5. **Every interstitial is `skippable`.**
6. **Conditions only use known flags and computed fields** — catches a typo'd flag name,
   which would otherwise silently make an ending unreachable.
7. **Wish reachability** — asserts the fixture set can actually produce equity ≥ 110 with
   sizing that also survives the trough. **This test fails today**, by design, until the
   gain fixture lands (section 3).

---

## 10. Build order

| # | Work | Owner | Blocks |
|---|---|---|---|
| 1 | Gain fixture (section 3) | B | endings 1, 2, and test 7 |
| 2 | `story_engine.py` + schema + tests | B | everything narrative |
| 3 | `prologue.json` — screens 1–4 + Vela's arrival | V1 | the opening |
| 4 | Checkpoint scenes, trough one first | V1 | the emotional core |
| 5 | Endings copy | V1 | the payoff |
| 6 | Storyboard the 5 interstitial slots | F + V2 | nothing — slots can stay empty |

Item 6 blocks nothing. That is the point of the slot design: **the product is playable and
the backend is complete with every animation slot empty.**
