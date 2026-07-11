# Tests for rich-log DAMAGE/HEAL event emissions added in the HP-event porting pass.
# Each test runs one full turn (both sides Splash) via run_with_capture and asserts the
# expected LogEvent.DAMAGE or LogEvent.HEAL event with correct amount and source string.
# Source strings map to SourceTag enums: RESIDUAL→"residual", ABILITY→"ability",
# ITEM→"item", MOVE→"move", RECOIL→"recoil".
import pytest

pytest.importorskip("nuzlocke_engine_cpp")

from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status
from liveplay.logger import LogEvent
from liveplay.rng import RNGEvent
from liveplay.state.battle import BattleState, WeatherEnum
from liveplay.state.pokemon import Volatile, VolatileEffect
from liveplay.state.side import SideState
from liveplay.sweep_driver import SideOverrides, SweepConfig, run_with_capture

from tests.state_builders import make_battle, make_mon, slot


# ---------------------------------------------------------------------------
# Luck config: deterministic roll, no crits, no secondaries.
# ---------------------------------------------------------------------------
_NO_LUCK = SideOverrides(roll=0.85, crit=False)
_CONFIG = SweepConfig(side0=_NO_LUCK, side1=_NO_LUCK)


def _run(state: BattleState):
    """Run one turn (Splash/Splash) and return the capturing logger."""
    _, capturing = run_with_capture(state, slot(0), slot(0), _CONFIG)
    return capturing


def _first_damage(capturing, species, source):
    """Return the first DAMAGE event for species with matching source."""
    for ev, kw in capturing.events:
        if ev == LogEvent.DAMAGE and kw.get("target") == species and kw.get("source") == source:
            return kw
    return None


def _first_heal(capturing, species, source):
    """Return the first HEAL event for species with matching source."""
    for ev, kw in capturing.events:
        if ev == LogEvent.HEAL and kw.get("target") == species and kw.get("source") == source:
            return kw
    return None


# ---------------------------------------------------------------------------
# 1. Burn residual DAMAGE(source="residual")
# ---------------------------------------------------------------------------

class TestBurnResidual:
    def test_burn_damage_event_fired(self):
        """Burn deals 1/16 max_hp per turn; event source should be 'residual'."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.SPLASH,), level=50,
                             status=Status.BURN)
        corsola = make_mon(Species.CORSOLA, moves=(Move.SPLASH,), level=50)
        state = make_battle(charizard, corsola)
        capturing = _run(state)
        ev = _first_damage(capturing, Species.CHARIZARD, "residual")
        assert ev is not None, "No residual DAMAGE event for burned Charizard"
        assert ev["amount"] > 0, "Burn damage amount must be positive"

    def test_burn_damage_no_move_source(self):
        """Burn damage must NOT appear with source='move' (purity check)."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.SPLASH,), level=50,
                             status=Status.BURN)
        corsola = make_mon(Species.CORSOLA, moves=(Move.SPLASH,), level=50)
        state = make_battle(charizard, corsola)
        capturing = _run(state)
        move_damages = [
            kw for ev, kw in capturing.events
            if ev == LogEvent.DAMAGE and kw.get("source") == "move"
        ]
        # Splash does no damage; no source="move" events expected
        assert move_damages == [], "Unexpected source='move' DAMAGE events from Splash+Burn turn"


# ---------------------------------------------------------------------------
# 2. Poison residual DAMAGE(source="residual")
# ---------------------------------------------------------------------------

class TestPoisonResidual:
    def test_poison_damage_event_fired(self):
        """Regular poison deals 1/8 max_hp per turn."""
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=50,
                             status=Status.POISON)
        corsola = make_mon(Species.CORSOLA, moves=(Move.SPLASH,), level=50)
        state = make_battle(bulbasaur, corsola)
        capturing = _run(state)
        ev = _first_damage(capturing, Species.BULBASAUR, "residual")
        assert ev is not None, "No residual DAMAGE event for poisoned Bulbasaur"
        assert ev["amount"] > 0


# ---------------------------------------------------------------------------
# 3. Leftovers HEAL(source="residual")
# ---------------------------------------------------------------------------

class TestLeftoversHeal:
    def test_leftovers_heal_event_fired(self):
        """Leftovers heals 1/16 max_hp per turn."""
        blissey = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50,
                           item=Item.LEFTOVERS, hp=100)
        corsola = make_mon(Species.CORSOLA, moves=(Move.SPLASH,), level=50)
        state = make_battle(blissey, corsola)
        capturing = _run(state)
        ev = _first_heal(capturing, Species.BLISSEY, "residual")
        assert ev is not None, "No residual HEAL event for Blissey with Leftovers"
        assert ev["amount"] > 0


# ---------------------------------------------------------------------------
# 4. Leech Seed: DAMAGE on seeded mon + HEAL on seeder (source="residual")
# ---------------------------------------------------------------------------

class TestLeechSeed:
    def _make_leech_seed_state(self):
        """Parasect (seeder, side1) with Leech Seed applied to Bulbasaur (side0)."""
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=50)
        # Bulbasaur has LEECH_SEEDED volatile
        bulbasaur = bulbasaur._replace(
            volatiles=int(Volatile.LEECH_SEEDED),
            timed_volatiles=[(VolatileEffect.LEECH_SEED_SOURCE_SLOT, 0)],
        )
        parasect = make_mon(Species.PARASECT, moves=(Move.SPLASH,), level=50, hp=1)
        return make_battle(bulbasaur, parasect)

    def test_leech_seed_damage_on_seeded(self):
        state = self._make_leech_seed_state()
        capturing = _run(state)
        ev = _first_damage(capturing, Species.BULBASAUR, "residual")
        assert ev is not None, "No DAMAGE event for Leech Seeded Bulbasaur"
        assert ev["amount"] > 0

    def test_leech_seed_heal_on_seeder(self):
        state = self._make_leech_seed_state()
        capturing = _run(state)
        ev = _first_heal(capturing, Species.PARASECT, "residual")
        assert ev is not None, "No HEAL event for Parasect (leech seed drain heal)"
        assert ev["amount"] > 0


# ---------------------------------------------------------------------------
# 5. Sandstorm weather DAMAGE(source="residual")
# ---------------------------------------------------------------------------

class TestSandstormDamage:
    @staticmethod
    def _sandstorm_battle(mon0, mon1) -> BattleState:
        """Build a battle with active sandstorm weather."""
        side0 = SideState(team=[mon0], active_indices=[0])
        side1 = SideState(team=[mon1], active_indices=[0])
        return BattleState(sides=(side0, side1), weather=WeatherEnum.SANDSTORM)

    def test_sandstorm_chips_normal_type(self):
        """Normal-type mon (Tauros) takes sandstorm chip."""
        tauros = make_mon(Species.TAUROS, moves=(Move.SPLASH,), level=50)
        corsola = make_mon(Species.CORSOLA, moves=(Move.SPLASH,), level=50)
        state = self._sandstorm_battle(tauros, corsola)
        capturing = _run(state)
        ev = _first_damage(capturing, Species.TAUROS, "residual")
        assert ev is not None, "No DAMAGE event for Tauros in sandstorm"
        assert ev["amount"] > 0

    def test_sandstorm_no_chip_on_rock_type(self):
        """Rock-type immune to sandstorm chip."""
        rhyhorn = make_mon(Species.RHYHORN, moves=(Move.SPLASH,), level=50)
        corsola = make_mon(Species.CORSOLA, moves=(Move.SPLASH,), level=50)
        state = self._sandstorm_battle(rhyhorn, corsola)
        capturing = _run(state)
        ev = _first_damage(capturing, Species.RHYHORN, "residual")
        assert ev is None, "Rhyhorn (Rock-type) should not take sandstorm chip"


# ---------------------------------------------------------------------------
# 6. Rough Skin recoil DAMAGE(source="ability")
# ---------------------------------------------------------------------------

class TestRoughSkinRecoil:
    def test_rough_skin_damages_attacker(self):
        """Tackle → Rough Skin holder damages the attacker."""
        carvanha = make_mon(Species.CARVANHA, moves=(Move.TACKLE,), level=50)
        garchomp = make_mon(Species.GARCHOMP, moves=(Move.SPLASH,), level=50,
                            ability=Ability.ROUGH_SKIN)
        state = make_battle(carvanha, garchomp)
        capturing = _run(state)
        ev = _first_damage(capturing, Species.CARVANHA, "ability")
        assert ev is not None, "No ABILITY DAMAGE event for Rough Skin recoil"
        assert ev["amount"] > 0


# ---------------------------------------------------------------------------
# 7. Rocky Helmet recoil DAMAGE(source="item")
# ---------------------------------------------------------------------------

class TestRockyHelmetRecoil:
    def test_rocky_helmet_damages_attacker(self):
        """Contact move → Rocky Helmet holder damages the attacker."""
        rattata = make_mon(Species.RATTATA, moves=(Move.TACKLE,), level=50)
        snorlax = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50,
                           item=Item.ROCKY_HELMET)
        state = make_battle(rattata, snorlax)
        capturing = _run(state)
        ev = _first_damage(capturing, Species.RATTATA, "item")
        assert ev is not None, "No ITEM DAMAGE event for Rocky Helmet recoil"
        assert ev["amount"] > 0


# ---------------------------------------------------------------------------
# 8. Crash damage (HJK miss) DAMAGE(source="recoil")
# ---------------------------------------------------------------------------

class TestCrashDamage:
    def test_hjk_miss_crash_damage(self):
        """High Jump Kick miss causes crash damage (1/2 max_hp)."""
        hitmonlee = make_mon(Species.HITMONLEE, moves=(Move.HIGH_JUMP_KICK,), level=50)
        corsola = make_mon(Species.CORSOLA, moves=(Move.SPLASH,), level=50)
        state = make_battle(hitmonlee, corsola)
        miss_config = SweepConfig(
            side0=SideOverrides(roll=0.85, crit=False, extra_overrides={RNGEvent.ACCURACY: False}),
            side1=_NO_LUCK,
        )
        _, capturing = run_with_capture(state, slot(0), slot(0), miss_config)
        ev = _first_damage(capturing, Species.HITMONLEE, "recoil")
        assert ev is not None, "No RECOIL DAMAGE event for HJK crash"
        assert ev["amount"] > 0


# ---------------------------------------------------------------------------
# 9. Drain heal HEAL(source="move") — Absorb
# ---------------------------------------------------------------------------

class TestDrainHeal:
    def test_drain_heal_event_fired(self):
        """Absorb drains HP from target; attacker should get HEAL(source='move')."""
        venusaur = make_mon(Species.VENUSAUR, moves=(Move.ABSORB,), level=50)
        blissey = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)
        venusaur = venusaur._replace(hp=1)  # start with low HP to ensure heal is gained
        state = make_battle(venusaur, blissey)
        config = SweepConfig(side0=SideOverrides(roll=0.85, crit=False), side1=_NO_LUCK)
        _, capturing = run_with_capture(state, slot(0), slot(0), config)
        ev = _first_heal(capturing, Species.VENUSAUR, "move")
        assert ev is not None, "No MOVE HEAL event for Absorb drain"
        assert ev["amount"] > 0


# ---------------------------------------------------------------------------
# 10. Liquid Ooze (Absorb into Liquid Ooze holder) DAMAGE(source="ability")
# ---------------------------------------------------------------------------

class TestLiquidOozeDrain:
    def test_liquid_ooze_damages_drainer(self):
        """Absorb vs Liquid Ooze holder damages the drainer instead of healing."""
        venusaur = make_mon(Species.VENUSAUR, moves=(Move.ABSORB,), level=50)
        tentacruel = make_mon(Species.TENTACRUEL, moves=(Move.SPLASH,), level=50,
                              ability=Ability.LIQUID_OOZE)
        state = make_battle(venusaur, tentacruel)
        config = SweepConfig(side0=SideOverrides(roll=0.85, crit=False), side1=_NO_LUCK)
        _, capturing = run_with_capture(state, slot(0), slot(0), config)
        ev = _first_damage(capturing, Species.VENUSAUR, "ability")
        assert ev is not None, "No ABILITY DAMAGE event for Liquid Ooze drain reversal"
        assert ev["amount"] > 0


# ---------------------------------------------------------------------------
# 11. Healing move HEAL(source="move") — Recover
# ---------------------------------------------------------------------------

class TestHealingMove:
    def test_recover_heal_event_fired(self):
        """Recover heals 1/2 max_hp; event source should be 'move'."""
        chansey = make_mon(Species.CHANSEY, moves=(Move.RECOVER,), level=50, hp=1)
        corsola = make_mon(Species.CORSOLA, moves=(Move.SPLASH,), level=50)
        state = make_battle(chansey, corsola)
        capturing = _run(state)
        ev = _first_heal(capturing, Species.CHANSEY, "move")
        assert ev is not None, "No MOVE HEAL event for Recover"
        assert ev["amount"] > 0


# ---------------------------------------------------------------------------
# 12. Shell Bell HEAL(source="item")
# ---------------------------------------------------------------------------

class TestShellBell:
    def test_shell_bell_heal_event_fired(self):
        """Shell Bell heals 1/8 of damage dealt; event source should be 'item'."""
        tauros = make_mon(Species.TAUROS, moves=(Move.TACKLE,), level=50,
                          item=Item.SHELL_BELL, hp=1)
        blissey = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)
        state = make_battle(tauros, blissey)
        config = SweepConfig(side0=SideOverrides(roll=0.85, crit=False), side1=_NO_LUCK)
        _, capturing = run_with_capture(state, slot(0), slot(0), config)
        ev = _first_heal(capturing, Species.TAUROS, "item")
        assert ev is not None, "No ITEM HEAL event for Shell Bell"
        assert ev["amount"] > 0
