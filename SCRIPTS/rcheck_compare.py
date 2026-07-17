#!/usr/bin/env python3
"""Per-matchup A/B diff of two rcheck output directories.

Joins records on (klass, seed, shard.k, index) and reports:
  - B-verdict transition matrix (baseline -> candidate).
  - b timing percentiles for both sides plus per-matchup speedup stats.
  - Cache + PP-canon counter totals on the candidate side.
Fails loud on join mismatches (a matchup present on one side only).

Two soundness contracts select the alarm rule:
  default (cache determinism A/B): any decided-verdict flip (WIN<->FAIL) alarms + exits 1.
  --canon  (exact baseline vs pp-canon candidate): only baseline FAIL -> candidate WIN
           hard-fails. A pp-canon WIN is audit-passed and claims a real win; a baseline
           FAIL means every action failed definitively in the REAL game, so FAIL -> WIN is
           a contradiction => bug. Baseline WIN -> candidate FAIL/INDET (any reason, incl.
           PpAuditFail) is expected canon conservatism; baseline INDET -> any candidate is
           deeper reach; THROWN either side is a frontier shift. All are allowed.

Usage: rcheck_compare.py [--canon] BASELINE_GLOB CANDIDATE_GLOB
"""
import glob
import json
import statistics
import sys


def load(pattern):
    rows = {}
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"FAIL: no files match {pattern}")
    for path in files:
        with open(path) as fh:
            for line in fh:
                d = json.loads(line)
                if "summary" in d:
                    continue
                key = (d["klass"], d["seed"], d["shard"]["k"], d["index"])
                if key in rows:
                    raise SystemExit(f"FAIL: duplicate matchup {key} in {path}")
                rows[key] = d
    return rows


def bv(rec):
    p = rec["pipeline"]
    if p["thrown"]:
        return "THROWN"
    if not p["b_ran"]:
        return "NOT_RUN"
    return p["b_verdict"]


def b_reason(rec):
    p = rec["pipeline"]
    if p["thrown"] or not p["b_ran"]:
        return "None"
    return p.get("b_reason", "None")


def pct(vals, q):
    if not vals:
        return 0
    vals = sorted(vals)
    return vals[min(len(vals) - 1, int(q * len(vals)))]


def main():
    args = sys.argv[1:]
    canon = False
    if args and args[0] == "--canon":
        canon = True
        args = args[1:]
    if len(args) != 2:
        raise SystemExit(__doc__)
    base = load(args[0])
    cand = load(args[1])
    if base.keys() != cand.keys():
        only_b = sorted(base.keys() - cand.keys())[:5]
        only_c = sorted(cand.keys() - base.keys())[:5]
        raise SystemExit(f"FAIL: join mismatch; baseline-only={only_b} candidate-only={only_c}")

    trans = {}
    alarms = []
    decided_to_indet = []
    bt_base, bt_cand = [], []
    counters = {k: 0 for k in ("edge_hits", "edge_misses", "memo_hits", "memo_stores",
                               "memo_suppressed", "memo_containment_missed",
                               "canonical_repeats", "pp_audit_rejects", "audit_expands")}
    # canon conservatism sub-types (baseline WIN -> weaker candidate verdict).
    conservatism = {"WIN->FAIL": 0, "WIN->INDET(PpAuditFail)": 0, "WIN->INDET(other)": 0}
    for key in base:
        vb, vc = bv(base[key]), bv(cand[key])
        trans[(vb, vc)] = trans.get((vb, vc), 0) + 1

        if canon:
            # Sole soundness violation: a real FAIL turning into an audit-passed canon WIN.
            if vb == "FAIL" and vc == "WIN":
                alarms.append((key, vb, vc))
            if vb == "WIN" and vc == "FAIL":
                conservatism["WIN->FAIL"] += 1
            elif vb == "WIN" and vc == "INDET":
                if b_reason(cand[key]) == "PpAuditFail":
                    conservatism["WIN->INDET(PpAuditFail)"] += 1
                else:
                    conservatism["WIN->INDET(other)"] += 1
        else:
            if {vb, vc} == {"WIN", "FAIL"}:
                alarms.append((key, vb, vc))

        if vb in ("WIN", "FAIL") and vc == "INDET":
            decided_to_indet.append((key, vb))
        if base[key]["pipeline"]["b_ran"] and cand[key]["pipeline"]["b_ran"]:
            bt_base.append(base[key]["timing_us"]["b"])
            bt_cand.append(cand[key]["timing_us"]["b"])
        tel = cand[key].get("telemetry", {})
        for k in counters:
            counters[k] += tel.get(k, 0)

    print(f"matchups joined: {len(base)}  mode={'canon' if canon else 'strict'}")
    print("\nB-verdict transitions (baseline -> candidate):")
    for (vb, vc), n in sorted(trans.items(), key=lambda x: -x[1]):
        if canon:
            marker = "  <-- HARD-FAIL" if (vb, vc) == ("FAIL", "WIN") else ""
        else:
            marker = "  <-- ALARM" if {vb, vc} == {"WIN", "FAIL"} else ""
        print(f"  {vb:>8} -> {vc:<8} : {n}{marker}")
    if decided_to_indet:
        print(f"\ndecided -> INDET (budget noise, not soundness): {len(decided_to_indet)}")

    if canon:
        print("\ncanon conservatism (baseline WIN -> weaker candidate):")
        for sub, n in conservatism.items():
            print(f"  {sub:<24}: {n}")
        print(f"\ncandidate PP-canon totals: "
              f"canonical_repeats={counters['canonical_repeats']}  "
              f"pp_audit_rejects={counters['pp_audit_rejects']}  "
              f"audit_expands={counters['audit_expands']}")

    if bt_base:
        print(f"\nb timing us over {len(bt_base)} B-ran pairs:")
        for name, vals in (("baseline", bt_base), ("candidate", bt_cand)):
            print(f"  {name:>9}: p50={pct(vals, .5)} p90={pct(vals, .9)} p99={pct(vals, .99)} "
                  f"sum={sum(vals)}")
        ratios = [b / c for b, c in zip(bt_base, bt_cand) if c > 0 and b > 0]
        if ratios:
            print(f"  speedup (base/cand): median={statistics.median(ratios):.2f}x "
                  f"max={max(ratios):.1f}x")

    print("\ncandidate cache counters:")
    for k, v in counters.items():
        print(f"  {k:<24}: {v}")
    eh, em = counters["edge_hits"], counters["edge_misses"]
    if eh + em:
        print(f"  edge hit rate           : {eh / (eh + em):.2%}")

    if alarms:
        label = "FAIL->WIN soundness violations" if canon else "decided-verdict flips"
        print(f"\nFAIL: {len(alarms)} {label}: {alarms[:10]}")
        return 1
    print("\nPASS: no soundness violations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
