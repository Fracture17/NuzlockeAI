"""Functional coverage for the plain-mode SPEED_TIE force hook (E2 Task 5).

run_one_turn_cpp gains an optional `speed_tie_order` param: a forced act-order for a
controlled cross-side speed tie, mirroring OLD sweep pre_rng_inject[SPEED_TIE]. Without it,
an unresolved cross-side MOVE tie makes the binding throw (NeedsRNG -> RuntimeError). With it,
the tie resolves by the ordering's rank and the earlier (side, slot) acts first.

Setup: two identical mons (same species/level/nature/IVs => identical Speed => a real tie),
each holding 1 HP and using Tackle at the other. Whoever acts first faints the other before it
can move, so the *surviving* side is exactly the tie winner named first in speed_tie_order.
"""
import pytest

from liveplay.cpp_driver import run_one_turn_cpp
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.rng import AVERAGE_LUCK
from tests.state_builders import make_mon, make_battle, slot, active


def _tie_battle():
    m0 = make_mon(Species.RATTATA, moves=(Move.TACKLE,), hp=1)
    m1 = make_mon(Species.RATTATA, moves=(Move.TACKLE,), hp=1)
    return make_battle(m0, m1)


def test_unresolved_cross_side_tie_raises():
    """No speed_tie_order => the binding must not silently pick; it raises."""
    state = _tie_battle()
    with pytest.raises(RuntimeError):
        run_one_turn_cpp(state, slot(0), slot(0), AVERAGE_LUCK, AVERAGE_LUCK)


def test_force_side0_first():
    """order [(0,0),(1,0)] => side 0 acts first, faints side 1; side 0 survives."""
    state = _tie_battle()
    out = run_one_turn_cpp(
        state, slot(0), slot(0), AVERAGE_LUCK, AVERAGE_LUCK,
        speed_tie_order=[(0, 0), (1, 0)],
    )
    assert not active(out, 0).fainted, "side 0 (tie winner) should survive"
    assert active(out, 1).fainted, "side 1 (tie loser) should faint before acting"


def test_force_side1_first():
    """order [(1,0),(0,0)] => side 1 acts first, faints side 0; side 1 survives."""
    state = _tie_battle()
    out = run_one_turn_cpp(
        state, slot(0), slot(0), AVERAGE_LUCK, AVERAGE_LUCK,
        speed_tie_order=[(1, 0), (0, 0)],
    )
    assert not active(out, 1).fainted, "side 1 (tie winner) should survive"
    assert active(out, 0).fainted, "side 0 (tie loser) should faint before acting"
