# random_battle_fuzz.py — Engine Consistency Fuzzer

`SCRIPTS/random_battle_fuzz.py` is a pure-Python (no emulator, no OCR)
bug-discovery tool for the **battle engine itself**. It generates random battles
and plays them to completion with uniformly-random legal actions on both sides
under real RNG, looping forever until a battle throws. Any unhandled exception is
treated as a detected internal inconsistency and is saved as a deterministic,
re-runnable replay.

This is the counterpart to `stress_test.py`: that one fuzzes the
capture+sweep *pipeline* through a live mGBA; this one fuzzes the `Simulator` /
engine in-process, so it is far faster and isolates engine bugs from vision bugs.

## What it does

Per battle:

1. Derive a per-battle `seed` from the master RNG and build
   `battle_rng = random.Random(seed)`.
2. Generate a random singles battle with `generate_battle` — `player_level` /
   `opp_level` in 5–100, `player_size` / `opp_size` in 1–6 — using `battle_rng`.
   Deep-copy the initial `BattleState`.
3. `random.seed(seed)` **after** generation (so the global `random` stream the
   engine draws from is reproducible from the seed alone).
4. Drive the `Simulator` with `luck_0 = luck_1 = LuckGroup.RANDOM` (real RNG —
   crits, misses, secondaries, flinch, etc. actually roll). At every pause:
   - `AWAIT_ACTIONS` → a uniform-random action per side from the request's
     `legal_actions_*`.
   - `AWAIT_FORCED_SWITCH` / `AWAIT_POST_FAINT_SWITCH` → a random legal switch.
   - `AWAIT_SUB_MOVE` (Metronome / Sleep Talk / Assist) → a random option.
   - `AWAIT_MOVE_RNG` / `AWAIT_RESIDUAL_RNG` (Roar target, Tri Attack, speed tie,
     Moody, Starf Berry, Acupressure, ...) → a random valid answer
     (`_rng_phase_options`).
   - Every chosen answer is appended, in order, to the replay's `answers` list.
5. A `--max-steps` budget (default 20 000 `sim.step()` calls) guards against a
   non-terminating battle; exceeding it raises `BattleStalledError`, which counts
   as a finding.

**Inconsistency = any unhandled exception** during the battle: `SimulationError`,
`UninjectedRNGError`, an `assert`, a `KeyError`, a stall, anything. Clean battles
leave no artifacts.

### Why AVERAGE_LUCK would be the wrong choice here

`LuckGroup.AVERAGE` (and GOOD/BAD) are **deterministic** — they compare against
fixed thresholds and never call `random.random()` (see `src/rng.py:174` and the
`random_mode` gate at `src/rng.py:246`). Under AVERAGE, normal-probability
branches (e.g. a ~6% crit) **never fire**, so a whole class of engine paths would
go untested. Only `LuckGroup.RANDOM` (`LuckProfile(random_mode=True)`,
`src/rng.py:232`) rolls real dice — which is why the fuzzer uses it.

## How to run

```bash
# from project root, with the venv. Use -u (unbuffered): when stdout is piped
# (tee, a redirect, a monitor) Python block-buffers it, so the per-100-battle
# progress lines and [CRASH] lines are withheld for many minutes. -u flushes them live.
.venv/bin/python -u SCRIPTS/random_battle_fuzz.py [--seed N] [--max-steps N] [--out-dir PATH]
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--seed` | time-based | Master seed for the whole run (makes the run reproducible) |
| `--max-steps` | `20000` | Per-battle `sim.step()` budget before a stall is flagged |
| `--out-dir` | `/tmp/vision/fuzz` | Where crash replays are written |
| `--replay PATH` | — | Replay a saved crash pickle instead of fuzzing (see below) |

It prints a `battles=… crashes=… (rate/s)` line every 100 battles, a `[CRASH]`
line with the error repr whenever a battle throws, and a final summary on
`Ctrl+C`. The loop does **not** stop on a crash — it saves the replay and keeps
going, so one run surfaces many distinct bugs.

### Autonomous bug-hunting

Launch it as a tracked background task and let it accumulate `crash_*.pkl` files
in `--out-dir`; triage them afterward. Pass a fixed `--seed` if you want the exact
same battle stream again.

## Outputs

Only crashes write to disk (clean battles are silent). In `--out-dir`:

| Path | Contents |
|------|----------|
| `crash_<ts>_seed<N>.pkl` | Pickled `FuzzReplay`: `seed`, `params`, `initial_state`, `answers`, `error_repr`, `traceback` |
| `crash_<ts>_seed<N>.txt` | Human-readable header: seed, params, step count, error, traceback |

## Replaying / debugging a crash

The whole point of the replay format (`seed + initial state + recorded answers`)
is exact reproduction without the emulator. Re-running re-seeds the global
`random` module to the saved seed and feeds the recorded answers back, so the
engine's real-RNG resolves draw the identical stream and the crash recurs at the
same step.

```bash
.venv/bin/python SCRIPTS/random_battle_fuzz.py --replay /tmp/vision/fuzz/crash_<ts>_seed<N>.pkl
```

It prints the recorded vs. replayed outcome and `REPRODUCED` / `DID NOT
REPRODUCE`. To debug interactively, load the replay and drive it yourself:

```python
import importlib.util, sys
spec = importlib.util.spec_from_file_location("f", "SCRIPTS/random_battle_fuzz.py")
f = importlib.util.module_from_spec(spec); sys.modules["f"] = f; spec.loader.exec_module(f)

rep = f.load_replay("/tmp/vision/fuzz/crash_<ts>_seed<N>.pkl")
print(rep.error_repr)
print(rep.traceback)

# Step through up to the crash to inspect state just before it:
import random, copy
from src.simulator import Simulator
from src.rng import LuckGroup
random.seed(rep.seed)
state = copy.deepcopy(rep.initial_state)
sim = Simulator(); sim.luck_0 = sim.luck_1 = LuckGroup.RANDOM
res = sim.start(state)
for i, ans in enumerate(rep.answers):
    if res.done: break
    try:
        res = sim.step(ans)
    except Exception as e:
        print("crashed feeding answer", i, ans, "->", repr(e))
        break
    print("step", i, "phase", res.request.phase if res.request else "DONE")
```

From there: print `res.state` (or `res.request.state`) before the failing step,
narrow to the species/move involved, and reproduce the same situation in a focused
unit test in `tests/`.

### Reproduction caveats

- **Determinism depends on a deterministic engine.** Replay seeds the *global*
  `random` module; if engine code ever introduces a second, unseeded entropy
  source (e.g. `secrets`, `os.urandom`, set/dict iteration order over unhashable
  objects), replays of real-RNG battles will drift. Action selection and engine
  RNG are deliberately two independent streams (`battle_rng` vs. the global
  module), and only the global one is needed for replay because the recorded
  answers already pin every choice.
- The replay pickles live `BattleState` / `Action` objects. Refactoring those
  dataclasses breaks old pickles — fine, they're disposable once the bug is fixed.
- A crash found here is an engine bug regardless of how "unrealistic" the random
  line was; random play legitimately reaches states the AI never would, which is
  exactly the value of the fuzzer.

## Tests

`tests/test_random_battle_fuzz.py` covers: completed battles replay to an
identical winner + final state, the recorded answer stream is stable across runs
of the same seed, an injected exception is recorded with its triggering answer and
reproduced on replay, and crashes write a loadable artifact while clean runs write
nothing.
