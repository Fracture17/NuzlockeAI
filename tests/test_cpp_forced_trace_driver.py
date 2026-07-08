# Forced-trace replay driver tests (forced_trace payload in GameDriver).
# Forced mode replays a golden RNG trace: actions are consumed from the answer stream
# rather than chosen by a policy. All 9 tests use random_mode luck (required by forced mode).
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.rng import RNGEvent

from tests.state_builders import make_mon, make_battle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ACTION_SELECT_INT    = RNGEvent.ACTION_SELECT.value     # 19
FORCED_SWITCH_INT    = RNGEvent.FORCED_SWITCH.value     # 20
POST_FAINT_SWITCH_INT = RNGEvent.POST_FAINT_SWITCH.value  # 21
CRIT_INT             = RNGEvent.CRIT.value              # 2
DAMAGE_ROLL_INT      = RNGEvent.DAMAGE_ROLL.value       # 5
SPEED_TIEBREAKER_INT = RNGEvent.SPEED_TIEBREAKER.value  # 32

# kind values: 0=MOVE, 1=SWITCH (from cpp_enumerate_legal_actions shape)
AK_MOVE   = 0
AK_SWITCH = 1


def _random_luck() -> dict:
    """Random-mode damage luck (required for forced_trace)."""
    return {
        "accuracy_threshold": 50.0,
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
        "random_mode": True,
    }


def _random_turn_luck() -> dict:
    return {"quick_claw_threshold": 50.0, "secondary_threshold": 50.0,
            "luck_tier": 1, "random_mode": True}


def _controlled_luck() -> dict:
    """Controlled-mode damage luck (NOT valid for forced_trace)."""
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


def _action_select(turn, actions_p0, actions_p1):
    """Build an ACTION_SELECT answer entry for the forced_trace answers list."""
    return {
        "turn": turn,
        "event": ACTION_SELECT_INT,
        "side": -1,
        "i0": -1,
        "i1": -1,
        "actions_p0": actions_p0,
        "actions_p1": actions_p1,
    }


def _move_action(move_slot):
    """Build an ExecAction dict for a MOVE."""
    return {
        "kind": AK_MOVE,
        "move_slot": move_slot,
        "move_override": -1,
        "switch_to_slot": -1,
        "target_side": -1,
        "target_slot": 0,
        "source_slot": 0,
    }


def _switch_action(switch_to_slot, source_slot=0):
    """Build an ExecAction dict for a SWITCH."""
    return {
        "kind": AK_SWITCH,
        "move_slot": -1,
        "move_override": -1,
        "switch_to_slot": switch_to_slot,
        "target_side": -1,
        "target_slot": 0,
        "source_slot": source_slot,
    }


def _rng_entry(turn, event_int, occurrence, outcome):
    return {"turn": turn, "event": event_int, "occurrence": occurrence, "outcome": outcome}


def _tiebreaker_entries(turn, *, occ0_val=0.9, occ1_val=0.1):
    """SPEED_TIEBREAKER is drawn unconditionally once per action in random_mode
    (core.py:316/319). In singles 1v1, two draws per turn: occ 0 (side 0's action)
    and occ 1 (side 1's action)."""
    return [
        _rng_entry(turn, SPEED_TIEBREAKER_INT, 0, occ0_val),
        _rng_entry(turn, SPEED_TIEBREAKER_INT, 1, occ1_val),
    ]


def _create_driver(state, forced_trace, *, controlled=False, max_turns=2):
    """Create a GameDriver with a forced_trace payload."""
    luck = _controlled_luck() if controlled else _random_luck()
    turn_luck = _controlled_turn_luck() if controlled else _random_turn_luck()
    args = {
        "state": sweep_io.to_jsonable(state),
        "seed": 42,
        "luck_p0": luck,
        "luck_p1": luck,
        "turn_luck_p0": turn_luck,
        "turn_luck_p1": turn_luck,
        "max_turns": max_turns,
        "forced_trace": forced_trace,
    }
    return cpp.GameDriver(json.dumps(args))


def _step(driver):
    return json.loads(driver.step())


def _make_two_move_battle():
    """Two mons with SPLASH (slot 0) and TACKLE (slot 1). Different speeds to avoid speed tie."""
    m0 = make_mon(Species.MACHOP, moves=(Move.SPLASH, Move.TACKLE), level=50)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH, Move.TACKLE), level=30)
    return make_battle(m0, m1)


# ---------------------------------------------------------------------------
# Test 1: forced_trace requires random_mode luck
# ---------------------------------------------------------------------------

def test_forced_requires_random_mode():
    """forced_trace + controlled luck → error mentioning random_mode."""
    state = _make_two_move_battle()
    trace = {
        "rng": [],
        "answers": [_action_select(1, [_move_action(0)], [_move_action(0)])],
    }
    # GameDriver constructor should raise or _run should return error status
    error_seen = False
    try:
        driver = cpp.GameDriver(json.dumps({
            "state": sweep_io.to_jsonable(state),
            "seed": 0,
            "luck_p0": _controlled_luck(),
            "luck_p1": _controlled_luck(),
            "turn_luck_p0": _controlled_turn_luck(),
            "turn_luck_p1": _controlled_turn_luck(),
            "max_turns": 2,
            "forced_trace": trace,
        }))
        result = json.loads(driver.step())
        error_seen = "random_mode" in result.get("status", "")
    except RuntimeError as e:
        error_seen = "random_mode" in str(e)
    assert error_seen, "Expected an error mentioning 'random_mode' for forced_trace + controlled luck"


# ---------------------------------------------------------------------------
# Test 2: forced actions drive turns
# ---------------------------------------------------------------------------

def test_forced_actions_drive_turns():
    """Two turns: turn 1 both sides SPLASH, turn 2 both sides TACKLE. Action log reflects it."""
    state = _make_two_move_battle()
    trace = {
        "rng": [
            *_tiebreaker_entries(1),
            *_tiebreaker_entries(2),
            # Turn 2: both Tackles hit (100 acc, saturated → no ACCURACY entries)
            _rng_entry(2, DAMAGE_ROLL_INT, 0, 0.5),
            _rng_entry(2, CRIT_INT, 0, False),
            _rng_entry(2, DAMAGE_ROLL_INT, 1, 0.5),
            _rng_entry(2, CRIT_INT, 1, False),
        ],
        "answers": [
            _action_select(1, [_move_action(0)], [_move_action(0)]),  # SPLASH
            _action_select(2, [_move_action(1)], [_move_action(1)]),  # TACKLE
        ],
    }
    driver = _create_driver(state, trace, max_turns=2)
    result = _step(driver)

    assert result["status"] in ("done", "max_turns"), f"Unexpected status: {result['status']!r}"

    action_log = result["action_log"]
    # Find the two "actions" phase entries
    action_entries = [e for e in action_log if e.get("phase") == "actions"]
    assert len(action_entries) == 2, f"Expected 2 action entries, got {len(action_entries)}"

    # Turn 1: both used SPLASH (move_slot 0)
    t1_p0 = action_entries[0]["p0"]
    t1_p1 = action_entries[0]["p1"]
    assert t1_p0[0]["move_slot"] == 0, f"Turn 1 p0 move_slot should be 0, got {t1_p0[0]['move_slot']}"
    assert t1_p1[0]["move_slot"] == 0, f"Turn 1 p1 move_slot should be 0, got {t1_p1[0]['move_slot']}"

    # Turn 2: both used TACKLE (move_slot 1)
    t2_p0 = action_entries[1]["p0"]
    t2_p1 = action_entries[1]["p1"]
    assert t2_p0[0]["move_slot"] == 1, f"Turn 2 p0 move_slot should be 1, got {t2_p0[0]['move_slot']}"
    assert t2_p1[0]["move_slot"] == 1, f"Turn 2 p1 move_slot should be 1, got {t2_p1[0]['move_slot']}"


# ---------------------------------------------------------------------------
# Test 3: wrong turn number in answer causes mismatch
# ---------------------------------------------------------------------------

def test_forced_answer_turn_mismatch():
    """Answer entry with turn=5 when game expects turn=1 → forced_trace_mismatch."""
    state = _make_two_move_battle()
    trace = {
        "rng": [],
        "answers": [
            # wrong turn: should be 1, set to 5
            _action_select(5, [_move_action(0)], [_move_action(0)]),
        ],
    }
    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)
    assert "forced_trace_mismatch" in result["status"], (
        f"Expected forced_trace_mismatch in status, got: {result['status']!r}")


# ---------------------------------------------------------------------------
# Test 4: answer stream exhausted mid-game
# ---------------------------------------------------------------------------

def test_forced_answers_exhausted_midgame():
    """Only 1 ACTION_SELECT answer but max_turns=2 → forced_trace_mismatch on exhaustion."""
    state = _make_two_move_battle()
    trace = {
        "rng": [
            # Turn 1 completes cleanly so the mismatch is genuinely answer exhaustion
            *_tiebreaker_entries(1),
        ],
        "answers": [
            _action_select(1, [_move_action(0)], [_move_action(0)]),
            # no turn-2 answer
        ],
    }
    driver = _create_driver(state, trace, max_turns=2)
    result = _step(driver)
    assert "forced_trace_mismatch" in result["status"], (
        f"Expected forced_trace_mismatch in status, got: {result['status']!r}")


# ---------------------------------------------------------------------------
# Test 5: leftover answers trigger verify_exhausted
# ---------------------------------------------------------------------------

def test_forced_leftover_answers_fail():
    """3 answers but game ends at max_turns=2 → verify_exhausted error in status."""
    state = _make_two_move_battle()
    trace = {
        "rng": [
            # Both turns complete cleanly so the failure is genuinely the leftover answer
            *_tiebreaker_entries(1),
            *_tiebreaker_entries(2),
        ],
        "answers": [
            _action_select(1, [_move_action(0)], [_move_action(0)]),
            _action_select(2, [_move_action(0)], [_move_action(0)]),
            _action_select(3, [_move_action(0)], [_move_action(0)]),  # extra
        ],
    }
    driver = _create_driver(state, trace, max_turns=2)
    result = _step(driver)
    assert "forced_trace_mismatch" in result["status"], (
        f"Expected forced_trace_mismatch in status, got: {result['status']!r}")


# ---------------------------------------------------------------------------
# Test 6: unconsumed rng entry triggers verify_exhausted
# ---------------------------------------------------------------------------

def test_forced_leftover_rng_fails():
    """An rng entry that nothing consumes → verify_exhausted error listing unconsumed rng."""
    state = _make_two_move_battle()
    trace = {
        "rng": [
            *_tiebreaker_entries(1),
            # ACCURACY entry that nothing consumes (SPLASH is accuracy-None → saturated)
            {"turn": 1, "event": 1, "occurrence": 0, "outcome": 0.9},
        ],
        "answers": [
            _action_select(1, [_move_action(0)], [_move_action(0)]),
        ],
    }
    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)
    assert "forced_trace_mismatch" in result["status"], (
        f"Expected forced_trace_mismatch in status, got: {result['status']!r}")


# ---------------------------------------------------------------------------
# Test 7: post-faint switch consumed correctly
# ---------------------------------------------------------------------------

def test_forced_post_faint_switch():
    """Side 1 has two mons; side 0 high-level mon KOs side 1's first mon.
    forced_trace includes ACTION_SELECT for turn 1 + a POST_FAINT_SWITCH for side 1.
    Assert replacement came in (final state active mon species matches bench mon).
    """
    # Side 0: very strong attacker (level 100 with Tackle)
    attacker = make_mon(Species.MACHAMP, moves=(Move.TACKLE,), level=100)
    # Side 1: weak first mon (level 5), bench mon (level 5 too)
    victim = make_mon(Species.CATERPIE, moves=(Move.SPLASH,), level=5)
    bench = make_mon(Species.RATTATA, moves=(Move.SPLASH,), level=5)

    state = make_battle(
        attacker, victim,
        team0=[attacker],
        team1=[victim, bench],
    )

    # After turn 1, victim should faint, triggering POST_FAINT_SWITCH for side 1.
    # The replacement is bench mon at team index 1.
    post_faint_answer = {
        "turn": 1,
        "event": POST_FAINT_SWITCH_INT,
        "side": 1,
        "i0": 1,   # team index of Rattata
        "i1": -1,
        "actions_p0": None,
        "actions_p1": None,
    }

    trace = {
        "rng": [
            *_tiebreaker_entries(1),
            # Machamp's Tackle hits (100 acc, saturated); Caterpie faints before acting
            _rng_entry(1, DAMAGE_ROLL_INT, 0, 0.5),
            _rng_entry(1, CRIT_INT, 0, False),
        ],
        "answers": [
            _action_select(1, [_move_action(0)], [_move_action(0)]),
            post_faint_answer,
        ],
    }

    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)

    assert "forced_trace_mismatch" not in result["status"], (
        f"Unexpected mismatch: {result['status']!r}")
    assert result["status"] in ("done", "max_turns"), (
        f"Unexpected status: {result['status']!r}")

    # Verify Rattata (bench slot 1) came in on side 1
    final_state = sweep_io.from_jsonable(result["state"])
    side1 = final_state.sides[1]
    active_mon = side1.team[side1.active_indices[0]]
    assert active_mon.species == Species.RATTATA, (
        f"Expected Rattata as replacement, got {active_mon.species}")


# ---------------------------------------------------------------------------
# Test 8: unwired Cat-A oracle pause becomes forced_trace_mismatch
# ---------------------------------------------------------------------------

def test_forced_pause_becomes_mismatch():
    """An unwired Cat-A event during forced replay → forced_trace_mismatch status.

    In random_mode, A3 oracle events (Moody, Metronome, Effect Spore, ...) resolve natively
    and never pause, so they can't exercise this path. Roar's target pick goes through
    Policy.select_phaze, which ReplayPolicy deliberately leaves unwired until B3 Task 3 —
    it throws forced_trace_mismatch, which the driver surfaces as an error status.
    Opponent has 2 bench mons so the phaze pick is a real choice.
    """
    from liveplay.data.moves import Move as Mv

    attacker = make_mon(Species.MACHOP, moves=(Mv.ROAR,), level=50)
    defender = make_mon(Species.SNORLAX, moves=(Mv.SPLASH,), level=50)
    bench1 = make_mon(Species.CATERPIE, moves=(Mv.SPLASH,), level=10)
    bench2 = make_mon(Species.RATTATA, moves=(Mv.SPLASH,), level=10)

    state = make_battle(
        attacker, defender,
        team0=[attacker],
        team1=[defender, bench1, bench2],
    )

    # Forced action: Roar (move_slot 0). Tiebreakers provided so the mismatch
    # is genuinely the unwired select_phaze pause, not a missing tiebreaker.
    # Roar/Splash are accuracy-None → no ACCURACY entries.
    trace = {
        "rng": [
            *_tiebreaker_entries(1),
        ],
        "answers": [
            _action_select(1, [_move_action(0)], [_move_action(0)]),
        ],
    }

    driver = _create_driver(state, trace, max_turns=1)
    result = _step(driver)

    assert "forced_trace_mismatch" in result["status"], (
        f"Expected forced_trace_mismatch in status, got: {result['status']!r}")


# ---------------------------------------------------------------------------
# Test 9: non-forced mode unchanged (regression)
# ---------------------------------------------------------------------------

def test_nonforced_unchanged():
    """Same battle without forced_trace, random policies: runs to done/max_turns."""
    state = _make_two_move_battle()
    args = {
        "state": sweep_io.to_jsonable(state),
        "seed": 42,
        "luck_p0": _random_luck(),
        "luck_p1": _random_luck(),
        "turn_luck_p0": _random_turn_luck(),
        "turn_luck_p1": _random_turn_luck(),
        "max_turns": 2,
    }
    driver = cpp.GameDriver(json.dumps(args))
    result = json.loads(driver.step())
    assert result["status"] in ("done", "max_turns"), (
        f"Expected done/max_turns, got: {result['status']!r}")
