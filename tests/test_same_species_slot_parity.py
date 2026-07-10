# Tests D3 parity: same-species doubles slot assignment is consistent across all consumers.
# All four sites that previously ran independent cursors now share _build_attacker_slot_map.
import pytest

from liveplay.battle_types import MatchResult
from liveplay.data.species import Species
from liveplay.data.moves import Move
from liveplay.data.natures import Nature
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.status import Status
from liveplay.state.pokemon import GenderEnum
from liveplay.state.side import SideState, FormatEnum
from liveplay.state.battle import BattleState
from liveplay.sweep_actions import (
    _build_attacker_slot_map,
    _extract_known_actions,
    _message_action_order_with_state,
    _extract_used_moves_from_groups,
)

from tests.state_builders import make_mon


def _make_mon(species, move_ids):
    return make_mon(species, moves=move_ids)


def _usedmove_msg(species_name: str, move_name: str, side_hint: int) -> MatchResult:
    """Minimal USEDMOVE MatchResult for a mon on the given side."""
    return MatchResult(
        string_id="STRINGID_USEDMOVE",
        id_value=0,
        constant_name="STRINGID_USEDMOVE",
        var_values=[species_name, move_name],
        score=0,
        side_hint=side_hint,
    )


def _make_doubles_state_same_species() -> BattleState:
    """Doubles BattleState: side 0 has two TENTACRUEL, side 1 has two MAGIKARP."""
    mon0a = _make_mon(Species.TENTACRUEL, (Move.SURF, Move.NONE, Move.NONE, Move.NONE))
    mon0b = _make_mon(Species.TENTACRUEL, (Move.TACKLE, Move.NONE, Move.NONE, Move.NONE))
    mon1a = _make_mon(Species.MAGIKARP, (Move.SPLASH, Move.NONE, Move.NONE, Move.NONE))
    mon1b = _make_mon(Species.MAGIKARP, (Move.SPLASH, Move.NONE, Move.NONE, Move.NONE))
    s0 = SideState(team=[mon0a, mon0b], active_indices=[0, 1], format=FormatEnum.DOUBLES)
    s1 = SideState(team=[mon1a, mon1b], active_indices=[0, 1], format=FormatEnum.DOUBLES)
    return BattleState(sides=(s0, s1), format=FormatEnum.DOUBLES)


class TestSameSpeciesSlotParity:
    """Verify that _build_attacker_slot_map produces a result that all consumers agree on.

    The canonical semantics (from _resolve_attacker_slot): when both active mons on a side
    share the same species, the FIRST observed USEDMOVE is assigned to slot 0, the SECOND
    to slot 1, etc. (cursor[side] % n, then increment). This test builds messages in
    "slot-0-first, slot-1-second" order and asserts all consumers see the same assignment.
    """

    def setup_method(self):
        self.state = _make_doubles_state_same_species()
        # Two same-species mons on side 0: slot 0 uses Surf, slot 1 uses Tackle.
        # Two same-species mons on side 1: slot 0 uses Splash, slot 1 also uses Splash.
        # Message order: side-0-slot0, side-1-slot0, side-0-slot1, side-1-slot1.
        self.msg_s0_slot0 = _usedmove_msg("TENTACRUEL", "SURF", side_hint=0)
        self.msg_s1_slot0 = _usedmove_msg("MAGIKARP", "SPLASH", side_hint=1)
        self.msg_s0_slot1 = _usedmove_msg("TENTACRUEL", "TACKLE", side_hint=0)
        self.msg_s1_slot1 = _usedmove_msg("MAGIKARP", "SPLASH", side_hint=1)
        self.messages = [
            self.msg_s0_slot0,
            self.msg_s1_slot0,
            self.msg_s0_slot1,
            self.msg_s1_slot1,
        ]
        self.slot_map = _build_attacker_slot_map(self.messages, self.state)

    def test_slot_map_assigns_first_occurrence_to_slot0(self):
        # First TENTACRUEL USEDMOVE → slot 0; second → slot 1.
        assert self.slot_map[id(self.msg_s0_slot0)] == (0, 0)
        assert self.slot_map[id(self.msg_s0_slot1)] == (0, 1)

    def test_slot_map_assigns_second_side_correctly(self):
        assert self.slot_map[id(self.msg_s1_slot0)] == (1, 0)
        assert self.slot_map[id(self.msg_s1_slot1)] == (1, 1)

    def test_action_order_agrees_with_slot_map(self):
        # _message_action_order_with_state using the shared map must produce the same
        # (side, slot) sequence as _build_attacker_slot_map.
        order = _message_action_order_with_state(self.messages, self.state, slot_map=self.slot_map)
        assert order == [(0, 0), (1, 0), (0, 1), (1, 1)]

    def test_action_order_without_map_matches_with_map(self):
        # The fallback (own cursor) must produce the same result as the shared map.
        order_with = _message_action_order_with_state(self.messages, self.state, slot_map=self.slot_map)
        order_without = _message_action_order_with_state(self.messages, self.state)
        assert order_with == order_without

    def test_extract_known_actions_agrees_with_slot_map(self):
        # _extract_known_actions with slot_map must assign Surf to slot 0 and Tackle to slot 1.
        known = _extract_known_actions(self.messages, self.state, slot_map=self.slot_map)
        s0_actions = known[0]
        assert s0_actions[0] is not None, "slot 0 action must be assigned"
        assert s0_actions[1] is not None, "slot 1 action must be assigned"
        # Surf is in move slot 0 for mon at team index 0; Tackle is in move slot 0 for mon at index 1.
        assert s0_actions[0].move_slot == 0   # slot 0 → Surf (move_slot 0)
        assert s0_actions[1].move_slot == 0   # slot 1 → Tackle (move_slot 0)

    def test_extract_known_actions_without_map_matches_with_map(self):
        known_with = _extract_known_actions(self.messages, self.state, slot_map=self.slot_map)
        known_without = _extract_known_actions(self.messages, self.state)
        for side in (0, 1):
            with_actions = known_with[side]
            without_actions = known_without[side]
            for slot in range(len(with_actions)):
                a_with = with_actions[slot]
                a_without = without_actions[slot]
                # Both must agree: either both None or both the same move_slot.
                if a_with is None:
                    assert a_without is None
                else:
                    assert a_without is not None
                    assert a_with.move_slot == a_without.move_slot

    def test_extract_used_moves_agrees_with_slot_map(self):
        used = _extract_used_moves_from_groups(
            None, self.state, flat_messages=self.messages, slot_map=self.slot_map
        )
        # slot 0 uses Surf, slot 1 uses Tackle
        assert used.get((0, 0)) == Move.SURF
        assert used.get((0, 1)) == Move.TACKLE

    def test_extract_used_moves_without_map_matches_with_map(self):
        used_with = _extract_used_moves_from_groups(
            None, self.state, flat_messages=self.messages, slot_map=self.slot_map
        )
        used_without = _extract_used_moves_from_groups(
            None, self.state, flat_messages=self.messages
        )
        assert used_with == used_without

    def test_all_consumers_agree_on_slot_assignment(self):
        """Cross-consumer parity: all three sites must assign the same (side, slot) per message."""
        order = _message_action_order_with_state(self.messages, self.state, slot_map=self.slot_map)
        used = _extract_used_moves_from_groups(
            None, self.state, flat_messages=self.messages, slot_map=self.slot_map
        )
        # The mover order must include the same (side, slot) pairs as the used_moves keys.
        assert set(order) == set(used.keys())

    def test_singles_is_noop_slot0_always(self):
        """Singles: non-ambiguous — one active per side — always resolves to slot 0."""
        from tests.state_builders import make_battle
        mon0 = _make_mon(Species.PIKACHU, (Move.THUNDERBOLT, Move.NONE, Move.NONE, Move.NONE))
        mon1 = _make_mon(Species.PIKACHU, (Move.THUNDERBOLT, Move.NONE, Move.NONE, Move.NONE))
        state = make_battle(mon0, mon1)
        msg0 = _usedmove_msg("PIKACHU", "THUNDERBOLT", side_hint=0)
        msg1 = _usedmove_msg("PIKACHU", "THUNDERBOLT", side_hint=1)
        messages = [msg0, msg1]
        slot_map = _build_attacker_slot_map(messages, state)
        # In singles there is only one active per side — exactly one matching position.
        # The cursor is never consumed; both resolve directly to slot 0.
        assert slot_map[id(msg0)] == (0, 0)
        assert slot_map[id(msg1)] == (1, 0)
        order = _message_action_order_with_state(messages, state, slot_map=slot_map)
        assert order == [(0, 0), (1, 0)]
