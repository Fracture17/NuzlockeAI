# Candidate dataclass: a BattleState with attached RNG history, unknown actions, and parent link for tree traversal.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from liveplay.state.battle import BattleState
    from liveplay.actions import Action

__all__ = ["Candidate", "PartialCandidate"]


@dataclass
class Candidate:
    """A state node in the search tree, tracking how it was reached."""
    state: 'BattleState'
    rng_sequence: list = field(default_factory=list)   # ordered [(RNGEvent, value), ...] tuples recording how this candidate was produced
    unknown_actions: dict = field(default_factory=dict)  # {side_idx: Action | None}; None = still unknown
    parent_candidate: Optional['Candidate'] = field(default=None, repr=False, compare=False, hash=False)


@dataclass(frozen=True)
class PartialCandidate:
    """Accumulates per-mover roll/crit decisions during the mover-loop sweep."""
    rolls: tuple = ()          # fixed DAMAGE_ROLL values for decided movers (scalar or per-hit tuple)
    crits: tuple = ()          # fixed CRIT values for decided movers (bool or per-hit tuple)
    mover_iteration: int = 0   # index of the next mover to decide
