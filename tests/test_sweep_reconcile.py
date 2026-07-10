# Tests for liveplay/sweep_reconcile.py — written before implementation.
import dataclasses
import pytest

from liveplay.battle_types import ActionGroup, MatchResult
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status as StatusEnum
from liveplay.logger import CapturingLogger, LogEvent
from liveplay.state.pokemon import Volatile
from liveplay.engine_select import SimulationError

from tests.state_builders import (
    make_battle, make_mon, pdelta, odelta, CapturingLogger,
)

_AUTO_SIDE_HINT = object()


def _foe_prefix_hint(var_values):
    """Derive side_hint from var_values[0]'s 'Foe ' prefix, mirroring the real matcher."""
    if not var_values:
        return None
    first = str(var_values[0])
    first_word = first.split()[0].lower() if first.strip() else ""
    return 1 if first_word == "foe" else 0


def _mr(string_id, *, constant_name="", var_values=None, id_value=0, score=0,
        side_hint=_AUTO_SIDE_HINT, matched_text="", name_side_slots=None):
    """Build a MatchResult with optional side_hint derived from var_values Foe-prefix."""
    vals = var_values or []
    if side_hint is _AUTO_SIDE_HINT:
        side_hint = _foe_prefix_hint(vals)
    return MatchResult(
        string_id=string_id,
        id_value=id_value,
        constant_name=constant_name,
        var_values=vals,
        score=score,
        matched_text=matched_text,
        slot_labels=[],
        side_hint=side_hint,
        name_side_slots=name_side_slots or {},
    )


# ---------------------------------------------------------------------------
# TestHpToK
# ---------------------------------------------------------------------------

class TestHpToK:
    """_hp_to_k mirrors pokeemerald's bar-pixel formula: floor(hp*48/max_hp), min 1 if hp>0."""

    def test_full_bar(self):
        from liveplay.sweep_reconcile import _hp_to_k
        assert _hp_to_k(48, 48) == 48

    def test_zero_hp_is_zero(self):
        from liveplay.sweep_reconcile import _hp_to_k
        assert _hp_to_k(0, 48) == 0

    def test_min_one_pixel_when_alive(self):
        from liveplay.sweep_reconcile import _hp_to_k
        assert _hp_to_k(1, 600) == 1

    def test_half_resolution(self):
        from liveplay.sweep_reconcile import _hp_to_k
        assert _hp_to_k(81, 96) == 40
        assert _hp_to_k(80, 96) == 40
        assert _hp_to_k(82, 96) == 41


# ---------------------------------------------------------------------------
# TestHpCountDetail
# ---------------------------------------------------------------------------

class TestHpCountDetail:
    """_hp_count_detail reconstructs simulated HP trajectory and compares transition count."""

    def _state_with_player_hp(self, species, hp):
        mon = make_mon(species, moves=(Move.SPLASH,), hp=hp)
        opp = make_mon(Species.RAICHU, moves=(Move.SPLASH,))
        return make_battle(mon, opp)

    def _state_with_opp_hp(self, species, hp):
        player = make_mon(Species.RAICHU, moves=(Move.SPLASH,))
        opp = make_mon(species, moves=(Move.SPLASH,), hp=hp)
        return make_battle(player, opp)

    def test_player_single_transition_matches(self):
        from liveplay.sweep_reconcile import _hp_count_detail
        state = self._state_with_player_hp(Species.PIDGEY, hp=6)
        cap = CapturingLogger()
        cap.handle(LogEvent.DAMAGE, target=Species.PIDGEY, amount=4,
                   defender_side=0, source="move")
        record = pdelta(Species.PIDGEY, (10, 6), max_hp=28)
        ok, reason = _hp_count_detail(state, cap, [record])
        assert ok, reason

    def test_player_phantom_extra_tick_fails(self):
        from liveplay.sweep_reconcile import _hp_count_detail
        state = self._state_with_player_hp(Species.PIDGEY, hp=3)
        cap = CapturingLogger()
        cap.handle(LogEvent.DAMAGE, target=Species.PIDGEY, amount=4,
                   defender_side=0, source="move")
        cap.handle(LogEvent.DAMAGE, target=Species.PIDGEY, amount=3,
                   source="residual_bound")
        record = pdelta(Species.PIDGEY, (10, 6), max_hp=28)
        ok, reason = _hp_count_detail(state, cap, [record])
        assert not ok
        assert "count" in reason.lower()
        assert "PIDGEY" in reason

    def test_player_two_observed_two_sim_matches(self):
        from liveplay.sweep_reconcile import _hp_count_detail
        state = self._state_with_player_hp(Species.PIDGEY, hp=3)
        cap = CapturingLogger()
        cap.handle(LogEvent.DAMAGE, target=Species.PIDGEY, amount=4,
                   defender_side=0, source="move")
        cap.handle(LogEvent.DAMAGE, target=Species.PIDGEY, amount=3,
                   source="residual_status")
        record = pdelta(Species.PIDGEY, (10, 6), (6, 3), max_hp=28)
        ok, reason = _hp_count_detail(state, cap, [record])
        assert ok, reason

    def test_player_no_change_no_events_matches(self):
        from liveplay.sweep_reconcile import _hp_count_detail
        state = self._state_with_player_hp(Species.PIDGEY, hp=10)
        cap = CapturingLogger()
        record = pdelta(Species.PIDGEY, (10, 10), max_hp=28)
        ok, reason = _hp_count_detail(state, cap, [record])
        assert ok, reason

    def test_player_heal_counts_as_transition(self):
        from liveplay.sweep_reconcile import _hp_count_detail
        state = self._state_with_player_hp(Species.PIDGEY, hp=30)
        cap = CapturingLogger()
        cap.handle(LogEvent.DAMAGE, target=Species.PIDGEY, amount=4,
                   defender_side=0, source="move")
        cap.handle(LogEvent.HEAL, target=Species.PIDGEY, amount=10, side=0,
                   source="berry")
        record = pdelta(Species.PIDGEY, (24, 20), (20, 30), max_hp=40)
        ok, reason = _hp_count_detail(state, cap, [record])
        assert ok, reason

    def test_opp_single_pixel_transition_matches(self):
        from liveplay.sweep_reconcile import _hp_count_detail
        state = self._state_with_opp_hp(Species.TENTACRUEL, hp=40)
        cap = CapturingLogger()
        cap.handle(LogEvent.DAMAGE, target=Species.TENTACRUEL, amount=8,
                   defender_side=1, source="move")
        record = odelta(Species.TENTACRUEL, (48, 40), max_hp=48)
        ok, reason = _hp_count_detail(state, cap, [record])
        assert ok, reason

    def test_opp_subpixel_tick_absorbed(self):
        from liveplay.sweep_reconcile import _hp_count_detail
        state = self._state_with_opp_hp(Species.TENTACRUEL, hp=80)
        cap = CapturingLogger()
        cap.handle(LogEvent.DAMAGE, target=Species.TENTACRUEL, amount=8,
                   defender_side=1, source="move")
        cap.handle(LogEvent.DAMAGE, target=Species.TENTACRUEL, amount=1,
                   source="residual_status")
        record = odelta(Species.TENTACRUEL, (44, 40), max_hp=96)
        ok, reason = _hp_count_detail(state, cap, [record])
        assert ok, reason

    def test_opp_two_visible_ticks_fail_when_one_observed(self):
        from liveplay.sweep_reconcile import _hp_count_detail
        state = self._state_with_opp_hp(Species.TENTACRUEL, hp=72)
        cap = CapturingLogger()
        cap.handle(LogEvent.DAMAGE, target=Species.TENTACRUEL, amount=8,
                   defender_side=1, source="move")
        cap.handle(LogEvent.DAMAGE, target=Species.TENTACRUEL, amount=8,
                   source="residual_bound")
        record = odelta(Species.TENTACRUEL, (44, 36), max_hp=96)
        ok, reason = _hp_count_detail(state, cap, [record])
        assert not ok
        assert "count" in reason.lower()

    def test_empty_deltas_skipped(self):
        from liveplay.sweep_reconcile import _hp_count_detail
        state = self._state_with_player_hp(Species.PIDGEY, hp=10)
        cap = CapturingLogger()
        record = pdelta(Species.PIDGEY, max_hp=28)
        ok, reason = _hp_count_detail(state, cap, [record])
        assert ok and reason is None

    def test_check_hp_count_wrapper_returns_bool(self):
        from liveplay.sweep_reconcile import _check_hp_count
        state = self._state_with_player_hp(Species.PIDGEY, hp=3)
        cap = CapturingLogger()
        cap.handle(LogEvent.DAMAGE, target=Species.PIDGEY, amount=4,
                   defender_side=0, source="move")
        cap.handle(LogEvent.DAMAGE, target=Species.PIDGEY, amount=3,
                   source="residual_bound")
        record = pdelta(Species.PIDGEY, (10, 6), max_hp=28)
        assert _check_hp_count(state, cap, [record]) is False


# ---------------------------------------------------------------------------
# TestActionOrderCheck
# ---------------------------------------------------------------------------

class TestActionOrderCheck:
    """_check_action_order: observed move order must be a prefix of sim's MOVE_USE order."""

    def test_correct_order_passes(self):
        from liveplay.sweep_reconcile import _check_action_order
        cap = CapturingLogger()
        cap.handle(LogEvent.MOVE_USE, user=Species.ELECTRODE, move=Move.SPLASH, side=1)
        cap.handle(LogEvent.MOVE_USE, user=Species.SLOWPOKE, move=Move.SPLASH, side=0)
        assert _check_action_order(cap, [1, 0]) is True

    def test_wrong_order_fails(self):
        from liveplay.sweep_reconcile import _check_action_order
        cap = CapturingLogger()
        cap.handle(LogEvent.MOVE_USE, user=Species.SLOWPOKE, move=Move.SPLASH, side=0)
        cap.handle(LogEvent.MOVE_USE, user=Species.ELECTRODE, move=Move.SPLASH, side=1)
        # observed says side 1 goes first, but sim has side 0 first
        assert _check_action_order(cap, [1, 0]) is False

    def test_empty_observed_passes(self):
        from liveplay.sweep_reconcile import _check_action_order
        cap = CapturingLogger()
        assert _check_action_order(cap, []) is True

    def test_sim_fewer_moves_than_observed_fails(self):
        from liveplay.sweep_reconcile import _check_action_order
        cap = CapturingLogger()
        cap.handle(LogEvent.MOVE_USE, user=Species.ELECTRODE, move=Move.SPLASH, side=1)
        # observed expects [1, 0] but sim only has one MOVE_USE
        assert _check_action_order(cap, [1, 0]) is False


# ---------------------------------------------------------------------------
# TestEmptyHpDeltasSkipCheck
# ---------------------------------------------------------------------------

class TestEmptyHpDeltasSkipCheck:
    """With empty HP deltas and None opp_species, the no-damage check is skipped."""

    def test_no_damage_events_empty_deltas_passes(self):
        from liveplay.sweep_reconcile import check_log_events
        cap = CapturingLogger()
        assert check_log_events(cap, [], [], None) is True

    def test_damage_events_but_none_opp_species_passes(self):
        from liveplay.sweep_reconcile import check_log_events
        cap = CapturingLogger()
        cap.handle(LogEvent.DAMAGE, target=Species.BULBASAUR, amount=20,
                   source="move", defender_side=1)
        # When opp_species is None, the no-damage constraint is skipped
        assert check_log_events(cap, [], [], None) is True


# ---------------------------------------------------------------------------
# TestMirrorMatchNoDamageCheck
# ---------------------------------------------------------------------------

class TestMirrorMatchNoDamageCheck:
    """No-damage check must be side-aware; foe hitting player must not count as opp damage."""

    def _make_foe_move_no_player_hp(self, foe_species, player_species):
        """Cap with foe hitting player only (damage on defender_side=0)."""
        cap = CapturingLogger()
        cap.handle(LogEvent.MOVE_USE, user=foe_species, move=Move.TACKLE, side=1)
        cap.handle(LogEvent.DAMAGE, target=player_species, amount=30,
                   source="move", defender_side=0)
        return cap

    def test_mirror_foe_hit_player_no_opp_damage_passes(self):
        from liveplay.sweep_reconcile import check_log_events
        # Same species on both sides; foe used Tackle on player (defender_side=0).
        # opponent_hp_deltas=[] with opp_species known → sum of defender_side=1 damage must be 0.
        cap = self._make_foe_move_no_player_hp(Species.PIDGEY, Species.PIDGEY)
        # Opponent hp deltas is empty but opp_species is set → check defender_side=1 sum only
        assert check_log_events(cap, [], [], Species.PIDGEY) is True

    def test_sim_damage_to_opp_when_empty_deltas_fails(self):
        from liveplay.sweep_reconcile import check_log_events
        cap = CapturingLogger()
        cap.handle(LogEvent.DAMAGE, target=Species.PIDGEY, amount=30,
                   source="move", defender_side=1)
        # No deltas but opp_species known + actual defender_side=1 damage → fails
        assert check_log_events(cap, [], [], Species.PIDGEY) is False


# ---------------------------------------------------------------------------
# TestLogEventFilter
# ---------------------------------------------------------------------------

class TestLogEventFilter:
    """check_log_events presence constraints for common message IDs."""

    def _make_crit_message(self):
        return _mr("STRINGID_CRITICALHIT")

    def test_crit_message_requires_crit_log_pass(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.CRIT)
        messages = [self._make_crit_message()]
        assert check_log_events(capturing, messages, [], None) is True

    def test_crit_message_requires_crit_log_fail(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        messages = [self._make_crit_message()]
        assert check_log_events(capturing, messages, [], None) is False


# ---------------------------------------------------------------------------
# TestHitCountMirrorMatch
# ---------------------------------------------------------------------------

class TestHitCountMirrorMatch:
    """HITXTIMES must isolate the attacker's SIDE to avoid conflating mirror-match hits."""

    def _usedmove(self, attacker_name, move_name, *, foe):
        prefix = "Foe " if foe else ""
        return MatchResult(
            string_id="STRINGID_USEDMOVE",
            id_value=0,
            constant_name="sText_AttackerUsedMove",
            var_values=[attacker_name, move_name],
            score=0,
            matched_text=f"{prefix}{attacker_name} used {move_name}!",
            slot_labels=[],
            side_hint=1 if foe else 0,
            name_side_slots={},
        )

    def _messages(self, expected_hits):
        return [
            self._usedmove("Exeggcute", "Confusion", foe=False),
            self._usedmove("Exeggcute", "Bullet Seed", foe=True),
            _mr("STRINGID_HITXTIMES", var_values=[str(expected_hits)]),
        ]

    def test_mirror_multihit_counts_only_attacker_side(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.HITCOUNT, user=Species.EXEGGCUTE, side=0)
        capturing.handle(LogEvent.HITCOUNT, user=Species.EXEGGCUTE, side=1)
        capturing.handle(LogEvent.HITCOUNT, user=Species.EXEGGCUTE, side=1)
        assert check_log_events(capturing, self._messages(2), [], None) is True

    def test_mirror_multihit_wrong_side_count_fails(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.HITCOUNT, user=Species.EXEGGCUTE, side=0)
        capturing.handle(LogEvent.HITCOUNT, user=Species.EXEGGCUTE, side=1)
        capturing.handle(LogEvent.HITCOUNT, user=Species.EXEGGCUTE, side=1)
        capturing.handle(LogEvent.HITCOUNT, user=Species.EXEGGCUTE, side=1)
        assert check_log_events(capturing, self._messages(2), [], None) is False


# ---------------------------------------------------------------------------
# TestApplyObservedLevelups
# ---------------------------------------------------------------------------

class TestApplyObservedLevelups:
    """_apply_observed_levelups forces player mons to observed level in-place."""

    def _grew(self, name, level):
        return _mr("STRINGID_PKMNGREWTOLV", var_values=[name, str(level)])

    def test_benched_mon_forced_to_observed_level(self):
        from liveplay.sweep_reconcile import _apply_observed_levelups
        active = make_mon(Species.PIKACHU)
        skitty = make_mon(Species.SKITTY, level=7)._replace(exp=337)
        state = make_battle(active, make_mon(Species.RATTATA),
                            team0=[active, skitty])
        old_max_hp = state.sides[0].team[1].max_hp

        _apply_observed_levelups(state, [self._grew("SKITTY", 8)])

        leveled = state.sides[0].team[1]
        assert leveled.level == 8
        from liveplay.data.species import SPECIES_DATA
        from liveplay.data.growth_rate import exp_for_level
        assert leveled.exp >= exp_for_level(SPECIES_DATA[Species.SKITTY].growth_rate, 8)
        assert leveled.max_hp > old_max_hp

    def test_already_correct_mon_untouched(self):
        from liveplay.sweep_reconcile import _apply_observed_levelups
        active = make_mon(Species.PIKACHU)
        skitty = make_mon(Species.SKITTY, level=8)
        state = make_battle(active, make_mon(Species.RATTATA),
                            team0=[active, skitty])
        before = state.sides[0].team[1]

        _apply_observed_levelups(state, [self._grew("SKITTY", 8)])

        assert state.sides[0].team[1] is before

    def test_no_levelup_messages_is_noop(self):
        from liveplay.sweep_reconcile import _apply_observed_levelups
        active = make_mon(Species.PIKACHU)
        state = make_battle(active, make_mon(Species.RATTATA))
        before = state.sides[0].team[0]

        _apply_observed_levelups(state, [])

        assert state.sides[0].team[0] is before

    def test_levelup_hp_bump_must_be_applied_after_hp_validation(self):
        """Level-up HP gain must not corrupt pre-bump HP validation."""
        from liveplay.sweep_reconcile import _apply_observed_levelups, _check_hp_match
        active = make_mon(Species.ROOKIDEE, level=10)._replace(hp=2)
        from liveplay.data.species import SPECIES_DATA
        from liveplay.data.growth_rate import exp_for_level
        active = active._replace(exp=exp_for_level(SPECIES_DATA[Species.ROOKIDEE].growth_rate, 11) - 1)
        state = make_battle(active, make_mon(Species.RATTATA))
        pre_max = state.sides[0].team[0].max_hp
        deltas = [pdelta(Species.ROOKIDEE, (11, 2))]

        assert _check_hp_match(state, deltas) is True

        _apply_observed_levelups(state, [self._grew("ROOKIDEE", 11)])
        leveled = state.sides[0].team[0]
        assert leveled.level == 11
        assert leveled.max_hp > pre_max
        assert leveled.hp == 2 + (leveled.max_hp - pre_max)

        assert _check_hp_match(state, deltas) is False


# ---------------------------------------------------------------------------
# TestLevelUpTrustsObserved
# ---------------------------------------------------------------------------

class TestLevelUpTrustsObserved:
    """check_log_events: sim level-ups must be a subset of observed; extras tolerated."""

    def _grew(self, name, level):
        return _mr("STRINGID_PKMNGREWTOLV", var_values=[name, str(level)])

    def test_observed_extra_levelup_tolerated(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.LEVEL_UP, pokemon=Species.ROOKIDEE, new_level=7)
        messages = [self._grew("SKITTY", 8), self._grew("ROOKIDEE", 7)]
        assert check_log_events(capturing, messages, [], None) is True

    def test_sim_invents_unobserved_levelup_pruned(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.LEVEL_UP, pokemon=Species.ROOKIDEE, new_level=7)
        capturing.handle(LogEvent.LEVEL_UP, pokemon=Species.SKITTY, new_level=8)
        messages = [self._grew("ROOKIDEE", 7)]
        assert check_log_events(capturing, messages, [], None) is False

    def test_exact_match_still_passes(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.LEVEL_UP, pokemon=Species.ROOKIDEE, new_level=7)
        messages = [self._grew("ROOKIDEE", 7)]
        assert check_log_events(capturing, messages, [], None) is True


# ---------------------------------------------------------------------------
# TestParalysisMessageRespected
# ---------------------------------------------------------------------------

class TestParalysisMessageRespected:
    """PKMNISPARALYZED message must require CANT_PARALYSIS event in log."""

    def test_paralysis_message_requires_cant_paralysis_event_pass(self):
        from liveplay.sweep_reconcile import check_log_events
        cap = CapturingLogger()
        cap.handle(LogEvent.CANT_PARALYSIS, pokemon=Species.PIKACHU)
        messages = [_mr("STRINGID_PKMNISPARALYZED", var_values=["PIKACHU"])]
        assert check_log_events(cap, messages, [], None) is True

    def test_paralysis_message_without_event_fails(self):
        from liveplay.sweep_reconcile import check_log_events
        cap = CapturingLogger()
        messages = [_mr("STRINGID_PKMNISPARALYZED", var_values=["PIKACHU"])]
        assert check_log_events(cap, messages, [], None) is False


# ---------------------------------------------------------------------------
# TestConfusionApplyConstraint
# ---------------------------------------------------------------------------

class TestConfusionApplyConstraint:
    """Confusion apply vs acting-reminder distinction."""

    def test_isconfused_reminder_does_not_require_volatile_apply(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        messages = [_mr("STRINGID_PKMNISCONFUSED", var_values=["EXEGGCUTE"])]
        assert check_log_events(capturing, messages, [], None) is True

    def test_wasconfused_application_requires_volatile_apply_pass(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.VOLATILE_APPLY, target=Species.EXEGGCUTE,
                         volatile="confused", source="move", duration=None, side=0)
        messages = [_mr("STRINGID_PKMNWASCONFUSED", var_values=["EXEGGCUTE"])]
        assert check_log_events(capturing, messages, [], None) is True

    def test_wasconfused_application_requires_volatile_apply_fail(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        messages = [_mr("STRINGID_PKMNWASCONFUSED", var_values=["EXEGGCUTE"])]
        assert check_log_events(capturing, messages, [], None) is False


# ---------------------------------------------------------------------------
# TestDirectionalStatChangeConstraint
# ---------------------------------------------------------------------------

class TestDirectionalStatChangeConstraint:
    """Directional ATTACKERS*/DEFENDERS* stat IDs require STAT_BOOST in log."""

    def _msg(self, string_id):
        return _mr(string_id, var_values=["BUDEW", "Speed", "fell!"])

    def test_attackersstatfell_requires_stat_boost_pass(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.STAT_BOOST, target=Species.BUDEW, stat=4,
                         stages=-1, new_stage=-1, source="move", side=0)
        assert check_log_events(
            capturing, [self._msg("STRINGID_ATTACKERSSTATFELL")], [], None) is True

    def test_attackersstatfell_requires_stat_boost_fail(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        assert check_log_events(
            capturing, [self._msg("STRINGID_ATTACKERSSTATFELL")], [], None) is False

    def test_defendersstatfell_requires_stat_boost_fail(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        assert check_log_events(
            capturing, [self._msg("STRINGID_DEFENDERSSTATFELL")], [], None) is False

    def test_severe_and_drastic_variants_recognized(self):
        from liveplay.sweep_reconcile import check_log_events
        for sid in ("STRINGID_ATTACKERSTATFELLSEVERELY",
                    "STRINGID_DEFENDERSTATFELLSEVERELY",
                    "STRINGID_ATTACKERSTATROSTEDRASTICALLY",
                    "STRINGID_DEFENDERSTATROSTEDRASTICALLY"):
            capturing = CapturingLogger()
            assert check_log_events(capturing, [self._msg(sid)], [], None) is False, sid


# ---------------------------------------------------------------------------
# TestUsingItemStatConstraint
# ---------------------------------------------------------------------------

class TestUsingItemStatConstraint:
    """STRINGID_USINGITEMSTATOFPKMNROSE requires a side-attributed STAT_BOOST."""

    def _foe_msg(self, item="Salac Berry"):
        return _mr("STRINGID_USINGITEMSTATOFPKMNROSE",
                   var_values=[item, "Speed", "CROAGUNK"],
                   side_hint=None,
                   name_side_slots={2: 1})

    def _player_msg(self, item="Salac Berry"):
        return _mr("STRINGID_USINGITEMSTATOFPKMNROSE",
                   var_values=[item, "Speed", "CROAGUNK"],
                   side_hint=None,
                   name_side_slots={2: 0})

    def _unresolvable_msg(self, item="Salac Berry"):
        return _mr("STRINGID_USINGITEMSTATOFPKMNROSE",
                   var_values=[item, "Speed", "CROAGUNK"],
                   side_hint=None,
                   name_side_slots={})

    def _truncated_msg(self, item="Salac Berry"):
        return _mr("STRINGID_USINGITEMSTATOFPKMNROSE",
                   var_values=[item, "Speed"],
                   side_hint=None,
                   name_side_slots={})

    def test_foe_proc_requires_side1_stat_boost_pass(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.STAT_BOOST, target=Species.CROAGUNK, stat=4,
                         stages=1, new_stage=1, source="item", side=1)
        assert check_log_events(capturing, [self._foe_msg()], [], None) is True

    def test_foe_proc_side0_stat_boost_fails(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.STAT_BOOST, target=Species.CROAGUNK, stat=4,
                         stages=1, new_stage=1, source="item", side=0)
        assert check_log_events(capturing, [self._foe_msg()], [], None) is False

    def test_player_proc_requires_side0_stat_boost_pass(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.STAT_BOOST, target=Species.CROAGUNK, stat=4,
                         stages=1, new_stage=1, source="item", side=0)
        assert check_log_events(capturing, [self._player_msg()], [], None) is True

    def test_player_proc_side1_stat_boost_fails(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.STAT_BOOST, target=Species.CROAGUNK, stat=4,
                         stages=1, new_stage=1, source="item", side=1)
        assert check_log_events(capturing, [self._player_msg()], [], None) is False

    def test_unresolvable_side_raises_simulation_error(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.STAT_BOOST, target=Species.CROAGUNK, stat=4,
                         stages=1, new_stage=1, source="item", side=1)
        with pytest.raises(SimulationError):
            check_log_events(capturing, [self._unresolvable_msg()], [], None)

    def test_truncated_message_raises_simulation_error(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.STAT_BOOST, target=Species.CROAGUNK, stat=4,
                         stages=1, new_stage=1, source="item", side=1)
        with pytest.raises(SimulationError):
            check_log_events(capturing, [self._truncated_msg()], [], None)

    def test_no_stat_boost_fails(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        assert check_log_events(capturing, [self._foe_msg()], [], None) is False

    @pytest.mark.parametrize("item", [
        "Salac Berry", "Liechi Berry", "Petaya Berry",
        "Apicot Berry", "Ganlon Berry", "Starf Berry",
    ])
    def test_foe_proc_all_pinch_berries(self, item):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.STAT_BOOST, target=Species.CROAGUNK, stat=4,
                         stages=1, new_stage=1, source="item", side=1)
        assert check_log_events(capturing, [self._foe_msg(item)], [], None) is True

    @pytest.mark.parametrize("item", [
        "Salac Berry", "Liechi Berry", "Petaya Berry",
        "Apicot Berry", "Ganlon Berry", "Starf Berry",
    ])
    def test_player_proc_all_pinch_berries(self, item):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.STAT_BOOST, target=Species.CROAGUNK, stat=4,
                         stages=1, new_stage=1, source="item", side=0)
        assert check_log_events(capturing, [self._player_msg(item)], [], None) is True


# ---------------------------------------------------------------------------
# TestPerHitDamagesHelper
# ---------------------------------------------------------------------------

class TestPerHitDamagesHelper:
    """Unit tests for the _per_hit_damages helper."""

    def test_multi_hit_per_hit_damages_helper(self):
        from liveplay.sweep_reconcile import _per_hit_damages
        capturing = CapturingLogger()
        capturing.handle(LogEvent.DAMAGE, target=Species.BLISSEY, amount=30, source="move",
                         hp_before=1000, hp_after=970)
        capturing.handle(LogEvent.DAMAGE, target=Species.BLISSEY, amount=45, source="move",
                         hp_before=970, hp_after=925)
        capturing.handle(LogEvent.DAMAGE, target=Species.BLISSEY, amount=10, source="item",
                         hp_before=925, hp_after=915)
        result = _per_hit_damages(capturing, Species.BLISSEY)
        assert result == [30, 45]


# ---------------------------------------------------------------------------
# TestCheekPouchCorroboration
# ---------------------------------------------------------------------------

class TestCheekPouchCorroboration:
    """Berry vs Cheek Pouch heals must be bucketed separately per side."""

    _ORAN = "STRINGID_PKMNSITEMRESTOREDHEALTH"
    _POUCH = "STRINGID_PKMNSITEMRESTOREDHPALITTLE"

    def _restore(self, string_id, source_name, side):
        return _mr(string_id, var_values=["BUNNELBY", source_name], side_hint=side)

    def test_cheek_pouch_restore_not_miscounted_as_berry(self):
        from liveplay.sweep_reconcile import check_log_events
        messages = [
            self._restore(self._ORAN, "Oran Berry", 0),
            self._restore(self._POUCH, "Cheek Pouch", 0),
        ]
        cap = CapturingLogger()
        cap.handle(LogEvent.HEAL, source="berry", side=0)
        cap.handle(LogEvent.HEAL, source="cheek_pouch", side=0)
        assert check_log_events(cap, messages, [], None) is True

    def test_plain_berry_still_corroborates(self):
        from liveplay.sweep_reconcile import check_log_events
        messages = [self._restore(self._ORAN, "Oran Berry", 0)]
        cap = CapturingLogger()
        cap.handle(LogEvent.HEAL, source="berry", side=0)
        assert check_log_events(cap, messages, [], None) is True

    def test_berry_count_mismatch_still_fails(self):
        from liveplay.sweep_reconcile import check_log_events
        messages = [
            self._restore(self._ORAN, "Oran Berry", 0),
            self._restore(self._ORAN, "Oran Berry", 0),
        ]
        cap = CapturingLogger()
        cap.handle(LogEvent.HEAL, source="berry", side=0)
        assert check_log_events(cap, messages, [], None) is False

    def test_cheek_pouch_without_hp_berry_corroborates(self):
        from liveplay.sweep_reconcile import check_log_events
        messages = [self._restore(self._POUCH, "Cheek Pouch", 0)]
        cap = CapturingLogger()
        cap.handle(LogEvent.HEAL, source="cheek_pouch", side=0)
        assert check_log_events(cap, messages, [], None) is True

    def test_cheek_pouch_count_mismatch_still_fails(self):
        from liveplay.sweep_reconcile import check_log_events
        messages = [self._restore(self._POUCH, "Cheek Pouch", 0)]
        cap = CapturingLogger()
        cap.handle(LogEvent.HEAL, source="berry", side=0)
        assert check_log_events(cap, messages, [], None) is False

    def test_cheek_pouch_credited_to_correct_side(self):
        from liveplay.sweep_reconcile import check_log_events
        messages = [self._restore(self._POUCH, "Cheek Pouch", 1)]
        cap = CapturingLogger()
        cap.handle(LogEvent.HEAL, source="cheek_pouch", side=1)
        assert check_log_events(cap, messages, [], None) is True


# ---------------------------------------------------------------------------
# TestHasFaintedActive
# ---------------------------------------------------------------------------

class TestHasFaintedActive:
    """has_fainted_active mirrors AWAIT_POST_FAINT_SWITCH condition."""

    def test_fainted_active_with_bench_returns_true(self):
        from liveplay.sweep_reconcile import has_fainted_active
        fainted = make_mon(Species.PIDGEY, hp=0)
        fainted = fainted._replace(fainted=True)
        bench = make_mon(Species.RATTATA)
        state = make_battle(fainted, make_mon(Species.BULBASAUR), team0=[fainted, bench])
        assert has_fainted_active(state) is True

    def test_no_fainted_active_returns_false(self):
        from liveplay.sweep_reconcile import has_fainted_active
        mon = make_mon(Species.PIDGEY)
        state = make_battle(mon, make_mon(Species.BULBASAUR))
        assert has_fainted_active(state) is False

    def test_fainted_active_no_bench_returns_false(self):
        from liveplay.sweep_reconcile import has_fainted_active
        fainted = make_mon(Species.PIDGEY, hp=0)
        fainted = fainted._replace(fainted=True)
        state = make_battle(fainted, make_mon(Species.BULBASAUR))
        # No bench members → battle-over condition, not a switch prompt
        assert has_fainted_active(state) is False
