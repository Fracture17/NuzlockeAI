# Tests for liveplay/sweep_recorder.py — session-format and I/O parts only.
# TRIM: all tests using record_and_run / replay_boundary are dropped because
# run_candidate_sweep is a NotImplementedError stub in this repo (Stage E wires it).
# Carried: TestLegacyPickleError — pure load_session I/O, no sweep call.
import pytest

from liveplay.sweep_recorder import load_session


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
