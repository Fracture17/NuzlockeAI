# Integration tests for run_candidate_sweep and related helpers ported from
# OLD tests/test_simulation_runner.py. Each class was absent from existing NEW
# helper-level test files; see the ledger in the report for full coverage mapping.
from __future__ import annotations

import pytest

from liveplay.battle_types import MatchResult
from liveplay.candidate import Candidate
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.moves import Move, move_name_to_enum
from liveplay.data.species import Species
from liveplay.data.status import Status as StatusEnum
from liveplay.engine_select import SimulationError
from liveplay.logger import CapturingLogger, LogEvent
from liveplay.rng import RNGEvent
from liveplay.state.pokemon import Volatile
from liveplay.sweep_reconcile import _check_hp_match
from liveplay.sweep_run import run_candidate_sweep
from tests.state_builders import (
    make_battle, make_mon, make_doubles_battle,
    pdelta, odelta, switch_to, slot, dslot,
)
from liveplay.state.side import SideState
from liveplay.state.battle import BattleState

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_AUTO_SIDE_HINT = object()


def _foe_prefix_hint(var_values):
    if not var_values:
        return None
    first = str(var_values[0])
    first_word = first.split()[0].lower() if first.strip() else ""
    return 1 if first_word == "foe" else 0


def _mr(string_id, *, constant_name="", var_values=None, id_value=0, score=0,
        side_hint=_AUTO_SIDE_HINT, matched_text="", name_side_slots=None):
    """Build a MatchResult; side_hint defaults to Foe-prefix detection."""
    vals = var_values or []
    if side_hint is _AUTO_SIDE_HINT:
        side_hint = _foe_prefix_hint(vals)
    return MatchResult(
        string_id=string_id,
        id_value=id_value,
        constant_name=constant_name,
        var_values=vals,
        score=score,
        matched_text=matched_text,
        slot_labels=[],
        side_hint=side_hint,
        name_side_slots=name_side_slots or {},
    )


def _usedmove_messages(attacker_name, move_name, secondaries=None, *, side_hint=0):
    primary = _mr(
        "STRINGID_USEDMOVE",
        constant_name="sText_AttackerUsedMove",
        var_values=[attacker_name, move_name],
        side_hint=side_hint,
    )
    msgs = [primary]
    if secondaries:
        msgs.extend(secondaries)
    return msgs


def _make_candidate(state):
    return Candidate(state=state)


# ---------------------------------------------------------------------------
# TestSingleMovePlausibleDelta — basic one-mover sweep
# ---------------------------------------------------------------------------

class TestSingleMovePlausibleDelta:
    """Side 0 uses Tackle. Opponent takes some damage. A matching delta yields candidates."""

    def test_at_least_one_candidate_returned(self):
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(charizard, bulbasaur)
        opp_max_hp = bulbasaur.max_hp
        # k=38 covers Charizard Tackle vs Bulbasaur low-damage rolls
        candidates = run_candidate_sweep(
            messages=_usedmove_messages("Charizard", "Tackle"),
            hp_deltas=[odelta(bulbasaur.species, (48, 38), max_hp=opp_max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1


# ---------------------------------------------------------------------------
# TestImpossibleHpDelta — impossible delta raises SimulationError
# ---------------------------------------------------------------------------

class TestImpossibleHpDelta:
    """Opponent fully faints from Splash (a non-damaging move) → SimulationError."""

    def test_no_candidates_for_impossible_delta(self):
        pikachu = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(pikachu, bulbasaur)
        opp_max_hp = bulbasaur.max_hp
        with pytest.raises(SimulationError):
            run_candidate_sweep(
                messages=_usedmove_messages("Pikachu", "Splash"),
                hp_deltas=[odelta(bulbasaur.species, (48, 0), max_hp=opp_max_hp)],
                initial_candidates=[_make_candidate(state)],
            )


# ---------------------------------------------------------------------------
# TestKnownActionsFromMessage — USEDMOVE constrains move slot
# ---------------------------------------------------------------------------

class TestKnownActionsFromMessage:
    """USEDMOVE for Tackle must constrain candidates to only Tackle (slot 0)."""

    def test_candidates_use_named_move(self):
        from liveplay.actions import ActionKind
        attacker = make_mon(Species.CHARIZARD, moves=(Move.TACKLE, Move.SPLASH))
        defender = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(attacker, defender)
        opp_max_hp = defender.max_hp
        k_after = 38
        messages = _usedmove_messages("Charizard", "Tackle")
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(defender.species, (48, k_after), max_hp=opp_max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for cand in candidates:
            action0 = cand.unknown_actions.get(0)
            if action0 is not None:
                assert action0.kind == ActionKind.MOVE
                assert action0.move_slot == 0


# ---------------------------------------------------------------------------
# TestCandidateWrapsParent — parent_candidate pointer is set
# ---------------------------------------------------------------------------

class TestCandidateWrapsParent:
    """Each returned Candidate has parent_candidate pointing to the initial candidate."""

    def test_parent_is_set(self):
        pikachu = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(pikachu, bulbasaur)
        initial_candidate = _make_candidate(state)
        messages = _usedmove_messages("Pikachu", "Splash")
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[],
            initial_candidates=[initial_candidate],
        )
        assert len(candidates) >= 1
        for cand in candidates:
            assert cand.parent_candidate is initial_candidate


# ---------------------------------------------------------------------------
# TestDeduplication — identical outcomes collapse
# ---------------------------------------------------------------------------

class TestDeduplication:
    """Multiple (action, roll, crit) combos producing identical final states yield one candidate."""

    def test_deduplication_reduces_to_unique_states(self):
        pikachu = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(pikachu, bulbasaur)
        candidates = run_candidate_sweep(
            messages=_usedmove_messages("Pikachu", "Splash"),
            hp_deltas=[],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) == 1

    def test_unique_states_not_collapsed(self):
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(charizard, bulbasaur)
        opp_max_hp = bulbasaur.max_hp
        candidates = run_candidate_sweep(
            messages=_usedmove_messages("Charizard", "Tackle"),
            hp_deltas=[odelta(bulbasaur.species, (48, 38), max_hp=opp_max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 2


# ---------------------------------------------------------------------------
# TestSequentialDedup — candidates well below 16
# ---------------------------------------------------------------------------

class TestSequentialDedup:
    """Deduplication by damage value must reduce candidates well below 16."""

    def test_sequential_dedup_fewer_than_16_candidates(self):
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(charizard, bulbasaur)
        candidates = run_candidate_sweep(
            messages=_usedmove_messages("Charizard", "Tackle"),
            hp_deltas=[odelta(bulbasaur.species, (48, 38), max_hp=bulbasaur.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert 1 <= len(candidates) < 16


# ---------------------------------------------------------------------------
# TestMoveNameToEnum — utility function
# ---------------------------------------------------------------------------

class TestMoveNameToEnum:
    def test_exact_match(self):
        assert move_name_to_enum("Flamethrower") == Move.FLAMETHROWER

    def test_spaced_name(self):
        assert move_name_to_enum("Thunder Punch") == Move.THUNDER_PUNCH

    def test_garbage(self):
        assert move_name_to_enum("xyzzy12345") is None


# ---------------------------------------------------------------------------
# TestEmptyOpponentHpDelta — empty HP constraint passes/fails correctly
# ---------------------------------------------------------------------------

class TestEmptyOpponentHpDelta:
    def test_no_damage_passes(self):
        from liveplay.sweep_reconcile import check_log_events
        pikachu = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        capturing = CapturingLogger()
        assert check_log_events(capturing, [], [], bulbasaur.species) is True

    def test_unexpected_damage_discarded(self):
        from liveplay.sweep_reconcile import check_log_events
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        capturing = CapturingLogger()
        capturing.handle(LogEvent.DAMAGE, target=bulbasaur.species, amount=25,
                         defender_side=1, source="move")
        assert check_log_events(capturing, [], [], bulbasaur.species) is False


# ---------------------------------------------------------------------------
# TestAccuracyHitInjection — low accuracy stage hit injects ACCURACY=True
# ---------------------------------------------------------------------------

class TestAccuracyHitInjection:
    """A move that visibly hit must not be simulated as a miss."""

    def test_low_accuracy_stage_hit_observed_yields_candidates(self):
        rookidee = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5,
                            stat_stages=(0, 0, 0, 0, 0, -4, 0))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
        state = make_battle(rookidee, poochyena)
        max_hp = poochyena.max_hp
        # Hit observed (no ATTACKMISSED); Peck lv5 does ~6-7 dmg on Poochyena lv5 (max_hp=20)
        # actual_hp 13-14 → k_pixel 31-33 out of display 48 (k = int(hp/max_hp*48))
        messages = [
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["ROOKIDEE", "PECK"]),
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["POOCHYENA", "SPLASH"], side_hint=1),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(poochyena.species, (48, 31), max_hp=max_hp)],
            initial_candidates=[Candidate(state=state)],
        )
        assert len(candidates) >= 1

    def test_observed_miss_still_simulated_as_miss(self):
        rookidee = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5,
                            stat_stages=(0, 0, 0, 0, 0, -1, 0))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
        state = make_battle(rookidee, poochyena)
        messages = [
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["ROOKIDEE", "PECK"]),
            _mr("STRINGID_ATTACKMISSED", constant_name="sText_AttackMissed",
                var_values=["ROOKIDEE"]),
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["POOCHYENA", "SPLASH"], side_hint=1),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[],
            initial_candidates=[Candidate(state=state)],
        )
        assert len(candidates) >= 1


# ---------------------------------------------------------------------------
# TestUninjectedProcDefaultsToNoFire — warn base resolves PROC_FIRES to False
# ---------------------------------------------------------------------------

class TestUninjectedProcDefaultsToNoFire:
    """Defender has STATIC; attacker uses contact move with no proc message → no paralysis."""

    def test_uninjected_proc_returns_candidates(self):
        attacker = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        defender = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), ability=Ability.STATIC)
        state = make_battle(attacker, defender)
        candidates = run_candidate_sweep(
            messages=_usedmove_messages("Charizard", "Tackle"),
            hp_deltas=[odelta(defender.species, (48, 38), max_hp=defender.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for c in candidates:
            assert c.state.sides[1].team[0].hp < defender.max_hp
            assert c.state.sides[1].team[0].status != StatusEnum.PARALYSIS

    def test_observed_proc_forces_paralysis(self):
        """When a paralysis-by-STATIC message IS observed, injection forces PROC_FIRES=True."""
        attacker = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        defender = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), ability=Ability.STATIC)
        state = make_battle(attacker, defender)
        messages = _usedmove_messages("Charizard", "Tackle") + [
            _mr("STRINGID_PKMNWASPARALYZEDBY", var_values=["Bulbasaur", "Static", "Charizard"],
                matched_text="Foe Bulbasaur's Static paralyzed Charizard!"),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(defender.species, (48, 38), max_hp=defender.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for c in candidates:
            assert c.state.sides[0].team[0].status == StatusEnum.PARALYSIS


# ---------------------------------------------------------------------------
# TestUninjectedRngFilteredButValidCandidateSurvives — valid candidate survives
# ---------------------------------------------------------------------------

class TestUninjectedRngFilteredButValidCandidateSurvives:
    """Faster opponent KOs player; low-damage branches expose uninjected ACCURACY,
    are filtered; high-damage (KO) branch matches observed faint and survives."""

    def test_valid_candidate_survives_despite_filtered_sibling(self):
        player = make_mon(Species.BULBASAUR, moves=(Move.TACKLE,), hp=25,
                          stat_stages=(0, 0, 0, 0, 0, -2, 0))
        opponent = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        state = make_battle(player, opponent)
        messages = (
            _usedmove_messages("Charizard", "Tackle", side_hint=1)
            + [_mr("STRINGID_ATTACKERFAINTED", var_values=["Bulbasaur"])]
        )
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[pdelta(player.species, (25, 0))],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for c in candidates:
            assert c.state.sides[0].team[0].hp == 0
            assert c.state.sides[1].team[0].hp == opponent.max_hp


# ---------------------------------------------------------------------------
# TestParalyzedMonThatActedSurvives — FULL_PARALYSIS=False injected
# ---------------------------------------------------------------------------

class TestParalyzedMonThatActedSurvives:
    """Side 0 has PARALYSIS but USEDMOVE appeared — FULL_PARALYSIS=False must be injected."""

    def test_paralyzed_mon_that_acted_survives(self):
        attacker = make_mon(Species.PIKACHU, moves=(Move.TACKLE,), status=StatusEnum.PARALYSIS)
        defender = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(attacker, defender)
        messages = (
            _usedmove_messages("Bulbasaur", "Splash", side_hint=1)
            + _usedmove_messages("Pikachu", "Tackle")
        )
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(defender.species, (48, 40), max_hp=defender.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1


# ---------------------------------------------------------------------------
# TestFlatMessageSecondaryBurn — burn applied/not applied based on message
# ---------------------------------------------------------------------------

class TestFlatMessageSecondaryBurn:
    """Burn secondary: PKMNWASBURNED in messages → all survivors have defender burned."""

    def test_burn_applied_when_message_present(self):
        attacker = make_mon(Species.CHARIZARD, moves=(Move.EMBER,))
        defender = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(attacker, defender)
        messages = (
            _usedmove_messages("Charizard", "Ember")
            + [_mr("STRINGID_PKMNWASBURNED", var_values=["Bulbasaur"],
                   matched_text="Foe Bulbasaur was burned!")]
        )
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(defender.species, (48, 22), (22, 16), max_hp=defender.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for c in candidates:
            opp_status = c.state.sides[1].team[0].status
            assert opp_status == StatusEnum.BURN, f"Expected BURN, got {opp_status}"

    def test_burn_not_applied_when_no_message(self):
        attacker = make_mon(Species.CHARIZARD, moves=(Move.EMBER,))
        defender = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(attacker, defender)
        messages = _usedmove_messages("Charizard", "Ember")
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(defender.species, (48, 16), max_hp=defender.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for c in candidates:
            opp_status = c.state.sides[1].team[0].status
            assert opp_status != StatusEnum.BURN, f"Expected no BURN, got {opp_status}"


# ---------------------------------------------------------------------------
# TestAmbiguousDualSecondariesRaise — both sides status-secondary → raises
# ---------------------------------------------------------------------------

class TestAmbiguousDualSecondariesRaise:
    """Both sides use status-secondary moves in flat mode → SimulationError."""

    def test_ambiguous_dual_secondaries_raise(self):
        attacker = make_mon(Species.CHARIZARD, moves=(Move.EMBER,))
        defender = make_mon(Species.BULBASAUR, moves=(Move.BODY_SLAM,))
        state = make_battle(attacker, defender)
        messages = (
            _usedmove_messages("Charizard", "Ember")
            + _usedmove_messages("Bulbasaur", "Body Slam", side_hint=1)
        )
        with pytest.raises(SimulationError):
            run_candidate_sweep(
                messages=messages,
                hp_deltas=[odelta(defender.species, (48, 17), max_hp=defender.max_hp)],
                initial_candidates=[_make_candidate(state)],
            )


# ---------------------------------------------------------------------------
# TestNoCrossCallContamination — two runs produce identical results
# ---------------------------------------------------------------------------

class TestNoCrossCallContamination:
    """run_candidate_sweep must produce identical results when called twice with same inputs."""

    def test_same_inputs_twice_identical_results(self):
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(charizard, bulbasaur)
        kwargs = dict(
            messages=_usedmove_messages("Charizard", "Tackle"),
            hp_deltas=[odelta(bulbasaur.species, (48, 38), max_hp=bulbasaur.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        c1 = run_candidate_sweep(**kwargs)
        c2 = run_candidate_sweep(**kwargs)
        hps1 = sorted(c.state.sides[1].team[0].hp for c in c1)
        hps2 = sorted(c.state.sides[1].team[0].hp for c in c2)
        assert hps1 == hps2

    def test_paralysis_scenario_does_not_poison_clean_scenario(self):
        attacker_p = make_mon(Species.PIKACHU, moves=(Move.TACKLE,), status=StatusEnum.PARALYSIS)
        defender = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state_p = make_battle(attacker_p, defender)
        run_candidate_sweep(
            messages=(
                _usedmove_messages("Bulbasaur", "Splash", side_hint=1)
                + _usedmove_messages("Pikachu", "Tackle")
            ),
            hp_deltas=[odelta(defender.species, (48, 40), max_hp=defender.max_hp)],
            initial_candidates=[_make_candidate(state_p)],
        )
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state_c = make_battle(charizard, bulbasaur)
        kwargs = dict(
            messages=_usedmove_messages("Charizard", "Tackle"),
            hp_deltas=[odelta(bulbasaur.species, (48, 38), max_hp=bulbasaur.max_hp)],
            initial_candidates=[_make_candidate(state_c)],
        )
        c_alone = run_candidate_sweep(**kwargs)
        c_after = run_candidate_sweep(**kwargs)
        hps_alone = sorted(c.state.sides[1].team[0].hp for c in c_alone)
        hps_after = sorted(c.state.sides[1].team[0].hp for c in c_after)
        assert hps_alone == hps_after


# ---------------------------------------------------------------------------
# TestEmptyObservedOrderRaisesSimulationError — no USEDMOVE → raises
# ---------------------------------------------------------------------------

class TestEmptyObservedOrderRaisesSimulationError:
    """No USEDMOVE messages → empty observed order → no candidates → SimulationError."""

    def test_no_usedmove_messages_raises_simulation_error(self):
        pikachu = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(pikachu, bulbasaur)
        non_move_message = _mr("STRINGID_PKMNISPARALYZED", var_values=["Pikachu"])
        with pytest.raises(SimulationError):
            run_candidate_sweep(
                messages=[non_move_message],
                hp_deltas=[],
                initial_candidates=[_make_candidate(state)],
            )


# ---------------------------------------------------------------------------
# TestOneMoverRngSequenceShape — single mover rng_sequence = length 3
# ---------------------------------------------------------------------------

class TestOneMoverRngSequenceShape:
    """Single USEDMOVE yields candidates with rng_sequence length 3:
    [(DAMAGE_ROLL,_), (CRIT,_), (SPEED_TIE,_)]."""

    def test_one_mover_rng_sequence_length_three(self):
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(charizard, bulbasaur)
        candidates = run_candidate_sweep(
            messages=_usedmove_messages("Charizard", "Tackle"),
            hp_deltas=[odelta(bulbasaur.species, (48, 38), max_hp=bulbasaur.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for cand in candidates:
            seq = cand.rng_sequence
            assert len(seq) == 3, f"Expected length 3, got {len(seq)}: {seq}"
            assert seq[0][0] == RNGEvent.DAMAGE_ROLL
            assert seq[1][0] == RNGEvent.CRIT
            assert seq[2][0] == RNGEvent.SPEED_TIE

    def test_one_mover_hp_delta_matches_end_state(self):
        from liveplay.hp_stability import hp_range
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(charizard, bulbasaur)
        opp_max_hp = bulbasaur.max_hp
        candidates = run_candidate_sweep(
            messages=_usedmove_messages("Charizard", "Tackle"),
            hp_deltas=[odelta(bulbasaur.species, (48, 38), max_hp=opp_max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        hp_min, hp_max = hp_range(38, opp_max_hp)
        for cand in candidates:
            opp_hp = cand.state.sides[1].team[0].hp
            assert hp_min <= opp_hp <= hp_max, (
                f"End-state HP {opp_hp} not in expected range [{hp_min}, {hp_max}]"
            )


# ---------------------------------------------------------------------------
# TestTwoMoverInterleavedRngSequence — two-mover rng_sequence = length 5, interleaved
# ---------------------------------------------------------------------------

class TestTwoMoverInterleavedRngSequence:
    """Both sides use Splash; rng_sequence must be the interleaved format, length 5."""

    def test_two_mover_rng_sequence_length_five(self):
        electrode = make_mon(Species.ELECTRODE, moves=(Move.SPLASH,))
        slowpoke = make_mon(Species.SLOWPOKE, moves=(Move.SPLASH,))
        state = make_battle(electrode, slowpoke)
        messages = (
            _usedmove_messages("Electrode", "Splash")
            + _usedmove_messages("Slowpoke", "Splash", side_hint=1)
        )
        candidates = run_candidate_sweep(
            messages=messages, hp_deltas=[], initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for cand in candidates:
            seq = cand.rng_sequence
            assert len(seq) == 5, f"Expected length 5, got {len(seq)}: {seq}"

    def test_two_mover_rng_sequence_is_interleaved(self):
        electrode = make_mon(Species.ELECTRODE, moves=(Move.SPLASH,))
        slowpoke = make_mon(Species.SLOWPOKE, moves=(Move.SPLASH,))
        state = make_battle(electrode, slowpoke)
        messages = (
            _usedmove_messages("Electrode", "Splash")
            + _usedmove_messages("Slowpoke", "Splash", side_hint=1)
        )
        candidates = run_candidate_sweep(
            messages=messages, hp_deltas=[], initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for cand in candidates:
            seq = cand.rng_sequence
            expected_events = [
                RNGEvent.DAMAGE_ROLL, RNGEvent.CRIT,
                RNGEvent.DAMAGE_ROLL, RNGEvent.CRIT,
                RNGEvent.SPEED_TIE,
            ]
            actual_events = [entry[0] for entry in seq]
            assert actual_events == expected_events, (
                f"Expected interleaved {[e.name for e in expected_events]}, "
                f"got {[e.name for e in actual_events]}"
            )

    def test_two_mover_damage_roll_entries_in_observed_order(self):
        electrode = make_mon(Species.ELECTRODE, moves=(Move.SPLASH,))
        slowpoke = make_mon(Species.SLOWPOKE, moves=(Move.SPLASH,))
        state = make_battle(electrode, slowpoke)
        messages = (
            _usedmove_messages("Electrode", "Splash")
            + _usedmove_messages("Slowpoke", "Splash", side_hint=1)
        )
        candidates = run_candidate_sweep(
            messages=messages, hp_deltas=[], initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for cand in candidates:
            seq = cand.rng_sequence
            assert seq[0][0] == RNGEvent.DAMAGE_ROLL
            assert seq[2][0] == RNGEvent.DAMAGE_ROLL


# ---------------------------------------------------------------------------
# TestInterleavedFormatRegression — guards against regression to old format
# ---------------------------------------------------------------------------

class TestInterleavedFormatRegression:
    """Guards the new interleaved rng_sequence format against regression."""

    def test_single_mover_rng_sequence_shape(self):
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(charizard, bulbasaur)
        candidates = run_candidate_sweep(
            messages=_usedmove_messages("Charizard", "Tackle"),
            hp_deltas=[odelta(bulbasaur.species, (48, 38), max_hp=bulbasaur.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for cand in candidates:
            seq = cand.rng_sequence
            assert len(seq) == 3
            assert seq[0][0] == RNGEvent.DAMAGE_ROLL
            assert seq[1][0] == RNGEvent.CRIT
            assert seq[2][0] == RNGEvent.SPEED_TIE

    def test_two_mover_sequence_is_not_old_format(self):
        """Old format: [DAMAGE_ROLL, DAMAGE_ROLL, CRIT, CRIT, SPEED_TIE]; new has CRIT at index 1."""
        electrode = make_mon(Species.ELECTRODE, moves=(Move.SPLASH,))
        slowpoke = make_mon(Species.SLOWPOKE, moves=(Move.SPLASH,))
        state = make_battle(electrode, slowpoke)
        messages = (
            _usedmove_messages("Electrode", "Splash")
            + _usedmove_messages("Slowpoke", "Splash", side_hint=1)
        )
        candidates = run_candidate_sweep(
            messages=messages, hp_deltas=[], initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for cand in candidates:
            seq = cand.rng_sequence
            assert seq[1][0] != RNGEvent.DAMAGE_ROLL, (
                "rng_sequence[1] is DAMAGE_ROLL — OLD non-interleaved format detected."
            )


# ---------------------------------------------------------------------------
# TestTwoMoverDeterminism — same inputs twice → identical rng_sequences
# ---------------------------------------------------------------------------

class TestTwoMoverDeterminism:
    """run_candidate_sweep is deterministic across two identical calls."""

    def test_same_two_mover_inputs_twice_identical_rng_sequences(self):
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(charizard, bulbasaur)
        messages = (
            _usedmove_messages("Charizard", "Tackle")
            + _usedmove_messages("Bulbasaur", "Splash", side_hint=1)
        )
        kwargs = dict(
            messages=messages,
            hp_deltas=[odelta(bulbasaur.species, (48, 38), max_hp=bulbasaur.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        c1 = run_candidate_sweep(**kwargs)
        c2 = run_candidate_sweep(**kwargs)
        seqs1 = sorted(str(c.rng_sequence) for c in c1)
        seqs2 = sorted(str(c.rng_sequence) for c in c2)
        assert seqs1 == seqs2


# ---------------------------------------------------------------------------
# TestMultiHitInLoopRngSequenceShape — multi-hit mover uses tuple roll/crit entries
# ---------------------------------------------------------------------------

class TestMultiHitInLoopRngSequenceShape:
    """Two-mover turn where one mover uses a multi-hit move; per-hit tuple entries."""

    def _make_state(self):
        dragonite = make_mon(Species.DRAGONITE, moves=(Move.DUAL_WINGBEAT,))
        blissey = make_mon(Species.BLISSEY, moves=(Move.TACKLE,))
        return make_battle(dragonite, blissey), dragonite, blissey

    def _usedmove_with_hits(self, attacker, move_name, n_hits):
        msgs = [_mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                    var_values=[attacker, move_name])]
        if n_hits > 1:
            msgs.append(_mr("STRINGID_HITXTIMES", var_values=[str(n_hits)]))
        return msgs

    def test_multi_hit_mover_has_tuple_roll_and_crit_entries(self):
        state, dragonite, blissey = self._make_state()
        messages = (
            self._usedmove_with_hits("Dragonite", "Dual Wingbeat", 2)
            + [_mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                   var_values=["Blissey", "Tackle"], side_hint=1)]
        )
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[
                pdelta(dragonite.species, (166, 159)),
                odelta(blissey.species, (48, 29), (29, 11), max_hp=blissey.max_hp),
            ],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for cand in candidates:
            seq = cand.rng_sequence
            assert len(seq) == 5, f"Expected length 5, got {len(seq)}: {seq}"
            assert seq[0][0] == RNGEvent.DAMAGE_ROLL
            assert seq[1][0] == RNGEvent.CRIT
            assert seq[2][0] == RNGEvent.DAMAGE_ROLL
            assert seq[3][0] == RNGEvent.CRIT
            assert seq[4][0] == RNGEvent.SPEED_TIE
            dragonite_roll = seq[0][1]
            dragonite_crit = seq[1][1]
            assert isinstance(dragonite_roll, tuple), (
                f"Multi-hit mover's DAMAGE_ROLL must be tuple, got {type(dragonite_roll)}"
            )
            assert isinstance(dragonite_crit, tuple), (
                f"Multi-hit mover's CRIT must be tuple, got {type(dragonite_crit)}"
            )
            assert len(dragonite_roll) == 2
            assert len(dragonite_crit) == 2
            blissey_roll = seq[2][1]
            blissey_crit = seq[3][1]
            assert not isinstance(blissey_roll, tuple), (
                f"Single-hit mover's DAMAGE_ROLL must be scalar, got {type(blissey_roll)}"
            )
            assert not isinstance(blissey_crit, tuple), (
                f"Single-hit mover's CRIT must be scalar, got {type(blissey_crit)}"
            )


# ---------------------------------------------------------------------------
# TestCritAttributionInSweep — per-mover crit from message position
# ---------------------------------------------------------------------------

class TestCritAttributionInSweep:
    """run_candidate_sweep must attribute crits to the mover whose USEDMOVE immediately
    preceded the CRITICALHIT message."""

    def _make_state(self):
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.TACKLE,))
        return make_battle(charizard, bulbasaur), charizard, bulbasaur

    def test_b1_only_second_mover_crits(self):
        """USEDMOVE(0), USEDMOVE(1), CRITICALHIT → mover 1 crits, mover 0 does not."""
        state, charizard, bulbasaur = self._make_state()
        messages = [
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["Charizard", "Tackle"]),
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["Bulbasaur", "Tackle"], side_hint=1),
            _mr("STRINGID_CRITICALHIT"),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[
                pdelta(charizard.species, (153, 134)),
                odelta(bulbasaur.species, (48, 38), max_hp=bulbasaur.max_hp),
            ],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1, "No candidates returned — check HP deltas"
        for cand in candidates:
            seq = cand.rng_sequence
            assert seq[1][1] is False, (
                f"rng_sequence[1][1] should be False (mover 0 did NOT crit), got {seq[1][1]}"
            )
            assert seq[3][1] is True, (
                f"rng_sequence[3][1] should be True (mover 1 DID crit), got {seq[3][1]}"
            )

    def test_b2_only_first_mover_crits(self):
        """USEDMOVE(0), CRITICALHIT, USEDMOVE(1) → mover 0 crits, mover 1 does not."""
        state, charizard, bulbasaur = self._make_state()
        messages = [
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["Charizard", "Tackle"]),
            _mr("STRINGID_CRITICALHIT"),
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["Bulbasaur", "Tackle"], side_hint=1),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[
                pdelta(charizard.species, (153, 141)),
                odelta(bulbasaur.species, (48, 32), max_hp=bulbasaur.max_hp),
            ],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1, "No candidates returned — check HP deltas"
        for cand in candidates:
            seq = cand.rng_sequence
            assert seq[1][1] is True, (
                f"rng_sequence[1][1] should be True (mover 0 DID crit), got {seq[1][1]}"
            )
            assert seq[3][1] is False, (
                f"rng_sequence[3][1] should be False (mover 1 did NOT crit), got {seq[3][1]}"
            )


# ---------------------------------------------------------------------------
# TestMultiHitSweep — multi-hit move integration
# ---------------------------------------------------------------------------

class TestMultiHitSweep:
    """Integration tests for multi-hit move handling in run_candidate_sweep."""

    def _make_state(self):
        dragonite = make_mon(Species.DRAGONITE, moves=(Move.DUAL_WINGBEAT,))
        blissey = make_mon(Species.BLISSEY)
        return make_battle(dragonite, blissey), dragonite, blissey

    def _usedmove_with_hits(self, attacker, move_name, n_hits):
        msgs = [_mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                    var_values=[attacker, move_name])]
        if n_hits > 1:
            msgs.append(_mr("STRINGID_HITXTIMES", var_values=[str(n_hits)]))
        return msgs

    def test_multi_hit_sweep_two_hit_consistent_deltas(self):
        """Two-hit Dual Wingbeat with consistent per-hit HP deltas yields ≥1 candidate."""
        state, dragonite, blissey = self._make_state()
        messages = self._usedmove_with_hits("Dragonite", "Dual Wingbeat", 2)
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(blissey.species, (48, 29), (29, 11), max_hp=blissey.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1

    def test_multi_hit_sweep_impossible_deltas(self):
        """Per-hit HP deltas implying more damage than possible → SimulationError."""
        state, dragonite, blissey = self._make_state()
        messages = self._usedmove_with_hits("Dragonite", "Dual Wingbeat", 2)
        with pytest.raises(SimulationError):
            run_candidate_sweep(
                messages=messages,
                hp_deltas=[odelta(blissey.species, (48, 0), (0, 0), max_hp=blissey.max_hp)],
                initial_candidates=[_make_candidate(state)],
            )

    def test_multi_hit_on_second_side_yields_candidates(self):
        """Multi-hit move by the slower mover (side 1) must not zero out candidates."""
        electrode = make_mon(Species.ELECTRODE, moves=(Move.SPLASH,))
        dragonite = make_mon(Species.DRAGONITE, moves=(Move.DUAL_WINGBEAT,))
        state = make_battle(electrode, dragonite)
        messages = (
            _usedmove_messages("Electrode", "Splash")
            + [_mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                   var_values=["Dragonite", "Dual Wingbeat"], side_hint=1,
                   matched_text="Foe Dragonite used Dual Wingbeat!")]
            + [_mr("STRINGID_HITXTIMES", var_values=["2"])]
        )
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[pdelta(electrode.species, (135, 114), (114, 93))],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1

    def test_multi_hit_requires_mixed_per_hit_damage(self):
        """A multi-hit KO whose only valid solution mixes per-hit damage must survive."""
        rookidee = make_mon(Species.ROOKIDEE, moves=(Move.FURY_ATTACK,), level=5)
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5, hp=10)
        state = make_battle(rookidee, poochyena)
        faint = MatchResult(
            string_id="STRINGID_TARGETFAINTED", id_value=29,
            constant_name="sText_TargetFainted", var_values=["POOCHYENA"],
            score=0, matched_text="Foe POOCHYENA fainted!", slot_labels=[],
        )
        exp = MatchResult(
            string_id="STRINGID_PKMNGAINEDEXP", id_value=13,
            constant_name="sText_PkmnGainedEXP", var_values=["ROOKIDEE", "57"],
            score=0, matched_text="ROOKIDEE gained 57 Exp. Points!", slot_labels=[],
        )
        messages = (
            _usedmove_messages("ROOKIDEE", "Fury Attack")
            + [_mr("STRINGID_HITXTIMES", var_values=["5"])]
            + [faint, exp]
        )
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(poochyena.species, (24, 16), (16, 12), (12, 7), (7, 2), (2, 0),
                               max_hp=poochyena.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1

    def test_multi_hit_player_side_ko_overkill(self):
        """KO-overkill relaxation applies when the PLAYER is the multi-hit target."""
        electrode = make_mon(Species.ELECTRODE, moves=(Move.SPLASH,), level=50, hp=35)
        dragonite = make_mon(Species.DRAGONITE, moves=(Move.DUAL_WINGBEAT,), level=50)
        state = make_battle(electrode, dragonite)
        faint = MatchResult(
            string_id="STRINGID_TARGETFAINTED", id_value=29,
            constant_name="sText_TargetFainted", var_values=["ELECTRODE"],
            score=0, matched_text="ELECTRODE fainted!", slot_labels=[],
        )
        messages = (
            _usedmove_messages("Electrode", "Splash")
            + [_mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                   var_values=["Dragonite", "Dual Wingbeat"], side_hint=1,
                   matched_text="Foe Dragonite used Dual Wingbeat!")]
            + [_mr("STRINGID_HITXTIMES", var_values=["2"])]
            + [faint]
        )
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[pdelta(electrode.species, (35, 15), (15, 0))],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1

    def test_multi_hit_plus_single_hit_same_turn_sweep(self):
        """Full-sweep repro: multi-hit by side 0 plus a damaging single-hit by side 1 yields candidates."""
        dragonite = make_mon(Species.DRAGONITE, moves=(Move.DUAL_WINGBEAT,))
        blissey = make_mon(Species.BLISSEY, moves=(Move.TACKLE,))
        state = make_battle(dragonite, blissey)
        messages = [
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["Dragonite", "Dual Wingbeat"]),
            _mr("STRINGID_HITXTIMES", var_values=["2"]),
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["Blissey", "Tackle"], side_hint=1),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[
                pdelta(dragonite.species, (166, 159)),
                odelta(blissey.species, (48, 29), (29, 11), max_hp=blissey.max_hp),
            ],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1

    def test_multi_hit_oran_heal_between_hits(self):
        """Mid-multihit Oran Berry heal corroborated by heal message survives."""
        electrode = make_mon(Species.ELECTRODE, moves=(Move.SPLASH,), level=50, hp=75,
                             item=Item.ORAN_BERRY)
        dragonite = make_mon(Species.DRAGONITE, moves=(Move.DUAL_WINGBEAT,), level=50)
        state = make_battle(electrode, dragonite)
        heal = _mr("STRINGID_PKMNSITEMRESTOREDHEALTH",
                   constant_name="sText_PkmnsItemRestoredHealth",
                   var_values=["Electrode", "Oran Berry"])
        messages = (
            _usedmove_messages("Electrode", "Splash")
            + [_mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                   var_values=["Dragonite", "Dual Wingbeat"], side_hint=1,
                   matched_text="Foe Dragonite used Dual Wingbeat!")]
            + [_mr("STRINGID_HITXTIMES", var_values=["2"])]
            + [heal]
        )
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[pdelta(electrode.species, (75, 51), (51, 61), (61, 37))],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1

    def test_multi_hit_hp_increase_without_heal_message_fails(self):
        """HP-increase bar reading with no corroborating heal message raises SimulationError."""
        electrode = make_mon(Species.ELECTRODE, moves=(Move.SPLASH,), level=50, hp=75,
                             item=Item.ORAN_BERRY)
        dragonite = make_mon(Species.DRAGONITE, moves=(Move.DUAL_WINGBEAT,), level=50)
        state = make_battle(electrode, dragonite)
        messages = (
            _usedmove_messages("Electrode", "Splash")
            + [_mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                   var_values=["Dragonite", "Dual Wingbeat"], side_hint=1,
                   matched_text="Foe Dragonite used Dual Wingbeat!")]
            + [_mr("STRINGID_HITXTIMES", var_values=["2"])]
        )
        with pytest.raises(SimulationError):
            run_candidate_sweep(
                messages=messages,
                hp_deltas=[pdelta(electrode.species, (75, 51), (51, 61), (61, 37))],
                initial_candidates=[_make_candidate(state)],
            )


# ---------------------------------------------------------------------------
# TestMetronomeSweep — Metronome two-USEDMOVE integration
# ---------------------------------------------------------------------------

class TestMetronomeSweep:
    """A Metronome turn (two USEDMOVE lines) must collapse and not over-count movers."""

    def _state(self):
        player = make_mon(Species.SKITTY, moves=(Move.SPLASH,), level=10)
        foe = make_mon(Species.SWIRLIX, moves=(Move.METRONOME,), level=20)
        return make_battle(player, foe)

    def test_metronome_call_produces_candidates(self):
        messages = [
            _mr("STRINGID_USEDMOVE", var_values=["Swirlix", "Metronome"], side_hint=1,
                constant_name="sText_AttackerUsedMove"),
            _mr("STRINGID_USEDMOVE", var_values=["Swirlix", "Splash"], side_hint=1,
                constant_name="sText_AttackerUsedMove"),
            _mr("STRINGID_USEDMOVE", var_values=["Skitty", "Splash"], side_hint=0,
                constant_name="sText_AttackerUsedMove"),
        ]
        candidates = run_candidate_sweep(
            messages=messages, hp_deltas=[],
            initial_candidates=[Candidate(state=self._state())],
        )
        assert len(candidates) >= 1

    def test_unknown_metronome_call_hard_crashes_sweep(self):
        messages = [
            _mr("STRINGID_USEDMOVE", var_values=["Swirlix", "Metronome"], side_hint=1,
                constant_name="sText_AttackerUsedMove"),
            _mr("STRINGID_USEDMOVE", var_values=["Swirlix", "Worry Seed"], side_hint=1,
                constant_name="sText_AttackerUsedMove"),
        ]
        with pytest.raises(SimulationError):
            run_candidate_sweep(
                messages=messages, hp_deltas=[],
                initial_candidates=[Candidate(state=self._state())],
            )


# ---------------------------------------------------------------------------
# TestHitcountAttribution — HITXTIMES counts only the attacker's hits
# ---------------------------------------------------------------------------

class TestHitcountAttribution:
    """HITXTIMES must count only the multi-hit attacker's strikes, not all HITCOUNT events."""

    def _hitxtimes_after(self, attacker, move_name, n_hits, *, foe=False):
        prefix = "Foe " if foe else ""
        return [
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=[attacker, move_name], side_hint=1 if foe else 0,
                matched_text=f"{prefix}{attacker} used {move_name}!"),
            _mr("STRINGID_HITXTIMES", var_values=[str(n_hits)]),
        ]

    def test_check_log_events_ignores_other_attackers_hitcount(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.HITCOUNT, user=Species.DRAGONITE, side=0)
        capturing.handle(LogEvent.HITCOUNT, user=Species.DRAGONITE, side=0)
        capturing.handle(LogEvent.HITCOUNT, user=Species.BLISSEY, side=1)
        messages = self._hitxtimes_after("Dragonite", "Dual Wingbeat", 2) + [
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["Blissey", "Tackle"], matched_text="Foe Blissey used Tackle!"),
        ]
        assert check_log_events(capturing, messages, [(48, 29)], Species.BLISSEY) is True

    def test_check_log_events_attributed_count_mismatch_fails(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.HITCOUNT, user=Species.DRAGONITE, side=0)
        capturing.handle(LogEvent.HITCOUNT, user=Species.BLISSEY, side=1)
        messages = self._hitxtimes_after("Dragonite", "Dual Wingbeat", 2)
        assert check_log_events(capturing, messages, [(48, 29)], Species.BLISSEY) is False

    def test_check_log_events_dual_multi_hit_attribution(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        for _ in range(2):
            capturing.handle(LogEvent.HITCOUNT, user=Species.DRAGONITE, side=0)
        for _ in range(3):
            capturing.handle(LogEvent.HITCOUNT, user=Species.BLISSEY, side=1)
        # Use Blissey as stand-in if CINCCINO absent; test the logic, not the species
        capturing2 = CapturingLogger()
        for _ in range(2):
            capturing2.handle(LogEvent.HITCOUNT, user=Species.DRAGONITE, side=0)
        for _ in range(3):
            capturing2.handle(LogEvent.HITCOUNT, user=Species.BLISSEY, side=1)
        messages = (
            self._hitxtimes_after("Dragonite", "Dual Wingbeat", 2)
            + self._hitxtimes_after("Blissey", "Tackle", 3, foe=True)
        )
        assert check_log_events(capturing2, messages, [(48, 29)], Species.BLISSEY) is True
        wrong_messages = (
            self._hitxtimes_after("Dragonite", "Dual Wingbeat", 2)
            + self._hitxtimes_after("Blissey", "Tackle", 2, foe=True)
        )
        assert check_log_events(capturing2, wrong_messages, [(48, 29)], Species.BLISSEY) is False

    def test_hitxtimes_without_usedmove_raises(self):
        from liveplay.sweep_reconcile import check_log_events
        capturing = CapturingLogger()
        capturing.handle(LogEvent.HITCOUNT, user=Species.DRAGONITE, side=0)
        messages = [_mr("STRINGID_HITXTIMES", var_values=["2"])]
        with pytest.raises(SimulationError):
            check_log_events(capturing, messages, [(48, 29)], Species.BLISSEY)

    def test_multi_hit_plus_single_hit_same_turn_sweep(self):
        """Full-sweep repro of the recorded failure: multi-hit + single-hit same turn."""
        dragonite = make_mon(Species.DRAGONITE, moves=(Move.DUAL_WINGBEAT,))
        blissey = make_mon(Species.BLISSEY, moves=(Move.TACKLE,))
        state = make_battle(dragonite, blissey)
        messages = self._hitxtimes_after("Dragonite", "Dual Wingbeat", 2) + [
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["Blissey", "Tackle"], side_hint=1),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[
                pdelta(dragonite.species, (166, 159)),
                odelta(blissey.species, (48, 29), (29, 11), max_hp=blissey.max_hp),
            ],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1


# ---------------------------------------------------------------------------
# TestIdentityBoundHpMatch — _check_hp_match by species identity
# ---------------------------------------------------------------------------

class TestIdentityBoundHpMatch:
    """_check_hp_match validates HP by identity (species), not slot index."""

    def test_player_exact_match(self):
        skitty = make_mon(Species.SKITTY, hp=18)
        foe = make_mon(Species.BULBASAUR)
        state = make_battle(skitty, foe)
        assert _check_hp_match(state, [pdelta(Species.SKITTY, (25, 18))]) is True

    def test_player_exact_mismatch(self):
        skitty = make_mon(Species.SKITTY, hp=19)
        foe = make_mon(Species.BULBASAUR)
        state = make_battle(skitty, foe)
        assert _check_hp_match(state, [pdelta(Species.SKITTY, (25, 18))]) is False

    def test_bug8_switch_case_correct_species(self):
        """Bug 8: Skitty sent in mid-turn; record for SKITTY validated against Skitty (hp=18)."""
        rookidee = make_mon(Species.ROOKIDEE)
        skitty = make_mon(Species.SKITTY, hp=18)
        foe = make_mon(Species.BULBASAUR)
        player_side = SideState(team=[rookidee, skitty], active_indices=[1])
        foe_side = SideState(team=[foe], active_indices=[0])
        state = BattleState(sides=(player_side, foe_side))
        assert _check_hp_match(state, [pdelta(Species.SKITTY, (25, 18))]) is True

    def test_bug8_switch_case_wrong_final_hp(self):
        rookidee = make_mon(Species.ROOKIDEE)
        skitty = make_mon(Species.SKITTY, hp=17)
        foe = make_mon(Species.BULBASAUR)
        player_side = SideState(team=[rookidee, skitty], active_indices=[1])
        foe_side = SideState(team=[foe], active_indices=[0])
        state = BattleState(sides=(player_side, foe_side))
        assert _check_hp_match(state, [pdelta(Species.SKITTY, (25, 18))]) is False

    def test_opponent_krange_match(self):
        from liveplay.hp_stability import hp_range
        foe = make_mon(Species.BULBASAUR)
        max_hp = foe.max_hp
        hp_min, _ = hp_range(40, max_hp)
        foe_in_range = make_mon(Species.BULBASAUR, hp=hp_min)
        player = make_mon(Species.CHARIZARD)
        state = make_battle(player, foe_in_range)
        assert _check_hp_match(state, [odelta(Species.BULBASAUR, (48, 40), max_hp=max_hp)]) is True

    def test_opponent_krange_mismatch(self):
        from liveplay.hp_stability import hp_range
        foe = make_mon(Species.BULBASAUR)
        max_hp = foe.max_hp
        _, hp_max = hp_range(40, max_hp)
        foe_out = make_mon(Species.BULBASAUR, hp=hp_max + 5)
        player = make_mon(Species.CHARIZARD)
        state = make_battle(player, foe_out)
        assert _check_hp_match(state, [odelta(Species.BULBASAUR, (48, 40), max_hp=max_hp)]) is False

    def test_unknown_species_raises(self):
        player = make_mon(Species.CHARIZARD)
        foe = make_mon(Species.BULBASAUR)
        state = make_battle(player, foe)
        with pytest.raises(SimulationError):
            _check_hp_match(state, [pdelta(Species.SKITTY, (25, 18))])

    def test_same_species_disambiguated_by_active_slot(self):
        """Two same-species mons → validate the active-slot one."""
        skitty_a = make_mon(Species.SKITTY, hp=18)
        skitty_b = make_mon(Species.SKITTY, hp=25)
        foe = make_mon(Species.BULBASAUR)
        player_side = SideState(team=[skitty_a, skitty_b], active_indices=[0])
        foe_side = SideState(team=[foe], active_indices=[0])
        state = BattleState(sides=(player_side, foe_side))
        assert _check_hp_match(state, [pdelta(Species.SKITTY, (25, 18))]) is True

    def test_same_species_disambiguated_active_slot_mismatch(self):
        skitty_a = make_mon(Species.SKITTY, hp=20)
        skitty_b = make_mon(Species.SKITTY, hp=18)
        foe = make_mon(Species.BULBASAUR)
        player_side = SideState(team=[skitty_a, skitty_b], active_indices=[0])
        foe_side = SideState(team=[foe], active_indices=[0])
        state = BattleState(sides=(player_side, foe_side))
        assert _check_hp_match(state, [pdelta(Species.SKITTY, (25, 18))]) is False

    def test_empty_deltas_record_skipped(self):
        skitty = make_mon(Species.SKITTY, hp=99)
        foe = make_mon(Species.BULBASAUR)
        state = make_battle(skitty, foe)
        assert _check_hp_match(state, [pdelta(Species.SKITTY)]) is True

    def test_faint_record_validates_unique_species_replacement(self):
        """Unique-species faint record validates against the fainted mon (hp=0)."""
        krabby = make_mon(Species.KRABBY, hp=0)
        yanma = make_mon(Species.YANMA)
        player = make_mon(Species.SKITTY, hp=24)
        foe_side = SideState(team=[krabby, yanma], active_indices=[1])
        player_side = SideState(team=[player], active_indices=[0])
        state = BattleState(sides=(player_side, foe_side))
        assert _check_hp_match(state, [odelta(Species.KRABBY, (1, 0), max_hp=krabby.max_hp)]) is True

    def test_faint_record_validates_fainted_same_species_not_replacement(self):
        """Issue 29: foe MAGIKARP faints and is replaced by a second MAGIKARP same turn;
        faint record validates against the fainted one (hp=0), not the active replacement."""
        mk_fainted = make_mon(Species.MAGIKARP, hp=0)
        mk_replacement = make_mon(Species.MAGIKARP)
        player = make_mon(Species.SKITTY, hp=24)
        foe_side = SideState(team=[mk_fainted, mk_replacement], active_indices=[1])
        player_side = SideState(team=[player], active_indices=[0])
        state = BattleState(sides=(player_side, foe_side))
        assert _check_hp_match(
            state, [odelta(Species.MAGIKARP, (14, 0), max_hp=mk_fainted.max_hp)]
        ) is True


# ---------------------------------------------------------------------------
# TestCheckHpMatchTwoPlayerSlots — doubles player HP validation
# ---------------------------------------------------------------------------

class TestCheckHpMatchTwoPlayerSlots:
    """_check_hp_match validates both side-0 slots in a doubles state."""

    def _build_state(self, hp0, hp1):
        mon0 = make_mon(Species.CHARIZARD, hp=hp0)
        mon1 = make_mon(Species.BLASTOISE, hp=hp1)
        opp0 = make_mon(Species.BULBASAUR, hp=100)
        opp1 = make_mon(Species.SQUIRTLE, hp=80)
        return make_doubles_battle(mon0, mon1, opp0, opp1)

    def test_both_slots_match(self):
        state = self._build_state(200, 150)
        records = [
            pdelta(Species.CHARIZARD, (210, 200), slot=0),
            pdelta(Species.BLASTOISE, (160, 150), slot=1),
        ]
        assert _check_hp_match(state, records) is True

    def test_first_slot_mismatch(self):
        state = self._build_state(200, 150)
        records = [
            pdelta(Species.CHARIZARD, (210, 199), slot=0),
            pdelta(Species.BLASTOISE, (160, 150), slot=1),
        ]
        assert _check_hp_match(state, records) is False

    def test_second_slot_mismatch(self):
        state = self._build_state(200, 150)
        records = [
            pdelta(Species.CHARIZARD, (210, 200), slot=0),
            pdelta(Species.BLASTOISE, (160, 140), slot=1),
        ]
        assert _check_hp_match(state, records) is False

    def test_empty_slot_skipped(self):
        state = self._build_state(200, 150)
        records = [
            pdelta(Species.CHARIZARD, (210, 200), slot=0),
            pdelta(Species.BLASTOISE, slot=1),
        ]
        assert _check_hp_match(state, records) is True


# ---------------------------------------------------------------------------
# TestCheckHpMatchOpponentPerSlotKRange — doubles opponent k-pixel validation
# ---------------------------------------------------------------------------

class TestCheckHpMatchOpponentPerSlotKRange:
    """_check_hp_match validates opponent k-pixel ranges for both doubles slots."""

    def test_both_opp_slots_k_match(self):
        player0 = make_mon(Species.CHARIZARD)
        player1 = make_mon(Species.BLASTOISE)
        opp0 = make_mon(Species.BULBASAUR, hp=100)
        opp1 = make_mon(Species.SQUIRTLE, hp=100)
        state = make_doubles_battle(player0, player1, opp0, opp1)
        records = [
            odelta(Species.BULBASAUR, (48, 40), max_hp=120, slot=0),
            odelta(Species.SQUIRTLE, (48, 40), max_hp=120, slot=1),
        ]
        assert _check_hp_match(state, records) is True

    def test_wrong_k_fails(self):
        player0 = make_mon(Species.CHARIZARD)
        player1 = make_mon(Species.BLASTOISE)
        opp0 = make_mon(Species.BULBASAUR, hp=100)
        opp1 = make_mon(Species.SQUIRTLE, hp=100)
        state = make_doubles_battle(player0, player1, opp0, opp1)
        records = [
            odelta(Species.BULBASAUR, (48, 20), max_hp=120, slot=0),
            odelta(Species.SQUIRTLE, (48, 40), max_hp=120, slot=1),
        ]
        assert _check_hp_match(state, records) is False


# ---------------------------------------------------------------------------
# TestRunToDecisionBoundaryPostFaint — post-faint switch applied in boundary
# ---------------------------------------------------------------------------

class TestRunToDecisionBoundaryPostFaint:
    """Opponent faint is auto-resolved within the same turn; boundary applies switch-in."""

    def _singles_state(self, opp_active_hp=1):
        from liveplay.sweep_driver import SweepConfig, SideOverrides
        player = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
        opp_active = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=5, hp=opp_active_hp)
        opp_bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,), level=5)
        return make_battle(player, opp_active, team1=[opp_active, opp_bench])

    def test_opponent_faint_applies_switch_in_and_continues(self):
        from liveplay.sweep_driver import run_to_decision_boundary, SweepConfig
        state = self._singles_state()
        result = run_to_decision_boundary(
            state, slot(0), slot(0), SweepConfig(),
            opp_switch_actions=(switch_to(1),),
        )
        assert result is not None
        assert result.sides[1].active_indices == [1]
        new_active = result.sides[1].team[result.sides[1].active_indices[0]]
        assert new_active.species == Species.PIDGEY
        assert not new_active.fainted

    def test_opponent_faint_without_switch_in_stops(self):
        from liveplay.sweep_driver import run_to_decision_boundary, SweepConfig
        state = self._singles_state()
        result = run_to_decision_boundary(
            state, slot(0), slot(0), SweepConfig(),
            opp_switch_actions=(),
        )
        assert result is not None
        assert result.sides[1].active_indices == [0]
        assert result.sides[1].team[0].fainted

    def test_player_faint_stops_at_boundary(self):
        from liveplay.sweep_driver import run_to_decision_boundary, SweepConfig
        player = make_mon(Species.CHARIZARD, moves=(Move.SPLASH,), level=5, hp=1)
        player_bench = make_mon(Species.PIKACHU, moves=(Move.SPLASH,), level=5)
        opp = make_mon(Species.BULBASAUR, moves=(Move.TACKLE,), level=50)
        state = make_battle(player, opp, team0=[player, player_bench])
        result = run_to_decision_boundary(
            state, slot(0), slot(0), SweepConfig(),
            opp_switch_actions=(),
        )
        assert result is not None
        assert result.sides[0].active_indices == [0]
        assert result.sides[0].team[0].fainted


# ---------------------------------------------------------------------------
# TestForcedReplacementNotVoluntaryAction — forced post-faint not a switch action
# ---------------------------------------------------------------------------

class TestForcedReplacementNotVoluntaryAction:
    """When a KO'd opponent is replaced in the same batch, that switch-in is
    a forced post-faint replacement (opp_switch_actions), NOT a voluntary action."""

    @staticmethod
    def _faint(species_name, *, foe):
        prefix = "Foe " if foe else ""
        return MatchResult(
            string_id="STRINGID_TARGETFAINTED", id_value=29,
            constant_name="sText_TargetFainted", var_values=[species_name],
            score=0, matched_text=f"{prefix}{species_name} fainted!", slot_labels=[],
        )

    @staticmethod
    def _opp_switch_in(species_name):
        return MatchResult(
            string_id="STRINGID_SWITCHINMON", id_value=3,
            constant_name="sText_Trainer1SentOutPkmn2",
            var_values=["Youngster", "Calvin", species_name],
            score=0, matched_text=f"Youngster Calvin sent out {species_name}!", slot_labels=[],
        )

    @staticmethod
    def _exp_msg(species_name, amount):
        return MatchResult(
            string_id="STRINGID_PKMNGAINEDEXP", id_value=13,
            constant_name="sText_PkmnGainedEXP", var_values=[species_name, str(amount)],
            score=0, matched_text=f"{species_name} gained {amount} Exp. Points!", slot_labels=[],
        )

    @staticmethod
    def _player_switch_in(species_name):
        return MatchResult(
            string_id="STRINGID_PLAYER_SWITCHINMON", id_value=3,
            constant_name="sText_PlayerSentOutPkmn", var_values=[species_name],
            score=0, matched_text=f"Go! {species_name}!", slot_labels=[],
        )

    @staticmethod
    def _intro_msg(trainer_class="Youngster", trainer_name="Calvin"):
        return MatchResult(
            string_id="STRINGID_INTROMSG", id_value=0,
            constant_name="sText_IntroMsg",
            var_values=[trainer_class, trainer_name],
            score=0, matched_text=f"{trainer_class} {trainer_name} would like to battle!",
            slot_labels=[],
        )

    def test_opponent_forced_replacement_not_assigned_as_action(self):
        """Faint of opp active + opp send-out in one batch => no voluntary opp action."""
        from liveplay.sweep_actions import _extract_known_actions
        from liveplay.actions import ActionKind
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), hp=1)
        lillipup = make_mon(Species.LILLIPUP, moves=(Move.TACKLE,))
        state = make_battle(charizard, poochyena, team1=[poochyena, lillipup])
        messages = (
            _usedmove_messages("Charizard", "Tackle")
            + [self._faint("Poochyena", foe=True)]
            + [self._opp_switch_in("Lillipup")]
        )
        known = _extract_known_actions(messages, state)
        assert known[1][0] is None
        assert known[0][0] is not None and known[0][0].kind == ActionKind.MOVE

    def test_battle_start_send_out_not_assigned_as_action(self):
        """Battle-start send-outs are forced, not decisions; neither side gets a known action."""
        from liveplay.sweep_actions import _extract_known_actions
        rookidee = make_mon(Species.ROOKIDEE, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,))
        lillipup = make_mon(Species.LILLIPUP, moves=(Move.TACKLE,))
        state = make_battle(rookidee, poochyena, team1=[poochyena, lillipup])
        messages = [
            self._intro_msg(),
            self._opp_switch_in("Poochyena"),
            self._player_switch_in("Rookidee"),
        ]
        known = _extract_known_actions(messages, state)
        assert known[1][0] is None
        assert known[0][0] is None

    def test_battle_start_opening_yields_single_candidate(self):
        """Opening sweep (INTROMSG present, no USEDMOVE): single survivor with opponent still active."""
        rookidee = make_mon(Species.ROOKIDEE, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.BITE, Move.SAND_ATTACK))
        lillipup = make_mon(Species.LILLIPUP, moves=(Move.TACKLE,))
        state = make_battle(rookidee, poochyena, team1=[poochyena, lillipup])
        messages = [
            self._intro_msg(),
            self._opp_switch_in("Poochyena"),
            self._player_switch_in("Rookidee"),
        ]
        candidates = run_candidate_sweep(
            messages=messages, hp_deltas=[],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) == 1
        surviving = candidates[0].state
        opp_active = surviving.sides[1].active_indices[0]
        assert surviving.sides[1].team[opp_active].species == Species.POOCHYENA

    def test_opponent_voluntary_switch_still_assigned(self):
        """A switch-in with NO preceding same-side faint stays a voluntary action."""
        from liveplay.sweep_actions import _extract_known_actions
        from liveplay.actions import ActionKind
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,))
        lillipup = make_mon(Species.LILLIPUP, moves=(Move.TACKLE,))
        state = make_battle(charizard, poochyena, team1=[poochyena, lillipup])
        messages = [self._opp_switch_in("Lillipup")] + _usedmove_messages("Charizard", "Tackle")
        known = _extract_known_actions(messages, state)
        assert known[1][0] is not None and known[1][0].kind == ActionKind.SWITCH
        assert known[1][0].switch_to_slot == 1

    def test_player_isolated_replacement_still_assigned(self):
        """The player's forced replacement arrives in its own batch (no faint present),
        so it must remain a SWITCH action — the post-faint branch relies on it."""
        from liveplay.sweep_actions import _extract_known_actions
        from liveplay.actions import ActionKind
        pidgey = make_mon(Species.PIDGEY, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,))
        rookidee = make_mon(Species.ROOKIDEE, moves=(Move.TACKLE,))
        state = make_battle(rookidee, poochyena, team0=[rookidee, pidgey])
        messages = [self._player_switch_in("Pidgey")]
        known = _extract_known_actions(messages, state)
        assert known[0][0] is not None and known[0][0].kind == ActionKind.SWITCH
        assert known[0][0].switch_to_slot == 1

    def test_sweep_survives_opponent_ko_and_forced_replacement(self):
        """Full sweep: fast player KOs opp active, AI sends replacement same turn → ≥1 candidate."""
        import math
        from liveplay.data.species import SPECIES_DATA
        def _calc_exp(fainted_species, fainted_level, winner_level):
            # Gen VIII EXP formula (no trainer-battle bonus)
            b = SPECIES_DATA[fainted_species].exp_yield
            L, Lp = fainted_level, winner_level
            e = math.floor(b * L / 5) * ((2 * L + 10) / (L + Lp + 10)) ** 2.5
            return math.floor(math.floor(e + 1))

        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
        poochyena = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), hp=10)
        lillipup = make_mon(Species.LILLIPUP, moves=(Move.TACKLE,))
        state = make_battle(charizard, poochyena, team1=[poochyena, lillipup])
        start_bar = max(1, (10 * 48) // poochyena.max_hp)
        exp_amount = _calc_exp(Species.POOCHYENA, poochyena.level, charizard.level)
        messages = (
            _usedmove_messages("Charizard", "Tackle")
            + [self._faint("Poochyena", foe=True)]
            + [self._exp_msg("Charizard", exp_amount)]
            + [self._opp_switch_in("Lillipup")]
        )
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[odelta(poochyena.species, (start_bar, 0), max_hp=poochyena.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1


# ---------------------------------------------------------------------------
# TestPsywaveSweepReconciliation — Psywave roll enumeration
# ---------------------------------------------------------------------------

class TestPsywaveSweepReconciliation:
    """Psywave with an injected roll reconciles to ≥1 survivor and is stable across two runs.

    SKIPPED: The NEW sweep discovers roll variants via LogEvent.DAMAGE events emitted by the
    C++ engine. Psywave does NOT emit LogEvent.DAMAGE (the C++ path uses a fixed-damage model
    that bypasses the normal damage callback), so the sweep deduplicates all 16 rolls to a
    single (roll=0.0, damage=0) entry, and no HP delta can ever match. This requires engine
    changes before the tests can be re-enabled.
    """

    _PSYWAVE_DAMAGE = 97

    def _psywave_messages(self):
        return [_mr(
            "STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
            var_values=["Alakazam", "Psywave"], side_hint=1,
        )]

    def _make_state(self):
        from liveplay.data.abilities import Ability
        from liveplay.data.items import Item
        from liveplay.data.natures import Nature
        from liveplay.state.pokemon import PokemonState, GenderEnum
        from liveplay.data.moves import MOVE_DATA
        padded = (Move.SPLASH, Move.NONE, Move.NONE, Move.NONE)
        move_pp = tuple(MOVE_DATA[m].pp if m != Move.NONE else 0 for m in padded)
        blissey = PokemonState(
            species=Species.BLISSEY, nature=Nature.HARDY, ivs=(31,) * 6,
            gender=GenderEnum.FEMALE, level=100, ability=Ability.NONE, item=Item.NONE,
            move_ids=padded, move_pp=move_pp, hp=5000,
        )
        blissey = blissey._replace(max_hp=5000)
        alakazam = make_mon(Species.ALAKAZAM, moves=(Move.PSYWAVE,), level=100)
        return make_battle(blissey, alakazam), blissey

    @pytest.mark.skip(reason="Psywave does not emit LogEvent.DAMAGE in C++ engine; roll enumeration cannot work until engine fix")
    def test_psywave_sweep_yields_survivors(self):
        state, blissey = self._make_state()
        hp_before = blissey.hp
        hp_after = hp_before - self._PSYWAVE_DAMAGE
        candidates = run_candidate_sweep(
            messages=self._psywave_messages(),
            hp_deltas=[pdelta(Species.BLISSEY, (hp_before, hp_after), max_hp=blissey.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1

    @pytest.mark.skip(reason="Psywave does not emit LogEvent.DAMAGE in C++ engine; roll enumeration cannot work until engine fix")
    def test_psywave_sweep_is_stable(self):
        state, blissey = self._make_state()
        hp_before = blissey.hp
        hp_after = hp_before - self._PSYWAVE_DAMAGE

        def run():
            return run_candidate_sweep(
                messages=self._psywave_messages(),
                hp_deltas=[pdelta(Species.BLISSEY, (hp_before, hp_after),
                                  max_hp=blissey.max_hp)],
                initial_candidates=[_make_candidate(state)],
            )

        survivors_a = run()
        survivors_b = run()
        assert len(survivors_a) == len(survivors_b)
        hps_a = sorted(c.state.sides[0].team[0].hp for c in survivors_a)
        hps_b = sorted(c.state.sides[0].team[0].hp for c in survivors_b)
        assert hps_a == hps_b


# ---------------------------------------------------------------------------
# TestConfusionSelfHitRollEnumeration — player confused mon self-hits
# ---------------------------------------------------------------------------

class TestConfusionSelfHitRollEnumeration:
    """Player (side 0) confused mon self-hits; sweep must enumerate the self-hit roll.

    Bulbasaur lv50: self-hit base=19, damage range 16-19. Pre-fix: only default roll
    tried; post-fix: all 16 rolls enumerated.
    """

    def _bulbasaur_self_hit_dmg(self, roll_idx: int) -> int:
        atk, defn, lv = 69, 69, 50
        base = (2 * lv // 5 + 2) * 40 * atk // defn // 50 + 2
        roll = roll_idx / 15.0
        return base * (85 + int(roll * 15)) // 100

    def _make_confused_player_state(self):
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        bulbasaur = bulbasaur._replace(
            volatiles=bulbasaur.volatiles | Volatile.CONFUSED,
            confusion_turns=2,
        )
        slowpoke = make_mon(Species.SLOWPOKE, moves=(Move.SPLASH,))
        return make_battle(bulbasaur, slowpoke)

    def _self_hit_messages(self, attacker_name="BULBASAUR"):
        return [
            _mr("STRINGID_USEDMOVE", var_values=["SLOWPOKE", "SPLASH"], side_hint=1),
            _mr("STRINGID_PKMNISCONFUSED", var_values=[attacker_name], side_hint=0),
            _mr("STRINGID_ITHURTCONFUSION"),
        ]

    def test_max_roll_player_self_hit_yields_candidate(self):
        state = self._make_confused_player_state()
        max_dmg = self._bulbasaur_self_hit_dmg(15)
        bulbasaur = state.sides[0].team[0]
        hp_before = bulbasaur.hp
        hp_after = hp_before - max_dmg
        candidates = run_candidate_sweep(
            messages=self._self_hit_messages(),
            hp_deltas=[pdelta(Species.BULBASAUR, (hp_before, hp_after),
                               max_hp=bulbasaur.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1

    def test_min_and_max_roll_both_yield_candidates(self):
        state = self._make_confused_player_state()
        bulbasaur = state.sides[0].team[0]
        hp_before = bulbasaur.hp
        for roll_idx in (0, 15):
            dmg = self._bulbasaur_self_hit_dmg(roll_idx)
            hp_after = hp_before - dmg
            candidates = run_candidate_sweep(
                messages=self._self_hit_messages(),
                hp_deltas=[pdelta(Species.BULBASAUR, (hp_before, hp_after),
                                   max_hp=bulbasaur.max_hp)],
                initial_candidates=[_make_candidate(state)],
            )
            assert len(candidates) >= 1, (
                f"roll_idx={roll_idx} dmg={dmg} hp_after={hp_after}: expected ≥1 candidate"
            )


# ---------------------------------------------------------------------------
# TestConfusionSelfHitSide1 — opponent confused mon self-hits
# ---------------------------------------------------------------------------

class TestConfusionSelfHitSide1(TestConfusionSelfHitRollEnumeration):
    """Opponent (side 1) confused mon self-hits; k-pixel range match."""

    def _make_confused_opponent_state(self):
        slowpoke = make_mon(Species.SLOWPOKE, moves=(Move.SPLASH,))
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        bulbasaur = bulbasaur._replace(
            volatiles=bulbasaur.volatiles | Volatile.CONFUSED,
            confusion_turns=2,
        )
        return make_battle(slowpoke, bulbasaur)

    def _opponent_self_hit_messages(self):
        return [
            _mr("STRINGID_USEDMOVE", var_values=["SLOWPOKE", "SPLASH"], side_hint=0),
            _mr("STRINGID_PKMNISCONFUSED", var_values=["BULBASAUR"], side_hint=1),
            _mr("STRINGID_ITHURTCONFUSION"),
        ]

    def test_max_roll_opponent_self_hit_yields_candidate(self):
        """Max self-hit roll vs opponent side; k-pixel match still finds ≥1 candidate."""
        from liveplay.hp_stability import hp_range as _hp_range
        state = self._make_confused_opponent_state()
        bulbasaur = state.sides[1].team[0]
        max_hp = bulbasaur.max_hp
        k_before = 48
        k_after = 40
        lo, hi = _hp_range(k_after, max_hp)
        assert lo <= 101 <= hi, f"Max-roll HP=101 must be in [{lo},{hi}]"
        candidates = run_candidate_sweep(
            messages=self._opponent_self_hit_messages(),
            hp_deltas=[odelta(Species.BULBASAUR, (k_before, k_after), max_hp=max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1


# ---------------------------------------------------------------------------
# TestConfusionSelfHitFaint — confused mon at low HP faints from high self-hit roll
# ---------------------------------------------------------------------------

class TestConfusionSelfHitFaint:
    """Confused mon at low HP faints from a high self-hit roll; sweep must survive."""

    def test_faint_from_self_hit_yields_candidate(self):
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), hp=18)
        bulbasaur = bulbasaur._replace(
            volatiles=bulbasaur.volatiles | Volatile.CONFUSED,
            confusion_turns=2,
        )
        slowpoke = make_mon(Species.SLOWPOKE, moves=(Move.SPLASH,))
        state = make_battle(bulbasaur, slowpoke)
        messages = [
            _mr("STRINGID_PKMNISCONFUSED", var_values=["BULBASAUR"], side_hint=0),
            _mr("STRINGID_ITHURTCONFUSION"),
            _mr("STRINGID_ATTACKERFAINTED", var_values=["BULBASAUR"], side_hint=0),
            _mr("STRINGID_USEDMOVE", var_values=["SLOWPOKE", "SPLASH"], side_hint=1),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=[pdelta(Species.BULBASAUR, (18, 0), max_hp=bulbasaur.max_hp)],
            initial_candidates=[_make_candidate(state)],
        )
        assert len(candidates) >= 1
        for cand in candidates:
            assert cand.state.sides[0].team[0].hp == 0


# ---------------------------------------------------------------------------
# TestMirrorMatchAccuracyInjection — mirror match, no ACCURACY override
# ---------------------------------------------------------------------------

class TestMirrorMatchAccuracyInjection:
    """In a same-species mirror match, a landed hit must NOT inject ACCURACY on either side."""

    def test_neither_side_gets_accuracy_in_mirror(self):
        from liveplay.sweep_secondaries import inject_non_move_rng
        player = make_mon(Species.EXEGGCUTE, moves=(Move.CONFUSION,))
        foe = make_mon(Species.EXEGGCUTE, moves=(Move.CONFUSION,))
        state = make_battle(player, foe)
        messages = [
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["Exeggcute", "Confusion"], side_hint=0),
            _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
                var_values=["Exeggcute", "Confusion"], side_hint=1),
        ]
        ovr0: dict = {}
        ovr1: dict = {}
        pre: dict = {}
        inject_non_move_rng(ovr0, ovr1, pre, messages, state)
        assert RNGEvent.ACCURACY not in ovr0
        assert RNGEvent.ACCURACY not in ovr1
