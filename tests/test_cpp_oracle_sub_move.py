# Oracle pause/resume layer — Stage 8: sub-move selection (METRONOME_MOVE / SLEEP_TALK_MOVE).
#
# Metronome and Sleep Talk call a RANDOM other move — Category-A oracle events (the answer is the
# CHOSEN MOVE ID, options are the callable-move list). In the GameDriver pause/resume path this must:
#   - pause (NeedsRNG) with event=METRONOME_MOVE/SLEEP_TALK_MOVE and options = the callable moves,
#     when no override is set;
#   - honor an injected override / resume answer (the chosen move id);
#   - produce identical final state via override vs. pause-then-resume.
#
# The plain run_game/bridge path is UNCHANGED — it stays fail-loud "unported: sub_move" in turn.cpp;
# only the oracle-driven GameDriver treats sub-move selection as a pausable oracle event.
#
# ASSIST in singles is NOT a pause: with no partner it fails immediately (Python simulator.py:727),
# so there is no ASSIST_MOVE oracle test here.
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status
from liveplay.rng import RNGEvent

from tests.state_builders import make_mon, make_battle

METRONOME_MOVE_INT = RNGEvent.METRONOME_MOVE.value   # 22
SLEEP_TALK_MOVE_INT = RNGEvent.SLEEP_TALK_MOVE.value  # 23


def _controlled_luck() -> dict:
    return {
        "accuracy_threshold": 0.0, "crit_threshold": 50.0, "damage_roll": 0.5,
        "proc_threshold": 50.0, "secondary_threshold": 50.0, "multi_hit_roll": 0.5,
        "rampage_duration_roll": 0.5, "psywave_roll": 0.5, "flinch_threshold": 50.0,
        "binding_duration_roll": 0.5, "wake_threshold": 100.0, "defrost_threshold": 20.0,
        "paralysis_threshold": 50.0, "confusion_snap_threshold": 50.0,
        "confusion_self_hit_threshold": 50.0, "attract_threshold": 50.0,
        "damage_rolls_per_hit": None, "crits_per_hit": None, "random_mode": False,
    }


def _controlled_turn_luck() -> dict:
    return {"quick_claw_threshold": 50.0, "secondary_threshold": 50.0,
            "luck_tier": 1, "random_mode": False}


def _make_metronome_battle():
    """Side 0 uses Metronome; distinct species => no speed tie. Bulky target survives one hit."""
    m0 = make_mon(Species.MACHOP, moves=(Move.METRONOME,), level=50)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    return make_battle(m0, m1)


def _make_sleep_talk_battle():
    """Side 0 is asleep and uses Sleep Talk over two callable moves (Tackle, Pound)."""
    m0 = make_mon(Species.MACHOP, moves=(Move.SLEEP_TALK, Move.TACKLE, Move.POUND),
                  level=50, status=Status.SLEEP)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    return make_battle(m0, m1)


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


def _side1_active_hp(result):
    state = sweep_io.from_jsonable(result["state"])
    side1 = state.sides[1]
    active = side1.active_indices[0]
    mon = side1.team[active]
    return mon.hp, mon.max_hp


# ---------------------------------------------------------------------------
# 1. Pause request shape — Metronome
# ---------------------------------------------------------------------------

def test_pause_returns_pending_metronome():
    driver = _create_driver(_make_metronome_battle(), max_turns=1)
    result = _step(driver)

    assert result["status"] == "pending", f"Expected pending, got {result['status']!r}"
    assert result["event"] == METRONOME_MOVE_INT, (
        f"Expected event={METRONOME_MOVE_INT} (METRONOME_MOVE), got {result['event']}")
    assert len(result["options"]) > 50, (
        f"Metronome should offer the full callable-move list, got {len(result['options'])}")
    assert Move.TACKLE.value in result["options"], "Tackle should be a Metronome option"


# ---------------------------------------------------------------------------
# 2. Override honored — the chosen sub-move actually executes (deals damage)
# ---------------------------------------------------------------------------

def test_override_metronome_executes_move():
    driver = _create_driver(_make_metronome_battle(),
                            overrides_json={"metronome_move": Move.TACKLE.value}, max_turns=1)
    result = _step(driver)
    assert result["status"] in ("done", "max_turns"), f"Unexpected status: {result['status']!r}"
    hp, max_hp = _side1_active_hp(result)
    assert hp < max_hp, f"Metronome->Tackle should have damaged the target (hp={hp}/{max_hp})"


# ---------------------------------------------------------------------------
# 3. Pause-then-resume equals override — Metronome
# ---------------------------------------------------------------------------

def test_pause_resume_equals_override_metronome():
    chosen = Move.TACKLE.value

    driver_a = _create_driver(_make_metronome_battle(),
                              overrides_json={"metronome_move": chosen}, max_turns=1)
    result_a = _step(driver_a)
    assert result_a["status"] in ("done", "max_turns")

    driver_b = _create_driver(_make_metronome_battle(), max_turns=1)
    paused = _step(driver_b)
    assert paused["status"] == "pending", f"Path B didn't pause: {paused['status']}"
    assert paused["event"] == METRONOME_MOVE_INT
    result_b = _step(driver_b, {"i0": chosen})
    assert result_b["status"] in ("done", "max_turns")

    assert result_a["state"] == result_b["state"], (
        "Override and pause-resume paths produced different final states (Metronome)")


# ---------------------------------------------------------------------------
# 4. Sleep Talk — pause shape offers only the mon's own callable moves
# ---------------------------------------------------------------------------

def test_pause_returns_pending_sleep_talk():
    driver = _create_driver(_make_sleep_talk_battle(), max_turns=1)
    result = _step(driver)

    assert result["status"] == "pending", f"Expected pending, got {result['status']!r}"
    assert result["event"] == SLEEP_TALK_MOVE_INT, (
        f"Expected event={SLEEP_TALK_MOVE_INT} (SLEEP_TALK_MOVE), got {result['event']}")
    assert sorted(result["options"]) == sorted([Move.TACKLE.value, Move.POUND.value]), (
        f"Sleep Talk options should be the mon's callable moves, got {result['options']}")


# ---------------------------------------------------------------------------
# 5. Sleep Talk — pause-then-resume equals override
# ---------------------------------------------------------------------------

def test_pause_resume_equals_override_sleep_talk():
    chosen = Move.TACKLE.value

    driver_a = _create_driver(_make_sleep_talk_battle(),
                              overrides_json={"sleep_talk_move": chosen}, max_turns=1)
    result_a = _step(driver_a)
    assert result_a["status"] in ("done", "max_turns")

    driver_b = _create_driver(_make_sleep_talk_battle(), max_turns=1)
    paused = _step(driver_b)
    assert paused["status"] == "pending", f"Path B didn't pause: {paused['status']}"
    result_b = _step(driver_b, {"i0": chosen})
    assert result_b["status"] in ("done", "max_turns")

    assert result_a["state"] == result_b["state"], (
        "Override and pause-resume paths produced different final states (Sleep Talk)")
