# Tests for src/rng_trace.py — standalone recorder module.
# Covers lifecycle, occurrence counting, set_turn semantics, mark/rollback,
# seq monotonicity, and context metadata propagation.
import pytest

from liveplay.rng import RNGEvent
import liveplay.rng_trace as rng_trace
from liveplay.rng_trace import TraceRecorder, TraceRecord, start_recording, stop_recording, active, get_recorder


@pytest.fixture(autouse=True)
def reset_module_state():
    """Guarantee a clean module-level recorder state before and after each test."""
    # Stop any leftover recording from a prior test.
    if rng_trace.active():
        rng_trace.stop_recording()
    yield
    if rng_trace.active():
        rng_trace.stop_recording()


# ---------------------------------------------------------------------------
# 1. Lifecycle: start_recording twice, stop without start, active() transitions,
#    and stop returning accumulated records.
# ---------------------------------------------------------------------------

class TestLifecycle:
    def test_start_twice_raises(self):
        start_recording()
        with pytest.raises(RuntimeError):
            start_recording()

    def test_stop_without_start_raises(self):
        with pytest.raises(RuntimeError):
            stop_recording()

    def test_active_transitions(self):
        assert not active()
        rec = start_recording()
        assert active()
        stop_recording()
        assert not active()

    def test_stop_returns_accumulated_records(self):
        recorder = start_recording()
        recorder.set_turn(1)
        recorder.record(RNGEvent.CRIT, True)
        recorder.record(RNGEvent.ACCURACY, False)
        records = stop_recording()
        assert len(records) == 2
        assert isinstance(records[0], TraceRecord)
        assert not active()

    def test_get_recorder_none_when_inactive(self):
        assert get_recorder() is None

    def test_get_recorder_returns_active(self):
        rec = start_recording()
        assert get_recorder() is rec


# ---------------------------------------------------------------------------
# 2. record before set_turn raises RuntimeError.
# ---------------------------------------------------------------------------

class TestRecordBeforeTurn:
    def test_record_without_set_turn_raises(self):
        recorder = start_recording()
        with pytest.raises(RuntimeError):
            recorder.record(RNGEvent.CRIT, True)


# ---------------------------------------------------------------------------
# 3. Occurrence counting: same event 3x → 0,1,2; two events count independently.
# ---------------------------------------------------------------------------

class TestOccurrenceCounting:
    def test_same_event_three_times(self):
        recorder = start_recording()
        recorder.set_turn(1)
        for expected_occ in range(3):
            recorder.record(RNGEvent.DAMAGE_ROLL, 0.5)
        records = stop_recording()
        assert [r.occurrence for r in records] == [0, 1, 2]

    def test_two_events_count_independently(self):
        recorder = start_recording()
        recorder.set_turn(1)
        recorder.record(RNGEvent.CRIT, True)
        recorder.record(RNGEvent.ACCURACY, True)
        recorder.record(RNGEvent.CRIT, False)
        recorder.record(RNGEvent.ACCURACY, False)
        records = stop_recording()
        crit_occs = [r.occurrence for r in records if r.event == RNGEvent.CRIT]
        acc_occs = [r.occurrence for r in records if r.event == RNGEvent.ACCURACY]
        assert crit_occs == [0, 1]
        assert acc_occs == [0, 1]


# ---------------------------------------------------------------------------
# 4. set_turn semantics: n+1 resets counters; same n does not reset; n-1 raises.
# ---------------------------------------------------------------------------

class TestSetTurn:
    def test_next_turn_resets_occurrence_counters(self):
        recorder = start_recording()
        recorder.set_turn(1)
        recorder.record(RNGEvent.CRIT, True)
        recorder.record(RNGEvent.CRIT, True)
        recorder.set_turn(2)
        recorder.record(RNGEvent.CRIT, True)
        records = stop_recording()
        turn2_records = [r for r in records if r.turn == 2]
        assert turn2_records[0].occurrence == 0

    def test_same_turn_does_not_reset(self):
        recorder = start_recording()
        recorder.set_turn(5)
        recorder.record(RNGEvent.CRIT, True)
        # Idempotent: calling set_turn again with same value should NOT reset.
        recorder.set_turn(5)
        recorder.record(RNGEvent.CRIT, True)
        records = stop_recording()
        assert [r.occurrence for r in records] == [0, 1]

    def test_previous_turn_raises(self):
        recorder = start_recording()
        recorder.set_turn(5)
        with pytest.raises(RuntimeError):
            recorder.set_turn(3)


# ---------------------------------------------------------------------------
# 5. mark / rollback: records restored, occurrence index and seq reused.
# ---------------------------------------------------------------------------

class TestMarkRollback:
    def test_rollback_restores_records(self):
        recorder = start_recording()
        recorder.set_turn(1)
        recorder.record(RNGEvent.CRIT, True)
        mark = recorder.mark()
        recorder.record(RNGEvent.ACCURACY, False)
        recorder.record(RNGEvent.DAMAGE_ROLL, 0.7)
        assert len(recorder.records) == 3
        recorder.rollback(mark)
        assert len(recorder.records) == 1

    def test_rollback_reuses_occurrence_index_and_seq(self):
        recorder = start_recording()
        recorder.set_turn(1)
        recorder.record(RNGEvent.CRIT, True)       # seq=0, occ=0
        mark = recorder.mark()
        recorder.record(RNGEvent.ACCURACY, False)  # seq=1, occ=0 (first ACCURACY)
        seq_before = recorder.records[-1].seq
        recorder.rollback(mark)

        # Re-record the same event: must reuse the same occurrence index and seq.
        recorder.record(RNGEvent.ACCURACY, True)
        replayed = recorder.records[-1]
        assert replayed.occurrence == 0
        assert replayed.seq == seq_before

    def test_rollback_across_turn_boundary_raises(self):
        recorder = start_recording()
        recorder.set_turn(1)
        mark = recorder.mark()
        recorder.set_turn(2)
        with pytest.raises(RuntimeError):
            recorder.rollback(mark)

    def test_sequential_marks_older_discards_newer(self):
        recorder = start_recording()
        recorder.set_turn(1)
        recorder.record(RNGEvent.CRIT, True)   # record 0
        mark_a = recorder.mark()
        recorder.record(RNGEvent.ACCURACY, True)  # record 1
        mark_b = recorder.mark()
        recorder.record(RNGEvent.DAMAGE_ROLL, 0.5)  # record 2
        # Rollback to mark_a must discard records 1 and 2.
        recorder.rollback(mark_a)
        assert len(recorder.records) == 1
        assert recorder.records[0].event == RNGEvent.CRIT


# ---------------------------------------------------------------------------
# 6. seq strictly increases across records and across turn boundaries.
# ---------------------------------------------------------------------------

class TestSeqMonotonicity:
    def test_seq_strictly_increases_within_turn(self):
        recorder = start_recording()
        recorder.set_turn(1)
        for _ in range(5):
            recorder.record(RNGEvent.CRIT, True)
        seqs = [r.seq for r in recorder.records]
        assert seqs == sorted(set(seqs))  # strictly increasing

    def test_seq_does_not_reset_across_turns(self):
        recorder = start_recording()
        recorder.set_turn(1)
        recorder.record(RNGEvent.CRIT, True)
        last_seq_t1 = recorder.records[-1].seq
        recorder.set_turn(2)
        recorder.record(RNGEvent.CRIT, True)
        first_seq_t2 = recorder.records[-1].seq
        stop_recording()
        assert first_seq_t2 > last_seq_t1


# ---------------------------------------------------------------------------
# 7. Metadata: records reflect latest set_context; None clears.
# ---------------------------------------------------------------------------

class TestContextMetadata:
    def test_records_reflect_set_context(self):
        recorder = start_recording()
        recorder.set_context(phase="move", side=0, slot=1)
        recorder.set_turn(1)
        recorder.record(RNGEvent.CRIT, True)
        rec = recorder.records[0]
        assert rec.phase == "move"
        assert rec.side == 0
        assert rec.slot == 1

    def test_set_context_none_clears(self):
        recorder = start_recording()
        recorder.set_context(phase="move", side=0, slot=1)
        recorder.set_context(phase=None, side=None, slot=None)
        recorder.set_turn(1)
        recorder.record(RNGEvent.CRIT, True)
        rec = recorder.records[0]
        assert rec.phase is None
        assert rec.side is None
        assert rec.slot is None

    def test_later_context_does_not_update_prior_records(self):
        recorder = start_recording()
        recorder.set_context(phase="phase_a", side=0, slot=0)
        recorder.set_turn(1)
        recorder.record(RNGEvent.CRIT, True)
        recorder.set_context(phase="phase_b", side=1, slot=2)
        recorder.record(RNGEvent.ACCURACY, True)
        first = recorder.records[0]
        second = recorder.records[1]
        assert first.phase == "phase_a"
        assert second.phase == "phase_b"
