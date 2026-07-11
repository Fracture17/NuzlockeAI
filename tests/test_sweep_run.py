# Tests for liveplay/sweep_run.py: roll/crit enumeration core (E2 Task 7b).
# Tests written before implementation — all should fail until sweep_run.py exists.
from __future__ import annotations

import itertools
import pytest

from liveplay.actions import Action, ActionKind
from liveplay.battle_types import ActionGroup, MatchResult
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.rng import RNGEvent
from tests.state_builders import make_mon, make_battle, slot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mr(string_id, var_values=None, side_hint=None):
    """Build a minimal MatchResult for testing."""
    return MatchResult(
        string_id=string_id,
        id_value=0,
        constant_name=string_id,
        var_values=var_values or [],
        score=0,
        side_hint=side_hint,
    )


def _usedmove(attacker_name, move_name, side_hint=None):
    return _mr("STRINGID_USEDMOVE", var_values=[attacker_name, move_name], side_hint=side_hint)


# ---------------------------------------------------------------------------
# _segment_hp_deltas_into_hits
# ---------------------------------------------------------------------------

class TestSegmentHpDeltasIntoHits:
    """Split a bar-reading sequence into per-hit segments, anchoring across heals."""

    def test_pure_damage_sequence_one_segment_per_hit(self):
        from liveplay.sweep_run import _segment_hp_deltas_into_hits

        # Three consecutive damage deltas → three damage hits, same segment (start=0).
        deltas = [(100, 80), (80, 60), (60, 40)]
        anchors, new_vals, seg_starts = _segment_hp_deltas_into_hits(deltas)

        assert len(anchors) == 3
        assert len(new_vals) == 3
        assert len(seg_starts) == 3
        assert anchors == [100, 100, 100]
        assert new_vals == [80, 60, 40]
        assert seg_starts == [0, 0, 0]

    def test_interior_heal_resets_anchor_and_consumes_no_hit_slot(self):
        from liveplay.sweep_run import _segment_hp_deltas_into_hits

        # Heal in the middle: (90,70) damage, then (70,90) heal, then (90,60) damage.
        # The heal resets the segment anchor to 90 and consumes no hit slot.
        deltas = [(90, 70), (70, 90), (90, 60)]
        anchors, new_vals, seg_starts = _segment_hp_deltas_into_hits(deltas)

        # Two damage deltas; the heal consumed no hit slot.
        assert len(anchors) == 2
        assert anchors[0] == 90   # first segment: anchor from first reading
        assert new_vals[0] == 70
        assert seg_starts[0] == 0
        # After heal, new segment starts at index 1.
        assert anchors[1] == 90   # anchor reset to heal-to value (90)
        assert new_vals[1] == 60
        assert seg_starts[1] == 1  # new segment started at hit index 1

    def test_leading_heal_resets_before_any_damage(self):
        from liveplay.sweep_run import _segment_hp_deltas_into_hits

        # Heal first, then damage. The heal just updates the anchor; zero damage hits before.
        deltas = [(50, 70), (70, 40)]
        anchors, new_vals, seg_starts = _segment_hp_deltas_into_hits(deltas)

        assert len(anchors) == 1   # one damage delta
        assert anchors[0] == 70    # anchor was reset by the heal
        assert new_vals[0] == 40
        assert seg_starts[0] == 0

    def test_empty_deltas(self):
        from liveplay.sweep_run import _segment_hp_deltas_into_hits

        anchors, new_vals, seg_starts = _segment_hp_deltas_into_hits([])
        assert anchors == []
        assert new_vals == []
        assert seg_starts == []

    def test_single_damage_delta(self):
        from liveplay.sweep_run import _segment_hp_deltas_into_hits

        anchors, new_vals, seg_starts = _segment_hp_deltas_into_hits([(48, 30)])
        assert anchors == [48]
        assert new_vals == [30]
        assert seg_starts == [0]


# ---------------------------------------------------------------------------
# _hit_passes_constraint
# ---------------------------------------------------------------------------

class TestHitPassesConstraint:
    """Opponent-side k-pixel range accept/reject; player-side exact; KO overkill accepted."""

    def test_opponent_side_within_range_accepted(self):
        from liveplay.sweep_run import _hit_passes_constraint
        # anchor=48, new_val=30, max_hp=100 → hp_range(30,100) = some range.
        # Any cumulative damage inside the valid window should pass.
        # With max_hp=100: hp_range(48,100): 48*100/48=100 HP, range ~[100,100].
        # Just test that a plausible small delta is accepted.
        assert _hit_passes_constraint(
            cumulative=10, anchor=48, new_val=43,
            use_hp_range=True, opponent_max_hp=100,
        )

    def test_opponent_side_out_of_range_rejected(self):
        from liveplay.sweep_run import _hit_passes_constraint
        # Absurdly large cumulative damage for the given bar drop.
        assert not _hit_passes_constraint(
            cumulative=1000, anchor=48, new_val=43,
            use_hp_range=True, opponent_max_hp=100,
        )

    def test_player_side_exact_match_accepted(self):
        from liveplay.sweep_run import _hit_passes_constraint
        # Player-side: anchor=100, cumulative=20, new_val=80 → exact (100-20=80).
        assert _hit_passes_constraint(
            cumulative=20, anchor=100, new_val=80,
            use_hp_range=False, opponent_max_hp=0,
        )

    def test_player_side_off_by_one_rejected(self):
        from liveplay.sweep_run import _hit_passes_constraint
        # cumulative=19, but new_val=80 → expected 81. Mismatch.
        assert not _hit_passes_constraint(
            cumulative=19, anchor=100, new_val=80,
            use_hp_range=False, opponent_max_hp=0,
        )

    def test_ko_overkill_accepted_opponent_side(self):
        from liveplay.sweep_run import _hit_passes_constraint
        # new_val=0 (KO) → upper-bound check skipped; even massive cumulative is fine.
        assert _hit_passes_constraint(
            cumulative=500, anchor=20, new_val=0,
            use_hp_range=True, opponent_max_hp=100,
        )

    def test_ko_overkill_accepted_player_side(self):
        from liveplay.sweep_run import _hit_passes_constraint
        # Player side KO: anchor=50, cumulative=60 → 50-60=-10 ≤ 0, accepted.
        assert _hit_passes_constraint(
            cumulative=60, anchor=50, new_val=0,
            use_hp_range=False, opponent_max_hp=0,
        )

    def test_player_side_insufficient_ko_rejected(self):
        from liveplay.sweep_run import _hit_passes_constraint
        # Player side KO: anchor=50, cumulative=30 → 50-30=20 > 0, not a KO.
        assert not _hit_passes_constraint(
            cumulative=30, anchor=50, new_val=0,
            use_hp_range=False, opponent_max_hp=0,
        )


# ---------------------------------------------------------------------------
# make_sweep_config (SweepConfig builder from partial candidate)
# ---------------------------------------------------------------------------

class TestMakeSweepConfig:
    """Build a SweepConfig from a partial candidate with various roll/crit shapes."""

    def _partial(self, rolls=(), crits=()):
        """Minimal PartialCandidate-like object."""
        from liveplay.sweep_run import PartialCandidate
        return PartialCandidate(rolls=rolls, crits=crits, mover_iteration=len(rolls))

    def test_scalar_crit_roll_produces_scalar_side_overrides(self):
        from liveplay.sweep_run import make_sweep_config, PartialCandidate
        from liveplay.sweep_driver import SideOverrides

        # One mover on side 0, scalar roll/crit
        movers = [(0, 0)]
        partial = PartialCandidate(rolls=(0.75,), crits=(True,), mover_iteration=1)
        config = make_sweep_config(
            partial=partial,
            movers=movers,
            mover_iteration=len(movers),
            current_roll=0.5,
            current_crit=False,
            tie_winner=0,
            combo_ovr_0={},
            combo_ovr_1={},
            injected_pre={},
        )
        # Side 0 should have scalar roll/crit (singles path)
        assert config.side0.roll == 0.75
        assert config.side0.crit == True
        assert config.side0.crits_per_hit is None
        assert config.side0.rolls_per_hit is None

    def test_per_hit_tuple_roll_produces_per_hit_side_overrides(self):
        from liveplay.sweep_run import make_sweep_config, PartialCandidate

        # Multi-hit mover: rolls stored as tuple
        movers = [(0, 0)]
        partial = PartialCandidate(
            rolls=((0.2, 0.8, 0.5),),
            crits=((0.0, 101.0, 101.0),),
            mover_iteration=1,
        )
        config = make_sweep_config(
            partial=partial,
            movers=movers,
            mover_iteration=len(movers),
            current_roll=0.5,
            current_crit=False,
            tie_winner=0,
            combo_ovr_0={},
            combo_ovr_1={},
            injected_pre={},
        )
        assert config.side0.rolls_per_hit == (0.2, 0.8, 0.5)
        assert config.side0.crits_per_hit == (0.0, 101.0, 101.0)

    def test_injected_overrides_land_in_extra_overrides(self):
        from liveplay.sweep_run import make_sweep_config, PartialCandidate

        movers = [(1, 0)]
        partial = PartialCandidate(rolls=(0.5,), crits=(False,), mover_iteration=1)
        # combo_ovr_1 carries a FLINCH override
        config = make_sweep_config(
            partial=partial,
            movers=movers,
            mover_iteration=len(movers),
            current_roll=0.5,
            current_crit=False,
            tie_winner=0,
            combo_ovr_0={},
            combo_ovr_1={RNGEvent.FLINCH: {0: True}},
            injected_pre={},
        )
        assert config.side1.extra_overrides is not None
        assert RNGEvent.FLINCH in config.side1.extra_overrides

    def test_tie_winner_and_injected_pre_set_on_config(self):
        from liveplay.sweep_run import make_sweep_config, PartialCandidate
        from liveplay.data.moves import Move

        movers = []
        partial = PartialCandidate(rolls=(), crits=(), mover_iteration=0)
        config = make_sweep_config(
            partial=partial,
            movers=movers,
            mover_iteration=0,
            current_roll=0.5,
            current_crit=False,
            tie_winner=1,
            combo_ovr_0={},
            combo_ovr_1={},
            injected_pre={RNGEvent.METRONOME_MOVE: Move.TACKLE},
        )
        assert config.tie_winner == 1
        assert config.extra_pre_inject == {RNGEvent.METRONOME_MOVE: Move.TACKLE}

    def test_current_mover_uses_current_roll_crit(self):
        from liveplay.sweep_run import make_sweep_config, PartialCandidate

        # Partial has one decided mover on side 0; current mover is side 1.
        movers = [(0, 0), (1, 0)]
        partial = PartialCandidate(rolls=(0.2,), crits=(False,), mover_iteration=1)
        config = make_sweep_config(
            partial=partial,
            movers=movers,
            mover_iteration=1,
            current_roll=0.9,
            current_crit=True,
            tie_winner=0,
            combo_ovr_0={},
            combo_ovr_1={},
            injected_pre={},
        )
        assert config.side0.roll == 0.2
        assert config.side1.roll == 0.9
        assert config.side1.crit == True

    def test_future_movers_get_placeholder(self):
        from liveplay.sweep_run import make_sweep_config, PartialCandidate

        # Two movers on side 0 and 1; partial has zero decided; current is iteration 0.
        movers = [(0, 0), (1, 0)]
        partial = PartialCandidate(rolls=(), crits=(), mover_iteration=0)
        config = make_sweep_config(
            partial=partial,
            movers=movers,
            mover_iteration=0,
            current_roll=0.7,
            current_crit=False,
            tie_winner=0,
            combo_ovr_0={},
            combo_ovr_1={},
            injected_pre={},
        )
        # Side 1 is a future mover — should get placeholder 0.5/False
        assert config.side1.roll == 0.5
        assert config.side1.crit == False


# ---------------------------------------------------------------------------
# _enumerate_mover_rolls and _run_phase_loop — end-to-end via C++
# ---------------------------------------------------------------------------

class TestEnumerateMoverRollsEndToEnd:
    """Single-hit mover Tackle: survivors deduped to distinct damage values."""

    def _tackle_battle(self):
        # Charizard (fast, high attack) uses Tackle on Bulbasaur.
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=50)
        return make_battle(charizard, bulbasaur)

    def _movers(self):
        # Player (side 0) moves first, opponent (side 1) second.
        return [(0, 0), (1, 0)]

    def test_tackle_survivors_deduped_below_16(self):
        """16 rolls should collapse to a small set of distinct damage values."""
        from liveplay.sweep_run import _run_phase_loop, PartialCandidate

        state = self._tackle_battle()
        a0 = slot(0)
        a1 = slot(0)
        movers = self._movers()
        mover_hit_counts = [1, 1]
        crit_counts = [0, 0]
        opp_side = state.sides[1]
        opp_max_hp = [opp_side.team[opp_side.active_indices[0]].max_hp]

        survivors = _run_phase_loop(
            state=state,
            action0=a0,
            action1=a1,
            movers=movers,
            mover_hit_counts=mover_hit_counts,
            tie_winner=0,
            combo_ovr_0={},
            combo_ovr_1={},
            injected_pre={},
            opponent_hp_deltas=[[]],
            player_hp_deltas=[[]],
            opponent_max_hp=opp_max_hp,
            crit_counts=crit_counts,
        )

        assert len(survivors) >= 1
        assert len(survivors) < 16, f"Expected deduplication; got {len(survivors)} survivors"
        # Each survivor is (rolls_tuple, crits_tuple, rs, capturing)
        for rolls, crits, rs, capturing in survivors:
            assert len(rolls) == 2  # one entry per mover
            assert len(crits) == 2

    def test_tackle_rng_sequence_shape_correct(self):
        """Each survivor's rolls/crits align with movers count."""
        from liveplay.sweep_run import _run_phase_loop

        state = self._tackle_battle()
        a0 = slot(0)
        a1 = slot(0)
        movers = self._movers()
        opp_side = state.sides[1]
        opp_max_hp = [opp_side.team[opp_side.active_indices[0]].max_hp]

        survivors = _run_phase_loop(
            state=state,
            action0=a0,
            action1=a1,
            movers=movers,
            mover_hit_counts=[1, 1],
            tie_winner=0,
            combo_ovr_0={},
            combo_ovr_1={},
            injected_pre={},
            opponent_hp_deltas=[[]],
            player_hp_deltas=[[]],
            opponent_max_hp=opp_max_hp,
            crit_counts=[0, 0],
        )

        for rolls, crits, rs, capturing in survivors:
            assert isinstance(rolls, tuple)
            assert isinstance(crits, tuple)
            assert len(rolls) == len(movers)
            assert len(crits) == len(movers)
            # Single-hit entries: scalar float roll, bool crit
            for r in rolls:
                assert isinstance(r, float)
            for c in crits:
                assert isinstance(c, bool)


class TestStatusMoveSurvivor:
    """Growl (status move) produces no damage — a zero-damage survivor must exist."""

    def test_growl_yields_at_least_one_survivor(self):
        from liveplay.sweep_run import _run_phase_loop

        charizard = make_mon(Species.CHARIZARD, moves=(Move.GROWL,), level=50)
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=50)
        state = make_battle(charizard, bulbasaur)

        a0 = slot(0)
        a1 = slot(0)
        movers = [(0, 0), (1, 0)]
        opp_side = state.sides[1]
        opp_max_hp = [opp_side.team[opp_side.active_indices[0]].max_hp]

        survivors = _run_phase_loop(
            state=state,
            action0=a0,
            action1=a1,
            movers=movers,
            mover_hit_counts=[1, 1],
            tie_winner=0,
            combo_ovr_0={},
            combo_ovr_1={},
            injected_pre={},
            opponent_hp_deltas=[[]],
            player_hp_deltas=[[]],
            opponent_max_hp=opp_max_hp,
            crit_counts=[0, 0],
        )

        assert len(survivors) >= 1


class TestMultiHitMovePhaseLoop:
    """Multi-hit move (Fury Swipes): per-hit tuples in rolls/crits, HP-prune applied."""

    def test_fury_swipes_produces_per_hit_tuples(self):
        from liveplay.sweep_run import _run_phase_loop

        # Sandslash (base speed 65) vs Rattata (base speed 72): Rattata is faster.
        # movers list reflects observed order: side 1 (Rattata Splash) then side 0 (Sandslash).
        sandslash = make_mon(Species.SANDSLASH, moves=(Move.FURY_SWIPES,), level=50)
        rattata = make_mon(Species.RATTATA, moves=(Move.SPLASH,), level=50)
        state = make_battle(sandslash, rattata)

        a0 = slot(0)
        a1 = slot(0)
        # Observed movers in execution order: Rattata (side 1) first, then Sandslash (side 0).
        movers = [(1, 0), (0, 0)]
        opp_side = state.sides[1]
        opp_max_hp = [opp_side.team[opp_side.active_indices[0]].max_hp]

        # Fury Swipes hits 2–5 times; try n_hits=2 (guaranteed possible).
        n_hits = 2
        survivors = _run_phase_loop(
            state=state,
            action0=a0,
            action1=a1,
            movers=movers,
            mover_hit_counts=[1, n_hits],  # Rattata: 1 hit; Sandslash: 2-hit
            tie_winner=1,                  # tie_winner from first mover's side
            combo_ovr_0={},
            combo_ovr_1={},
            injected_pre={},
            opponent_hp_deltas=[[]],
            player_hp_deltas=[[]],
            opponent_max_hp=opp_max_hp,
            crit_counts=[0, 0],
        )

        assert len(survivors) >= 1
        # Multi-hit: rolls[1] and crits[1] are for Sandslash (mover index 1), should be tuples.
        for rolls, crits, rs, capturing in survivors:
            assert isinstance(rolls[1], tuple), "Multi-hit rolls should be a tuple"
            assert isinstance(crits[1], tuple), "Multi-hit crits should be a tuple"
            assert len(rolls[1]) == n_hits
            assert len(crits[1]) == n_hits

    def test_fury_swipes_hp_prune_reduces_candidates(self):
        """Observed bar constraint should prune impossible combos without error."""
        from liveplay.sweep_run import _run_phase_loop

        # Rattata faster than Sandslash; movers ordered by execution order.
        sandslash = make_mon(Species.SANDSLASH, moves=(Move.FURY_SWIPES,), level=50)
        rattata = make_mon(Species.RATTATA, moves=(Move.SPLASH,), level=50)
        state = make_battle(sandslash, rattata)

        a0 = slot(0)
        a1 = slot(0)
        movers = [(1, 0), (0, 0)]
        opp_side = state.sides[1]
        max_hp = opp_side.team[opp_side.active_indices[0]].max_hp
        opp_max_hp = [max_hp]

        # Tight bar constraint (k=40 before, k=35 after) for the 2-hit multi-hit.
        hp_deltas_tight = [[(40, 35)]]

        survivors = _run_phase_loop(
            state=state,
            action0=a0,
            action1=a1,
            movers=movers,
            mover_hit_counts=[1, 2],
            tie_winner=1,
            combo_ovr_0={},
            combo_ovr_1={},
            injected_pre={},
            opponent_hp_deltas=hp_deltas_tight,
            player_hp_deltas=[[]],
            opponent_max_hp=opp_max_hp,
            crit_counts=[0, 0],
        )
        # May be zero (constraint may eliminate all combos) or few — key: no crash.
        assert isinstance(survivors, list)
