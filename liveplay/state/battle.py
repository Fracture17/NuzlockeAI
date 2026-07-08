# BattleState dataclass: top-level snapshot of a full battle, containing both sides and field state.
import copy
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

from liveplay.state.side import SideState, FormatEnum


class WeatherEnum(IntEnum):
    NONE = 0
    SUNNY = 1       # Sunny Day / Drought
    RAINY = 2       # Rain Dance / Drizzle
    SANDSTORM = 3
    HAIL = 4
    HEAVY_RAIN = 5  # Primordial Sea
    HARSH_SUN = 6   # Desolate Land
    STRONG_WIND = 7 # Delta Stream


class TerrainEnum(IntEnum):
    NONE = 0
    ELECTRIC = 1
    GRASSY = 2
    PSYCHIC = 3
    MISTY = 4


class PseudoWeather(IntEnum):
    TRICK_ROOM = 1
    GRAVITY = 2
    MAGIC_ROOM = 3
    WONDER_ROOM = 4
    TAILWIND_FIELD = 5  # field-wide tailwind (not per-side)


@dataclass
class BattleState:
    sides: tuple[SideState, SideState]

    weather: WeatherEnum = WeatherEnum.NONE
    weather_turns: int = 0  # -1 = permanent (ability-set in RnB)

    terrain: TerrainEnum = TerrainEnum.NONE
    terrain_turns: int = 0  # -1 = permanent

    # list of (PseudoWeather, turns_remaining)
    pseudo_weather: list[tuple[PseudoWeather, int]] = field(default_factory=list)

    turn_number: int = 1
    # Echoed Voice multiplier: 1 on first use, increments each consecutive turn any mon uses Echoed Voice (max 5); resets if no one uses it a turn
    echoed_voice_multiplier: int = 0
    echoed_voice_used_this_turn: bool = False  # set True when any mon uses Echoed Voice; cleared at EOT
    # int(Move) of the last move successfully launched by any Pokemon this battle; -1 if none
    battle_last_move: int = -1
    format: FormatEnum = FormatEnum.SINGLES

    # Side indices in execution order for the current turn; populated by speed_order / resolve_turn
    turn_order: list[int] = field(default_factory=list)
    # Immutable snapshot of the PREVIOUS turn's execution order; read by next-turn AI scoring
    # (Analytic/Payback/Bolt Beak/Fishious Rend bug replication). () before any turn completes.
    prev_turn_order: tuple[int, ...] = ()

    is_trainer_battle: bool = True
    level_cap: Optional[int] = None
    # One frozenset per opponent active slot; each set contains player team indices on field during that opponent's tenure.
    exp_participants: tuple[frozenset, ...] = ()

    def __hash__(self):
        return hash((
            self.sides,
            self.weather,
            self.weather_turns,
            self.terrain,
            self.terrain_turns,
            tuple(self.pseudo_weather),
            self.turn_number,
            self.echoed_voice_multiplier,
            self.echoed_voice_used_this_turn,
            self.battle_last_move,
            self.format,
            tuple(self.turn_order),
            self.prev_turn_order,
            self.is_trainer_battle,
            self.level_cap,
            self.exp_participants,
        ))

    def __copy__(self):
        new_sides = tuple(copy.copy(s) for s in self.sides)
        new_obj = object.__new__(BattleState)
        new_obj.__dict__.update(self.__dict__)
        new_obj.sides = new_sides
        new_obj.pseudo_weather = list(self.pseudo_weather)
        new_obj.turn_order = list(self.turn_order)
        return new_obj
