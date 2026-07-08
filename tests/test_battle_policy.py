# Tests for src/battle_policy.py: eligible_switch_targets, available_moves, RandomPolicy.
import random
import pytest

from liveplay.data.species import Species
from liveplay.data.moves import Move
from liveplay.data.natures import Nature
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.state.pokemon import PokemonState, GenderEnum, VolatileEffect
from liveplay.state.side import SideState
from liveplay.state.battle import BattleState
from liveplay.battle_policy import (
    eligible_switch_targets, available_moves, RandomPolicy, can_switch_out,
)


def _make_mon(species=Species.RATTATA, move_ids=None, move_pp=None, fainted=False, hp=50):
    move_ids = move_ids or (Move.TACKLE, Move.NONE, Move.NONE, Move.NONE)
    move_pp = move_pp or (35, 0, 0, 0)
    mon = PokemonState(
        species=species,
        nature=Nature.HARDY,
        ivs=(31,) * 6,
        gender=GenderEnum.MALE,
        move_ids=move_ids,
        move_pp=move_pp,
    )
    return mon._replace(hp=hp, fainted=fainted)


def _make_state(player_team, active_index=0, opponent_team=None):
    """Build a BattleState with the given player team and active slot."""
    if opponent_team is None:
        opponent_team = [_make_mon(Species.PIDGEY)]
    side0 = SideState(team=player_team, active_indices=[active_index])
    side1 = SideState(team=opponent_team, active_indices=[0])
    return BattleState(sides=(side0, side1))


# ---------------------------------------------------------------------------
# eligible_switch_targets
# ---------------------------------------------------------------------------

class TestEligibleSwitchTargets:

    def test_excludes_active_by_index(self):
        active = _make_mon(Species.BULBASAUR, hp=50)
        bench = _make_mon(Species.CHARMANDER, hp=50)
        state = _make_state([active, bench], active_index=0)
        result = eligible_switch_targets(state)
        assert len(result) == 1
        assert result[0].species == Species.CHARMANDER

    def test_excludes_fainted(self):
        active = _make_mon(Species.BULBASAUR, hp=50)
        fainted = _make_mon(Species.CHARMANDER, fainted=True, hp=0)
        state = _make_state([active, fainted], active_index=0)
        assert eligible_switch_targets(state) == []

    def test_excludes_zero_hp(self):
        active = _make_mon(Species.BULBASAUR, hp=50)
        zero_hp = _make_mon(Species.CHARMANDER, hp=0)
        state = _make_state([active, zero_hp], active_index=0)
        assert eligible_switch_targets(state) == []

    def test_includes_valid_bench(self):
        active = _make_mon(Species.BULBASAUR, hp=50)
        bench1 = _make_mon(Species.CHARMANDER, hp=40)
        bench2 = _make_mon(Species.SQUIRTLE, hp=30)
        state = _make_state([active, bench1, bench2], active_index=0)
        result = eligible_switch_targets(state)
        assert len(result) == 2

    def test_active_at_non_zero_index(self):
        # Active is at index 1; index 0 should be a valid target
        mon0 = _make_mon(Species.BULBASAUR, hp=50)
        mon1 = _make_mon(Species.CHARMANDER, hp=50)
        state = _make_state([mon0, mon1], active_index=1)
        result = eligible_switch_targets(state)
        assert len(result) == 1
        assert result[0].species == Species.BULBASAUR

    def test_none_hp_treated_as_zero(self):
        # hp=None means (hp or 0) == 0, so should be excluded
        active = _make_mon(Species.BULBASAUR, hp=50)
        bench = _make_mon(Species.CHARMANDER, hp=50)
        bench = bench._replace(hp=None)
        state = _make_state([active, bench], active_index=0)
        assert eligible_switch_targets(state) == []


# ---------------------------------------------------------------------------
# available_moves
# ---------------------------------------------------------------------------

class TestAvailableMoves:

    def test_excludes_move_none_slots(self):
        mon = _make_mon(
            move_ids=(Move.TACKLE, Move.NONE, Move.NONE, Move.NONE),
            move_pp=(35, 0, 0, 0),
        )
        state = _make_state([mon])
        result = available_moves(state)
        assert result == [Move.TACKLE]

    def test_excludes_zero_pp(self):
        mon = _make_mon(
            move_ids=(Move.TACKLE, Move.SCRATCH, Move.NONE, Move.NONE),
            move_pp=(0, 5, 0, 0),
        )
        state = _make_state([mon])
        result = available_moves(state)
        assert result == [Move.SCRATCH]

    def test_includes_all_usable(self):
        mon = _make_mon(
            move_ids=(Move.TACKLE, Move.SCRATCH, Move.NONE, Move.NONE),
            move_pp=(10, 5, 0, 0),
        )
        state = _make_state([mon])
        result = available_moves(state)
        assert set(result) == {Move.TACKLE, Move.SCRATCH}

    def test_empty_when_all_zero_pp(self):
        mon = _make_mon(
            move_ids=(Move.TACKLE, Move.SCRATCH, Move.NONE, Move.NONE),
            move_pp=(0, 0, 0, 0),
        )
        state = _make_state([mon])
        assert available_moves(state) == []


# ---------------------------------------------------------------------------
# RandomPolicy
# ---------------------------------------------------------------------------

class TestRandomPolicyForcedSwitch:

    def test_never_returns_active_species(self):
        active = _make_mon(Species.BULBASAUR, hp=50)
        bench = _make_mon(Species.CHARMANDER, hp=50)
        state = _make_state([active, bench], active_index=0)
        rng = random.Random(42)
        policy = RandomPolicy(rng=rng)
        for _ in range(100):
            result = policy.choose_forced_switch(state)
            assert result != Species.BULBASAUR.name

    def test_never_returns_fainted(self):
        active = _make_mon(Species.BULBASAUR, hp=50)
        fainted = _make_mon(Species.CHARMANDER, fainted=True, hp=0)
        bench = _make_mon(Species.SQUIRTLE, hp=30)
        state = _make_state([active, fainted, bench], active_index=0)
        rng = random.Random(99)
        policy = RandomPolicy(rng=rng)
        for _ in range(100):
            result = policy.choose_forced_switch(state)
            assert result == Species.SQUIRTLE.name

    def test_raises_when_bench_empty(self):
        active = _make_mon(Species.BULBASAUR, hp=50)
        state = _make_state([active], active_index=0)
        policy = RandomPolicy()
        with pytest.raises(RuntimeError):
            policy.choose_forced_switch(state)

    def test_raises_when_all_bench_fainted(self):
        active = _make_mon(Species.BULBASAUR, hp=50)
        fainted = _make_mon(Species.CHARMANDER, fainted=True, hp=0)
        state = _make_state([active, fainted], active_index=0)
        policy = RandomPolicy()
        with pytest.raises(RuntimeError):
            policy.choose_forced_switch(state)


@pytest.mark.skip(reason="Stage E: enumerate_legal_actions not wired")
class TestRandomPolicyBattleAction:

    def _make_battle_state(self, has_bench=True, has_moves=True):
        move_ids = (Move.TACKLE, Move.NONE, Move.NONE, Move.NONE) if has_moves else (Move.NONE,) * 4
        move_pp = (35, 0, 0, 0) if has_moves else (0,) * 4
        active = _make_mon(Species.BULBASAUR, move_ids=move_ids, move_pp=move_pp, hp=50)
        if has_bench:
            bench = _make_mon(Species.CHARMANDER, hp=50)
            return _make_state([active, bench], active_index=0)
        return _make_state([active], active_index=0)

    def test_100_percent_move_when_no_bench(self):
        state = self._make_battle_state(has_bench=False, has_moves=True)
        rng = random.Random(0)
        policy = RandomPolicy(rng=rng)
        results = [policy.choose_battle_action(state) for _ in range(200)]
        assert all(isinstance(r, Move) for r in results)

    def test_raises_when_no_moves_and_no_bench(self):
        state = self._make_battle_state(has_bench=False, has_moves=False)
        policy = RandomPolicy()
        with pytest.raises(RuntimeError):
            policy.choose_battle_action(state)

    def test_always_switches_when_no_moves_but_has_bench(self):
        state = self._make_battle_state(has_bench=True, has_moves=False)
        rng = random.Random(7)
        policy = RandomPolicy(rng=rng)
        results = [policy.choose_battle_action(state) for _ in range(100)]
        assert all(isinstance(r, str) for r in results)

    def test_80_20_split(self):
        state = self._make_battle_state(has_bench=True, has_moves=True)
        rng = random.Random(12345)
        policy = RandomPolicy(rng=rng)
        results = [policy.choose_battle_action(state) for _ in range(2000)]
        switch_fraction = sum(isinstance(r, str) for r in results) / len(results)
        assert 0.15 <= switch_fraction <= 0.25, f"Switch fraction {switch_fraction:.3f} outside 0.15–0.25"

    def test_move_returns_are_in_available_moves(self):
        state = self._make_battle_state(has_bench=True, has_moves=True)
        moves = available_moves(state)
        rng = random.Random(55)
        policy = RandomPolicy(rng=rng)
        results = [policy.choose_battle_action(state) for _ in range(500)]
        for r in results:
            if isinstance(r, Move):
                assert r in moves

    def test_switch_returns_are_eligible_targets(self):
        state = self._make_battle_state(has_bench=True, has_moves=True)
        eligible_names = {m.species.name for m in eligible_switch_targets(state)}
        rng = random.Random(77)
        policy = RandomPolicy(rng=rng)
        results = [policy.choose_battle_action(state) for _ in range(500)]
        for r in results:
            if isinstance(r, str):
                assert r in eligible_names

    def test_default_rng_is_isolated(self):
        # Two policies with no explicit rng should be independent instances
        p1 = RandomPolicy()
        p2 = RandomPolicy()
        assert p1._rng is not p2._rng


# ---------------------------------------------------------------------------
# can_switch_out / trapping (regression for the stress-test infinite-switch loop:
# Clobbopus Bind trapped Natu, but RandomPolicy kept offering switches the game
# rejected, hanging forever at "What will Natu do?")
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Stage E: enumerate_legal_actions not wired")
class TestCanSwitchOut:

    def _state_with(self, active, bench_species=Species.CHARMANDER, opp=None):
        bench = _make_mon(bench_species, hp=40)
        return _make_state([active, bench], active_index=0, opponent_team=opp)

    def test_free_when_untrapped(self):
        active = _make_mon(Species.BULBASAUR, hp=50)
        assert can_switch_out(self._state_with(active)) is True

    def test_blocked_by_bound(self):
        # Bind/Wrap etc. apply the BOUND timed volatile → cannot voluntarily switch.
        active = _make_mon(Species.BULBASAUR, hp=50)
        active = active._replace(timed_volatiles=[(VolatileEffect.BOUND, 3)])
        assert can_switch_out(self._state_with(active)) is False

    def test_blocked_by_trapped_volatile(self):
        # Mean Look / Anchor Shot / Spirit Shackle apply the TRAPPED volatile.
        active = _make_mon(Species.BULBASAUR, hp=50)
        active = active._replace(timed_volatiles=[(VolatileEffect.TRAPPED, -1)])
        assert can_switch_out(self._state_with(active)) is False

    def test_shed_shell_bypasses_bound(self):
        # Shed Shell lets a BOUND mon switch out anyway.
        active = _make_mon(Species.BULBASAUR, hp=50)
        active = active._replace(
            timed_volatiles=[(VolatileEffect.BOUND, 3)], item=Item.SHED_SHELL,
        )
        assert can_switch_out(self._state_with(active)) is True

    def test_blocked_by_opponent_shadow_tag(self):
        active = _make_mon(Species.BULBASAUR, hp=50)  # non-Ghost
        trapper = _make_mon(Species.PIDGEY, hp=40)._replace(ability=Ability.SHADOW_TAG)
        assert can_switch_out(self._state_with(active, opp=[trapper])) is False


@pytest.mark.skip(reason="Stage E: enumerate_legal_actions not wired")
class TestRandomPolicyTrapping:

    def _trapped_state(self, *, item=Item.NONE, has_moves=True):
        move_ids = (Move.TACKLE, Move.NONE, Move.NONE, Move.NONE) if has_moves else (Move.NONE,) * 4
        move_pp = (35, 0, 0, 0) if has_moves else (0,) * 4
        active = _make_mon(Species.BULBASAUR, move_ids=move_ids, move_pp=move_pp, hp=50)
        active = active._replace(timed_volatiles=[(VolatileEffect.BOUND, 3)], item=item)
        bench = _make_mon(Species.CHARMANDER, hp=40)
        return _make_state([active, bench], active_index=0)

    def test_trapped_never_switches(self):
        # The core regression: a BOUND active with a live bench must never be told to
        # switch; every decision must be a move so the runner makes progress.
        state = self._trapped_state()
        rng = random.Random(12345)
        policy = RandomPolicy(rng=rng)
        results = [policy.choose_battle_action(state) for _ in range(500)]
        assert all(isinstance(r, Move) for r in results)

    def test_shed_shell_trapped_still_switches_sometimes(self):
        # Shed Shell bypasses BOUND, so the 20% switch path is available again.
        state = self._trapped_state(item=Item.SHED_SHELL)
        rng = random.Random(999)
        policy = RandomPolicy(rng=rng)
        results = [policy.choose_battle_action(state) for _ in range(500)]
        assert any(isinstance(r, str) for r in results)
