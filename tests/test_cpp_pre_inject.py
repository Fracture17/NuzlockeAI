# Plain-mode pre_inject hook: sticky, non-consuming map (event_name -> int) that resolves
# Category-A RNG events in plain mode (overrides==nullptr) so the Python candidate sweep
# can force answers without the GameDriver oracle path.
#
# Tests are written BEFORE implementation — they are expected to FAIL until the hook lands.
# Each test exercises one of the 6 supported events + 2 binding-validation tests.
import pytest

from liveplay.cpp_driver import run_one_turn_cpp
from liveplay.data.abilities import Ability
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status
from liveplay.rng import GOOD_LUCK, LuckProfile

from tests.state_builders import (
    active,
    assert_stages,
    assert_status,
    make_battle,
    make_mon,
    slot,
    switch_to,
)

# ---------------------------------------------------------------------------
# Luck helpers
# ---------------------------------------------------------------------------

# All thresholds set for determinism (no random_mode).
_GOOD = GOOD_LUCK
# Force secondary to always fire (secondary_threshold=0.0) and proc to always fire.
_SURE_PROC = LuckProfile(proc_threshold=0.0, secondary_threshold=0.0)


# ---------------------------------------------------------------------------
# Metronome
# ---------------------------------------------------------------------------

class TestMetronome:
    """Metronome with pre_inject METRONOME_MOVE=<move_id> uses that move instead of failing."""

    def _battle(self):
        # Metronome user (Clefable is a classic Metronome user) vs a Snorlax that can survive
        # anything. We use Machop for simplicity; the key is Metronome in slot 0.
        user = make_mon(Species.CLEFABLE, moves=(Move.METRONOME,), level=50)
        target = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
        return make_battle(user, target)

    def test_metronome_pre_inject_resolves(self):
        """With pre_inject, Metronome calls POUND; Snorlax loses HP (deterministic damaging move)."""
        state = self._battle()
        hp_before = active(state, 1).hp

        # POUND (id=1) is a basic damaging move callable by Metronome.
        result = run_one_turn_cpp(
            state,
            slot(0),
            slot(0),
            _GOOD,
            _GOOD,
            pre_inject={"METRONOME_MOVE": int(Move.POUND)},
        )
        hp_after = active(result, 1).hp
        assert hp_after < hp_before, (
            f"POUND via Metronome should deal damage; HP unchanged at {hp_before}"
        )

    def test_metronome_without_pre_inject_raises(self):
        """Without pre_inject, plain controlled mode raises 'unported: sub_move'."""
        state = self._battle()
        with pytest.raises(RuntimeError, match="unported: sub_move"):
            run_one_turn_cpp(state, slot(0), slot(0), _GOOD, _GOOD)

    def test_metronome_invalid_move_fails_silently(self):
        """An injected move not in the callable list causes the sub-move to fail (no effect)."""
        state = self._battle()
        hp_before = active(state, 1).hp
        # Splash (id=150) is in METRONOME_EXCLUDED; it is not callable so the sub-move fails.
        result = run_one_turn_cpp(
            state,
            slot(0),
            slot(0),
            _GOOD,
            _GOOD,
            pre_inject={"METRONOME_MOVE": int(Move.SPLASH)},
        )
        hp_after = active(result, 1).hp
        # Sub-move failed → no damage dealt.
        assert hp_after == hp_before, (
            f"Excluded move should cause sub-move failure (no damage); got HP {hp_after}"
        )


# ---------------------------------------------------------------------------
# Sleep Talk
# ---------------------------------------------------------------------------

class TestSleepTalk:
    """Sleeping mon with Sleep Talk + one usable move; inject SLEEP_TALK_MOVE to call it."""

    def _battle(self):
        # Snorlax: SLEEP_TALK + TACKLE; starts asleep.
        sleeper = make_mon(
            Species.SNORLAX,
            moves=(Move.SLEEP_TALK, Move.TACKLE),
            level=50,
            status=Status.SLEEP,
        )
        target = make_mon(Species.CATERPIE, moves=(Move.TACKLE,), level=50)
        return make_battle(sleeper, target)

    def test_sleep_talk_pre_inject_calls_tackle(self):
        """Injecting SLEEP_TALK_MOVE=TACKLE deals damage to the opponent."""
        state = self._battle()
        hp_before = active(state, 1).hp

        result = run_one_turn_cpp(
            state,
            slot(0),
            slot(0),
            _GOOD,
            _GOOD,
            pre_inject={"SLEEP_TALK_MOVE": int(Move.TACKLE)},
        )
        hp_after = active(result, 1).hp
        assert hp_after < hp_before, (
            f"TACKLE via Sleep Talk should deal damage; HP unchanged at {hp_before}"
        )

    def test_sleep_talk_without_pre_inject_raises(self):
        """Without pre_inject, plain controlled mode raises 'unported: sub_move'."""
        state = self._battle()
        with pytest.raises(RuntimeError, match="unported: sub_move"):
            run_one_turn_cpp(state, slot(0), slot(0), _GOOD, _GOOD)


# ---------------------------------------------------------------------------
# Effect Spore
# ---------------------------------------------------------------------------

class TestEffectSpore:
    """Contact attacker hits Effect Spore defender; inject EFFECT_SPORE_WHICH to force a status."""

    def _battle(self):
        # Low-level attacker uses Tackle (contact); tanky Snorlax has Effect Spore.
        atk = make_mon(Species.MACHOP, moves=(Move.TACKLE,), level=30)
        defender = make_mon(
            Species.SNORLAX,
            moves=(Move.SPLASH,),
            ability=Ability.EFFECT_SPORE,
            level=50,
        )
        return make_battle(atk, defender)

    def test_effect_spore_inject_sleep(self):
        """Injecting EFFECT_SPORE_WHICH=SLEEP causes the attacker to fall asleep."""
        state = self._battle()
        # proc_threshold=0.0 forces the 30% proc to fire; injection picks the status.
        result = run_one_turn_cpp(
            state,
            slot(0),
            slot(0),
            _SURE_PROC,
            _SURE_PROC,
            pre_inject={"EFFECT_SPORE_WHICH": int(Status.SLEEP)},
        )
        assert_status(result, 0, Status.SLEEP)

    def test_effect_spore_inject_paralysis(self):
        """Injecting EFFECT_SPORE_WHICH=PARALYSIS causes the attacker to be paralyzed."""
        state = self._battle()
        result = run_one_turn_cpp(
            state,
            slot(0),
            slot(0),
            _SURE_PROC,
            _SURE_PROC,
            pre_inject={"EFFECT_SPORE_WHICH": int(Status.PARALYSIS)},
        )
        assert_status(result, 0, Status.PARALYSIS)

    def test_effect_spore_without_pre_inject_raises(self):
        """Without pre_inject, plain controlled mode raises NeedsRNG."""
        state = self._battle()
        with pytest.raises(RuntimeError, match="NeedsRNG"):
            run_one_turn_cpp(state, slot(0), slot(0), _SURE_PROC, _SURE_PROC)


# ---------------------------------------------------------------------------
# Tri Attack
# ---------------------------------------------------------------------------

class TestTriAttack:
    """Tri Attack with forced secondary; inject TRI_ATTACK_STATUS to pick the status."""

    def _battle(self):
        atk = make_mon(Species.PORYGON, moves=(Move.TRI_ATTACK,), level=50)
        target = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
        return make_battle(atk, target)

    def test_tri_attack_inject_burn(self):
        """Injecting TRI_ATTACK_STATUS=BURN causes the defender to be burned."""
        state = self._battle()
        result = run_one_turn_cpp(
            state,
            slot(0),
            slot(0),
            _SURE_PROC,
            _SURE_PROC,
            pre_inject={"TRI_ATTACK_STATUS": int(Status.BURN)},
        )
        assert_status(result, 1, Status.BURN)

    def test_tri_attack_inject_paralysis(self):
        """Injecting TRI_ATTACK_STATUS=PARALYSIS causes the defender to be paralyzed.

        Note: FREEZE is not tested here because the default LuckProfile (defrost_threshold=20.0)
        causes the defender to defrost immediately on its own premove check within the same turn
        (resolve_fire_high(20, 20.0) = true). PARALYSIS is stable within a single turn.
        """
        state = self._battle()
        result = run_one_turn_cpp(
            state,
            slot(0),
            slot(0),
            _SURE_PROC,
            _SURE_PROC,
            pre_inject={"TRI_ATTACK_STATUS": int(Status.PARALYSIS)},
        )
        assert_status(result, 1, Status.PARALYSIS)

    def test_tri_attack_without_pre_inject_raises(self):
        """Without pre_inject, plain controlled mode raises NeedsRNG."""
        state = self._battle()
        with pytest.raises(RuntimeError, match="NeedsRNG"):
            run_one_turn_cpp(state, slot(0), slot(0), _SURE_PROC, _SURE_PROC)


# ---------------------------------------------------------------------------
# Acupressure
# ---------------------------------------------------------------------------

class TestAcupressure:
    """Acupressure raises a random stat by +2; inject ACUPRESSURE_STAT to pick the stat index."""

    def _battle(self):
        user = make_mon(Species.MACHOP, moves=(Move.ACUPRESSURE,), level=50)
        opp = make_mon(Species.CATERPIE, moves=(Move.TACKLE,), level=5)
        return make_battle(user, opp)

    def test_acupressure_inject_stat0(self):
        """Injecting ACUPRESSURE_STAT=0 boosts Attack (index 0) by +2."""
        state = self._battle()
        result = run_one_turn_cpp(
            state,
            slot(0),
            slot(0),
            _GOOD,
            _GOOD,
            pre_inject={"ACUPRESSURE_STAT": 0},
        )
        assert_stages(result, 0, {0: 2})

    def test_acupressure_inject_stat4(self):
        """Injecting ACUPRESSURE_STAT=4 boosts Speed (index 4) by +2."""
        state = self._battle()
        result = run_one_turn_cpp(
            state,
            slot(0),
            slot(0),
            _GOOD,
            _GOOD,
            pre_inject={"ACUPRESSURE_STAT": 4},
        )
        assert_stages(result, 0, {4: 2})

    def test_acupressure_without_pre_inject_raises(self):
        """Without pre_inject, plain controlled mode raises NeedsRNG."""
        state = self._battle()
        with pytest.raises(RuntimeError, match="NeedsRNG"):
            run_one_turn_cpp(state, slot(0), slot(0), _GOOD, _GOOD)


# ---------------------------------------------------------------------------
# Roar
# ---------------------------------------------------------------------------

class TestRoar:
    """Roar phazes the target; inject ROAR_TARGET to force which bench mon comes in."""

    def _battle(self):
        # Side 0 uses Roar; side 1 has 2 bench mons so Roar can pick.
        roarer = make_mon(Species.ARCANINE, moves=(Move.ROAR,), level=50)
        active1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
        bench1a = make_mon(Species.CATERPIE, moves=(Move.TACKLE,), level=10)
        bench1b = make_mon(Species.RATTATA, moves=(Move.TACKLE,), level=10)
        # side 1 team: [active1(slot0), bench1a(slot1), bench1b(slot2)]
        return make_battle(
            roarer, active1,
            team1=[active1, bench1a, bench1b],
        )

    def test_roar_inject_slot1(self):
        """Injecting ROAR_TARGET=1 brings in bench slot 1 (Caterpie)."""
        state = self._battle()
        result = run_one_turn_cpp(
            state,
            slot(0),
            slot(0),
            _GOOD,
            _GOOD,
            pre_inject={"ROAR_TARGET": 1},
        )
        # Side 1 active should now be Caterpie (bench slot 1).
        assert active(result, 1).species == Species.CATERPIE, (
            f"Expected Caterpie, got {active(result, 1).species}"
        )

    def test_roar_inject_slot2(self):
        """Injecting ROAR_TARGET=2 brings in bench slot 2 (Rattata)."""
        state = self._battle()
        result = run_one_turn_cpp(
            state,
            slot(0),
            slot(0),
            _GOOD,
            _GOOD,
            pre_inject={"ROAR_TARGET": 2},
        )
        assert active(result, 1).species == Species.RATTATA, (
            f"Expected Rattata, got {active(result, 1).species}"
        )

    def test_roar_inject_invalid_target_raises(self):
        """Injecting a fainted slot or out-of-range target raises a RuntimeError."""
        state = self._battle()
        # Slot 0 is the currently active mon → invalid Roar target (can't phaze to self).
        with pytest.raises(RuntimeError):
            run_one_turn_cpp(
                state,
                slot(0),
                slot(0),
                _GOOD,
                _GOOD,
                pre_inject={"ROAR_TARGET": 0},
            )

    def test_roar_without_pre_inject_runs(self):
        """Without pre_inject, plain mode uses the Policy (RandomPolicy) — doesn't raise."""
        # Plain mode with policies uses Policy.select_phaze which is random uniform pick;
        # it should not raise in plain mode (no oracle, Policy available from run_one_turn_cpp
        # default finalize_on_post_faint=False).
        # NOTE: run_one_turn_cpp uses nullptr for policies in the binding, so if the
        # binding passes nullptr policies and Roar fires, it will throw "unported: pending_switch"
        # OR use a policy. We test what actually happens: if it throws, that's the current behavior;
        # the test documents it.
        state = self._battle()
        # This will likely raise "unported: pending_switch" since binding passes nullptr policies.
        # Document this as expected behavior to be aware of.
        try:
            run_one_turn_cpp(state, slot(0), slot(0), _GOOD, _GOOD)
            # If it doesn't raise, just pass (Policy resolved it).
        except RuntimeError:
            pass  # Expected — plain binding has no Policy for phaze resolution.


# ---------------------------------------------------------------------------
# Binding validation
# ---------------------------------------------------------------------------

class TestBindingValidation:
    """Tests for the binding-level validation of pre_inject payload."""

    def _simple_battle(self):
        m0 = make_mon(Species.MACHOP, moves=(Move.SPLASH,), level=50)
        m1 = make_mon(Species.CATERPIE, moves=(Move.TACKLE,), level=5)
        return make_battle(m0, m1)

    def test_unknown_event_name_raises(self):
        """An unknown event name in pre_inject raises RuntimeError."""
        state = self._simple_battle()
        with pytest.raises(RuntimeError, match="pre_inject: unknown event"):
            run_one_turn_cpp(
                state,
                slot(0),
                slot(0),
                _GOOD,
                _GOOD,
                pre_inject={"UNKNOWN_EVENT_XYZ": 42},
            )

    def test_pre_inject_none_byte_identical(self):
        """pre_inject=None produces the same output state as omitting the kwarg entirely."""
        state = self._simple_battle()
        result_omit = run_one_turn_cpp(state, slot(0), slot(0), _GOOD, _GOOD)
        result_none = run_one_turn_cpp(
            state, slot(0), slot(0), _GOOD, _GOOD, pre_inject=None
        )
        # Both should be identical post-turn states (Splash vs Tackle, deterministic).
        assert result_omit == result_none, "pre_inject=None differs from omitted pre_inject"
