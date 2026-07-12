# Known Bug: no faint-queue rebuild after post-KO replacements

Status: **FIXED 2026-07-11** (C++, new repo). `cpp_drain_faint_queue` (orchestrate.cpp)
now rebuilds the queue after each drain pass and keeps draining until no fainted active
with a live bench remains — hazard-killed replacements are re-prompted immediately,
matching the real game. Tests: `tests/test_faint_queue_rebuild.py` (red pre-fix, green
post-fix). Gates: frozen 1028 + fast suite + native ctest clean; the 100k extended corpus
lost exactly 2 stale Python-parity traces that encoded this bug — quarantined, then
retired along with the whole random Python-parity corpus in the 2026-07-12 rebase to the
C++ self-regression manifest gate (see TODO.md "Re-base" entry, record
`cpp_manifest_gate`). See record `faint_queue_no_rebuild_bug`.

Original deferral: user decision 2026-07-04 (Stage A exit gate review) — fix in the new
repo under golden-trace verification.

## Behavior

When a post-KO replacement dies to entry hazards during the post-faint drain, neither engine
re-prompts for another replacement:

- Python: `simulator.py` `_phase_await_post_faint_switch` drains `pending_faint_queue` and calls
  `_finalize_turn()` directly — no re-run of `_check_fainted`.
- C++: `cpp_drain_faint_queue` (orchestrate.cpp) mirrors this exactly ("no queue rebuild after
  replacements").

The next turn therefore begins with a fainted active on the field. In real Run&Bun this state is
unreachable: the game re-prompts until a replacement survives entry (or the side is out of mons).
The engines instead give the opponent a free turn against an empty slot.

## Symptom that exposed it

`cpp_run_game` skips fainted actives at action selection (orchestrate.cpp "Skip fainted active
slots"), so the action_log gets an EMPTY per-side list for that turn. The c17h gate replay feeds
it to the Python Simulator, whose `_begin_turn` mega-check indexes `actions[0]` →
`IndexError: list index out of range`, counted as `[err]`.

Observed: 10 / 100,000 battles at gate master seed 20260630 (indices 4287, 8273, 12611, 16127,
41329, +5 more past the 5-failure report cap). 0 divergences among the other 99,990.

Repro: `python SCRIPTS/c17h_repro_battle.py --index 4287`

## Pre-existing

The identical IndexError reproduces at pre-Stage-A commit 2294c69 — NOT a Stage A regression.
Stage A's behavior-preservation claim is unaffected.

## Proper fix (DONE 2026-07-11)

Rebuilt the faint queue after applying replacements: `cpp_drain_faint_queue` loops
`cpp_build_faint_queue` after each drain pass until no fainted active with a live bench
remains, matching the real game. This supersedes the retired "no queue rebuild" mirror
decision and changes trajectories only for the rare hazard-death battles. The old Python
engine is retired and shares the bug, so no lockstep change was needed there — the C++
engine is now the sole authority. Trajectory changes surfaced as 2 invalidated 100k traces
(quarantined; the whole random corpus was later retired by the 2026-07-12 manifest rebase).
