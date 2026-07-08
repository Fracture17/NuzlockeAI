"""Tests for src.vision.hp_bar.read_opponent_hp_bar."""
import math
import pytest
from PIL import Image
from liveplay.vision.hp_bar import read_opponent_hp_bar
from liveplay.vision.regions import OPPONENT_HP_BAR_PIXELS
from liveplay.battle_types import HpReading


_BX, _BY, _BW, _BH = OPPONENT_HP_BAR_PIXELS


def _make_bar(pixels: list[tuple[int, int, int]]) -> Image.Image:
    """Create a full image with bar pixels placed at the HP bar crop region.

    pixels should be the full 50-pixel bar contents:
      [WHITE, <up to 48 HP pixels>, ..., WHITE]
    Any positions not covered by pixels default to black.
    """
    img = Image.new("RGB", (_BX + _BW, _BY + _BH), (0, 0, 0))
    for i, color in enumerate(pixels):
        img.putpixel((_BX + i, _BY), color)
    return img


GREEN  = (115, 255, 173)
YELLOW = (255, 231, 57)
RED    = (255, 90, 57)
BLACK  = (82, 107, 90)
WHITE  = (255, 255, 255)
GRAY   = (128, 128, 128)  # invalid


def test_all_black_no_maxhp():
    img = _make_bar([WHITE] + [BLACK] * 48 + [WHITE])
    r = read_opponent_hp_bar(img)
    assert r.k == 0
    assert r.hp_min is None
    assert r.hp_max is None
    assert r.hp_mid is None


def test_full_green_no_maxhp():
    img = _make_bar([WHITE] + [GREEN] * 48 + [WHITE])
    r = read_opponent_hp_bar(img)
    assert r.k == 48
    assert r.hp_min is None


def test_full_green_with_maxhp():
    img = _make_bar([WHITE] + [GREEN] * 48 + [WHITE])
    r = read_opponent_hp_bar(img, max_hp=100)
    assert r.k == 48
    assert r.hp_min == math.ceil(48 * 100 / 48)   # 100
    assert r.hp_max == (49 * 100 - 1) // 48        # 102
    assert r.hp_mid == round((r.hp_min + r.hp_max) / 2)


def test_half_bar_with_maxhp():
    img = _make_bar([WHITE] + [GREEN] * 24 + [BLACK] * 24 + [WHITE])
    r = read_opponent_hp_bar(img, max_hp=100)
    assert r.k == 24
    assert r.hp_min == math.ceil(24 * 100 / 48)   # 50
    assert r.hp_max == (25 * 100 - 1) // 48        # 52
    assert r.hp_mid == round((r.hp_min + r.hp_max) / 2)


def test_one_pixel_with_maxhp():
    img = _make_bar([WHITE] + [GREEN] + [BLACK] * 47 + [WHITE])
    r = read_opponent_hp_bar(img, max_hp=100)
    assert r.k == 1
    assert r.hp_min == math.ceil(1 * 100 / 48)    # 3
    assert r.hp_max == (2 * 100 - 1) // 48         # 4
    assert r.hp_mid == round((r.hp_min + r.hp_max) / 2)


def test_invalid_pixel_returns_none_k():
    img = _make_bar([WHITE] + [GREEN] * 10 + [GRAY] + [BLACK] * 37 + [WHITE])
    r = read_opponent_hp_bar(img)
    assert r.k is None
    assert r.hp_min is None
    assert r.hp_max is None
    assert r.hp_mid is None


def test_yellow_pixels_count():
    img = _make_bar([WHITE] + [YELLOW] * 20 + [BLACK] * 28 + [WHITE])
    r = read_opponent_hp_bar(img)
    assert r.k == 20


def test_red_pixels_count():
    img = _make_bar([WHITE] + [RED] * 5 + [BLACK] * 43 + [WHITE])
    r = read_opponent_hp_bar(img)
    assert r.k == 5


def test_mixed_valid_colors():
    # 10 green + 5 yellow + 3 red + 30 black = 18 non-black
    #This should fail, since it's not a real possible HP bar
    img = _make_bar([WHITE] + [GREEN] * 10 + [YELLOW] * 5 + [RED] * 3 + [BLACK] * 30 + [WHITE])
    r = read_opponent_hp_bar(img)
    assert r.k is None
