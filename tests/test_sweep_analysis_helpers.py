# Tests for sweep "analysis" helpers ported to liveplay/sweep_actions.py.
# Covers: _collapse_metronome_calls, message_crit_counts_with_state,
# _message_hit_counts_with_state, _detect_multi_hit, _validate_forced_opponent_switch,
# _opponent_switch_in_actions, _sweep_resolve_candidate_actions, PostFaintMovePhaseError.
import pytest

from liveplay.battle_types import ActionGroup, MatchResult
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.actions import Action, ActionKind
from liveplay.engine_select import SimulationError
from liveplay.state.side import SideState
from liveplay.state.battle import BattleState

from tests.state_builders import make_mon, make_battle, make_doubles_battle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mr(string_id, *, constant_name="", var_values=None, side_hint=None, matched_text=""):
    vals = var_values or []
    return MatchResult(
        string_id=string_id,
        id_value=0,
        constant_name=constant_name,
        var_values=vals,
        score=0,
        matched_text=matched_text,
        side_hint=side_hint,
    )


def _usedmove(attacker: str, move: str, *, foe: bool = False) -> MatchResult:
    return _mr(
        "STRINGID_USEDMOVE",
        constant_name="sText_AttackerUsedMove",
        var_values=[attacker, move],
        side_hint=1 if foe else 0,
    )


def _crit_mr() -> MatchResult:
    return _mr("STRINGID_CRITICALHIT")


def _hitxtimes_mr(n: int) -> MatchResult:
    return _mr("STRINGID_HITXTIMES", var_values=[str(n)])


def _group(primary, secondaries=None):
    return ActionGroup(primary=primary, secondaries=secondaries or [], hp_readings=[])


def _usedmove_group(attacker: str, move: str, secondaries=None, *, side_hint: int = 0):
    primary = _mr(
        "STRINGID_USEDMOVE",
        constant_name="sText_AttackerUsedMove",
        var_values=[attacker, move],
        side_hint=side_hint,
    )
    return _group(primary, secondaries=secondaries)


def _opp_switchin_msg(species_name: str) -> MatchResult:
    """Opponent STRINGID_SWITCHINMON message (trainer-side constant → side 1)."""
    return _mr(
        "STRINGID_SWITCHINMON",
        constant_name="sText_Trainer1SentOutPkmn2",
        var_values=["Youngster Calvin", species_name],
    )


def _fainted(mon):
    return mon._replace(hp=0, fainted=True)


def _fainted_opp_state(fainted_species=Species.MAGIKARP, bench_species=Species.GYARADOS,
                       player_species=Species.BUDEW):
    """Singles: player alive, opponent active fainted with living bench (has_fainted_active → True)."""
    player = make_mon(player_species, moves=(Move.ABSORB,))
    fainted_opp = _fainted(make_mon(fainted_species, moves=(Move.SPLASH,)))
    bench_opp = make_mon(bench_species, moves=(Move.TACKLE,))
    side0 = SideState(team=[player], active_indices=[0])
    side1 = SideState(team=[fainted_opp, bench_opp], active_indices=[0])
    return BattleState(sides=(side0, side1))


# ---------------------------------------------------------------------------
# PostFaintMovePhaseError
# ---------------------------------------------------------------------------

class TestPostFaintMovePhaseError:
    """PostFaintMovePhaseError is a distinct (non-SimulationError) exception."""

    def test_is_exception(self):
        from liveplay.sweep_actions import PostFaintMovePhaseError
        err = PostFaintMovePhaseError("test")
        assert isinstance(err, Exception)

    def test_not_subclass_of_simulation_error(self):
        from liveplay.sweep_actions import PostFaintMovePhaseError
        assert not issubclass(PostFaintMovePhaseError, SimulationError)


# ---------------------------------------------------------------------------
# _collapse_metronome_calls
# ---------------------------------------------------------------------------

class TestMetronomeCollapse:
    """Metronome emits two USEDMOVE lines (wrapper + called). The collapse function
    merges the pair into one tagged message and drops the called-move USEDMOVE."""

    def _state(self):
        player = make_mon(Species.SKITTY, moves=(Move.TACKLE,), level=12)
        foe = make_mon(Species.SWIRLIX, moves=(Move.METRONOME,), level=12)
        return make_battle(player, foe)

    def _metronome_then(self, called_name):
        wrapper = _mr(
            "STRINGID_USEDMOVE",
            constant_name="sText_AttackerUsedMove",
            var_values=["Swirlix", "Metronome"],
            side_hint=1,
        )
        called = _mr(
            "STRINGID_USEDMOVE",
            constant_name="sText_AttackerUsedMove",
            var_values=["Swirlix", called_name],
            side_hint=1,
        )
        return [wrapper, called]

    def test_pair_collapses_to_single_tagged_message(self):
        from liveplay.sweep_actions import _collapse_metronome_calls
        collapsed = _collapse_metronome_calls(self._metronome_then("Water Gun"), self._state())
        assert len(collapsed) == 1
        assert collapsed[0].var_values[1] == "Metronome"
        assert collapsed[0].metronome_called == Move.WATER_GUN

    def test_unknown_called_move_hard_crashes(self):
        from liveplay.sweep_actions import _collapse_metronome_calls
        with pytest.raises(SimulationError):
            _collapse_metronome_calls(self._metronome_then("Worry Seed"), self._state())

    def test_charge_not_fuzzy_matched_to_charm(self):
        # Regression (Issue 23): 'Charge' absent from Move enum but Lev-dist 2 from CHARM.
        from liveplay.sweep_actions import _collapse_metronome_calls
        with pytest.raises(SimulationError):
            _collapse_metronome_calls(self._metronome_then("Charge"), self._state())

    def test_gen3_fused_spelling_resolves(self):
        from liveplay.sweep_actions import _collapse_metronome_calls
        collapsed = _collapse_metronome_calls(self._metronome_then("SolarBeam"), self._state())
        assert len(collapsed) == 1
        assert collapsed[0].metronome_called == Move.SOLAR_BEAM

    def test_plain_moves_untouched(self):
        from liveplay.sweep_actions import _collapse_metronome_calls
        msgs = [_mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                    var_values=["Swirlix", "Water Gun"], side_hint=1)]
        collapsed = _collapse_metronome_calls(msgs, self._state())
        assert len(collapsed) == 1
        assert collapsed[0].metronome_called is None


class TestSleepTalkCollapse:
    """Sleep Talk shares Metronome's 2-USEDMOVE / 1-MOVE_USE structure."""

    def _state(self):
        player = make_mon(Species.SKITTY, moves=(Move.TACKLE,), level=20)
        foe = make_mon(Species.SNORLAX, moves=(Move.SLEEP_TALK, Move.BODY_SLAM), level=20)
        return make_battle(player, foe)

    def _sleeptalk_then(self, called_name):
        wrapper = _mr(
            "STRINGID_USEDMOVE",
            constant_name="sText_AttackerUsedMove",
            var_values=["Snorlax", "Sleep Talk"],
            side_hint=1,
        )
        called = _mr(
            "STRINGID_USEDMOVE",
            constant_name="sText_AttackerUsedMove",
            var_values=["Snorlax", called_name],
            side_hint=1,
        )
        return [wrapper, called]

    def test_pair_collapses_to_single_tagged_message(self):
        from liveplay.sweep_actions import _collapse_metronome_calls
        collapsed = _collapse_metronome_calls(self._sleeptalk_then("Body Slam"), self._state())
        assert len(collapsed) == 1
        assert collapsed[0].var_values[1] == "Sleep Talk"
        assert collapsed[0].metronome_called == Move.BODY_SLAM

    def test_unknown_called_move_hard_crashes(self):
        from liveplay.sweep_actions import _collapse_metronome_calls
        with pytest.raises(SimulationError):
            _collapse_metronome_calls(self._sleeptalk_then("Worry Seed"), self._state())

    def test_lone_sleep_talk_untouched(self):
        # Sleep Talk with no following called-move USEDMOVE passes through unchanged.
        from liveplay.sweep_actions import _collapse_metronome_calls
        msgs = [_mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                    var_values=["Snorlax", "Sleep Talk"], side_hint=1)]
        collapsed = _collapse_metronome_calls(msgs, self._state())
        assert len(collapsed) == 1
        assert collapsed[0].metronome_called is None


# ---------------------------------------------------------------------------
# message_crit_counts_with_state
# ---------------------------------------------------------------------------

class TestMessageCritCountsWithState:
    """Per-mover crit counts derived from flat message stream + state."""

    def _state(self):
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.TACKLE,))
        return make_battle(charizard, bulbasaur)

    def test_first_mover_crits(self):
        """USEDMOVE(A), CRITICALHIT, USEDMOVE(B) → [1, 0]."""
        from liveplay.sweep_actions import message_crit_counts_with_state
        state = self._state()
        messages = [
            _usedmove("Charizard", "Tackle", foe=False),
            _crit_mr(),
            _usedmove("Bulbasaur", "Tackle", foe=True),
        ]
        assert message_crit_counts_with_state(messages, state) == [1, 0]

    def test_second_mover_crits(self):
        """USEDMOVE(A), USEDMOVE(B), CRITICALHIT → [0, 1]."""
        from liveplay.sweep_actions import message_crit_counts_with_state
        state = self._state()
        messages = [
            _usedmove("Charizard", "Tackle", foe=False),
            _usedmove("Bulbasaur", "Tackle", foe=True),
            _crit_mr(),
        ]
        assert message_crit_counts_with_state(messages, state) == [0, 1]

    def test_multi_hit_both_crits_attributed_to_first_mover(self):
        """USEDMOVE(A), HITXTIMES(2), CRITICALHIT, CRITICALHIT, USEDMOVE(B) → [2, 0]."""
        from liveplay.sweep_actions import message_crit_counts_with_state
        state = self._state()
        messages = [
            _usedmove("Charizard", "Tackle", foe=False),
            _hitxtimes_mr(2),
            _crit_mr(),
            _crit_mr(),
            _usedmove("Bulbasaur", "Tackle", foe=True),
        ]
        assert message_crit_counts_with_state(messages, state) == [2, 0]

    def test_no_crit_messages(self):
        """No CRITICALHIT messages → [0, 0]."""
        from liveplay.sweep_actions import message_crit_counts_with_state
        state = self._state()
        messages = [
            _usedmove("Charizard", "Tackle", foe=False),
            _usedmove("Bulbasaur", "Tackle", foe=True),
        ]
        assert message_crit_counts_with_state(messages, state) == [0, 0]

    def test_leading_crit_before_any_usedmove_ignored(self):
        """CRITICALHIT before any USEDMOVE must not crash and must not be attributed."""
        from liveplay.sweep_actions import message_crit_counts_with_state
        state = self._state()
        messages = [
            _crit_mr(),
            _usedmove("Charizard", "Tackle", foe=False),
            _usedmove("Bulbasaur", "Tackle", foe=True),
        ]
        assert message_crit_counts_with_state(messages, state) == [0, 0]


# ---------------------------------------------------------------------------
# _message_hit_counts_with_state
# ---------------------------------------------------------------------------

class TestMessageHitCountsWithState:
    """Per-mover hit counts from STRINGID_HITXTIMES messages."""

    def _state(self):
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.TACKLE,))
        return make_battle(charizard, bulbasaur)

    def test_default_hit_count_one(self):
        from liveplay.sweep_actions import _message_hit_counts_with_state
        state = self._state()
        messages = [
            _usedmove("Charizard", "Tackle", foe=False),
            _usedmove("Bulbasaur", "Tackle", foe=True),
        ]
        assert _message_hit_counts_with_state(messages, state) == [1, 1]

    def test_hitxtimes_parsed_for_first_mover(self):
        from liveplay.sweep_actions import _message_hit_counts_with_state
        state = self._state()
        messages = [
            _usedmove("Charizard", "Dual Wingbeat", foe=False),
            _hitxtimes_mr(3),
            _usedmove("Bulbasaur", "Tackle", foe=True),
        ]
        assert _message_hit_counts_with_state(messages, state) == [3, 1]

    def test_hitxtimes_parsed_for_second_mover(self):
        from liveplay.sweep_actions import _message_hit_counts_with_state
        state = self._state()
        messages = [
            _usedmove("Charizard", "Tackle", foe=False),
            _usedmove("Bulbasaur", "Fury Swipes", foe=True),
            _hitxtimes_mr(4),
        ]
        assert _message_hit_counts_with_state(messages, state) == [1, 4]


# ---------------------------------------------------------------------------
# _detect_multi_hit
# ---------------------------------------------------------------------------

class TestDetectMultiHit:
    """_detect_multi_hit returns (n_hits, n_crits) from a message list."""

    def test_no_hitxtimes_returns_one(self):
        from liveplay.sweep_actions import _detect_multi_hit
        group = _usedmove_group("Pikachu", "Tackle")
        assert _detect_multi_hit([group]) == (1, 0)

    def test_hitxtimes_parsed(self):
        from liveplay.sweep_actions import _detect_multi_hit
        secondary = _mr("STRINGID_HITXTIMES", var_values=["3"])
        group = _usedmove_group("Pikachu", "Double Slap", secondaries=[secondary])
        assert _detect_multi_hit([group]) == (3, 0)

    def test_critical_hit_counted(self):
        from liveplay.sweep_actions import _detect_multi_hit
        crit_sec = _crit_mr()
        group = _usedmove_group("Pikachu", "Tackle", secondaries=[crit_sec])
        assert _detect_multi_hit([group]) == (1, 1)

    def test_multi_hit_with_crits(self):
        from liveplay.sweep_actions import _detect_multi_hit
        hit_sec = _mr("STRINGID_HITXTIMES", var_values=["4"])
        crit_sec = _crit_mr()
        group = _usedmove_group("Pikachu", "Fury Swipes", secondaries=[hit_sec, crit_sec])
        assert _detect_multi_hit([group]) == (4, 1)

    def test_flat_match_results(self):
        # _detect_multi_hit also accepts flat MatchResult objects (no .secondaries)
        from liveplay.sweep_actions import _detect_multi_hit
        msgs = [
            _mr("STRINGID_HITXTIMES", var_values=["2"]),
            _crit_mr(),
        ]
        assert _detect_multi_hit(msgs) == (2, 1)


# ---------------------------------------------------------------------------
# _opponent_switch_in_actions
# ---------------------------------------------------------------------------

class TestOpponentSwitchInActions:
    """_opponent_switch_in_actions builds SWITCH Action branches for opponent switch-ins."""

    def test_no_switch_in_returns_empty_tuple_branch(self):
        from liveplay.sweep_actions import _opponent_switch_in_actions
        state = make_battle(make_mon(Species.CHARIZARD, moves=(Move.TACKLE,)),
                            make_mon(Species.BULBASAUR, moves=(Move.SPLASH,)))
        messages = [_usedmove("Charizard", "Tackle")]
        branches = _opponent_switch_in_actions(messages, state)
        assert branches == [tuple()]

    def test_known_switch_in_returns_action(self):
        from liveplay.sweep_actions import _opponent_switch_in_actions
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,))
        lillipup = make_mon(Species.LILLIPUP, moves=(Move.TACKLE,))
        state = make_battle(charizard, poochyena, team1=[poochyena, lillipup])
        messages = [_opp_switchin_msg("Lillipup")]
        branches = _opponent_switch_in_actions(messages, state)
        assert len(branches) == 1
        assert len(branches[0]) == 1
        assert branches[0][0].kind == ActionKind.SWITCH
        assert branches[0][0].switch_to_slot == 1

    def test_unknown_species_raises_simulation_error(self):
        from liveplay.sweep_actions import _opponent_switch_in_actions
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,))
        state = make_battle(charizard, poochyena)
        messages = [_opp_switchin_msg("Raticate")]
        with pytest.raises(SimulationError):
            _opponent_switch_in_actions(messages, state)

    def test_unknown_species_error_names_species(self):
        from liveplay.sweep_actions import _opponent_switch_in_actions
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,))
        state = make_battle(charizard, poochyena)
        messages = [_opp_switchin_msg("Raticate")]
        with pytest.raises(SimulationError, match="Raticate"):
            _opponent_switch_in_actions(messages, state)

    def test_player_switch_in_ignored(self):
        # Only side-1 switch-ins are returned; side-0 messages are skipped.
        from liveplay.sweep_actions import _opponent_switch_in_actions
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        pidgey = make_mon(Species.PIDGEY, moves=(Move.TACKLE,))
        state = make_battle(charizard, bulbasaur, team0=[charizard, pidgey])
        player_switchin = _mr(
            "STRINGID_SWITCHINMON",
            constant_name="STRINGID_PLAYER_SWITCHINMON",
            var_values=["Player", "Pidgey"],
        )
        branches = _opponent_switch_in_actions([player_switchin], state)
        assert branches == [tuple()]


# ---------------------------------------------------------------------------
# _validate_forced_opponent_switch (C++ binding substitution)
# ---------------------------------------------------------------------------

class TestValidateForcedOpponentSwitch:
    """_validate_forced_opponent_switch checks observed switch-in against cpp.ai_switch_info."""

    def _build_fainted_state(self, fainted_species, bench_species, player_species=Species.RATTATA):
        fainted_mon = _fainted(make_mon(fainted_species, moves=(Move.TACKLE,)))
        bench_mon = make_mon(bench_species, moves=(Move.TACKLE,))
        player_mon = make_mon(player_species, moves=(Move.TACKLE,))
        side0 = SideState(team=[player_mon], active_indices=[0])
        side1 = SideState(team=[fainted_mon, bench_mon], active_indices=[0])
        return BattleState(sides=(side0, side1))

    def test_passes_when_no_switch_in_message(self):
        # No SWITCHINMON message → nothing to validate → no raise.
        from liveplay.sweep_actions import _validate_forced_opponent_switch
        state = self._build_fainted_state(Species.ROOKIDEE, Species.NIDORAN_M)
        _validate_forced_opponent_switch([], state)  # must not raise

    def test_passes_when_matches_ai_pick(self):
        # Build a state and use cpp to find the expected slot, then confirm match → no raise.
        from liveplay.sweep_actions import _validate_forced_opponent_switch
        import json
        import nuzlocke_engine_cpp as cpp
        import liveplay.sweep_io as sweep_io
        state = self._build_fainted_state(Species.ROOKIDEE, Species.NIDORAN_M)
        result = cpp.ai_switch_info(json.dumps(sweep_io.to_jsonable(state)), 1)
        expected_slot = result["post_ko_switch"]
        if expected_slot is None:
            pytest.skip("AI has no valid post-KO candidate for this state")
        bench_mon = state.sides[1].team[expected_slot]
        display_name = bench_mon.species.name.replace("_", " ")
        messages = [_opp_switchin_msg(display_name)]
        _validate_forced_opponent_switch(messages, state)  # must not raise

    def test_raises_when_wrong_mon_sent_in(self):
        from liveplay.sweep_actions import _validate_forced_opponent_switch
        from liveplay.sweep_actions import UnexpectedOpponentActionError
        # Nidoking (high atk, fast) vs Rattata → AI should prefer Nidoking over Caterpie.
        player_mon = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
        fainted_mon = _fainted(make_mon(Species.ROOKIDEE, moves=(Move.TACKLE,)))
        bench_preferred = make_mon(Species.NIDOKING, moves=(Move.TACKLE,))
        bench_other = make_mon(Species.CATERPIE, moves=(Move.TACKLE,))
        side0 = SideState(team=[player_mon], active_indices=[0])
        side1 = SideState(team=[fainted_mon, bench_preferred, bench_other], active_indices=[0])
        state = BattleState(sides=(side0, side1))

        import json
        import nuzlocke_engine_cpp as cpp
        import liveplay.sweep_io as sweep_io
        result = cpp.ai_switch_info(json.dumps(sweep_io.to_jsonable(state)), 1)
        ai_pick = result["post_ko_switch"]
        if ai_pick is None:
            pytest.skip("AI has no valid post-KO candidate for this state")
        assert ai_pick == 1, f"Expected AI to prefer slot 1 (Nidoking), got slot {ai_pick}"

        # Observed: Caterpie sent in (slot 2) instead of AI's pick
        messages = [_opp_switchin_msg("CATERPIE")]
        with pytest.raises(UnexpectedOpponentActionError):
            _validate_forced_opponent_switch(messages, state)

    def test_skipped_in_doubles(self):
        # Doubles: strict check skipped (no raise even for wrong switch-in).
        from liveplay.sweep_actions import _validate_forced_opponent_switch
        from liveplay.state.side import FormatEnum
        player_a = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
        player_b = make_mon(Species.PIDGEY, moves=(Move.TACKLE,))
        fainted_opp = _fainted(make_mon(Species.ROOKIDEE, moves=(Move.TACKLE,)))
        bench_a = make_mon(Species.NIDOKING, moves=(Move.TACKLE,))
        bench_b = make_mon(Species.CATERPIE, moves=(Move.TACKLE,))
        side0 = SideState(team=[player_a, player_b], active_indices=[0, 1],
                          format=FormatEnum.DOUBLES)
        side1 = SideState(team=[fainted_opp, bench_a, bench_b], active_indices=[0, 1],
                          format=FormatEnum.DOUBLES)
        state = BattleState(sides=(side0, side1), format=FormatEnum.DOUBLES)
        messages = [_opp_switchin_msg("CATERPIE")]
        _validate_forced_opponent_switch(messages, state)  # must not raise

    def test_all_bench_fainted_none_path(self):
        # When cpp.ai_switch_info returns post_ko_switch=None (all bench fainted),
        # there's no observed switch-in message either → validate returns without raising.
        from liveplay.sweep_actions import _validate_forced_opponent_switch
        fainted_active = _fainted(make_mon(Species.ROOKIDEE, moves=(Move.TACKLE,)))
        # No living bench → ai_switch_info returns None for post_ko_switch.
        player_mon = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
        side0 = SideState(team=[player_mon], active_indices=[0])
        side1 = SideState(team=[fainted_active], active_indices=[0])
        state = BattleState(sides=(side0, side1))
        # No switch-in message → early return; must not raise.
        _validate_forced_opponent_switch([], state)


# ---------------------------------------------------------------------------
# _sweep_resolve_candidate_actions
# ---------------------------------------------------------------------------

class TestSweepResolveCandidateActions:
    """_sweep_resolve_candidate_actions resolves per-side candidate action lists."""

    def test_raises_post_faint_move_phase_error_when_usedmove_in_faint_state(self):
        """Fainted active + USEDMOVE in messages → PostFaintMovePhaseError (per-candidate filter)."""
        from liveplay.sweep_actions import (
            _sweep_resolve_candidate_actions, PostFaintMovePhaseError, _extract_known_actions,
        )
        state = _fainted_opp_state()
        messages = [_usedmove("MAGIKARP", "SPLASH", foe=True)]
        known = _extract_known_actions(messages, state)
        with pytest.raises(PostFaintMovePhaseError):
            _sweep_resolve_candidate_actions(state, messages, known)

    def test_post_faint_error_not_simulation_error(self):
        """PostFaintMovePhaseError is NOT a SimulationError (per-candidate vs fatal)."""
        from liveplay.sweep_actions import PostFaintMovePhaseError
        assert not issubclass(PostFaintMovePhaseError, SimulationError)

    def test_post_faint_path_returns_switch_actions(self):
        """Fainted active + switch-in message → candidates contain the SWITCH action."""
        from liveplay.sweep_actions import (
            _sweep_resolve_candidate_actions, _extract_known_actions,
        )
        player = make_mon(Species.BUDEW, moves=(Move.ABSORB,))
        fainted_opp = _fainted(make_mon(Species.MAGIKARP, moves=(Move.SPLASH,)))
        bench_opp = make_mon(Species.GYARADOS, moves=(Move.TACKLE,))
        side0 = SideState(team=[player], active_indices=[0])
        side1 = SideState(team=[fainted_opp, bench_opp], active_indices=[0])
        state = BattleState(sides=(side0, side1))
        messages = [_opp_switchin_msg("GYARADOS")]
        known = _extract_known_actions(messages, state)
        candidates0, candidates1 = _sweep_resolve_candidate_actions(state, messages, known)
        # Player side: no fainted active → None action
        assert candidates0 == [None]
        # Opponent side: SWITCH action to slot 1 (Gyarados)
        assert len(candidates1) == 1
        assert candidates1[0] is not None
        assert candidates1[0].kind == ActionKind.SWITCH
        assert candidates1[0].switch_to_slot == 1

    def test_normal_path_returns_candidates_for_both_sides(self):
        """Normal (non-faint) path returns non-empty candidate lists for both sides."""
        from liveplay.sweep_actions import (
            _sweep_resolve_candidate_actions, _extract_known_actions,
        )
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(charizard, bulbasaur)
        messages = [
            _usedmove("Charizard", "Tackle", foe=False),
            _usedmove("Bulbasaur", "Splash", foe=True),
        ]
        known = _extract_known_actions(messages, state)
        candidates0, candidates1 = _sweep_resolve_candidate_actions(state, messages, known)
        assert len(candidates0) >= 1
        assert len(candidates1) >= 1
