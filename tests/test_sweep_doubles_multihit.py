"""Tests for per-mover multi-hit support in doubles sweep.

LEDGER
======
PORTED:
  TestActingAction                  — _acting_action singles/doubles/None/out-of-range cases
  TestPerMoverHitCountsDoubles      — _message_hit_counts_with_state in a doubles state
  TestSinglesMultiHitRegression     — singles Dual Wingbeat still finds candidates
  TestDoublesOneMultiHitMover       — doubles slot0 2-hit Dual Wingbeat vs Blissey
  TestDoublesDoubleMultiHit         — two multi-hit movers one per side same turn

DROPPED:
  _make_candidate import from test_simulation_runner — the helper is just Candidate(state=state),
    inlined directly here to avoid cross-test imports.

ALREADY-COVERED: none
FAILED-NEEDS-REVIEW: none

API MAPPING:
  OLD _acting_action from src.simulation_runner → liveplay.sweep_actions._acting_action
  OLD _message_hit_counts_with_state from src.simulation_runner → liveplay.sweep_actions
  OLD _message_action_order_with_state → liveplay.sweep_actions
  OLD run_candidate_sweep from src.simulation_runner → liveplay.sweep_run
"""
from liveplay.actions import Action, ActionKind
from liveplay.battle_types import MatchResult
from liveplay.candidate import Candidate
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.engine_select import SimulationError
from liveplay.sweep_actions import (
    _acting_action,
    _message_action_order_with_state,
    _message_hit_counts_with_state,
)
from liveplay.sweep_run import run_candidate_sweep
from tests.state_builders import (
    make_battle, make_doubles_battle, make_mon, odelta, pdelta,
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


def usedmove(attacker, move, *, foe=False):
    prefix = "Foe " if foe else ""
    return _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
               var_values=[f"{prefix}{attacker}", move],
               matched_text=f"{prefix}{attacker} used {move}!")


def hitxtimes(n):
    return _mr("STRINGID_HITXTIMES", var_values=[str(n)])


def _make_candidate(state):
    return Candidate(state=state)


# ---------------------------------------------------------------------------
# 1. _acting_action
# ---------------------------------------------------------------------------

class TestActingAction:
    def _make_action(self, move_slot=0, target_slot=0, source_slot=0):
        return Action(kind=ActionKind.MOVE, move_slot=move_slot,
                      target_slot=target_slot, source_slot=source_slot)

    def test_singles_bare_action_side0(self):
        """Singles: bare Action for side 0 → returned as-is."""
        a0 = self._make_action(move_slot=1)
        a1 = self._make_action(move_slot=2)
        result = _acting_action(a0, a1, mover_side=0, source_slot=0)
        assert result is a0

    def test_singles_bare_action_side1(self):
        """Singles: bare Action for side 1 → returned as-is."""
        a0 = self._make_action(move_slot=1)
        a1 = self._make_action(move_slot=2)
        result = _acting_action(a0, a1, mover_side=1, source_slot=0)
        assert result is a1

    def test_doubles_list_side0_slot0(self):
        """Doubles: list for side 0, source_slot=0 → act[0]."""
        a0_list = [self._make_action(move_slot=0), self._make_action(move_slot=1)]
        a1 = self._make_action(move_slot=0)
        result = _acting_action(a0_list, a1, mover_side=0, source_slot=0)
        assert result is a0_list[0]

    def test_doubles_list_side0_slot1(self):
        """Doubles: list for side 0, source_slot=1 → act[1]."""
        a0_list = [self._make_action(move_slot=0), self._make_action(move_slot=1)]
        a1 = self._make_action(move_slot=0)
        result = _acting_action(a0_list, a1, mover_side=0, source_slot=1)
        assert result is a0_list[1]

    def test_doubles_list_out_of_range_returns_slot0(self):
        """Doubles: source_slot out of range → act[0] fallback."""
        a0_list = [self._make_action(move_slot=5)]
        a1 = self._make_action(move_slot=0)
        result = _acting_action(a0_list, a1, mover_side=0, source_slot=99)
        assert result is a0_list[0]

    def test_none_action_returns_none(self):
        """None action → None returned."""
        result = _acting_action(None, None, mover_side=0, source_slot=0)
        assert result is None

    def test_doubles_list_side1(self):
        """Doubles: list for side 1, source_slot=1 → a1[1]."""
        a0 = self._make_action(move_slot=0)
        a1_list = [self._make_action(move_slot=2), self._make_action(move_slot=3)]
        result = _acting_action(a0, a1_list, mover_side=1, source_slot=1)
        assert result is a1_list[1]


# ---------------------------------------------------------------------------
# 2. Per-mover hit counts aligned with action order (doubles state)
# ---------------------------------------------------------------------------

class TestPerMoverHitCountsDoubles:
    def _doubles_state(self):
        p0 = make_mon(Species.ROOKIDEE, moves=(Move.FURY_ATTACK,), level=5)
        p1 = make_mon(Species.PIDGEY, moves=(Move.GUST,), level=5)
        o0 = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
        o1 = make_mon(Species.LILLIPUP, moves=(Move.SPLASH,), level=5)
        return make_doubles_battle(p0, p1, o0, o1)

    def test_first_mover_multihit(self):
        """HITXTIMES=3 after first mover → [3, 1, 1, 1] aligned with 4 movers."""
        state = self._doubles_state()
        messages = [
            usedmove("ROOKIDEE", "Fury Attack"),
            hitxtimes(3),
            usedmove("PIDGEY", "Gust"),
            usedmove("POOCHYENA", "Splash", foe=True),
            usedmove("LILLIPUP", "Splash", foe=True),
        ]
        order = _message_action_order_with_state(messages, state)
        counts = _message_hit_counts_with_state(messages, state)
        assert len(counts) == len(order), f"counts={counts} order={order}"
        assert counts[0] == 3
        assert counts[1] == 1
        assert counts[2] == 1
        assert counts[3] == 1

    def test_second_mover_multihit(self):
        """HITXTIMES=2 after second mover → [1, 2, 1, 1]."""
        state = self._doubles_state()
        messages = [
            usedmove("ROOKIDEE", "Fury Attack"),
            usedmove("PIDGEY", "Gust"),
            hitxtimes(2),
            usedmove("POOCHYENA", "Splash", foe=True),
            usedmove("LILLIPUP", "Splash", foe=True),
        ]
        order = _message_action_order_with_state(messages, state)
        counts = _message_hit_counts_with_state(messages, state)
        assert len(counts) == len(order)
        assert counts[0] == 1
        assert counts[1] == 2
        assert counts[2] == 1
        assert counts[3] == 1


# ---------------------------------------------------------------------------
# 3. SINGLES multi-hit regression via run_candidate_sweep
# ---------------------------------------------------------------------------

class TestSinglesMultiHitRegression:
    """Stage E must not regress singles multi-hit sweep path."""

    def _make_state(self):
        dragonite = make_mon(Species.DRAGONITE, moves=(Move.DUAL_WINGBEAT,))
        blissey = make_mon(Species.BLISSEY, moves=(Move.SPLASH,))
        return make_battle(dragonite, blissey), dragonite, blissey

    def test_singles_two_hit_still_finds_candidates(self):
        """Dual Wingbeat (2 hits) in singles must return ≥1 candidate."""
        state, dragonite, blissey = self._make_state()
        messages = [
            usedmove("Dragonite", "Dual Wingbeat"),
            hitxtimes(2),
            usedmove("Blissey", "Splash", foe=True),
        ]
        # HP deltas for Blissey: k=29 then k=11 out of 48
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(blissey.species, (48, 29), (29, 11), max_hp=blissey.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1

    def test_singles_multihit_second_mover_still_works(self):
        """Multi-hit on second (slower) mover in singles → ≥1 candidate."""
        electrode = make_mon(Species.ELECTRODE, moves=(Move.SPLASH,))
        dragonite = make_mon(Species.DRAGONITE, moves=(Move.DUAL_WINGBEAT,))
        state = make_battle(electrode, dragonite)
        messages = [
            usedmove("Electrode", "Splash"),
            usedmove("Dragonite", "Dual Wingbeat", foe=True),
            hitxtimes(2),
        ]
        # electrode (side 0) attacked: 135 → 114 → 93
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[pdelta(electrode.species, (135, 114), (114, 93))],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1


# ---------------------------------------------------------------------------
# 4. DOUBLES one multi-hit mover end-to-end through run_candidate_sweep
# ---------------------------------------------------------------------------

class TestDoublesOneMultiHitMover:
    """Player slot 0 uses a multi-hit move against opponent slot 0 in doubles."""

    def _doubles_state(self):
        p0 = make_mon(Species.DRAGONITE, moves=(Move.DUAL_WINGBEAT,), level=50)
        p1 = make_mon(Species.ELECTRODE, moves=(Move.SPLASH,), level=50)
        o0 = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)
        o1 = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
        return make_doubles_battle(p0, p1, o0, o1), p0, p1, o0, o1

    def test_doubles_one_multihit_mover_finds_candidates(self):
        """Doubles: Dragonite (slot 0) uses 2-hit Dual Wingbeat vs Blissey (opp slot 0).

        Per-hit readings: 48→29 (hit 1), 29→11 (hit 2) — same as verified singles scenario.
        """
        state, p0, p1, o0, o1 = self._doubles_state()

        messages = [
            usedmove("Dragonite", "Dual Wingbeat"),
            hitxtimes(2),
            usedmove("Electrode", "Splash"),
            usedmove("Blissey", "Splash", foe=True),
            usedmove("Poochyena", "Splash", foe=True),
        ]

        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(o0.species, (48, 29), (29, 11), max_hp=o0.max_hp, slot=0)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1


# ---------------------------------------------------------------------------
# 5. Two multi-hit movers one-per-side in a single turn
# ---------------------------------------------------------------------------

class TestDoublesDoubleMultiHit:
    """One multi-hit mover per side in the same turn — both enumerated independently."""

    def test_two_multihit_movers_one_per_side(self):
        """Dragonite (2-hit Dual Wingbeat) vs Cinccino; Cinccino (3-hit Tail Slap) vs Dragonite."""
        p0 = make_mon(Species.DRAGONITE, moves=(Move.DUAL_WINGBEAT,), level=50)
        p1 = make_mon(Species.ELECTRODE, moves=(Move.SPLASH,), level=50)
        o0 = make_mon(Species.CINCCINO, moves=(Move.TAIL_SLAP,), level=50)
        o1 = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)
        state = make_doubles_battle(p0, p1, o0, o1)

        messages = [
            usedmove("Electrode", "Splash"),
            usedmove("Cinccino", "Tail Slap", foe=True),
            hitxtimes(3),
            usedmove("Dragonite", "Dual Wingbeat"),
            hitxtimes(2),
            usedmove("Blissey", "Splash", foe=True),
        ]

        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[
                # Cinccino's 3-hit Tail Slap vs Dragonite: one exact-HP reading per hit
                pdelta(p0.species, (166, 147), (147, 128), (128, 109), slot=0),
                # Dragonite's 2-hit Dual Wingbeat vs Cinccino: k-pixel per hit
                odelta(o0.species, (48, 31), (31, 15), max_hp=o0.max_hp, slot=0),
            ],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
