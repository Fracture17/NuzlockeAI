"""Tests for the move data layer.

Verifies:
- Move enum has expected entries
- MoveData fields are correctly populated for key moves
- MoveTag classification is present
- Secondary effect data is accessible
"""
import pytest
from liveplay.data.moves import Move, MoveData, MoveTag, MoveCategory, MOVE_DATA


class TestMoveEnum:
    def test_key_moves_present(self):
        expected_names = {
            "FLAMETHROWER", "SURF", "THUNDERBOLT", "PSYCHIC", "EARTHQUAKE",
            "IRON_HEAD", "DRAGON_CLAW", "CLOSE_COMBAT", "MOONBLAST", "TOXIC",
            "WILL_O_WISP", "PROTECT", "ROOST", "SWORDS_DANCE", "CALM_MIND",
            "STEALTH_ROCK", "REFLECT", "LIGHT_SCREEN",
        }
        actual_names = {m.name for m in Move}
        missing = expected_names - actual_names
        assert not missing, f"Missing moves: {missing}"

    def test_moves_are_unique(self):
        values = [m.value for m in Move]
        assert len(values) == len(set(values))


class TestMoveData:
    def test_flamethrower_data(self):
        data = MOVE_DATA[Move.FLAMETHROWER]
        assert data.base_power == 90
        from liveplay.data.types import Type
        assert data.move_type == Type.FIRE
        assert data.category == MoveCategory.SPECIAL
        assert data.accuracy == 100
        assert data.pp == 15
        assert data.priority == 0

    def test_earthquake_data(self):
        data = MOVE_DATA[Move.EARTHQUAKE]
        assert data.base_power == 100
        from liveplay.data.types import Type
        assert data.move_type == Type.GROUND
        assert data.category == MoveCategory.PHYSICAL
        assert data.accuracy == 100

    def test_toxic_is_status(self):
        data = MOVE_DATA[Move.TOXIC]
        assert data.base_power == 0
        assert data.category == MoveCategory.STATUS

    def test_swift_never_misses(self):
        data = MOVE_DATA[Move.SWIFT]
        assert data.accuracy is None or data.accuracy == 0

    def test_protect_has_priority(self):
        data = MOVE_DATA[Move.PROTECT]
        assert data.priority == 4

    def test_quick_attack_priority(self):
        data = MOVE_DATA[Move.QUICK_ATTACK]
        assert data.priority == 1

    def test_flamethrower_has_secondary(self):
        data = MOVE_DATA[Move.FLAMETHROWER]
        assert data.secondary is not None
        assert data.secondary.chance == 10

    def test_no_secondary_for_earthquake(self):
        data = MOVE_DATA[Move.EARTHQUAKE]
        assert data.secondary is None

    def test_surf_spread_target(self):
        data = MOVE_DATA[Move.SURF]
        from liveplay.data.moves import MoveTarget
        assert data.target in (MoveTarget.ALL_ADJACENT_FOES, MoveTarget.ALL_ADJACENT)

    def test_swords_dance_tag(self):
        data = MOVE_DATA[Move.SWORDS_DANCE]
        assert MoveTag.SETUP in data.tags

    def test_roost_tag(self):
        data = MOVE_DATA[Move.ROOST]
        assert MoveTag.RECOVERY in data.tags

    def test_stealth_rock_tag(self):
        data = MOVE_DATA[Move.STEALTH_ROCK]
        assert MoveTag.HAZARD in data.tags

    def test_reflect_tag(self):
        data = MOVE_DATA[Move.REFLECT]
        assert MoveTag.SCREEN in data.tags

    def test_toxic_tag(self):
        data = MOVE_DATA[Move.TOXIC]
        assert MoveTag.STATUS in data.tags

    def test_flamethrower_tag(self):
        data = MOVE_DATA[Move.FLAMETHROWER]
        assert MoveTag.DAMAGE in data.tags

    def test_all_moves_have_move_data(self):
        for move in Move:
            assert move in MOVE_DATA, f"{move.name} missing from MOVE_DATA"

    def test_move_data_fields_typed(self):
        data = MOVE_DATA[Move.SURF]
        assert isinstance(data.base_power, int)
        assert isinstance(data.pp, int)
        assert isinstance(data.priority, int)

    def test_removed_moves_absent_from_enum(self):
        # Guard: Shadow Force, Lock On, and Mind Reader are not in this game.
        assert not hasattr(Move, 'SHADOW_FORCE')
        assert not hasattr(Move, 'LOCK_ON')
        assert not hasattr(Move, 'MIND_READER')

    def test_removed_moves_absent_from_move_data(self):
        move_names = {m.name for m in MOVE_DATA}
        assert 'SHADOW_FORCE' not in move_names
        assert 'LOCK_ON' not in move_names
        assert 'MIND_READER' not in move_names
