"""
Tests for battle_messages.py schema — verifies player vs trainer switch-in ID split
and EXP gain template format.

Player send-out templates use B_PLAYER_MON* placeholders (no trainer name/class)
and must carry player-specific string IDs. Trainer/opponent send-out templates
include B_TRAINER1_CLASS/NAME and must keep the original IDs.
"""

import pytest
from liveplay.battle_messages import BATTLE_MESSAGES
from liveplay.battle_constants import PRIMARY_STRING_IDS

# constant_names that are exclusively player send-out actions
_PLAYER_INTRO_CONSTANTS = {"sText_GoPkmn", "sText_GoTwoPkmn"}
_PLAYER_SWITCH_CONSTANTS = {
    "sText_GoPkmn2",
    "sText_DoItPkmn",
    "sText_GoForItPkmn",
    "sText_YourFoesWeakGetEmPkmn",
}

# constant_names that are trainer/opponent send-outs
_TRAINER_INTRO_CONSTANTS = {
    "sText_Trainer1SentOutPkmn",
    "sText_Trainer1SentOutTwoPkmn",
    "sText_TwoTrainersSentPkmn",
}
_TRAINER_SWITCH_CONSTANTS = {"sText_Trainer1SentOutPkmn2"}

_MSG_BY_CONSTANT = {m["constant_name"]: m for m in BATTLE_MESSAGES}


@pytest.mark.unit
class TestPlayerSwitchInIds:
    def test_player_intro_sendout_has_player_id(self):
        for c in _PLAYER_INTRO_CONSTANTS:
            msg = _MSG_BY_CONSTANT[c]
            assert msg["string_id"] == "STRINGID_PLAYER_INTROSENDOUT", (
                f"{c} should have STRINGID_PLAYER_INTROSENDOUT, got {msg['string_id']!r}"
            )

    def test_player_switchinmon_has_player_id(self):
        for c in _PLAYER_SWITCH_CONSTANTS:
            msg = _MSG_BY_CONSTANT[c]
            assert msg["string_id"] == "STRINGID_PLAYER_SWITCHINMON", (
                f"{c} should have STRINGID_PLAYER_SWITCHINMON, got {msg['string_id']!r}"
            )

    def test_trainer_intro_sendout_keeps_original_id(self):
        for c in _TRAINER_INTRO_CONSTANTS:
            msg = _MSG_BY_CONSTANT[c]
            assert msg["string_id"] == "STRINGID_INTROSENDOUT", (
                f"{c} should keep STRINGID_INTROSENDOUT, got {msg['string_id']!r}"
            )

    def test_trainer_switchinmon_keeps_original_id(self):
        for c in _TRAINER_SWITCH_CONSTANTS:
            msg = _MSG_BY_CONSTANT[c]
            assert msg["string_id"] == "STRINGID_SWITCHINMON", (
                f"{c} should keep STRINGID_SWITCHINMON, got {msg['string_id']!r}"
            )


@pytest.mark.unit
class TestExpTemplate:
    _msg = _MSG_BY_CONSTANT["sText_PkmnGainedEXP"]

    def test_exp_template_has_two_placeholders(self):
        assert len(self._msg["placeholders"]) == 2, (
            f"EXP template should have 2 placeholders, got {self._msg['placeholders']}"
        )

    def test_exp_template_normalized_uses_lowercase_exp(self):
        normalized = self._msg["normalized"]
        assert "Exp." in normalized, f"Expected 'Exp.' in normalized, got {normalized!r}"
        assert "EXP." not in normalized, f"Got uppercase 'EXP.' in normalized: {normalized!r}"

    def test_exp_in_primary_string_ids(self):
        assert "STRINGID_PKMNGAINEDEXP" in PRIMARY_STRING_IDS


@pytest.mark.unit
class TestWhiteoutPrimaryIds:
    def test_playerwhiteout_in_primary_string_ids(self):
        assert "STRINGID_PLAYERWHITEOUT" in PRIMARY_STRING_IDS

    def test_playerwhiteout2_in_primary_string_ids(self):
        assert "STRINGID_PLAYERWHITEOUT2" in PRIMARY_STRING_IDS
