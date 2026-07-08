# Pure battle-decision helpers and policy abstraction. No I/O or emulator imports.
from __future__ import annotations

import random
from abc import ABC, abstractmethod

from liveplay.data.moves import Move
from liveplay.actions import ActionKind
from liveplay.engine_select import enumerate_legal_actions
from liveplay.state.battle import BattleState
from liveplay.state.pokemon import PokemonState


def eligible_switch_targets(state: BattleState) -> list[PokemonState]:
    """Non-active, non-fainted, non-zero-HP members of the player's team."""
    side = state.sides[0]
    active_idx = side.active_indices[0]
    return [
        mon for i, mon in enumerate(side.team)
        if i != active_idx
        and not mon.fainted
        and (mon.hp or 0) > 0
    ]


def can_switch_out(state: BattleState) -> bool:
    """True if the active player Pokémon may VOLUNTARILY switch this turn.

    Trapping (partial-trap moves like Bind/Wrap → BOUND, Mean Look/Anchor Shot →
    TRAPPED, and the Shadow Tag / Magnet Pull / Arena Trap abilities, with the usual
    Ghost-type and Shed Shell exceptions) blocks switching. Rather than re-deriving
    those rules, delegate to the engine's canonical action enumerator: switching is
    allowed iff it produced at least one SWITCH action. Keeping trap logic in one
    place avoids the stress-test policy drifting out of sync with the simulation.
    """
    return any(
        a.kind == ActionKind.SWITCH
        for a in enumerate_legal_actions(state, side_idx=0)
    )


def available_moves(state: BattleState) -> list[Move]:
    """Moves the active player Pokémon can legally select: non-NONE and non-zero PP."""
    side = state.sides[0]
    active = side.team[side.active_indices[0]]
    return [
        move for move, pp in zip(active.move_ids, active.move_pp)
        if move != Move.NONE and pp > 0
    ]


class BattlePolicy(ABC):
    """Abstract base for battle decision policies."""

    @abstractmethod
    def choose_battle_action(self, state: BattleState) -> Move | str:
        """Return a Move to use or a species-name str to voluntarily switch to."""

    @abstractmethod
    def choose_forced_switch(self, state: BattleState) -> str:
        """Return a species-name str to switch to (forced, e.g. after KO)."""


class RandomPolicy(BattlePolicy):
    """Policy that picks uniformly at random with an 80/20 move/switch split."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def choose_battle_action(self, state: BattleState) -> Move | str:
        """Pick a move (80%) or switch (20%). Respects edge cases when one set is empty."""
        # A trapped active (Bind/Wrap, Mean Look, Shadow Tag, etc.) cannot voluntarily
        # switch — offering one hangs the runner forever at the move menu. Treat the
        # bench as empty when switching is illegal so we always fall back to a move.
        targets = eligible_switch_targets(state) if can_switch_out(state) else []
        moves = available_moves(state)

        if not targets and not moves:
            raise RuntimeError("No legal battle action: active Pokémon has no usable moves and no bench.")
        if not targets:
            return self._rng.choice(moves)
        if not moves:
            return self._rng.choice(targets).species.name
        # Both non-empty: 20% chance to switch, 80% chance to move.
        if self._rng.random() < 0.20:
            return self._rng.choice(targets).species.name
        return self._rng.choice(moves)

    def choose_forced_switch(self, state: BattleState) -> str:
        """Return a random eligible bench member's species name; raises if bench is empty."""
        targets = eligible_switch_targets(state)
        if not targets:
            raise RuntimeError("No valid bench member to switch to (forced switch).")
        return self._rng.choice(targets).species.name
