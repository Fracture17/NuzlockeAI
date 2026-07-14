# Phase 2 state snapshot — PAUSED 2026-07-14

Phase 2 (SOLVER_PHASE2_PLAN.md) is paused: the user is pivoting to a new solver design
(bsolver-like but faster; spec to follow). Pessimal collapse stays as a LOSS-pruner.
The analytic certifier is the only part likely retired; oracle, MatchupGen, bsolver
infrastructure, and the audit harnesses are all kept. This file records where Task 7
stood so the lemma-wave work can resume if the pivot is reversed.

## Task status at pause
- Tasks 1–6: COMPLETE. Suite green at 222 cases / 22,796 assertions.
- Task 7 (lemma waves): paused at the wave-1 decision point. Zero waves implemented.
  Referee validated first (injected fixtures + CertifierFn seam; all five verification
  paths proven: exact-adjudicated WIN, exact LOSS, WIN-on-LOSS failure, LOSS-on-WIN
  failure [loss_vs_exact_win, printed first], UNKNOWN passthrough at zero cost).
- Task 8: not started.

## Session hardening that predates the pause (all kept)
- bsolver runs b_win on a dedicated pthread, 256 MB stack (BsolverConfig::stack_size);
  depth_cap=500 safe; ccheck sash: exact 215.7ms / pessimal 45.4ms / coarse 94.0ms, clean.
- Oracle collapse probs are NaN-poisoned (Pessimal/Coarse); Exact bit-identical (tested).
- MatchupGen: player side item-free 30% in every class (USER decision); opp always holds
  the class item. Starf regression fixture made self-locating.

## Wave-1 measured data (fast scans, n=20000/class, seed 1, wave-0 analytic)
Decided: 0 in all classes (ITEM_NOT_ALLOWED gates 99.5% uniform / 97.7% berry / 85.4%
sash; opp item allowlist is only NONE/Sitrus/Sash). Unlock counts if a wave cleared W
(mask ⊆ W; tool: `audit_analytic --combo-top 10000 | SCRIPTS/wave_unlock.py`):

| W (bits cleared)                          | uniform | berry | sash |
|-------------------------------------------|--------:|------:|-----:|
| SECONDARY                                  |       5 |    25 |  124 |
| SECONDARY+ACCURACY_LT100                   |      15 |    89 |  571 |
| +HP_DEP_BP                                 |      43 |   202 | 1348 |
| +PRIORITY                                  |      62 |   292 | 1873 |

RESIDUAL_UNKNOWN adds zero marginal unlock (perfectly co-occurs with ITEM). Open oddity:
RESIDUAL_UNKNOWN fires on 67% of sash but 0% of berry — understand before a residual wave.
Analytic latency ~5–6 µs/matchup while everything routes UNKNOWN; expect ~100 µs once
matchups enter scope (user prediction, unconfirmed).

## Resume point
Wave-1 options presented (A: SEC+ACC; B: +HP_DEP_BP; C: +PRIORITY; D: item wave first);
recommendation was A. No user pick — the pivot preempted it. To resume: re-run the scans
above (generator may have drifted), re-present options, then follow the Task 7 protocol
(regression fixture BEFORE each fix; exit gate ≥2000 decided, 3 classes × ≥3 seeds, zero
soundness failures).
