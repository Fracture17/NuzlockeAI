"""Regression guards for confirmed findings in RECORDS/StaticIssues.md.

Each test asserts the CANONICAL (emulator-correct) behavior that the C++ engine
implements correctly. Ported from the retired old repo (PycharmProjects/NuzlockeAI)
as regression guards — xfail markers removed because all bugs are now fixed.

The audit's guiding principle: a divergence from the emulator with no exception is a
silent desync — the worst class of bug. Several of these tests demonstrate the engine
producing a state the emulator never reaches, with nothing raising.

Verified against Pokémon Showdown's data/abilities.ts (Gen 8) and confirmed to have no
Run & Bun override in "Mechanic Changes.txt".
"""
import dataclasses

from liveplay.cpp_driver import run_one_turn_cpp, apply_switch_cpp
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.moves import Move
from liveplay.data.natures import Nature
from liveplay.data.species import Species
from liveplay.data.status import Status
from liveplay.rng import GOOD_LUCK
from liveplay.state.battle import BattleState, WeatherEnum
from liveplay.state.pokemon import Volatile, VolatileEffect
from liveplay.state.side import SideState
from tests.state_builders import make_mon, make_battle, slot

# Deterministic luck profile — random_mode=False explicitly for reproducibility.
DET = dataclasses.replace(GOOD_LUCK, random_mode=False)

_MV0 = slot(0)


def _attack_with(move, defender_species, defender_ability, *,
                 attacker_species=Species.PIKACHU, defender_hp=None):
    """Run one turn: side 0 uses `move` (slot 0) at a defender with the given ability."""
    p0 = make_mon(attacker_species, moves=(move,))
    p1 = make_mon(defender_species, moves=(Move.TACKLE,),
                  ability=defender_ability, hp=defender_hp)
    result = run_one_turn_cpp(make_battle(p0, p1), _MV0, _MV0, DET, DET)
    return result.sides[1].team[0]


# ---------------------------------------------------------------------------
# Group H — execution-path parity: STATUS moves bypass type/ability immunity
# ---------------------------------------------------------------------------
# The STATUS move path (_handle_status_action) does not call _check_type_immunity,
# and effects.py only wires up Flash Fire (Will-O-Wisp) and Sap Sipper-vs-Leech-Seed.
# Electric-absorbing abilities and Sap Sipper-vs-other-Grass-status are unhandled, so
# the engine applies a status the emulator never applies. With no observed status
# message to contradict it (the foe's bar does not move and check_log_events' STATUS
# check is presence-only — finding A1), the wrong state survives the sweep silently.


class TestH1_ElectricAbsorbVsThunderWave:
    """H1: Thunder Wave (Electric, STATUS) must be absorbed by Electric-immunity
    abilities on a NON-Electric holder (Electric-types are already paralysis-immune
    by type via _can_apply_status). Showdown abilities.ts: lightningrod/voltabsorb/
    motordrive onTryHit filter only on move.type === 'Electric' (no category gate)."""

    def test_thunder_wave_vs_lightning_rod_marowak(self):
        # Marowak is Ground-type (not paralysis-immune by type) with Lightning Rod.
        d = _attack_with(Move.THUNDER_WAVE, Species.MAROWAK, Ability.LIGHTNING_ROD)
        assert d.status == Status.NONE, "Lightning Rod must block Thunder Wave's paralysis"
        assert d.stat_stages[2] == +1, "Lightning Rod must raise SpA by 1"

    def test_thunder_wave_vs_motor_drive(self):
        d = _attack_with(Move.THUNDER_WAVE, Species.MAROWAK, Ability.MOTOR_DRIVE)
        assert d.status == Status.NONE, "Motor Drive must block Thunder Wave's paralysis"
        assert d.stat_stages[4] == +1, "Motor Drive must raise Speed by 1"

    def test_thunder_wave_vs_volt_absorb_heals(self):
        # Non-Electric Volt Absorb holder at low HP: must be immune AND heal 1/4 max.
        d = _attack_with(Move.THUNDER_WAVE, Species.BLISSEY, Ability.VOLT_ABSORB,
                         defender_hp=1)
        assert d.status == Status.NONE, "Volt Absorb must block Thunder Wave's paralysis"
        assert d.hp > 1, "Volt Absorb must heal when hit by an Electric move"


class TestH2_SapSipperVsGrassStatusMoves:
    """H2: Sap Sipper grants immunity to ALL Grass moves (Showdown abilities.ts:
    sapsipper onTryHit filters only on move.type === 'Grass'). The engine only wires
    it up for Leech Seed (effects.py:667-676); other Grass status moves slip through."""

    def test_spore_vs_sap_sipper_non_grass_holder(self):
        # Azumarill (Water/Fairy) is not Grass-type, so the _can_apply_status powder/
        # Grass check does not save it; only Sap Sipper should.
        d = _attack_with(Move.SPORE, Species.AZUMARILL, Ability.SAP_SIPPER,
                         attacker_species=Species.VENUSAUR)
        assert d.status == Status.NONE, "Sap Sipper must block Spore's sleep"
        assert d.stat_stages[0] == +1, "Sap Sipper must raise Attack by 1"

    def test_grass_whistle_vs_sap_sipper(self):
        # Grass Whistle is Grass-type but NOT a powder move, so even a Grass-type holder
        # is not covered by the powder immunity — Sap Sipper is the only block.
        d = _attack_with(Move.GRASS_WHISTLE, Species.AZUMARILL, Ability.SAP_SIPPER,
                         attacker_species=Species.VENUSAUR)
        assert d.status == Status.NONE, "Sap Sipper must block Grass Whistle's sleep"
        assert d.stat_stages[0] == +1, "Sap Sipper must raise Attack by 1"


# ---------------------------------------------------------------------------
# Group I — end-of-turn residual order: heals must run BEFORE the drains
# ---------------------------------------------------------------------------
# _apply_residuals_for_slot (residuals.py:543) runs its _res_* sub-functions in source
# order, which places Leftovers/Black Sludge healing (_res_item_residuals, line 623)
# AFTER Leech Seed (line 606) and poison/burn status damage (line 615). Canonical
# onResidualOrder (Showdown items.ts/moves.ts/conditions.ts, Gen 8): Leftovers=5,
# Aqua Ring=6, Ingrain=7, Leech Seed=8, poison/toxic=9, burn=10 — the heal band runs
# first. Emitting the heal last both inflates final HP (a small overshoot that can hide
# under the opponent HP-bar tolerance — silent desync) and changes faint timing (the
# engine faints a Pokemon the emulator keeps alive). Both are asserted at canonical values.


def _poisoned_leftovers_turn(mode):
    """One turn where a POISONed Leftovers Snorlax and a Pikachu both use Splash (no HP
    interaction), so the only HP change is the residual band. ``mode`` selects the
    starting HP: "full" = max, "low" = exactly 1/8 max (one poison tick from fainting).
    Returns (resulting_mon, max_hp)."""
    p0 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,),
                  item=Item.LEFTOVERS, status=Status.POISON)
    max_hp = p0.max_hp
    p0 = p0._replace(hp=max_hp if mode == "full" else max_hp // 8)
    p1 = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
    result = run_one_turn_cpp(make_battle(p0, p1), _MV0, _MV0, DET, DET)
    return result.sides[0].team[0], max_hp


class TestI1_ResidualHealBeforeDrain:
    """I1: Leftovers heals BEFORE poison (Showdown onResidualOrder 5 < poison 9), not
    after. The engine runs the heal last, so at full HP it overheals by 1/16 and at low
    HP it faints a mon that should have survived."""

    def test_full_hp_does_not_overheal(self):
        # At full HP, Leftovers heals 0 (already capped), then poison removes 1/8.
        # Canonical final = max_hp - max_hp//8. The engine heals 1/16 too much (poison first).
        mon, max_hp = _poisoned_leftovers_turn("full")
        assert not mon.fainted
        assert mon.hp == max_hp - max_hp // 8, (
            "Leftovers runs before poison; at full HP it heals nothing, so the turn's "
            "only HP change is -1/8 from poison"
        )

    def test_low_hp_survives_via_pre_drain_heal(self):
        # At exactly 1/8 max HP: canonical Leftovers +1/16 -> 3/16, then poison -1/8 -> 1/16.
        # The mon SURVIVES at max_hp//16. The engine applies poison first (-> 0, faint).
        mon, max_hp = _poisoned_leftovers_turn("low")
        assert not mon.fainted, "Leftovers must heal before poison and keep the mon alive"
        assert mon.hp == max_hp // 16


def _poisoned_raindish_turn(mode):
    """Like _poisoned_leftovers_turn but the heal source is Rain Dish in rain (a weather
    ability), which canonically resolves in the weather band (onFieldResidualOrder 1) —
    BEFORE poison. The sim runs it in the late ability band, after poison."""
    p0 = make_mon(Species.LUDICOLO, moves=(Move.SPLASH,),
                  ability=Ability.RAIN_DISH, status=Status.POISON)
    max_hp = p0.max_hp
    p0 = p0._replace(hp=max_hp if mode == "full" else max_hp // 8)
    p1 = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
    battle = BattleState(
        sides=(SideState(team=[p0], active_indices=[0]),
               SideState(team=[p1], active_indices=[0])),
        weather=WeatherEnum.RAINY, weather_turns=5,
    )
    result = run_one_turn_cpp(battle, _MV0, _MV0, DET, DET)
    return result.sides[0].team[0], max_hp


class TestI2_WeatherAbilityHealBeforeDrain:
    """I2: Rain Dish/Dry Skin/Solar Power are onWeather effects that canonically resolve in
    the weather band (onFieldResidualOrder 1), before Leech Seed/poison/burn — the same band
    as Ice Body, which the sim DOES place early. The sim instead runs these three in the late
    _res_ability_residuals band, after poison, so they overheal at full HP and faint a mon at
    low HP that should have healed first."""

    def test_rain_dish_full_hp_does_not_overheal(self):
        mon, max_hp = _poisoned_raindish_turn("full")
        assert not mon.fainted
        assert mon.hp == max_hp - max_hp // 8, (
            "Rain Dish resolves in the weather band before poison; at full HP it heals 0, "
            "so the only change is -1/8 poison"
        )

    def test_rain_dish_low_hp_survives_via_pre_drain_heal(self):
        mon, max_hp = _poisoned_raindish_turn("low")
        assert not mon.fainted, "Rain Dish heal must run in the weather band, before poison"
        assert mon.hp == max_hp // 16


class TestI3_StatusCureAbilityBeforeTick:
    """I3: Shed Skin / Hydration are onResidualOrder 5 (before poison=9/burn=10), so when
    they cure they prevent that turn's status tick entirely. The sim deals the tick in
    _res_status_damage (step 5) and only cures in _res_ability_residuals (step 7), so it
    applies one extra tick the emulator never deals. Hydration in rain is a 100% repro."""

    def test_hydration_in_rain_takes_no_poison_tick(self):
        p0 = make_mon(Species.LUDICOLO, moves=(Move.SPLASH,),
                      ability=Ability.HYDRATION, status=Status.POISON)
        max_hp = p0.max_hp  # start at full HP
        p1 = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        battle = BattleState(
            sides=(SideState(team=[p0], active_indices=[0]),
                   SideState(team=[p1], active_indices=[0])),
            weather=WeatherEnum.RAINY, weather_turns=5,
        )
        result = run_one_turn_cpp(battle, _MV0, _MV0, DET, DET)
        mon = result.sides[0].team[0]
        assert mon.status == Status.NONE, "Hydration cures poison in rain"
        assert mon.hp == max_hp, (
            "Hydration cures at onResidualOrder 5, before the poison tick (9), so a "
            "full-HP holder takes no residual damage this turn"
        )

    def test_hydration_in_rain_does_not_cure_flame_orb_burn_same_turn(self):
        # Flame Orb is onResidualOrder 28; Hydration is onResidualOrder 5. On the orb's
        # ACTIVATION turn, Hydration's cure band (5) runs first, finds no status to cure,
        # and only then does the orb (28) inflict BURN — so the mon ends the turn BURNED.
        # The engine inverts this: orb burns at item step (6), then Hydration cures at
        # ability step (7), so the burn vanishes the instant it is applied.
        p0 = make_mon(Species.LAPRAS, moves=(Move.SPLASH,),
                      ability=Ability.HYDRATION, item=Item.FLAME_ORB)
        p1 = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        battle = BattleState(
            sides=(SideState(team=[p0], active_indices=[0]),
                   SideState(team=[p1], active_indices=[0])),
            weather=WeatherEnum.RAINY, weather_turns=5,
        )
        result = run_one_turn_cpp(battle, _MV0, _MV0, DET, DET)
        mon = result.sides[0].team[0]
        assert mon.status == Status.BURN, (
            "Flame Orb (onResidualOrder 28) inflicts BURN after Hydration's cure band (5) "
            "has already passed for the turn, so the mon ends the activation turn burned"
        )


# ---------------------------------------------------------------------------
# Group J — post-damage self-effect order: Life Orb recoil must run LAST
# ---------------------------------------------------------------------------
# Life Orb recoil is applied in _apply_post_hit_items (post_hit.py:147), the FIRST post-hit
# step, before drain/recoil/secondaries. Canonically it is onAfterMoveSecondarySelf (Showdown
# items.ts:3408) — the last self-effect, after drain (which resolves during the hit). The
# sim then guards drain with `not attacker.fainted`, so a low-HP drain-move user holding Life
# Orb dies to the recoil before the drain that would canonically have kept it alive.


class TestJ1_LifeOrbRecoilBeforeDrain:
    """J1: a Life Orb holder at exactly 1/10 max HP using a drain move should survive — drain
    heals before Life Orb recoil. The sim applies recoil first (-> 0, faint) and skips the
    drain."""

    def test_life_orb_drain_user_survives(self):
        # Venusaur @ 1/10 max HP, Life Orb, Giga Drain into a 4x-weak bulky target.
        p0 = make_mon(Species.VENUSAUR, moves=(Move.GIGA_DRAIN,), item=Item.LIFE_ORB)
        max_hp = p0.max_hp
        p0 = p0._replace(hp=max(1, max_hp // 10))
        p1 = make_mon(Species.SWAMPERT, moves=(Move.SPLASH,))
        result = run_one_turn_cpp(make_battle(p0, p1), _MV0, _MV0, DET, DET)
        atk = result.sides[0].team[0]
        assert not atk.fainted, (
            "Giga Drain heals before Life Orb recoil (onAfterMoveSecondarySelf), so the "
            "attacker must survive"
        )
        assert atk.hp > 0


# ---------------------------------------------------------------------------
# Group K — switch-path reset parity: forced switches skip the full reset
# ---------------------------------------------------------------------------
# There are TWO switch implementations with DIFFERENT reset sets:
#   * voluntary switch action resets ~25 per-battle fields incl. stat_stages=(0,...),
#     crit_stage, confusion_turns, AND applies Natural Cure + Regenerator on switch-out.
#   * apply_switch_cpp resets only the forced-switch fields — but the C++ engine now
#     applies full clearVolatile() and onSwitchOut (Regenerator/Natural Cure) on all
#     switch-outs, forced included.
#
# Canonical Gen 8 (Showdown sim/battle-actions.ts): dragIn -> switchIn(...,isDrag=true);
# the SwitchOut event (Regenerator/Natural Cure onSwitchOut) fires UNCONDITIONALLY (line 87)
# and clearVolatile() (line 117 -> pokemon.ts:1509) zeroes ALL boosts and clears volatiles
# on every switch-out, forced included. No Run & Bun override exists.


def _forced_switch_out(active_mon):
    """Switch `active_mon` (side 0, slot 0) OUT via apply_switch_cpp (new-repo equivalent
    of effects._apply_switch). Returns the outgoing mon after the switch so its
    post-switch-out state can be asserted."""
    bench = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
    foe = make_mon(Species.CHARIZARD, moves=(Move.SPLASH,))
    s0 = SideState(team=[active_mon, bench], active_indices=[0])
    s1 = SideState(team=[foe], active_indices=[0])
    state = BattleState(sides=(s0, s1))
    result_state = apply_switch_cpp(state, side_idx=0, new_slot=1, source_slot=0)
    # The mon that was switched OUT is still at team[0]; it should have been reset.
    return result_state.sides[0].team[0]


class TestK1_ForcedSwitchResetsStatStages:
    """K1: a +6 Atk mon phazed out by Roar must leave the field with stat_stages back to 0
    (Showdown clearVolatile zeroes boosts on every switch-out). The forced-switch helper
    leaves the boosts intact, and since no switch-IN path re-zeroes them, they leak back when
    the mon returns — a damage-calc desync with nothing thrown."""

    def test_boosts_cleared_on_forced_switch_out(self):
        active = make_mon(Species.SNORLAX, moves=(Move.SPLASH,))
        active = active._replace(stat_stages=(6, 0, 0, 0, 0, 0, 0))
        out = _forced_switch_out(active)
        assert out.stat_stages == (0, 0, 0, 0, 0, 0, 0), (
            "Switching out (even forced) zeroes all stat stages; the benched mon must not "
            "carry +6 Atk back onto the field"
        )


class TestK2_ForcedSwitchAppliesRegenerator:
    """K2: a Regenerator mon forced out by Roar heals 1/3 max HP on switch-out (Showdown
    SwitchOut event fires on drag). effects._apply_switch applies no heal, so the benched
    mon's HP is 1/3 max too low — an HP desync that surfaces when it returns."""

    def test_regenerator_heals_on_forced_switch_out(self):
        active = make_mon(Species.SLOWBRO, moves=(Move.SPLASH,),
                          ability=Ability.REGENERATOR)
        max_hp = active.max_hp
        active = active._replace(hp=max(1, max_hp // 2))
        out = _forced_switch_out(active)
        assert out.hp == min(max_hp, max_hp // 2 + max_hp // 3), (
            "Regenerator restores 1/3 max HP on switch-out, forced included"
        )


class TestK3_ForcedSwitchAppliesNaturalCure:
    """K3: a statused Natural Cure mon forced out by Roar is cured on switch-out (Showdown
    SwitchOut event fires on drag). effects._apply_switch leaves the status, so the benched
    mon stays burned — a status (and status-tick) desync that surfaces when it returns."""

    def test_natural_cure_clears_status_on_forced_switch_out(self):
        active = make_mon(Species.BLISSEY, moves=(Move.SPLASH,),
                          ability=Ability.NATURAL_CURE, status=Status.BURN)
        out = _forced_switch_out(active)
        assert out.status == Status.NONE, (
            "Natural Cure clears status on switch-out, forced included"
        )


# ---------------------------------------------------------------------------
# Group L — cross-mon residual order is per-side, not globally banded by onResidualOrder
# ---------------------------------------------------------------------------
# _apply_residuals (residuals.py:668-673) runs side 0's ENTIRE residual chain, then side 1's,
# with no speed sort. Canonical Gen 8 (Showdown sim/battle.ts:2837 fieldEvent('Residual'))
# gathers every active mon's onResidual handler into ONE list (battle.ts:491-503) and
# speedSort()s it (line 507) by onResidualOrder first, then speed — so a band-8 effect on one
# side resolves before a band-9 effect on the OTHER side. Group I covers the within-mon band
# order; this is the cross-mon dimension. Because the engine finishes side 0 (incl. its
# band-9 poison) before starting side 1 (incl. its band-8 Leech Seed), a later band on side 0
# pre-empts an earlier band on side 1 — observable as an order-dependent faint.


class TestL1_CrossMonResidualBandOrder:
    """L1: Leech Seed (onResidualOrder 8) on side 1 must resolve before poison
    (onResidualOrder 9) on side 0, healing side 0's seeded beneficiary before its own poison
    tick. The engine runs side 0's poison first, fainting a 1/8-HP beneficiary that the
    emulator keeps alive. SILENT-DESYNC + order-dependent faint."""

    def test_leech_seed_heal_precedes_opposite_side_poison(self):
        # P0 (side 0): poisoned, exactly 1/8 max HP, and the Leech Seed beneficiary.
        p0 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), status=Status.POISON)
        p0 = p0._replace(hp=max(1, p0.max_hp // 8))
        # P1 (side 1): seeded (its drain heals the opposing P0). Healthy.
        # LEECH_SEED_SOURCE_SLOT=0 means the seeder-side slot that receives the heal is
        # side 0's active mon (the beneficiary we want healed).
        p1 = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        p1 = p1._replace(
            volatiles=int(Volatile.LEECH_SEEDED),
            timed_volatiles=[(VolatileEffect.LEECH_SEED_SOURCE_SLOT, 0)],
        )
        battle = BattleState(sides=(
            SideState(team=[p0], active_indices=[0]),
            SideState(team=[p1], active_indices=[0]),
        ))
        result = run_one_turn_cpp(battle, _MV0, _MV0, DET, DET)
        out0 = result.sides[0].team[0]
        assert not out0.fainted, (
            "Leech Seed (band 8) heals P0 before its poison (band 9) ticks, so the "
            "1/8-HP beneficiary survives"
        )
        assert out0.hp == p1.max_hp // 8, (
            "P0 ends at +leech(P1/8) - poison(P0/8) = P1.max_hp//8"
        )


# ---------------------------------------------------------------------------
# Group M — Life Orb recoil is applied before drain heal (reversed vs canonical)
# ---------------------------------------------------------------------------
# Engine order: _apply_post_hit_effects calls _apply_post_hit_items (Life Orb recoil,
# post_hit.py:147) at line 605, then applies move drain at post_hit.py:820 — Life Orb FIRST.
# Canonical Gen 8 (Showdown): drain is applied inside spreadDamage during the hit
# (sim/battle.ts:2173-2175, this.heal(..., 'drain')), while Life Orb is onAfterMoveSecondarySelf
# (data/items.ts:3408) which fires in afterMoveSecondaryEvent AFTER the per-hit loop
# (sim/battle-actions.ts:1026) — drain FIRST, Life Orb LAST. Because the drain heal caps at
# max HP, the order changes the attacker's final HP whenever the heal would overheal. At full
# HP the divergence is exactly one Life-Orb recoil (max_hp//10): canonically the overheal is
# wasted at the cap and the holder ends at max-10%, but the engine subtracts Life Orb first so
# the drain refills it and the holder ends at full HP. No R&B override (Mechanic Changes.txt).
# Life Orb recoil also logs no DAMAGE event (post_hit.py:147-159), so check_log_events has
# nothing to validate the attacker's HP against at that step -> the wrong HP is silent.


class TestM1_LifeOrbAppliedBeforeDrain:
    """M1: a full-HP attacker holding Life Orb that uses a drain move (Giga Drain) must end at
    max_hp - max_hp//10: the drain overheal is wasted at the cap, then Life Orb recoil applies.
    The engine subtracts Life Orb first, so the drain refills it and the attacker stays at full
    HP — a state the emulator never reaches (attacker HP too high by one Life-Orb recoil).
    SILENT-DESYNC (Life Orb recoil is not logged, so the attacker HP is never reconciled)."""

    def test_full_hp_giga_drain_lifeorb_ends_below_max(self):
        atk = make_mon(Species.VENUSAUR, moves=(Move.GIGA_DRAIN,), item=Item.LIFE_ORB)
        # Bulky defender that survives Giga Drain so the drain heal actually occurs and the
        # damage dealt (>= 2*recoil) makes the drain large enough to overheal a full-HP holder.
        dfn = make_mon(Species.SNORLAX, moves=(Move.SPLASH,))
        battle = BattleState(sides=(
            SideState(team=[atk], active_indices=[0]),
            SideState(team=[dfn], active_indices=[0]),
        ))
        result = run_one_turn_cpp(battle, _MV0, _MV0, DET, DET)
        out_atk = result.sides[0].team[0]
        out_dfn = result.sides[1].team[0]
        dealt = dfn.hp - out_dfn.hp
        # Precondition: defender survived and the drain (1/2 dealt) would overheal at full HP.
        assert not out_dfn.fainted and dealt // 2 >= atk.max_hp // 10, (
            "test precondition: defender must survive and drain must exceed Life Orb recoil"
        )
        assert out_atk.hp == atk.max_hp - atk.max_hp // 10, (
            "drain overheal is wasted at the cap; only the Life Orb recoil (max_hp//10) "
            "should remain, leaving the holder below full HP"
        )


class TestM2_DrainAppliedAfterContactRecoil:
    """M2: same root cause as M1, but for contact recoil. A full-HP attacker using a contact
    drain move (Leech Life) into a Rough Skin holder must end at max_hp - max_hp//8: canonically
    the drain heal happens during the hit (overheal wasted at the cap) BEFORE the Rough Skin
    recoil (DamagingHit). The engine applies Rough Skin in-loop first and drain post-loop, so the
    drain refills the recoil and the attacker stays at full HP — proving the divergence is the
    drain being ordered last among ALL attacker HP changes, not specific to Life Orb."""

    def test_full_hp_leech_life_into_rough_skin_ends_below_max(self):
        atk = make_mon(Species.SCIZOR, moves=(Move.LEECH_LIFE,))
        dfn = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), ability=Ability.ROUGH_SKIN)
        battle = BattleState(sides=(
            SideState(team=[atk], active_indices=[0]),
            SideState(team=[dfn], active_indices=[0]),
        ))
        result = run_one_turn_cpp(battle, _MV0, _MV0, DET, DET)
        out_atk = result.sides[0].team[0]
        out_dfn = result.sides[1].team[0]
        dealt = dfn.hp - out_dfn.hp
        assert not out_dfn.fainted and dealt // 2 >= atk.max_hp // 8, (
            "test precondition: defender must survive and drain must exceed Rough Skin recoil"
        )
        assert out_atk.hp == atk.max_hp - atk.max_hp // 8, (
            "drain overheal is wasted at the cap; only the Rough Skin recoil (max_hp//8) "
            "should remain, leaving the holder below full HP"
        )
