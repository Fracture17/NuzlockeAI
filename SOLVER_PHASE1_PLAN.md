# Solver Port — Phase 1 Plan (oracle seam + audit harness)

Context: porting solver concepts from the prototype at /home/Fracture/Projects/port
(read port/docs/OVERVIEW.md, AUDIT.md, PSOLVER.md, BSOLVER.md, ANALYTIC.md, CHAIN.md first).
Overall roadmap: (1) this phase, (2) psolver, (3) bsolver exact + policy-table export + B1/B2,
(4) pessimal/coarse tiers + factorized fast oracle, (5) analytic re-derivation, (6) 6v6 chain.

## Fixed decisions (user requirements)
- Solvers never touch game logic; oracle owns all turn resolution behind a lazy abortable
  adverse-first-orderable stream `step(state, action, emit)`. Two read-only engine queries
  (damage tables, HP-threshold sets) will additionally be exposed to solvers later — user
  accepted the coupling since Run & Bun mechanics are frozen.
- 1v1 only: one active per side, no switches, no battle items; player actions = legal moves
  + mega variants. Opponent = exact Run & Bun AI distribution (cpp_compute_action_probabilities).
- Offline pre-battle consumer; fights execute from an exported policy lookup table.
- Exact single states now; APIs amenable to set/interval certification later.
- Pure-random audit matchup stream now; real box-vs-encounter fights later.
- Opponent switch/bait logic lives in the 6v6 layer via B1 exit-state constraints.
- Fail loud everywhere. Prototype numbers are calibration only — measure on this engine.
- USER-CONFIRMED (2026-07-12): (a) a Question is a CONJUNCTION of positively-asserted required
  state; everything not asserted is UNCONSTRAINED. No special simultaneous-KO rule: at a terminal
  state, WIN iff every asserted condition holds, else LOSS. `requireNoFaint` means only "player
  must not be fainted" (default true for the standard "faint the opponent without fainting
  yourself" question); with it false, "can you faint the opponent?" counts a simultaneous KO
  as WIN. Classifier fully question-parametrized.
  (b) Quick Draw excluded in phase 1 (uninstrumented 30% draw; generator blocklists, oracle throws).

## Execution rules
- One coding agent at a time (no parallel agents — user requirement).
- Tests written BEFORE implementation for every task; verify before and after.
- Do NOT touch uncommitted in-flight files: turn.cpp, orchestrate.cpp, residuals.cpp,
  game_driver.cpp (+ their modified headers). Plan only depends on committed declarations
  (cpp_find_mega_entry turn.h:22-25; cpp_enumerate_legal_actions/cpp_compute_winner orchestrate.h).

## Module layout
New `engine/src/solver/` as a SEPARATE static lib `nuzlocke_solver` linking `nuzlocke_core`
(build-enforced one-way dependency). Same flags as core (-ffp-contract=off; bit-reproducible
replays). Files: oracle_types.h; transition_oracle.h/.cpp; state_codec.h/.cpp; question.h/.cpp;
action_space.h/.cpp; matchup_gen.h/.cpp; audit/audit_oracle.cpp + audit/solver_trace.cpp
(standalone exes, EXCLUDE_FROM_ALL); engine/bench/bench_oracle.cpp. Tests in engine/tests/
(Catch2 glob): test_solver_instrumentation.cpp, test_solver_codec.cpp, test_solver_question.cpp,
test_solver_oracle.cpp, test_solver_gen.cpp.

## Task 1 — Complete Cat-B RNG instrumentation + probability attribution
Files: logger.h, rng_resolver.h, move_exec_premove.cpp, core_leaf.cpp, post_hit.cpp,
move_exec_damage.cpp, damage.cpp (all committed).
- Add `double p_chosen` to AnalyticalRngEntry (keep POD; sentinel -1.0 = cannot attribute;
  every Cat-B site must attribute). Populate existing resolvers (ACCURACY eff_acc; CRIT chance;
  MULTI_HIT_COUNT 35/35/15/15; chance-based chance/100 or complement).
- Instrument uncovered sites with the exact rng_resolver.h pattern (saturation short-circuit →
  bump_occurrence → try_consume_injection w/ kind-check throw → threshold/random → log w/ p_chosen):
  - move_exec_premove.cpp: WAKE (33.3/50/100 by sleep_turns), DEFROST 20%, FULL_PARALYSIS 25%,
    CONFUSION_SNAP (25/33.3/50/100), CONFUSION_SELF_HIT 33.3%, ATTRACT 50%; confusion self-hit
    damage roll at :174-184 — VERIFY the random path's draw shape (appears 15 outcomes at 1/15,
    `85 + int(roll*15)`, NOT the main 16-value site; mirror the actual code).
  - core_leaf.cpp: QUICK_CLAW :640-651 (20%); PSYWAVE_ROLL :181-189 (k=0..100; weights 1/200 at
    k∈{0,100}, 1/100 interior; matches `50 + python_round(roll*100)`).
  - post_hit.cpp:824-826 BINDING_DURATION (4/5, 0.5 each).
  - move_exec_damage.cpp:356-358 RAMPAGE_DURATION (2/3, 0.5 each).
  - damage.cpp:1434-1448 DAMAGE_ROLL (16 options 1/16; random path rng->randint(0,15)).
- HARD RULE: random-mode RNG call order/count byte-identical before/after.
- Focus Band: no work (routes through PROC_FIRES, move_exec_helpers.cpp:102).
  Quick Draw (core_leaf.cpp:770-784): NO instrumentation — phase-1 exclusion.
Tests (test_solver_instrumentation.cpp): para inject both branches (p_chosen .25/.75); sleep 50%
tier both branches; Shell Armor + DAMAGE_ROLL inject 0 vs 15 (16 options, p 1/16); Psywave k=0→25
k=100→75 at L50 (p 1/200 at k=0); Rock Blast MULTI_HIT_COUNT 2 vs 5 (p .35/.15); same-seed
random-mode logging on vs off → state_equal; wrong-kind injection throws; unfired occurrence →
verify_exhausted throws.

## Task 2 — Solver lib scaffolding + SolverTurnResult pause extension
Files: engine/CMakeLists.txt, solver_turn.h/.cpp (committed), solver/oracle_types.h.
- CMake nuzlocke_solver lib; link into tests/bench/audit.
- Extend SolverTurnResult: {bool paused; RngEventC event; vector<int32_t> options} from
  TurnPause::needs (options currently dropped). paused=true is not an error.
- oracle_types.h: ChildOutcome{BattleState child; double prob}; emit returns bool (false=abort);
  OrderingHint{Natural, AdverseFirst}; StepStats{leaves, turn_executions, aborted, budget_exceeded};
  declared-but-throwing future queries (damage tables, HP-threshold sets).
Tests: equal-speed tie with no speed_tie_queue → paused=true, event=SPEED_TIE, options=side·10+slot;
normal turn → ok=true.

## Task 3 — State codec
Files: solver/state_codec.h/.cpp (reads state.h, state_eq.h).
- PackedKey = ctx_id(32b) | plHP(16b) | oppHP(16b). Context = solver-view state with both actives'
  HP masked canonical, hashed via state_hash_solver/state_equal_solver (do NOT extend their
  exclusion set). Interner stores masked exemplar so unpack re-materializes exact BattleState.
  HP masking isolated in ONE function (phase-4 lever). PP stays in context (provisional —
  measure growth). Fail loud: HP >16 bits, id overflow. Expose context_count().
Tests (test_solver_codec.cpp): round-trip state_equal_solver + exact HPs; HP-only diff → same ctx;
PP diff → different ctx; turn_number diff → same ctx; re-pack idempotent.

## Task 4 — Question + terminal classifier + action filter
Files: solver/question.h/.cpp. Reference: prototype psolver/solver.h Question/classify; B1 in BSOLVER.md.
- Question = CONJUNCTION of positively-asserted required terminal state; unasserted = unconstrained.
  Question{requireOppFaint=true; requireNoFaint=true; keepHp; keepItem(item id, 0=off); banMove}.
  classify(state,q)→{WIN,LOSS,CONTINUE}: terminal (either side fainted) → WIN iff ALL asserted
  conditions hold (requireOppFaint: opp fainted; requireNoFaint: player not fainted; keepItem:
  terminal item == id — Harvest-restored berry counts as KEPT, Knock Off/Trick loss fails;
  HP ≥ keepHp), else LOSS. NO special simultaneous-KO rule — it falls out of the conjunction
  (requireNoFaint=false + requireOppFaint=true → simultaneous KO = WIN).
  Non-terminal → CONTINUE. keepItem early-fail DISABLED (Harvest makes it non-monotone;
  future opt: early-fail when no restoration path). keepHp only meaningful with requireNoFaint.
  action_filter(q, action) for banMove. Free functions on const state (set-variant addable later).
Tests (test_solver_question.cpp): 4 terminal combos under default question (both-fainted → LOSS);
both-fainted with requireNoFaint=false → WIN; player-only-fainted with requireNoFaint=false →
LOSS (requireOppFaint unmet); keepItem terminal + early-fail non-terminal; keepHp boundary N-1/N;
banMove filters exactly that slot, accepts Struggle.

## Task 5 — TransitionOracle (brute-force DFS prefix-replay)
Files: solver/transition_oracle.h/.cpp. Uses Tasks 1-3 + ai_analytic.h.
- step(state, playerAction, emit, hint, budget) → StepStats.
- Outer branch: cpp_compute_action_probabilities(state, ai_idx); fail loud Σ≠1±1e-9 or empty.
- DFS prefix replay: prefix = ordered (channel, event, occurrence, forced value, prob). Per
  iteration: reset g_catb_occ_counters; rebuild CategoryBInjection + OracleOverrides from prefix;
  copy state; cpp_run_one_turn_solver.
  - paused → Cat-A branch point; extend prefix per option (probs from oracle-owned Cat-A table;
    unmodeled event → throw).
  - ok → read AnalyticalRngLog; first logged draw beyond prefix = next Cat-B branch point (options
    + p_chosen; p_chosen==-1 → throw). No new draws → LEAF: emit {child, ∏ prefix probs × p(ai)};
    emit false → abort all.
  - After every replay: verify_exhausted() (consumed-prefix mismatch → fail loud).
- Cat-A table: SPEED_TIE .5/.5; EFFECT_SPORE_WHICH {11/30,10/30,9/30}; TRI_ATTACK 1/3;
  METRONOME/SLEEP_TALK/STARF/ACUPRESSURE uniform over options; MOODY 1/7×1/6.
  ACTION_SELECT/FORCED_SWITCH/POST_FAINT_SWITCH/ROAR_TARGET → throw (impossible in 1v1).
- Preconditions (throw): one active/side, both alive, no Quick Draw, action legal.
- Budget: per-leaf; exhaustion → stop, budget_exceeded=true (never silent partial).
- AdverseFirst: best-effort opponent-favoring order (miss first, opp crit first, min-player/
  max-opp roll first); must not change emitted multiset.
- No leaf dedup in phase 1 (raw 16-roll).
Tests (test_solver_oracle.cpp; fixtures per test_solver_projection.cpp conventions):
deterministic turn → 1 child p=1; Hypnosis 60% → 2 children .6/.4; damage roll w/ Shell Armor →
16 leaves 1/16; crit×roll → 32 leaves, crit mass = engine crit chance; Rock Blast → class masses
0.9·{.35,.35,.15,.15} + .1 miss; para 25%; speed tie both-KO → 2 children .5/.5; AI 2-action
outer product; invariants every test: Σp=1±1e-9, Natural≡AdverseFirst multiset,
turn_executions==leaves; emit-abort → aborted=true leaves==1; budget=1 → budget_exceeded;
Quick Draw active → throws; unmodeled Cat-A table lookup → throws.

## Task 6 — Player action space
Files: solver/action_space.h/.cpp. Uses cpp_enumerate_legal_actions (orchestrate.h),
cpp_find_mega_entry (turn.h), move_exec.h.
- legal_player_actions(state): wrap cpp_enumerate_legal_actions (handles PP-empty → Struggle,
  move_slot=-2/override=165); append mega variants per base move iff cpp_find_mega_entry(item)
  matches pre_species==active.species && !is_mega && !side.mega_used (mirrors liveplay/actions.py:175-185).
  AI side never megas.
Tests: 2 moves + matching stone → 4 actions; mega_used → 2; wrong stone → 2; all PP 0 → Struggle only.

## Task 7 — Random matchup generator
Files: solver/matchup_gen.h/.cpp. Data: runtime JSON load of liveplay/data/generated_learnsets.json
+ generated_abilities.json via existing nlohmann path (no codegen). Legality reference:
liveplay/battle_gen.py; stats via compute_stat (stats.h).
- MatchupGen(seed, klass, shard, of) → stream of 1v1 BattleStates (team of one/side, full HP,
  legal moves, real abilities/items). Classes: Uniform, BerryHolders (Sitrus/Custap/pinch per
  battle_gen.py GENERAL_ITEMS), SashSturdy (Focus Sash/Band, Sturdy). Blocklist Quick Draw.
- Sharding: generation stream identical regardless of shard args; shard k/of n = indices ≡ k mod n
  (generate-then-filter, never split RNG). Deterministic per (seed, klass).
Tests (test_solver_gen.cpp): same-seed reproducibility (100 states); shards 0..3/4 disjoint,
union == unsharded; validity over 500 (one active, hp==max_hp>0, moves in learnset, no Quick Draw,
oracle preconditions pass); BerryHolders 100% hold stress item.

## Task 8 — Audit harness skeleton
Files: solver/audit/audit_oracle.cpp (modes selfcheck, mc), solver/audit/solver_trace.cpp.
- selfcheck --seed --klass --n [--shard k/of n]: per matchup × legal action: Σp=1±1e-9;
  Natural≡AdverseFirst; child sanity. Collect-until-N-decided framing; reason-bitmask histogram.
- mc --samples M: enumerate oracle support (packed keys); M random-mode cpp_run_one_turn samples
  with BOTH actions pinned explicitly (do NOT trust "ai" policy sampling ==
  cpp_compute_action_probabilities; verify once, note finding). Sampled child outside support →
  HARD FAIL printed first (completeness hole = worst class). Chi-squared/5σ per-child frequency
  check. Random mode resolves Cat-A natively → cross-checks Cat-A tables too.
- solver_trace --seed --index --action [--leaf]: print state, full leaf enumeration (event path
  (event,occ,value,p) + cumulative prob per leaf), optional leaf replay with analytical log dump.
- Every failure prints seed/index/action/leaf-path for regression fixture capture; regressions
  become Catch2 tests over time.
Tests: inline selfcheck smoke over 10 matchups (fast); MC M=2000 over 3 matchups tagged [.slow].

## Task 9 — Benchmark
Files: engine/bench/bench_oracle.cpp (conventions from bench_solver_seam.cpp; EXCLUDE_FROM_ALL).
- Over G matchups per class × all legal actions: leaves, turn executions, wall time. Report
  p50/p90/p99/max per (state,action), leaves/sec, leaf-count histogram (1, ≤16, ≤512, ≤32k, >32k),
  budget-exceeded count at default 1e6. Decides whether multi-hit worst case (~(2·16)^5 ≈ 33.5M
  paths) needs phase-2 mitigation.

## Settled/provisional decisions (record via records.py at wrap-up)
- settled: DFS prefix-replay over actBranches over-enumeration (completeness by construction;
  one execution per leaf; no mechanics duplication).
- settled: Quick Draw excluded phase 1. settled: p_chosen at resolution site; Cat-A table
  oracle-owned, fail-loud, MC-verified. settled: no leaf dedup phase 1. settled: separate lib.
- provisional: PP in context (measure growth); budget 1e6; AdverseFirst best-effort; gen teams of one.

## Known issues / notes
- Stale comment ai_policy.cpp:86 (claims ExecAction has no mega field; it does) — comment-only bug.
- Confusion self-hit damage roll (move_exec_premove.cpp:174-184) appears to be 15 outcomes, not 16 —
  Task 1 must mirror actual code, not assume.
- MC harness pins actions explicitly; if "ai" policy sampling verified == distribution, simplify later.
