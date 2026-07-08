"""Tests for the ability and item enum data layers.

Verifies:
- Key abilities and items are present in their enums
- Enums are unique
- ABILITY_DATA and ITEM_DATA dicts are complete

Note: Effect logic (callbacks) is tested at the engine layer.
"""
import pytest
from liveplay.data.abilities import Ability, ABILITY_DATA
from liveplay.data.items import Item, ITEM_DATA


class TestAbilityEnum:
    def test_key_abilities_present(self):
        expected = {
            "OVERGROW", "BLAZE", "TORRENT", "INTIMIDATE", "LEVITATE",
            "WONDER_GUARD", "DROUGHT", "DRIZZLE", "SAND_STREAM", "SNOW_WARNING",
            "ADAPTABILITY", "MULTISCALE", "THICK_FAT", "REGENERATOR",
            "SPEED_BOOST", "PROTEAN", "DISGUISE", "GALE_WINGS", "MAGMA_ARMOR",
            "MOODY", "SYNCHRONIZE", "CHLOROPHYLL", "SWIFT_SWIM",
        }
        actual = {a.name for a in Ability}
        missing = expected - actual
        assert not missing, f"Missing abilities: {missing}"

    def test_abilities_are_unique(self):
        values = [a.value for a in Ability]
        assert len(values) == len(set(values))

    def test_all_abilities_have_data(self):
        for ability in Ability:
            assert ability in ABILITY_DATA, f"{ability.name} missing from ABILITY_DATA"


class TestItemEnum:
    def test_key_items_present(self):
        expected = {
            "LEFTOVERS", "CHOICE_BAND", "CHOICE_SCARF", "CHOICE_SPECS",
            "LIFE_ORB", "FOCUS_SASH", "ROCKY_HELMET", "ASSAULT_VEST",
            "EVIOLITE", "WEAKNESS_POLICY", "LUM_BERRY", "SITRUS_BERRY",
            "SHED_SHELL", "AIR_BALLOON", "BLACK_SLUDGE", "FLAME_ORB",
            "TOXIC_ORB",
        }
        actual = {i.name for i in Item}
        missing = expected - actual
        assert not missing, f"Missing items: {missing}"

    def test_no_item_enum_value(self):
        assert hasattr(Item, "NONE"), "Item.NONE must exist for 'no held item' state"

    def test_items_are_unique(self):
        values = [i.value for i in Item]
        assert len(values) == len(set(values))

    def test_all_items_have_data(self):
        for item in Item:
            assert item in ITEM_DATA, f"{item.name} missing from ITEM_DATA"
