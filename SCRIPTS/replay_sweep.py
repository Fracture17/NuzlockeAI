# CLI wrapper over src/sweep_recorder.py for offline replay of recorded sweep boundaries.
# Loads a session directory, re-runs each boundary through the real sweep engine, and reports PASS/FAIL.
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from liveplay.sweep_recorder import load_session, replay_boundary

_RECORDINGS_BASE = Path("/tmp/vision/recordings")


def _latest_session_dir() -> Path:
    """Return the most recently modified directory under /tmp/vision/recordings/, or raise."""
    if not _RECORDINGS_BASE.exists():
        raise SystemExit(f"ERROR: recordings base dir does not exist: {_RECORDINGS_BASE}")
    dirs = [d for d in _RECORDINGS_BASE.iterdir() if d.is_dir()]
    if not dirs:
        raise SystemExit(f"ERROR: no session directories found under {_RECORDINGS_BASE}")
    return max(dirs, key=lambda d: d.stat().st_mtime)


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Replay recorded sweep boundaries and compare against the live engine."
    )
    parser.add_argument(
        "session_dir",
        nargs="?",
        default=None,
        help="Path to the session directory (default: most recently modified under /tmp/vision/recordings/)",
    )
    parser.add_argument(
        "--boundary",
        type=int,
        default=None,
        metavar="N",
        help="Replay a single boundary by index",
    )
    parser.add_argument(
        "--failing-only",
        action="store_true",
        help="Replay only boundaries that recorded an error",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full diffs and per-candidate detail",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    session_dir = Path(args.session_dir) if args.session_dir else _latest_session_dir()
    if not session_dir.exists():
        print(f"ERROR: session directory not found: {session_dir}", file=sys.stderr)
        return 1

    records = load_session(session_dir)
    if not records:
        print(f"ERROR: no boundary records found in {session_dir}", file=sys.stderr)
        return 1

    # Apply selection filters
    if args.boundary is not None:
        selected = [r for r in records if r.index == args.boundary]
        if not selected:
            print(f"ERROR: boundary {args.boundary} not found in session (have {[r.index for r in records]})", file=sys.stderr)
            return 1
    elif args.failing_only:
        selected = [r for r in records if r.error is not None]
        if not selected:
            print("No error boundaries in this session.")
            return 0
    else:
        selected = records

    all_passed = True
    for record in selected:
        result = replay_boundary(record)
        recorded_error = record.error["type"] if record.error else None

        status = "PASS" if result.passed else "FAIL"
        summary = (
            f"[{record.index:04d}] {status}"
            f"  recorded={result.recorded_survivor_count}"
            f"  replayed={result.replayed_survivor_count}"
        )
        if recorded_error:
            summary += f"  error={recorded_error}"
        print(summary)

        if not result.passed:
            all_passed = False
            if result.diffs:
                for diff in result.diffs:
                    print(f"  DIFF: {diff}")
            if args.verbose:
                if result.unmatched_recorded:
                    print(f"  unmatched_recorded ({len(result.unmatched_recorded)}):")
                    for c in result.unmatched_recorded:
                        print(f"    {c}")
                if result.unmatched_replayed:
                    print(f"  unmatched_replayed ({len(result.unmatched_replayed)}):")
                    for c in result.unmatched_replayed:
                        print(f"    {c}")
        elif args.verbose and result.diffs:
            # Passed but diffs present (shouldn't normally happen; surface if so)
            for diff in result.diffs:
                print(f"  DIFF: {diff}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
