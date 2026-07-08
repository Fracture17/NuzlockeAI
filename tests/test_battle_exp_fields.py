# Tests for new BattleState fields added for EXP tracking (Task 4).
import pytest
from liveplay.state.battle import BattleState
from liveplay.state.side import SideState, FormatEnum
from liveplay.data.species import Species
from liveplay.data.natures import Nature
from liveplay.state.pokemon import PokemonState, GenderEnum


def make_side():
    mon = PokemonState(
        species=Species.RATTATA,
        nature=Nature.HARDY,
        ivs=(31, 31, 31, 31, 31, 31),
        gender=GenderEnum.MALE,
    )
    return SideState(team=[mon], active_indices=[0])


def make_battle(**kwargs):
    sides = (make_side(), make_side())
    return BattleState(sides=sides, **kwargs)


class TestBattleStateNewFields:
    def test_default_is_trainer_battle(self):
        battle = make_battle()
        assert battle.is_trainer_battle is True

    def test_default_level_cap_none(self):
        battle = make_battle()
        assert battle.level_cap is None

    def test_default_exp_participants_empty(self):
        battle = make_battle()
        assert battle.exp_participants == ()

    def test_is_trainer_battle_false(self):
        battle = make_battle(is_trainer_battle=False)
        assert battle.is_trainer_battle is False

    def test_level_cap_set(self):
        battle = make_battle(level_cap=50)
        assert battle.level_cap == 50

    def test_exp_participants_set(self):
        participants = (frozenset([0, 1]),)
        battle = make_battle(exp_participants=participants)
        assert battle.exp_participants == participants

    def test_hash_changes_with_is_trainer_battle(self):
        b1 = make_battle(is_trainer_battle=True)
        b2 = make_battle(is_trainer_battle=False)
        assert hash(b1) != hash(b2)

    def test_hash_changes_with_level_cap(self):
        b1 = make_battle(level_cap=None)
        b2 = make_battle(level_cap=50)
        assert hash(b1) != hash(b2)

    def test_hash_changes_with_exp_participants(self):
        b1 = make_battle(exp_participants=())
        b2 = make_battle(exp_participants=(frozenset([0]),))
        assert hash(b1) != hash(b2)
