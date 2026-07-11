"""
OCR functions for the Pokemon Emerald (GBA) battle screen.

All text uses template matching against pokeemerald font bitmaps via font_matcher.
Battle message, opponent, and player boxes use FONT_NORMAL/FONT_SMALL/FONT_BOLD.
Party menu text uses FONT_SMALL via match_text and match_status_region.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from PIL import Image

from .font_matcher import match_status_region, match_text
from .regions import (
    PARTY_SLOT_NAME, PARTY_SLOT_STATUS, PARTY_SLOT_HP_CURRENT, PARTY_SLOT_HP_MAX,
    PARTY_SLOT_ROW_NAME, PARTY_SLOT_ROW_STATUS, PARTY_SLOT_ROW_HP_CURRENT, PARTY_SLOT_ROW_HP_MAX,
)


# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class BattleMessageResult:
    """Raw OCR text from the battle message box.

    The region can contain dialogue, the battle menu (FIGHT/BAG/POKEMON/RUN),
    or the move list (move names + PP). Parse the text field downstream.
    """
    text: str


@dataclass
class PlayerInfoResult:
    """Parsed data from the player HP box (name, level, HP, status condition)."""
    name:       str | None
    level:      int | None
    hp_current: int | None
    hp_max:     int | None
    status:     str | None  # "PSN", "BRN", "SLP", "FRZ", "PAR", "TOX", or None


@dataclass
class OpponentInfoResult:
    """Parsed data from the opponent name/level box (no numeric HP)."""
    name:   str | None
    level:  int | None
    status: str | None


@dataclass
class PartyMemberResult:
    """Parsed data for one party member from the party menu."""
    name:       str | None
    level:      int | None
    hp_current: int | None
    hp_max:     int | None
    status:     str | None  # "PSN", "BRN", "SLP", "FRZ", "PAR", "TOX", "FNT", or None
    raw_text:   str         = ""
    slot_index: int         = 0


# ---------------------------------------------------------------------------
# Parsing helpers — all operate on already-OCR'd strings
# ---------------------------------------------------------------------------

def _parse_level(text: str) -> int | None:
    """Extract level from 'Lv##' or 'Lv ##'."""
    m = re.search(r"Lv\s*(\d+)", text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _parse_int(text: str) -> int | None:
    """Extract the first integer from text."""
    m = re.search(r"\d+", text)
    return int(m.group()) if m else None


def _parse_hp_fraction(text: str) -> tuple[int | None, int | None]:
    """Extract current/max HP from a '##/##' fraction (optional spaces around slash)."""
    m = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


_STATUS_TOKENS: frozenset[str] = frozenset({"PSN", "BRN", "SLP", "FRZ", "PAR", "TOX", "FNT"})


def _extract_status(text: str) -> str | None:
    """Return the first status condition token found, or None."""
    for m in re.finditer(r"\b([A-Z]{3})\b", text):
        if m.group(1) in _STATUS_TOKENS:
            return m.group(1)
    return None


_NAME_SKIP: frozenset[str] = frozenset({"HP", "LVL", "LV", "THE", "MON", "BAG", "RUN"})


def _extract_name(text: str) -> str | None:
    """Return the first capitalised word (3+ chars) that isn't a known non-name.

    Matches both ALL-CAPS ("PIKACHU") and mixed-case ("Poochyena") names.
    Skip-set comparison is case-insensitive.
    """
    skip = {s.upper() for s in (_STATUS_TOKENS | _NAME_SKIP)}
    for m in re.finditer(r"\b([A-Z][a-zA-Z]{2,})\b", text):
        token = m.group(1)
        if token.upper() not in skip:
            return token
    return None


def _crop(image: Image.Image, region: tuple[int, int, int, int]) -> Image.Image:
    x, y, w, h = region
    return image.crop((x, y, x + w, y + h))


# ---------------------------------------------------------------------------
# Public OCR API
# ---------------------------------------------------------------------------

_ALPHA_NUM_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!'?.,- /()é"
_ALPHA_CHARS     = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_DIGIT_CHARS     = "0123456789"

# Name pass for HP boxes, where the name shares a glyph row with "Lv##". The "Lv"
# tile is included as a token so _name_before_level can hard-stop the name at the
# level: FONT_SMALL's digit "0" and letter "O" templates are pixel-identical, so an
# alpha-only pass silently reads the level's 0 as a trailing "O" on the name
# (e.g. "BudewO" at Lv 10), which splits name-keyed HP logs when the level rolls
# over and the artifact disappears (Allen1 sweep crash, 2026-07-11).
_HPBOX_NAME_CHARS: tuple[str, ...] = ("Lv",) + tuple(_ALPHA_CHARS)


def _name_before_level(name_text: str) -> str | None:
    """Extract the mon name from an HP-box name-row scan, truncated at 'Lv'.

    Everything from the first 'Lv' token onward is level territory — including
    any digit glyphs the alpha charset would misread as letters. No species
    display name contains the exact substring 'Lv', so the cut is unambiguous.
    """
    return _extract_name(name_text.split("Lv", 1)[0])


def read_battle_message(image: Image.Image) -> BattleMessageResult:
    """OCR the battle message / move selection box using FONT_NORMAL and FONT_NARROW.

    Row 1 glyphs at y=12, row 2 at y=28 (height 11 = normal font row_start..row_end).
    The crop starts at x=4: dialogue text begins near x=12, but the action-select
    prompt ("What will <mon> do?") is indented to x=5, so a narrower left margin
    would clip its leading capital. The extra left columns are blank for dialogue.
    """
    row1_img = _crop(image, (4, 12, image.width - 8, 11))
    row2_img = _crop(image, (4, 28, image.width - 8, 11))
    row1 = match_text(row1_img, _ALPHA_NUM_CHARS, fonts=("normal", "narrow"))
    row2 = match_text(row2_img, _ALPHA_NUM_CHARS, fonts=("normal", "narrow"))
    text = (row1.strip() + " " + row2.strip()).strip()
    return BattleMessageResult(text=text)


def read_player_info(image: Image.Image) -> PlayerInfoResult:
    """OCR the player HP box (name, Lv, current HP, max HP) using FONT_SMALL.

    Name and level share one glyph row at y=4 (height 7); HP "##/##" is at
    x=55, y=22. The "Lv" prefix is a single font tile, matched via the "Lv" token.
    """
    strip = _crop(image, (0, 4, image.width, 7))
    name_text  = match_text(strip, _HPBOX_NAME_CHARS, fonts=("small",))
    level_text = match_text(strip, ("Lv",) + tuple(_DIGIT_CHARS), fonts=("small",))

    hp_img  = _crop(image, (55, 22, 25, 7))
    hp_text = match_text(hp_img, _DIGIT_CHARS + "/", fonts=("small",))
    hp_current, hp_max = _parse_hp_fraction(hp_text)

    return PlayerInfoResult(
        name=_name_before_level(name_text),
        level=_parse_level(level_text),
        hp_current=hp_current,
        hp_max=hp_max,
        status=None,
    )


def read_opponent_info(image: Image.Image) -> OpponentInfoResult:
    """OCR the opponent name/level box using FONT_SMALL. No numeric HP.

    Name and level share one glyph row at y=3 (height 7). The "Lv" prefix is a
    single font tile matched via the "Lv" token.
    """
    strip = _crop(image, (0, 3, image.width, 7))
    name_text  = match_text(strip, _HPBOX_NAME_CHARS, fonts=("small",))
    level_text = match_text(strip, ("Lv",) + tuple(_DIGIT_CHARS), fonts=("small",))

    return OpponentInfoResult(
        name=_name_before_level(name_text),
        level=_parse_level(level_text),
        status=None,
    )


_PARTY_PROMPT_CORE: tuple[int, int, int] = (99, 99, 99)


def read_party_prompt(image: Image.Image) -> bool:
    """Detect the party-screen "Choose a POKéMON." message in the prompt box.

    The party menu message box renders glyphs with a (99,99,99) core on a light
    background, a different palette than the battle message box — so the standard
    binarizer reads nothing. Remap that core to white, then template-match in
    FONT_NORMAL. The text sits a few rows down in the crop and match_text is
    top-aligned, so scan a small vertical offset range. 'é' is outside our
    charset ("POKéMON" -> "Pok mon"), so detection keys on 'choose' + 'pok'.
    """
    arr = np.array(image.convert("RGB"))
    core = (
        (arr[:, :, 0] == _PARTY_PROMPT_CORE[0])
        & (arr[:, :, 1] == _PARTY_PROMPT_CORE[1])
        & (arr[:, :, 2] == _PARTY_PROMPT_CORE[2])
    )
    remapped = np.zeros_like(arr)
    remapped[core] = (255, 255, 255)
    remapped_img = Image.fromarray(remapped, "RGB")

    for y0 in range(5):
        sub = remapped_img.crop((0, y0, remapped_img.width, remapped_img.height))
        text = match_text(sub, _ALPHA_CHARS + " .", fonts=("normal",)).lower()
        if "choose" in text and "pok" in text:
            return True
    return False


def read_party_menu(slot_images: list[Image.Image]) -> list[PartyMemberResult]:
    """OCR each party slot via dedicated sub-regions. Returns one result per non-empty slot."""
    members: list[PartyMemberResult] = []
    for i, image in enumerate(slot_images):
        if i == 0:
            r_name, r_status, r_cur, r_max = (
                PARTY_SLOT_NAME, PARTY_SLOT_STATUS, PARTY_SLOT_HP_CURRENT, PARTY_SLOT_HP_MAX
            )
        else:
            r_name, r_status, r_cur, r_max = (
                PARTY_SLOT_ROW_NAME, PARTY_SLOT_ROW_STATUS, PARTY_SLOT_ROW_HP_CURRENT, PARTY_SLOT_ROW_HP_MAX
            )
        name_text   = match_text(_crop(image, r_name),   "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
        status_text = match_status_region(_crop(image, r_status))
        cur_text    = match_text(_crop(image, r_cur),    "0123456789")
        max_text    = match_text(_crop(image, r_max),    "0123456789")

        name       = _extract_name(name_text)
        status     = _extract_status(status_text)
        level      = _parse_level(status_text)
        hp_current = _parse_int(cur_text)
        hp_max     = _parse_int(max_text)

        raw = f"name={name_text!r} status={status_text!r} cur={cur_text!r} max={max_text!r}"
        if name is not None or hp_current is not None:
            members.append(PartyMemberResult(
                name=name,
                level=level,
                hp_current=hp_current,
                hp_max=hp_max,
                status=status,
                raw_text=raw,
                slot_index=i,
            ))
    return members
