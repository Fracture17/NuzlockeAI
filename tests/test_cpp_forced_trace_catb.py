# Cat-B forced-trace consumption tests.
# Each test provides a forced_trace rng payload that dictates a specific Cat-B outcome and
# asserts the observable game effect. All tests use random_mode luck (required for forced mode).
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status
from liveplay.rng import RNGEvent

from tests.state_builders import make_mon, make_battle


# ---------------------------------------------------------------------------
# Shared helpers (mirror tests/test_cpp_forced_trace_driver.py)
# ---------------------------------------------------------------------------

ACCURACY_INT           = RNGEvent.ACCURACY.value            # 1
CRIT_INT               = RNGEvent.CRIT.value                # 2
DAMAGE_ROLL_INT        = RNGEvent.DAMAGE_ROLL.value         # 5
MULTI_HIT_COUNT_INT    = RNGEvent.MULTI_HIT_COUNT.value     # 7
CONFUSION_SELF_HIT_INT = RNGEvent.CONFUSION_SELF_HIT.value  # 11
ATTRACT_IMMOBILIZE_INT = RNGEvent.ATTRACT_IMMOBILIZE.value  # 12
FULL_PARALYSIS_INT     = RNGEvent.FULL_PARALYSIS.value      # 13
QUICK_CLAW_INT         = RNGEvent.QUICK_CLAW.value          # 15
BINDING_DURATION_INT   = RNGEvent.BINDING_DURATION.value    # 17
RAMPAGE_DURATION_INT   = RNGEvent.RAMPAGE_DURATION.value    # 18
SPEED_TIEBREAKER_INT   = RNGEvent.SPEED_TIEBREAKER.value    # 32
ACTION_SELECT_INT      = RNGEvent.ACTION_SELECT.value       # 19

AK_MOVE = 0


def _random_luck():
    return {
        "accuracy_threshold": 50.0, "crit_threshold": 50.0, "damage_roll": 0.5,
        "proc_threshold": 50.0, "secondary_threshold": 50.0, "multi_hit_roll": 0.5,
        "rampage_duration_roll": 0.5, "psywave_roll": 0.5, "flinch_threshold": 50.0,
        "binding_duration_roll": 0.5, "wake_threshold": 50.0, "defrost_threshold": 20.0,
        "paralysis_threshold": 50.0, "confusion_snap_threshold": 50.0,
        "confusion_self_hit_threshold": 50.0, "attract_threshold": 50.0,
        "damage_rolls_per_hit": None, "crits_per_hit": None, "random_mode": True,
    }


def _random_turn_luck():
    return {"quick_claw_threshold": 50.0, "secondary_threshold": 50.0,
            "luck_tier": 1, "random_mode": True}


def _move_action(move_slot, *, source_slot=0, target_slot=0):
    return {
        "kind": AK_MOVE, "move_slot": move_slot, "move_override": -1,
        "switch_to_slot": -1, "target_side": -1, "target_slot": target_slot,
        "source_slot": source_slot,
    }


def _action_select(turn, actions_p0, actions_p1):
    return {
        "turn": turn, "event": ACTION_SELECT_INT, "side": -1, "i0": -1, "i1": -1,
        "actions_p0": actions_p0, "actions_p1": actions_p1,
    }


def _rng_entry(turn, event_int, occurrence, outcome):
    return {"turn": turn, "event": event_int, "occurrence": occurrence, "outcome": outcome}


def _tiebreaker_entries(turn, *, occ0_val=0.9, occ1_val=0.1):
    """SPEED_TIEBREAKER is drawn once per action in random_mode (rng.py:564).
    In singles 1v1, two draws per turn: occ 0 (side 0's action) and occ 1 (side 1's action).
    Default values keep side 0's action first (higher val sorts first for non-trick-room)."""
    return [
        _rng_entry(turn, SPEED_TIEBREAKER_INT, 0, occ0_val),
        _rng_entry(turn, SPEED_TIEBREAKER_INT, 1, occ1_val),
    ]


def _create_driver(state, forced_trace, *, max_turns=2):
    luck = _random_luck()
    turn_luck = _random_turn_luck()
    args = {
        "state": sweep_io.to_jsonable(state),
        "seed": 42,
        "luck_p0": luck, "luck_p1": luck,
        "turn_luck_p0": turn_luck, "turn_luck_p1": turn_luck,
        "max_turns": max_turns,
        "forced_trace": forced_trace,
    }
    return cpp.GameDriver(json.dumps(args))


def _step(driver):
    return json.loads(driver.step())


def _make_slam_battle():
    """Machop (faster, side 0) and Snorlax (slower, side 1) both knowing Slam.
    Slam has 90 accuracy — sub-100, so ACCURACY is genuinely drawn/recorded.
    (100-acc moves like Tackle saturate: neither engine consults ACCURACY.)"""
    m0 = make_mon(Species.MACHOP, moves=(Move.SLAM,), level=50)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SLAM,), level=30)
    return make_battle(m0, m1)


def _hp_after(result, side):
    """Get active mon's HP from result state."""
    state = sweep_io.from_jsonable(result["state"])
    s = state.sides[side]
    return s.team[s.active_indices[0]].hp


# ---------------------------------------------------------------------------
# Test 1: ACCURACY forced false → miss; forced true → hit
# ---------------------------------------------------------------------------

def test_accuracy_forced_false_miss():
    """ACCURACY=False → Slam misses; defender HP unchanged."""
    state = _make_slam_battle()
    m0 = state.sides[0].team[0]
    m1 = state.sides[1].team[0]
    trace = {
        "rng": [
            *_tiebreaker_entries(1),
            _rng_entry(1, ACCURACY_INT, 0, False),   # Machop misses
            _rng_entry(1, ACCURACY_INT, 1, False),   # Snorlax misses
        ],
        "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
    }
    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)
    assert "forced_trace_mismatch" not in result["status"], result["status"]
    assert _hp_after(result, 0) == m0.max_hp, "p0 HP should be unchanged (missed)"
    assert _hp_after(result, 1) == m1.max_hp, "p1 HP should be unchanged (missed)"


def test_accuracy_forced_true_hits():
    """ACCURACY=True → Slam hits; defender HP decreases."""
    state = _make_slam_battle()
    m1 = state.sides[1].team[0]
    trace = {
        "rng": [
            *_tiebreaker_entries(1),
            _rng_entry(1, ACCURACY_INT, 0, True),
            _rng_entry(1, DAMAGE_ROLL_INT, 0, 0.5),
            _rng_entry(1, CRIT_INT, 0, False),
            _rng_entry(1, ACCURACY_INT, 1, True),
            _rng_entry(1, DAMAGE_ROLL_INT, 1, 0.5),
            _rng_entry(1, CRIT_INT, 1, False),
        ],
        "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
    }
    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)
    assert "forced_trace_mismatch" not in result["status"], result["status"]
    assert _hp_after(result, 1) < m1.max_hp, "p1 HP should decrease (hit)"


# ---------------------------------------------------------------------------
# Test 2: DAMAGE_ROLL mapping — f=0.999 vs f=0.0 give different damage
# ---------------------------------------------------------------------------

def test_damage_roll_high_vs_low():
    """High damage roll (f=0.999) produces more damage than low (f=0.0)."""
    state = _make_slam_battle()

    def _run(roll_val):
        trace = {
            "rng": [
                *_tiebreaker_entries(1),
                _rng_entry(1, ACCURACY_INT, 0, True),
                _rng_entry(1, DAMAGE_ROLL_INT, 0, roll_val),
                _rng_entry(1, CRIT_INT, 0, False),
                _rng_entry(1, ACCURACY_INT, 1, False),  # Snorlax misses to isolate
            ],
            "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
        }
        driver = _create_driver(state, trace, max_turns=1)
        result = _step(driver)
        assert "forced_trace_mismatch" not in result["status"], result["status"]
        return _hp_after(result, 1)

    hp_high = _run(0.999)
    hp_low  = _run(0.0)
    assert hp_low > hp_high, f"Low roll should leave more HP: high={hp_high}, low={hp_low}"


def test_damage_roll_equivalence():
    """Forced f=0.5 matches controlled roll=0.5 for same attacker/defender pair.
    int(0.5 * 15) == 7 in both Python and C++."""
    m0 = make_mon(Species.MACHOP, moves=(Move.SLAM,), level=50)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=30)
    state = make_battle(m0, m1)

    trace = {
        "rng": [
            *_tiebreaker_entries(1),
            _rng_entry(1, ACCURACY_INT, 0, True),
            _rng_entry(1, DAMAGE_ROLL_INT, 0, 0.5),
            _rng_entry(1, CRIT_INT, 0, False),
        ],
        "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
    }
    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)
    assert "forced_trace_mismatch" not in result["status"], result["status"]
    hp_forced = _hp_after(result, 1)

    # Controlled mode: damage_roll=0.5 → int(0.5 * 15) = 7 also
    luck_controlled = {
        "accuracy_threshold": 0.0, "crit_threshold": 50.0, "damage_roll": 0.5,
        "proc_threshold": 50.0, "secondary_threshold": 50.0, "multi_hit_roll": 0.5,
        "rampage_duration_roll": 0.5, "psywave_roll": 0.5, "flinch_threshold": 50.0,
        "binding_duration_roll": 0.5, "wake_threshold": 50.0, "defrost_threshold": 20.0,
        "paralysis_threshold": 50.0, "confusion_snap_threshold": 50.0,
        "confusion_self_hit_threshold": 50.0, "attract_threshold": 50.0,
        "damage_rolls_per_hit": None, "crits_per_hit": None, "random_mode": False,
    }
    turn_luck_ctrl = {"quick_claw_threshold": 50.0, "secondary_threshold": 50.0,
                      "luck_tier": 1, "random_mode": False}
    args_ctrl = {
        "state": sweep_io.to_jsonable(state), "seed": 0,
        "luck_p0": luck_controlled, "luck_p1": luck_controlled,
        "turn_luck_p0": turn_luck_ctrl, "turn_luck_p1": turn_luck_ctrl,
        "max_turns": 1,
    }
    driver_ctrl = cpp.GameDriver(json.dumps(args_ctrl))
    result_ctrl = json.loads(driver_ctrl.step())
    hp_ctrl = _hp_after(result_ctrl, 1)
    assert hp_forced == hp_ctrl, (
        f"Forced f=0.5 and controlled damage_roll=0.5 should give same HP: "
        f"forced={hp_forced}, ctrl={hp_ctrl}"
    )


# ---------------------------------------------------------------------------
# Test 3: CRIT forced true vs false — strictly more damage when true
# ---------------------------------------------------------------------------

def test_crit_forced_true_vs_false():
    """Forced CRIT=True gives strictly more damage than CRIT=False (same damage roll)."""
    state = _make_slam_battle()

    def _run(crit_val):
        trace = {
            "rng": [
                *_tiebreaker_entries(1),
                _rng_entry(1, ACCURACY_INT, 0, True),
                _rng_entry(1, DAMAGE_ROLL_INT, 0, 0.5),
                _rng_entry(1, CRIT_INT, 0, crit_val),
                _rng_entry(1, ACCURACY_INT, 1, False),
            ],
            "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
        }
        driver = _create_driver(state, trace, max_turns=1)
        result = _step(driver)
        assert "forced_trace_mismatch" not in result["status"], result["status"]
        return _hp_after(result, 1)

    hp_crit = _run(True)
    hp_no_crit = _run(False)
    assert hp_crit < hp_no_crit, (
        f"Crit should do more damage: crit hp={hp_crit}, no-crit hp={hp_no_crit}"
    )


# ---------------------------------------------------------------------------
# Test 4: Occurrence ordering — two ACCURACY draws in one turn, consumed in order
# ---------------------------------------------------------------------------

def test_occurrence_ordering():
    """Two Slam users → occ 0 and occ 1 consumed in recorded order."""
    state = _make_slam_battle()
    trace_normal = {
        "rng": [
            *_tiebreaker_entries(1),
            _rng_entry(1, ACCURACY_INT, 0, True),
            _rng_entry(1, DAMAGE_ROLL_INT, 0, 0.5),
            _rng_entry(1, CRIT_INT, 0, False),
            _rng_entry(1, ACCURACY_INT, 1, False),   # second draw misses
        ],
        "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
    }
    driver = _create_driver(state, trace_normal, max_turns=1)
    result = _step(driver)
    assert "forced_trace_mismatch" not in result["status"], result["status"]
    m1_start_hp = state.sides[1].team[0].max_hp
    assert _hp_after(result, 1) < m1_start_hp, "First attack (occ=0, hit) should have reduced HP"

    # Missing occ 1 ACCURACY → mismatch when second draw is attempted
    trace_missing_occ1 = {
        "rng": [
            *_tiebreaker_entries(1),
            _rng_entry(1, ACCURACY_INT, 0, True),
            _rng_entry(1, DAMAGE_ROLL_INT, 0, 0.5),
            _rng_entry(1, CRIT_INT, 0, False),
            # no occ 1 ACCURACY entry
        ],
        "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
    }
    driver2 = _create_driver(state, trace_missing_occ1, max_turns=1)
    result2 = _step(driver2)
    assert "forced_trace_mismatch" in result2["status"], (
        f"Expected mismatch for missing occ 1, got: {result2['status']!r}"
    )


# ---------------------------------------------------------------------------
# Test 5: Missing rng entry → forced_trace_mismatch
# ---------------------------------------------------------------------------

def test_missing_rng_entry_mismatch():
    """Move used but no ACCURACY entry in trace → forced_trace_mismatch."""
    state = _make_slam_battle()
    trace = {
        "rng": [
            # Tiebreakers provided, but no ACCURACY entry
            *_tiebreaker_entries(1),
        ],
        "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
    }
    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)
    assert "forced_trace_mismatch" in result["status"], (
        f"Expected forced_trace_mismatch, got: {result['status']!r}"
    )


# ---------------------------------------------------------------------------
# Test 6: Leftover rng entry → verify_exhausted mismatch
# ---------------------------------------------------------------------------

def test_leftover_rng_catb_entry_fails():
    """A Cat-B rng entry that should be consumed but is extra → verify_exhausted mismatch."""
    state = _make_slam_battle()
    # Both miss, so no CRIT draw. Extra CRIT entry left unconsumed.
    trace = {
        "rng": [
            *_tiebreaker_entries(1),
            _rng_entry(1, ACCURACY_INT, 0, False),
            _rng_entry(1, ACCURACY_INT, 1, False),
            _rng_entry(1, CRIT_INT, 0, False),   # extra: no crit draw after miss
        ],
        "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
    }
    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)
    assert "forced_trace_mismatch" in result["status"], (
        f"Expected forced_trace_mismatch for leftover entry, got: {result['status']!r}"
    )


# ---------------------------------------------------------------------------
# Test 7: FULL_PARALYSIS polarity
# ---------------------------------------------------------------------------

def test_full_paralysis_polarity_blocked():
    """Paralyzed mon, forced inner Bernoulli=True → cannot act (Python: return not True = False)."""
    # rng.py:508: return not _roll_bernoulli(FULL_PARALYSIS, chance)
    # Stored True = inner draw True → Python returns False (cannot act)
    m0 = make_mon(Species.MACHOP, moves=(Move.TACKLE,), level=50,
                  status=Status.PARALYSIS)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=30)
    state = make_battle(m0, m1)

    trace = {
        "rng": [
            *_tiebreaker_entries(1),
            _rng_entry(1, FULL_PARALYSIS_INT, 0, True),   # blocked
        ],
        "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
    }
    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)
    assert "forced_trace_mismatch" not in result["status"], result["status"]
    assert _hp_after(result, 1) == m1.max_hp, (
        "Paralyzed mon forced inactive → no damage dealt to opponent"
    )


def test_full_paralysis_polarity_acts():
    """Paralyzed mon, forced inner Bernoulli=False → can act (Python: return not False = True)."""
    m0 = make_mon(Species.MACHOP, moves=(Move.TACKLE,), level=50,
                  status=Status.PARALYSIS)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=30)
    state = make_battle(m0, m1)

    trace = {
        "rng": [
            *_tiebreaker_entries(1),
            _rng_entry(1, FULL_PARALYSIS_INT, 0, False),  # can act
            # Tackle is 100-acc: ACCURACY saturates, no entry recorded/consumed
            _rng_entry(1, DAMAGE_ROLL_INT, 0, 0.5),
            _rng_entry(1, CRIT_INT, 0, False),
        ],
        "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
    }
    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)
    assert "forced_trace_mismatch" not in result["status"], result["status"]
    assert _hp_after(result, 1) < m1.max_hp, "Paralyzed mon forced active → damage dealt"


# ---------------------------------------------------------------------------
# Test 8: MULTI_HIT_COUNT forced — Fury Swipes 5 vs 2 hits → different total damage
# ---------------------------------------------------------------------------

def test_multi_hit_count_forced():
    """Fury Swipes forced to 5 vs 2 hits → different total damage."""
    m0 = make_mon(Species.MEOWTH, moves=(Move.FURY_SWIPES,), level=50)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    state = make_battle(m0, m1)

    def _run(hit_count):
        rng_entries = [
            *_tiebreaker_entries(1),
            _rng_entry(1, ACCURACY_INT, 0, True),
            _rng_entry(1, MULTI_HIT_COUNT_INT, 0, hit_count),
        ]
        for i in range(hit_count):
            rng_entries.append(_rng_entry(1, DAMAGE_ROLL_INT, i, 0.5))
            rng_entries.append(_rng_entry(1, CRIT_INT, i, False))
        trace = {
            "rng": rng_entries,
            "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
        }
        driver = _create_driver(state, trace, max_turns=1)
        result = _step(driver)
        assert "forced_trace_mismatch" not in result["status"], (
            f"hit_count={hit_count}: {result['status']}"
        )
        return _hp_after(result, 1)

    hp_5 = _run(5)
    hp_2 = _run(2)
    assert hp_5 < hp_2, f"5 hits should deal more damage than 2: hp_5={hp_5}, hp_2={hp_2}"


# ---------------------------------------------------------------------------
# Test 9: QUICK_CLAW forced true on slower mon → moves first
# ---------------------------------------------------------------------------

def test_quick_claw_forced_true_slower_moves_first():
    """Machamp (side 1, slow) with Quick Claw forced True → acts first and KOs Caterpie."""
    m0 = make_mon(Species.CATERPIE, moves=(Move.SPLASH,), level=1)
    m1 = make_mon(Species.MACHAMP, moves=(Move.TACKLE,), level=100,
                  item=Item.QUICK_CLAW)
    state = make_battle(m0, m1)

    # Quick Claw is evaluated per-entry during build_pending_entries (same pass as tiebreaker).
    # Side 1 (Machamp) gets QUICK_CLAW occ=0; the tiebreaker entries follow (occ=0,1).
    # When Quick Claw fires, Machamp's action gets priority_item_fires=True (speed=9999).
    trace = {
        "rng": [
            *_tiebreaker_entries(1),
            _rng_entry(1, QUICK_CLAW_INT, 0, True),   # Machamp's Quick Claw fires
            # Tackle is 100-acc: ACCURACY saturates, no entry recorded/consumed
            _rng_entry(1, DAMAGE_ROLL_INT, 0, 0.999),
            _rng_entry(1, CRIT_INT, 0, False),
        ],
        "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
    }
    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)
    assert "forced_trace_mismatch" not in result["status"], result["status"]
    state_out = sweep_io.from_jsonable(result["state"])
    active_p0 = state_out.sides[0].team[state_out.sides[0].active_indices[0]]
    assert active_p0.fainted or active_p0.hp == 0, (
        "Caterpie should be fainted after Machamp hits first with Quick Claw"
    )


# ---------------------------------------------------------------------------
# Test 10: Quick Draw divergence — no entry consumed
# ---------------------------------------------------------------------------

def test_quick_draw_no_trace_entry():
    """Quick Draw ability in forced mode returns false, nothing consumed from trace."""
    m0 = make_mon(Species.MACHOP, moves=(Move.TACKLE,), level=50,
                  ability=Ability.QUICK_DRAW)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=30)
    state = make_battle(m0, m1)

    # Only tiebreaker + damage/crit — no Quick Draw entry (and no ACCURACY:
    # Tackle is 100-acc, saturated). If code tries to consume a Quick Draw trace
    # entry it would mismatch; INTENTIONAL_DIVERGENCES.md #1 says forced mode
    # must return false with no consumption.
    trace = {
        "rng": [
            *_tiebreaker_entries(1),
            _rng_entry(1, DAMAGE_ROLL_INT, 0, 0.5),
            _rng_entry(1, CRIT_INT, 0, False),
        ],
        "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
    }
    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)
    assert "forced_trace_mismatch" not in result["status"], (
        f"Quick Draw in forced mode should not consume a trace entry, got: {result['status']!r}"
    )


# ---------------------------------------------------------------------------
# Test 11: BINDING_DURATION forced int honored
# ---------------------------------------------------------------------------

def test_binding_duration_forced():
    """Wrap forced to 4 vs 5 — no mismatch; BOUND volatile applied to defender."""
    m0 = make_mon(Species.EKANS, moves=(Move.WRAP,), level=50)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    state = make_battle(m0, m1)

    for duration in (4, 5):
        trace = {
            "rng": [
                *_tiebreaker_entries(1),
                # Wrap is 100-acc in this game's data: ACCURACY saturates, no entry
                _rng_entry(1, DAMAGE_ROLL_INT, 0, 0.5),
                _rng_entry(1, CRIT_INT, 0, False),
                _rng_entry(1, BINDING_DURATION_INT, 0, duration),
            ],
            "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
        }
        driver = _create_driver(state, trace, max_turns=1)
        result = _step(driver)
        assert "forced_trace_mismatch" not in result["status"], (
            f"duration={duration}: {result['status']}"
        )
        state_out = sweep_io.from_jsonable(result["state"])
        snorlax = state_out.sides[1].team[state_out.sides[1].active_indices[0]]
        # timed_volatiles holds (VolatileEffect, turns) tuples; BOUND = 4 (pokemon.py)
        has_bound = any(effect == 4 for effect, _turns in snorlax.timed_volatiles)
        assert has_bound, f"Snorlax should have BOUND volatile after Wrap (duration={duration})"


# ---------------------------------------------------------------------------
# Test 12: Saturated accuracy (Aerial Ace) — no ACCURACY entry needed
# ---------------------------------------------------------------------------

def test_saturated_accuracy_no_entry_needed():
    """Aerial Ace (accuracy=None, always hits) — no ACCURACY rng entry → no mismatch."""
    m0 = make_mon(Species.MACHOP, moves=(Move.AERIAL_ACE,), level=50)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=30)
    state = make_battle(m0, m1)

    trace = {
        "rng": [
            *_tiebreaker_entries(1),
            # No ACCURACY entry — is_none short-circuit fires before forced lookup (rng.py:330)
            _rng_entry(1, DAMAGE_ROLL_INT, 0, 0.5),
            _rng_entry(1, CRIT_INT, 0, False),
        ],
        "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
    }
    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)
    assert "forced_trace_mismatch" not in result["status"], (
        f"Aerial Ace should bypass ACCURACY forced lookup: {result['status']!r}"
    )
    m1_start = state.sides[1].team[0].max_hp
    assert _hp_after(result, 1) < m1_start, "Aerial Ace should always hit"
