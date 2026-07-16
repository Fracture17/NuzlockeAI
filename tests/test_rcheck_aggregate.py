"""Tests for SCRIPTS/rcheck_aggregate.py — the bucket-solver Task 10 shard merger/validator.

Fixture shard files exercise: clean merge, hard-fail detection (exit 1 + FAIL text),
missing-summary loud failure, corrupt-bins loud failure, and known-timing percentiles.
"""
import importlib.util
import json
import os
import sys

import pytest

_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "SCRIPTS", "rcheck_aggregate.py")
_spec = importlib.util.spec_from_file_location("rcheck_aggregate", _SCRIPT)
agg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agg)


def _record(klass, seed, index, classification, timing=(10, 20, 30),
            b_reason="None", concessions=None, thrown=None):
    pipeline = {"verdict": "UNKNOWN", "b_ran": True, "b_reason": b_reason,
                "concessions": concessions or {}, "thrown": None}
    if thrown is not None:
        pipeline = {"verdict": None, "b_ran": False, "thrown": thrown}
    return {
        "klass": klass, "seed": seed, "index": index, "shard": {"k": 0, "of": 1},
        "classification": classification, "pipeline": pipeline,
        "exact": {"verdict": "WIN", "reason": "None"},
        "timing_us": {"pessimal": timing[0], "b": timing[1], "exact": timing[2]},
        "telemetry": {"buckets_visited": 5, "expand_calls": 3, "replays": 2,
                      "oracle_leaves": 10, "max_depth": 4},
    }


def _summary(records, seed=1, klass="uniform", override_bins=None, override_hard=None):
    bins = {c: 0 for c in agg.CLASSES}
    for r in records:
        bins[r["classification"]] += 1
    hard = sum(bins[c] for c in agg.HARD_FAIL_CLASSES)
    return {"summary": {"klass": klass, "seed": seed, "shard": {"k": 0, "of": 1},
                        "n": len(records),
                        "bins": override_bins if override_bins is not None else bins,
                        "throw_census": {}, "concession_histogram": {},
                        "hard_fails": override_hard if override_hard is not None else hard}}


def _write(path, records, summary=None, omit_summary=False):
    with open(path, "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
        if not omit_summary:
            fh.write(json.dumps(summary if summary is not None else _summary(records)) + "\n")


def test_two_fixtures_merge(tmp_path):
    s0 = tmp_path / "s0.jsonl"
    s1 = tmp_path / "s1.jsonl"
    _write(str(s0), [_record("uniform", 1, 0, "SOUND_AGREE_WIN"),
                     _record("uniform", 1, 1, "CONSERVATIVE_UNTAGGED", b_reason="DepthCap")])
    _write(str(s1), [_record("berry", 2, 2, "REFEREE_INDET"),
                     _record("berry", 2, 3, "SOUND_AGREE_WIN")])
    rep = agg.aggregate([str(s0), str(s1)])
    assert rep["n"] == 4
    assert rep["bins"]["SOUND_AGREE_WIN"] == 2
    assert rep["bins"]["REFEREE_INDET"] == 1
    assert rep["conservative_untagged_by_reason"]["DepthCap"] == 1
    assert rep["referee_indet_rate"] == pytest.approx(0.25)
    assert rep["per_class_bins"]["berry"]["REFEREE_INDET"] == 1


def test_hard_fail_exit1_and_text(tmp_path, capsys):
    hf = tmp_path / "hf.jsonl"
    _write(str(hf), [_record("uniform", 1, 0, "HARD_FAIL_B_WIN"),
                     _record("uniform", 1, 1, "SOUND_AGREE_WIN")])
    rc = agg.main([str(hf)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "soundness failure" in out


def test_missing_summary_is_loud(tmp_path):
    miss = tmp_path / "miss.jsonl"
    _write(str(miss), [_record("uniform", 1, 0, "SOUND_AGREE_WIN")], omit_summary=True)
    with pytest.raises(agg.IntegrityError):
        agg.aggregate([str(miss)])


def test_corrupt_bins_is_loud(tmp_path):
    corrupt = tmp_path / "corrupt.jsonl"
    recs = [_record("uniform", 1, 0, "SOUND_AGREE_WIN")]
    bad_bins = {c: 0 for c in agg.CLASSES}  # claims zero, but a record exists
    _write(str(corrupt), recs, summary=_summary(recs, override_bins=bad_bins))
    with pytest.raises(agg.IntegrityError):
        agg.aggregate([str(corrupt)])


def test_line_count_mismatch_is_loud(tmp_path):
    bad = tmp_path / "bad.jsonl"
    recs = [_record("uniform", 1, 0, "SOUND_AGREE_WIN")]
    summ = _summary(recs)
    summ["summary"]["n"] = 5  # lie about n
    _write(str(bad), recs, summary=summ)
    with pytest.raises(agg.IntegrityError):
        agg.aggregate([str(bad)])


def test_known_timings_percentiles(tmp_path):
    t = tmp_path / "t.jsonl"
    recs = [_record("uniform", 1, i, "SOUND_AGREE_WIN", timing=(i, 0, 0))
            for i in range(1, 101)]
    _write(str(t), recs)
    rep = agg.aggregate([str(t)])
    p = rep["timing_us"]["pessimal"]
    assert p["p50"] == pytest.approx(50.5, abs=1.0)
    assert p["p90"] == pytest.approx(90.1, abs=1.0)
    assert p["p99"] == pytest.approx(99.01, abs=1.0)


def test_clean_exit0_and_pass(tmp_path, capsys):
    s0 = tmp_path / "s0.jsonl"
    _write(str(s0), [_record("uniform", 1, 0, "SOUND_AGREE_WIN")])
    rc = agg.main([str(s0)])
    assert rc == 0
    assert "PASS: zero soundness failures" in capsys.readouterr().out


def test_expect_shards_violation(tmp_path):
    s0 = tmp_path / "s0.jsonl"
    _write(str(s0), [_record("uniform", 1, 0, "SOUND_AGREE_WIN")])
    with pytest.raises(agg.IntegrityError):
        agg.aggregate([str(s0)], expect_shards=2)
