# Oracle pause/resume + ordering override for SPEED_TIE (Stage 4).
#
# A genuine cross-side speed tie in controlled mode is a Category-A oracle event. Unlike the
# single-index events (Effect Spore, Tri Attack, ...), SPEED_TIE's answer is a doubles-compatible
# ORDERING of (side, slot) pairs — earliest acts first — stored in OracleOverrides.speed_tie
# rather than the answers map. When the override is set it resolves ALL ties by rank in BOTH
# modes; when unset in controlled mode the GameDriver pauses (NeedsRNG) and the caller resumes
# with {"order": [[side, slot], ...]}.
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.rng import RNGEvent

from tests.state_builders import make_mon, make_battle

SPEED_TIE_INT = RNGEvent.SPEED_TIE.value


def _controlled_luck() -> dict:
    """Controlled damage luck; accuracy_threshold=0.0 so Tackle always connects."""
    return {
        "accuracy_threshold": 0.0,      # always hits
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
    # luck_tier equal on both sides => tiebreaker ties => genuine speed tie in controlled mode.
    return {"quick_claw_threshold": 50.0, "secondary_threshold": 50.0,
            "luck_tier": 1, "random_mode": False}


def _mirror_tie_battle():
    """Identical mons at hp=1, both Tackle => guaranteed cross-side speed tie; first mover wins."""
    m0 = make_mon(Species.MACHOP, moves=(Move.TACKLE,), level=50, hp=1)
    m1 = make_mon(Species.MACHOP, moves=(Move.TACKLE,), level=50, hp=1)
    return make_battle(m0, m1)


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


# ---------------------------------------------------------------------------
# Test 1: Pause with correct request
# ---------------------------------------------------------------------------

def test_pause_returns_pending_speed_tie():
    state = _mirror_tie_battle()
    driver = _create_driver(state, max_turns=1)
    result = _step(driver)
    assert result["status"] == "pending", f"Expected pending, got: {result['status']!r}"
    assert result["event"] == SPEED_TIE_INT, (
        f"Expected event={SPEED_TIE_INT} (SPEED_TIE), got {result['event']}")
    # Singles cross-side tie => orderable slots (0,0) and (1,0) encoded as side*10+slot.
    assert sorted(result["options"]) == [0, 10], (
        f"Expected options [0, 10], got {sorted(result['options'])}")


# ---------------------------------------------------------------------------
# Test 2: Ordering override honored — either side can be made to move first
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("order,expected_winner", [
    ([[0, 0], [1, 0]], 0),
    ([[1, 0], [0, 0]], 1),
])
def test_ordering_override_honored(order, expected_winner):
    state = _mirror_tie_battle()
    driver = _create_driver(state, overrides_json={"speed_tie": order}, max_turns=1)
    result = _step(driver)
    assert result["status"] == "done", f"Unexpected status: {result['status']!r}"
    assert result["winner"] == expected_winner, (
        f"order {order}: expected winner {expected_winner}, got {result['winner']}")


# ---------------------------------------------------------------------------
# Test 3: Pause-resume equals override (snapshot equivalence)
# ---------------------------------------------------------------------------

def test_pause_resume_equals_override():
    state = _mirror_tie_battle()

    driver_a = _create_driver(state, overrides_json={"speed_tie": [[1, 0], [0, 0]]}, max_turns=1)
    result_a = _step(driver_a)
    assert result_a["status"] == "done"

    driver_b = _create_driver(state, max_turns=1)
    paused = _step(driver_b)
    assert paused["status"] == "pending", f"Path B didn't pause: {paused['status']}"
    result_b = _step(driver_b, {"order": [[1, 0], [0, 0]]})
    assert result_b["status"] == "done"

    assert result_a["winner"] == result_b["winner"] == 1
    assert result_a["state"] == result_b["state"], (
        "Override path and pause-resume path produced different final states")
