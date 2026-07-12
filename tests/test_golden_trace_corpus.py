# Hand-authored scenario-trace gate: every committed scenario_* trace in
# tests/fixtures/golden_traces/ must replay clean through the C++ GameDriver
# forced replay (no forced_trace mismatch; winner/turn-count/fingerprint match).
#
# History (2026-07-12 rebase): the 1000 random Python-parity trace_* files and the
# git-ignored 100k extended corpus were RETIRED — the C++ engine is the sole
# authority, so parity-to-Python fought correctness on every intentional fix.
# Their replacement is the C++ self-regression manifest gate:
#   committed 2k subset  tests/fixtures/cpp_manifest/  (tests/test_cpp_manifest_gate.py)
#   full 1M corpus       cpp_manifest_1m/ (git-ignored), regenerate/verify with
#   SCRIPTS/record_cpp_manifest.py.
# The 28 scenario_* traces remain: they pin specific mechanics turn-by-turn and were
# recorded by the old repo's SCRIPTS/record_scenario_traces.py (frozen archive).
#
# Slow (opt-in with -m slow): replays the 28 scenario traces (<1s).
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden_traces"

_SCRIPT = Path(__file__).parent.parent / "SCRIPTS" / "replay_golden_traces.py"
_spec = importlib.util.spec_from_file_location("replay_golden_traces", _SCRIPT)
replay_mod = importlib.util.module_from_spec(_spec)
sys.modules["replay_golden_traces"] = replay_mod
_spec.loader.exec_module(replay_mod)


def _trace_paths() -> list[Path]:
    return sorted(GOLDEN_DIR.glob("*.jsonl*"))


def test_frozen_corpus_present():
    """Fail loudly if the frozen corpus is missing — the parity gate must never
    silently pass on an empty directory."""
    assert GOLDEN_DIR.is_dir(), f"missing frozen golden corpus dir: {GOLDEN_DIR}"
    assert _trace_paths(), f"no golden traces in {GOLDEN_DIR}"


@pytest.mark.slow
@pytest.mark.parametrize("trace_path", _trace_paths(), ids=lambda p: p.name)
def test_frozen_corpus_replays_clean(trace_path: Path):
    failure = replay_mod.replay_one(trace_path)
    assert failure is None, f"{trace_path.name}: {failure}"
