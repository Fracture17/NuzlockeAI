# Global zero-cost debug logger. None logger = no-op; BattleLogger translates events to strings.
from enum import IntEnum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from liveplay.state.battle import BattleState


class LogEvent(IntEnum):
    TURN_START = 1
    ACTION_ORDER = 2
    UPKEEP_START = 3
    UPKEEP_END = 4
    CANT_SLEEP = 5
    SLEEP_COUNTER = 6
    WAKE_UP = 7
    CANT_FROZEN = 8
    THAW = 9
    CANT_PARALYSIS = 10
    CANT_FLINCH = 11
    SNAP_OUT_CONFUSION = 12
    HIT_SELF_CONFUSION = 13
    CANT_INFATUATION = 14
    CANT_RECHARGE = 15
    CANT_TRUANT = 16
    CANT_TAUNT = 17
    CANT_ENCORE = 18
    CANT_DISABLE = 19
    CANT_IMPRISON = 20
    CANT_TORMENT = 21
    CANT_CHOICE_LOCKED = 22
    CANT_TRAPPED = 23
    CANT_NO_PP = 24
    CANT_GRAVITY = 25
    FOCUS_PUNCH_INTERRUPTED = 26
    MOVE_USE = 27
    CALLED_MOVE = 28
    NATURE_POWER_RESOLVE = 29
    PP_USE = 30
    FUTURE_SIGHT_STORE = 31
    FUTURE_SIGHT_HIT = 32
    MOVE_MISS = 33
    MOVE_BLOCKED = 34
    MOVE_IMMUNE = 35
    MOVE_NO_TARGET = 36
    MOVE_FAIL = 37
    CHARGE_TURN = 38
    SEMI_INVULNERABLE_ENTER = 39
    SEMI_INVULNERABLE_EXIT = 40
    MAGIC_BOUNCE_REFLECT = 41
    MAGIC_COAT_REFLECT = 42
    GRAVITY_CANCEL_CHARGE = 43
    PURSUIT_INTERCEPT = 44
    DAMAGE = 45
    CRIT = 46
    EFFECTIVENESS = 47
    HITCOUNT = 48
    SUBSTITUTE_ABSORB = 49
    SUBSTITUTE_BREAK = 50
    HEAL = 51
    HEAL_BLOCKED = 52
    STAT_BOOST = 53
    STAT_SET = 54
    STAT_COPY = 55
    STAT_SWAP = 56
    STAT_INVERT = 57
    STAT_CLEAR = 58
    STAT_BATON_PASS = 59
    MOODY_TICK = 60
    STATUS_APPLY = 61
    STATUS_CURE = 62
    SLEEP_RESET = 63
    VOLATILE_APPLY = 64
    VOLATILE_END = 65
    PERISH_SONG_TICK = 66
    PERISH_SONG_FAINT = 67
    DESTINY_BOND_TRIGGER = 68
    LOCKED_MOVE_CONFUSION = 69
    INFATUATION_TRIGGER = 70
    WEATHER_START = 71
    WEATHER_TICK = 72
    WEATHER_END = 73
    WEATHER_SUPPRESSED = 74
    WEATHER_UNSUPPRESSED = 75
    TERRAIN_START = 76
    TERRAIN_TICK = 77
    TERRAIN_END = 78
    TERRAIN_SEED_ACTIVATE = 79
    SIDE_CONDITION_APPLY = 80
    SIDE_CONDITION_TICK = 81
    SIDE_CONDITION_END = 82
    SIDE_CONDITION_SWAP = 83
    FIELD_CONDITION_START = 84
    FIELD_CONDITION_TICK = 85
    FIELD_CONDITION_END = 86
    GROUNDED_APPLY = 87
    SWITCH_OUT = 88
    SWITCH_IN = 89
    DRAG = 90
    PIVOT = 91
    BATON_PASS_TRANSFER = 92
    HAZARD_APPLY = 93
    HAZARD_REMOVE = 94
    HAZARD_ABSORBED = 95
    HAZARD_BYPASSED = 96
    ABILITY_ACTIVATE = 97
    ABILITY_CHANGE = 98
    ABILITY_SUPPRESS = 99
    ABILITY_RESTORE = 100
    INTIMIDATE_ACTIVATE = 101
    ITEM_ACTIVATE = 102
    ITEM_CONSUME = 103
    ITEM_REMOVE = 104
    ITEM_TRANSFER = 105
    ITEM_GAIN = 106
    ITEM_SUPPRESSED = 107
    WHITE_HERB_ACTIVATE = 108
    MENTAL_HERB_ACTIVATE = 109
    GEM_ACTIVATE = 110
    QUICK_CLAW_ACTIVATE = 111
    CUSTAP_BERRY_ACTIVATE = 112
    CHOICE_LOCK = 113
    EJECT_PACK_TRIGGER = 114
    RED_CARD_TRIGGER = 115
    BERRY_CONFUSION = 116
    MEGA_EVOLVE = 117
    FORME_CHANGE_TEMP = 118
    FORME_CHANGE_REVERT = 119
    TYPE_CHANGE = 120
    ROOST_TYPE_RESTORE = 121
    TRANSFORM = 122
    FAINT = 123
    FORCED_SWITCH_REQUIRED = 124
    WIN = 125
    TIE = 126
    SPEED_TIE = 127
    PRESSURE_PP_DRAIN = 128
    SOUND_MOVE_BLOCKED = 129
    PERMANENT_EFFECT_APPLY = 130
    HINT = 131
    EXP_GAIN = 132
    LEVEL_UP = 133


def species_name(species) -> str:
    """Convert a species enum to a display string."""
    return species.name.title()


def move_name(move_id) -> str:
    """Convert a move enum to a display string."""
    return move_id.name.replace("_", " ").title()


# Module-level global — None = zero-cost no-op
logger: Optional['BattleLogger'] = None


def log(event: LogEvent, **kwargs) -> None:
    """Near-no-op when logger is None; forwards kwargs to handler when set."""
    if logger:
        logger.handle(event, **kwargs)


class BattleLogger:
    def handle(self, event: LogEvent, **kwargs) -> None:
        msg = self._format(event, **kwargs)
        if msg:
            print(msg)

    def _format(self, event: LogEvent, **kwargs) -> str:
        """Dispatch on event type and return a human-readable string, or ""."""
        if event == LogEvent.TURN_START:
            return f"=== Turn {kwargs['turn']} ==="

        if event == LogEvent.MOVE_USE:
            return f"{species_name(kwargs['user'])} used {move_name(kwargs['move'])}!"

        if event == LogEvent.DAMAGE:
            return (
                f"{species_name(kwargs['target'])} took {kwargs['amount']} damage! "
                f"(HP: {kwargs['hp_after']}/{kwargs.get('max_hp', '?')})"
            )

        if event == LogEvent.MOVE_MISS:
            return f"{species_name(kwargs['user'])}'s attack missed!"

        if event == LogEvent.FAINT:
            return f"{species_name(kwargs['pokemon'])} fainted!"

        if event == LogEvent.SWITCH_IN:
            label = 'Player' if kwargs.get('side') == 0 else 'Opponent'
            return f"{label} sent out {species_name(kwargs['pokemon'])}!"

        if event == LogEvent.STATUS_APPLY:
            return f"{species_name(kwargs['target'])} was inflicted with {kwargs['status']}!"

        if event == LogEvent.STAT_BOOST:
            direction = 'rose' if kwargs['stages'] > 0 else 'fell'
            return f"{species_name(kwargs['target'])}'s stat {direction}!"

        if event == LogEvent.WEATHER_START:
            return f"The weather became {kwargs['weather']}!"

        if event == LogEvent.WIN:
            return f"Side {kwargs['winner_side']} wins!"

        if event == LogEvent.TIE:
            return "It's a tie!"

        return ""


class CapturingLogger(BattleLogger):
    """Records all events without printing; provides query helpers for tests."""

    def __init__(self):
        self._events: list[tuple[LogEvent, dict]] = []

    def handle(self, event: LogEvent, **kwargs) -> None:
        self._events.append((event, kwargs))

    @property
    def events(self) -> list[tuple[LogEvent, dict]]:
        return self._events

    def of(self, event_type: LogEvent) -> list[dict]:
        return [kw for ev, kw in self._events if ev == event_type]

    def all_of(self, event_type: LogEvent, **filters) -> list[dict]:
        return [kw for kw in self.of(event_type) if all(kw.get(k) == v for k, v in filters.items())]

    def first(self, event_type: LogEvent, **filters) -> 'dict | None':
        results = self.all_of(event_type, **filters) if filters else self.of(event_type)
        return results[0] if results else None

    def fired(self, event_type: LogEvent, **filters) -> bool:
        return bool(self.all_of(event_type, **filters) if filters else self.of(event_type))

    def count(self, event_type: LogEvent, **filters) -> int:
        return len(self.all_of(event_type, **filters) if filters else self.of(event_type))

    @classmethod
    def from_cpp(cls, rich_log) -> 'CapturingLogger':
        """Rebuild a CapturingLogger from a native RichEventLog: each entry -> (LogEvent, kwargs).

        Reconstructs enums (Species/Move) and tag strings, dropping RICH_UNSET fields.
        Fails loud on an unmapped event or an unknown tag int (see _rich_kwargs).
        """
        inst = cls()
        for i in range(len(rich_log)):
            entry = rich_log[i]
            event = LogEvent(entry.event)
            inst._events.append((event, _rich_kwargs(event, entry)))
        return inst


# Must match engine/src/event_log.h RICH_UNSET.
_RICH_UNSET = -2147483648


def _present(value: int) -> bool:
    """A rich-entry int field is set iff it is not the RICH_UNSET sentinel."""
    return value != _RICH_UNSET


# Tag int -> canonical string maps (mirror event_log.h SourceTag/VolatileTag/CauseTag).
# The engine stores string kwargs as int tags to keep entries POD; this is the single
# place they are re-expanded. NONE (0) means "no such kwarg" -> dropped. E1b grows these.
_SOURCE_TAG_STRINGS = {1: "move", 2: "berry", 3: "cheek_pouch", 4: "ability",
                       5: "item", 6: "residual"}
_VOLATILE_TAG_STRINGS = {1: "confused", 2: "taunt", 3: "encore", 4: "leech_seeded"}
_CAUSE_TAG_STRINGS: dict = {}


def _source_tag_str(tag: int) -> 'str | None':
    if tag == 0:
        return None
    if tag not in _SOURCE_TAG_STRINGS:
        raise ValueError(f"from_cpp: unknown source_tag int {tag}")
    return _SOURCE_TAG_STRINGS[tag]


def _volatile_tag_str(tag: int) -> 'str | None':
    if tag == 0:
        return None
    if tag not in _VOLATILE_TAG_STRINGS:
        raise ValueError(f"from_cpp: unknown volatile_tag int {tag}")
    return _VOLATILE_TAG_STRINGS[tag]


def _cause_tag_str(tag: int) -> 'str | None':
    if tag == 0:
        return None
    if tag not in _CAUSE_TAG_STRINGS:
        raise ValueError(f"from_cpp: unknown cause_tag int {tag}")
    return _CAUSE_TAG_STRINGS[tag]


def _kw_charge(entry) -> dict:
    from liveplay.data.species import Species
    from liveplay.data.moves import Move
    return {"user": Species(entry.species), "move": Move(entry.aux0)}


def _kw_baton_pass(entry) -> dict:
    from liveplay.data.species import Species
    return {"side": entry.side, "pokemon": Species(entry.species)}


def _kw_stat_copy(entry) -> dict:
    from liveplay.data.species import Species
    return {"side": entry.side, "target": Species(entry.species),
            "source_species": Species(entry.aux0)}


# Dispatch: LogEvent -> function(entry) -> kwargs dict. E1b extends this cleanly.
# E1a covers only the five "silent" events.
_RICH_EVENT_KWARGS = {
    LogEvent.CHARGE_TURN: _kw_charge,
    LogEvent.SEMI_INVULNERABLE_ENTER: _kw_charge,
    LogEvent.SEMI_INVULNERABLE_EXIT: _kw_charge,
    LogEvent.BATON_PASS_TRANSFER: _kw_baton_pass,
    LogEvent.STAT_COPY: _kw_stat_copy,
}


def _rich_kwargs(event: LogEvent, entry) -> dict:
    """Reconstruct the kwargs dict for one rich entry; fail loud on an unmapped event."""
    handler = _RICH_EVENT_KWARGS.get(event)
    if handler is None:
        raise ValueError(f"from_cpp: no kwargs mapping for {event!r}")
    return handler(entry)


def capturing_from_cpp(rich_log) -> 'CapturingLogger':
    """Module-level alias for CapturingLogger.from_cpp."""
    return CapturingLogger.from_cpp(rich_log)


def format_state(state: 'BattleState') -> str:
    """Multi-line summary of BattleState: active Pokemon, HP, status, stat stages, weather, turn."""
    from liveplay.state.battle import WeatherEnum

    lines = [f"Turn {state.turn_number}"]

    labels = ["Side 0", "Side 1"]
    for side_idx, label in enumerate(labels):
        side = state.sides[side_idx]
        pokemon = side.team[side.active_indices[0]]
        name = species_name(pokemon.species)
        hp_bar = f"{pokemon.hp}/{pokemon.max_hp}"
        line = f"  {label}: {name} (HP: {hp_bar})"
        if pokemon.status.name != "NONE":
            line += f" [{pokemon.status.name.title()}]"
        stages = pokemon.stat_stages
        nonzero = [(i, v) for i, v in enumerate(stages) if v != 0]
        if nonzero:
            stat_names = ["Atk", "Def", "SpA", "SpD", "Spe", "Acc", "Eva"]
            stage_str = ", ".join(f"{stat_names[i]}{v:+d}" for i, v in nonzero)
            line += f" ({stage_str})"
        lines.append(line)

    if state.weather != WeatherEnum.NONE:
        lines.append(f"  Weather: {state.weather.name.title()}")

    return "\n".join(lines)
