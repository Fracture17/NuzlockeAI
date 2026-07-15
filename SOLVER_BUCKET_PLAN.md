# Bucketed Range Solver — plan & discussion record (2026-07-14)

The user authored the spec (Part 4, verbatim) in a separate session without code access,
then reviewed it with the tech lead against the actual codebase. Part 1 records the
agreed amendments — WHERE PART 1 CONFLICTS WITH PART 4, PART 1 WINS. Part 2 maps the
spec's assumed host interfaces to existing code. Part 3 lists what is still undecided.
Supersedes SOLVER_PHASE2_PLAN.md as the active workstream (phase 2 paused, see
SOLVER_PHASE2_STATE.md). Pipeline roles: pessimal kept as step-1 LOSS pruner; bsolver
retired from the pipeline but KEPT as the audit ground-truth referee; analytic likely
retired (disposition decided after the new system works).

---

## Part 1 — Amendments and resolutions (all USER-approved unless marked)

1. **Yawn concede rule corrected (spec §5.1 is wrong).** Do NOT concede on Yawn
   landing. Sleep begins at END of the turn after Yawn connects, so the player acts
   freely that next turn. Concede only when the player is *asleep* while trying to act.
   If a question requires not-asleep at end-of-turn, the question predicate handles it.

2. **Solver C is exact; all inexactness lives in the concede list.** Characterization
   for docs: "C is exact; the concede list trades bounded-duration-gate stall wins for
   speed." Sleep (1–3 turns) and confusion (bounded) can end adversarially, so
   stall-then-win lines exist and are conceded away. Para/freeze/flinch concessions are
   EXACT under probability-1 semantics (adversarial RNG can repeat those gates forever).
   USER: conceded→FAIL is accepted; §5.3 no-op tolerance stays OFF by default.

3. **Pessimal is a universally sound LOSS-pruner for ANY goal** (supersedes earlier
   worry). Argument: any fixed assignment of *realizable* RNG outcomes is a real
   scenario; a guaranteed win must survive every scenario; an adaptive real player
   cannot beat an informed player within the fixed scenario. Direction only tunes the
   miss rate, never soundness. USER direction choice: opponent max rolls + procs land,
   player min rolls + procs fail ("can you win even when the mechanics are completely
   against you"); optional inversion for unusual goals is an optimization. Precondition
   (already guaranteed by the implementation): collapsed outcomes must be actual
   enumerated branch options, never fabricated values.

4. **Shift-property assertion (spec §4).** Image-splitting at breakpoints is valid only
   because standard damage is independent of defender current HP (per-cell map is a
   constant shift ⇒ image splits == input splits). `Expand` must ASSERT the shift
   property and THROW when it fails; HP-dependent maps route to §5.2 special cases.

5. **Crit-ordering claim (spec §3) — AUDITED 2026-07-14, spec claim FALSE.** The
   1.275× ratio fails for ~96% of standard moves (integer floors give ~1.25), and
   strict dominance fails at low damage (crit_min == noncrit_max when pre-roll ≤ ~5).
   Measured guarantee: WEAK dominance (crit_min ≥ noncrit_max; zero violations over
   1500-matchup corpus, fixed-damage family allowlisted). USER decision: assert weak
   dominance; treat strict dominance (measured 99.92%) as a per-table fast-path
   predicate — one integer compare at Expand — exploited when true (single ordered
   range / top-cell collapse), separate crit/noncrit cells otherwise. Test also gates
   fast-path frequency ≥90% against damage-formula regressions
   (test_bucket_crit_ordering.cpp).

6. **Breakpoint set B: exhaustive per-mechanic enumeration derived from engine code.**
   USER: most breakpoints arise from single mechanics, not interactions, so an
   exhaustive independent list is feasible. Additions beyond spec §1.2's illustrative
   list: pinch ABILITIES that change damage (Blaze/Torrent/Overgrow/Swarm at 1/3),
   heal-cap kinks (hmax − heal_amount for Leftovers/Sitrus/etc.), faint (hp 0) as an
   explicit transition-semantics boundary.

7. **AI breakpoints: analytical derivation primary, sampled scans as auditor.** Eager
   scanning explodes (HP² × 2^10 status combos × precondition space); lazy per-(d,axis)
   scanning helps but USER prefers analytical. Derive support-flip boundaries from the
   AI scorer (kill-estimate flips use the AI's exact damage-estimate convention from
   ai.cpp; cap-tie values; Pursuit/Explosion/recovery thresholds), then VERIFY against
   measured support flips (mask-scan) on sampled reached configs. `first_turn_out`
   (Fake Out / Stealth Rock AI priority) lives in `d` / question preconditions —
   deterministic, expires after one turn, buckets cleanly. Matchup space is bench ×
   items × moves × stat changes × statuses × opponent team; heuristics may shrink it
   later but make NO timing assumptions.

8. **Multi-hit is handled, not conceded.** (a) Heal-berry case: if no single hit can
   take the target from above the heal threshold to KO, the berry deterministically
   fires when total damage crosses it ⇒ piecewise shift with known heal offset; the
   jump point (threshold + damage) is a breakpoint; monotone per piece. (b) Hard
   sub-case (single hit spans threshold→KO): per-hit enumeration. (c) Defense-changing
   triggers mid-sequence (Weak Armor/Stamina-style, defense berries): per-hit
   micro-pass — hits contain no decisions, so it is a linear chain of monotone maps
   with occasional bucket splits, effectively O(1); thread resulting `d'` (stage
   changes) to the next turn. Per-hit crit flags multiply cells modestly.
   FIRST-PASS SOFTENING (USER 2026-07-14): sub-case (b) is conceded with a DISTINCT
   tag in the prototype; rcheck measures its prevalence, and per-hit enumeration is
   implemented only if the count is material. (a)/(c) remain handled.

9. **Branching model (USER, replaces spec §8.3 "buckets ≤ opponent_moves"):**
   player_moves × opponent_moves × small factor; similar opponent moves merge into the
   same buckets. Expect the small factor ≈ 2–4 from d-changing secondaries (burn/stat
   drops; SECONDARY present in ~95% of matchups per phase-2 histograms).

10. **Audit-first discipline (USER-approved).** Solver B and Solver C are each
    validated against bsolver over the generator corpus BEFORE entering the pipeline
    (the phase-2 certifier-seam referee generalizes directly). FAIL verdicts must carry
    a concession tag so bsolver-WIN vs C-FAIL mismatches are classifiable as expected
    (conceded) vs soundness bugs (unacceptable).

11. **Solver C example of model-vs-game gap** (for the record): opponent sleeps the
    player but cannot make progress; sleep is bounded, so no-op through worst-case
    sleep then KO is a true guaranteed win; conceded→FAIL loses it. Accepted trade.

12. **Breakpoint registry is GLOBAL and one-time** (per-mechanic formulas keyed by
    item/ability/move IDs, each with source reference + test); B is *instantiated* per
    matchup+question by evaluating registry entries against concrete max HPs, movesets,
    items, and question boundaries. Engine-mechanics inventory = one-time agent task
    with USER approval of the resulting list.

13. **Prototype-first strategy (USER).** Build the full stack quickly, tolerating
    potential errors, to get end-to-end timing feedback; then refine each component.
    Caveat (lead): correctness bugs usually UNDER-split buckets, so prototype timings
    are optimistic lower bounds; keep the free fail-loud checks and run the bsolver
    audit alongside for an error-rate signal (non-blocking).

14. **Endpoint-paired replay + sequence verification APPROVED** (USER accepted ≤2×;
    in practice near-free — endpoint reduction already requires replaying BOTH
    endpoints, so verification is just an event-log comparison; only
    single-representative shortcuts pay the second replay).

15. **Question semantics (USER).** Chunk boundary = the moment a new pokemon would be
    sent in (by either side): after faints + slower side acting + residuals, at the
    replacement-decision moment — exactly when the AI picks its send-in. Mid-turn
    switch triggers (Eject Button/Red Card/E-Exit/U-turn family): state is checked at
    the decision moment and must also encode pending opponent actions if they haven't
    moved; representation unknown → AUTO-FAIL for now. Future sketch (lead): success
    predicate over (state, pending-action set), AND-quantified over the support at that
    moment. Pure 1v1 has no bench, so this only bites at 6v6-chain embedding.

16. **`d` contents (USER).** PP for ALL moves on BOTH sides (prevents cycles, no
    downside without caching; strictly decreasing ⇒ DAG). All game-influencing
    counters (sleep/confusion/binding/Encore/Taunt/weather/screens/Yawn-pending). NO
    raw global turn count — only the first_turn_out flag the AI reads.
    PROVISIONAL amendment for when Solver C caching lands: track exact PP only for
    HEAL moves (full PP fragments the cache — keys never repeat). Requires two
    companions to stay sound: (a) on-stack repeated bucket = FAIL (needed anyway:
    Leftovers regen has no PP, and looping forever is never a win); (b) conservative
    depth cap = total remaining PP at root (kills false WINs from stall lines needing
    more uses of an attack than its PP allows).

17. **Build order (USER).** Solver B finished and measured before Solver C (C adds
    mechanics to the same core). First pass skips bitmaps/slivers, §5.2 special cases
    (concede them), §5.3 — but keeps free invariant checks (sequence match, shift
    assert). Timing telemetry (per-matchup latency percentiles, ccheck-style) from day
    one; no performance target.

18. **Pipeline verdict semantics (USER 2026-07-14).** LOSS is reported only from sound
    sources: pessimal LOSS now, and later Solver C root-FAIL — which per USER is an
    OPERATIONAL LOSS even when concession-caused (nobody ever re-checks a concession;
    C shares the concede list). Solver B's WINs are sound; its non-WIN is "couldn't
    certify", never LOSS. The dispute set = pessimal-survived ∧ B-not-certified is
    surfaced as UNKNOWN + concession tags and is exactly Solver C's future work queue.
    Once C lands, UNKNOWN disappears from final output.

19. **Naming (USER: any name fine).** Whole system = "the bucket solver"; module
    `engine/src/solver/bucket/`. Spec Solver B = bucket WIN pruner, entry
    `bucket_win_certify()`. Spec Solver C = bucket partition solver (later). Referee/
    timing audit tool = `rcheck` (ccheck-style, EXCLUDE_FROM_ALL).

20. **Inventory §11 resolutions (USER 2026-07-14).**
    (a) REST: engine bug confirmed — Rest must FAIL at resolution when user is at
    full HP, but selection stays legal (it can matter if hit before acting). Fix task
    scheduled (effects.cpp + regression test) BEFORE Task 10; manifest/golden-trace
    fingerprints may shift → run gates, re-record if needed. Full-HP becomes a Rest
    resolution-semantics breakpoint.
    (b) Overkill coupling (drain/recoil/Shell Bell/Leech Seed heal = min(dmg, hp) in
    kill-possible cells breaks attacker-axis shift): CONCEDE with distinct tag for the
    prototype; revisit after timing feedback ("we'll likely need something better").
    **SUPERSEDED by amendment 21(a): THROW for now (USER 2026-07-15).**
    (c) max_hp constant per question chunk — sound in 1v1 (EXP only on opp faint =
    chunk end); form-change species conceded with tag. NEW REQUIREMENT: player LEVEL
    is an input parameter of the Question (staying under level cap to manipulate the
    AI is a viable tactic). Wrinkle: level-up happens AFTER the matchup ends but
    BEFORE the end state is checked — never affects in-matchup HP thresholds, but the
    checked end state can differ. EXP handling in general deferred (USER: later).
    (d) Wish/Strength Sap: NOT conceded (lead's concern withdrawn). Heal amounts have
    finitely many candidates (Wish: floor(max_hp/2) of either active or the given
    starting-state value; Sap: opp base Atk × 13 stages), and B may be a superset —
    registry statically enumerates every candidate heal-cap kink; ordinary
    status-parameterized entries.
    Remaining §11 items resolved by lead (settled): residual_unknown THROWS (rcheck
    census absorbs); chip kinks = derived splits at Expand (single convention);
    per-hit berry/ability thresholds folded into amendment 8 cumulative splits;
    toxic_turns verified in d; damage_table caveats (Parental Bond/Metronome/
    Minimize/OHKO/resist berries) added to Task 6 concede coverage; Substitute
    sub_hp = concede tag.

21. **Inventory sign-off + review decisions (USER 2026-07-15).** Inventory APPROVED —
    Task 8 unblocked. Decisions from the line-by-line review (details + postponed list
    in SOLVER_BREAKPOINT_INVENTORY.md §11/§14):
    (a) Overkill coupling: **THROW for now** — supersedes 20(b)'s concede-tag. Promote
    to concede tag only if the Task 10 rcheck throw census is noisy.
    (b) Fixed-damage moves (Seismic Toss/Night Shade/Dragon Rage/Sonic Boom/Psywave)
    **reclassified SUPPORTED** — HP-independent damage, cannot crit; the §5.2 corner
    damage-table-equality screen passes them legitimately. They stay on the Task 1
    crit-audit allowlist (different concern) but are NOT §5.2 concessions.
    (c) OHKO moves: semantically an always-kill (1M-BP analogy), blocked only by
    infrastructure (`damage = hp` override applied outside cpp_calculate_damage, so
    damage_table doesn't model it). Prototype THROWS; always-kill fast path is the
    refinement.
    (d) Gluttony: **implement FULLY in Task 8, no hacks** — extend hp_thresholds()
    with the ability-conditional denominator + the Custap action-order site.
    (e) Substitute: prototype concede tag stands; TRUE THIRD AXIS is the long-run
    design (post-Sub healing extends reachable space by max_hp/4). Player can have
    Substitute; postponed, not dropped.
    (f) Confusion/stunlock §5.1 concession is **PLAYER-side only**; opponent
    confusion self-hits are adversarial AND-branches.
    (g) Multi-hit hard sub-case: USER's precompute outline (per-hit berry/trigger
    deltas enumerable beforehand → finite cumulative damage set) documented as the
    refinement; amendment-8 concede tag stands meanwhile.
    (h) Embargo exists in Run & Bun but is ABSENT from the engine (grep: zero
    matches) — known engine gap, postponed (inventory §14 #10).
    (i) ENGINE BUGS found during review → **Task R2** (fix before Task 10, same
    protocol as Task R): Destiny Bond must faint the attacker DIRECTLY (survival
    mechanics — Endure/Band/Sash/Sturdy — must NOT apply; today it routes through
    cpp_apply_damage, move_exec_damage.cpp:248-251); Explosion/Self-Destruct family
    must self-faint even on miss/Protect/zero damage (today gated on damage > 0,
    post_hit.cpp:875-878); Curse (Ghost) at/below half HP must still curse the
    target and self-faint the user (today silently no-ops, effects.cpp:1500-1506);
    Memento must faint iff the move activates — no faint on miss/Protect/Substitute,
    yes on Clear Body/−6 (faint-first order verified correct; guard-path gating to
    VERIFY in R2, effects.cpp:1492-1497).

## Part 2 — Host-interface mapping (spec §0 → existing code)

- `Support(s)` → engine_queries / cpp_compute_action_probabilities (p>0 filter). EXISTS.
- `Order` + speed-tie surfacing → oracle Cat-A SPEED_TIE events; analytic already forks
  both orders. EXISTS.
- `ResolveTurn(s, pm, om, rng_cell)` → oracle forced-prefix replay. Wrinkle: our oracle
  discovers RNG events dynamically; spec assumes cells enumerable up-front. APPROVED
  (USER 2026-07-14, per amendment 14): enumerate the event tree by replaying the LO
  endpoint, then replay each cell's forced prefix at HI and VERIFY the event sequences
  match — a free runtime INV-1 checker (mismatch = missing breakpoint = throw).
- `DamageInterval` + crit variant → dmg_by_roll[16] from the real modifier chain
  (damage.cpp apply_roll_and_modifiers); crit variant is a small extension. MOSTLY EXISTS.
- Pessimistic solver → oracle Pessimal collapse + bsolver-style search. EXISTS
  (hardened: NaN-poisoned collapse probs, 256 MB dedicated-stack thread).
- Also available: bsolver as ground-truth referee; audit harness with injected-fixture
  + certifier seam; MatchupGen stress classes; analytic scope classifier (reusable for
  §5 concede detection: SECONDARY/MULTI_HIT/BINDING/PRIORITY bits); analytic_mask_scan
  (support-flip measurement); 256 MB stack-thread pattern for deep recursion.

## Part 3 — Open discussion points (updated after resolutions 12–19)

1. Breakpoint registry CONTENT work: covered by Tasks 2/8/9 below (inventory
   APPROVED by USER 2026-07-15, amendment 21 — Task 8 unblocked).
2. Mid-turn switch second-half encoding — deferred (auto-fail placeholder; lead's
   pending-action-set predicate sketch in item 15 when revisited).
3. State codec d-hash excluding HP — settled in principle (item 16 defines d);
   field list written at implementation time.
4. Task decomposition — DONE, see Part 3.5 (Plan-agent output, USER-approved
   2026-07-14).

## Part 3.5 — Prototype task plan (USER-approved 2026-07-14)

Tests designed BEFORE implementation per task; one Code agent at a time. Layout: new
`engine/src/solver/bucket/` inside nuzlocke_solver; tests `engine/tests/test_bucket_*`;
audit tool `engine/src/solver/audit/rcheck.cpp`.

1. **Crit-ordering audit (S).** Test-only — `damage_table()` in engine_queries.h
   ALREADY returns crit+noncrit vectors. Integer check `40*crit_min >= 51*noncrit_max`
   over MatchupGen corpus (≥500/class ×3 classes); collect violators; every violator
   must be on a hard-coded §5.2 fixed-damage allowlist (Seismic Toss/Night Shade/
   Super Fang/Counter-family/OHKO) else FAIL. Violator list seeds Task 6's concede set.
2. **Engine-mechanics breakpoint inventory (M).** Research doc
   SOLVER_BREAKPOINT_INVENTORY.md: per mechanic — axis, exact floor-arithmetic formula,
   trigger ID, source file:line; flagged registry-vs-§5.2-concede. USER APPROVAL gates
   Task 8; nothing else blocks on it.
3. **Oracle extensions (M).** transition_oracle: (a) per-leaf AI-action attribution in
   LeafDebugInfo; (b) `replay_path` — force a captured prefix for one turn, return
   child + observed event sequence, THROW on divergence. bsolver behaviorally untouched
   (leaf-multiset bit-identity test); hot path unaffected (null-check pattern).
4. **Bucket core (M).** bucket/breakpoints.h/.cpp + bucket/bucket.h/.cpp:
   BreakpointRegistry (global one-time; instantiate(state,question)→BpSet; skeleton
   delegates to hp_thresholds(), which is the existing d-codec's threshold source —
   THROWS on residual_unknown); Bucket (d = ctx_id via ContextInterner, no interior
   breakpoint by construction); conservative merge; classify_bucket consistent with
   concrete classify().
5. **Expand (L).** bucket/expand.h/.cpp. Order matters: (i) derived input splits
   FIRST — analytic boundaries at `b + dmg` (cumulative for multi-hit) from
   damage_table; (ii) endpoint-paired replay via replay_path as VERIFICATION; (iii)
   support-equality check at both endpoints (cpp_compute_action_probabilities); (iv)
   shift assertion (image width == input width per cell); (v) image splits at BpSet
   with per-child d' (endpoint children must intern to same ctx_id). Any mismatch =
   THROW — NEVER auto-bisect (self-healing would mask under-splitting, item 13).
6. **Concede detectors (M).** bucket/concede.h/.cpp → ConcessionTag enum. §5 as
   amended (sleep-while-acting NOT Yawn-landing — the Yawn regression test is the
   task's most important test); para/confusion/freeze gates; Outrage/Hyper Beam;
   flinch-capable+slower; speed tie/Quick Claw; §5.2 moves (reuse analytic scope-bit
   logic, don't fork); multi-hit hard sub-case (distinct tag, item 8).
7. **Solver B core (L).** bucket/win_solver: `bucket_win_certify` DFS per spec §6;
   on-stack repeated bucket = FAIL (item 16(a), needed NOW for Leftovers loops);
   depth cap → INDETERMINATE; 256 MB dedicated-stack pthread (bsolver pattern); NO
   memoization first pass; day-one telemetry (buckets/expands/replays/depth/µs);
   Result carries policy + concession-tag histogram.
8. **Registry content fill (M).** Post-USER-approval of Task 2 list; one test per
   entry (hand-computed floor-arithmetic boundary + negative case + corpus
   no-throw sweep). Unimplementable entries escalate, never silently dropped.
9. **AI-scorer breakpoints (L).** bucket/ai_breakpoints from engine/src/ai_scorer.cpp
   + ai_damage.cpp (spec says "ai.cpp" — doesn't exist; verify the AI's damage-estimate
   convention from code, don't assume player-max-roll/no-crit). Kill-estimate flips,
   cap-ties, Pursuit/Explosion/Sub/recovery thresholds. Gate: sampled mask-scan audit
   (reuse analytic_mask_scan; ≥100 configs/class ×3) — ZERO unexplained support flips.
   Sequencing: after core (Tasks 4–7 use hand-built constant-support matchups), before
   Task 10 (corpus runs throw without AI breakpoints).
10. **Pipeline + rcheck (M).** bucket/pipeline (pessimal→B per item 18) + audit/rcheck
    vs bsolver Exact: HARD-FAIL classes (B-WIN∧exact-LOSS; pessimal-LOSS∧exact-WIN),
    tagged-vs-untagged conservatism split (untagged UNKNOWN-on-exact-WIN = refinement
    signal), throw census per exception type (under-split error-rate signal), timing
    p50/p90/p99 + telemetry aggregates. Classification logic unit-tested via injected
    verdict pairs (phase-2 certifier-seam pattern) BEFORE the corpus run.
    EXIT GATE (USER): 3 classes × 3 seeds × 1000/class, sharded across 10 cores
    (100 matchups/shard; rcheck takes a shard argument, emits machine-readable
    summaries; SCRIPTS/rcheck_aggregate.py merges) — ZERO soundness failures;
    histograms + timing delivered to USER.

Task R (S, added 2026-07-14, amendment 20a) — **Rest full-HP failure engine fix**:
    effects.cpp Rest resolution fails ("but it failed") when user at full HP;
    selection stays legal. Regression test both branches. Then run manifest 2k gate +
    golden traces; re-record divergent entries per protocol. Must land before Task 10.
    DONE 2026-07-15 (manifest entry i=1041 re-recorded, gate green).

Task R2 (S, added 2026-07-15, amendment 21i) — **Faint-semantics engine fixes**:
    (1) Destiny Bond drag-down faints the attacker directly, bypassing Endure/Focus
    Band/Sash/Sturdy (move_exec_damage.cpp:248-251 — replace cpp_apply_damage route);
    (2) Explosion/Self-Destruct family self-faints even on miss/Protect/zero damage
    (post_hit.cpp:875-878 — remove damage>0 gate, move to always-fires site);
    (3) Curse (Ghost) at/below half HP still curses the target and self-faints the
    user, paying all remaining HP (effects.cpp:1500-1506 — replace silent no-op);
    (4) VERIFY Memento guard-path gating: no faint on miss/Protect/Substitute, faint
    on Clear Body/−6 (effects.cpp:1492-1497) — fix only if wrong. Tests FIRST for all
    four. Then full suite + manifest 2k gate + golden traces; re-record divergent
    entries per protocol. Must land before Task 10.

Follow-on (not in this plan): Solver C, bitmaps §1.4, §5.2 special cases, §5.3,
C-era caching with item-16 heal-PP-only companions. Level-as-Question-parameter +
EXP dial-in (amendment 20c) — design with Solver C / 6v6 embedding.
Bug found during planning (report, unrelated): transition_oracle.cpp:417 ternary with
identical branches — harmless editing slip, simplify when convenient.

## Part 4 — Original specification (verbatim)

Bucketed Range Solver — Formal Specification
This document specifies three solvers and a pipeline that composes them, for answering 1v1 reachability questions of the form:
Under an optimal, outcome-adaptive player policy, is it guaranteed (probability 1, i.e. for every opponent choice in the AI support and every RNG outcome) that the battle reaches a success end-of-turn state before any failure end-of-turn state, starting from a given initial state?
Goals and failures are predicates over end-of-turn state: HP one-way thresholds, HP ranges, statuses, and field conditions, on either side. Checking happens only at end-of-turn. Search is DFS; a parent player-action is pruned as soon as any child is found to fail.
The design leaves HP as the only "continuous" state axis and collapses it via interval (bucket) reasoning, so that per-turn cost is O(1) in HP and the branching factor is governed by moves and by the number of distinct downstream buckets rather than by HP magnitude.

0. Interfaces assumed from the host system
The host system is assumed to already provide the following. This spec builds logic on top of them and does not re-implement them.

* `Support(s) -> {opponent_move, ...}`: the exact set of moves the AI may select in concrete state `s`. This is treated as ground truth. (0-probability moves are already excluded.) All ties are included.
* `Order(s, player_move, opponent_move) -> ordering`: resolves who acts first, including priority, speed, and any deterministic order rules. Speed-tie and Quick-Claw branching is surfaced here (see §5, concede list).
* `ResolveTurn(s, player_move, opponent_move, rng_cell) -> s'`: applies one full turn deterministically given a fully-specified RNG cell (damage roll endpoint, crit flag, secondary/status proc flags, hit/miss flags, multi-hit count), including residual ticks (weather, status, Leech Seed, item heals), item/ability trigger effects, and status application, in the correct in-game order. `rng_cell` fully determines the outcome, so `ResolveTurn` is a function.
* `DamageInterval(s, attacker, move) -> [lo, hi]` and a crit variant, giving the reachable damage range for one attack (already accounts for stats, items, boosts).
* The pessimistic solver (existing): a sound LOSS pruner. If it returns LOSS, the state is a true loss. It may return not-LOSS for both wins and losses. It does not enumerate status procs or accuracy; it assumes worst case. Its branching factor is `player_moves × opponent_moves` with no other axes.
Everything below is new logic.

1. State model
1.1 Concrete state
A concrete state `s` is a full end-of-turn battle state. Split it conceptually into:

* HP pair `(h_P, h_O)` — player and opponent current HP, integers.
* Discrete configuration `d` — everything else that is policy- or transition- relevant: statuses (both sides), stat stages, field/weather/screens, one-shot trigger flags (each consumable berry/ability marked spent-or-live), tracked recovery PP, item identities, form (post-mega), Yawn-pending flag, and any move-lock flags (Encore/Disable/Taunt/Torment/Choice/confusion-lock/recharge-pending).
So `s = (d, h_P, h_O)`.

1.2 Breakpoint set `B` (static, per matchup + per question)
`B` is a finite set of HP values on each axis, computed once from both movesets, items, abilities, and the question's goal/failure predicates. A value is a breakpoint if crossing it can change the AI support or the transition semantics or a goal/failure verdict. Include, per relevant axis:

1. Goal HP boundaries and failure HP boundaries (both sides). (Mandatory — see INV-3.)
2. Item HP triggers: Sitrus (50%), pinch/stat berries (25%), Focus Sash source (full HP).
3. Ability HP triggers: Sturdy (full), Multiscale/Shadow Shield (full), Berserk / Anger Shell / Emergency Exit / Wimp Out (50% crossing).
4. AI regime thresholds from the AI spec:
   * Player-HP kill-estimate boundaries: for each opponent damaging move, the player-HP value(s) at which the AI's (player-max-roll, no-crit) estimate flips kill/no-kill.
   * Player-HP cap-tie boundaries: the set of distinct estimated-damage values of the opponent's damaging moves. Below a cap value, multiple moves tie at the cap and enter support together; this is a support-changing breakpoint.
   * Opponent-HP thresholds the AI reads: Pursuit 20% / 40% (player HP); Explosion & Memento 10% / 33% / 66% (AI HP); Substitute and switch-block 50% (AI HP); recovery function 40% / 50% / 66% / 70% / 85% (AI HP).
5. HP-dependent move tiers: Reversal/Flail power tiers, Water Spout/Eruption power tiers (attacker HP). (Or special-case per §5.2.)

1.3 Bucket (abstract state)
A bucket `A = (d, I_P, I_O)` is a discrete configuration `d` together with an HP set on each axis. The default representation of each HP set is an interval `[lo, hi]` lying entirely between two consecutive breakpoints (so no breakpoint falls strictly inside). Optionally an axis carries a bitmap refinement: the exact set of reachable integer HP values within the interval (see §1.4).
Bucket uniformity invariant (INV-1): every concrete state in a bucket shares `d`, induces the identical support, and has identical transition semantics. This is guaranteed by construction because no support/transition/trigger/goal/fail breakpoint lies inside the bucket.
Two buckets merge iff they have identical `d` and identical induced support and identical transition semantics and adjacent/overlapping intervals. Merge is what yields the small branching factor (§8); it must be conservative — never merge across a difference in `d`, support, or resulting trigger state, even if damage numbers coincide.

1.4 Bitmap refinement — when required
Carry a bitmap (exact reachable-value set within the interval) only for boundary-touching buckets: buckets whose image under some transition intersects a goal or failure boundary, and buckets that will be used as preimage targets in backprop (§7). Interior buckets stay as plain intervals. Bitmap width is `interval_span / 64` words — negligible. Memoize on `(d, interval)`; attach the bitmap as a refinement rather than folding it into the memo key, so near-identical boundary buckets still share structure where legal.

2. Within-bucket monotonicity and endpoint reduction
Monotonicity (INV-2): fix `(player_move, opponent_move, rng_cell)`. On each axis, `h_out` is a nondecreasing function of `h_in` over the bucket. This holds because no trigger, cap, or clamp boundary is crossed inside the bucket (they are all breakpoints), so the composed per-turn map (opponent chip + player chip + residual ticks + heals) is monotone there.
Consequence: the image of an interval `[lo, hi]` is exactly `[ResolveAxis(lo), ResolveAxis(hi)]`. Only the two endpoints are transitioned. For a bitmap-refined axis, transition the endpoints for the interval bounds and, if a failure sliver detection is needed, transition the bitmap's set membership through the (monotone) map by mapping the min/max reachable values and re-deriving reachable image points from the known roll structure (or, conservatively, transition each set bit — still cheap at a few hundred bits).

3. RNG cell structure (per attack)
For a single attack, the 32 damage outcomes (16 rolls × crit/no-crit) are totally ordered in this hack: crit-min > noncrit-max unconditionally (crit only strips attacker-hostile modifiers; the roll spread gives crit-min ≥ 1.275·noncrit-max). So the damage outcomes for one attack collapse to cells = maximal roll-ranges lying between consecutive HP breakpoints in the target's post-hit HP; within a cell, endpoints suffice (§2). No-crit and crit are separate cells (crit is the top cell). If no breakpoint falls inside `[noncrit-min, crit-max]` post-hit, two representatives suffice (or one for a one-way goal on the safe side).
Non-HP RNG — secondary/status procs, hit/miss, multi-hit count — are flag-splits: separate AND-branches producing children with different `d`, not HP cells. Multi-hit count collapse is assumed already handled by the host.
Player accuracy: for a player move with accuracy < 100%, the miss outcome is an adversarial AND-branch (the miss happens). A winning line must therefore also win on the miss branch, which in practice forces 100%-accurate moves into guaranteed lines. Do not suppress the miss branch.

4. Turn transition (bucket → child buckets)
`Expand(A, player_move)` produces the set of AND-children:

1. If `player_move` is illegal under a lock in `d` (Encore/Disable/Taunt/Torment/Choice), skip it.
2. Apply §5 concede checks; if any fires for this line, mark the whole `player_move` branch as FAIL (do not expand).
3. For each `opponent_move ∈ Support` (host-provided; constant across the bucket by INV-1):
   * Resolve `Order`. Speed-tie / Quick-Claw: per §5, either concede the line or branch into both orderings as additional AND-children (exact mode).
   * Enumerate RNG cells (§3): damage cells × crit × proc/hit flag-splits.
   * For each cell, transition the two HP endpoints of `A` (INV-2) via `ResolveTurn`, yielding an image interval on each axis and a possibly-updated `d'` (flags for any trigger the cell crosses). Because the input interval touches no interior breakpoint, at most the trigger at the boundary can fire; split the image at any goal/fail/trigger breakpoint it lands across into separate child buckets, each with its own `d'`.
4. The children are the AND-set: the player action succeeds iff every child is a WIN; the bucket is a WIN iff some legal player action succeeds.
Every child is itself a bucket; recurse.
End-of-turn verdict on a child bucket (before recursing):

* If the child's HP intervals and `d'` satisfy the success predicate for all members → WIN leaf. (For a range goal: `image_interval ⊆ goal_interval`, checked at endpoints; valid by ordering even with gaps.)
* If they satisfy a failure predicate for any member → FAIL leaf. (If the interval straddles the failure boundary, the boundary is a breakpoint so the child was already split; if a bitmap is present, use it to detect a failure sliver that the endpoints miss.)
* Else recurse.

5. Concede list and special-cased mechanics
These are hard concessions (mark FAIL for the line) accepted in exchange for speed. They are sound as FAIL calls only in the sense of "not proven win"; they never cause false WINs. An optional refinement (§5.3) recovers some of them exactly.
5.1 Inflicted-no-op gates (stunlock family)
If the player's line requires acting through any turn where an RNG/deterministic gate can replace the player's action with nothing (or self-harm), concede the line — unless the question is already decided at the end of that same turn. Gates:

* Full paralysis; confusion (self-hit = no-op + self-chip, strictly worse); freeze; sleep (including Rest self-sleep); infatuation.
* Yawn connecting: a deterministic future no-op unless immune → concede on Yawn landing, not only on sleep. [AMENDED — see Part 1 item 1: concede only when asleep while trying to act.]
* Player-chosen confusion-lock moves (Outrage/Thrash/Petal Dance): concede the move.
* Recharge moves (Hyper Beam family) in the player's line: concede (scheduled no-op that must be robust to everything else).
* Opponent flinch-capable move in support while player is slower: concede lines that depend on the player acting that turn.
* Speed tie / Quick Claw: concede lines whose correctness depends on move order (or branch, in exact mode).
5.2 HP-dependent / non-monotone moves — special-case, do not interval-collapse
These break §2 monotonicity or compress the image; either expand them at full breakpoint granularity or transition per bitmap value: Super Fang, Nature's Madness, Ruination (fractional-current-HP); Endeavor, Pain Split (equalizers); Night Shade, Seismic Toss (fixed); OHKO moves; Counter/Mirror Coat/Metal Burst (reflect); Reversal/Flail, Water Spout/Eruption (HP-scaled power); Wring Out/Hard Press. Also treat HP-triggered abilities (Berserk/Anger Shell/Emergency Exit/Wimp Out) as bucket-splitters via §1.2, not as within-bucket effects.
5.3 Optional exact refinement — no-op tolerance
Before conceding a §5.1 gate in the exact solver, test whether the line still wins with a single adversarial no-op inserted at the gated turn. For one-way goals a no-op is monotone-bad, so one linear check suffices (no subtree). If it still wins, keep the line instead of conceding. Off by default in the fast solvers. [Part 1 item 2: stays OFF by default.]

6. Solver B — no-backprop range WIN pruner
Purpose: fast, sound WIN verdicts. A WIN is always correct; a not-WIN is inconclusive (may be a real win requiring intra-bucket policy).
Representation: plain intervals; bitmaps only where a goal/failure boundary is touched (so failure slivers are caught). No backprop, no failure caching.

```
solveWIN(A):
    if A ⊨ success:        return WIN
    if A ⊨ failure:        return FAIL        # whole bucket fails
    for player_move in legal_moves(A):
        children = Expand(A, player_move)
        if all(solveWIN(c) == WIN for c in children):   # AND; bail on first FAIL
            return WIN
    return NOT_WIN            # inconclusive, NOT a proof of loss (INV-4)
```

Bail-on-first-FAIL under the AND makes this cheap. It never splits a bucket for policy, so it explores the pessimistic-shaped tree once. Output is 2-valued from its caller's view: WIN (trustworthy) or not-WIN (defer).
Soundness (INV-3): requires goal & failure boundaries ∈ `B`, so no failure member hides mid-bucket. Then a WIN leaf holds for all members, and a WIN at an OR node holds for all members under a single bucket-uniform policy — a fortiori under an HP-adaptive one.

7. Solver C — exact backprop range solver
Purpose: definitive verdict. Partitions each reached bucket into exact WIN-member and FAIL-member sets, recovering the intra-bucket policy that Solver B cannot.
Return contract: `solveEXACT(A) -> partition of A.members into (WIN_set, FAIL_set)`. Because search is DFS-to-conclusive and cycles are structurally impossible (host tracks every cycle-creating resource, e.g. recovery PP), there is no pending class: each member resolves to WIN or FAIL before return.

```
solveEXACT(A):                       # A carries a bitmap of A.members
    resolve leaf members of A directly against success/failure predicates
    remaining = A.members not decided as leaves
    if remaining empty: return (wins, fails)

    global_win = ∅
    for player_move in legal_moves(A):
        # members that FAIL under this move = union over the AND of preimages
        fail_m = ∅
        for child in Expand(A, player_move):          # AND: support × rng × splits
            (cw, cf) = solveEXACT(child)              # recurse
            if cf nonempty:
                pre = preimage(child, cf)             # monotone ⇒ interval on each axis
                fail_m ∪= (pre ∩ A.members)           # INV-6: intersect removes phantoms
        winners_m = remaining \ fail_m                 # all AND-branches land in WINs
        global_win ∪= winners_m
        if global_win == remaining: break              # every member already covered
    return (leaf_wins ∪ global_win, remaining \ global_win)
```

* AND union (INV-7): a member fails under `move` if any AND-branch (any `opponent_move` in support, any RNG cell, any flag-split, any conceded gate) sends it to a failing child. So `fail_m` is the union of per-branch failure preimages. A conceded gate (§5) contributes its entire member range to `fail_m` for that move.
* Preimage (INV-6): child failure set `cf` (an interval, or bitmap) pulled back through the monotone turn map is `[preimage(cf.lo), preimage(cf.hi)]`; intersect with `A.members` (bitmap) to drop unreachable phantoms. The intersection cannot drop a true failing member (the map is a function: a real failing member's image lies in `cf`, so it lies in the preimage).
* Winners by elimination: `remaining \ fail_m` are members whose every AND-branch lands in a WIN child — true wins under `move`.
* Bucket verdict as reached: the bucket-as-a-range is a WIN iff `global_win == A.members`. Otherwise the range as reached is a FAIL, but the harvested `global_win` members are true wins for this `d`.
* Failure/winner caching (optional): cache `(d, WIN_set, FAIL_set)` per discrete config. A future range that lands entirely inside a cached WIN_set resolves instantly; one landing entirely in a FAIL_set fails instantly.
Completeness (INV-5): the partition is exact; combined with caching, revisiting a `d` under a different incoming range is O(set-ops).

8. Pipeline and complexity
8.1 Exact pipeline (goal 1: always-correct verifier)

1. Pessimistic solver → if LOSS, return LOSS (sound; no false losses). Screens most losses fast.
2. Else Solver B (WIN pruner) → if WIN, return WIN (sound; no false wins).
3. Else Solver C (exact) → definitive WIN/LOSS. [Part 1 item 2: "definitive" = exact modulo concede list; FAILs carry concession tags.]
The set reaching step 3 is exactly `{not proven-loss} ∩ {not proven-win}`.
8.2 Fast tri-valued solver (goal 2: whole-game sweep)
Use steps 1–2 only. Output ∈ {LOSS (from 1), WIN (from 2), UNKNOWN (neither)}. UNKNOWN either defers to the exact solver if budget allows, or carries a cheap heuristic verdict for resource allocation. This pair is fast because neither step splits buckets for policy.
8.3 Branching factor and cost

* Pessimistic: `player_moves × opponent_moves`, no status/accuracy axes (worst-cased by fiat). Smallest constant; strict loss-pruner.
* Solver B: tree shape `player_moves × buckets` [Part 1 item 9 branching model applies]. Per-node cost adds interval arithmetic + boundary clipping, O(1) in HP. Bails on first child FAIL.
* Solver C: same tree shape, but a bucket may be reprocessed under multiple player moves until `global_win == members`, so ≈ `×(move-count)` reprocessing, plus preimage set-ops (bitmap words, trivial). Cycles are excluded structurally, so the worst case is bounded.
The `player_moves × buckets` figure depends entirely on the conservative merge (§1.3) being tested on `(d, support, resulting-trigger-state)`, not on damage numbers alone. Merging on damage alone silently degrades toward `player_moves × opponent_moves`.

9. Consolidated invariants (soundness ledger)

* INV-1 bucket uniformity: all members share `d`, support, transition semantics. Guaranteed by putting every support/transition/trigger/goal/fail breakpoint in `B`.
* INV-2 within-bucket monotonicity: `h_out` nondecreasing in `h_in`; ⇒ endpoint reduction. From INV-1.
* INV-3 WIN soundness (Solver B): a WIN verdict holds for every member. Requires goal & failure boundaries ∈ `B`.
* INV-4 not-WIN is not LOSS (Solver B): bucket-level policy is coarser than HP-adaptive policy.
* INV-5 exact partition (Solver C): each bucket splits into exact WIN/FAIL member sets; DFS-to-conclusive + structural acyclicity ⇒ no pending class.
* INV-6 preimage exactness: `real_fail = preimage(child_fail) ∩ members`; drops phantoms, drops no true failure.
* INV-7 AND union: `fail(A, move) = ⋃_branches preimage_branch(child_fail) ∩ members`, over the full support × RNG × split AND (conceded gates contribute their whole range).
* Range success with gaps: within one bucket the map is monotone, so `[min,max] ⊆ goal ⇒ interior ⊆ goal` regardless of roll gaps. Gap-induced false losses arise only from (a) a failure sliver inside a bucket image, or (b) phantom straddle values at bucket splits; both are closed by the bitmap on boundary-touching buckets.

10. Implementation checklist (order of work)

1. Build `B` (§1.2) from movesets/items/abilities/question; include goal & failure boundaries.
2. Bucketing + conservative merge keyed on `(d, support, transition semantics)` (§1.3).
3. Endpoint-reduced `Expand` (§4) over host `Support`/`Order`/`ResolveTurn`, with RNG-cell collapse (§3).
4. Concede checks + HP-dependent special cases (§5).
5. Solver B (§6); wire pipeline steps 1–2 (§8.1); this is also the fast sweep (§8.2).
6. Bitmap refinement on boundary-touching buckets (§1.4); failure-sliver + straddle checks.
7. Solver C (§7): preimage, AND-union failure sets, winner-by-elimination, caching.
8. Optional §5.3 no-op tolerance in exact mode.
