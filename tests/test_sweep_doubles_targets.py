"""Tests for doubles target inference, per-slot known actions, and spread detection.

LEDGER
======
PORTED:
  TestMoveIsSpread                    — _move_is_spread for spread/single/None moves
  TestMessageHitCountsWithState       — singles hit count parsing
  TestFoeDamagedSlots                 — _foe_damaged_slots slot assignment
  TestExtractKnownActionsSingles      — singles _extract_known_actions shape + forced replacement
  TestExtractKnownActionsDoubles      — doubles per-slot known actions
  TestSweepResolveCandidateActions    — singles/doubles candidate shape + target enumeration
  TestSpreadMoveHandling              — spread fixes target_slot=0; spread+multihit raises
  TestSinglesEndToEndSmoke            — end-to-end singles sweep after doubles refactor

DROPPED:
  Inline import from tests.test_simulation_runner — no NEW analog; _make_candidate
    is inlined as Candidate(state=state) directly.

ALREADY-COVERED: none
FAILED-NEEDS-REVIEW: none

API MAPPING:
  OLD src.simulation_runner._extract_known_actions → liveplay.sweep_actions._extract_known_actions
  OLD src.simulation_runner._foe_damaged_slots → liveplay.sweep_actions._foe_damaged_slots
  OLD src.simulation_runner._move_is_spread → liveplay.sweep_common._move_is_spread
  OLD src.simulation_runner._sweep_resolve_candidate_actions → liveplay.sweep_actions
  OLD src.simulation_runner._message_hit_counts_with_state → liveplay.sweep_actions
  OLD src.simulation_runner._message_action_order_with_state → liveplay.sweep_actions
  OLD src.simulation_runner.run_candidate_sweep → liveplay.sweep_run.run_candidate_sweep
  OLD src.simulation_runner.SimulationError → liveplay.engine_select.SimulationError
"""
import pytest

from liveplay.actions import Action, ActionKind
from liveplay.battle_types import MatchResult
from liveplay.candidate import Candidate
from liveplay.data.moves import Move, MOVE_DATA, MoveCategory, MoveTarget
from liveplay.data.species import Species
from liveplay.engine_select import SimulationError
from liveplay.sweep_actions import (
    _extract_known_actions,
    _foe_damaged_slots,
    _message_action_order_with_state,
    _message_hit_counts_with_state,
    _sweep_resolve_candidate_actions,
)
from liveplay.sweep_common import _move_is_spread
from liveplay.sweep_run import run_candidate_sweep
from tests.state_builders import (
    dslot, make_battle, make_doubles_battle, make_mon, odelta, slot,
)


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------

_AUTO_SIDE_HINT = object()  # sentinel: derive side_hint from the Foe prefix


def _foe_prefix_hint(var_values):
    if not var_values:
        return None
    first = str(var_values[0]).split()
    if not first:
        return None
    return 1 if first[0].lower() == "foe" else 0


def _strip_foe(var_values):
    if not var_values:
        return var_values
    out = list(var_values)
    words = str(out[0]).split()
    if words and words[0].lower() == "foe":
        out[0] = " ".join(words[1:])
    return out


def _mr(string_id, *, constant_name="", var_values=None, matched_text="",
        side_hint=_AUTO_SIDE_HINT):
    vals = var_values or []
    if side_hint is _AUTO_SIDE_HINT:
        side_hint = _foe_prefix_hint(vals)
    return MatchResult(
        string_id=string_id, id_value=0, constant_name=constant_name,
        var_values=_strip_foe(vals), score=0, matched_text=matched_text, slot_labels=[],
        side_hint=side_hint,
    )


def usedmove(attacker, move):
    return _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
               var_values=[attacker, move])


def hitxtimes(n):
    return _mr("STRINGID_HITXTIMES", var_values=[str(n)])


def _faint(name, *, foe=False):
    sid = "STRINGID_TARGETFAINTED" if foe else "STRINGID_ATTACKERFAINTED"
    return _mr(sid, var_values=[name])


def _opp_switch_in(name):
    return _mr("STRINGID_SWITCHINMON", constant_name="sText_OppSendOut",
               var_values=["Trainer", name])


def _player_switch_in(name):
    return _mr("STRINGID_PLAYER_SWITCHINMON", constant_name="sText_PlayerSendOut",
               var_values=[name])


# ---------------------------------------------------------------------------
# 1. _move_is_spread
# ---------------------------------------------------------------------------

class TestMoveIsSpread:
    def test_spread_move_all_adjacent_foes(self):
        """RAZOR_WIND targets ALL_ADJACENT_FOES (value 2) → spread."""
        assert _move_is_spread(Move.RAZOR_WIND) is True

    def test_single_target_move(self):
        """PECK targets NORMAL (value 0) → not spread."""
        assert _move_is_spread(Move.PECK) is False

    def test_tackle_not_spread(self):
        assert _move_is_spread(Move.TACKLE) is False

    def test_none_returns_false(self):
        assert _move_is_spread(None) is False

    def test_unknown_move_returns_false(self):
        """A move enum with MoveTarget.SELF → not spread."""
        assert _move_is_spread(Move.NONE) is False

    def test_spread_targets_values(self):
        """Verify the spread targets set covers values 2, 3, 8."""
        spread_targets = {MoveTarget.ALL_ADJACENT_FOES, MoveTarget.ALL_ADJACENT, MoveTarget.ALL}
        assert {t.value for t in spread_targets} == {2, 3, 8}


# ---------------------------------------------------------------------------
# 2. _message_hit_counts_with_state
# ---------------------------------------------------------------------------

class TestMessageHitCountsWithState:
    def _make_singles_state(self):
        p = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)
        o = make_mon(Species.POOCHYENA, moves=(Move.TACKLE,), level=5)
        return make_battle(p, o)

    def test_singles_two_movers_no_hitxtimes(self):
        """Two movers with no HITXTIMES → [1, 1]."""
        state = self._make_singles_state()
        messages = [
            usedmove("ROOKIDEE", "Peck"),
            usedmove("Foe POOCHYENA", "Tackle"),
        ]
        counts = _message_hit_counts_with_state(messages, state)
        assert counts == [1, 1]

    def test_hitxtimes_after_first_mover(self):
        """HITXTIMES=3 after first mover's USEDMOVE → first gets 3, second gets 1."""
        state = self._make_singles_state()
        messages = [
            usedmove("ROOKIDEE", "Peck"),
            hitxtimes(3),
            usedmove("Foe POOCHYENA", "Tackle"),
        ]
        counts = _message_hit_counts_with_state(messages, state)
        assert counts == [3, 1]

    def test_index_aligned_with_action_order(self):
        """Hit counts list has same length as _message_action_order_with_state result."""
        state = self._make_singles_state()
        messages = [
            usedmove("ROOKIDEE", "Peck"),
            usedmove("Foe POOCHYENA", "Tackle"),
        ]
        order = _message_action_order_with_state(messages, state)
        counts = _message_hit_counts_with_state(messages, state)
        assert len(counts) == len(order)

    def test_hitxtimes_after_second_mover(self):
        """HITXTIMES=4 after second mover → second gets 4, first gets 1."""
        state = self._make_singles_state()
        messages = [
            usedmove("ROOKIDEE", "Peck"),
            usedmove("Foe POOCHYENA", "Tackle"),
            hitxtimes(4),
        ]
        counts = _message_hit_counts_with_state(messages, state)
        assert counts == [1, 4]

    def test_no_movers(self):
        """No resolved USEDMOVEs → empty list."""
        state = self._make_singles_state()
        counts = _message_hit_counts_with_state([], state)
        assert counts == []


# ---------------------------------------------------------------------------
# 3. _foe_damaged_slots
# ---------------------------------------------------------------------------

class TestFoeDamagedSlots:
    def test_slot0_damaged_slot1_unchanged(self):
        """Slot0 lost HP (40→30), slot1 unchanged (48→48) → [0]."""
        deltas = [[(48, 40), (40, 30)], [(48, 48)]]
        assert _foe_damaged_slots(deltas) == [0]

    def test_both_slots_damaged(self):
        """Both slots lost HP → [0, 1]."""
        deltas = [[(48, 30)], [(48, 20)]]
        assert _foe_damaged_slots(deltas) == [0, 1]

    def test_empty_slots(self):
        """No HP data in either slot → []."""
        assert _foe_damaged_slots([[], []]) == []

    def test_slot0_empty_slot1_unchanged(self):
        """Slot0 no data, slot1 unchanged → []."""
        deltas = [[], [(48, 48)]]
        assert _foe_damaged_slots(deltas) == []

    def test_slot_gained_hp_not_counted(self):
        """A slot that gained HP (e.g. recovery) is not damaged."""
        deltas = [[(30, 45)], [(48, 20)]]
        assert _foe_damaged_slots(deltas) == [1]

    def test_single_slot_damaged(self):
        """Singles-like input: one slot with damage → [0]."""
        deltas = [[(48, 30)]]
        assert _foe_damaged_slots(deltas) == [0]

    def test_single_slot_undamaged(self):
        """Singles-like input: one slot no change → []."""
        deltas = [[(48, 48)]]
        assert _foe_damaged_slots(deltas) == []


# ---------------------------------------------------------------------------
# 4. _extract_known_actions singles: per-slot length-1 lists
# ---------------------------------------------------------------------------

class TestExtractKnownActionsSingles:
    def test_singles_returns_length1_lists(self):
        """Singles: result[0] and result[1] are length-1 lists."""
        p = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)
        o = make_mon(Species.POOCHYENA, moves=(Move.TACKLE,), level=5)
        state = make_battle(p, o)
        messages = [
            usedmove("ROOKIDEE", "Peck"),
            usedmove("Foe POOCHYENA", "Tackle"),
        ]
        known = _extract_known_actions(messages, state)
        assert isinstance(known[0], list) and len(known[0]) == 1
        assert isinstance(known[1], list) and len(known[1]) == 1

    def test_singles_move_action_source_slot_0(self):
        """Singles USEDMOVE → Action with source_slot=0 and correct move_slot."""
        p = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)
        o = make_mon(Species.POOCHYENA, moves=(Move.TACKLE,), level=5)
        state = make_battle(p, o)
        messages = [usedmove("ROOKIDEE", "Peck")]
        known = _extract_known_actions(messages, state)
        action = known[0][0]
        assert action is not None
        assert action.kind == ActionKind.MOVE
        assert action.move_slot == 0  # PECK is move slot 0
        assert action.source_slot == 0

    def test_singles_no_message_yields_none(self):
        """Side with no USEDMOVE → None in their slot list."""
        p = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)
        o = make_mon(Species.POOCHYENA, moves=(Move.TACKLE,), level=5)
        state = make_battle(p, o)
        messages = [usedmove("ROOKIDEE", "Peck")]
        known = _extract_known_actions(messages, state)
        assert known[1][0] is None

    def test_singles_forced_replacement_not_action(self):
        """Faint + opp send-out in same batch → opp slot has None (forced replacement)."""
        p = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
        o1 = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5, hp=1)
        o2 = make_mon(Species.LILLIPUP, moves=(Move.TACKLE,), level=5)
        state = make_battle(p, o1, team1=[o1, o2])
        messages = (
            [usedmove("CHARIZARD", "Tackle")]
            + [_faint("POOCHYENA", foe=True)]
            + [_opp_switch_in("Lillipup")]
        )
        known = _extract_known_actions(messages, state)
        # Forced replacement → opp slot is None
        assert known[1][0] is None
        assert known[0][0] is not None


# ---------------------------------------------------------------------------
# 5. _extract_known_actions doubles: two player USEDMOVEs from slot0 and slot1
# ---------------------------------------------------------------------------

class TestExtractKnownActionsDoubles:
    def test_doubles_two_player_moves(self):
        """Doubles: ROOKIDEE (slot0) + PIDGEY (slot1) → result[0] is length-2 with both set."""
        p0 = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)
        p1 = make_mon(Species.PIDGEY, moves=(Move.GUST,), level=5)
        o0 = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
        o1 = make_mon(Species.LILLIPUP, moves=(Move.SPLASH,), level=5)
        state = make_doubles_battle(p0, p1, o0, o1)
        messages = [
            usedmove("ROOKIDEE", "Peck"),
            usedmove("PIDGEY", "Gust"),
            usedmove("Foe POOCHYENA", "Splash"),
            usedmove("Foe LILLIPUP", "Splash"),
        ]
        known = _extract_known_actions(messages, state)
        assert isinstance(known[0], list) and len(known[0]) == 2
        assert isinstance(known[1], list) and len(known[1]) == 2

    def test_doubles_player_slot0_has_source_slot_0(self):
        """ROOKIDEE is slot0 → its action has source_slot=0."""
        p0 = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)
        p1 = make_mon(Species.PIDGEY, moves=(Move.GUST,), level=5)
        o0 = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
        o1 = make_mon(Species.LILLIPUP, moves=(Move.SPLASH,), level=5)
        state = make_doubles_battle(p0, p1, o0, o1)
        messages = [
            usedmove("ROOKIDEE", "Peck"),
            usedmove("PIDGEY", "Gust"),
        ]
        known = _extract_known_actions(messages, state)
        action_slot0 = known[0][0]
        assert action_slot0 is not None
        assert action_slot0.source_slot == 0
        assert action_slot0.move_slot == 0  # Peck

    def test_doubles_player_slot1_has_source_slot_1(self):
        """PIDGEY is slot1 → its action has source_slot=1."""
        p0 = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)
        p1 = make_mon(Species.PIDGEY, moves=(Move.GUST,), level=5)
        o0 = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
        o1 = make_mon(Species.LILLIPUP, moves=(Move.SPLASH,), level=5)
        state = make_doubles_battle(p0, p1, o0, o1)
        messages = [
            usedmove("ROOKIDEE", "Peck"),
            usedmove("PIDGEY", "Gust"),
        ]
        known = _extract_known_actions(messages, state)
        action_slot1 = known[0][1]
        assert action_slot1 is not None
        assert action_slot1.source_slot == 1
        assert action_slot1.move_slot == 0  # Gust


# ---------------------------------------------------------------------------
# 6. Target enumeration: doubles vs singles candidate shape
# ---------------------------------------------------------------------------

class TestSweepResolveCandidateActions:
    def _doubles_state(self):
        p0 = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)
        p1 = make_mon(Species.PIDGEY, moves=(Move.GUST,), level=5)
        o0 = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
        o1 = make_mon(Species.LILLIPUP, moves=(Move.SPLASH,), level=5)
        return make_doubles_battle(p0, p1, o0, o1), p0, p1, o0, o1

    def _singles_state(self):
        p = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)
        o = make_mon(Species.POOCHYENA, moves=(Move.TACKLE,), level=5)
        return make_battle(p, o)

    def test_singles_yields_bare_actions(self):
        """Singles side always yields bare Action instances, not lists."""
        state = self._singles_state()
        messages = [
            usedmove("ROOKIDEE", "Peck"),
            usedmove("Foe POOCHYENA", "Tackle"),
        ]
        known = _extract_known_actions(messages, state)
        foe_deltas = [[(48, 30)]]
        player_deltas = [[]]
        candidates0, candidates1 = _sweep_resolve_candidate_actions(
            state, messages, known,
            opponent_hp_deltas=foe_deltas,
            player_hp_deltas=player_deltas,
        )
        for cand in candidates0:
            assert isinstance(cand, Action), f"Expected bare Action, got {type(cand)}"
        for cand in candidates1:
            assert isinstance(cand, Action), f"Expected bare Action, got {type(cand)}"

    def test_doubles_yields_action_lists(self):
        """Doubles side yields list[Action] of length 2 for each candidate."""
        state, *_ = self._doubles_state()
        messages = [
            usedmove("ROOKIDEE", "Peck"),
            usedmove("PIDGEY", "Gust"),
            usedmove("Foe POOCHYENA", "Splash"),
            usedmove("Foe LILLIPUP", "Splash"),
        ]
        known = _extract_known_actions(messages, state)
        foe_deltas = [[(48, 30)], [(48, 48)]]
        player_deltas = [[], []]
        candidates0, candidates1 = _sweep_resolve_candidate_actions(
            state, messages, known,
            opponent_hp_deltas=foe_deltas,
            player_hp_deltas=player_deltas,
        )
        for cand in candidates0:
            assert isinstance(cand, list) and len(cand) == 2, (
                f"Expected list[Action] of length 2, got {type(cand)}: {cand}"
            )

    def test_doubles_target_enumeration_over_damaged_slots(self):
        """Both foe slots damaged → candidate set contains target assignments for both."""
        state, *_ = self._doubles_state()
        messages = [
            usedmove("ROOKIDEE", "Peck"),
            usedmove("PIDGEY", "Gust"),
            usedmove("Foe POOCHYENA", "Splash"),
            usedmove("Foe LILLIPUP", "Splash"),
        ]
        known = _extract_known_actions(messages, state)
        foe_deltas = [[(48, 30)], [(48, 20)]]
        player_deltas = [[], []]
        candidates0, _c1 = _sweep_resolve_candidate_actions(
            state, messages, known,
            opponent_hp_deltas=foe_deltas,
            player_hp_deltas=player_deltas,
        )
        target_slot0_seen = any(c[0].target_slot == 0 for c in candidates0)
        target_slot1_seen = any(c[0].target_slot == 1 for c in candidates0)
        assert target_slot0_seen, "Expected some candidate with slot0 target for first mover"
        assert target_slot1_seen, "Expected some candidate with slot1 target for first mover"

    def test_doubles_no_damage_defaults_to_slot0(self):
        """No foe HP change → target_slot=0 by default."""
        state, *_ = self._doubles_state()
        messages = [
            usedmove("ROOKIDEE", "Peck"),
            usedmove("PIDGEY", "Gust"),
            usedmove("Foe POOCHYENA", "Splash"),
            usedmove("Foe LILLIPUP", "Splash"),
        ]
        known = _extract_known_actions(messages, state)
        foe_deltas = [[], []]
        player_deltas = [[], []]
        candidates0, _c1 = _sweep_resolve_candidate_actions(
            state, messages, known,
            opponent_hp_deltas=foe_deltas,
            player_hp_deltas=player_deltas,
        )
        for cand in candidates0:
            assert cand[0].target_slot == 0


# ---------------------------------------------------------------------------
# 7. Spread+multi-hit raises SimulationError; spread alone fixes target_slot=0
# ---------------------------------------------------------------------------

class TestSpreadMoveHandling:
    def _spread_state(self):
        # RAZOR_WIND targets ALL_ADJACENT_FOES (spread)
        p0 = make_mon(Species.CHARIZARD, moves=(Move.RAZOR_WIND,), level=50)
        p1 = make_mon(Species.PIDGEY, moves=(Move.GUST,), level=5)
        o0 = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
        o1 = make_mon(Species.LILLIPUP, moves=(Move.SPLASH,), level=5)
        return make_doubles_battle(p0, p1, o0, o1)

    def test_spread_move_fixes_target_slot_0(self):
        """A known spread move action gets target_slot=0, not enumerated."""
        state = self._spread_state()
        messages = [
            usedmove("CHARIZARD", "Razor Wind"),
            usedmove("Foe POOCHYENA", "Splash"),
            usedmove("Foe LILLIPUP", "Splash"),
        ]
        known = _extract_known_actions(messages, state)
        foe_deltas = [[(48, 30)], [(48, 20)]]
        player_deltas = [[], []]
        candidates0, _c1 = _sweep_resolve_candidate_actions(
            state, messages, known,
            opponent_hp_deltas=foe_deltas,
            player_hp_deltas=player_deltas,
        )
        for cand in candidates0:
            assert cand[0].target_slot == 0, (
                f"Spread move should fix target_slot=0, got {cand[0].target_slot}"
            )

    def test_spread_plus_multihit_raises(self):
        """Spread move + HITXTIMES → SimulationError (unsupported combination)."""
        state = self._spread_state()
        messages = [
            usedmove("CHARIZARD", "Razor Wind"),
            hitxtimes(3),
            usedmove("Foe POOCHYENA", "Splash"),
        ]
        known = _extract_known_actions(messages, state)
        foe_deltas = [[(48, 30)], [(48, 20)]]
        player_deltas = [[], []]
        with pytest.raises(SimulationError):
            _sweep_resolve_candidate_actions(
                state, messages, known,
                opponent_hp_deltas=foe_deltas,
                player_hp_deltas=player_deltas,
            )


# ---------------------------------------------------------------------------
# 8. Singles end-to-end smoke test: run_candidate_sweep unchanged
# ---------------------------------------------------------------------------

class TestSinglesEndToEndSmoke:
    def test_singles_sweep_survives(self):
        """Singles sweep still produces candidates after doubles-related changes.

        Charizard (lv50) Tackle vs Bulbasaur (lv50) yields HP ~92-97 (k=36-38 out of 48).
        Using k_after=38 passes with lowest-damage rolls.
        """
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=50)
        state = make_battle(charizard, bulbasaur)

        messages = [
            usedmove("CHARIZARD", "Tackle"),
            usedmove("Foe BULBASAUR", "Splash"),
        ]

        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(bulbasaur.species, (48, 38), max_hp=bulbasaur.max_hp)],
            initial_candidates=[Candidate(state=state)],
        )
        assert len(candidates) >= 1
