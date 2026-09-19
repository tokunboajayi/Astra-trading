"""
server/tests/test_scenes.py

Lint and fact-check for the coached dialogue (web/scenes/*.json, web/coach.json).

Two jobs:

1. **Enforce the Spec 3 principles.** They are only real if a test fails when they are broken.
   Principle 1 (no dead ends), 2 (no score), 3 (a loss always has a next), 6 (never end on the low).

2. **Fact-check every dollar figure against the fixture.** The coach quotes exact numbers. If the
   fixture is regenerated and a number drifts, the demo breaks in front of judges. This catches it
   at build time instead, the same way `build_fixtures.py --check` catches stale fixtures.

Contract: docs/SPEC_3.md sections 0 and 5.
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
WEB = ROOT / "web"
SCENES_DIR = WEB / "scenes"

# Acts that do not exist yet. A goto into one of these is a forward reference, not a dead end.
FUTURE_ACTS = {"act5", "act6"}

# Principle 1: an escape hatch is any option that lets her decline to answer.
FORBIDDEN_OPTION_TEXT = (
    "i don't know", "i dont know", "don't know", "dont know", "not sure", "unsure",
    "skip", "no idea", "pass", "n/a", "prefer not",
)

# Principle 2: nothing is graded.
FORBIDDEN_KEYS = ("score", "points", "grade", "rank", "streak", "xp", "stars", "correct_count")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


ACTS = sorted(SCENES_DIR.glob("act*.json"))
COACH = load(WEB / "coach.json")


def all_nodes():
    """[(act_file_stem, node_id, node)] across every act."""
    out = []
    for path in ACTS:
        act = load(path)
        for node_id, node in act["nodes"].items():
            out.append((path.stem, node_id, node))
    return out


def walk(obj):
    """Every (key, value) pair anywhere in a nested structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from walk(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk(item)


def fixture_for(act):
    return load(ROOT / "fixtures" / f"{act['fixture']}.json")


def fixture_exists(act):
    return (ROOT / "fixtures" / f"{act['fixture']}.json").exists()


def position_at(act, bar_index):
    """What the Act's premise position is worth at `bar_index`, straight from the fixture."""
    fx = fixture_for(act)
    p = act["premise"]
    price = fx["bars"][bar_index]["c"]
    qty, entry = p["qty"], p["entry_price"]
    return {
        "price": price,
        "market_value": round(qty * price, 2),
        "pnl": round((price - entry) * qty, 2),
        "pnl_pct": round((price / entry - 1) * 100, 2),
    }


# --------------------------------------------------------------------- structure

def test_there_is_at_least_one_act():
    assert ACTS, "No scene files found in web/scenes/."


@pytest.mark.parametrize("stem,node_id,node", all_nodes())
def test_every_node_has_a_speaker_and_lines(stem, node_id, node):
    assert node.get("speaker"), f"{stem}:{node_id} has no speaker."
    assert node.get("lines"), f"{stem}:{node_id} has no lines."
    assert all(isinstance(line, str) and line.strip() for line in node["lines"]), \
        f"{stem}:{node_id} has an empty line."


@pytest.mark.parametrize("stem,node_id,node", all_nodes())
def test_every_node_can_be_left(stem, node_id, node):
    """Principle 1, structural half: no node is a dead end."""
    respond = node.get("respond")
    assert respond, f"{stem}:{node_id} has no respond block, so there is no way out of it."
    if respond["type"] == "choice":
        assert respond.get("options"), f"{stem}:{node_id} is a choice with no options."
        for opt in respond["options"]:
            assert opt.get("goto"), f"{stem}:{node_id} option {opt.get('id')} goes nowhere."
    else:
        assert respond.get("goto"), f"{stem}:{node_id} has no goto."


def test_every_goto_resolves():
    known = {node_id for _, node_id, _ in all_nodes()}
    for stem, node_id, node in all_nodes():
        respond = node["respond"]
        targets = [o["goto"] for o in respond.get("options", [])] if respond["type"] == "choice" \
            else [respond["goto"]]
        for target in targets:
            if target.split(".")[0] in FUTURE_ACTS:
                continue
            assert target in known, f"{stem}:{node_id} points at {target}, which does not exist."


def test_the_start_node_exists():
    for path in ACTS:
        act = load(path)
        assert act["start"] in act["nodes"], f"{path.stem} start node {act['start']} is missing."


# --------------------------------------------------------------------- principles

@pytest.mark.parametrize("stem,node_id,node", all_nodes())
def test_principle_1_no_escape_hatch(stem, node_id, node):
    """There is no 'I don't know' option, ever. This is the product."""
    respond = node["respond"]
    for opt in respond.get("options", []):
        label = opt["label"].lower()
        for banned in FORBIDDEN_OPTION_TEXT:
            assert banned not in label, \
                (f"{stem}:{node_id} offers an escape hatch ({opt['label']!r}). Principle 1: every "
                 f"question is answerable and there is no 'I don't know' option.")


def test_principle_2_nothing_is_scored():
    for path in list(ACTS) + [WEB / "coach.json"]:
        for key, _ in walk(load(path)):
            assert key not in FORBIDDEN_KEYS, \
                f"{path.name} contains a scoring field {key!r}. Principle 2: nothing is graded."


@pytest.mark.parametrize("stem,node_id,node", all_nodes())
def test_principle_3_a_loss_is_never_stated_alone(stem, node_id, node):
    """A named loss always carries what happens next. Honest, and actionable."""
    if "loss" in node:
        assert node.get("next", "").strip(), \
            (f"{stem}:{node_id} names a loss ({node['loss']}) with no `next`. Principle 3: a loss "
             f"is always paired with what happens now.")


@pytest.mark.parametrize("stem,node_id,node", all_nodes())
def test_principle_6_never_end_on_the_low(stem, node_id, node):
    """Any drawdown scene must name the scene that shows what came next."""
    if node.get("drawdown"):
        target = node.get("recovery_shown")
        assert target, f"{stem}:{node_id} is a drawdown with no recovery_shown. Principle 6."
        known = {n for _, n, _ in all_nodes()}
        assert target in known, f"{stem}:{node_id} recovery_shown points at missing {target}."


@pytest.mark.parametrize("stem,node_id,node", all_nodes())
def test_no_decision_is_labelled_wrong(stem, node_id, node):
    """No option may be framed as the mistake. She finds out by watching, not by being told."""
    for opt in node["respond"].get("options", []):
        label = opt["label"].lower()
        for banned in ("wrong", "mistake", "bad idea", "don't do"):
            assert banned not in label, f"{stem}:{node_id} pre-judges an option: {opt['label']!r}"


# --------------------------------------------------------------------- fact-check

def act_fact_cases():
    cases = []
    for path in ACTS:
        act = load(path)
        for node_id, node in act["nodes"].items():
            if "facts" in node and "at_bar" in node:
                cases.append(pytest.param(act, node_id, node, id=f"{path.stem}:{node_id}"))
    return cases


@pytest.mark.parametrize("act,node_id,node", act_fact_cases())
def test_quoted_numbers_match_the_fixture(act, node_id, node):
    """Every price and P&L the coach quotes is what the engine actually produces at that bar."""
    if not fixture_exists(act):
        pytest.skip(f"{act['fixture']}.json no longer exists: the fixtures were replaced with "
                     "richher.html's six intraday symbols for the richher/backend integration. "
                     f"act{act['act']}.json's own story is orphaned until it is rewritten against "
                     "one of the new fixtures (or retired) - tracked separately from that work.")
    truth = position_at(act, node["at_bar"])
    for key, claimed in node["facts"].items():
        if key in truth:
            assert claimed == pytest.approx(truth[key], abs=0.01), \
                (f"{node_id} claims {key}={claimed} at bar {node['at_bar']}, but the fixture says "
                 f"{truth[key]}. Regenerate the fixture or fix the copy.")


def test_the_three_way_counterfactual_is_arithmetically_true():
    """The Act 4 payoff - sell/hold/buy-more - has to survive a fixture rebuild.

    This is the single most important assertion in the file: the whole lesson is those
    numbers. Starting capital comes from the premise, never hardcoded, so moving the
    account from $10,000 to $100 does not silently invalidate the test.
    """
    act = load(SCENES_DIR / "act4.json")
    if not fixture_exists(act):
        pytest.skip(f"{act['fixture']}.json no longer exists: see test_quoted_numbers_match_the_fixture.")
    fx = fixture_for(act)
    p = act["premise"]
    qty, entry, cash0 = p["qty"], p["entry_price"], p["cash_after_buy"]
    start_capital = round(cash0 + qty * entry, 2)

    decision_bar = act["nodes"]["act4.deep"]["at_bar"]
    decision_price = fx["bars"][decision_bar]["c"]

    def equity(shares, cash, price):
        return round(cash + shares * price, 2)

    # "more" buys one additional share at the decision price, matching the scene's option.
    outcomes = {
        "sell": lambda price: equity(0, cash0 + qty * decision_price, price),
        "hold": lambda price: equity(qty, cash0, price),
        "more": lambda price: equity(qty + 1, cash0 - decision_price, price),
    }

    for node_id in ("act4.compare", "act4.recovery"):
        node = act["nodes"][node_id]
        price = fx["bars"][node["at_bar"]]["c"]
        for choice, fn in outcomes.items():
            if choice in node["facts"]:
                assert node["facts"][choice] == pytest.approx(fn(price), abs=0.01),                     f"{node_id} claims {choice}={node['facts'][choice]}, arithmetic says {fn(price)}"
        if "spread" in node["facts"]:
            values = [fn(price) for fn in outcomes.values()]
            assert node["facts"]["spread"] == pytest.approx(max(values) - min(values), abs=0.01)

    # The beat only lands if the RANKING INVERTS: whatever looks best at the lowest point
    # must not be what is best at the end. That is the lesson, on a recovering arc or a
    # converging one. If a fixture rebuild flattens this, Act 4 needs rewriting.
    trough_price = fx["bars"][act["nodes"]["act4.compare"]["at_bar"]]["c"]
    end_price = fx["bars"][act["nodes"]["act4.recovery"]["at_bar"]]["c"]
    best_at_trough = max(outcomes, key=lambda k: outcomes[k](trough_price))
    best_at_end = max(outcomes, key=lambda k: outcomes[k](end_price))
    assert best_at_trough != best_at_end, (
        f"At the trough and at the end the best choice is both {best_at_trough!r}. "
        "Act 4's payoff depends on the ranking changing - this fixture no longer produces it."
    )

    # And the account must actually be able to end up ahead, or the wager is rigged.
    assert max(fn(end_price) for fn in outcomes.values()) > start_capital,         "No Act 4 path ends above the starting capital. See STORY.md section 3."


# --------------------------------------------------------------------- the coach

def test_the_coach_has_a_name_and_a_bio():
    persona = COACH["persona"]
    for field in ("name", "short_name", "role", "bio", "voice_rules"):
        assert persona.get(field), f"The coach has no {field}."
    assert len(persona["bio"].split()) >= 40, "The coach's bio is too thin to establish a person."


@pytest.mark.parametrize("control_id", list(COACH["controls"]))
def test_every_coached_control_explains_itself_and_says_what_to_do(control_id):
    """Principle 3 applied to the pop-outs: explain, then hand her an action."""
    control = COACH["controls"][control_id]
    assert control.get("lines"), f"{control_id} has no lines."
    assert control.get("next", "").strip(), f"{control_id} explains but never says what to do next."
    assert isinstance(control.get("auto_pop"), bool), f"{control_id} must declare auto_pop."


@pytest.mark.parametrize("control_id", list(COACH["controls"]))
def test_the_coach_keeps_her_voice(control_id):
    """Her voice rules are testable, so they are tested."""
    banned = ("obviously", "simply", "just ", "of course")
    text = " ".join(COACH["controls"][control_id]["lines"] + [COACH["controls"][control_id]["next"]]).lower()
    for word in banned:
        assert word not in text, \
            f"{control_id} uses {word.strip()!r}, which the coach's voice rules forbid."
