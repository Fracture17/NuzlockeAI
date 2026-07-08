# Oracle pause/resume layer — Stage 5: ROAR_TARGET.
#
# Phazing (Roar/Whirlwind/Dragon Tail/Circle Throw) forces the target side to switch to a
# RANDOM live bench member — a Category-A oracle event (ROAR_TARGET). In the GameDriver
# pause/resume path this must:
#   - pause (NeedsRNG) with event=ROAR_TARGET and options = the live bench team-slot indices
#     (every team slot except the current active and fainted mons), when no override is set;
#   - honor an injected override / resume answer (the chosen bench team slot);
#   - produce identical final state via override vs. pause-then-resume.
#
# The plain whole-game run_game path is UNCHANGED (phaze target drawn by the runner Policy);
# only the oracle-driven GameDriver treats ROAR_TARGET as a pausable oracle event.
#
# NOTE: the phazed side's RandomPolicy may voluntarily switch on the same turn before it is
# phazed, so the exact bench options depend on which mon is active at phaze time. The tests
# therefore DERIVE the expected options from the paused state rather than hard-coding them —
# the seed/state are identical across drivers, so the options are reproducible.
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.rng import RNGEvent

from tests.state_builders import make_mon, make_battle

ROAR_TARGET_INT = RNGEvent.ROAR_TARGET.value  # 26


def _controlled_luck() -> dict:
    return {
        "accuracy_threshold": 0.0,   # Roar always hits
        "crit_threshold": 50.0, "damage_roll": 0.5, "proc_threshold": 50.0,
        "secondary_threshold": 50.0, "multi_hit_roll": 0.5, "rampage_duration_roll": 0.5,
        "psywave_roll": 0.5, "flinch_threshold": 50.0, "binding_duration_roll": 0.5,
        "wake_threshold": 50.0, "defrost_threshold": 20.0, "paralysis_threshold": 50.0,
        "confusion_snap_threshold": 50.0, "confusion_self_hit_threshold": 50.0,
        "attract_threshold": 50.0, "damage_rolls_per_hit": None, "crits_per_hit": None,
        "random_mode": False,
    }


def _controlled_turn_luck() -> dict:
    return {"quick_claw_threshold": 50.0, "secondary_threshold": 50.0,
            "luck_tier": 1, "random_mode": False}


def _make_roar_battle():
    """Side 0 uses Roar; side 1 active + two live bench mons => phaze picks a random bench slot.

    Roar is priority -6, so side 1 acts first, then side 0's Roar phazes side 1. No damage on
    either side, no speed tie (distinct priority brackets), so ROAR_TARGET is the only oracle event.
    """
    m0 = make_mon(Species.MACHOP, moves=(Move.ROAR,), level=50)
    s1_active = make_mon(Species.CATERPIE, moves=(Move.SPLASH,), level=50)
    s1_bench1 = make_mon(Species.WEEDLE, moves=(Move.SPLASH,), level=50)
    s1_bench2 = make_mon(Species.PIDGEY, moves=(Move.SPLASH,), level=50)
    return make_battle(m0, s1_active, team1=[s1_active, s1_bench1, s1_bench2])


def _create_driver(state, *, overrides_json=None, max_turns=1):
    args = {
        "state": sweep_io.to_jsonable(state),
        "seed": 0,
        "luck_p0": _controlled_luck(), "luck_p1": _controlled_luck(),
        "turn_luck_p0": _controlled_turn_luck(), "turn_luck_p1": _controlled_turn_luck(),
        "max_turns": max_turns,
    }
    if overrides_json is not None:
        args["overrides"] = overrides_json
    return cpp.GameDriver(json.dumps(args))


def _step(driver, answer=None):
    if answer is None:
        return json.loads(driver.step())
    return json.loads(driver.step(json.dumps(answer)))


def _side1_active_slot(result):
    state = sweep_io.from_jsonable(result["state"])
    return state.sides[1].active_indices[0]


def _expected_bench_options(result):
    """Live bench team-slot indices for side 1 in the paused state (active + fainted excluded)."""
    state = sweep_io.from_jsonable(result["state"])
    side1 = state.sides[1]
    active = side1.active_indices[0]
    return sorted(i for i, mon in enumerate(side1.team)
                  if i != active and not mon.fainted)


def _probe_options():
    """Run a probe driver to discover the ROAR_TARGET options for the shared seed/state."""
    driver = _create_driver(_make_roar_battle(), max_turns=1)
    paused = _step(driver)
    assert paused["status"] == "pending" and paused["event"] == ROAR_TARGET_INT
    return sorted(paused["options"])


# ---------------------------------------------------------------------------
# 1. Pause request shape
# ---------------------------------------------------------------------------

def test_pause_returns_pending_roar_target():
    driver = _create_driver(_make_roar_battle(), max_turns=1)
    result = _step(driver)

    assert result["status"] == "pending", f"Expected pending, got {result['status']!r}"
    assert result["event"] == ROAR_TARGET_INT, (
        f"Expected event={ROAR_TARGET_INT} (ROAR_TARGET), got {result['event']}")
    expected = _expected_bench_options(result)
    assert len(expected) == 2, f"Setup should leave 2 live bench options, got {expected}"
    assert sorted(result["options"]) == expected, (
        f"Expected bench options {expected}, got {sorted(result['options'])}")


# ---------------------------------------------------------------------------
# 2. Override honored — phaze target set to a chosen live bench slot
# ---------------------------------------------------------------------------

def test_override_roar_target():
    options = _probe_options()
    for target in options:
        driver = _create_driver(_make_roar_battle(),
                                 overrides_json={"roar_target": target}, max_turns=1)
        result = _step(driver)
        assert result["status"] in ("done", "max_turns"), f"Unexpected status: {result['status']!r}"
        assert _side1_active_slot(result) == target, (
            f"Expected side-1 phazed to slot {target}, got {_side1_active_slot(result)}")


# ---------------------------------------------------------------------------
# 3. Pause-then-resume equals override (final-state equivalence)
# ---------------------------------------------------------------------------

def test_pause_resume_equals_override():
    options = _probe_options()
    target = options[-1]

    driver_a = _create_driver(_make_roar_battle(),
                              overrides_json={"roar_target": target}, max_turns=1)
    result_a = _step(driver_a)
    assert result_a["status"] in ("done", "max_turns")

    driver_b = _create_driver(_make_roar_battle(), max_turns=1)
    paused = _step(driver_b)
    assert paused["status"] == "pending", f"Path B didn't pause: {paused['status']}"
    result_b = _step(driver_b, {"i0": target})
    assert result_b["status"] in ("done", "max_turns")

    assert result_a["state"] == result_b["state"], (
        "Override and pause-resume paths produced different final states")
