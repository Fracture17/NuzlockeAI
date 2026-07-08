# Emulator I/O for battle decisions: key presses, party navigation, and screen-kind dispatch.
from __future__ import annotations

import re
import time
from pathlib import Path

from rapidfuzz.distance import Levenshtein as _Lev

from liveplay.data.moves import Move
from liveplay.battle_message_matcher import ScreenKind
from liveplay.vision.regions import (
    PARTY_SLOTS,
    PARTY_SLOT_NAME, PARTY_SLOT_STATUS, PARTY_SLOT_HP_CURRENT, PARTY_SLOT_HP_MAX,
    PARTY_SLOT_ROW_NAME, PARTY_SLOT_ROW_STATUS, PARTY_SLOT_ROW_HP_CURRENT, PARTY_SLOT_ROW_HP_MAX,
)
from liveplay.vision.ocr import read_party_menu
from liveplay.vision.capture import ScreenCapture

_CAPTURE_OUT = Path("/tmp/vision")

# ---------------------------------------------------------------------------
# Timing constants (verbatim from play.py ~143-145)
# ---------------------------------------------------------------------------

_FIGHT_OPEN_WAIT = 0.5  # seconds to wait for fight submenu to fully open
_NAV_HOLD = 0.1         # seconds to hold a nav key (~6 frames)
_NAV_GAP = 0.3          # seconds between consecutive nav presses

# ---------------------------------------------------------------------------
# Key-press helpers (verbatim from play.py ~132-156)
# ---------------------------------------------------------------------------

def _press(socket, key: str) -> None:
    """Register a key press using add_key/clear_key (safe inside frame callback).

    No explicit sleep needed: the TCP round-trip to the Lua frame callback (~17ms at 60fps)
    gives the game at least one frame to register the key before clear_key fires.
    tap() must not be used — it calls emu:runFrame() inside the frame callback, crashing mGBA.
    """
    socket.add_key(key)
    socket.clear_key(key)


def _press_held(socket, key: str) -> None:
    """Hold a key for multiple frames before releasing.

    Sleeping between add_key and clear_key ensures the key is held long enough
    for JOY_NEW edge detection even if fight-menu opening adds a latency frame.
    """
    socket.add_key(key)
    time.sleep(_NAV_HOLD)
    socket.clear_key(key)

# ---------------------------------------------------------------------------
# Move input (verbatim from play.py ~159-180)
# ---------------------------------------------------------------------------

def _send_move_input(socket, move_slot: int) -> None:
    """Press A→Fight, normalize cursor to slot 0, navigate to move_slot, press A.

    No wrapping occurs in the move select grid. The cursor persists between turns,
    so we always normalize to (0,0) with UP+LEFT before navigating to the target.
    """
    tgt_row, tgt_col = divmod(move_slot, 2)
    _press(socket, "a")
    time.sleep(_FIGHT_OPEN_WAIT)
    _press_held(socket, "up")
    time.sleep(_NAV_GAP)
    _press_held(socket, "left")
    time.sleep(_NAV_GAP)
    for _ in range(tgt_row):
        _press_held(socket, "down")
        time.sleep(_NAV_GAP)
    for _ in range(tgt_col):
        _press_held(socket, "right")
        time.sleep(_NAV_GAP)
    time.sleep(_NAV_GAP)
    _press(socket, "a")
    print(f"[input] Move slot {move_slot} (row={tgt_row} col={tgt_col})", flush=True)

# ---------------------------------------------------------------------------
# Party OCR helpers (verbatim from play.py ~183-307)
# ---------------------------------------------------------------------------

_PARTY_SUBREGIONS_SLOT1 = (
    ("name",   PARTY_SLOT_NAME),
    ("status", PARTY_SLOT_STATUS),
    ("hp_cur", PARTY_SLOT_HP_CURRENT),
    ("hp_max", PARTY_SLOT_HP_MAX),
)

_PARTY_SUBREGIONS_ROW = (
    ("name",   PARTY_SLOT_ROW_NAME),
    ("status", PARTY_SLOT_ROW_STATUS),
    ("hp_cur", PARTY_SLOT_ROW_HP_CURRENT),
    ("hp_max", PARTY_SLOT_ROW_HP_MAX),
)


def _read_party_members(screen_capture: ScreenCapture):
    """Capture each party slot, save all crops to /tmp/vision/, and OCR all visible members."""
    slot_images = [screen_capture.capture(*slot) for slot in PARTY_SLOTS]
    out = _CAPTURE_OUT
    for i, img in enumerate(slot_images):
        img.save(out / f"party_slot_{i}.png")
        subregions = _PARTY_SUBREGIONS_SLOT1 if i == 0 else _PARTY_SUBREGIONS_ROW
        for label, (x, y, w, h) in subregions:
            img.crop((x, y, x + w, y + h)).save(out / f"party_slot_{i}_{label}.png")
    return read_party_menu(slot_images)

# ---------------------------------------------------------------------------
# Name-matching helper (pure — no I/O)
# ---------------------------------------------------------------------------

# Regional / form suffixes carried by the Species enum name but NOT shown in the
# in-game party menu (which displays the base species name). Stripped before
# matching so e.g. "ZIGZAGOON_GALAR" matches the menu's "Zigzagoon".
_FORM_SUFFIX_RE = re.compile(r"_(GALAR|ALOLA|HISUI|PALDEA|GMAX|MEGA_X|MEGA_Y|MEGA)$")


def _strip_form_suffix(name: str | None) -> str:
    """Remove a trailing regional/form suffix (e.g. _GALAR) from a species name."""
    if name is None:
        return ""
    return _FORM_SUFFIX_RE.sub("", name.upper())


def _normalize_name(name: str | None) -> str:
    """Uppercase, drop a regional/form suffix, and strip all non-alphanumeric chars."""
    if name is None:
        return ""
    return re.sub(r"[^A-Z0-9]", "", _strip_form_suffix(name))


def find_member_by_name(members: list, species_name: str):
    """Return the PartyMemberResult whose OCR name best matches species_name via fuzzy match.

    Exact normalized match wins; else pick closest by Levenshtein with a length-scaled threshold.
    Raises RuntimeError if nothing is within threshold.
    """
    norm_target = _normalize_name(species_name)
    norm_members = [(_normalize_name(m.name), m) for m in members]

    # Exact match first
    for norm, member in norm_members:
        if norm == norm_target:
            return member

    # Fuzzy fallback
    best_norm, best_member = min(norm_members, key=lambda t: _Lev.distance(t[0], norm_target))
    threshold = max(2, len(norm_target) // 4)
    if _Lev.distance(best_norm, norm_target) <= threshold:
        return best_member

    raise RuntimeError(
        f"[party] No party member matches {species_name!r} (normalized: {norm_target!r}); "
        f"members: {[m.name for m in members]}"
    )

# ---------------------------------------------------------------------------
# Party selection executor
# ---------------------------------------------------------------------------

def send_party_selection(socket, members, target_species: str) -> None:
    """Navigate party menu to target_species and select it (two A presses)."""
    target = find_member_by_name(members, target_species)
    print(f"[party] Selecting slot {target.slot_index}: {target.name}", flush=True)
    for _ in range(target.slot_index):
        _press_held(socket, "down")
        time.sleep(_NAV_GAP)
    _press(socket, "a")
    time.sleep(_NAV_GAP)
    _press(socket, "a")

# ---------------------------------------------------------------------------
# Shared screen handler
# ---------------------------------------------------------------------------

def handle_battle_screen(socket, screen_capture, screen_kind: ScreenKind,
                         battle_state, policy, pending_switch_ref: list) -> None:
    """Dispatch battle input for a screen-kind edge transition.

    pending_switch_ref is a one-element list [species_name | None] owned by the caller.
    Called only on edge transitions; caller manages last_screen_kind guarding.
    """
    if screen_kind == ScreenKind.OPTION_SELECT:
        action = policy.choose_battle_action(battle_state)
        if isinstance(action, Move):
            active = battle_state.sides[0].team[battle_state.sides[0].active_indices[0]]
            try:
                slot = active.move_ids.index(action)
            except ValueError:
                raise RuntimeError(
                    f"[battle_input] Move {action.name!r} is not in the active Pokémon's moveset: "
                    f"{list(active.move_ids)}"
                )
            _send_move_input(socket, slot)
            pending_switch_ref[0] = None
        else:
            # action is a species name str — voluntary switch
            pending_switch_ref[0] = action
            _press_held(socket, "down")  # Fight -> Pokémon cursor navigation
            time.sleep(_NAV_GAP)
            _press(socket, "a")
            # The PARTY_MENU handler's own 1s fade-in wait covers party-menu load.

    elif screen_kind == ScreenKind.PARTY_MENU:
        time.sleep(1.0)  # wait for fade-in transition to complete
        screen_capture.invalidate()
        members = _read_party_members(screen_capture)
        print(f"[party] Detected {len(members)} member(s):", flush=True)
        for m in members:
            print(f"  [{m.slot_index}] raw={m.raw_text!r}", flush=True)
            print(f"         {m.name}  Lv{m.level}  HP {m.hp_current}/{m.hp_max}  {m.status or ''}", flush=True)

        if pending_switch_ref[0] is not None:
            send_party_selection(socket, members, pending_switch_ref[0])
            pending_switch_ref[0] = None
        else:
            target = policy.choose_forced_switch(battle_state)
            send_party_selection(socket, members, target)
