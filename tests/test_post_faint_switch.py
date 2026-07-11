# Port of OLD tests/test_post_faint_switch.py — run_candidate_sweep integration for post-faint
# switch scenarios. TestSimStartPhaseInference and TestFaintThenSweepIntegration use the OLD
# Simulator (no NEW analog); they are DROPPED. TestHasFaintedActive helper tests that exist in
# test_sweep_analysis_helpers.py are DROPPED. Only the run_candidate_sweep-level integration
# from TestSweepPostFaint is kept here.
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
from liveplay.sweep_reconcile import has_fainted_active
from liveplay.sweep_run import run_candidate_sweep
from liveplay.state.battle import BattleState
from liveplay.state.side import SideState
from tests.state_builders import make_mon, make_battle, switch_to, slot, odelta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fainted(mon):
    """Return a copy of mon with hp=0 and fainted=True."""
    return mon._replace(hp=0, fainted=True)


def _post_faint_state(active_species, bench_species, opp_species=Species.POOCHYENA):
    """Build a BattleState where side 0's active Pokemon is fainted and has one bench member."""
    fainted_mon = _fainted(make_mon(active_species, moves=(Move.TACKLE,)))
    bench_mon = make_mon(bench_species, moves=(Move.TACKLE,))
    opp_mon = make_mon(opp_species, moves=(Move.TACKLE,))
    side0 = SideState(team=[fainted_mon, bench_mon], active_indices=[0])
    side1 = SideState(team=[opp_mon], active_indices=[0])
    return BattleState(sides=(side0, side1))


def _switch_message(incoming_species_name: str) -> MatchResult:
    """Minimal PLAYER_SWITCHINMON MatchResult for the given species name."""
    return MatchResult(
        string_id="STRINGID_PLAYER_SWITCHINMON",
        id_value=0,
        constant_name="sText_GoPkmn",
        var_values=[incoming_species_name],
        score=0,
        matched_text="",
        slot_labels=[],
    )


def _usedmove_message(attacker: str, move: str, *, foe: bool = False) -> MatchResult:
    """USEDMOVE message; foe=True → side_hint=1 (opponent), else side_hint=0 (player)."""
    return MatchResult(
        string_id="STRINGID_USEDMOVE",
        id_value=0,
        constant_name="sText_AttackerUsedMove",
        var_values=[attacker, move],
        score=0,
        matched_text="",
        slot_labels=[],
        side_hint=1 if foe else 0,
    )


# ---------------------------------------------------------------------------
# has_fainted_active — integration-level (complementary to helper-level coverage)
# ---------------------------------------------------------------------------

class TestHasFaintedActive:
    def test_true_when_active_fainted_with_bench(self):
        state = _post_faint_state(Species.ROOKIDEE, Species.PIDGEY)
        assert has_fainted_active(state) is True

    def test_false_when_no_fainted_active(self):
        state = make_battle(
            make_mon(Species.ROOKIDEE, moves=(Move.TACKLE,)),
            make_mon(Species.POOCHYENA, moves=(Move.TACKLE,)),
        )
        assert has_fainted_active(state) is False

    def test_false_when_active_fainted_but_no_bench(self):
        fainted = _fainted(make_mon(Species.ROOKIDEE, moves=(Move.TACKLE,)))
        opp = make_mon(Species.POOCHYENA, moves=(Move.TACKLE,))
        state = BattleState(sides=(
            SideState(team=[fainted], active_indices=[0]),
            SideState(team=[opp], active_indices=[0]),
        ))
        assert has_fainted_active(state) is False


# ---------------------------------------------------------------------------
# run_candidate_sweep with post-faint state
# ---------------------------------------------------------------------------

class TestSweepPostFaint:
    def test_produces_exactly_one_candidate(self):
        """Post-faint state + correct PLAYER_SWITCHINMON → exactly 1 candidate, Pidgey active."""
        state = _post_faint_state(Species.ROOKIDEE, Species.PIDGEY)
        candidate = Candidate(state=state)

        msgs = [_switch_message("PIDGEY")]
        result = run_candidate_sweep(msgs, hp_deltas=[], initial_candidates=[candidate])

        assert len(result) == 1
        final = result[0].state
        active_idx = final.sides[0].active_indices[0]
        assert final.sides[0].team[active_idx].species == Species.PIDGEY

    def test_guard_usedmove_filters_candidate(self):
        """USEDMOVE while the simulator expects a post-faint switch is a per-candidate
        contradiction — it FILTERS that candidate. With the sole candidate filtered, the
        standard no-survivors SimulationError fires (no 'disagree on turn phase' text)."""
        state = _post_faint_state(Species.ROOKIDEE, Species.PIDGEY)
        candidate = Candidate(state=state)

        msgs = [
            _usedmove_message("POOCHYENA", "Tackle", foe=True),
            _switch_message("PIDGEY"),
        ]
        with pytest.raises(SimulationError) as exc_info:
            run_candidate_sweep(msgs, hp_deltas=[], initial_candidates=[candidate])
        assert "No candidates survived sweep" in str(exc_info.value)
        assert "disagree on turn phase" not in str(exc_info.value)

    def test_guard_usedmove_raises_filterable_at_helper(self):
        """At the helper level the guard raises PostFaintMovePhaseError, which is NOT a
        SimulationError so callers can distinguish per-candidate filter from fatal abort."""
        state = _post_faint_state(Species.ROOKIDEE, Species.PIDGEY)
        msgs = [_usedmove_message("POOCHYENA", "Tackle", foe=True)]
        known = _extract_known_actions(msgs, state)
        with pytest.raises(PostFaintMovePhaseError):
            _sweep_resolve_candidate_actions(state, msgs, known)
        assert not issubclass(PostFaintMovePhaseError, SimulationError)

    def test_guard_no_switch_message_raises(self):
        """No switch message while side 0 has fainted active → SimulationError."""
        state = _post_faint_state(Species.ROOKIDEE, Species.PIDGEY)
        candidate = Candidate(state=state)

        with pytest.raises(SimulationError, match="side 0"):
            run_candidate_sweep([], hp_deltas=[], initial_candidates=[candidate])

    def test_empty_hp_deltas_accepted(self):
        """Post-faint sweep with empty HP deltas must not fail and must produce a candidate."""
        state = _post_faint_state(Species.ROOKIDEE, Species.PIDGEY)
        candidate = Candidate(state=state)
        msgs = [_switch_message("PIDGEY")]
        result = run_candidate_sweep(msgs, hp_deltas=[], initial_candidates=[candidate])
        assert len(result) == 1
