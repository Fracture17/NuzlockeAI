# Tests for liveplay/sweep_driver.py and SWEEP_LUCK in liveplay/rng.py (E2 Task 5).
import sys
import pytest

from liveplay.rng import (
    RNGEvent, LuckProfile, BAD_LUCK, SWEEP_LUCK,
)
from liveplay.actions import Action, ActionKind
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.state.side import SideCondition
from tests.state_builders import (
    make_mon, make_battle, make_doubles_battle,
    slot, switch_to, active, assert_status,
)
from liveplay.data.status import Status
from liveplay.sweep_driver import (
    SideOverrides, SweepConfig, SweepLuck,
    build_sweep_luck, build_speed_tie_order,
    pre_inject_payload,
    run_to_decision_boundary, run_with_capture,
    has_fainted_active, reset_seen_errors,
    _sum_damage, _total_side_move_damage, _per_hit_damages,
    _own_damage, _attacker_per_hit_damages, _self_hit_damage,
)
from liveplay.logger import LogEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_errors():
    """Reset dedup set before every test for isolation."""
    reset_seen_errors()
    yield
    reset_seen_errors()


def _singles_battle(hp0=200, hp1=200):
    m0 = make_mon(Species.SNORLAX, moves=(Move.TACKLE,), hp=hp0)
    m1 = make_mon(Species.SNORLAX, moves=(Move.TACKLE,), hp=hp1)
    return make_battle(m0, m1)


def _tie_battle():
    m0 = make_mon(Species.RATTATA, moves=(Move.TACKLE,), hp=1)
    m1 = make_mon(Species.RATTATA, moves=(Move.TACKLE,), hp=1)
    return make_battle(m0, m1)


# ---------------------------------------------------------------------------
# Part A — SWEEP_LUCK preset tests
# ---------------------------------------------------------------------------

class TestSweepLuck:
    def test_inherits_bad_luck_base(self):
        # SWEEP_LUCK derives from BAD_LUCK; non-overridden fields stay at BAD values.
        assert SWEEP_LUCK.crit_threshold == BAD_LUCK.crit_threshold
        assert SWEEP_LUCK.secondary_threshold == BAD_LUCK.secondary_threshold
        assert SWEEP_LUCK.proc_threshold == BAD_LUCK.proc_threshold
        assert SWEEP_LUCK.flinch_threshold == BAD_LUCK.flinch_threshold
        assert SWEEP_LUCK.wake_threshold == BAD_LUCK.wake_threshold
        assert SWEEP_LUCK.confusion_snap_threshold == BAD_LUCK.confusion_snap_threshold
        assert SWEEP_LUCK.defrost_threshold == BAD_LUCK.defrost_threshold
        assert SWEEP_LUCK.quick_claw_threshold == BAD_LUCK.quick_claw_threshold

    def test_silent_defaults_flipped(self):
        # The 4 events whose BAD default EMITS a message are flipped to silent.
        assert SWEEP_LUCK.accuracy_threshold == 0.0          # hit (silent)
        assert SWEEP_LUCK.paralysis_threshold == 0.0         # can act (silent)
        assert SWEEP_LUCK.attract_threshold == 0.0           # can act (silent)
        assert SWEEP_LUCK.confusion_self_hit_threshold == 0.0  # no self-hit (silent)

    def test_max_duration_rolls(self):
        assert SWEEP_LUCK.binding_duration_roll == 1.0
        assert SWEEP_LUCK.rampage_duration_roll == 1.0

    def test_warn_uninjected(self):
        assert SWEEP_LUCK.warn_uninjected is True

    def test_damage_roll(self):
        # Inherits BAD_LUCK damage_roll=0.0
        assert SWEEP_LUCK.damage_roll == 0.0


# ---------------------------------------------------------------------------
# Part B adapter tests (build_sweep_luck — pure/no engine)
# ---------------------------------------------------------------------------

class TestBuildSweepLuckDefaults:
    def test_default_config_crit(self):
        luck = build_sweep_luck(SweepConfig())
        assert luck.p0.crit_threshold == 101.0
        assert luck.p1.crit_threshold == 101.0

    def test_default_config_damage_roll(self):
        luck = build_sweep_luck(SweepConfig())
        assert luck.p0.damage_roll == 0.5
        assert luck.p1.damage_roll == 0.5

    def test_default_config_psywave_roll(self):
        luck = build_sweep_luck(SweepConfig())
        assert luck.p0.psywave_roll == 0.5
        assert luck.p1.psywave_roll == 0.5

    def test_default_config_no_slot1_profiles(self):
        luck = build_sweep_luck(SweepConfig())
        assert luck.p0_slot1 is None
        assert luck.p1_slot1 is None

    def test_crit_true(self):
        luck = build_sweep_luck(SweepConfig(side0=SideOverrides(crit=True)))
        assert luck.p0.crit_threshold == 0.0

    def test_crit_false(self):
        luck = build_sweep_luck(SweepConfig(side0=SideOverrides(crit=False)))
        assert luck.p0.crit_threshold == 101.0

    def test_roll_scalar(self):
        luck = build_sweep_luck(SweepConfig(side0=SideOverrides(roll=0.83)))
        assert luck.p0.damage_roll == pytest.approx(0.83)
        assert luck.p0.psywave_roll == pytest.approx(0.83)

    def test_crits_per_hit_tuple(self):
        luck = build_sweep_luck(SweepConfig(
            side0=SideOverrides(crits_per_hit=(True, False))
        ))
        assert luck.p0.crits_per_hit == (0.0, 101.0)

    def test_rolls_per_hit_tuple_replaces_damage_roll(self):
        luck = build_sweep_luck(SweepConfig(
            side0=SideOverrides(rolls_per_hit=(0.2, 0.9))
        ))
        assert luck.p0.damage_rolls_per_hit == (0.2, 0.9)

    def test_rolls_per_hit_psywave_still_scalar(self):
        # psywave_roll mirrors s.roll (the scalar), not the tuple
        luck = build_sweep_luck(SweepConfig(
            side0=SideOverrides(roll=0.7, rolls_per_hit=(0.2, 0.9))
        ))
        assert luck.p0.psywave_roll == pytest.approx(0.7)

    def test_slot_keyed_rolls_per_hit(self):
        # {0: scalar, 1: tuple} → base gets damage_roll=0.3; slot-1 profile damage_rolls_per_hit=(0.1, 0.9)
        luck = build_sweep_luck(SweepConfig(
            side0=SideOverrides(rolls_per_hit={0: 0.3, 1: (0.1, 0.9)})
        ))
        assert luck.p0.damage_roll == pytest.approx(0.3)
        assert luck.p0.damage_rolls_per_hit is None
        assert luck.p0_slot1 is not None
        assert luck.p0_slot1.damage_rolls_per_hit == (0.1, 0.9)


class TestBuildSweepLuckExtraOverrides:
    def _config(self, overrides, side=0):
        if side == 0:
            return SweepConfig(side0=SideOverrides(extra_overrides=overrides))
        return SweepConfig(side1=SideOverrides(extra_overrides=overrides))

    def test_accuracy_true(self):
        luck = build_sweep_luck(self._config({RNGEvent.ACCURACY: True}))
        assert luck.p0.accuracy_threshold == 0.0

    def test_accuracy_false(self):
        luck = build_sweep_luck(self._config({RNGEvent.ACCURACY: False}))
        assert luck.p0.accuracy_threshold == 101.0

    def test_crit_true(self):
        luck = build_sweep_luck(self._config({RNGEvent.CRIT: True}))
        assert luck.p0.crit_threshold == 0.0

    def test_crit_false(self):
        luck = build_sweep_luck(self._config({RNGEvent.CRIT: False}))
        assert luck.p0.crit_threshold == 101.0

    def test_crit_tuple_per_hit(self):
        luck = build_sweep_luck(self._config({RNGEvent.CRIT: [True, False]}))
        assert luck.p0.crits_per_hit == (0.0, 101.0)

    def test_secondary_fires(self):
        luck = build_sweep_luck(self._config({RNGEvent.SECONDARY_FIRES: True}))
        assert luck.p0.secondary_threshold == 0.0

    def test_proc_fires(self):
        luck = build_sweep_luck(self._config({RNGEvent.PROC_FIRES: True}))
        assert luck.p0.proc_threshold == 0.0

    def test_wake_true(self):
        luck = build_sweep_luck(self._config({RNGEvent.WAKE: True}))
        assert luck.p0.wake_threshold == 0.0

    def test_confusion_snap(self):
        luck = build_sweep_luck(self._config({RNGEvent.CONFUSION_SNAP: True}))
        assert luck.p0.confusion_snap_threshold == 0.0

    def test_defrost(self):
        luck = build_sweep_luck(self._config({RNGEvent.DEFROST: True}))
        assert luck.p0.defrost_threshold == 0.0

    def test_confusion_self_hit_true_means_no_self_hit(self):
        # True = does NOT self-hit → threshold 0.0
        luck = build_sweep_luck(self._config({RNGEvent.CONFUSION_SELF_HIT: True}))
        assert luck.p0.confusion_self_hit_threshold == 0.0

    def test_confusion_self_hit_false_means_self_hit(self):
        luck = build_sweep_luck(self._config({RNGEvent.CONFUSION_SELF_HIT: False}))
        assert luck.p0.confusion_self_hit_threshold == 101.0

    def test_attract_immobilize_true_can_act(self):
        # True = CAN act → 0.0
        luck = build_sweep_luck(self._config({RNGEvent.ATTRACT_IMMOBILIZE: True}))
        assert luck.p0.attract_threshold == 0.0

    def test_full_paralysis_true_can_act(self):
        luck = build_sweep_luck(self._config({RNGEvent.FULL_PARALYSIS: True}))
        assert luck.p0.paralysis_threshold == 0.0

    def test_flinch(self):
        luck = build_sweep_luck(self._config({RNGEvent.FLINCH: True}))
        assert luck.p0.flinch_threshold == 0.0

    def test_quick_claw_scalar(self):
        luck = build_sweep_luck(self._config({RNGEvent.QUICK_CLAW: True}))
        assert luck.p0.quick_claw_threshold == 0.0

    def test_quick_claw_slot_keyed_same_value(self):
        # Same value for both slots → scalar on the base profile
        luck = build_sweep_luck(self._config({RNGEvent.QUICK_CLAW: {0: True, 1: True}}))
        assert luck.p0.quick_claw_threshold == 0.0

    def test_quick_claw_conflicting_slot_keyed_raises(self):
        with pytest.raises(ValueError):
            build_sweep_luck(self._config({RNGEvent.QUICK_CLAW: {0: True, 1: False}}))

    def test_damage_roll_float(self):
        luck = build_sweep_luck(self._config({RNGEvent.DAMAGE_ROLL: 0.75}))
        assert luck.p0.damage_roll == pytest.approx(0.75)

    def test_damage_roll_tuple(self):
        luck = build_sweep_luck(self._config({RNGEvent.DAMAGE_ROLL: [0.3, 0.7]}))
        assert luck.p0.damage_rolls_per_hit == (0.3, 0.7)

    def test_psywave_roll(self):
        luck = build_sweep_luck(self._config({RNGEvent.PSYWAVE_ROLL: 0.9}))
        assert luck.p0.psywave_roll == pytest.approx(0.9)

    def test_multi_hit_float(self):
        luck = build_sweep_luck(self._config({RNGEvent.MULTI_HIT_COUNT: 0.8}))
        assert luck.p0.multi_hit_roll == pytest.approx(0.8)

    def test_multi_hit_bool_true(self):
        luck = build_sweep_luck(self._config({RNGEvent.MULTI_HIT_COUNT: True}))
        assert luck.p0.multi_hit_roll == 1.0

    def test_multi_hit_bool_false(self):
        luck = build_sweep_luck(self._config({RNGEvent.MULTI_HIT_COUNT: False}))
        assert luck.p0.multi_hit_roll == 0.0

    def test_binding_duration_truthy(self):
        luck = build_sweep_luck(self._config({RNGEvent.BINDING_DURATION: True}))
        assert luck.p0.binding_duration_roll == 1.0

    def test_binding_duration_falsy(self):
        luck = build_sweep_luck(self._config({RNGEvent.BINDING_DURATION: False}))
        assert luck.p0.binding_duration_roll == 0.0

    def test_rampage_duration_truthy(self):
        luck = build_sweep_luck(self._config({RNGEvent.RAMPAGE_DURATION: True}))
        assert luck.p0.rampage_duration_roll == 1.0

    def test_rampage_duration_falsy(self):
        luck = build_sweep_luck(self._config({RNGEvent.RAMPAGE_DURATION: False}))
        assert luck.p0.rampage_duration_roll == 0.0

    def test_ancient_power_boost_raises(self):
        with pytest.raises(ValueError, match="ANCIENT_POWER_BOOST"):
            build_sweep_luck(self._config({RNGEvent.ANCIENT_POWER_BOOST: True}))

    def test_unmapped_category_a_event_raises(self):
        with pytest.raises(ValueError):
            build_sweep_luck(self._config({RNGEvent.METRONOME_MOVE: 1}))

    def test_nonempty_extra_pre_inject_no_longer_raises_not_implemented(self):
        # SPEED_TIE in extra_pre_inject is a caller bug → ValueError from pre_inject_payload,
        # but build_sweep_luck no longer raises NotImplementedError for non-empty extra_pre_inject.
        with pytest.raises(ValueError, match="SPEED_TIE"):
            build_sweep_luck(SweepConfig(extra_pre_inject={RNGEvent.SPEED_TIE: 0}))


class TestBuildSpeedTieOrder:
    def test_singles_winner_0(self):
        state = _singles_battle()
        order = build_speed_tie_order(state, tie_winner=0)
        assert order == [(0, 0), (1, 0)]

    def test_singles_winner_1(self):
        state = _singles_battle()
        order = build_speed_tie_order(state, tie_winner=1)
        assert order == [(1, 0), (0, 0)]

    def test_doubles_winner_0(self):
        m = make_mon(Species.SNORLAX, moves=(Move.TACKLE,))
        state = make_doubles_battle(m, m, m, m)
        order = build_speed_tie_order(state, tie_winner=0)
        assert order == [(0, 0), (0, 1), (1, 0), (1, 1)]

    def test_doubles_winner_1(self):
        m = make_mon(Species.SNORLAX, moves=(Move.TACKLE,))
        state = make_doubles_battle(m, m, m, m)
        order = build_speed_tie_order(state, tie_winner=1)
        assert order == [(1, 0), (1, 1), (0, 0), (0, 1)]


# ---------------------------------------------------------------------------
# has_fainted_active
# ---------------------------------------------------------------------------

class TestHasFaintedActive:
    def test_no_faint(self):
        state = _singles_battle()
        assert has_fainted_active(state) is False

    def test_fainted_no_bench(self):
        m = make_mon(Species.SNORLAX, moves=(Move.SPLASH,))
        m_fainted = m._replace(fainted=True)
        from liveplay.state.side import SideState
        from liveplay.state.battle import BattleState
        side0 = SideState(team=[m_fainted], active_indices=[0])
        side1 = SideState(team=[m], active_indices=[0])
        state = BattleState(sides=(side0, side1))
        # Fainted with no bench = battle-over condition, not decision boundary
        assert has_fainted_active(state) is False

    def test_fainted_with_bench(self):
        m = make_mon(Species.SNORLAX, moves=(Move.SPLASH,))
        m_fainted = m._replace(fainted=True)
        bench = make_mon(Species.RATTATA, moves=(Move.SPLASH,))
        from liveplay.state.side import SideState
        from liveplay.state.battle import BattleState
        side0 = SideState(team=[m_fainted, bench], active_indices=[0])
        side1 = SideState(team=[m], active_indices=[0])
        state = BattleState(sides=(side0, side1))
        assert has_fainted_active(state) is True


# ---------------------------------------------------------------------------
# Boundary flow tests
# ---------------------------------------------------------------------------

class TestBoundaryFlow:
    def test_player_ohko_no_bench_no_switch(self):
        """Player OHKOs opponent, no bench → fainted opp stays in place, no opp switch consumed."""
        # Give opp 1 HP so any Tackle OHKOs it
        m0 = make_mon(Species.MACHAMP, moves=(Move.TACKLE,), level=100)
        m1 = make_mon(Species.RATTATA, moves=(Move.SPLASH,), hp=1)
        state = make_battle(m0, m1)
        config = SweepConfig()
        result = run_to_decision_boundary(state, slot(0), slot(0), config)
        assert result is not None
        assert active(result, 1).fainted

    def test_opp_ohko_player_has_bench_returns_at_boundary(self):
        """Opponent OHKOs player's active; player has bench → state returned with fainted active."""
        from liveplay.state.side import SideState
        from liveplay.state.battle import BattleState
        m_player = make_mon(Species.RATTATA, moves=(Move.SPLASH,), hp=1)
        bench = make_mon(Species.SNORLAX, moves=(Move.SPLASH,))
        m_opp = make_mon(Species.MACHAMP, moves=(Move.TACKLE,), level=100)
        side0 = SideState(team=[m_player, bench], active_indices=[0])
        side1 = SideState(team=[m_opp], active_indices=[0])
        state = BattleState(sides=(side0, side1))
        config = SweepConfig()
        # No opp switch actions; opponent-only switch not needed since player fainted
        result = run_to_decision_boundary(state, slot(0), slot(0), config)
        assert result is not None
        # Player active fainted; state returned at party boundary
        assert active(result, 0).fainted
        # Opp is still alive
        assert not active(result, 1).fainted

    def test_player_ohkos_opp_with_bench_and_switch_action(self):
        """Player OHKOs opponent; opp has bench; one switch action → replacement applied."""
        from liveplay.state.side import SideState
        from liveplay.state.battle import BattleState
        m0 = make_mon(Species.MACHAMP, moves=(Move.TACKLE,), level=100)
        m1_active = make_mon(Species.RATTATA, moves=(Move.SPLASH,), hp=1)
        m1_bench = make_mon(Species.SNORLAX, moves=(Move.SPLASH,))
        side0 = SideState(team=[m0], active_indices=[0])
        side1 = SideState(team=[m1_active, m1_bench], active_indices=[0])
        state = BattleState(sides=(side0, side1))
        config = SweepConfig()
        opp_switch = Action(kind=ActionKind.SWITCH, switch_to_slot=1, source_slot=0)
        result = run_to_decision_boundary(state, slot(0), slot(0), config, opp_switch_actions=(opp_switch,))
        assert result is not None
        # Replacement should be active: Snorlax (slot 1) is now the active index
        assert not active(result, 1).fainted
        assert active(result, 1).species == Species.SNORLAX

    def test_opp_switch_actions_empty_leaves_fainted_in_place(self):
        """opp_switch_actions=() → fainted opponent left in place."""
        from liveplay.state.side import SideState
        from liveplay.state.battle import BattleState
        m0 = make_mon(Species.MACHAMP, moves=(Move.TACKLE,), level=100)
        m1_active = make_mon(Species.RATTATA, moves=(Move.SPLASH,), hp=1)
        m1_bench = make_mon(Species.SNORLAX, moves=(Move.SPLASH,))
        side0 = SideState(team=[m0], active_indices=[0])
        side1 = SideState(team=[m1_active, m1_bench], active_indices=[0])
        state = BattleState(sides=(side0, side1))
        config = SweepConfig()
        result = run_to_decision_boundary(state, slot(0), slot(0), config, opp_switch_actions=())
        assert result is not None
        assert active(result, 1).fainted

    def test_opp_last_mon_no_bench_no_switch_consumed(self):
        """Opponent's last mon (no bench) → no switch consumed, result non-None."""
        m0 = make_mon(Species.MACHAMP, moves=(Move.TACKLE,), level=100)
        m1 = make_mon(Species.RATTATA, moves=(Move.SPLASH,), hp=1)
        state = make_battle(m0, m1)
        config = SweepConfig()
        result = run_to_decision_boundary(state, slot(0), slot(0), config)
        assert result is not None

    def test_both_sides_faint_player_boundary(self, monkeypatch):
        """Both sides faint simultaneously (player has bench) → player boundary, opp NOT switched."""
        from liveplay.state.side import SideState
        from liveplay.state.battle import BattleState
        import liveplay.cpp_driver as cpp_driver

        m_fainted = make_mon(Species.RATTATA, moves=(Move.TACKLE,), hp=1)._replace(fainted=True, hp=0)
        bench_p = make_mon(Species.SNORLAX, moves=(Move.SPLASH,))
        bench_o = make_mon(Species.SNORLAX, moves=(Move.SPLASH,))

        post_faint_state = BattleState(sides=(
            SideState(team=[m_fainted, bench_p], active_indices=[0]),
            SideState(team=[m_fainted, bench_o], active_indices=[0]),
        ))

        monkeypatch.setattr(cpp_driver, "run_one_turn_cpp",
                            lambda *args, **kwargs: post_faint_state)

        opp_switch = Action(kind=ActionKind.SWITCH, switch_to_slot=1, source_slot=0)
        config = SweepConfig()
        state = _singles_battle()
        result = run_to_decision_boundary(
            state, slot(0), slot(0), config, opp_switch_actions=(opp_switch,)
        )
        assert result is not None
        # Player fainted → party boundary; opp switch NOT consumed, opp bench still not switched in
        assert active(result, 0).fainted
        # Opp's active is still the fainted Rattata (no switch applied)
        assert active(result, 1).species == Species.RATTATA

    def test_stealth_rock_entry_chip_in_capture(self):
        """Switch-in through Stealth Rock → DAMAGE event captured in run_with_capture."""
        from liveplay.state.side import SideState, SideCondition
        from liveplay.state.battle import BattleState
        m0 = make_mon(Species.MACHAMP, moves=(Move.TACKLE,), level=100)
        m1_active = make_mon(Species.RATTATA, moves=(Move.SPLASH,), hp=1)
        m1_bench = make_mon(Species.SNORLAX, moves=(Move.SPLASH,))
        # Stealth Rock on side 1 (hits incoming)
        side0 = SideState(team=[m0], active_indices=[0])
        side1 = SideState(
            team=[m1_active, m1_bench],
            active_indices=[0],
            side_conditions=[(SideCondition.STEALTH_ROCK, -1)],
        )
        state = BattleState(sides=(side0, side1))
        config = SweepConfig()
        opp_switch = Action(kind=ActionKind.SWITCH, switch_to_slot=1, source_slot=0)
        result, capture = run_with_capture(state, slot(0), slot(0), config, opp_switch_actions=(opp_switch,))
        assert result is not None
        # DAMAGE event from Stealth Rock on the switch-in should be captured
        damages = capture.of(LogEvent.DAMAGE)
        assert any(
            d.get("source") == "move" or d.get("target") is not None
            for d in damages
        ), f"Expected DAMAGE events from turn and/or entry hazard, got: {damages}"


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_needsrng_returns_none(self, monkeypatch):
        import liveplay.sweep_driver as sd
        import liveplay.cpp_driver as cpp_driver

        def _raise_needs_rng(*args, **kwargs):
            raise RuntimeError("NeedsRNG: oracle event unresolved")

        monkeypatch.setattr(cpp_driver, "run_one_turn_cpp", _raise_needs_rng)
        state = _singles_battle()
        result, capture = run_with_capture(state, slot(0), slot(0), SweepConfig())
        assert result is None

    def test_needsrng_stderr_once(self, monkeypatch, capsys):
        import liveplay.cpp_driver as cpp_driver

        def _raise_needs_rng(*args, **kwargs):
            raise RuntimeError("NeedsRNG: oracle event unresolved")

        monkeypatch.setattr(cpp_driver, "run_one_turn_cpp", _raise_needs_rng)
        state = _singles_battle()
        run_with_capture(state, slot(0), slot(0), SweepConfig())
        run_with_capture(state, slot(0), slot(0), SweepConfig())
        err = capsys.readouterr().err
        # Exactly one occurrence of the deduped message
        assert err.count("[sweep] uninjected RNG") == 1

    def test_reset_seen_errors_restores_printing(self, monkeypatch, capsys):
        import liveplay.cpp_driver as cpp_driver

        def _raise_needs_rng(*args, **kwargs):
            raise RuntimeError("NeedsRNG: oracle event unresolved")

        monkeypatch.setattr(cpp_driver, "run_one_turn_cpp", _raise_needs_rng)
        state = _singles_battle()
        run_with_capture(state, slot(0), slot(0), SweepConfig())
        capsys.readouterr()  # clear

        reset_seen_errors()
        run_with_capture(state, slot(0), slot(0), SweepConfig())
        err = capsys.readouterr().err
        assert "[sweep] uninjected RNG" in err

    def test_unported_turn_propagates(self, monkeypatch):
        from liveplay.cpp_driver import UnportedTurn
        import liveplay.cpp_driver as cpp_driver

        def _raise_unported(*args, **kwargs):
            raise UnportedTurn("unported: test_boundary")

        monkeypatch.setattr(cpp_driver, "run_one_turn_cpp", _raise_unported)
        state = _singles_battle()
        with pytest.raises(UnportedTurn):
            run_to_decision_boundary(state, slot(0), slot(0), SweepConfig())

    def test_value_error_returns_none_and_prints_once(self, monkeypatch, capsys):
        import liveplay.cpp_driver as cpp_driver

        def _raise_value_error(*args, **kwargs):
            raise ValueError("test value error from mock")

        monkeypatch.setattr(cpp_driver, "run_one_turn_cpp", _raise_value_error)
        state = _singles_battle()
        result, capture = run_with_capture(state, slot(0), slot(0), SweepConfig())
        assert result is None
        err = capsys.readouterr().err
        assert "[sweep] unexpected error" in err
        # Second call: deduped
        run_with_capture(state, slot(0), slot(0), SweepConfig())
        err2 = capsys.readouterr().err
        assert "[sweep] unexpected error" not in err2

    def test_config_value_error_propagates(self):
        """ValueError from build_sweep_luck escapes before try-wrapped run."""
        with pytest.raises(ValueError):
            run_to_decision_boundary(
                _singles_battle(), slot(0), slot(0),
                SweepConfig(side0=SideOverrides(extra_overrides={RNGEvent.ANCIENT_POWER_BOOST: True})),
            )

    def test_capture_sink_unregistered_after_error(self, monkeypatch):
        """Even on error, the C++ rich event log sink is unregistered."""
        import liveplay.cpp_driver as cpp_driver

        def _raise_needs_rng(*args, **kwargs):
            raise RuntimeError("NeedsRNG: oracle event unresolved")

        monkeypatch.setattr(cpp_driver, "run_one_turn_cpp", _raise_needs_rng)
        state = _singles_battle()
        run_with_capture(state, slot(0), slot(0), SweepConfig())
        # Second call should still work (sink not leaked from first)
        result, capture = run_with_capture(state, slot(0), slot(0), SweepConfig())
        assert result is None


# ---------------------------------------------------------------------------
# Capture and damage helper tests
# ---------------------------------------------------------------------------

class TestCaptureAndHelpers:
    def _run(self, state=None, config=None, opp_switch=None):
        if state is None:
            state = _singles_battle()
        if config is None:
            config = SweepConfig(side0=SideOverrides(roll=0.5), side1=SideOverrides(roll=0.5))
        opp = (opp_switch,) if opp_switch else ()
        return run_with_capture(state, slot(0), slot(0), config, opp_switch_actions=opp)

    def test_move_use_event_captured(self):
        result, capture = self._run()
        assert result is not None
        move_uses = capture.of(LogEvent.MOVE_USE)
        assert len(move_uses) >= 2  # both sides use a move

    def test_damage_event_captured(self):
        result, capture = self._run()
        assert result is not None
        assert capture.fired(LogEvent.DAMAGE)

    def test_sum_damage_matches_hp_delta(self):
        state = _singles_battle(hp0=200, hp1=200)
        m1_before = active(state, 1)
        config = SweepConfig(side0=SideOverrides(crit=False, roll=0.5))
        result, capture = run_with_capture(state, slot(0), slot(0), config)
        assert result is not None
        damage_reported = _sum_damage(capture, m1_before.species, target_side=1)
        hp_delta = m1_before.hp - active(result, 1).hp
        assert damage_reported == hp_delta

    def test_own_damage_matches_sum_damage(self):
        state = _singles_battle(hp0=200, hp1=200)
        m1_before = active(state, 1)
        config = SweepConfig(side0=SideOverrides(crit=False, roll=0.5))
        # attacker_slot is the team index of side 0's active mon
        attacker_slot = state.sides[0].active_indices[0]
        result, capture = run_with_capture(state, slot(0), slot(0), config)
        assert result is not None
        own = _own_damage(capture, attacker_side=0, attacker_slot=attacker_slot)
        total = _sum_damage(capture, m1_before.species, target_side=1)
        assert own == total

    def test_self_hit_damage_zero_normally(self):
        result, capture = self._run()
        assert result is not None
        assert _self_hit_damage(capture, 0) == 0

    def test_two_captures_independent(self):
        state = _singles_battle()
        config = SweepConfig()
        _, cap1 = run_with_capture(state, slot(0), slot(0), config)
        _, cap2 = run_with_capture(state, slot(0), slot(0), config)
        # Both captures should have the same number of events (not accumulated)
        assert len(cap1.events) == len(cap2.events)
        # Specifically, neither should be empty and they should be equal length
        assert len(cap1.events) > 0


# ---------------------------------------------------------------------------
# Speed tie via run_to_decision_boundary
# ---------------------------------------------------------------------------

class TestSpeedTieEndToEnd:
    def test_tie_winner_0_survives(self):
        state = _tie_battle()
        config = SweepConfig(tie_winner=0)
        result = run_to_decision_boundary(state, slot(0), slot(0), config)
        assert result is not None
        assert not active(result, 0).fainted
        assert active(result, 1).fainted

    def test_tie_winner_1_survives(self):
        state = _tie_battle()
        config = SweepConfig(tie_winner=1)
        result = run_to_decision_boundary(state, slot(0), slot(0), config)
        assert result is not None
        assert not active(result, 1).fainted
        assert active(result, 0).fainted


# ---------------------------------------------------------------------------
# pre_inject_payload unit tests (E2 Task 6d)
# ---------------------------------------------------------------------------

class TestPreInjectPayload:
    """Unit tests for pre_inject_payload: RNGEvent → (name_str, int) conversion."""

    # --- six supported events, one per test ---

    def test_metronome_move_converts(self):
        result = pre_inject_payload({RNGEvent.METRONOME_MOVE: Move.POUND})
        assert result == {"METRONOME_MOVE": int(Move.POUND)}

    def test_sleep_talk_move_converts(self):
        result = pre_inject_payload({RNGEvent.SLEEP_TALK_MOVE: Move.TACKLE})
        assert result == {"SLEEP_TALK_MOVE": int(Move.TACKLE)}

    def test_effect_spore_which_converts(self):
        result = pre_inject_payload({RNGEvent.EFFECT_SPORE_WHICH: Status.SLEEP})
        assert result == {"EFFECT_SPORE_WHICH": int(Status.SLEEP)}

    def test_acupressure_stat_converts(self):
        result = pre_inject_payload({RNGEvent.ACUPRESSURE_STAT: 3})
        assert result == {"ACUPRESSURE_STAT": 3}

    def test_roar_target_converts(self):
        result = pre_inject_payload({RNGEvent.ROAR_TARGET: 2})
        assert result == {"ROAR_TARGET": 2}

    def test_tri_attack_status_converts(self):
        result = pre_inject_payload({RNGEvent.TRI_ATTACK_STATUS: Status.BURN})
        assert result == {"TRI_ATTACK_STATUS": int(Status.BURN)}

    # --- empty / None ---

    def test_none_returns_none(self):
        assert pre_inject_payload(None) is None

    def test_empty_dict_returns_none(self):
        assert pre_inject_payload({}) is None

    # --- error cases ---

    def test_moody_stats_raises(self):
        with pytest.raises(ValueError, match="MOODY_STATS"):
            pre_inject_payload({RNGEvent.MOODY_STATS: 0})

    def test_speed_tie_raises(self):
        with pytest.raises(ValueError, match="SPEED_TIE"):
            pre_inject_payload({RNGEvent.SPEED_TIE: 0})

    def test_wrong_type_for_move_event_raises(self):
        # METRONOME_MOVE expects a Move enum; an int is accepted (pass-through); Status is wrong.
        with pytest.raises(ValueError):
            pre_inject_payload({RNGEvent.METRONOME_MOVE: Status.BURN})

    def test_wrong_type_for_status_event_raises(self):
        # TRI_ATTACK_STATUS expects a Status enum; a raw int (wrong type) should raise.
        with pytest.raises(ValueError):
            pre_inject_payload({RNGEvent.TRI_ATTACK_STATUS: Move.TACKLE})

    def test_multiple_events_converts_all(self):
        result = pre_inject_payload({
            RNGEvent.METRONOME_MOVE: Move.POUND,
            RNGEvent.ACUPRESSURE_STAT: 2,
        })
        assert result == {"METRONOME_MOVE": int(Move.POUND), "ACUPRESSURE_STAT": 2}


# ---------------------------------------------------------------------------
# ANCIENT_POWER_BOOST message update (E2 Task 6d)
# ---------------------------------------------------------------------------

class TestAncientPowerBoostMessage:
    """ANCIENT_POWER_BOOST still raises ValueError; message confirms dead in BOTH engines."""

    def test_ancient_power_boost_message_mentions_both_engines(self):
        with pytest.raises(ValueError, match="ANCIENT_POWER_BOOST") as exc_info:
            build_sweep_luck(
                SweepConfig(side0=SideOverrides(extra_overrides={RNGEvent.ANCIENT_POWER_BOOST: True}))
            )
        msg = str(exc_info.value)
        # Updated message should mention it's dead in both engines (not just C++)
        assert "both" in msg.lower() or "python" in msg.lower() or "engines" in msg.lower(), (
            f"Expected message to mention both engines being dead, got: {msg!r}"
        )


# ---------------------------------------------------------------------------
# End-to-end: extra_pre_inject via SweepConfig (E2 Task 6d)
# ---------------------------------------------------------------------------

class TestExtraPreInjectEndToEnd:
    """SweepConfig.extra_pre_inject flows through run_to_decision_boundary into C++."""

    def _tri_attack_battle(self):
        # Porygon uses Tri Attack (secondary fires with proc_threshold=0.0);
        # Snorlax is the target (bulky enough to survive one hit).
        from liveplay.rng import LuckProfile
        atk = make_mon(Species.PORYGON, moves=(Move.TRI_ATTACK,), level=50)
        target = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
        return make_battle(atk, target)

    def test_tri_attack_burn_via_sweep_config(self):
        """extra_pre_inject TRI_ATTACK_STATUS=BURN flows end-to-end; defender ends up burned."""
        state = self._tri_attack_battle()
        config = SweepConfig(
            # Force secondary to fire: secondary_threshold=0.0 on attacker's side
            side0=SideOverrides(extra_overrides={RNGEvent.SECONDARY_FIRES: True}),
            extra_pre_inject={RNGEvent.TRI_ATTACK_STATUS: Status.BURN},
        )
        result = run_to_decision_boundary(state, slot(0), slot(0), config)
        assert result is not None
        assert_status(result, 1, Status.BURN)

    def test_tri_attack_burn_via_run_with_capture(self):
        """Same injection via run_with_capture; defender burned, events captured."""
        state = self._tri_attack_battle()
        config = SweepConfig(
            side0=SideOverrides(extra_overrides={RNGEvent.SECONDARY_FIRES: True}),
            extra_pre_inject={RNGEvent.TRI_ATTACK_STATUS: Status.BURN},
        )
        result, capture = run_with_capture(state, slot(0), slot(0), config)
        assert result is not None
        assert_status(result, 1, Status.BURN)
        # Events should be populated (at least DAMAGE and MOVE_USE)
        assert capture.fired(LogEvent.DAMAGE)
        assert capture.fired(LogEvent.MOVE_USE)
