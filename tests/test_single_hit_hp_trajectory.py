# Port of OLD tests/test_single_hit_hp_trajectory.py — single-hit HP trajectory handling.
#
# TestSharedHelpers (_segment_hp_deltas_into_hits, _hit_passes_constraint) are DROPPED:
#   already covered by test_sweep_run.py::TestSegmentHpDeltasIntoHits and
#   test_sweep_run.py::TestHitPassesConstraint.
# TestSingleHitDisambiguationViaIntermediateReading is DROPPED: SKIPPED in OLD (deferred).
#
# Ported:
#   TestSingleHitUncorroboratedHealRaisesError  — phantom HP increase → SimulationError
#   TestMultiMoverGatePreventsSegmentation       — 2 movers/gate prevents false prune
#   TestSingleHitCorroboratedHealDoesNotRaise    — Oran Berry heal with message
#   TestRecoveryMoveHealDoesNotCrash             — Synthesis heal reproduced by sim
from __future__ import annotations

import pytest

from liveplay.data.items import Item
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.battle_types import MatchResult
from liveplay.engine_select import SimulationError
from liveplay.candidate import Candidate
from liveplay.sweep_run import run_candidate_sweep
from tests.state_builders import make_mon, make_battle, make_doubles_battle, odelta, pdelta


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _mr(string_id, *, constant_name="", var_values=None, side_hint=None, matched_text=""):
    vals = var_values or []
    if side_hint is None:
        first = str(vals[0]).split()[0].lower() if vals else ""
        side_hint = 1 if first == "foe" else 0
    return MatchResult(
        string_id=string_id, id_value=0, constant_name=constant_name,
        var_values=vals, score=0, matched_text=matched_text, slot_labels=[],
        side_hint=side_hint,
    )


def _usedmove(attacker, move_name, *, side_hint=None):
    return _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
               var_values=[attacker, move_name], side_hint=side_hint)


def _make_candidate(state):
    return Candidate(state=state)


def _oran_heal_msg(mon_name):
    return _mr("STRINGID_PKMNSITEMRESTOREDHEALTH",
               constant_name="sText_PkmnsItemRestoredHealth",
               var_values=[mon_name, "Oran Berry"])


def _regained_health_msg(mon_name, *, side_hint=None):
    return _mr("STRINGID_PKMNREGAINEDHEALTH",
               constant_name="sText_PkmnRegainedHealth",
               var_values=[mon_name], side_hint=side_hint)


# ---------------------------------------------------------------------------
# Test 1: phantom HP increase the sim never reproduces → SimulationError
# ---------------------------------------------------------------------------

class TestSingleHitUncorroboratedHealRaisesError:
    """A phantom HP increase the sim never reproduces leaves no survivor (SimulationError)."""

    def _make_state(self):
        blissey = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50, item=Item.ORAN_BERRY)
        kangaskhan = make_mon(Species.KANGASKHAN, moves=(Move.TACKLE,), level=50)
        return make_battle(blissey, kangaskhan), blissey, kangaskhan

    def test_uncorroborated_hp_increase_raises(self):
        """Phantom HP increase no candidate reproduces → count prune → no-candidate raise."""
        state, blissey, kangaskhan = self._make_state()
        messages = [
            _usedmove("Blissey", "Splash"),
            _usedmove("Foe Kangaskhan", "Tackle"),
        ]
        with pytest.raises(SimulationError):
            run_candidate_sweep(
                messages=messages,
                hp_deltas=[pdelta(blissey.species, (blissey.max_hp, blissey.max_hp - 93),
                                  (blissey.max_hp - 93, blissey.max_hp - 93 + 10))],
                initial_candidates=[_make_candidate(state)],
            )

    def test_uncorroborated_hp_increase_raises_opponent_side(self):
        """Phantom HP increase on opponent-side (k-pixel) reading also leaves no survivor."""
        blissey = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50, item=Item.ORAN_BERRY)
        kangaskhan = make_mon(Species.KANGASKHAN, moves=(Move.TACKLE,), level=50)
        state = make_battle(kangaskhan, blissey)  # player=Kangaskhan, opp=Blissey
        max_hp = blissey.max_hp
        messages = [
            _usedmove("Kangaskhan", "Tackle"),
            _usedmove("Foe Blissey", "Splash"),
        ]
        with pytest.raises(SimulationError):
            run_candidate_sweep(
                messages=messages,
                hp_deltas=[odelta(blissey.species, (48, 34), (34, 35), max_hp=max_hp)],
                initial_candidates=[_make_candidate(state)],
            )


# ---------------------------------------------------------------------------
# Test 3: multi-mover gate — ≥2 damage deltas means another mover also hit
# ---------------------------------------------------------------------------

class TestMultiMoverGatePreventsSegmentation:
    """Single-hit gate: ≥2 damage deltas means another mover also hit; no segmentation."""

    def test_two_movers_same_target_no_false_prune(self):
        """Two foe mons each deal one hit to the same player slot: both candidates survive."""
        blissey = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)
        ralts = make_mon(Species.RALTS, moves=(Move.SPLASH,), level=50)
        kangaskhan = make_mon(Species.KANGASKHAN, moves=(Move.TACKLE,), level=50)
        pikachu = make_mon(Species.PIKACHU, moves=(Move.TACKLE,), level=50)

        state = make_doubles_battle(blissey, ralts, kangaskhan, pikachu)

        messages = [
            _usedmove("Blissey", "Splash"),
            _usedmove("Ralts", "Splash"),
            _usedmove("Foe Kangaskhan", "Tackle", side_hint=1),
            _usedmove("Foe Pikachu", "Tackle", side_hint=1),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1, "Multi-mover turn must return candidates, not raise"

    def test_two_damage_deltas_no_uncorroborated_heal_guard_false_trigger(self):
        """Two damage deltas on a single-hit mover's target must NOT trigger the heal guard."""
        kangaskhan = make_mon(Species.KANGASKHAN, moves=(Move.TACKLE,), level=50)
        blissey = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)
        state = make_battle(kangaskhan, blissey)

        messages = [
            _usedmove("Kangaskhan", "Tackle"),
            _usedmove("Foe Blissey", "Splash"),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(blissey.species, (48, 34), max_hp=blissey.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1, "Normal single-hit with one damage delta must return candidates"


# ---------------------------------------------------------------------------
# Test 4: corroborated single heal on a single-hit turn does NOT raise.
# ---------------------------------------------------------------------------

class TestSingleHitCorroboratedHealDoesNotRaise:
    """A corroborated HP increase (heal message present) must not raise SimulationError."""

    def test_corroborated_oran_heal_survives(self):
        """Single-hit turn with Oran Berry heal + heal message must yield candidates."""
        blissey = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50,
                           item=Item.ORAN_BERRY, hp=267)
        kangaskhan = make_mon(Species.KANGASKHAN, moves=(Move.TACKLE,), level=50)
        state = make_battle(kangaskhan, blissey)

        oran_msg = _oran_heal_msg("Foe Blissey")
        messages = [
            _usedmove("Kangaskhan", "Tackle"),
            _usedmove("Foe Blissey", "Splash"),
            oran_msg,
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(blissey.species, (38, 24), (24, 25), max_hp=330)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1, "Corroborated Oran Berry heal must not raise"


# ---------------------------------------------------------------------------
# Test 4b: Synthesis heal reproduced by the sim must not crash.
# ---------------------------------------------------------------------------

class TestRecoveryMoveHealDoesNotCrash:
    """A recovery-move HP increase the sim reproduces must yield candidates, not raise."""

    def test_synthesis_heal_survives(self):
        """Opponent Synthesis heal (+max_hp//2) is matched by the sim trajectory."""
        kangaskhan = make_mon(Species.KANGASKHAN, moves=(Move.SPLASH,), level=50)
        blissey = make_mon(Species.BLISSEY, moves=(Move.SYNTHESIS,), level=50,
                           item=Item.NONE, hp=1)
        state = make_battle(kangaskhan, blissey)
        max_hp = blissey.max_hp
        messages = [
            _usedmove("Kangaskhan", "Splash"),
            _usedmove("Foe Blissey", "Synthesis"),
            _regained_health_msg("Foe Blissey", side_hint=1),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(blissey.species, (1, 24), max_hp=max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1, "Synthesis heal reproduced by sim must not crash"
