#!/usr/bin/env python3
"""Merge and validate rcheck shard JSONL outputs (bucket-solver Task 10 exit gate).

Reads shard JSONL files (one record per matchup + a trailing summary line). FAILS LOUD on
any integrity violation: a missing summary line, a per-matchup line count that disagrees
with the embedded summary n, embedded bins that disagree with recomputed bins, or
--expect-shards / --expect-n violations. Recomputes every bin from the per-matchup records
and cross-checks the embedded summaries. Reports per-class/per-seed bin tables, concession
histogram, throw census, timing percentiles (pessimal/B/exact/total), telemetry aggregates,
CONSERVATIVE_UNTAGGED sub-split by B reason, edge-cache/verdict-memo effectiveness (over
B-ran records), and the referee-INDET rate. Exit 1 on any hard soundness failure or
integrity error; else prints "PASS: zero soundness failures".

Usage:
  rcheck_aggregate.py GLOB [GLOB ...] [--expect-shards N] [--expect-n N] [--json OUT]
  rcheck_aggregate.py --selftest
"""
import argparse
import glob
import json
import sys
from collections import defaultdict

CLASSES = [
    "THROWN", "REFEREE_INDET", "SOUND_AGREE_WIN", "SOUND_AGREE_LOSS",
    "HARD_FAIL_B_WIN", "HARD_FAIL_PESSIMAL_LOSS", "SOUND_UNKNOWN_ON_LOSS",
    "CONSERVATIVE_TAGGED", "CONSERVATIVE_UNTAGGED",
]
HARD_FAIL_CLASSES = {"HARD_FAIL_B_WIN", "HARD_FAIL_PESSIMAL_LOSS"}

# Edge-cache + verdict-memo counters (win_solver Tasks 1-2). Required on every B-ran record.
CACHE_FIELDS = ("edge_hits", "edge_misses", "memo_hits", "memo_stores",
                "memo_suppressed", "memo_containment_missed")


class IntegrityError(Exception):
    """Raised on any structural inconsistency in a shard file (fail-loud)."""


def _percentile(sorted_vals, pct):
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    rank = pct / 100.0 * (len(sorted_vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = rank - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _pctiles(vals):
    s = sorted(vals)
    return {
        "p50": _percentile(s, 50),
        "p90": _percentile(s, 90),
        "p99": _percentile(s, 99),
        "n": len(s),
    }


def parse_shard_file(path):
    """Parse one shard file. Returns (records, summary). Raises IntegrityError on any flaw."""
    records = []
    summary = None
    with open(path) as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise IntegrityError(f"{path}:{lineno}: invalid JSON: {e}")
            if "summary" in obj:
                if summary is not None:
                    raise IntegrityError(f"{path}: multiple summary lines")
                summary = obj["summary"]
            else:
                if summary is not None:
                    raise IntegrityError(
                        f"{path}:{lineno}: record after summary line (truncated/corrupt)")
                records.append(obj)

    if summary is None:
        raise IntegrityError(f"{path}: missing summary line (shard incomplete)")

    # Line count must match embedded n.
    if len(records) != summary["n"]:
        raise IntegrityError(
            f"{path}: record count {len(records)} != summary n {summary['n']}")

    # Recompute bins from records and cross-check the embedded summary.
    recomputed = {c: 0 for c in CLASSES}
    for rec in records:
        cls = rec["classification"]
        if cls not in recomputed:
            raise IntegrityError(f"{path}: unknown classification '{cls}'")
        recomputed[cls] += 1
    for c in CLASSES:
        embedded = summary["bins"].get(c, 0)
        if embedded != recomputed[c]:
            raise IntegrityError(
                f"{path}: bin '{c}' embedded {embedded} != recomputed {recomputed[c]} (corrupt)")

    hard = sum(recomputed[c] for c in HARD_FAIL_CLASSES)
    if hard != summary.get("hard_fails", 0):
        raise IntegrityError(
            f"{path}: hard_fails embedded {summary.get('hard_fails')} != recomputed {hard}")

    return records, summary


def aggregate(paths, expect_shards=None, expect_n=None):
    """Aggregate all shard files. Returns a merged report dict. Raises IntegrityError."""
    if expect_shards is not None and len(paths) != expect_shards:
        raise IntegrityError(
            f"--expect-shards {expect_shards} but found {len(paths)} shard files")

    bins = {c: 0 for c in CLASSES}
    per_class_bins = defaultdict(lambda: {c: 0 for c in CLASSES})   # klass -> bins
    per_seed_bins = defaultdict(lambda: {c: 0 for c in CLASSES})    # seed  -> bins
    throw_census = defaultdict(int)
    concession_histogram = defaultdict(int)
    untagged_by_reason = defaultdict(int)  # B reason for CONSERVATIVE_UNTAGGED

    timings = {"pessimal": [], "b": [], "exact": [], "total": []}
    timings_by_class = defaultdict(lambda: {"pessimal": [], "b": [], "exact": [], "total": []})
    telemetry = {k: [] for k in
                 ("buckets_visited", "expand_calls", "replays", "oracle_leaves", "max_depth")}
    cache_series = {k: [] for k in CACHE_FIELDS}  # per-field values over B-ran records

    total_records = 0
    hard_fails = 0

    for path in paths:
        records, _summary = parse_shard_file(path)
        for rec in records:
            total_records += 1
            cls = rec["classification"]
            klass = rec["klass"]
            seed = rec["seed"]
            bins[cls] += 1
            per_class_bins[klass][cls] += 1
            per_seed_bins[seed][cls] += 1
            if cls in HARD_FAIL_CLASSES:
                hard_fails += 1

            pl = rec["pipeline"]
            if pl.get("thrown"):
                throw_census[pl["thrown"]["key"]] += 1
            else:
                for name, cnt in pl.get("concessions", {}).items():
                    concession_histogram[name] += cnt
                if cls == "CONSERVATIVE_UNTAGGED":
                    untagged_by_reason[pl.get("b_reason", "None")] += 1

            t = rec["timing_us"]
            tot = t["pessimal"] + t["b"] + t["exact"]
            for key, val in (("pessimal", t["pessimal"]), ("b", t["b"]),
                             ("exact", t["exact"]), ("total", tot)):
                timings[key].append(val)
                timings_by_class[klass][key].append(val)

            tel = rec.get("telemetry", {})
            for key in telemetry:
                if key in tel:
                    telemetry[key].append(tel[key])

            # Cache/memo effectiveness — only over records where B actually ran.
            # A B-ran record missing any counter is a corrupt/stale shard: fail loud.
            if not pl.get("thrown") and pl.get("b_ran"):
                for key in CACHE_FIELDS:
                    if key not in tel:
                        raise IntegrityError(
                            f"{path}: B-ran record index {rec.get('index')} missing "
                            f"telemetry field '{key}' (stale shard?)")
                    cache_series[key].append(tel[key])

    if expect_n is not None and total_records != expect_n:
        raise IntegrityError(
            f"--expect-n {expect_n} but aggregated {total_records} matchups")

    edge_hits = sum(cache_series["edge_hits"])
    edge_misses = sum(cache_series["edge_misses"])
    edge_total = edge_hits + edge_misses
    cache = {
        "b_ran_records": len(cache_series["edge_hits"]),
        "edge_hits": edge_hits,
        "edge_misses": edge_misses,
        "edge_hit_rate": (edge_hits / edge_total) if edge_total else 0.0,
        "memo_hits": sum(cache_series["memo_hits"]),
        "memo_stores": sum(cache_series["memo_stores"]),
        "memo_suppressed": sum(cache_series["memo_suppressed"]),
        "memo_containment_missed": sum(cache_series["memo_containment_missed"]),
        "per_field": {k: {"sum": sum(v), **_pctiles(v)} for k, v in cache_series.items()},
    }

    referee_indet = bins["REFEREE_INDET"]
    report = {
        "shards": len(paths),
        "n": total_records,
        "hard_fails": hard_fails,
        "bins": bins,
        "per_class_bins": {k: dict(v) for k, v in per_class_bins.items()},
        "per_seed_bins": {str(k): dict(v) for k, v in per_seed_bins.items()},
        "throw_census": dict(throw_census),
        "concession_histogram": dict(concession_histogram),
        "conservative_untagged_by_reason": dict(untagged_by_reason),
        "referee_indet": referee_indet,
        "referee_indet_rate": (referee_indet / total_records) if total_records else 0.0,
        "timing_us": {k: _pctiles(v) for k, v in timings.items()},
        "timing_us_by_class": {
            k: {kk: _pctiles(vv) for kk, vv in v.items()}
            for k, v in timings_by_class.items()},
        "telemetry": {
            k: {"sum": sum(v), **_pctiles(v)} for k, v in telemetry.items()},
        "cache": cache,
    }
    return report


def _print_bins(bins, indent=""):
    for c in CLASSES:
        print(f"{indent}{c:<26}: {bins[c]}")


def print_report(report):
    print("\n=== rcheck aggregate ===")
    print(f"shards={report['shards']}  matchups={report['n']}  hard_fails={report['hard_fails']}")
    print("\nBins (overall):")
    _print_bins(report["bins"], "  ")

    print("\nPer-class bins:")
    for klass, bins in sorted(report["per_class_bins"].items()):
        print(f"  [{klass}]")
        _print_bins(bins, "    ")

    print("\nPer-seed bins:")
    for seed, bins in sorted(report["per_seed_bins"].items()):
        print(f"  seed {seed}: " +
              " ".join(f"{c}={bins[c]}" for c in CLASSES if bins[c]))

    print("\nThrow census:")
    for key, cnt in sorted(report["throw_census"].items(), key=lambda kv: -kv[1]):
        print(f"  {key:<28}: {cnt}")

    print("\nConcession histogram:")
    for name, cnt in sorted(report["concession_histogram"].items(), key=lambda kv: -kv[1]):
        print(f"  {name:<20}: {cnt}")

    print("\nCONSERVATIVE_UNTAGGED sub-split by B reason:")
    for reason, cnt in sorted(report["conservative_untagged_by_reason"].items()):
        print(f"  {reason:<12}: {cnt}")

    print(f"\nReferee-INDET rate: {report['referee_indet']}/{report['n']} "
          f"= {100.0 * report['referee_indet_rate']:.1f}%")

    print("\nTiming us (overall p50/p90/p99):")
    for stage in ("pessimal", "b", "exact", "total"):
        p = report["timing_us"][stage]
        print(f"  {stage:<9}: p50={p['p50']:.0f}  p90={p['p90']:.0f}  p99={p['p99']:.0f}")

    print("\nTiming us by class (total p50/p90/p99):")
    for klass, stages in sorted(report["timing_us_by_class"].items()):
        p = stages["total"]
        print(f"  {klass:<8}: p50={p['p50']:.0f}  p90={p['p90']:.0f}  p99={p['p99']:.0f}")

    print("\nTelemetry aggregates (sum + p50/p90/p99):")
    for key, agg in report["telemetry"].items():
        print(f"  {key:<16}: sum={agg['sum']}  p50={agg['p50']:.0f}  "
              f"p90={agg['p90']:.0f}  p99={agg['p99']:.0f}")

    c = report["cache"]
    print(f"\nCache effectiveness (over {c['b_ran_records']} B-ran records):")
    print(f"  edge hits={c['edge_hits']}  misses={c['edge_misses']}  "
          f"hit_rate={100.0 * c['edge_hit_rate']:.2f}%")
    print(f"  memo hits={c['memo_hits']}  stores={c['memo_stores']}  "
          f"suppressed={c['memo_suppressed']}  containment_missed={c['memo_containment_missed']}")
    for key in CACHE_FIELDS:
        agg = c["per_field"][key]
        print(f"  {key:<24}: sum={agg['sum']}  p50={agg['p50']:.0f}  "
              f"p90={agg['p90']:.0f}  p99={agg['p99']:.0f}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Merge/validate rcheck shard JSONL outputs.")
    ap.add_argument("globs", nargs="*", help="shard JSONL file globs")
    ap.add_argument("--expect-shards", type=int, default=None)
    ap.add_argument("--expect-n", type=int, default=None)
    ap.add_argument("--json", dest="json_out", default=None, help="write merged summary JSON")
    ap.add_argument("--selftest", action="store_true", help="run built-in self-test")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    paths = []
    for g in args.globs:
        paths.extend(sorted(glob.glob(g)))
    if not paths:
        print("rcheck_aggregate: no shard files matched", file=sys.stderr)
        return 1

    try:
        report = aggregate(paths, args.expect_shards, args.expect_n)
    except IntegrityError as e:
        print(f"\nFAIL: integrity error: {e}", file=sys.stderr)
        return 1

    print_report(report)

    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=2)

    if report["hard_fails"] > 0:
        print(f"\nFAIL: {report['hard_fails']} soundness failure(s)")
        return 1
    print("\nPASS: zero soundness failures")
    return 0


# ---------------------------------------------------------------------------
# Self-test fallback (when pytest is unavailable): builds fixtures in a temp dir.
# ---------------------------------------------------------------------------

def _make_record(klass, seed, index, classification, thrown=None, concessions=None,
                 b_reason="None", timing=(10, 20, 30), telemetry=None):
    pipeline = {"verdict": "UNKNOWN", "b_ran": True, "b_reason": b_reason,
                "concessions": concessions or {}, "thrown": None}
    if thrown is not None:
        pipeline = {"verdict": None, "b_ran": False, "thrown": thrown}
    return {
        "klass": klass, "seed": seed, "index": index, "shard": {"k": 0, "of": 1},
        "classification": classification, "pipeline": pipeline,
        "exact": {"verdict": "WIN", "reason": "None"},
        "timing_us": {"pessimal": timing[0], "b": timing[1], "exact": timing[2]},
        "telemetry": telemetry or {"buckets_visited": 5, "expand_calls": 3, "replays": 2,
                                   "oracle_leaves": 10, "max_depth": 4,
                                   "edge_hits": 1, "edge_misses": 3, "memo_hits": 0,
                                   "memo_stores": 2, "memo_suppressed": 0,
                                   "memo_containment_missed": 0},
    }


def _write_shard(path, records):
    bins = {c: 0 for c in CLASSES}
    for r in records:
        bins[r["classification"]] += 1
    hard = sum(bins[c] for c in HARD_FAIL_CLASSES)
    summary = {"summary": {"klass": records[0]["klass"] if records else "uniform",
                           "seed": 1, "shard": {"k": 0, "of": 1}, "n": len(records),
                           "bins": bins, "throw_census": {}, "concession_histogram": {},
                           "hard_fails": hard}}
    with open(path, "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
        fh.write(json.dumps(summary) + "\n")


def _selftest():
    import tempfile
    import os
    failures = 0

    def check(name, cond):
        nonlocal failures
        print(f"  {'ok' if cond else 'FAIL'}: {name}")
        if not cond:
            failures += 1

    with tempfile.TemporaryDirectory() as d:
        # (a) two clean fixtures merge correctly.
        _write_shard(os.path.join(d, "s0.jsonl"), [
            _make_record("uniform", 1, 0, "SOUND_AGREE_WIN"),
            _make_record("uniform", 1, 1, "CONSERVATIVE_UNTAGGED", b_reason="DepthCap"),
        ])
        _write_shard(os.path.join(d, "s1.jsonl"), [
            _make_record("berry", 1, 2, "REFEREE_INDET"),
            _make_record("berry", 1, 3, "SOUND_AGREE_WIN"),
        ])
        rep = aggregate(sorted(glob.glob(os.path.join(d, "s*.jsonl"))))
        check("merge n", rep["n"] == 4)
        check("merge bins SOUND_AGREE_WIN", rep["bins"]["SOUND_AGREE_WIN"] == 2)
        check("untagged sub-split", rep["conservative_untagged_by_reason"]["DepthCap"] == 1)
        check("referee indet rate", abs(rep["referee_indet_rate"] - 0.25) < 1e-9)

        # (d) known timings → correct percentiles.
        recs = [_make_record("uniform", 2, i, "SOUND_AGREE_WIN",
                             timing=(i, 0, 0)) for i in range(1, 101)]
        _write_shard(os.path.join(d, "t.jsonl"), recs)
        rep2 = aggregate([os.path.join(d, "t.jsonl")])
        p = rep2["timing_us"]["pessimal"]
        check("p50 timing", abs(p["p50"] - 50.5) < 1.0)
        check("p90 timing", abs(p["p90"] - 90.1) < 1.0)

        # (b) hard-fail fixture → exit 1 + FAIL text.
        hf = os.path.join(d, "hf.jsonl")
        _write_shard(hf, [_make_record("uniform", 3, 0, "HARD_FAIL_B_WIN")])
        rc = main([hf])
        check("hard-fail exit 1", rc == 1)

        # (c) missing summary line → loud failure.
        miss = os.path.join(d, "miss.jsonl")
        with open(miss, "w") as fh:
            fh.write(json.dumps(_make_record("uniform", 4, 0, "SOUND_AGREE_WIN")) + "\n")
        try:
            aggregate([miss])
            check("missing summary raises", False)
        except IntegrityError:
            check("missing summary raises", True)

        # corrupt bins → loud failure.
        corrupt = os.path.join(d, "corrupt.jsonl")
        with open(corrupt, "w") as fh:
            fh.write(json.dumps(_make_record("uniform", 5, 0, "SOUND_AGREE_WIN")) + "\n")
            bad = {"summary": {"klass": "uniform", "seed": 5, "shard": {"k": 0, "of": 1},
                               "n": 1, "bins": {c: 0 for c in CLASSES},
                               "throw_census": {}, "concession_histogram": {}, "hard_fails": 0}}
            fh.write(json.dumps(bad) + "\n")
        try:
            aggregate([corrupt])
            check("corrupt bins raises", False)
        except IntegrityError:
            check("corrupt bins raises", True)

        # (e) clean → exit 0 + PASS.
        rc_clean = main([os.path.join(d, "s0.jsonl")])
        check("clean exit 0", rc_clean == 0)

    print(f"\n{'PASS' if failures == 0 else 'FAIL'}: selftest ({failures} failures)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
