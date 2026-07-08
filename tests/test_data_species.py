"""Tests for the species data layer.

Verifies:
- Species enum has expected entries including Gen 1-8 and regional forms
- SpeciesData fields are correctly populated (base stats, types, gender ratio)
- Run & Bun has no EVs, so we only track base stats here (IVs applied at PokemonState level)
"""
import pytest
from liveplay.data.species import Species, SpeciesData, SPECIES_DATA
from liveplay.data.types import Type


class TestSpeciesEnum:
    def test_key_species_present(self):
        expected = {
            "BULBASAUR", "CHARIZARD", "BLASTOISE", "PIKACHU", "MEWTWO",
            "RAYQUAZA", "GARCHOMP", "HYDREIGON", "SYLVEON", "CORVIKNIGHT",
        }
        actual = {s.name for s in Species}
        missing = expected - actual
        assert not missing, f"Missing species: {missing}"

    def test_regional_forms_present(self):
        names = {s.name for s in Species}
        assert any("ALOLAN" in n or "ALOLA" in n for n in names), "No Alolan forms"
        assert any("GALARIAN" in n or "GALAR" in n for n in names), "No Galarian forms"

    def test_species_are_unique(self):
        values = [s.value for s in Species]
        assert len(values) == len(set(values))


class TestSpeciesData:
    def test_charizard_base_stats(self):
        data = SPECIES_DATA[Species.CHARIZARD]
        assert data.base_hp == 78
        assert data.base_atk == 84
        assert data.base_def == 78
        assert data.base_spa == 109
        assert data.base_spd == 85
        assert data.base_spe == 100

    def test_charizard_types(self):
        data = SPECIES_DATA[Species.CHARIZARD]
        assert Type.FIRE in data.types
        assert Type.FLYING in data.types
        assert len(data.types) == 2

    def test_gengar_types(self):
        data = SPECIES_DATA[Species.GENGAR]
        assert Type.GHOST in data.types
        assert Type.POISON in data.types

    def test_single_type_species(self):
        data = SPECIES_DATA[Species.SNORLAX]
        assert Type.NORMAL in data.types
        assert len(data.types) == 1

    def test_base_stats_are_positive(self):
        for species, data in SPECIES_DATA.items():
            for stat in (data.base_hp, data.base_atk, data.base_def,
                         data.base_spa, data.base_spd, data.base_spe):
                assert stat > 0, f"{species.name} has non-positive base stat"

    def test_all_species_have_species_data(self):
        for species in Species:
            assert species in SPECIES_DATA, f"{species.name} missing from SPECIES_DATA"

    def test_gender_ratio_bulbasaur(self):
        data = SPECIES_DATA[Species.BULBASAUR]
        assert data.male_ratio is not None
        assert abs(data.male_ratio - 0.875) < 0.001

    def test_gender_ratio_gardevoir(self):
        data = SPECIES_DATA[Species.GARDEVOIR]
        assert data.male_ratio is not None

    def test_genderless_species(self):
        data = SPECIES_DATA[Species.METAGROSS]
        assert data.male_ratio is None

    def test_base_stat_types_are_int(self):
        data = SPECIES_DATA[Species.CHARIZARD]
        assert isinstance(data.base_hp, int)
        assert isinstance(data.base_spe, int)
