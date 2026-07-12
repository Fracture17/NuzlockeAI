# Exception-move kill-bonus scoring (RECORDS/AI.md §2/§3, ai.ts:673-703).
#
# Relic Song, Meteor Beam, Future Sight, and damaging trapping moves are EXCLUDED
# from the highest-damage (HD) competition, so they never receive the +6/+8 HD base.
# But per ai.ts they DO receive the kill bonus when they KO — and it is the kill
# bonus ONLY: a fixed +6 (AI faster / priority) or +3 (AI slower), +1 with a Moxie-
# family ability. No HD base, no 0.8/0.2 variance. This is exactly what AI.md's
# exception-move kill-score thresholds [3, 6] (→ [4, 7] with Moxie) encode.
#
# Pre-fix bugs this locks against:
#   * Relic Song / Meteor Beam returned a FLAT score (+10 / +9 / -20) and skipped the
#     kill bonus entirely.
#   * Future Sight / trapping OVER-counted a killing move as {6+kb (80%), 8+kb (20%)}
#     — a spurious +6/+8 HD base plus variance.
#
# The additive move score stacks on top of the kill bonus:
#   Relic Song  = +10 (Meloetta base) / -20 (Meloetta-Pirouette)
#   Meteor Beam = +9 (Power Herb) / -20 (no Power Herb)
#   Future Sight / trapping = 0 additive (their non-kill +6/+8 is discarded on a KO)
#
# Scores are read raw from the cpp.ai_action_dists binding (per-move [score, prob]).
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.moves import Move
from liveplay.data.species import Species
from tests.state_builders import make_mon, make_battle


def _dist_for_slot(state, slot: int, ai_idx: int = 1):
    """Return (ai_fst, {score: prob}) for the AI move in the given slot."""
    res = cpp.ai_action_dists(json.dumps(sweep_io.to_jsonable(state)), ai_idx)
    for a, d in zip(res["actions"], res["dists"]):
        if a["move_slot"] == slot:
            return res["ai_fst"], {int(s): round(float(p), 6) for s, p in d}
    raise AssertionError(f"No AI move action found for slot {slot}: {res['actions']}")


# Fast/slow species chosen so speed (not level) decides AI order; both level 50 so a
# KO check on a 1-HP target never underflows to 0 damage.
def _fast_ai(moves, **kw):
    return make_mon(Species.JOLTEON, moves=moves, level=50, **kw)


def _slow_ai(moves, **kw):
    return make_mon(Species.SNORLAX, moves=moves, level=50, **kw)


def _ko_target_vs_fast_ai():
    """Slow player at 1 HP → any AI move KOs, AI (Jolteon) is faster."""
    return make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50, hp=1)


def _ko_target_vs_slow_ai():
    """Fast player at 1 HP → any AI move KOs, AI (Snorlax) is slower."""
    return make_mon(Species.JOLTEON, moves=(Move.SPLASH,), level=50, hp=1)


def _bulky_full():
    """Full-HP bulky player → exception moves do NOT KO."""
    return make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)


# ---------------------------------------------------------------------------
# Relic Song (Meloetta base form: +10 additive)
# ---------------------------------------------------------------------------

class TestRelicSong:
    def test_ko_faster_stacks_plus6(self):
        """Base-form Relic Song KO while faster: +10 base +6 kb = 16 (fixed)."""
        ai = _fast_ai((Move.RELIC_SONG, Move.SPLASH))
        ai = ai._replace(species=Species.MELOETTA)
        fst, dist = _dist_for_slot(make_battle(_ko_target_vs_fast_ai(), ai), 0)
        assert fst is True
        assert dist == {16: 1.0}, dist

    def test_ko_slower_stacks_plus3(self):
        """Base-form Relic Song KO while slower: +10 base +3 kb = 13 (fixed)."""
        ai = _slow_ai((Move.RELIC_SONG, Move.SPLASH))
        ai = ai._replace(species=Species.MELOETTA)
        fst, dist = _dist_for_slot(make_battle(_ko_target_vs_slow_ai(), ai), 0)
        assert fst is False
        assert dist == {13: 1.0}, dist

    def test_ko_faster_moxie_adds_one(self):
        """Moxie family adds +1 to the kill bonus: +10 +6 +1 = 17."""
        ai = _fast_ai((Move.RELIC_SONG, Move.SPLASH), ability=Ability.MOXIE)
        ai = ai._replace(species=Species.MELOETTA)
        fst, dist = _dist_for_slot(make_battle(_ko_target_vs_fast_ai(), ai), 0)
        assert fst is True
        assert dist == {17: 1.0}, dist

    def test_no_kill_flat_plus10(self):
        """No KO: flat +10, no kill bonus."""
        ai = _fast_ai((Move.RELIC_SONG, Move.SPLASH))
        ai = ai._replace(species=Species.MELOETTA)
        _, dist = _dist_for_slot(make_battle(_bulky_full(), ai), 0)
        assert dist == {10: 1.0}, dist

    def test_pirouette_no_kill_flat_minus20(self):
        """Meloetta-Pirouette, no KO: flat -20."""
        ai = _fast_ai((Move.RELIC_SONG, Move.SPLASH))
        ai = ai._replace(species=Species.MELOETTA_PIROUETTE)
        _, dist = _dist_for_slot(make_battle(_bulky_full(), ai), 0)
        assert dist == {-20: 1.0}, dist

    def test_pirouette_kill_stacks_on_minus20(self):
        """Meloetta-Pirouette KO while faster: -20 base +6 kb = -14 (still discouraged)."""
        ai = _fast_ai((Move.RELIC_SONG, Move.SPLASH))
        ai = ai._replace(species=Species.MELOETTA_PIROUETTE)
        fst, dist = _dist_for_slot(make_battle(_ko_target_vs_fast_ai(), ai), 0)
        assert fst is True
        assert dist == {-14: 1.0}, dist


# ---------------------------------------------------------------------------
# Meteor Beam (Power Herb: +9 additive; otherwise -20)
# ---------------------------------------------------------------------------

class TestMeteorBeam:
    def test_power_herb_ko_faster_stacks_plus6(self):
        """Power Herb Meteor Beam KO while faster: +9 base +6 kb = 15."""
        ai = _fast_ai((Move.METEOR_BEAM, Move.SPLASH), item=Item.POWER_HERB)
        fst, dist = _dist_for_slot(make_battle(_ko_target_vs_fast_ai(), ai), 0)
        assert fst is True
        assert dist == {15: 1.0}, dist

    def test_power_herb_ko_slower_stacks_plus3(self):
        """Power Herb Meteor Beam KO while slower: +9 base +3 kb = 12."""
        ai = _slow_ai((Move.METEOR_BEAM, Move.SPLASH), item=Item.POWER_HERB)
        fst, dist = _dist_for_slot(make_battle(_ko_target_vs_slow_ai(), ai), 0)
        assert fst is False
        assert dist == {12: 1.0}, dist

    def test_power_herb_no_kill_flat_plus9(self):
        """Power Herb, no KO: flat +9."""
        ai = _fast_ai((Move.METEOR_BEAM, Move.SPLASH), item=Item.POWER_HERB)
        _, dist = _dist_for_slot(make_battle(_bulky_full(), ai), 0)
        assert dist == {9: 1.0}, dist

    def test_no_power_herb_no_kill_flat_minus20(self):
        """No Power Herb, no KO: flat -20."""
        ai = _fast_ai((Move.METEOR_BEAM, Move.SPLASH))
        _, dist = _dist_for_slot(make_battle(_bulky_full(), ai), 0)
        assert dist == {-20: 1.0}, dist


# ---------------------------------------------------------------------------
# Future Sight (0 additive; non-kill +6/+8 discarded on KO)
# ---------------------------------------------------------------------------

class TestFutureSight:
    def test_ko_faster_is_kb_only(self):
        """Future Sight KO while faster: kb only = 6 (fixed, no HD base/variance)."""
        ai = _fast_ai((Move.FUTURE_SIGHT, Move.SPLASH))
        fst, dist = _dist_for_slot(make_battle(_ko_target_vs_fast_ai(), ai), 0)
        assert fst is True
        assert dist == {6: 1.0}, dist

    def test_ko_slower_is_kb_only(self):
        """Future Sight KO while slower: kb only = 3 (fixed)."""
        ai = _slow_ai((Move.FUTURE_SIGHT, Move.SPLASH))
        fst, dist = _dist_for_slot(make_battle(_ko_target_vs_slow_ai(), ai), 0)
        assert fst is False
        assert dist == {3: 1.0}, dist

    def test_no_kill_slower_flat_plus6(self):
        """No KO, not (faster & OHKO-threatened): flat +6."""
        ai = _slow_ai((Move.FUTURE_SIGHT, Move.SPLASH))
        _, dist = _dist_for_slot(make_battle(_bulky_full(), ai), 0)
        assert dist == {6: 1.0}, dist


# ---------------------------------------------------------------------------
# Damaging trapping moves (Whirlpool)
# ---------------------------------------------------------------------------

class TestTrappingMoves:
    def test_ko_faster_is_kb_only(self):
        """Trapping KO while faster: kb only = 6 (fixed, was 12/14 pre-fix)."""
        ai = _fast_ai((Move.WHIRLPOOL, Move.SPLASH))
        fst, dist = _dist_for_slot(make_battle(_ko_target_vs_fast_ai(), ai), 0)
        assert fst is True
        assert dist == {6: 1.0}, dist

    def test_ko_slower_is_kb_only(self):
        """Trapping KO while slower: kb only = 3 (fixed, was 9/11 pre-fix)."""
        ai = _slow_ai((Move.WHIRLPOOL, Move.SPLASH))
        fst, dist = _dist_for_slot(make_battle(_ko_target_vs_slow_ai(), ai), 0)
        assert fst is False
        assert dist == {3: 1.0}, dist

    def test_no_kill_is_plus6_plus8(self):
        """Trapping no KO: unchanged +6 (80%) / +8 (20%)."""
        ai = _fast_ai((Move.WHIRLPOOL, Move.SPLASH))
        _, dist = _dist_for_slot(make_battle(_bulky_full(), ai), 0)
        assert dist == {6: 0.8, 8: 0.2}, dist
