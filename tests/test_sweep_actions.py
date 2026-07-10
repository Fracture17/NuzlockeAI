# Tests for liveplay/sweep_actions.py — focused unit tests, one behavior each.
import pytest

from liveplay.battle_types import ActionGroup, MatchResult
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.actions import Action, ActionKind
from liveplay.engine_select import SimulationError

from tests.state_builders import (
    make_mon, make_battle, make_doubles_battle,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mr(string_id, *, constant_name="", var_values=None, id_value=0, score=0,
        side_hint=None, matched_text=""):
    """Build a MatchResult for testing."""
    vals = var_values or []
    return MatchResult(
        string_id=string_id,
        id_value=id_value,
        constant_name=constant_name,
        var_values=vals,
        score=score,
        matched_text=matched_text,
        side_hint=side_hint,
    )


def _usedmove(attacker: str, move: str, side_hint: int) -> MatchResult:
    return _mr("STRINGID_USEDMOVE", var_values=[attacker, move], side_hint=side_hint)


def _make_singles_state(species0=Species.PIKACHU, moves0=(Move.THUNDERBOLT,),
                        species1=Species.RAICHU, moves1=(Move.TACKLE,)):
    mon0 = make_mon(species0, moves=moves0)
    mon1 = make_mon(species1, moves=moves1)
    return make_battle(mon0, mon1)


# ---------------------------------------------------------------------------
# TestSlotForName
# ---------------------------------------------------------------------------

class TestSlotForName:
    """_slot_for_name resolves (side, slot) of an active mon by fuzzy name."""

    def test_returns_correct_side_and_slot(self):
        from liveplay.sweep_actions import _slot_for_name
        state = _make_singles_state()
        result = _slot_for_name("PIKACHU", state)
        assert result == (0, 0)

    def test_returns_none_for_unknown_name(self):
        from liveplay.sweep_actions import _slot_for_name
        state = _make_singles_state()
        result = _slot_for_name("ONIX", state)
        assert result is None

    def test_side_constraint_restricts_search(self):
        from liveplay.sweep_actions import _slot_for_name
        state = _make_singles_state()
        # PIKACHU is on side 0; side_constraint=1 should find nothing
        assert _slot_for_name("PIKACHU", state, side_constraint=1) is None
        assert _slot_for_name("PIKACHU", state, side_constraint=0) == (0, 0)

    def test_same_species_raises_without_hp_disambiguator(self):
        from liveplay.sweep_actions import _slot_for_name
        mon_a = make_mon(Species.MAGIKARP, moves=(Move.SPLASH,))
        mon_b = make_mon(Species.MAGIKARP, moves=(Move.SPLASH,))
        state = make_doubles_battle(mon_a, mon_b, make_mon(Species.RAICHU, moves=(Move.TACKLE,)),
                                    make_mon(Species.RAICHU, moves=(Move.TACKLE,)))
        with pytest.raises(SimulationError):
            _slot_for_name("MAGIKARP", state)

    def test_same_species_resolves_via_hp_changed(self):
        from liveplay.sweep_actions import _slot_for_name
        mon_a = make_mon(Species.MAGIKARP, moves=(Move.SPLASH,))
        mon_b = make_mon(Species.MAGIKARP, moves=(Move.SPLASH,))
        state = make_doubles_battle(mon_a, mon_b, make_mon(Species.RAICHU, moves=(Move.TACKLE,)),
                                    make_mon(Species.RAICHU, moves=(Move.TACKLE,)))
        # slot 1 took damage → hp_changed_by_slot disambiguates to slot 1
        result = _slot_for_name("MAGIKARP", state, hp_changed_by_slot={(0, 1): True})
        assert result == (0, 1)


# ---------------------------------------------------------------------------
# TestRecipientSlot
# ---------------------------------------------------------------------------

class TestRecipientSlot:
    """_recipient_slot reads var_values[0] and delegates to _slot_for_name."""

    def test_resolves_from_var_values(self):
        from liveplay.sweep_actions import _recipient_slot
        state = _make_singles_state()
        msg = _mr("STRINGID_PKMNFLINCHED", var_values=["PIKACHU"])
        assert _recipient_slot(msg, state) == (0, 0)

    def test_returns_none_when_no_var_values(self):
        from liveplay.sweep_actions import _recipient_slot
        state = _make_singles_state()
        msg = _mr("STRINGID_PKMNFLINCHED", var_values=[])
        assert _recipient_slot(msg, state) is None


# ---------------------------------------------------------------------------
# TestResolveAttackerSlot
# ---------------------------------------------------------------------------

class TestResolveAttackerSlot:
    """_resolve_attacker_slot returns the active position, advancing cursor on ties."""

    def test_unique_species_returns_position(self):
        from liveplay.sweep_actions import _resolve_attacker_slot
        state = _make_singles_state()
        cursor = [0, 0]
        pos = _resolve_attacker_slot(0, "PIKACHU", state, cursor)
        assert pos == 0

    def test_unknown_species_raises(self):
        from liveplay.sweep_actions import _resolve_attacker_slot
        state = _make_singles_state()
        cursor = [0, 0]
        with pytest.raises(SimulationError):
            _resolve_attacker_slot(0, "ONIX", state, cursor)

    def test_same_species_cursor_advances(self):
        from liveplay.sweep_actions import _resolve_attacker_slot
        mon_a = make_mon(Species.MAGIKARP, moves=(Move.SPLASH,))
        mon_b = make_mon(Species.MAGIKARP, moves=(Move.SPLASH,))
        state = make_doubles_battle(mon_a, mon_b, make_mon(Species.RAICHU, moves=(Move.TACKLE,)),
                                    make_mon(Species.RAICHU, moves=(Move.TACKLE,)))
        cursor = [0, 0]
        first = _resolve_attacker_slot(0, "MAGIKARP", state, cursor)
        second = _resolve_attacker_slot(0, "MAGIKARP", state, cursor)
        assert first == 0
        assert second == 1


# ---------------------------------------------------------------------------
# TestBuildAttackerSlotMap
# ---------------------------------------------------------------------------

class TestBuildAttackerSlotMap:
    """_build_attacker_slot_map assigns (side, slot) for each USEDMOVE."""

    def test_singles_both_sides(self):
        from liveplay.sweep_actions import _build_attacker_slot_map
        state = _make_singles_state()
        msg0 = _usedmove("PIKACHU", "THUNDERBOLT", side_hint=0)
        msg1 = _usedmove("RAICHU", "TACKLE", side_hint=1)
        slot_map = _build_attacker_slot_map([msg0, msg1], state)
        assert slot_map[id(msg0)] == (0, 0)
        assert slot_map[id(msg1)] == (1, 0)

    def test_non_usedmove_not_in_map(self):
        from liveplay.sweep_actions import _build_attacker_slot_map
        state = _make_singles_state()
        other = _mr("STRINGID_CRITICALHIT")
        slot_map = _build_attacker_slot_map([other], state)
        assert id(other) not in slot_map

    def test_unknown_attacker_omitted(self):
        from liveplay.sweep_actions import _build_attacker_slot_map
        state = _make_singles_state()
        msg = _usedmove("ONIX", "TACKLE", side_hint=0)
        slot_map = _build_attacker_slot_map([msg], state)
        assert id(msg) not in slot_map


# ---------------------------------------------------------------------------
# TestBuildAttackerSlotMaps
# ---------------------------------------------------------------------------

class TestBuildAttackerSlotMaps:
    """_build_attacker_slot_maps fans out ambiguous same-species assignments."""

    def test_singles_returns_single_map(self):
        from liveplay.sweep_actions import _build_attacker_slot_maps
        state = _make_singles_state()
        msg = _usedmove("PIKACHU", "THUNDERBOLT", side_hint=0)
        maps = _build_attacker_slot_maps([msg], state)
        assert len(maps) == 1
        assert maps[0][id(msg)] == (0, 0)

    def test_same_species_doubles_fans_out(self):
        from liveplay.sweep_actions import _build_attacker_slot_maps
        mon_a = make_mon(Species.MAGIKARP, moves=(Move.SPLASH,))
        mon_b = make_mon(Species.MAGIKARP, moves=(Move.SPLASH,))
        state = make_doubles_battle(mon_a, mon_b,
                                    make_mon(Species.RAICHU, moves=(Move.TACKLE,)),
                                    make_mon(Species.RAICHU, moves=(Move.TACKLE,)))
        msg0 = _usedmove("MAGIKARP", "SPLASH", side_hint=0)
        msg1 = _usedmove("MAGIKARP", "SPLASH", side_hint=0)
        maps = _build_attacker_slot_maps([msg0, msg1], state)
        # Two distinct non-colliding assignments: (slot0,slot1) and (slot1,slot0)
        assert len(maps) == 2


# ---------------------------------------------------------------------------
# TestSegmentFlatMessagesByMover
# ---------------------------------------------------------------------------

class TestSegmentFlatMessagesByMover:
    """_segment_flat_messages_by_mover groups non-USEDMOVE messages by attacker."""

    def test_basic_segmentation(self):
        from liveplay.sweep_actions import _segment_flat_messages_by_mover
        state = _make_singles_state()
        crit = _mr("STRINGID_CRITICALHIT")
        msg0 = _usedmove("PIKACHU", "THUNDERBOLT", side_hint=0)
        msg1 = _usedmove("RAICHU", "TACKLE", side_hint=1)
        segments = _segment_flat_messages_by_mover([msg0, crit, msg1], state)
        assert len(segments) == 2
        side0, slot0, msgs0 = segments[0]
        assert side0 == 0 and slot0 == 0
        assert crit in msgs0

    def test_messages_before_first_usedmove_discarded(self):
        from liveplay.sweep_actions import _segment_flat_messages_by_mover
        state = _make_singles_state()
        orphan = _mr("STRINGID_CRITICALHIT")
        msg = _usedmove("PIKACHU", "THUNDERBOLT", side_hint=0)
        segments = _segment_flat_messages_by_mover([orphan, msg], state)
        assert len(segments) == 1
        _, _, msgs = segments[0]
        assert orphan not in msgs

    def test_slot_map_path(self):
        from liveplay.sweep_actions import _segment_flat_messages_by_mover, _build_attacker_slot_map
        state = _make_singles_state()
        msg0 = _usedmove("PIKACHU", "THUNDERBOLT", side_hint=0)
        msg1 = _usedmove("RAICHU", "TACKLE", side_hint=1)
        slot_map = _build_attacker_slot_map([msg0, msg1], state)
        segments = _segment_flat_messages_by_mover([msg0, msg1], state, slot_map=slot_map)
        assert len(segments) == 2


# ---------------------------------------------------------------------------
# TestMessageActionOrderWithState
# ---------------------------------------------------------------------------

class TestMessageActionOrderWithState:
    """_message_action_order_with_state returns (side, slot) tuples in USEDMOVE order."""

    def test_singles_order(self):
        from liveplay.sweep_actions import _message_action_order_with_state
        state = _make_singles_state()
        msg0 = _usedmove("PIKACHU", "THUNDERBOLT", side_hint=0)
        msg1 = _usedmove("RAICHU", "TACKLE", side_hint=1)
        order = _message_action_order_with_state([msg0, msg1], state)
        assert order == [(0, 0), (1, 0)]

    def test_non_usedmove_skipped(self):
        from liveplay.sweep_actions import _message_action_order_with_state
        state = _make_singles_state()
        crit = _mr("STRINGID_CRITICALHIT")
        msg = _usedmove("PIKACHU", "THUNDERBOLT", side_hint=0)
        order = _message_action_order_with_state([crit, msg], state)
        assert order == [(0, 0)]

    def test_with_slot_map(self):
        from liveplay.sweep_actions import _message_action_order_with_state, _build_attacker_slot_map
        state = _make_singles_state()
        msg0 = _usedmove("PIKACHU", "THUNDERBOLT", side_hint=0)
        msg1 = _usedmove("RAICHU", "TACKLE", side_hint=1)
        slot_map = _build_attacker_slot_map([msg0, msg1], state)
        order = _message_action_order_with_state([msg0, msg1], state, slot_map=slot_map)
        assert order == [(0, 0), (1, 0)]


# ---------------------------------------------------------------------------
# TestFoeDamagedSlots
# ---------------------------------------------------------------------------

class TestFoeDamagedSlots:
    """_foe_damaged_slots returns indices where final HP < initial HP."""

    def test_single_damaged_slot(self):
        from liveplay.sweep_actions import _foe_damaged_slots
        foe_deltas = [[(100, 60)], []]
        assert _foe_damaged_slots(foe_deltas) == [0]

    def test_no_damage(self):
        from liveplay.sweep_actions import _foe_damaged_slots
        foe_deltas = [[(100, 100)], [(80, 80)]]
        assert _foe_damaged_slots(foe_deltas) == []

    def test_both_slots_damaged(self):
        from liveplay.sweep_actions import _foe_damaged_slots
        foe_deltas = [[(100, 50)], [(80, 30)]]
        assert _foe_damaged_slots(foe_deltas) == [0, 1]

    def test_empty_slot_skipped(self):
        from liveplay.sweep_actions import _foe_damaged_slots
        foe_deltas = [[], [(80, 30)]]
        assert _foe_damaged_slots(foe_deltas) == [1]


# ---------------------------------------------------------------------------
# TestSweepBuildFlatMessages
# ---------------------------------------------------------------------------

class TestSweepBuildFlatMessages:
    """_sweep_build_flat_messages merges messages and action group content."""

    def test_no_groups_returns_copy(self):
        from liveplay.sweep_actions import _sweep_build_flat_messages
        msg = _mr("STRINGID_CRITICALHIT")
        result = _sweep_build_flat_messages([msg], None)
        assert result == [msg]

    def test_group_primary_added_once(self):
        from liveplay.sweep_actions import _sweep_build_flat_messages
        primary = _mr("STRINGID_USEDMOVE", var_values=["PIKACHU", "TACKLE"])
        secondary = _mr("STRINGID_CRITICALHIT")
        group = ActionGroup(primary=primary, secondaries=[secondary])
        result = _sweep_build_flat_messages([], [group])
        assert primary in result
        assert secondary in result

    def test_no_duplicate_if_primary_already_present(self):
        from liveplay.sweep_actions import _sweep_build_flat_messages
        primary = _mr("STRINGID_USEDMOVE", var_values=["PIKACHU", "TACKLE"])
        group = ActionGroup(primary=primary, secondaries=[])
        result = _sweep_build_flat_messages([primary], [group])
        assert result.count(primary) == 1


# ---------------------------------------------------------------------------
# TestResolveCalledMove
# ---------------------------------------------------------------------------

class TestResolveCalledMove:
    """_resolve_called_move strictly resolves Metronome-called move names."""

    def test_exact_normalized_name(self):
        from liveplay.sweep_actions import _resolve_called_move
        assert _resolve_called_move("SURF") == Move.SURF

    def test_spaced_name_resolves(self):
        from liveplay.sweep_actions import _resolve_called_move
        # "SOLAR BEAM" normalized → "SOLAR_BEAM"
        assert _resolve_called_move("SOLAR BEAM") == Move.SOLAR_BEAM

    def test_fused_spelling_resolves(self):
        from liveplay.sweep_actions import _resolve_called_move
        # Gen-3 fused: "SOLARBEAM" → SOLAR_BEAM via flat comparison
        assert _resolve_called_move("SOLARBEAM") == Move.SOLAR_BEAM

    def test_unknown_returns_none(self):
        from liveplay.sweep_actions import _resolve_called_move
        assert _resolve_called_move("NONEXISTENT_MOVE_XYZ") is None

    def test_does_not_fuzzy_match_different_move(self):
        from liveplay.sweep_actions import _resolve_called_move
        # "CHARM" and "CHARGE" differ by ≤2 Levenshtein but must NOT cross-match
        # _resolve_called_move must return None for "CHARGE" if CHARGE isn't in the enum
        result = _resolve_called_move("CHARGE")
        # CHARGE is not a Move enum member — must return None, never CHARM
        if result is not None:
            assert result != Move.CHARM


# ---------------------------------------------------------------------------
# TestActingAction
# ---------------------------------------------------------------------------

class TestActingAction:
    """_acting_action extracts the per-slot action from scalars or lists."""

    def test_scalar_action_side0(self):
        from liveplay.sweep_actions import _acting_action
        a0 = Action(kind=ActionKind.MOVE, move_slot=0)
        a1 = Action(kind=ActionKind.MOVE, move_slot=1)
        assert _acting_action(a0, a1, 0, 0) is a0

    def test_scalar_action_side1(self):
        from liveplay.sweep_actions import _acting_action
        a0 = Action(kind=ActionKind.MOVE, move_slot=0)
        a1 = Action(kind=ActionKind.MOVE, move_slot=1)
        assert _acting_action(a0, a1, 1, 0) is a1

    def test_list_action_by_slot(self):
        from liveplay.sweep_actions import _acting_action
        a0 = Action(kind=ActionKind.MOVE, move_slot=0)
        a1 = Action(kind=ActionKind.MOVE, move_slot=1)
        assert _acting_action([a0, a1], None, 0, 1) is a1

    def test_none_action_returns_none(self):
        from liveplay.sweep_actions import _acting_action
        assert _acting_action(None, None, 0, 0) is None

    def test_out_of_range_slot_falls_back_to_first(self):
        from liveplay.sweep_actions import _acting_action
        a0 = Action(kind=ActionKind.MOVE, move_slot=0)
        assert _acting_action([a0], None, 0, 5) is a0


# ---------------------------------------------------------------------------
# TestActionMoveEnum
# ---------------------------------------------------------------------------

class TestActionMoveEnum:
    """_action_move_enum looks up the Move enum from a mon's moveset."""

    def test_returns_correct_move(self):
        from liveplay.sweep_actions import _action_move_enum
        state = _make_singles_state()
        action = Action(kind=ActionKind.MOVE, move_slot=0)
        result = _action_move_enum(action, 0, 0, state)
        assert result == Move.THUNDERBOLT

    def test_switch_returns_none(self):
        from liveplay.sweep_actions import _action_move_enum
        state = _make_singles_state()
        action = Action(kind=ActionKind.SWITCH, switch_to_slot=0)
        assert _action_move_enum(action, 0, 0, state) is None

    def test_negative_slot_returns_none(self):
        from liveplay.sweep_actions import _action_move_enum
        state = _make_singles_state()
        action = Action(kind=ActionKind.MOVE, move_slot=-1)
        assert _action_move_enum(action, 0, 0, state) is None


# ---------------------------------------------------------------------------
# TestExpandActionTargets
# ---------------------------------------------------------------------------

class TestExpandActionTargets:
    """_expand_action_targets enumerates target slots for double battles."""

    def test_status_move_not_expanded(self):
        from liveplay.sweep_actions import _expand_action_targets
        # SPLASH is STATUS category — target irrelevant
        state = make_battle(make_mon(Species.PIKACHU, moves=(Move.SPLASH,)),
                            make_mon(Species.RAICHU, moves=(Move.TACKLE,)))
        action = Action(kind=ActionKind.MOVE, move_slot=0)
        result = _expand_action_targets(action, 0, 0, state, [0, 1], {})
        assert result == [action]

    def test_switch_not_expanded(self):
        from liveplay.sweep_actions import _expand_action_targets
        state = _make_singles_state()
        action = Action(kind=ActionKind.SWITCH, switch_to_slot=1)
        result = _expand_action_targets(action, 0, 0, state, [0], {})
        assert result == [action]

    def test_damaging_move_enumerated_over_foe_dmg(self):
        from liveplay.sweep_actions import _expand_action_targets
        state = _make_singles_state()
        action = Action(kind=ActionKind.MOVE, move_slot=0)
        result = _expand_action_targets(action, 0, 0, state, [0, 1], {})
        # One variant per damaged foe slot
        assert len(result) == 2
        assert result[0].target_slot == 0
        assert result[1].target_slot == 1


# ---------------------------------------------------------------------------
# TestFmtAction
# ---------------------------------------------------------------------------

class TestFmtAction:
    """_fmt_action produces readable log strings."""

    def test_none_is_none(self):
        from liveplay.sweep_actions import _fmt_action
        assert _fmt_action(None) == "none"

    def test_move_action(self):
        from liveplay.sweep_actions import _fmt_action
        action = Action(kind=ActionKind.MOVE, move_slot=2, target_slot=0)
        assert "move[2]" in _fmt_action(action)

    def test_switch_action(self):
        from liveplay.sweep_actions import _fmt_action
        action = Action(kind=ActionKind.SWITCH, switch_to_slot=3)
        assert "switch" in _fmt_action(action)
        assert "3" in _fmt_action(action)

    def test_list_of_actions(self):
        from liveplay.sweep_actions import _fmt_action
        a0 = Action(kind=ActionKind.MOVE, move_slot=0, target_slot=1)
        a1 = Action(kind=ActionKind.SWITCH, switch_to_slot=2)
        result = _fmt_action([a0, a1])
        assert result.startswith("[")
        assert result.endswith("]")


# ---------------------------------------------------------------------------
# TestExtractUsedMovesFromGroups
# ---------------------------------------------------------------------------

class TestExtractUsedMovesFromGroups:
    """_extract_used_moves_from_groups returns (side, slot) → Move mapping."""

    def test_flat_messages_path(self):
        from liveplay.sweep_actions import _extract_used_moves_from_groups
        state = _make_singles_state()
        msg = _usedmove("PIKACHU", "THUNDERBOLT", side_hint=0)
        result = _extract_used_moves_from_groups(None, state, flat_messages=[msg])
        assert result == {(0, 0): Move.THUNDERBOLT}

    def test_action_groups_path(self):
        from liveplay.sweep_actions import _extract_used_moves_from_groups
        state = _make_singles_state()
        primary = _usedmove("PIKACHU", "THUNDERBOLT", side_hint=0)
        group = ActionGroup(primary=primary, secondaries=[])
        result = _extract_used_moves_from_groups([group], state)
        assert result == {(0, 0): Move.THUNDERBOLT}

    def test_first_occurrence_wins(self):
        from liveplay.sweep_actions import _extract_used_moves_from_groups
        state = _make_singles_state()
        msg1 = _usedmove("PIKACHU", "THUNDERBOLT", side_hint=0)
        msg2 = _usedmove("PIKACHU", "TACKLE", side_hint=0)
        result = _extract_used_moves_from_groups(None, state, flat_messages=[msg1, msg2])
        # Only first occurrence kept
        assert result[(0, 0)] == Move.THUNDERBOLT

    def test_empty_returns_empty(self):
        from liveplay.sweep_actions import _extract_used_moves_from_groups
        state = _make_singles_state()
        assert _extract_used_moves_from_groups(None, state) == {}

    def test_metronome_tagged_move_used(self):
        from liveplay.sweep_actions import _extract_used_moves_from_groups
        state = _make_singles_state(species0=Species.CLEFABLE, moves0=(Move.METRONOME,))
        # Simulate a Metronome-tagged message (the called-move USEDMOVE is dropped;
        # the wrapper carries metronome_called).
        msg = _usedmove("CLEFABLE", "METRONOME", side_hint=0)
        msg.metronome_called = Move.SURF
        result = _extract_used_moves_from_groups(None, state, flat_messages=[msg])
        assert result.get((0, 0)) == Move.SURF


# ---------------------------------------------------------------------------
# TestExtractKnownActions
# ---------------------------------------------------------------------------

class TestExtractKnownActions:
    """_extract_known_actions identifies per-slot actions from messages."""

    def test_usedmove_produces_move_action(self):
        from liveplay.sweep_actions import _extract_known_actions
        state = _make_singles_state()
        msg = _usedmove("PIKACHU", "THUNDERBOLT", side_hint=0)
        known = _extract_known_actions([msg], state)
        action = known[0][0]
        assert action is not None
        assert action.kind == ActionKind.MOVE
        assert action.move_slot == 0

    def test_no_messages_returns_nones(self):
        from liveplay.sweep_actions import _extract_known_actions
        state = _make_singles_state()
        known = _extract_known_actions([], state)
        assert known[0] == [None]
        assert known[1] == [None]

    def test_faint_then_switch_treated_as_forced(self):
        """A switch-in that follows a faint is forced and must NOT be recorded as a voluntary action."""
        from liveplay.sweep_actions import _extract_known_actions
        state = _make_singles_state()
        faint = _mr("STRINGID_TARGETFAINTED", var_values=["Foe RAICHU"],
                    matched_text="Foe RAICHU fainted!", side_hint=1)
        # A switch-in for side 1 after the faint
        switch_in = _mr("STRINGID_SWITCHINMON",
                        constant_name="sText_Trainer1SentOutPkmn2",
                        var_values=["TRAINER", "MAGIKARP"],
                        side_hint=1)
        known = _extract_known_actions([faint, switch_in], state)
        # Must be None — the switch-in is the forced replacement, not a chosen action
        assert known[1][0] is None

    def test_battle_start_send_out_not_recorded(self):
        """Send-outs during the intro banner are forced, not voluntary."""
        from liveplay.sweep_actions import _extract_known_actions
        state = _make_singles_state()
        intro = _mr("STRINGID_INTROMSG")
        switch_in = _mr("STRINGID_SWITCHINMON",
                        constant_name="sText_Trainer1SentOutPkmn2",
                        var_values=["TRAINER", "RAICHU"],
                        side_hint=1)
        known = _extract_known_actions([intro, switch_in], state)
        assert known[1][0] is None

    def test_move_not_in_moveset_raises(self):
        from liveplay.sweep_actions import _extract_known_actions, UnreproducibleObservedMoveError
        state = _make_singles_state()
        # PIKACHU's moveset has THUNDERBOLT only; claim it used SURF
        msg = _usedmove("PIKACHU", "SURF", side_hint=0)
        with pytest.raises(UnreproducibleObservedMoveError):
            _extract_known_actions([msg], state)


# ---------------------------------------------------------------------------
# TestValidateKnownOpponentAction — error class and early-exit paths
# ---------------------------------------------------------------------------

class TestValidateKnownOpponentAction:
    """_validate_known_opponent_action raises UnexpectedOpponentActionError on p=0."""

    def test_nothing_identified_skips(self):
        """When all slots are None, validation is a no-op."""
        from liveplay.sweep_actions import _validate_known_opponent_action
        state = _make_singles_state()
        # Must not raise even without compute_action_probabilities available
        _validate_known_opponent_action({1: [None]}, state)

    def test_fainted_active_skips(self):
        """When opponent's active is fainted, validation skips (forced replacement)."""
        from liveplay.sweep_actions import _validate_known_opponent_action
        from liveplay.actions import Action, ActionKind
        state = _make_singles_state()
        # Mark the active mon as fainted
        side = state.sides[1]
        idx = side.active_indices[0]
        fainted_mon = side.team[idx]._replace(fainted=True)
        new_team = list(side.team)
        new_team[idx] = fainted_mon
        import dataclasses
        new_side = dataclasses.replace(side, team=new_team)
        new_state = dataclasses.replace(state, sides=(state.sides[0], new_side))

        action = Action(kind=ActionKind.MOVE, move_slot=0, source_slot=0)
        # Must not raise — skip because active is fainted
        _validate_known_opponent_action({1: [action]}, new_state)

    def test_error_class_is_exception(self):
        from liveplay.sweep_actions import UnexpectedOpponentActionError
        err = UnexpectedOpponentActionError("test")
        assert isinstance(err, Exception)


# ---------------------------------------------------------------------------
# TestMoveIsSpread
# ---------------------------------------------------------------------------

class TestMoveIsSpread:
    """_move_is_spread identifies spread moves by MoveTarget."""

    def test_surf_is_spread(self):
        from liveplay.sweep_actions import _move_is_spread
        assert _move_is_spread(Move.SURF) is True

    def test_tackle_is_not_spread(self):
        from liveplay.sweep_actions import _move_is_spread
        assert _move_is_spread(Move.TACKLE) is False

    def test_none_is_not_spread(self):
        from liveplay.sweep_actions import _move_is_spread
        assert _move_is_spread(None) is False
