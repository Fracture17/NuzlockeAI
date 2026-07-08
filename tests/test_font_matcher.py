"""
Unit and integration tests for src/vision/font_matcher.py.

Unit tests build synthetic images from known templates (no real screenshots).
Integration tests require debug images at tests/Fixtures/.
"""

import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from liveplay.vision.font_matcher import _load, match_text
from liveplay.vision.ocr import (
    read_battle_message,
    read_opponent_info,
    read_party_prompt,
    read_player_info,
)


def _make_image_from_template(tmpl: np.ndarray) -> Image.Image:
    """Convert a binary (0/1) numpy array to an RGB PIL image with white text on black."""
    h, w = tmpl.shape
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    arr[tmpl == 1] = [255, 255, 255]
    return Image.fromarray(arr, "RGB")


def _make_two_char_image(tmpl_a: np.ndarray, adv_a: int, tmpl_b: np.ndarray) -> Image.Image:
    """Place tmpl_a then tmpl_b (at adv_a offset) in a single image row."""
    h = max(tmpl_a.shape[0], tmpl_b.shape[0])
    w = adv_a + tmpl_b.shape[1]
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    ha, wa = tmpl_a.shape
    hb, wb = tmpl_b.shape
    arr[:ha, :wa][tmpl_a == 1] = [255, 255, 255]
    arr[:hb, adv_a : adv_a + wb][tmpl_b == 1] = [255, 255, 255]
    return Image.fromarray(arr, "RGB")


# ---------------------------------------------------------------------------
# Unit tests — fast, no real images needed
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestMatchTextSingleChar:
    def test_exact_match_single_char(self):
        templates, advances = _load("small")
        tmpl = templates["5"]
        img  = _make_image_from_template(tmpl)
        assert match_text(img, "0123456789", fonts=("small",)) == "5"

    def test_near_miss_no_match(self):
        """Flipping one foreground pixel should prevent an exact match."""
        templates, advances = _load("small")
        tmpl = templates["5"].copy()
        # Find and flip the first foreground pixel.
        ys, xs = np.where(tmpl == 1)
        tmpl[ys[0], xs[0]] = 0
        img = _make_image_from_template(tmpl)
        assert match_text(img, "0123456789", fonts=("small",)) == ""

    def test_near_miss_inner_column_no_match(self):
        """Flipping a pixel in a non-first column must still reject the match.

        Guards the first-column-count prefilter: a glyph whose column-0 ink is
        unchanged passes the cheap prune, so the full pixel-equality check must
        still catch a difference in a later column (prune is necessary, not
        sufficient).
        """
        templates, advances = _load("small")
        tmpl = templates["5"].copy()
        # Find a foreground pixel that is NOT in column 0, so column-0 ink count
        # is preserved and only an inner column differs.
        ys, xs = np.where(tmpl == 1)
        inner = next((i for i in range(len(xs)) if xs[i] != 0), None)
        assert inner is not None, "template has ink only in column 0; pick another glyph"
        tmpl[ys[inner], xs[inner]] = 0
        img = _make_image_from_template(tmpl)
        assert match_text(img, "0123456789", fonts=("small",)) == ""

    def test_two_chars_in_sequence(self):
        templates, advances = _load("small")
        tmpl1, adv1 = templates["1"], advances["1"]
        tmpl9 = templates["9"]
        img = _make_two_char_image(tmpl1, adv1, tmpl9)
        assert match_text(img, "0123456789", fonts=("small",)) == "19"

    def test_max_gap_stops(self):
        """A 10-column gap between glyphs should stop scanning when max_gap=5."""
        templates, advances = _load("small")
        tmpl5, adv5 = templates["5"], advances["5"]
        tmpl9 = templates["9"]
        gap = 10
        h = max(tmpl5.shape[0], tmpl9.shape[0])
        w = adv5 + gap + tmpl9.shape[1]
        arr = np.zeros((h, w, 3), dtype=np.uint8)
        ha, wa = tmpl5.shape
        arr[:ha, :wa][tmpl5 == 1] = [255, 255, 255]
        hb, wb = tmpl9.shape
        x_off = adv5 + gap
        arr[:hb, x_off : x_off + wb][tmpl9 == 1] = [255, 255, 255]
        img = Image.fromarray(arr, "RGB")
        result = match_text(img, "0123456789", fonts=("small",), max_gap=5)
        assert result == "5"

    def test_mismatched_font_no_match(self):
        """A small-font glyph image should not match normal-font templates."""
        templates, advances = _load("small")
        tmpl = templates["5"]
        img  = _make_image_from_template(tmpl)
        assert match_text(img, "0123456789", fonts=("normal",)) == ""

    def test_word_gap_emits_space(self):
        """A space-width blank run between two glyphs should produce a ' '."""
        templates, advances = _load("normal")
        tmpl_a, adv_a = templates["A"], advances["A"]
        tmpl_b        = templates["B"]
        space_adv     = advances[" "]
        h  = max(tmpl_a.shape[0], tmpl_b.shape[0])
        # Layout: A at 0, then a full space advance, then B.
        x_b = adv_a + space_adv
        w   = x_b + tmpl_b.shape[1]
        arr = np.zeros((h, w, 3), dtype=np.uint8)
        ha, wa = tmpl_a.shape
        arr[:ha, :wa][tmpl_a == 1] = [255, 255, 255]
        hb, wb = tmpl_b.shape
        arr[:hb, x_b : x_b + wb][tmpl_b == 1] = [255, 255, 255]
        img = Image.fromarray(arr, "RGB")
        result = match_text(img, "AB ", fonts=("normal",))
        assert result == "A B", f"Expected 'A B', got: {result!r}"

    def test_no_space_within_word(self):
        """Adjacent glyphs (no blank run) must not produce a space."""
        templates, advances = _load("normal")
        tmpl_a, adv_a = templates["A"], advances["A"]
        tmpl_b        = templates["B"]
        img = _make_two_char_image(tmpl_a, adv_a, tmpl_b)
        result = match_text(img, "AB ", fonts=("normal",))
        assert result == "AB", f"Expected 'AB', got: {result!r}"

    def test_e_accent_read_in_pokemon(self):
        """'POKéMON' must read with its 'é' glyph, not drop it into a space.

        The 'é' template exists in the font sheet; the regression was that 'é'
        was absent from the OCR charset, so its pixels were skipped and the
        word split into 'POK' + 'MON' (real OCR: 'Pok' 'mon')."""
        from liveplay.vision.ocr import _ALPHA_NUM_CHARS
        templates, advances = _load("normal")
        word = "POKéMON"
        h = max(templates[c].shape[0] for c in word)
        total_w = sum(advances[c] for c in word) + 16  # pad to avoid clipping
        arr = np.zeros((h, total_w, 3), dtype=np.uint8)
        x = 0
        for c in word:
            t = templates[c]
            th, tw = t.shape
            arr[:th, x : x + tw][t == 1] = [255, 255, 255]
            x += advances[c]
        img = Image.fromarray(arr, "RGB")
        result = match_text(img, _ALPHA_NUM_CHARS, fonts=("normal",))
        assert result == "POKéMON", f"Expected 'POKéMON', got: {result!r}"

    def test_lv_combined_tile(self):
        """The combined 'Lv' tile followed by '5' should match as 'Lv5'."""
        templates, advances = _load("small")
        if "Lv" not in templates:
            pytest.skip("'Lv' tile not yet implemented")
        tmpl_lv, adv_lv = templates["Lv"], advances["Lv"]
        tmpl_5 = templates["5"]
        img = _make_two_char_image(tmpl_lv, adv_lv, tmpl_5)
        result = match_text(img, ("Lv",) + tuple("0123456789"), fonts=("small",))
        assert result == "Lv5", f"Expected 'Lv5', got: {result!r}"


# ---------------------------------------------------------------------------
# Regression tests — use committed fixtures (always run)
# ---------------------------------------------------------------------------

_FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.mark.unit
class TestBattleMessageRegression:
    def test_action_prompt_two_lines(self):
        """Action-select prompt is two left-indented lines; both must read fully.

        Regression for the crop x-origin clipping leading capitals
        ('What will' -> 'at will', 'Rookidee do?' -> 'okidee do?').
        """
        img = Image.open(os.path.join(_FIXTURES, "battle_msg_what_will.png"))
        result = read_battle_message(img)
        assert result.text == "What will Rookidee do?", (
            f"Expected 'What will Rookidee do?', got: {result.text!r}"
        )


@pytest.mark.unit
class TestPartyPromptRegression:
    def test_detects_choose_a_pokemon(self):
        """The party-screen prompt uses a (99,99,99) glyph core the battle-message
        binarizer ignores; read_party_prompt must remap it and detect the phrase."""
        img = Image.open(os.path.join(_FIXTURES, "party_prompt_choose.png"))
        assert read_party_prompt(img) is True

    def test_blank_frame_is_not_party(self):
        """A frame with no party-prompt glyph core must not be detected as the party screen."""
        arr = np.full((13, 95, 3), 214, dtype=np.uint8)  # solid light box, no text
        assert read_party_prompt(Image.fromarray(arr, "RGB")) is False


# ---------------------------------------------------------------------------
# Integration tests — require /tmp/vision/ debug images
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestIntegrationOCR:
    def test_read_battle_message_integration(self):
        path = Path(__file__).parent / "Fixtures" / "region_battle_msg.png"
        if not path.exists():
            pytest.skip(f"Integration image not found: {path}")
        img    = Image.open(path)
        result = read_battle_message(img)
        assert "Calvin" in result.text, f"Expected 'Calvin' in: {result.text!r}"
        assert "Poochyena" in result.text, f"Expected 'Poochyena' in: {result.text!r}"

    @pytest.mark.skip(reason="region_player_hp.png needs a real capture image; currently blank")
    def test_read_player_info_integration(self):
        path = "/tmp/vision/region_player_hp.png"
        if not os.path.exists(path):
            pytest.skip(f"Integration image not found: {path}")
        img    = Image.open(path)
        result = read_player_info(img)
        assert result.name == "Rookidee", f"Expected name 'Rookidee', got: {result.name!r}"
        assert result.level == 5,         f"Expected level 5, got: {result.level!r}"
        assert result.hp_current == 19,   f"Expected hp_current 19, got: {result.hp_current!r}"
        assert result.hp_max == 19,       f"Expected hp_max 19, got: {result.hp_max!r}"

    def test_read_opponent_info_integration(self):
        path = Path(__file__).parent / "Fixtures" / "region_opp_hp.png"
        if not path.exists():
            pytest.skip(f"Integration image not found: {path}")
        img    = Image.open(path)
        result = read_opponent_info(img)
        assert result.name == "Poochyena", f"Expected name 'Poochyena', got: {result.name!r}"
        assert result.level == 5,          f"Expected level 5, got: {result.level!r}"
