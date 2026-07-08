# JSONL golden-trace reader and validator. Read-only side of golden_trace; no record_game.
# Enums and BattleState decode via sweep_io tagged-JSON. No timestamps.
import gzip
import json
from pathlib import Path
from typing import Any

from liveplay.sweep_io import to_jsonable, from_jsonable

FORMAT_VERSION = 1


def decode_state(record: dict) -> Any:
    """Decode the BattleState from a 'header', 'snapshot', or 'end' record."""
    t = record.get("t")
    if t == "header":
        return from_jsonable(record["initial_state"])
    if t == "snapshot":
        return from_jsonable(record["state"])
    if t == "end":
        return from_jsonable(record["final_state"])
    raise ValueError(f"decode_state: unsupported record type {t!r}")


def read_trace(path) -> list:
    """Parse a JSONL trace file. Returns a list of dicts; tagged values remain encoded."""
    path = Path(path)
    if str(path).endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            content = f.read()
    else:
        content = path.read_text(encoding="utf-8")
    records = []
    for line in content.splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def validate_trace(records: list) -> None:
    """Raise ValueError unless the record list satisfies all structural invariants.

    Checks: header first with format_version==1; end last; exactly one header and end;
    rng seq strictly increasing; turn non-decreasing; occurrences contiguous 0..k per
    (turn, event) independently for rng and answer streams; before_seq non-decreasing
    across driver records; unknown 't' raises.
    """
    if not records:
        raise ValueError("validate_trace: record list is empty")

    # Header must be first and unique
    header_indices = [i for i, r in enumerate(records) if r.get("t") == "header"]
    if not header_indices:
        raise ValueError("validate_trace: no 'header' record found")
    if len(header_indices) > 1:
        raise ValueError("validate_trace: multiple 'header' records found")
    if header_indices[0] != 0:
        raise ValueError("validate_trace: 'header' is not the first record")
    if records[0].get("format_version") != FORMAT_VERSION:
        raise ValueError(
            f"validate_trace: format_version must be {FORMAT_VERSION}, "
            f"got {records[0].get('format_version')!r}"
        )

    # End must be last and unique
    end_indices = [i for i, r in enumerate(records) if r.get("t") == "end"]
    if not end_indices:
        raise ValueError("validate_trace: no 'end' record found")
    if len(end_indices) > 1:
        raise ValueError("validate_trace: multiple 'end' records found")
    if end_indices[0] != len(records) - 1:
        raise ValueError("validate_trace: 'end' is not the last record")

    _KNOWN_TYPES = {"header", "rng", "answer", "snapshot", "end"}
    rng_seq_prev: "int | None" = None
    turn_prev: "int | None" = None

    # Per-(turn, event) occurrence counters for rng and answer streams (tracked independently)
    rng_occurrence_next: dict = {}     # (turn, event_key) → next expected occurrence
    answer_occurrence_next: dict = {}  # (turn, event_key) → next expected occurrence
    driver_before_seq_prev: "int | None" = None

    body = records[1:-1]
    for i, rec in enumerate(body):
        t = rec.get("t")
        if t not in _KNOWN_TYPES:
            raise ValueError(f"validate_trace: unknown record type {t!r} at body index {i}")

        # Turn non-decreasing across entire stream (use first available turn field)
        turn = rec.get("turn")
        if turn is not None:
            if turn_prev is not None and turn < turn_prev:
                raise ValueError(
                    f"validate_trace: turn decreased from {turn_prev} to {turn} at body index {i}"
                )
            turn_prev = turn

        if t == "rng":
            seq = rec["seq"]
            if rng_seq_prev is not None and seq <= rng_seq_prev:
                raise ValueError(
                    f"validate_trace: rng seq not strictly increasing: "
                    f"{rng_seq_prev} → {seq} at body index {i}"
                )
            rng_seq_prev = seq

            event_key = json.dumps(rec["event"], sort_keys=True)
            key = (rec["turn"], event_key)
            expected = rng_occurrence_next.get(key, 0)
            occ = rec["occurrence"]
            if occ != expected:
                raise ValueError(
                    f"validate_trace: rng occurrence gap for (turn={rec['turn']}, "
                    f"event={event_key!r}): expected {expected}, got {occ} at body index {i}"
                )
            rng_occurrence_next[key] = expected + 1

        elif t == "answer":
            # Driver before_seq must be non-decreasing
            before_seq = rec["before_seq"]
            if driver_before_seq_prev is not None and before_seq < driver_before_seq_prev:
                raise ValueError(
                    f"validate_trace: answer before_seq decreased from "
                    f"{driver_before_seq_prev} to {before_seq} at body index {i}"
                )
            driver_before_seq_prev = before_seq

            event_raw = rec["event"]
            event_key = event_raw if isinstance(event_raw, str) else json.dumps(event_raw, sort_keys=True)
            key = (rec["turn"], event_key)
            expected = answer_occurrence_next.get(key, 0)
            occ = rec["occurrence"]
            if occ != expected:
                raise ValueError(
                    f"validate_trace: answer occurrence gap for (turn={rec['turn']}, "
                    f"event={event_key!r}): expected {expected}, got {occ} at body index {i}"
                )
            answer_occurrence_next[key] = expected + 1

        elif t == "snapshot":
            before_seq = rec["before_seq"]
            if driver_before_seq_prev is not None and before_seq < driver_before_seq_prev:
                raise ValueError(
                    f"validate_trace: snapshot before_seq decreased from "
                    f"{driver_before_seq_prev} to {before_seq} at body index {i}"
                )
            driver_before_seq_prev = before_seq
