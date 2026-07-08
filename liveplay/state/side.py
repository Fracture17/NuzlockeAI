# SideState dataclass: one trainer's team and battlefield state for a single battle side.
import copy
from dataclasses import dataclass, field
from enum import IntEnum

from typing import Optional

from liveplay.state.pokemon import PokemonState
from liveplay.data.moves import Move


class FormatEnum(IntEnum):
    SINGLES = 0
    DOUBLES = 1


class SideCondition(IntEnum):
    REFLECT = 1
    LIGHT_SCREEN = 2
    AURORA_VEIL = 3
    STEALTH_ROCK = 4
    SPIKES_1 = 5
    SPIKES_2 = 6
    SPIKES_3 = 7
    TOXIC_SPIKES_1 = 8
    TOXIC_SPIKES_2 = 9
    STICKY_WEB = 10
    TAILWIND = 11
    LUCKY_CHANT = 12
    SAFEGUARD = 13


@dataclass
class SideState:
    team: list[PokemonState]  # up to 6
    format: FormatEnum = FormatEnum.SINGLES

    # Active slots: [0] for singles, [0, 1] for doubles
    active_indices: list[int] = field(default_factory=list)

    # list of (SideCondition, turns_remaining); turns=-1 for permanent
    side_conditions: list[tuple[SideCondition, int]] = field(default_factory=list)

    mega_used: bool = False   # has a Pokemon on this side mega evolved this battle
    # Baton Pass pending data: (stat_stages, volatiles_bitmask, timed_volatiles, crit_stage, sub_hp) or None
    baton_pass_data: Optional[tuple[tuple[int, ...], int, tuple, int, int]] = None
    ally_fainted_last_turn: bool = False  # True if any Pokemon on this side fainted last turn; used by Retaliate
    wish_pending: Optional[tuple[int, int, int]] = None  # (turns_remaining, hp_to_heal, slot_index) or None
    future_sight_pending: Optional[tuple[int, int, Move, int]] = None  # (turns_remaining, damage, move_enum, target_slot_pos) or None
    imprisoned_moves: frozenset[Move] = field(default_factory=frozenset)  # moves blocked by Imprison
    redirect_target: int = -1          # Follow Me / Rage Powder: slot index to redirect single-target moves to; -1 = none
    redirect_is_rage_powder: bool = False  # True if the current redirect was set by Rage Powder (not Follow Me)

    def __post_init__(self):
        if not self.active_indices:
            if self.format == FormatEnum.SINGLES:
                self.active_indices = [0]
            else:
                self.active_indices = [0, 1]

    def spikes_count(self) -> int:
        """Returns 0–3 based on active Spikes layers."""
        active = {cond for cond, _ in self.side_conditions}
        if SideCondition.SPIKES_3 in active:
            return 3
        if SideCondition.SPIKES_2 in active:
            return 2
        if SideCondition.SPIKES_1 in active:
            return 1
        return 0

    def toxic_spikes_count(self) -> int:
        """Returns 0–2 based on active Toxic Spikes layers."""
        active = {cond for cond, _ in self.side_conditions}
        if SideCondition.TOXIC_SPIKES_2 in active:
            return 2
        if SideCondition.TOXIC_SPIKES_1 in active:
            return 1
        return 0

    def __hash__(self):
        return hash((
            tuple(self.team),
            self.format,
            tuple(self.active_indices),
            tuple(self.side_conditions),
            self.mega_used,
            self.baton_pass_data,
            self.ally_fainted_last_turn,
            self.wish_pending,
            self.future_sight_pending,
            self.imprisoned_moves,
            self.redirect_target,
            self.redirect_is_rage_powder,
        ))

    def __copy__(self):
        new_obj = object.__new__(SideState)
        new_obj.__dict__.update(self.__dict__)
        new_obj.team = list(self.team)                          # new list, same poke refs
        new_obj.active_indices = list(self.active_indices)
        new_obj.side_conditions = list(self.side_conditions)
        return new_obj
