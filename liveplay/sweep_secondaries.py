# Attributable-secondaries layer of the candidate sweep. Classifies move secondary effects
# into attributable (status/stat_changes/confused volatile/Tri Attack) vs non-attributable
# (flinch-only), detects whether observed messages confirm firing, and injects per-slot
# SECONDARY_FIRES overrides. Ported in behavior from OLD src/simulation_runner.py.
from __future__ import annotations

from typing import Optional

from liveplay.battle_types import ActionGroup, MatchResult
from liveplay.data.moves import Move, MOVE_DATA
from liveplay.data.status import Status
from liveplay.rng import RNGEvent

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
