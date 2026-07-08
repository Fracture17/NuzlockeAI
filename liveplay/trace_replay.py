# JSONL golden-trace to C++ forced_trace converter. Reads a golden trace produced by
# liveplay.golden_trace.record_game and emits the dict consumed by cpp.GameDriver's forced_trace key.
import json

from liveplay.golden_trace import read_trace
from liveplay.rng import RNGEvent
from liveplay.sweep_io import from_jsonable, to_jsonable
from liveplay.cpp_driver import action_payload


# Map RNGEvent members that appear as answer records to their int values.
_ANSWER_EVENT_INTS: dict = {e: e.value for e in RNGEvent}

# Events that may never appear as answer records in a random-mode trace.
_FORBIDDEN_ANSWER_EVENTS = frozenset({RNGEvent.SPEED_TIE})


def convert_trace(path) -> dict:
    """Convert a golden-trace JSONL to a C++ forced_trace payload.

    Returns {
        "initial_state": BattleState,
        "forced_trace": {"rng": [...], "answers": [...]},
        "end_fingerprint": str,
        "winner": int|None,
        "turn_count": int,
    }.
    Raises ValueError on SPEED_TIE or unrecognized event names in answer records.
    """
    records = read_trace(path)
    if not records:
        raise ValueError("convert_trace: empty trace file")

    header = records[0]
    if header.get("t") != "header":
        raise ValueError("convert_trace: first record is not a header")

    end = records[-1]
    if end.get("t") != "end":
        raise ValueError("convert_trace: last record is not an end record")

    initial_state = from_jsonable(header["initial_state"])

    rng_entries = []
    answer_entries = []

    for rec in records[1:-1]:
        t = rec.get("t")
        if t == "rng":
            rng_entries.append(_convert_rng_record(rec))
        elif t == "answer":
            answer_entries.extend(_convert_answer_record(rec))
        # snapshot records are ignored

    return {
        "initial_state": initial_state,
        "forced_trace": {"rng": rng_entries, "answers": answer_entries},
        "end_fingerprint": end["fingerprint"],
        "winner": end["winner"],
        "turn_count": end["turn_count"],
    }


def _convert_rng_record(rec: dict) -> dict:
    """Convert one 'rng' record to a forced_trace rng entry."""
    event_raw = rec["event"]
    event_enum = from_jsonable(event_raw)
    event_int = event_enum.value

    outcome_raw = rec["outcome"]
    outcome = from_jsonable(outcome_raw)

    # Keep native JSON typing: bool → bool, int → int, float → float.
    # Enum-valued outcomes (e.g. RANDOM_TARGET slot) become plain int.
    if isinstance(outcome, bool):
        pass  # keep as-is
    elif hasattr(outcome, "value"):
        outcome = int(outcome.value)
    elif isinstance(outcome, int):
        pass
    elif isinstance(outcome, float):
        # Guard against int coercion of float zero.
        outcome = float(outcome)
    # else: keep as-is (strings etc. would be unusual but are passed through)

    return {
        "turn": rec["turn"],
        "event": event_int,
        "occurrence": rec["occurrence"],
        "outcome": outcome,
    }


def _convert_answer_record(rec: dict) -> list:
    """Convert one 'answer' record to zero or more forced_trace answer entries.

    ACTION_SELECT emits one entry with actions_p0/actions_p1.
    FORCED_SWITCH and POST_FAINT_SWITCH each emit one entry per switching side.
    RNGEvent-tagged answers emit one entry with i0/i1.
    SPEED_TIE raises ValueError.
    """
    turn = rec["turn"]
    event_raw = rec["event"]

    # Decode the event: plain string (ACTION_SELECT/FORCED_SWITCH/POST_FAINT_SWITCH)
    # or tagged RNGEvent enum.
    if isinstance(event_raw, str):
        event_name = event_raw
        event_enum = None
        event_int = None
    else:
        event_enum = from_jsonable(event_raw)
        event_name = event_enum.name
        event_int = event_enum.value

    if event_name == "ACTION_SELECT":
        return [_make_action_select(turn, rec["answer"])]

    if event_name in ("FORCED_SWITCH", "POST_FAINT_SWITCH"):
        ev_int = RNGEvent.FORCED_SWITCH.value if event_name == "FORCED_SWITCH" \
            else RNGEvent.POST_FAINT_SWITCH.value
        return _split_switch_answer(turn, ev_int, rec["answer"])

    # RNGEvent-tagged Cat-A answers
    if event_enum is None:
        raise ValueError(f"convert_trace: unrecognized answer event string {event_name!r}")

    if event_enum in _FORBIDDEN_ANSWER_EVENTS:
        raise ValueError(
            f"convert_trace: SPEED_TIE must never appear in random-mode trace answers"
        )

    return [_make_rng_answer(turn, event_int, event_enum, rec["answer"])]


def _make_action_select(turn: int, answer_raw) -> dict:
    """Build an ACTION_SELECT answer entry from the normalized [side0, side1] answer."""
    answer = from_jsonable(answer_raw)
    # answer is [side0_actions_or_None, side1_actions_or_None]
    side0, side1 = answer[0], answer[1]

    actions_p0 = _encode_actions(side0)
    actions_p1 = _encode_actions(side1)

    return {
        "turn": turn,
        "event": RNGEvent.ACTION_SELECT.value,
        "side": -1,
        "i0": -1,
        "i1": -1,
        "actions_p0": actions_p0,
        "actions_p1": actions_p1,
    }


def _encode_actions(actions_or_none) -> "list | None":
    """Serialize a list of Python Action objects to C++ action dicts, or return None."""
    if actions_or_none is None:
        return None
    return [action_payload(a) for a in actions_or_none]


def _split_switch_answer(turn: int, ev_int: int, answer_raw) -> list:
    """Convert a (slot_0, slot_1) FORCED_SWITCH / POST_FAINT_SWITCH answer to per-side entries.

    The Python answer is a 2-element list [slot_0_or_None, slot_1_or_None] where each
    element is an int (team index) or None. C++ resolves side 0 before side 1, so we
    emit entries in side order matching that resolution.
    """
    answer = from_jsonable(answer_raw)
    slot_0, slot_1 = answer[0], answer[1]

    entries = []
    for si, slot in [(0, slot_0), (1, slot_1)]:
        if slot is None:
            continue
        # slot may be an int or an Action-like object with switch_to_slot attribute
        team_idx = slot.switch_to_slot if hasattr(slot, "switch_to_slot") else int(slot)
        entries.append({
            "turn": turn,
            "event": ev_int,
            "side": si,
            "i0": team_idx,
            "i1": -1,
            "actions_p0": None,
            "actions_p1": None,
        })
    return entries


def _make_rng_answer(turn: int, event_int: int, event_enum: RNGEvent, answer_raw) -> dict:
    """Convert a Cat-A RNGEvent answer to a forced_trace answer entry."""
    answer = from_jsonable(answer_raw)

    # Decode i0/i1 per the event encoding table in the task description.
    if event_enum == RNGEvent.MOODY_STATS:
        # answer is a (boost_idx, drop_idx) tuple
        boost_idx, drop_idx = answer[0], answer[1]
        i0 = int(boost_idx) if not hasattr(boost_idx, "value") else int(boost_idx.value)
        i1 = int(drop_idx) if not hasattr(drop_idx, "value") else int(drop_idx.value)
    else:
        # All other single-value events: i0 is the answer integer (or enum int value)
        if hasattr(answer, "value"):
            i0 = int(answer.value)
        else:
            i0 = int(answer)
        i1 = -1

    return {
        "turn": turn,
        "event": event_int,
        "side": -1,
        "i0": i0,
        "i1": i1,
        "actions_p0": None,
        "actions_p1": None,
    }
