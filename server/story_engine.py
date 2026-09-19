"""
server/story_engine.py

Pure, deterministic story engine for Rich-HER. Same rules as sim_engine.py:
no FastAPI, no I/O, no clock, no randomness. Every function maps inputs to outputs,
so the narrative rules are unit-tested without a server.
Owned by B (Backend). Contract: STORY.md.

The three things this file does:

  1. Walk a scene graph   -> next_scene()
  2. Evaluate conditions  -> matches()
  3. Pick an ending       -> choose_ending()

Scenes, conditions and endings are plain dicts loaded from story/*.json and
web/scenes/*.json. Nothing here is ever eval'd: a condition is data, so a writer
can edit content files without being able to execute code.
"""

WISH_LINE = 110.0        # Vela grants a wish at or above this
BUST_LINE = 90.0         # Vela reclaims the money at or below this
START_CAPITAL = 100.0

# Flags a choice may set. Anything outside this set is a typo and is rejected loudly,
# because a misspelled flag would silently make an ending unreachable.
KNOWN_FLAGS = frozenset({
    "panicked_at_trough", "held_through_drop", "overtraded", "went_all_in",
    "diversified", "took_money_out", "held_the_line", "refused_the_wish",
})

# Fields computed from the portfolio. Never stored, so they cannot drift.
KNOWN_COMPUTED = frozenset({
    "equity", "equity_pct", "cash", "trade_count", "position_count",
    "worst_equity_seen", "vs_wish", "vs_bust", "start_capital",
})

# Effects a choice may apply to the real portfolio. The engine only NAMES them; main.py
# applies them, because touching money is I/O and this file stays pure. An effect outside
# this set is a typo and is rejected loudly - otherwise a pressure event would set its flag
# and silently move no money, which is very hard to debug from the content side.
KNOWN_EFFECTS = frozenset({"withdraw", "deposit"})

OPERATORS = {
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
}


class StoryError(Exception):
    """A malformed story file. `code` is stable and machine-readable."""

    def __init__(self, code, message, **extra):
        super().__init__(message)
        self.code, self.message, self.extra = code, message, extra


# --------------------------------------------------------------------- computed state

def compute(equity, cash, trades, positions, worst_equity_seen, start_capital=START_CAPITAL):
    """Everything a condition may test, derived from the portfolio.

    Recomputed on every request from the sim's own numbers, so the story can never
    disagree with the trading screen.
    """
    equity = round(equity, 2)
    return {
        "equity": equity,
        "equity_pct": round((equity / start_capital - 1) * 100, 2),
        "cash": round(cash, 2),
        "trade_count": len(trades),
        "position_count": len(positions),
        "worst_equity_seen": round(min(worst_equity_seen, equity), 2),
        "vs_wish": round(equity - start_capital * 1.10, 2),
        "vs_bust": round(equity - start_capital * 0.90, 2),
        "start_capital": round(start_capital, 2),
    }


def derive_flags(computed, trades, positions, sold_at_worst):
    """Flags the engine can work out for itself, so content never has to set them.

    A choice may still set its own flags on top of these (see apply_choice).
    """
    flags = set()
    if computed["trade_count"] > 6:
        flags.add("overtraded")
    if computed["position_count"] > 1:
        flags.add("diversified")
    if sold_at_worst:
        flags.add("panicked_at_trough")
    # "all in" means one position held more than 75% of the account at entry.
    for pos in positions:
        if pos.get("cost", 0) > computed["start_capital"] * 0.75:
            flags.add("went_all_in")
    return flags


# --------------------------------------------------------------------- conditions

def matches(condition, computed, flags):
    """Is this condition true? Conditions are data, never expressions.

        {"all": [{"computed": "equity", "gte": 110}, {"flag": "diversified", "is": True}]}

    Combinators: all, any, not. Leaf: {"computed": <field>, <op>: <value>} or
    {"flag": <name>, "is": <bool>}. An empty or missing condition is always true,
    so an ending with no `when` is the catch-all.
    """
    if not condition:
        return True

    if "all" in condition:
        return all(matches(c, computed, flags) for c in condition["all"])
    if "any" in condition:
        return any(matches(c, computed, flags) for c in condition["any"])
    if "not" in condition:
        return not matches(condition["not"], computed, flags)

    if "flag" in condition:
        name = condition["flag"]
        if name not in KNOWN_FLAGS:
            raise StoryError("UNKNOWN_FLAG", f"Unknown flag {name!r}.", flag=name)
        return (name in flags) == condition.get("is", True)

    if "computed" in condition:
        field = condition["computed"]
        if field not in KNOWN_COMPUTED:
            raise StoryError("UNKNOWN_FIELD", f"Unknown computed field {field!r}.", field=field)
        value = computed[field]
        ops = [k for k in condition if k in OPERATORS]
        if not ops:
            raise StoryError("NO_OPERATOR", f"Condition on {field!r} has no operator.", field=field)
        return all(OPERATORS[op](value, condition[op]) for op in ops)

    raise StoryError("BAD_CONDITION", f"Condition is neither a combinator nor a leaf: {condition!r}")


# --------------------------------------------------------------------- traversal

def get_scene(graph, scene_id):
    """One scene by id, or a clear error naming what was asked for."""
    scene = graph.get("nodes", {}).get(scene_id)
    if scene is None:
        raise StoryError("UNKNOWN_SCENE", f"There is no scene {scene_id!r}.", scene_id=scene_id)
    return scene


def next_scene(graph, scene_id, option_id=None):
    """Where does this scene go? Returns the next scene id.

    A `choice` scene needs an option_id; everything else follows its single `goto`.
    """
    scene = get_scene(graph, scene_id)
    respond = scene.get("respond") or {}

    if respond.get("type") == "choice":
        if option_id is None:
            raise StoryError("CHOICE_REQUIRED", "This scene needs a choice.", scene_id=scene_id,
                             options=[o["id"] for o in respond.get("options", [])])
        for opt in respond.get("options", []):
            if opt["id"] == option_id:
                return opt["goto"]
        raise StoryError("UNKNOWN_OPTION", f"No option {option_id!r} on {scene_id}.",
                         scene_id=scene_id, options=[o["id"] for o in respond.get("options", [])])

    if option_id is not None:
        raise StoryError("NOT_A_CHOICE", f"{scene_id} takes no choice.", scene_id=scene_id)
    goto = respond.get("goto")
    if not goto:
        raise StoryError("DEAD_END", f"{scene_id} has no way out.", scene_id=scene_id)
    return goto


def apply_choice(graph, scene_id, option_id, flags):
    """The consequences of one choice: (new_flags, effect).

    `effect` is whatever the option declares - e.g. {"withdraw": 40} - and is applied
    by the caller against the real portfolio. The engine stays pure.
    """
    scene = get_scene(graph, scene_id)
    for opt in (scene.get("respond") or {}).get("options", []):
        if opt["id"] == option_id:
            new = set(flags)
            for name in opt.get("sets", []):
                if name not in KNOWN_FLAGS:
                    raise StoryError("UNKNOWN_FLAG", f"Option sets unknown flag {name!r}.", flag=name)
                new.add(name)
            effect = opt.get("effect") or {}
            for key in effect:
                if key not in KNOWN_EFFECTS:
                    raise StoryError("UNKNOWN_EFFECT", f"Option declares unknown effect {key!r}.",
                                     effect=key, known=sorted(KNOWN_EFFECTS))
            return new, effect
    raise StoryError("UNKNOWN_OPTION", f"No option {option_id!r} on {scene_id}.", scene_id=scene_id)


def visible(scene, computed, flags):
    """The scene as the browser receives it: content plus the media slot, no internals.

    `media` is an opaque slot name. The backend never knows what it looks like, which is
    what lets storyboarding happen without touching Python (STORY.md section 0).
    """
    return {
        "id": scene.get("id"),
        "speaker": scene.get("speaker", "coach"),
        "stage": scene.get("stage"),
        "media": scene.get("media"),
        "skippable": scene.get("skippable", True),
        "duration_hint_ms": scene.get("duration_hint_ms"),
        "lines": list(scene.get("lines", [])),
        "loss": scene.get("loss"),
        "next": scene.get("next"),
        "respond": scene.get("respond"),
        "facts": scene.get("facts"),
    }


# --------------------------------------------------------------------- endings

def choose_ending(endings, computed, flags):
    """First ending whose condition matches, in priority order.

    Endings are ordered by their `priority` (lowest first), so the list in the JSON can
    be in any order and the resolution is still deterministic. Deliberately NOT ranked by
    money: see STORY.md section 8.
    """
    for ending in sorted(endings, key=lambda e: e.get("priority", 999)):
        if matches(ending.get("when"), computed, flags):
            return ending
    raise StoryError("NO_ENDING", "No ending matched. One ending must be a catch-all.")


def wager_state(computed):
    """Where she stands against Vela's two lines, scaled to this session's capital."""
    equity = computed["equity"]
    WISH = round(computed["start_capital"] * 1.10, 2)
    BUST = round(computed["start_capital"] * 0.90, 2)
    return {
        "wish_line": WISH,
        "bust_line": BUST,
        "equity": equity,
        "above_wish": equity >= WISH,
        "below_bust": equity <= BUST,
        "verdict": "wish" if equity >= WISH else ("bust" if equity <= BUST else "open"),
    }
