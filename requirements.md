[[record]]
name = "doubles_target_slot_simplified"
file = "src/ai.py"
confidence = "provisional"
rationale = "Doubles target-slot expansion duplicates MOVE actions (target_slot=1 at 50/50 probability share) but scores both against the same first opponent. Full per-target scoring needs _build_damage_context keyed by (move_slot, target_slot)."
updated = "2026-06-07T20:45:45.201Z"

[[record]]
name = "switch_candidate_bug"
file = "src/ai.py"
confidence = "requirement"
rationale = "Candidate validation bug: once a faster non-OHKOd bench mon is found, subsequent slower mons are also treated as valid. Replicates documented AI.md game behavior (_has_valid_switch_candidate)."
updated = "2026-06-07T20:45:53.621Z"

[[record]]
name = "stability_filter_design"
file = "liveplay/battle_message_matcher.py"
confidence = "requirement"
rationale = "Char-level prefix finalization, not Levenshtein stability. Pixel-exact OCR means intra-message variation is only typewriter growth. A pending frame is final iff its raw string is not a prefix of the next; flush() drains it at boundaries."
updated = "2026-06-13T21:40:39.199Z"

[[record]]
name = "stable_unmatched_raises"
file = "liveplay/battle_message_matcher.py"
confidence = "requirement"
rationale = "Stable raw text that matches no template raises UnknownMessageError; returning None would silently drop valid battle events."
updated = "2026-06-07T21:41:58.061Z"

[[record]]
name = "hp_stability_required_readings"
file = "liveplay/hp_stability.py"
confidence = "requirement"
rationale = "Three consecutive identical readings required to confirm a stable HP value; fewer tolerated too much OCR/animation noise."
updated = "2026-06-07T21:42:00.934Z"

[[record]]
name = "opponent_hp_as_k_pixel"
file = "liveplay/hp_stability.py"
confidence = "requirement"
rationale = "Opponent HP tracked as k-pixel (0–48) from bar pixel count; hp_range() converts to HP bounds for sweep validation since exact HP is not visible."
updated = "2026-06-07T21:42:00.984Z"

[[record]]
name = "unconstrained_move_name_flags"
file = "liveplay/battle_types.py"
confidence = "requirement"
rationale = "Constraints.unconstrained_moves bypasses move-name validation for Metronome/Assist; unconstrained_names bypasses species-name validation for Transform/Illusion."
updated = "2026-06-07T21:42:04.280Z"

[[record]]
name = "sweep_enumeration_design"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "_run_phase_loop enumerates an arbitrary-length mover list (partial turn=1, singles=2, doubles up to 4) one mover per iteration, carrying PartialCandidate survivors forward. Replaces the old fixed two-phase (first/second damage side) design."
updated = "2026-06-11T18:11:14.498Z"

[[record]]
name = "capture_interval_25hz"
file = "SCRIPTS/play.py"
confidence = "requirement"
rationale = "Capture runs at 25Hz (0.04s interval); user ruled 2026-07 the code is correct and the old 10fps record was stale. Stability filter deduplicates repeated frames so template matching only runs on newly stable text."
updated = "2026-07-08T19:13:35.697Z"

[[record]]
name = "sweep_save_on_failure"
file = "SCRIPTS/play.py"
confidence = "requirement"
rationale = "SimulationError/UninjectedRNGError still dumps JSON to /tmp/vision/sweep_errors/, then is FATAL: log the recording path and halt. A sweep with no survivors means invalid state; never continue playing."
updated = "2026-06-10T02:50:21.948Z"

[[record]]
name = "matcher_budget_scaling"
file = "liveplay/battle_message_matcher.py"
confidence = "requirement"
rationale = "Budget scales at ~20% of segment text length for lengths > 6 chars (max(3, word_len // 5)); OCR word-merging (e.g. 'teamis' for 'team is') inflates the segmented DP cost beyond the true string edit distance — for UNNERVESTART the true edit distance is ~5 (missing spaces) but the DP cost is 9 because the ENUM segment absorbs the merged token and the phrase must re-derive the lost characters."
updated = "2026-06-07"

[[record]]
name = "key_map_hardcoded_integers"
file = "SCRIPTS/mGBASocketServer.lua"
confidence = "settled"
rationale = "KEY_MAP uses GBA KEYINPUT bit positions (A=0..L=9) instead of C.GBA_KEY_* constants, which are nil in some mGBA builds."
updated = "2026-06-08T05:42:27.873Z"

[[record]]
name = "auto_play_gated_by_capture"
file = "SCRIPTS/play.py"
confidence = "requirement"
rationale = "Automated inputs (move selection and B-press text advance) are active only while capture_active is True; toggled via L or O (init_battle)."
updated = "2026-06-08T05:42:30.588Z"

[[record]]
name = "b_press_text_advance"
file = "SCRIPTS/play.py"
confidence = "requirement"
rationale = "While capture is active and not on a menu screen (last_screen_kind is None), press B twice per second to advance battle text boxes."
updated = "2026-06-08T05:42:33.664Z"

[[record]]
name = "Strict pixel template matching"
file = "liveplay/vision/"
confidence = "requirement"
rationale = "User decision: OCR matches font-bitmap templates by exact pixel equality (window must equal template, no extra or missing ink) — no IoU, threshold, or confidence scoring."
updated = "2026-06-09T11:44:40.858Z"

[[record]]
name = "No image scaling in OCR"
file = "liveplay/vision/"
confidence = "requirement"
rationale = "User decision: no upscaling or scale search; glyph templates are matched at native 1x GBA resolution."
updated = "2026-06-09T11:44:40.907Z"

[[record]]
name = "Lv prefix is one combined tile"
file = "liveplay/vision/font_matcher.py"
confidence = "settled"
rationale = "The 'Lv' level prefix is a single combined font tile (charmap LV=0x34), not separate 'L'+'v' glyphs; it must be loaded explicitly or level reads fail."
updated = "2026-06-09T11:44:41.007Z"

[[record]]
name = "Top-aligned exact crops"
file = "liveplay/vision/font_matcher.py"
confidence = "settled"
rationale = "Glyphs match top-aligned against fixed cell-anchored crops with no dynamic vertical search; first-ink-row detection misaligns on stray pixels and all-lowercase rows."
updated = "2026-06-09T11:44:50.180Z"

[[record]]
name = "Spaces from blank-run width"
file = "liveplay/vision/font_matcher.py"
confidence = "settled"
rationale = "The space glyph has zero ink and cannot be pixel-matched; a ' ' is emitted when the blank run between matched glyphs spans at least one space advance."
updated = "2026-06-09T11:44:50.230Z"

[[record]]
name = "Battle msg crop left margin"
file = "liveplay/vision/ocr.py"
confidence = "settled"
rationale = "Battle-message rows are cropped from x=4: the action-select prompt indents to x=5 (vs dialogue's x=12); a tighter left margin clips the prompt's leading capital glyph."
updated = "2026-06-09T11:44:50.282Z"

[[record]]
name = "Party prompt palette remap"
file = "liveplay/vision/ocr.py"
confidence = "settled"
rationale = "Party-menu 'Choose a POKéMON.' glyph core is (99,99,99) on light bg, outside the battle-message palette, so the standard binarizer reads empty. read_party_prompt remaps core to white, scans a small y-offset, keys on 'choose'+'pok' ('é' absent)."
updated = "2026-06-09T16:24:41.681Z"

[[record]]
name = "HP stability required=2"
file = "liveplay/hp_stability.py"
confidence = "requirement"
rationale = "User decision: PlayerHpBuffer and OpponentHpBuffer both require 2 consecutive identical readings. At ~7Hz the HP bar settles to its final value for at least 2 frames before the turn ends."
updated = "2026-06-09T17:28:41.876Z"

[[record]]
name = "accuracy_hit_injection"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Matcher injects ACCURACY only on an observed ATTACKMISSED (=False). A landed hit needs no injection: SWEEP_LUCK's silent default is hit. Old hit-side ACCURACY=True reconstruction removed; only visible failure messages drive injections."
updated = "2026-06-19T15:42:03.628Z"

[[record]]
name = "boundary_flight_recorder"
file = "liveplay/sweep_recorder.py"
confidence = "requirement"
rationale = "Record every sweep decision boundary live (inputs incl. candidates, then survivors or error) as fsynced pickles in /tmp/vision/recordings/<ts>/, one battle per session. Must survive hard crashes. Vision/OCR stays out; logs saved as-is."
updated = "2026-06-10T02:50:23.851Z"

[[record]]
name = "pickle_now_json_later"
file = "liveplay/sweep_recorder.py"
confidence = "requirement"
rationale = "Recordings use pickle; breakage of old recordings on BattleState refactors is accepted. Migrate to explicit JSON to/from-dict once the schema settles."
updated = "2026-06-10T02:50:25.334Z"

[[record]]
name = "strip_parent_candidate_links"
file = "liveplay/sweep_recorder.py"
confidence = "settled"
rationale = "Replace Candidate.parent_candidate with None before pickling; chains make boundary N pickle all ancestors (O(n^2) session size) and the field is compare=False so replay equality is unaffected."
updated = "2026-06-10T02:50:26.680Z"

[[record]]
name = "strict_sweep_no_silent_rng"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Sweep base SWEEP_LUCK=BAD_LUCK+warn_uninjected, thresholds tuned so every Category-B event defaults to its NO-message (silent) outcome: ACCURACY/PARALYSIS/ATTRACT/CONFUSION_SELF_HIT flipped to 0.0. Uninjected events log a WARNING, never raise."
updated = "2026-06-19T15:41:55.225Z"

[[record]]
name = "category_a_pauses_strict"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "_run_to_decision_boundary must not auto-answer Category-A pauses (Acupressure/Moody/Roar target etc.) with the first option during sweeps; un-pre-injected pauses raise UninjectedRNGError like any other silent default."
updated = "2026-06-10T02:50:37.518Z"

[[record]]
name = "strictness_in_luckprofile"
file = "liveplay/rng.py"
confidence = "settled"
rationale = "Strict mode = LuckProfile fields (strict, injected events, side); resolve_* raise after their deterministic guard clauses. Single choke point: engine code never threads strictness and acc>=100 etc. never raise since no RNG is consumed."
updated = "2026-06-10T02:50:53.912Z"

[[record]]
name = "secondary_vs_proc_fires"
file = "liveplay/rng.py"
confidence = "requirement"
rationale = "SECONDARY_FIRES is exclusively move secondaries; ability/item procs (Static, Effect Spore, Shed Skin, Focus Band, Protect chains...) use a distinct PROC_FIRES event so a move-secondary injection can never silently answer a proc roll."
updated = "2026-06-10T02:50:55.855Z"

[[record]]
name = "replay_imports_real_sweep"
file = "SCRIPTS/replay_sweep.py"
confidence = "requirement"
rationale = "Replay must call the real run_candidate_sweep via src/sweep_recorder.py; no copied sweep logic in the script (a copy would diverge and be worthless). Per-boundary PASS/FAIL with state diffs; exit 0 iff all selected boundaries pass."
updated = "2026-06-10T02:50:57.595Z"

[[record]]
name = "proc_fires_shared_override"
file = "src/simulator.py"
confidence = "settled"
rationale = "PROC_FIRES has its own proc_threshold override field (split from SECONDARY_FIRES's secondary_threshold), so a move secondary and an ability/item proc inject different values in one action without colliding. _OVERRIDE_MAP gives each event a triple."
updated = "2026-06-14T05:35:32.741Z"

[[record]]
name = "mover_list_no_fallback"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "_build_mover_list returns the observed USEDMOVE side order verbatim; with no observed USEDMOVE it returns [] and the sweep yields no candidates (SimulationError), never falling back to a guessed mover order."
updated = "2026-06-11T18:11:21.081Z"

[[record]]
name = "sweep_own_damage_dedup"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Single-hit movers dedup their 16 rolls by the mover's OWN damage (_own_damage keyed on attacker_side/slot), not cumulative damage to the target. Maximizes per-attack granularity and shrinks the candidate space."
updated = "2026-06-11T18:11:21.120Z"

[[record]]
name = "rng_sequence_interleaved"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Candidate.rng_sequence is interleaved per mover: (DAMAGE_ROLL, roll),(CRIT, crit) for each mover in observed order, then a trailing (SPEED_TIE). Every mover gets a pair (even non-damaging); multi-hit movers' entries are per-hit tuples."
updated = "2026-06-11T18:11:21.159Z"

[[record]]
name = "multi_hit_in_loop"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Movers enumerated by ONE unified fn _enumerate_mover_rolls (single-hit=n_hits 1, multi-hit=n_hits>1), inside the mover loop at the acting iteration via a PartialCandidate (not a separate phase). apply_hp_prune (n_hits>1 only) gates HP-delta pruning."
updated = "2026-06-17T15:49:49.895Z"

[[record]]
name = "crit_attribution_by_message"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Crits are attributed per-mover by which USEDMOVE directly preceded each CRITICALHIT message (_message_crit_counts_with_state), not a global count by position. Multi-hit moves use their own attributed count for which-hit enumeration."
updated = "2026-06-11T18:11:36.963Z"

[[record]]
name = "post_faint_empty_mover_branch"
file = "src/simulation_runner.py"
confidence = "provisional"
rationale = "When movers==[] and an active Pokemon has fainted, run_candidate_sweep runs one sim per action pair directly (no roll/crit enumeration, tie_winner=0) since a bare switch has no controllable RNG. Limitations tracked in TODO 2c."
updated = "2026-06-11T18:11:37.000Z"

[[record]]
name = "damage_event_attacker_identity"
file = "src/engine/core.py"
confidence = "settled"
rationale = "Move-source LogEvent.DAMAGE records attacker_side and attacker_slot so the sweep can attribute damage to the specific attacking mover (own-damage dedup), independent of the target's species."
updated = "2026-06-11T18:11:37.038Z"

[[record]]
name = "literal-coverage fallback"
file = "liveplay/battle_message_matcher.py"
confidence = "requirement"
rationale = "If the score-winner explains <0.30 of OCR words via literal/enum segments, _try_full_match re-picks the highest-coverage aligner (tie-break: score, literal_count, context). Stops var-greedy templates winning on garbled OCR. 0.30 adjustable."
updated = "2026-06-13T17:50:59.963Z"

[[record]]
name = "opp_switch_not_boundary"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Opponent faint+replacement is NOT a player decision boundary. Sweep auto-applies observed opponent switch-ins (ordered list, one per faint round, doubles-ready); stops only on player battle menu (AWAIT_ACTIONS) or party-select (switches_needed[0])."
updated = "2026-06-13T18:34:45.665Z"

[[record]]
name = "uninjected_rng_filters_cand"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "UninjectedRNGError in _run_to_decision_boundary filters the candidate (return None + log once) instead of aborting the sweep: it means the branch diverged from observed reality. All-filtered still raises the no-candidate SimulationError."
updated = "2026-06-13T18:52:34.861Z"

[[record]]
name = "ellipsis_stripped_at_parse"
file = "liveplay/battle_message_matcher.py"
confidence = "requirement"
rationale = "Strip ellipsis ('…' and ASCII runs of 2+ dots) from templates in _parse and from OCR in _preprocess_ocr. A trailing ellipsis otherwise becomes a required phrase segment that OCR rarely captures, so no-ellipsis messages fail to match."
updated = "2026-06-13T19:08:50.090Z"

[[record]]
name = "phrase_window_plus_one"
file = "liveplay/battle_message_matcher.py"
confidence = "requirement"
rationale = "Phrase segments may consume up to max_words+1 OCR words (not just len(tokens)). Absorbs one intra-phrase OCR token split (e.g. dropped apostrophe: 'doesn't'->'doesn' 't'). The char edit budget still gates quality, so the wider word window stays safe."
updated = "2026-06-13T19:08:54.076Z"

[[record]]
name = "midturn_paralysis_injection"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Matcher injects FULL_PARALYSIS only on an observed PKMNISPARALYZED message (=False, fully paralyzed). A mon that acted needs no injection: SWEEP_LUCK's silent default is can-act. Old can-act (=True) reconstruction for used/paralyzed slots removed."
updated = "2026-06-19T15:42:12.051Z"

[[record]]
name = "active_opp_klog_selection"
file = "SCRIPTS/play.py"
confidence = "requirement"
rationale = "Sweep reads the ACTIVE opponent's k-pixel HP log by name, not next(iter(opp_k_logs)). Stale entries for fainted/switched-out mons else yield empty deltas. Lookup: exact (lowercased species name), then fuzzy (Levenshtein <= max(2,len//4)), else raise."
updated = "2026-06-13T19:24:43.478Z"

[[record]]
name = "match_text first-col prune"
file = "liveplay/vision/font_matcher.py"
confidence = "settled"
rationale = "match_text prunes glyph candidates by template column-0 ink count (cheap necessary condition) before full pixel-equality, and precomputes template sums; ~15x faster, bit-identical. Preserves insertion order so first-font/first-candidate still wins."
updated = "2026-06-13T20:05:03.934Z"

[[record]]
name = "No trainer item messages"
file = "liveplay/battle_message_matcher.py"
confidence = "requirement"
rationale = "User decision: trainers cannot use battle items in Run & Bun, so item-use templates (STRINGID_PLAYERUSEDITEM etc.) were removed. 'Trainer used <item>!' correctly fails as no_template_match; do not re-add item templates or valid_items."
updated = "2026-06-13T20:19:38.423Z"

[[record]]
name = "forced_replace_not_action"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "_extract_known_actions pairs each faint with the next same-side switch-in (pending_faint counters) and skips it: forced post-faint replacements go via opp_switch_actions, not as actions. Counting twice withdrew the doomed mon pre-faint. Doubles-safe."
updated = "2026-06-13T22:59:56.371Z"

[[record]]
name = "multihit_per_hit_sampling"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Multi-hit damage discovery samples each hit alone: vary hit i's roll, pin others to min roll so target survives for hit i. Uniform rolls KO early, drop the count, and hide higher per-hit damage. Damage is HP-independent, so isolated rolls recombine."
updated = "2026-06-13T23:06:29.308Z"

[[record]]
name = "multihit_ko_overkill"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Multi-hit cumulative HP-delta filter: a KO reading (new_val==0) drops the upper bound since the killing blow may overkill; only the lower bound (damage reaches 0) applies. Applies to BOTH opponent pixel-range and player exact-HP branches."
updated = "2026-06-13T23:12:03.777Z"

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
name = "movers_side_slot_tuples"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "movers is list[tuple[int,int]] of (side, source_slot) in execution order, index-aligned with per-mover rolls/crits/hit_counts. source_slot is the acting active-slot position, inferred from USEDMOVE order via _message_action_order_with_state."
updated = "2026-06-14T02:00:47.943Z"

[[record]]
name = "target_slot_from_deltas"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Doubles target inference: a single-target damaging move's target_slot is constrained to the foe slots that lost HP (turn-order matched). No damage calc; wrong assignments are filtered by the per-slot HP check and fail loud if none survive."
updated = "2026-06-14T02:00:53.678Z"

[[record]]
name = "per_mover_multi_hit"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Supports two multi-hit movers in one doubles turn: mover_hit_counts is a per-mover list[int] index-aligned with movers; entries >1 trigger _enumerate_multi_hit_rolls for that mover. Spread+multi-hit combined is deferred and fails loud."
updated = "2026-06-14T02:00:53.720Z"

[[record]]
name = "doubles_secondary_single_move"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "GAP CLOSED: secondaries are attributed per (side, slot). Messages are segmented by USEDMOVE (names user to source_slot) and effects attributed to the recipient named in the effect message; SECONDARY_FIRES/PROC_FIRES injected as per-slot dicts."
updated = "2026-06-14T05:35:59.434Z"

[[record]]
name = "flinch_via_secondary_fires"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "All move-flinch (flinch-only secondaries and Fang secondary2) resolves via RNGEvent.FLINCH (attacker luck), not SECONDARY_FIRES; forced on hitter slot if observed, else enumerated under FLINCH. SECONDARY_FIRES=status/stat/confusion only."
updated = "2026-06-15T19:40:22.695Z"

[[record]]
name = "action_order_from_move_use"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "_check_action_order compares observed USEDMOVE order against the side sequence of captured MOVE_USE events, NOT state.turn_order. turn_order includes mons slated to act but that never moved (flinch/para/sleep), mismatching mid-order in doubles."
updated = "2026-06-14T05:36:33.554Z"

[[record]]
name = "proc_injection_from_by_msg"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Ability/item procs (Static etc.) are injected from PKMNWAS*BY status messages: the afflicted name is the LAST var_value (layout [source, ability, target]). PROC_FIRES is forced per-slot on the afflicted target (the attacker for contact-punish)."
updated = "2026-06-14T05:36:44.352Z"

[[record]]
name = "secondary_combo_no_cap"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "No cap on flinch combo count: old guard removed, total combo count printed. Flinch combos keyed per (side, slot, RNGEvent.FLINCH) over non-attributable (flinch-only) movers, excluding slots already force-injected from an observed flinch."
updated = "2026-06-15T19:40:36.221Z"

[[record]]
name = "move_use_logs_side"
file = "src/engine/core.py"
confidence = "settled"
rationale = "LogEvent.MOVE_USE records side=side_idx so the sweep can reconstruct the move-execution order (which mons actually moved) without consulting state.turn_order. Subset-matching consumers (CapturingLogger.fired/all_of) are unaffected by the extra kwarg."
updated = "2026-06-14T05:37:04.643Z"

[[record]]
name = "proc_threshold_field"
file = "liveplay/rng.py"
confidence = "settled"
rationale = "LuckProfile has a distinct proc_threshold field (separate from secondary_threshold): resolve_proc reads proc_threshold, resolve_secondary reads secondary_threshold. GOOD=0.0, BAD=101.0, AVERAGE=50.0, so secondaries and procs roll independently."
updated = "2026-06-14T05:37:59.229Z"

[[record]]
name = "joined_trainer_pair_validation"
file = "liveplay/battle_message_matcher.py"
confidence = "settled"
rationale = "Adjacent (TRAINER_CLASS, TRAINER_NAME) VARs validate as one joined 'Class Name' span (vs constraint, else TRAINER_NAMES). The DP split between the two zero-cost VARs is arbitrary, so multi-word classes (e.g. 'Team Aqua') fail per-VAR checks."
updated = "2026-06-14T06:04:12.635Z"

[[record]]
name = "trainer_name_strip_annotations"
file = "SCRIPTS/play.py"
confidence = "settled"
rationale = "Trainer pkl names carry Run & Bun annotations ([Boss],[Double],[Double Battle With ...]) absent in-game; _split_trainer_name strips trailing [...] before class/name split so the constraint rejoins to the intro display text."
updated = "2026-06-14T06:25:44.830Z"

[[record]]
name = "battle_msg_e_accent_in_charset"
file = "liveplay/vision/ocr.py"
confidence = "settled"
rationale = "_ALPHA_NUM_CHARS includes 'é' so battle messages read 'POKéMON' whole (the é glyph template exists). 24 templates use literal é; do not normalize é to e."
updated = "2026-06-14T06:25:49.417Z"

[[record]]
name = "choose_pokemon_prompt_signal"
file = "liveplay/battle_message_matcher.py"
confidence = "settled"
rationale = "Forced-replacement 'Choose a POKéMON.' prompt (normal palette, no Cancel) reaches the matcher as a battle message with no template; _is_choose_pokemon_prompt returns a PARTY_MENU signal to avoid a spurious UnknownMessageError. Keys on 'choose'+'pok'."
updated = "2026-06-14T06:26:01.681Z"

[[record]]
name = "do_what_with_mon_template"
file = "liveplay/battle_messages.py"
confidence = "settled"
rationale = "Synthetic non-primary template 'Do what with this ?' (STRINGID_DOWHATWITHMON) for the party-menu action submenu. Its literal 'PKMN' glyph uses a non-standard font that never OCRs, so it matches var-less and is ignored, not raised."
updated = "2026-06-14T06:35:51.573Z"

[[record]]
name = "confusion_selfhit_midturn"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Matcher injects CONFUSION_SELF_HIT only on an observed ITHURTCONFUSION message (=False, self-hit). SWEEP_LUCK's silent default is no self-hit, so a confused mon that acted needs no injection. Old PKMNISCONFUSED-keyed no-self-hit reconstruction gone."
updated = "2026-06-19T15:42:38.539Z"

[[record]]
name = "fuzzy_find_side_active_first"
file = "liveplay/state_transition.py"
confidence = "settled"
rationale = "_fuzzy_find_side matches ACTIVE mons first (an attacker is always active), so a benched duplicate can't steal a name belonging to the other side's active. side_hint (Foe prefix: 1=opp,0=player) breaks mirror ties; else full-team scan."
updated = "2026-06-14T14:34:03.431Z"

[[record]]
name = "matchresult_side_hint"
file = "liveplay/battle_message_matcher.py"
confidence = "settled"
rationale = "MatchResult.side_hint = side of var_values[0] from the Foe prefix (1=opp Foe-prefixed, 0=player, None if slot0 isn't a Pokemon name). Surfaces the prefix (consumed as a literal token) so _fuzzy_find_side can disambiguate mirror matches."
updated = "2026-06-14T14:34:07.286Z"

[[record]]
name = "number_slot_ocr_digit_norm"
file = "liveplay/battle_message_matcher.py"
confidence = "settled"
rationale = "NUMBER-category VAR validation/canonicalization normalizes OCR letter->digit confusions (O/o/Q/D->0, I/l/|/i->1, Z->2, S->5, G->6, T->7, B->8) so values like '6O' read as '60'. Safe: a NUMBER slot only appears inside an already-matched template."
updated = "2026-06-14T15:01:54.471Z"

[[record]]
name = "warn_uninjected_guard"
file = "liveplay/rng.py"
confidence = "settled"
rationale = "_strict_check tri-mode: strict raises; warn_uninjected logs a WARNING and returns True (caller falls to the profile threshold default) uniformly for ALL events including ACCURACY. No per-event raise exceptions; silent defaults encoded via thresholds."
updated = "2026-06-19T15:41:49.772Z"

[[record]]
name = "stat_direction_literal_tmpl"
file = "liveplay/battle_message_matcher.py"
confidence = "settled"
rationale = "Stat-direction phrases (sharply rose!/harshly fell!) are literal template text via _LITERAL_DIRECTION_OVERRIDES, not an extracted B_BUFF2 var: multi-word phrases with detached '!' exceed enum max_words. Stat name stays enum; +1/+2 share string_id."
updated = "2026-06-14T16:18:17.209Z"

[[record]]
name = "mirror_damage_side_aware"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "_sum_damage/_per_hit_damages take target_side, filtering DAMAGE events by defender_side (a kwarg on move-damage emissions). Species-only matching conflated mirror actives: a foe's hit on the player counted as opponent damage, pruning all candidates."
updated = "2026-06-14T16:33:51.576Z"

[[record]]
name = "menu_rejection_phantom_turn"
file = "liveplay/battle_constants.py"
confidence = "settled"
rationale = "turn_has_real_action()/MENU_REJECTION_STRING_IDS detect phantom turns: a move-select rejection (no PP/disabled/taunt/torment/sealed) makes the menu vanish then reappear, faking a turn. play.py skips the sweep when a turn holds only these."
updated = "2026-06-14T17:11:56.920Z"

[[record]]
name = "proc_fires_attacker_side"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Contact ability procs (_PROC_STATUS_BY_IDS) inject PROC_FIRES on the most-recent move user (attacker), whose luck_atk the roll consumes - not the afflicted mon. Fixes Poison Touch (afflicts defender) pruning all candidates; contact-punish unaffected."
updated = "2026-06-14T17:48:39.726Z"

[[record]]
name = "move_select_timing"
file = "liveplay/emulator/battle_input.py"
confidence = "requirement"
rationale = "Move-selection inputs are deliberately slow: wait 0.5s after entering the FIGHT menu (_FIGHT_OPEN_WAIT) and 0.3s between each directional nav press (_NAV_GAP, shared with party-menu nav); nav keys held ~0.1s (_NAV_HOLD) for JOY_NEW edge detection."
updated = "2026-06-15T04:45:20.202Z"

[[record]]
name = "key_press_no_sleep"
file = "liveplay/emulator/battle_input.py"
confidence = "settled"
rationale = "add_key/clear_key with no sleep: TCP round-trip to Lua frame callback (~17ms at 60fps) gives game one frame to register. tap() must not be used inside the frame callback (it calls emu:runFrame(), causing a recursive crash)."
updated = "2026-06-14T19:08:24.247Z"

[[record]]
name = "move_select_input"
file = "liveplay/emulator/battle_input.py"
confidence = "requirement"
rationale = "OPTION_SELECT move: press A (Fight), normalize cursor to (0,0) via UP+LEFT, navigate to slot row/col, press A. Slot = active mon's move_ids index of the policy-chosen Move. No grid wrapping; cursor persists between turns."
updated = "2026-06-14T19:08:45.246Z"

[[record]]
name = "party_select_by_name"
file = "liveplay/emulator/battle_input.py"
confidence = "requirement"
rationale = "Party members are matched by species name, not slot index: emulator reorders slots on switch so indices desync from the sim's team[]. Nuzlocke rules guarantee no duplicate species, so name match is unambiguous."
updated = "2026-06-14T19:08:52.484Z"

[[record]]
name = "fuzzy_name_match"
file = "liveplay/emulator/battle_input.py"
confidence = "provisional"
rationale = "OCR party names matched to species via exact normalized compare, then Levenshtein fallback within max(2, len//4). Fuzzy chosen for now since the viable name set is small; revisit if mismatches occur."
updated = "2026-06-14T19:08:52.537Z"

[[record]]
name = "voluntary_switch_flow"
file = "liveplay/emulator/battle_input.py"
confidence = "requirement"
rationale = "Voluntary switch from battle menu: press DOWN (Fight->Pokemon), A, then select chosen species (the PARTY_MENU handler's 1s fade-in wait covers menu load). pending_switch_ref distinguishes voluntary (species pre-chosen) from forced at PARTY_MENU."
updated = "2026-06-14T19:16:41.840Z"

[[record]]
name = "default_policy_80_20"
file = "liveplay/battle_policy.py"
confidence = "requirement"
rationale = "RandomPolicy default: 80% use a move, 20% voluntarily switch (only if a non-active non-fainted bench mon exists), uniform within each category. Falls back to the only available category when one is empty; raises if both empty."
updated = "2026-06-14T19:09:02.530Z"

[[record]]
name = "exclude_zero_pp_moves"
file = "liveplay/battle_policy.py"
confidence = "requirement"
rationale = "available_moves excludes Move.NONE and 0-PP moves. Battle state is assumed perfect (no uncertainty modeling); switch targets are non-active, non-fainted, HP>0 team members."
updated = "2026-06-14T19:09:02.582Z"

[[record]]
name = "two_endpoint_policy"
file = "liveplay/battle_policy.py"
confidence = "requirement"
rationale = "BattlePolicy has two endpoints: choose_battle_action (battle menu) returns a Move OR species name (voluntary switch decided up front); choose_forced_switch (party menu) returns a species name. Two decision locations => two injectable callables."
updated = "2026-06-14T19:09:07.693Z"

[[record]]
name = "hp_deltas_identity_bound"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Sweep validates HP deltas by mon IDENTITY, not slot. run_candidate_sweep takes hp_deltas: list[HpDeltaSeq] binding (before,after) to (side,species). _check_hp_match resolves species vs result-state team (follows switches); raises if unknown/dup."
updated = "2026-06-14T21:04:15.491Z"

[[record]]
name = "exp_part_postfaint_init"
file = "src/simulator.py"
confidence = "settled"
rationale = "start() post-faint path skips _begin_turn, so it must restore turn_ctx.exp_participants from state itself (else a player replacement drops historical EXP participants). Player switch-in preserves; opponent switch-in wipes its slot via _apply_switch."
updated = "2026-06-14T21:25:45.685Z"

[[record]]
name = "tib_counts_initiators"
file = "src/engine/residuals.py"
confidence = "settled"
rationale = "turns_in_battle increments at end of turn ONLY for mons active at turn start (ctx.turn_start_active, set in _begin_turn). Mid-turn switch-ins skip the entry turn, so Fake Out/Mat Block/Speed Boost fire on first INITIATED turn. ctx unset => count all."
updated = "2026-06-14T21:52:37.187Z"

[[record]]
name = "multihit_stops_on_atk_faint"
file = "src/engine/core.py"
confidence = "settled"
rationale = "Multi-hit moves end if the attacker faints mid-sequence (e.g. contact recoil like Rough Skin/Rocky Helmet), matching the game's 'Hit N time(s)!' count. Loop breaks on attacker.fainted."
updated = "2026-06-14T22:26:54.803Z"

[[record]]
name = "miss_still_acted_inject"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Matcher injects only VISIBLE failure outcomes; a used move that hit or missed needs no can-act injection. SWEEP_LUCK silent-defaults para/attract/confusion to can-act and accuracy to hit, so acted/missed mons fall through without injection."
updated = "2026-06-19T15:42:33.246Z"

[[record]]
name = "confusion_apply_keys_became"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "check_log_events confusion VOLATILE_APPLY constraint keys on STRINGID_PKMNWASCONFUSED ('became confused!'), not PKMNISCONFUSED ('is confused!', per-turn reminder). The reminder fires every turn a confused mon acts; keying on it pruned all candidates."
updated = "2026-06-14T23:01:19.236Z"

[[record]]
name = "trust_observed_levelups"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Sweep trusts OCR PKMNGREWTOLV: level-up check requires sim levels be a sub-multiset of observed (tolerates low live-seed extras, prunes sim-invented); _apply_observed_levelups forces player mons up to observed level so carried state stays consistent."
updated = "2026-06-15T00:38:29.342Z"

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
name = "stress_failure_outcome"
file = "SCRIPTS/stress_test.py"
confidence = "requirement"
rationale = "A team that cannot win the position (no winning luck tier) raises TeamFailureError, recorded as the FAILURE outcome; unlike other non-OK outcomes the loop continues so the run isn't aborted."
updated = "2026-06-15T05:01:22.877Z"

[[record]]
name = "converter_int_slot"
file = "src/search/driver.py"
confidence = "requirement"
rationale = "Switch phases (forced/post-faint) return best_action as a plain int bench slot, not an Action (search/engine.py). action_to_move_or_species must handle the int case (-> team[int].species.name), as choose_forced_switch relies on it."
updated = "2026-06-15T05:23:19.798Z"

[[record]]
name = "psywave_injectable_roll"
file = "src/engine/core.py"
confidence = "settled"
rationale = "Psywave damage uses injectable RNGEvent.PSYWAVE_ROLL (0..1) mapped to 50+round(r*100) pct of level damage, mirroring DAMAGE_ROLL; _compute_fixed_damage takes luck_atk. Sweep mirrors s.roll into PSYWAVE_ROLL so its range enumerates like normal damage."
updated = "2026-06-15T19:40:54.323Z"

[[record]]
name = "fixed_damage_attacker_identity"
file = "src/engine/core.py"
confidence = "settled"
rationale = "Fixed-damage DAMAGE logs (Psywave/Counter/Dragon Rage etc.) carry attacker_side/attacker_slot so _own_damage() attributes them; without it all fixed-damage rolls dedup to one and the sweep cannot distinguish candidates."
updated = "2026-06-15T19:40:59.063Z"

[[record]]
name = "active_opp_name_fail_loud"
file = "SCRIPTS/play.py"
confidence = "requirement"
rationale = "_active_opp_name raises RuntimeError on genuine opponent desync (non-empty active_indices but opp_active>=len(team)) instead of a silent max_hp=1 fallback. Empty active_indices (pre-battle) still maps to slot 0. Fail-loud per design."
updated = "2026-06-15T19:41:05.130Z"

[[record]]
name = "record_and_run_catch_all"
file = "liveplay/sweep_recorder.py"
confidence = "requirement"
rationale = "record_and_run catches Exception (not just SimulationError/UninjectedRNGError) so every sweep failure drops an .error.pkl; record-then-reraise contract unchanged. Orphan input.pkl with no output/error pkl => uncaught hard crash."
updated = "2026-06-15T19:41:05.175Z"

[[record]]
name = "typeless_sentinel"
file = "liveplay/data/types.py"
confidence = "settled"
rationale = "Type.TYPELESS (=18) is the single sentinel for typelessness on both axes (attacker and defender), mirroring Showdown '???'. Chart is 19x19 so TYPELESS row/column are always 1.0x. TYPELESS never gets STAB. Distinct from Roost (pure-Flying->NORMAL)."
updated = "2026-06-15T20:23:06.133Z"

[[record]]
name = "species_min_one_type"
file = "liveplay/data/species.py"
confidence = "requirement"
rationale = "Every SPECIES_DATA row must have >=1 valid Type; validated at import time (raises ValueError naming the species). Zero-type is a data bug, not a runtime state; legitimate type loss (Burn Up mono-Fire) uses Type.TYPELESS instead of an empty tuple."
updated = "2026-06-15T20:23:06.187Z"

[[record]]
name = "burn_up_drops_fire"
file = "src/engine/post_hit.py"
confidence = "requirement"
rationale = "Burn Up drops the Fire type entirely (dual-type keeps remaining types; mono-Fire becomes (Type.TYPELESS,), never NORMAL). Emits LogEvent.TYPE_CHANGE source=burn_up with old/new types. (user decisions 2026-06-15)"
updated = "2026-06-15T20:23:10.124Z"

[[record]]
name = "dynamic_turn_queue"
file = "src/engine/core.py"
confidence = "settled"
rationale = "Turn order is dynamic: after each action the next un-acted actor is re-selected via _select_next_action, recomputing priority bracket + speed from current state (Showdown speedSort). turn_order appended incrementally; QC/Custap resolved at build."
updated = "2026-06-15T22:11:08.992Z"

[[record]]
name = "quick_claw_dedicated_event"
file = "src/engine/core.py"
confidence = "settled"
rationale = "Quick Claw uses RNGEvent.QUICK_CLAW + quick_claw_threshold (resolve_quick_claw, 20%), decoupled from secondary_threshold. On proc bumps holder to front-of-bracket (speed=9999), gated priority<=0, emits QUICK_CLAW_ACTIVATE. Custap stays deterministic."
updated = "2026-06-15T22:11:29.249Z"

[[record]]
name = "quick_claw_observed_pinning"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Quick Claw observed via STRINGID_QUICKCLAWACTIVATE: pin QUICK_CLAW=True per holder slot when seen, else False for QC holders that used a priority<=0 move with no QC message (always shown on proc). Keyed on used-priority0 slots only. No enumeration."
updated = "2026-06-15T22:11:47.849Z"

[[record]]
name = "struggle_recoil"
file = "src/engine/post_hit.py"
confidence = "requirement"
rationale = "Struggle recoil = max(1, user.max_hp//4), a dedicated post_hit branch (MOVE_DATA recoil stays None). Magic Guard blocks it; Rock Head does NOT (matches Showdown struggleRecoil). Logged DAMAGE source=recoil. (user decisions 2026-06-15)"
updated = "2026-06-15T22:41:00.571Z"

[[record]]
name = "battle_start_sendout_forced"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "_extract_known_actions skips both sides' send-outs when STRINGID_INTROMSG is in the batch: opening lead-ins are forced, not voluntary. Recording them tripped the opponent-action filter (switch p=0 vs move preds) and crashed the sweep."
updated = "2026-06-16T17:21:47.081Z"

[[record]]
name = "hitcount_side_attrib"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "HITXTIMES count filters HITCOUNT by attacker SIDE (USEDMOVE 'Foe' prefix via _msg_is_foe), not species alone; species-only conflated both mons in same-species mirrors. core.py logs HITCOUNT with side=side_idx."
updated = "2026-06-16T17:21:51.466Z"

[[record]]
name = "opp_action_filter"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "_validate_known_opponent_action filters a candidate if an OCR-identified opponent action had p=0 in compute_action_probabilities (per-candidate UnexpectedOpponentActionError; all-filtered => no survivors). Surfaces AI prediction gaps as crashes."
updated = "2026-06-16T17:21:55.172Z"

[[record]]
name = "battle_start_no_enum"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Opening sweep (STRINGID_INTROMSG) short-circuits: neither side acted, so emit each lead state unchanged as one child candidate, no enumeration/sim. Enumeration invented opponent switch->bench branches that diverged observed active, crashing sweep."
updated = "2026-06-16T18:05:03.585Z"

[[record]]
name = "multi_hit_aware_damage"
file = "src/queries.py"
confidence = "requirement"
rationale = "Query+AI KO/damage decisions must use expected_damage (multi-hit aware), not single-hit calculate_damage; calculate_damage stays single-hit for the engine's per-hit loop. Undercounting Double Slap made the AI mispredict and crash the sweep."
updated = "2026-06-16T18:47:39.773Z"

[[record]]
name = "setup_routing_self_only"
file = "src/ai.py"
confidence = "requirement"
rationale = "Offensive-setup scoring (_dist_setup via SETUP+STATUS tag) only applies to target==SELF moves. Opponent-targeting moves (Swagger, Flatter, Curse, Decorate) are confusion/debuffs, not self-buffs; routing them as setup gave p=0 and crashed the sweep."
updated = "2026-06-16T19:16:00.953Z"

[[record]]
name = "kill_bonus_joint_highest"
file = "src/ai.py"
confidence = "requirement"
rationale = "KO bonus is computed jointly with highest-damage odds on the same damage roll (correlated), using uncapped damage for KO. Kill bonus applies only when the move is also highest-damage. Replaces the buggy max-roll guaranteed-kill flag."
updated = "2026-06-16T20:43:40.476Z"

[[record]]
name = "belch_excluded_from_rank"
file = "src/ai.py"
confidence = "requirement"
rationale = "Belch is skipped in _build_damage_context when consumed_berry==NONE (unusable per engine core.py:1571), so it falls to the status-branch scorer instead of being ranked at 120 BP and predicted as the opponent's move."
updated = "2026-06-16T22:58:54.286Z"

[[record]]
name = "analytical_joint_roll_enum"
file = "src/ai.py"
confidence = "settled"
rationale = "compute_action_probabilities enumerates all 16^m damage-roll combos using the same capped-rank/uncapped-kill formula as _sample_highest_slots, so analytical and sim paths agree. Co-highest moves share p_highest; switches excluded from enumeration."
updated = "2026-06-16T22:59:02.482Z"

[[record]]
name = "voluntary_switch_single_tgt"
file = "src/ai.py"
confidence = "requirement"
rationale = "Voluntary switch gives the full 0.5 to ONE Cond2-filtered post-KO target (not split across benches); switches get 0 otherwise. HP gate is >=50% (not strict >). Target selection replicates the found_faster Cond2 bug."
updated = "2026-06-16T22:59:03.927Z"

[[record]]
name = "forced_switch_post_ko_check"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Forced post-faint opponent switch-ins (fainted active) skip the beginning-of-turn compute_action_probabilities check; _validate_forced_opponent_switch strictly asserts send-out equals select_post_ko_switch (singles only)."
updated = "2026-06-16T23:35:08.189Z"

[[record]]
name = "per_roll_damage_index_override"
file = "src/engine/damage.py"
confidence = "settled"
rationale = "calculate_damage takes opt-in roll_index (0..15) for an exact roll; roll applied before STAB/type with flooring, so per-roll damage is nonlinear (Wing Attack 8x15 then 12), not a linear rescale of max. Default callers unchanged."
updated = "2026-06-17T01:23:54.357Z"

[[record]]
name = "ai_true_per_roll_damage"
file = "src/ai.py"
confidence = "settled"
rationale = "AI scoring uses true 16-element per-roll damage arrays from damage_roll_values, not max_damage*(85+r)//100 rescale. The old rescale collapsed low rolls upward, hiding marginal-KO branches and giving status moves p=0 (crashed sweeps)."
updated = "2026-06-17T01:23:58.855Z"

[[record]]
name = "harvest_proc_side_hint"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "HARVESTADDITEM message forces harvester PROC_FIRES=True so the berry-restored (item present) candidate survives the sweep; uses side_hint to disambiguate mirror species."
updated = "2026-06-17T04:08:25.765Z"

[[record]]
name = "party_match_strips_form_suffix"
file = "liveplay/emulator/battle_input.py"
confidence = "settled"
rationale = "find_member_by_name strips regional/form suffixes (_GALAR/_ALOLA/_HISUI/_PALDEA/_GMAX/_MEGA*) before fuzzy-matching, since the in-game party menu shows the base species name."
updated = "2026-06-17T05:13:36.977Z"

[[record]]
name = "attract_midturn_can_act"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Matcher injects ATTRACT_IMMOBILIZE only on an observed PKMNIMMOBILIZEDBYLOVE message (=False, immobilized). SWEEP_LUCK's silent default is can-act, so an infatuated mon that acted needs no injection. Old PKMNINLOVE-keyed can-act reconstruction gone."
updated = "2026-06-19T15:42:38.596Z"

[[record]]
name = "multihit_heal_segmenting"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "HP-delta walk segments bar readings at heal deltas (to>from): a heal resets the cumulative anchor, consumes no hit. Heal legitimacy is NOT judged here (no message-count guard); _hp_count_detail decides via observed-vs-sim HP-delta sequence match."
updated = "2026-06-23T20:15:31.122Z"

[[record]]
name = "fixed_damage_hd_ranking"
file = "src/ai.py"
confidence = "requirement"
rationale = "Proactive fixed-damage moves (Sonic Boom, Dragon Rage, Seismic Toss, Night Shade, Super Fang, Nature's Madness, Psywave) rank in HD/KO by flat value despite no DAMAGE tag; type-immune target scores -40. Reactive ones keep their own branches."
updated = "2026-06-17T14:29:55.721Z"

[[record]]
name = "valid_pokemon_base_names"
file = "SCRIPTS/play.py"
confidence = "requirement"
rationale = "valid_pokemon constraint must use emulator_species_name (base form name), not the enum member name. Regional/form species (e.g. ZIGZAGOON_GALAR) display under their base name, so the raw member name fails to match OCR'd send-out text."
updated = "2026-06-17T14:45:49.969Z"

[[record]]
name = "mover_damage_attacker_keyed"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Per-hit damage discovery keys on the ATTACKER (side+team-slot) via _attacker_per_hit_damages, not the defender's pre-turn species. Switch-robust: a mid-turn switch-in leaves the old species stale; the attacker is fixed. Single+multi-hit both use it."
updated = "2026-06-17T15:50:16.798Z"

[[record]]
name = "single_hit_scalar_override"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Single-hit movers (n_hits 1) drive the sim via SCALAR roll/crit, storing scalar roll+bool crit; per-hit tuple overrides don't control fixed-damage random (Psywave). Single-hit crit_count clamps to 0/1 (spread moves crit many targets, roll crit once)."
updated = "2026-06-17T15:50:33.964Z"

[[record]]
name = "rapid_spin_speed_boost"
file = "liveplay/data/moves.py"
confidence = "requirement"
rationale = "Gen 8 Rapid Spin raises the user's Speed +1 on hit, encoded via self_stat_changes=((4,1),) (applied when damage>0). Confirmed by in-game OCR 'SPEED rose!'. Mortal Spin does NOT get this boost (it poisons foes instead). Index 4 = Speed."
updated = "2026-06-17T15:58:33.724Z"

[[record]]
name = "EXP_GAIN logs gross"
file = "src/engine/exp.py"
confidence = "settled"
rationale = "Game 'gained X Exp' message shows gross calc_exp_gain, not cap-clamped net. When a mon crosses into the level cap, stored EXP is clamped below gross; log gross (net>0) so the reconciler's EXP-amount match works. Already-capped mons (net 0) log 0."
updated = "2026-06-17T16:08:48.972Z"

[[record]]
name = "play_nice_mechanics"
file = "liveplay/data/moves.py"
confidence = "requirement"
rationale = "Play Nice lowers target Attack -1 (idx 0). Never misses (accuracy=None). Bypasses Protect (PROTECT_BYPASS_MOVES) and Substitute (status stat path has no sub gate). Crafty Shield exception moot. Effect in effects.py _STATUS_MOVE_EFFECTS."
updated = "2026-06-17T16:27:18.966Z"

[[record]]
name = "perslot_acted_doubles"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Per-mon message-driven overrides (FULL_PARALYSIS, ACCURACY, ATTRACT_IMMOBILIZE, CONFUSION_SNAP/SELF_HIT, MULTI_HIT_COUNT) written per-slot keyed by acting slot in doubles, scalar in singles. Global scalar let two same-turn movers clobber each other."
updated = "2026-06-19T15:42:53.604Z"

[[record]]
name = "multi_hit_count_perslot"
file = "src/simulator.py"
confidence = "settled"
rationale = "The MULTI_HIT_COUNT override branch calls _resolve_slot so per-slot dict values dispatch by source_slot (scalars still pass through for singles). Without it, doubles two-multihit-mover turns could not carry distinct per-mover hit counts."
updated = "2026-06-17T17:58:15.028Z"

[[record]]
name = "prev_turn_order_field"
file = "liveplay/state/battle.py"
confidence = "settled"
rationale = "prev_turn_order holds the PREVIOUS turn's move order (captured in simulator._finalize_turn), so AI scoring can replicate Bug #8 (AI judges order-dependent damage by last turn's order). MUST stay in __hash__; empty () on turn 1."
updated = "2026-06-18T18:26:08.113Z"

[[record]]
name = "ai_scoring_view_prev_turn"
file = "src/engine/damage.py"
confidence = "requirement"
rationale = "calculate_damage's ai_scoring_view replicates Bug #8: when True, Analytic (1.3x) is judged by prev_turn_order, not the current turn. Engine default False stays current-turn-correct (core.py _compute_variable_bp is the engine path)."
updated = "2026-06-18T18:26:34.965Z"

[[record]]
name = "ai_damage_prev_turn_screens"
file = "src/queries.py"
confidence = "requirement"
rationale = "expected_damage drives AI scoring with ai_scoring_view=True: Analytic/Payback/Bolt Beak/Fishious Rend judged by prev_turn_order (Bug #8). Also passes def_side_idx so screens+Friend Guard now apply in AI scoring (in-game calc factors screens)."
updated = "2026-06-18T18:26:46.604Z"

[[record]]
name = "rollout_switch_in_480bp"
file = "src/queries.py"
confidence = "requirement"
rationale = "rollout_max_bp (on expected_damage/can_ko/best_damage_move) reads Rollout at max 480 BP, replicating Bug #25 (switch-in AI sees Rollout as 480 BP). Passed True ONLY by switch scoring, ONLY for Rollout; active-move scoring stays flat +7."
updated = "2026-06-18T18:26:57.576Z"

[[record]]
name = "coaching_doubles_scoring"
file = "src/ai.py"
confidence = "requirement"
rationale = "Coaching: -20 in singles / no living partner / Contrary partner. Doubles with valid partner: score=6+sum(1-stage for partner Atk[0],Def[1] where stage<2), returned as [(score,0.20),(score+1,0.80)]. Proper distribution, never assigns p=0."
updated = "2026-06-18T18:27:00.805Z"

[[record]]
name = "ai_pp_max_bug_no_code"
file = "liveplay/emulator/pokemon_snapshot.py"
confidence = "settled"
rationale = "Bug #40 (AI maxes PP of first move slot only) needs no production code: it is already reproduced via live emulator snapshots ingested by pokemon_snapshot.py, so move PP comes from real game state rather than being synthesized."
updated = "2026-06-18T18:27:06.393Z"

[[record]]
name = "status_move_semi_invuln_miss"
file = "src/engine/core.py"
confidence = "requirement"
rationale = "Opponent-targeting STATUS moves miss a semi-invuln target (emit MOVE_MISS) like the damaging path. No Guard (either side) bypasses the miss on both paths and the Magic Bounce branch. Other bypasses (Toxic/Gust/Thunder/Gravity) are out of scope."
updated = "2026-06-18T20:08:03.127Z"

[[record]]
name = "status_type_immune_electric"
file = "src/engine/core.py"
confidence = "requirement"
rationale = "Type-chart immunity for STATUS moves is scoped to Electric moves vs Ground (Thunder Wave) only. Broader 0x type immunity is intentionally NOT applied to status moves (Ghost Curse vs Normal still works). Mold Breaker does not bypass type immunity."
updated = "2026-06-18T20:08:12.992Z"

[[record]]
name = "status_substitute_gate"
file = "src/engine/core.py"
confidence = "requirement"
rationale = "Opponent-targeting STATUS effects are blocked by an active Substitute, bypassed only by SOUND-tagged moves, the Infiltrator ability, and Move.PLAY_NICE (its documented special case). Growl is SOUND-tagged so it bypasses Sub."
updated = "2026-06-18T20:08:16.455Z"

[[record]]
name = "status_path_guard_parity"
file = "src/engine/core.py"
confidence = "settled"
rationale = "STATUS path mirrors the damaging _pdg_ guards to avoid sweep crashes: last_move_failed reset+set-on-miss, evasion/accuracy items (Bright Powder/Wide Lens/Sand Veil/Snow Cloak/Tangled Feet/Victory Star), priority blocks (Psychic Terrain, Dazzling/QM)."
updated = "2026-06-18T20:08:33.077Z"

[[record]]
name = "removed_unused_moves"
file = "liveplay/data/moves.py"
confidence = "requirement"
rationale = "Shadow Force, Lock On, and Mind Reader do not appear in this game and were removed from the Move enum and all data tables. Do not re-add them. The Move enum uses explicit integer values so removals do not renumber other members."
updated = "2026-06-18T20:08:37.240Z"

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
name = "fuzzy_match_display_name"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "OCR-name fuzzy matching vs species must use emulator_species_name() (base display name for forms), NOT raw species.name, else ZIGZAGOON_GALAR fails to match OCR 'ZIGZAGOON'. Sites: _resolve_attacker_slot, status-recipient loop, _species_name_matches."
updated = "2026-06-19T06:15:59.832Z"

[[record]]
name = "team_mon_match_display_name"
file = "SCRIPTS/play.py"
confidence = "settled"
rationale = "_resolve_team_mon matches OCR HP-log names via emulator_species_name (base display name), not raw enum name. Regional forms (ZIGZAGOON_GALAR) OCR as 'zigzagoon'; the _GALAR suffix blows past the fuzzy threshold otherwise."
updated = "2026-06-19T06:29:31.941Z"

[[record]]
name = "charging_move_forces_continue"
file = "liveplay/actions.py"
confidence = "settled"
rationale = "enumerate_legal_actions: a mon mid two-turn move (charging_move_slot>=0, e.g. Bounce/Fly/Dig) is forced to complete that move next turn. Overrides Choice lock, 0 PP (spent on charge turn), and switching."
updated = "2026-06-19T07:24:09.494Z"

[[record]]
name = "two_turn_pp_charge_only"
file = "src/engine/core.py"
confidence = "settled"
rationale = "Two-turn moves spend PP only on the charge turn. PP block gated by _two_turn_release (charging_move_slot==effective_slot, still set on release turn before _handle_pre_damage_checks clears it). Stops inferred opp PP draining 2x."
updated = "2026-06-19T07:45:37.845Z"

[[record]]
name = "fake_out_bonus_stacks"
file = "src/ai.py"
confidence = "requirement"
rationale = "Fake Out scores as a normal damaging move (HD odds + kill bonus) with +9 STACKED on top (like Acid Spray's +6) when first-turn, target lacks Shield Dust/Inner Focus, and not type-immune; else -40. Flat +9 made a KOing Fake Out lose to rival KO moves."
updated = "2026-06-19T16:55:47.482Z"

[[record]]
name = "greedy_prune_player_faints"
file = "src/search/search.py"
confidence = "requirement"
rationale = "GreedySearch blocks any child whose player faint count exceeds the root baseline: such nodes are never explored or returned as wins. A faint-ful win is not a clean win, so found_win stays False and the driver loosens RNG then gives up."
updated = "2026-06-19T17:10:18.932Z"

[[record]]
name = "player_damage_no_crit"
file = "src/ai.py"
confidence = "requirement"
rationale = "AI player-damage threat checks never assume crits (AI.md de-crits the player's highest roll). Recovery/nhko/Belly Drum use AVERAGE_LUCK; post-KO switch checks use _MAX_DAMAGE_LUCK to match neighbors. GOOD_LUCK (forced crit) removed."
updated = "2026-06-19T17:32:30.793Z"

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
name = "gen_training_source"
file = "SCRIPTS/nn_iterative_train.py"
confidence = "requirement"
rationale = "Generated battles REPLACE fixed fixtures as training source; real fixtures (Test3) are validation-only. Curriculum label_fn generates a fresh batch each round from the current model's value head so difficulty adapts. User decision."
updated = "2026-06-20T20:23:48.351Z"

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
name = "gap_species_manual"
file = "liveplay/data/generated_abilities.json"
confidence = "requirement"
rationale = "CELEBI/STARYU/STARMIE/DURALUDON have NO ability lines in the RnB source txt; abilities were filled in MANUALLY in this JSON. Re-running extract_abilities.py blindly WIPES them (resets to empty -> excluded from pool). Pool=554."
updated = "2026-06-21T00:15:56.361Z"

[[record]]
name = "struggle_no_pp_spend"
file = "src/engine/core.py"
confidence = "settled"
rationale = "Struggle/recharge spend no PP: _consume_pp raises on slot<0; PP block guards slot>=0. Priority<0=0. Recharge branch stays ==-1 so Struggle flows to execution (move=move_override). Sucker Punch reads move_override so it succeeds vs Struggle."
updated = "2026-06-21T18:20:57.493Z"

[[record]]
name = "struggle_action_representation"
file = "liveplay/actions.py"
confidence = "provisional"
rationale = "Forced Struggle = Action(MOVE, move_slot=-2 STRUGGLE_SLOT, move_override=STRUGGLE); -2 distinct from recharge -1, disambiguator is move_override. Appended only when no usable MOVE action exists (after mega block), and in CHOICE_LOCKED at 0 PP."
updated = "2026-06-21T18:21:07.855Z"

[[record]]
name = "faint log flush"
file = "liveplay/hp_delta.py"
confidence = "settled"
rationale = "Binds a fainted foe's name-keyed k-log to its identity at the send-out reset, BEFORE play.py clears the key for a same-name replacement (Issue 29). Truncate at the first k=0 so a replacement full-bar reading isn't folded in as a bogus heal."
updated = "2026-06-21T20:57:12.692Z"

[[record]]
name = "faint hp disambig"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "_check_hp_match same-species: a delta ending at 0 (faint) prefers the matching mon with hp==0, not the active-slot mon. A same-species faint+replacement puts the replacement in the active slot, so slot matching falsely rejects the faint (Issue 29)."
updated = "2026-06-21T20:57:27.510Z"

[[record]]
name = "per-survivor prune log"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Sweep failure diagnostic lists, per surviving candidate, the stage it died at (HP vs LOG) and mismatch values via _hp_match_detail. The old 'first HP fail' printed the active-slot opp HP (a replacement's bar on faint turns), which misled Issue 29."
updated = "2026-06-21T20:57:41.165Z"

[[record]]
name = "foe faint delta flush"
file = "SCRIPTS/play.py"
confidence = "settled"
rationale = "On opponent send-out reset, build a foe HpDeltaSeq from the outgoing active mon and push to foe_faint_deltas_ref BEFORE clearing the name-keyed k-log. A same-name replacement otherwise wipes the dead foe's readings, leaving no sweep constraint (29)."
updated = "2026-06-21T20:58:08.157Z"

[[record]]
name = "called_move_collapse_general"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Metronome AND Sleep Talk collapse via _collapse_metronome_calls (shared 2-USEDMOVE/1-MOVE_USE shape); injection routes to METRONOME_MOVE or SLEEP_TALK_MOVE keyed on the wrapper via _CALLED_MOVE_EVENTS. Add new wrappers to that map, not a parallel fn."
updated = "2026-06-22T22:17:40.445Z"

[[record]]
name = "action_order_prefix_floor"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "_check_action_order requires sim MOVE_USE sides == observed prefix AND len(sim)>=len(observed). Sim is legitimately LONGER (MOVE_USE for unobserved opponent moves), so only a SHORTER sim prunes. Collapse called-move wrappers first or 2:1 over-prunes."
updated = "2026-06-22T22:17:55.939Z"

[[record]]
name = "single_hit_no_enum_constraint"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Single-hit movers keep ALL damage values at enum time; only multi-hit applies the per-hit cumulative constraint. Enum sim omits final-sim secondary RNG, so a single-hit enum constraint false-over-prunes (B1 pt2 deferred)."
updated = "2026-06-23T20:15:36.391Z"

[[record]]
name = "dedup_by_state_not_hash"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Sweep candidate dedup stores BattleState objects in a set (collision-proof via __eq__), NOT hash(rs) ints. A 64-bit hash collision would silently drop a distinct candidate (F2). Don't revert to storing hashes."
updated = "2026-06-22T22:18:15.734Z"

[[record]]
name = "event_side_attribution"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "check_log_events attributes STATUS/STAT_BOOST/VOLATILE events by matching engine event side (=side_idx) vs the observed side from _msg_is_foe ('Foe ' prefix) plus species via emulator_species_name. Collision-proof in mirrors; keep the side filter."
updated = "2026-06-22T22:18:27.316Z"

[[record]]
name = "slot_map_single_pass"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "One _build_attacker_slot_map cursor pass assigns (side,slot) per USEDMOVE msg id; consumers do slot_map.get(id(msg)) and SKIP on miss (no per-consumer cursor). Prevents action-extraction vs order-validation cursor disagreement (D3 parity)."
updated = "2026-06-22T22:18:36.683Z"

[[record]]
name = "unreproducible_move_filter"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "C1: an observed move not in the moveset/legal actions raises UnreproducibleObservedMoveError, caught per-candidate in run_candidate_sweep (print+continue), not dropped. C2: switch-in to unknown team slot hard-raises SimulationError (roster desync)."
updated = "2026-06-22T22:18:52.498Z"

[[record]]
name = "fuzzy_team_slot_ambiguity"
file = "liveplay/state_transition.py"
confidence = "settled"
rationale = "D1: _fuzzy_find_team_slot collects ALL matching same-species slots and raises RosterAmbiguityError if >1 (opponent may carry duplicates; no silent first-match). Returns the slot if exactly 1, None if 0."
updated = "2026-06-22T22:18:56.529Z"

[[record]]
name = "actor_not_active_raise"
file = "liveplay/state_transition.py"
confidence = "settled"
rationale = "D2: _fuzzy_find_side(reference_kind='actor') raises ActorNotActiveError when the name is RECOGNIZABLE (matches >=1 slot anywhere) but neither active. OCR garble (matches nothing) trusts the hint. Actor-naming callers pass reference_kind='actor'."
updated = "2026-06-22T22:19:07.926Z"

[[record]]
name = "opp_no_change_all_slots"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "check_log_events no-opponent-deltas guard sums ALL move damage to defender_side=1 (_total_side_move_damage), not just opp_species/slot-0, so doubles slot-1 opponents of another species are constrained (E2). opp_species kept as known-opponent gate."
updated = "2026-06-22T22:53:06.423Z"

[[record]]
name = "damage_attacker_slot_via_swap"
file = "src/engine/core.py"
confidence = "settled"
rationale = "Move-damage DAMAGE uses attacker_slot=active_indices[0]; CORRECT in doubles because _handle_damage_loop runs inside _active_slot_swapped(side, source_slot), swapping the acting mon's team index into slot 0. Do not 'fix' to a hardcoded slot (G1)."
updated = "2026-06-22T22:53:25.319Z"

[[record]]
name = "berry_consume_corroboration"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "check_log_events matches observed berry-restore messages (berry-only string ids) one-for-one per side vs sim HEAL source='berry', pruning rolls that trip/skip a berry even when final HP coincides (B1 pt2). Side via msg.side_hint."
updated = "2026-06-23T00:16:58.787Z"

[[record]]
name = "berry_heal_side_kwarg"
file = "src/engine/_helpers.py"
confidence = "settled"
rationale = "_check_berry emits HEAL with side=side_idx so check_log_events can attribute berry consumption per side (mirror-safe) for the berry-restore corroboration constraint."
updated = "2026-06-23T00:17:02.094Z"

[[record]]
name = "warn_uninjected_dedup"
file = "liveplay/rng.py"
confidence = "requirement"
rationale = "Per sweep call, warn_uninjected logs are deduped: each unique text (event+side, strict match) prints once with its count. run_candidate_sweep wraps each call in aggregate_uninjected_warnings(); stays WARNING; covers all warn_uninjected events."
updated = "2026-06-23T01:00:16.878Z"

[[record]]
name = "natgift_no_berry_spends_pp"
file = "src/engine/core.py"
confidence = "requirement"
rationale = "No-berry Natural Gift executes and fails, so it spends PP (Gen 4/5), unlike pre-execution blocks (sleep). Skipping PP stalled the engine: only-PP-move loops forever, never forced to Struggle. Called moves/Dancer pay no slot PP."
updated = "2026-06-23T04:08:34.739Z"

[[record]]
name = "gravity_filters_legal_moves"
file = "liveplay/actions.py"
confidence = "requirement"
rationale = "Under Gravity, gravity-blocked moves (Fly/Bounce/HJK/Magnet Rise) are filtered from enumerate_legal_actions like Taunt/Assault Vest, so an all-blocked moveset falls through to forced Struggle, not a no-PP fail loop."
updated = "2026-06-23T04:08:44.570Z"

[[record]]
name = "cheek_pouch_corroboration"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Cheek Pouch shares berries' generic restore strings; only its source-name var distinguishes it. Engine logs it source=cheek_pouch with side=. Corroboration buckets restore msgs by var, matching source=berry and cheek_pouch separately per side."
updated = "2026-06-23T05:23:01.468Z"

[[record]]
name = "fuzzy_team_slot_reducer"
file = "liveplay/state_transition.py"
confidence = "settled"
rationale = "_fuzzy_find_team_slots reduces duplicate-species matches by switch-eligibility (drops active/fainted slots), returning the rest to fan out. _fuzzy_find_team_slot raises only on unreduced ties. Fixes same-species switch-in regression."
updated = "2026-06-23T14:18:12.083Z"

[[record]]
name = "ambiguity_reduce_then_fanout"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Same-species ambiguity is reduced then fanned out into branches pruned by validation: switch-ins via _opponent_switch_in_actions->list[tuple], attackers via _build_attacker_slot_maps->list[dict]. Capped at _SWEEP_BRANCH_CAP=1000, fail loud."
updated = "2026-06-23T14:18:15.558Z"

[[record]]
name = "recipient_slot_hp_reduction"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "_slot_for_name reduces same-species recipient ambiguity by per-slot HP delta (flinch/damage recipient changed HP), else raises. _inject_non_move_rng resolves attacker pos via slot_map for doubles parity, not the raising _slot_for_name."
updated = "2026-06-23T14:18:19.342Z"

[[record]]
name = "hp_delta_count_check"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Sweep checks COUNT of HP-bar transitions (observed vs sim), not just endpoint, to catch a phantom/extra residual tick a value-only check hides. Player=exact HP, opp=k-pixel. Consistency guard SKIPs (never false-prunes) on unaccounted HP changes."
updated = "2026-06-23T15:10:31.641Z"

[[record]]
name = "wrap_release_override"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "Observed PKMNFREEDFROM ('freed from Wrap') is ground truth: _apply_observed_wrap_release clears BOUND+BOUND_SOURCE_SLOT on the named mon at turn start so a too-long carried duration roll can't keep it trapped or add a tick. Needs Foe side_hint."
updated = "2026-06-23T15:10:56.112Z"

[[record]]
name = "centralized_opponent_faint_exp"
file = "src/engine/exp.py"
confidence = "requirement"
rationale = "Opponent-faint EXP triggers from the faint itself, not a move/event path. flush_opponent_faint_exp scans side-1 active mons for fainted ones, called per causing-event. Simultaneous player faint => no EXP (skips fainted winners). Idempotent."
updated = "2026-06-23T16:50:45.760Z"

[[record]]
name = "move_exp_flush_after_recoil"
file = "src/engine/core.py"
confidence = "requirement"
rationale = "Move-action opponent KOs award EXP via _flush_opponent_faint_exp at end of _execute_action, after the move body (incl. recoil) resolves. Covers attacker self-KO (Struggle/Double-Edge recoil) old inline paths missed. Switch path flushes too."
updated = "2026-06-23T16:50:57.347Z"

[[record]]
name = "residual_exp_flush_points"
file = "src/engine/residuals.py"
confidence = "requirement"
rationale = "Residual KOs award EXP after each battler's per-battler chain + after Future Sight; no inline distribute_exp. Residual flushes use allow_fainted_winners=True so a player fainted earlier keeps EXP from a later opponent KO. Idempotent, no double-award."
updated = "2026-06-25T17:54:35.055Z"

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
name = "Persistent calc server"
file = "SCRIPTS/ai_decision.py"
confidence = "requirement"
rationale = "User chose persistent Node server (AIDecision.js itself, no new JS, no Calculator.js changes): loads calc once, reused across calls so only first request pays startup. Returns both probs and damage rolls. Needed for a faster downstream script."
updated = "2026-06-24T05:47:56.040Z"

[[record]]
name = "residual_per_battler_order"
file = "src/engine/residuals.py"
confidence = "settled"
rationale = "Residuals process per-battler in fixed Speed order (fastest first); each battler runs its full chain (_BAND_TABLE + _LATE_PER_SLOT_HANDLERS, stop on faint) before the next. Within-battler order unchanged. Matches Emerald; fixes Unnerve phantom-heal."
updated = "2026-06-25T17:54:32.153Z"

[[record]]
name = "residual_order_fixed"
file = "src/engine/residuals.py"
confidence = "provisional"
rationale = "Per-battler residual order computed ONCE at phase start; mid-phase speed changes (Speed Boost) do NOT reorder remaining battlers this turn. Chosen for simplicity; unconfirmed vs dynamic order. Revisit if a dynamic-order case appears."
updated = "2026-06-25T17:54:33.578Z"

[[record]]
name = "faint_active_canonical_setter"
file = "src/engine/_helpers.py"
confidence = "requirement"
rationale = "All faint sites route through faint_active(sides,side_idx,*,notify_soul_heart,slot). Idempotent (early-return if fainted). Does NOT own log(FAINT); callers keep it to preserve order. Hook for faint side-effects (trap release before soul-heart)."
updated = "2026-06-28T20:14:44.095Z"

[[record]]
name = "trap_release_pull_identity"
file = "src/engine/trap_release.py"
confidence = "requirement"
rationale = "Traps release when inflictor leaves (faint OR switch). Inflictor id=team_idx in BOUND/TRAPPED_SOURCE_ID (side derived; cross-side). Eager release in faint_active + _apply_switch_out_reset. NO_RETREAT self-trap has no source id, never releases."
updated = "2026-06-28T20:14:55.429Z"

[[record]]
name = "switch_reset_releases_traps"
file = "src/engine/effects.py"
confidence = "settled"
rationale = "_apply_switch_out_reset(sides,side_idx,old_idx) is the shared switch-out choke-point (voluntary/forced/pivot/post-faint). After self-reset it calls release_inflicted_traps to free opponents the departed mon trapped."
updated = "2026-06-28T20:15:00.903Z"

[[record]]
name = "bound_tick_inflictor_skip"
file = "src/engine/residuals.py"
confidence = "settled"
rationale = "_band_late_damage skips the BOUND tick when BOUND_SOURCE_ID's inflictor is gone (inflictor_gone), covering an inflictor that faints earlier in the same residual phase before its slot reset. SOURCE_ID entries preserved in _res_tick (not decremented)."
updated = "2026-06-28T20:15:03.333Z"

[[record]]
name = "bad_dreams_faint_logging"
file = "src/engine/residuals.py"
confidence = "settled"
rationale = "Bad Dreams KO now logs DAMAGE+FAINT and fires Soul-Heart via faint_active (previously a silent inline HP write), making it consistent with all other residual faint paths."
updated = "2026-06-28T20:15:08.752Z"

[[record]]
name = "bound_counter_exact_ticks"
file = "src/engine/residuals.py"
confidence = "requirement"
rationale = "BOUND counter = EXACT ticks remaining (4/5/7). _band_late_damage ticks every turn counter>=1, incl the final counter==1 turn, so duration-N deals N ticks. On BOUND expiry, _res_tick_timed_volatiles strips its BOUND_SOURCE_SLOT/ID companions."
updated = "2026-06-28T21:27:14.744Z"

[[record]]
name = "sweep_assume_max_trap"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "SWEEP_LUCK sets binding_duration_roll=rampage_duration_roll=1.0 so the sweep assumes MAX hidden duration (Bind=5, Thrash=3); Grip Claw still forces 7. Assuming shortest under-counts ticks and crashes on a real tick. Trimmed by observed end-messages."
updated = "2026-06-28T21:27:22.647Z"

[[record]]
name = "rampage_end_observed_trim"
file = "src/simulation_runner.py"
confidence = "settled"
rationale = "_apply_observed_rampage_end (keyed on PKMNFATIGUECONFUSION, side_hint from B_ATK_NAME prefix) clears RAMPAGING+LOCKED_MOVE and sets CONFUSED on the named mon at turn start, trimming the assumed-max rampage. Mirrors _apply_observed_wrap_release."
updated = "2026-06-28T21:27:22.693Z"

[[record]]
name = "search_no_assume_max_trap"
file = "src/search/driver.py"
confidence = "settled"
rationale = "Search/stress uses random_mode live rollout + per-tier BAD/AVG/GOOD presets for forward planning, NOT observed reconciliation. So do NOT apply the sweep's assume-max trap-duration here; per-tier duration luck is correct for search."
updated = "2026-06-28T21:27:31.112Z"

[[record]]
name = "cpp_bound_gate_parity"
file = "engine/src/residuals.cpp"
confidence = "requirement"
rationale = "C++ bound tick mirrors Python: gate bound_turns>=1 (every turn incl final counter==1 deals a tick), strip BOUND_SOURCE_SLOT/ID on natural BOUND expiry. BOUND_SOURCE_ID IS modeled; trap release keys on it. Parity: test_cpp_residuals.TestBound."
updated = "2026-06-30T04:54:16.663Z"

[[record]]
name = "name_side_slots_per_slot_side"
file = "liveplay/battle_types.py"
confidence = "settled"
rationale = "name_side_slots maps each POKEMON_NAME slot index to its side, generalizing slot-0-only side_hint. side_of_name_slot(idx) returns None for non-name indices so callers fail loud. Needed when the mon subject isn't slot 0 (USINGITEMSTATOFPKMNROSE)."
updated = "2026-06-28T22:40:50.445Z"

[[record]]
name = "side_attribution_uses_hint"
file = "src/simulation_runner.py"
confidence = "requirement"
rationale = "Messages resolve side via side_hint AND name. _slot_for_name/_recipient_slot take side_constraint; flinch, Quick Claw, USINGITEM pinch-berry verifier use _fuzzy_find_side + side_of_name_slot. Unresolvable side fails loud."
updated = "2026-06-28T22:40:56.769Z"

[[record]]
name = "oracle_resolution_at_bridge"
file = "engine/src/"
confidence = "requirement"
rationale = "Category-A oracle RNG: CONTROLLED stays C++-fail-loud (Python resolves at bridge). random_mode resolves NATIVELY via NativeRng: A1 (dmg/premove/residual), A2 (SPEED_TIE/Quick Claw), A3 (Starf/Acupressure/Effect Spore/Tri Attack/Moody). All ported."
updated = "2026-07-03T02:19:59.598Z"

[[record]]
name = "run_one_turn_state_only"
file = "engine/src/"
confidence = "settled"
rationale = "SUPERSEDED by C++ GameDriver orchestration (C1.7h): cpp_run_one_turn returned only the mutated BattleState with winner/done/phase computed in Python; orchestrate.cpp/game_driver.cpp now own the game loop and outcome."
updated = "2026-07-08T19:13:35.697Z"

[[record]]
name = "run_one_turn_static_order"
file = "engine/src/"
confidence = "settled"
rationale = "SUPERSEDED (Issue 5 S3+S4): cpp_run_one_turn now uses dynamic cpp_select_next_action and accepts a LIST of actions per side (doubles). Each ExecAction carries source_slot; per-mover loop uses best.source_slot, not slot 0."
updated = "2026-07-03T05:51:13.646Z"

[[record]]
name = "turn_ctx_per_turn_shared"
file = "engine/src/"
confidence = "settled"
rationale = "cpp_run_one_turn builds ONE ExecCtx for the whole turn (Python's single TurnContext). Protect-family side state accumulates across movers; per-actor fields (attacker_slot, opp_action, exp_participants) are overwritten each iteration."
updated = "2026-06-29T17:29:38.007Z"

[[record]]
name = "residual_ko_exp_clear"
file = "engine/src/"
confidence = "settled"
rationale = "cpp_apply_residuals consumes a CONST copy of exp_participants, so its KO-driven slot clears (exp.py:156) never reach the driver. cpp_run_one_turn replays the clear for fainted opponent slots before committing, keeping committed sets in parity."
updated = "2026-06-29T17:29:45.294Z"

[[record]]
name = "bridge_seam_begin_turn"
file = "src/cpp_bridge.py"
confidence = "settled"
rationale = "cpp_bridge intercepts the deterministic slice at Simulator._begin_turn for clean singles turns; unported/non-interceptable fall back to Python (raise under BRIDGE_STRICT). Verify-mode (default on) reruns on a vanilla Simulator, raising on py!=cpp."
updated = "2026-06-29T17:51:17.300Z"

[[record]]
name = "exp allow_fainted_winners"
file = "engine/src/exp.cpp"
confidence = "settled"
rationale = "Residual-phase exp flushes pass allow_fainted_winners=True so a mon that fainted earlier in the same turn still receives EXP from an opponent KO'd later in the residual phase. The post-Future-Sight flush stays default false."
updated = "2026-06-29T19:09:32.831Z"

[[record]]
name = "gem id->Type transposed"
file = "engine/src/post_hit.cpp"
confidence = "settled"
rationale = "Gem item-id->Type is NOT a clean item-4000 map: GRASS_GEM(4003) and ELECTRIC_GEM(4004) are transposed vs Type enum (ELECTRIC=3, GRASS=4). gem_type/gem_type_of special-case these before item-4000 fallback, else gems aren't consumed."
updated = "2026-06-29T19:09:46.554Z"

[[record]]
name = "parity tripwire uses PINNED"
file = "tests/test_cpp_c17g_gate.py"
confidence = "settled"
rationale = "Parity tripwire must use a fully-PINNED LuckProfile, not SWEEP_LUCK. SWEEP_LUCK is warn-and-sample: uninjected Category-B rolls sample independently per engine, so py/cpp comparison surfaces RNG artifacts not port gaps."
updated = "2026-06-29T19:09:46.600Z"

[[record]]
name = "faint_via_cpp_faint_active"
file = "engine/src/"
confidence = "settled"
rationale = "Every C++ faint transition must route through cpp_faint_active (hp=0/fainted + cpp_release_inflicted_traps), never set fainted=true directly. Skipping it leaks the fainter's BOUND/TRAPPED onto opponents. Bit self-KO sites and Rocky Helmet recoil."
updated = "2026-06-30T04:52:01.468Z"

[[record]]
name = "technician_after_var_bp"
file = "engine/src/damage.cpp"
confidence = "settled"
rationale = "resolve_move_type_and_bp must NOT early-return for variable-power moves (Weather Ball/Terrain Pulse/Aura Wheel/Multi-Attack/Revelation Dance); they fall through to Technician's base_power<=60 1.5x gate like damage.py. Only Natural Gift returns early."
updated = "2026-06-30T04:52:13.981Z"

[[record]]
name = "secondary_is_chance_nonzero"
file = "engine/src/"
confidence = "settled"
rationale = "C++ mirrors Python's 'secondary is not None' as md.secondary.chance != 0, NOT field-decomposition (status/flinch/stat/volatile). A chance-only secondary (BUBBLE) still counts: suppresses Life Orb recoil under Sheer Force and gets the SF damage boost."
updated = "2026-06-30T05:15:34.772Z"

[[record]]
name = "promote_run_one_turn_binding"
file = "engine/bindings/module.cpp"
confidence = "settled"
rationale = "C1.7i: probe submodule removed; run_one_turn promoted to top-level nuzlocke_engine_cpp.run_one_turn. The Python bridge (cpp_bridge.py) depends on it. Do not re-nest under a probe submodule."
updated = "2026-06-30T06:12:05.207Z"

[[record]]
name = "keep_sweep_capture_hook"
file = "src/engine/"
confidence = "settled"
rationale = "C1.7i removed the 4 sub-unit capture hooks (DAMAGE/EFFECTS/POSTHIT/RESIDUAL_CAPTURE). The NUZLOCKE_CAPTURE hook in engine_select.py is KEPT: it feeds the permanent c17g corpus. Do not delete it with the others."
updated = "2026-06-30T06:12:09.946Z"

[[record]]
name = "sortkey_neg_slot_prio0"
file = "src/engine/core.py"
confidence = "settled"
rationale = "_action_sort_key treats ANY move_slot<0 as priority 0 (recharge -1 AND Struggle -2), like _check_priority_item. Old 'slot==-1' let Struggle index move_ids[-2], inheriting that slot's priority. Caught by C1.7h parity gate; test TestStruggleSortKey."
updated = "2026-06-30T15:26:33.539Z"

[[record]]
name = "eject_pack_ported"
file = "engine/src/"
confidence = "settled"
rationale = "Eject Pack ported (C1.7h.2 S2): change_stat_stage appends the holder side to ExecCtx.eject_pack_sides; cpp_run_one_turn drains them into pending as cause 'eject_button' after each mover, resolved via Policy like u_turn."
updated = "2026-07-01T00:15:11.847Z"

[[record]]
name = "forced_switch_resolver"
file = "engine/src/"
confidence = "settled"
rationale = "cpp_resolve_pending_switches (C1.7h.2) resolves ALL mid-turn switches after each mover: u_turn/eject_button/red_card via Policy, roar/phaze via oracle draw. Suction Cups blocks phaze at RESOLUTION not trigger (both engines append the cause)."
updated = "2026-07-01T00:15:17.254Z"

[[record]]
name = "baton_pass_transfer"
file = "engine/src/orchestrate.cpp"
confidence = "settled"
rationale = "Baton Pass transfer (C1.7h.2 S4) in cpp_apply_switch copies 5 fields to the incoming mon BEFORE the turns_in_battle reset: stat_stages(copy), volatiles(OR), timed_volatiles(append), crit_stage, sub_hp; then clears baton_pass_data."
updated = "2026-07-01T00:15:18.708Z"

[[record]]
name = "action_log_phase_key"
file = "SCRIPTS/c17h_game_gate.py"
confidence = "settled"
rationale = "Game action_log dispatches on the 'phase' string (no version field): actions/post_faint/forced_switch/phaze. Mid-turn switch entries carry the chosen bench idx; Python replay applies it verbatim (never re-draws), pinning phaze RNG via the log."
updated = "2026-07-01T00:15:24.058Z"

[[record]]
name = "analytic_module_separation"
file = "engine/src/ai_analytic.cpp"
confidence = "provisional"
rationale = "compute_action_probabilities/possible_ai_actions/iter_damage_configs live in ai_analytic.{h,cpp}, apart from ai_scorer (_dist_*) and ai_policy (sampler). Analytic config-enum + argmax-share aggregation is its own concern; mirrors Python layering."
updated = "2026-07-02T14:42:08.463Z"

[[record]]
name = "cpp_possible_actions_support"
file = "engine/src/ai_analytic.cpp"
confidence = "requirement"
rationale = "cpp_possible_ai_actions = analytic support {a:p>0} of cpp_compute_action_probabilities, deliberately diverging from Python possible_ai_actions (stochastic _score_ai_actions). User decision: search wants deterministic support."
updated = "2026-07-02T14:42:41.413Z"

[[record]]
name = "analytic_gate_compares_zeros"
file = "SCRIPTS/ai_analytic_dist_gate.py"
confidence = "settled"
rationale = "The analytic-dist gate compares EVERY key-aligned action prob within 1e-9, including p==0 keys (Python emits explicit 0.0 for non-target switches under all_ineffective). Positive-support-only would hide all_ineffective/doubles bugs."
updated = "2026-07-02T14:43:03.501Z"

[[record]]
name = "policy_switch_phaze_ctx"
file = "engine/src/policy.h"
confidence = "settled"
rationale = "Policy gains select_switch(SwitchCtx)+select_phaze, defaulting to select() so Random/Scripted stay unchanged. AIPolicy: select=sampler, select_switch=cpp_select_post_ko_switch, select_phaze=uniform. Phaze is a game oracle: random even on AI side."
updated = "2026-07-02T15:07:21.575Z"

[[record]]
name = "run_game_selectable_policy"
file = "engine/src/orchestrate.cpp"
confidence = "settled"
rationale = "cpp_run_game takes policy_p0/policy_p1 ('random'|'ai', default 'random'). Default keeps identical seeds so c17h random-vs-random parity stays byte-exact. AI path verified structurally only (each AI decision in cpp_possible_ai_actions), not vs Python."
updated = "2026-07-02T15:07:38.529Z"

[[record]]
name = "called_move_uniform_choice"
file = "engine/src/turn.cpp"
confidence = "settled"
rationale = "random_mode resolves Metronome/Sleep Talk sub-move via uniform NativeRng::choice over callable options; controlled stays fail-loud (unported: sub_move). Python _phase_await_sub_move is oracle-only, no else-random branch, so uniform is correct."
updated = "2026-07-03T03:12:18.190Z"

[[record]]
name = "called_exclude_hand_arrays"
file = "engine/src/move_exec.cpp"
confidence = "provisional"
rationale = "METRONOME_EXCLUDED/SLEEP_TALK_EXCLUDED are hand-written int arrays mirroring src/data/moves.py, not codegen. Small, stable sets; keep in sync with the Python source if it changes."
updated = "2026-07-03T03:12:21.445Z"

[[record]]
name = "turn_start_raw_weather"
file = "engine/src/effects.cpp"
confidence = "settled"
rationale = "cpp_apply_turn_start_effects (RKS/Silvally type-sync + Castform Forecast) uses RAW s.weather, not air-lock-suppressed effective_weather, per core.py. Deterministic (no RNG); reuses helpers memory_type/forecast_form/update_castform."
updated = "2026-07-03T03:25:35.269Z"

[[record]]
name = "residual_switch_unported"
file = "engine/src/turn.cpp"
confidence = "requirement"
rationale = "Emergency Exit/Wimp Out residual forced switch left UNPORTED (user 2026-07-02). C++ fails loud (unported: residual_switch); Python double-applies residuals on resume, frozen not fixed; abilities pruned from corpora. See INTENTIONAL_DIVERGENCES.md #2."
updated = "2026-07-03T04:55:55.471Z"

[[record]]
name = "mega_primal_singles_ported"
file = "engine/src/turn.cpp"
confidence = "settled"
rationale = "Mega (mega_pX flag) + primal (auto, Blue/Red Orb) ported to cpp_run_one_turn SINGLES, after turn_start: primal then mega (speed-sorted, TR-inverted), per simulator.py:543-598. MEGA_TABLE mirrors mega.py. State-based gate needs no MEGA_EVOLVE log."
updated = "2026-07-03T05:15:26.382Z"

[[record]]
name = "dynamic_action_reselect"
file = "engine/src/core_leaf.cpp"
confidence = "settled"
rationale = "cpp_select_next_action recomputes sort key vs current state each pick (mirrors Python _select_next_action); cpp_build_pending_entries resolves tiebreaker/Custap/Quick Draw ONCE. Enables mid-turn speed changes; singles order == static order."
updated = "2026-07-03T05:33:18.312Z"

[[record]]
name = "doubles_multislot_driver"
file = "engine/src/turn.cpp"
confidence = "settled"
rationale = "cpp_run_one_turn takes vector<ExecAction> per side (up to 2 slots). Each action carries source_slot; per-mover loop uses best.source_slot for active-index and action lookup, passes it to cpp_execute_action. opp_action=opp slot-0; mega slot-0 only."
updated = "2026-07-03T05:51:43.132Z"

[[record]]
name = "speed_tie_throw_scope"
file = "engine/src/core_leaf.cpp"
confidence = "settled"
rationale = "SPEED_TIE throw fires ONLY for cross-side MOVE ties (need bridge oracle). Same-side and switch-switch ties resolve via stable first-max, matching Python gate-replay (oracle=None). Switch-vs-move ties are impossible (switch key=7 > any move)."
updated = "2026-07-03T06:24:44.765Z"

[[record]]
name = "doubles_game_perslot_select"
file = "engine/src/orchestrate.cpp"
confidence = "settled"
rationale = "cpp_run_game selects one action per active slot per side; fainted slots skipped. Slot-1 switch candidates filtered to avoid claiming slot-0's bench mon (joint legality; safe since gate replays C++ choices). action_log p0/p1 always JSON arrays."
updated = "2026-07-03T06:24:51.575Z"

[[record]]
name = "random_normal_native"
file = "engine/src/core_leaf.cpp"
confidence = "settled"
rationale = "Multi-foe RANDOM_NORMAL: random_mode picks via NativeRng->choice (mirrors Python random.choice); controlled mode throws unported so the pinned-luck parity gate prunes it. Independent RNG streams mean random_mode need not match Python."
updated = "2026-07-03T06:24:51.620Z"

[[record]]
name = "doubles_clean_corpus"
file = "SCRIPTS/c17h_clean_battle_gen.py"
confidence = "settled"
rationale = "make_doubles_battle builds DOUBLES states (active_indices=[0,1], team>=2). Doubles clean corpus excludes RANDOM_NORMAL moves (THRASH/PETAL_DANCE/OUTRAGE/UPROAR/RAGING_FURY): fail-loud in controlled mode with >=2 live foes. STRUGGLE caught by probe."
updated = "2026-07-03T06:55:58.010Z"

[[record]]
name = "doubles_exp_participants_dedup"
file = "engine/src/turn.cpp"
confidence = "settled"
rationale = "Post-residual exp_participants clearing clears only the FIRST fainted occurrence of each team_idx in active_indices (dedup guard). Duplicate active slots (e.g. [0,0]) else double-clear, dropping a set and diverging from Python's turn-end commit."
updated = "2026-07-03T06:56:18.355Z"

[[record]]
name = "oracle_pause_resume_driver"
file = "engine/src/game_driver.cpp"
confidence = "settled"
rationale = "Category-A oracle: unresolved event -> NeedsRNG; cpp_run_one_turn_oracle restores pre-action snapshot {state,ctx,exp_participants,pending} and rethrows TurnPause. Resume skips _begin_turn (no double-consume). Override map READ-ONLY, reused each fire."
updated = "2026-07-03T19:13:48.061Z"

[[record]]
name = "oracle_overrides_luck_channel"
file = "engine/src/effects.cpp"
confidence = "settled"
rationale = "OracleOverrides reach oracle_resolve via TWO channels: ExecCtx.overrides where ctx flows (post_hit), and luck.overrides (DamageLoopLuck/EffectsLuck/MoveExecLuck) where only luck flows (Acupressure/Starf/Moody). make_effects_luck copies it through."
updated = "2026-07-03T19:31:40.404Z"

[[record]]
name = "cpp_logger_runtime_toggle"
file = "engine/src/logger.h"
confidence = "requirement"
rationale = "C++ event logger mirrors Python src/logger.py LogEvent stream. MUST toggle on/off at RUNTIME in one build (global Logger* nullptr=off; NO preprocessor) since usecases coexist. Back with POD vector, not nlohmann::json; JSON only at boundary."
updated = "2026-07-03T20:24:00.601Z"

[[record]]
name = "cpp_analytical_rng_logger"
file = "engine/src/logger.h"
confidence = "requirement"
rationale = "Separate lighter RNG log for analytical/search: each draw records {event_id, options, chosen} PLUS participants (which pokemon / side+slot involved). Category B sites need explicit log calls to surface. Runtime-toggled, same on/off model as tracker."
updated = "2026-07-03T20:24:07.604Z"

[[record]]
name = "roar_target_oracle_dual_path"
file = "engine/src/turn.cpp"
confidence = "settled"
rationale = "ROAR_TARGET phaze: cpp_resolve_pending_switches overrides!=null resolves via oracle_resolve (GameDriver pause/override); overrides==null (run_game) keeps Policy select_phaze. Do NOT collapse nullptr branch — parity gate replays the logged idx."
updated = "2026-07-03T20:50:50.789Z"

[[record]]
name = "random_normal_oracle_deferred"
file = "engine/src/core_leaf.cpp"
confidence = "requirement"
rationale = "RANDOM_NORMAL target stays fail-loud (unported) in controlled doubles; NOT a Category-A oracle. Python core.py:461 uses raw random.choice, not an RNGEvent; singles has 1 foe (deterministic). Deferred to a doubles-oracle phase (user 2026-07-03)."
updated = "2026-07-03T20:54:11.176Z"

[[record]]
name = "moody_stats_oracle_dual_path"
file = "engine/src/residuals.cpp"
confidence = "settled"
rationale = "MOODY stat pick, dual-path like ROAR: random_mode draws natively; oracle path (overrides!=null) resolves two-pick MOODY_STATS via oracle_resolve_pair (override or NeedsRNG pause), boost=i0%7 drop=i1%5; plain path stays fail-loud unported:moody."
updated = "2026-07-03T21:07:05.747Z"

[[record]]
name = "sub_move_oracle_driver_path"
file = "engine/src/game_driver.cpp"
confidence = "settled"
rationale = "METRONOME/SLEEP_TALK sub-move: oracle path uses oracle_resolve (answer=chosen move id, options=callable moves) -> override or NeedsRNG pause; bad answer fails. Plain run_game stays fail-loud unported:sub_move (turn.cpp). ASSIST singles fails."
updated = "2026-07-03T21:14:44.850Z"

[[record]]
name = "gamedriver_oracle_layer"
file = "engine/src/game_driver.cpp"
confidence = "settled"
rationale = "GameDriver resumable turn loop resolves singles Category-A events via override or NeedsRNG pause (additive to fail-loud bridge). Per event: random_mode native; oracle override/pause; plain run_game fail-loud for c17g. RANDOM_NORMAL deferred."
updated = "2026-07-03T21:18:36.228Z"

[[record]]
name = "voluntary_switch_trigger"
file = "src/ai.py"
confidence = "requirement"
rationale = "Voluntary switch (user 2026-07-04): ALL move scores <= +5 (not -5), HP >= 50%, Cond2 candidate, singles; 50% gate. Priority over move scoring: SWITCH excluded from move tie-break. Target = Cond2-filtered post-KO scoring. Mirrored in cpp."
updated = "2026-07-04T16:03:33.036Z"

[[record]]
name = "faint_queue_no_rebuild_bug"
file = ""
confidence = "requirement"
rationale = "KNOWN BUG, fix deferred to new repo (user, 2026-07-04): hazard-killed post-KO replacement is not re-prompted (no faint-queue rebuild, both engines); next turn starts with fainted active, unlike real game. Details/repro: RECORDS/FaintQueueBug.md"
updated = "2026-07-04T18:49:21.294Z"

[[record]]
name = "trace-match-key"
file = "liveplay/rng_trace.py"
confidence = "settled"
rationale = "Trace records keyed by (turn, RNGEvent, occurrence_idx); counters reset per turn. C++ ForcedTrace Cat-B map uses the SAME key; Cat-A answers are an ORDERED stream (turn/event/side checked, not keyed). Richer key rejected: sites can't learn side."
updated = "2026-07-07T00:33:55.458Z"

[[record]]
name = "rngevent-append-only"
file = "liveplay/rng.py"
confidence = "settled"
rationale = "RNGEvent int values are frozen: cpp/src/oracle.h RngEventC hard-codes the auto() sequence (1-31, SPEED_TIE=31). New members append only (SPEED_TIEBREAKER=32, RANDOM_TARGET=33). Never reorder or delete members."
updated = "2026-07-04T23:25:29.860Z"

[[record]]
name = "trace-outcome-pre-negation"
file = "liveplay/rng.py"
confidence = "settled"
rationale = "Recorded outcome is the sampler return value (_roll_bernoulli/_roll_categorical/_roll_uniform), BEFORE any caller negation/conversion (e.g. attract/paralysis use 'not _roll_bernoulli'). C++ replay must force at the same sampler boundary."
updated = "2026-07-04T23:25:34.788Z"

[[record]]
name = "random-target-1foe-no-draw"
file = "liveplay/rng.py"
confidence = "settled"
rationale = "resolve_random_target draws (and records) only when len(foe_slots)>1; single foe returns directly with NO draw, matching cpp core_leaf.cpp RANDOM_NORMAL short-circuit. Preserves RNG-stream identity (verified by transition golden)."
updated = "2026-07-04T23:25:49.225Z"

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
name = "flattener-preprocessor-gated"
file = "engine/"
confidence = "requirement"
rationale = "USER (2026-07-04): the C++ port of the eps-mixture RNG flattener must be behind a preprocessor statement (compile-time gate) so it has zero effect on normal runtime builds. Only trace-recording builds enable it."
updated = "2026-07-04T23:26:11.111Z"

[[record]]
name = "flatten-eps-zero-bit-identity"
file = "liveplay/rng.py"
confidence = "settled"
rationale = "eps=0 must be bit-identical to pre-refactor RNG streams: eps check short-circuits BEFORE any extra draw; only legal support flattened (0<chance_pct<100 gate; saturation guards precede). Locked by test_transition_golden.py + test_rng_flatten.py."
updated = "2026-07-04T23:26:20.595Z"

[[record]]
name = "crit-single-roll-override"
file = "src/engine/damage.py"
confidence = "settled"
rationale = "Hit loop resolves crit ONCE (draw -> Merciless -> Lucky Chant), passes crit_override to calculate_damage; C++ mirrors (-1/0/1). Overrides must NEVER skip the draw: trace replay depends on draw counts. Internal roll = non-loop callers only."
updated = "2026-07-06T15:34:49.378Z"

[[record]]
name = "unified-answer-stream"
file = "liveplay/golden_trace.py"
confidence = "settled"
rationale = "All Cat-A inputs (RNG answers, action selections, switches) live in one 'answer' record stream keyed by (turn, event, occurrence) with before_seq for merging. One stream = one replay cursor in C++; no cross-stream ordering bugs."
updated = "2026-07-06T16:11:22.943Z"

[[record]]
name = "buffer-and-merge-at-game-end"
file = "liveplay/golden_trace.py"
confidence = "settled"
rationale = "Traces are buffered and merged (merge_records) at game end, not flushed incrementally: Cat-A pauses roll the recorder back, so records are only stable at pause boundaries. Driver records sort before rng records at equal seq."
updated = "2026-07-06T16:11:25.143Z"

[[record]]
name = "plain-string-answer-events"
file = "liveplay/golden_trace.py"
confidence = "requirement"
rationale = "ACTION_SELECT/FORCED_SWITCH/POST_FAINT_SWITCH are plain strings in answer records, NOT RNGEvent members: RNGEvent ints are frozen for C++ (oracle.h) and these are driver inputs, not engine RNG. AWAIT_SUB_MOVE uses its real rng_event."
updated = "2026-07-06T16:11:27.114Z"

[[record]]
name = "trace-byte-determinism"
file = "liveplay/golden_trace.py"
confidence = "settled"
rationale = "Traces contain no timestamps; JSON uses sort_keys; gzip written via gzip.compress(mtime=0) so .gz files carry no mtime/filename. Same seed => byte-identical file, enabling cheap corpus diffing and dedup."
updated = "2026-07-06T16:11:34.937Z"

[[record]]
name = "turn1-snapshot-omitted"
file = "liveplay/golden_trace.py"
confidence = "settled"
rationale = "Snapshots are emitted at AWAIT_ACTIONS pauses only for turn>1 (turn % snapshot_every == 0); turn 1 state equals the header's initial_state so a snapshot there is redundant. record_game returns the end record for caller logging."
updated = "2026-07-06T16:11:35.996Z"

[[record]]
name = "transient_oracle_answers"
file = "engine/src/oracle.h"
confidence = "settled"
rationale = "Resume answers are FIFO transient queues + replay cursors, NOT consume-once: pause/resume replays a whole region from snapshot, so earlier occurrences must re-get their answers. Cleared fail-loud at region end. Constructor overrides stay persistent."
updated = "2026-07-06T18:34:23.268Z"

[[record]]
name = "forced_trace_replay"
file = "engine/src/"
confidence = "settled"
rationale = "Forced replay: saturated draws (acc None/>=100 etc.) short-circuit BEFORE forced lookup — Python never records them, traces must omit them. Cat-A sites consume recorded answers in stream order inside random-mode branches; CONTROLLED path unchanged."
updated = "2026-07-07T00:34:03.594Z"

[[record]]
name = "volatiles_codec_asymmetry"
file = "engine/src/codec.cpp"
confidence = "settled"
rationale = "FIXED 8dc8387 (user-approved): codec.cpp encodes volatiles as plain int, matching Python's int bitfield (pokemon.py). Tagged Volatile enum form broke state-fingerprint parity. decode_enum_or_int still accepts both forms for old payloads."
updated = "2026-07-07T04:51:29.161Z"

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
name = "parity_corpus_species_prune"
file = "SCRIPTS/random_battle_fuzz.py"
confidence = "settled"
rationale = "Golisopod/Wimpod are pruned from all parity corpora (_parity_species_pool): their only ability is Emergency Exit/Wimp Out, whose mid-turn switch path is unported in C++ and double-residual-buggy (frozen) in Python. INTENTIONAL_DIVERGENCES #2."
updated = "2026-07-07T05:22:44.952Z"

[[record]]
name = "sub_move_field_presence"
file = "src/simulator.py"
confidence = "settled"
rationale = "Sub-move phase (Metronome/Sleep Talk) must register exp_participants field presence itself: sub-move detection exits _advance_queue BEFORE the normal update. Mirrors C++ turn.cpp; gap caused a golden-trace fingerprint mismatch (exp_participants)."
updated = "2026-07-07T05:22:51.995Z"

[[record]]
name = "golden_corpus_freeze"
file = "tests/fixtures/golden_traces/"
confidence = "requirement"
rationale = "User: 1000-game gate slice (seed 20260706) + 27 scenario_* rare-interaction traces (record_scenario_traces.py) in-repo, run via test_golden_trace_corpus.py (slow, ~6s). 100k local corpus (seed 20260707, gitignored) verified before milestones."
updated = "2026-07-07T16:50:41.101Z"

[[record]]
name = "rng_inject_single_occurrence"
file = "src/simulator.py"
confidence = "settled"
rationale = "FIXED: transient Cat-A events (Effect Spore/Tri Attack/Acupressure/Moody/Starf) inject as per-event QUEUES; each answer consumed once, next same-event occurrence pauses for a fresh answer. Scalar injects (sweep pre-injects, SPEED_TIE) unchanged."
updated = "2026-07-07T17:56:31.818Z"

[[record]]
name = "forced_trace_mega_threading"
file = "src/cpp_bridge.py"
confidence = "settled"
rationale = "action_payload carries Action.mega; GameDriver folds per-side any(mega) into run_one_turn mega_pX scalars (fresh turn only — resume skips _begin_turn where mega applies). Without this, replayed traces never mega-evolve (1000-corpus divergence)."
updated = "2026-07-07T06:22:08.944Z"

[[record]]
name = "transition_golden_retired"
file = "tests/"
confidence = "requirement"
rationale = "User (2026-07-06): retire the transition_golden B1 lock-in fixture (test, fixture, gen script deleted). The golden-trace corpus supersedes it; it was seed-fragile and forced regeneration on any generator change."
updated = "2026-07-07T06:22:15.270Z"

[[record]]
name = "no_target_move_fails"
file = "src/engine/core.py"
confidence = "settled"
rationale = "Moves (damaging AND status) with no live target fail (MOVE_FAIL no_target) BEFORE any rolls via draw-free _move_has_target; side/field/self targets exempt. Guard sits before the STATUS dispatch. C++ mirror: cpp_move_has_target."
updated = "2026-07-08T05:47:40.353Z"

[[record]]
name = "doubles_faint_showdown_gen8"
file = "src/engine/core.py"
confidence = "requirement"
rationale = "User (2026-07-07): doubles moves into a slot that fainted mid-turn follow Showdown Gen 8 — single-target retargets to survivor, spread skips corpse, fail only when no live target. Fixed-damage moves resolve targets too (were hitting slot 0 blindly)."
updated = "2026-07-08T05:47:49.749Z"

[[record]]
name = "apply_damage_fainted_raises"
file = "src/engine/_helpers.py"
confidence = "settled"
rationale = "_apply_damage / cpp_apply_damage raise on an already-fainted defender: no legit path damages a corpse post no-target+doubles fixes; silent corpse damage caused the Focus Band revival divergence class. Fail loudly over corrupting state."
updated = "2026-07-08T05:47:52.413Z"

[[record]]
name = "charging_move_payload_volatile"
file = "liveplay/state/pokemon.py"
confidence = "settled"
rationale = "CHARGING_MOVE(34) stores the charged move id ONLY when it differs from the slot move (Metronome/Copycat two-turn); conditional keeps normal two-turn traces byte-identical. Mirrors Showdown twoturnmove.onLockMove. Tick-exempt; cleared on switch."
updated = "2026-07-08T05:48:27.466Z"
