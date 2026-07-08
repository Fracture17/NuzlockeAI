# Migration Audit — Move to /home/Fracture/CLionProjects/NuzlockeAI

Date: 2026-07-03. Consolidates four audit passes (C++ engine, Python live-play stack,
parity infrastructure, documentation drift). This document guides the port; the old
repo is retired afterward (kept archived; NN code stays behind).

## 1. Locked scope decisions (user)

- New repo = C++ engine/solver core + retained high-level **Python live-play layer**
  (OCR/vision, mGBA input, message matching, sweep reconciliation). Live play is a
  HARD, IMMEDIATE requirement — every port decision must keep the emulator path first-class.
- "State transition system" to port = SCRIPTS/play.py + SCRIPTS/stress_test.py + debug
  tooling (replays, sweep-error dumps). Greedy search is NOT ported (replaced by the
  C++ RNG-bucketing solver, the design center of the new repo).
- **Two C++ loggers:** (1) fast/minimal RNG-decision logger for the solver hot path;
  (2) richer event logger for live-play message↔event reconciliation (perf non-critical).
- **Parity:** record golden traces from random Python games (RNG decisions identity-keyed
  + action log + per-turn state snapshots); C++ replays with forced RNG; **compare
  end-of-turn full state** (NOT event streams — user approved). Skiplist = corpus
  exclusion / per-battle quarantine, not event-pattern skipping.
- **Tests:** no bulk test porting. Golden traces (random corpus + targeted scenario
  traces harvested from existing test setups) cover existing Python-era behavior.
  **Hybrid policy for new tests:** game-semantics tests in Python (pytest driving C++
  via bridge; existing test_cpp_* suites carry over); solver + C++ internals in native
  C++ tests (Catch2/GoogleTest).
- Trace half-life accepted: after intentional C++ behavior changes, re-record goldens
  from the new C++ engine (Python traces are the bootstrap, not the forever format).

## 2. C++ engine findings (cpp/, ~18.6k lines)

### 2.1 Critical structural issues
- **Turn-loop duplication (top drift risk):** the entire ~370-line turn loop exists
  twice — `turn.cpp cpp_run_one_turn` vs `game_driver.cpp:213-625 cpp_run_one_turn_oracle`,
  plus `MEGA_TABLE`/`MEGA_TABLE_GD` (game_driver.cpp:178-191) and `gd_*` helper copies.
  FIX: delete the plain loop; the oracle loop with `overrides=nullptr` is the only loop.
- **Other duplications:** `resolve_accuracy` ×2 (move_exec_guards.cpp:222 / move_exec.cpp:235),
  `hidden_power_type` ×2, `check_type_immunity` mirror (move_exec.cpp:247),
  `decode_damage_luck` ×3 (game_driver, orchestrate, bench_driver:22-51 → move to codec),
  `GameDriver::_run` vs `cpp_run_game` action loop.
- **Fail-loud violations (bugs):**
  1. `bindings/module.cpp:636-654` — `ai_switch_info` catches runtime_error → returns None.
  2. `native_rng.h:50` — `choices()` silent fallback return; should throw.
  3. `move_exec_helpers.cpp:137-141` — catches ANY runtime_error from berry logic and
     relabels it "unported: starf_berry_oracle" (real bugs masked + swallowed by
     orchestrate.cpp:691-698 unported handler).
- **Stale bridge metadata:** module.cpp `is_stub()`→true, version "0.0.2-c1.2".
- **Zero C++ tests** (cpp/tests/ empty); parity gates + pytest suites were the only net.

### 2.2 Unported fail-loud boundaries (complete list)
core_leaf.cpp:494 RANDOM_NORMAL multi-foe (controlled mode); core_leaf.cpp:830 SPEED_TIE
(plain path); turn.cpp:185/190 pending_switch; turn.cpp:440 sub_move (plain path);
turn.cpp:613 + game_driver.cpp:597 residual_switch (accepted, INTENTIONAL_DIVERGENCES #2);
turn.cpp:633 + game_driver.cpp:615 post_faint_switch **mid-turn pause unsupported on the
oracle path too**; move_exec_helpers.cpp:140 starf relabel; residuals.cpp:289 Moody (plain);
effects.cpp:1979 status-move fallthrough. Header-documented: turn_start (effects.h:41),
eject_pack (effects.h:93), volatile/self_status STUBs (effects.h:60-61), Endure/Mat Block
(effects.cpp:1064), mega missing from enumerate_legal_actions (orchestrate.cpp:400).
Deferred mechanics: Baton Pass, U-turn/Volt Switch, phazing mid-turn, eject pack.

### 2.3 Solver-readiness gaps
- **No logging of any kind** — both loggers are greenfield.
- **BattleState NOT trivially copyable:** vectors in PokemonState (types, timed_volatiles),
  SideState (team, imprisoned_moves) + `nlohmann::json baton_pass_data_raw` embedded in
  SideState (drags json.hpp everywhere). Copy ≈ 30-60 heap allocs. FIX: fixed-capacity
  inline arrays + evict baton_pass json → memcpy-able state, slab-allocated node pools.
  **This is the dominant solver speed win.**
- `state_eq.cpp` state_equal/state_hash: solid bucket-key primitives, but hash covers
  solver-irrelevant fields (turn_number, exp_participants, prev turn_order) → need a
  projection variant. NOT comparable to Python hashes (by design).
- Exception-based pause flow (NeedsRNG/TurnPause carrying full ActionSnapshot) is fine
  for live play, wrong for the solver — solver calls the resolver layer directly with
  enumerated answers.
- Minor: PendingSwitch `std::string reason` compares (turn.cpp:181-184); RecordingPolicy
  full-state JSON per AI decision (debug-only); per-Entry TurnLuck copies.

### 2.4 RNG architecture (good news)
- All Category-A oracle events flow through 2 inline functions (`oracle_resolve[_pair]`,
  oracle.h:85-104) with 8 call sites; all random_mode draws through NativeRng's 4 methods
  (43 sites, wrappable with zero call-site edits); threshold mode is pure-function.
- FIX during move: consolidate scattered resolvers (resolve_crit damage.cpp:655,
  resolve_multi_hit move_exec_damage.cpp:180, resolve_accuracy ×2, resolve_proc_me,
  resolve_secondary/proc/flinch_det effects.cpp:505/514/523) into one `rng_resolver.h` —
  that file then IS the solver RNG-logger + trace-replay hook.
- Replay gaps: OracleOverrides answers re-fire on every occurrence (oracle.h:64-69) →
  need consumable queue semantics; Category-B thresholds are per-game scalars → need
  occurrence-keyed injection. Both localized.
- Keep: single damage formula shared by engine and AI (ai_damage.cpp:201 →
  cpp_calculate_damage with ai_scoring_view flag). Preserve this property.
- Keep `-ffp-contract=off` (parity requirement).

### 2.5 Oversized units (split during move)
cpp_calculate_damage (damage.cpp:1281, ~330 + ~460-line modifier chain),
handle_damage_loop (move_exec_damage.cpp:325, ~400), apply_secondary_effects
(post_hit.cpp:547, ~350), _apply_status_move dispatcher (effects.cpp ~1300-1980),
cpp_apply_entry_effects (effects.cpp:774), ai_scorer dist functions (227-448 lines),
both turn loops. effects.cpp (2118) is the worst file.

## 3. Python live-play stack findings

### 3.1 The seam
The ENTIRE hot-path engine dependency is one function: `run_candidate_sweep`
(simulation_runner.py:3818), reached via play.py:641 → sweep_recorder.record_and_run:117
→ engine_select.py:35. Cold path: enumerate_legal_actions (battle_policy.py:35-38).
Vision, matcher, hp_stability, state_transition, battle_input, known_values are
engine-independent and port unchanged.

### 3.2 What the sweep needs from C++ (gap list)
1. **Rich event trace — the biggest gap.** `check_log_events` (simulation_runner.py:1425)
   consumes only ~20 of 133 LogEvents: DAMAGE (source, defender_side, attacker_side,
   attacker_slot, amount), HEAL (source, side), MOVE_USE, MOVE_MISS, CRIT, HITCOUNT,
   CANT_FLINCH/PARALYSIS/SLEEP/FROZEN/INFATUATION, HIT_SELF_CONFUSION, STATUS_APPLY,
   STAT_BOOST, VOLATILE_APPLY, FAINT, EXP_GAIN, LEVEL_UP. That set + exact kwargs is
   the C++ rich-logger spec. check_log_events itself is engine-independent and ports as-is.
2. Per-hit tuple / per-slot dict Category-B override injection through GameDriver
   (cpp_bridge payloads only cover profile-level today).
3. Sweep orchestration stays in Python; swap `_make_sweep_sim`/`_run_to_decision_boundary`
   internals to drive GameDriver. `run_candidate_sweep_cpp` is a NotImplementedError stub.

### 3.3 Performance at the seam
Sweeps run once per battle turn (budget = seconds; capture loop is 25Hz between turns).
Hundreds→~1000 full-turn sims per boundary (_SWEEP_BRANCH_CAP=1000, sim_runner.py:81).
JSON codec per call ≈ 0.5-2s/boundary — viable but marginal. Mitigation: batched API
(N (action-pair, rng-config) per call against one resident state, one parse) — pattern
exists in iter_damage_configs (module.cpp:525). Benchmark before anything fancier.

### 3.4 Live-play keep/replace/retire map
KEEP: play.py, stress_test.py (strip greedy wiring), replay_sweep.py, sweep_recorder.py,
sweep_io.py, engine_select.py, candidate_tracker.py, battle_policy.py, state_transition.py,
battle_message_matcher.py, battle_messages.py, battle_constants.py, hp_stability.py,
hp_delta.py, vision/, emulator/battle_input.py, known_values.py, rng.py (vocabulary),
logger.py (interface), check_log_events + sweep orchestration from simulation_runner.py.
REPLACE: simulator.py + engine internals of simulation_runner.py (→ C++ GameDriver).
RETIRE: greedy_policy.py + src/search, cpp_bridge.py (after port; its luck-payload
serializers are the wire-format template), NN code, src/sgz, src/curriculum.

### 3.5 Live-play bugs/risks surfaced
- candidate_tracker.py:34 dedups by `hash(state)` only — collision risk; fix to __eq__.
- sweep_recorder pickles Candidates/BattleStates — won't survive the restructure;
  migrate payloads to sweep_io JSON during the move.
- Pause-boundary alignment: Cat-A pauses must fire at identical execution points in both
  engines or sweep injection misaligns silently (validated by replay_boundary + oracle suites).
- HP k-pixel formula (hp_stability) vs engine rounding must stay consistent.
- Post-port, delete Python AI-probability remnants (opponent_probs.py etc.) or they rot.

## 4. Parity infrastructure findings

### 4.1 What exists (verdict on "pinned RNG only": confirmed)
- c17h whole-game gate (SCRIPTS/c17h_game_gate.py): full BattleState == over whole games,
  per-turn localizer, 1M battles 0 divergences — but under a fully PINNED luck profile
  (always-hit/never-crit/median-damage/no-secondaries). Variance branches never compared
  Python-vs-C++ at whole-game scale.
- random_mode sweeps (36.7M games): liveness only, compares nothing against Python.
- ~35 tests/test_cpp_*.py: handwritten luck-injected edge tests + oracle pause/resume
  suites + regression corpus replay (diff_harness full-state diff).
- AI gates: exact/TVD<0.03 vs analytic oracles.

### 4.2 Golden-trace design (agreed)
Trace = JSONL per game: header (initial state via sweep_io tagged-JSON — the schema
authority, + engine git hashes); RNG decision records keyed
(turn, phase, side, slot, RNGEvent, occurrence_idx) storing RESOLVED OUTCOMES (not raw
uniforms); action log (existing schema, proven as replay bridge); per-turn state
snapshots (the comparison channel). Optional Python LogEvent stream for human
localization within a diverging turn only.
- C++ consumption: extend GameDriver — occurrence-indexed Cat-B value queues threaded
  into DamageLoopLuck/TurnLuck (fail-loud on miss/exhaustion/leftover), Cat-A per
  occurrence via existing step() protocol. Compare per-turn state JSON; report turn +
  field diff.
- Stray draws needing identity keys: speed-tie tiebreaker (core.py:311/339), doubles
  RANDOM_NORMAL target (core.py:461 — has NO RNGEvent today; needs one).
- Effort: Python Cat-B hooks Small (src/rng.py ~18 resolve_* choke points); Cat-A hooks
  Small-Medium (~10 sites or record at Simulator answer boundary); per-turn snapshots
  Small; C++ Cat-A consumption Small; C++ Cat-B occurrence-queues Medium-Large (riskiest
  piece); harness Medium.
- Corpus: large random corpus + TARGETED SCENARIO TRACES harvested from existing test
  setups (covers rare mechanics without porting assertions). Quarantine known-divergent
  battles (persistent trajectory forks): INTENTIONAL #1 Quick Draw random_mode,
  INTENTIONAL #2 Emergency-Exit residual, CPP_CORRECT #1 stale-BOUND, EXP recoil bug —
  triage every red battle against the ledgers before freezing goldens.

### 4.3 Blind spots (never whole-game-compared; decision deferred)
Moves: ACUPRESSURE, METRONOME, SLEEP_TALK, TRI_ATTACK, PSYWAVE (+ rampage moves in
doubles). Abilities: MOODY, EFFECT_SPORE, FORECAST, RKS_SYSTEM, EMERGENCY_EXIT, WIMP_OUT,
QUICK_DRAW. Items: mega stones, STARF_BERRY. Species: Castform/Silvally forms. Plus
cross-side speed-tie games (probe-rejected at generation), residual forced switches,
doubles generally (~460 gated vs 1M singles). Options when reached: trace via oracle
GameDriver path before retiring Python, or write off explicitly. User: "we'll see."

## 5. Documentation findings

### 5.1 Migration seed list
CARRY AS-IS: Mechanics.md, Moves.md, Abilities.md, AI.md (engine-independent port spec;
mark resolved inline discrepancies), POST_ARCHIVE_FIXES.md, INTENTIONAL_DIVERGENCES.md,
CPP_CORRECT_DIVERGENCES.md (become primary correctness docs post-retirement),
requirements.md record store via query tool (fix capture_interval_10fps; mark
run_one_turn_state_only superseded), TODO.md (refresh line refs), StressTest.md,
RandomBattle.md, DebugScript.md (fix Programmatic section signature).
CARRY AFTER FIXING: architecture.md (25Hz, stress policies 80/20 Random/Greedy, cpp
doubles, drop NN/sgz lines). C++Transition.md (keep C1.7h/A-stage/decision sections as
history; top-of-file Goal/Strategy describes the superseded NN-centric plan).
REGENERATE: Simulator.md + LOGGER_GUIDE.md (fix Moody table, two-turn-moves claim),
SCRIPTS/DESCRIPTIONS.md. DROP: RECORDS/ARCHITECTURE.md, ADVANCED.md, Issues.md,
records.toml/index/search.log (dead second store), NN.md, empty SCRIPTS/architecture.md
+ SCRIPTS/requirements.md, and the five *Issues.md audit files AFTER mining still-open
doubles-gated entries into TODO.md (~15/15 sampled non-doubles findings already fixed).

### 5.2 Notable contradictions (resolve during move)
- capture_interval_10fps is a REQUIREMENT-confidence record; code is 0.04s (25Hz)
  (play.py:110). Needs user ruling.
- Moody three-way: code %7/%5 (residuals.py:350-352); POST_ARCHIVE_FIXES says intended
  %7/%7; Simulator.md says 0-4. POST_ARCHIVE_FIXES is authoritative.
- LOGGER_GUIDE "two-turn moves not implemented" false (core.py:1549 _TWO_TURN_MOVES).
- RECORDS/ARCHITECTURE.md claims Tesseract OCR; actual is font_matcher pixel templates.

## 6. Recommended staging (high level; ordering rationale: do parity-critical
refactors WHERE THE REFEREE LIVES — this repo has the Python engine + 1M-battle gates)

- **Stage A (this repo):** behavior-preserving C++ structural fixes validated by
  existing gates — delete plain turn loop, consolidate resolvers into rng_resolver.h,
  dedupe helpers, fix 3 silent fallbacks + bridge metadata.
- **Stage B (this repo):** identity-keyed RNG trace recording (Python) + occurrence-
  keyed forced consumption (C++) + golden-trace harness; generate random corpus +
  targeted scenario traces; triage/quarantine; freeze goldens GREEN.
- **Stage C:** stand up new repo; move C++ + live-play Python + harness + traces +
  seed docs (per 5.1); new CMake/CLion layout; pickle→JSON recorder fix.
- **Stage D (new repo, trace-protected):** trivially-copyable BattleState + perf work +
  solver RNG logger + state_hash projection.
- **Stage E:** rich event logger (~20 events) + sweep re-point (batched GameDriver API)
  + replay_boundary validation on recorded sessions + live mGBA validation. Retire old
  repo after this.
- **Stage F:** bucketing solver POC (design per project_rng_bucketing_search memory).

Alternative (user may prefer): move first (Stage C before A/B) and refactor in the new
repo; costs re-pointing the existing gates at the new location before traces exist.

## 7. Surfaced bugs (full list)
1. module.cpp:636-654 ai_switch_info silent None fallback.
2. native_rng.h:50 choices() silent fallback.
3. move_exec_helpers.cpp:137-141 catch-and-relabel masks berry bugs.
4. module.cpp:95-98 is_stub()/version() stale.
5. candidate_tracker.py:34 hash-only dedup.
6. capture-rate contradiction: code 25Hz vs requirement record 10fps (4 conflicting claims).
7. sweep_recorder pickle fragility (breaks on restructure).
8. Known frozen Python bugs (ledgered): Emergency-Exit double-residual, stale-BOUND
   resurrection, recoil-self-KO EXP.
9. Five RECORDS/*Issues.md files present ~15 already-fixed bugs as open.
