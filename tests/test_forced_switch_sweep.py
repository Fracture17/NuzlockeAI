# Port of OLD tests/test_forced_switch_sweep.py — cross-boundary forced-switch sweep.
#
# Already covered by test_sweep_analysis_helpers.py:
#   - _validate_forced_opponent_switch (passes/raises/doubles) → DROPPED (already covered)
# NOT yet covered — ported here:
#   - _validate_known_opponent_action skipping when opp active fainted
#   - _extract_known_actions recording voluntary switch on living active
#   - Integration: cross-boundary forced switch does not raise
from __future__ import annotations

import pytest

from liveplay.battle_types import MatchResult
from liveplay.actions import ActionKind
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.sweep_actions import (
    _extract_known_actions,
    _validate_known_opponent_action,
    UnexpectedOpponentActionError,
)
from liveplay.state.battle import BattleState
from liveplay.state.side import SideState
from tests.state_builders import make_mon, make_battle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mr(string_id, *, constant_name="", var_values=None):
    return MatchResult(
        string_id=string_id,
        id_value=0,
        constant_name=constant_name,
        var_values=var_values or [],
        score=0,
        matched_text="",
        slot_labels=[],
        side_hint=None,
    )


def _fainted(mon):
    return mon._replace(hp=0, fainted=True)


def _opp_switchin_msg(species_name: str) -> MatchResult:
    """Opponent SWITCHINMON message (trainer-side constant → side 1)."""
    return _mr(
        "STRINGID_SWITCHINMON",
        constant_name="sText_Trainer1SentOutPkmn2",
        var_values=["Youngster Calvin", species_name],
    )


def _build_fainted_active_opp_state(
    fainted_species: Species,
    bench_species: Species,
    player_species: Species = Species.RATTATA,
) -> BattleState:
    """Opponent's active mon is fainted with one living bench member."""
    fainted_mon = _fainted(make_mon(fainted_species, moves=(Move.TACKLE,)))
    bench_mon = make_mon(bench_species, moves=(Move.TACKLE,))
    player_mon = make_mon(player_species, moves=(Move.TACKLE,))
    side0 = SideState(team=[player_mon], active_indices=[0])
    side1 = SideState(team=[fainted_mon, bench_mon], active_indices=[0])
    return BattleState(sides=(side0, side1))


# ---------------------------------------------------------------------------
# Part 1 unit: fainted active → _validate_known_opponent_action skips scoring
# ---------------------------------------------------------------------------

def test_validate_known_action_skips_when_opp_active_fainted():
    """Part 1 unit: switch recorded in known_actions but validation skips when opp active fainted."""
    state = _build_fainted_active_opp_state(Species.ROOKIDEE, Species.NIDORAN_M)
    messages = [_opp_switchin_msg("NIDORAN M")]
    result = _extract_known_actions(messages, state)
    # The switch IS recorded (needed by post-faint path)
    assert result[1][0] is not None
    assert result[1][0].kind == ActionKind.SWITCH
    # _validate_known_opponent_action must not raise (skips probability scoring)
    _validate_known_opponent_action(result, state)  # must not raise


def test_extract_known_actions_records_voluntary_switch_when_active_alive():
    """Contrast: non-fainted active + no pending faint → voluntary switch IS recorded."""
    player_mon = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
    active_opp = make_mon(Species.PIDGEY, moves=(Move.TACKLE,))
    bench_opp = make_mon(Species.NIDORAN_M, moves=(Move.TACKLE,))
    side0 = SideState(team=[player_mon], active_indices=[0])
    side1 = SideState(team=[active_opp, bench_opp], active_indices=[0])
    state = BattleState(sides=(side0, side1))

    messages = [_opp_switchin_msg("NIDORAN M")]
    result = _extract_known_actions(messages, state)
    assert result[1][0] is not None
    assert result[1][0].kind == ActionKind.SWITCH
    assert result[1][0].switch_to_slot == 1


# ---------------------------------------------------------------------------
# Part 1 regression: full pipeline does not raise for cross-boundary forced switch
# ---------------------------------------------------------------------------

def test_validate_does_not_raise_for_cross_boundary_forced_switch():
    """Part 1 regression: fainted opp active + SWITCHINMON msg → no UnexpectedOpponentActionError."""
    state = _build_fainted_active_opp_state(Species.ROOKIDEE, Species.NIDORAN_M)
    messages = [_opp_switchin_msg("NIDORAN M")]
    known = _extract_known_actions(messages, state)
    # Should not raise — opp fainted active → validation skipped
    _validate_known_opponent_action(known, state)
