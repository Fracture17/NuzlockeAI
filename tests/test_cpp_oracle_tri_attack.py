# Oracle pause/resume for TRI_ATTACK_STATUS (Stage 2).
#
# Tri Attack is a damaging Normal move whose 20% secondary inflicts one of
# BURN / FREEZE / PARALYSIS chosen uniformly. In controlled mode this pick is a
# Category-A oracle event: GameDriver pauses (NeedsRNG) unless an override is set.
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status
from liveplay.rng import RNGEvent

from tests.state_builders import make_mon, make_battle

TRI_ATTACK_STATUS_INT = RNGEvent.TRI_ATTACK_STATUS.value

STATUS_BURN      = Status.BURN.value       # 1
STATUS_FREEZE    = Status.FREEZE.value     # 2
STATUS_PARALYSIS = Status.PARALYSIS.value  # 3

EXPECTED_OPTIONS = sorted([STATUS_BURN, STATUS_FREEZE, STATUS_PARALYSIS])


def _controlled_luck() -> dict:
    """Controlled damage luck; secondary_threshold=0.0 so Tri Attack's 20% secondary always fires."""
    return {
        "accuracy_threshold": 0.0,      # always hits
        "crit_threshold": 50.0,
        "damage_roll": 0.5,
        "proc_threshold": 0.0,
        "secondary_threshold": 0.0,     # secondaries always fire
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
    return {"quick_claw_threshold": 50.0, "secondary_threshold": 0.0,
            "luck_tier": 1, "random_mode": False}


def _make_tri_attack_battle():
    """Attacker (side 0) uses Tri Attack; defender (side 1) is a tanky Normal-type."""
    atk = make_mon(Species.MACHOP, moves=(Move.TRI_ATTACK,), level=40)
    defender = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    return make_battle(atk, defender)


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


def _defender_status_from_result(result):
    state = sweep_io.from_jsonable(result["state"])
    mon = state.sides[1].team[state.sides[1].active_indices[0]]
    return mon.status.value


# ---------------------------------------------------------------------------
# Test 1: Pause with correct request
# ---------------------------------------------------------------------------

def test_pause_returns_pending_tri_attack():
    state = _make_tri_attack_battle()
    driver = _create_driver(state, max_turns=1)
    result = _step(driver)
    assert result["status"] == "pending", f"Expected pending, got: {result['status']!r}"
    assert result["event"] == TRI_ATTACK_STATUS_INT, (
        f"Expected event={TRI_ATTACK_STATUS_INT} (TRI_ATTACK_STATUS), got {result['event']}")
    assert sorted(result["options"]) == EXPECTED_OPTIONS, (
        f"Expected options {EXPECTED_OPTIONS}, got {sorted(result['options'])}")


# ---------------------------------------------------------------------------
# Test 2: Override honored — each status
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status_value", [STATUS_BURN, STATUS_FREEZE, STATUS_PARALYSIS])
def test_override_honored(status_value):
    state = _make_tri_attack_battle()
    driver = _create_driver(state, overrides_json={"tri_attack_status": status_value}, max_turns=1)
    result = _step(driver)
    assert result["status"] in ("done", "max_turns"), f"Unexpected status: {result['status']!r}"
    st = _defender_status_from_result(result)
    assert st == status_value, f"Expected status {status_value}, got {st}"


# ---------------------------------------------------------------------------
# Test 3: Pause-resume equals override (snapshot equivalence)
# ---------------------------------------------------------------------------

def test_pause_resume_equals_override():
    state = _make_tri_attack_battle()

    driver_a = _create_driver(state, overrides_json={"tri_attack_status": STATUS_BURN}, max_turns=1)
    result_a = _step(driver_a)
    assert result_a["status"] in ("done", "max_turns")

    driver_b = _create_driver(state, max_turns=1)
    paused = _step(driver_b)
    assert paused["status"] == "pending", f"Path B didn't pause: {paused['status']}"
    result_b = _step(driver_b, {"i0": STATUS_BURN})
    assert result_b["status"] in ("done", "max_turns")

    assert result_a["state"] == result_b["state"], (
        "Override path and pause-resume path produced different final states")
