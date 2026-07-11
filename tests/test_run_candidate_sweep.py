# Focused tests for run_candidate_sweep orchestration (Task 7c).
# Covers: (a) plain single-turn sweep with rng_sequence shape, (b) SimulationError on
# no survivors, (c) state dedup, (d) battle-start INTROMSG path.
import pytest

from liveplay.battle_types import MatchResult
from liveplay.candidate import Candidate
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.engine_select import SimulationError
from liveplay.rng import RNGEvent
from liveplay.sweep_run import run_candidate_sweep
from tests.state_builders import make_mon, make_battle, odelta


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _mr(string_id, *, constant_name="", var_values=None, side_hint=None):
    vals = var_values or []
    if side_hint is None and vals:
        first = str(vals[0]).split()
        side_hint = 1 if (first and first[0].lower() == "foe") else 0
    return MatchResult(
        string_id=string_id,
        id_value=0,
        constant_name=constant_name,
        var_values=vals,
        score=0,
        matched_text="",
        slot_labels=[],
        side_hint=side_hint,
    )


def _tackle_inputs():
    """Charizard (side 0) uses Tackle vs Bulbasaur (side 1). Returns sweep inputs."""
    charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
    bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=50)
    state = make_battle(charizard, bulbasaur)
    messages = [
        _mr("STRINGID_USEDMOVE",
            constant_name="sText_AttackerUsedMove",
            var_values=["Charizard", "Tackle"]),
    ]
    hp_deltas = [odelta(bulbasaur.species, (48, 38), max_hp=bulbasaur.max_hp)]
    return messages, hp_deltas, [Candidate(state=state)]


# ---------------------------------------------------------------------------
# (a) Plain single-turn sweep — survivors non-empty; rng_sequence shape correct
# ---------------------------------------------------------------------------

class TestPlainSingleTurnSweep:

    def test_survivors_non_empty_and_are_candidates(self):
        messages, hp_deltas, initial_candidates = _tackle_inputs()
        result = run_candidate_sweep(messages, hp_deltas, initial_candidates)
        assert len(result) >= 1
        for c in result:
            assert isinstance(c, Candidate)

    def test_rng_sequence_shape(self):
        """Each candidate must have rng_sequence = (DAMAGE_ROLL, CRIT) per mover + SPEED_TIE.

        Single-mover Tackle: 1 mover → [(DAMAGE_ROLL, roll), (CRIT, crit), (SPEED_TIE, tw)].
        """
        messages, hp_deltas, initial_candidates = _tackle_inputs()
        result = run_candidate_sweep(messages, hp_deltas, initial_candidates)
        for c in result:
            seq = c.rng_sequence
            # 1 mover → 2 entries (DAMAGE_ROLL + CRIT) + 1 SPEED_TIE = 3
            assert len(seq) == 3, f"Expected 3 rng entries, got {len(seq)}: {seq}"
            assert seq[0][0] is RNGEvent.DAMAGE_ROLL
            assert seq[1][0] is RNGEvent.CRIT
            assert seq[2][0] is RNGEvent.SPEED_TIE

    def test_parent_candidate_set(self):
        messages, hp_deltas, initial_candidates = _tackle_inputs()
        result = run_candidate_sweep(messages, hp_deltas, initial_candidates)
        for c in result:
            assert c.parent_candidate is initial_candidates[0]

    def test_unknown_actions_populated(self):
        messages, hp_deltas, initial_candidates = _tackle_inputs()
        result = run_candidate_sweep(messages, hp_deltas, initial_candidates)
        for c in result:
            assert 0 in c.unknown_actions
            assert 1 in c.unknown_actions


# ---------------------------------------------------------------------------
# (b) SimulationError raised when no candidate survives (impossible hp_deltas)
# ---------------------------------------------------------------------------

class TestSimulationErrorOnImpossible:

    def test_impossible_deltas_raise_simulation_error(self):
        """Splash used but hp_deltas claim massive damage — no survivors → SimulationError."""
        pikachu = make_mon(Species.PIKACHU, moves=(Move.SPLASH,), level=5)
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=5)
        state = make_battle(pikachu, bulbasaur)
        messages = [
            _mr("STRINGID_USEDMOVE",
                constant_name="sText_AttackerUsedMove",
                var_values=["Pikachu", "Splash"]),
        ]
        # Claim opponent lost all HP — Splash does no damage.
        hp_deltas = [odelta(bulbasaur.species, (48, 0), max_hp=bulbasaur.max_hp)]
        initial_candidates = [Candidate(state=state)]

        with pytest.raises(SimulationError):
            run_candidate_sweep(messages, hp_deltas, initial_candidates)

    def test_simulation_error_carries_inputs(self):
        """SimulationError stores messages and hp_deltas for diagnostics."""
        pikachu = make_mon(Species.PIKACHU, moves=(Move.SPLASH,), level=5)
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=5)
        state = make_battle(pikachu, bulbasaur)
        messages = [
            _mr("STRINGID_USEDMOVE",
                constant_name="sText_AttackerUsedMove",
                var_values=["Pikachu", "Splash"]),
        ]
        hp_deltas = [odelta(bulbasaur.species, (48, 0), max_hp=bulbasaur.max_hp)]
        initial_candidates = [Candidate(state=state)]

        with pytest.raises(SimulationError) as exc_info:
            run_candidate_sweep(messages, hp_deltas, initial_candidates)

        err = exc_info.value
        assert err.messages is not None
        assert err.hp_deltas is not None
        assert err.initial_candidates is not None


# ---------------------------------------------------------------------------
# (c) Dedup — identical final states collapse to one candidate
# ---------------------------------------------------------------------------

class TestDedup:

    def test_two_identical_initial_candidates_deduplicate(self):
        """Two initial candidates with identical BattleState must yield the same survivors as one.

        The dedup guard (seen_states) prevents duplicating results for redundant initial states.
        """
        messages, hp_deltas, initial_candidates = _tackle_inputs()
        # Duplicate the single initial candidate
        doubled = initial_candidates + [Candidate(state=initial_candidates[0].state)]

        result_single = run_candidate_sweep(messages, hp_deltas, initial_candidates)
        result_double = run_candidate_sweep(messages, hp_deltas, doubled)

        # Unique final states should match (duplicates pruned)
        states_single = {c.state for c in result_single}
        states_double = {c.state for c in result_double}
        assert states_single == states_double


# ---------------------------------------------------------------------------
# (d) Battle-start INTROMSG path — each initial state echoed as own child, no enumeration
# ---------------------------------------------------------------------------

class TestIntroMsgPath:

    def test_intromsg_echoes_each_candidate_unchanged(self):
        """When INTROMSG is present the sweep must echo each initial state and skip enumeration."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=50)
        state = make_battle(charizard, bulbasaur)
        messages = [_mr("STRINGID_INTROMSG")]
        initial_candidates = [Candidate(state=state)]

        result = run_candidate_sweep(messages, [], initial_candidates)
        assert len(result) == 1
        assert result[0].state == state

    def test_intromsg_rng_sequence_is_empty(self):
        """INTROMSG path emits no RNG sequence (no turn was simulated)."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=50)
        state = make_battle(charizard, bulbasaur)
        messages = [_mr("STRINGID_INTROMSG")]
        initial_candidates = [Candidate(state=state)]

        result = run_candidate_sweep(messages, [], initial_candidates)
        assert result[0].rng_sequence == []

    def test_intromsg_deduplicates_identical_initial_states(self):
        """Duplicate initial candidates on INTROMSG path are deduplicated."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=50)
        state = make_battle(charizard, bulbasaur)
        messages = [_mr("STRINGID_INTROMSG")]
        # Two candidates with identical state
        initial_candidates = [Candidate(state=state), Candidate(state=state)]

        result = run_candidate_sweep(messages, [], initial_candidates)
        assert len(result) == 1

    def test_intromsg_parent_candidate_set(self):
        """INTROMSG path sets parent_candidate on each emitted child."""
        charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
        bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=50)
        state = make_battle(charizard, bulbasaur)
        messages = [_mr("STRINGID_INTROMSG")]
        initial_candidates = [Candidate(state=state)]

        result = run_candidate_sweep(messages, [], initial_candidates)
        assert result[0].parent_candidate is initial_candidates[0]
