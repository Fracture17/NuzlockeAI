# C++ Transition — Historical Record

This document is a historical record of the C++ engine port that was completed in the
old repo (PycharmProjects/NuzlockeAI). The NN-centric goal described in the original
plan has been superseded. The current plan is:

- **Stage C** — repo migration to CLionProjects/NuzlockeAI (done; this repo).
- **Stage D** — performance/refactor work on the C++ engine in the new repo.
- **Stage E** — sweep re-point: wire `run_candidate_sweep` and `enumerate_legal_actions`
  in `liveplay/engine_select.py` to the C++ engine (currently `NotImplementedError` stubs).
- A new **RNG-bucketing guaranteed-win search** (AND-OR tree over RNG equivalence buckets)
  replaces the greedy/NN approach. The NN models and `sgz/` training infrastructure were
  dropped from this repo.

## Old-repo retirement (2026-07-11)

The old repo (`/home/Fracture/PycharmProjects/NuzlockeAI`) is **retired**: frozen in
place as a read-only archive per user decision — nothing deleted, nothing to be
modified. Final sweep confirmed zero code/runtime dependencies from this repo (ROM in
`~/Downloads`, mgba-qt in `~/.local/bin`, `States/` byte-identical here, codegen reads
`liveplay/data/`), and no uncommitted work there. Carried before freezing:
`RECORDS/EXPYield.md` + `EXPYieldExtra.md` (hand-verified exp-yield source data).
Left in the archive (still readable if ever needed): old Python engine/AI issue
trackers (`AbilityIssues/AIIssues/ItemIssues/MechanicIssues/MoveIssues/Issues.md`),
`NN.md` (abandoned v1 NN), old `ARCHITECTURE.md`/`ADVANCED.md`, the 809-file
`tests/ExhaustiveTests/` Python-engine suite (18 StaticIssues regression tests noted
as port candidates in `RECORDS/StaticIssues.md`), and ~2.3 GB of v1 NN training
artifacts (`checkpoints/`, `TrainingData/`).

Path references in the historical sections below reflect the old-repo layout (`cpp/` →
now `engine/`, `src/` → now `liveplay/`); they are preserved as-is since they describe
completed work.

## Phases

### Phase 0 — Foundations (no engine porting yet)

No engine logic is ported in Phase 0. The point is to build the scaffolding that
makes Phases 1-2 safe and measurable: a way to call a (stub) C++ engine from
Python, a way to prove parity, and a single source of truth for data. Components:

- **C0.0 — pybind11/3.14 build spike. [DONE — PASSED]** Verified on 2026-06-21:
  pybind11 3.0.4 installed into `.venv`; a hello-world extension built with GCC
  15.2.1 (`-std=c++17 -shared -fPIC`, ext suffix `.cpython-314-x86_64-linux-gnu.so`)
  and imported + called successfully under Python 3.14.4. Toolchain available:
  CMake 4.3.2. Binding strategy is viable; no fallback (nanobind) needed.
- **C0.1 — Engine-selection seam.** The seam is `run_candidate_sweep(messages,
  hp_deltas, initial_candidates, action_groups) -> list[Candidate]` (the pure,
  stateless, one-call-per-sweep function in `src/simulation_runner.py`) — NOT the
  stateful `Simulator`, which stays a Phase 1 internal reimplemented behind the
  sweep. A new `src/engine_select.py` dispatches to the Python impl or the C++
  extension via a `NUZLOCKE_ENGINE` flag/env var (default `python`); the Python
  impl is imported unrenamed so the Python path is untouched. Call sites
  (`src/cli.py`, `src/sweep_recorder.py`) import the dispatcher.
  **[DONE]** `src/engine_select.py` created (`get_engine`/`set_engine`, ValueError on
  bad name); `src/sweep_recorder.py` rerouted. `cli.py` needed no change — it goes
  through `Simulator`, not `run_candidate_sweep`. Test: `tests/test_engine_select.py`
  (9/9), incl. a real Charizard-vs-Bulbasaur transparency sweep. Regression:
  `test_simulation_runner` + `test_sweep_recorder` = 216 pass / 1 skip (unchanged).
- **C0.2 — C++ build skeleton. [DONE]** CMake + pybind11 producing importable
  `nuzlocke_engine_cpp`, installed into `.venv` via `SCRIPTS/build_cpp.py`. No-op
  stub exposing `run_candidate_sweep_cpp` (raises NotImplementedError), `is_stub()`,
  `version()`. Test: `tests/test_cpp_build.py` (3/3 pass). Files under `cpp/`
  (`CMakeLists.txt`, `bindings/module.cpp`, `src/`, `generated/`, `tests/`);
  `cpp/build/` gitignored.
- **C0.3 — Data codegen pipeline. [DONE]** `SCRIPTS/gen_cpp_data.py` (`generate(out_dir)`
  core + `--check` staleness flag) reads the in-process `src/data/` dicts and emits 7
  deterministic headers into `cpp/generated/`: `species_data.h` (1,220), `move_data.h`
  (813), `item_data.h` (332), `nature_data.h` (25), `type_chart.h` (19x19),
  `status.h`, `growth_rate.h`. Test: `tests/test_cpp_data_codegen.py` (9/9:
  determinism, staleness pass/fail, coverage, spot-value). Headers committed; `--check`
  fails CI on drift.
- **C0.4 — Differential harness. [DONE]** `tests/diff_harness.py` — `SweepInput`,
  `run_both` (forces python then cpp via the seam, restores prior engine in
  finally), `diff_results` (authoritative verdict = full `BattleState ==`, plus
  `rng_sequence`/`unknown_actions`/count; reuses partial `diff_battle_states` only
  for readable location), `run_and_diff`, `DiffReport`. Tolerates the cpp stub's
  NotImplementedError as `cpp_not_implemented`. Test: `tests/test_diff_harness.py`
  (10/10). Note: `sweep_recorder.diff_battle_states` is incomplete (misses side
  conditions/weather/turn counters); full `==` covers them, flagged explicitly.
- **C0.5 — Oracle ingestion + capture-hook. [DONE]** `src/sweep_io.py` — lossless
  type-tagged JSON codec (`to_jsonable`/`from_jsonable`, `dump/load_sweep_input`,
  `dump/load_candidates`) covering all engine dataclasses + IntEnum/IntFlag/tuple/
  frozenset/int-keyed dict; fail-loud on unknown types. Capture-hook in
  `src/engine_select.py` dumps inputs to `NUZLOCKE_CAPTURE_DIR` when
  `NUZLOCKE_CAPTURE` is set (call-time env check, lazy import, true no-op otherwise).
  Classifier `tests/oracle_subset.py` (`is_engine_touching`,
  `ENGINE_TOUCHING/EXCLUDING_PATTERNS`). Codec gotcha recorded: enum check MUST
  precede the int check (IntEnum is an int subclass). Tests: `tests/test_sweep_io.py`,
  `tests/test_oracle_ingest.py`.
- **C0.6 — Regression corpus + replay. [DONE]** `tests/regression_corpus.py`
  (`CORPUS_DIR`, `add_to_corpus`, `iter_corpus`; corpus only grows, JSON fixtures
  with date/reason metadata). Seeded with
  `tests/fixtures/regression/fixture_charizard_vs_bulbasaur_seed.json`. Replay test
  `tests/test_regression_corpus.py` runs every fixture through the harness (python
  vs python now; becomes python vs cpp once the engine is ported).

Phase 0 exit criteria — ALL MET (55/55 Phase 0 tests pass): stub C++ engine builds
and imports into `.venv`; the harness runs sweep inputs through both engines (cpp
stub tolerated); codegen produces stable headers with a staleness check; the corpus
replay runs as part of the suite. **Phase 0 COMPLETE.** Next: Phase 1 (core engine
port, bottom-up) — mind the Phase 1 data-representation risks recorded below.

### Phase 1 progress (live)
Execution: one Code agent per component, serial, each committed after independent
verification (build + probe parity + Phase-0 regression). **Use Opus coding agents
for difficult sections** (mutating ports, core orchestration).
- **C1.0 DONE** (commit 8fb5359) — probe submodule + nlohmann/json vendored + harness.
- **C1.1 DONE** (0242dde) — codegen emits full inline stat_changes arrays.
- **C1.2 DONE** (29a104a) — C++ structs + typed codec + compute_stat + lookup.
- **C1.3 DONE** (7d7d746) — calculate_damage exact parity; roll 0..15 ladder + 162
  harvested fixtures. Temporary env-gated damage capture hook in damage.py.
- **C1.4 PARTIAL** (2d2b77b) — effects.py mutating units. PORTED to exact parity:
  `_apply_entry_hazards`, `_apply_switch_out_reset`, `_sec_self_stat_changes`, and in
  `_apply_status_move`: first-use protect, hazard moves, field moves, simple recovery,
  status-infliction+stat-change interaction subset. STUBBED fail-loud (`throw
  "unported: ..."`): `_apply_volatile_move`, `_apply_self_status_move`, complex
  interaction moves, terrain seeds, HealBell/HealPulse/Wish/StrengthSap/Swallow/Roost,
  Synchronize, status berries, and the `apply_entry_effects`/`apply_post_hit_effects`
  probe seams. **C1.4 REMAINING (next session, Opus):** all of `post_hit.py`
  (`_apply_post_hit_effects` tree: items, on-hit abilities, contact, standard
  secondaries) + the stubbed effects branches. Fixtures harvested 5,778->776; effects
  capture hook still in effects.py. NOTE: harvested fixtures do NOT record the luck
  profile, so luck-dependent paths (e.g. consecutive Protect) can't be replayed from
  fixtures — covered by handwritten luck-injected tests instead.
- **C1.4 COMPLETION DONE** (9e594bb) — finished the mutating port: `check_status_berry`
  (effects_internal.h) + full `post_hit.py` tree (post_hit.cpp), probe + capture hook +
  reduce_posthit_fixtures.py + test_cpp_posthit.py. Regenerated 2 stale Trick Room fixtures.
- **C1.5 DONE** (2ebf312) — `_apply_residuals` ported (residuals.cpp): all 10 field-wide
  bands + late per-slot pass + timed-volatile ticks + Emergency Exit + Wish + Future Sight;
  tib gating and bound release-turn no-tick honored. FAIL-LOUD STUBS (`throw "unported:"`):
  exp_flush (residual opponent KO — EXP distribution deferred to a follow-on C1.5b), Moody,
  random_mode, Starf berry. Luck captured as a FLAT scalar dict per side (not the sweep_io
  dataclass codec); C++ decodes proc/secondary/flinch thresholds into the C1.4 EffectsLuck.
  75 fixtures + handwritten luck-injected edge tests. test_cpp_residuals.py: 96 pass / 10
  skip (all exp_flush stub). C++ parity regression (effects/posthit/damage/residuals/
  diff_harness/corpus): 1173 pass. **Open:** C1.5b must port EXP-on-residual-KO so those
  paths verify instead of skip (residual_exp_flush_points is a `requirement`).
- **C1.6 DONE** (562992b) — in-C++ dedup hash/equality (state_eq.{h,cpp}) + rng resolver
  audit. C++ `state_equal` matches Python's full dataclass `__eq__` field set (broader than
  diagnostic-only `diff_battle_states`); `state_hash` is self-consistent (eq ⇒ equal hash),
  NOT a reproduction of Python hash values (per `dedup_by_state_not_hash`). Sets hashed
  order-independently; weight_kg_reduced exact float ==; baton_pass_data raw-JSON compare.
  Temporary probes state_hash/state_eq/dedup_count + test_cpp_dedup_hash.py (1178 pass / 21
  skip total). rng audit: crit/secondary/proc/damage_roll/flinch/binding_duration reached +
  covered; psywave_roll + ancient_power_boost confirmed NOT reached (deferred to C1.7);
  remaining resolve_* surface documented in state_eq.h. **Bug found:**
  `resolve_ancient_power_boost` (rng.py:493) is DEAD CODE — no call site in src/ (Ancient
  Power omni-boost handled elsewhere or unimplemented; confirm during C1.7).
- **C1.7a DONE** (82f2e01) — EXP distribution ported (`cpp/src/exp.{h,cpp}` +
  `species_exp_lookup.{h,cpp}`); residual `unported: exp_flush` throw replaced by
  `cpp_flush_opponent_faint_exp`. The 10 skipped exp_flush residual fixtures now PASS
  (test_cpp_residuals 106 pass/0 skip; new test_cpp_exp.py 8 cases). Growth-rate enum
  inlined, fail-loud on unknown. Did NOT inherit the pre-existing recoil-self-KO EXP bug.
  1199 pass / 11 skip total.
- **C1.7b DONE** (08be1d7) — remaining C1.4 effects/post_hit fail-loud stubs ported to
  byte-identical parity: Cheek Pouch heal (effects + post_hit), Weakness Policy (new
  `cpp_check_type_immunity` in damage.{h,cpp}), Pluck/Bug Bite berry steal, Gulp Missile
  (apply_form_change helper), Relic Song, `_apply_status_move` 44-id no-op allow-list.
  KEPT fail-loud as genuinely uncontrolled oracle: Acupressure, Effect Spore, Tri Attack
  (Tri Attack's secondary gate returns early → throw is an unreachable defensive guard).
  New test_cpp_c17b.py. 1300 pass / 9 skip total (`-k cpp`).
- **C1.7c DONE** (Unit A 78eb374, Unit B 134bf88) — core leaf helpers in new
  `cpp/src/core_leaf.{h,cpp}`. Unit A: `cpp_compute_variable_bp`,
  `cpp_compute_fixed_damage` (Python round-half-to-even Psywave), `cpp_resolve_targets`,
  `cpp_resolve_psywave_roll`. Unit B: `cpp_effective_speed`, `cpp_has_trick_room`,
  `cpp_triage_priority_bump`, `cpp_check_priority_item` (mutating Custap consume),
  `cpp_action_sort_key`, `cpp_build_queue`; promoted `effective_weather` to a shared
  `eff_internal` decl (de-dup damage.cpp/effects.cpp statics, Air Lock/Cloud Nine kept).
  Fail-loud (excluded from parity): RANDOM_NORMAL random.choice, Psywave random_mode,
  SPEED_TIE oracle, random_mode tiebreaker. Tests: test_cpp_c17c_leaf.py (38p/2s),
  test_cpp_c17c_turnorder.py (22p/2s). 1360 pass / 13 skip total (`-k cpp`).
  **Bug found (separate, spawned task):** generated `species_data.h::weight_kg` is
  unpopulated (0.0 for all species); SCRIPTS/gen_cpp_data.py never reads SPECIES_WEIGHTS
  into it. Unit A embedded SPECIES_WEIGHTS locally in core_leaf.cpp as a parity-safe
  workaround — to be removed once the codegen is fixed.

### Bug surfaced (pre-existing, unrelated to the port)
`tests/test_exp_centralized_faint.py::TestOpponentRecoilSelfKO::
test_opponent_recoil_self_ko_awards_exp` fails (recoil self-KO awards 0 EXP, expected
180). Reproduces at HEAD with all working-tree changes stashed; lives in Python exp
logic (`src/engine/exp.py`/`effects.py`, modified before this work). Not touched by the
C++ transition.

### Phase 1 — Core engine (Tier 1), bottom-up
Port in dependency order, each unit gated by the harness against Python:
`state/` structs -> `damage` -> `effects` -> `post_hit` -> `residuals` -> `core`,
plus the `rng` injection interface mirrored exactly. Candidate dedup hashing lives
*inside* C++, so Python hash semantics need not be replicated. Watch-item:
damage-calc integer rounding must match Python bit-for-bit.

#### Phase 1 staged components (user-approved plan)
Each stage is self-contained, tests-first, executed in a separate session with
per-stage approval. The parity mechanism is a **temporary per-unit function-probe**
(`nuzlocke_engine_cpp.probe` submodule): one C++ function exposed at a time, fed
`sweep_io`-tagged JSON inputs, diffed against its Python twin (full `BattleState ==`
for mutating units, int-equality for `calculate_damage`). Removed at end of Phase 1.

- **C1.0** Probe harness + codec boundary; `echo_state` round-trip smoke test (no logic).
- **C1.1** Extend `gen_cpp_data.py` to emit full variable-length `stat_changes`
  (inline max-N array: N=5 secondary, N=3 self); regenerate headers.
- **C1.2** C++ state structs (`PokemonState`->`SideState`->`BattleState`->`Action`->
  `Candidate`) + C++ JSON codec + `compute_stat` + binary-search `lookup`. Structs
  restore fields as-is (bypass `__post_init__`); `sweep_io` is the schema authority.
- **C1.3** `calculate_damage` (pure). Bit-for-bit rounding gate — probe sweeps
  `roll_index` 0..15, crit, type, STAB, weather, screens, Mold Breaker, AI view.
- **C1.4** `effects` + `post_hit` (mutating; consume stat_changes from C1.1).
- **C1.5** `residuals` / end-of-turn (mutating).
- **C1.6** `rng` resolve_* completeness audit + gap-fill (deterministic paths only;
  `random_mode` excluded from parity). Defines the in-C++ dedup hash.
- **C1.7** `core` orchestration + `enumerate_legal_actions`; **Bridge single-turn replay**
  (Option A): a thin, disposable adapter lets the real corpus replay drive C++ `core` per
  turn so the whole-sweep `diff_harness` gates the end of Phase 1 (enumeration loop stays
  Python until Phase 2). Then **remove probes + probe harness + sub-unit capture hook**.

##### C1.7 decomposition (user-approved 2026-06-23)
Scope correction: "core orchestration" spans `src/simulator.py` (1332L turn state-machine) +
`src/engine/core.py` (2846L move-execution lib) + `src/engine/actions.py` (170L
`enumerate_legal_actions`). Executed as serial sub-stages, autonomous (stop only to escalate):
- **C1.7a** — EXP port (`src/engine/exp.py` → `cpp/src/exp.{h,cpp}`); replaces the C1.5
  `unported: exp_flush` throw. The 10 skipped exp_flush residual fixtures must then PASS.
  Opus. NOTE: the pre-existing recoil-self-KO EXP bug lives in this surface (don't inherit).
- **C1.7b** — remaining C1.4 effects/post_hit fail-loud stubs (Acupressure, Effect Spore/
  Tri-Attack status selection, Gulp Missile/Relic Song form change, Weakness Policy, Pluck/
  Bug Bite berry steal, Cheek Pouch, `_apply_entry_effects`). Opus.
- **C1.7c** — core leaf helpers (`_compute_variable_bp`, `_compute_fixed_damage`/Psywave,
  `_resolve_targets`, turn-order: `_action_sort_key`/`_build_queue`/`_check_priority_item`).
  Probe parity. Opus.
- **C1.7d** — move-execution core (`execute_action` tree: damage/fixed/status/multi-hit
  loop, pre-move checks, `_pdg_*` guards, faint+on-KO, switch, recharge). Opus.
  **Decomposed (Plan agent, 2026-06-23) into 5 serial bottom-up Code units:**
  - U1 `move_exec_helpers.{h,cpp}` — `_apply_damage`, `_apply_rocky_helmet`,
    `_apply_gulp_missile_projectile`, `_apply_on_ko_effects`, `_notify_faint_soul_heart`,
    `_apply_unburden`, `_reset_stockpile`, `_bump_rollout_counter`, `_consume_pp`+Leppa.
    Starf-Berry `oracle(STARF_BERRY_STAT)` stays fail-loud.
  - U2 `move_exec_premove.{h,cpp}` — `_pre_move_checks` (sleep/freeze/paralysis/confusion/
    attract via injectable luck; confusion self-hit uses U1 `_apply_damage`).
  - U3 `move_exec_guards.{h,cpp}` — `_pdg_*` chain + accuracy modifiers + `_handle_pre_damage_
    checks` (two-turn/Future Sight/Imprison/Fake Out/etc.). Defines the flat `ExecCtx`/`GuardCtx`
    scalar struct (ctx→scalars, per C1.4 posthit precedent) reused by U4/U5.
  - U4 `move_exec_damage.{h,cpp}` — multi-hit loop, `_apply_defender_faint_effects`,
    `_handle_damage_action` (incl. spread/redirect), `_handle_fixed_damage_action`.
  - U5 `move_exec.{h,cpp}` — `_execute_action`/`_execute_action_body` dispatcher + status path
    + switch/recharge + Dancer + the centralized EXP flush (only at the two `_execute_action`
    returns via `cpp_flush_opponent_faint_exp`, NEVER in the hit loop — req `move_exp_flush_after_recoil`).
  - **USER DECISION (2026-06-23): port DOUBLES branches to full parity now** (Lightning Rod/
    Storm Drain redirect, Follow Me/Rage Powder, spread penalty) — NOT fail-loud. (Training
    sweeps are singles-only per sgz/train.py, but the user wants the C++ engine doubles-complete.)
  - Fail-loud (excluded from parity): uncontrolled oracle only (Starf Berry; the status-selection
    oracles Tri Attack/Effect Spore/Acupressure already fail-loud in `cpp_apply_status_move`).
    Focus Band is deterministic (rng.py resolve_proc) → port; Dancer is deterministic → port.
  - **PROGRESS:** U1 DONE (c0c5acb), U2 DONE (b5595d2), U3 DONE (b9d0ef0),
    **U4 DONE (move_exec_damage.{h,cpp})** — `cpp_handle_damage_action`/
    `cpp_handle_fixed_damage_action` return `{state, pending_switches}`; file-local
    `handle_damage_loop`/`apply_defender_faint_effects`/`with_active_slot_swapped`;
    re-implemented resolve_multi_hit/resolve_hit_count + resist-berry table; `DamageLoopLuck`.
    Doubles spread/redirect (Follow Me/Rage Powder) ported. Fail-loud: random_mode reaching
    multi_hit/hit_count/crit/damage_roll resolvers; `unported: rampage_duration` (rampage
    first-use) and `unported: dancer_trigger` (Dancer) — **both deferred to U5 to wire up**.
    **Fix:** `cpp_apply_damage`'s trailing arg is an active-slot POSITION (indexes
    `active_indices[slot]`), NOT a team index — all 3 call sites pass `0` (== Python
    `_get_active`=active_indices[0]); double-index bug when slot-swap active. Verify
    placeholder `VE_RAMPAGING_ID=6` against real VolatileEffect in U5. Tests:
    test_cpp_c17d_unit4.py 33p; regression 1415p/13s.
  - **U4.5 DONE (prerequisite for U5's switch path)** — `cpp_apply_entry_effects`
    (`effects.{h,cpp}`). `_apply_entry_effects` was listed in C1.7b's scope but had
    slipped (left as a fail-loud stub probe); ported now to full parity since U5's
    `_handle_switch_action` calls it. Fully deterministic (no RNG → no `unported:`):
    Intimidate (Contrary/Guard Dog/immunities/Substitute/Adrenaline Orb/Rattled/Mold
    Breaker), weather+terrain setters, Trace, Imposter, Intrepid Sword/Dauntless Shield,
    Download, Screen Cleaner, terrain seeds, Soul Dew, Forecast/Castform, RKS/Silvally,
    Pastel Veil, Truant re-loaf, Neutralizing-Gas sync. Reused existing eff_internal
    helpers (change_stat_stage w/ caused_by_opponent+mold_breaker, on_stat_dropped,
    apply_form_change, is_grounded, cpp_effective_stat); ported update_castform +
    sync_neutralizing_gas file-local. Replaced the STUBBED probe in module.cpp with a
    real differential probe (TEMPORARY, remove at C1.7i). Removed obsolete
    test_cpp_effects.py::test_unported_entry_effects_raises. tests/test_cpp_entry_effects.py
    36p; regression 1447p/13s.
  - **U5 DONE (C1.7d COMPLETE)** — `cpp/src/move_exec.{h,cpp}`: `cpp_execute_action`
    (public) + file-local `_execute_action_body` dispatcher, `_handle_status_action`,
    `_handle_switch_action` (calls cpp_apply_entry_effects), `_handle_recharge_action`,
    `cpp_apply_dancer_trigger`. Signature: `cpp_execute_action(BattleState&, int side_idx,
    const ExecAction&, DamageLoopLuck& luck_atk, DamageLoopLuck& luck_def,
    vector<PendingSwitch>&, ExecCtx&, int source_slot)`. EXP flush ONLY at the two
    cpp_execute_action returns (req move_exp_flush_after_recoil). Rampage wired in
    move_exec_damage.cpp: **VE_RAMPAGING_ID corrected 6->12**, deterministic
    `resolve_rampage_duration` (roll>=0.5?3:2) threaded via LuckProfile.rampage_duration_roll.
    Dancer wired in BOTH damaging-dance (move_exec_damage.cpp) and status-dance paths.
    Exported `cpp_apply_protect_contact_penalty` wrapper from move_exec_guards (impl was
    anon-namespace). unit5 26p/2s; regression 1483p/13s.
  - **Bugs found & fixed during U5 (latent, never hit by U1-U4):** (1) Dancer ability id
    hardcoded 209; real `Ability.DANCER==216` -> Dancer copy never fired. (2) codec.cpp read
    `timed_volatiles` as bare list but to_jsonable wraps the outer tuple as `__tuple__`
    (now accepts both); any state with non-empty timed_volatiles failed to deserialize.
    (3) codec.cpp read `battle_last_move`/`mirror_move_last_move` via `.get<int32_t>()` but a
    non-None Move serializes as `__enum__` (now `decode_enum_or_int`).
  - **U5 NEW fail-loud branches (OUTSTANDING before C1.7g 0-unported gate):**
    `unported: baton_pass_data` (status-path Baton Pass -- C++ JSON writer always nulls
    baton_pass_data, can't round-trip; needs codec support); rampage volatile-set logic is
    ported but **parity-UNTESTED** because every rampage move targets RANDOM_NORMAL whose
    `random.choice` resolver is still fail-loud (C1.7c) -- unblocks once RANDOM_NORMAL ported.
    `unported: random_mode` resolvers as before.
- **C1.7d-gaps DONE** — finished the deterministic (Category C) fail-loud gaps +
  RANDOM_NORMAL-singles (user-confirmed scope: "Cat C + RANDOM_NORMAL").
  - **RANDOM_NORMAL singles** (`core_leaf.cpp` `cpp_resolve_targets`): singles has ≤1 foe so
    `random.choice` is deterministic (the sole foe); ported. Doubles (>1 foe) stays fail-loud
    (`unported: RANDOM_NORMAL random.choice (multi-foe)`). Unblocked the 2 rampage parity tests.
  - **Fling power table** (`move_exec_damage.cpp`): ported the item→BP switch (13 items + 10 BP
    default; no item → move fails). +3 tests in `test_cpp_c17d_unit4.py`.
  - **baton_pass_data** (`move_exec.cpp` status path): codec already round-trips it as raw JSON;
    C++ now builds the nested tuple in `to_jsonable` shape (stat_stages, allowlisted volatiles
    [mask 1282055], timed_volatiles, crit_stage, sub_hp) + queues the u-turn switch. +2 tests in U5.
  - **status-move fallthrough audit** (`effects.cpp:1841`): audited all 201 STATUS moves via
    `SCRIPTS/audit_status_move_fallthrough.py`. No fallthrough gaps (44-id no-op allow-list is
    complete). Audit surfaced a REAL latent parity bug: Block/Mean Look applied `TRAPPED` but
    not the `TRAPPED_SOURCE_ID` companion timed-volatile. Fixed (`VE_TRAPPED_SOURCE_ID=33`);
    regenerated 6 stale Mean Look/Block harvested fixtures (predated the Python feature).
    +2 regression tests in `test_cpp_effects.py`. All 1564 cpp tests green, 12 intended skips.
  - **Oracle plan of record (user-confirmed):** Category A uncontrolled oracles (SPEED_TIE,
    STARF_BERRY_STAT, Acupressure, Effect Spore, Tri Attack, Moody, RANDOM_NORMAL-doubles,
    `random_mode`) stay C++-fail-loud by design; **Python resolves them at the C1.7f bridge.**
- **C1.7e DONE** — one-turn state-machine slice (`_advance_queue`/`_begin_turn`/`_finish_turn`/
  `_check_fainted` → C++ `cpp_run_one_turn`, in new `cpp/src/turn.{h,cpp}`). Composes the ported
  leaves (`cpp_build_queue`/`cpp_execute_action`/`cpp_apply_residuals`) + 5 new begin/EOT helpers
  in `effects.cpp`. SINGLES static order only (`_select_next_action` not ported — see record
  `run_one_turn_static_order`). Fail-loud at every pause/decision boundary via `throw
  std::runtime_error("unported: <reason>")`: `doubles`, `mega`, `primal`, `turn_start`,
  `sub_move`, `acupressure`, `pending_switch`, `residual_switch`, `post_faint_switch`. Probe
  binding `probe.run_one_turn`; tests `tests/test_cpp_c17e_run_one_turn.py` (9 parity pass,
  8 boundary skip).
- **C1.7e-gaps DONE** — fixed the three C1.7d-layer gaps surfaced during C1.7e (records
  `eject_pack_fail_loud`, `turn_ctx_per_turn_shared`, `residual_ko_exp_clear`):
  (1) Eject Pack now throws `unported: eject_pack` in `change_stat_stage` when the holder has a
  bench (Python-owned mid-turn switch); no-bench case stays inert, matching Python.
  (2) Protect now propagates across movers: `apply_protect_move` writes Protect/Wide/Quick-Guard
  state into `ExecCtx`, `cpp_apply_status_move` threads `ctx`, and `cpp_run_one_turn` builds ONE
  `ExecCtx` per turn (hoisted out of the queue loop) so the first mover's Protect is visible to the
  second mover's guard chain — mirroring Python's single per-turn TurnContext.
  (3) Residual-KO exp-participant clear (`exp.py:156`) is replayed by the driver: `cpp_apply_residuals`
  consumes a const copy of the sets, so the driver clears fainted opponent slots before committing.
  New tests: `test_cross_mover_protect_parity`, `test_residual_ko_no_bench_exp_parity` (parity),
  `test_eject_pack_boundary` (skip). cpp suite 1573 pass / 20 skip.
- **C1.7f DONE** — the bridge: disposable `cpp_bridge` engine wired into `engine_select`
  (`_VALID_ENGINES`/dispatch). New `src/cpp_bridge.py` houses the probe serializers
  (`damage_luck_payload`/`turn_luck_payload`/`action_payload`, promoted from the C1.7e test),
  the per-turn driver `run_one_turn_cpp` (raises `UnportedTurn` on `unported:`, re-raises
  anything else), and `BridgeSimulator(Simulator)` which intercepts the WHOLE deterministic
  slice at `_begin_turn` (the entry to begin→advance→finish→check→finalize). On a clean
  singles turn (both sides one action, SINGLES, no mega) it builds the payload from
  `self._get_profile(side)` — exactly what `_begin_turn` uses — calls `cpp.probe.run_one_turn`,
  and commits the C++ post-turn state via `_commit_cpp_turn` (mirrors `_finalize_turn`).
  Non-interceptable/`unported:` turns delegate to `super()._begin_turn()` (Python). Verify
  mode (default ON) re-runs the same turn on a vanilla Python Simulator and raises on any
  `py!=cpp` full-BattleState mismatch — independent of strict mode. `BRIDGE_STRICT` makes
  `unported:`/non-interceptable/C++ failure FAIL LOUDLY. Engine selection reuses the Python
  `run_candidate_sweep` with `use_bridge_simulator()` monkeypatching `runner.Simulator`
  (runner instantiates `Simulator()` directly; the Python path is untouched when unused).
  Tests `tests/test_cpp_bridge.py` (12): serializers, driver parity, `unported` classify,
  bridge clean-turn parity, unported→Python fallback, strict-raise, engine dispatch, and a
  full sweep `cpp_bridge`==`python`. cpp suite 1592 pass / 20 skip. Left for C1.7g: corpus
  harvest + whole-sweep gate run under `BRIDGE_STRICT`. Opus.
- **C1.7g** — corpus harvest (curriculum `generate_battle`, ~2-5k battles) + final
  whole-sweep gate green (0 divergence, 0 `unported:`). **Phase 1 EXIT.** Sonnet.
- **C1.7i DONE** — scaffolding removal (irreversible). `probe.run_one_turn` was PROMOTED to a
  top-level `nuzlocke_engine_cpp.run_one_turn` binding (the bridge depends on it); the rest of
  the `probe` submodule, `probe_harness.py`, and all harvested-fixture/sub-unit probe tests were
  deleted. The 4 sub-unit capture hooks (DAMAGE/EFFECTS/POSTHIT/RESIDUAL) + `_sides_to_battle_state`
  were removed from the engine; the 4 `*_calls/` fixture dirs and the dead `reduce_*`/audit scripts
  are gone. The C1.7e luck-injected tests (`test_cpp_c17e_run_one_turn.py`) + `test_cpp_bridge.py`
  re-point to the promoted binding and stay green. The `NUZLOCKE_CAPTURE` corpus hook is KEPT.
  Gate (non-strict, verify ON) GREEN: 2000/2000, 0 divergences. Opus.
- **C1.7h DEFERRED TO PHASE 2** — wiring real `run_candidate_sweep_cpp` = porting the
  enumeration loop to C++; per the locked "enumeration stays Python until Phase 2".

##### C1.7 user decisions (2026-06-23)
- **Phase-1 exit = bridge gate** (C1.7g) + scaffolding removal (C1.7i); full C++ enumeration
  (run_candidate_sweep_cpp) opens Phase 2, NOT part of C1.7.
- **Luck coverage:** keep the handwritten luck-injected edge tests and re-point them to drive
  the C++ core via the bridge with injected luck (the harvested corpus only records observed
  luck, so rare RNG branches would otherwise lose coverage after probe removal).
- **Pacing:** autonomous through C1.7a-g,i; stop only to escalate genuine decisions/failures.

#### Phase 1 resolved decisions (user-approved)
- **D1 — variable-length stat_changes:** inline fixed max-N array (secondary N=5,
  self N=3) on the POD move table, not a side-table. Measured max lengths: secondary
  `{1:56, 5:2}`, self `{1:8, 2:3, 3:1}`.
- **D2 — sparse/negative ids:** binary-search (`std::lower_bound`) on the
  sorted-by-id `SPECIES/MOVE/ITEM` tables; fail loud on miss. Direct indexing is
  impossible (Species max ~7.74M, Item negative e.g. `VILE_VIAL=-2`).
- **D3 — struct order:** leaf-up dataclass dependency order; `sweep_io` codec is the
  field/schema authority.
- **D4 — stat recompute:** C++ structs store all fields as-is for round-trip parity
  (match the codec, which bypasses `__post_init__`); `compute_stat` ported separately
  for any in-engine recompute path.
- **Phase 1/2 boundary:** Option A — C1.7 bridges single-turn corpus replay through
  C++ `core` so Phase 1 closes against the real corpus gate, not just probes.
- **Probe inputs:** add a temporary sub-unit capture hook (C0.5-style, one level down)
  to harvest real `calculate_damage`/residual/effect call args from a corpus run;
  augmented with handwritten edge cases; removed with the probes.
- **C++ probe codec:** may vendor a header-only JSON library (e.g. nlohmann/json) for
  the throwaway probe boundary.

#### Phase 1 risks / open items
- Float determinism: `compute_stat` + damage use `math.floor` on float products; C++
  must reproduce Python IEEE-754 double + floor exactly. The `roll_index` 0..15 ladder
  test is the tripwire (nonlinear — not a linear rescale).
- `random_mode` paths are non-deterministic and excluded from probe parity; confirm no
  corpus/oracle input depends on `random_mode` (sweep uses threshold profiles).
- Probes only catch divergence on inputs fed to them; the whole-sweep gate (C1.7) is
  the real backstop for composition bugs.
- `_helpers.py` ported lazily (only what each component reaches); may need its own
  component first if it carries heavy shared mutable state.

### Phase 2 — Sweep loop (Tier 2)
Port `simulation_runner` enumeration + dedup + HP/order filtering into C++ so an
entire sweep is one pybind11 call. This is where the bulk of the training speedup
lands. Differential-tested at the whole-sweep level against recorded + curriculum
battles.

#### C1.7h — pure-C++ whole-game runner (DONE)
Self-contained C++ runner that plays arbitrary full singles battles end-to-end
(multi-turn rollouts on `cpp_run_one_turn`) for NN-training throughput. Hot path only.
- **Stage 1** `cpp_apply_switch` (post-faint path only) + `cpp_battle_over` +
  `cpp_compute_winner`. Baton Pass throws loudly (deferred).
- **Stage 2** `cpp_enumerate_legal_actions` mirroring `actions.py` branch order; mega
  omitted; Struggle = `move_slot=-2, move_override=165`. Policy interface (Random/Scripted;
  NN seam documented only).
- **Stage 3** `cpp_run_game` loop + `run_game(json)` pybind binding. Returns
  `{final_state, winner, turn_count, action_log, status}`. `debug_snapshots` adds per-turn
  `turn_states` for the localizer.
- **Stage 4** constrained clean-battle/team generator (`SCRIPTS/c17h_clean_battle_gen.py`):
  excludes the still-unported mechanics so every generated battle is hot-path-only.
- **Stage 5** whole-game parity gate (`SCRIPTS/c17h_game_gate.py`): run `cpp_run_game`
  under a PINNED LuckProfile, replay its `action_log` through the Python Simulator, assert
  full `BattleState ==`. Per-turn localizer under `--per-turn`; 5 negative controls prove the
  gate has teeth. **GREEN: 500/500, 0 divergences, 0 skips.**
- **Bug found by the gate:** Python `_action_sort_key` used `slot==-1` so Struggle (-2)
  inherited `move_ids[-2]`'s priority; cpp correctly used `slot<0`. Fixed Python to `slot<0`
  (full suite still green); C++ was already correct.
- **Deferred to C1.7h.2:** Baton Pass, U-turn/Volt-Switch, eject_pack, Roar/Whirlwind phazing.

#### C1.7h.2 — mid-turn forced-switch mechanics (DONE)
Ported the four deferred switch flows into the C++ runner, each landed incrementally with the
parity gate driven back to GREEN before the next. Autonomous (Plan+Code agents), escalate-only.
- **Shared resolver** `cpp_resolve_pending_switches` (turn.cpp) runs after each mover's
  `cpp_execute_action`, mirroring Python `_handle_pending_switches`: resolves every mid-turn
  switch so the other mover still acts on the post-switch state.
- **action_log schema** dispatches on the `phase` string (no version field): added
  `{"phase":"forced_switch","p0":<idx|null>,"p1":<idx|null>}` and
  `{"phase":"phaze","side":<idx>,"target":<idx>}`. Every entry carries the concrete chosen bench
  idx; the gate's Python replay applies it verbatim (never re-draws) — this pins the phaze
  (ROAR_TARGET) oracle. Mid-turn switch entries do NOT advance the per-turn localizer's `turn_idx`.
- **S1** U-turn/Volt Switch/Flip Turn (cause `u_turn`, Policy-selected replacement).
- **S2** Eject Button/Red Card (post_hit causes) + Eject Pack (ExecCtx.eject_pack_sides threaded
  out of `change_stat_stage`, drained in `cpp_run_one_turn` as cause `eject_button`).
- **S3** Roar/Whirlwind/Dragon Tail/Circle Throw (cause `roar`). Suction Cups immunity checked at
  RESOLUTION not trigger (both engines append the cause unconditionally) + Mold Breaker override.
- **S4** Baton Pass state transfer in `cpp_apply_switch`: copies stat_stages, OR volatiles,
  append timed_volatiles, crit_stage, sub_hp to the incoming mon BEFORE the turns_in_battle reset.
- **Gate GREEN: 1000/1000, 0 divergences, 0 skips (UNRESTRICTED population).** Full suite 9184 pass.
- **Remaining EXCLUDED_MOVES** (genuinely unported): acupressure, metronome/sleep_talk (sub_move),
  tri_attack (oracle status), psywave (random_mode). Plus doubles/mega and the oracle-RNG set.
- **Note (for NN realism, not parity):** the phaze/forced-switch replacement is chosen by the
  runner's Policy, not a uniform ROAR_TARGET RNG draw. Parity holds because the gate replays the
  logged idx; a real random phaze-target distribution is a Policy concern to wire in later.

#### C1.7h.3 — 1M-battle scale validation + parity fixes (DONE)
Ran the game gate at 1,000,000 battles (10 parallel processes, master seeds 11–20 × 100k each;
distinct integer seeds → uncorrelated MT streams, empirically 0 battle-population overlap). The
initial 1M run was RED with 32 divergences — real parity bugs invisible at 1k–10k scale. Built
`SCRIPTS/c17h_repro.py` (single-battle reproduction by master seed + index) and extended
`diff_battle_states` to cover EVERY `PokemonState`/`SideState` field (was blind to most). Five bugs,
all with the Python engine authoritative:
- **Weight precision** — C++ stored species `weight_kg` as float32 (`42.4f` = 42.400001525878906);
  Python uses float64. Flipped Low Kick/Heavy Slam/Heat Crash BP tiers. Fix: `weight_kg`→`double`
  end-to-end (`gen_cpp_data.py` drops the `f` suffix + struct type; `species_data.h` regenerated).
- **Grounding** — `effects.cpp:is_grounded` ignored MAGNET_RISE/TELEKINESIS/VE_GROUNDED (a correct
  copy already existed in `damage.cpp`). Cascaded into terrain status-block, Grassy-Terrain heal,
  and hazard residuals. Fix: mirror `damage.cpp:is_grounded`.
- **Struggle ordering** — `core_leaf.cpp` sort key guarded `slot == -1`; Struggle uses slot -2, so
  `move_id_at(-2)`→move 0 (STATUS) let a PRANKSTER Struggler gain phantom +1 priority. Fix: `slot < 0`.
- **Heavy Slam floordiv** — `std::floor(a/b)` diverges from CPython `a // b` at IEEE boundaries
  (`18.0 // 3.6 == 4`, not 5). Fix: `py_float_floordiv` reproducing CPython `float.__floordiv__`.
- **diff_battle_states blindness** — now iterates all dataclass fields, so triage isn't blind.
- **Gate GREEN: 1,000,000/1,000,000, 0 divergences, 0 skips** across seeds 11–20.

#### Native-RNG oracle ladder (A-stages) — pure-C++ random_mode resolution
The Phase-1 bridge left every Category-A uncontrolled oracle fail-loud (Python resolved them at
the bridge). For the Phase-2 pure-C++ whole-game runner (NN/search) to run without Python, those
oracles resolve natively via `NativeRng` (`cpp/src/native_rng.h`, header-only mt19937_64;
behavioural — NOT bitwise — parity with CPython). One RNG per game, seeded from the game seed.
- **Stage A1 DONE** — damage/premove/residual `random_mode` resolvers (accuracy, crit, multi-hit,
  binding/rampage duration, psywave, secondary/proc, wake/defrost/paralysis/confusion/attract).
  Wired `luck.rng` through the DamageLoopLuck path in `run_game`. Tests
  `tests/test_random_mode_resolvers.py` (13) + `SCRIPTS/random_mode_smoke_gate.py`.
- **Stage A2 DONE** — turn-luck oracles: speed-tie tiebreaker + Quick Claw. `TurnLuck` gains an
  `rng` field (`run_game` wires it when the side is turn-luck random_mode). `tiebreaker()` draws
  `rng->random()` per side (mirrors `core.py:_build_queue._tiebreaker`, so the sort-by-tie key
  breaks the tie natively); `resolve_quick_claw_det()` draws `rng->random() < 0.2` (rng.py:481).
  `cpp_build_queue` skips the SPEED_TIE throw when a tying entry is random_mode, but **keeps the
  throw in controlled mode** so the Phase-1 bridge still delegates injected ties to Python.
  Tests `tests/test_cpp_speed_tie_random_mode.py` (5, incl. the non-random bridge-contract
  regression). Validation: full suite 10370p/19s; c17h game gate green; 1-hour 10-worker
  `SCRIPTS/random_mode_parallel_sweep.py` = **36,765,085 battles, 0 failures**.
  - **Quick Draw micro-stage DONE** — `resolve_quick_draw()` resolves ONCE per `Entry` (stored
    on the struct, not drawn inside the O(n²) sort key). **Controlled mode UNCHANGED** and matches
    Python: fires iff `secondary_threshold <= 30.0` (GOOD-only). **random_mode is an INTENTIONAL
    C++-only divergence**: fires `rng->random() < 0.3` (30%), whereas Python never fires Quick Draw
    in random_mode (its `_action_sort_key` has no random_mode branch and `secondary_threshold`
    stays 50.0). The random battle creator (`c17h_clean_battle_gen.py` `EXCLUDED_ABILITIES`) prunes
    Quick Draw so the parity corpus never surfaces the divergence. Recorded in
    `RECORDS/INTENTIONAL_DIVERGENCES.md #1`. Tests `tests/test_cpp_quick_draw_random_mode.py` (5,
    incl. the ~30% fire-rate + controlled GOOD/high-threshold regressions).
- **Stage A3 DONE** — the remaining Category-A status/stat oracles now resolve natively in
  `random_mode`, mirroring each Python `else random.*` fallback; **controlled mode stays
  fail-loud** so the Phase-1 bridge still delegates the pick to Python:
  - Effect Spore (`post_hit.cpp`): `rng.randint(1,30)` → SLEEP(≤11)/PARALYSIS(≤21)/POISON.
  - Tri Attack (`post_hit.cpp`): `rng.choice([BURN, FREEZE, PARALYSIS])`.
  - Acupressure (`effects.cpp`, via `apply_volatile_move` gaining an `EffectsLuck` param):
    `rng.randint(0,6)` → +2 to that stat. `turn.cpp` pre-guard keys off DAMAGE luck.
  - Moody (`residuals.cpp`): boost `rng.randint(0,6)` +2, drop `(boost+1)%5` (bumped if equal) -1.
  - Starf Berry (`effects.cpp check_berry`, gaining a `NativeRng*` param threaded through 7
    callers incl. `band_poison`/`band_burn`): `rng.randint(0,4)` → +2 to that stat.
  - Also fixed a latent parity bug (masked by corpus exclusion): the shared secondary-effect entry
    guard in `post_hit.cpp` used field-decomposition instead of Python's `secondary is not None`;
    corrected to `sec.chance != 0` (record `secondary_is_chance_nonzero`) so Tri Attack's
    all-empty-fields chance-20 secondary is not skipped.
  - Tests `tests/test_cpp_category_a_oracles_random_mode.py` (9). Corpus generators
    (`SCRIPTS/random_mode_smoke_gate.py`) un-exclude the 5 oracles so the sweep exercises them.
    Validation: c17h game gate green (guard change no-regress); 6-min 10-worker
    `random_mode_parallel_sweep.py` = **3,539,607 battles, 0 failures**.

- **Issue 1 (called moves) DONE** — Metronome/Sleep Talk sub-move selection now resolves natively
  in `random_mode`; **controlled mode stays fail-loud** (`"unported: sub_move"`) so the bridge
  delegates to Python. Python `_phase_await_sub_move` is oracle-only (no `else random.*` branch), so
  the correct native semantics is a **uniform** `NativeRng::choice` over the callable options.
  - `move_exec.cpp` gains hand-written `METRONOME_EXCLUDED[]`/`SLEEP_TALK_EXCLUDED[]` int arrays
    (mirroring `src/data/moves.py`) plus `metronome_options()` / `sleep_talk_options(const&)`.
  - `turn.cpp` replaces the fail-loud throw with the native branch: build options → empty→fail
    (`last_move_failed`, no PP) → `choice` → `sub_action{move_slot=orig, move_override=chosen}`
    (PP from the caller's slot) → Sleep Talk clears SLEEP before / restores after execute →
    normal per-actor ctx path → eject_pack drain → resolve pending switches.
  - Tests `tests/test_cpp_metronome_sleeptalk_random_mode.py` (10). Corpus generator un-excludes
    METRONOME/SLEEP_TALK (`_EXCLUDED_MOVES` now empty; added `_CALLED_MOVES`).
    Validation: c17h game gate green; 6-min 10-worker sweep = **3,541,246 battles, 0 failures**.

- **Issue 2 (turn_start form changes) DONE** — `cpp_apply_turn_start_effects` (effects.cpp) no longer
  fails loud; it ports core.py `_apply_turn_start_effects` **deterministically** (no RNG, so identical
  in controlled/random mode): (a) RKS System / Silvally set their type from the held Memory item
  (default NORMAL); (b) Castform+Forecast changes form to match **raw** `s.weather` (NOT air-lock
  effective weather — parity-critical), via the existing on-entry helpers `memory_type()`,
  `forecast_form()`, `update_castform()` (which delegates to `apply_form_change`). Removed the stale
  `"turn_start": 31` boundary from `tests/fixtures/c17g_corpus/boundary_breakdown.json`.
  - Tests `tests/test_cpp_turn_start_form.py` (10). Validation: c17h game gate green;
    full suite 10404 passed; 6-min 10-worker sweep = **3,689,308 battles, 0 failures**.

- **Issue 3 (Baton Pass) — VERIFIED ALREADY DONE (no code change)** — Baton Pass transfer was fully
  ported back in C1.7h.2 Stage 4, on BOTH sides: the move-execution side builds `baton_pass_data`
  (move_exec.cpp ~559, mirroring core.py:1887) and `cpp_apply_switch` applies it to the incoming mon
  (orchestrate.cpp ~184, mirroring effects.py:533) — stat_stages(copy), allowlisted volatiles(OR),
  timed_volatiles(append), crit_stage, sub_hp; then clears the data, before the turns_in_battle reset.
  The throws in that block are malformed-JSON guards, NOT a fail-loud stub. A stale header comment
  claiming "Baton Pass transfer is deferred" was corrected. Parity test
  `tests/test_cpp_c17h_switch.py::test_apply_switch_baton_pass_transfers_state` passes (C++/Python
  equality). Record `baton_pass_transfer` already present. My earlier "remaining work" list wrongly
  flagged this (it was built from the stale comment, not the code). Regression sweep (comment-only
  change) = **3,690,198 battles, 0 failures**.

- **Issue 4 (residual_switch) — CLOSED as INTENTIONALLY UNPORTED (user decision 2026-07-02)** —
  While tracing the residual forced-switch path I found a real bug in the AUTHORITATIVE Python
  engine: when an end-of-turn residual (burn/poison/toxic/weather/Leech Seed/…) drops an Emergency
  Exit / Wimp Out holder to ≤50%, `_finish_turn` (simulator.py:791) re-runs in full on resume and
  **double-applies every residual for the turn** (independently verified: burn tick 20 → 40 HP lost;
  `UPKEEP_START` logged twice; one `SWITCH_OUT`). Presented the user Option A (replicate the
  double-application in C++ via a residual loop) vs Option B (fix Python to apply residuals once).
  **User chose neither: leave BOTH engines as-is and document the discrepancy.** So: Python bug is
  frozen (not fixed), C++ keeps its fail-loud `unported: residual_switch` throw as an ACCEPTED
  boundary (not a Category-A gap), and `EMERGENCY_EXIT`/`WIMP_OUT` stay pruned from every parity
  corpus so the divergence never appears in a comparison. Documented in
  `RECORDS/INTENTIONAL_DIVERGENCES.md #2`; pointer comments added at the C++ throw (turn.cpp:448),
  the Python `_finish_turn` docstring, and both corpus-exclusion lists; record
  `residual_switch_unported` (requirement) added. **No code behavior change** — docs/comments only.

- **Issue 5 (doubles/mega/primal) — Stages 1+2 DONE: mega + primal reversion for SINGLES.** A prior
  user decision (2026-06-23, above) requires the C++ engine doubles-complete; Issue 5 decomposes into
  mega (singles), primal (singles), then the doubles driver. Stages 1+2 (mega + primal) were done
  together since they share the item→form lookup and interleave in Python's turn order. `cpp_run_one_turn`
  (turn.cpp): removed the `unported: mega` throw and the `unported: primal` throw-loop; after
  `cpp_apply_turn_start_effects` it now runs primal auto-reversion (Blue/Red Orb holders, no flag) then
  the mega pre-queue block (gated by `mega_pX`, speed-sorted descending unless Trick Room), mirroring
  simulator.py:543-598. Added `MEGA_TABLE` (46-row static array mirroring `src/data/mega.py`, item→{mega
  species, mega ability, pre species}). No `MEGA_EVOLVE` log emitted — the parity gate is state-based
  (compares full BattleState), so only state mutations matter. Blue/Red Orb un-excluded from both parity
  corpora (`c17h_clean_battle_gen.py`, `random_mode_smoke_gate.py`) so primal rides the whole-game gate;
  mega stones stay excluded (whole-game runner hardcodes mega=False → mega covered by targeted single-turn
  parity tests instead). Tests: `tests/test_cpp_mega_primal_singles.py` (8 C++-vs-Python single-turn parity
  tests, all green). Gates: `c17h_game_gate` **1500 battles, 0 divergences**; random_mode smoke **400, 0
  failures**. Record `mega_primal_singles_ported` added. User approved full-autonomous through the doubles
  stages (build doubles corpus, native-resolve RANDOM_NORMAL, stop only on unresolvable divergence).

- **Issue 5 Stage 3 DONE: dynamic per-pick action selection (singles-preserving).** `cpp_run_one_turn`
  (turn.cpp) no longer iterates a statically-sorted `cpp_build_queue`; it now builds a pending-entries
  list once via `cpp_build_pending_entries` (resolves tiebreaker / priority-item / Quick Draw once,
  consumes Custap) then loops `cpp_select_next_action`, which recomputes each entry's sort key against
  **current** state per pick and erases the winner — mirroring Python `_build_pending_entries` +
  `_select_next_action` (core.py). `Entry` moved from the core_leaf.cpp anon namespace to core_leaf.h.
  In singles (<=2 entries) the dynamic order equals the old static order; this is prep for doubles where
  mid-turn speed changes reorder later movers. Record `dynamic_action_reselect` added. Gate
  `c17h_game_gate` **1500 battles, 0 divergences** (self-verified, seed 20260630). **Remaining: Stages
  4-6 (doubles targeting / multi-slot execution / mega in doubles + doubles corpus generator).**
- **Issue 5 Stage 4 DONE: doubles multi-slot turn driver.** `cpp_run_one_turn` (turn.cpp) now accepts
  `std::vector<ExecAction>` per side (was scalar); `ExecAction` gained a `source_slot` field threaded
  through `to_action_c`. The doubles guard was removed; recharge-forcing iterates all per-slot actions;
  the per-mover loop retrieves each action by matching `source_slot`, sets `active_team_idx` from
  `side.active_indices[source_slot]`, and passes `source_slot` into `cpp_execute_action` (which sets
  `ctx.attacker_slot` internally). `run_one_turn` binding decodes each side's action as a single dict
  (singles back-compat) OR a JSON list (doubles). 5 C++-vs-Python doubles parity tests added
  (`tests/test_cpp_doubles_run_one_turn.py`): four independent moves, spread move, status target_slot,
  mid-turn faint, slot-0 mega — all full-state equality.
- **Issue 5 Stage 5 DONE: doubles whole-game orchestration + native RANDOM_NORMAL.** `orchestrate.cpp`
  game loop now loops over each side's active slots, skips fainted slots, enumerates per-slot legal
  actions, filters slot>0 switch candidates that conflict with an already-claimed bench target
  (joint switch legality enforced in C++ only — safe because the gate replays C++'s chosen actions
  through Python verbatim), stamps `source_slot`, and passes `std::vector<ExecAction>` per side to
  `cpp_run_one_turn`. Action-log `p0`/`p1` are now ALWAYS JSON arrays (even singles, 1-element) with a
  `source_slot` field. `cpp_resolve_targets` gained `(bool random_mode, NativeRng*)`: multi-foe
  RANDOM_NORMAL throws `unported: ...` in controlled mode (naturally pruned by the pinned-luck gate,
  Quick-Draw precedent) but resolves natively via `rng->choice(foe_slots)` in random_mode — purely
  additive for standalone C++ search. The `unported: SPEED_TIE oracle` throw was narrowed to fire only
  for **cross-side MOVE-vs-MOVE** ties (same-side and switch ties fall through to stable sort); verified
  safe because gate replay uses `oracle=None` so Python stable-sorts all ties identically, and
  `cpp_build_queue` is dead code. `c17h_game_gate.py` replay handles list-shape `p0`/`p1`. Records
  `speed_tie_throw_scope`, `doubles_game_perslot_select`, `random_normal_native` added. 4 doubles-game
  tests added (`tests/test_cpp_doubles_run_game.py`): completes, action_log replay parity, RANDOM_NORMAL
  random_mode completes, RANDOM_NORMAL controlled throws. Full suite 42 passed / 6 skipped; gate
  `c17h_game_gate` **2000 battles, 0 divergences, 0 skipped** (self-verified, seed 20260630).
  **Remaining: Stage 6 (doubles parity gate + doubles corpus generator).**

- **Issue 5 Stage 6 DONE: doubles parity gate + doubles corpus generator.** `c17h_clean_battle_gen.py`
  gained `make_doubles_battle(rng)` (player/opp size randint(2,6), `SideState active_indices=[0,1]
  format=DOUBLES`, `BattleState format=DOUBLES`) and a `doubles` param threaded through
  `clean_battle_gen`/`is_clean_battle`; the doubles clean corpus additionally excludes RANDOM_NORMAL
  moves (THRASH/PETAL_DANCE/OUTRAGE/UPROAR/RAGING_FURY) since they fail-loud in controlled mode with
  >=2 live foes (STRUGGLE caught by the trajectory probe). `c17h_game_gate.py` got a `doubles` param on
  `run_gate` and a `--format {singles,doubles}` CLI flag; `_find_diverging_turn` now handles list-shape
  `p0`/`p1` (per-slot arrays). One C++ fix in `turn.cpp`: the post-residual `exp_participants` clearing
  loop dropped a slot's participant set when `active_indices` had a duplicate (e.g. `[0,0]` after a
  voluntary switch) or a fainted-slot repeat, double-clearing; guarded to clear only the FIRST fainted
  occurrence of each `team_idx`, mirroring Python's no-faint-based clearing at turn-end commit. This
  killed the ~13% doubles EXP divergence (`exp` off-by-one on a participant + top-level
  `exp_participants` set mismatch surfacing as "full mismatch"). New smoke suite
  `tests/test_cpp_doubles_game_gate.py` (generator sanity, clean-gen completes, population gate
  60 battles 0 div/0 err/0 skip, 5 parametrized verify_battle seeds). Two singles-gate tests fixed for
  the Stage-5 array-shape change (`log[0]["p0"]` → `log[0]["p0"][0]`). Records `doubles_clean_corpus`,
  `doubles_exp_participants_dedup` added. Suites: singles gate **41 passed**; doubles suites (game_gate
  + run_game + run_one_turn) **17 passed**. Doubles gate self-verified **GREEN 200×2 seeds (999,
  12345), 0 divergences**; singles gate **GREEN 500 battles, 0 divergences**.

- **Oracle pause/resume — Stage 0+1 DONE: infra + GameDriver + Effect Spore.** Supersedes the old
  "Oracle plan of record" above (line 337): now that the parity gate is retired and we're C++-only, the
  C++ engine resolves Category-A oracle events itself (for enumerated/bucketed search), instead of
  deferring to Python at the bridge. Design: `cpp/src/oracle.h` defines `RngEventC` (int values ==
  Python `RNGEvent` auto() 1–31), `OracleOverrides {optional<SpeedTieOrder> speed_tie; unordered_map<int,
  OracleAnswer> answers}`, `NeedsRNG` (carries event + options), and `oracle_resolve(ov, ev, options)`
  which returns the override's `i0` or throws `NeedsRNG`. `ExecCtx` gained `const OracleOverrides*
  overrides`. Resolution rule: override set → use it (reused every fire, map is READ-ONLY on lookup);
  unset + Category A → pause; unset + Category B → still threshold-controlled (never pauses).
  `cpp/src/game_driver.{h,cpp}`: `GameDriver` is a resumable turn loop mirroring `cpp_run_game`;
  `cpp_run_one_turn_oracle` snapshots `{state, ctx, exp_participants, pending, turn_start_active, luck}`
  BEFORE each action, catches `NeedsRNG`, restores the snapshot, and throws `TurnPause`. `step()` runs to
  `NeedsRNG`/DONE returning `{"status":"pending","event","options","state"}` or `{"status":"done"|
  "max_turns","winner","state","action_log"}`; `step({"i0":...})` injects the answer into the override
  map and resumes from the snapshot with `resume_snap` non-null, which SKIPS `_begin_turn` so movers that
  already ran are not re-executed (verified no Custap double-consume / no Quick-Claw re-draw). First
  wired event: `EFFECT_SPORE_WHICH` in `post_hit.cpp` (random_mode branch unchanged; controlled branch
  now calls `oracle_resolve`). pybind: `py::class_<GameDriver>` with two `step` overloads. Tests-first:
  `tests/test_cpp_oracle_pause_resume.py` **8 passed** (pause request shape, override honored per status,
  override reused, pause-resume == override final-state equivalence, Custap-no-double-consume,
  Category-B-no-pause). Regression: **373 passed, 5 failed** — the 5 (`test_cpp_c17h_run_game.py` ×4,
  `test_cpp_c17h_clean_gen.py` ×1) are PRE-EXISTING Stage-5 array-shape test bugs, confirmed identical
  with the oracle diff stashed out; unrelated to this work.
- **Oracle pause/resume — Stages 2–8 DONE: all singles Category-A events wired.** Each stage keeps the
  same dual-path shape: `random_mode` draws natively; the GameDriver oracle path resolves via override
  or `NeedsRNG` pause; the plain `run_game`/bridge path (`turn.cpp`, `overrides==null`) stays fail-loud
  `unported: <reason>` so the c17g boundary allow-list is unchanged. Stage 2 `TRI_ATTACK_STATUS`, Stage 3
  `ACUPRESSURE_STAT` + `STARF_BERRY_STAT` (post_hit.cpp / move_exec_helpers.cpp), Stage 4 `SPEED_TIE`
  (dedicated `OracleOverrides.speed_tie` ordering channel; resume parses `{"order":[[side,slot],...]}`),
  Stage 5 `ROAR_TARGET` (turn.cpp phaze; `cpp_resolve_pending_switches` gained an `overrides` param),
  Stage 7 `MOODY_STATS` (two-pick: `oracle_resolve_pair` returns `{i0,i1}`, boost=i0%7 drop=i1%5;
  residual pause snapshots pre-residual state with EMPTY pending so resume re-runs residuals once),
  Stage 8 `METRONOME_MOVE`/`SLEEP_TALK_MOVE` (answer = chosen move id; out-of-options answer fails the
  sub-move; `ASSIST` in singles fails, no pause). Constructor override keys: `tri_attack_status`,
  `acupressure_stat`, `starf_berry_stat`, `speed_tie`, `roar_target`, `moody_stats` (`[boost,drop]`),
  `metronome_move`, `sleep_talk_move`. Tests: `test_cpp_oracle_{speed_tie,roar_target,moody,sub_move}.py`
  (+ earlier stage suites). Regression steady at the same 5 pre-existing failures; 10655 passed.
  **Stage 6 (`RANDOM_NORMAL` target) DEFERRED** (user decision, record `random_normal_oracle_deferred`):
  it is a raw `random.choice` over foe slots, doubles-only, with NO Python `RNGEvent`, so it does not fit
  the oracle taxonomy — it stays fail-loud in controlled doubles, to be revisited in a doubles-oracle
  phase. **Stage 9:** the `oracle_resolution_at_bridge` requirement record is LEFT INTACT — it describes
  the plain-bridge fail-loud contract, which every stage preserves; the GameDriver oracle layer is purely
  additive, so nothing to retire.

### Phase 3 — Wire into training; both engines stay live
*(Superseded — NN/sgz dropped. Carried as historical record only.)*
Flip the engine selection at the `simulator` seam so `nn/` and `sgz/` adapters
drive the C++ engine. Python engine remains selectable behind the flag. Validate
that the labeling loop produces identical labels for identical inputs under both
engines before C++ becomes the default.

### Phase 4 — Profile, then conditional Option 3
*(Superseded — NN/sgz dropped. Carried as historical record only.)*
Profile the labeling/MCTS loop now that the engine is fast. Only if the Python
tree-walk is proven to be the new bottleneck, port `search/` to C++ — which
requires exporting each model to TorchScript and running it via libtorch. This is
the single invasive coupling step, so it is deferred and evidence-gated. Otherwise
stop at Phase 3.

## File placement

C++ lives **in this repo**, not a separate project. Reasons:
- The data codegen reads Python and emits C++ — trivial in one repo, awkward across
  repos (version skew, submodules).
- The differential harness imports both the Python engine and the compiled C++
  extension in-process from the same `.venv`.
- Parity tests and the regression corpus sit alongside existing tests; versions
  stay in lockstep. A separate project only pays off if the engine must be reused
  elsewhere, which conflicts with the minimize-work/invasiveness goal.

Proposed layout (same repo):
- `cpp/` — C++ source root (now `engine/` in this repo)
  - `cpp/CMakeLists.txt`
  - `cpp/src/` — state, damage, effects, post_hit, residuals, core, rng, sweep
  - `cpp/generated/` — codegen output headers (from Python `data/`)
  - `cpp/bindings/` — pybind11 module (compiles to an importable extension, e.g.
    `nuzlocke_engine_cpp`, installed into `.venv`)
  - `cpp/tests/` — optional C++-side unit tests
- Codegen script in `SCRIPTS/` (per project convention), with an entry in
  `SCRIPTS/DESCRIPTIONS.md`.
- Differential harness + regression corpus under `tests/`; the permanent
  regression corpus lives in `tests/fixtures/`.

## Phase 0 resolved decisions (user-approved)

- **Seam = `run_candidate_sweep`** (not `Simulator`). `Simulator` is a Phase 1
  internal behind the sweep.
- **Build risk handled by a C0.0 spike first** — prove pybind11 builds/imports on
  Python 3.14 before any other Phase 0 work; fall back to nanobind if it fails.
- **Corpus + captured oracle inputs serialized as JSON** (a stable, reviewable
  schema with explicit (de)serializers for `Candidate`/`BattleState`), not pickle.
- **Oracle ingestion via a capture-hook on the seam** — dump real sweep inputs when
  a capture env flag is set; run the engine-touching subset once to harvest.
- **Codegen reads the in-process Python `src/data/` dicts** (single source of
  truth), not the upstream `generated_*.json`.

## Tracked risks / open items

- Determinism: damage rounding, RNG event ordering, stat recalculation must match
  Python exactly — the harness catches drift.
- Single source of truth: data never hand-edited in C++; always regenerated.
- pybind11 must build cleanly against the Python 3.14 `.venv`.
- Regression corpus lives in `tests/fixtures/`.
- Option 3's C++<->PyTorch coupling (libtorch + per-model TorchScript export) is the
  main fragility; only taken on profiling evidence.

### Phase 1 data-representation risks (surfaced by C0.3 codegen)
- **Variable-length `SecondaryEffect.stat_changes`** — tuple of `(stat_idx, delta[,
  self_flag])` triples; ~20 unique multi-change patterns. Current headers encode only
  the first entry + count. Phase 1 must choose a representation (side-table or inline
  max-N array) for moves with >1 stat change.
- **`MoveData.self_stat_changes`** — same variable-length shape, applied to the user
  after damage, and NOT suppressed by Sheer Force (unlike `secondary`). Needs handling
  separate from `SecondaryEffect`.
- **Sparse/large `Species` enum values** (max ~7.74M for an Arceus variant) and
  **negative `Item` values** (e.g. `VILE_VIAL = -2`) — direct-index arrays are not
  viable; binary-search (D2) is the chosen solution.
