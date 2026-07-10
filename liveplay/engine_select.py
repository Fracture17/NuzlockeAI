# Engine seam: SimulationError, enumerate_legal_actions (Python impl), and Stage-E stub for run_candidate_sweep.
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from liveplay.actions import enumerate_legal_actions  # noqa: F401 (re-exported)

if TYPE_CHECKING:
    from liveplay.battle_types import MatchResult, ActionGroup
    from liveplay.candidate import Candidate
    from liveplay.state.battle import BattleState


class SimulationError(Exception):
    """Raised when the sweep produces no valid candidates, or an unsupported RNG situation is detected."""

    def __init__(self, messages=None, hp_deltas=None, initial_candidates=None, reason: str = ""):
        if reason:
            super().__init__(reason)
        else:
            super().__init__(
                f"No candidates survived sweep: "
                f"{len(initial_candidates or [])} initial, "
                f"{len(messages or [])} messages, "
                f"hp_deltas={hp_deltas}"
            )
        self.messages = messages or []
        self.hp_deltas = hp_deltas or []
        self.initial_candidates = initial_candidates or []


def run_candidate_sweep(
    messages: "list[MatchResult]",
    hp_deltas: list,
    initial_candidates: "list[Candidate]",
    action_groups: "Optional[list[ActionGroup]]" = None,
) -> "list[Candidate]":
    """Enumerate RNG/action combos for each initial candidate and return survivors.

    Filters by HP delta match, action order match, and log-event consistency.
    Uses sequential per-side roll enumeration with damage-value deduplication.
    Returns deduplicated Candidate list (one per unique final BattleState).

    hp_deltas: list of HpDeltaSeq records — identity-bound (side, species, slot, deltas, max_hp).
    action_groups: optional structured message groups for secondary effect injection.
    """
    raise NotImplementedError("Stage E: C++ sweep not wired")


