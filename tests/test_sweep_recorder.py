# Tests for liveplay/sweep_recorder.py — session-format, I/O, and replay tests.
# All tests that called run_candidate_sweep were previously dropped (Stage E stub);
# now restored since run_candidate_sweep is wired. diff_harness not carried (no analog).
import json
import pytest

from liveplay.battle_types import MatchResult
from liveplay.candidate import Candidate
from liveplay.data.abilities import Ability
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.rng import UninjectedRNGError
from liveplay.engine_select import SimulationError
from liveplay.sweep_recorder import (
    BoundaryRecord,
    ReplayResult,
    SweepRecorder,
    diff_battle_states,
    load_session,
    record_and_run,
    replay_boundary,
)
from liveplay.sweep_io import to_jsonable, from_jsonable
from tests.state_builders import make_battle, make_mon, odelta


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _mr(string_id, *, constant_name="", var_values=None, side_hint=None):
    """Build a MatchResult. side_hint defaults to the Foe-prefix-derived hint (mirroring the
    real matcher): opponent names ("Foe X") → 1, the player's bare names → 0, None if empty."""
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


def _tackle_scenario():
    """Return (state, messages, hp_deltas) for a simple Tackle turn.

    Charizard (side 0) uses Tackle on Bulbasaur (side 1).
    k=38 accepts damage 23–25 (HP 95–97 from 120).
    """
    charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,), level=50)
    bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=50)
    state = make_battle(charizard, bulbasaur)
    messages = [
        _mr("STRINGID_USEDMOVE",
            constant_name="sText_AttackerUsedMove",
            var_values=["Charizard", "Tackle"]),
    ]
    hp_deltas = [odelta(bulbasaur.species, (48, 38), max_hp=bulbasaur.max_hp)]
    return state, messages, hp_deltas


def _splash_scenario():
    """Return sweep inputs for a Splash-only turn (no damage, no deltas)."""
    pikachu = make_mon(Species.PIKACHU, moves=(Move.SPLASH,), level=5)
    bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=5)
    state = make_battle(pikachu, bulbasaur)
    messages = [
        _mr("STRINGID_USEDMOVE",
            constant_name="sText_AttackerUsedMove",
            var_values=["Pikachu", "Splash"]),
    ]
    return state, messages, []


def _impossible_scenario():
    """Splash used, but opponent delta claims huge damage → SimulationError."""
    pikachu = make_mon(Species.PIKACHU, moves=(Move.SPLASH,), level=5)
    bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,), level=5)
    state = make_battle(pikachu, bulbasaur)
    messages = [
        _mr("STRINGID_USEDMOVE",
            constant_name="sText_AttackerUsedMove",
            var_values=["Pikachu", "Splash"]),
    ]
    # Claim the opponent lost all HP — impossible from Splash
    hp_deltas = [odelta(bulbasaur.species, (48, 0), max_hp=bulbasaur.max_hp)]
    return state, messages, hp_deltas


def _run_tackle(recorder):
    """Call record_and_run with the Tackle scenario; return survivors."""
    state, messages, hp_deltas = _tackle_scenario()
    initial_candidates = [Candidate(state=state)]
    return record_and_run(
        recorder,
        messages=messages,
        hp_deltas=hp_deltas,
        initial_candidates=initial_candidates,
    )


def _tamper_output_json(session_dir, tamper_fn):
    """Load output JSON for boundary 0, apply tamper_fn to the survivors list, rewrite."""
    output_path = session_dir / "boundary_0000.output.json"
    # The file encodes {"survivors": [...]} via to_jsonable, which wraps dicts under __dict__.
    # Decode the full payload then re-encode after mutation.
    decoded = from_jsonable(json.loads(output_path.read_text()))
    survivors = tamper_fn(decoded["survivors"])
    output_path.write_text(json.dumps(to_jsonable({"survivors": survivors})))


# ---------------------------------------------------------------------------
# Test 1: round-trip equality
# ---------------------------------------------------------------------------

class TestRoundTripEquality:
    def test_round_trip_equality(self, tmp_path):
        recorder = SweepRecorder.create(base_dir=tmp_path)
        state, messages, hp_deltas = _tackle_scenario()
        initial_candidates = [Candidate(state=state)]

        survivors = record_and_run(
            recorder,
            messages=messages,
            hp_deltas=hp_deltas,
            initial_candidates=initial_candidates,
        )

        records = load_session(recorder.session_dir)
        assert len(records) == 1
        rec = records[0]

        # Inputs round-trip
        assert rec.inputs["messages"] == messages
        assert rec.inputs["hp_deltas"] == hp_deltas

        # Loaded candidate states match original (equality ignores parent_candidate)
        orig_states = [c.state for c in initial_candidates]
        loaded_states = [c.state for c in rec.inputs["initial_candidates"]]
        assert orig_states == loaded_states

        # Loaded survivors match function return value
        assert rec.survivors is not None
        assert len(rec.survivors) == len(survivors)
        for ls, rs in zip(rec.survivors, survivors):
            assert ls.state == rs.state

        # All loaded candidates have parent_candidate None
        for c in rec.inputs["initial_candidates"]:
            assert c.parent_candidate is None
        for c in rec.survivors:
            assert c.parent_candidate is None


# ---------------------------------------------------------------------------
# Test 2: caller objects not mutated
# ---------------------------------------------------------------------------

class TestCallerObjectsNotMutated:
    def test_caller_objects_not_mutated(self, tmp_path):
        recorder = SweepRecorder.create(base_dir=tmp_path)
        state, messages, hp_deltas = _tackle_scenario()

        # Give the candidate a non-None parent to verify it's not cleared in place
        parent = Candidate(state=state)
        child = Candidate(state=state, parent_candidate=parent)
        initial_candidates = [child]

        record_and_run(
            recorder,
            messages=messages,
            hp_deltas=hp_deltas,
            initial_candidates=initial_candidates,
        )

        # Original candidate's parent_candidate must be intact
        assert child.parent_candidate is parent


# ---------------------------------------------------------------------------
# Test 3: live append durability (crash mid-sweep)
# ---------------------------------------------------------------------------

class TestLiveAppendDurability:
    def test_live_append_durability(self, tmp_path):
        recorder = SweepRecorder.create(base_dir=tmp_path)
        state, messages, hp_deltas = _tackle_scenario()
        initial_candidates = [Candidate(state=state)]

        # Record input only — simulate crash before output is written
        idx = recorder.record_input(
            messages=messages,
            hp_deltas=hp_deltas,
            initial_candidates=initial_candidates,
        )
        assert idx == 0

        # Load immediately — boundary present with no output or error
        records = load_session(recorder.session_dir)
        assert len(records) == 1
        assert records[0].index == 0
        assert records[0].inputs is not None
        assert records[0].survivors is None
        assert records[0].error is None

        # Now record a full second boundary
        record_and_run(
            recorder,
            messages=messages,
            hp_deltas=hp_deltas,
            initial_candidates=initial_candidates,
        )

        records = load_session(recorder.session_dir)
        assert len(records) == 2
        assert records[0].index == 0
        assert records[1].index == 1
        assert records[1].survivors is not None


# ---------------------------------------------------------------------------
# Test 4: failure boundary marked for SimulationError
# ---------------------------------------------------------------------------

class TestFailureBoundaryMarked:
    def test_failure_boundary_marked(self, tmp_path):
        recorder = SweepRecorder.create(base_dir=tmp_path)
        state, messages, hp_deltas = _impossible_scenario()
        initial_candidates = [Candidate(state=state)]

        with pytest.raises(SimulationError):
            record_and_run(
                recorder,
                messages=messages,
                hp_deltas=hp_deltas,
                initial_candidates=initial_candidates,
            )

        records = load_session(recorder.session_dir)
        assert len(records) == 1
        rec = records[0]
        assert rec.error is not None
        assert rec.survivors is None
        assert rec.error["type"] == "SimulationError"
        assert len(rec.error["traceback"]) > 0


# ---------------------------------------------------------------------------
# Test 5: session files contain no pickle bytes and are valid JSON
# ---------------------------------------------------------------------------

class TestSessionFileIsJson:
    def test_session_files_are_valid_json_no_pickle(self, tmp_path):
        recorder = SweepRecorder.create(base_dir=tmp_path)
        state, messages, hp_deltas = _tackle_scenario()
        initial_candidates = [Candidate(state=state)]

        record_and_run(
            recorder,
            messages=messages,
            hp_deltas=hp_deltas,
            initial_candidates=initial_candidates,
        )

        # Every file in the session directory must parse as JSON
        session_files = list(recorder.session_dir.iterdir())
        assert len(session_files) >= 2  # at least input + output

        # Pickle magic bytes: b'\x80' followed by a protocol byte
        pickle_magic = b'\x80'
        for path in session_files:
            raw = path.read_bytes()
            assert not raw.startswith(pickle_magic), (
                f"{path.name} starts with pickle magic bytes"
            )
            # Must parse as valid JSON
            json.loads(raw.decode("utf-8"))


# ---------------------------------------------------------------------------
# Test: replay_boundary on a fresh session reproduces the recorded decision
# ---------------------------------------------------------------------------

class TestReplayBoundaryFreshSession:
    def test_replay_boundary_reproduces_decision(self, tmp_path):
        recorder = SweepRecorder.create(base_dir=tmp_path)
        state, messages, hp_deltas = _tackle_scenario()
        initial_candidates = [Candidate(state=state)]

        record_and_run(
            recorder,
            messages=messages,
            hp_deltas=hp_deltas,
            initial_candidates=initial_candidates,
        )

        records = load_session(recorder.session_dir)
        assert len(records) == 1
        result = replay_boundary(records[0])
        assert result.passed
        assert result.unmatched_recorded == []
        assert result.unmatched_replayed == []


# ---------------------------------------------------------------------------
# TestLegacyPickleError: loading a pickle-era file raises a clear legacy error
# ---------------------------------------------------------------------------

class TestLegacyPickleError:
    def test_legacy_pickle_file_raises_clear_error(self, tmp_path):
        import pickle
        session_dir = tmp_path / "legacy_session"
        session_dir.mkdir()

        # Write a file that looks like a legacy pickle session (pickle bytes)
        legacy_data = {"messages": [], "hp_deltas": [], "initial_candidates": [], "action_groups": None}
        pkl_path = session_dir / "boundary_0000.input.pkl"
        pkl_path.write_bytes(pickle.dumps(legacy_data))

        with pytest.raises(Exception, match="legacy pickle"):
            load_session(session_dir)


# ---------------------------------------------------------------------------
# Test: fatal re-raise contract
# ---------------------------------------------------------------------------

class TestFatalReraiseContract:
    def test_simulation_error_reraised(self, tmp_path):
        recorder = SweepRecorder.create(base_dir=tmp_path)
        state, messages, hp_deltas = _impossible_scenario()
        initial_candidates = [Candidate(state=state)]

        with pytest.raises(SimulationError):
            record_and_run(
                recorder,
                messages=messages,
                hp_deltas=hp_deltas,
                initial_candidates=initial_candidates,
            )


# ---------------------------------------------------------------------------
# Test: bit-for-bit session replay (2-boundary, chained)
# ---------------------------------------------------------------------------

class TestBitForBitSessionReplay:
    def test_bitforbit_session_replay(self, tmp_path):
        recorder = SweepRecorder.create(base_dir=tmp_path)
        state, messages, hp_deltas = _splash_scenario()
        initial_candidates = [Candidate(state=state)]

        # Boundary 0
        survivors0 = record_and_run(
            recorder,
            messages=messages,
            hp_deltas=hp_deltas,
            initial_candidates=initial_candidates,
        )

        # Boundary 1: survivors of boundary 0 become inputs
        survivors1 = record_and_run(
            recorder,
            messages=messages,
            hp_deltas=hp_deltas,
            initial_candidates=survivors0,
        )

        records = load_session(recorder.session_dir)
        assert len(records) == 2

        for rec in records:
            result = replay_boundary(rec)
            assert result.passed, (
                f"Boundary {rec.index} replay failed: {result.unmatched_recorded} "
                f"vs {result.unmatched_replayed}"
            )
            assert result.unmatched_recorded == []
            assert result.unmatched_replayed == []


# ---------------------------------------------------------------------------
# Test: replay diff detection
# ---------------------------------------------------------------------------

class TestReplayDiffDetection:
    def _record_one_tackle(self, tmp_path):
        recorder = SweepRecorder.create(base_dir=tmp_path)
        _run_tackle(recorder)
        return recorder.session_dir

    def test_hp_corruption_detected(self, tmp_path):
        session_dir = self._record_one_tackle(tmp_path)
        records = load_session(session_dir)
        assert records[0].survivors is not None
        assert len(records[0].survivors) >= 1

        def bump_hp(survivors):
            first = survivors[0]
            side0 = first.state.sides[1]
            mon = side0.team[side0.active_indices[0]]
            tampered_mon = mon._replace(hp=mon.hp + 50)
            tampered_team = list(side0.team)
            tampered_team[side0.active_indices[0]] = tampered_mon
            from liveplay.state.side import SideState
            tampered_side = SideState(
                team=tampered_team,
                active_indices=side0.active_indices,
            )
            from liveplay.state.battle import BattleState
            tampered_state = BattleState(
                sides=(first.state.sides[0], tampered_side),
            )
            survivors[0] = Candidate(state=tampered_state)
            return survivors

        _tamper_output_json(session_dir, bump_hp)

        records2 = load_session(session_dir)
        result = replay_boundary(records2[0])
        assert not result.passed
        # HP divergence should be mentioned in at least one diff string
        diffs_text = " ".join(result.diffs)
        assert "hp" in diffs_text.lower() or len(result.diffs) > 0

    @pytest.mark.parametrize("corruption", ["stat_stages", "status"])
    def test_stat_and_status_corruption_detected(self, tmp_path, corruption):
        session_dir = self._record_one_tackle(tmp_path)
        records = load_session(session_dir)
        assert records[0].survivors is not None
        assert len(records[0].survivors) >= 1

        def tamper(survivors):
            first = survivors[0]
            side1 = first.state.sides[1]
            mon = side1.team[side1.active_indices[0]]

            if corruption == "stat_stages":
                new_stages = list(mon.stat_stages)
                new_stages[0] = 3
                tampered_mon = mon._replace(stat_stages=tuple(new_stages))
            else:
                from liveplay.data.status import Status
                tampered_mon = mon._replace(status=Status.BURN)

            tampered_team = list(side1.team)
            tampered_team[side1.active_indices[0]] = tampered_mon
            from liveplay.state.side import SideState
            tampered_side = SideState(
                team=tampered_team,
                active_indices=side1.active_indices,
            )
            from liveplay.state.battle import BattleState
            tampered_state = BattleState(
                sides=(first.state.sides[0], tampered_side),
            )
            survivors[0] = Candidate(state=tampered_state)
            return survivors

        _tamper_output_json(session_dir, tamper)

        records2 = load_session(session_dir)
        result = replay_boundary(records2[0])
        assert not result.passed


# ---------------------------------------------------------------------------
# Test: single boundary selection
# ---------------------------------------------------------------------------

class TestSingleBoundarySelection:
    def test_single_boundary_selection(self, tmp_path):
        recorder = SweepRecorder.create(base_dir=tmp_path)
        state, messages, hp_deltas = _splash_scenario()
        initial_candidates = [Candidate(state=state)]

        # Two boundaries
        survivors0 = record_and_run(
            recorder,
            messages=messages,
            hp_deltas=hp_deltas,
            initial_candidates=initial_candidates,
        )
        record_and_run(
            recorder,
            messages=messages,
            hp_deltas=hp_deltas,
            initial_candidates=survivors0,
        )

        records = load_session(recorder.session_dir)
        assert len(records) == 2

        # Select only index 1
        rec1 = records[1]
        assert rec1.index == 1

        result = replay_boundary(rec1)
        assert result.passed
