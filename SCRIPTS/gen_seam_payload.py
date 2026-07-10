# Extracts a representative BattleState from a golden trace into a flat JSON payload
# the native D5 seam benchmark (engine/bench/bench_solver_seam.cpp) loads. The trace's
# luck is "RANDOM" (seeded random-mode); the seam bench runs controlled mode with
# in-harness deterministic luck, so only the initial_state is needed. Reproducible via
# a fixed default trace, overridable with --trace. Output key: "state".
import argparse
import gzip
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRACE = (
    REPO_ROOT / "tests" / "fixtures" / "golden_traces"
    / "scenario_aftermath_mold_breaker.jsonl.gz"
)
DEFAULT_OUT = Path("/tmp/d5_seam_payload.json")


def _read_header(trace_path: Path) -> dict:
    with gzip.open(trace_path, "rt") as f:
        return json.loads(next(f))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    hdr = _read_header(args.trace)
    state = hdr["initial_state"]
    args.out.write_text(json.dumps({"state": state}))
    print(f"wrote {args.out} from {args.trace.name} "
          f"(state json bytes={len(json.dumps(state))})")


if __name__ == "__main__":
    main()
