"""End-to-end integration tests for doubles sweep: non-KO, KO, and singles regression.

LEDGER
======
PORTED:
  test_non_ko_doubles     — all four mons act, no faint; sweep recovers HP
  test_ko_doubles         — CHARIZARD KOs CATERPIE; KO slot has hp=0, survivors match
  test_singles_regression — 1v1 CHARIZARD vs SNORLAX; sweep recovers opp HP

DROPPED: none
ALREADY-COVERED: none
FAILED-NEEDS-REVIEW: none

API MAPPING (OLD → NEW):
  OLD make_sim + CapturingLogger swap → NEW run_with_capture(state, a0, a1, config) -> (state, log)
  OLD run_candidate_sweep from src.simulation_runner → from liveplay.sweep_run
  OLD BAD luck sim → SweepConfig() (default SWEEP_LUCK derived from BAD)
  OLD GOOD luck sim → SweepConfig(sideN=SideOverrides(crit=True, roll=1.0, extra_overrides={...}))
  OLD TurnPhase/request asserts → assert on returned BattleState fields
"""
import copy
import math

from liveplay.battle_types import MatchResult
from liveplay.candidate import Candidate
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.logger import LogEvent
from liveplay.sweep_driver import SweepConfig, run_with_capture
from liveplay.sweep_run import run_candidate_sweep
from tests.state_builders import (
    dslot, make_battle, make_doubles_battle, make_mon, odelta, slot,
)


# ---------------------------------------------------------------------------
# Message builders
# ---------------------------------------------------------------------------

def _mr(string_id, *, constant_name="", var_values=None, matched_text="", side_hint=None):
    return MatchResult(
        string_id=string_id, id_value=0, constant_name=constant_name,
        var_values=var_values or [], score=0, matched_text=matched_text, slot_labels=[],
        side_hint=side_hint,
    )


def _usedmove(attacker_upper, move_display, *, foe=False):
    """USEDMOVE message. foe=True → side_hint=1 (opponent)."""
    return _mr(
        "STRINGID_USEDMOVE",
        constant_name="sText_AttackerUsedMove",
        var_values=[attacker_upper, move_display],
        side_hint=1 if foe else 0,
    )


def _foe_faint(species_upper):
    return _mr(
        "STRINGID_TARGETFAINTED",
        var_values=[species_upper],
        matched_text=f"Foe {species_upper.title()}",
    )


def _hp_to_k(hp: int, max_hp: int) -> int:
    """Convert raw HP to k-pixel bar value (mirrors the game's bar formula)."""
    if hp == 0:
        return 0
    return max(1, math.floor(hp * 48 / max_hp))


def _run_one_turn(state, side0_actions, side1_actions):
    """Drive C++ engine through one turn; return (final_state, capturing_logger).

    Uses default SWEEP_LUCK (BAD for crits/secondaries) to avoid uncontrolled RNG events.
    """
    return run_with_capture(state, side0_actions, side1_actions, SweepConfig())


def _move_use_order(capturing):
    """Return (species, move, side) tuples in MOVE_USE event order."""
    return [
        (kw["user"], kw["move"], kw["side"])
        for ev, kw in capturing.events
        if ev == LogEvent.MOVE_USE
    ]


# ---------------------------------------------------------------------------
# Test 1: Non-KO doubles — all four mons act, no faint
# ---------------------------------------------------------------------------

def test_non_ko_doubles():
    """Non-KO doubles: four mons act, sweep recovers HP for all active slots."""
    p0 = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
    p1 = make_mon(Species.PIDGEOT, moves=(Move.GUST,), level=50)
    o0 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    o1 = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)

    pristine = make_doubles_battle(p0, p1, o0, o1)
    state_for_engine = copy.deepcopy(pristine)

    final, capturing = _run_one_turn(
        state_for_engine,
        [dslot(0, target=0, source=0), dslot(0, target=1, source=1)],
        [dslot(0, target=0, source=0), dslot(0, target=0, source=1)],
    )
    assert final is not None, "run_with_capture returned None — engine error"

    for s in [0, 1]:
        for pos, idx in enumerate(final.sides[s].active_indices):
            assert not final.sides[s].team[idx].fainted, (
                f"Unexpected faint: side {s} slot {pos}"
            )

    move_use_order = _move_use_order(capturing)
    assert len(move_use_order) == 4, f"Expected 4 MOVE_USE events, got {len(move_use_order)}"
    messages = [
        _usedmove(sp.name, mv.name.replace("_", " ").title(), foe=(side == 1))
        for sp, mv, side in move_use_order
    ]

    hp_deltas = []
    for pos in range(2):
        mon = pristine.sides[1].team[pristine.sides[1].active_indices[pos]]
        start_hp = mon.hp
        final_hp = final.sides[1].team[final.sides[1].active_indices[pos]].hp
        k_before = _hp_to_k(start_hp, mon.max_hp)
        k_after = _hp_to_k(final_hp, mon.max_hp)
        if k_before != k_after:
            hp_deltas.append(odelta(mon.species, (k_before, k_after), max_hp=mon.max_hp, slot=pos))

    candidates = run_candidate_sweep(
        messages=messages,
        hp_deltas=hp_deltas,
        initial_candidates=[Candidate(state=pristine)],
    )
    assert len(candidates) >= 1, "Sweep returned no candidates"

    def _final_hp_matches(cand):
        for s in [0, 1]:
            for pos, idx in enumerate(cand.state.sides[s].active_indices):
                expected = final.sides[s].team[final.sides[s].active_indices[pos]].hp
                if cand.state.sides[s].team[idx].hp != expected:
                    return False
        return True

    assert any(_final_hp_matches(c) for c in candidates), (
        "No candidate matched engine final HP"
    )


# ---------------------------------------------------------------------------
# Test 2: KO doubles — CHARIZARD KOs CATERPIE (opp slot0)
# ---------------------------------------------------------------------------

def test_ko_doubles():
    """KO doubles: CATERPIE is KO'd, KO slot has hp=0, surviving mons match engine HP."""
    p0 = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
    p1 = make_mon(Species.PIDGEOT, moves=(Move.SPLASH,), level=50)
    o0 = make_mon(Species.CATERPIE, moves=(Move.SPLASH,), level=5)
    o1 = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)

    pristine = make_doubles_battle(p0, p1, o0, o1)
    state_for_engine = copy.deepcopy(pristine)

    final, capturing = _run_one_turn(
        state_for_engine,
        [dslot(0, target=0, source=0), dslot(0, target=0, source=1)],
        [dslot(0, target=0, source=0), dslot(0, target=0, source=1)],
    )
    assert final is not None, "run_with_capture returned None — engine error"

    caterpie_idx = final.sides[1].active_indices[0]
    assert final.sides[1].team[caterpie_idx].hp == 0, "CATERPIE should have fainted"

    messages = []
    for ev, kw in capturing.events:
        if ev == LogEvent.MOVE_USE:
            sp = kw["user"]
            mv = kw["move"]
            messages.append(_usedmove(sp.name, mv.name.replace("_", " ").title(), foe=(kw["side"] == 1)))
        elif ev == LogEvent.FAINT:
            sp = kw["pokemon"]
            side = kw["side"]
            if side == 1:
                messages.append(_foe_faint(sp.name))
            else:
                messages.append(_mr("STRINGID_ATTACKERFAINTED", var_values=[sp.name]))
        elif ev == LogEvent.EXP_GAIN:
            messages.append(_mr(
                "STRINGID_PKMNGAINEDEXP",
                var_values=[kw["pokemon"].name, str(kw["amount"])],
            ))

    hp_deltas = []
    for pos in range(2):
        mon = pristine.sides[1].team[pristine.sides[1].active_indices[pos]]
        start_hp = mon.hp
        final_hp = final.sides[1].team[final.sides[1].active_indices[pos]].hp
        k_before = _hp_to_k(start_hp, mon.max_hp)
        k_after = _hp_to_k(final_hp, mon.max_hp)
        if k_before != k_after:
            hp_deltas.append(odelta(mon.species, (k_before, k_after), max_hp=mon.max_hp, slot=pos))

    candidates = run_candidate_sweep(
        messages=messages,
        hp_deltas=hp_deltas,
        initial_candidates=[Candidate(state=pristine)],
    )
    assert len(candidates) >= 1, "Sweep returned no candidates"

    def _ko_slot_zero(cand):
        idx = cand.state.sides[1].active_indices[0]
        return cand.state.sides[1].team[idx].hp == 0

    assert any(_ko_slot_zero(c) for c in candidates), (
        "No candidate has hp=0 for KO'd opp slot0"
    )

    def _survivors_match(cand):
        for s in [0, 1]:
            for pos, idx in enumerate(cand.state.sides[s].active_indices):
                final_idx = final.sides[s].active_indices[pos]
                expected = final.sides[s].team[final_idx].hp
                actual = cand.state.sides[s].team[idx].hp
                if s == 1 and pos == 0:
                    continue  # KO'd slot; checked separately
                if actual != expected:
                    return False
        return True

    assert any(_survivors_match(c) for c in candidates), (
        "No candidate matched surviving mons' final HP"
    )


# ---------------------------------------------------------------------------
# Test 3: Singles regression — same drive-capture-sweep pattern for 1v1
# ---------------------------------------------------------------------------

def test_singles_regression():
    """Singles regression: 1v1 sweep works after doubles changes."""
    p = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
    o = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)

    pristine = make_battle(p, o)
    state_for_engine = copy.deepcopy(pristine)

    final, capturing = run_with_capture(state_for_engine, slot(0), slot(0), SweepConfig())
    assert final is not None, "run_with_capture returned None — engine error"

    assert not final.sides[1].team[final.sides[1].active_indices[0]].fainted, (
        "SNORLAX should survive CHARIZARD Tackle"
    )

    messages = [
        _usedmove(sp.name, mv.name.replace("_", " ").title(), foe=(side == 1))
        for sp, mv, side in _move_use_order(capturing)
    ]

    opp_max_hp = pristine.sides[1].team[pristine.sides[1].active_indices[0]].max_hp
    opp_start_hp = pristine.sides[1].team[pristine.sides[1].active_indices[0]].hp
    opp_final_hp = final.sides[1].team[final.sides[1].active_indices[0]].hp
    k_before = _hp_to_k(opp_start_hp, opp_max_hp)
    k_after = _hp_to_k(opp_final_hp, opp_max_hp)

    opp_mon = pristine.sides[1].team[pristine.sides[1].active_indices[0]]
    candidates = run_candidate_sweep(
        messages=messages,
        hp_deltas=[odelta(opp_mon.species, (k_before, k_after), max_hp=opp_max_hp)],
        initial_candidates=[Candidate(state=pristine)],
    )
    assert len(candidates) >= 1, "Sweep returned no candidates"

    def _hp_matches(cand):
        idx = cand.state.sides[1].active_indices[0]
        return cand.state.sides[1].team[idx].hp == opp_final_hp

    assert any(_hp_matches(c) for c in candidates), (
        "No candidate matched engine final opponent HP"
    )
