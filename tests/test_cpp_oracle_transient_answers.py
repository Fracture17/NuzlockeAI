# Oracle transient-channel tests: verify that pause/resume correctly re-pauses on repeated
# Category-A oracle events instead of silently reusing a stale injected answer.
#
# After the fix, each occurrence of an oracle event must produce a fresh pause. Transient
# answers accumulate for the current replay region with a cursor; the persistent channel
# (constructor-injected overrides) is tested separately to confirm it still fires every time.
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.abilities import Ability
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.rng import RNGEvent

from tests.state_builders import make_mon, make_battle

METRONOME_MOVE_INT = RNGEvent.METRONOME_MOVE.value   # 22
MOODY_STATS_INT    = RNGEvent.MOODY_STATS.value      # 29
SPEED_TIE_INT      = RNGEvent.SPEED_TIE.value        # 31


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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


def _create_driver(state, *, overrides_json=None, max_turns=2):
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


# ---------------------------------------------------------------------------
# Battles
# ---------------------------------------------------------------------------

def _make_metronome_battle():
    """Side 0 uses Metronome; Snorlax is bulky enough to survive many turns (no speed tie)."""
    m0 = make_mon(Species.MACHOP, moves=(Move.METRONOME,), level=50)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    return make_battle(m0, m1)


def _make_both_metronome_battle():
    """Both sides use Metronome; Snorlax vs Machop — different speeds, no speed tie."""
    m0 = make_mon(Species.MACHOP, moves=(Move.METRONOME,), level=50)
    m1 = make_mon(Species.SNORLAX, moves=(Move.METRONOME,), level=50)
    return make_battle(m0, m1)


def _make_two_moody_battle():
    """Both sides have Moody and use Splash (no damage). Different speeds, no speed tie.

    Side 0: Machop (spe=55) with Moody.
    Side 1: Snorlax (spe=50) with Moody.
    Both survive to end-of-turn where Moody fires for each mon in the same residual block.
    """
    m0 = make_mon(Species.MACHOP, moves=(Move.SPLASH,), level=50, ability=Ability.MOODY)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50, ability=Ability.MOODY)
    return make_battle(m0, m1)


def _make_speed_tie_battle():
    """Two Machops at full HP using Splash (safe, no KO). Identical speed => speed tie each turn."""
    m0 = make_mon(Species.MACHOP, moves=(Move.SPLASH,), level=50)
    m1 = make_mon(Species.MACHOP, moves=(Move.SPLASH,), level=50)
    return make_battle(m0, m1)


# ---------------------------------------------------------------------------
# 1. test_repeat_event_across_turns_pauses_again
#
# One side uses Metronome. Turn 1: pause on METRONOME_MOVE, resume with Splash.
# Turn 2: must pause AGAIN (bug: without the fix, the stale answer runs without pausing).
# ---------------------------------------------------------------------------

def test_repeat_event_across_turns_pauses_again():
    state = _make_metronome_battle()
    driver = _create_driver(state, max_turns=2)

    # Turn 1: expect pause on METRONOME_MOVE
    r1 = _step(driver)
    assert r1["status"] == "pending", f"Turn 1 expected pending, got {r1['status']!r}"
    assert r1["event"] == METRONOME_MOVE_INT

    # Resume with Splash (safe move, target survives)
    r2 = _step(driver, {"i0": Move.SPLASH.value})
    # After resume, turn 1 completes; turn 2 begins
    # Turn 2 must pause again on METRONOME_MOVE
    assert r2["status"] == "pending", (
        f"Turn 2 expected pending (second METRONOME_MOVE pause), got {r2['status']!r}")
    assert r2["event"] == METRONOME_MOVE_INT, (
        f"Turn 2 pause event should be METRONOME_MOVE ({METRONOME_MOVE_INT}), got {r2['event']}")

    # Resume turn 2 with Splash as well; game should complete (max_turns=2)
    r3 = _step(driver, {"i0": Move.SPLASH.value})
    assert r3["status"] in ("done", "max_turns"), (
        f"After two resumes expected done/max_turns, got {r3['status']!r}")


# ---------------------------------------------------------------------------
# 2. test_two_movers_same_event_same_turn
#
# Both sides use Metronome, max_turns=1. Expect two METRONOME_MOVE pauses within the one turn.
# ---------------------------------------------------------------------------

def test_two_movers_same_event_same_turn():
    state = _make_both_metronome_battle()
    driver = _create_driver(state, max_turns=1)

    # First mover (Machop, faster) pauses for METRONOME_MOVE
    r1 = _step(driver)
    assert r1["status"] == "pending", f"First pause expected, got {r1['status']!r}"
    assert r1["event"] == METRONOME_MOVE_INT

    # Resume first mover with Splash
    r2 = _step(driver, {"i0": Move.SPLASH.value})
    # Second mover (Snorlax) must also pause on METRONOME_MOVE
    assert r2["status"] == "pending", (
        f"Second METRONOME_MOVE pause expected for second mover, got {r2['status']!r}")
    assert r2["event"] == METRONOME_MOVE_INT, (
        f"Expected METRONOME_MOVE ({METRONOME_MOVE_INT}) for second mover, got {r2['event']}")

    # Resume second mover with Splash; turn completes
    r3 = _step(driver, {"i0": Move.SPLASH.value})
    assert r3["status"] in ("done", "max_turns"), (
        f"After two resumes expected done/max_turns, got {r3['status']!r}")


# ---------------------------------------------------------------------------
# 3. test_same_region_two_occurrences_replay
#
# Two Moody mons (one per side) — both Moody effects fire in the same residual block.
# Expect two sequential MOODY_STATS pauses, each with a distinct answer, and verify
# stat stages reflect answer A on side 0 and answer B on side 1.
# ---------------------------------------------------------------------------

def test_same_region_two_occurrences_replay():
    state = _make_two_moody_battle()
    driver = _create_driver(state, max_turns=1)

    # First MOODY_STATS pause (side 0 Machop fires first in residuals)
    r1 = _step(driver)
    assert r1["status"] == "pending", f"First MOODY_STATS pause expected, got {r1['status']!r}"
    assert r1["event"] == MOODY_STATS_INT

    # Answer A: boost Atk (i0=0), drop Def (i1=1) — for Machop (side 0)
    boost_a, drop_a = 0, 1  # Atk +2, Def -1
    r2 = _step(driver, {"i0": boost_a, "i1": drop_a})

    # Second MOODY_STATS pause (side 1 Snorlax fires)
    assert r2["status"] == "pending", (
        f"Second MOODY_STATS pause expected for side 1, got {r2['status']!r}")
    assert r2["event"] == MOODY_STATS_INT, (
        f"Expected MOODY_STATS ({MOODY_STATS_INT}) for second occurrence, got {r2['event']}")

    # Answer B: boost SpA (i0=2), drop Spe (i1=4) — for Snorlax (side 1)
    boost_b, drop_b = 2, 4  # SpA +2, Spe -1
    r3 = _step(driver, {"i0": boost_b, "i1": drop_b})
    assert r3["status"] in ("done", "max_turns"), (
        f"After two Moody resumes expected done/max_turns, got {r3['status']!r}")

    # Verify stat stages
    final = sweep_io.from_jsonable(r3["state"])

    # Side 0 Machop: stages[0]=+2 (Atk), stages[1]=-1 (Def)
    m0 = final.sides[0].team[final.sides[0].active_indices[0]]
    assert m0.stat_stages[boost_a] == 2, (
        f"Side 0 stat[{boost_a}] should be +2 (answer A boost), got {m0.stat_stages[boost_a]}")
    assert m0.stat_stages[drop_a] == -1, (
        f"Side 0 stat[{drop_a}] should be -1 (answer A drop), got {m0.stat_stages[drop_a]}")

    # Side 1 Snorlax: stages[2]=+2 (SpA), stages[4]=-1 (Spe)
    m1 = final.sides[1].team[final.sides[1].active_indices[0]]
    assert m1.stat_stages[boost_b] == 2, (
        f"Side 1 stat[{boost_b}] should be +2 (answer B boost), got {m1.stat_stages[boost_b]}")
    assert m1.stat_stages[drop_b] == -1, (
        f"Side 1 stat[{drop_b}] should be -1 (answer B drop), got {m1.stat_stages[drop_b]}")


# ---------------------------------------------------------------------------
# 4. test_speed_tie_pauses_each_turn
#
# Two same-speed mons using Splash (no damage) for 2 turns. Expect SPEED_TIE pause on
# turn 1 AND on turn 2 (bug: without fix, turn 2 reuses the injected order without pausing).
# ---------------------------------------------------------------------------

def test_speed_tie_pauses_each_turn():
    state = _make_speed_tie_battle()
    driver = _create_driver(state, max_turns=2)

    # Turn 1: expect SPEED_TIE pause
    r1 = _step(driver)
    assert r1["status"] == "pending", f"Turn 1 expected pending (SPEED_TIE), got {r1['status']!r}"
    assert r1["event"] == SPEED_TIE_INT

    # Resume turn 1: side 0 first
    r2 = _step(driver, {"order": [[0, 0], [1, 0]]})

    # Turn 2: must pause AGAIN on SPEED_TIE
    assert r2["status"] == "pending", (
        f"Turn 2 expected pending (second SPEED_TIE pause), got {r2['status']!r}")
    assert r2["event"] == SPEED_TIE_INT, (
        f"Turn 2 pause event should be SPEED_TIE ({SPEED_TIE_INT}), got {r2['event']}")

    # Resume turn 2: side 1 first this time
    r3 = _step(driver, {"order": [[1, 0], [0, 0]]})
    assert r3["status"] in ("done", "max_turns"), (
        f"After two speed-tie resumes expected done/max_turns, got {r3['status']!r}")


# ---------------------------------------------------------------------------
# 5. test_persistent_override_queue_consumes_in_order
#
# D3: the persistent-override channel is now a consume-once queue mirroring Python's
# _rng_inject semantics. Constructor-injecting a LIST of N answers lets N successive
# occurrences resolve without pausing (in FIFO order); when the queue is empty, the
# next occurrence pauses (NeedsRNG). Verified with two Metronome turns and two answers.
# ---------------------------------------------------------------------------

def test_persistent_override_queue_consumes_in_order():
    state = _make_metronome_battle()
    # Provide TWO persistent answers so both metronome fires (turn 1 and turn 2)
    # can consume from the queue without pausing.
    driver = _create_driver(state,
                            overrides_json={"metronome_move": [
                                Move.SPLASH.value, Move.SPLASH.value]},
                            max_turns=2)

    result = _step(driver)
    assert result["status"] in ("done", "max_turns"), (
        f"Two persistent answers should cover both occurrences; got {result['status']!r}")


def test_persistent_override_queue_exhausted_pauses():
    """A single injected answer covers only the first occurrence; the second pauses."""
    state = _make_metronome_battle()
    driver = _create_driver(state,
                            overrides_json={"metronome_move": Move.SPLASH.value},
                            max_turns=2)

    r1 = _step(driver)
    # Turn 1 consumed the single answer; turn 2's metronome must pause loudly.
    assert r1["status"] == "pending", (
        f"Second occurrence with exhausted queue should pause; got {r1['status']!r}")
    assert r1["event"] == METRONOME_MOVE_INT
