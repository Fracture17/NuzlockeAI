"""
Replay a directory of golden traces through the C++ GameDriver and verify parity.

For each trace (.jsonl / .jsonl.gz) in --dir: convert via liveplay.trace_replay.convert_trace,
run cpp.GameDriver in forced-trace mode, and compare status, winner, turn count, and the
end-state sha256 fingerprint against the Python recording. Failures are reported with the
first differing field; --quarantine-dir moves failing traces aside for triage. Replays
are independent, so --jobs N (0 = all cores) parallelizes across processes. Exits 1 if
any trace fails, 0 if all pass.
"""
import argparse
import hashlib
import json
import multiprocessing
import shutil
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.trace_replay import convert_trace


# Random-mode luck dicts (native draws for anything not in the forced trace;
# forced entries always win, so these values only matter for unforced saturated paths).
_LUCK = {
    "accuracy_threshold": 50.0, "crit_threshold": 50.0, "damage_roll": 0.5,
    "proc_threshold": 50.0, "secondary_threshold": 50.0, "multi_hit_roll": 0.5,
    "rampage_duration_roll": 0.5, "psywave_roll": 0.5, "flinch_threshold": 50.0,
    "binding_duration_roll": 0.5, "wake_threshold": 50.0, "defrost_threshold": 20.0,
    "paralysis_threshold": 50.0, "confusion_snap_threshold": 50.0,
    "confusion_self_hit_threshold": 50.0, "attract_threshold": 50.0,
    "damage_rolls_per_hit": None, "crits_per_hit": None, "random_mode": True,
}
_TURN_LUCK = {"quick_claw_threshold": 50.0, "secondary_threshold": 50.0,
              "luck_tier": 1, "random_mode": True}


def _fingerprint(state) -> str:
    """sha256 of to_jsonable(state) — mirrors golden_trace.build_end_record."""
    jsonable = sweep_io.to_jsonable(state)
    return hashlib.sha256(json.dumps(jsonable, sort_keys=True).encode()).hexdigest()


def replay_one(path: Path) -> "str | None":
    """Replay one trace. Returns None on success, else a one-line failure reason."""
    converted = convert_trace(path)
    args = {
        "state": sweep_io.to_jsonable(converted["initial_state"]),
        "seed": 42,
        "luck_p0": _LUCK, "luck_p1": _LUCK,
        "turn_luck_p0": _TURN_LUCK, "turn_luck_p1": _TURN_LUCK,
        "max_turns": converted["turn_count"] + 10,
        "forced_trace": converted["forced_trace"],
    }
    driver = cpp.GameDriver(json.dumps(args))
    result = json.loads(driver.step())

    if "forced_trace_mismatch" in result["status"]:
        return f"mismatch: {result['status']}"
    if result["status"] not in ("done", "max_turns"):
        return f"unexpected status: {result['status']!r}"
    if result["winner"] != converted["winner"]:
        return f"winner: cpp={result['winner']!r} py={converted['winner']!r}"

    cpp_state = sweep_io.from_jsonable(result["state"])
    if cpp_state.turn_number != converted["turn_count"]:
        return f"turn_count: cpp={cpp_state.turn_number} py={converted['turn_count']}"

    fp = _fingerprint(cpp_state)
    if fp != converted["end_fingerprint"]:
        return f"fingerprint: cpp={fp[:16]}… py={converted['end_fingerprint'][:16]}…"
    return None


def _replay_worker(path: Path) -> "tuple[Path, str | None]":
    """Pool worker: replay one trace, never raise (return the traceback instead)."""
    try:
        return path, replay_one(path)
    except Exception:
        return path, "exception:\n" + traceback.format_exc()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, required=True, help="Directory of trace files.")
    ap.add_argument("--quarantine-dir", type=Path, default=None,
                    help="Move failing traces here for triage.")
    ap.add_argument("--jobs", type=int, default=1,
                    help="Parallel worker processes (replays are independent; "
                         "0 = one per CPU core).")
    args = ap.parse_args(argv)
    jobs = args.jobs if args.jobs > 0 else multiprocessing.cpu_count()

    paths = sorted(
        p for p in args.dir.iterdir()
        if p.name.endswith(".jsonl") or p.name.endswith(".jsonl.gz")
    )
    if not paths:
        raise SystemExit(f"replay_golden_traces: no trace files in {args.dir}")

    if jobs == 1:
        results = map(_replay_worker, paths)
    else:
        pool = multiprocessing.Pool(jobs)
        results = pool.imap(_replay_worker, paths, chunksize=64)

    quiet = len(paths) > 2000  # only print failures + a progress line on huge corpora
    failures = []
    for i, (path, reason) in enumerate(results):
        tag = "ok" if reason is None else "FAIL"
        if not quiet:
            print(f"  [{i + 1}/{len(paths)}] {path.name}: {tag}")
        elif (i + 1) % 5000 == 0:
            print(f"  [{i + 1}/{len(paths)}] ... ({len(failures)} failures so far)")
        if reason is not None:
            print(f"  FAIL {path.name}:\n      {reason}")
            failures.append((path, reason))
            if args.quarantine_dir is not None:
                args.quarantine_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(args.quarantine_dir / path.name))

    print(f"\n{len(paths) - len(failures)}/{len(paths)} traces replayed clean.")
    if failures:
        print(f"{len(failures)} FAILURES:")
        for path, reason in failures:
            print(f"  {path.name}: {reason.splitlines()[0]}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
