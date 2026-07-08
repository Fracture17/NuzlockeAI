# Tests for src/state_transition.py — covers the side/Pokémon identification helpers.
import pytest

from liveplay.state_transition import (
    _side_from_constant_name,
    _fuzzy_find_side,
    SideHintMissingError,
    SideHintContradictionError,
)
from liveplay.data.species import Species
from tests.state_builders import make_mon, make_battle


class TestFuzzyFindSide:
    """_fuzzy_find_side resolves a named mon to its battle side.

    The acting side is authoritative from the Foe prefix (side_hint=1 opponent, 0 player)
    and REQUIRED: every actor-naming message must carry one. A missing hint is a hard
    error; the name is used only as a loud consistency check against the battle state.
    """

    def test_side_hint_is_authoritative(self):
        # The hint determines the side; the named species need only be consistent with it.
        p0 = make_mon(Species.PIKACHU)
        p1 = make_mon(Species.BULBASAUR)
        state = make_battle(p0, p1)
        assert _fuzzy_find_side("PIKACHU", state, side_hint=0) == 0
        assert _fuzzy_find_side("BULBASAUR", state, side_hint=1) == 1

    def test_side_hint_breaks_mirror_tie(self):
        # Both actives are PIKACHU — only the side_hint (from the Foe prefix) disambiguates.
        p0 = make_mon(Species.PIKACHU)
        p1 = make_mon(Species.PIKACHU)
        state = make_battle(p0, p1)
        assert _fuzzy_find_side("PIKACHU", state, side_hint=1) == 1
        assert _fuzzy_find_side("PIKACHU", state, side_hint=0) == 0

    def test_benched_reference_trusts_hint(self):
        # Name matches neither active (it's a benched mon) → no contradiction → trust hint.
        charizard = make_mon(Species.CHARIZARD)
        bulbasaur = make_mon(Species.BULBASAUR)
        bench_squirtle = make_mon(Species.SQUIRTLE)
        state = make_battle(charizard, bulbasaur,
                            team0=[charizard], team1=[bulbasaur, bench_squirtle])
        assert _fuzzy_find_side("SQUIRTLE", state, side_hint=1) == 1

    def test_missing_hint_raises(self):
        charizard = make_mon(Species.CHARIZARD)
        bulbasaur = make_mon(Species.BULBASAUR)
        state = make_battle(charizard, bulbasaur)
        with pytest.raises(SideHintMissingError):
            _fuzzy_find_side("CHARIZARD", state)

    def test_contradicting_hint_raises(self):
        # hint says side 0 but the name matches side 1's active (and not side 0's) → loud error.
        charizard = make_mon(Species.CHARIZARD)
        bulbasaur = make_mon(Species.BULBASAUR)
        state = make_battle(charizard, bulbasaur)
        with pytest.raises(SideHintContradictionError):
            _fuzzy_find_side("BULBASAUR", state, side_hint=0)

    def test_unknown_name_with_hint_trusts_hint(self):
        # An unresolvable name matches neither active → no contradiction → the hint stands.
        charizard = make_mon(Species.CHARIZARD)
        bulbasaur = make_mon(Species.BULBASAUR)
        state = make_battle(charizard, bulbasaur)
        assert _fuzzy_find_side("MISSINGNO", state, side_hint=1) == 1

    def test_form_matches_emulator_base_name(self):
        # The emulator displays Galarian Weezing as "WEEZING"; the reverse-name
        # override lets the form match its base name so the consistency check passes.
        pikachu = make_mon(Species.PIKACHU)
        weezing_g = make_mon(Species.WEEZING_GALAR)
        state = make_battle(pikachu, weezing_g)
        assert _fuzzy_find_side("WEEZING", state, side_hint=1) == 1


class TestSideFromConstantName:
    def test_trainer1_withdrew(self):
        assert _side_from_constant_name("sText_Trainer1WithdrewPkmn") == 1

    def test_trainer1_sent_out(self):
        assert _side_from_constant_name("sText_Trainer1SentOutPkmn") == 1

    def test_trainer1_sent_out_2(self):
        assert _side_from_constant_name("sText_Trainer1SentOutPkmn2") == 1

    def test_player_come_back(self):
        assert _side_from_constant_name("sText_PkmnComeBack") == 0

    def test_player_go_pkmn(self):
        assert _side_from_constant_name("sText_GoPkmn2") == 0

    def test_unknown_defaults_to_player(self):
        assert _side_from_constant_name("sText_SomeUnknownConstant") == 0
