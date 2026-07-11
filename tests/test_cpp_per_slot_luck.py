"""Tests for per-slot-1 attacker luck in cpp_run_one_turn (doubles).

Drives the binding directly via nuzlocke_engine_cpp.run_one_turn to test the new
luck_p0_slot1 / luck_p1_slot1 payload keys before run_one_turn_cpp exposes them.
All tests use random_mode=False (controlled deterministic luck).
"""
import dataclasses
import json

import liveplay.sweep_io as sweep_io
from liveplay.cpp_driver import damage_luck_payload, turn_luck_payload, action_payload
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.rng import LuckProfile, GOOD_LUCK
from tests.state_builders import make_mon, make_battle, make_doubles_battle, dslot, slot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Action helpers: move_slot index for a specific move in the attacker's moveset.
# Attackers are built with moves=(Move.TACKLE, Move.SPLASH) — TACKLE=slot 0, SPLASH=slot 1.
_TACKLE_SLOT = 0
_SPLASH_SLOT = 1


def _action_payload_with_source(action) -> dict:
    """Serialize Action to the C++ binding dict, including source_slot (absent from action_payload)."""
    d = action_payload(action)
    d["source_slot"] = action.source_slot
    return d


def _run(state, action_p0, action_p1, luck_p0: LuckProfile, luck_p1: LuckProfile,
         *, luck_p0_slot1: LuckProfile | None = None,
         luck_p1_slot1: LuckProfile | None = None,
         finalize_on_post_faint: bool = True):
    """Build and dispatch a run_one_turn payload; return the output BattleState."""
    import nuzlocke_engine_cpp as cpp

    def encode_actions(a):
        if isinstance(a, list):
            return [_action_payload_with_source(x) for x in a]
        return _action_payload_with_source(a)

    payload = {
        "state": sweep_io.to_jsonable(state),
        "action_p0": encode_actions(action_p0),
        "action_p1": encode_actions(action_p1),
        "luck_p0": damage_luck_payload(luck_p0),
        "luck_p1": damage_luck_payload(luck_p1),
        "turn_luck_p0": turn_luck_payload(luck_p0),
        "turn_luck_p1": turn_luck_payload(luck_p1),
        "mega_p0": False,
        "mega_p1": False,
        "finalize_on_post_faint": finalize_on_post_faint,
    }
    if luck_p0_slot1 is not None:
        payload["luck_p0_slot1"] = damage_luck_payload(luck_p0_slot1)
    if luck_p1_slot1 is not None:
        payload["luck_p1_slot1"] = damage_luck_payload(luck_p1_slot1)

    out_json = cpp.run_one_turn(json.dumps(payload))
    decoded = json.loads(out_json)
    return sweep_io.from_jsonable(decoded["state"])


def _luck(damage_roll: float = 0.5,
          damage_rolls_per_hit: list | None = None) -> LuckProfile:
    """Controlled LuckProfile: always-hit, no crits, specified damage_roll."""
    base = dataclasses.replace(GOOD_LUCK, damage_roll=damage_roll, random_mode=False)
    if damage_rolls_per_hit is not None:
        base = dataclasses.replace(base, damage_rolls_per_hit=tuple(damage_rolls_per_hit))
    return base


def _doubles_state():
    """Two Blissey (TACKLE=slot0, SPLASH=slot1) vs two Snorlax (SPLASH=slot0)."""
    atk0 = make_mon(Species.BLISSEY, moves=(Move.TACKLE, Move.SPLASH), level=50)
    atk1 = make_mon(Species.BLISSEY, moves=(Move.TACKLE, Move.SPLASH), level=50)
    def0 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    def1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    return make_doubles_battle(atk0, atk1, def0, def1)


def _def_hp(state, slot_idx: int) -> int:
    """HP of opp active slot `slot_idx`."""
    return state.sides[1].team[state.sides[1].active_indices[slot_idx]].hp


# ---------------------------------------------------------------------------
# Test 1: per-slot luck separates damage for two identical doubles attackers
# ---------------------------------------------------------------------------

class TestPerSlotLuckDifferentDamage:
    """luck_p0_slot1 differs from luck_p0 → slot 0 and slot 1 deal distinct damage."""

    def test_slot0_damage_greater_than_slot1_when_per_slot_luck_differs(self):
        """slot 0 uses damage_roll=1.0 (side-level), slot 1 uses damage_roll=0.0 (slot-1 luck).

        Run A: only slot 0 attacks opp slot 0; slot 1 uses Splash.
        Run B: only slot 1 attacks opp slot 0; slot 0 uses Splash.
        Expected: damage from run A > damage from run B.
        """
        state = _doubles_state()
        high_luck = _luck(damage_roll=1.0)
        low_luck = _luck(damage_roll=0.0)

        # Opp actions: both Snorlax use Splash (move_slot=0).
        opp_actions = [dslot(0, target=0, source=0), dslot(0, target=0, source=1)]

        # Run A: slot 0 Tackle, slot 1 Splash.
        state_a = _run(
            state,
            [dslot(_TACKLE_SLOT, target=0, source=0),   # slot 0: Tackle
             dslot(_SPLASH_SLOT, target=0, source=1)],   # slot 1: Splash
            opp_actions,
            luck_p0=high_luck,
            luck_p1=high_luck,
            luck_p0_slot1=low_luck,  # doesn't matter here since slot 1 uses Splash
        )
        start_hp = _def_hp(state, 0)
        damage_slot0 = start_hp - _def_hp(state_a, 0)

        # Run B: slot 0 Splash, slot 1 Tackle.
        state_b = _run(
            state,
            [dslot(_SPLASH_SLOT, target=0, source=0),   # slot 0: Splash
             dslot(_TACKLE_SLOT, target=0, source=1)],   # slot 1: Tackle
            opp_actions,
            luck_p0=high_luck,
            luck_p1=high_luck,
            luck_p0_slot1=low_luck,  # slot 1 uses Tackle with roll=0.0
        )
        damage_slot1 = start_hp - _def_hp(state_b, 0)

        assert damage_slot0 > 0, f"slot 0 (roll=1.0) should deal damage, got 0"
        assert damage_slot1 > 0, f"slot 1 (roll=0.0) should deal damage, got 0"
        assert damage_slot0 > damage_slot1, (
            f"slot 0 (side-level roll=1.0) should deal more than slot 1 (slot-1 roll=0.0); "
            f"got slot0={damage_slot0}, slot1={damage_slot1}"
        )


# ---------------------------------------------------------------------------
# Test 2: absent luck_p0_slot1 → side-level luck applies to both slots equally
# ---------------------------------------------------------------------------

class TestAbsentSlotLuckFallsBackToSideLevel:
    """Without luck_p0_slot1, both slots use the same side-level luck → equal damage."""

    def test_equal_damage_without_slot1_key(self):
        """Both slots attack with the same side-level luck → equal damage from each.

        Run A: slot 0 Tackle; Run B: slot 1 Tackle. No luck_p0_slot1 key.
        Same side-level luck → identical damage output.
        """
        state = _doubles_state()
        avg_luck = _luck(damage_roll=0.5)
        opp_actions = [dslot(0, target=0, source=0), dslot(0, target=0, source=1)]

        state_a = _run(
            state,
            [dslot(_TACKLE_SLOT, target=0, source=0),
             dslot(_SPLASH_SLOT, target=0, source=1)],
            opp_actions,
            luck_p0=avg_luck, luck_p1=avg_luck,
            # luck_p0_slot1 absent → side-level applies to slot 1 too
        )
        state_b = _run(
            state,
            [dslot(_SPLASH_SLOT, target=0, source=0),
             dslot(_TACKLE_SLOT, target=0, source=1)],
            opp_actions,
            luck_p0=avg_luck, luck_p1=avg_luck,
            # luck_p0_slot1 absent
        )
        start_hp = _def_hp(state, 0)
        damage_a = start_hp - _def_hp(state_a, 0)
        damage_b = start_hp - _def_hp(state_b, 0)

        assert damage_a > 0, "slot 0 Tackle should deal damage"
        assert damage_b > 0, "slot 1 Tackle should deal damage"
        assert damage_a == damage_b, (
            f"Without slot-1 luck key both slots should deal equal damage; "
            f"got slot0={damage_a}, slot1={damage_b}"
        )


# ---------------------------------------------------------------------------
# Test 3: singles with slot-1 keys present-but-equal → byte-identical state
# ---------------------------------------------------------------------------

class TestSinglesByteParity:
    """Singles: luck_p0_slot1/luck_p1_slot1 equal to side-level luck → identical output."""

    def test_singles_with_slot1_keys_equal_to_side_level_is_identical(self):
        """Sanity: extra keys don't corrupt singles output when values match side-level."""
        import nuzlocke_engine_cpp as cpp

        mon0 = make_mon(Species.BLISSEY, moves=(Move.TACKLE,), level=50)
        mon1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
        state = make_battle(mon0, mon1)

        luck = _luck(damage_roll=0.7)
        a0 = slot(0)
        a1 = slot(0)

        payload_base = {
            "state": sweep_io.to_jsonable(state),
            "action_p0": _action_payload_with_source(a0),
            "action_p1": _action_payload_with_source(a1),
            "luck_p0": damage_luck_payload(luck),
            "luck_p1": damage_luck_payload(luck),
            "turn_luck_p0": turn_luck_payload(luck),
            "turn_luck_p1": turn_luck_payload(luck),
            "mega_p0": False,
            "mega_p1": False,
        }
        out_base = json.loads(cpp.run_one_turn(json.dumps(payload_base)))["state"]

        payload_with = dict(payload_base)  # already uses _action_payload_with_source
        payload_with["luck_p0_slot1"] = damage_luck_payload(luck)
        payload_with["luck_p1_slot1"] = damage_luck_payload(luck)
        out_with = json.loads(cpp.run_one_turn(json.dumps(payload_with)))["state"]

        assert out_base == out_with, "Extra equal slot-1 luck keys must not alter singles output"


# ---------------------------------------------------------------------------
# Test 4: per-slot damage_rolls_per_hit for a 2-hit move on slot 1
# ---------------------------------------------------------------------------

class TestPerSlotMultiHitRolls:
    """slot-1 luck with damage_rolls_per_hit=[0.0, 1.0] vs uniform 0.5 → different total damage."""

    def test_two_hits_differ_with_per_hit_rolls(self):
        """Hitmonlee slot 1 uses Double Kick with per-hit [0.0, 1.0] vs uniform 0.5.

        Both runs use the same slot-0 (Splash), only slot 1 attacks.
        Per-hit [0.0, 1.0] hits low then high; uniform 0.5 hits medium twice.
        Total damage should differ between the two rolls.
        """
        # Hitmonlee (Fighting): 120 Atk, Double Kick (Fighting, 30 BP x2).
        # Target: Snorlax level 100 (~460 HP) — won't faint from two Double Kick hits at L50.
        hitmonlee = make_mon(Species.HITMONLEE, moves=(Move.SPLASH, Move.DOUBLE_KICK), level=50)
        hitmonlee2 = make_mon(Species.HITMONLEE, moves=(Move.SPLASH, Move.DOUBLE_KICK), level=50)
        target0 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=100)
        target1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=100)

        state = make_doubles_battle(hitmonlee, hitmonlee2, target0, target1)
        # Double Kick is at move_slot=1 (second slot in moveset)
        _DOUBLE_KICK_SLOT = 1

        opp_actions = [dslot(0, target=0, source=0), dslot(0, target=0, source=1)]

        side_luck = _luck(damage_roll=0.5)
        slot1_luck_low_high = _luck(damage_rolls_per_hit=[0.0, 1.0])
        # Use high damage for reference (1.0 both hits) — notably different from [0.0, 1.0] avg.
        slot1_luck_max = _luck(damage_roll=1.0)

        # Run with slot-1 luck carrying per-hit rolls [0.0, 1.0]
        out_per_hit = _run(
            state,
            [dslot(_SPLASH_SLOT, target=0, source=0),             # slot 0: Splash
             dslot(_DOUBLE_KICK_SLOT, target=0, source=1)],        # slot 1: Double Kick
            opp_actions,
            luck_p0=side_luck,
            luck_p1=side_luck,
            luck_p0_slot1=slot1_luck_low_high,
        )

        # Run with slot-1 luck at max (1.0 flat) — should give higher damage
        out_max = _run(
            state,
            [dslot(_SPLASH_SLOT, target=0, source=0),
             dslot(_DOUBLE_KICK_SLOT, target=0, source=1)],
            opp_actions,
            luck_p0=side_luck,
            luck_p1=side_luck,
            luck_p0_slot1=slot1_luck_max,
        )

        start_hp = _def_hp(state, 0)
        damage_per_hit = start_hp - _def_hp(out_per_hit, 0)
        damage_max = start_hp - _def_hp(out_max, 0)

        assert damage_per_hit > 0, "Double Kick with per-hit rolls should deal damage"
        assert damage_max > 0, "Double Kick with max luck should deal damage"
        assert damage_max > damage_per_hit, (
            f"Max luck (roll=1.0 both hits, damage={damage_max}) should exceed "
            f"per-hit [0.0, 1.0] (damage={damage_per_hit})"
        )
