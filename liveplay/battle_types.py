"""Shared data types for the NuzlockeAI battle pipeline."""
from __future__ import annotations
from dataclasses import dataclass, field

__all__ = ["MatchResult", "Constraints", "ActionGroup", "HpReading"]

@dataclass
class MatchResult:
    string_id:     str
    id_value:      int
    constant_name: str
    var_values:    list[str]   # one entry per extracting slot (VAR or Enum), in order
    score:         int         # total edit-distance across all literal/enum tokens
    context_score: int = 0    # Foe-prefix side-mismatch penalty; final tie-breaker in template ranking (lower wins)
    matched_text:  str  = ""  # canonical reconstructed message (template literals + matched vars)
    slot_labels:   list = field(default_factory=list)  # placeholder name per extracting slot
    literal_coverage: float = 1.0  # fraction of OCR words explained by literal/enum segments (not free VARs); 1.0 = fully explained
    side_hint:     int | None = None  # side of var_values[0] from the Foe prefix: 1=opponent (Foe-prefixed), 0=player, None if slot 0 isn't a Pokémon name
    name_side_slots: dict = field(default_factory=dict)  # extracting-slot index -> side (0=player, 1=opponent) for each POKEMON_NAME slot
    metronome_called: "Move | None" = None  # set by _collapse_metronome_calls: the Move a called-move wrapper USEDMOVE (Metronome/Sleep Talk) resolved into (the called-move USEDMOVE is dropped)

    def side_of_name_slot(self, extracting_idx: int) -> "int | None":
        """Side (0/1) of the POKEMON_NAME var at the given extracting-slot index, or None
        if that index is not a resolvable pokémon-name slot. Callers that require a side
        (e.g. the pinch-berry stat verifier) treat None as a fail-loud condition."""
        return self.name_side_slots.get(extracting_idx)

@dataclass
class Constraints:
    """Optional caller-supplied constraints to narrow variable slot matching."""
    valid_pokemon:  list[str] | None = None
    valid_moves:    list[str] | None = None
    valid_items:    list[str] | None = None
    valid_abilities: list[str] | None = None
    trainer_name:   str | None = None
    trainer_class:  str | None = None
    unconstrained_moves: bool = False   # if True, move names match against all known moves (for Metronome/Assist)
    unconstrained_names: bool = False   # if True, Pokémon names match against all known species (for Transform/Illusion)

@dataclass
class ActionGroup:
    """One primary message + all following secondary messages for the same in-game action."""
    primary:     MatchResult
    secondaries: list[MatchResult] = field(default_factory=list)
    hp_readings: list[HpReading]  = field(default_factory=list)

@dataclass
class HpReading:
    """Result of reading the opponent's HP bar pixels.

    k: number of non-black pixels in the bar row. None means the bar was animating
       (an unexpected pixel color was found) and the reading should be discarded.
    hp_min/hp_max/hp_mid: HP range derived from k and max_hp. None if max_hp not supplied
       or if k is None.

    Formula: bar shows floor(hp * 48 / max_hp) pixels, minimum 1 if hp > 0.
    A change of 1 pixel corresponds to max_hp/48 HP — changes smaller than that
    are invisible. k=0 means the bar is fully empty (KO).
    """
    k:      int | None
    hp_min: int | None
    hp_max: int | None
    hp_mid: int | None
