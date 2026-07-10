"""E1a: CapturingLogger.from_cpp rebuilds (LogEvent, kwargs) tuples from a native
RichEventLog for the five silent events, reconstructing Species/Move enums.
Entries are built through the native emit helpers (the single source of truth), so
the field layout is never duplicated in Python."""
import pytest

nuzlocke_engine_cpp = pytest.importorskip("nuzlocke_engine_cpp")

from liveplay.logger import CapturingLogger, LogEvent, capturing_from_cpp
from liveplay.data.species import Species
from liveplay.data.moves import Move


def _build_log():
    """Emit the five silent events into a fresh native RichEventLog and return it."""
    cpp = nuzlocke_engine_cpp
    log = cpp.RichEventLog()
    cpp.set_rich_event_log(log)
    try:
        cpp.rich_log_charge_turn(1, Species.PIKACHU.value, Move.FLY.value)
        cpp.rich_log_semi_invuln_enter(1, Species.PIKACHU.value, Move.FLY.value)
        cpp.rich_log_semi_invuln_exit(2, Species.PIKACHU.value, Move.FLY.value)
        cpp.rich_log_baton_pass_transfer(3, 1, Species.CHARIZARD.value)
        cpp.rich_log_stat_copy(4, 0, Species.BLASTOISE.value, Species.VENUSAUR.value)
    finally:
        cpp.set_rich_event_log(None)
    return log


def test_from_cpp_reconstructs_five_silent_events():
    log = _build_log()
    cap = CapturingLogger.from_cpp(log)
    events = cap.events
    assert len(events) == 5

    (ev0, kw0) = events[0]
    assert ev0 == LogEvent.CHARGE_TURN
    assert kw0 == {"user": Species.PIKACHU, "move": Move.FLY}
    assert isinstance(kw0["user"], Species) and isinstance(kw0["move"], Move)

    (ev1, kw1) = events[1]
    assert ev1 == LogEvent.SEMI_INVULNERABLE_ENTER
    assert kw1 == {"user": Species.PIKACHU, "move": Move.FLY}

    (ev2, kw2) = events[2]
    assert ev2 == LogEvent.SEMI_INVULNERABLE_EXIT
    assert kw2 == {"user": Species.PIKACHU, "move": Move.FLY}

    (ev3, kw3) = events[3]
    assert ev3 == LogEvent.BATON_PASS_TRANSFER
    assert kw3 == {"side": 1, "pokemon": Species.CHARIZARD}
    assert isinstance(kw3["pokemon"], Species)

    (ev4, kw4) = events[4]
    assert ev4 == LogEvent.STAT_COPY
    assert kw4 == {"side": 0, "target": Species.BLASTOISE,
                   "source_species": Species.VENUSAUR}


def test_capturing_from_cpp_alias_matches_classmethod():
    log = _build_log()
    a = CapturingLogger.from_cpp(log).events
    b = capturing_from_cpp(log).events
    assert a == b


def test_from_cpp_query_helpers_work():
    cap = CapturingLogger.from_cpp(_build_log())
    assert cap.fired(LogEvent.CHARGE_TURN)
    assert cap.count(LogEvent.SEMI_INVULNERABLE_ENTER) == 1
    first = cap.first(LogEvent.STAT_COPY)
    assert first["target"] == Species.BLASTOISE


def test_unmapped_event_fails_loud():
    """An entry whose LogEvent has no kwargs mapping must raise (fail loud)."""
    cpp = nuzlocke_engine_cpp
    log = cpp.RichEventLog()
    cpp.set_rich_event_log(log)
    try:
        # DAMAGE (45) is not in the E1a dispatch table.
        # Reuse charge_turn plumbing is impossible, so emit a mapped event and then
        # assert an unmapped LogEvent raises via the internal helper.
        cpp.rich_log_charge_turn(1, Species.PIKACHU.value, Move.FLY.value)
    finally:
        cpp.set_rich_event_log(None)

    from liveplay.logger import _rich_kwargs
    entry = log[0]
    with pytest.raises(ValueError):
        _rich_kwargs(LogEvent.DAMAGE, entry)


def test_unknown_tag_fails_loud():
    """Tag helpers raise on an unknown tag int; NONE(0) maps to None (dropped)."""
    from liveplay.logger import _source_tag_str, _volatile_tag_str, _cause_tag_str
    assert _source_tag_str(0) is None
    assert _source_tag_str(1) == "move"
    with pytest.raises(ValueError):
        _source_tag_str(999)
    assert _volatile_tag_str(0) is None
    with pytest.raises(ValueError):
        _volatile_tag_str(999)
    assert _cause_tag_str(0) is None
    with pytest.raises(ValueError):
        _cause_tag_str(999)
