"""
Unit and integration tests for src/vision/ocr.py.

Unit tests cover the internal parsing helpers directly — no OCR call needed.
Integration tests (marked @pytest.mark.integration) require real images at tests/Fixtures/.
"""

import pytest
from pathlib import Path
from PIL import Image
from liveplay.vision.ocr import (
    _parse_level,
    _parse_hp_fraction,
    _extract_status,
    _extract_name,
    read_player_info,
    read_opponent_info,
    read_battle_message,
    read_party_menu,
    PlayerInfoResult,
)


# ---------------------------------------------------------------------------
# _parse_level
# ---------------------------------------------------------------------------

class TestParseLevel:
    def test_finds_compact_level(self):
        assert _parse_level("PIKACHU Lv36") == 36

    def test_finds_level_with_space(self):
        assert _parse_level("Lv 36") == 36

    def test_returns_none_when_absent(self):
        assert _parse_level("PIKACHU 36/36") is None

    def test_returns_none_on_empty_string(self):
        assert _parse_level("") is None

    def test_finds_level_at_start(self):
        assert _parse_level("Lv1 BULBASAUR") == 1


# ---------------------------------------------------------------------------
# _parse_hp_fraction
# ---------------------------------------------------------------------------

class TestParseHpFraction:
    def test_finds_standard_fraction(self):
        assert _parse_hp_fraction("HP 80/80") == (80, 80)

    def test_finds_fraction_with_space_after_slash(self):
        assert _parse_hp_fraction("80/ 80") == (80, 80)

    def test_finds_low_hp(self):
        assert _parse_hp_fraction("1/100") == (1, 100)

    def test_returns_none_none_when_absent(self):
        assert _parse_hp_fraction("PIKACHU Lv36") == (None, None)

    def test_returns_none_none_on_empty_string(self):
        assert _parse_hp_fraction("") == (None, None)

    def test_finds_first_fraction_in_text(self):
        current, maximum = _parse_hp_fraction("45/80 200/200")
        assert current == 45
        assert maximum == 80


# ---------------------------------------------------------------------------
# _extract_status
# ---------------------------------------------------------------------------

class TestExtractStatus:
    @pytest.mark.parametrize("token", ["PSN", "BRN", "SLP", "FRZ", "PAR", "TOX"])
    def test_finds_each_status(self, token):
        assert _extract_status(f"PIKACHU Lv5 {token}") == token

    def test_returns_none_when_no_status(self):
        assert _extract_status("PIKACHU Lv5 40/40") is None

    def test_returns_none_on_empty_string(self):
        assert _extract_status("") is None

    def test_returns_first_status_when_multiple_present(self):
        result = _extract_status("PSN BRN")
        assert result == "PSN"

    def test_does_not_match_partial_token(self):
        assert _extract_status("POISON") is None


# ---------------------------------------------------------------------------
# _extract_name
# ---------------------------------------------------------------------------

class TestExtractName:
    def test_finds_pokemon_name(self):
        assert _extract_name("PIKACHU Lv5") == "PIKACHU"

    def test_skips_hp_token(self):
        assert _extract_name("HP PIKACHU") == "PIKACHU"

    def test_skips_status_tokens(self):
        assert _extract_name("PSN PIKACHU") == "PIKACHU"

    def test_skips_other_common_tokens(self):
        for token in ["LVL", "THE", "MON", "BAG", "RUN"]:
            assert _extract_name(f"{token} BULBASAUR") == "BULBASAUR"

    def test_returns_none_when_no_valid_name(self):
        assert _extract_name("HP 40/40") is None

    def test_returns_none_on_empty_string(self):
        assert _extract_name("") is None

    def test_requires_minimum_three_chars(self):
        assert _extract_name("AB PIKACHU") == "PIKACHU"

    def test_name_with_mixed_case_line(self):
        assert _extract_name("the PIKACHU Lv5") == "PIKACHU"


# ---------------------------------------------------------------------------
# Integration test — requires /tmp/vision/player_hp.png
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_read_player_info_returns_playerinforesult():
    import os
    path = "/tmp/vision/player_hp.png"
    if not os.path.exists(path):
        pytest.skip(f"Integration image not found: {path}")
    img = Image.open(path)
    result = read_player_info(img)
    assert isinstance(result, PlayerInfoResult)
    assert result.name is not None, "Expected a non-None name from real player HP image"


# ---------------------------------------------------------------------------
# New integration tests — require /tmp/vision/ debug images
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_read_battle_message_calvin_poochyena():
    path = Path(__file__).parent / "Fixtures" / "region_battle_msg.png"
    if not path.exists():
        pytest.skip(f"Integration image not found: {path}")
    img = Image.open(path)
    result = read_battle_message(img)
    assert "Calvin" in result.text, f"Expected 'Calvin' in: {result.text!r}"
    assert "Poochyena" in result.text, f"Expected 'Poochyena' in: {result.text!r}"


@pytest.mark.skip(reason="region_player_hp.png needs a real capture image; currently blank")
@pytest.mark.integration
def test_read_player_info_rookidee_lv5():
    import os
    path = "/tmp/vision/region_player_hp.png"
    if not os.path.exists(path):
        pytest.skip(f"Integration image not found: {path}")
    img = Image.open(path)
    result = read_player_info(img)
    assert result.name == "Rookidee",  f"Expected name 'Rookidee', got: {result.name!r}"
    assert result.level == 5,          f"Expected level 5, got: {result.level!r}"
    assert result.hp_current == 19,    f"Expected hp_current 19, got: {result.hp_current!r}"
    assert result.hp_max == 19,        f"Expected hp_max 19, got: {result.hp_max!r}"


@pytest.mark.integration
def test_read_opponent_info_poochyena_lv5():
    path = Path(__file__).parent / "Fixtures" / "region_opp_hp.png"
    if not path.exists():
        pytest.skip(f"Integration image not found: {path}")
    img = Image.open(path)
    result = read_opponent_info(img)
    assert result.name == "Poochyena", f"Expected name 'Poochyena', got: {result.name!r}"
    assert result.level == 5,          f"Expected level 5, got: {result.level!r}"


@pytest.mark.integration
def test_read_party_menu_slots():
    path0 = Path(__file__).parent / "Fixtures" / "party_slot_0.png"
    path1 = Path(__file__).parent / "Fixtures" / "party_slot_1.png"
    if not path0.exists() or not path1.exists():
        pytest.skip(f"Integration party images not found")
    img0 = Image.open(path0)
    img1 = Image.open(path1)
    results = read_party_menu([img0, img1])
    assert len(results) >= 1, "Expected at least one party member result"
    r0 = next((r for r in results if r.slot_index == 0), None)
    assert r0 is not None, "No result for slot 0"
    assert r0.name == "Pidgey", f"Expected slot 0 name 'Pidgey', got: {r0.name!r}"
    assert r0.hp_max == 21, f"Expected slot 0 hp_max 21, got: {r0.hp_max!r}"
    r1 = next((r for r in results if r.slot_index == 1), None)
    if r1 is not None:
        assert r1.name == "Rookidee", f"Expected slot 1 name 'Rookidee', got: {r1.name!r}"
        assert r1.hp_max == 19,       f"Expected slot 1 hp_max 19, got: {r1.hp_max!r}"
