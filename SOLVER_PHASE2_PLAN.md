# Solver Port — Phase 2 Plan (roll aggregation + bsolver + analytic re-derivation)

Context: phase 1 (oracle seam + audit harness, SOLVER_PHASE1_PLAN.md) is DONE and committed.
This phase: (a) per-hit damage-roll aggregation inside the oracle, (b) the REAL bsolver —
exact boolean certifier core plus pessimal/coarse cheap tiers (user decision: pulled forward
from phase 3; the tiers are fast and easy, and they accelerate all later verification), and
(c) the ANALYTIC tier-0 certifier, re-derived on the real engine via the audit loop
(port/docs/ANALYTIC.md, BSOLVER.md, AUDIT.md). Deferred to phase 3: segSkip segment queries,
B2 exit summaries, psolver, 6v6 chain.

## Fixed decisions (user requirements)
- Bsolver scope: exact AND-OR core + pessimal/coarse modes + their audits. NO segment
  queries, NO B2 exit summaries this phase.
- Analytic rules are prototype-specific and MUST be RE-DERIVED here via the audit loop
  (measure, don't assume) — skeleton + tooling first, then lemma waves driven by audit
  failures and reason-bitmask histograms. Never transliterate prototype lemma rules.
  Each lemma wave is PROPOSED TO THE USER for approval before implementation.
- Multi-hit mitigation: per-hit damage-roll AGGREGATION inside the oracle — collapse the 16
  rolls per hit into distinct-damage buckets. Followed by a fresh full audit pass.
- Fail-loud hardening (approved): expand_catb_options' unknown-event fallback (which GUESSES
  distribution shapes, transition_oracle.cpp:363-385) becomes a throw naming the event.
- Analytic tier is EXCEPTED from "solvers never touch game logic": it may use two read-only
  engine queries — damage tables (distinct roll damages per move/crit/context) and
  HP-threshold sets. Bsolver sees ONLY the oracle. (Prior user approval; mechanics frozen.)
- Verdict semantics: WIN and LOSS are conclusive; UNKNOWN/INDETERMINATE is pure ROUTING —
  never an error, never a silent fallback. Degradation to UNKNOWN allowed; flips never.
  False LOSS is the worst failure class (silently prunes winning plans): audits print those
  first and verify BOTH directions.
- Verification pipeline (user decision): run analytic AND pessimal on everything. If both
  say LOSS, that's confirmed (pessimal LOSS conclusive by subset-support). Pessimal WIN is
  NEVER evidence (a true LOSS may pessimal-report as WIN), so every other decided combination
  goes to the full exact bsolver. Analytic-WIN + pessimal-LOSS = soundness failure (false WIN).
- Exit gate (approved): zero soundness failures over ≥2000 decided analytic verdicts
  (3 classes × ≥3 seeds, sharded), all regression fixtures green; coverage reported, not gated.
- Fail loud everywhere. Prototype numbers (~10% uniform decided, ~31% of true wins, ~100µs
  analytic; ~1.5ms pessimal, 3-9% false positives) are CALIBRATION ONLY.

## Execution rules
- One coding agent at a time; tasks sequential and self-contained.
- Tests written BEFORE implementation for every task; run before and after.
- Zero regressions in the existing native suite. New Catch2 tests in engine/tests/ —
  the glob is configure-time: re-run cmake after adding test files.
- New tools are EXCLUDE_FROM_ALL executables in engine/CMakeLists.txt linking
  nuzlocke_solver + nuzlocke_core, with NUZLOCKE_REPO_ROOT define and shard/of support
  (generation stream identical across shards; solve indices ≡ k mod n).

## Module layout (additions)
engine/src/solver/: bsolver.h/.cpp; engine_queries.h/.cpp (replaces the two
declared-but-throwing stubs in oracle_types.h); analytic/analytic.h/.cpp.
engine/src/solver/audit/: bcheck.cpp, ccheck.cpp, audit_analytic.cpp, analytic_trace.cpp
(exes). Modified: damage.cpp/.h, logger.h, transition_oracle.h/.cpp, audit/audit_core.h/.cpp,
engine/CMakeLists.txt. Tests: test_solver_aggregation.cpp, test_solver_bsolver.cpp,
test_solver_engine_queries.cpp, test_solver_analytic.cpp (+ regression fixtures over time).

## Task 1 — Damage-roll aggregation inside the oracle (+ fail-loud hardening + fresh audit + bench)
Files: damage.cpp/.h, logger.h, transition_oracle.h/.cpp, audit/audit_core.h/.cpp,
engine/tests/test_solver_aggregation.cpp.
Rationale: DAMAGE_ROLL is the only 16-way Cat-B event and it compounds per hit
(5-hit worst case ≈ (2·16)^5 ≈ 33.5M paths; 5/199 bench calls blew the 1M budget at 3–4.6s).
Many rolls yield identical damage; merging them BEFORE recursion cuts turn executions
multiplicatively. Lands first: every later solver and audit cycle gets cheaper.
- Mechanism: annotate the DAMAGE_ROLL log entry with the per-roll FINAL damage vector,
  computed at the resolution site with the live context.
  - damage.cpp: factor the post-roll modifier chain (roll multiply, STAB, pinch,
    effectiveness, Tinted Lens/Neuroforce/Filter, auras, defender halvers, Life Orb,
    Expert Belt, Multiscale/Shadow Shield/Ice Scales/Fluffy, burn, screens, Analytic,
    Friend Guard, max(1,·)) into a helper taking (pre_roll_damage, roll_int, ctx).
    The normal return uses it once; when the analytical log is active, also compute all 16
    and annotate the just-logged entry. Nothing after the roll reads roll_int except through
    damage — assert this invariant in a comment at the helper.
  - logger.h: AnalyticalRngEntry gains int32_t dmg_by_roll[16] + uint8_t has_dmg_by_roll
    (stays POD; keep the static_assert). Add an annotate-last-entry API that fail-louds if
    the last entry is not DAMAGE_ROLL. Zero cost when the log sink is null.
  - Caller-side modifiers after cpp_calculate_damage (Parental Bond ×0.25, Metronome item,
    Minimize doubling, OHKO override) are deterministic functions of the return value:
    equal returns ⇒ equal final damage, so bucketing on the return stays EXACT (it may only
    under-merge, never mis-merge).
  - transition_oracle.cpp expand_catb_options(DAMAGE_ROLL): when Config.aggregate_damage_rolls
    (new flag, default ON) and annotation present: group rolls 0..15 by identical
    dmg_by_roll value; one branch per bucket: value = lowest roll in bucket (deterministic
    representative), prob = count/16. Annotation missing with aggregation ON → throw.
  - Soundness (document in code): prefix replay is deterministic up to the draw, so the
    state at the draw is branch-invariant; equal final damage at the same draw context ⇒
    identical entire subtree (roll reaches the state only through damage). Merging whole
    subtrees pre-recursion is therefore exact — Σp=1 preserved; children that were already
    distinct are unchanged; only identical-child duplicates merge.
  - Scope: main 16-way site only. CONFUSION_SELF_HIT (separate 15-way site) and PSYWAVE
    (101-way) are NOT aggregated — neither compounds multiplicatively. No clamp-aware
    bucketing (overkill/sash rolls stay distinct-damage; children may still coincide —
    acceptable under-merge, documented future option).
  - AdverseFirst: sort buckets ascending by representative damage (keeps phase-1
    best-effort semantics); multiset (post-merge) unchanged between hints.
  - HARD RULE: random-mode RNG behavior byte-identical; annotation only under active log.
- Fail-loud hardening: unknown-Cat-B-event fallback → runtime_error naming the event.
- audit_core: add selfcheck reason bit AggregationMismatch — run step() aggregation-ON vs
  OFF per (matchup, action), compare child distributions as PackedKey→Σprob maps (≤1e-9);
  OFF-run budget exceeded ⇒ skip (counted), not fail.
Tests (before impl): single-hit vs Shell Armor holder → children = distinct damages,
probs = count/16, Σp=1±1e-9; ON vs OFF identical PackedKey→prob maps and leaves(ON) ≤
leaves(OFF) on a mixed set; Skill Link 5-hit → leaves(ON) strictly < leaves(OFF), Σp=1;
crit×roll → buckets keyed within crit class; Natural ≡ AdverseFirst multiset with ON;
hand-built entry w/o annotation → throw; unknown Cat-B event → throw naming it;
same-seed random-mode with log on vs off → state_equal (annotation side-effect-free).
Acceptance: full fresh audit pass — selfcheck (incl. aggregation-compare) + mc, seeds
{1,2,3} × classes {uniform,berry,sash}, sharded, ZERO failures; bench_oracle re-run:
report p50/p90/p99, leaf histogram, budget-exceeded count vs phase-1 (5 exceeders at 33M
paths expected to fit; report any residual exceeders).

## Task 2 — Bsolver exact core (AND-OR boolean certifier over the oracle)
Files: solver/bsolver.h/.cpp, engine/tests/test_solver_bsolver.cpp.
Rationale: the real certification engine (P(win, no faint)==1), pulled forward from phase 3;
it is also the exact reference that verifies every later tier. Only sees the oracle.
- bsolver_certify(state, question, cfg{mode=Exact, per-step leaf budget, node cap, depth cap})
  → {WIN, LOSS, INDETERMINATE(reason)} + stored best-action policy for WIN (needed later for
  MC policy-replay validation and phase-3 B2).
- Semantics (BSOLVER.md): WIN(s) iff some legal player action (action_space + Question
  action filter) has ALL p>0 oracle children WIN; Question classify() at terminals; monotone
  constraints may fail early where phase 1 flagged them safe. Self-loop children (child
  PackedKey == parent) are ignored; an action whose children are ALL self-loops fails.
  In-stack revisit of a non-self-loop ancestor → INDETERMINATE (log it). Budget/cap →
  INDETERMINATE, never a partial answer.
- INTERLEAVED ENUMERATION: children tested during oracle emit; the action aborts (emit
  returns false) on its first losing child; AdverseFirst ordering so losses resolve fast.
- MEMO GEOMETRY (prototype): per-context (all non-HP state, interned to an id) bitmap
  planes over (plHP, oppHP) for decided-WIN / decided-LOSE; one interner per certify call.
  Segment queries (segSkip) are NOT ported this phase — the planes just serve as the memo.
Tests: player-faster guaranteed OHKO → WIN with policy; opponent guaranteed OHKO under both
orders → LOSS; both-fainted terminal under default question → LOSS; harmless-opponent +
<100%-acc player move → self-loop-ignore rule (WIN); keepItem question flips a
berry-spending win to LOSS; tiny budget → INDETERMINATE; same matchup twice → identical
verdict; memo: revisited context+HP resolves without new oracle steps (assert via StepStats
call counting).

## Task 3 — Pessimal + coarse modes and their theorem audits (bcheck/ccheck shapes)
Files: solver/bsolver.h/.cpp (mode flag in the random-outcome loops), solver/audit/bcheck.cpp,
solver/audit/ccheck.cpp (EXCLUDE_FROM_ALL exes, shard/of), engine/tests/test_solver_bsolver.cpp.
Rationale: user decision — the cheap tiers kill the loss-majority almost for free and thus
accelerate every later verification pass. ~30 lines each on top of the exact core, but the
SOUNDNESS BOUNDARY must be re-derived on our engine.
- Pessimal (g_pess): every ALWAYS-PROGRESSING random node collapses to its single
  worst-for-player outcome (no chance branching). Coarse (g_coarse): min/max rolls per crit
  class. LOSS conclusive by the subset-support theorem; WIN is a candidate for exact.
- LEMMA (o) re-derivation (required deliverable, in code comments + records): enumerate OUR
  engine's starvation shapes — randomness whose pessimization can starve an action into a
  pure self-loop (accuracy, proc/act-or-not, full-para, flinch...; also recharge/charge
  turns, PP). Rule: collapse only randomness that always progresses (damage rolls, crits,
  hit counts, opponent events, timers); keep the player's act-or-not branching intact.
  The collapse-eligible event list is an explicit auditable table over RngEventC.
- bcheck exe: exact-vs-reference on generator matchups — reference = independent naive
  unmemoized AND-OR walker (audit-grade, lives in audit/ only) cross-checking bsolver-exact
  on small-budget matchups, both directions.
- ccheck exe: pessimal/coarse-vs-exact with theorem checking — every pessimal/coarse LOSS
  must be exact-LOSS (soundness, HARD FAIL printed first); pessimal/coarse WIN vs exact
  outcome → false-positive rate reported (cost, not failure); INDETERMINATE = skip counted.
Tests: pessimal on a matchup whose only loss path needs a crit → LOSS while exact needs
enumeration (subset check); pessimal never flips an exact-LOSS to WIN on a seeded batch
([.slow] smoke over ≥25 matchups, zero soundness failures); accuracy is NOT collapsed
(player <100%-acc move still branches in pessimal — starvation guard); coarse ⊆ exact
support per node (spot-check via oracle children); mode flag default = Exact.
Acceptance: bcheck + ccheck runs over seeds {1,2,3} × {uniform,berry,sash}, sharded,
zero soundness failures; report pessimal/coarse false-positive rates + µs/matchup vs the
~1.5ms / 3-9% prototype calibration.

## Task 4 — Read-only engine queries: damage tables + HP-threshold sets
Files: solver/engine_queries.h/.cpp; oracle_types.h/.cpp (DELETE the two throwing stubs —
this task is their real implementation); engine/tests/test_solver_engine_queries.cpp.
Rationale: the analytic tier's core representation (point + cover interval) is built on
distinct-damage lists and one-shot HP thresholds, re-fetched at act time.
- damage_table(state, attacker_side, ExecAction): per crit class {0,1} the sorted distinct
  damage list from cpp_calculate_damage(roll_index=0..15, crit_override, ai_scoring_view=
  false, real def_side_idx), plus immune flag (all-zero) and multi-hit metadata (max_hits and
  the hit-count support mirroring resolve_hit_count). NO multi-hit total-damage math in
  phase 2 (mid-sequence context drift — Multiscale off after hit 1, pinch activation,
  per-hit crit — makes naive totals unsound); analytic wave 0 scopes multi-hit out.
  Caveat to document: the table mirrors cpp_calculate_damage's view only — caller-side
  modifiers (Parental Bond, Metronome item, Minimize, OHKO) are NOT reflected; those
  features sit behind analytic scope bits until a wave models them.
- hp_thresholds(state, side): list of (threshold_hp, kind) for one-shot discontinuities:
  full-HP (Sash/Sturdy/Multiscale/Shadow Shield), half (Sitrus), quarter (Custap/pinch
  berries per item table). Unrecognized consumable held → a residual flag so callers scope
  out (fail loud is wrong here: UNKNOWN routing is the design).
- Contract: queries are const, mutate nothing, and consume NO RNG machinery — no occurrence
  bumps, no injections, no log entries (crit_override + roll_index bypass the resolvers).
- NOTE: cpp_damage_roll_values (ai_damage.h) is the AI-view cousin (ai_scoring_view=true,
  AI quirks); do NOT reuse it for battle-view tables.
Tests: for an in-scope single-hit no-secondary matchup, oracle children's HP deltas ==
table values exactly (miss branch excluded; crit class masses match) — a true
two-implementation cross-check; burn/screen/boost/item contexts change the table; immune →
zeros + flag; crit list ≥ non-crit pointwise; thresholds: Sitrus → (max/2, sitrus), Sash at
full → (max, sash), no items/abilities → empty, unknown consumable → residual flag;
query with a log sink attached → sink stays empty and occurrence counters untouched.

## Task 5 — Analytic certifier skeleton (wave 0: pure damage race)
Files: solver/analytic/analytic.h/.cpp; engine/tests/test_solver_analytic.cpp.
Rationale: skeleton = representation + verdict plumbing + UNKNOWN routing + scope bitmask,
with the NARROWEST sound scope. Lemmas grow later, audit-driven (Task 7). Structure ports
from prototype analytic.h; concrete rules do not.
- Public contract: AnalyticResult{verdict WIN/LOSS/UNKNOWN; tag (AT_*-style reason enum);
  scope_mask (ALL failing scope reasons, not just first); tight; kill_turn; lines}.
  certify(const BattleState&, const Question&). Non-default Question → UNKNOWN(scope).
  UNKNOWN is routing; internal inconsistencies (interval inverted, Σ over buckets wrong,
  unexpected engine reply) THROW.
- Representation (prototype structure): player HP = worst-case-realizable POINT (+ pwHi
  cover ceiling while a live one-shot heal exists — wave 0 scopes player Sitrus out, but the
  field and dominance plumbing land now); opponent HP = point + cover interval [lo,hi]; tight
  flag (any worst-case-sound-but-not-realizable step degrades LOSS→UNKNOWN); runLine turn
  loop with turn cap + line/depth caps (cap → UNKNOWN(AT_CAP)); Pareto frontier of adversary
  continuations with a dominance predicate; kill-now preemption check.
- Adversary: exact per-state AI SUPPORT SET = actions with p>0 from
  cpp_compute_action_probabilities. Interval mask guard: re-query the support at EVERY HP in
  [oLo,oHi] (correct with no monotonicity assumption; prototype's endpoint-agreement trick
  relied on a PROVED single-crossing property we have not measured here). Endpoint-only
  optimization is gated on Task 6's mask-scan telemetry. Any support disagreement across the
  interval → UNKNOWN(AT_MASK).
- Wave-0 scope allowlist (everything else accumulates scope bits and routes UNKNOWN):
  both sides only single-hit damaging 100%-accuracy moves with no secondary/recoil/drain/
  bind/charge/priority/HP-dependent BP; no weather/screens/terrain; clean entry context
  (no status/boosts/volatiles/side conditions); items: exact allowlist derived from
  generator classes + move/item data (opp Sitrus and Sash/Sturdy handled as thresholds);
  opponent must have ≥1 effective damaging move (stall reason). Speed ties: fork BOTH orders
  and certify both (exact; no commutation assumption). Threshold straddles (Sitrus/Sash
  lines inside the interval): both-or-neither, else UNKNOWN(AT_THRESH). Damage tables
  re-fetched at act time.
Tests (behavior only): player-faster guaranteed OHKO → WIN, kill_turn=1; opponent guaranteed
2HKO vs player guaranteed 3HKO (all 100% acc) → LOSS; opp-Sitrus trigger straddling the
interval → UNKNOWN(AT_THRESH); multi-hit move present → UNKNOWN(AT_SCOPE) with the
multi-hit bit AND every other applicable bit set (accumulation test); a lost race after any
non-tight step → UNKNOWN not LOSS; full-HP Sash opponent + lethal single hit → no false
kill-now WIN; smoke: certify() over 200 uniform generator matchups never throws and returns
only WIN/LOSS/UNKNOWN.

## Task 6 — Analytic audit + trace tools (acheck/adbg equivalents, tiered verification)
Files: solver/audit/audit_analytic.cpp, solver/audit/analytic_trace.cpp (both new exes,
EXCLUDE_FROM_ALL, shard/of), CMakeLists.txt; small Catch2 smoke in test_solver_analytic.cpp.
Rationale: AUDIT.md discipline — two-sided verification, collect-until-N-decided, reason
histograms, single-case trace. Budget for the trace tool on day one.
- audit_analytic --seed --klass --n N --mode {all|collect|fast} [--shard k/of]:
  scan generator matchups (collect: until N DECIDED verdicts); run analytic AND pessimal on
  every matchup; verify EVERY decided analytic verdict: analytic-LOSS + pessimal-LOSS →
  confirmed cheap; analytic-WIN + pessimal-LOSS → soundness failure (pessimal LOSS is
  conclusive); ALL other decided combinations → exact bsolver adjudicates (pessimal WIN is
  never evidence — a true LOSS may pessimal-report as WIN). Analytic-LOSS vs
  exact-WIN failures print FIRST with full repro (seed/class/index). bsolver INDETERMINATE
  = skip (counted), not fail. Summaries: decided/WIN/LOSS/UNKNOWN counts, coverage %, exact
  WIN base rate, UNKNOWN tag histogram, scope-reason bitmask histogram (all reasons per
  matchup), analytic µs/matchup, pessimal-vs-exact verification cost split.
  Nonzero exit on any soundness failure.
- --mask-scan mode: over M matchups sweep opponent HP 1..max, query the AI support set at
  each HP, count crossings per action; report multi-crossing frequency. This telemetry
  decides whether the interval mask guard can move to endpoint-agreement.
- analytic_trace --seed --klass --index [--action slot]: print both mons, speed comparison,
  both sides' damage tables per crit class, analytic per-turn line trace, verdict/
  tag/tight/scope_mask, bsolver verdicts (pessimal + exact); with --action: enumerate that
  action's oracle children and mark losers (classify, else bsolver on the child) — the
  adbg shape.
Tests: inline [.slow] smoke — audit loop over 10 uniform matchups with small budgets:
zero soundness failures (skips allowed), histograms populated; trace helper runs without
crashing on 3 matchups.

## Task 7 — Lemma waves: audit-driven expansion (repeating protocol, per-wave approval)
Files: solver/analytic/*.cpp/.h, regression fixtures in engine/tests/.
Rationale: this is the re-derivation. The meta-rule governs every wave: EVERY scalar
shortcut over a support set must name the branch that realizes it; if no single branch
realizes the combination, fork or return UNKNOWN. WIN needs coverage; LOSS needs
realizability.
Protocol per wave (repeat until exit gate):
1. Run sharded collect audits across seeds {1,2,3} × classes {uniform,berry,sash}.
2. ANY soundness failure: reproduce with analytic_trace; NAME the lemma (which unrealizable
   composite / uncovered branch did the shortcut assume) in a code comment; capture the
   matchup as a Catch2 regression fixture (seed/class/index + expected verdicts) BEFORE
   fixing; fix; re-run ALL regression fixtures + a fresh audit.
3. If clean: pick the next expansion from the UNKNOWN-tag + scope-reason histograms
   (largest MEASURED unlock; reasons co-occur, so no wave unlocks its face value).
   PRESENT the histogram and proposed wave to the user; implement only after approval.
Candidate waves (prototype inventory — candidates ONLY, order and rules must be measured):
accuracy<100 handling, opponent secondary/status exposure with branch-once bookkeeping,
para/flinch P<1 refutations with sustainability caveats, sleep bounded-skip, one-shot item
classes both sides (Sitrus/Sash/Lum), choice-lock enumeration, opener families (WIN-only,
state-gated), drain/recoil correlation (tight rules), multi-hit tables, defensive-boost/
screen re-branching. Latent holes are expected (prototype: 3 lemmas sat quiet through ~450k
scans) — always audit stress classes, not just uniform.
Exit gate (user-approved): zero soundness failures over ≥2000 decided verdicts (collect
mode, 3 classes × ≥3 seeds, sharded) with every regression fixture green. Coverage is
REPORTED, not gated.

## Task 8 — Phase-2 exit report + calibration comparison
Files: none new (runs + summary; audit/bench output).
- Re-run bench_oracle (post-aggregation), bcheck/ccheck, audit_analytic (fast + collect).
- Present to the user: uniform decided fraction (calibration ~10%), share of exact true wins
  analytic decides (~31%), analytic latency p50/p90 (~100µs; expect AI support queries to
  dominate — report the mask-guard share), pessimal/coarse false-positive rates + speed vs
  exact (~1.5ms / 3-9% calibration), verification cost split (pessimal-confirmed vs
  exact-adjudicated), oracle step latency/leaf/budget-exceeded deltas vs phase-1 bench,
  tag/scope histograms.
- Output: console summaries + a short verbal report; user decides phase-3 (segSkip, B2,
  psolver, chain) go/no-go.

## Settled/provisional decisions (record via records.py at wrap-up)
- requirement: bsolver (exact + pessimal/coarse) pulled into phase 2; segSkip + B2 deferred.
- settled: aggregation via per-roll final-damage annotation at the resolution site, grouped
  pre-recursion in expand_catb_options. Post-hoc child dedup by state hash REJECTED as
  primary: it pays the full turn replay per leaf before merging — it cannot cut the 33M-path
  executions; annotation merges whole subtrees before recursion and is exactness-provable
  at the draw context. SUPERSEDES phase-1 provisional "no leaf dedup in oracle" (update it).
- settled: bucket on the UNCLAMPED cpp_calculate_damage return (clamp/overkill-aware merging
  deferred). settled: multi-hit scoped out of analytic wave 0 (unsound naive totals under
  mid-sequence context drift). settled: bcheck's naive reference walker is permanent
  audit-grade infrastructure (prototype kept the same shape), not a solver.
- provisional: interval mask guard = full per-HP support scan (endpoint optimization gated
  on --mask-scan telemetry). provisional: bsolver in-stack-cycle → INDETERMINATE.
  provisional: aggregation Config flag default ON (OFF exists for the audit A/B only).

## Known risks
- Analytic latency: cpp_compute_action_probabilities is far heavier than the prototype's
  mask and wave-0 scans every HP in the opponent interval; the ~100µs calibration may be
  unreachable until endpoint optimization is telemetry-justified. Task 8 reports the split.
- Bsolver exact win-certification cost without segSkip is unknown on the real engine
  (prototype leaned on segments for ~70% of probes); budgets keep audits bounded — if
  exact adjudication throughput blocks the exit gate, segSkip moves up (user decision then).
- Lemma (o) starvation shapes on this engine (recharge/charge/PP/full-para) are unmeasured;
  the collapse-eligible table must err toward keeping branches (soundness over speed).
- The analytic tier must NOT run engine queries inside oracle replays (global injection/log
  state); it never does by design — asserted via the Task 4 cleanliness test.
