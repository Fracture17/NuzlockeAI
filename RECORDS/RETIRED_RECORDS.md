# Retired Records

These records governed subsystems dropped at the C++ migration (greedy policy, NN pipeline, tree search)
or the Python Simulator class superseded by the C++ turn driver, or removed utilities.
Archived verbatim 2026-07-11 for when that work resumes; original `file` scopes preserved.

## Dropped subsystems: greedy policy, NN pipeline, tree search

[[record]]
name = "greedy_policy_module"
file = "src/greedy_policy.py"
confidence = "settled"
rationale = "GreedyPolicy needs the Simulator/search stack, so it lives apart from the I/O-free battle_policy.py. TeamFailureError is raised when no luck tier wins; callers treat the battle as a failure."
updated = "2026-06-15T05:01:12.372Z"

[[record]]
name = "mixed_policy_split"
file = "src/greedy_policy.py"
confidence = "requirement"
rationale = "MixedPolicy flips an independent 50/50 coin per decision between greedy and random. stress_test picks pure-greedy vs mixed per battle by a 50/50 coin flip. Prints policy mode per battle and per decision."
updated = "2026-06-15T05:01:15.841Z"

[[record]]
name = "driver_shared_helpers"
file = "src/search/driver.py"
confidence = "settled"
rationale = "Loosening/uncontrolled-advance/action-conversion helpers extracted here so run_greedy_search.py and greedy_policy.py share one implementation and stay in lockstep."
updated = "2026-06-15T05:01:19.370Z"

[[record]]
name = "converter_int_slot"
file = "src/search/driver.py"
confidence = "requirement"
rationale = "Switch phases (forced/post-faint) return best_action as a plain int bench slot, not an Action (search/engine.py). action_to_move_or_species must handle the int case (-> team[int].species.name), as choose_forced_switch relies on it."
updated = "2026-06-15T05:23:19.798Z"

[[record]]
name = "naive_matchup_cache_key"
file = "src/nn/matchup.py"
confidence = "settled"
rationale = "Cache key=full attacker+defender PokemonState (HP INCLUDED: pinch/Defeatist/Multiscale make damage HP-dependent)+side idxs+build_sig. _field_sig strips per-turn timers so bench edges reuse cross-turn; folds active ability/item for Air Lock/rooms."
updated = "2026-06-19T03:12:47.474Z"

[[record]]
name = "greedy_clean_win_invariant"
file = "src/greedy_policy.py"
confidence = "requirement"
rationale = "GreedyPolicy._search commits only to clean wins: found_win AND best_score==20-20*root_faints (no NEW faints; relative so forced-switch positions with prior faints pass). Else raise GreedyInvariantError (not TeamFailureError) with debug context."
updated = "2026-06-19T05:57:22.477Z"

[[record]]
name = "greedy_prune_player_faints"
file = "src/search/search.py"
confidence = "requirement"
rationale = "GreedySearch blocks any child whose player faint count exceeds the root baseline: such nodes are never explored or returned as wins. A faint-ful win is not a clean win, so found_win stays False and the driver loosens RNG then gives up."
updated = "2026-06-19T17:10:18.932Z"

[[record]]
name = "bootstrap_value_policy_targets"
file = "src/nn/labeling.py"
confidence = "settled"
rationale = "Each undecided non-terminal child gets a bootstrap policy target = its child's value (weight 0.2). If that action has >=10 descendants it ALSO gets a soft-negative 0.5^((desc+90)/100), weight 0.2. Both co-exist. All on the [0,1] win-prob scale."
updated = "2026-06-20T03:10:45.927Z"

[[record]]
name = "ability_learned_embedding"
file = "src/nn/spec.py"
confidence = "requirement"
rationale = "Abilities = 32-d learned nn.Embedding (vocab=all Ability), NOT effect-primitive decomposition (mapping too costly, failed loud on unmapped). Default std init per user. SPEC_VERSION=2; effect_primitives ABIL_* kept to keep N_PRIM stable."
updated = "2026-06-19T19:30:39.449Z"

[[record]]
name = "spawn_pool_cpu_workers"
file = "src/nn/parallel_label.py"
confidence = "settled"
rationale = "Label workers use a SPAWN pool (not fork: parent inits CUDA; fork-after-CUDA unsafe). Spawn also lets each worker init its own CUDA context, so NN forward runs on GPU when worker_device=cuda (label/train phases don't overlap). Weights via CPU ckpt."
updated = "2026-06-19T19:39:19.112Z"

[[record]]
name = "estimated_damage_rolls"
file = "src/nn/matchup.py"
confidence = "settled"
rationale = "Matchup-LOCAL fast path: 1 engine call for the factor-100 max roll (idx 15), other 15 estimated as max*(85+r)//100. ~17x fewer damage calls, ~1-2 HP error. queries/engine stay full-fidelity for search; only NN features estimate."
updated = "2026-06-19T19:39:19.001Z"

[[record]]
name = "closed_form_turns_to_ko"
file = "src/nn/matchup.py"
confidence = "settled"
rationale = "_turns_to_ko is closed-form: exact OHKO check then ceil(hp/net_loss), loss=damage minus eot residual. Toxic approximated as CONSTANT (toxic_turns+1)/16*max_hp (not its ramp) to keep the divisor constant; error small unless KO is slow."
updated = "2026-06-19T19:39:19.055Z"

[[record]]
name = "content_addressed_token_cache"
file = "src/nn/token_builder.py"
confidence = "settled"
rationale = "MonTokenCache memoizes per-mon tokens on (mon, is_active) content, mirroring NaiveMatchupCache. Bench mons are unchanged across nodes, so token_build drops ~11s to ~0.6s (98% hit). Threaded parallel to the matchup cache; off by default (None)."
updated = "2026-06-19T20:04:47.573Z"

[[record]]
name = "batched_worst_case_scoring"
file = "src/search/engine.py"
confidence = "settled"
rationale = "_worst_over/expand_node fork+advance all candidate leaves first, then score them in ONE heuristic.score_many call (NN forward batched per worst-case set). First-argmin worst pick preserved exactly. Heuristic-agnostic via getattr fallback to score."
updated = "2026-06-19T20:25:35.850Z"

[[record]]
name = "iterate_fresh_labels_only"
file = "src/nn/iterate.py"
confidence = "requirement"
rationale = "User: train ONLY on each round's fresh labels; no positive buffer, nothing persists between rounds. Positives AND negatives regenerate every round with the current model, so the value head sees balanced win/loss verdicts, not stale buffered wins."
updated = "2026-06-20T03:10:30.613Z"

[[record]]
name = "player_move_rules"
file = "src/nn/battle_gen.py"
confidence = "requirement"
rationale = "Player movesets: level-up moves at/below current level full weight, TM and tutor moves HALF weight, NO egg moves. Opponent gets ALL moves (level-up regardless of level, TM, tutor, egg) at full weight. User decision."
updated = "2026-06-20T20:23:28.094Z"

[[record]]
name = "natures_ivs"
file = "src/nn/battle_gen.py"
confidence = "requirement"
rationale = "Player random nature; opponent optimized nature (ADAMANT/JOLLY if physical, MODEST/TIMID if special, chosen via rng). IVs all 31 both sides. User decision."
updated = "2026-06-20T20:23:28.140Z"

[[record]]
name = "ability_rules"
file = "src/nn/battle_gen.py"
confidence = "requirement"
rationale = "Player draws only from NORMAL abilities (no hidden); opponent draws from normal+hidden. Ability JSON is structured {normal,hidden} to support this gating. User decision."
updated = "2026-06-20T20:23:28.226Z"

[[record]]
name = "difficulty_band_knob"
file = "src/nn/curriculum.py"
confidence = "requirement"
rationale = "Target a win-prob band (~0.35-0.65 centered, with tails) via the model's own value head. Anchor player team level; perturb ONLY opponent levels to hit the band. User decision."
updated = "2026-06-20T20:23:48.262Z"

[[record]]
name = "coverage_quota_hybrid"
file = "src/nn/curriculum.py"
confidence = "requirement"
rationale = "Cover ALL items/abilities/pokemon/moves on BOTH sides across all 9 luck tiers. Quota hybrid: when coverage conflicts with edge-difficulty, coverage wins (forced battle ignores band until quota met). User decision."
updated = "2026-06-20T20:23:48.307Z"

[[record]]
name = "item_rules"
file = "src/nn/battle_gen.py"
confidence = "requirement"
rationale = "Opponents ALWAYS hold an item; players 20% none. Pool restricted to items with real in-battle effect (battle berries, gems, standard battle items, Mega Stones on holder only); other species items excluded. GENERAL_ITEMS=122."
updated = "2026-06-20T20:23:52.174Z"

[[record]]
name = "controls_validated"
file = "src/nn/curriculum.py"
confidence = "settled"
rationale = "Stage 5 (SCRIPTS/validate_curriculum_difficulty.py): opp-level knob yields a monotonic difficulty gradient via the non-NN Greedy oracle (offset -20 wins at strictest tier; +20 wins ~37%, only at favorable tiers). Controls sound; no tuning needed."
updated = "2026-06-20T20:24:07.170Z"

[[record]]
name = "search_no_assume_max_trap"
file = "src/search/driver.py"
confidence = "settled"
rationale = "Search/stress uses random_mode live rollout + per-tier BAD/AVG/GOOD presets for forward planning, NOT observed reconciliation. So do NOT apply the sweep's assume-max trap-duration here; per-tier duration luck is correct for search."
updated = "2026-06-28T21:27:31.112Z"

## Retired gate test

[[record]]
name = "parity tripwire uses PINNED"
file = "tests/test_cpp_c17g_gate.py"
confidence = "settled"
rationale = "Parity tripwire must use a fully-PINNED LuckProfile, not SWEEP_LUCK. SWEEP_LUCK is warn-and-sample: uninjected Category-B rolls sample independently per engine, so py/cpp comparison surfaces RNG artifacts not port gaps."
updated = "2026-06-29T19:09:46.600Z"

## Superseded by C++ turn driver (Python Simulator class retired)

[[record]]
name = "proc_fires_shared_override"
file = "src/simulator.py"
confidence = "settled"
rationale = "PROC_FIRES has its own proc_threshold override field (split from SECONDARY_FIRES's secondary_threshold), so a move secondary and an ability/item proc inject different values in one action without colliding. _OVERRIDE_MAP gives each event a triple."
updated = "2026-06-14T05:35:32.741Z"

[[record]]
name = "slot_keyed_rng_override"
file = "src/simulator.py"
confidence = "settled"
rationale = "_get_profile(side, source_slot) accepts EVERY _OVERRIDE_MAP event (CRIT, DAMAGE_ROLL, SECONDARY_FIRES, PROC_FIRES, FLINCH, ACCURACY) as a scalar (singles path) OR a dict keyed by active-slot position, so each doubles slot injects its own value."
updated = "2026-06-14T05:35:52.593Z"

[[record]]
name = "slot_override_lazy_failloud"
file = "src/simulator.py"
confidence = "settled"
rationale = "Missing slot in a slot-keyed override: _get_profile omits it and drops the event from the strict injected set instead of raising. Fail-loud defers to resolve_crit/resolve_damage_roll, so status moves and queue probes at that slot don't false-fail."
updated = "2026-06-14T02:00:41.918Z"

[[record]]
name = "exp_part_postfaint_init"
file = "src/simulator.py"
confidence = "settled"
rationale = "start() post-faint path skips _begin_turn, so it must restore turn_ctx.exp_participants from state itself (else a player replacement drops historical EXP participants). Player switch-in preserves; opponent switch-in wipes its slot via _apply_switch."
updated = "2026-06-14T21:25:45.685Z"

[[record]]
name = "multi_hit_count_perslot"
file = "src/simulator.py"
confidence = "settled"
rationale = "The MULTI_HIT_COUNT override branch calls _resolve_slot so per-slot dict values dispatch by source_slot (scalars still pass through for singles). Without it, doubles two-multihit-mover turns could not carry distinct per-mover hit counts."
updated = "2026-06-17T17:58:15.028Z"

[[record]]
name = "trace-rollback-snapshot-pair"
file = "src/simulator.py"
confidence = "settled"
rationale = "TraceRecorder mark()/rollback() is tied 1:1 to _take_snapshot/_restore_snapshot: Cat-A pauses restore a snapshot and re-execute, so Cat-B draws from the aborted run must roll back or traces get phantom records. Keep the pairing if snapshots change."
updated = "2026-07-04T23:25:59.118Z"

[[record]]
name = "cat-a-record-at-b2-boundary"
file = "src/simulator.py"
confidence = "provisional"
rationale = "Cat-A oracle fallbacks (Tri Attack, Moody, Starf, Acupressure) stay unrewired; B2 records them at the oracle-answer boundary. B2's random driver must answer EFFECT_SPORE_WHICH with weights 11/10/9 (slp/par/psn, matches Showdown), NOT uniform."
updated = "2026-07-04T23:26:04.937Z"

[[record]]
name = "recorder_snapshot_random_state"
file = "src/simulator.py"
confidence = "settled"
rationale = "Cat-A pause snapshots MUST capture/restore random.getstate(): random_mode draws from the GLOBAL stream, so rollback+re-execution otherwise draws a different stream and can flip an answered proc, leaving stale answer records in golden traces."
updated = "2026-07-07T05:22:21.533Z"

[[record]]
name = "transient_oracle_injects_py"
file = "src/simulator.py"
confidence = "settled"
rationale = "Resume-injected Cat-A answers (_rng_inject) are TRANSIENT: cleared at region end (_clear_transient_injects), mirroring C++ oracle.h. Else the non-popping oracle reuses old answers for later same-event procs. pre_rng_inject stays persistent."
updated = "2026-07-07T05:22:38.546Z"

[[record]]
name = "sub_move_field_presence"
file = "src/simulator.py"
confidence = "settled"
rationale = "Sub-move phase (Metronome/Sleep Talk) must register exp_participants field presence itself: sub-move detection exits _advance_queue BEFORE the normal update. Mirrors C++ turn.cpp; gap caused a golden-trace fingerprint mismatch (exp_participants)."
updated = "2026-07-07T05:22:51.995Z"

[[record]]
name = "rng_inject_single_occurrence"
file = "src/simulator.py"
confidence = "settled"
rationale = "FIXED: transient Cat-A events (Effect Spore/Tri Attack/Acupressure/Moody/Starf) inject as per-event QUEUES; each answer consumed once, next same-event occurrence pauses for a fresh answer. Scalar injects (sweep pre-injects, SPEED_TIE) unchanged."
updated = "2026-07-07T17:56:31.818Z"

## Removed utilities

[[record]]
name = "opp_prob_print_module"
file = "src/opponent_probs.py"
confidence = "settled"
rationale = "_print_opponent_probs/_action_str live in standalone src/opponent_probs.py so the policy-agnostic turn loop (handle_battle_screen) prints opponent action probs EVERY turn, not just under greedy. Greedy no longer calls it (avoids double-print)."
updated = "2026-06-23T20:15:52.026Z"

[[record]]
name = "Cross-check threshold"
file = "src/calc_crosscheck.py"
confidence = "requirement"
rationale = "User spec: engine move-slot probs (renormalised over moves; switch/recharge dropped) vs syl-rnb-calc generateMoveDist; any per-slot abs diff > 0.01 dumps JSON and raises CrossCheckError (crash run). Skip boundaries with no voluntary opponent move."
updated = "2026-06-24T05:47:51.388Z"

[[record]]
name = "keep_sweep_capture_hook"
file = "src/engine/"
confidence = "settled"
rationale = "C1.7i removed the 4 sub-unit capture hooks (DAMAGE/EFFECTS/POSTHIT/RESIDUAL_CAPTURE). The NUZLOCKE_CAPTURE hook in engine_select.py is KEPT: it feeds the permanent c17g corpus. Do not delete it with the others."
updated = "2026-06-30T06:12:09.946Z"

