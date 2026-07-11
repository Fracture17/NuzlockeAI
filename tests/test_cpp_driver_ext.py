# Tests for cpp_driver.py extensions: source_slot fix, finalize_on_post_faint,
# apply_switch_cpp, doubles action lists, per-slot luck kwargs, and back-compat.
import dataclasses
import json

import pytest

import liveplay.sweep_io as sweep_io
from liveplay.cpp_driver import (
    action_payload,
    apply_switch_cpp,
    run_one_turn_cpp,
    UnportedTurn,
)
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.rng import LuckProfile, GOOD_LUCK, AVERAGE_LUCK
from liveplay.state.side import SideCondition
from tests.state_builders import (
    make_mon,
    make_battle,
    make_doubles_battle,
    dslot,
    slot,
    active,
)


# ---------------------------------------------------------------------------
# Luck helpers (controlled, deterministic)
# ---------------------------------------------------------------------------

def _luck(damage_roll: float = 0.5) -> LuckProfile:
    """Always-hit, no-crit, specified damage_roll. random_mode=False for determinism."""
    return dataclasses.replace(GOOD_LUCK, damage_roll=damage_roll, random_mode=False)


_HIGH = _luck(1.0)
_LOW = _luck(0.0)
_AVG = _luck(0.5)


# ---------------------------------------------------------------------------
# Test 1: action_payload source_slot
# ---------------------------------------------------------------------------

class TestActionPayloadSourceSlot:
    """action_payload must include source_slot from the Action dataclass."""

    def test_source_slot_1(self):
        assert action_payload(dslot(0, source=1))["source_slot"] == 1

    def test_source_slot_default_zero(self):
        assert action_payload(slot(0))["source_slot"] == 0

    def test_source_slot_explicit_zero(self):
        assert action_payload(dslot(0, source=0))["source_slot"] == 0


# ---------------------------------------------------------------------------
# Test 2: finalize_on_post_faint
# ---------------------------------------------------------------------------

def _make_ohko_battle():
    """Side 0: Machamp (strong attacker). Side 1: 1-HP Blissey (active) + healthy Snorlax (bench)."""
    attacker = make_mon(Species.MACHAMP, moves=(Move.TACKLE,), level=100)
    # 1-HP defender — guaranteed OHKO
    defender_active = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=1, hp=1)
    bench = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    state = make_battle(attacker, defender_active, team1=[defender_active, bench])
    return state, attacker


class TestFinalizeOnPostFaint:
    """finalize_on_post_faint controls whether post-faint switch raises or returns."""

    def test_false_raises_unported(self):
        state, _ = _make_ohko_battle()
        with pytest.raises(UnportedTurn):
            run_one_turn_cpp(
                state,
                slot(0),   # Tackle
                slot(0),   # Splash (defender)
                _HIGH, _HIGH,
                finalize_on_post_faint=False,
            )

    def test_true_returns_fainted_active(self):
        state, _ = _make_ohko_battle()
        result = run_one_turn_cpp(
            state,
            slot(0),
            slot(0),
            _HIGH, _HIGH,
            finalize_on_post_faint=True,
        )
        # Side 1's active mon should be fainted and still in place
        assert result.sides[1].team[result.sides[1].active_indices[0]].fainted


# ---------------------------------------------------------------------------
# Test 3: apply_switch_cpp
# ---------------------------------------------------------------------------

class TestApplySwitchCpp:
    """apply_switch_cpp: finalized faint state → switch the living bench mon in."""

    def _finalized_state(self):
        state, _ = _make_ohko_battle()
        return run_one_turn_cpp(
            state,
            slot(0),
            slot(0),
            _HIGH, _HIGH,
            finalize_on_post_faint=True,
        )

    def test_switch_replaces_fainted_active(self):
        faint_state = self._finalized_state()
        # Team slot 1 is the bench Snorlax
        result = apply_switch_cpp(faint_state, 1, 1, 0)
        new_active = result.sides[1].team[result.sides[1].active_indices[0]]
        assert not new_active.fainted
        assert new_active.species == Species.SNORLAX

    def test_switch_with_stealth_rock_chips_hp(self):
        """Stealth Rock on side 1 should chip the switch-in's HP."""
        faint_state = self._finalized_state()
        # Set Stealth Rock on side 1 before the switch
        side1 = faint_state.sides[1]
        side1_with_sr = dataclasses.replace(
            side1,
            side_conditions=list(side1.side_conditions) + [(SideCondition.STEALTH_ROCK, -1)],
        )
        state_with_sr = dataclasses.replace(
            faint_state,
            sides=(faint_state.sides[0], side1_with_sr),
        )
        result = apply_switch_cpp(state_with_sr, 1, 1, 0)
        new_active = result.sides[1].team[result.sides[1].active_indices[0]]
        # The incoming Snorlax should have taken SR chip damage
        assert not new_active.fainted
        assert new_active.hp < new_active.max_hp


# ---------------------------------------------------------------------------
# Test 4: doubles action lists
# ---------------------------------------------------------------------------

class TestDoublesActionLists:
    """Each side may pass a list of two Actions; both attackers' effects occur."""

    def test_both_attackers_deal_damage(self):
        """Both slot-0 and slot-1 Blissey use Tackle → both opponents take damage."""
        atk0 = make_mon(Species.BLISSEY, moves=(Move.TACKLE,), level=50)
        atk1 = make_mon(Species.BLISSEY, moves=(Move.TACKLE,), level=50)
        def0 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
        def1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
        state = make_doubles_battle(atk0, atk1, def0, def1)

        p0_actions = [dslot(0, target=0, source=0), dslot(0, target=1, source=1)]
        p1_actions = [dslot(0, target=0, source=0), dslot(0, target=1, source=1)]

        result = run_one_turn_cpp(
            state,
            p0_actions,
            p1_actions,
            _AVG, _AVG,
            finalize_on_post_faint=True,
        )

        def0_start = state.sides[1].team[state.sides[1].active_indices[0]].hp
        def1_start = state.sides[1].team[state.sides[1].active_indices[1]].hp
        def0_after = result.sides[1].team[result.sides[1].active_indices[0]].hp
        def1_after = result.sides[1].team[result.sides[1].active_indices[1]].hp

        assert def0_after < def0_start, "Opponent slot 0 should have taken damage"
        assert def1_after < def1_start, "Opponent slot 1 should have taken damage"


# ---------------------------------------------------------------------------
# Test 5: per-slot luck kwargs
# ---------------------------------------------------------------------------

class TestPerSlotLuckKwargs:
    """luck_p0_slot1 / luck_p1_slot1 kwargs are serialized and affect per-slot damage."""

    def _doubles_state(self):
        atk0 = make_mon(Species.BLISSEY, moves=(Move.TACKLE, Move.SPLASH), level=50)
        atk1 = make_mon(Species.BLISSEY, moves=(Move.TACKLE, Move.SPLASH), level=50)
        def0 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
        def1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
        return make_doubles_battle(atk0, atk1, def0, def1)

    def _def_hp(self, state, slot_idx: int) -> int:
        return state.sides[1].team[state.sides[1].active_indices[slot_idx]].hp

    def test_per_slot_luck_produces_different_damage(self):
        """slot-0 luck=1.0 (side-level), slot-1 luck=0.0 → slot 0 deals more than slot 1."""
        state = self._doubles_state()
        opp_actions = [dslot(0, target=0, source=0), dslot(0, target=0, source=1)]

        # Run A: only slot 0 attacks (slot 1 uses Splash)
        state_a = run_one_turn_cpp(
            state,
            [dslot(0, target=0, source=0), dslot(1, target=0, source=1)],  # Tackle, Splash
            opp_actions,
            _HIGH, _HIGH,
            luck_p0_slot1=_LOW,
            finalize_on_post_faint=True,
        )
        start_hp = self._def_hp(state, 0)
        damage_slot0 = start_hp - self._def_hp(state_a, 0)

        # Run B: only slot 1 attacks (slot 0 uses Splash)
        state_b = run_one_turn_cpp(
            state,
            [dslot(1, target=0, source=0), dslot(0, target=0, source=1)],  # Splash, Tackle
            opp_actions,
            _HIGH, _HIGH,
            luck_p0_slot1=_LOW,
            finalize_on_post_faint=True,
        )
        damage_slot1 = start_hp - self._def_hp(state_b, 0)

        assert damage_slot0 > 0
        assert damage_slot1 > 0
        assert damage_slot0 > damage_slot1, (
            f"Slot 0 (roll=1.0) should beat slot 1 (roll=0.0); got {damage_slot0} vs {damage_slot1}"
        )

    def test_absent_slot1_luck_gives_equal_damage(self):
        """Without luck_p0_slot1, both slots use side-level luck → equal damage."""
        state = self._doubles_state()
        opp_actions = [dslot(0, target=0, source=0), dslot(0, target=0, source=1)]

        state_a = run_one_turn_cpp(
            state,
            [dslot(0, target=0, source=0), dslot(1, target=0, source=1)],
            opp_actions,
            _AVG, _AVG,
            finalize_on_post_faint=True,
        )
        state_b = run_one_turn_cpp(
            state,
            [dslot(1, target=0, source=0), dslot(0, target=0, source=1)],
            opp_actions,
            _AVG, _AVG,
            finalize_on_post_faint=True,
        )
        start_hp = self._def_hp(state, 0)
        assert (start_hp - self._def_hp(state_a, 0)) == (start_hp - self._def_hp(state_b, 0))


# ---------------------------------------------------------------------------
# Test 6: back-compat (singles, no new kwargs)
# ---------------------------------------------------------------------------

class TestBackCompat:
    """Plain singles call with no new kwargs works and deals damage."""

    def test_singles_no_new_kwargs(self):
        attacker = make_mon(Species.MACHAMP, moves=(Move.TACKLE,), level=50)
        defender = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
        state = make_battle(attacker, defender)

        result = run_one_turn_cpp(state, slot(0), slot(0), _AVG, _AVG)
        assert active(result, 1).hp < defender.hp, "Defender should have taken damage"
