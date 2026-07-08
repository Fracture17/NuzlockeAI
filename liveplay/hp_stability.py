"""
HP stability tracking for the NuzlockeAI battle pipeline.

StabilityBuffer: generic N-consecutive-identical-readings tracker.
OpponentHpBuffer: wraps k-pixel readings (int | None), requires 2 identical.
PlayerHpBuffer: wraps hp_current readings (int | None), requires 2 identical.
hp_range: convert k-pixel value to (hp_min, hp_max) using bar formula.
"""
from __future__ import annotations
import math

__all__ = ["StabilityBuffer", "OpponentHpBuffer", "PlayerHpBuffer", "hp_range"]


class StabilityBuffer:
    """Confirms a value only after N consecutive identical non-None readings."""

    def __init__(self, required: int = 3) -> None:
        self._required: int = required
        self._candidate: int | None = None
        self._streak: int = 0
        self._confirmed: int | None = None

    def update(self, value: int | None) -> bool:
        """Feed a new reading. Returns True if a NEW stable value was just confirmed.

        None readings break the streak (same as a different value).
        """
        if value is None or value != self._candidate:
            self._candidate = value
            self._streak = 1 if value is not None else 0
            return False
        self._streak += 1
        if self._streak >= self._required and value != self._confirmed:
            self._confirmed = value
            return True
        return False

    @property
    def confirmed(self) -> int | None:
        """The last confirmed stable value, or None if not yet confirmed."""
        return self._confirmed

    def reset(self) -> None:
        """Reset all state."""
        self._candidate = None
        self._streak = 0
        self._confirmed = None


class OpponentHpBuffer(StabilityBuffer):
    """Stability buffer for opponent k-pixel HP readings; requires 2 identical."""

    def __init__(self) -> None:
        super().__init__(required=2)


class PlayerHpBuffer(StabilityBuffer):
    """Stability buffer for player hp_current readings; requires 2 identical."""

    def __init__(self) -> None:
        super().__init__(required=2)


def hp_range(k: int, max_hp: int) -> tuple[int, int]:
    """Convert k-pixel bar value to (hp_min, hp_max).

    Formula (from pokeemerald battle_interface.c):
      bar_pixels = floor(hp * 48 / max_hp), minimum 1 if hp > 0.
    k=0 means the bar is empty (KO); returns (0, 0).
    """
    if k == 0:
        return 0, 0
    hp_min = math.ceil(k * max_hp / 48)
    hp_max = min(math.ceil((k + 1) * max_hp / 48) - 1, max_hp)
    return hp_min, hp_max
