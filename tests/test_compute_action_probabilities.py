# Tests for liveplay.engine_select.compute_action_probabilities and its integration with _validate_known_opponent_action.
import pytest

from liveplay.actions import Action, ActionKind
from liveplay.data.moves import Move
from liveplay.data.species import Species
from tests.state_builders import make_mon, make_battle


def _make_simple_state():
    """1v1: Gengar (Sludge Bomb + Shadow Ball) vs Chansey (Soft-Boiled + Seismic Toss)."""
    ai_mon = make_mon(Species.GENGAR, moves=(Move.SLUDGE_BOMB, Move.SHADOW_BALL))
    player_mon = make_mon(Species.CHANSEY, moves=(Move.SOFT_BOILED, Move.SEISMIC_TOSS))
    return make_battle(player_mon, ai_mon)


# ---------------------------------------------------------------------------
# Test 1: basic return shape and probability axioms
# ---------------------------------------------------------------------------

def test_returns_nonempty_list():
    from liveplay.engine_select import compute_action_probabilities
    state = _make_simple_state()
    result = compute_action_probabilities(state, ai_idx=1)
    assert isinstance(result, list)
    assert len(result) > 0


def test_probs_sum_to_one():
    from liveplay.engine_select import compute_action_probabilities
    state = _make_simple_state()
    result = compute_action_probabilities(state, ai_idx=1)
    total = sum(p for _, p in result)
    assert abs(total - 1.0) < 1e-6, f"Probabilities sum to {total}, expected ~1.0"


def test_all_kinds_are_action_kind_members():
    from liveplay.engine_select import compute_action_probabilities
    state = _make_simple_state()
    result = compute_action_probabilities(state, ai_idx=1)
    for action, _ in result:
        assert isinstance(action.kind, ActionKind), f"Expected ActionKind, got {type(action.kind)}"


def test_move_actions_have_valid_move_slot():
    from liveplay.engine_select import compute_action_probabilities
    state = _make_simple_state()
    result = compute_action_probabilities(state, ai_idx=1)
    for action, _ in result:
        if action.kind == ActionKind.MOVE:
            assert action.move_slot >= 0 or action.move_slot in (-1, -2), (
                f"Invalid move_slot: {action.move_slot}"
            )


# ---------------------------------------------------------------------------
# Test 2: ai_idx default is 1; explicit call matches default
# ---------------------------------------------------------------------------

def test_ai_idx_default_is_1():
    from liveplay.engine_select import compute_action_probabilities
    import inspect
    sig = inspect.signature(compute_action_probabilities)
    assert sig.parameters["ai_idx"].default == 1


def test_explicit_ai_idx_1_matches_default():
    from liveplay.engine_select import compute_action_probabilities
    state = _make_simple_state()
    default_result = compute_action_probabilities(state)
    explicit_result = compute_action_probabilities(state, ai_idx=1)
    assert len(default_result) == len(explicit_result)
    for (a1, p1), (a2, p2) in zip(default_result, explicit_result):
        assert a1 == a2
        assert abs(p1 - p2) < 1e-9


# ---------------------------------------------------------------------------
# Test 3: integration — _validate_known_opponent_action import resolves
# ---------------------------------------------------------------------------

def test_validate_known_opponent_action_no_import_error():
    """Confirm lazy import no longer raises ImportError when validation is reached."""
    from liveplay.sweep_actions import _validate_known_opponent_action

    state = _make_simple_state()
    # AI (side 1) has Gengar with Sludge Bomb at slot 0 and Shadow Ball at slot 1.
    # Both moves have nonzero probability, so either slot 0 or slot 1 should pass.
    known_action = Action(kind=ActionKind.MOVE, move_slot=0)
    known_actions = {1: [known_action]}
    # Should not raise ImportError or UnexpectedOpponentActionError
    _validate_known_opponent_action(known_actions, state)


def test_validate_raises_for_zero_probability_action():
    """A known action that doesn't match any legal action should raise UnexpectedOpponentActionError."""
    from liveplay.sweep_actions import _validate_known_opponent_action, UnexpectedOpponentActionError

    state = _make_simple_state()
    # Slot 3 doesn't exist for Gengar (only 2 moves) — should be p=0 or not in legal actions.
    # Use a slot index clearly out of range for the 2-move mon.
    known_action = Action(kind=ActionKind.MOVE, move_slot=3)
    known_actions = {1: [known_action]}
    with pytest.raises(UnexpectedOpponentActionError):
        _validate_known_opponent_action(known_actions, state)
