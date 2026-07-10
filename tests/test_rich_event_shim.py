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
        # Emit any mapped event, then assert an unmapped LogEvent raises via the
        # internal helper. TURN_START (1) is not in the rich dispatch table.
        cpp.rich_log_charge_turn(1, Species.PIKACHU.value, Move.FLY.value)
    finally:
        cpp.set_rich_event_log(None)

    from liveplay.logger import _rich_kwargs
    entry = log[0]
    with pytest.raises(ValueError):
        _rich_kwargs(LogEvent.TURN_START, entry)


# --- E1b consumed-event round-trip coverage. Emit each E1b event through the bound
# native helpers (single source of truth), then assert from_cpp rebuilds the kwargs
# with Species/Move/Status enums and tag strings. ---

# SourceTag ints mirror event_log.h: NONE=0, MOVE=1, BERRY=2, ...
_TAG_MOVE = 1
_TAG_BERRY = 2
# VolatileTag: NONE=0, CONFUSED=1, ...
_VOL_CONFUSED = 1


def _build_e1b_log():
    cpp = nuzlocke_engine_cpp
    from liveplay.data.status import Status
    log = cpp.RichEventLog()
    cpp.set_rich_event_log(log)
    try:
        cpp.rich_log_move_use(1, Species.PIKACHU.value, Move.THUNDERBOLT.value, 0)
        cpp.rich_log_presence(1, LogEvent.CANT_PARALYSIS.value, Species.PIKACHU.value)
        cpp.rich_log_hit_self_confusion(1, Species.PIKACHU.value, 12, 0)
        cpp.rich_log_status_apply(1, Species.CHARIZARD.value, Status.PARALYSIS.value, 1, _TAG_MOVE)
        cpp.rich_log_stat_boost(1, Species.CHARIZARD.value, 1, -1, 1, _TAG_MOVE)
        cpp.rich_log_volatile_apply(1, Species.CHARIZARD.value, _VOL_CONFUSED, 1, 0)
        cpp.rich_log_hitcount(1, Species.PIKACHU.value, 0)
        cpp.rich_log_damage(1, Species.CHARIZARD.value, 40, 60, 0, 0, 1, 0)
        cpp.rich_log_heal(1, Species.PIKACHU.value, 20, 80, 0, _TAG_BERRY)
        cpp.rich_log_faint(1, Species.CHARIZARD.value, 1)
        cpp.rich_log_exp_gain(1, Species.PIKACHU.value, 340)
        cpp.rich_log_level_up(1, Species.PIKACHU.value, 22)
    finally:
        cpp.set_rich_event_log(None)
    return log


def test_e1b_events_round_trip():
    from liveplay.data.status import Status
    cap = CapturingLogger.from_cpp(_build_e1b_log())
    ev = dict(cap.events)  # LogEvent -> kwargs (each fired once here)

    assert ev[LogEvent.MOVE_USE] == {
        "user": Species.PIKACHU, "move": Move.THUNDERBOLT, "side": 0}
    assert ev[LogEvent.CANT_PARALYSIS] == {"pokemon": Species.PIKACHU}
    assert ev[LogEvent.HIT_SELF_CONFUSION] == {
        "pokemon": Species.PIKACHU, "damage": 12, "side": 0}
    assert ev[LogEvent.STATUS_APPLY] == {
        "target": Species.CHARIZARD, "status": Status.PARALYSIS, "side": 1, "source": "move"}
    assert ev[LogEvent.STAT_BOOST] == {
        "target": Species.CHARIZARD, "stat": 1, "stages": -1, "side": 1, "source": "move"}
    assert ev[LogEvent.VOLATILE_APPLY] == {
        "target": Species.CHARIZARD, "side": 1, "volatile": "confused"}
    assert ev[LogEvent.HITCOUNT] == {"user": Species.PIKACHU, "side": 0}
    assert ev[LogEvent.DAMAGE] == {
        "target": Species.CHARIZARD, "amount": 40, "hp_after": 60,
        "attacker_side": 0, "attacker_slot": 0, "defender_side": 1}
    assert ev[LogEvent.HEAL] == {
        "target": Species.PIKACHU, "amount": 20, "side": 0, "source": "berry", "hp_after": 80}
    assert ev[LogEvent.FAINT] == {"pokemon": Species.CHARIZARD, "side": 1}
    assert ev[LogEvent.EXP_GAIN] == {"pokemon": Species.PIKACHU, "amount": 340}
    assert ev[LogEvent.LEVEL_UP] == {"pokemon": Species.PIKACHU, "new_level": 22}


def test_e1b_enum_types_reconstructed():
    """Species/Move/Status must come back as enum objects, not raw ints (the reconciler
    compares with == against enums)."""
    cap = CapturingLogger.from_cpp(_build_e1b_log())
    move_use = cap.first(LogEvent.MOVE_USE)
    assert isinstance(move_use["user"], Species)
    assert isinstance(move_use["move"], Move)
    status = cap.first(LogEvent.STATUS_APPLY)
    from liveplay.data.status import Status
    assert isinstance(status["status"], Status)


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
