"""
Launch mGBA for normal play. L toggles periodic screenshot capture (0.1/sec).
Turn events print automatically when the option-select screen is detected.
Press Ctrl+C to quit.

    python SCRIPTS/play.py
"""

import argparse
import dataclasses
import json
import pickle
import re
import shutil
import sys
import time
import traceback
import datetime
from pathlib import Path
from typing import IO

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from _shared import _Tee  # noqa: E402
from liveplay.emulator import MGBAProcess, MGBAConnectionError
from liveplay.emulator.battle_input import _press, handle_battle_screen
from liveplay.vision.regions import (
    BATTLE_MESSAGE, OPPONENT_HP_BAR, PLAYER_HP,
)
from liveplay.vision.ocr import read_battle_message, read_player_info, read_opponent_info, read_party_prompt
from liveplay.vision.capture import ScreenCapture
from liveplay.vision.hp_bar import read_opponent_hp_bar
from liveplay.battle_message_matcher import (
    BattleMessageMatcher, MatchResult, ScreenKind, ScreenSignal,
)
from liveplay.battle_types import Constraints
from liveplay.battle_types import ActionGroup, HpReading
from liveplay.battle_constants import PRIMARY_STRING_IDS, turn_has_real_action
from liveplay.state.battle import BattleState
from liveplay.state.side import SideState
from liveplay.data.species import Species, SPECIES_DATA
from liveplay.data.growth_rate import level_from_exp
from liveplay.data.natures import Nature
from liveplay.data.status import Status
from liveplay.data.moves import Move, MOVE_DATA
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.trainer import load_trainers, iv_tuple
from liveplay.data.name_aliases import ENUM_ALIASES, emulator_species_name
from liveplay.state.pokemon import PokemonState, GenderEnum
from liveplay.emulator.pokemon_snapshot import PokemonSnapshot
from liveplay.emulator.gba_items import GBA_ITEM_MAP
from liveplay.emulator.gba_moves import GBA_MOVE_MAP
from liveplay.emulator.gba_abilities import SPECIES_ABILITIES
from liveplay.hp_stability import OpponentHpBuffer, PlayerHpBuffer
from liveplay.hp_delta import HpDeltaSeq, build_faint_record_from_klog
from liveplay.battle_policy import RandomPolicy
from liveplay.candidate import Candidate
from liveplay.candidate_tracker import CandidateTracker
from liveplay.rng import UninjectedRNGError
from liveplay.engine_select import SimulationError
from liveplay.sweep_recorder import SweepRecorder, record_and_run
from rapidfuzz.distance import Levenshtein as _Lev

_CAPTURE_DIR = Path("/tmp/vision/captures")
# Created at import so any entry point that uses _do_capture (e.g. stress_test.py)
# is safe — not just play.main(). parents=True also creates _OUT (/tmp/vision).
_CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
_BATTLE_SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "CurrentBattle.pkl"
_TRAINING_DATA_DIR = Path(__file__).resolve().parent.parent / "TrainingData"
_CURRENT_RESOURCES_PATH = Path(__file__).resolve().parent.parent / "CurrentResources.json"
_PLAY_LOG_DIR = Path("/tmp/vision/play")


_verbose_log: IO | None = None


def _vlog(msg: str) -> None:
    """Write a verbose-only message to the log file, not to the terminal."""
    if _verbose_log is not None:
        _verbose_log.write(msg + "\n")
        _verbose_log.flush()


# String IDs that signal the PLAYER sent out a new Pokemon — triggers HP baseline reset.
_PLAYER_SWITCH_IN_IDS: frozenset[str] = frozenset({
    "STRINGID_PLAYER_SWITCHINMON",
    "STRINGID_PLAYER_INTROSENDOUT",
})
# String IDs that signal the OPPONENT sent out a new Pokemon — triggers that mon's HP baseline reset.
_OPPONENT_SWITCH_IN_IDS: frozenset[str] = frozenset({
    "STRINGID_SWITCHINMON",
    "STRINGID_INTROSENDOUT",
})
# Placeholder names that carry the switched-in opponent Pokémon's name.
_OPP_NAME_SLOTS: frozenset[str] = frozenset({
    "B_OPPONENT_MON1_NAME",
    "B_OPPONENT_MON2_NAME",
    "B_BUFF1",
})
# String IDs that mark the end of the battle (win or loss).
_BATTLE_END_IDS: frozenset[str] = frozenset({
    "STRINGID_BATTLEEND",
    "STRINGID_PLAYERWHITEOUT",
    "STRINGID_PLAYERWHITEOUT2",
})
_CAPTURE_INTERVAL = 0.04  # seconds between screenshots (25 Hz; OCR is ~12ms so the loop keeps up)
_B_PRESS_INTERVAL = 0.5     # seconds between B presses while advancing battle text


def _extract_opponent_names(result: MatchResult) -> list[str]:
    """Return lowercased names of all opponent Pokémon from a switch-in MatchResult.

    Handles both intro send-outs (B_OPPONENT_MON1/2_NAME) and mid-battle
    switches (B_BUFF1). Used to key which HP buffer(s) to reset.
    """
    return [
        val.lower()
        for label, val in zip(result.slot_labels, result.var_values)
        if label in _OPP_NAME_SLOTS and val
    ]


def _select_active_opp_klog(opp_k_logs: dict, active_name: str) -> list:
    """Return the k-pixel HP log for the currently-active opponent.

    ``opp_k_logs`` is keyed by lowercased OCR names and accumulates stale entries
    for opponents that already fainted/switched out. Picking an arbitrary entry
    (e.g. ``next(iter(...))``) can return the wrong mon's log and silently zero out
    HP deltas. Resolve against the active opponent's species name: exact match
    first, then a fuzzy fallback (closest key within a small edit distance), else
    raise — logs exist but none plausibly belong to the active mon, which signals
    a capture/name bug we want to surface loudly rather than mask as "no damage".
    """
    if not opp_k_logs:
        return []
    active = active_name.lower()
    if active in opp_k_logs:
        return opp_k_logs[active]
    # Fuzzy fallback: closest key within a length-scaled threshold.
    best = min(opp_k_logs, key=lambda n: _Lev.distance(n, active))
    threshold = max(2, len(active) // 4)
    if _Lev.distance(best, active) <= threshold:
        return opp_k_logs[best]
    raise RuntimeError(
        f"[sweep] No opponent HP log matches active opponent {active_name!r}; "
        f"have keys {sorted(opp_k_logs)}. Capture/name mismatch — refusing to "
        f"proceed with wrong HP deltas."
    )


# Slot labels that carry the switched-in PLAYER Pokémon's name on a send-out message.
_PLAYER_NAME_SLOTS: frozenset[str] = frozenset({"B_BUFF1"})


def _extract_player_names(result: MatchResult) -> list[str]:
    """Return lowercased names of player Pokémon from a player send-out MatchResult.

    Mirrors _extract_opponent_names: used to key which player HP buffer(s) to reset
    when the player sends out a new mon (so only the incoming mon's baseline clears).
    """
    return [
        val.lower()
        for label, val in zip(result.slot_labels, result.var_values)
        if label in _PLAYER_NAME_SLOTS and val
    ]


def _resolve_team_mon(name: str, team: list) -> tuple:
    """Resolve a lowercased OCR name to a (mon, team_idx) in ``team`` by species name.

    Exact species-name match first, then a length-scaled fuzzy fallback (the player
    box can mis-OCR a glyph), else raise. Player mons are assumed un-nicknamed in this
    setup (OCR names are validated against species elsewhere); a name that resolves to
    no team species signals a capture/nickname mismatch we surface loudly rather than
    silently mis-attribute HP to the wrong mon.
    """
    target = name.lower()
    # Match against the base display name (emulator_species_name) so regional forms
    # (e.g. ZIGZAGOON_GALAR) resolve from their in-game name ('zigzagoon'); the raw
    # enum name's '_GALAR' suffix would otherwise blow past the fuzzy threshold.
    def _disp(mon) -> str:
        return emulator_species_name(mon.species).lower()
    for idx, mon in enumerate(team):
        if _disp(mon) == target:
            return mon, idx
    best_idx = min(range(len(team)), key=lambda i: _Lev.distance(_disp(team[i]), target))
    if _Lev.distance(_disp(team[best_idx]), target) <= max(2, len(target) // 4):
        return team[best_idx], best_idx
    raise RuntimeError(
        f"[sweep] No player team mon matches HP-log name {name!r}; have species "
        f"{[m.species.name for m in team]}. Capture/nickname mismatch — refusing to "
        f"proceed with wrong HP deltas."
    )


def _canonical_team_key(name: str, team: list) -> str:
    """Canonicalize a raw OCR name to a stable per-species key for HP-log/buffer dicts.

    When the team roster is known, resolve ``name`` to a team mon (exact species-display
    match, then fuzzy) and return that mon's canonical display name — so OCR jitter across
    frames collapses to ONE key and an unresolvable name fails loud (per _resolve_team_mon)
    instead of silently creating a phantom log. Before the battle state is populated the
    team is empty (pre-battle stub); there is nothing to resolve, so fall back to the raw
    lowercased name and do NOT raise.
    """
    if not team:
        return name.lower()
    mon, _ = _resolve_team_mon(name, team)
    return emulator_species_name(mon.species).lower()


_TEXT_COLORS = {(255, 255, 255), (74, 74, 74), (66, 66, 66)}
_OUT = _CAPTURE_DIR.parent


def _text_mask(img) -> np.ndarray:
    """Boolean mask: True where a pixel is a known text color."""
    arr = np.array(img.convert("RGB"))
    mask = np.zeros(arr.shape[:2], dtype=bool)
    for r, g, b in _TEXT_COLORS:
        mask |= (arr[:, :, 0] == r) & (arr[:, :, 1] == g) & (arr[:, :, 2] == b)
    return mask


def _first_text_col(mask: np.ndarray) -> int | None:
    """Return the leftmost column containing any text pixel, or None."""
    cols = np.where(mask.any(axis=0))[0]
    return int(cols[0]) if len(cols) else None


def _col_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Return (x_start, x_end) inclusive runs of columns that contain text pixels."""
    col_has_text = mask.any(axis=0)
    runs, in_run, start = [], False, 0
    for x, has in enumerate(col_has_text):
        if has and not in_run:
            in_run, start = True, x
        elif not has and in_run:
            runs.append((start, x - 1))
            in_run = False
    if in_run:
        runs.append((start, len(col_has_text) - 1))
    return runs


def _text_row_range(mask: np.ndarray, x0: int, x1: int) -> tuple[int, int] | None:
    """Return (y_min, y_max) of text pixels within columns x0..x1, or None."""
    band = mask[:, x0:x1 + 1]
    rows = np.where(band.any(axis=1))[0]
    return (int(rows[0]), int(rows[-1])) if len(rows) else None


def _save_region_crops(battle_msg_img, player_img, opp_img) -> None:
    """Save battle-region crops to /tmp/vision/ and print text-position diagnostics."""
    battle_msg_img.save(_OUT / "region_battle_msg.png")
    player_img.save(_OUT / "region_player_hp.png")
    opp_img.save(_OUT / "region_opp_hp.png")

    player_mask = _text_mask(player_img)
    opp_mask    = _text_mask(opp_img)

    player_col = _first_text_col(player_mask)
    opp_col    = _first_text_col(opp_mask)
    _vlog(f"[crops] player first_text_col={player_col}  opp first_text_col={opp_col}")

    # Report each contiguous column-run in the player HP region with its row span.
    # Runs separated by ≤2 blank columns are merged (avoids splitting one digit group).
    raw_runs = _col_runs(player_mask)
    merged: list[tuple[int, int]] = []
    for run in raw_runs:
        if merged and run[0] - merged[-1][1] <= 2:
            merged[-1] = (merged[-1][0], run[1])
        else:
            merged.append(list(run))
    merged = [tuple(r) for r in merged]

    parts = []
    for x0, x1 in merged:
        yr = _text_row_range(player_mask, x0, x1)
        parts.append(f"x={x0}-{x1} y={yr[0]}-{yr[1]}" if yr else f"x={x0}-{x1} y=?")
    _vlog(f"[crops] player text runs: {parts}")


def _gba_status_to_engine(gba_status: int) -> Status:
    """Map GBA status bitmask to engine Status enum."""
    if gba_status & 0x07:
        return Status.SLEEP
    if gba_status & 0x80:
        return Status.TOXIC
    if gba_status & 0x40:
        return Status.PARALYSIS
    if gba_status & 0x20:
        return Status.FREEZE
    if gba_status & 0x10:
        return Status.BURN
    if gba_status & 0x08:
        return Status.POISON
    return Status.NONE


_MISSING = object()


def _lookup_enum(enum_cls, name: str, default=_MISSING):
    """Look up an enum member by name.

    An override alias (keyed by the raw external name) wins first; otherwise the
    name is normalized (spaces/hyphens -> underscores) for a direct member lookup.
    If neither resolves and no default is given, raise — never silently fall back
    to NONE, so unmatched trainer data surfaces loudly.
    """
    alias_map = ENUM_ALIASES.get(enum_cls)
    if alias_map is not None and name in alias_map:
        return alias_map[name]
    key = name.upper().replace(" ", "_").replace("-", "_")
    result = enum_cls.__members__.get(key, _MISSING)
    if result is _MISSING:
        if default is not _MISSING:
            return default
        raise ValueError(f"{enum_cls.__name__} has no member {key!r} (normalized from {name!r})")
    return result


def _resolve_ability(species: Species, alt_ability: int) -> Ability:
    """Resolve a mon's ability from its species and ability-slot index.

    Mirrors the game's GetAbilityBySpecies: the alt_ability bit selects an ability
    slot, but slots the species doesn't fill are stored as ABILITY_NONE. The game
    falls back to slot 0 in that case (a valid mon never has a NONE ability), so we
    do the same — otherwise a single-ability species like Skitty (NORMALIZE in slot 0
    only) whose alt_ability bit reads 1 would be left with Ability.NONE.
    """
    slots = SPECIES_ABILITIES.get(species, (Ability.NONE, Ability.NONE, Ability.NONE))
    ability = slots[alt_ability] if 0 <= alt_ability < len(slots) else Ability.NONE
    if ability == Ability.NONE and alt_ability != 0:
        ability = slots[0]
    return ability


def _move_from_gba_id(move_id: int) -> Move:
    """Translate a raw GBA (Run & Bun) move ID to the Move enum.

    Move IDs read from ROM memory use R&B's internal numbering, which only
    matches the Showdown-based Move enum for vanilla moves; GBA_MOVE_MAP bridges
    the rest. An unmapped ID has no engine equivalent and fails loud."""
    if move_id == 0:
        return Move.NONE
    try:
        return GBA_MOVE_MAP[move_id]
    except KeyError as e:
        raise ValueError(f"unmapped GBA move id {move_id}") from e


def _snapshot_to_pokemon_state(snap: PokemonSnapshot) -> PokemonState:
    """Convert a live party PokemonSnapshot to a PokemonState."""
    try:
        species = Species(snap.species)
        nature = Nature(snap.nature)
        # Engine IV order: (hp, atk, def, spa, spd, spe)
        # Snapshot fields: hp_iv, atk_iv, def_iv, spe_iv, spa_iv, spd_iv (spe/spa swapped)
        ivs = (snap.hp_iv, snap.atk_iv, snap.def_iv, snap.spa_iv, snap.spd_iv, snap.spe_iv)
        # Party mons store their level directly; box mons do not, so derive it from EXP.
        if snap.level is not None:
            level = snap.level
        else:
            level = level_from_exp(SPECIES_DATA[species].growth_rate, snap.experience)
        move_ids = tuple(_move_from_gba_id(m) for m in snap.moves)
        move_pp = snap.pp
        status = _gba_status_to_engine(snap.status or 0)
        hp = snap.current_hp
        return PokemonState(
            species=species,
            nature=nature,
            ivs=ivs,
            gender=GenderEnum.MALE,  # TODO: compute from personality and species gender ratio
            level=level,
            exp=snap.experience,
            ability=_resolve_ability(species, snap.alt_ability),
            item=GBA_ITEM_MAP.get(snap.held_item, Item.NONE),
            status=status,
            move_ids=move_ids,
            move_pp=move_pp,
            hp=hp,
        )
    except ValueError as e:
        raise ValueError(f"[snapshot_to_pokemon_state] species_id={snap.species}: {e}") from e


def _max_pp(base_pp: int) -> int:
    """Maximum PP for a move with 3 PP Ups applied (each adds 20% of base)."""
    return base_pp + (base_pp // 5) * 3


def _trainer_pokemon_to_state(tp) -> PokemonState:
    """Convert a trainer.Pokemon from parsed trainer data to a PokemonState."""
    species = _lookup_enum(Species, tp.name)
    nature = _lookup_enum(Nature, tp.nature)
    ability = _lookup_enum(Ability, tp.ability) if tp.ability else Ability.NONE
    item = _lookup_enum(Item, tp.item) if tp.item else Item.NONE
    raw_moves = [_lookup_enum(Move, m) if m else Move.NONE for m in tp.moves]
    # Pad to 4 slots with Move.NONE
    while len(raw_moves) < 4:
        raw_moves.append(Move.NONE)
    move_ids = tuple(raw_moves[:4])
    # Opponent PP is unobservable in-game. Run & Bun trainer mons get a single PP Up
    # bundle applied to their FIRST move slot only (max PP), with the remaining slots
    # at base PP. Under-estimating slot 0's PP wrongly marks an observed move illegal
    # and crashes the sweep; matching the convention keeps the estimate correct.
    move_pp = tuple(
        (_max_pp(MOVE_DATA[m].pp) if i == 0 else MOVE_DATA[m].pp) if m != Move.NONE else 0
        for i, m in enumerate(move_ids)
    )
    return PokemonState(
        species=species,
        nature=nature,
        ivs=iv_tuple(getattr(tp, "ivs", {})),  # calc IVs; missing stats default to 31
        gender=GenderEnum.MALE,
        level=tp.level,
        ability=ability,
        item=item,
        move_ids=move_ids,
        move_pp=move_pp,
    )


def _split_trainer_name(name: str) -> tuple[str, str]:
    """Split a trainer pkl name into (class, name) matching the in-game intro display.

    Trainer pkl names carry Run & Bun bracket annotations ([Boss], [Double],
    [Double Battle With ...]) that never appear in-game; strip them before splitting
    so the rejoined class+name equals the intro text ('<class> <name> would like to
    battle!'). The split point is cosmetic — the matcher rejoins the pair.
    """
    display = re.sub(r"\s*\[[^\]]*\]\s*$", "", name).strip()
    parts = display.rsplit(" ", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return display, ""


def _valid_pokemon_names(all_mons) -> list[str]:
    """Species names for the matcher's valid_pokemon constraint.

    Regional/form species (Galarian, Alolan, Hisuian, etc.) are displayed by the emulator
    under their BASE name, so the constraint must use the emulator display name rather than
    the enum member name (e.g. ZIGZAGOON_GALAR -> ZIGZAGOON). Otherwise the OCR'd send-out
    message 'Go! Zigzagoon!' fails to match the form member name and crashes the matcher.
    """
    return [emulator_species_name(mon.species).upper() for mon in all_mons]


def _snapshots_to_states(snapshots) -> list[PokemonState]:
    """Convert party/box snapshots to PokemonStates, skipping eggs and empty slots."""
    return [
        _snapshot_to_pokemon_state(snap)
        for snap in snapshots
        if not snap.is_egg and snap.has_species
    ]


def _save_training_snapshot(
    folder: Path,
    battle_state: BattleState,
    box_mons: list[PokemonState],
    opponent_index: int,
    level_cap: int,
    resources_path: Path = _CURRENT_RESOURCES_PATH,
) -> None:
    """Write a training-data snapshot into `folder`.

    BattleState holds the player party (sides[0]), opponent team (sides[1]) and
    level cap; box pokemon and a verbatim copy of the resources file are stored
    alongside it. Raises if the resources file is missing (fail loud)."""
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "battle_state.pkl").open("wb") as f:
        pickle.dump(battle_state, f)
    with (folder / "box.pkl").open("wb") as f:
        pickle.dump(box_mons, f)
    with (folder / "config.json").open("w") as f:
        json.dump({"opponent_index": opponent_index, "level_cap": level_cap}, f)
    shutil.copy(resources_path, folder / resources_path.name)


def _build_battle_state(opponent_idx: int, socket, level_cap: int) -> tuple[BattleState, Constraints]:
    """Build a BattleState from trainer data and live party snapshot. Raises on invalid inputs."""
    trainers = load_trainers()
    if opponent_idx >= len(trainers):
        raise IndexError(f"opponent_idx={opponent_idx} out of range (len={len(trainers)})")

    trainer = trainers[opponent_idx]
    trainer_class, trainer_name = _split_trainer_name(trainer.name)
    opponent_mons = [_trainer_pokemon_to_state(tp) for tp in trainer.pokemon]

    player_mons = _snapshots_to_states(socket.read_party())

    if not player_mons:
        print("[state] WARNING: player team is empty")

    all_mons = opponent_mons + player_mons
    valid_pokemon = _valid_pokemon_names(all_mons)
    valid_items = [
        mon.item.name.upper() for mon in all_mons
        if mon.item is not None and mon.item.name != "NONE"
    ]
    valid_abilities = [
        mon.ability.name.upper() for mon in all_mons
        if mon.ability is not None and mon.ability.name != "NONE"
    ]

    valid_moves = [
        move.name.replace("_", " ")
        for mon in all_mons
        for move in mon.move_ids
        if move is not Move.NONE
    ]

    constraints = Constraints(
        trainer_class=trainer_class,
        trainer_name=trainer_name,
        valid_pokemon=valid_pokemon or None,
        valid_items=valid_items or None,
        valid_abilities=valid_abilities or None,
        valid_moves=valid_moves or None,
    )

    player_side = SideState(team=player_mons, active_indices=[0])
    opponent_side = SideState(team=opponent_mons, active_indices=[0])
    return BattleState(sides=(player_side, opponent_side), level_cap=level_cap), constraints


def _make_stub_battle_state() -> BattleState:
    """Create a minimal valid BattleState with empty teams.

    TODO: replace with real state constructed from trainer/team data.
    """
    return BattleState(sides=(SideState(team=[], active_indices=[]), SideState(team=[], active_indices=[])))


def _make_constraints_for_active(state: BattleState, base_constraints: Constraints) -> Constraints:
    """Return a copy of base_constraints with unconstrained flags set from the active Pokémon."""
    active_mons: list = []
    for side in state.sides:
        for idx in side.active_indices:
            if 0 <= idx < len(side.team):
                active_mons.append(side.team[idx])

    unconstrained_moves = any(
        Move.METRONOME in mon.move_ids or Move.ASSIST in mon.move_ids
        for mon in active_mons
    )
    unconstrained_names = any(
        Move.TRANSFORM in mon.move_ids or mon.ability == Ability.ILLUSION
        for mon in active_mons
    )
    return dataclasses.replace(
        base_constraints,
        unconstrained_moves=unconstrained_moves,
        unconstrained_names=unconstrained_names,
    )



def _print_turn(current_turn: list[dict]) -> None:
    """Print all events in the current turn, grouped into action groups."""
    if not current_turn:
        return
    print("\n=== Turn events ===")

    # Group messages into action groups using primary message set
    groups: list[ActionGroup] = []
    current_group: ActionGroup | None = None
    for entry in current_turn:
        match: MatchResult = entry["match"]
        if match.string_id in PRIMARY_STRING_IDS or current_group is None:
            if current_group is not None:
                groups.append(current_group)
            current_group = ActionGroup(primary=match, secondaries=[])
        else:
            current_group.secondaries.append(match)
    if current_group is not None:
        groups.append(current_group)

    # Associate HP readings with groups by replaying the same grouping logic
    gidx = 0
    first_entry = True
    for entry in current_turn:
        match = entry["match"]
        if match.string_id in PRIMARY_STRING_IDS and not first_entry:
            if gidx < len(groups) - 1:
                gidx += 1
        first_entry = False
        groups[gidx].hp_readings.append(entry["opponent_hp"])

    for group in groups:
        p = group.primary
        label = p.string_id.replace("STRINGID_", "")
        print(f"  [PRIMARY] {label:<22}  {p.matched_text}")
        for slot, val in zip(p.slot_labels, p.var_values):
            slot_display = slot[2:] if slot.startswith("B_") else slot
            print(f"    {slot_display}: {val}")
        for s in group.secondaries:
            slabel = s.string_id.replace("STRINGID_", "")
            print(f"    [+] {slabel:<20}  {s.matched_text}")
            for slot, val in zip(s.slot_labels, s.var_values):
                slot_display = slot[2:] if slot.startswith("B_") else slot
                print(f"        {slot_display}: {val}")


def _candidate_state_summary(state) -> dict:
    """Compact JSON-friendly snapshot of a candidate BattleState for error dumps."""
    def _mon(m):
        return {
            "species": m.species.name,
            "level": m.level,
            "hp": m.hp,
            "max_hp": m.max_hp,
            "status": m.status.name,
            "stat_stages": list(m.stat_stages),
            "volatiles": int(m.volatiles),
            "moves": [mv.name for mv in m.move_ids if mv.name != "NONE"],
            "stats": list(m.stats),
            "ability": m.ability.name,
        }
    return {
        "weather": state.weather.name,
        "sides": [
            {
                "active_indices": list(side.active_indices),
                "team": [_mon(m) for m in side.team],
            }
            for side in state.sides
        ],
    }


def _active_opp_name(opp_side) -> str:
    """Return the active opponent mon's species name, or raise on desync.

    Raises RuntimeError when active_indices is non-empty but the slot exceeds team length
    (genuine desync — continuing would silently corrupt HP reconciliation).
    Empty active_indices is a legitimate pre-battle state; defaults to slot 0 with an
    empty-string fallback when the team is also empty.
    """
    opp_active = opp_side.active_indices[0] if opp_side.active_indices else 0
    if opp_side.active_indices and opp_active >= len(opp_side.team):
        raise RuntimeError(
            f"Opponent active slot {opp_active} out of range for team of "
            f"{len(opp_side.team)} (desync); cannot reconcile HP"
        )
    return opp_side.team[opp_active].species.name if opp_active < len(opp_side.team) else ""


def _run_turn_sweep(
    current_turn: list[dict],
    candidate_tracker_ref: list,
    opp_k_log_ref: list,
    player_hp_log_ref: list,
    player_hp_bufs: dict,
    opponent_hp_bufs: dict,
    battle_state_ref: list,
    recorder_ref: list,          # single-element list holding SweepRecorder for this battle
    foe_faint_deltas_ref: list,  # single-element list holding list[HpDeltaSeq] flushed mid-turn
) -> None:
    """Run simulation sweep for the completed turn and update the candidate tracker + battle state.

    Does nothing if tracker is None or has no candidates.
    Computes HP deltas from the accumulated stability-confirmed log lists and reseeds them
    with the current confirmed values for the next turn.
    Fatal on SimulationError/UninjectedRNGError — invalid state must halt.
    """
    if not current_turn:
        return  # still at the same decision boundary; sweep already ran for this turn
    tracker = candidate_tracker_ref[0]
    if tracker is None or not tracker.candidates:
        return

    recorder = recorder_ref[0] if recorder_ref else None
    if recorder is None:
        raise RuntimeError(
            "[sweep] No SweepRecorder available — battle started before recorder was created. "
            "Cannot run unrecorded sweep."
        )

    messages = [entry["match"] for entry in current_turn]

    opp_k_logs = opp_k_log_ref[0]      # dict[str, list[int]]
    player_logs = player_hp_log_ref[0]  # dict[str, list[int]]

    state = tracker.candidates[0].state
    opp_side = state.sides[1]
    active_opp_name = _active_opp_name(opp_side)
    opp_active = opp_side.active_indices[0] if opp_side.active_indices else 0
    # Use the canonical display name as the lookup key — matches the write side's canonical key.
    # _active_opp_name returns the raw enum name (e.g. "ZIGZAGOON_GALAR") which won't match.
    active_opp_display = (
        emulator_species_name(opp_side.team[opp_active].species).lower()
        if opp_active < len(opp_side.team)
        else active_opp_name
    )

    # Build identity-bound HP delta records (HpDeltaSeq) for the sweep. Each record
    # binds a mon's observed (before, after) sequence to its (side, species) so the
    # sweep validates it against the right mon even across mid-turn switches.
    hp_deltas: list[HpDeltaSeq] = []

    # Foe mons that fainted mid-turn and were replaced by a SAME-NAME mon: their k-log was
    # flushed at the send-out reset (before the shared name key was wiped) into this ref.
    # Drain it here so the killing move still has its HP constraint (Issue 29).
    hp_deltas.extend(foe_faint_deltas_ref[0])
    foe_faint_deltas_ref[0] = []

    # Opponent: the active mon's k-pixel log, keyed by the active mon's canonical display name.
    # (Mid-turn opponent faint/switch attribution is a separate concern; preserved as active-only.)
    # TODO: doubles will need separate per-slot records.
    k_log = _select_active_opp_klog(opp_k_logs, active_opp_display)
    if len(k_log) >= 2 and active_opp_name:
        opp_mon = opp_side.team[opp_active]
        hp_deltas.append(HpDeltaSeq(
            side=1, species=opp_mon.species, slot=0,
            deltas=tuple(zip(k_log, k_log[1:])), max_hp=opp_mon.max_hp,
        ))

    # Player: a per-species record for EVERY mon that changed HP this turn (the
    # outgoing mon's pre-switch deltas AND the incoming mon's deltas both survive,
    # because the player log is per-species and no longer discarded on switch).
    player_team = state.sides[0].team
    player_active = state.sides[0].active_indices
    for name, log in player_logs.items():
        if len(log) < 2:
            continue
        mon, team_idx = _resolve_team_mon(name, player_team)
        slot = player_active.index(team_idx) if team_idx in player_active else 0
        hp_deltas.append(HpDeltaSeq(
            side=0, species=mon.species, slot=slot,
            deltas=tuple(zip(log, log[1:])), max_hp=mon.max_hp,
        ))

    def _reseed_logs():
        opp_k_log_ref[0] = {
            name: ([buf.confirmed] if buf.confirmed is not None else [])
            for name, buf in opponent_hp_bufs.items()
        }
        player_hp_log_ref[0] = {
            name: ([buf.confirmed] if buf.confirmed is not None else [])
            for name, buf in player_hp_bufs.items()
        }

    try:
        new_candidates = record_and_run(
            recorder,
            messages=messages,
            hp_deltas=hp_deltas,
            initial_candidates=tracker.candidates,
        )
    except (SimulationError, UninjectedRNGError) as e:
        error_dir = Path("/tmp/vision/sweep_errors")
        error_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().isoformat(timespec="seconds").replace(":", "-")
        error_file = error_dir / f"{ts}.json"
        error_data = {
            "timestamp": ts,
            "error": str(e),
            "error_type": type(e).__name__,
            "messages": [dataclasses.asdict(m) for m in messages],
            "hp_deltas": [dataclasses.asdict(r) for r in hp_deltas],
            "n_initial_candidates": len(tracker.candidates),
            "initial_candidate_states": [
                _candidate_state_summary(c.state) for c in tracker.candidates[:5]
            ],
        }
        error_file.write_text(json.dumps(error_data, indent=2, default=str))
        print(f"[sweep] FATAL {type(e).__name__}: {e}", flush=True)
        print(f"[sweep] Error dump: {error_file}", flush=True)
        print(f"[sweep] Recording session: {recorder.session_dir}", flush=True)
        raise

    pruned = tracker.prune_empty(new_candidates)
    if pruned:
        print(f"[sweep] Pruned {len(pruned)} dead branch(es)", flush=True)
    tracker.update(new_candidates)
    tracker.deduplicate()

    if tracker.candidates:
        battle_state_ref[0] = tracker.candidates[0].state
        print(
            f"[sweep] {len(tracker)} candidate(s)  resolved={tracker.is_resolved}  "
            f"weather={battle_state_ref[0].weather.name}",
            flush=True,
        )

    _reseed_logs()


def _do_capture(
    screen_capture: ScreenCapture,
    matcher: BattleMessageMatcher,
    captures: list[dict],
    current_turn: list[dict],
    last_capture_time_ref: list[float],
    capture_active: bool,
    opponent_hp_bufs: dict,
    player_hp_bufs: dict,
    candidate_tracker_ref: list,  # single-element list holding CandidateTracker | None
    opp_k_log_ref: list,          # single-element list holding dict[str, list[int]] keyed by Pokémon name
    player_hp_log_ref: list,      # single-element list holding dict[str, list[int]] keyed by player species name
    battle_state_ref: list,       # single-element list holding the current BattleState
    constraints_ref: list,        # single-element list holding the current Constraints
    recorder_ref: list,           # single-element list holding SweepRecorder for this battle
    foe_faint_deltas_ref: list,   # single-element list holding list[HpDeltaSeq] flushed mid-turn
) -> tuple[bool, ScreenKind | None, str]:  # (battle_ended, screen_kind, ocr_text)
    """Take one screenshot, OCR it, match it, and append to captures if new."""
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    image_path = str(_CAPTURE_DIR / f"{timestamp}.png")

    # Force a fresh screenshot for this cycle: the capture interval (50ms) is
    # shorter than the frame-cache TTL (100ms), so without invalidating, the
    # first grab below would reuse the previous cycle's stale frame. After this,
    # the four grabs all share this one fresh frame (their TTL window).
    screen_capture.invalidate()

    # Capture all regions from one frame before running OCR, so the cache
    # TTL cannot expire between captures and produce a stale 2nd screenshot.
    # The party-prompt crop is included here for the same reason — it is only
    # examined when the battle message is empty, but it must be captured now.
    t0 = time.time()
    image          = screen_capture.capture(*BATTLE_MESSAGE)
    player_image   = screen_capture.capture(*PLAYER_HP)
    opponent_image = screen_capture.capture(*OPPONENT_HP_BAR)
    prompt_image   = screen_capture.capture(7, 138, 95, 13)
    image.save(image_path)
    text = read_battle_message(image).text
    elapsed_ms = int((time.time() - t0) * 1000)
    last_capture_time_ref[0] = time.time()
    _save_region_crops(image, player_image, opponent_image)
    player  = read_player_info(player_image)
    opp     = read_opponent_info(opponent_image)
    reading = read_opponent_hp_bar(opponent_image)
    opp_name = (opp.name or "").lower()
    if opp_name:
        opp_key = _canonical_team_key(opp_name, battle_state_ref[0].sides[1].team)
        opp_buf = opponent_hp_bufs.setdefault(opp_key, OpponentHpBuffer())
        if opp_buf.update(reading.k):
            k = opp_buf.confirmed
            name_log = opp_k_log_ref[0].setdefault(opp_key, [])
            if not name_log or name_log[-1] != k:
                name_log.append(k)
    player_name = (player.name or "").lower()
    if player_name:
        player_key = _canonical_team_key(player_name, battle_state_ref[0].sides[0].team)
        pl_buf = player_hp_bufs.setdefault(player_key, PlayerHpBuffer())
        if pl_buf.update(player.hp_current):
            hp = pl_buf.confirmed
            name_log = player_hp_log_ref[0].setdefault(player_key, [])
            if not name_log or name_log[-1] != hp:
                name_log.append(hp)

    words = text.split()
    _vlog(
        f"[{elapsed_ms}ms] {text!r}"
        f" | player={player.name} HP {player.hp_current}/{player.hp_max}"
        f" opp={opp.name}({opp.status}) bar_k={reading.k}"
    )

    def _record_match(finalized_result) -> bool:
        """Record a finalized MatchResult into captures/current_turn; return True if battle ended.

        No cross-frame dedup: prefix finalization emits each complete message exactly once,
        and a message legitimately repeated (across a turn boundary, or within a turn separated
        by a shorter partial) must be recorded every time it occurs.
        """
        entry = {
            "image_path":      image_path,
            "ocr_text":        text,
            "match":           finalized_result,
            "player":          player,
            "opponent_name":   opp.name,
            "opponent_status": opp.status,
            "opponent_hp":     reading,
        }
        captures.append(entry)
        current_turn.append(entry)

        # Reset the switched-in player mon's HP baseline by name, preserving other
        # mons' logs (so the outgoing mon's pre-switch deltas survive this turn).
        if finalized_result.string_id in _PLAYER_SWITCH_IN_IDS:
            for name in _extract_player_names(finalized_result):
                key = _canonical_team_key(name, battle_state_ref[0].sides[0].team)
                player_hp_log_ref[0][key] = []
                buf = player_hp_bufs.get(key)
                if buf is not None:
                    buf.reset()

        # Reset the switched-in opponent's HP baseline by name, preserving other slots.
        if finalized_result.string_id in _OPPONENT_SWITCH_IN_IDS:
            for name in _extract_opponent_names(finalized_result):
                # The opponent log is keyed by species name. A SAME-NAME replacement (e.g. a
                # 2nd Magikarp sent out after the first faints this turn) would otherwise wipe
                # the fainted mon's readings here before the end-of-turn sweep builds its record.
                # Bind those readings to the OUTGOING (still-active, pre-switch) foe's identity
                # now, so the killing move keeps its HP constraint (Issue 29).
                bs = battle_state_ref[0]
                foe_side = bs.sides[1] if bs and len(bs.sides) > 1 else None
                key = _canonical_team_key(name, foe_side.team if foe_side is not None else [])
                if foe_side is not None and foe_side.active_indices:
                    outgoing = foe_side.team[foe_side.active_indices[0]]
                    rec = build_faint_record_from_klog(
                        opp_k_log_ref[0].get(key, []), outgoing.species, outgoing.max_hp,
                    )
                    if rec is not None:
                        foe_faint_deltas_ref[0].append(rec)
                opp_k_log_ref[0][key] = []
                buf = opponent_hp_bufs.get(key)
                if buf is not None:
                    buf.reset()

        if finalized_result.string_id in _BATTLE_END_IDS:
            _print_turn(current_turn)
            _run_turn_sweep(current_turn, candidate_tracker_ref, opp_k_log_ref,
                            player_hp_log_ref, player_hp_bufs, opponent_hp_bufs, battle_state_ref,
                            recorder_ref, foe_faint_deltas_ref)
            current_turn.clear()
            outcome = "player lost" if "WHITEOUT" in finalized_result.string_id else "battle ended"
            print(f"[capture] OFF ({outcome})", flush=True)
            return True

        return False

    def _finalize_turn_boundary() -> None:
        """Run the turn sweep at a menu boundary, unless no real turn elapsed.

        A move selection rejected in the menu (e.g. "There's no PP left for this
        move!") makes the menu vanish and reappear, masquerading as a completed
        turn. Sweeping such a phantom turn enumerates bogus candidates (incl.
        switches) and then crashes. Skip the sweep when current_turn holds only
        menu-rejection messages; clear it either way so the noise does not bleed
        into the next real turn.
        """
        string_ids = [e["match"].string_id for e in current_turn]
        if not turn_has_real_action(string_ids):
            if current_turn:
                print(f"[capture] phantom turn ignored (menu rejection): {string_ids}", flush=True)
            current_turn.clear()
            return
        _print_turn(current_turn)
        _run_turn_sweep(current_turn, candidate_tracker_ref, opp_k_log_ref,
                        player_hp_log_ref, player_hp_bufs, opponent_hp_bufs, battle_state_ref,
                        recorder_ref, foe_faint_deltas_ref)
        current_turn.clear()

    if not words:
        # Preserve pending — process([]) does not clear it.
        matcher.process([])
        # An empty battle message is the cheap gate for the party-screen check:
        # its prompt box uses a different palette and reads empty here, so scan
        # the dedicated region for "Choose a POKéMON.".
        if read_party_prompt(prompt_image):
            if capture_active:
                flushed = matcher.flush()
                if flushed is not None:
                    if _record_match(flushed):
                        return True, None, text
                _finalize_turn_boundary()
            return False, ScreenKind.PARTY_MENU, text
        return False, None, text

    result = matcher.process(words, constraints=_make_constraints_for_active(battle_state_ref[0], constraints_ref[0]))

    if isinstance(result, ScreenSignal):
        if result.kind in (ScreenKind.OPTION_SELECT, ScreenKind.PARTY_MENU):
            if capture_active:
                flushed = matcher.flush()
                if flushed is not None:
                    if _record_match(flushed):
                        return True, result.kind, text
                _finalize_turn_boundary()
        return False, result.kind, text

    if result is None:
        return False, None, text

    if _record_match(result):
        return True, None, text

    return False, None, text


def main() -> None:
    global _verbose_log

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, metavar="PATH",
                        help="Path to a state config.json with opponent_index and level_cap.")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open() as f:
        _cfg = json.load(f)
    if not isinstance(_cfg.get("opponent_index"), int):
        raise ValueError(f"config.json missing integer 'opponent_index': {config_path}")
    if not isinstance(_cfg.get("level_cap"), int):
        raise ValueError(f"config.json missing integer 'level_cap': {config_path}")
    opponent_index: int = _cfg["opponent_index"]
    level_cap: int = _cfg["level_cap"]
    states_dir: Path = Path(__file__).parent.parent / "States"

    _CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    _PLAY_LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    log_path = _PLAY_LOG_DIR / f"session_{ts}.log"
    log_file = log_path.open("w", buffering=1)
    orig_stdout = sys.stdout
    sys.stdout = _Tee(orig_stdout, log_file)
    _verbose_log = log_file

    try:
        print(f"[play] log → {log_path}", flush=True)
        print("Launching mGBA...")
        with MGBAProcess(event_timeout=0.1) as mgba:
            print("  mGBA is running.")
            print("  Press L to toggle capture, O to start a battle. Ctrl+C to quit.\n")

            screen_capture = ScreenCapture(mgba.socket)
            matcher = BattleMessageMatcher()
            captures: list[dict] = []
            current_turn: list[dict] = []
            capture_active = False
            last_capture_time_ref = [0.0]   # mutable float ref passed into _do_capture
            opponent_hp_bufs: dict = {}     # dict[str, OpponentHpBuffer] keyed by lowercased Pokémon name
            player_hp_bufs: dict = {}       # dict[str, PlayerHpBuffer] keyed by lowercased player species name
            battle_state_ref = [_make_stub_battle_state()]
            constraints_ref = [Constraints()]
            candidate_tracker_ref = [None]  # holds CandidateTracker | None
            opp_k_log_ref = [{}]            # dict[str, list[int]] — confirmed k-pixel values per opponent name
            player_hp_log_ref = [{}]        # dict[str, list[int]] confirmed player HP per species name
            last_screen_kind_ref = [None]   # ScreenKind when on a menu; None during battle text
            last_b_press_time_ref = [0.0]   # time of last B tap
            recorder_ref = [None]           # holds SweepRecorder | None; one session per battle
            foe_faint_deltas_ref = [[]]     # list[HpDeltaSeq] flushed when a same-name foe replacement wipes the dead mon's log
            pending_switch_ref = [None]     # species name set on voluntary switch; None for forced
            policy = RandomPolicy()

            try:
                while True:
                    event = mgba.socket.recv_event()

                    if event == "toggle_capture":
                        capture_active = not capture_active
                        if capture_active:
                            matcher = BattleMessageMatcher()
                            opponent_hp_bufs = {}
                            player_hp_bufs = {}
                            last_capture_time_ref[0] = 0.0  # force immediate first capture
                            candidate_tracker_ref[0] = None
                            opp_k_log_ref[0] = {}
                            player_hp_log_ref[0] = {}
                            last_screen_kind_ref[0] = None
                            last_b_press_time_ref[0] = 0.0
                            pending_switch_ref[0] = None
                            print("[capture] ON", flush=True)
                        else:
                            last_screen_kind_ref[0] = None
                            pending_switch_ref[0] = None
                            print("[capture] OFF", flush=True)

                    elif event == "init_battle":
                        print("[O] initializing battle state...", flush=True)
                        battle_state_ref[0], constraints_ref[0] = _build_battle_state(opponent_index, mgba.socket, level_cap)
                        initial_candidate = Candidate(state=battle_state_ref[0])
                        candidate_tracker_ref[0] = CandidateTracker([initial_candidate])
                        recorder_ref[0] = SweepRecorder.create()
                        opp_k_log_ref[0] = {}
                        player_hp_log_ref[0] = {}
                        current_turn.clear()
                        matcher = BattleMessageMatcher()
                        opponent_hp_bufs = {}
                        player_hp_bufs = {}
                        capture_active = True
                        last_capture_time_ref[0] = 0.0
                        last_screen_kind_ref[0] = None
                        last_b_press_time_ref[0] = 0.0
                        pending_switch_ref[0] = None
                        print(f"[state] Ready: {len(battle_state_ref[0].sides[0].team)} player mons, "
                              f"{len(battle_state_ref[0].sides[1].team)} opponent mons", flush=True)
                        print(f"[recorder] Session: {recorder_ref[0].session_dir}", flush=True)
                        print("[capture] ON (battle started)", flush=True)
                        with _BATTLE_SNAPSHOT_PATH.open("wb") as f:
                            pickle.dump(battle_state_ref[0], f)
                        print(f"[O] Battle snapshot saved to {_BATTLE_SNAPSHOT_PATH}", flush=True)

                    elif event == "save_state":
                        name = input("State name: ").strip()
                        if not name or "/" in name or "\\" in name:
                            raise ValueError(f"Invalid state name: {name!r}")
                        state_folder = states_dir / name
                        if state_folder.exists():
                            raise FileExistsError(f"State folder already exists: {state_folder}")
                        state_folder.mkdir(parents=True)
                        ss_path = state_folder / f"{name}.ss1"
                        mgba.socket.save_state(str(ss_path))
                        with (state_folder / "config.json").open("w") as f:
                            json.dump({"opponent_index": opponent_index, "level_cap": level_cap}, f)
                        print(f"[save] State saved to States/{name}/", flush=True)

                    elif event == "save_training_data":
                        name = input("Training snapshot name: ").strip()
                        if not name or "/" in name or "\\" in name:
                            raise ValueError(f"Invalid snapshot name: {name!r}")
                        snapshot_folder = _TRAINING_DATA_DIR / name
                        if snapshot_folder.exists():
                            raise FileExistsError(f"Snapshot folder already exists: {snapshot_folder}")
                        ts_state, _ = _build_battle_state(opponent_index, mgba.socket, level_cap)
                        box_mons = _snapshots_to_states(mgba.socket.read_all_boxes())
                        _save_training_snapshot(snapshot_folder, ts_state, box_mons, opponent_index, level_cap)
                        print(f"[P] Training snapshot saved to TrainingData/{name}/ "
                              f"({len(ts_state.sides[0].team)} party, {len(box_mons)} box, "
                              f"{len(ts_state.sides[1].team)} opponent)", flush=True)

                    elif event is None:
                        # Timeout — check whether it is time for the next capture
                        if capture_active and time.time() - last_capture_time_ref[0] >= _CAPTURE_INTERVAL:
                            battle_ended, screen_kind, _ = _do_capture(
                                screen_capture, matcher, captures, current_turn,
                                last_capture_time_ref, capture_active,
                                opponent_hp_bufs=opponent_hp_bufs,
                                player_hp_bufs=player_hp_bufs,
                                candidate_tracker_ref=candidate_tracker_ref,
                                opp_k_log_ref=opp_k_log_ref,
                                player_hp_log_ref=player_hp_log_ref,
                                battle_state_ref=battle_state_ref,
                                constraints_ref=constraints_ref,
                                recorder_ref=recorder_ref,
                                foe_faint_deltas_ref=foe_faint_deltas_ref,
                            )
                            if battle_ended:
                                capture_active = False
                                last_screen_kind_ref[0] = None
                            elif screen_kind in (ScreenKind.OPTION_SELECT, ScreenKind.PARTY_MENU) \
                                    and last_screen_kind_ref[0] != screen_kind:
                                handle_battle_screen(
                                    mgba.socket, screen_capture, screen_kind,
                                    battle_state_ref[0], policy, pending_switch_ref,
                                )
                                last_screen_kind_ref[0] = screen_kind
                            else:
                                last_screen_kind_ref[0] = screen_kind

                        # Press B to advance battle text while not on a menu screen
                        if capture_active and last_screen_kind_ref[0] is None:
                            if time.time() - last_b_press_time_ref[0] >= _B_PRESS_INTERVAL:
                                _vlog("[input] pressing b")
                                _press(mgba.socket, "b")
                                last_b_press_time_ref[0] = time.time()

            except MGBAConnectionError as e:
                print(f"\nmGBA closed: {e}")
            except KeyboardInterrupt:
                print("\nQuitting...")
            except Exception:
                print(f"\n[play] Unexpected crash:", flush=True)
                traceback.print_exc(file=sys.stdout)
                sys.stdout.flush()
    finally:
        sys.stdout = orig_stdout
        _verbose_log = None
        log_file.close()


if __name__ == "__main__":
    main()
