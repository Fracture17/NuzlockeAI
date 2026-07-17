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


_CACHE_TEL = {"edge_hits": 0, "edge_misses": 3, "memo_hits": 0, "memo_stores": 1,
              "memo_suppressed": 0, "memo_containment_missed": 0}
_PP_TEL = {"canonical_repeats": 0, "pp_horizon_used": 0, "audit_expands": 0,
           "pp_audit_rejects": 0}


def _record(klass, seed, index, classification, timing=(10, 20, 30),
            b_reason="None", concessions=None, thrown=None, telemetry=None):
    pipeline = {"verdict": "UNKNOWN", "b_ran": True, "b_reason": b_reason,
                "concessions": concessions or {}, "thrown": None}
    if thrown is not None:
        pipeline = {"verdict": None, "b_ran": False, "thrown": thrown}
    tel = {"buckets_visited": 5, "expand_calls": 3, "replays": 2,
           "oracle_leaves": 10, "max_depth": 4, **_CACHE_TEL, **_PP_TEL}
    if telemetry is not None:
        tel = telemetry
    return {
        "klass": klass, "seed": seed, "index": index, "shard": {"k": 0, "of": 1},
        "classification": classification, "pipeline": pipeline,
        "exact": {"verdict": "WIN", "reason": "None"},
        "timing_us": {"pessimal": timing[0], "b": timing[1], "exact": timing[2]},
        "telemetry": tel,
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


def _cache_tel(edge_hits, edge_misses, **extra):
    return {"buckets_visited": 5, "expand_calls": 3, "replays": 2, "oracle_leaves": 10,
            "max_depth": 4, "edge_hits": edge_hits, "edge_misses": edge_misses,
            "memo_hits": extra.get("memo_hits", 0), "memo_stores": extra.get("memo_stores", 0),
            "memo_suppressed": extra.get("memo_suppressed", 0),
            "memo_containment_missed": extra.get("memo_containment_missed", 0),
            "canonical_repeats": extra.get("canonical_repeats", 0),
            "pp_horizon_used": extra.get("pp_horizon_used", 0),
            "audit_expands": extra.get("audit_expands", 0),
            "pp_audit_rejects": extra.get("pp_audit_rejects", 0)}


def test_cache_effectiveness_hit_rate(tmp_path):
    s0 = tmp_path / "s0.jsonl"
    _write(str(s0), [
        _record("uniform", 1, 0, "SOUND_AGREE_WIN",
                telemetry=_cache_tel(2, 6, memo_hits=1, memo_stores=3)),
        _record("uniform", 1, 1, "CONSERVATIVE_UNTAGGED",
                telemetry=_cache_tel(1, 1, memo_stores=2, memo_suppressed=1)),
    ])
    rep = agg.aggregate([str(s0)])
    cache = rep["cache"]
    assert cache["edge_hits"] == 3
    assert cache["edge_misses"] == 7
    assert cache["edge_hit_rate"] == pytest.approx(3 / 10)
    assert cache["memo_hits"] == 1
    assert cache["memo_stores"] == 5
    assert cache["memo_suppressed"] == 1
    assert cache["memo_containment_missed"] == 0


def test_cache_zero_edges_hit_rate_is_zero(tmp_path):
    s0 = tmp_path / "s0.jsonl"
    _write(str(s0), [_record("uniform", 1, 0, "SOUND_AGREE_WIN",
                             telemetry=_cache_tel(0, 0))])
    rep = agg.aggregate([str(s0)])
    assert rep["cache"]["edge_hit_rate"] == 0.0


def test_b_ran_missing_cache_field_is_loud(tmp_path):
    bad = tmp_path / "bad.jsonl"
    tel = _cache_tel(1, 1)
    del tel["edge_misses"]  # B ran but a new field is missing
    _write(str(bad), [_record("uniform", 1, 0, "SOUND_AGREE_WIN", telemetry=tel)])
    with pytest.raises(agg.IntegrityError):
        agg.aggregate([str(bad)])


def test_thrown_row_missing_cache_field_ok(tmp_path):
    # Thrown rows carry no telemetry; must not trip the strict B-ran check.
    s0 = tmp_path / "s0.jsonl"
    _write(str(s0), [_record("uniform", 1, 0, "THROWN",
                             thrown={"key": "expand:ShiftViolation", "what": "boom"})])
    rep = agg.aggregate([str(s0)])
    assert rep["cache"]["edge_hits"] == 0


def test_pp_canon_totals_aggregated(tmp_path):
    s0 = tmp_path / "s0.jsonl"
    _write(str(s0), [
        _record("uniform", 1, 0, "CONSERVATIVE_UNTAGGED", b_reason="PpAuditFail",
                telemetry=_cache_tel(0, 1, canonical_repeats=3, pp_horizon_used=7,
                                     audit_expands=2, pp_audit_rejects=1)),
        _record("uniform", 1, 1, "SOUND_AGREE_WIN",
                telemetry=_cache_tel(0, 1, canonical_repeats=5, audit_expands=1)),
    ])
    rep = agg.aggregate([str(s0)])
    pp = rep["pp_canon"]
    assert pp["b_ran_records"] == 2
    assert pp["canonical_repeats"] == 8
    assert pp["pp_audit_rejects"] == 1
    assert pp["audit_expands"] == 3
    assert pp["per_field"]["pp_horizon_used"]["sum"] == 7


def test_b_ran_missing_pp_field_is_loud(tmp_path):
    bad = tmp_path / "bad.jsonl"
    tel = _cache_tel(1, 1)
    del tel["pp_audit_rejects"]  # B ran but a PP-canon field is missing
    _write(str(bad), [_record("uniform", 1, 0, "SOUND_AGREE_WIN", telemetry=tel)])
    with pytest.raises(agg.IntegrityError):
        agg.aggregate([str(bad)])
