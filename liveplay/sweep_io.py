# Lossless JSON codec for sweep inputs/outputs. Handles all types in the BattleState/Candidate graph.
# Format: tagged dicts for dataclasses, enums, tuples, and frozensets; primitives pass through.
import dataclasses
import json
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Enum and dataclass registries
# ---------------------------------------------------------------------------

def _build_enum_registry() -> dict:
    """Collect every enum class that can appear in the sweep graph."""
    from liveplay.data.species import Species
    from liveplay.data.moves import Move
    from liveplay.data.status import Status
    from liveplay.data.natures import Nature, Stat
    from liveplay.data.abilities import Ability
    from liveplay.data.items import Item
    from liveplay.data.types import Type
    from liveplay.state.battle import WeatherEnum, TerrainEnum, PseudoWeather
    from liveplay.state.side import FormatEnum, SideCondition
    from liveplay.state.pokemon import GenderEnum, VolatileEffect, Volatile
    from liveplay.actions import ActionKind
    from liveplay.rng import RNGEvent, LuckGroup
    return {
        cls.__name__: cls for cls in [
            Species, Move, Status, Nature, Stat, Ability, Item, Type,
            WeatherEnum, TerrainEnum, PseudoWeather,
            FormatEnum, SideCondition,
            GenderEnum, VolatileEffect, Volatile,
            ActionKind,
            RNGEvent, LuckGroup,
        ]
    }


def _build_dataclass_registry() -> dict:
    """Collect every dataclass that can appear in the sweep graph."""
    from liveplay.candidate import Candidate, PartialCandidate
    from liveplay.state.battle import BattleState
    from liveplay.state.side import SideState
    from liveplay.state.pokemon import PokemonState
    from liveplay.battle_types import MatchResult, ActionGroup, HpReading, Constraints
    from liveplay.hp_delta import HpDeltaSeq
    from liveplay.actions import Action
    return {
        cls.__name__: cls for cls in [
            Candidate, PartialCandidate,
            BattleState, SideState, PokemonState,
            MatchResult, ActionGroup, HpReading, Constraints,
            HpDeltaSeq,
            Action,
        ]
    }


# Lazy singletons — built once per process.
_ENUM_REGISTRY: dict | None = None
_DATACLASS_REGISTRY: dict | None = None


def _enum_registry() -> dict:
    global _ENUM_REGISTRY
    if _ENUM_REGISTRY is None:
        _ENUM_REGISTRY = _build_enum_registry()
    return _ENUM_REGISTRY


def _dataclass_registry() -> dict:
    global _DATACLASS_REGISTRY
    if _DATACLASS_REGISTRY is None:
        _DATACLASS_REGISTRY = _build_dataclass_registry()
    return _DATACLASS_REGISTRY


# ---------------------------------------------------------------------------
# Core codec
# ---------------------------------------------------------------------------

def to_jsonable(obj: Any) -> Any:
    """Recursively encode obj to a JSON-serialisable structure. Raises TypeError for unknown types."""
    import enum

    # Enums must be checked BEFORE int/bool because IntEnum IS an int subclass.
    if isinstance(obj, enum.Enum):
        return {"__enum__": type(obj).__name__, "name": obj.name, "value": obj.value}

    # Primitives — pass through
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    # Dataclasses
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        fields = {}
        for f in dataclasses.fields(obj):
            # Skip compare=False, hash=False parent_candidate to avoid circular refs
            if not f.compare and f.name == "parent_candidate":
                fields[f.name] = None
                continue
            fields[f.name] = to_jsonable(getattr(obj, f.name))
        return {"__type__": type(obj).__name__, "fields": fields}

    # tuple — tagged so it round-trips as tuple, not list
    if isinstance(obj, tuple):
        return {"__tuple__": [to_jsonable(item) for item in obj]}

    # frozenset — tagged
    if isinstance(obj, frozenset):
        return {"__frozenset__": [to_jsonable(item) for item in sorted(obj, key=repr)]}

    # list
    if isinstance(obj, list):
        return [to_jsonable(item) for item in obj]

    # dict — encode as list of [key, value] pairs to support non-string keys (e.g. int keys
    # in unknown_actions). Uses a tag to distinguish from plain lists.
    if isinstance(obj, dict):
        return {
            "__dict__": [[to_jsonable(k), to_jsonable(v)] for k, v in obj.items()]
        }

    raise TypeError(
        f"to_jsonable: unsupported type {type(obj).__name__!r} — value: {obj!r}"
    )


def from_jsonable(obj: Any) -> Any:
    """Recursively decode a structure produced by to_jsonable."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    if isinstance(obj, list):
        return [from_jsonable(item) for item in obj]

    if isinstance(obj, dict):
        # Enum
        if "__enum__" in obj:
            reg = _enum_registry()
            cls_name = obj["__enum__"]
            if cls_name not in reg:
                raise ValueError(f"from_jsonable: unknown enum class {cls_name!r}")
            cls = reg[cls_name]
            # Reconstruct by value (handles IntFlag composites correctly)
            return cls(obj["value"])

        # Dataclass
        if "__type__" in obj:
            reg = _dataclass_registry()
            cls_name = obj["__type__"]
            if cls_name not in reg:
                raise ValueError(f"from_jsonable: unknown dataclass {cls_name!r}")
            cls = reg[cls_name]
            raw_fields = obj["fields"]
            decoded = {k: from_jsonable(v) for k, v in raw_fields.items()}
            return _reconstruct_dataclass(cls, decoded)

        # Tuple
        if "__tuple__" in obj:
            return tuple(from_jsonable(item) for item in obj["__tuple__"])

        # Frozenset
        if "__frozenset__" in obj:
            return frozenset(from_jsonable(item) for item in obj["__frozenset__"])

        # Tagged dict (supports non-string keys)
        if "__dict__" in obj:
            return {from_jsonable(k): from_jsonable(v) for k, v in obj["__dict__"]}

        # Plain dict (string keys only — e.g. the top-level file payload)
        return {k: from_jsonable(v) for k, v in obj.items()}

    raise ValueError(f"from_jsonable: unexpected object type {type(obj).__name__!r}")


def _reconstruct_dataclass(cls, fields: dict):
    """Reconstruct a dataclass from decoded fields, bypassing __post_init__ for stateful classes."""
    # PokemonState has a heavy __post_init__ that recomputes stats from scratch.
    # We must bypass it and restore all fields as-is so the round-trip is exact.
    from liveplay.state.pokemon import PokemonState
    from liveplay.state.battle import BattleState
    from liveplay.state.side import SideState

    if cls in (PokemonState, BattleState, SideState):
        obj = object.__new__(cls)
        obj.__dict__.update(fields)
        return obj

    # For frozen dataclasses, use object.__new__ + __dict__/object.__setattr__
    if dataclasses.fields(cls) and getattr(cls, "__dataclass_params__", None) is not None:
        params = cls.__dataclass_params__
        if params.frozen:
            obj = object.__new__(cls)
            for k, v in fields.items():
                object.__setattr__(obj, k, v)
            return obj

    # Default: call constructor. Works for simple dataclasses without side effects.
    # Pass only fields the constructor accepts (filter out compare=False fields that
    # were stored as None sentinel, like parent_candidate).
    try:
        return cls(**fields)
    except TypeError:
        # Fallback: reconstruct via object.__new__ for complex cases
        obj = object.__new__(cls)
        obj.__dict__.update(fields)
        return obj


# ---------------------------------------------------------------------------
# File-level dump/load helpers
# ---------------------------------------------------------------------------

def _encode_sweep_input(messages, hp_deltas, initial_candidates, action_groups) -> dict:
    """Encode all four sweep-input components into a single JSON-serialisable dict."""
    return {
        "messages": to_jsonable(messages),
        "hp_deltas": to_jsonable(hp_deltas),
        "initial_candidates": to_jsonable(initial_candidates),
        "action_groups": to_jsonable(action_groups),
    }


def dump_sweep_input(messages, hp_deltas, initial_candidates, action_groups, path) -> None:
    """Write sweep inputs to a JSON file at path."""
    path = Path(path)
    payload = _encode_sweep_input(messages, hp_deltas, initial_candidates, action_groups)
    path.write_text(json.dumps(payload, indent=2))


def load_sweep_input(path) -> tuple:
    """Load sweep inputs from a JSON file. Returns (messages, hp_deltas, initial_candidates, action_groups)."""
    path = Path(path)
    payload = json.loads(path.read_text())
    messages = from_jsonable(payload["messages"])
    hp_deltas = from_jsonable(payload["hp_deltas"])
    initial_candidates = from_jsonable(payload["initial_candidates"])
    action_groups = from_jsonable(payload["action_groups"])
    return messages, hp_deltas, initial_candidates, action_groups


def dump_candidates(candidates, path) -> None:
    """Write a list of Candidates to a JSON file."""
    path = Path(path)
    path.write_text(json.dumps(to_jsonable(candidates), indent=2))


def load_candidates(path) -> list:
    """Load a list of Candidates from a JSON file."""
    path = Path(path)
    return from_jsonable(json.loads(path.read_text()))
