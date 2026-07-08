# Side/Pokémon/move identification helpers used by simulation_runner.py.
from __future__ import annotations

import logging
from typing import Literal, Optional

from rapidfuzz.distance import Levenshtein as _Lev

from .state.battle import BattleState
from .data.name_aliases import emulator_species_name

__all__ = [
    "_side_from_constant_name",
    "_fuzzy_find_side",
    "_fuzzy_find_team_slot",
    "_fuzzy_find_team_slots",
    "_fuzzy_find_move_slot",
    "SideHintMissingError",
    "SideHintContradictionError",
    "RosterAmbiguityError",
    "ActorNotActiveError",
]

logger = logging.getLogger(__name__)

_TRAINER_SIDE_CONSTANT_NAMES: frozenset[str] = frozenset({
    # INTROSENDOUT (id_value=1) — trainer sends out
    "sText_Trainer1SentOutPkmn",
    "sText_Trainer1SentOutTwoPkmn",
    "sText_TwoTrainersSentPkmn",
    # RETURNMON (id_value=2) — trainer withdraws
    "sText_Trainer1WithdrewPkmn",
    # SWITCHINMON (id_value=3) — trainer switches in mid-battle
    "sText_Trainer1SentOutPkmn2",
})


def _side_from_constant_name(constant_name: str) -> int:
    """Return 1 for trainer-side send-out/withdraw constant names, 0 for player-side."""
    return 1 if constant_name in _TRAINER_SIDE_CONSTANT_NAMES else 0


def _species_match_threshold(name: str) -> int:
    return max(1, len(name) // 5)


class SideHintMissingError(ValueError):
    """Raised when an actor-naming battle message reaches side resolution without a
    side_hint. The acting side is always derivable from the Foe prefix (1=opponent,
    0=player); a missing hint means the matcher/template failed to emit one."""


class SideHintContradictionError(ValueError):
    """Raised when a side_hint contradicts the battle state (the hinted side's active
    does not match the named species, but the opposite side's active does)."""


class RosterAmbiguityError(ValueError):
    """Raised when multiple team slots on one side fuzzy-match the same OCR'd name.

    The opponent may legally carry two of the same species (player side cannot — Nuzlocke
    no-duplicates rule). A switch-in naming that species cannot be resolved from the name
    alone; guessing the first match is a silent desync."""


class ActorNotActiveError(ValueError):
    """Raised when an actor-naming message names a species that matches neither side's active.

    The actor of a USEDMOVE/status/etc. message is always currently on the field. If the
    OCR'd name matches neither active, the engine's view of who is active is wrong — a
    genuine desync that must not be silently accepted."""


def _recognizable_anywhere(upper_name: str, state) -> bool:
    """Return True if upper_name fuzzy-matches at least one team slot on either side (active or benched)."""
    for side in state.sides:
        for pokemon in side.team:
            species_name = emulator_species_name(pokemon.species)
            if _Lev.distance(upper_name, species_name) <= _species_match_threshold(species_name):
                return True
    return False


def _fuzzy_find_side(
    bare_name: str,
    state,
    side_hint: Optional[int] = None,
    reference_kind: Literal["actor", "benched"] = "benched",
) -> int:
    """Resolve which battle side a message refers to.

    side_hint (Foe prefix: 1=opponent, 0=player) is REQUIRED — missing it is a hard error
    (SideHintMissingError). The name is a loud consistency check:
    - If the hinted side's active does NOT match but the opposite side's active does:
      SideHintContradictionError (always raised regardless of reference_kind).
    - If neither active matches and reference_kind="actor": ActorNotActiveError if the name is
      recognizable (fuzzy-matches any team slot anywhere) — genuine desync. If the name matches
      nothing anywhere (pure OCR garble), trust the hint instead (preserves garble-tolerance).
    - If neither active matches and reference_kind="benched": trust the hint (switch-in path).
    - Mirror matches (both actives match) and exact-side matches trust the hint.
    """
    if side_hint is None:
        raise SideHintMissingError(
            f"cannot resolve the acting side for {bare_name!r} without a side_hint "
            f"(every actor-naming battle message must carry a Foe-prefix-derived hint)"
        )

    upper_name = bare_name.upper()

    def _active_matches(side_idx: int) -> bool:
        for team_idx in state.sides[side_idx].active_indices:
            species_name = emulator_species_name(state.sides[side_idx].team[team_idx].species)
            if _Lev.distance(upper_name, species_name) <= _species_match_threshold(species_name):
                return True
        return False

    hint_matches = _active_matches(side_hint)
    other_matches = _active_matches(1 - side_hint)

    if not hint_matches and other_matches:
        raise SideHintContradictionError(
            f"side_hint={side_hint} for {bare_name!r} contradicts the battle state: "
            f"side {side_hint}'s active does not match the name but side {1 - side_hint}'s does"
        )

    if not hint_matches and not other_matches and reference_kind == "actor":
        # Only raise if the name is recognizable (matches ≥1 slot anywhere) — pure OCR
        # garble that matches nothing is not a desync; trust the structural side_hint.
        if _recognizable_anywhere(upper_name, state):
            raise ActorNotActiveError(
                f"actor message names {bare_name!r} (side_hint={side_hint}) but that species "
                f"is not currently active on either side — possible desync"
            )

    return side_hint


def _fuzzy_find_team_slots(name: str, side_idx: int, state) -> list[int]:
    """Fuzzy-match name against species on one side, returning all candidate team slots.

    When more than one slot matches the same species, reduce by switch-eligibility:
    a slot that is currently active or fainted cannot be the target of a switch-in, so
    it is excluded. If reduction leaves a single slot the ambiguity is resolved; if it
    leaves several, all are returned so the caller can fan out and try each. If every
    match is ineligible (e.g. one active, one fainted), fall back to the full match set
    rather than returning nothing — that genuinely-ambiguous case fails loud upstream.
    """
    upper_name = name.upper()
    matching_slots: list[int] = []
    for slot_i, pokemon in enumerate(state.sides[side_idx].team):
        species_name = emulator_species_name(pokemon.species)
        threshold = _species_match_threshold(species_name)
        if _Lev.distance(upper_name, species_name) <= threshold:
            matching_slots.append(slot_i)
    if len(matching_slots) <= 1:
        return matching_slots
    side = state.sides[side_idx]
    eligible = [s for s in matching_slots
                if s not in side.active_indices and not side.team[s].fainted]
    return eligible if eligible else matching_slots


def _fuzzy_find_team_slot(name: str, side_idx: int, state) -> Optional[int]:
    """Fuzzy-match name against species names on one side. Returns team slot index or None.

    Reduces duplicate-species matches by switch-eligibility (see _fuzzy_find_team_slots).
    Raises RosterAmbiguityError if more than one slot remains after reduction — an
    unresolvable duplicate must fail loud rather than silently return a possibly-wrong
    first match. Callers that can fan out should use _fuzzy_find_team_slots directly.
    """
    slots = _fuzzy_find_team_slots(name, side_idx, state)
    if len(slots) > 1:
        raise RosterAmbiguityError(
            f"name {name!r} fuzzy-matches multiple team slots on side {side_idx}: "
            f"slots {slots} — cannot determine which duplicate to use"
        )
    return slots[0] if slots else None


def _fuzzy_find_move_slot(move_name: str, poke) -> int:
    """Return the best-matching move slot index for move_name, or -1 if no match."""
    best_slot = -1
    best_dist = float("inf")
    for slot_i, move_enum in enumerate(poke.move_ids):
        candidate = move_enum.name.replace("_", " ")
        dist = _Lev.distance(move_name.upper(), candidate.upper())
        if dist < best_dist:
            best_dist = dist
            best_slot = slot_i
    if best_slot < 0 or best_dist > 4:
        return -1
    return best_slot
