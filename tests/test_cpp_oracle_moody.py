# Oracle pause/resume layer — Stage 7: MOODY_STATS (two-pick Category-A event).
#
# The Moody ability, at end of turn, boosts one random stat (0-6) by +2 and drops a different
# stat (0-6, excl boost) by -1. R&B: acc/eva (indices 5-6) eligible for both picks.
# In the GameDriver pause/resume path this is a Category-A oracle event resolved during
# residuals (residuals.cpp band_late). Unlike other oracle events it needs TWO picks:
# boost_idx (i0) and drop_idx (i1). This must:
#   - pause (NeedsRNG) with event=MOODY_STATS and options = the boost domain [0..6], when no
#     override is set;
#   - honor an injected override / resume answer (both boost and drop indices);
#   - produce identical final state via override vs. pause-then-resume;
#   - fail loud if boost_idx == drop_idx after modulo.
#
# Contract mirrors Python residuals.py:347-360: boost = i0 % 7, drop = i1 % 7. stat_stages
# layout is (Atk, Def, SpA, SpD, Spe, Acc, Eva); boost/drop indices address that tuple.
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.abilities import Ability
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.rng import RNGEvent

from tests.state_builders import make_mon, make_battle

MOODY_STATS_INT = RNGEvent.MOODY_STATS.value  # 29


def _controlled_luck() -> dict:
    return {
        "accuracy_threshold": 0.0, "crit_threshold": 50.0, "damage_roll": 0.5,
        "proc_threshold": 50.0, "secondary_threshold": 50.0, "multi_hit_roll": 0.5,
        "rampage_duration_roll": 0.5, "psywave_roll": 0.5, "flinch_threshold": 50.0,
        "binding_duration_roll": 0.5, "wake_threshold": 50.0, "defrost_threshold": 20.0,
        "paralysis_threshold": 50.0, "confusion_snap_threshold": 50.0,
        "confusion_self_hit_threshold": 50.0, "attract_threshold": 50.0,
        "damage_rolls_per_hit": None, "crits_per_hit": None, "random_mode": False,
    }


def _controlled_turn_luck() -> dict:
    return {"quick_claw_threshold": 50.0, "secondary_threshold": 50.0,
            "luck_tier": 1, "random_mode": False}


def _make_moody_battle():
    """Side 0 active mon has Moody; both sides Splash (no damage). Distinct species => no speed tie.

    The only Category-A oracle event on turn 1 is the end-of-turn MOODY_STATS pick for side 0.
    """
    m0 = make_mon(Species.MACHOP, moves=(Move.SPLASH,), level=50, ability=Ability.MOODY)
    m1 = make_mon(Species.CATERPIE, moves=(Move.SPLASH,), level=50)
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


def _side0_stat_stages(result):
    state = sweep_io.from_jsonable(result["state"])
    side0 = state.sides[0]
    active = side0.active_indices[0]
    return list(side0.team[active].stat_stages)


# ---------------------------------------------------------------------------
# 1. Pause request shape
# ---------------------------------------------------------------------------

def test_pause_returns_pending_moody_stats():
    driver = _create_driver(_make_moody_battle(), max_turns=1)
    result = _step(driver)

    assert result["status"] == "pending", f"Expected pending, got {result['status']!r}"
    assert result["event"] == MOODY_STATS_INT, (
        f"Expected event={MOODY_STATS_INT} (MOODY_STATS), got {result['event']}")
    assert sorted(result["options"]) == [0, 1, 2, 3, 4, 5, 6], (
        f"Expected boost domain [0..6], got {sorted(result['options'])}")


# ---------------------------------------------------------------------------
# 2. Override honored — boost +2 / drop -1 at the chosen indices
# ---------------------------------------------------------------------------

def test_override_moody_stats():
    boost_idx, drop_idx = 1, 3  # Def +2, SpD -1
    driver = _create_driver(_make_moody_battle(),
                            overrides_json={"moody_stats": [boost_idx, drop_idx]}, max_turns=1)
    result = _step(driver)
    assert result["status"] in ("done", "max_turns"), f"Unexpected status: {result['status']!r}"
    stages = _side0_stat_stages(result)
    assert stages[boost_idx] == 2, f"Expected +2 at stat {boost_idx}, got stages={stages}"
    assert stages[drop_idx] == -1, f"Expected -1 at stat {drop_idx}, got stages={stages}"


def test_override_moody_stats_modulo():
    # boost=8 -> 8%7=1 (Def); drop=7 -> 7%7=0 (Atk). R&B: both indices mod 7.
    driver = _create_driver(_make_moody_battle(),
                            overrides_json={"moody_stats": [8, 7]}, max_turns=1)
    result = _step(driver)
    assert result["status"] in ("done", "max_turns")
    stages = _side0_stat_stages(result)
    assert stages[1] == 2, f"Expected +2 at Def (8%7=1), got {stages}"
    assert stages[0] == -1, f"Expected -1 at Atk (7%7=0), got {stages}"


# ---------------------------------------------------------------------------
# 3. Pause-then-resume equals override (final-state equivalence)
# ---------------------------------------------------------------------------

def test_pause_resume_equals_override():
    boost_idx, drop_idx = 4, 0  # Spe +2, Atk -1

    driver_a = _create_driver(_make_moody_battle(),
                              overrides_json={"moody_stats": [boost_idx, drop_idx]}, max_turns=1)
    result_a = _step(driver_a)
    assert result_a["status"] in ("done", "max_turns")

    driver_b = _create_driver(_make_moody_battle(), max_turns=1)
    paused = _step(driver_b)
    assert paused["status"] == "pending", f"Path B didn't pause: {paused['status']}"
    assert paused["event"] == MOODY_STATS_INT
    result_b = _step(driver_b, {"i0": boost_idx, "i1": drop_idx})
    assert result_b["status"] in ("done", "max_turns")

    assert result_a["state"] == result_b["state"], (
        "Override and pause-resume paths produced different final states")


# ---------------------------------------------------------------------------
# 4. R&B semantics: acc/eva indices (5/6) reachable via oracle
# ---------------------------------------------------------------------------

def test_override_acc_boost_eva_drop():
    # R&B: Acc +2 (idx=5), Eva -1 (idx=6) — previously impossible under old semantics.
    driver = _create_driver(_make_moody_battle(),
                            overrides_json={"moody_stats": [5, 6]}, max_turns=1)
    result = _step(driver)
    assert result["status"] in ("done", "max_turns"), f"Unexpected status: {result['status']!r}"
    stages = _side0_stat_stages(result)
    assert stages[5] == 2, f"Expected Acc +2 (idx 5), got stages={stages}"
    assert stages[6] == -1, f"Expected Eva -1 (idx 6), got stages={stages}"


def test_override_eva_boost_acc_drop():
    # Eva +2 (idx=6), Acc -1 (idx=5).
    driver = _create_driver(_make_moody_battle(),
                            overrides_json={"moody_stats": [6, 5]}, max_turns=1)
    result = _step(driver)
    assert result["status"] in ("done", "max_turns"), f"Unexpected status: {result['status']!r}"
    stages = _side0_stat_stages(result)
    assert stages[6] == 2, f"Expected Eva +2 (idx 6), got stages={stages}"
    assert stages[5] == -1, f"Expected Acc -1 (idx 5), got stages={stages}"


# ---------------------------------------------------------------------------
# 5. C++ oracle: boost==drop after modulo raises a loud error
# ---------------------------------------------------------------------------

def test_override_boost_equals_drop_raises():
    # moody_stats: [2, 2] → 2%7==2%7 == 2; must fail loud with "boost==drop" in status.
    driver = _create_driver(_make_moody_battle(),
                            overrides_json={"moody_stats": [2, 2]}, max_turns=1)
    result = _step(driver)
    status = result.get("status", "")
    assert "boost==drop" in status, (
        f"Expected error status containing 'boost==drop', got {status!r}"
    )
