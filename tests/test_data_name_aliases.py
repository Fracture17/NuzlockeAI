# Tests for src/data/name_aliases.py — override maps + emulator-name helper.
from liveplay.data.name_aliases import (
    SPECIES_ALIASES,
    MOVE_ALIASES,
    ITEM_ALIASES,
    ABILITY_ALIASES,
    ENUM_ALIASES,
    SPECIES_TO_EMULATOR_NAME,
    emulator_species_name,
)
from liveplay.data.species import Species
from liveplay.data.moves import Move
from liveplay.data.items import Item
from liveplay.data.abilities import Ability


class TestAliasMapsAreWellFormed:
    def test_species_alias_values_are_species(self):
        assert all(isinstance(v, Species) for v in SPECIES_ALIASES.values())

    def test_move_alias_values_are_moves(self):
        assert all(isinstance(v, Move) for v in MOVE_ALIASES.values())

    def test_item_alias_values_are_items(self):
        assert all(isinstance(v, Item) for v in ITEM_ALIASES.values())

    def test_ability_alias_values_are_abilities(self):
        assert all(isinstance(v, Ability) for v in ABILITY_ALIASES.values())

    def test_dispatch_table_wires_each_class(self):
        assert ENUM_ALIASES[Species] is SPECIES_ALIASES
        assert ENUM_ALIASES[Move] is MOVE_ALIASES
        assert ENUM_ALIASES[Item] is ITEM_ALIASES
        assert ENUM_ALIASES[Ability] is ABILITY_ALIASES


class TestSoftCaseAliases:
    def test_vice_grip(self):
        assert MOVE_ALIASES["Vice Grip"] == Move.VISE_GRIP

    def test_natures_madness(self):
        assert MOVE_ALIASES["Natures Madness"] == Move.NATURE_S_MADNESS

    def test_kings_shield(self):
        assert MOVE_ALIASES["Kings Shield"] == Move.KING_S_SHIELD

    def test_kings_rock(self):
        assert ITEM_ALIASES["Kings Rock"] == Item.KING_S_ROCK

    def test_as_one_glastrier(self):
        assert ABILITY_ALIASES["As One (Glastrier)"] == Ability.AS_ONE_GLASTRIER


class TestSpeciesAliasSpotChecks:
    def test_galarian_form(self):
        assert SPECIES_ALIASES["Weezing_Galarian"] == Species.WEEZING_GALAR

    def test_alolan_form(self):
        assert SPECIES_ALIASES["Raichu_Alolan"] == Species.RAICHU_ALOLA

    def test_hisuian_form(self):
        assert SPECIES_ALIASES["Typhlosion_Hisuian"] == Species.TYPHLOSION_HISUI

    def test_apostrophe_base(self):
        assert SPECIES_ALIASES["Farfetchd"] == Species.FARFETCH_U2019D

    def test_female_form(self):
        assert SPECIES_ALIASES["Meowstic_Female"] == Species.MEOWSTIC_F

    def test_battle_bond(self):
        assert SPECIES_ALIASES["Greninja_Battle_Bond"] == Species.GRENINJA_BOND

    def test_pau_form(self):
        assert SPECIES_ALIASES["Oricorio_Pau"] == Species.ORICORIO_PA_U

    def test_count_is_47(self):
        # Sanity: the validation report listed 54 unresolved species; 7 cosmetic
        # forms (Furfrou/Florges/Alcremie/Vivillon variants) are intentionally
        # skipped, leaving 47 confident mappings.
        assert len(SPECIES_ALIASES) == 47

    def test_skipped_forms_absent(self):
        for skipped in (
            "Furfrou_Heart_Trim",
            "Florges_Orange_Flower",
            "Alcremie_Caramel_Swirl",
            "Vivillon_Elegant",
            "Vivillon_Modern",
            "Vivillon_Sun",
            "Vivillon_Garden",
        ):
            assert skipped not in SPECIES_ALIASES


class TestEmulatorSpeciesName:
    def test_form_returns_base_name(self):
        assert emulator_species_name(Species.WEEZING_GALAR) == Species.WEEZING.name

    def test_non_form_returns_member_name(self):
        # Species without an override fall back to the member name (current behavior).
        assert emulator_species_name(Species.PIKACHU) == Species.PIKACHU.name

    def test_override_values_match_a_base_member_name(self):
        member_names = set(Species.__members__)
        assert all(v in member_names for v in SPECIES_TO_EMULATOR_NAME.values())

    def test_every_overridden_form_is_an_aliased_species(self):
        # Reverse-map keys should all be species we actually resolve from pkl data.
        resolved = set(SPECIES_ALIASES.values())
        assert all(form in resolved for form in SPECIES_TO_EMULATOR_NAME)
