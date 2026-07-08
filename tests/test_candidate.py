"""Tests for __hash__/__eq__ on state classes and Candidate construction."""
import copy
import pytest

from liveplay.data.species import Species
from liveplay.data.natures import Nature
from liveplay.data.status import Status
from liveplay.data.items import Item
from liveplay.data.moves import Move
from liveplay.state.pokemon import PokemonState, GenderEnum, Volatile, VolatileEffect
from liveplay.state.side import SideState, FormatEnum, SideCondition
from liveplay.state.battle import BattleState, WeatherEnum
from liveplay.candidate import Candidate

# ---------------------------------------------------------------------------
# PartialCandidate import (needed for T1-T4; not yet implemented)
# ---------------------------------------------------------------------------
# Import deferred to test bodies — tests must fail (not skip) when missing.
def _import_partial_candidate():
    """Import PartialCandidate; raises ImportError if refactor not yet in place."""
    from liveplay.candidate import PartialCandidate  # noqa: PLC0415
    return PartialCandidate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_pokemon(**kwargs) -> PokemonState:
    defaults = dict(
        species=Species.CHARIZARD,
        nature=Nature.TIMID,
        ivs=(31, 31, 31, 31, 31, 31),
        gender=GenderEnum.MALE,
    )
    defaults.update(kwargs)
    return PokemonState(**defaults)


def make_side(pokemon=None, **kwargs) -> SideState:
    if pokemon is None:
        pokemon = [make_pokemon()]
    return SideState(team=pokemon, **kwargs)


def make_battle(side0=None, side1=None, **kwargs) -> BattleState:
    if side0 is None:
        side0 = make_side()
    if side1 is None:
        side1 = make_side(pokemon=[make_pokemon(species=Species.BLASTOISE)])
    return BattleState(sides=(side0, side1), **kwargs)


# ---------------------------------------------------------------------------
# PokemonState equality and hashing
# ---------------------------------------------------------------------------

class TestPokemonStateHash:
    def test_identical_objects_equal_and_same_hash(self):
        p1 = make_pokemon()
        p2 = make_pokemon()
        assert p1 == p2
        assert hash(p1) == hash(p2)

    def test_different_hp_unequal(self):
        p1 = make_pokemon()
        p2 = make_pokemon()
        p2 = p2._replace(hp=p2.hp - 1)
        assert p1 != p2
        assert hash(p1) != hash(p2)

    def test_different_status_unequal(self):
        p1 = make_pokemon()
        p2 = make_pokemon()
        p2 = p2._replace(status=Status.BURN)
        assert p1 != p2
        assert hash(p1) != hash(p2)

    def test_different_item_unequal(self):
        p1 = make_pokemon()
        p2 = make_pokemon()
        p2 = p2._replace(item=Item.LEFTOVERS)
        assert p1 != p2
        assert hash(p1) != hash(p2)

    def test_different_volatiles_unequal(self):
        p1 = make_pokemon()
        p2 = make_pokemon()
        p2 = p2._replace(volatiles=Volatile.CONFUSED)
        assert p1 != p2
        assert hash(p1) != hash(p2)

    def test_different_timed_volatiles_unequal(self):
        p1 = make_pokemon()
        p2 = make_pokemon()
        p2 = p2._replace(timed_volatiles=[(VolatileEffect.TAUNT, 3)])
        assert p1 != p2
        assert hash(p1) != hash(p2)

    def test_is_hashable(self):
        p = make_pokemon()
        s = {p}
        assert len(s) == 1


# ---------------------------------------------------------------------------
# SideState equality and hashing
# ---------------------------------------------------------------------------

class TestSideStateHash:
    def test_identical_sides_equal_and_same_hash(self):
        s1 = make_side()
        s2 = make_side()
        assert s1 == s2
        assert hash(s1) == hash(s2)

    def test_different_team_unequal(self):
        s1 = make_side(pokemon=[make_pokemon()])
        s2 = make_side(pokemon=[make_pokemon(species=Species.BLASTOISE)])
        assert s1 != s2
        assert hash(s1) != hash(s2)

    def test_different_active_indices_unequal(self):
        p = make_pokemon()
        s1 = SideState(team=[p, make_pokemon(species=Species.BLASTOISE)], format=FormatEnum.DOUBLES)
        s2 = copy.copy(s1)
        s2.active_indices = [1, 0]
        assert s1 != s2
        assert hash(s1) != hash(s2)

    def test_different_side_conditions_unequal(self):
        s1 = make_side()
        s2 = make_side()
        s2 = copy.copy(s2)
        s2.side_conditions = [(SideCondition.STEALTH_ROCK, -1)]
        assert s1 != s2
        assert hash(s1) != hash(s2)

    def test_is_hashable(self):
        s = make_side()
        h = {s}
        assert len(h) == 1


# ---------------------------------------------------------------------------
# BattleState equality and hashing
# ---------------------------------------------------------------------------

class TestBattleStateHash:
    def test_identical_battles_equal_and_same_hash(self):
        b1 = make_battle()
        b2 = make_battle()
        assert b1 == b2
        assert hash(b1) == hash(b2)

    def test_different_weather_unequal(self):
        b1 = make_battle()
        b2 = make_battle(weather=WeatherEnum.RAINY)
        assert b1 != b2
        assert hash(b1) != hash(b2)

    def test_set_deduplicates_equal_states(self):
        b1 = make_battle()
        b2 = make_battle()
        s = {b1, b2}
        assert len(s) == 1

    def test_set_keeps_unequal_states(self):
        b1 = make_battle()
        b2 = make_battle(weather=WeatherEnum.SUNNY)
        s = {b1, b2}
        assert len(s) == 2

    def test_is_hashable(self):
        b = make_battle()
        h = {b}
        assert len(h) == 1


# ---------------------------------------------------------------------------
# Candidate construction
# ---------------------------------------------------------------------------

class TestCandidateConstruction:
    def test_construct_with_state_only(self):
        state = make_battle()
        c = Candidate(state=state)
        assert c.state is state

    def test_rng_sequence_defaults_to_empty_list(self):
        c = Candidate(state=make_battle())
        assert c.rng_sequence == []

    def test_unknown_actions_defaults_to_empty_dict(self):
        c = Candidate(state=make_battle())
        assert c.unknown_actions == {}

    def test_parent_candidate_defaults_to_none(self):
        c = Candidate(state=make_battle())
        assert c.parent_candidate is None

    def test_parent_candidate_can_be_set(self):
        parent = Candidate(state=make_battle())
        child = Candidate(state=make_battle(), parent_candidate=parent)
        assert child.parent_candidate is parent

    def test_rng_sequence_independent_per_instance(self):
        c1 = Candidate(state=make_battle())
        c2 = Candidate(state=make_battle())
        c1.rng_sequence.append(("event", 1))
        assert c2.rng_sequence == []


# ===========================================================================
# REFACTOR TESTS: PartialCandidate (T1-T4)
# These tests require the not-yet-built refactor of src/candidate.py.
# They will fail with ImportError until PartialCandidate is implemented.
# ===========================================================================

class TestPartialCandidateDefaults:
    """T1: PartialCandidate has empty tuple defaults and mover_iteration == 0."""

    def test_rolls_default_empty_tuple(self):
        PartialCandidate = _import_partial_candidate()
        pc = PartialCandidate()
        assert pc.rolls == ()

    def test_crits_default_empty_tuple(self):
        PartialCandidate = _import_partial_candidate()
        pc = PartialCandidate()
        assert pc.crits == ()

    def test_mover_iteration_default_zero(self):
        PartialCandidate = _import_partial_candidate()
        pc = PartialCandidate()
        assert pc.mover_iteration == 0


class TestPartialCandidateFrozenAndHashable:
    """T2: PartialCandidate is frozen (mutation raises FrozenInstanceError) and hashable."""

    def test_assign_field_raises_frozen_instance_error(self):
        from dataclasses import FrozenInstanceError
        PartialCandidate = _import_partial_candidate()
        pc = PartialCandidate()
        with pytest.raises(FrozenInstanceError):
            pc.rolls = (0.5,)

    def test_assign_crits_raises_frozen_instance_error(self):
        from dataclasses import FrozenInstanceError
        PartialCandidate = _import_partial_candidate()
        pc = PartialCandidate()
        with pytest.raises(FrozenInstanceError):
            pc.crits = (True,)

    def test_assign_mover_iteration_raises_frozen_instance_error(self):
        from dataclasses import FrozenInstanceError
        PartialCandidate = _import_partial_candidate()
        pc = PartialCandidate()
        with pytest.raises(FrozenInstanceError):
            pc.mover_iteration = 1

    def test_hashable(self):
        PartialCandidate = _import_partial_candidate()
        pc = PartialCandidate(rolls=(0.5,), crits=(False,), mover_iteration=1)
        s = {pc}
        assert len(s) == 1


class TestPartialCandidateEquality:
    """T3: Two identical PartialCandidates compare equal; differing ones compare unequal."""

    def test_identical_instances_equal(self):
        PartialCandidate = _import_partial_candidate()
        pc1 = PartialCandidate(rolls=(0.5, 1.0), crits=(False, True), mover_iteration=2)
        pc2 = PartialCandidate(rolls=(0.5, 1.0), crits=(False, True), mover_iteration=2)
        assert pc1 == pc2

    def test_different_rolls_unequal(self):
        PartialCandidate = _import_partial_candidate()
        pc1 = PartialCandidate(rolls=(0.5,), crits=(False,), mover_iteration=1)
        pc2 = PartialCandidate(rolls=(1.0,), crits=(False,), mover_iteration=1)
        assert pc1 != pc2

    def test_different_crits_unequal(self):
        PartialCandidate = _import_partial_candidate()
        pc1 = PartialCandidate(rolls=(0.5,), crits=(False,), mover_iteration=1)
        pc2 = PartialCandidate(rolls=(0.5,), crits=(True,), mover_iteration=1)
        assert pc1 != pc2

    def test_different_mover_iteration_unequal(self):
        PartialCandidate = _import_partial_candidate()
        pc1 = PartialCandidate(rolls=(0.5,), crits=(False,), mover_iteration=0)
        pc2 = PartialCandidate(rolls=(0.5,), crits=(False,), mover_iteration=1)
        assert pc1 != pc2


class TestPartialCandidateForwardExtension:
    """T4: Building a new PartialCandidate with extended fields does not mutate the original."""

    def test_forward_extension_does_not_mutate_original(self):
        PartialCandidate = _import_partial_candidate()
        original = PartialCandidate(rolls=(0.5,), crits=(False,), mover_iteration=1)
        extended = PartialCandidate(
            rolls=original.rolls + (1.0,),
            crits=original.crits + (True,),
            mover_iteration=original.mover_iteration + 1,
        )
        # Original is unchanged
        assert original.rolls == (0.5,)
        assert original.crits == (False,)
        assert original.mover_iteration == 1
        # Extended has the new values
        assert extended.rolls == (0.5, 1.0)
        assert extended.crits == (False, True)
        assert extended.mover_iteration == 2

    def test_original_and_extended_are_distinct(self):
        PartialCandidate = _import_partial_candidate()
        original = PartialCandidate()
        extended = PartialCandidate(
            rolls=(0.5,),
            crits=(False,),
            mover_iteration=1,
        )
        assert original != extended
