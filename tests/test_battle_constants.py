"""Tests for battle_constants.PRIMARY_STRING_IDS and turn_has_real_action."""
import pytest
from liveplay.battle_constants import (
    PRIMARY_STRING_IDS,
    MENU_REJECTION_STRING_IDS,
    turn_has_real_action,
)

def test_usedmove_is_primary():
    assert "STRINGID_USEDMOVE" in PRIMARY_STRING_IDS

def test_criticalhit_is_not_primary():
    assert "STRINGID_CRITICALHIT" not in PRIMARY_STRING_IDS

def test_intromsg_is_primary():
    assert "STRINGID_INTROMSG" in PRIMARY_STRING_IDS

def test_pkmnhurtbypoison_is_primary():
    assert "STRINGID_PKMNHURTBYPOISON" in PRIMARY_STRING_IDS

def test_supereffective_is_not_primary():
    assert "STRINGID_SUPEREFFECTIVE" not in PRIMARY_STRING_IDS


# ---------------------------------------------------------------------------
# turn_has_real_action — phantom-turn detection
# ---------------------------------------------------------------------------

def test_nopp_is_a_menu_rejection():
    assert "STRINGID_NOPPLEFT" in MENU_REJECTION_STRING_IDS

def test_empty_turn_is_not_real():
    assert turn_has_real_action([]) is False

def test_only_nopp_is_not_real():
    assert turn_has_real_action(["STRINGID_NOPPLEFT"]) is False

def test_repeated_rejections_are_not_real():
    # Selecting two different out-of-PP / disabled moves before giving up.
    assert turn_has_real_action(
        ["STRINGID_NOPPLEFT", "STRINGID_PKMNCANTUSEMOVETAUNT"]
    ) is False

def test_all_known_rejections_are_not_real():
    assert turn_has_real_action(sorted(MENU_REJECTION_STRING_IDS)) is False

def test_move_use_is_real():
    assert turn_has_real_action(["STRINGID_USEDMOVE"]) is True

def test_rejection_then_real_move_is_real():
    # Rejected the empty slot, then picked a valid move that resolved the turn.
    assert turn_has_real_action(
        ["STRINGID_NOPPLEFT", "STRINGID_USEDMOVE"]
    ) is True

def test_butnopp_is_not_a_menu_rejection():
    # "But there was no PP left for the move!" is a Struggle/execution message,
    # not a selection refusal — it must NOT suppress a turn.
    assert "STRINGID_BUTNOPPLEFT" not in MENU_REJECTION_STRING_IDS
    assert turn_has_real_action(["STRINGID_BUTNOPPLEFT"]) is True
