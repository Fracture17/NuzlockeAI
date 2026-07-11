# Port of OLD tests/test_unreproducible_move_and_unknown_switch.py.
# C1 (UnreproducibleObservedMoveError) and C2 (SimulationError on unknown switch-in).
# C1: observed USEDMOVE not in moveset, or not in enumerate_legal_actions → filter candidate.
# C2: switch-in naming unknown species in _extract_known_actions / _opponent_switch_in_actions
#     → hard raise.
#
# _opponent_switch_in_actions unknown-species tests are PARTIALLY covered in
# test_sweep_analysis_helpers.py (unknown_species_raises, unknown_species_error_names_species).
# The full _extract_known_actions and run_candidate_sweep paths are NOT covered → ported here.
from __future__ import annotations

import pytest

from liveplay.battle_types import MatchResult
from liveplay.candidate import Candidate
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status
from liveplay.actions import ActionKind
from liveplay.engine_select import SimulationError
from liveplay.sweep_actions import (
    UnreproducibleObservedMoveError,
    _extract_known_actions,
    _opponent_switch_in_actions,
)
from liveplay.state.pokemon import Volatile
from liveplay.sweep_run import run_candidate_sweep
from tests.state_builders import make_battle, make_mon, odelta


# ---------------------------------------------------------------------------
# Shared MatchResult builders
# ---------------------------------------------------------------------------

def _usedmove_msg(attacker_name: str, move_name: str, *, side_hint: int = 0) -> MatchResult:
    return MatchResult(
        string_id="STRINGID_USEDMOVE",
        id_value=1,
        constant_name="sText_AttackerUsedMove",
        var_values=[attacker_name, move_name],
        score=0,
        matched_text=f"{attacker_name} used {move_name}!",
        slot_labels=[],
        side_hint=side_hint,
    )


def _opp_switch_in(species_name: str) -> MatchResult:
    return MatchResult(
        string_id="STRINGID_SWITCHINMON",
        id_value=3,
        constant_name="sText_Trainer1SentOutPkmn2",
        var_values=["Youngster", "Calvin", species_name],
        score=0,
        matched_text=f"Youngster Calvin sent out {species_name}!",
        slot_labels=[],
        side_hint=1,
    )


# ---------------------------------------------------------------------------
# C1a: observed move not in moveset → filter candidate (sweep → SimulationError)
# ---------------------------------------------------------------------------

class TestC1MoveNotInMoveset:
    """Observed USEDMOVE names a move not present in the mon's modeled moveset."""

    def test_extract_known_actions_raises_unreproducible(self):
        """_extract_known_actions raises UnreproducibleObservedMoveError directly."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(charizard, bulbasaur)

        messages = [_usedmove_msg("Charizard", "Flamethrower")]
        with pytest.raises(UnreproducibleObservedMoveError):
            _extract_known_actions(messages, state)

    def test_sweep_filters_all_candidates_to_simulation_error(self):
        """run_candidate_sweep filters every candidate and raises the no-candidate SimulationError."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(charizard, bulbasaur)

        messages = [_usedmove_msg("Charizard", "Flamethrower")]
        with pytest.raises(SimulationError):
            run_candidate_sweep(
                messages=messages,
                hp_deltas=[odelta(bulbasaur.species, (48, 48), max_hp=bulbasaur.max_hp)],
                initial_candidates=[Candidate(state=state)],
            )

    def test_error_message_names_species_and_move(self):
        """Exception message identifies the species and OCR'd move name for diagnostics."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(charizard, bulbasaur)

        messages = [_usedmove_msg("Charizard", "Flamethrower")]
        with pytest.raises(UnreproducibleObservedMoveError, match="Flamethrower"):
            _extract_known_actions(messages, state)


# ---------------------------------------------------------------------------
# C1b: observed move resolves but is not in enumerate_legal_actions → filter candidate
# ---------------------------------------------------------------------------

class TestC1MoveNotLegal:
    """Observed USEDMOVE resolves in moveset but is illegal in the candidate state (Taunt)."""

    def test_taunted_status_move_not_legal_raises_unreproducible(self):
        """A Taunted mon can't use a STATUS move. Observing it must raise UnreproducibleObservedMoveError."""
        pikachu = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        pikachu = pikachu._replace(volatiles=pikachu.volatiles | Volatile.TAUNT_ACTIVE)
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.TACKLE,))
        state = make_battle(pikachu, bulbasaur)

        messages = [_usedmove_msg("Pikachu", "Splash")]
        with pytest.raises(UnreproducibleObservedMoveError):
            _extract_known_actions(messages, state)

    def test_taunted_sweep_filters_to_simulation_error(self):
        """Full sweep with Taunted mon using STATUS move → all filtered → SimulationError."""
        pikachu = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        pikachu = pikachu._replace(volatiles=pikachu.volatiles | Volatile.TAUNT_ACTIVE)
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.TACKLE,))
        state = make_battle(pikachu, bulbasaur)

        messages = [_usedmove_msg("Pikachu", "Splash")]
        with pytest.raises(SimulationError):
            run_candidate_sweep(
                messages=messages,
                hp_deltas=[odelta(bulbasaur.species, (48, 48), max_hp=bulbasaur.max_hp)],
                initial_candidates=[Candidate(state=state)],
            )

    def test_error_message_identifies_not_legal(self):
        """Exception message includes 'not-legal desync' to distinguish from moveset case."""
        pikachu = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        pikachu = pikachu._replace(volatiles=pikachu.volatiles | Volatile.TAUNT_ACTIVE)
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.TACKLE,))
        state = make_battle(pikachu, bulbasaur)

        messages = [_usedmove_msg("Pikachu", "Splash")]
        with pytest.raises(UnreproducibleObservedMoveError, match="not-legal"):
            _extract_known_actions(messages, state)


# ---------------------------------------------------------------------------
# C2: switch-in naming unknown species → hard raise SimulationError
# ---------------------------------------------------------------------------

class TestC2UnknownSwitchIn:
    """Switch-in messages naming a species not on the team raise SimulationError (hard raise)."""

    def test_extract_known_actions_unknown_switch_in_raises(self):
        """_extract_known_actions raises SimulationError on unrecognized switch-in species."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,))
        state = make_battle(charizard, poochyena)

        messages = [_opp_switch_in("Raticate")]
        with pytest.raises(SimulationError):
            _extract_known_actions(messages, state)

    def test_extract_known_actions_error_names_species(self):
        """SimulationError message names the unrecognized species for diagnostics."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,))
        state = make_battle(charizard, poochyena)

        messages = [_opp_switch_in("Raticate")]
        with pytest.raises(SimulationError, match="Raticate"):
            _extract_known_actions(messages, state)

    def test_opponent_switch_in_actions_unknown_species_raises(self):
        """_opponent_switch_in_actions raises SimulationError on unrecognized switch-in species."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,))
        state = make_battle(charizard, poochyena)

        messages = [_opp_switch_in("Raticate")]
        with pytest.raises(SimulationError):
            _opponent_switch_in_actions(messages, state)

    def test_opponent_switch_in_actions_error_names_species(self):
        """SimulationError from _opponent_switch_in_actions names the unrecognized species."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,))
        state = make_battle(charizard, poochyena)

        messages = [_opp_switch_in("Raticate")]
        with pytest.raises(SimulationError, match="Raticate"):
            _opponent_switch_in_actions(messages, state)

    def test_known_species_switch_in_does_not_raise(self):
        """A switch-in to a species actually on the team must NOT raise — regression guard."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,))
        lillipup = make_mon(Species.LILLIPUP, moves=(Move.TACKLE,))
        state = make_battle(charizard, poochyena, team1=[poochyena, lillipup])

        messages = [_opp_switch_in("Lillipup")]
        known = _extract_known_actions(messages, state)
        assert known[1][0] is not None
        assert known[1][0].kind == ActionKind.SWITCH
        assert known[1][0].switch_to_slot == 1
