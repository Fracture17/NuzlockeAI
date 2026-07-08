# Standalone RNG-outcome recorder. Records every resolved RNG outcome keyed by
# (turn, event, occurrence_idx) for C++ replay with forced outcomes.
# Contract: one game per process; recording games must run with random_mode=True
# luck profiles on both sides; parallel recording requires one process per game.
# rng.py imports this module, so this file must NOT import from liveplay.rng or any
# other src module (would create a circular import).
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TraceRecord:
    """One resolved RNG outcome. event is the RNGEvent enum member (typed as Any to avoid import cycle)."""
    turn: int
    seq: int
    event: Any       # RNGEvent member; Any to avoid circular import with liveplay.rng
    occurrence: int  # 0-based count of this event within the current turn
    outcome: object
    phase: str | None
    side: int | None
    slot: int | None


class _Checkpoint:
    """Opaque mark returned by TraceRecorder.mark()."""
    __slots__ = ("length", "counters", "seq", "turn")

    def __init__(self, length: int, counters: dict, seq: int, turn: int | None) -> None:
        self.length = length
        self.counters = counters
        self.seq = seq
        self.turn = turn


class TraceRecorder:
    """Append-only (except rollback) recorder for resolved RNG outcomes within one game."""

    def __init__(self) -> None:
        self._turn: int | None = None
        self._seq: int = 0
        self._counters: dict[Any, int] = {}  # event → next occurrence index within this turn
        self._context_phase: str | None = None
        self._context_side: int | None = None
        self._context_slot: int | None = None
        self.records: list[TraceRecord] = []

    def set_turn(self, n: int) -> None:
        """Advance to turn n. Same n is idempotent; n < current turn raises RuntimeError."""
        if self._turn is not None:
            if n < self._turn:
                raise RuntimeError(
                    f"set_turn: cannot go backwards (current={self._turn}, requested={n})"
                )
            if n == self._turn:
                return  # idempotent
        # n > current (or first call): new turn — reset per-event occurrence counters.
        self._turn = n
        self._counters = {}

    def set_context(self, phase: str | None = None, side: int | None = None,
                    slot: int | None = None) -> None:
        """Store debug metadata that will be attached to subsequent records."""
        self._context_phase = phase
        self._context_side = side
        self._context_slot = slot

    def record(self, event: Any, outcome: object) -> None:
        """Append a TraceRecord for the resolved outcome. Raises if no turn has been set."""
        if self._turn is None:
            raise RuntimeError("record: set_turn must be called before record")
        occurrence = self._counters.get(event, 0)
        self._counters[event] = occurrence + 1
        self.records.append(TraceRecord(
            turn=self._turn,
            seq=self._seq,
            event=event,
            occurrence=occurrence,
            outcome=outcome,
            phase=self._context_phase,
            side=self._context_side,
            slot=self._context_slot,
        ))
        self._seq += 1

    def mark(self) -> _Checkpoint:
        """Return an opaque checkpoint capturing current records length, counters, and seq."""
        return _Checkpoint(
            length=len(self.records),
            counters=dict(self._counters),
            seq=self._seq,
            turn=self._turn,
        )

    def rollback(self, mark: _Checkpoint) -> None:
        """Truncate records to the mark and restore counters/seq.

        A subsequent identical draw after rollback reuses the same occurrence index and seq,
        so the rolled-back records are indistinguishable from an original recording.
        Raises RuntimeError if the turn has advanced since the mark (snapshots never span turns).
        """
        if mark.turn != self._turn:
            raise RuntimeError(
                f"rollback: turn changed since mark (mark turn={mark.turn}, current={self._turn})"
            )
        del self.records[mark.length:]
        self._counters = dict(mark.counters)
        self._seq = mark.seq


# ---------------------------------------------------------------------------
# Module-level singleton and lifecycle helpers
# ---------------------------------------------------------------------------

_recorder: TraceRecorder | None = None


def start_recording() -> TraceRecorder:
    """Create and activate the module-level recorder. Raises RuntimeError if already active."""
    global _recorder
    if _recorder is not None:
        raise RuntimeError("start_recording: a recording is already active")
    _recorder = TraceRecorder()
    return _recorder


def stop_recording() -> list[TraceRecord]:
    """Deactivate the recorder and return its records. Raises RuntimeError if not active."""
    global _recorder
    if _recorder is None:
        raise RuntimeError("stop_recording: no active recording")
    records = list(_recorder.records)
    _recorder = None
    return records


def active() -> bool:
    """Return True if a recording is currently in progress."""
    return _recorder is not None


def get_recorder() -> TraceRecorder | None:
    """Return the active TraceRecorder, or None if no recording is in progress."""
    return _recorder
