# Frozen golden-trace corpus gate (Stage B freeze): every committed trace in
# tests/fixtures/golden_traces/ must replay clean through the C++ GameDriver
# (no forced_trace mismatch; winner/turn-count/fingerprint match the Python recording).
#
# Slow (opt-in with -m slow): replays the frozen in-repo slice (1000 games + scenario
# traces, ~7s). A larger 100k corpus lives gitignored in golden_traces_100k/ (same
# recorder, seed 20260707); verify it before milestones with:
#   .venv/bin/python SCRIPTS/replay_golden_traces.py --dir golden_traces_100k --jobs 0
# Re-record after INTENTIONAL C++ behavior changes with:
#   .venv/bin/python SCRIPTS/record_golden_traces.py --count 1000 --seed 20260706 \
#       --out-dir tests/fixtures/golden_traces --gzip
#   .venv/bin/python SCRIPTS/record_scenario_traces.py \
#       --out-dir tests/fixtures/golden_traces
# then verify with SCRIPTS/replay_golden_traces.py before committing.
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
