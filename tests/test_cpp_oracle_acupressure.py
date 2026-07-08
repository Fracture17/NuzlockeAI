# Oracle pause/resume for ACUPRESSURE_STAT (Stage 3).
#
# Acupressure is a status move that raises one of 7 stat stages (+2) of the user chosen
# uniformly at random. In controlled mode this pick is a Category-A oracle event:
# GameDriver pauses (NeedsRNG) unless an override is set.
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.rng import RNGEvent

from tests.state_builders import make_mon, make_battle

ACUPRESSURE_STAT_INT = RNGEvent.ACUPRESSURE_STAT.value

# Stat indices 0..6 (HP=0, ATK=1, DEF=2, SPA=3, SPD=4, SPE=5, ACC=6).
EXPECTED_OPTIONS = sorted(range(7))


def _controlled_luck() -> dict:
    """Controlled damage luck; all thresholds conservative to avoid secondary oracle events."""
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


def _make_acupressure_battle():
    """Attacker (side 0) uses Acupressure; opponent (side 1) is tanky so the turn completes."""
    attacker = make_mon(Species.MACHOP, moves=(Move.ACUPRESSURE,), level=50)
    defender = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    return make_battle(attacker, defender)


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


def _attacker_stat_stages(result):
    state = sweep_io.from_jsonable(result["state"])
    mon = state.sides[0].team[state.sides[0].active_indices[0]]
    return mon.stat_stages


# ---------------------------------------------------------------------------
# Test 1: Pause with correct request
# ---------------------------------------------------------------------------

def test_pause_returns_pending_acupressure():
    state = _make_acupressure_battle()
    driver = _create_driver(state, max_turns=1)
    result = _step(driver)
    assert result["status"] == "pending", f"Expected pending, got: {result['status']!r}"
    assert result["event"] == ACUPRESSURE_STAT_INT, (
        f"Expected event={ACUPRESSURE_STAT_INT} (ACUPRESSURE_STAT), got {result['event']}")
    assert sorted(result["options"]) == EXPECTED_OPTIONS, (
        f"Expected options {EXPECTED_OPTIONS}, got {sorted(result['options'])}")


# ---------------------------------------------------------------------------
# Test 2: Override honored — each valid stat index
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stat_idx", list(range(7)))
def test_override_honored(stat_idx):
    state = _make_acupressure_battle()
    driver = _create_driver(state, overrides_json={"acupressure_stat": stat_idx}, max_turns=1)
    result = _step(driver)
    assert result["status"] in ("done", "max_turns"), f"Unexpected status: {result['status']!r}"
    stages = _attacker_stat_stages(result)
    assert stages[stat_idx] == 2, (
        f"Expected stat_idx={stat_idx} to be +2, got stages={stages}")


# ---------------------------------------------------------------------------
# Test 3: Pause-resume equals override (snapshot equivalence)
# ---------------------------------------------------------------------------

def test_pause_resume_equals_override():
    state = _make_acupressure_battle()

    driver_a = _create_driver(state, overrides_json={"acupressure_stat": 1}, max_turns=1)
    result_a = _step(driver_a)
    assert result_a["status"] in ("done", "max_turns")

    driver_b = _create_driver(state, max_turns=1)
    paused = _step(driver_b)
    assert paused["status"] == "pending", f"Path B didn't pause: {paused['status']}"
    result_b = _step(driver_b, {"i0": 1})
    assert result_b["status"] in ("done", "max_turns")

    assert result_a["state"] == result_b["state"], (
        "Override path and pause-resume path produced different final states")
