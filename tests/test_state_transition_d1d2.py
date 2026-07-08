# Tests for D1 (RosterAmbiguityError) and D2 (reference_kind) fixes in state_transition.py.
import pytest

from liveplay.state_transition import (
    _fuzzy_find_side,
    _fuzzy_find_team_slot,
    _fuzzy_find_team_slots,
    SideHintContradictionError,
    SideHintMissingError,
    RosterAmbiguityError,
    ActorNotActiveError,
)
from liveplay.data.species import Species
from liveplay.data.moves import Move
from liveplay.data.natures import Nature
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.status import Status
from liveplay.state.pokemon import PokemonState, GenderEnum
from liveplay.state.side import SideState
from liveplay.state.battle import BattleState


def _bare_mon(species: Species, fainted: bool = False) -> PokemonState:
    return PokemonState(
        species=species,
        nature=Nature.HARDY,
        ivs=(31,) * 6,
        gender=GenderEnum.MALE,
        ability=Ability.NONE,
        item=Item.NONE,
        move_ids=(Move.SPLASH, Move.NONE, Move.NONE, Move.NONE),
        move_pp=(40, 0, 0, 0),
        status=Status.NONE,
        fainted=fainted,
    )


def _make_state(team0: list, team1: list, active0=0, active1=0) -> BattleState:
    return BattleState(sides=(
        SideState(team=team0, active_indices=[active0]),
        SideState(team=team1, active_indices=[active1]),
    ))


# ---------------------------------------------------------------------------
# D1 — _fuzzy_find_team_slot ambiguity on duplicate species
# ---------------------------------------------------------------------------

class TestFuzzyFindTeamSlotD1:
    """_fuzzy_find_team_slot reduces duplicate-species matches by switch-eligibility and
    only raises RosterAmbiguityError when the ambiguity genuinely cannot be reduced."""

    def test_single_match_returns_slot(self):
        # Exactly one slot matches — normal path, unchanged.
        tentacruel = _bare_mon(Species.TENTACRUEL)
        pikachu = _bare_mon(Species.PIKACHU)
        state = _make_state([pikachu], [tentacruel, pikachu])
        slot = _fuzzy_find_team_slot("TENTACRUEL", 1, state)
        assert slot == 0

    def test_no_match_returns_none(self):
        # No slot matches — returns None, caller handles it.
        pikachu = _bare_mon(Species.PIKACHU)
        state = _make_state([pikachu], [pikachu])
        slot = _fuzzy_find_team_slot("CHARIZARD", 1, state)
        assert slot is None

    def test_duplicate_both_benched_alive_raises(self):
        # Two Tentacruel both benched and alive — genuinely ambiguous, fail loud.
        pikachu = _bare_mon(Species.PIKACHU)
        tentacruel_a = _bare_mon(Species.TENTACRUEL)
        tentacruel_b = _bare_mon(Species.TENTACRUEL)
        state = _make_state([pikachu], [pikachu, tentacruel_a, tentacruel_b], active1=0)
        with pytest.raises(RosterAmbiguityError):
            _fuzzy_find_team_slot("TENTACRUEL", 1, state)

    def test_ambiguity_error_names_species_side_and_slots(self):
        # The error message must mention the species name, side, and matching slot indices.
        pikachu = _bare_mon(Species.PIKACHU)
        tentacruel_a = _bare_mon(Species.TENTACRUEL)
        tentacruel_b = _bare_mon(Species.TENTACRUEL)
        state = _make_state([pikachu], [pikachu, tentacruel_a, tentacruel_b], active1=0)
        with pytest.raises(RosterAmbiguityError, match="TENTACRUEL"):
            _fuzzy_find_team_slot("TENTACRUEL", 1, state)

    def test_duplicate_one_active_resolves_to_benched(self):
        # Two Magikarp, slot 0 active — the switch-in must name the benched slot 1.
        magikarp_a = _bare_mon(Species.MAGIKARP)
        magikarp_b = _bare_mon(Species.MAGIKARP)
        pikachu = _bare_mon(Species.PIKACHU)
        state = _make_state([pikachu], [magikarp_a, magikarp_b], active1=0)
        assert _fuzzy_find_team_slot("MAGIKARP", 1, state) == 1

    def test_duplicate_one_fainted_resolves_to_alive(self):
        # Two Magikarp, slot 0 fainted (just KO'd) — the replacement is benched slot 1.
        magikarp_dead = _bare_mon(Species.MAGIKARP, fainted=True)
        magikarp_alive = _bare_mon(Species.MAGIKARP)
        pikachu = _bare_mon(Species.PIKACHU)
        # active1 points at the fainted slot (state mid-replacement, before the swap).
        state = _make_state([pikachu], [magikarp_dead, magikarp_alive], active1=0)
        assert _fuzzy_find_team_slot("MAGIKARP", 1, state) == 1

    def test_single_match_among_different_species(self):
        # Two different species, only one matches — no ambiguity.
        tentacruel = _bare_mon(Species.TENTACRUEL)
        pikachu = _bare_mon(Species.PIKACHU)
        state = _make_state([pikachu], [tentacruel, pikachu])
        slot = _fuzzy_find_team_slot("PIKACHU", 1, state)
        assert slot == 1


class TestFuzzyFindTeamSlotsReducer:
    """_fuzzy_find_team_slots returns the candidate slot list after eligibility reduction."""

    def test_no_match_returns_empty(self):
        pikachu = _bare_mon(Species.PIKACHU)
        state = _make_state([pikachu], [pikachu])
        assert _fuzzy_find_team_slots("CHARIZARD", 1, state) == []

    def test_single_match_returns_singleton(self):
        tentacruel = _bare_mon(Species.TENTACRUEL)
        pikachu = _bare_mon(Species.PIKACHU)
        state = _make_state([pikachu], [tentacruel, pikachu])
        assert _fuzzy_find_team_slots("TENTACRUEL", 1, state) == [0]

    def test_duplicate_active_slot_excluded(self):
        magikarp_a = _bare_mon(Species.MAGIKARP)
        magikarp_b = _bare_mon(Species.MAGIKARP)
        pikachu = _bare_mon(Species.PIKACHU)
        state = _make_state([pikachu], [magikarp_a, magikarp_b], active1=0)
        assert _fuzzy_find_team_slots("MAGIKARP", 1, state) == [1]

    def test_duplicate_fainted_slot_excluded(self):
        magikarp_dead = _bare_mon(Species.MAGIKARP, fainted=True)
        magikarp_alive = _bare_mon(Species.MAGIKARP)
        pikachu = _bare_mon(Species.PIKACHU)
        state = _make_state([pikachu], [magikarp_dead, magikarp_alive], active1=0)
        assert _fuzzy_find_team_slots("MAGIKARP", 1, state) == [1]

    def test_duplicate_both_eligible_returns_both(self):
        pikachu = _bare_mon(Species.PIKACHU)
        magikarp_a = _bare_mon(Species.MAGIKARP)
        magikarp_b = _bare_mon(Species.MAGIKARP)
        state = _make_state([pikachu], [pikachu, magikarp_a, magikarp_b], active1=0)
        assert _fuzzy_find_team_slots("MAGIKARP", 1, state) == [1, 2]

    def test_all_matches_ineligible_falls_back_to_full_set(self):
        # One active, one fainted — neither is switch-eligible; fall back to both so the
        # caller fails loud rather than silently returning an empty list.
        magikarp_active = _bare_mon(Species.MAGIKARP)
        magikarp_dead = _bare_mon(Species.MAGIKARP, fainted=True)
        pikachu = _bare_mon(Species.PIKACHU)
        # Both matching slots ineligible: slot 0 active, slot 1 fainted.
        state = _make_state([pikachu], [magikarp_active, magikarp_dead], active1=0)
        assert _fuzzy_find_team_slots("MAGIKARP", 1, state) == [0, 1]


# ---------------------------------------------------------------------------
# D2 — _fuzzy_find_side reference_kind parameter
# ---------------------------------------------------------------------------

class TestFuzzyFindSideD2:
    """_fuzzy_find_side raises ActorNotActiveError for actor references that match neither active."""

    def _state_with_benched(self) -> BattleState:
        """Side 0: Pikachu active. Side 1: Bulbasaur active, Squirtle benched."""
        pikachu = _bare_mon(Species.PIKACHU)
        bulbasaur = _bare_mon(Species.BULBASAUR)
        squirtle = _bare_mon(Species.SQUIRTLE)
        return _make_state([pikachu], [bulbasaur, squirtle], active0=0, active1=0)

    def test_actor_matches_active_returns_side(self):
        state = self._state_with_benched()
        result = _fuzzy_find_side("BULBASAUR", state, side_hint=1, reference_kind="actor")
        assert result == 1

    def test_actor_neither_active_raises(self):
        # "SQUIRTLE" matches neither active (it's benched on side 1) — actor must be active.
        state = self._state_with_benched()
        with pytest.raises(ActorNotActiveError):
            _fuzzy_find_side("SQUIRTLE", state, side_hint=1, reference_kind="actor")

    def test_benched_neither_active_trusts_hint(self):
        # "SQUIRTLE" matches neither active but reference_kind="benched" → trust the hint.
        state = self._state_with_benched()
        result = _fuzzy_find_side("SQUIRTLE", state, side_hint=1, reference_kind="benched")
        assert result == 1

    def test_default_kind_benched_neither_active_trusts_hint(self):
        # Default (reference_kind not specified) behaves like "benched" — permissive.
        state = self._state_with_benched()
        result = _fuzzy_find_side("SQUIRTLE", state, side_hint=1)
        assert result == 1

    def test_actor_contradiction_still_raises_contradiction_error(self):
        # Hint says side 0 but BULBASAUR is side 1's active — contradiction error, not actor error.
        state = self._state_with_benched()
        with pytest.raises(SideHintContradictionError):
            _fuzzy_find_side("BULBASAUR", state, side_hint=0, reference_kind="actor")

    def test_actor_mirror_match_trusts_hint(self):
        # Both actives share a species — mirror match, hint breaks the tie. No error.
        pikachu_a = _bare_mon(Species.PIKACHU)
        pikachu_b = _bare_mon(Species.PIKACHU)
        state = _make_state([pikachu_a], [pikachu_b])
        assert _fuzzy_find_side("PIKACHU", state, side_hint=0, reference_kind="actor") == 0
        assert _fuzzy_find_side("PIKACHU", state, side_hint=1, reference_kind="actor") == 1

    def test_missing_hint_still_raises_missing_error(self):
        state = self._state_with_benched()
        with pytest.raises(SideHintMissingError):
            _fuzzy_find_side("BULBASAUR", state, reference_kind="actor")

    def test_actor_recognizable_benched_raises(self):
        # "SQUIRTLE" is recognizable (matches a benched slot) but neither active → genuine desync.
        state = self._state_with_benched()
        with pytest.raises(ActorNotActiveError):
            _fuzzy_find_side("SQUIRTLE", state, side_hint=1, reference_kind="actor")

    def test_actor_ocr_garble_trusts_hint(self):
        # "ZZZZZ" matches no species anywhere — pure OCR garble, not desync; trust the hint.
        state = self._state_with_benched()
        result = _fuzzy_find_side("ZZZZZ", state, side_hint=0, reference_kind="actor")
        assert result == 0
