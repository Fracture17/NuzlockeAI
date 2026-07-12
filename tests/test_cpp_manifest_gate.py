# C++ self-regression manifest gate. Tests the record_cpp_manifest script's API
# and the committed tests/fixtures/cpp_manifest corpus. Fast tests need no fixture;
# slow replay test skips cleanly when the fixture hasn't been generated yet.
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).parent.parent / "SCRIPTS" / "record_cpp_manifest.py"
_spec = importlib.util.spec_from_file_location("record_cpp_manifest", _SCRIPT)
manifest_mod = importlib.util.module_from_spec(_spec)
sys.modules["record_cpp_manifest"] = manifest_mod
_spec.loader.exec_module(manifest_mod)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cpp_manifest"
_FIXTURE_REASON = "cpp_manifest fixture not yet generated — Stage 4"


# ---------------------------------------------------------------------------
# Fixture presence (skip if missing, fail loudly on corrupt partial contents)
# ---------------------------------------------------------------------------

def test_committed_manifest_present():
    """Skip if fixture dir doesn't exist; fail loudly on partial/corrupt contents when it does."""
    if not FIXTURE_DIR.exists():
        pytest.skip(_FIXTURE_REASON)
    shards = sorted(FIXTURE_DIR.glob("manifest_*.jsonl.gz"))
    header = FIXTURE_DIR / "manifest_header.json"
    assert header.exists(), f"manifest_header.json missing in {FIXTURE_DIR}"
    assert shards, f"no manifest shard files in {FIXTURE_DIR}"
    # Validate header is parseable and has required fields
    data = json.loads(header.read_text())
    for field in ("format_version", "master_seed", "count", "shard_size", "max_turns",
                  "git_commit", "policy_scheme", "generator"):
        assert field in data, f"manifest_header.json missing field: {field!r}"


# ---------------------------------------------------------------------------
# Determinism (fast, no fixture needed)
# ---------------------------------------------------------------------------

def test_recorder_determinism(tmp_path):
    """Two independent runs with identical seeds produce byte-identical entries; verify_entry passes all."""
    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"

    # Run via main() API twice with same params: 6 games, shard_size=4 → 2 shards
    manifest_mod.main(["--count", "6", "--seed", "123", "--out-dir", str(out_a),
                       "--shard-size", "4", "--jobs", "1"])
    manifest_mod.main(["--count", "6", "--seed", "123", "--out-dir", str(out_b),
                       "--shard-size", "4", "--jobs", "1"])

    shards_a = sorted(out_a.glob("manifest_*.jsonl.gz"))
    shards_b = sorted(out_b.glob("manifest_*.jsonl.gz"))
    assert len(shards_a) == 2, f"expected 2 shards, got {len(shards_a)}"
    assert len(shards_b) == 2

    import gzip
    entries_a: list[dict] = []
    entries_b: list[dict] = []
    for path in shards_a:
        with gzip.open(path, "rt") as f:
            for line in f:
                entries_a.append(json.loads(line))
    for path in shards_b:
        with gzip.open(path, "rt") as f:
            for line in f:
                entries_b.append(json.loads(line))

    assert len(entries_a) == 6
    assert len(entries_b) == 6

    # Byte-identical entries (compare via json dumps with sort_keys)
    for i, (ea, eb) in enumerate(zip(entries_a, entries_b)):
        assert json.dumps(ea, sort_keys=True) == json.dumps(eb, sort_keys=True), \
            f"entry {i} differs between runs"

    # Both policy kinds must appear across 6 games (0,2,4 → ai/ai; 1,3,5 → random/random)
    policies = {(e["policy_p0"], e["policy_p1"]) for e in entries_a}
    assert ("ai", "ai") in policies, "ai/ai policy not present"
    assert ("random", "random") in policies, "random/random policy not present"

    # verify_entry returns None for every entry
    for entry in entries_a:
        reason = manifest_mod.verify_entry(entry, max_turns=500)
        assert reason is None, f"verify_entry failed for index {entry['i']}: {reason}"


# ---------------------------------------------------------------------------
# Tamper detection (fast)
# ---------------------------------------------------------------------------

def test_verify_entry_detects_tamper(tmp_path):
    """Corrupt a fingerprint; verify_entry must return a non-None reason."""
    out = tmp_path / "tamper_run"
    manifest_mod.main(["--count", "2", "--seed", "456", "--out-dir", str(out),
                       "--shard-size", "10", "--jobs", "1"])

    import gzip
    shard = sorted(out.glob("manifest_*.jsonl.gz"))[0]
    with gzip.open(shard, "rt") as f:
        entry = json.loads(f.readline())

    entry["fingerprint"] = "deadbeef" * 8  # corrupt
    reason = manifest_mod.verify_entry(entry, max_turns=500)
    assert reason is not None, "verify_entry should detect corrupted fingerprint"


# ---------------------------------------------------------------------------
# Committed manifest replay (slow, skip when fixture absent)
# ---------------------------------------------------------------------------

def _load_all_entries() -> list[dict]:
    """Load every entry from every shard in the committed fixture."""
    import gzip
    entries = []
    for shard in sorted(FIXTURE_DIR.glob("manifest_*.jsonl.gz")):
        with gzip.open(shard, "rt") as f:
            for line in f:
                entries.append(json.loads(line))
    return entries


@pytest.mark.slow
def test_committed_manifest_replays_clean():
    """Every entry in the committed fixture must pass verify_entry. Skip if fixture absent."""
    if not FIXTURE_DIR.exists() or not list(FIXTURE_DIR.glob("manifest_*.jsonl.gz")):
        pytest.skip(_FIXTURE_REASON)

    header = json.loads((FIXTURE_DIR / "manifest_header.json").read_text())
    max_turns = header["max_turns"]

    entries = _load_all_entries()
    failures: list[str] = []
    for entry in entries:
        reason = manifest_mod.verify_entry(entry, max_turns=max_turns)
        if reason is not None:
            failures.append(f"  seed={entry['seed']} index={entry['i']}: {reason}")

    if failures:
        report = "\n".join(failures)
        pytest.fail(f"{len(failures)}/{len(entries)} entries failed verify_entry:\n{report}")
