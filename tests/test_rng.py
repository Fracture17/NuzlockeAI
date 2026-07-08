"""Tests for the RNG control layer (LuckProfile).

Verifies:
- GOOD_LUCK, BAD_LUCK, AVERAGE_LUCK presets work correctly
- resolve_accuracy: hits when effective >= threshold, misses when below
- resolve_crit: crits when effective >= threshold, can't exceed ability caps
- resolve_secondary: fires when chance >= threshold
- resolve_damage_roll: returns correct value for 0.0/1.0/0.5 rolls
- resolve_multi_hit: returns correct hit count (round-half-up)
- resolve_speed_tie_between: higher luck_tier wins; player breaks equal-tier ties
- resolve_wake/confusion_snap/defrost: per-turn based on threshold
- resolve_confusion_self_hit/attract/paralysis: new per-turn checks
- random_mode: nondeterministic resolution via random.random()
- Effective values are always used (not base values)
- LuckGroup enum and luck_group_to_profile mapping
- RNGEvent enum members
"""
import pytest
from liveplay.rng import (
    LuckProfile,
    GOOD_LUCK, BAD_LUCK, AVERAGE_LUCK, STRICT_LUCK,
    UninjectedRNGError,
    resolve_accuracy, resolve_crit, resolve_secondary,
    resolve_damage_roll, resolve_multi_hit, resolve_speed_tie_between,
    resolve_wake, resolve_confusion_snap, resolve_defrost,
    resolve_binding_duration, resolve_rampage_duration,
    resolve_flinch, resolve_ancient_power_boost,
    resolve_confusion_self_hit, resolve_attract, resolve_paralysis,
    resolve_proc,
    LuckGroup, RNGEvent, luck_group_to_profile,
    _saturated,
    aggregate_uninjected_warnings,
)


class TestPresets:
    def test_good_luck_always_hits(self):
        assert resolve_accuracy(effective_accuracy=50, profile=GOOD_LUCK) is True

    def test_good_luck_always_crits(self):
        assert resolve_crit(effective_crit_chance=6.25, profile=GOOD_LUCK) is True

    def test_good_luck_max_damage(self):
        result = resolve_damage_roll(profile=GOOD_LUCK)
        assert result == 1.0  # max roll

    def test_good_luck_always_secondary(self):
        assert resolve_secondary(chance=10, profile=GOOD_LUCK) is True

    def test_good_luck_wins_speed_tie(self):
        # GOOD_LUCK (tier=2) beats AVERAGE_LUCK (tier=1)
        assert resolve_speed_tie_between(GOOD_LUCK, AVERAGE_LUCK, a_is_player=False) is True

    def test_good_luck_always_wakes(self):
        assert resolve_wake(wake_chance=33.0, profile=GOOD_LUCK) is True

    def test_good_luck_min_hits_is_max_hits(self):
        # multi-hit: max hits when roll=1.0 → 5 hits for 2-5 hit moves
        result = resolve_multi_hit(min_hits=2, max_hits=5, profile=GOOD_LUCK)
        assert result == 5

    def test_bad_luck_always_misses(self):
        # 95% accurate move still misses under BAD_LUCK (effective < 100% so LuckProfile applies)
        assert resolve_accuracy(effective_accuracy=95, profile=BAD_LUCK) is False

    def test_bad_luck_never_crits(self):
        # 12.5% crit chance (standard stage 1) — never crits under BAD_LUCK
        assert resolve_crit(effective_crit_chance=12.5, profile=BAD_LUCK) is False

    def test_bad_luck_min_damage(self):
        result = resolve_damage_roll(profile=BAD_LUCK)
        assert result == 0.0

    def test_bad_luck_never_secondary(self):
        # 30% secondary chance — never fires under BAD_LUCK
        assert resolve_secondary(chance=30, profile=BAD_LUCK) is False

    def test_bad_luck_loses_speed_tie(self):
        # BAD_LUCK (tier=0) loses to AVERAGE_LUCK (tier=1)
        assert resolve_speed_tie_between(BAD_LUCK, AVERAGE_LUCK, a_is_player=True) is False

    def test_bad_luck_never_wakes(self):
        # 33% wake chance — never wakes under BAD_LUCK
        assert resolve_wake(wake_chance=33.0, profile=BAD_LUCK) is False

    def test_bad_luck_min_hits(self):
        result = resolve_multi_hit(min_hits=2, max_hits=5, profile=BAD_LUCK)
        assert result == 2

    def test_average_luck_hits_at_50(self):
        assert resolve_accuracy(effective_accuracy=50, profile=AVERAGE_LUCK) is True

    def test_average_luck_misses_below_50(self):
        assert resolve_accuracy(effective_accuracy=49, profile=AVERAGE_LUCK) is False

    def test_average_luck_secondary_at_50(self):
        assert resolve_secondary(chance=50, profile=AVERAGE_LUCK) is True

    def test_average_luck_no_secondary_below_50(self):
        assert resolve_secondary(chance=49, profile=AVERAGE_LUCK) is False


class TestEffectiveValues:
    def test_100_accuracy_always_hits_even_bad_luck(self):
        """If effective accuracy is 100%, it always hits regardless of profile."""
        assert resolve_accuracy(effective_accuracy=100, profile=BAD_LUCK) is True

    def test_zero_accuracy_always_misses_even_good_luck(self):
        """If effective accuracy is 0% it never hits."""
        assert resolve_accuracy(effective_accuracy=0, profile=GOOD_LUCK) is False

    def test_crit_cap_respected(self):
        """If effective crit chance is 0% (ability blocks crits), never crits."""
        assert resolve_crit(effective_crit_chance=0.0, profile=GOOD_LUCK) is False

    def test_guaranteed_crit_always_crits(self):
        """If effective crit chance is 100%, always crits."""
        assert resolve_crit(effective_crit_chance=100.0, profile=BAD_LUCK) is True


class TestResolveAccuracy:
    def test_threshold_boundary_exact(self):
        profile = LuckProfile(accuracy_threshold=80.0)
        assert resolve_accuracy(80, profile) is True
        assert resolve_accuracy(79, profile) is False

    def test_never_miss_overrides(self):
        """accuracy=None (never-miss move) always hits."""
        profile = BAD_LUCK
        assert resolve_accuracy(None, profile) is True


class TestResolveCrit:
    def test_custom_threshold(self):
        profile = LuckProfile(crit_threshold=50.0)
        assert resolve_crit(50.0, profile) is True
        assert resolve_crit(49.9, profile) is False


class TestResolveDamageRoll:
    def test_custom_roll(self):
        profile = LuckProfile(damage_roll=0.5)
        result = resolve_damage_roll(profile)
        assert 0.0 <= result <= 1.0
        assert result == 0.5

    def test_roll_maps_to_range(self):
        """roll=0.0 → min factor (85/100), roll=1.0 → max factor (100/100)"""
        min_factor = resolve_damage_roll_as_factor(BAD_LUCK)
        max_factor = resolve_damage_roll_as_factor(GOOD_LUCK)
        assert abs(min_factor - 0.85) < 0.001
        assert abs(max_factor - 1.00) < 0.001


class TestResolveMultiHit:
    def test_bad_luck_always_min(self):
        assert resolve_multi_hit(2, 5, BAD_LUCK) == 2

    def test_good_luck_always_max(self):
        assert resolve_multi_hit(2, 5, GOOD_LUCK) == 5

    def test_fixed_hit_count_unchanged(self):
        """If min==max, always returns that value."""
        assert resolve_multi_hit(3, 3, BAD_LUCK) == 3
        assert resolve_multi_hit(3, 3, GOOD_LUCK) == 3


class TestResolveWake:
    def test_good_luck_always_wakes_at_any_chance(self):
        for chance in [1.0, 10.0, 33.0, 100.0]:
            assert resolve_wake(chance, GOOD_LUCK) is True

    def test_bad_luck_never_wakes(self):
        assert resolve_wake(33.0, BAD_LUCK) is False

    def test_average_luck_boundary(self):
        assert resolve_wake(50.0, AVERAGE_LUCK) is True
        assert resolve_wake(49.9, AVERAGE_LUCK) is False


class TestResolveConfusionSnap:
    def test_good_luck_snaps_immediately(self):
        assert resolve_confusion_snap(33.3, GOOD_LUCK) is True

    def test_bad_luck_never_snaps(self):
        assert resolve_confusion_snap(33.3, BAD_LUCK) is False


class TestResolveDefrost:
    def test_good_luck_always_thaws(self):
        assert resolve_defrost(20.0, GOOD_LUCK) is True

    def test_bad_luck_never_thaws(self):
        assert resolve_defrost(20.0, BAD_LUCK) is False


class TestResolveBindingDuration:
    def test_bad_luck_gives_min(self):
        assert resolve_binding_duration(BAD_LUCK) == 4

    def test_good_luck_gives_max(self):
        assert resolve_binding_duration(GOOD_LUCK) == 5


class TestResolveRampageDuration:
    def test_bad_luck_gives_min(self):
        assert resolve_rampage_duration(BAD_LUCK) == 2

    def test_good_luck_gives_max(self):
        assert resolve_rampage_duration(GOOD_LUCK) == 3


class TestResolveFlinch:
    def test_good_luck_always_flinches(self):
        assert resolve_flinch(10, GOOD_LUCK) is True

    def test_bad_luck_never_flinches(self):
        assert resolve_flinch(30, BAD_LUCK) is False


class TestResolveAncientPowerBoost:
    def test_good_luck_always_boosts(self):
        assert resolve_ancient_power_boost(10, GOOD_LUCK) is True

    def test_bad_luck_never_boosts(self):
        assert resolve_ancient_power_boost(10, BAD_LUCK) is False

    def test_strict_uninjected_raises(self):
        # Strict profile without ANCIENT_POWER_BOOST injected must raise for a probabilistic chance.
        with pytest.raises(UninjectedRNGError):
            resolve_ancient_power_boost(10, STRICT_LUCK)

    def test_strict_chance_100_does_not_raise(self):
        # Deterministic true (chance >= 100) bypasses strict check entirely.
        assert resolve_ancient_power_boost(100, STRICT_LUCK) is True

    def test_strict_chance_0_does_not_raise(self):
        # Deterministic false (chance <= 0) bypasses strict check entirely.
        assert resolve_ancient_power_boost(0, STRICT_LUCK) is False

    def test_strict_injected_resolves_normally(self):
        # With the event pre-injected, strict profile resolves using its threshold.
        injected_profile = LuckProfile(
            strict=True,
            injected=frozenset({RNGEvent.ANCIENT_POWER_BOOST}),
            ancient_power_boost_threshold=50.0,
        )
        assert resolve_ancient_power_boost(50, injected_profile) is True
        assert resolve_ancient_power_boost(49, injected_profile) is False


class TestLuckProfileConstruction:
    def test_custom_profile(self):
        profile = LuckProfile(
            accuracy_threshold=70.0,
            crit_threshold=100.1,
            secondary_threshold=100.1,
            damage_roll=0.0,
            multi_hit_roll=0.0,
            luck_tier=0,
            wake_threshold=100.1,
            confusion_snap_threshold=100.1,
            defrost_threshold=100.1,
            binding_duration_roll=0.0,
            rampage_duration_roll=0.0,
            flinch_threshold=100.1,
            ancient_power_boost_threshold=100.1,
        )
        assert resolve_accuracy(69, profile) is False
        assert resolve_accuracy(70, profile) is True
        assert resolve_crit(100.0, profile) is False


class TestMultiHitRoundHalfUp:
    def test_roll_half_two_to_three(self):
        profile = LuckProfile(multi_hit_roll=0.5)
        assert resolve_multi_hit(2, 3, profile) == 3  # 2 + floor(0.5*1 + 0.5) = 2 + floor(1.0) = 3

    def test_roll_half_two_to_five(self):
        # Gen 5+ weighted distribution: roll=0.5 falls in [0.35, 0.70) → 3 hits
        profile = LuckProfile(multi_hit_roll=0.5)
        assert resolve_multi_hit(2, 5, profile) == 3

    def test_roll_half_fixed(self):
        profile = LuckProfile(multi_hit_roll=0.5)
        assert resolve_multi_hit(3, 3, profile) == 3

    def test_roll_zero_always_min(self):
        profile = LuckProfile(multi_hit_roll=0.0)
        assert resolve_multi_hit(2, 5, profile) == 2

    def test_roll_one_always_max(self):
        profile = LuckProfile(multi_hit_roll=1.0)
        assert resolve_multi_hit(2, 5, profile) == 5


class TestSpeedTieBetween:
    def test_good_beats_average(self):
        # tier 2 > tier 1
        assert resolve_speed_tie_between(GOOD_LUCK, AVERAGE_LUCK, a_is_player=False) is True

    def test_average_beats_bad(self):
        # tier 1 > tier 0
        assert resolve_speed_tie_between(AVERAGE_LUCK, BAD_LUCK, a_is_player=False) is True

    def test_equal_tier_player_wins_as_a(self):
        assert resolve_speed_tie_between(GOOD_LUCK, GOOD_LUCK, a_is_player=True) is True

    def test_equal_tier_player_loses_as_b(self):
        assert resolve_speed_tie_between(BAD_LUCK, BAD_LUCK, a_is_player=False) is False

    def test_random_mode_produces_both_outcomes(self):
        random_profile = LuckProfile(random_mode=True)
        results = {resolve_speed_tie_between(random_profile, AVERAGE_LUCK, a_is_player=True) for _ in range(100)}
        assert True in results
        assert False in results


class TestRandomMode:
    def test_resolve_accuracy_nondeterministic(self):
        random_profile = LuckProfile(random_mode=True)
        results = {resolve_accuracy(50, random_profile) for _ in range(100)}
        assert True in results
        assert False in results


class TestNewResolvePresets:
    def test_good_luck_no_confusion_self_hit(self):
        # True = no self-hit (good outcome); GOOD_LUCK never self-hits
        assert resolve_confusion_self_hit(GOOD_LUCK) is True

    def test_bad_luck_always_confusion_self_hit(self):
        # False = self-hits; BAD_LUCK always self-hits
        assert resolve_confusion_self_hit(BAD_LUCK) is False

    def test_good_luck_no_attract(self):
        # True = can act (not immobilized); GOOD_LUCK never blocks
        assert resolve_attract(50.0, GOOD_LUCK) is True

    def test_bad_luck_always_attract(self):
        # False = cannot act (immobilized); BAD_LUCK always blocks
        assert resolve_attract(50.0, BAD_LUCK) is False

    def test_good_luck_no_paralysis(self):
        # True = can act; GOOD_LUCK never fully paralyzes
        assert resolve_paralysis(25.0, GOOD_LUCK) is True

    def test_bad_luck_always_paralysis(self):
        # False = cannot act; BAD_LUCK always fully paralyzes
        assert resolve_paralysis(25.0, BAD_LUCK) is False

    def test_zero_chance_never_fires(self):
        # 0% chance of bad = never blocked = True (can always act)
        assert resolve_attract(0, BAD_LUCK) is True
        assert resolve_paralysis(0, BAD_LUCK) is True

    def test_hundred_chance_always_fires(self):
        # 100% chance of bad = always blocked = False (cannot act)
        assert resolve_attract(100, GOOD_LUCK) is False
        assert resolve_paralysis(100, GOOD_LUCK) is False


# ── Part 3: new enum and function tests ────────────────────────────────────────

class TestLuckGroupEnum:
    def test_luck_group_has_four_members(self):
        members = list(LuckGroup)
        assert len(members) == 4

    def test_luck_group_good_exists(self):
        assert LuckGroup.GOOD is not None

    def test_luck_group_bad_exists(self):
        assert LuckGroup.BAD is not None

    def test_luck_group_average_exists(self):
        assert LuckGroup.AVERAGE is not None

    def test_luck_group_random_exists(self):
        assert LuckGroup.RANDOM is not None


class TestRNGEventEnum:
    def test_category_b_accuracy(self):
        assert hasattr(RNGEvent, 'ACCURACY')

    def test_category_b_crit(self):
        assert hasattr(RNGEvent, 'CRIT')

    def test_category_b_secondary_fires(self):
        assert hasattr(RNGEvent, 'SECONDARY_FIRES')

    def test_category_b_damage_roll(self):
        assert hasattr(RNGEvent, 'DAMAGE_ROLL')

    def test_category_b_wake(self):
        assert hasattr(RNGEvent, 'WAKE')

    def test_category_b_confusion_snap(self):
        assert hasattr(RNGEvent, 'CONFUSION_SNAP')

    def test_category_b_rampage_duration(self):
        assert hasattr(RNGEvent, 'RAMPAGE_DURATION')

    def test_category_a_action_select(self):
        assert hasattr(RNGEvent, 'ACTION_SELECT')

    def test_category_a_metronome_move(self):
        assert hasattr(RNGEvent, 'METRONOME_MOVE')

    def test_category_a_acupressure_stat(self):
        assert hasattr(RNGEvent, 'ACUPRESSURE_STAT')

    def test_category_a_roar_target(self):
        assert hasattr(RNGEvent, 'ROAR_TARGET')

    def test_category_a_moody_stats(self):
        assert hasattr(RNGEvent, 'MOODY_STATS')

    def test_category_a_starf_berry_stat(self):
        assert hasattr(RNGEvent, 'STARF_BERRY_STAT')


class TestLuckGroupToProfile:
    def test_good_maps_to_good_luck_accuracy(self):
        profile = luck_group_to_profile(LuckGroup.GOOD)
        assert profile.accuracy_threshold == 0.0

    def test_bad_maps_to_bad_luck_accuracy(self):
        profile = luck_group_to_profile(LuckGroup.BAD)
        assert profile.accuracy_threshold == 101.0

    def test_average_maps_to_average_luck_accuracy(self):
        profile = luck_group_to_profile(LuckGroup.AVERAGE)
        assert profile.accuracy_threshold == 50.0

    def test_random_maps_to_random_mode(self):
        profile = luck_group_to_profile(LuckGroup.RANDOM)
        assert profile.random_mode is True


class TestAverageLuckDamageRoll:
    def test_average_luck_damage_roll_is_max(self):
        assert AVERAGE_LUCK.damage_roll == 1.0


# ---------------------------------------------------------------------------
# Task 1: QUICK_CLAW RNGEvent + resolve_quick_claw
# ---------------------------------------------------------------------------

class TestQuickClawRNGEvent:
    def test_quick_claw_event_exists(self):
        assert hasattr(RNGEvent, 'QUICK_CLAW')

    def test_quick_claw_is_category_b(self):
        # Must be in the enum (verifying it's not accidentally in Category A)
        assert RNGEvent.QUICK_CLAW in list(RNGEvent)


class TestResolveQuickClaw:
    """resolve_quick_claw: 20% item proc — fires when quick_claw_threshold <= 20.0."""

    def test_good_luck_fires(self):
        # GOOD_LUCK quick_claw_threshold=0.0, 20 >= 0.0 → True
        from liveplay.rng import resolve_quick_claw
        assert resolve_quick_claw(GOOD_LUCK) is True

    def test_bad_luck_does_not_fire(self):
        # BAD_LUCK quick_claw_threshold=101.0, 20 >= 101.0 → False
        from liveplay.rng import resolve_quick_claw
        assert resolve_quick_claw(BAD_LUCK) is False

    def test_average_luck_does_not_fire(self):
        # AVERAGE_LUCK quick_claw_threshold=50.0, 50 > 20 → False
        from liveplay.rng import resolve_quick_claw
        assert resolve_quick_claw(AVERAGE_LUCK) is False

    def test_threshold_exactly_20_fires(self):
        from liveplay.rng import resolve_quick_claw
        profile = LuckProfile(quick_claw_threshold=20.0)
        assert resolve_quick_claw(profile) is True

    def test_threshold_above_20_does_not_fire(self):
        from liveplay.rng import resolve_quick_claw
        profile = LuckProfile(quick_claw_threshold=20.1)
        assert resolve_quick_claw(profile) is False

    def test_random_mode_produces_both_outcomes(self):
        from liveplay.rng import resolve_quick_claw
        random_profile = LuckProfile(random_mode=True)
        results = {resolve_quick_claw(random_profile) for _ in range(200)}
        assert True in results
        assert False in results

    def test_strict_uninjected_raises(self):
        from liveplay.rng import resolve_quick_claw
        with pytest.raises(UninjectedRNGError):
            resolve_quick_claw(STRICT_LUCK)

    def test_strict_injected_resolves(self):
        from liveplay.rng import resolve_quick_claw
        profile = LuckProfile(
            strict=True,
            injected=frozenset({RNGEvent.QUICK_CLAW}),
            quick_claw_threshold=20.0,
        )
        assert resolve_quick_claw(profile) is True

    def test_strict_injected_no_fire(self):
        from liveplay.rng import resolve_quick_claw
        profile = LuckProfile(
            strict=True,
            injected=frozenset({RNGEvent.QUICK_CLAW}),
            quick_claw_threshold=21.0,
        )
        assert resolve_quick_claw(profile) is False

    def test_parity_with_resolve_flinch_strict_behavior(self):
        """Strict-mode raise-on-uninjected parity with resolve_flinch."""
        from liveplay.rng import resolve_quick_claw
        # Neither flinch nor quick_claw injected under strict → both raise
        with pytest.raises(UninjectedRNGError) as exc_flinch:
            resolve_flinch(10, STRICT_LUCK)
        with pytest.raises(UninjectedRNGError) as exc_qc:
            resolve_quick_claw(STRICT_LUCK)
        assert exc_flinch.value.event == RNGEvent.FLINCH
        assert exc_qc.value.event == RNGEvent.QUICK_CLAW


class TestQuickClawPresets:
    def test_good_luck_has_threshold_0(self):
        assert GOOD_LUCK.quick_claw_threshold == 0.0

    def test_bad_luck_has_threshold_101(self):
        assert BAD_LUCK.quick_claw_threshold == 101.0

    def test_average_luck_has_threshold_50(self):
        assert AVERAGE_LUCK.quick_claw_threshold == 50.0


class TestResolveConfusionSelfHitNew:
    def test_good_luck_no_self_hit(self):
        # True = no self-hit (good outcome)
        assert resolve_confusion_self_hit(GOOD_LUCK) is True

    def test_bad_luck_self_hits(self):
        # False = self-hits
        assert resolve_confusion_self_hit(BAD_LUCK) is False

    def test_random_mode_returns_bool(self):
        random_profile = LuckProfile(random_mode=True)
        result = resolve_confusion_self_hit(random_profile)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# proc_threshold split (Stage 1)
# ---------------------------------------------------------------------------

class TestResolvePsywaveRoll:
    def test_good_luck_returns_max(self):
        from liveplay.rng import resolve_psywave_roll
        assert resolve_psywave_roll(GOOD_LUCK) == 1.0

    def test_bad_luck_returns_min(self):
        from liveplay.rng import resolve_psywave_roll
        assert resolve_psywave_roll(BAD_LUCK) == 0.0

    def test_average_luck_returns_midpoint(self):
        from liveplay.rng import resolve_psywave_roll
        assert resolve_psywave_roll(AVERAGE_LUCK) == 0.5

    def test_strict_uninjected_raises(self):
        from liveplay.rng import resolve_psywave_roll
        with pytest.raises(UninjectedRNGError):
            resolve_psywave_roll(STRICT_LUCK)

    def test_strict_injected_resolves_normally(self):
        from liveplay.rng import resolve_psywave_roll
        injected_profile = LuckProfile(
            strict=True,
            injected=frozenset({RNGEvent.PSYWAVE_ROLL}),
            psywave_roll=0.75,
        )
        assert resolve_psywave_roll(injected_profile) == 0.75


class TestProcThresholdSplit:
    def test_resolve_proc_uses_proc_threshold(self):
        """proc_threshold fires proc; secondary_threshold controls secondary independently."""
        from liveplay.rng import resolve_proc
        # proc fires (proc_threshold=0.0 → 30 >= 0.0 True), secondary does not (secondary_threshold=101.0)
        profile_proc_fires = LuckProfile(proc_threshold=0.0, secondary_threshold=101.0)
        assert resolve_proc(30, profile_proc_fires) is True
        assert resolve_secondary(30, profile_proc_fires) is False

        # proc does not fire (proc_threshold=101.0), secondary fires (secondary_threshold=0.0)
        profile_secondary_fires = LuckProfile(proc_threshold=101.0, secondary_threshold=0.0)
        assert resolve_proc(30, profile_secondary_fires) is False
        assert resolve_secondary(30, profile_secondary_fires) is True

    def test_presets_proc_matches_secondary(self):
        """Legacy equivalence: proc_threshold == secondary_threshold for all non-strict presets."""
        assert GOOD_LUCK.proc_threshold == GOOD_LUCK.secondary_threshold
        assert BAD_LUCK.proc_threshold == BAD_LUCK.secondary_threshold
        assert AVERAGE_LUCK.proc_threshold == AVERAGE_LUCK.secondary_threshold


# ---------------------------------------------------------------------------
# TestWarnProfile — warn_uninjected=True base behavior
# ---------------------------------------------------------------------------

import dataclasses
import logging


def _warn_empty(side=0):
    """BAD_LUCK with warn_uninjected=True and an empty injected set."""
    return dataclasses.replace(BAD_LUCK, warn_uninjected=True, injected=frozenset(), side=side)


def _warn_injected(*events, side=0):
    """BAD_LUCK with warn_uninjected=True and the given events pre-injected."""
    return dataclasses.replace(BAD_LUCK, warn_uninjected=True, injected=frozenset(events), side=side)


class TestWarnProfile:
    """warn_uninjected=True: un-injected Category-B events log WARNING and resolve via the
    profile's threshold default — including ACCURACY (the old special-case raise was removed
    when SWEEP_LUCK became a silent-default profile). Injected events and deterministic
    short-circuits are unaffected."""

    # --- resolve_proc ---

    def test_proc_uninjected_returns_bad_default(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = resolve_proc(30, _warn_empty())
        assert result is False

    def test_proc_uninjected_logs_one_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            resolve_proc(30, _warn_empty())
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "PROC_FIRES" in warnings[0].message

    def test_proc_uninjected_does_not_raise(self, caplog):
        with caplog.at_level(logging.WARNING):
            resolve_proc(30, _warn_empty())  # must not raise

    # --- resolve_secondary ---

    def test_secondary_uninjected_returns_bad_default(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = resolve_secondary(30, _warn_empty())
        assert result is False

    def test_secondary_uninjected_logs_one_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            resolve_secondary(30, _warn_empty())
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "SECONDARY_FIRES" in warnings[0].message

    # --- resolve_crit ---

    def test_crit_uninjected_returns_bad_default(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = resolve_crit(6.25, _warn_empty())
        assert result is False

    def test_crit_uninjected_logs_one_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            resolve_crit(6.25, _warn_empty())
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "CRIT" in warnings[0].message

    # --- injected event: no warning ---

    def test_proc_injected_no_warning(self, caplog):
        profile = _warn_injected(RNGEvent.PROC_FIRES)
        with caplog.at_level(logging.WARNING):
            result = resolve_proc(30, profile)
        assert result is False  # BAD threshold=101 → 30 < 101 → False
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 0

    # --- ACCURACY un-injected sub-100: logs and falls through to threshold (no raise) ---

    def test_accuracy_uninjected_warns_and_falls_through(self):
        # Old behavior raised here; now ACCURACY behaves like any other warn event.
        # _warn_empty uses BAD's accuracy_threshold=101 → 80 < 101 → miss (False).
        result = resolve_accuracy(80, _warn_empty())
        assert result is False

    def test_accuracy_uninjected_logs_one_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            resolve_accuracy(80, _warn_empty())
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "ACCURACY" in warnings[0].message

    # --- ACCURACY >=100 / None: short-circuit, no raise, no warning ---

    def test_accuracy_100_no_raise(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = resolve_accuracy(100, _warn_empty())
        assert result is True
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 0

    def test_accuracy_none_no_raise(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = resolve_accuracy(None, _warn_empty())
        assert result is True
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 0

    # --- ACCURACY injected: resolves by threshold, no raise, no warning ---

    def test_accuracy_injected_no_raise(self, caplog):
        profile = _warn_injected(RNGEvent.ACCURACY)
        with caplog.at_level(logging.WARNING):
            # BAD accuracy_threshold=101.0 → 80 < 101 → False (misses)
            result = resolve_accuracy(80, profile)
        assert result is False
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 0

    # --- deterministic short-circuits: no warning, no raise ---

    def test_proc_100_no_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = resolve_proc(100, _warn_empty())
        assert result is True
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 0

    def test_proc_0_no_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = resolve_proc(0, _warn_empty())
        assert result is False
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 0

    # --- REGRESSION: normal presets unaffected ---

    def test_bad_luck_proc_no_warning_no_raise(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = resolve_proc(30, BAD_LUCK)
        assert result is False
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 0

    def test_good_luck_proc_no_warning_no_raise(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = resolve_proc(30, GOOD_LUCK)
        assert result is True
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 0

    def test_average_luck_proc_no_warning_no_raise(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = resolve_proc(30, AVERAGE_LUCK)
        assert result is False
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 0

    def test_random_mode_proc_no_warning_no_raise(self, caplog):
        profile = LuckProfile(random_mode=True)
        with caplog.at_level(logging.WARNING):
            resolve_proc(30, profile)  # result is random; just must not warn/raise
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 0

    # --- REGRESSION: strict=True still RAISES for un-injected non-ACCURACY events ---

    def test_strict_proc_uninjected_raises(self):
        with pytest.raises(UninjectedRNGError):
            resolve_proc(30, STRICT_LUCK)

    def test_strict_crit_uninjected_raises(self):
        with pytest.raises(UninjectedRNGError):
            resolve_crit(6.25, STRICT_LUCK)

    def test_strict_secondary_uninjected_raises(self):
        with pytest.raises(UninjectedRNGError):
            resolve_secondary(30, STRICT_LUCK)

    # --- defrost warns under warn_uninjected (consolidation test) ---

    def test_defrost_uninjected_warns_not_raises(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = resolve_defrost(20.0, _warn_empty())
        assert result is False  # BAD defrost_threshold=101 → 20 < 101 → False
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warnings) == 1
        assert "DEFROST" in warnings[0].message

    def test_defrost_strict_still_raises(self):
        with pytest.raises(UninjectedRNGError):
            resolve_defrost(20.0, STRICT_LUCK)


class TestSaturated:
    """Unit tests for _saturated — the shared saturation short-circuit helper."""

    def test_high_chance_returns_high_param(self):
        assert _saturated(100, high=True, low=False) is True
        assert _saturated(100, high=False, low=True) is False

    def test_low_chance_returns_low_param(self):
        assert _saturated(0, high=True, low=False) is False
        assert _saturated(0, high=False, low=True) is True

    def test_above_100_boundary(self):
        assert _saturated(150, high=True, low=False) is True
        assert _saturated(150, high=False, low=True) is False


class TestUninjectedWarningAggregation:
    """aggregate_uninjected_warnings(): inside the context, each uninjected-event warning is
    counted by its exact rendered text (event + side) instead of logged immediately; on exit
    one WARNING per unique text is flushed with its occurrence count. Used by the sweep to
    collapse the hundreds of per-candidate re-simulation warnings from one decision boundary
    into a deduped summary. Outside the context, behavior is unchanged (immediate per-call)."""

    def _warns(self, caplog):
        return [r for r in caplog.records if r.levelno == logging.WARNING]

    def test_no_warnings_emitted_inside_context(self, caplog):
        # The per-event warnings are suppressed (buffered) while the context is open.
        with caplog.at_level(logging.WARNING):
            with aggregate_uninjected_warnings():
                resolve_proc(30, _warn_empty())
                resolve_proc(30, _warn_empty())
                assert len(self._warns(caplog)) == 0  # nothing logged yet

    def test_duplicate_event_collapses_to_one_warning_with_count(self, caplog):
        # 3 identical (event, side) consumes → one flushed WARNING tagged with the count.
        with caplog.at_level(logging.WARNING):
            with aggregate_uninjected_warnings():
                for _ in range(3):
                    resolve_proc(30, _warn_empty())
        warnings = self._warns(caplog)
        assert len(warnings) == 1
        assert "PROC_FIRES" in warnings[0].message
        assert "3" in warnings[0].message  # count present

    def test_distinct_events_each_get_their_own_summary(self, caplog):
        # Two different events → two unique summary lines, each with its own count.
        with caplog.at_level(logging.WARNING):
            with aggregate_uninjected_warnings():
                resolve_proc(30, _warn_empty())
                resolve_proc(30, _warn_empty())
                resolve_crit(6.25, _warn_empty())
        warnings = self._warns(caplog)
        assert len(warnings) == 2
        texts = [w.message for w in warnings]
        assert any("PROC_FIRES" in t and "2" in t for t in texts)
        assert any("CRIT" in t for t in texts)

    def test_same_event_different_side_are_distinct(self, caplog):
        # Strict-text dedup includes the side: side 0 and side 1 do not merge.
        with caplog.at_level(logging.WARNING):
            with aggregate_uninjected_warnings():
                resolve_proc(30, _warn_empty(side=0))
                resolve_proc(30, _warn_empty(side=1))
        warnings = self._warns(caplog)
        assert len(warnings) == 2
        assert any("side 0" in w.message for w in warnings)
        assert any("side 1" in w.message for w in warnings)

    def test_outside_context_logs_immediately(self, caplog):
        # No active aggregation → unchanged eager per-call WARNING behavior.
        with caplog.at_level(logging.WARNING):
            resolve_proc(30, _warn_empty())
            resolve_proc(30, _warn_empty())
        assert len(self._warns(caplog)) == 2

    def test_context_resets_between_calls(self, caplog):
        # A second context starts with a fresh counter (no leakage from the first).
        with caplog.at_level(logging.WARNING):
            with aggregate_uninjected_warnings():
                resolve_proc(30, _warn_empty())
            with aggregate_uninjected_warnings():
                resolve_proc(30, _warn_empty())
        warnings = self._warns(caplog)
        assert len(warnings) == 2  # one summary per context, not a running total

    def test_injected_event_still_silent_inside_context(self, caplog):
        # An injected event short-circuits before the warn path → nothing buffered or flushed.
        with caplog.at_level(logging.WARNING):
            with aggregate_uninjected_warnings():
                resolve_proc(30, _warn_injected(RNGEvent.PROC_FIRES))
        assert len(self._warns(caplog)) == 0

    def test_below_0_boundary(self):
        assert _saturated(-1, high=True, low=False) is False
        assert _saturated(-1, high=False, low=True) is True

    def test_in_between_returns_none(self):
        assert _saturated(50, high=True, low=False) is None
        assert _saturated(1, high=True, low=False) is None
        assert _saturated(99, high=False, low=True) is None

    def test_round_trip_shape_a_resolve_secondary(self):
        # Shape A: chance>=100 → True (always fires)
        assert resolve_secondary(100, GOOD_LUCK) is True
        assert resolve_secondary(100, BAD_LUCK) is True

    def test_round_trip_shape_a_resolve_secondary_zero(self):
        # Shape A: chance<=0 → False (never fires)
        assert resolve_secondary(0, GOOD_LUCK) is False
        assert resolve_secondary(0, BAD_LUCK) is False

    def test_round_trip_shape_b_resolve_attract(self):
        # Shape B: chance>=100 → False (always blocked, can't act)
        assert resolve_attract(100, GOOD_LUCK) is False
        assert resolve_attract(100, BAD_LUCK) is False

    def test_round_trip_shape_b_resolve_attract_zero(self):
        # Shape B: chance<=0 → True (never blocked, can always act)
        assert resolve_attract(0, GOOD_LUCK) is True
        assert resolve_attract(0, BAD_LUCK) is True


# ── helper ─────────────────────────────────────────────────────────────────────

def resolve_damage_roll_as_factor(profile: LuckProfile) -> float:
    """Convert damage_roll (0.0-1.0) to the actual multiplier (0.85-1.00)."""
    roll = resolve_damage_roll(profile)
    return 0.85 + roll * 0.15
