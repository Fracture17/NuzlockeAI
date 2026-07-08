"""
Template-matching OCR for pokeemerald font bitmaps (small, normal, narrow, bold).

Parses glyph shapes from font PNGs and advance widths from fonts.c,
then matches text left-to-right against binarized image strips.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

import numpy as np
from PIL import Image

_POKEEMERALD:      Final = Path(os.environ.get("POKEEMERALD_PATH", "/home/Fracture/Downloads/pokeemerald-master"))
_CHARMAP_TXT:      Final = _POKEEMERALD / "charmap.txt"
_FONTS_C:          Final = _POKEEMERALD / "src/fonts.c"
_STATUS_ICONS_PNG: Final = _POKEEMERALD / "graphics/interface/status_icons.png"

# Sprite-sheet row (y) for each status condition icon (each sprite is 32×8 px).
# Order matches sSpriteTemplate_StatusCondition in party_menu.h.
_STATUS_SPRITE_ROWS: Final = {
    "PSN":  0,
    "PAR":  8,
    "SLP": 16,
    "FRZ": 24,
    "BRN": 32,
    "FNT": 48,
}

# Valid text pixel colors — all other pixels are background.
_TEXT_COLORS: Final = frozenset({(255, 255, 255), (74, 74, 74), (66, 66, 66)})


@dataclass(frozen=True)
class FontConfig:
    """Static geometry and source info for one pokeemerald font."""
    png:           Path
    widths_name:   str | None   # array name in fonts.c; None for fixed-advance fonts
    fixed_advance: int | None   # advance for every glyph; None when widths_name is set
    cell_w:        int
    cell_h:        int
    ncols:         int
    row_start:     int
    row_end:       int          # exclusive


_FONT_DIR: Final = _POKEEMERALD / "graphics/fonts"

_FONT_CONFIGS: Final[dict[str, FontConfig]] = {
    "small": FontConfig(
        png=_FONT_DIR / "latin_small.png",
        widths_name="gFontSmallLatinGlyphWidths",
        fixed_advance=None,
        cell_w=16, cell_h=16, ncols=16,
        row_start=4, row_end=11,
    ),
    "normal": FontConfig(
        png=_FONT_DIR / "latin_normal.png",
        widths_name="gFontNormalLatinGlyphWidths",
        fixed_advance=None,
        cell_w=16, cell_h=16, ncols=16,
        row_start=3, row_end=14,
    ),
    "narrow": FontConfig(
        png=_FONT_DIR / "latin_narrow.png",
        widths_name="gFontNarrowLatinGlyphWidths",
        fixed_advance=None,
        cell_w=16, cell_h=16, ncols=16,
        row_start=3, row_end=14,
    ),
    "bold": FontConfig(
        png=_FONT_DIR / "japanese_bold.png",
        widths_name=None,
        fixed_advance=8,
        cell_w=8, cell_h=16, ncols=16,
        row_start=9, row_end=15,
    ),
}


def _parse_charmap(path: Path) -> dict[str, int]:
    charmap: dict[str, int] = {}
    for line in path.read_text().splitlines():
        m = re.match(r"'(.)'.*=\s*(?:0[xX])?([0-9A-Fa-f]+)", line)
        if m:
            charmap[m.group(1)] = int(m.group(2), 16)
    # The "Lv" level prefix is a single combined tile at index 0x34.
    m = re.search(r"^LV\s*=\s*([0-9A-Fa-f]+)", path.read_text(), re.MULTILINE)
    if m:
        charmap["Lv"] = int(m.group(1), 16)
    return charmap


def _parse_glyph_widths(path: Path, array_name: str) -> list[int]:
    """Extract the width array named array_name from fonts.c."""
    m = re.search(
        rf"{re.escape(array_name)}\[.*?\]\s*=\s*\{{([^}}]+)\}}",
        path.read_text(), re.DOTALL,
    )
    if not m:
        raise ValueError(f"{array_name} not found in fonts.c")
    return [int(n) for n in re.findall(r"\d+", m.group(1))]


def _extract_template(
    pixels: np.ndarray,
    glyph_idx: int,
    advance: int,
    cfg: FontConfig,
) -> np.ndarray:
    """Binary (0/1) array: value-1 pixels in glyph body rows, spacing col excluded."""
    x0 = (glyph_idx % cfg.ncols) * cfg.cell_w
    y0 = (glyph_idx // cfg.ncols) * cfg.cell_h
    cell = pixels[y0 + cfg.row_start : y0 + cfg.row_end, x0 : x0 + advance - 1]
    return (cell == 1).astype(np.uint8)


@lru_cache(maxsize=4)
def _load(font: str) -> tuple[dict[str, np.ndarray], dict[str, int]]:
    """Load charmap, glyph widths, and templates for the named font."""
    cfg = _FONT_CONFIGS[font]
    charmap = _parse_charmap(_CHARMAP_TXT)

    if cfg.widths_name is not None:
        widths = _parse_glyph_widths(_FONTS_C, cfg.widths_name)
        def advance_for(idx: int) -> int | None:
            return widths[idx] if idx < len(widths) and widths[idx] >= 2 else None
    else:
        def advance_for(idx: int) -> int | None:
            return cfg.fixed_advance

    pixels = np.array(Image.open(cfg.png))

    templates: dict[str, np.ndarray] = {}
    advances:  dict[str, int]        = {}
    for char, idx in charmap.items():
        adv = advance_for(idx)
        if adv is None:
            continue
        tmpl = _extract_template(pixels, idx, adv, cfg)
        templates[char] = tmpl
        advances[char]  = adv
    return templates, advances


@lru_cache(maxsize=1)
def _load_status_sprites() -> dict[str, np.ndarray]:
    """Load binary (0/1) white-pixel templates for each status condition (32×8)."""
    arr = np.array(Image.open(_STATUS_ICONS_PNG))
    # Palette index 2 is white (255,255,255) in the sprite sheet.
    return {
        name: (arr[y0 : y0 + 8, 0:32] == 2).astype(np.uint8)
        for name, y0 in _STATUS_SPRITE_ROWS.items()
    }


def _binarize(img: Image.Image) -> np.ndarray:
    """Return bool HxW mask: True wherever any valid text color appears."""
    arr = np.array(img.convert("RGB"))
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    mask = (
        ((r == 255) & (g == 255) & (b == 255)) |
        ((r ==  74) & (g ==  74) & (b ==  74)) |
        ((r ==  66) & (g ==  66) & (b ==  66))
    )
    return mask


def match_text(
    image: Image.Image,
    chars: str | tuple[str, ...],
    fonts: tuple[str, ...] = ("small",),
    max_gap: int | None = None,
) -> str:
    """Scan image left-to-right, returning exactly matched characters from chars.

    chars: a str (iterates single chars) or tuple of tokens (supports multi-char
           keys like "Lv"). fonts: names of fonts to draw candidates from; first
           exact pixel match wins. max_gap: stop scanning after this many consecutive
           unmatched pixels.
    """
    # Precompute per candidate: (char, tmpl, adv, th, tw, first_col_count).
    # first_col_count (ink pixels in template column 0) is a cheap necessary
    # condition used to prune the expensive full pixel-equality check below.
    # Zero-ink glyphs (the space) are dropped here so total>0 need not be rechecked.
    candidates: list[tuple[str, np.ndarray, int, int, int, int]] = []
    space_w: int | None = None
    for font in fonts:
        templates, advances = _load(font)
        if " " in chars and " " in advances and space_w is None:
            space_w = advances[" "]
        for c in chars:
            if c == " ":
                continue  # blank glyph — emitted from gap width, never pixel-matched
            if c in templates:
                tmpl = templates[c]
                if int(tmpl.sum()) == 0:
                    continue
                th, tw = tmpl.shape
                candidates.append((c, tmpl, advances[c], th, tw, int(tmpl[:, 0].sum())))
    if not candidates:
        return ""

    binary = _binarize(image).astype(np.uint8)
    tmpl_h = max(c[3] for c in candidates)
    if binary.shape[0] < tmpl_h:
        return ""

    # Crops are anchored to the glyph top, so match top-aligned (no vertical search).
    strip = binary[:tmpl_h]
    img_w = strip.shape[1]

    # Per-height column ink counts (glyph heights are constant within a font, so
    # there are at most one per font). strip[:h].sum(axis=0)[x] gives the ink in
    # column x over the first h rows — compared against each glyph's column-0
    # count to prune candidates before the full equality check. Stored as Python
    # lists so the hot-loop lookup is a scalar int, not a numpy scalar.
    col_counts_by_h = {h: strip[:h].sum(axis=0).tolist() for h in {c[3] for c in candidates}}

    result:    list[str] = []
    x         = 0
    gap_count = 0
    while x < img_w:
        if max_gap is not None and gap_count >= max_gap:
            break
        best_char, best_adv = "", 1
        for char, tmpl, adv, th, tw, first_col in candidates:
            if x + tw > img_w:
                continue
            if col_counts_by_h[th][x] != first_col:
                continue  # column-0 ink differs — cannot be an exact match
            window = strip[:th, x : x + tw]
            if np.array_equal(window, tmpl):
                best_char, best_adv = char, adv
                break  # exact match — first candidate wins
        if best_char:
            if space_w is not None and result and gap_count >= space_w:
                result.append(" ")  # blank run >= a space advance = word boundary
            result.append(best_char)
            x += best_adv
            gap_count = 0
        else:
            x += 1
            gap_count += 1
    return "".join(result)


def match_status_region(image: Image.Image) -> str:
    """Return the status condition token ("FNT", "PSN", …) or Lv## font text.

    First tries to match each 32×8 status sprite exactly against the image.
    Falls back to font-text scanning (for "Lv##" when no condition is present).
    The returned string is suitable for _extract_status() and _parse_level().
    """
    sprites = _load_status_sprites()

    binary = _binarize(image).astype(np.uint8)

    h, w = binary.shape
    # The sprite is placed 1 pixel from the left edge of the status crop.
    x_off, y_off = 1, 0
    if w >= x_off + 32 and h >= y_off + 8:
        crop = binary[y_off : y_off + 8, x_off : x_off + 32]
        for name, tmpl in sprites.items():
            if int(tmpl.sum()) == 0:
                continue
            if int((tmpl & crop).sum()) == int(tmpl.sum()):
                return name

    # No sprite matched — scan for level font text (e.g. "Lv5").
    return match_text(image, ("Lv",) + tuple("0123456789"))
