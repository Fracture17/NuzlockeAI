# Port of OLD tests/test_postfaint_move_phase.py — Darian1 Magikarp crash regression.
# A candidate whose sim-state has a fainted active but emulator messages show a move
# being used is a per-candidate contradiction; it must FILTER that candidate, not abort
# the whole sweep. test_valid_sibling_candidate_survives is PORTED but the opponent-fainted
# path exercises a different code path from the player-fainted path; see notes below.
from __future__ import annotations

import pytest

from liveplay.battle_types import MatchResult
from liveplay.candidate import Candidate
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.engine_select import SimulationError
from liveplay.sweep_actions import (
    PostFaintMovePhaseError,
    _extract_known_actions,
    _sweep_resolve_candidate_actions,
)
from liveplay.sweep_run import run_candidate_sweep
from liveplay.state.battle import BattleState
from liveplay.state.side import SideState
from tests.state_builders import make_mon, make_battle, odelta


def _mr(string_id, *, constant_name="", var_values=None, side_hint=None):
    return MatchResult(
        string_id=string_id, id_value=0, constant_name=constant_name,
        var_values=var_values or [], score=0, matched_text="", slot_labels=[],
        side_hint=side_hint,
    )


def _usedmove(attacker, move, *, foe=False):
    """USEDMOVE message; foe=True → side_hint=1, else side_hint=0."""
    return _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
               var_values=[attacker, move], side_hint=1 if foe else 0)


def _fainted_opp_active_state():
    """Player active alive; opponent active fainted with a living bench member."""
    player = make_mon(Species.BUDEW, moves=(Move.ABSORB,))
    fainted_opp = make_mon(Species.MAGIKARP, moves=(Move.SPLASH,))._replace(hp=0, fainted=True)
    bench_opp = make_mon(Species.GYARADOS, moves=(Move.TACKLE,))
    side0 = SideState(team=[player], active_indices=[0])
    side1 = SideState(team=[fainted_opp, bench_opp], active_indices=[0])
    return BattleState(sides=(side0, side1))


def test_resolve_raises_filterable_not_fatal():
    """The guard raises PostFaintMovePhaseError (a per-candidate filter signal), not
    SimulationError — so the caller can distinguish 'filter this candidate' from fatal.

    Use a move that IS in Magikarp's modeled moveset (SPLASH) so the C1 moveset-desync
    check doesn't intercept before _sweep_resolve_candidate_actions can fire PostFaintMovePhaseError.
    """
    state = _fainted_opp_active_state()
    messages = [_usedmove("MAGIKARP", "SPLASH", foe=True)]
    known = _extract_known_actions(messages, state)
    with pytest.raises(PostFaintMovePhaseError):
        _sweep_resolve_candidate_actions(state, messages, known)
    assert not issubclass(PostFaintMovePhaseError, SimulationError)


def test_sweep_filters_contradicted_candidate():
    """run_candidate_sweep must filter the contradicted candidate rather than leak the raw
    post-faint guard error. With the sole candidate filtered, the standard no-survivors
    SimulationError fires — its message is the no-candidate one, NOT the turn-phase guard text.

    HYDRO PUMP is not in Magikarp's modeled moveset, so C1 (UnreproducibleObservedMoveError)
    fires first — but the end result is identical: all candidates filtered → SimulationError
    with no-candidate message.
    """
    state = _fainted_opp_active_state()
    messages = [_usedmove("MAGIKARP", "HYDRO PUMP", foe=True)]
    with pytest.raises(SimulationError) as exc_info:
        run_candidate_sweep(
            messages=messages,
            hp_deltas=[],
            initial_candidates=[Candidate(state=state)],
        )
    assert "No candidates survived sweep" in str(exc_info.value)
    assert "disagree on turn phase" not in str(exc_info.value)


def test_valid_sibling_candidate_survives():
    """The core fix: when one candidate is contradicted (fainted active vs observed move)
    but a sibling candidate keeps the mon alive, the sibling must survive."""
    # Valid candidate: Bulbasaur alive at full HP, takes the observed Tackle.
    charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
    bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=50)
    good_state = make_battle(charizard, bulbasaur)
    # Contradicted candidate: same matchup but opponent Bulbasaur already fainted, with a
    # living bench member so the sim would be at AWAIT_POST_FAINT_SWITCH.
    bad_player = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
    bad_opp = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=50)._replace(hp=0, fainted=True)
    bad_bench = make_mon(Species.IVYSAUR, moves=(Move.TACKLE,), level=50)
    bad_state = BattleState(sides=(
        SideState(team=[bad_player], active_indices=[0]),
        SideState(team=[bad_opp, bad_bench], active_indices=[0]),
    ))

    messages = [
        _usedmove("CHARIZARD", "Tackle"),
        _usedmove("BULBASAUR", "Splash", foe=True),
    ]
    survivors = run_candidate_sweep(
        messages=messages,
        hp_deltas=[odelta(bulbasaur.species, (48, 38), max_hp=bulbasaur.max_hp)],
        initial_candidates=[Candidate(state=bad_state), Candidate(state=good_state)],
    )
    assert len(survivors) >= 1
