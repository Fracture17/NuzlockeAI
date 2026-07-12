"""
C++ self-regression manifest recorder. Supersedes Python-era golden traces.
Generates deterministic self-play games via make_random_battle and the C++ run_game binding,
storing winner/fingerprint/final_state per entry for parity-gate replay.

Usage — 1M corpus (gitignored, milestone verification):
    python SCRIPTS/record_cpp_manifest.py --count 1000000 --seed 20260712 \\
        --out-dir cpp_manifest_1m --jobs 0

Usage — committed 2k subset (tests/fixtures/cpp_manifest; first 2 shards of 1M corpus):
    python SCRIPTS/record_cpp_manifest.py --count 2000 --seed 20260712 \\
        --out-dir tests/fixtures/cpp_manifest --jobs 0
"""
import argparse
import gzip
import hashlib
import json
import multiprocessing
import random
import subprocess
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.battle_gen import make_random_battle


# Random-mode luck dicts — MUST stay identical to the replay/gate side in
# replay_golden_traces.py. Any drift between the two sides will cause false
# parity failures on the golden-trace gate.
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
    """sha256 of to_jsonable(state) — mirrors replay_golden_traces._fingerprint."""
    jsonable = sweep_io.to_jsonable(state)
    return hashlib.sha256(json.dumps(jsonable, sort_keys=True).encode()).hexdigest()


def _policy_for_index(index: int) -> str:
    """Even index → 'ai', odd → 'random'."""
    return "ai" if index % 2 == 0 else "random"


def run_one(seed: int, index: int, max_turns: int) -> dict:
    """Build and play one game; return the manifest entry dict. Fails loudly on any error."""
    grng = random.Random(seed)
    state, params = make_random_battle(grng)
    policy = _policy_for_index(index)

    args = {
        "state": sweep_io.to_jsonable(state),
        "seed": seed,
        "luck_p0": _LUCK,
        "luck_p1": _LUCK,
        "turn_luck_p0": _TURN_LUCK,
        "turn_luck_p1": _TURN_LUCK,
        "max_turns": max_turns,
        "policy_p0": policy,
        "policy_p1": policy,
    }

    result_json = cpp.run_game(json.dumps(args))
    result = json.loads(result_json)

    status = result.get("status")
    if status not in ("completed", "max_turns"):
        raise RuntimeError(
            f"run_game returned unexpected status {status!r} "
            f"(seed={seed}, index={index})"
        )

    final_state = sweep_io.from_jsonable(result["final_state"])
    final_state_jsonable = sweep_io.to_jsonable(final_state)
    fp = hashlib.sha256(json.dumps(final_state_jsonable, sort_keys=True).encode()).hexdigest()

    return {
        "i": index,
        "seed": seed,
        "params": params,
        "policy_p0": policy,
        "policy_p1": policy,
        "status": status,
        "winner": result["winner"],
        "turn_count": result["turn_count"],
        "fingerprint": fp,
        "final_state": final_state_jsonable,
    }


def verify_entry(entry: dict, max_turns: int) -> "str | None":
    """Re-run entry's game and compare status, winner, turn_count, fingerprint, and final_state.

    Returns None on match, else a one-line reason string.
    """
    try:
        fresh = run_one(entry["seed"], entry["i"], max_turns)
    except Exception:
        return "exception during re-run:\n" + traceback.format_exc()

    for field in ("status", "winner", "turn_count", "fingerprint"):
        if fresh[field] != entry[field]:
            return f"{field}: stored={entry[field]!r} rerun={fresh[field]!r}"

    stored_dump = json.dumps(entry["final_state"], sort_keys=True)
    fresh_dump = json.dumps(fresh["final_state"], sort_keys=True)
    if stored_dump != fresh_dump:
        return "final_state JSON differs"

    return None


# ---------------------------------------------------------------------------
# Shard worker (runs in a subprocess pool worker)
# ---------------------------------------------------------------------------

def _shard_worker(args: tuple) -> "str | None":
    """Generate and write one shard. Returns None on success, error string on failure."""
    shard_index, game_seeds, shard_indices, max_turns, out_path = args
    entries = []
    for seed, idx in zip(game_seeds, shard_indices):
        try:
            entry = run_one(seed, idx, max_turns)
        except Exception:
            tb = traceback.format_exc()
            raise RuntimeError(
                f"FATAL: run_one failed for seed={seed} index={idx}.\n{tb}"
            )
        entries.append(entry)

    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")

    return None


def _git_commit(repo_root: Path) -> str:
    """Return the current HEAD git commit hash, or 'unknown' on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=repo_root
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--count", type=int, required=True, help="Total games to generate.")
    ap.add_argument("--seed", type=int, required=True, help="Master RNG seed.")
    ap.add_argument("--out-dir", type=Path, required=True, help="Output directory.")
    ap.add_argument("--shard-size", type=int, default=1000,
                    help="Games per shard file (default 1000).")
    ap.add_argument("--jobs", type=int, default=1,
                    help="Worker processes (0 = all cores).")
    ap.add_argument("--max-turns", type=int, default=500,
                    help="Max turns per game (default 500).")
    args = ap.parse_args(argv)

    jobs = args.jobs if args.jobs > 0 else multiprocessing.cpu_count()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Deterministic seed derivation: the same master seed always produces the same
    # game_seeds prefix regardless of --count, so a 2k run equals the first 2 shards
    # of a 1M run with the same --seed.
    rng = random.Random(args.seed)
    game_seeds = [rng.getrandbits(63) for _ in range(args.count)]

    # Build shard task list
    shards: list[tuple] = []
    for shard_idx in range(0, args.count, args.shard_size):
        end = min(shard_idx + args.shard_size, args.count)
        shard_number = shard_idx // args.shard_size
        shard_seeds = game_seeds[shard_idx:end]
        shard_game_indices = list(range(shard_idx, end))
        shard_path = out_dir / f"manifest_{shard_number:05d}.jsonl.gz"
        shards.append((shard_number, shard_seeds, shard_game_indices, args.max_turns, shard_path))

    # Write header before running games
    repo_root = Path(__file__).parent.parent
    header = {
        "format_version": 1,
        "master_seed": args.seed,
        "count": args.count,
        "shard_size": args.shard_size,
        "max_turns": args.max_turns,
        "git_commit": _git_commit(repo_root),
        "policy_scheme": "even=ai/ai, odd=random/random",
        "generator": "liveplay.battle_gen.make_random_battle",
    }
    (out_dir / "manifest_header.json").write_text(
        json.dumps(header, indent=2) + "\n"
    )

    if jobs == 1:
        for shard_args in shards:
            _shard_worker(shard_args)
    else:
        with multiprocessing.Pool(jobs) as pool:
            for _ in pool.imap_unordered(_shard_worker, shards):
                pass  # errors propagate as exceptions from the pool

    total_shards = len(shards)
    print(f"Wrote {args.count} games across {total_shards} shard(s) to {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
