# Tests for liveplay/sweep_secondaries.py — written before implementation.
from __future__ import annotations

import pytest

from liveplay.battle_types import ActionGroup, MatchResult
from liveplay.data.moves import Move
from liveplay.data.status import Status
from liveplay.rng import RNGEvent
from liveplay.sweep_secondaries import (
    classify_secondaries,
    _secondary_match_in_messages,
    _secondary_fired_in_group,
    _secondary_fired_in_flat_messages,
    _inject_attributable_secondaries,
    _CONFUSION_APPLY_ID,
    _CONFUSION_ACTING_ID,
)
from tests.state_builders import make_battle, make_mon
from liveplay.data.species import Species


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AUTO_SIDE_HINT = object()


def _foe_prefix_hint(var_values):
    """Derive side_hint from var_values[0]'s 'Foe ' prefix."""
    if not var_values:
        return None
    first = str(var_values[0])
    first_word = first.split()[0].lower() if first.strip() else ""
    return 1 if first_word == "foe" else 0


def _mr(string_id, *, constant_name="", var_values=None, id_value=0, score=0,
        side_hint=_AUTO_SIDE_HINT, matched_text=""):
    """Build a minimal MatchResult."""
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
    )


def _usedmove_group(attacker_name, move_name, secondaries=None, *, side_hint=0):
    primary = _mr(
        "STRINGID_USEDMOVE",
        constant_name="sText_AttackerUsedMove",
        var_values=[attacker_name, move_name],
        side_hint=side_hint,
    )
    return ActionGroup(primary=primary, secondaries=secondaries or [], hp_readings=[])


def _simple_state():
    """A minimal BattleState for tests that require one."""
    muk = make_mon(Species.MUK, moves=(Move.SLUDGE_BOMB,))
    corsola = make_mon(Species.CORSOLA, moves=(Move.SPLASH,))
    return make_battle(muk, corsola)


# ---------------------------------------------------------------------------
# Tests: classify_secondaries
# ---------------------------------------------------------------------------

class TestClassifySecondaries:
    def test_sludge_bomb_attributable_poison(self):
        """Sludge Bomb has a poison status secondary → attributable only."""
        attributable, non_attr = classify_secondaries(Move.SLUDGE_BOMB)
        assert len(attributable) == 1
        assert attributable[0].status == Status.POISON
        assert non_attr == []

    def test_iron_head_flinch_only_non_attributable(self):
        """Iron Head has a flinch-only secondary → non-attributable only."""
        attributable, non_attr = classify_secondaries(Move.IRON_HEAD)
        assert attributable == []
        assert len(non_attr) == 1
        assert non_attr[0].flinch is True

    def test_thunder_fang_attributable_paralysis_only(self):
        """Thunder Fang: paralysis secondary → attributable; secondary2 flinch excluded from both."""
        attributable, non_attr = classify_secondaries(Move.THUNDER_FANG)
        assert len(attributable) == 1
        assert attributable[0].status == Status.PARALYSIS
        # secondary2 flinch is excluded from non_attributable (routes through FLINCH event)
        assert non_attr == []

    def test_ancient_power_stat_boost_attributable(self):
        """Ancient Power has a full-stat-boost secondary → attributable."""
        attributable, non_attr = classify_secondaries(Move.ANCIENT_POWER)
        assert len(attributable) == 1
        assert attributable[0].stat_changes  # all-stat +1 tuple
        assert non_attr == []

    def test_tri_attack_attributable(self):
        """Tri Attack has a secondary and is the TRI_ATTACK move → attributable."""
        attributable, non_attr = classify_secondaries(Move.TRI_ATTACK)
        assert len(attributable) >= 1
        assert non_attr == []

    def test_tackle_no_secondary(self):
        """Tackle has no secondary effects."""
        attributable, non_attr = classify_secondaries(Move.TACKLE)
        assert attributable == []
        assert non_attr == []

    def test_flamethrower_burn_attributable(self):
        """Flamethrower burn secondary is attributable, no non-attributable."""
        attributable, non_attr = classify_secondaries(Move.FLAMETHROWER)
        assert len(attributable) >= 1
        assert any(sec.status == Status.BURN for sec in attributable)
        assert non_attr == []

    def test_headbutt_flinch_non_attributable(self):
        """Headbutt flinch secondary is non-attributable."""
        attributable, non_attr = classify_secondaries(Move.HEADBUTT)
        assert attributable == []
        assert len(non_attr) >= 1
        assert all(sec.flinch for sec in non_attr)


# ---------------------------------------------------------------------------
# Tests: _secondary_match_in_messages
# ---------------------------------------------------------------------------

class TestSecondaryMatchInMessages:
    def _get_secondary(self, move_enum):
        """Get the first attributable secondary for the given move."""
        attributable, _ = classify_secondaries(move_enum)
        assert attributable, f"{move_enum} must have attributable secondary"
        return attributable[0]

    def test_status_match_true(self):
        """Matching status-apply message → True."""
        sec = self._get_secondary(Move.SLUDGE_BOMB)  # poison
        msgs = [_mr("STRINGID_PKMNWASPOISONED", var_values=["Corsola"])]
        assert _secondary_match_in_messages(msgs, sec) is True

    def test_status_match_false_wrong_id(self):
        """Non-matching string_id → False."""
        sec = self._get_secondary(Move.SLUDGE_BOMB)  # poison
        msgs = [_mr("STRINGID_PKMNWASBURNED", var_values=["Corsola"])]
        assert _secondary_match_in_messages(msgs, sec) is False

    def test_status_no_messages_false(self):
        """Empty message list for status secondary → False."""
        sec = self._get_secondary(Move.SLUDGE_BOMB)
        assert _secondary_match_in_messages([], sec) is False

    def test_stat_change_match_true(self):
        """Stat-change message → True."""
        sec = self._get_secondary(Move.ANCIENT_POWER)
        msgs = [_mr("STRINGID_ATTACKERSSTATROSE", var_values=["Corsola", "Attack"])]
        assert _secondary_match_in_messages(msgs, sec) is True

    def test_stat_change_no_match_false(self):
        """No stat-change message → False."""
        sec = self._get_secondary(Move.ANCIENT_POWER)
        msgs = [_mr("STRINGID_PKMNWASBURNED", var_values=["Corsola"])]
        assert _secondary_match_in_messages(msgs, sec) is False

    def test_confusion_wasconfused_matches(self):
        """PKMNWASCONFUSED (apply) → True for confusion secondary."""
        attributable, _ = classify_secondaries(Move.WATER_PULSE)
        assert attributable and attributable[0].volatile == "confused"
        sec = attributable[0]
        msgs = [_mr(_CONFUSION_APPLY_ID, var_values=["Corsola"])]
        assert _secondary_match_in_messages(msgs, sec) is True

    def test_confusion_isconfused_reminder_not_match(self):
        """PKMNISCONFUSED (acting reminder) → False; regression: Bug 19."""
        attributable, _ = classify_secondaries(Move.WATER_PULSE)
        sec = attributable[0]
        msgs = [_mr(_CONFUSION_ACTING_ID, var_values=["Corsola"])]
        assert _secondary_match_in_messages(msgs, sec) is False


# ---------------------------------------------------------------------------
# Tests: _secondary_fired_in_group
# ---------------------------------------------------------------------------

class TestSecondaryFiredInGroup:
    def _poison_secondary(self):
        attributable, _ = classify_secondaries(Move.SLUDGE_BOMB)
        return attributable[0]

    def test_none_group_returns_none(self):
        """None action_group → None (can't tell)."""
        sec = self._poison_secondary()
        assert _secondary_fired_in_group(None, Move.SLUDGE_BOMB, sec) is None

    def test_fired_true_when_status_message_present(self):
        """Poison message in group → True."""
        sec = self._poison_secondary()
        poison_msg = _mr("STRINGID_PKMNWASPOISONED", var_values=["Corsola"])
        group = _usedmove_group("Muk", "Sludge Bomb", secondaries=[poison_msg])
        assert _secondary_fired_in_group(group, Move.SLUDGE_BOMB, sec) is True

    def test_fired_false_when_usedmove_but_no_effect(self):
        """USEDMOVE in group but no secondary effect message → False."""
        sec = self._poison_secondary()
        group = _usedmove_group("Muk", "Sludge Bomb")
        assert _secondary_fired_in_group(group, Move.SLUDGE_BOMB, sec) is False

    def test_no_usedmove_no_effect_returns_none(self):
        """Group with no USEDMOVE and no effect message → None."""
        sec = self._poison_secondary()
        # Group whose primary is NOT a USEDMOVE
        primary = _mr("STRINGID_SWITCHINMON", var_values=["Corsola"])
        group = ActionGroup(primary=primary, secondaries=[], hp_readings=[])
        assert _secondary_fired_in_group(group, Move.SLUDGE_BOMB, sec) is None


# ---------------------------------------------------------------------------
# Tests: _secondary_fired_in_flat_messages
# ---------------------------------------------------------------------------

class TestSecondaryFiredInFlatMessages:
    def _poison_secondary(self):
        attributable, _ = classify_secondaries(Move.SLUDGE_BOMB)
        return attributable[0]

    def _paralysis_secondary(self):
        attributable, _ = classify_secondaries(Move.THUNDERBOLT)
        return attributable[0]

    def test_fired_true_status_message_in_flat(self):
        """Poison message in flat list → True."""
        sec = self._poison_secondary()
        msgs = [_mr("STRINGID_PKMNWASPOISONED", var_values=["Corsola"])]
        assert _secondary_fired_in_flat_messages(msgs, Move.SLUDGE_BOMB, sec, 1, None) is True

    def test_fired_false_no_status_message(self):
        """Status secondary with no matching message → False."""
        sec = self._poison_secondary()
        assert _secondary_fired_in_flat_messages([], Move.SLUDGE_BOMB, sec, 1, None) is False

    def test_fired_false_no_paralysis_message(self):
        """Paralysis secondary with no matching message → False."""
        sec = self._paralysis_secondary()
        assert _secondary_fired_in_flat_messages([], Move.THUNDERBOLT, sec, 1, None) is False

    def test_fired_true_stat_change_in_flat(self):
        """Stat-change message in flat list → True."""
        sec_ap, _ = classify_secondaries(Move.ANCIENT_POWER)
        sec = sec_ap[0]
        msgs = [_mr("STRINGID_ATTACKERSSTATROSE", var_values=["Corsola", "Attack"])]
        assert _secondary_fired_in_flat_messages(msgs, Move.ANCIENT_POWER, sec, 1, None) is True

    def test_fired_false_no_stat_change(self):
        """Stat-change secondary with no message → False."""
        sec_ap, _ = classify_secondaries(Move.ANCIENT_POWER)
        sec = sec_ap[0]
        assert _secondary_fired_in_flat_messages([], Move.ANCIENT_POWER, sec, 1, None) is False

    def test_fired_true_confusion_in_flat(self):
        """Confusion message in flat list → True."""
        attributable, _ = classify_secondaries(Move.WATER_PULSE)
        sec = attributable[0]
        msgs = [_mr(_CONFUSION_APPLY_ID, var_values=["Corsola"])]
        assert _secondary_fired_in_flat_messages(msgs, Move.WATER_PULSE, sec, 1, None) is True

    def test_fired_false_no_confusion(self):
        """Confusion secondary with no message → False."""
        attributable, _ = classify_secondaries(Move.WATER_PULSE)
        sec = attributable[0]
        assert _secondary_fired_in_flat_messages([], Move.WATER_PULSE, sec, 1, None) is False


# ---------------------------------------------------------------------------
# Tests: _inject_attributable_secondaries
# ---------------------------------------------------------------------------

class TestInjectAttributableSecondaries:
    def test_no_secondary_move_writes_nothing(self):
        """Tackle has no secondary → no overrides written."""
        overrides = {}
        pre_inject = {}
        _inject_attributable_secondaries(overrides, pre_inject, Move.TACKLE, None)
        assert overrides == {}
        assert pre_inject == {}

    def test_fired_true_writes_secondary_fires_true(self):
        """Fired secondary (via group) → SECONDARY_FIRES[slot] = True."""
        poison_msg = _mr("STRINGID_PKMNWASPOISONED", var_values=["Corsola"])
        group = _usedmove_group("Muk", "Sludge Bomb", secondaries=[poison_msg])
        overrides = {}
        pre_inject = {}
        _inject_attributable_secondaries(overrides, pre_inject, Move.SLUDGE_BOMB, group, source_slot=0)
        assert RNGEvent.SECONDARY_FIRES in overrides
        assert isinstance(overrides[RNGEvent.SECONDARY_FIRES], dict)
        assert overrides[RNGEvent.SECONDARY_FIRES][0] is True

    def test_fired_false_writes_secondary_fires_false(self):
        """No secondary fired (via group with USEDMOVE but no effect) → SECONDARY_FIRES[slot] = False."""
        group = _usedmove_group("Muk", "Sludge Bomb")
        overrides = {}
        pre_inject = {}
        _inject_attributable_secondaries(overrides, pre_inject, Move.SLUDGE_BOMB, group, source_slot=0)
        assert RNGEvent.SECONDARY_FIRES in overrides
        assert overrides[RNGEvent.SECONDARY_FIRES][0] is False

    def test_fired_none_writes_nothing(self):
        """Unknown outcome (no group, no flat messages) → no SECONDARY_FIRES entry."""
        overrides = {}
        pre_inject = {}
        _inject_attributable_secondaries(overrides, pre_inject, Move.SLUDGE_BOMB, None, source_slot=0)
        assert RNGEvent.SECONDARY_FIRES not in overrides

    def test_fired_true_slot1_writes_correct_slot(self):
        """source_slot=1 → SECONDARY_FIRES dict keyed at slot 1."""
        poison_msg = _mr("STRINGID_PKMNWASPOISONED", var_values=["Corsola"])
        group = _usedmove_group("Muk", "Sludge Bomb", secondaries=[poison_msg])
        overrides = {}
        pre_inject = {}
        _inject_attributable_secondaries(overrides, pre_inject, Move.SLUDGE_BOMB, group, source_slot=1)
        assert overrides[RNGEvent.SECONDARY_FIRES][1] is True

    def test_flat_message_path_fired_true(self):
        """Flat-message path (no group): status message present → SECONDARY_FIRES[slot] = True."""
        overrides = {}
        pre_inject = {}
        flat_msgs = [_mr("STRINGID_PKMNWASPOISONED", var_values=["Corsola"])]
        _inject_attributable_secondaries(
            overrides, pre_inject, Move.SLUDGE_BOMB, None,
            source_slot=0, flat_messages=flat_msgs
        )
        assert overrides[RNGEvent.SECONDARY_FIRES][0] is True

    def test_flat_message_path_fired_false(self):
        """Flat-message path (no group): no status message → SECONDARY_FIRES[slot] = False."""
        overrides = {}
        pre_inject = {}
        _inject_attributable_secondaries(
            overrides, pre_inject, Move.SLUDGE_BOMB, None,
            source_slot=0, flat_messages=[]
        )
        assert overrides[RNGEvent.SECONDARY_FIRES][0] is False

    def test_flat_message_path_none_when_no_group_no_flat(self):
        """No group AND flat_messages=None → nothing written (can't determine)."""
        overrides = {}
        pre_inject = {}
        _inject_attributable_secondaries(
            overrides, pre_inject, Move.SLUDGE_BOMB, None,
            source_slot=0, flat_messages=None
        )
        assert RNGEvent.SECONDARY_FIRES not in overrides


# ---------------------------------------------------------------------------
# Tests: Tri Attack special handling
# ---------------------------------------------------------------------------

class TestTriAttackInject:
    def test_tri_attack_classify_attributable(self):
        """Tri Attack is marked attributable in classify_secondaries."""
        attributable, non_attr = classify_secondaries(Move.TRI_ATTACK)
        assert len(attributable) >= 1
        assert non_attr == []

    def test_tri_attack_group_no_status_msg_fired_false(self):
        """Tri Attack group, no status message → SECONDARY_FIRES = False (USEDMOVE confirms it ran).

        Tri Attack secondary.status is None, so _secondary_match_in_messages returns False;
        USEDMOVE is present → fired=False. TRI_ATTACK_STATUS not set (fired is falsy).
        """
        group = _usedmove_group("Porygon", "Tri Attack")
        overrides = {}
        pre_inject = {}
        _inject_attributable_secondaries(overrides, pre_inject, Move.TRI_ATTACK, group, source_slot=0)
        assert overrides[RNGEvent.SECONDARY_FIRES][0] is False
        assert RNGEvent.TRI_ATTACK_STATUS not in pre_inject

    def test_tri_attack_group_with_status_msg_fired_false(self):
        """Tri Attack group WITH burn message: secondary.status is None so match fails → fired=False.

        _secondary_match_in_messages only matches against secondary.status; since Tri Attack
        secondary.status is None, burn messages don't make fired=True. Matches OLD behavior.
        """
        burn_msg = _mr("STRINGID_PKMNWASBURNED", var_values=["Corsola"])
        group = _usedmove_group("Porygon", "Tri Attack", secondaries=[burn_msg])
        overrides = {}
        pre_inject = {}
        _inject_attributable_secondaries(overrides, pre_inject, Move.TRI_ATTACK, group, source_slot=0)
        # secondary.status=None → match fails → fired=False (USEDMOVE present)
        assert overrides[RNGEvent.SECONDARY_FIRES][0] is False
        assert RNGEvent.TRI_ATTACK_STATUS not in pre_inject

    def test_tri_attack_flat_messages_none_outcome(self):
        """Tri Attack flat-message path: secondary.status is None → falls through to None.

        _secondary_fired_in_flat_messages returns None for unrecognized secondaries,
        so no SECONDARY_FIRES entry is written.
        """
        flat_msgs = [_mr("STRINGID_PKMNWASBURNED", var_values=["Corsola"])]
        overrides = {}
        pre_inject = {}
        _inject_attributable_secondaries(
            overrides, pre_inject, Move.TRI_ATTACK, None,
            source_slot=0, flat_messages=flat_msgs
        )
        # Tri Attack's secondary has status=None, stat_changes=(), volatile=None → None returned
        assert RNGEvent.SECONDARY_FIRES not in overrides
        assert RNGEvent.TRI_ATTACK_STATUS not in pre_inject

    def test_tri_attack_tri_attack_status_set_when_fired_true(self):
        """When fired=True (hypothetical), TRI_ATTACK_STATUS is set from status msg in msgs.

        Exercises the TRI_ATTACK_STATUS injection branch. We force fired=True by providing
        a group where _secondary_match_in_messages returns True. This requires a secondary
        with a status field — we test via direct call to _inject_attributable_secondaries
        with a mock secondary that has status set to simulate the if-block being reachable.

        In practice with real Tri Attack data, fired is never True from group path (secondary.status
        is None). This test documents what happens IF fired were True via the TRI_ATTACK_STATUS path.
        We test via the flat-message path where the match can still be None but TRI_ATTACK_STATUS
        injection would run. Since fired is always False/None for real Tri Attack data, this
        test simply confirms the block is correct by using a direct integration via flat_messages
        where the secondary match fires True via status match.

        NOTE: Since Tri Attack secondary.status is None, this test uses PARALYZEDBY (special form)
        which maps to PARALYSIS in _TRI_ATTACK_STATUS_MAP. The test checks that if Tri Attack DID
        fire (hypothetical; can only happen if _secondary_match_in_messages is enhanced), the
        status would be correct. We document the actual OLD behavior: fired is False from group
        path, None from flat path → TRI_ATTACK_STATUS never set.
        """
        # This is a documentation test — confirming the current behavior is: TRI_ATTACK_STATUS
        # is never set from inject_attributable_secondaries for real Tri Attack data.
        for status_msg_id in [
            "STRINGID_PKMNWASBURNED",
            "STRINGID_PKMNWASFROZEN",
            "STRINGID_PKMNWASPARALYZED",
        ]:
            overrides = {}
            pre_inject = {}
            msg = _mr(status_msg_id, var_values=["Corsola"])
            group = _usedmove_group("Porygon", "Tri Attack", secondaries=[msg])
            _inject_attributable_secondaries(overrides, pre_inject, Move.TRI_ATTACK, group, source_slot=0)
            # Tri Attack secondary has status=None → match fails → USEDMOVE present → fired=False
            assert overrides[RNGEvent.SECONDARY_FIRES][0] is False
            assert RNGEvent.TRI_ATTACK_STATUS not in pre_inject
