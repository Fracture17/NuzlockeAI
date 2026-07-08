"""Tests for the nature data layer.

Verifies:
- All 25 natures are present
- Boosted/lowered stat multipliers are correct (1.1x / 0.9x)
- Neutral natures return 1.0x for all stats
"""
import pytest
from liveplay.data.natures import Nature, NATURE_DATA, Stat


class TestNatureEnum:
    def test_all_25_natures_present(self):
        expected = {
            "HARDY", "LONELY", "BRAVE", "ADAMANT", "NAUGHTY",
            "BOLD", "DOCILE", "RELAXED", "IMPISH", "LAX",
            "TIMID", "HASTY", "SERIOUS", "JOLLY", "NAIVE",
            "MODEST", "MILD", "QUIET", "BASHFUL", "RASH",
            "CALM", "GENTLE", "SASSY", "CAREFUL", "QUIRKY",
        }
        actual = {n.name for n in Nature}
        assert expected == actual

    def test_natures_are_unique(self):
        values = [n.value for n in Nature]
        assert len(values) == len(set(values))


class TestNatureData:
    def test_adamant_boosts_atk(self):
        data = NATURE_DATA[Nature.ADAMANT]
        assert data.boosted == Stat.ATK

    def test_adamant_lowers_spa(self):
        data = NATURE_DATA[Nature.ADAMANT]
        assert data.lowered == Stat.SPA

    def test_timid_boosts_spe(self):
        data = NATURE_DATA[Nature.TIMID]
        assert data.boosted == Stat.SPE

    def test_timid_lowers_atk(self):
        data = NATURE_DATA[Nature.TIMID]
        assert data.lowered == Stat.ATK

    def test_modest_boosts_spa(self):
        data = NATURE_DATA[Nature.MODEST]
        assert data.boosted == Stat.SPA
        assert data.lowered == Stat.ATK

    def test_bold_boosts_def(self):
        data = NATURE_DATA[Nature.BOLD]
        assert data.boosted == Stat.DEF
        assert data.lowered == Stat.ATK

    def test_calm_boosts_spd(self):
        data = NATURE_DATA[Nature.CALM]
        assert data.boosted == Stat.SPD
        assert data.lowered == Stat.ATK

    def test_neutral_natures(self):
        neutral = {Nature.HARDY, Nature.DOCILE, Nature.SERIOUS, Nature.BASHFUL, Nature.QUIRKY}
        for nature in neutral:
            data = NATURE_DATA[nature]
            assert data.boosted is None and data.lowered is None, \
                f"{nature.name} should be neutral"

    def test_boost_multiplier(self):
        data = NATURE_DATA[Nature.ADAMANT]
        assert data.boost_multiplier == 1.1

    def test_lower_multiplier(self):
        data = NATURE_DATA[Nature.ADAMANT]
        assert data.lower_multiplier == 0.9

    def test_neutral_multiplier(self):
        data = NATURE_DATA[Nature.HARDY]
        assert data.boost_multiplier == 1.0
        assert data.lower_multiplier == 1.0

    def test_all_natures_have_data(self):
        for nature in Nature:
            assert nature in NATURE_DATA, f"{nature.name} missing from NATURE_DATA"

    def test_stat_enum_has_six_stats(self):
        expected = {"HP", "ATK", "DEF", "SPA", "SPD", "SPE"}
        actual = {s.name for s in Stat}
        assert expected.issubset(actual)
