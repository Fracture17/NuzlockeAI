# Tests for CandidateTracker: candidate pool management across turn generations.
import pytest
from liveplay.candidate import Candidate
from liveplay.candidate_tracker import CandidateTracker


class _FakeState:
    def __init__(self, h):
        self._h = h

    def __hash__(self):
        return self._h

    def __eq__(self, other):
        return self._h == other._h


def make_candidate(h=0):
    return Candidate(state=_FakeState(h))


def test_init_stores_candidates():
    c1, c2 = make_candidate(1), make_candidate(2)
    tracker = CandidateTracker([c1, c2])
    assert tracker.candidates == [c1, c2]


def test_len_matches_count():
    tracker = CandidateTracker([make_candidate(1), make_candidate(2)])
    assert len(tracker) == 2


def test_is_resolved_false_with_two():
    tracker = CandidateTracker([make_candidate(1), make_candidate(2)])
    assert tracker.is_resolved is False


def test_is_resolved_true_with_one():
    tracker = CandidateTracker([make_candidate(1)])
    assert tracker.is_resolved is True


def test_is_resolved_false_with_zero():
    tracker = CandidateTracker([])
    assert tracker.is_resolved is False


def test_update_replaces_candidates():
    c1, c2, c3 = make_candidate(1), make_candidate(2), make_candidate(3)
    tracker = CandidateTracker([c1, c2])
    tracker.update([c3])
    assert tracker.candidates == [c3]


def test_update_does_not_alias():
    c1, c2, c3 = make_candidate(1), make_candidate(2), make_candidate(3)
    tracker = CandidateTracker([c1, c2])
    new_list = [c3]
    tracker.update(new_list)
    new_list.append(make_candidate(4))
    assert len(tracker) == 1


def test_deduplicate_removes_equal_states():
    # Two candidates whose states hash the same AND compare equal — only one survives.
    c1 = make_candidate(42)
    c2 = make_candidate(42)
    tracker = CandidateTracker([c1, c2])
    tracker.deduplicate()
    assert len(tracker) == 1
    assert tracker.candidates[0] is c1


class _CollidingState:
    """Stub state: all instances share one hash but compare unequal (identity only)."""
    def __hash__(self):
        return 42

    def __eq__(self, other):
        return self is other


def test_deduplicate_hash_collision_keeps_distinct_states():
    # Two states with identical hashes but unequal values must both be kept.
    c1 = Candidate(state=_CollidingState())
    c2 = Candidate(state=_CollidingState())
    tracker = CandidateTracker([c1, c2])
    tracker.deduplicate()
    assert len(tracker) == 2


def test_deduplicate_keeps_unique():
    c1, c2 = make_candidate(1), make_candidate(2)
    tracker = CandidateTracker([c1, c2])
    tracker.deduplicate()
    assert len(tracker) == 2


def test_prune_empty_removes_childless_parent():
    parent = make_candidate(1)
    tracker = CandidateTracker([parent])
    pruned = tracker.prune_empty([])
    assert tracker.candidates == []
    assert pruned == [parent]


def test_prune_empty_keeps_parent_with_children():
    parent = make_candidate(1)
    child = Candidate(state=_FakeState(2), parent_candidate=parent)
    tracker = CandidateTracker([parent])
    pruned = tracker.prune_empty([child])
    assert tracker.candidates == [parent]
    assert pruned == []


def test_prune_empty_mixed():
    parent_a = make_candidate(1)
    parent_b = make_candidate(2)
    child = Candidate(state=_FakeState(3), parent_candidate=parent_a)
    tracker = CandidateTracker([parent_a, parent_b])
    pruned = tracker.prune_empty([child])
    assert tracker.candidates == [parent_a]
    assert pruned == [parent_b]


def test_prune_empty_empty_new_candidates():
    p1, p2 = make_candidate(1), make_candidate(2)
    tracker = CandidateTracker([p1, p2])
    pruned = tracker.prune_empty([])
    assert tracker.candidates == []
    assert sorted(pruned, key=id) == sorted([p1, p2], key=id)


def test_prune_empty_returns_pruned_list():
    parent = make_candidate(1)
    tracker = CandidateTracker([parent])
    result = tracker.prune_empty([])
    assert result == [parent]


def test_prune_empty_uses_id_not_equality():
    # Two distinct Candidate objects that compare equal (same state hash) are separate parents
    state = _FakeState(99)
    parent_a = Candidate(state=state)
    parent_b = Candidate(state=state)  # equal to parent_a but different id

    child_of_a = Candidate(state=_FakeState(1), parent_candidate=parent_a)
    tracker = CandidateTracker([parent_a, parent_b])
    pruned = tracker.prune_empty([child_of_a])

    # parent_a has a child; parent_b does not — even though they compare equal
    assert tracker.candidates == [parent_a]
    assert pruned == [parent_b]
