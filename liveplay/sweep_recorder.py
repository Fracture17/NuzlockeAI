# Flight recorder for sweep boundary transitions.
# On-disk layout: session_dir/<timestamp>/, one boundary_NNNN.{input,output,error}.json per boundary.
# input written before sweep; output (survivors list) or error (type/str/traceback) written after.
# parent_candidate stripped before writing to prevent O(n²) ancestry chains.
# Legacy pickle-era files (.pkl) are detected and rejected loudly — not silently decoded.
import json
import os
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import dataclasses

from liveplay.candidate import Candidate
from liveplay.rng import UninjectedRNGError
from liveplay.engine_select import SimulationError
from liveplay.engine_select import run_candidate_sweep
from liveplay.state.battle import BattleState
from liveplay.state.pokemon import PokemonState
from liveplay.state.side import SideState
from liveplay.sweep_io import to_jsonable, from_jsonable

DEFAULT_BASE_DIR = Path("/tmp/vision/recordings")


def _strip_parent(candidate: Candidate) -> Candidate:
    """Return a shallow copy of candidate with parent_candidate set to None."""
    return Candidate(
        state=candidate.state,
        rng_sequence=candidate.rng_sequence,
        unknown_actions=candidate.unknown_actions,
        parent_candidate=None,
    )


def _write_json(path: Path, data: object) -> None:
    """Encode data via sweep_io, serialize to JSON, and write with flush+fsync."""
    text = json.dumps(to_jsonable(data))
    raw = text.encode("utf-8")
    with open(path, "wb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())


def _read_json(path: Path) -> object:
    """Read and decode a sweep_io JSON file. Raises ValueError on pickle-era files."""
    raw = path.read_bytes()
    # Pickle files begin with 0x80 (protocol opcode). Fail loudly before any decode attempt.
    if raw and raw[0] == 0x80:
        raise ValueError(
            f"legacy pickle session; use the old reader from git history — file: {path}"
        )
    return from_jsonable(json.loads(raw.decode("utf-8")))


@dataclass
class BoundaryRecord:
    """Loaded representation of one boundary: inputs plus either survivors or error."""
    index: int
    inputs: dict                    # keys: messages, hp_deltas, initial_candidates, action_groups.
                                    # hp_deltas is a list of HpDeltaSeq identity-bound records.
    survivors: Optional[list]       # list[Candidate] if sweep succeeded, else None
    error: Optional[dict]           # {"type": str, "message": str, "traceback": str} on failure


@dataclass
class ReplayResult:
    """Result of replaying a recorded boundary against the real sweep engine."""
    passed: bool
    recorded_survivor_count: int
    replayed_survivor_count: int
    unmatched_recorded: list = field(default_factory=list)   # Candidates in recorded but not replayed
    unmatched_replayed: list = field(default_factory=list)   # Candidates in replayed but not recorded
    diffs: list = field(default_factory=list)                # human-readable divergence descriptions


class SweepRecorder:
    """Records sweep boundary inputs/outputs to a session directory for offline replay."""

    def __init__(self, session_dir: Path) -> None:
        self.session_dir = session_dir
        self._next_index: int = 0

    @classmethod
    def create(cls, base_dir: Path = DEFAULT_BASE_DIR) -> "SweepRecorder":
        """Create a new session directory and return a SweepRecorder bound to it."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        session_dir = Path(base_dir) / timestamp
        session_dir.mkdir(parents=True, exist_ok=True)
        return cls(session_dir)

    def record_input(
        self,
        *,
        messages,
        hp_deltas,
        initial_candidates,
        action_groups=None,
    ) -> int:
        """Persist boundary inputs; return the boundary index."""
        idx = self._next_index
        self._next_index += 1
        stripped_candidates = [_strip_parent(c) for c in initial_candidates]
        data = {
            "messages": messages,
            "hp_deltas": hp_deltas,
            "initial_candidates": stripped_candidates,
            "action_groups": action_groups,
        }
        _write_json(self.session_dir / f"boundary_{idx:04d}.input.json", data)
        return idx

    def record_output(self, idx: int, survivors: list) -> None:
        """Persist successful sweep output."""
        stripped = [_strip_parent(c) for c in survivors]
        _write_json(self.session_dir / f"boundary_{idx:04d}.output.json", {"survivors": stripped})

    def record_failure(self, idx: int, exc: Exception) -> None:
        """Persist a sweep failure as a plain-dict JSON payload (no sweep_io encoding needed)."""
        data = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        # Error records are plain string dicts; write raw JSON (no to_jsonable round-trip needed).
        text = json.dumps(data)
        path = self.session_dir / f"boundary_{idx:04d}.error.json"
        raw = text.encode("utf-8")
        with open(path, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())


def record_and_run(
    recorder: SweepRecorder,
    *,
    messages,
    hp_deltas,
    initial_candidates,
    action_groups=None,
) -> list:
    """Record input, run the real sweep, record output or failure, re-raise on any exception.

    This is the live-play seam. All exceptions are recorded then re-raised unchanged —
    the caller's fatal-halt contract.
    """
    idx = recorder.record_input(
        messages=messages,
        hp_deltas=hp_deltas,
        initial_candidates=initial_candidates,
        action_groups=action_groups,
    )
    try:
        survivors = run_candidate_sweep(
            messages=messages,
            hp_deltas=hp_deltas,
            initial_candidates=initial_candidates,
            action_groups=action_groups,
        )
    except Exception as exc:
        recorder.record_failure(idx, exc)
        raise
    recorder.record_output(idx, survivors)
    return survivors


def load_session(session_dir) -> list:
    """Load all boundary records from a session directory, sorted by index.

    Raises ValueError if any input file uses the legacy pickle format.
    Raises if any existing input file is unloadable.
    """
    session_dir = Path(session_dir)

    # Detect legacy sessions: any .pkl file means this is a pickle-era session directory.
    pkl_files = list(session_dir.glob("boundary_*.input.pkl"))
    if pkl_files:
        raise ValueError(
            f"legacy pickle session; use the old reader from git history — "
            f"found: {pkl_files[0].name}"
        )

    input_paths = sorted(session_dir.glob("boundary_*.input.json"))
    records = []
    for input_path in input_paths:
        stem = input_path.stem  # e.g. "boundary_0000.input"
        prefix = stem.split(".")[0]  # "boundary_0000"
        idx = int(prefix.split("_")[1])
        inputs = _read_json(input_path)

        output_path = session_dir / f"boundary_{idx:04d}.output.json"
        error_path = session_dir / f"boundary_{idx:04d}.error.json"

        survivors = None
        error = None
        if output_path.exists():
            survivors = _read_json(output_path)["survivors"]
        elif error_path.exists():
            error = json.loads(error_path.read_bytes().decode("utf-8"))

        records.append(BoundaryRecord(index=idx, inputs=inputs, survivors=survivors, error=error))
    return records


_SIDE_SKIP_FIELDS = frozenset({"team", "format"})
_MON_SCALAR_FIELDS = [f for f in dataclasses.fields(PokemonState) if f.name != "timed_volatiles"]


def diff_battle_states(a: BattleState, b: BattleState) -> list:
    """Return a list of strings naming every divergence between two BattleStates.

    Covers all PokemonState fields (via dataclasses.fields) and all scalar SideState
    fields. team/format are skipped at the side level since team is iterated per-mon.
    """
    diffs = []
    for side_idx in range(len(a.sides)):
        if side_idx >= len(b.sides):
            diffs.append(f"side {side_idx}: missing in b")
            continue
        sa = a.sides[side_idx]
        sb = b.sides[side_idx]

        # Side-level scalar fields
        for f in dataclasses.fields(SideState):
            if f.name in _SIDE_SKIP_FIELDS:
                continue
            pv = getattr(sa, f.name)
            qv = getattr(sb, f.name)
            if pv != qv:
                diffs.append(f"side {side_idx}.{f.name}: {pv!r} vs {qv!r}")

        for mon_idx in range(max(len(sa.team), len(sb.team))):
            if mon_idx >= len(sa.team) or mon_idx >= len(sb.team):
                diffs.append(f"side {side_idx} mon {mon_idx}: team length mismatch")
                continue
            ma = sa.team[mon_idx]
            mb = sb.team[mon_idx]

            # All PokemonState scalar fields
            for f in _MON_SCALAR_FIELDS:
                pv = getattr(ma, f.name)
                qv = getattr(mb, f.name)
                if pv != qv:
                    diffs.append(f"side {side_idx} mon {mon_idx}.{f.name}: {pv!r} vs {qv!r}")

            # timed_volatiles is a list; compare separately
            if ma.timed_volatiles != mb.timed_volatiles:
                diffs.append(
                    f"side {side_idx} mon {mon_idx}.timed_volatiles:"
                    f" {ma.timed_volatiles!r} vs {mb.timed_volatiles!r}"
                )
    return diffs


def _nearest_diff(recorded: Candidate, replayed_pool: list) -> list:
    """Return diff_battle_states between recorded and the closest replayed candidate by diff count."""
    if not replayed_pool:
        return ["(no replayed candidates)"]
    best = min(replayed_pool, key=lambda r: len(diff_battle_states(recorded.state, r.state)))
    return diff_battle_states(recorded.state, best.state)


def replay_boundary(record: BoundaryRecord) -> ReplayResult:
    """Re-run the recorded inputs through the real sweep and compare results.

    For a success boundary: pass iff recorded and replayed survivors match as an
    order-independent multiset (compared by Candidate equality, not hash).
    For an error boundary: pass iff replay raises the same exception type name.
    """
    inputs = record.inputs
    try:
        replayed = run_candidate_sweep(
            messages=inputs["messages"],
            hp_deltas=inputs["hp_deltas"],
            initial_candidates=inputs["initial_candidates"],
            action_groups=inputs.get("action_groups"),
        )
        replayed_error_type = None
    except (SimulationError, UninjectedRNGError) as exc:
        replayed = []
        replayed_error_type = type(exc).__name__

    # Error boundary case
    if record.error is not None:
        recorded_type = record.error["type"]
        passed = replayed_error_type == recorded_type
        diffs = []
        if not passed:
            if replayed_error_type is None:
                diffs = [f"Recorded {recorded_type} but replay succeeded with "
                         f"{len(replayed)} survivor(s)"]
            else:
                diffs = [f"Recorded {recorded_type} but replay raised {replayed_error_type}"]
        return ReplayResult(
            passed=passed,
            recorded_survivor_count=0,
            replayed_survivor_count=len(replayed),
            diffs=diffs,
        )

    # Success boundary case — multiset comparison by equality
    if replayed_error_type is not None:
        return ReplayResult(
            passed=False,
            recorded_survivor_count=len(record.survivors or []),
            replayed_survivor_count=0,
            diffs=[f"Expected success but got {replayed_error_type}"],
        )

    recorded = list(record.survivors or [])
    replayed_remaining = list(replayed)
    unmatched_recorded = []

    for rec_cand in recorded:
        matched = False
        for i, rep_cand in enumerate(replayed_remaining):
            if rec_cand == rep_cand:
                replayed_remaining.pop(i)
                matched = True
                break
        if not matched:
            unmatched_recorded.append(rec_cand)

    unmatched_replayed = replayed_remaining

    all_diffs = []
    for rec_cand in unmatched_recorded:
        candidate_diffs = _nearest_diff(rec_cand, list(replayed))
        all_diffs.extend(candidate_diffs)

    passed = not unmatched_recorded and not unmatched_replayed
    return ReplayResult(
        passed=passed,
        recorded_survivor_count=len(recorded),
        replayed_survivor_count=len(replayed),
        unmatched_recorded=unmatched_recorded,
        unmatched_replayed=unmatched_replayed,
        diffs=all_diffs,
    )
