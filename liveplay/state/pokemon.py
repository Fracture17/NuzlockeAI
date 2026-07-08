# PokemonState dataclass: flat, fast-copyable snapshot of a single Pokemon's in-battle state.
import copy
import math
from dataclasses import dataclass, field
from enum import IntEnum, IntFlag
from typing import Optional

from liveplay.data.species import Species, SPECIES_DATA
from liveplay.data.natures import Nature, Stat, NATURE_DATA
from liveplay.data.moves import Move
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.types import Type
from liveplay.data.status import Status


class GenderEnum(IntEnum):
    MALE = 0
    FEMALE = 1
    GENDERLESS = 2


class Volatile(IntFlag):
    """Boolean volatile flags stored as bitfield in PokemonState.volatiles."""
    NONE = 0
    CONFUSED = 1
    LEECH_SEEDED = 2
    CURSED = 4
    ENCORE_ACTIVE = 8
    TAUNT_ACTIVE = 16
    TORMENT = 32
    FLINCHED = 64
    CHARGING = 128        # two-turn moves (Solar Beam charging, Fly, Dig, etc.)
    RECHARGING = 256      # must recharge (Hyper Beam, etc.)
    LOCKED_MOVE = 512     # Outrage/Thrash lock
    MINIMIZE = 1024       # doubled damage from certain moves
    DEFENSE_CURL = 2048   # powers up Rollout
    SUBSTITUTE = 4096
    DESTINY_BOND = 8192
    PERISH_SONG_ACTIVE = 16384
    AQUA_RING = 32768
    INGRAIN = 65536
    POWER_TRICK = 131072  # swapped Atk and Def
    CHOICE_LOCKED = 262144   # locked to Choice item move slot; switches still allowed
    UNBURDEN = 524288        # Unburden speed boost active (item consumed while ability=UNBURDEN)
    FLASH_FIRE = 1048576     # Flash Fire triggered; next Fire move is 1.5x powered
    ENDURE_ACTIVE = 2097152  # Endure used this turn; survive next KO hit at 1 HP
    PROTECT_USED = 4194304   # protect-family move used last turn; consecutive use fails
    ATTRACTED = 8388608      # infatuated; 50% chance to be unable to act
    TRUANT_LOAFING = 16777216  # set when Truant loafs; cleared to allow acting next turn
    HELPING_HAND = 33554432   # Helping Hand boost active; next damaging move by this mon is 1.5×
    PROTEAN_USED = 67108864   # Protean/Libero type change already triggered this switch-in
    IDENTIFIED = 134217728    # Foresight/Odor Sleuth: Ghost immunity to Normal/Fighting removed


class VolatileEffect(IntEnum):
    """Timed volatile effects stored in PokemonState.timed_volatiles as (effect, turns)."""
    ENCORE = 1
    TAUNT = 2
    PERISH_SONG = 3
    BOUND = 4         # Wrap, Fire Spin, etc.
    DISABLE = 5
    EMBARGO = 7
    MAGNET_RISE = 8
    TELEKINESIS = 29      # Lifted off ground for 3 turns; treated as ungrounded
    SLOW_START = 9    # Regigigas ability timer
    STOCKPILE = 10
    ROOST = 11   # Roost temporarily removes Flying type until end of turn
    RAMPAGING = 12  # Outrage/Thrash/Petal Dance mid-rampage lock
    DROWSY = 20       # Yawn: delayed sleep; converts to SLEEP when expired
    THROAT_CHOPPED = 21  # Can't use sound moves for 2 turns
    TRAPPED = 22         # Cannot switch voluntarily (Anchor Shot, Spirit Shackle, Jaw Lock, etc.)
    OCTOLOCK = 23        # Permanent trap marker; also lowers Def/SpDef each EOT
    GROUNDED = 24        # Thousand Arrows/Smack Down: treat as grounded; Ground hits and terrain apply
    LASER_FOCUS = 25     # Next move always crits; expires after 1 turn
    NIGHTMARE = 26       # Sleeping target loses 1/4 HP each EOT; permanent until target wakes
    SEMI_INVULNERABLE = 27  # Pokemon is mid-air/underground; most moves miss it
    NO_RETREAT = 28          # Marks that No Retreat has been used; prevents second use
    LEECH_SEED_SOURCE_SLOT = 30  # Stores slot position (0|1) of the seeder; never expires
    BOUND_SOURCE_SLOT = 31       # Stores slot position (0|1) of the trapper; never expires
    # int field = team_idx of the inflictor (not a duration; never expires).
    BOUND_SOURCE_ID = 32         # Team index of the mon that applied BOUND
    TRAPPED_SOURCE_ID = 33       # Team index of the mon that applied TRAPPED (not for NO_RETREAT)
    CHARGING_MOVE = 34           # int field = Move id being charged when it differs from the slot
    #                              move (called two-turn: Metronome/Copycat -> Solar Beam).
    #                              Payload, never ticks; mirrors Showdown twoturnmove.onLockMove.


def compute_stat(stat: Stat, base: int, iv: int, nature: Nature, level: int) -> int:
    """Compute a single stat value. No EVs (Run & Bun removes EVs)."""
    if stat == Stat.HP:
        return math.floor((2 * base + iv) * level / 100) + level + 10
    else:
        intermediate = math.floor((2 * base + iv) * level / 100) + 5
        nat = NATURE_DATA[nature]
        if nat.boosted == stat:
            return math.floor(intermediate * nat.boost_multiplier)
        elif nat.lowered == stat:
            return math.floor(intermediate * nat.lower_multiplier)
        return intermediate


@dataclass
class PokemonState:
    # Required construction fields
    species: Species
    nature: Nature
    ivs: tuple[int, int, int, int, int, int]  # (hp_iv, atk_iv, def_iv, spa_iv, spd_iv, spe_iv)
    gender: GenderEnum

    # Optional construction fields
    level: int = 50
    exp: int = 0
    ability: Ability = Ability.NONE
    item: Item = Item.NONE
    status: Status = Status.NONE

    # Move slots — filled with NONE/0 if fewer than 4 moves
    move_ids: tuple[Move, Move, Move, Move] = (Move.NONE, Move.NONE, Move.NONE, Move.NONE)
    move_pp: tuple[int, int, int, int] = (0, 0, 0, 0)

    # Battle state — computed in __post_init__ if not provided
    stats: Optional[tuple[int, int, int, int, int, int]] = None  # (hp, atk, def, spa, spd, spe) computed values
    max_hp: Optional[int] = None
    hp: Optional[int] = None
    types: Optional[tuple[Type, ...]] = None  # overridable (Soak, etc.)

    # Stage modifiers: Atk, Def, SpA, SpD, Spe, Acc, Eva
    stat_stages: tuple[int, int, int, int, int, int, int] = (0, 0, 0, 0, 0, 0, 0)

    # Volatile state
    volatiles: int = 0                 # Volatile bitfield
    timed_volatiles: list[tuple[VolatileEffect, int]] = field(default_factory=list)

    # Turn counter — resets on switch-out
    turns_in_battle: int = 0

    # Dedicated toxic counter — set to 1 on TOXIC application, incremented each residual tick, resets on switch-out
    toxic_turns: int = 0

    # Sleep/confusion turn counters — reset on wake/snap/switch-in
    sleep_turns: int = 0       # turns slept while action-eligible; reset on wake and switch-in
    confusion_turns: int = 0   # turns confused while action-eligible; reset on snap
    is_rest_sleep: bool = False  # True if current sleep caused by Rest; cleared on wake

    # Locked move slot: which move slot is forced when ENCORE_ACTIVE or LOCKED_MOVE is set
    locked_slot: int = -1

    # Charging move slot: which slot is being charged for a two-turn move (-1 = not charging)
    charging_move_slot: int = -1

    # HP of active Substitute; 0 when no sub
    sub_hp: int = 0

    # Move slot last executed; -1 if none (used by Encore/Disable)
    last_used_slot: int = -1

    fainted: bool = False

    # True once the Pokemon has executed at least one move action this battle; persists across switch-outs.
    # Used by Truant to re-apply TRUANT_LOAFING on switch-in after the Pokemon has already moved.
    has_acted: bool = False

    crit_stage: int = 0   # cumulative crit stage modifier (e.g. from LANSAT_BERRY)

    # Metronome item: tracks consecutive use of the same move for stacking damage bonus
    metronome_count: int = 0     # current consecutive use count (1-10); 0 = not started
    metronome_last_move: int = -1  # Move enum value of last move used with Metronome item
    # int(Move) of the last move this Pokemon launched; -1 until this Pokemon acts; resets on switch-out
    mirror_move_last_move: int = -1

    # Tracks the last berry consumed; used by Harvest to restore it
    consumed_berry: Item = Item.NONE

    # Per-turn damage/stat tracking — cleared at turn start; used for variable-BP and Counter/Mirror Coat
    took_damage_this_turn: bool = False
    had_stat_lowered_this_turn: bool = False
    had_stat_raised_this_turn: bool = False
    last_move_failed: bool = False
    last_physical_damage_taken: int = 0
    last_special_damage_taken: int = 0
    last_damage_taken: int = 0
    # True if this mon used Sucker Punch last turn (regardless of success); cleared at turn start
    sucker_punch_last_turn: bool = False

    base_ability: Ability = Ability.NONE   # original ability; set to `ability` in __post_init__ if not provided
    saved_ability: Ability = Ability.NONE  # stores `ability` while Neutralizing Gas suppresses it
    is_mega: bool = False                  # has this Pokemon mega evolved this battle

    # Bitmask tracking which move slots have been used (bits 0-3 for slots 0-3); used by Last Resort
    moves_used: int = 0

    # Rollout / Ice Ball hit counter — resets on miss, faint, or switch-out; 0 = not in sequence
    rollout_hits: int = 0
    # True once Defense Curl has been used this battle (persists until switch-out); doubles Rollout/Ice Ball BP
    defense_curl_used: bool = False
    # Weight reduction in kg from Autotomize (each use subtracts 100 kg, floor 0.1 kg)
    weight_kg_reduced: float = 0.0
    # Protect success probability denominator: 0 = no consecutive protect, else cascades 3→9→27→81...
    protect_counter: int = 0

    # Stockpile counter and the actual Def/SpD stage deltas accumulated; all reset on switch-out or after Spit Up/Swallow
    stockpile_count: int = 0
    stockpile_def_boost: int = 0
    stockpile_spd_boost: int = 0

    def __post_init__(self):
        if self.stats is None:
            sp = SPECIES_DATA[self.species]
            bases = (sp.base_hp, sp.base_atk, sp.base_def, sp.base_spa, sp.base_spd, sp.base_spe)
            ivs = self.ivs
            self.stats = tuple(
                compute_stat(Stat(i), bases[i], ivs[i], self.nature, self.level)
                for i in range(6)
            )
            # Shedinja always has exactly 1 HP regardless of level or IVs
            if self.species == Species.SHEDINJA:
                self.stats = (1,) + self.stats[1:]
        # Shedinja's ability is always Wonder Guard (set if not explicitly overridden)
        if self.species == Species.SHEDINJA and self.ability == Ability.NONE:
            self.ability = Ability.WONDER_GUARD
        if self.max_hp is None:
            self.max_hp = self.stats[0]
        if self.hp is None:
            self.hp = self.max_hp
        if self.types is None:
            self.types = SPECIES_DATA[self.species].types
        if self.base_ability == Ability.NONE and self.ability != Ability.NONE:
            self.base_ability = self.ability
        # volatiles is declared as a PLAIN int bitfield, but `int | Volatile.X` returns a
        # Volatile IntFlag (subclass reflected-operator priority), which then serializes as
        # a tagged enum and breaks state-fingerprint parity with C++. Coerce here and in
        # _replace so the representation is always a bare int.
        self.volatiles = int(self.volatiles)

    def __hash__(self):
        return hash((
            self.species, self.nature, self.ivs, self.gender, self.level, self.exp,
            self.ability, self.item, self.status,
            self.move_ids, self.move_pp,
            self.stats, self.max_hp, self.hp, self.types,
            self.stat_stages,
            self.volatiles, tuple(self.timed_volatiles),
            self.turns_in_battle, self.toxic_turns,
            self.sleep_turns, self.confusion_turns, self.is_rest_sleep,
            self.locked_slot, self.charging_move_slot,
            self.sub_hp, self.last_used_slot, self.fainted, self.has_acted,
            self.crit_stage, self.metronome_count, self.metronome_last_move,
            self.mirror_move_last_move,
            self.consumed_berry,
            self.took_damage_this_turn, self.had_stat_lowered_this_turn,
            self.had_stat_raised_this_turn, self.last_move_failed,
            self.last_physical_damage_taken, self.last_special_damage_taken,
            self.last_damage_taken, self.sucker_punch_last_turn,
            self.base_ability, self.saved_ability, self.is_mega,
            self.moves_used, self.rollout_hits, self.defense_curl_used,
            self.weight_kg_reduced, self.protect_counter,
            self.stockpile_count, self.stockpile_def_boost, self.stockpile_spd_boost,
        ))

    def __copy__(self):
        new_obj = object.__new__(PokemonState)
        new_obj.__dict__.update(self.__dict__)
        new_obj.timed_volatiles = list(self.timed_volatiles)
        return new_obj

    def _replace(self, **kwargs):
        """Return a new PokemonState with specified fields changed, skipping __post_init__."""
        new_obj = copy.copy(self)
        for k, v in kwargs.items():
            # Keep volatiles a plain int (see __post_init__): IntFlag results from bitwise
            # ops must not leak into state, or serialization diverges from C++.
            setattr(new_obj, k, int(v) if k == "volatiles" else v)
        return new_obj
