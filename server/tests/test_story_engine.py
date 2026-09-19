"""
server/tests/test_story_engine.py

Unit tests for the pure story engine, plus reachability checks over the real content.
No server needed: story_engine.py has no I/O, same as sim_engine.py.
"""

import json
from pathlib import Path

import pytest

from server import story_engine as story

ROOT = Path(__file__).resolve().parent.parent.parent
ENDINGS = json.loads((ROOT / "web" / "scenes" / "endings.json").read_text(encoding="utf-8"))
ACT4 = json.loads((ROOT / "web" / "scenes" / "act4.json").read_text(encoding="utf-8"))


def state(equity, trades=0, positions=0, worst=None):
    return story.compute(equity, 0.0, [None] * trades, [None] * positions,
                         equity if worst is None else worst)


# ------------------------------------------------------------------ conditions

def test_a_missing_condition_is_always_true():
    assert story.matches(None, state(100), set()) is True
    assert story.matches({}, state(100), set()) is True


@pytest.mark.parametrize("equity,expected", [(109.99, False), (110.0, True), (150.0, True)])
def test_a_computed_comparison(equity, expected):
    assert story.matches({"computed": "equity", "gte": 110}, state(equity), set()) is expected


def test_all_any_and_not_combine():
    c, f = state(120), {"went_all_in"}
    assert story.matches({"all": [{"computed": "equity", "gte": 110}, {"flag": "went_all_in"}]}, c, f)
    assert story.matches({"any": [{"computed": "equity", "gte": 999}, {"flag": "went_all_in"}]}, c, f)
    assert story.matches({"not": {"flag": "diversified"}}, c, f)


def test_a_typo_in_a_flag_name_fails_loudly():
    """A silent typo would make an ending permanently unreachable, so it must raise."""
    with pytest.raises(story.StoryError) as e:
        story.matches({"flag": "paniked_at_trough"}, state(100), set())
    assert e.value.code == "UNKNOWN_FLAG"


def test_a_typo_in_a_computed_field_fails_loudly():
    with pytest.raises(story.StoryError) as e:
        story.matches({"computed": "equitee", "gte": 1}, state(100), set())
    assert e.value.code == "UNKNOWN_FIELD"


def test_a_condition_with_no_operator_is_rejected():
    with pytest.raises(story.StoryError) as e:
        story.matches({"computed": "equity"}, state(100), set())
    assert e.value.code == "NO_OPERATOR"


# ------------------------------------------------------------------ traversal

def test_walking_a_continue_scene():
    assert story.next_scene(ACT4, "act4.open") == "act4.drop5"


def test_a_choice_scene_needs_an_option():
    with pytest.raises(story.StoryError) as e:
        story.next_scene(ACT4, "act4.drop5")
    assert e.value.code == "CHOICE_REQUIRED"
    assert set(e.value.extra["options"]) == {"sell", "hold", "more"}


@pytest.mark.parametrize("option,target", [
    ("sell", "act4.chose.sell"), ("hold", "act4.chose.hold"), ("more", "act4.chose.more")])
def test_each_choice_goes_where_it_says(option, target):
    assert story.next_scene(ACT4, "act4.drop5", option) == target


def test_an_unknown_option_is_rejected():
    with pytest.raises(story.StoryError) as e:
        story.next_scene(ACT4, "act4.drop5", "panic")
    assert e.value.code == "UNKNOWN_OPTION"


def test_an_unknown_scene_is_rejected():
    with pytest.raises(story.StoryError) as e:
        story.get_scene(ACT4, "act4.nope")
    assert e.value.code == "UNKNOWN_SCENE"


def test_the_visible_scene_carries_the_media_slot_and_no_internals():
    """The browser gets an opaque slot name; the backend never knows what it renders."""
    v = story.visible({"id": "x", "media": "slot:int-aftermath", "lines": ["hi"],
                       "respond": {"type": "continue", "goto": "y"}, "internal": "secret"},
                      state(100), set())
    assert v["media"] == "slot:int-aftermath"
    assert v["skippable"] is True
    assert "internal" not in v


# ------------------------------------------------------------------ endings

def test_every_ending_is_reachable():
    """An ending nobody can ever reach is dead content. Each must fire for some state."""
    cases = {
        "hollow_wish": (state(120), {"went_all_in"}),
        "wish_granted": (state(120), set()),
        "the_panic": (state(95), {"panicked_at_trough"}),
        "untouched_hundred": (state(100, trades=0), set()),
        "cost_of_certainty": (state(85, trades=3), set()),
        "steady_hand": (state(102, trades=3), set()),
    }
    for expected, (computed, flags) in cases.items():
        got = story.choose_ending(ENDINGS["endings"], computed, flags)
        assert got["id"] == expected, f"expected {expected}, got {got['id']}"


def test_priority_order_decides_when_two_endings_both_match():
    """+10% reached by going all in is the hollow wish, not the clean one."""
    got = story.choose_ending(ENDINGS["endings"], state(130), {"went_all_in"})
    assert got["id"] == "hollow_wish"


def test_there_is_always_an_ending():
    """The catch-all must exist, or a player could finish with nothing to show her."""
    got = story.choose_ending(ENDINGS["endings"], state(101, trades=2), set())
    assert got["id"] == "steady_hand"


def test_every_ending_has_words_for_both_characters():
    for e in ENDINGS["endings"]:
        assert e["lines"] and e["next"], f"{e['id']} has no Vela copy"
        assert e["coach_coda"], f"{e['id']} has no coda from Nia"


# ------------------------------------------------------------------ the wager

@pytest.mark.parametrize("equity,verdict", [(110.0, "wish"), (125.0, "wish"),
                                            (90.0, "bust"), (82.48, "bust"),
                                            (100.0, "open"), (109.99, "open")])
def test_the_wager_verdict(equity, verdict):
    assert story.wager_state(state(equity))["verdict"] == verdict


def test_derived_flags():
    assert "overtraded" in story.derive_flags(state(100, trades=7), [None] * 7, [], False)
    assert "diversified" in story.derive_flags(state(100, positions=2), [], [{}, {}], False)
    assert "went_all_in" in story.derive_flags(state(100), [], [{"cost": 84.0}], False)
    assert "went_all_in" not in story.derive_flags(state(100), [], [{"cost": 42.0}], False)


# ------------------------------------------------------------------ effects

def _graph_with_effect(effect):
    """A minimal two-scene graph whose one option carries `effect`."""
    return {"nodes": {
        "s1": {"respond": {"type": "choice", "options": [
            {"id": "take", "label": "Take it", "goto": "s2",
             "sets": ["took_money_out"], "effect": effect}]}},
        "s2": {"respond": {"type": "continue", "goto": "s3"}},
    }}


def test_a_choice_carries_its_effect_out_to_the_caller():
    """The engine names the effect; main.py applies it. It must survive the round trip."""
    flags, effect = story.apply_choice(_graph_with_effect({"withdraw": 40}), "s1", "take", set())
    assert effect == {"withdraw": 40}
    assert "took_money_out" in flags


def test_an_option_with_no_effect_returns_an_empty_one():
    graph = {"nodes": {"s1": {"respond": {"type": "choice", "options": [
        {"id": "keep", "label": "Keep it", "goto": "s2"}]}}}}
    _flags, effect = story.apply_choice(graph, "s1", "keep", set())
    assert effect == {}


def test_a_typo_in_an_effect_name_fails_loudly():
    """Silently moving no money is the worst possible failure for a pressure event."""
    with pytest.raises(story.StoryError) as e:
        story.apply_choice(_graph_with_effect({"withdaw": 40}), "s1", "take", set())
    assert e.value.code == "UNKNOWN_EFFECT"
    assert e.value.extra["effect"] == "withdaw"
