# Attributable-secondaries layer of the candidate sweep. Classifies move secondary effects,
# detects whether observed messages confirm firing, injects per-slot SECONDARY_FIRES overrides,
# and injects all non-move RNG (ACCURACY, FULL_PARALYSIS, WAKE, DEFROST, CONFUSION, FLINCH, etc.).
# Ported in behavior from OLD src/simulation_runner.py. Pure leaf: no Simulator, no engine.
from __future__ import annotations

import itertools
from typing import Optional

from liveplay.battle_types import ActionGroup, MatchResult
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.moves import Move, MOVE_DATA, move_name_to_enum
from liveplay.data.status import Status
from liveplay.engine_select import SimulationError
from liveplay.rng import RNGEvent
from liveplay.state.battle import BattleState
from liveplay.state_transition import _fuzzy_find_side, _fuzzy_find_team_slot
from liveplay.sweep_actions import (
    _CALLED_MOVE_EVENTS,
    _recipient_slot,
    _resolve_attacker_slot,
    _segment_flat_messages_by_mover,
    _slot_for_name,
)

# ---------------------------------------------------------------------------
# Message ID tables
# ---------------------------------------------------------------------------

_USEDMOVE_ID = "STRINGID_USEDMOVE"

# Status-apply string IDs → Status enum (subset of possible status-apply messages)
_STATUS_APPLY_IDS: dict[str, Status] = {
    "STRINGID_PKMNFELLASLEEP": Status.SLEEP,
    "STRINGID_PKMNMADESLEEP": Status.SLEEP,
    "STRINGID_PKMNWASPOISONED": Status.POISON,
    "STRINGID_PKMNBADLYPOISONED": Status.TOXIC,
    "STRINGID_PKMNWASBURNED": Status.BURN,
    "STRINGID_PKMNWASFROZEN": Status.FREEZE,
    "STRINGID_PKMNWASPARALYZED": Status.PARALYSIS,
    "STRINGID_PKMNWASPARALYZEDBY": Status.PARALYSIS,
}

# Stat-change string IDs (boost or fell)
_STAT_CHANGE_IDS: frozenset[str] = frozenset({
    "STRINGID_STATROSE", "STRINGID_STATSHARPLY",
    "STRINGID_STATFELL", "STRINGID_STATHARSHLY",
    "STRINGID_ATTACKERSSTATROSE", "STRINGID_DEFENDERSSTATROSE",
    "STRINGID_ATTACKERSSTATFELL", "STRINGID_DEFENDERSSTATFELL",
    "STRINGID_ATTACKERSTATROSTEDRASTICALLY", "STRINGID_DEFENDERSTATROSTEDRASTICALLY",
    "STRINGID_ATTACKERSTATFELLSEVERELY", "STRINGID_DEFENDERSTATFELLSEVERELY",
    "STRINGID_STATROSEFROMITEM", "STRINGID_STATSHARPLYROSEFROMITEM",
    "STRINGID_STATFELLFROMITEM", "STRINGID_STATHARSHLYFELLFROMIITEM",
    "STRINGID_USINGITEMSTATOFPKMNROSE",
})

# Confusion-apply ID (the "became confused!" apply message, not the per-turn "is confused!")
_CONFUSION_APPLY_ID = "STRINGID_PKMNWASCONFUSED"
# Per-turn acting reminder: NOT the apply event; must not match confusion application.
_CONFUSION_ACTING_ID = "STRINGID_PKMNISCONFUSED"

# Tri Attack status map: string_id → Status (used to set TRI_ATTACK_STATUS pre-inject)
_TRI_ATTACK_STATUS_MAP: dict[str, Status] = {
    "STRINGID_PKMNWASBURNED": Status.BURN,
    "STRINGID_PKMNWASFROZEN": Status.FREEZE,
    "STRINGID_PKMNWASPARALYZED": Status.PARALYSIS,
    "STRINGID_PKMNWASPARALYZEDBY": Status.PARALYSIS,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_secondaries(move_enum: Move) -> tuple[list, list]:
    """Return (attributable, non_attributable) secondary effect lists for the move.

    Attributable: status, stat_changes, volatile=='confused', or Tri Attack → SECONDARY_FIRES.
    Non-attributable: flinch-only secondaries that route through RNGEvent.FLINCH.
    Fang-move secondary2 flinch is excluded entirely (routes through FLINCH in-engine,
    not SECONDARY_FIRES, and is not a candidate for SECONDARY_FIRES combo keys).
    """
    data = MOVE_DATA.get(move_enum)
    if data is None:
        return [], []

    attributable: list = []
    non_attributable: list = []

    secondaries = []
    if data.secondary is not None:
        secondaries.append(data.secondary)
    # secondary2 flinch-only (Fang moves) routes through FLINCH event; exclude entirely.
    if data.secondary2 is not None:
        sec2 = data.secondary2
        sec2_flinch_only = sec2.flinch and sec2.status is None and not sec2.stat_changes
        if not sec2_flinch_only:
            secondaries.append(sec2)

    for sec in secondaries:
        is_attributable = (
            sec.status is not None
            or (sec.stat_changes and len(sec.stat_changes) > 0)
            or sec.volatile == "confused"
            or move_enum == Move.TRI_ATTACK
        )
        is_flinch_only = (
            sec.flinch
            and not sec.status
            and not sec.stat_changes
            and sec.volatile != "confused"
        )

        if is_attributable:
            attributable.append(sec)
        elif is_flinch_only:
            non_attributable.append(sec)
        else:
            # Unrecognized secondary — treat as non-attributable (matches OLD behavior)
            non_attributable.append(sec)

    return attributable, non_attributable


def _secondary_match_in_messages(msgs: list[MatchResult], secondary) -> bool:
    """Return True if any message in msgs positively matches the secondary's type."""
    if secondary.status is not None:
        return any(_STATUS_APPLY_IDS.get(msg.string_id) == secondary.status for msg in msgs)
    if secondary.stat_changes and len(secondary.stat_changes) > 0:
        return any(msg.string_id in _STAT_CHANGE_IDS for msg in msgs)
    if secondary.volatile == "confused":
        return any(msg.string_id == _CONFUSION_APPLY_ID for msg in msgs)
    return False


def _secondary_fired_in_group(
    action_group: Optional[ActionGroup],
    move_enum: Move,
    secondary,
) -> Optional[bool]:
    """Return True/False if observed, None if outcome unknown from messages.

    Scans primary + secondaries for status-apply, stat-change, or confusion-apply messages.
    If a USEDMOVE message is present but no effect message, returns False (move ran, no fire).
    """
    if action_group is None:
        return None

    all_msgs = [action_group.primary] + list(action_group.secondaries)

    if _secondary_match_in_messages(all_msgs, secondary):
        return True

    # USEDMOVE present confirms the move ran; absence of effect message means no fire.
    if any(msg.string_id == _USEDMOVE_ID for msg in all_msgs):
        return False

    return None


def _secondary_fired_in_flat_messages(
    flat_messages: list[MatchResult],
    move_enum: Move,
    secondary,
    defender_side: Optional[int],
    state,
) -> Optional[bool]:
    """Return True/False/None for whether an attributable secondary fired, from flat messages.

    True if matching status/stat-change/confusion message present; False for the three known
    attributable categories when no match found; None for unrecognized fall-through.
    """
    if _secondary_match_in_messages(flat_messages, secondary):
        return True

    # Known categories: USEDMOVE confirms the move ran; no effect message = did not fire.
    if secondary.status is not None:
        return False
    if secondary.stat_changes and len(secondary.stat_changes) > 0:
        return False
    if secondary.volatile == "confused":
        return False

    return None


def _inject_attributable_secondaries(
    overrides_side: dict,
    pre_inject: dict,
    move_enum: Move,
    action_group: Optional[ActionGroup],
    source_slot: int = 0,
    flat_messages: Optional[list] = None,
    defender_side: Optional[int] = None,
    state=None,
) -> None:
    """Write per-slot SECONDARY_FIRES override for each attributable secondary of the move.

    Sets overrides_side[RNGEvent.SECONDARY_FIRES][source_slot] = fired.
    For Tri Attack with fired=True, also sets pre_inject[RNGEvent.TRI_ATTACK_STATUS].
    flat_messages is used when action_group is None (segment-based or live-play path).
    Writes nothing when outcome is unknown (fired=None).
    """
    attributable, _ = classify_secondaries(move_enum)
    if not attributable:
        return

    # Only the first attributable secondary governs SECONDARY_FIRES (one RNG event)
    sec = attributable[0]
    fired = _secondary_fired_in_group(action_group, move_enum, sec)

    if fired is None and action_group is None and flat_messages is not None:
        fired = _secondary_fired_in_flat_messages(flat_messages, move_enum, sec, defender_side, state)

    if fired is not None:
        overrides_side.setdefault(RNGEvent.SECONDARY_FIRES, {})[source_slot] = fired

    # Tri Attack: if fired, determine which status was applied and inject it
    if move_enum == Move.TRI_ATTACK and fired:
        msgs_to_check = (
            [action_group.primary] + list(action_group.secondaries)
            if action_group is not None
            else (flat_messages or [])
        )
        for msg in msgs_to_check:
            status = _TRI_ATTACK_STATUS_MAP.get(msg.string_id)
            if status is not None:
                pre_inject[RNGEvent.TRI_ATTACK_STATUS] = status
                break


# ---------------------------------------------------------------------------
# Non-move RNG injection constants
# ---------------------------------------------------------------------------

# Contact-ability proc messages: format [source, ability, target]. The roll always
# consumes the ATTACKER's (most-recent move user's) luck profile.
_PROC_STATUS_BY_IDS: frozenset[str] = frozenset({
    "STRINGID_PKMNWASPARALYZEDBY",
    "STRINGID_PKMNPOISONEDBY",
    "STRINGID_PKMNBURNEDBY",
    "STRINGID_PKMNFROZENBY",
})

# Acupressure stat name → stat index (0=Atk, 1=Def, 2=SpA, 3=SpD, 4=Spe, 5=Acc, 6=Eva)
_ACUPRESSURE_STAT_MAP: dict[str, int] = {
    "ATTACK": 0, "DEFENSE": 1, "SP. ATK": 2, "SP. DEF": 3,
    "SPEED": 4, "ACCURACY": 5, "EVASIVENESS": 6, "EVASION": 6,
}

# Effect Spore: BY-form messages → the status Effect Spore applied
_EFFECT_SPORE_BY_STATUS: dict[str, Status] = {
    "STRINGID_PKMNWASPARALYZEDBY": Status.PARALYSIS,
    "STRINGID_PKMNPOISONEDBY": Status.POISON,
    "STRINGID_PKMNMADESLEEP": Status.SLEEP,
}

# HITXTIMES hit-count → midpoint of the corresponding multi_hit_roll range
# resolve_multi_hit: r<0.35→2, r<0.70→3, r<0.85→4, else→5
_HIT_ROLL_MIDPOINTS: dict[int, float] = {2: 0.175, 3: 0.525, 4: 0.775, 5: 0.925}


# ---------------------------------------------------------------------------
# inject_non_move_rng
# ---------------------------------------------------------------------------

def inject_non_move_rng(
    overrides_0: dict,
    overrides_1: dict,
    pre_inject: dict,
    all_messages: list[MatchResult],
    state: BattleState,
    slot_map: Optional[dict] = None,
    hp_changed_by_slot: Optional[dict[tuple[int, int], bool]] = None,
) -> set[tuple[int, int]]:
    """Inject RNG overrides derived from non-move battle messages (status checks, misses, etc.).

    Writes directly into overrides_0/overrides_1/pre_inject (plain dicts, no Simulator).
    slot_map: precomputed {id(msg): (side, slot)} from _build_attacker_slot_map.
    hp_changed_by_slot: per-(side, slot) bool flags for flinch-target disambiguation.
    Returns set of (side, slot) for mons that hit themselves in confusion this turn.
    """
    confusion_self_hit_slots: set[tuple[int, int]] = set()
    last_move_attacker: Optional[tuple[int, int]] = None
    last_acupressure_attacker: Optional[tuple[int, int]] = None
    qc_observed_slots: set[tuple[int, int]] = set()
    used_with_priority0: set[tuple[int, int]] = set()

    def _name_slot(name: str, side: int) -> int:
        if len(state.sides[side].active_indices) <= 1:
            return 0
        sm = _slot_for_name(name, state, side_constraint=side)
        return sm[1] if sm is not None else 0

    def _ovr(side: int) -> dict:
        return overrides_0 if side == 0 else overrides_1

    def _set_acted_override(side: int, slot: int, event, value) -> None:
        """Write a per-acted-slot override; scalar in singles, per-slot dict in doubles."""
        ovr = _ovr(side)
        if len(state.sides[side].active_indices) <= 1:
            ovr[event] = value
            return
        d = ovr.setdefault(event, {})
        if isinstance(d, dict):
            d[slot] = value

    for i, msg in enumerate(all_messages):
        sid = msg.string_id
        var_values = msg.var_values

        if sid == _USEDMOVE_ID and var_values:
            entry = slot_map.get(id(msg)) if slot_map is not None else None
            if entry is not None:
                atk_side, atk_pos = entry
            else:
                atk_side = _fuzzy_find_side(
                    var_values[0], state, side_hint=msg.side_hint, reference_kind="actor"
                )
                atk_pos = 0
                if atk_side is not None and len(state.sides[atk_side].active_indices) > 1:
                    slot_match = _slot_for_name(var_values[0], state)
                    atk_pos = slot_match[1] if slot_match is not None else 0
            if atk_side is not None:
                last_move_attacker = (atk_side, atk_pos)
                move_name = var_values[1].upper().replace(" ", "_") if len(var_values) > 1 else ""
                if move_name == "ACUPRESSURE":
                    last_acupressure_attacker = (atk_side, atk_pos)
                else:
                    last_acupressure_attacker = None
                used_move_enum = move_name_to_enum(var_values[1]) if len(var_values) > 1 else None
                used_priority = (
                    MOVE_DATA[used_move_enum].priority
                    if used_move_enum is not None and used_move_enum in MOVE_DATA
                    else 0
                )
                if used_priority <= 0:
                    used_with_priority0.add((atk_side, atk_pos))
                # Called-move wrapper (Metronome/Sleep Talk): inject sub-move selection
                if getattr(msg, "metronome_called", None) is not None:
                    wrapper_enum = move_name_to_enum(var_values[1]) if len(var_values) > 1 else None
                    sub_event = _CALLED_MOVE_EVENTS.get(wrapper_enum, RNGEvent.METRONOME_MOVE)
                    pre_inject[sub_event] = msg.metronome_called

        elif sid == "STRINGID_PKMNISPARALYZED":
            side = (
                _fuzzy_find_side(var_values[0], state, side_hint=msg.side_hint, reference_kind="actor")
                if var_values else None
            )
            if side is not None:
                _set_acted_override(side, _name_slot(var_values[0], side), RNGEvent.FULL_PARALYSIS, False)

        elif sid in _PROC_STATUS_BY_IDS or sid == "STRINGID_PKMNMADESLEEP":
            # Contact-ability proc: inject PROC_FIRES on the attacker's side/slot
            if last_move_attacker is not None:
                p_side, p_pos = last_move_attacker
                pf = _ovr(p_side).setdefault(RNGEvent.PROC_FIRES, {})
                if isinstance(pf, dict):
                    pf[p_pos] = True
                effect_spore_status = _EFFECT_SPORE_BY_STATUS.get(sid)
                if (effect_spore_status is not None
                        and any(v.upper().replace(" ", "_") == "EFFECT_SPORE" for v in var_values)):
                    pre_inject[RNGEvent.EFFECT_SPORE_WHICH] = effect_spore_status

        elif sid == "STRINGID_PKMNFELLASLEEP":
            # No ability name — if defender has Effect Spore, treat as Effect Spore sleep proc
            if last_move_attacker is not None:
                def_side = 1 - last_move_attacker[0]
                active_indices = state.sides[def_side].active_indices
                if active_indices:
                    defender = state.sides[def_side].team[active_indices[0]]
                    if defender.ability == Ability.EFFECT_SPORE:
                        p_side, p_pos = last_move_attacker
                        pf = _ovr(p_side).setdefault(RNGEvent.PROC_FIRES, {})
                        if isinstance(pf, dict):
                            pf[p_pos] = True
                        pre_inject[RNGEvent.EFFECT_SPORE_WHICH] = Status.SLEEP

        elif sid == "STRINGID_HARVESTADDITEM":
            h_side = (
                _fuzzy_find_side(var_values[0], state, side_hint=msg.side_hint, reference_kind="actor")
                if var_values else None
            )
            if h_side is not None:
                active_indices = state.sides[h_side].active_indices
                if len(active_indices) == 1:
                    h_pos = 0
                else:
                    slot_match = _slot_for_name(var_values[0], state)
                    h_pos = slot_match[1] if slot_match is not None else 0
                pf = _ovr(h_side).setdefault(RNGEvent.PROC_FIRES, {})
                if isinstance(pf, dict):
                    pf[h_pos] = True

        elif sid == "STRINGID_PKMNWOKEUP":
            side = (
                _fuzzy_find_side(var_values[0], state, side_hint=msg.side_hint, reference_kind="actor")
                if var_values else None
            )
            if side is not None:
                _ovr(side)[RNGEvent.WAKE] = True

        elif sid == "STRINGID_PKMNFASTASLEEP":
            side = (
                _fuzzy_find_side(var_values[0], state, side_hint=msg.side_hint, reference_kind="actor")
                if var_values else None
            )
            if side is not None:
                _ovr(side)[RNGEvent.WAKE] = False

        elif sid in ("STRINGID_PKMNWASDEFROSTED", "STRINGID_PKMNWASDEFROSTED2", "STRINGID_PKMNWASDEFROSTEDBY"):
            side = (
                _fuzzy_find_side(var_values[0], state, side_hint=msg.side_hint, reference_kind="actor")
                if var_values else None
            )
            if side is not None:
                _ovr(side)[RNGEvent.DEFROST] = True

        elif sid == "STRINGID_PKMNISFROZEN":
            side = (
                _fuzzy_find_side(var_values[0], state, side_hint=msg.side_hint, reference_kind="actor")
                if var_values else None
            )
            if side is not None:
                _ovr(side)[RNGEvent.DEFROST] = False

        elif sid == "STRINGID_PKMNHEALEDCONFUSION":
            side = (
                _fuzzy_find_side(var_values[0], state, side_hint=msg.side_hint, reference_kind="actor")
                if var_values else None
            )
            if side is not None:
                _set_acted_override(side, _name_slot(var_values[0], side), RNGEvent.CONFUSION_SNAP, True)

        elif sid == "STRINGID_ITHURTCONFUSION":
            # Preceded by PKMNISCONFUSED naming the acting confused mon
            side = None
            prev_name = None
            if (
                i > 0
                and all_messages[i - 1].string_id == _CONFUSION_ACTING_ID
                and all_messages[i - 1].var_values
            ):
                prev_name = all_messages[i - 1].var_values[0]
                side = _fuzzy_find_side(
                    prev_name, state,
                    side_hint=all_messages[i - 1].side_hint,
                    reference_kind="actor",
                )
            if side is not None:
                slot = _name_slot(prev_name, side)
                _set_acted_override(side, slot, RNGEvent.CONFUSION_SELF_HIT, False)
                confusion_self_hit_slots.add((side, slot))
            else:
                # Fallback: cannot attribute — inject on both sides
                overrides_0[RNGEvent.CONFUSION_SELF_HIT] = False
                overrides_1[RNGEvent.CONFUSION_SELF_HIT] = False
                confusion_self_hit_slots.update({(0, 0), (1, 0)})

        elif sid == "STRINGID_PKMNIMMOBILIZEDBYLOVE":
            side = (
                _fuzzy_find_side(var_values[0], state, side_hint=msg.side_hint, reference_kind="actor")
                if var_values else None
            )
            if side is not None:
                _set_acted_override(side, _name_slot(var_values[0], side), RNGEvent.ATTRACT_IMMOBILIZE, False)

        elif sid == "STRINGID_ATTACKMISSED":
            side = (
                _fuzzy_find_side(var_values[0], state, side_hint=msg.side_hint, reference_kind="actor")
                if var_values else None
            )
            if side is not None:
                _set_acted_override(side, _name_slot(var_values[0], side), RNGEvent.ACCURACY, False)

        elif sid in ("STRINGID_ATTACKERSSTATROSE", "STRINGID_DEFENDERSSTATROSE"):
            if last_acupressure_attacker is not None and len(var_values) >= 2:
                stat_name = var_values[1].upper().strip()
                stat_idx = _ACUPRESSURE_STAT_MAP.get(stat_name)
                if stat_idx is not None:
                    pre_inject[RNGEvent.ACUPRESSURE_STAT] = stat_idx

        elif sid == "STRINGID_QUICKCLAWACTIVATE":
            if var_values:
                h_side = _fuzzy_find_side(
                    var_values[0], state, side_hint=msg.side_hint, reference_kind="actor"
                )
                if h_side is not None:
                    active_indices = state.sides[h_side].active_indices
                    if len(active_indices) > 1:
                        name_slot = _slot_for_name(var_values[0], state, side_constraint=h_side)
                        h_pos = name_slot[1] if name_slot is not None else 0
                    else:
                        h_pos = 0
                    qc = _ovr(h_side).setdefault(RNGEvent.QUICK_CLAW, {})
                    if isinstance(qc, dict):
                        qc[h_pos] = True
                    qc_observed_slots.add((h_side, h_pos))

        elif sid == "STRINGID_PKMNWASDRAGGEDOUT":
            if var_values:
                bare_name = var_values[0]
                if bare_name.upper().startswith("FOE "):
                    bare_name = bare_name.split(None, 1)[1] if " " in bare_name else bare_name[4:]
                phased_side = msg.side_hint if msg.side_hint is not None else 0
                slot = _fuzzy_find_team_slot(bare_name, phased_side, state)
                if slot is not None:
                    pre_inject[RNGEvent.ROAR_TARGET] = slot

        elif sid == "STRINGID_HITXTIMES":
            if var_values:
                try:
                    n_hits = int(var_values[0])
                except (ValueError, IndexError):
                    n_hits = None
                if n_hits is not None and last_move_attacker is not None:
                    roll = _HIT_ROLL_MIDPOINTS.get(n_hits, 0.5)
                    h_side, h_pos = last_move_attacker
                    mh = _ovr(h_side).setdefault(RNGEvent.MULTI_HIT_COUNT, {})
                    if isinstance(mh, dict):
                        mh[h_pos] = roll

    # Inject per-slot flinch overrides by scanning mover segments
    segments = _segment_flat_messages_by_mover(all_messages, state, slot_map=slot_map)
    flinch_forced_slots: dict[tuple[int, int], set[int]] = {}
    seg_cursor = 0
    for msg in all_messages:
        if msg.string_id == _USEDMOVE_ID:
            seg_cursor += 1
            continue
        if msg.string_id == "STRINGID_PKMNFLINCHED" and msg.var_values:
            if msg.side_hint is not None:
                flinched_side = _fuzzy_find_side(
                    msg.var_values[0], state, side_hint=msg.side_hint, reference_kind="actor"
                )
                recipient = _recipient_slot(
                    msg, state, hp_changed_by_slot=hp_changed_by_slot,
                    side_constraint=flinched_side,
                )
            else:
                recipient = _recipient_slot(msg, state, hp_changed_by_slot=hp_changed_by_slot)
            if recipient is None:
                continue
            flinched_side, flinched_slot = recipient
            attacker_side = 1 - flinched_side
            current_seg_idx = seg_cursor - 1
            if current_seg_idx < 0 or current_seg_idx >= len(segments):
                continue
            seg_side, seg_slot, _ = segments[current_seg_idx]
            if seg_side != attacker_side:
                raise SimulationError(
                    reason=(
                        f"PKMNFLINCHED for side {flinched_side} slot {flinched_slot}: "
                        f"preceding mover is on side {seg_side} slot {seg_slot}, "
                        f"but expected attacker side {attacker_side}. "
                        f"Cannot attribute flinch to a hitter."
                    )
                )
            key = (attacker_side, seg_slot)
            flinch_forced_slots.setdefault(key, set()).add(flinched_slot)

    for (side, slot) in flinch_forced_slots:
        sf = _ovr(side).setdefault(RNGEvent.FLINCH, {})
        if isinstance(sf, dict):
            sf[slot] = True

    # QUICK_CLAW=False for holders that used priority-0 with no observed QC message
    for (side, slot) in used_with_priority0:
        if (side, slot) in qc_observed_slots:
            continue
        active_indices = state.sides[side].active_indices
        if slot >= len(active_indices):
            continue
        team_idx = active_indices[slot]
        mon = state.sides[side].team[team_idx]
        if mon.item != Item.QUICK_CLAW:
            continue
        qc = _ovr(side).setdefault(RNGEvent.QUICK_CLAW, {})
        if isinstance(qc, dict) and slot not in qc:
            qc[slot] = False

    return confusion_self_hit_slots


# ---------------------------------------------------------------------------
# build_sweep_injected_overrides
# ---------------------------------------------------------------------------

def build_sweep_injected_overrides(
    all_messages_flat: list[MatchResult],
    state: BattleState,
    used_moves: dict,
    action_groups: Optional[list[ActionGroup]],
    slot_map: Optional[dict] = None,
    hp_changed_by_slot: Optional[dict[tuple[int, int], bool]] = None,
) -> tuple[dict, dict, dict, list[dict], frozenset[tuple[int, int]]]:
    """Build per-side RNG overrides and secondary combo list for one candidate turn.

    used_moves: dict[(side, source_slot), Move] from _extract_used_moves_from_groups.
    Non-move injection runs first (including observed-flinch pinning), then attributable-
    secondary injection per (side, slot). Unobserved flinch-capable movers are enumerated
    as a FLINCH True/False cross-product in secondary_combos.
    Returns (overrides_0, overrides_1, pre_inject, secondary_combos, self_hit_slots).
    Raises SimulationError for flinch-attribution mismatches.
    """
    # Identify non-attributable (flinch-only) mover slots — candidates for combo enumeration
    non_attr_movers: list[tuple[int, int]] = []
    for (side, slot), move_enum in sorted(used_moves.items()):
        _, non_attr = classify_secondaries(move_enum)
        if non_attr:
            non_attr_movers.append((side, slot))

    overrides_0: dict = {}
    overrides_1: dict = {}
    pre_inject: dict = {}

    self_hit_slots_raw = inject_non_move_rng(
        overrides_0, overrides_1, pre_inject,
        all_messages_flat, state,
        slot_map=slot_map,
        hp_changed_by_slot=hp_changed_by_slot,
    )
    self_hit_slots: frozenset[tuple[int, int]] = frozenset(self_hit_slots_raw)

    def _flinch_forced(side: int, slot: int) -> bool:
        inj = overrides_0 if side == 0 else overrides_1
        sf = inj.get(RNGEvent.FLINCH)
        return isinstance(sf, dict) and sf.get(slot) is True

    combo_movers = [m for m in non_attr_movers if not _flinch_forced(*m)]
    secondary_combo_keys = [(side, slot, RNGEvent.FLINCH) for side, slot in combo_movers]
    secondary_combos: list[dict] = [{}]
    if secondary_combo_keys:
        combo_values = list(itertools.product([True, False], repeat=len(secondary_combo_keys)))
        secondary_combos = [
            {key: val for key, val in zip(secondary_combo_keys, vals)}
            for vals in combo_values
        ]

    if action_groups:
        ag_cursor = [0, 0]  # fallback cursor used only when slot_map is None (mirrors OLD)
        for grp in action_groups:
            if grp.primary.string_id != _USEDMOVE_ID or not grp.primary.var_values:
                continue
            if slot_map is not None:
                entry = slot_map.get(id(grp.primary))
                if entry is None:
                    continue
                side, source_slot = entry
            else:
                attacker_name = grp.primary.var_values[0]
                side = _fuzzy_find_side(
                    attacker_name, state, side_hint=grp.primary.side_hint, reference_kind="actor"
                )
                if side is None:
                    continue
                source_slot = _resolve_attacker_slot(side, attacker_name, state, ag_cursor)
            move_enum = used_moves.get((side, source_slot))
            if move_enum is None:
                continue
            ovr_target = overrides_0 if side == 0 else overrides_1
            _inject_attributable_secondaries(
                ovr_target, pre_inject, move_enum, grp,
                source_slot=source_slot,
                defender_side=1 - side,
                state=state,
            )
    else:
        segments = _segment_flat_messages_by_mover(all_messages_flat, state, slot_map=slot_map)
        for seg_side, seg_slot, seg_msgs in segments:
            move_enum = used_moves.get((seg_side, seg_slot))
            if move_enum is None:
                continue
            ovr_target = overrides_0 if seg_side == 0 else overrides_1
            _inject_attributable_secondaries(
                ovr_target, pre_inject, move_enum, None,
                source_slot=seg_slot,
                flat_messages=seg_msgs,
                defender_side=1 - seg_side,
                state=state,
            )

    return overrides_0, overrides_1, pre_inject, secondary_combos, self_hit_slots
