"""Tests for the type chart data layer.

Verifies:
- All 18 standard types are present in the Type enum
- Type effectiveness values are correct (0.0, 0.5, 1.0, 2.0)
- Key matchups used in RnB battles are correct
"""
import pytest
from liveplay.data.types import Type, type_effectiveness


class TestTypeEnum:
    def test_all_standard_types_present(self):
        expected = {
            "NORMAL", "FIRE", "WATER", "ELECTRIC", "GRASS", "ICE",
            "FIGHTING", "POISON", "GROUND", "FLYING", "PSYCHIC", "BUG",
            "ROCK", "GHOST", "DRAGON", "DARK", "STEEL", "FAIRY",
        }
        actual = {t.name for t in Type}
        assert expected.issubset(actual)

    def test_types_are_unique(self):
        values = [t.value for t in Type]
        assert len(values) == len(set(values))


class TestTypeEffectiveness:
    # Super-effective (2.0x)
    def test_fire_vs_grass(self):
        assert type_effectiveness(Type.FIRE, Type.GRASS) == 2.0

    def test_water_vs_fire(self):
        assert type_effectiveness(Type.WATER, Type.FIRE) == 2.0

    def test_electric_vs_water(self):
        assert type_effectiveness(Type.ELECTRIC, Type.WATER) == 2.0

    def test_fighting_vs_normal(self):
        assert type_effectiveness(Type.FIGHTING, Type.NORMAL) == 2.0

    def test_ice_vs_dragon(self):
        assert type_effectiveness(Type.ICE, Type.DRAGON) == 2.0

    def test_fairy_vs_dragon(self):
        assert type_effectiveness(Type.FAIRY, Type.DRAGON) == 2.0

    def test_dark_vs_psychic(self):
        assert type_effectiveness(Type.DARK, Type.PSYCHIC) == 2.0

    def test_rock_vs_flying(self):
        assert type_effectiveness(Type.ROCK, Type.FLYING) == 2.0

    # Not very effective (0.5x)
    def test_fire_vs_rock(self):
        assert type_effectiveness(Type.FIRE, Type.ROCK) == 0.5

    def test_normal_vs_steel(self):
        assert type_effectiveness(Type.NORMAL, Type.STEEL) == 0.5

    def test_fighting_vs_psychic(self):
        assert type_effectiveness(Type.FIGHTING, Type.PSYCHIC) == 0.5

    def test_bug_vs_fighting(self):
        assert type_effectiveness(Type.BUG, Type.FIGHTING) == 0.5

    # Immune (0.0x)
    def test_normal_vs_ghost(self):
        assert type_effectiveness(Type.NORMAL, Type.GHOST) == 0.0

    def test_ghost_vs_normal(self):
        assert type_effectiveness(Type.GHOST, Type.NORMAL) == 0.0

    def test_electric_vs_ground(self):
        assert type_effectiveness(Type.ELECTRIC, Type.GROUND) == 0.0

    def test_ground_vs_flying(self):
        assert type_effectiveness(Type.GROUND, Type.FLYING) == 0.0

    def test_poison_vs_steel(self):
        assert type_effectiveness(Type.POISON, Type.STEEL) == 0.0

    def test_dragon_vs_fairy(self):
        assert type_effectiveness(Type.DRAGON, Type.FAIRY) == 0.0

    def test_psychic_vs_dark(self):
        assert type_effectiveness(Type.PSYCHIC, Type.DARK) == 0.0

    def test_fighting_vs_ghost(self):
        assert type_effectiveness(Type.FIGHTING, Type.GHOST) == 0.0

    # Neutral (1.0x)
    def test_normal_vs_normal(self):
        assert type_effectiveness(Type.NORMAL, Type.NORMAL) == 1.0

    def test_water_vs_water(self):
        assert type_effectiveness(Type.WATER, Type.WATER) == 0.5

    def test_fire_vs_normal(self):
        assert type_effectiveness(Type.FIRE, Type.NORMAL) == 1.0

    def test_return_type_is_float(self):
        assert isinstance(type_effectiveness(Type.FIRE, Type.GRASS), float)

    def test_dual_type_effectiveness_not_handled_here(self):
        """type_effectiveness takes single types; dual-type handling is in engine."""
        result = type_effectiveness(Type.WATER, Type.FIRE)
        assert result == 2.0
