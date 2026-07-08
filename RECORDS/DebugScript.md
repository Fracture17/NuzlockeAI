# debug_sweep.py — Automated Sweep Pipeline Debugger

`SCRIPTS/debug_sweep.py` auto-plays a battle with a fixed move sequence and runs the full sweep pipeline on each turn, writing all output to stdout and `/tmp/vision/debug_sweep.log`.

## Before running

The script must be the sole owner of the mGBA socket. On startup it automatically kills any running mGBA instance via `pkill mgba-qt`, waits 400ms, then launches a fresh one. **Every run therefore terminates the previous emulator session** — close any work in mGBA before running.

If a previous run crashed and left a zombie process that `pkill` misses, kill it manually before the next run:

```bash
pkill -9 mgba-qt
```

## What it does

On startup it launches a fresh mGBA instance, loads a save state, and auto-initializes the battle state (equivalent to pressing O in `play.py`). It then loops: periodically OCR-captures the screen, presses B to advance text, and when the action-select screen appears it inputs the next move from the sequence. After each turn, the sweep pipeline runs exactly as it does in live play. The script exits when `STRINGID_BATTLEEND` is detected or on Ctrl+C.

## Outputs

| Path | Contents |
|------|----------|
| `/tmp/vision/debug_sweep.log` | Full stdout mirror (timestamped captures, sweep results) |
| `/tmp/vision/debug_sweep.done` | `OK`, `ERRORS`, or `INTERRUPTED` — written at exit |
| `/tmp/vision/sweep_errors/*.json` | One JSON file per sweep error (see below) |

### Sweep error JSON fields
- `error` — human-readable description of which check failed
- `player_hp_deltas` — observed player HP delta list for the turn
- `opponent_hp_deltas` — observed opponent HP bar k-values for the turn
- `messages` — list of `{string_id, var_values}` matched that turn

## Usage

```
python SCRIPTS/debug_sweep.py [--moves SLOT [SLOT ...]] [--opponent IDX] [--state PATH]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--moves` | `[0]` | Move slots (0–3) to use, cycling each turn. Slot layout matches the 2×2 fight grid: 0=top-left, 1=top-right, 2=bottom-left, 3=bottom-right. |
| `--opponent` | same as `play.py` | Index into the trainers list for the battle opponent. |
| `--state` | `/home/Fracture/Downloads/RunNBun.ss2` | mGBA save state loaded immediately on startup. |

### Examples

```bash
# Use move slot 0 every turn (default)
python SCRIPTS/debug_sweep.py

# Alternate between slot 0 and slot 2
python SCRIPTS/debug_sweep.py --moves 0 2

# Use slot 2 (Fury Attack) against trainer 5, starting from a different state
python SCRIPTS/debug_sweep.py --moves 2 --opponent 5 --state ~/Downloads/other.ss2
```

## Checking results

```bash
# Follow sweep output live
tail -f /tmp/vision/debug_sweep.log | grep -E '\[sweep\]|candidate|survived|ERRORS|OK'

# Block until done, then show result
until [ -f /tmp/vision/debug_sweep.done ]; do sleep 1; done; cat /tmp/vision/debug_sweep.done

# Inspect the latest sweep error
python -c "
import json, pathlib
errors = sorted(pathlib.Path('/tmp/vision/sweep_errors').glob('*.json'))
print(json.loads(errors[-1].read_text()) if errors else 'no errors')
"
```

## Limitations

- Only one move is selected per turn; there is no support for switching or using items.
- mGBA is relaunched from scratch on every run, so the save state must place the game directly in front of the battle (on the battle intro screen).

---

# Sweep Flight Recorder & Replay

Every battle run by `play.py`, `debug_sweep.py`, or `stress_test.py` automatically records each sweep decision boundary to a session directory under `/tmp/vision/recordings/<timestamp>/` (one session per battle; the path is printed at battle init as `[recorder] Session: …`). Inputs are written **before** the sweep runs and fsynced, so sessions survive hard crashes — every live failure is an offline-replayable repro.

## Session contents

| File | Contents |
|------|----------|
| `boundary_NNNN.input.json` | Sweep inputs: messages, identity-bound HP deltas, initial candidates |
| `boundary_NNNN.output.json` | Surviving candidates (written only if the sweep succeeded) |
| `boundary_NNNN.error.json` | Exception type/str/traceback (written only if it raised) |

Recordings are `liveplay/sweep_io.py` JSON payloads; legacy pickle-era sessions (`.pkl`) are detected and rejected loudly rather than silently decoded.

## Failure behavior

A sweep that finds zero candidates raises `SimulationError`; a strict-mode RNG event consumed without injection raises `UninjectedRNGError`. Both are fatal: the error JSON path and recording session path are printed, then the process halts (`stress_test.py` marks the run `CRASHED` and moves on to the next battle).

## replay_sweep.py — replay a session offline

```
python SCRIPTS/replay_sweep.py [session_dir] [--boundary N] [--failing-only] [--verbose]
```

| Flag | Description |
|------|-------------|
| `session_dir` | Session to replay. Defaults to the most recent under `/tmp/vision/recordings/`. |
| `--boundary N` | Replay only boundary N. |
| `--failing-only` | Replay only error boundaries. |
| `--verbose` | Print full state diffs for mismatches. |

Exit code 0 iff every boundary passes. Per-boundary semantics:

- **Success boundary**: PASS iff replayed survivors match recorded survivors exactly (order-independent). A FAIL with `DIFF:` lines means a code change altered simulation behavior for those inputs.
- **Error boundary**: PASS iff the replay raises the same exception type. After fixing the bug, the boundary reports FAIL with `DIFF: Recorded X but replay succeeded with N survivor(s)` — that FAIL is the confirmation the fix works.

```bash
# Replay the most recent session
python SCRIPTS/replay_sweep.py

# Re-check just the crash boundary of a specific session
python SCRIPTS/replay_sweep.py /tmp/vision/recordings/20260609_203801_007512 --failing-only --verbose
```

## Programmatic debugging (liveplay/sweep_recorder.py)

`load_session(dir)` returns `BoundaryRecord`s whose `.inputs` dict feeds `run_candidate_sweep` directly — the standard probe pattern for diagnosing a recorded failure:

```python
from liveplay.sweep_recorder import load_session
import liveplay.engine_select as sr

inp = load_session("/tmp/vision/recordings/<ts>")[3].inputs   # failing boundary index
survivors = sr.run_candidate_sweep(
    messages=inp["messages"],
    hp_deltas=inp["hp_deltas"],
    initial_candidates=inp["initial_candidates"],
    action_groups=inp.get("action_groups"),
)
```

**Stage E note:** in this repo `run_candidate_sweep` is a seam stub that raises `NotImplementedError` until the C++ sweep is wired; until then, run the probe in the old repo (`PycharmProjects/NuzlockeAI`, `import src.simulation_runner as sr`) where the Python sweep still lives.

To find *why* candidates are rejected, monkeypatch the relevant filter (e.g. wrap the sweep's `_check_log_events` to dump `capturing.events` and its return value) and re-run the boundary — fully deterministic, no emulator needed. `replay_boundary(record)` and `diff_battle_states(a, b)` are also importable for custom comparisons.
