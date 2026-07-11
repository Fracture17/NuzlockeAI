# Port of OLD tests/test_rampage_binding.py — SWEEP SECTIONS ONLY (from line 294 onward).
# The engine-mechanics sections before that (TestRampage, TestBinding mechanics) are covered
# by golden-trace parity and must NOT be ported per task instructions.
#
# TestSweepAssumeMaxDuration (lines 500–521) uses OLD run_sim (Simulator-based) with no NEW
# analog — DROPPED (engine-mechanics; SWEEP_LUCK max-duration rolling covered by
# test_sweep_driver.py::TestSweepLuck::test_max_duration_rolls).
#
# Ported:
#   TestBindingSweep          — run_candidate_sweep for binding/rampage turns
#   TestWrapReleaseOverride   — _apply_observed_wrap_release unit + integration
#   TestRampageEndOverride    — _apply_observed_rampage_end unit
from __future__ import annotations

import pytest

from liveplay.battle_types import MatchResult
from liveplay.candidate import Candidate
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.natures import Nature
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.status import Status
from liveplay.state.pokemon import PokemonState, GenderEnum, Volatile, VolatileEffect
from liveplay.state.side import SideState
from liveplay.state.battle import BattleState
from liveplay.sweep_reconcile import _apply_observed_wrap_release, _apply_observed_rampage_end
from liveplay.sweep_run import run_candidate_sweep
from tests.state_builders import odelta


# ---------------------------------------------------------------------------
# Local make_mon matching the OLD file's signature
# ---------------------------------------------------------------------------

def make_mon(species=Species.RATICATE, move_ids=None, move_pp=None, ability=Ability.NONE,
             item=Item.NONE, status=Status.NONE, volatiles=0, timed_volatiles=None,
             locked_slot=-1):
    """Build a PokemonState matching the OLD test file's make_mon signature."""
    move_ids = move_ids or (Move.SPLASH, Move.NONE, Move.NONE, Move.NONE)
    move_pp = move_pp or (40, 0, 0, 0)
    p = PokemonState(
        species=species, nature=Nature.HARDY, ivs=(31,) * 6,
        gender=GenderEnum.MALE, move_ids=move_ids, move_pp=move_pp,
        ability=ability, item=item, status=status,
    )
    if volatiles:
        p = p._replace(volatiles=volatiles)
    if timed_volatiles is not None:
        p = p._replace(timed_volatiles=list(timed_volatiles))
    if locked_slot != -1:
        p = p._replace(locked_slot=locked_slot)
    return p


def make_battle(p0, p1):
    s0 = SideState(team=[p0], active_indices=[0])
    s1 = SideState(team=[p1], active_indices=[0])
    return BattleState(sides=(s0, s1))


def _mr(string_id, *, constant_name="", var_values=None, side_hint=None):
    return MatchResult(
        string_id=string_id,
        id_value=0,
        constant_name=constant_name,
        var_values=var_values or [],
        score=0,
        matched_text="",
        slot_labels=[],
        side_hint=side_hint,
    )


# ---------------------------------------------------------------------------
# TestBindingSweep
# ---------------------------------------------------------------------------

class TestBindingSweep:
    """Sweep-level tests: binding-move turns must produce candidates without raising."""

    _RATICATE_MAX_HP = 130

    def _initial_candidate(self, p0, p1):
        state = make_battle(p0, p1)
        return Candidate(state=state)

    def test_opponent_wrap_produces_candidates(self):
        """Opponent uses Wrap; PKMNWRAPPEDBY present; sweep yields ≥1 candidate without raising."""
        p0 = make_mon(move_ids=(Move.SPLASH, Move.NONE, Move.NONE, Move.NONE), move_pp=(40, 0, 0, 0))
        p1 = make_mon(move_ids=(Move.WRAP, Move.NONE, Move.NONE, Move.NONE), move_pp=(20, 0, 0, 0))
        state = make_battle(p0, p1)

        messages = [
            _mr("STRINGID_USEDMOVE", var_values=["Raticate", "Wrap"], side_hint=1,
                constant_name="sText_AttackerUsedMove"),
            _mr("STRINGID_PKMNWRAPPEDBY", var_values=["Raticate", "Raticate"], side_hint=0),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[],
            initial_candidates=[Candidate(state=state)],
        )
        assert len(candidates) >= 1

    def test_player_wrap_produces_candidates(self):
        """Player uses Wrap; PKMNWRAPPEDBY present; sweep yields ≥1 candidate without raising."""
        p0 = make_mon(move_ids=(Move.WRAP, Move.NONE, Move.NONE, Move.NONE), move_pp=(20, 0, 0, 0))
        p1 = make_mon(move_ids=(Move.SPLASH, Move.NONE, Move.NONE, Move.NONE), move_pp=(40, 0, 0, 0))
        state = make_battle(p0, p1)

        messages = [
            _mr("STRINGID_USEDMOVE", var_values=["Raticate", "Wrap"], side_hint=0,
                constant_name="sText_AttackerUsedMove"),
            _mr("STRINGID_PKMNWRAPPEDBY", var_values=["Raticate", "Raticate"], side_hint=1),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(Species.RATICATE, (48, 43), (43, 37), max_hp=self._RATICATE_MAX_HP)],
            initial_candidates=[Candidate(state=state)],
        )
        assert len(candidates) >= 1

    def test_rampage_thrash_sweep_produces_candidates(self):
        """Player uses Thrash (first turn, no RAMPAGING yet); sweep yields ≥1 candidate."""
        p0 = make_mon(move_ids=(Move.THRASH, Move.NONE, Move.NONE, Move.NONE), move_pp=(10, 0, 0, 0))
        p1 = make_mon(move_ids=(Move.SPLASH, Move.NONE, Move.NONE, Move.NONE), move_pp=(40, 0, 0, 0))
        state = make_battle(p0, p1)

        messages = [
            _mr("STRINGID_USEDMOVE", var_values=["Raticate", "Thrash"], side_hint=0,
                constant_name="sText_AttackerUsedMove"),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(Species.RATICATE, (48, 16), max_hp=self._RATICATE_MAX_HP)],
            initial_candidates=[Candidate(state=state)],
        )
        assert len(candidates) >= 1


# ---------------------------------------------------------------------------
# TestWrapReleaseOverride
# ---------------------------------------------------------------------------

class TestWrapReleaseOverride:
    """_apply_observed_wrap_release clears BOUND on observed 'freed from Wrap!' message."""

    def _freed(self, side_hint, name="Raticate"):
        return _mr("STRINGID_PKMNFREEDFROM", var_values=[name, "Wrap"], side_hint=side_hint)

    def test_clears_bound_on_named_opponent(self):
        p0 = make_mon()
        p1 = make_mon(timed_volatiles=[(VolatileEffect.BOUND, 3),
                                       (VolatileEffect.BOUND_SOURCE_SLOT, 0)])
        state = make_battle(p0, p1)
        new_state = _apply_observed_wrap_release(state, [self._freed(side_hint=1)])
        victim = new_state.sides[1].team[0]
        assert not any(e == VolatileEffect.BOUND for e, _ in victim.timed_volatiles)
        assert not any(e == VolatileEffect.BOUND_SOURCE_SLOT for e, _ in victim.timed_volatiles)

    def test_clears_bound_on_named_player(self):
        p0 = make_mon(timed_volatiles=[(VolatileEffect.BOUND, 4),
                                       (VolatileEffect.BOUND_SOURCE_SLOT, 0)])
        p1 = make_mon()
        state = make_battle(p0, p1)
        new_state = _apply_observed_wrap_release(state, [self._freed(side_hint=0)])
        victim = new_state.sides[0].team[0]
        assert not any(e == VolatileEffect.BOUND for e, _ in victim.timed_volatiles)

    def test_preserves_other_timed_volatiles(self):
        p0 = make_mon()
        p1 = make_mon(timed_volatiles=[(VolatileEffect.BOUND, 3),
                                       (VolatileEffect.BOUND_SOURCE_SLOT, 0),
                                       (VolatileEffect.TAUNT, 2)])
        state = make_battle(p0, p1)
        new_state = _apply_observed_wrap_release(state, [self._freed(side_hint=1)])
        victim = new_state.sides[1].team[0]
        assert any(e == VolatileEffect.TAUNT and t == 2 for e, t in victim.timed_volatiles)
        assert not any(e == VolatileEffect.BOUND for e, _ in victim.timed_volatiles)

    def test_no_freed_message_is_noop(self):
        p0 = make_mon()
        p1 = make_mon(timed_volatiles=[(VolatileEffect.BOUND, 3)])
        state = make_battle(p0, p1)
        new_state = _apply_observed_wrap_release(state, [
            _mr("STRINGID_USEDMOVE", var_values=["Raticate", "Splash"], side_hint=0)])
        assert new_state is state
        assert any(e == VolatileEffect.BOUND for e, _ in new_state.sides[1].team[0].timed_volatiles)

    def test_not_bound_is_noop(self):
        p0 = make_mon()
        p1 = make_mon()  # no BOUND
        state = make_battle(p0, p1)
        new_state = _apply_observed_wrap_release(state, [self._freed(side_hint=1)])
        assert new_state is state

    def test_sweep_release_turn_no_tick(self):
        """End-to-end: opponent carried still-BOUND (counter 3) is observed freed this turn.
        The override clears BOUND so the engine deals NO residual tick — sweep yields a candidate."""
        p0 = make_mon(move_ids=(Move.SPLASH, Move.NONE, Move.NONE, Move.NONE), move_pp=(40, 0, 0, 0))
        p1 = make_mon(move_ids=(Move.SPLASH, Move.NONE, Move.NONE, Move.NONE), move_pp=(40, 0, 0, 0),
                      timed_volatiles=[(VolatileEffect.BOUND, 3), (VolatileEffect.BOUND_SOURCE_SLOT, 0)])
        state = make_battle(p0, p1)
        messages = [
            _mr("STRINGID_USEDMOVE", var_values=["Raticate", "Splash"], side_hint=0,
                constant_name="sText_AttackerUsedMove"),
            _mr("STRINGID_USEDMOVE", var_values=["Raticate", "Splash"], side_hint=1,
                constant_name="sText_AttackerUsedMove"),
            _mr("STRINGID_PKMNFREEDFROM", var_values=["Raticate", "Wrap"], side_hint=1),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(Species.RATICATE, (48, 48), max_hp=130)],
            initial_candidates=[Candidate(state=state)],
        )
        assert len(candidates) >= 1
        freed = candidates[0].state.sides[1].team[0]
        assert not any(e == VolatileEffect.BOUND for e, _ in freed.timed_volatiles)

    def test_clears_bound_source_id_companion(self):
        """BOUND_SOURCE_ID companion is also stripped on an observed release."""
        p0 = make_mon()
        p1 = make_mon(timed_volatiles=[(VolatileEffect.BOUND, 3),
                                       (VolatileEffect.BOUND_SOURCE_SLOT, 0),
                                       (VolatileEffect.BOUND_SOURCE_ID, 0)])
        state = make_battle(p0, p1)
        new_state = _apply_observed_wrap_release(state, [self._freed(side_hint=1)])
        victim = new_state.sides[1].team[0]
        leftover = {e for e, _ in victim.timed_volatiles}
        assert VolatileEffect.BOUND not in leftover
        assert VolatileEffect.BOUND_SOURCE_SLOT not in leftover
        assert VolatileEffect.BOUND_SOURCE_ID not in leftover


# ---------------------------------------------------------------------------
# TestRampageEndOverride
# ---------------------------------------------------------------------------

class TestRampageEndOverride:
    """_apply_observed_rampage_end clears RAMPAGING + LOCKED_MOVE and applies CONFUSED."""

    def _fatigue(self, side_hint, name="Raticate"):
        return _mr("STRINGID_PKMNFATIGUECONFUSION", var_values=[name], side_hint=side_hint)

    def _rampaging_mon(self, turns=2):
        return make_mon(
            move_ids=(Move.THRASH, Move.NONE, Move.NONE, Move.NONE), move_pp=(10, 0, 0, 0),
            volatiles=Volatile.LOCKED_MOVE,
            timed_volatiles=[(VolatileEffect.RAMPAGING, turns)],
            locked_slot=0,
        )

    def test_clears_rampaging_on_named_player(self):
        p0 = self._rampaging_mon()
        p1 = make_mon()
        state = make_battle(p0, p1)
        new_state = _apply_observed_rampage_end(state, [self._fatigue(side_hint=0)])
        mon = new_state.sides[0].team[0]
        assert not any(e == VolatileEffect.RAMPAGING for e, _ in mon.timed_volatiles)
        assert not (mon.volatiles & Volatile.LOCKED_MOVE)
        assert mon.volatiles & Volatile.CONFUSED
        assert mon.locked_slot == -1

    def test_clears_rampaging_on_named_opponent(self):
        p0 = make_mon()
        p1 = self._rampaging_mon()
        state = make_battle(p0, p1)
        new_state = _apply_observed_rampage_end(state, [self._fatigue(side_hint=1)])
        mon = new_state.sides[1].team[0]
        assert not any(e == VolatileEffect.RAMPAGING for e, _ in mon.timed_volatiles)
        assert mon.volatiles & Volatile.CONFUSED

    def test_no_fatigue_message_is_noop(self):
        p0 = self._rampaging_mon()
        p1 = make_mon()
        state = make_battle(p0, p1)
        new_state = _apply_observed_rampage_end(state, [
            _mr("STRINGID_USEDMOVE", var_values=["Raticate", "Splash"], side_hint=0)])
        assert new_state is state
        assert any(e == VolatileEffect.RAMPAGING for e, _ in new_state.sides[0].team[0].timed_volatiles)

    def test_not_rampaging_is_noop(self):
        p0 = make_mon()  # no RAMPAGING
        p1 = make_mon()
        state = make_battle(p0, p1)
        new_state = _apply_observed_rampage_end(state, [self._fatigue(side_hint=0)])
        assert new_state is state

    def test_missing_side_hint_is_noop(self):
        p0 = self._rampaging_mon()
        p1 = make_mon()
        state = make_battle(p0, p1)
        new_state = _apply_observed_rampage_end(state, [self._fatigue(side_hint=None)])
        assert new_state is state
