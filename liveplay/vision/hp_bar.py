"""
Opponent HP bar pixel reader for Pokémon Emerald.

Reads a single row of pixels from the HP bar region and counts non-black pixels
to estimate the opponent's remaining HP.

Formula (from pokeemerald battle_interface.c):
  bar_pixels = floor(hp * 48 / max_hp), minimum 1 if hp > 0.

From a pixel count k, the HP range is:
  hp_min = ceil(k * max_hp / 48)
  hp_max = ((k + 1) * max_hp - 1) // 48

Edge cases:
  - A change of 1 pixel corresponds to max_hp/48 HP; changes smaller than that
    are invisible to this method.
  - k=0 means the bar is fully empty (KO). hp_max will still be non-zero per
    the formula — this is expected; treat k=0 as meaning HP=0 at the game level.
  - If hp > 0, the bar always shows at least 1 pixel.
"""
from __future__ import annotations
import math
from PIL import Image
from ..battle_types import HpReading
from .regions import OPPONENT_HP_BAR_PIXELS

__all__ = ["read_opponent_hp_bar"]


def _classify_pixel(r: int, g: int, b: int) -> str:
    """Classify a pixel as 'green', 'yellow', 'red', 'black', or 'invalid'."""
    if r == 115 and g == 255 and b == 173:
        return "green"
    if r == 255 and g == 231 and b == 57:
        return "yellow"
    if r == 255 and g == 90 and b == 57:
        return "red"
    if r == 82 and g == 107 and b == 90:
        return "black"
    if r == 255 and g == 255 and b == 255:
        return "white"
    return "invalid"


def read_opponent_hp_bar(image: Image.Image, max_hp: int | None = None) -> HpReading:
    """Read the opponent HP bar from the OPPONENT_HP_BAR crop.

    Args:
        image: The OPPONENT_HP_BAR region crop (coordinates from regions.py).
        max_hp: Known maximum HP. If None, hp_min/hp_max/hp_mid will be None.

    Returns:
        HpReading with k=None if the bar is animating (unexpected pixel colors found).
    """
    x, y, w, h = OPPONENT_HP_BAR_PIXELS
    row = image.crop((x, y, x + w, y + h))
    pixels = list(row.getdata())

    if _classify_pixel(*pixels[0]) != "white" and _classify_pixel(*pixels[-1]) != "white":
        return HpReading(k=None, hp_min=None, hp_max=None, hp_mid=None)

    HPKind = _classify_pixel(*pixels[1])
    k = 0
    for pixel in pixels[1:-1]:
        r, g, b = pixel[:3]
        kind = _classify_pixel(r, g, b)
        if kind != HPKind and kind != "black":
            return HpReading(k=None, hp_min=None, hp_max=None, hp_mid=None)
        if kind == "invalid":
            return HpReading(k=None, hp_min=None, hp_max=None, hp_mid=None)
        if kind != "black":
            k += 1

    #These thresholds may be off by 1
    """if k >= 24:
        if HPKind != "green":
            return HpReading(k=None, hp_min=None, hp_max=None, hp_mid=None)
    elif k >= 12:
        if HPKind != "yellow":
            return HpReading(k=None, hp_min=None, hp_max=None, hp_mid=None)
    else:
        if HPKind != "red":
            return HpReading(k=None, hp_min=None, hp_max=None, hp_mid=None)"""

    if max_hp is None:
        return HpReading(k=k, hp_min=None, hp_max=None, hp_mid=None)

    hp_min = math.ceil(k * max_hp / 48)
    hp_max = ((k + 1) * max_hp - 1) // 48
    hp_mid = round((hp_min + hp_max) / 2)
    return HpReading(k=k, hp_min=hp_min, hp_max=hp_max, hp_mid=hp_mid)
