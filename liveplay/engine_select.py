# Engine seam: SimulationError, enumerate_legal_actions (Python impl), Stage-E stub, and C++ AI probability wrapper.
from __future__ import annotations

import json
from typing import Optional, TYPE_CHECKING

from liveplay.actions import Action, ActionKind, enumerate_legal_actions  # noqa: F401 (re-exported)

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


def compute_action_probabilities(state: "BattleState", ai_idx: int = 1) -> list[tuple[Action, float]]:
    """Return the analytic probability distribution over legal actions for the AI side.

    Delegates to the C++ binding, which enumerates damage-roll configs to compute
    exact per-action probabilities. Returns a list of (Action, prob) pairs summing to 1.
    """
    import nuzlocke_engine_cpp as cpp
    from liveplay.data.moves import Move
    import liveplay.sweep_io as sweep_io

    state_json = json.dumps(sweep_io.to_jsonable(state))
    result = cpp.compute_action_probabilities(state_json, ai_idx)

    actions_raw = result["actions"]
    probs_raw = result["probs"]

    pairs: list[tuple[Action, float]] = []
    for d, prob in zip(actions_raw, probs_raw):
        move_override_val = d["move_override"]
        move_override = Move(move_override_val) if move_override_val >= 0 else None
        action = Action(
            kind=ActionKind(d["kind"]),
            move_slot=d["move_slot"],
            move_override=move_override,
            switch_to_slot=d["switch_to_slot"],
            target_side=d["target_side"],
            target_slot=d["target_slot"],
            source_slot=d.get("source_slot", 0),
        )
        pairs.append((action, prob))
    return pairs


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


