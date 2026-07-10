# Pure action/mover/slot-resolution and observed-action-inference helpers for the sweep.
# No Simulator, GameDriver, override, or RNG-inject dependencies — pure leaf module.
from __future__ import annotations

import itertools
from dataclasses import replace as _dc_replace
from typing import Optional

from rapidfuzz.distance import Levenshtein as _Lev

from liveplay.actions import Action, ActionKind, enumerate_legal_actions, STRUGGLE_SLOT
from liveplay.battle_types import ActionGroup, MatchResult
from liveplay.data.moves import Move, MOVE_DATA, MoveCategory, move_name_to_enum, safe_move
from liveplay.data.name_aliases import emulator_species_name, MOVE_ALIASES
from liveplay.engine_select import SimulationError
from liveplay.rng import RNGEvent
from liveplay.state.battle import BattleState
from liveplay.state_transition import (
    _fuzzy_find_move_slot,
    _fuzzy_find_side,
    _fuzzy_find_team_slot,
    _side_from_constant_name,
    _species_match_threshold,
)
# Shared pure predicates/constants (re-exported for callers that import them from here).
from liveplay.sweep_common import _SPREAD_TARGETS, _msg_is_foe, _move_is_spread

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_USEDMOVE_ID = "STRINGID_USEDMOVE"

_FAINT_MSG_IDS = frozenset({"STRINGID_ATTACKERFAINTED", "STRINGID_TARGETFAINTED"})

_SWITCH_IDS = frozenset({
    "STRINGID_SWITCHINMON", "STRINGID_INTROSENDOUT",
    "STRINGID_PLAYER_SWITCHINMON", "STRINGID_PLAYER_INTROSENDOUT",
})

# Called-move wrappers: a move that emits "used <wrapper>!" then "used <called>!" as
# two USEDMOVE lines for the same attacker, while the engine models a SINGLE move use
# (the called move). Each maps to the RNGEvent the engine consumes to pick the sub-move.
_CALLED_MOVE_EVENTS: dict[Move, RNGEvent] = {
    Move.METRONOME: RNGEvent.METRONOME_MOVE,
    Move.SLEEP_TALK: RNGEvent.SLEEP_TALK_MOVE,
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class UnexpectedOpponentActionError(Exception):
    """Raised when the opponent takes an action that compute_action_probabilities assigned p=0.

    Raised per-candidate inside run_candidate_sweep so only that candidate is filtered;
    if every candidate is filtered the sweep naturally produces no survivors (SimulationError).
    """


class UnreproducibleObservedMoveError(Exception):
    """Raised when an observed USEDMOVE cannot be reproduced in the sim for a candidate.

    Two causes: the OCR'd move name has no match in the mon's modeled moveset (moveset
    desync), or the resolved move is not in enumerate_legal_actions for the candidate's
    state (legality desync). Either means the observed turn is unreproducible for this
    candidate, so the candidate is filtered.
    """


# ---------------------------------------------------------------------------
# Slot resolution
# ---------------------------------------------------------------------------

def _slot_for_name(
    recipient_name: str,
    state: BattleState,
    hp_changed_by_slot: Optional[dict[tuple[int, int], bool]] = None,
    side_constraint: Optional[int] = None,
) -> Optional[tuple[int, int]]:
    """Resolve (side, active-slot position) of the active mon matching a bare name.

    Fuzzy-matches the name against each side's active mons. Returns the unique (side, slot)
    match, None if no active mon matches. On same-species ambiguity (the name matches both
    active slots on a side), reduces by hp_changed_by_slot when provided: the recipient of
    the effect changed HP this turn, so a single same-species slot whose per-slot HP delta
    is non-zero resolves the ambiguity. If the reduction cannot pick a single slot, raises
    SimulationError — fail loud rather than silently picking a slot.
    side_constraint: when not None, restrict the search to that single side only.
    """
    upper_name = recipient_name.upper()

    sides_to_scan = (side_constraint,) if side_constraint is not None else (0, 1)
    for side_idx in sides_to_scan:
        active_indices = state.sides[side_idx].active_indices
        matching_positions = []
        for pos, team_idx in enumerate(active_indices):
            mon = state.sides[side_idx].team[team_idx]
            species_name = emulator_species_name(mon.species)
            threshold = _species_match_threshold(species_name)
            if _Lev.distance(upper_name, species_name) <= threshold:
                matching_positions.append(pos)

        if len(matching_positions) == 1:
            return (side_idx, matching_positions[0])
        if len(matching_positions) > 1:
            # Same-species ambiguity. Reduce by which slot's HP actually changed this turn:
            # the recipient of a damage/heal/flinch effect took an HP change, so a single
            # HP-changed same-species slot disambiguates.
            if hp_changed_by_slot is not None:
                reduced = [p for p in matching_positions
                           if hp_changed_by_slot.get((side_idx, p), False)]
                if len(reduced) == 1:
                    return (side_idx, reduced[0])
            raise SimulationError(
                reason=(
                    f"Cannot resolve recipient slot: '{recipient_name}' matches multiple active mons "
                    f"on side {side_idx} (same species in both active slots) and per-slot HP deltas "
                    f"do not single out one slot. Slot disambiguation requires additional vision "
                    f"features — failing loud rather than silently picking a slot."
                )
            )

    return None


def _recipient_slot(
    msg: MatchResult,
    state: BattleState,
    hp_changed_by_slot: Optional[dict[tuple[int, int], bool]] = None,
    side_constraint: Optional[int] = None,
) -> Optional[tuple[int, int]]:
    """Resolve the (side, active-slot position) of the recipient named in an effect message.

    Reads var_values[0] as the recipient's name, fuzzy-matches to find its side, then
    finds its position within that side's active_indices. If the name matches more than
    one active mon (same species in both active slots), the ambiguity is reduced using
    hp_changed_by_slot (the recipient of a damage/heal/flinch effect changed HP this turn);
    if it remains ambiguous, raises SimulationError. Returns None if the name cannot be
    matched to any active mon.
    side_constraint: when not None, restrict the search to that side only.
    """
    if not msg.var_values:
        return None
    return _slot_for_name(
        msg.var_values[0], state,
        hp_changed_by_slot=hp_changed_by_slot,
        side_constraint=side_constraint,
    )


def _resolve_attacker_slot(side: int, attacker_name: str, state: BattleState, cursor: list[int]) -> int:
    """Return the active-slot POSITION for attacker_name on side, using cursor for same-species ties.

    cursor is a per-side list of integers tracking the next unconsumed slot position for each
    side (cursor[side]). When a species matches exactly one active position, that position is
    returned directly. When both actives share a species (ambiguous), the cursor position is
    consumed and advanced. Raises SimulationError if no active position matches at all.
    """
    active_indices = state.sides[side].active_indices
    upper_name = attacker_name.upper()
    matching_positions = []
    for pos, team_idx in enumerate(active_indices):
        mon = state.sides[side].team[team_idx]
        species_name = emulator_species_name(mon.species)
        threshold = _species_match_threshold(species_name)
        if _Lev.distance(upper_name, species_name) <= threshold:
            matching_positions.append(pos)

    if not matching_positions:
        raise SimulationError(
            reason=(
                f"Cannot resolve attacker slot: '{attacker_name}' did not fuzzy-match any active "
                f"mon on side {side}. Active mons: "
                f"{[state.sides[side].team[i].species.name for i in active_indices]}"
            )
        )

    if len(matching_positions) == 1:
        return matching_positions[0]

    # Ambiguous (same species in both active slots): consume cursor position
    pos = cursor[side] % len(matching_positions)
    cursor[side] += 1
    return matching_positions[pos]


def _attacker_match_positions(side: int, attacker_name: str, state: BattleState) -> list[int]:
    """Return all active-slot POSITIONS on side whose species fuzzy-matches attacker_name."""
    active_indices = state.sides[side].active_indices
    upper_name = attacker_name.upper()
    out: list[int] = []
    for pos, team_idx in enumerate(active_indices):
        mon = state.sides[side].team[team_idx]
        species_name = emulator_species_name(mon.species)
        if _Lev.distance(upper_name, species_name) <= _species_match_threshold(species_name):
            out.append(pos)
    return out


def _build_attacker_slot_map(
    messages: list,
    state: BattleState,
) -> dict:
    """Walk messages once and return {id(msg): (side, slot)} for each resolved USEDMOVE.

    This is the single authoritative same-species cursor pass. All consumers that need
    (side, slot) for a USEDMOVE message should look up this map instead of running their
    own cursor, so every site agrees on which same-species slot acted in which order.
    Messages that cannot be resolved (unknown side, no match) are omitted — callers that
    need loud failure on no-match should detect absence and raise explicitly.
    """
    result: dict = {}
    cursor = [0, 0]
    for msg in messages:
        if msg.string_id != _USEDMOVE_ID or not msg.var_values:
            continue
        side = _fuzzy_find_side(msg.var_values[0], state, side_hint=msg.side_hint, reference_kind="actor")
        if side is None:
            continue
        try:
            slot = _resolve_attacker_slot(side, msg.var_values[0], state, cursor)
        except SimulationError:
            continue
        result[id(msg)] = (side, slot)
    return result


def _build_attacker_slot_maps(
    messages: list,
    state: BattleState,
) -> list[dict]:
    """Like _build_attacker_slot_map but fans out same-species attacker ambiguity.

    Walks USEDMOVE messages; each resolves to a side and one or more candidate active
    positions. When every message matches exactly one position there is a single map
    (identical to _build_attacker_slot_map / the singles case). When some messages are
    ambiguous (both active slots share the attacker's species), the alternative slot
    assignments are enumerated as separate maps so the sweep can try each; downstream
    HP/log validation prunes the wrong ones. Assignments that reuse the same active slot
    within one side are rejected (each slot acts at most once per ordered USEDMOVE round).
    Returns at least one map.
    """
    resolved: list = []  # (msg, side, positions)
    for msg in messages:
        if msg.string_id != _USEDMOVE_ID or not msg.var_values:
            continue
        side = _fuzzy_find_side(msg.var_values[0], state, side_hint=msg.side_hint, reference_kind="actor")
        if side is None:
            continue
        positions = _attacker_match_positions(side, msg.var_values[0], state)
        if not positions:
            continue
        resolved.append((msg, side, positions))

    per_msg_choices = [positions for (_m, _s, positions) in resolved]
    maps: list[dict] = []
    seen: set = set()
    for combo in (itertools.product(*per_msg_choices) if per_msg_choices else [()]):
        used: set = set()
        ok = True
        for (_msg, side, _positions), pos in zip(resolved, combo):
            key = (side, pos)
            if key in used:
                ok = False
                break
            used.add(key)
        if not ok:
            continue
        m = {id(msg): (side, pos) for (msg, side, _positions), pos in zip(resolved, combo)}
        sig = tuple(sorted(m.items()))
        if sig in seen:
            continue
        seen.add(sig)
        maps.append(m)
    if not maps:
        # All enumerated assignments collided — fall back to the cursor map.
        maps = [_build_attacker_slot_map(messages, state)]
    return maps


# ---------------------------------------------------------------------------
# Message segmentation / order
# ---------------------------------------------------------------------------

def _segment_flat_messages_by_mover(
    flat_messages: list,
    state: BattleState,
    slot_map: Optional[dict] = None,
) -> list[tuple[int, int, list]]:
    """Split flat_messages into segments, one per USEDMOVE.

    Each segment is (side, source_slot, messages) where messages are the non-USEDMOVE
    messages that follow that USEDMOVE until the next one. Messages before the first
    USEDMOVE are discarded.

    slot_map: precomputed {id(msg): (side, slot)} from _build_attacker_slot_map; when
    provided, slot assignment comes from the shared pass instead of a local cursor.
    """
    segments: list[tuple[int, int, list]] = []
    cursor = [0, 0]
    current_segment: Optional[list] = None

    for msg in flat_messages:
        if msg.string_id == _USEDMOVE_ID and msg.var_values:
            if slot_map is not None:
                entry = slot_map.get(id(msg))
                if entry is not None:
                    side, source_slot = entry
                    current_segment = []
                    segments.append((side, source_slot, current_segment))
                continue
            side = _fuzzy_find_side(msg.var_values[0], state, side_hint=msg.side_hint, reference_kind="actor")
            if side is not None:
                source_slot = _resolve_attacker_slot(side, msg.var_values[0], state, cursor)
                current_segment = []
                segments.append((side, source_slot, current_segment))
                continue
        if current_segment is not None:
            current_segment.append(msg)

    return segments


def _message_action_order_with_state(
    messages: list[MatchResult],
    state: BattleState,
    slot_map: Optional[dict] = None,
) -> list[tuple[int, int]]:
    """Return (side, source_slot) tuples in move order from USEDMOVE messages.

    source_slot is the active-slot POSITION (0 or 1) of the acting mon.
    Singles produces e.g. [(0,0),(1,0)] — same ordering as before, wrapped.
    slot_map: precomputed {id(msg): (side, slot)} from _build_attacker_slot_map; when
    provided, avoids re-running the cursor so all sites agree on same-species assignment.
    """
    order: list[tuple[int, int]] = []
    if slot_map is not None:
        for msg in messages:
            if msg.string_id == _USEDMOVE_ID and msg.var_values:
                entry = slot_map.get(id(msg))
                if entry is not None:
                    order.append(entry)
        return order
    # Fallback: own cursor (used when called without a precomputed map)
    cursor = [0, 0]
    for msg in messages:
        if msg.string_id == _USEDMOVE_ID and msg.var_values:
            side = _fuzzy_find_side(msg.var_values[0], state, side_hint=msg.side_hint, reference_kind="actor")
            if side is not None:
                source_slot = _resolve_attacker_slot(side, msg.var_values[0], state, cursor)
                order.append((side, source_slot))
    return order


def _foe_damaged_slots(foe_deltas: list[list[tuple]]) -> list[int]:
    """Return sorted slot indices with a net HP decrease.

    foe_deltas is per-slot list[list[tuple]]. Each tuple is (prev_hp, curr_hp) where
    the second element is the current HP value. A slot is damaged if non-empty and
    the final HP (seq[-1][1]) is less than the initial HP (seq[0][0]).
    """
    damaged = []
    for slot_idx, seq in enumerate(foe_deltas):
        if seq and seq[-1][1] < seq[0][0]:
            damaged.append(slot_idx)
    return damaged


def _sweep_build_flat_messages(
    messages: list[MatchResult],
    action_groups: Optional[list[ActionGroup]],
) -> list[MatchResult]:
    """Assemble the flat message list from base messages and action group primaries/secondaries.

    Preserves dedup-by-identity: only appends group messages not already present in messages.
    """
    all_messages_flat: list[MatchResult] = list(messages)
    if action_groups:
        for grp in action_groups:
            if grp.primary not in all_messages_flat:
                all_messages_flat.append(grp.primary)
            for sec in grp.secondaries:
                if sec not in all_messages_flat:
                    all_messages_flat.append(sec)
    return all_messages_flat


# ---------------------------------------------------------------------------
# Called-move / action shaping
# ---------------------------------------------------------------------------

def _resolve_called_move(name: str) -> Optional[Move]:
    """Strictly resolve a Metronome-called move display name to its Move enum member.

    Unlike `move_name_to_enum`, whose ≤2 Levenshtein fuzzy fallback can cross to a
    DIFFERENT move (e.g. 'CHARGE'→CHARM — Issue 23, a silent wrong-move that corrupts
    state), this accepts only an exact normalized lookup, an explicit alias, or a
    separator-insensitive exact match (Gen-3 fused spellings: 'SOLARBEAM'↔SOLAR_BEAM).
    Returns None for any move genuinely absent from the enum so the caller can hard-crash
    per the 'implemented = in the Move enum' rule.
    """
    raw = name.strip()
    norm = raw.upper().replace(" ", "_").replace("-", "_")
    m = safe_move(norm)
    if m is not None:
        return m
    if raw in MOVE_ALIASES:
        return MOVE_ALIASES[raw]
    flat = norm.replace("_", "")
    for member in Move:
        if member.name.replace("_", "") == flat:
            return member
    return None


def _acting_action(action0, action1, mover_side: int, source_slot: int):
    """Return the bare Action for the mover identified by (mover_side, source_slot).

    If the side's action is a list (doubles), returns act[source_slot] with fallback to act[0]
    if source_slot is out of range. Returns None if the side's action is None.
    """
    act = action0 if mover_side == 0 else action1
    if act is None:
        return None
    if isinstance(act, list):
        if source_slot < len(act):
            return act[source_slot]
        return act[0]
    return act


def _action_move_enum(action: Action, side: int, slot_pos: int, state: BattleState):
    """Resolve the Move enum for a MOVE action by looking up the mon's move_ids."""
    if action.kind != ActionKind.MOVE or action.move_slot < 0:
        return None
    active_indices = state.sides[side].active_indices
    if slot_pos >= len(active_indices):
        return None
    team_idx = active_indices[slot_pos]
    mon = state.sides[side].team[team_idx]
    move_ids = mon.move_ids
    if action.move_slot >= len(move_ids):
        return None
    mv = move_ids[action.move_slot]
    return mv if mv != Move.NONE else None


def _expand_action_targets(
    action: Action,
    side: int,
    slot_pos: int,
    state: BattleState,
    foe_dmg: list[int],
    hit_count_map: dict[tuple[int, int], int],
) -> list[Action]:
    """Expand a single action into variants by enumerating target slots when appropriate.

    Spread moves: fix target_slot=0, check spread+multi-hit constraint.
    Single-target damaging moves: enumerate over foe_dmg.
    SWITCH / status: return as-is (target_slot irrelevant).
    """
    if action.kind != ActionKind.MOVE:
        return [action]

    # Resolve move enum for this slot
    move_enum = _action_move_enum(action, side, slot_pos, state)

    if move_enum is not None and _move_is_spread(move_enum):
        # Spread+multi-hit is unsupported (deferred to Stage E)
        n_hits = hit_count_map.get((side, slot_pos), 1)
        if n_hits > 1:
            raise SimulationError(
                reason=(
                    f"Spread+multi-hit combination on side {side} slot {slot_pos} "
                    f"({move_enum.name}, {n_hits} hits) is not yet supported."
                )
            )
        return [_dc_replace(action, target_slot=0)]

    # For single-target damaging moves (or unknown), enumerate over foe_dmg
    md = MOVE_DATA.get(move_enum) if move_enum is not None else None
    if md is not None and md.category == MoveCategory.STATUS:
        # Status move: target irrelevant
        return [action]

    # Damaging or unknown: enumerate over damaged foe slots
    return [_dc_replace(action, target_slot=t) for t in foe_dmg]


def _build_side_candidates(
    side: int,
    state: BattleState,
    known_slots: list[Optional[Action]],
    opponent_hp_deltas: list[list[tuple]],
    player_hp_deltas: list[list[tuple]],
    hit_counts: list[int],
    movers: list[tuple[int, int]],
) -> list:
    """Build candidate actions for one side.

    Singles (one active slot): returns list of bare Actions (unchanged path).
    Doubles (two active slots): returns list of [Action, Action] pairs (cross product
    with target enumeration over foe-damaged slots for single-target damaging moves).
    """
    n_slots = len(state.sides[side].active_indices)

    if n_slots == 1:
        # Singles path: bare Actions, byte-identical to previous behavior
        known = known_slots[0]
        if known is not None:
            return [known]
        return enumerate_legal_actions(state, side) or [Action(kind=ActionKind.MOVE, move_slot=0)]

    # Doubles path: build per-slot variant lists then cross-product
    foe_side = 1 - side
    foe_deltas = opponent_hp_deltas if foe_side == 1 else player_hp_deltas
    foe_dmg = _foe_damaged_slots(foe_deltas)
    if not foe_dmg:
        foe_dmg = [0]

    # Map (mover_side, mover_slot) → hit count for spread+multi-hit detection
    hit_count_map: dict[tuple[int, int], int] = {}
    for i, (ms, mslot) in enumerate(movers):
        if i < len(hit_counts):
            hit_count_map[(ms, mslot)] = hit_counts[i]

    per_slot_variants: list[list[Action]] = []
    for slot_pos in range(n_slots):
        known = known_slots[slot_pos]
        if known is not None:
            variants = _expand_action_targets(
                known, side, slot_pos, state, foe_dmg, hit_count_map
            )
        else:
            legal = enumerate_legal_actions(state, side, slot_pos)
            base_actions = legal or [Action(kind=ActionKind.MOVE, move_slot=0, source_slot=slot_pos)]
            variants = []
            for act in base_actions:
                expanded = _expand_action_targets(
                    act, side, slot_pos, state, foe_dmg, hit_count_map
                )
                variants.extend(expanded)
        per_slot_variants.append(variants)

    # Cross product across slots → list of [a0, a1] candidates
    return [list(combo) for combo in itertools.product(*per_slot_variants)]


def _fmt_action(action) -> str:
    """Format an action or list of per-slot actions for logging."""
    if action is None:
        return "none"
    if isinstance(action, list):
        parts = []
        for a in action:
            if a is None:
                parts.append("none")
            elif a.kind == ActionKind.MOVE:
                parts.append(f"move[{a.move_slot}]→{a.target_slot}")
            else:
                parts.append(f"switch→{a.switch_to_slot}")
        return "[" + ", ".join(parts) + "]"
    if action.kind == ActionKind.MOVE:
        return f"move[{action.move_slot}]"
    return f"switch→{action.switch_to_slot}"


# ---------------------------------------------------------------------------
# Observed-action inference
# ---------------------------------------------------------------------------

def _extract_used_moves_from_groups(
    action_groups: Optional[list[ActionGroup]],
    state: BattleState,
    flat_messages: Optional[list] = None,
    slot_map: Optional[dict] = None,
) -> dict[tuple[int, int], Move]:
    """Scan action groups (or flat message list) for USEDMOVE messages.

    Returns a dict keyed by (side, source_slot) where source_slot is the active-slot
    position (0 or 1). Singles produces {(0,0): move, (1,0): move}. Doubles may produce
    up to four entries.

    slot_map: precomputed {id(msg): (side, slot)} from _build_attacker_slot_map; when
    provided, slot assignment comes from the shared pass. Always uses flat_messages when
    slot_map is given (action_groups path uses a separate cursor that can desync).
    """
    result: dict[tuple[int, int], Move] = {}

    # When a slot_map is provided, always scan flat_messages to stay consistent with the
    # shared authoritative pass. Without a map, fall back to the action_groups ordering.
    if slot_map is not None:
        msgs_to_scan = flat_messages or []
    elif action_groups:
        msgs_to_scan = []
        for group in action_groups:
            msgs_to_scan.extend([group.primary] + list(group.secondaries))
    elif flat_messages:
        msgs_to_scan = flat_messages
    else:
        return result

    cursor = [0, 0]  # used only in the no-slot_map fallback path

    for msg in msgs_to_scan:
        if msg.string_id != _USEDMOVE_ID or not msg.var_values:
            continue
        attacker_name = msg.var_values[0]
        move_name = msg.var_values[1] if len(msg.var_values) > 1 else ""

        if slot_map is not None:
            entry = slot_map.get(id(msg))
            if entry is None:
                continue
            side, source_slot = entry
        else:
            side = _fuzzy_find_side(attacker_name, state, side_hint=msg.side_hint, reference_kind="actor")
            if side is None:
                continue
            source_slot = _resolve_attacker_slot(side, attacker_name, state, cursor)

        key = (side, source_slot)
        if key in result:
            continue  # already recorded this (side, slot) — keep first occurrence
        move_enum = move_name_to_enum(move_name)
        # Metronome collapses to the Metronome USEDMOVE tagged with the resolved called move
        # (the called-move USEDMOVE is dropped). The engine executes the CALLED move, so its
        # secondary effects (e.g. Water Pulse's confusion) — not Metronome's (none) — must drive
        # the sweep's SECONDARY_FIRES/FLINCH enumeration. Treat it as a normal use of the call.
        _called = getattr(msg, "metronome_called", None)
        if _called is not None and _called != Move.NONE:
            move_enum = _called
        if move_enum is not None and move_enum != Move.NONE:
            result[key] = move_enum
    return result


def _extract_known_actions(
    messages: list[MatchResult],
    state: BattleState,
    slot_map: Optional[dict] = None,
) -> dict[int, list[Optional[Action]]]:
    """Scan messages for USEDMOVE and switch IDs to identify each side's per-slot action.

    Returns {0: list[Action|None], 1: list[Action|None]} where each list is indexed by
    active-slot POSITION and has length == len(state.sides[side].active_indices).
    Singles produces length-1 lists.

    slot_map: precomputed {id(msg): (side, slot)} from _build_attacker_slot_map; when
    provided, avoids re-running the cursor so all sites agree on same-species assignment.

    A switch-in that follows a faint of that same side's active mon *within this batch*
    is a FORCED post-faint replacement, not a voluntary turn action: those are applied
    mid-turn via opp_switch_actions / the post-faint branch. Assigning them here too would
    double-count the switch and make the sim withdraw the doomed mon before it can faint.
    Per-side counters pair each faint with its following replacement, so this also handles
    multiple opponent faints in one turn (doubles). The player's forced replacement never
    shares a batch with its faint (a player faint forces a party-menu boundary that isolates
    the send-out), so this is a no-op for side 0 in practice.
    """
    result: dict[int, list[Optional[Action]]] = {
        side: [None] * len(state.sides[side].active_indices)
        for side in (0, 1)
    }
    # Battle-start send-outs are forced, not decisions. When the intro banner is in this
    # batch, both sides' send-outs (matched as SWITCHINMON) are the opening lead-ins, not
    # voluntary switches — recording them would make the opponent-action filter reject the
    # send-out (it had p=0 vs the AI's move predictions) and crash the sweep. Same principle
    # as forced post-faint replacements (see `forced_replace_not_action`), but no faint
    # precedes the opening send-out so the pending_faint pairing below can't catch it.
    battle_start = any(msg.string_id == "STRINGID_INTROMSG" for msg in messages)
    pending_faint: dict[int, int] = {0: 0, 1: 0}
    # Per-side cursor for same-species slot disambiguation when no slot_map is provided.
    cursor = [0, 0]

    for msg in messages:
        string_id = msg.string_id
        var_values = msg.var_values

        if string_id in _FAINT_MSG_IDS:
            faint_side = 1 if _msg_is_foe(msg) else 0
            pending_faint[faint_side] += 1
            continue

        if string_id == _USEDMOVE_ID:
            if not var_values:
                continue
            attacker_name = var_values[0]
            move_name = var_values[1] if len(var_values) > 1 else ""

            if slot_map is not None:
                entry = slot_map.get(id(msg))
                if entry is None:
                    continue
                side, source_slot = entry
            else:
                side = _fuzzy_find_side(attacker_name, state, side_hint=msg.side_hint, reference_kind="actor")
                if side is None:
                    continue
                try:
                    source_slot = _resolve_attacker_slot(side, attacker_name, state, cursor)
                except SimulationError:
                    continue

            if result[side][source_slot] is not None:
                continue

            active_idx = state.sides[side].active_indices[source_slot]
            poke = state.sides[side].team[active_idx]
            # Struggle is a forced fallback never present in any moveset, so it can't be
            # resolved to a real slot. The matcher canonicalizes the name to "STRUGGLE";
            # build the Struggle action (STRUGGLE_SLOT + override) directly.
            if move_name.upper() == Move.STRUGGLE.name:
                action = Action(kind=ActionKind.MOVE, move_slot=STRUGGLE_SLOT,
                                move_override=Move.STRUGGLE, source_slot=source_slot)
            else:
                move_slot = _fuzzy_find_move_slot(move_name, poke)
                if move_slot < 0:
                    raise UnreproducibleObservedMoveError(
                        f"{poke.species.name} used '{move_name}' but that move is not in its "
                        f"modeled moveset {[m.name for m in poke.move_ids]} "
                        f"(not-in-moveset desync)"
                    )
                action = Action(kind=ActionKind.MOVE, move_slot=move_slot, source_slot=source_slot)
            # Legal-action check: enumerate for the specific source slot
            legal = enumerate_legal_actions(state, side, source_slot)
            # Compare by kind+move_slot only: enumerated actions may not carry source_slot
            if any(a.kind == action.kind and a.move_slot == action.move_slot for a in legal):
                result[side][source_slot] = action
            else:
                raise UnreproducibleObservedMoveError(
                    f"{poke.species.name} used '{move_name}' (slot {move_slot}) but that action "
                    f"is not in enumerate_legal_actions for this candidate's state "
                    f"(not-legal desync)"
                )

        elif string_id in _SWITCH_IDS:
            side = _side_from_constant_name(msg.constant_name)
            if battle_start:
                # Forced opening send-out (not a chosen action); skip for both sides.
                continue
            if pending_faint[side] > 0:
                # Forced post-faint replacement; consume the pending faint and skip.
                pending_faint[side] -= 1
                continue
            # For switches: place in first None slot (voluntary switches are one per side)
            if any(a is not None for a in result[side]):
                continue
            incoming_name = var_values[-1] if var_values else ""
            team_slot = _fuzzy_find_team_slot(incoming_name, side, state)
            if team_slot is None:
                team_species = [p.species.name for p in state.sides[side].team]
                raise SimulationError(
                    reason=(
                        f"Observed switch-in '{incoming_name}' on side {side} does not match "
                        f"any team slot (roster desync). Team: {team_species}"
                    )
                )
            # Singles: source_slot=0 always. Doubles: default 0 (no species info to resolve).
            result[side][0] = Action(kind=ActionKind.SWITCH, switch_to_slot=team_slot, source_slot=0)

    return result


def _validate_known_opponent_action(known_actions: dict, state: BattleState) -> None:
    """Check that each identified opponent action had nonzero predicted probability.

    Compares known_actions[1] (extracted from OCR messages) against the output of
    compute_action_probabilities. Matching is loose: kind + move_slot for MOVE actions,
    kind + switch_to_slot for SWITCH actions (target_slot is not carried by OCR).
    Skips slots where the action is None (not identified from messages).

    Skips validation entirely when the opponent's active mon is fainted: the switch-in
    is a forced post-faint replacement (either same-batch or cross-boundary), not a
    voluntary action, and compute_action_probabilities does not score forced switches.
    The _validate_forced_opponent_switch function handles correctness for that case.

    Raises UnexpectedOpponentActionError if any identified action had p=0.
    """
    opp_known = known_actions.get(1, [])
    if not any(a is not None for a in opp_known):
        return  # nothing identified; nothing to validate

    # Forced post-faint switch-in: skip probability scoring (not a voluntary action).
    opp_side = state.sides[1]
    if any(opp_side.team[idx].fainted for idx in opp_side.active_indices):
        return

    # Local import: compute_action_probabilities lives in the C++ extension; deferred
    # so sweep_actions remains importable and the early-exit paths work even when the
    # C++ binding is not yet built.
    from liveplay.engine_select import compute_action_probabilities  # type: ignore[attr-defined]
    probs = compute_action_probabilities(state, ai_idx=1)
    possible: set[tuple] = set()
    for a, p in probs:
        if p > 0.0:
            key = (a.kind, a.move_slot) if a.kind == ActionKind.MOVE else (a.kind, a.switch_to_slot)
            possible.add(key)

    for slot, action in enumerate(opp_known):
        if action is None:
            continue
        key = (action.kind, action.move_slot) if action.kind == ActionKind.MOVE else (action.kind, action.switch_to_slot)
        if key not in possible:
            # Build a readable label for the unexpected action
            if action.kind == ActionKind.MOVE:
                if action.move_override is not None:
                    act_label = action.move_override.name.replace("_", " ").title()
                elif action.move_slot == -1:
                    act_label = "Recharge"
                else:
                    opp_side = state.sides[1]
                    active_idx = (opp_side.active_indices[action.source_slot]
                                  if action.source_slot < len(opp_side.active_indices)
                                  else opp_side.active_indices[0])
                    move = opp_side.team[active_idx].move_ids[action.move_slot]
                    act_label = move.name.replace("_", " ").title()
            else:
                mon = state.sides[1].team[action.switch_to_slot]
                act_label = f"Switch → {mon.species.name.replace('_', ' ').title()}"
            opp_side = state.sides[1]
            active_idx_0 = opp_side.active_indices[0] if opp_side.active_indices else 0
            possible_labels = []
            for a, p in sorted(probs, key=lambda x: -x[1]):
                if p > 0.0:
                    if a.kind == ActionKind.MOVE:
                        if a.move_override is not None:
                            lbl = a.move_override.name.replace("_", " ").title()
                        elif a.move_slot == -1:
                            lbl = "Recharge"
                        else:
                            src = (opp_side.active_indices[a.source_slot]
                                   if a.source_slot < len(opp_side.active_indices)
                                   else active_idx_0)
                            lbl = opp_side.team[src].move_ids[a.move_slot].name.replace("_", " ").title()
                    else:
                        lbl = f"Switch→{opp_side.team[a.switch_to_slot].species.name.replace('_', ' ').title()}"
                    possible_labels.append(f"{lbl}({p*100:.1f}%)")
            raise UnexpectedOpponentActionError(
                f"slot {slot}: opponent used {act_label!r} "
                f"which had p=0; possible={possible_labels}"
            )
