# Shared pure predicates/constants for the sweep reconciliation leaf modules
# (sweep_reconcile, sweep_actions, and the forthcoming sweep_driver/sweep_secondaries).
# Kept here so the leaf modules stay mutually independent without duplicating logic.
from __future__ import annotations

from liveplay.battle_types import MatchResult
from liveplay.data.moves import MOVE_DATA, MoveTarget

# Spread move-targets (hit multiple foes simultaneously).
_SPREAD_TARGETS = frozenset({MoveTarget.ALL_ADJACENT_FOES, MoveTarget.ALL_ADJACENT, MoveTarget.ALL})


def _msg_is_foe(msg: MatchResult) -> bool:
    """True if the reconstructed message carries the opponent 'Foe' prefix (→ side 1)."""
    text = (msg.matched_text or "").strip().lower()
    return text.startswith("foe ")


def _move_is_spread(move_enum) -> bool:
    """Return True if move_enum is a spread move (hits multiple foes simultaneously)."""
    if move_enum is None:
        return False
    md = MOVE_DATA.get(move_enum)
    return md is not None and md.target in _SPREAD_TARGETS
