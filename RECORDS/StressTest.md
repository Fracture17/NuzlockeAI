# stress_test.py — Looped Battle Fuzzer

`SCRIPTS/stress_test.py` is the bug-discovery engine for the battle-capture +
sweep pipeline. It plays random battles back-to-back until something faults,
recording every sweep boundary so each failure is an offline-replayable repro.

## What it does

Each run it picks a random state subfolder from `--states-dir`, kills any live
mGBA, launches a fresh instance, loads the save state, auto-initialises the
battle (equivalent to pressing `O` in `play.py`), then plays it to the end. The
driving policy is **100% `RandomPolicy`** (near-instant, maximises throughput).
After every turn the full candidate sweep runs exactly as in live play.

> Historical note: this used to be an 80/20 split with `GreedyPolicy`. The greedy
> searcher was dropped in the migration to this repo, so `_make_policy` now returns
> `RandomPolicy` unconditionally. Coverage is therefore random-policy-shaped — see
> the coverage caveat in README.md.

The loop continues only while the outcome is `OK` or `FAILURE`. Any other
outcome (notably `CRASHED`) **stops the loop** — that is the signal a bug was
found. `Ctrl+C` stops it manually and prints final totals.

## How to run

```bash
# from project root, with the venv active
python SCRIPTS/stress_test.py [--states-dir PATH] [--timeout SECS]
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--states-dir` | `States/` | Dir of state subfolders, each with `config.json` + one `*.ss*` file |
| `--timeout` | `1200` | Per-battle hard timeout in seconds |

Each `States/<name>/config.json` must contain integer `opponent_index` and
`level_cap`, e.g. `{"opponent_index": 7, "level_cap": 12}`. A subfolder with a
missing/invalid config or zero/multiple `.ss*` files makes startup fail loudly.

### Running it for autonomous bug-hunting

Launch it as a **tracked background task** (not detached with `nohup`/`&`) so the
harness notifies you when it halts on a crash — that completion event is the
crash-triggered wake-up:

```bash
python SCRIPTS/stress_test.py 2>&1 | tee /tmp/vision/stress/stress_run_$(date +%Y%m%d_%H%M%S).out
```

Do not poll it on a timer; wait for the task-completion notification.

## Per-battle outcomes

| Outcome | Meaning | Loop continues? |
|---------|---------|-----------------|
| `OK` | Battle finished, no new sweep errors | yes (log purged) |
| `FAILURE` | `TeamFailureError` — team can't win the position; an *expected* battle result, not a pipeline fault | yes |
| `STUCK` | Same OCR text for >10s — a hung/frozen screen | no |
| `TIMEOUT` | Battle exceeded `--timeout` | no |
| `ERRORS` | Battle ended but new `sweep_errors/*.json` appeared | no |
| `CRASHED` | Unhandled exception (usually `SimulationError`/`UninjectedRNGError`) or mGBA died | no |

`OK` logs are deleted automatically — only failing runs keep their log.

## Outputs

| Path | Contents |
|------|----------|
| stdout / `.out` tee | Run banners + the `Run N → OUTCOME` and `Totals:` summary lines |
| `/tmp/vision/stress/run_NNNN_<state>_<ts>.log` | Full per-run capture/sweep trace (kept only for non-`OK` runs) |
| `/tmp/vision/recordings/<ts>/` | Flight-recorder session for that battle — one `boundary_*.{input,output,error}.pkl` per turn |
| `/tmp/vision/sweep_errors/*.json` | One JSON per sweep error (drives the `ERRORS` outcome) |

The recording session path is printed at battle init as `[recorder] Session: …`.

## Debugging a CRASHED run

1. **Read the tail of the run log** (or the `.out`) for the traceback. A
   `SimulationError: No candidates survived sweep: …` line names the species and
   the observed `hp_deltas` for the offending turn.

2. **Find the recording session and the failing boundary.** The newest dir under
   `/tmp/vision/recordings/` is this battle; the boundary with an `.error.pkl` is
   the crash turn.

   ```python
   import liveplay.sweep_recorder as sr
   recs = sr.load_session("/tmp/vision/recordings/<ts>")
   for r in recs:
       if r.error: print(r.index, r.error["type"], r.error["message"][:120])
   ```

3. **Inspect the messages and HP deltas** of the failing boundary (and the ones
   before it) to understand what the game actually did:

   ```python
   for r in recs:
       print("== boundary", r.index, "==")
       for m in r.inputs["messages"]:
           print("  ", m.string_id, list(m.var_values) if m.var_values else "")
   ```

4. **Reproduce offline** by feeding the boundary inputs straight into the engine.
   Current signature is `messages, hp_deltas, initial_candidates, action_groups`:

   ```python
   inp = recs[N].inputs
   sr.run_candidate_sweep(
       messages=inp["messages"], hp_deltas=inp["hp_deltas"],
       initial_candidates=inp["initial_candidates"],
       action_groups=inp.get("action_groups"),
   )
   ```

   To see *why* candidates die, monkeypatch the relevant filter (e.g. wrap
   `sr.check_log_events` to print `capturing` events and its return value) and
   re-run — fully deterministic, no emulator needed.

### CRITICAL: verifying a fix needs a *chained* replay, not an isolated one

Each boundary's `initial_candidates` were frozen **by the engine version that
recorded them**. If a bug spans turns — e.g. a stat drop on turn 1 that should
weaken a hit on turn 2 — replaying the turn-2 boundary alone still feeds the
*old, wrong* turn-1 state, so it will keep failing even after a correct fix. That
is expected and does **not** mean the fix is wrong.

To truly verify, replay from an earlier good boundary forward, threading each
boundary's fresh survivors into the next as `initial_candidates`:

```python
surv = recs[1].inputs["initial_candidates"]          # last known-good input
for i in (1, 2):                                     # the affected turns
    surv = sr.run_candidate_sweep(
        messages=recs[i].inputs["messages"],
        hp_deltas=recs[i].inputs["hp_deltas"],
        initial_candidates=surv,
        action_groups=recs[i].inputs.get("action_groups"),
    )
    print("boundary", i, "survivors:", len(surv))
```

A non-empty survivor list through the previously-failing boundary confirms the
fix. (This is how the Play Nice cross-turn Attack-drop crash was verified.)

5. **Or use the replay harness** for the standard PASS/FAIL report — see
   `RECORDS/DebugScript.md` (`SCRIPTS/replay_sweep.py`). Note its per-error-boundary
   semantics: after a fix lands, an error boundary reports `FAIL` with
   `DIFF: Recorded X but replay succeeded with N survivor(s)` — that FAIL is the
   confirmation the crash is gone. It does **not** do the chained replay above, so
   for cross-turn bugs prefer the manual chain.

## Caveats

- Every run **kills the running mGBA** (`_kill_existing_mgba`); close any mGBA
  work first. Kill zombies with `pkill -9 mgba-qt`.
- The `ERRORS` check counts `sweep_errors/*.json` files; stale JSONs from old runs
  can inflate the baseline. Check mtimes if `ERRORS` seems spurious.
- Recordings are pickles of live `BattleState`/`Candidate` objects. Refactoring
  those dataclasses breaks old sessions — fine, they're disposable once fixed.
- `Uninjected Category-B RNG event consumed under warn profile: … (side N)` WARNING lines
  are **benign**, not failures. The sweep re-simulates each turn under a silent-default luck
  profile (`SWEEP_LUCK`); a status roll (paralysis, infatuation, etc.) for a mon that the game
  showed *acting* is consumed but not injected, so it defaults to the silent "can act" branch
  and logs this. A genuine desync surfaces downstream as an HP/log mismatch (`ERRORS`/`CRASHED`).
  These are deduped per sweep call: each unique line prints once with a `[xN]` occurrence count.
- A passing sweep is only as strict as `check_log_events`. If a validation
  constraint is missing, the sweep can silently accept a wrong post-turn state and
  the real divergence surfaces a turn later. When a crash's HP delta looks correct
  in isolation, suspect an *earlier* unvalidated boundary.
