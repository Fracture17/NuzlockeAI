"""Tests for SCRIPTS/rcheck_compare.py — exact-vs-pp-canon A/B contract.

Fabricated JSONL fixture pairs exercise: canon mode allowing baseline WIN -> candidate
FAIL/INDET conservatism, canon mode hard-failing baseline FAIL -> candidate WIN, canon
conservatism sub-type counts, and non-canon mode still alarming on any WIN<->FAIL flip.
"""
import importlib.util
import json
import os

import pytest

_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "SCRIPTS", "rcheck_compare.py")
_spec = importlib.util.spec_from_file_location("rcheck_compare", _SCRIPT)
cmp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cmp)


def _rec(index, b_verdict, b_reason="None", telemetry=None):
    return {
        "klass": "uniform", "seed": 1, "index": index, "shard": {"k": 0, "of": 1},
        "classification": "SOUND_AGREE_WIN",
        "pipeline": {"verdict": "UNKNOWN", "b_ran": True, "b_verdict": b_verdict,
                     "b_reason": b_reason, "concessions": {}, "thrown": None},
        "exact": {"verdict": "WIN", "reason": "None"},
        "timing_us": {"pessimal": 1, "b": 10, "exact": 5},
        "telemetry": telemetry or {"edge_hits": 0, "edge_misses": 1,
                                   "canonical_repeats": 0, "pp_audit_rejects": 0,
                                   "audit_expands": 0},
    }


def _write(path, records):
    with open(path, "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
        summary = {"summary": {"klass": "uniform", "seed": 1, "shard": {"k": 0, "of": 1},
                               "n": len(records), "bins": {}, "throw_census": {},
                               "concession_histogram": {}, "hard_fails": 0}}
        fh.write(json.dumps(summary) + "\n")


def _run(monkeypatch, canon, base_path, cand_path):
    argv = ["rcheck_compare.py"]
    if canon:
        argv.append("--canon")
    argv += [base_path, cand_path]
    monkeypatch.setattr("sys.argv", argv)
    return cmp.main()


def test_canon_allows_win_to_fail(tmp_path, monkeypatch, capsys):
    base = tmp_path / "base.jsonl"
    cand = tmp_path / "cand.jsonl"
    _write(str(base), [_rec(0, "WIN"), _rec(1, "WIN")])
    _write(str(cand), [_rec(0, "FAIL"),
                       _rec(1, "INDET", b_reason="PpAuditFail")])
    rc = _run(monkeypatch, True, str(base), str(cand))
    assert rc == 0
    out = capsys.readouterr().out
    assert "PASS" in out


def test_canon_hard_fails_fail_to_win(tmp_path, monkeypatch, capsys):
    base = tmp_path / "base.jsonl"
    cand = tmp_path / "cand.jsonl"
    _write(str(base), [_rec(0, "FAIL")])
    _write(str(cand), [_rec(0, "WIN")])
    rc = _run(monkeypatch, True, str(base), str(cand))
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert "HARD-FAIL" in out


def test_canon_counts_conservatism_subtypes(tmp_path, monkeypatch, capsys):
    base = tmp_path / "base.jsonl"
    cand = tmp_path / "cand.jsonl"
    _write(str(base), [_rec(0, "WIN"), _rec(1, "WIN"), _rec(2, "WIN")])
    _write(str(cand), [
        _rec(0, "FAIL"),
        _rec(1, "INDET", b_reason="PpAuditFail",
             telemetry={"pp_audit_rejects": 1, "canonical_repeats": 4}),
        _rec(2, "INDET", b_reason="DepthCap"),
    ])
    rc = _run(monkeypatch, True, str(base), str(cand))
    assert rc == 0
    out = capsys.readouterr().out
    lines = [ln.strip() for ln in out.splitlines()]

    def subtype_count(label):
        for ln in lines:
            if ln.startswith(label):
                return int(ln.rsplit(":", 1)[1])
        raise AssertionError(f"sub-type {label!r} not reported")

    assert subtype_count("WIN->FAIL") == 1
    assert subtype_count("WIN->INDET(PpAuditFail)") == 1
    assert subtype_count("WIN->INDET(other)") == 1
    assert "pp_audit_rejects=1" in out
    assert "canonical_repeats=4" in out


def test_noncanon_alarms_on_win_to_fail(tmp_path, monkeypatch, capsys):
    base = tmp_path / "base.jsonl"
    cand = tmp_path / "cand.jsonl"
    _write(str(base), [_rec(0, "WIN")])
    _write(str(cand), [_rec(0, "FAIL")])
    rc = _run(monkeypatch, False, str(base), str(cand))
    assert rc == 1
    out = capsys.readouterr().out
    assert "ALARM" in out


def test_noncanon_clean_passes(tmp_path, monkeypatch):
    base = tmp_path / "base.jsonl"
    cand = tmp_path / "cand.jsonl"
    _write(str(base), [_rec(0, "WIN"), _rec(1, "FAIL")])
    _write(str(cand), [_rec(0, "WIN"), _rec(1, "FAIL")])
    rc = _run(monkeypatch, False, str(base), str(cand))
    assert rc == 0
