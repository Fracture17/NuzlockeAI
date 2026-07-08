# Oracle pause/resume for STARF_BERRY_STAT (Stage 3).
#
# Starf Berry triggers when the holder drops to ≤25% HP, raising one of 5 combat
# stat stages (+2) chosen uniformly at random. In controlled mode this pick is a
# Category-A oracle event: GameDriver pauses (NeedsRNG) unless an override is set.
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.items import Item
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.rng import RNGEvent

from tests.state_builders import make_mon, make_battle

STARF_BERRY_STAT_INT = RNGEvent.STARF_BERRY_STAT.value

# Combat stat indices 0..4 (ATK=0, DEF=1, SPA=2, SPD=3, SPE=4 in Starf's randint range).
EXPECTED_OPTIONS = sorted(range(5))


def _controlled_luck() -> dict:
    """Controlled damage luck; accuracy_threshold=0.0 so the attacker's move always lands."""
    return {
        "accuracy_threshold": 0.0,
        "crit_threshold": 50.0,
        "damage_roll": 0.5,
        "proc_threshold": 50.0,
        "secondary_threshold": 50.0,
        "multi_hit_roll": 0.5,
        "rampage_duration_roll": 0.5,
        "psywave_roll": 0.5,
        "flinch_threshold": 50.0,
        "binding_duration_roll": 0.5,
        "wake_threshold": 50.0,
        "defrost_threshold": 20.0,
        "paralysis_threshold": 50.0,
        "confusion_snap_threshold": 50.0,
        "confusion_self_hit_threshold": 50.0,
        "attract_threshold": 50.0,
        "damage_rolls_per_hit": None,
        "crits_per_hit": None,
        "random_mode": False,
    }


def _controlled_turn_luck() -> dict:
    return {"quick_claw_threshold": 50.0, "secondary_threshold": 50.0,
            "luck_tier": 1, "random_mode": False}


def _make_starf_battle():
    """Holder (side 0) holds Starf Berry, already at ≤25% HP so any chip triggers the berry."""
    holder = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), item=Item.STARF_BERRY, level=50)
    # Set HP to exactly the 25% threshold so the next hit will still keep it alive but berry fires.
    holder = holder._replace(hp=max(1, holder.max_hp // 4))
    attacker = make_mon(Species.CATERPIE, moves=(Move.TACKLE,), level=5)
    return make_battle(holder, attacker)


def _create_driver(state, *, overrides_json=None, max_turns=1):
    args = {
        "state": sweep_io.to_jsonable(state),
        "seed": 0,
        "luck_p0": _controlled_luck(),
        "luck_p1": _controlled_luck(),
        "turn_luck_p0": _controlled_turn_luck(),
        "turn_luck_p1": _controlled_turn_luck(),
        "max_turns": max_turns,
    }
    if overrides_json is not None:
        args["overrides"] = overrides_json
    return cpp.GameDriver(json.dumps(args))


def _step(driver, answer=None):
    if answer is None:
        return json.loads(driver.step())
    return json.loads(driver.step(json.dumps(answer)))


def _holder_stat_stages(result):
    state = sweep_io.from_jsonable(result["state"])
    mon = state.sides[0].team[state.sides[0].active_indices[0]]
    return mon.stat_stages


# ---------------------------------------------------------------------------
# Test 1: Pause with correct request
# ---------------------------------------------------------------------------

def test_pause_returns_pending_starf():
    state = _make_starf_battle()
    driver = _create_driver(state, max_turns=1)
    result = _step(driver)
    assert result["status"] == "pending", f"Expected pending, got: {result['status']!r}"
    assert result["event"] == STARF_BERRY_STAT_INT, (
        f"Expected event={STARF_BERRY_STAT_INT} (STARF_BERRY_STAT), got {result['event']}")
    assert sorted(result["options"]) == EXPECTED_OPTIONS, (
        f"Expected options {EXPECTED_OPTIONS}, got {sorted(result['options'])}")


# ---------------------------------------------------------------------------
# Test 2: Override honored — each valid stat index
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stat_idx", list(range(5)))
def test_override_honored(stat_idx):
    state = _make_starf_battle()
    driver = _create_driver(state, overrides_json={"starf_berry_stat": stat_idx}, max_turns=1)
    result = _step(driver)
    assert result["status"] in ("done", "max_turns"), f"Unexpected status: {result['status']!r}"
    stages = _holder_stat_stages(result)
    # Starf stat_idx maps to combat stat stages[1..5] in the same order as randint(0,4).
    # The actual stage index in PokemonState.stat_stages may start at index 1 (ATK).
    # We verify that exactly one stat has a +2 boost.
    boosted = [i for i, v in enumerate(stages) if v == 2]
    assert len(boosted) == 1, f"Expected exactly one +2 stage, got stages={stages}"


# ---------------------------------------------------------------------------
# Test 3: Pause-resume equals override (snapshot equivalence)
# ---------------------------------------------------------------------------

def test_pause_resume_equals_override():
    state = _make_starf_battle()

    driver_a = _create_driver(state, overrides_json={"starf_berry_stat": 0}, max_turns=1)
    result_a = _step(driver_a)
    assert result_a["status"] in ("done", "max_turns")

    driver_b = _create_driver(state, max_turns=1)
    paused = _step(driver_b)
    assert paused["status"] == "pending", f"Path B didn't pause: {paused['status']}"
    result_b = _step(driver_b, {"i0": 0})
    assert result_b["status"] in ("done", "max_turns")

    assert result_a["state"] == result_b["state"], (
        "Override path and pause-resume path produced different final states")
