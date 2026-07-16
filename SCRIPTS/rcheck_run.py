#!/usr/bin/env python3
"""Drive the 90-shard rcheck exit-gate grid (bucket-solver Task 10).

Launches one rcheck invocation per (class, seed, shard) over a subprocess pool and writes
each shard's JSONL to --out-dir. Default grid = 3 classes x 3 seeds x --shards shards, each
covering --n matchups per shard. Exits nonzero if any child process fails (nonzero exit =
that shard hit a hard soundness failure or crashed). SCRIPTS/rcheck_aggregate.py merges the
resulting files.

Usage:
  rcheck_run.py --build-dir engine/build --out-dir /tmp/rcheck --n 100 --shards 10 --jobs 10
                [--classes uniform berry sash] [--seeds 1 2 3]
                [--exact-leaves N --exact-nodes N --pess-leaves N --pess-nodes N
                 --b-depth N --b-visits N]
"""
import argparse
import concurrent.futures
import os
import subprocess
import sys


def build_commands(args):
    """Yield (label, out_path, argv) for every (class, seed, shard) cell."""
    rcheck = os.path.join(args.build_dir, "rcheck")
    if not os.path.exists(rcheck):
        raise FileNotFoundError(
            f"rcheck binary not found at {rcheck}; build it: "
            f"cmake --build {args.build_dir} --target rcheck")
    os.makedirs(args.out_dir, exist_ok=True)

    budget_flags = []
    for flag, val in (("--exact-leaves", args.exact_leaves),
                      ("--exact-nodes", args.exact_nodes),
                      ("--pess-leaves", args.pess_leaves),
                      ("--pess-nodes", args.pess_nodes),
                      ("--b-depth", args.b_depth),
                      ("--b-visits", args.b_visits)):
        if val is not None:
            budget_flags += [flag, str(val)]
    if args.no_cache:
        budget_flags += ["--no-cache"]

    for klass in args.classes:
        for seed in args.seeds:
            for k in range(args.shards):
                label = f"{klass}_seed{seed}_shard{k}of{args.shards}"
                out_path = os.path.join(args.out_dir, label + ".jsonl")
                argv = [rcheck, "--seed", str(seed), "--klass", klass,
                        "--n", str(args.n), "--shard", f"{k}/{args.shards}",
                        "--out", out_path] + budget_flags
                yield label, out_path, argv


def run_one(cell):
    label, out_path, argv = cell
    proc = subprocess.run(argv, capture_output=True, text=True)
    return label, proc.returncode, proc.stderr


def main(argv=None):
    ap = argparse.ArgumentParser(description="Drive the rcheck shard grid.")
    ap.add_argument("--build-dir", default="engine/build")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--n", type=int, default=100, help="matchups per shard")
    ap.add_argument("--shards", type=int, default=10)
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--classes", nargs="+", default=["uniform", "berry", "sash"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--exact-leaves", type=int, default=None)
    ap.add_argument("--exact-nodes", type=int, default=None)
    ap.add_argument("--pess-leaves", type=int, default=None)
    ap.add_argument("--pess-nodes", type=int, default=None)
    ap.add_argument("--b-depth", type=int, default=None)
    ap.add_argument("--b-visits", type=int, default=None)
    ap.add_argument("--no-cache", action="store_true",
                    help="disable B-solver edge cache + verdict memo (A/B determinism)")
    args = ap.parse_args(argv)

    cells = list(build_commands(args))
    print(f"rcheck_run: {len(cells)} shards, {args.jobs} jobs, n={args.n} each")

    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for label, rc, stderr in ex.map(run_one, cells):
            status = "ok" if rc == 0 else f"FAIL(rc={rc})"
            print(f"  {label:<32}: {status}")
            if rc != 0:
                failures.append((label, rc, stderr))

    if failures:
        print(f"\nFAIL: {len(failures)} shard(s) failed:")
        for label, rc, stderr in failures:
            print(f"  {label} (rc={rc})")
            tail = "\n".join(stderr.strip().splitlines()[-5:])
            if tail:
                print(f"    {tail}")
        return 1

    print(f"\nAll {len(cells)} shards completed with exit 0. "
          f"Aggregate: SCRIPTS/rcheck_aggregate.py '{args.out_dir}/*.jsonl' "
          f"--expect-shards {len(cells)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
