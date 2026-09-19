# Story architecture

> **PARKED — the wager and Vela are not in the build.**
>
> The $100 gift, the ±10% wager, the wish, and Vela herself were removed from `main` to keep
> the first release focused. Nothing was deleted: the full implementation lives on the branch
> `feature/vela-wager`, which is pushed and can be merged back whenever you want it.
>
> **What is still live:** the six endings, now narrated by Nia rather than Vela and framed
> around what the player did rather than whether she beat a line. Everything below that
> describes Vela, the wager, checkpoints or the wish is the parked design, kept as the
> blueprint for bringing it back.

How the narrative layer works, what the backend needs to implement, and where the storyboard (the animation/visual design work) plugs in. **Written so backend work and storyboarding can happen at the same time, by different people, without blocking each other.**

> A note on the role abbreviations used throughout: **B** = backend developer, **F** = frontend developer, **V1** = the person writing dialogue/copy, **V2** = the person handling the pitch, deck, and testing with outside users.

---

## 0. The architectural promise

The backend never needs to know what an animation looks like. It only needs to know that a beat (a moment in the story) exists, when it plays, and what it can branch on.

```
sim_engine.py     (exists)   the market maths      - pure, no I/O
story_engine.py   (NEW)      scenes, flags, branching, endings - pure, no I/O
main.py           (exists)   session + HTTP, now also drives the story
story/*.json      (NEW)      the actual words and branches
```

`story_engine.py` follows the same rule as `sim_engine.py`: **no file reading, no clock, no randomness, no framework.** It takes plain data structures in, and returns plain data structures out — which means it can be tested without running a server at all.

**This means the backend can be finished before a single frame of animation exists.** Every interstitial (a between-scenes beat) declares a `media` slot by name (`"media": "slot:wizard-arrives"`). The backend just passes that slot name through to the browser. The browser then renders whatever is registered under that name — an SVG, an animation file, a CSS sequence, or nothing at all during early development. Storyboarding can fill in those slots later without touching a single `.py` file.

---

## 1. Characters

### Nia Okafor — the coach
Already exists in `web/coach.json`. Warm, plain-spoken, on the user's side. Explains, never judges. **Nia represents safety.**

### Vela — the wizard
The one who gifts the $100 and sets the wager (the bet described below). **Vela is a woman.**

That's a deliberate choice. This product exists because women opt out of investing more than men do. A story where a *man* hands a woman money and then judges how she manages it would reproduce the exact dynamic we're trying to dissolve. A powerful, enigmatic woman who sets hard terms — and respects the player enough to let her fail — is a better fit. It also gives us two female characters who play very different roles:

| | Nia | Vela |
|---|---|---|
| Tone | warm, present, patient | cool, appears occasionally, transactional |
| Function | teaches | tests |
| Speaks in | plain dollars | terms and conditions |
| Wants | that she understands | that she performs |
| Right about | almost everything | wrong about one specific thing (below) |

**Vela is an unreliable narrator, and that's what drives the whole story.**

She frames investing as a wager: beat +10% and win a wish, lose 10% and forfeit. That framing is *wrong*, and the endings are built to reveal why. The best ending is not the richest one. Vela believes the money is the point — by the end, the player knows better.

This is what keeps the wager from turning into a scoreboard. A scoreboard is exactly the kind of thing research says drives women away from investing tools.

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
| Between | $90.01–$109.99 | Vela calls this "nothing happened." **The story treats it as the real win.** |

### When Vela checks in — and why the timing matters

Vela checks the player's progress at specific **checkpoints**, not continuously. Where those checkpoints land is a deliberate design choice:

Measured against the shipped NVX story arc ($21.00 entry price, $100 starting account):

| How much she put in, back in Chapter 3 | Value at the lowest point (Chapter 4) | Value at the end |
|---|---|---|
| All in — 4 shares, $84 | **$82.48 — fails ("busts")** | $95.00 |
| Half in — 2 shares, $42 | $91.24 — survives | $97.50 |
| A toe in — 1 share, $21 | $95.62 — survives | $98.75 |

**Vela shows up right at the lowest point.** That's the emotional-control test, condensed into one moment: the player who went all-in is *below the bust line at the exact moment the wizard appears* — even though the price recovers afterward. The question the whole product is built around — do you make decisions based on the worst moment? — becomes a real scene in the story.

Notice that the sizing decision from Chapter 3 already decided this outcome before the scene even began. That's the risk-management lesson, now baked directly into the plot.

---

## 3. Current blocker: the wish is currently unreachable

| Fixture | Ending value if $100 was fully invested |
|---|---|
| BRW | **$103.92** ← best result currently in the repo |
| BRD | $102.64 |
| KIN | $95.80 |
| HLX | $94.05 |
| VLT | $82.06 |

**The best possible outcome right now is $103.92 — but winning the wish requires $110.00.** There's no path through the current price data that reaches it. Every player loses Vela's wager no matter what they do, which makes the wager feel rigged and turns the product into a lesson in futility instead of a lesson in risk management.

### What's needed: a new fixture (owned by B, and this is blocking other work)

One new synthetic symbol (company), using the same generator script and the same `--check` verification:

| Property | Target |
|---|---|
| Entry price | $18.00–$25.00 (so $100 buys 4–5 shares) |
| Early dip | −6% to −9% around day 10–15 (so the "it drops" lesson still happens) |
| Recovery | crosses back to breakeven by around day 45 |
| Finish | **+22% to +28%** |

At +25%, a player who only put in half ($50) would reach $112.50 — clearing the wish line with a sizing decision that also survives the earlier drop. **That's the target: winning the wish should be possible through good decision-making, not only by betting everything.** If going all-in is the only way to win, the story ends up teaching gambling instead of investing.

Until this fixture exists, everything else can be built, but "The Wish Granted" should be treated as an ending that can't fire yet.

---

## 4. Screen order (the revised opening)

The opening now leads with a statistic. The reasoning: it does the work of *"this is for you, and here's why you were held back"* **before** asking the player for anything. Someone who has just read that hesitation — not lack of ability — is the real barrier will answer the next question differently.

| # | Screen | What it does |
|---|---|---|
| 1 | **The statistic** | The hook. One number, minimal decoration. She clicks to continue. |
| 2 | **Experience** | New / some experience / confident. Sets the starting tone — never restricts content. |
| 3 | **Name + avatar** | By now she's invested enough in the experience to personalize it. |
| 4 | **Vela arrives** | The gift, the wager, the terms. The journey begins. |

Note the reorder: the name prompt used to come first — now it's third. Asking for a name before giving someone a reason to care is the weakest possible way to open.

---

## 5. Chapter outline with interstitials

Every chapter boundary has a beat attached to it. Entries starting with `int` are the animation slots.

```
S1  stat  ->  S2 experience  ->  S3 name  ->  int:arrival  ->  Vela: the wager
ch1  what a stock is
     int:first-light          slot:int-first-light
ch2  reading the chart                                      [CHECKPOINT: Vela, light touch]
     int:the-offer            slot:int-the-offer
ch3  how much of your $100                                  [CHECKPOINT: Vela sees the size]
     int:waiting              slot:int-waiting
ch4  the drop                                    [CHECKPOINT AT THE LOWEST POINT - the big one]
     int:aftermath            slot:int-aftermath
ch5  diversification                                        [PRESSURE EVENT fires here]
     int:reckoning            slot:int-reckoning
ch6  endings
```

### The interstitial format

An interstitial is a scene with an animation slot, optional narration, and **no branching choices**.

```jsonc
{
  "id": "int.aftermath",
  "kind": "interstitial",
  "media": "slot:int-aftermath",      // the browser looks this up; the backend just passes it along
  "duration_hint_ms": 6000,           // the storyboard's estimate; the browser is free to ignore it
  "skippable": true,                  // always true - never trap the player in a scene they can't leave
  "speaker": "narrator",
  "lines": ["The price stopped falling. Nobody rang a bell."],
  "respond": { "type": "continue", "label": "Go on", "goto": "ch5.open" }
}
```

**The backend treats `media` as just a string it doesn't understand.** The storyboard team can rename slots, replace them, or leave them empty, and nothing on the server side changes. `skippable: true` is required on every one of these — a cutscene the player can't leave is a dead end, and avoiding dead ends is our first design principle.

---

## 6. State model

There are two different kinds of state here, and the difference matters.

### Computed values — calculated fresh every time, never stored

These are recalculated on every request from the player's actual trading activity, so they can never drift out of sync.

```python
{"equity": 91.24, "equity_pct": -8.76, "cash": 58.0,
 "trade_count": 3, "position_count": 1, "worst_equity_seen": 82.48,
 "vs_wish": -18.76, "vs_bust": 1.24}
```

### Flags — set by player choices, saved to their session

These only track facts that genuinely can't be calculated — if something *can* be computed, it shouldn't be a flag.

| Flag | Set when |
|---|---|
| `panicked_at_trough` | player sold while their account value was at its lowest point |
| `held_through_drop` | player still held their Chapter 3 position by Chapter 5 |
| `overtraded` | player made more than 6 trades |
| `went_all_in` | any single position was more than 75% of the account |
| `diversified` | player held 2 or more companies' shares at once |
| `took_money_out` | player accepted the pressure-event withdrawal (see section 7) |
| `refused_the_wish` | player declined Vela's wish in the final scene |

### Conditions, written as data

```jsonc
"when": { "all": [
  { "computed": "equity", "lte": 90 },
  { "flag": "panicked_at_trough", "is": true }
]}
```

Comparisons available: `lt lte gt gte eq neq` (less than, less than or equal, etc). Ways to combine them: `all any not`. **Nothing here is ever executed as code** — a string in this file never gets run as a program. That keeps the content files safe to hand to a writer who isn't a programmer.

---

## 7. Pressure events

An event that introduces a real financial decision at an emotionally charged moment. Each fires once, after a specific chapter ends.

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

Withdrawing $40 makes winning the wish significantly harder, and might push the player under the bust line. That's the point: **money has real-world demands on it that have nothing to do with the market.**

### About using a hospital storyline for this — worth thinking through first

One early idea for this scene was a parent in the hospital. That would create very strong emotional pressure, but it comes with two real costs worth naming:

1. **It can land on a real, painful memory.** A meaningful portion of any audience currently has a seriously ill parent. For a product whose entire point is *lowering* emotional barriers, a sick-parent scene risks doing the opposite — and the player can't opt out of seeing it.
2. **It muddies the lesson.** "Should I pull money out for my mother's care?" has an obvious right answer that isn't really about trading at all. The scene stops teaching risk management and starts testing whether the player is a good daughter, which isn't what this product is for.

Some alternatives that create the same "do I break my plan?" tension without either of those costs:

| Option | Kind of pressure | What it actually teaches |
|---|---|---|
| A friend asks to borrow $40 | social obligation | liquid cash vs. money that's committed elsewhere |
| A deposit is due on something she's been saving for | a want, not a need | opportunity cost |
| Her car needs a repair to keep running | necessity | the value of an emergency fund |
| Vela offers to double it on one coin flip | greed | process vs. gambling |

**The version currently shipped in the code is the neutral "someone you love needs $40."** It's a single string of text — swap it for whichever option you decide on, no code changes needed.

That last option (Vela's coin flip) is worth genuine consideration: it tempts the player to try reaching the wish through pure luck, and choosing it can set the `went_all_in` flag, routing her toward *The Hollow Wish* ending. It tests exactly the thing the product is trying to teach.

---

## 8. Endings

There are six possible endings. **They are deliberately not ranked by how much money the player ends up with.** Vela thinks the money is the score; the endings exist to prove she's wrong. This is what keeps the wager mechanic from turning into a scoreboard, even though a no-score product wouldn't normally have a "win condition" at all.

Checked in this order — the first one that matches, wins.

| # | Ending | Fires when | Vela's closing line |
|---|---|---|---|
| 1 | **The Hollow Wish** | equity ≥ 110 **and** (`went_all_in` or `overtraded`) | Grants it — and it feels empty. "You got lucky. Luck is not a method, and it does not come twice." |
| 2 | **The Wish Granted** | equity ≥ 110 | Grants it properly. The wish she asks for is small, because she already got the thing that mattered. |
| 3 | **The Panic** | `panicked_at_trough` | Vela takes the money. Then the story shows the recovery she sold before it happened. Nia closes it out gently. |
| 4 | **The Untouched Hundred** | `trade_count == 0` | "You kept every dollar and learned nothing. That is the only way to truly lose here." |
| 5 | **The Cost of Certainty** | equity ≤ 90 | Vela takes it back. Nia's closing note: the money was never really hers — what she knows now is. |
| 6 | **The Steady Hand** | everything else (in between the two lines) | "You did not win my wager. You did something harder. You did not flinch." **This is the true "good" ending.** |

Ending 6 is the most common outcome, and it's written to be the best one on purpose. That's the whole thesis of the product, expressed in the structure of the story itself: she was never actually being graded, and the one character who told her she was turns out to be wrong.

---

## 9. What the backend needs to build

Three new routes. Everything else stays the same.

| Route | Body | Returns |
|---|---|---|
| `GET /api/story` | — | `{act, scene, computed, flags, wager, acts}` |
| `POST /api/story/advance` | `{scene_id}` | `{scene, state}` — the next beat |
| `POST /api/story/choice` | `{scene_id, option_id}` | `{scene, state, effects_applied}` |

Rules that follow the same pattern as the rest of the app:

- **Every response carries the full snapshot**, exactly like the trading routes do. The browser still never calculates anything on its own.
- **Scene transitions get recorded in `replay_log`**, so restart-recovery keeps working the same way it does for trading.
- **Checkpoints are evaluated on the server.** The browser never decides on its own whether the player has "busted."
- **`story_engine.py` stays pure** — no I/O. `main.py` owns the session state; the engine owns the rules for how the story branches.

### Current status: built

`server/story_engine.py`, the five routes, `web/scenes/act4.json`, `web/scenes/endings.json`, and `web/coach.json` all exist and are covered by tests (197 tests total). Choice effects can move real money — for example `{"withdraw": 40}` reduces the player's cash, and is refused with a `409 CANNOT_WITHDRAW` error if they can't afford it. An unknown effect or flag name causes an error rather than silently doing nothing, so a typo can't quietly break a scene.

**What's left is content, not code:** Acts 1, 2, 3, 5, and 6, the four prologue screens, Vela's checkpoint scenes, and the interstitials are all still unwritten. Each one is just a JSON file following the same shape as Act 4 — no Python changes needed for any of them.

### Files still to add

```
server/story_engine.py        pure: resolve conditions, pick next scene, evaluate endings
story/prologue.json           screens 1-4 and Vela's arrival
story/interstitials.json      the between-chapter beats + media slots
story/checkpoints.json        Vela's appearances and what she evaluates
story/pressure.json           the pressure events
story/endings.json            the six endings and their conditions
server/tests/test_story.py    checks the content for correctness + reachability
```

### Tests the story layer still needs

Extending the same pattern already used in `test_scenes.py`:

1. **Every ending is reachable** — there's at least one combination of flags/equity that routes to each one.
2. **No unreachable scenes** — every scene is the target of at least one `goto` link.
3. **No dead ends** — every scene has a way out (our first design principle).
4. **Every `media` slot is declared exactly once** and named consistently.
5. **Every interstitial is `skippable`.**
6. **Conditions only reference flags and computed fields that actually exist** — this catches a typo'd flag name, which would otherwise silently make an ending unreachable without anyone noticing.
7. **The wish is actually reachable** — confirms the fixture set can produce equity ≥ 110 with a sizing choice that also survives the drop. **This test fails today, on purpose**, until the new gain fixture (section 3) is built.

---

## 10. Suggested build order

| # | Work | Owner | What it blocks |
|---|---|---|---|
| 1 | Gain fixture (section 3) | B | Endings 1, 2, and test 7 |
| 2 | `story_engine.py` + schema + tests | B | everything narrative |
| 3 | `prologue.json` — screens 1–4 + Vela's arrival | V1 | the opening |
| 4 | Checkpoint scenes, starting with the trough one | V1 | the emotional core of the story |
| 5 | Endings copy | V1 | the payoff |
| 6 | Storyboard the 5 interstitial slots | F + V2 | nothing — slots can stay empty in the meantime |

Item 6 doesn't block anything else. That's the whole point of designing it around named "slots": **the product is fully playable, and the backend is complete, even with every animation slot left empty.**
