[[record]]
name = "doubles_target_slot_simplified"
file = "engine/src/ai_damage.cpp"
confidence = "provisional"
rationale = "Doubles target-slot expansion duplicates MOVE actions (target_slot=1 at 50/50 probability share) but scores both against the same first opponent. Full per-target scoring needs _build_damage_context keyed by (move_slot, target_slot)."
updated = "2026-06-07T20:45:45.201Z"

[[record]]
name = "switch_candidate_bug"
file = "engine/src/ai_scorer.cpp"
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
file = "liveplay/sweep_run.py"
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
file = "liveplay/sweep_secondaries.py"
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
file = "liveplay/sweep_run.py"
confidence = "requirement"
rationale = "Sweep base SWEEP_LUCK=BAD_LUCK+warn_uninjected, thresholds tuned so every Category-B event defaults to its NO-message (silent) outcome: ACCURACY/PARALYSIS/ATTRACT/CONFUSION_SELF_HIT flipped to 0.0. Uninjected events log a WARNING, never raise."
updated = "2026-06-19T15:41:55.225Z"

[[record]]
name = "category_a_pauses_strict"
file = "liveplay/sweep_run.py"
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
name = "mover_list_no_fallback"
file = "liveplay/sweep_run.py"
confidence = "requirement"
rationale = "_build_mover_list returns the observed USEDMOVE side order verbatim; with no observed USEDMOVE it returns [] and the sweep yields no candidates (SimulationError), never falling back to a guessed mover order."
updated = "2026-06-11T18:11:21.081Z"

[[record]]
name = "sweep_own_damage_dedup"
file = "liveplay/sweep_run.py"
confidence = "requirement"
rationale = "Single-hit movers dedup their 16 rolls by the mover's OWN damage (_own_damage keyed on attacker_side/slot), not cumulative damage to the target. Maximizes per-attack granularity and shrinks the candidate space."
updated = "2026-06-11T18:11:21.120Z"

[[record]]
name = "rng_sequence_interleaved"
file = "liveplay/sweep_run.py"
confidence = "requirement"
rationale = "Candidate.rng_sequence is interleaved per mover: (DAMAGE_ROLL, roll),(CRIT, crit) for each mover in observed order, then a trailing (SPEED_TIE). Every mover gets a pair (even non-damaging); multi-hit movers' entries are per-hit tuples."
updated = "2026-06-11T18:11:21.159Z"

[[record]]
name = "multi_hit_in_loop"
file = "liveplay/sweep_run.py"
confidence = "requirement"
rationale = "Movers enumerated by ONE unified fn _enumerate_mover_rolls (single-hit=n_hits 1, multi-hit=n_hits>1), inside the mover loop at the acting iteration via a PartialCandidate (not a separate phase). apply_hp_prune (n_hits>1 only) gates HP-delta pruning."
updated = "2026-06-17T15:49:49.895Z"

[[record]]
name = "crit_attribution_by_message"
file = "liveplay/sweep_run.py"
confidence = "requirement"
rationale = "Crits are attributed per-mover by which USEDMOVE directly preceded each CRITICALHIT message (_message_crit_counts_with_state), not a global count by position. Multi-hit moves use their own attributed count for which-hit enumeration."
updated = "2026-06-11T18:11:36.963Z"

[[record]]
name = "post_faint_empty_mover_branch"
file = "liveplay/sweep_run.py"
confidence = "provisional"
rationale = "When movers==[] and an active Pokemon has fainted, run_candidate_sweep runs one sim per action pair directly (no roll/crit enumeration, tie_winner=0) since a bare switch has no controllable RNG. Limitations tracked in TODO 2c."
updated = "2026-06-11T18:11:37.000Z"

[[record]]
name = "damage_event_attacker_identity"
file = "engine/src/move_exec_damage.cpp"
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
file = "liveplay/sweep_actions.py"
confidence = "requirement"
rationale = "Opponent faint+replacement is NOT a player decision boundary. Sweep auto-applies observed opponent switch-ins (ordered list, one per faint round, doubles-ready); stops only on player battle menu (AWAIT_ACTIONS) or party-select (switches_needed[0])."
updated = "2026-06-13T18:34:45.665Z"

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
file = "liveplay/sweep_secondaries.py"
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
file = "liveplay/sweep_actions.py"
confidence = "settled"
rationale = "_extract_known_actions pairs each faint with the next same-side switch-in (pending_faint counters) and skips it: forced post-faint replacements go via opp_switch_actions, not as actions. Counting twice withdrew the doomed mon pre-faint. Doubles-safe."
updated = "2026-06-13T22:59:56.371Z"

[[record]]
name = "multihit_per_hit_sampling"
file = "liveplay/sweep_run.py"
confidence = "settled"
rationale = "Multi-hit damage discovery samples each hit alone: vary hit i's roll, pin others to min roll so target survives for hit i. Uniform rolls KO early, drop the count, and hide higher per-hit damage. Damage is HP-independent, so isolated rolls recombine."
updated = "2026-06-13T23:06:29.308Z"

[[record]]
name = "multihit_ko_overkill"
file = "liveplay/sweep_run.py"
confidence = "settled"
rationale = "Multi-hit cumulative HP-delta filter: a KO reading (new_val==0) drops the upper bound since the killing blow may overkill; only the lower bound (damage reaches 0) applies. Applies to BOTH opponent pixel-range and player exact-HP branches."
updated = "2026-06-13T23:12:03.777Z"

[[record]]
name = "movers_side_slot_tuples"
file = "liveplay/sweep_run.py"
confidence = "settled"
rationale = "movers is list[tuple[int,int]] of (side, source_slot) in execution order, index-aligned with per-mover rolls/crits/hit_counts. source_slot is the acting active-slot position, inferred from USEDMOVE order via _message_action_order_with_state."
updated = "2026-06-14T02:00:47.943Z"

[[record]]
name = "target_slot_from_deltas"
file = "liveplay/sweep_run.py"
confidence = "requirement"
rationale = "Doubles target inference: a single-target damaging move's target_slot is constrained to the foe slots that lost HP (turn-order matched). No damage calc; wrong assignments are filtered by the per-slot HP check and fail loud if none survive."
updated = "2026-06-14T02:00:53.678Z"

[[record]]
name = "per_mover_multi_hit"
file = "liveplay/sweep_run.py"
confidence = "requirement"
rationale = "Supports two multi-hit movers in one doubles turn: mover_hit_counts is a per-mover list[int] index-aligned with movers; entries >1 trigger _enumerate_multi_hit_rolls for that mover. Spread+multi-hit combined is deferred and fails loud."
updated = "2026-06-14T02:00:53.720Z"

[[record]]
name = "doubles_secondary_single_move"
file = "liveplay/sweep_actions.py"
confidence = "settled"
rationale = "GAP CLOSED: secondaries are attributed per (side, slot). Messages are segmented by USEDMOVE (names user to source_slot) and effects attributed to the recipient named in the effect message; SECONDARY_FIRES/PROC_FIRES injected as per-slot dicts."
updated = "2026-06-14T05:35:59.434Z"

[[record]]
name = "flinch_via_secondary_fires"
file = "liveplay/sweep_secondaries.py"
confidence = "requirement"
rationale = "All move-flinch (flinch-only secondaries and Fang secondary2) resolves via RNGEvent.FLINCH (attacker luck), not SECONDARY_FIRES; forced on hitter slot if observed, else enumerated under FLINCH. SECONDARY_FIRES=status/stat/confusion only."
updated = "2026-06-15T19:40:22.695Z"

[[record]]
name = "action_order_from_move_use"
file = "liveplay/sweep_actions.py"
confidence = "requirement"
rationale = "_check_action_order compares observed USEDMOVE order against the side sequence of captured MOVE_USE events, NOT state.turn_order. turn_order includes mons slated to act but that never moved (flinch/para/sleep), mismatching mid-order in doubles."
updated = "2026-06-14T05:36:33.554Z"

[[record]]
name = "proc_injection_from_by_msg"
file = "liveplay/sweep_secondaries.py"
confidence = "settled"
rationale = "Ability/item procs (Static etc.) are injected from PKMNWAS*BY status messages: the afflicted name is the LAST var_value (layout [source, ability, target]). PROC_FIRES is forced per-slot on the afflicted target (the attacker for contact-punish)."
updated = "2026-06-14T05:36:44.352Z"

[[record]]
name = "secondary_combo_no_cap"
file = "liveplay/sweep_secondaries.py"
confidence = "requirement"
rationale = "No cap on flinch combo count: old guard removed, total combo count printed. Flinch combos keyed per (side, slot, RNGEvent.FLINCH) over non-attributable (flinch-only) movers, excluding slots already force-injected from an observed flinch."
updated = "2026-06-15T19:40:36.221Z"

[[record]]
name = "move_use_logs_side"
file = "engine/src/move_exec.cpp"
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
file = "liveplay/sweep_secondaries.py"
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
file = "liveplay/sweep_reconcile.py"
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
file = "liveplay/sweep_secondaries.py"
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
file = "liveplay/sweep_run.py"
confidence = "requirement"
rationale = "Sweep validates HP deltas by mon IDENTITY, not slot. run_candidate_sweep takes hp_deltas: list[HpDeltaSeq] binding (before,after) to (side,species). _check_hp_match resolves species vs result-state team (follows switches); raises if unknown/dup."
updated = "2026-06-14T21:04:15.491Z"

[[record]]
name = "tib_counts_initiators"
file = "engine/src/residuals.cpp"
confidence = "settled"
rationale = "turns_in_battle increments at end of turn ONLY for mons active at turn start (ctx.turn_start_active, set in _begin_turn). Mid-turn switch-ins skip the entry turn, so Fake Out/Mat Block/Speed Boost fire on first INITIATED turn. ctx unset => count all."
updated = "2026-06-14T21:52:37.187Z"

[[record]]
name = "multihit_stops_on_atk_faint"
file = "engine/src/move_exec_damage.cpp"
confidence = "settled"
rationale = "Multi-hit moves end if the attacker faints mid-sequence (e.g. contact recoil like Rough Skin/Rocky Helmet), matching the game's 'Hit N time(s)!' count. Loop breaks on attacker.fainted."
updated = "2026-06-14T22:26:54.803Z"

[[record]]
name = "miss_still_acted_inject"
file = "liveplay/sweep_secondaries.py"
confidence = "settled"
rationale = "Matcher injects only VISIBLE failure outcomes; a used move that hit or missed needs no can-act injection. SWEEP_LUCK silent-defaults para/attract/confusion to can-act and accuracy to hit, so acted/missed mons fall through without injection."
updated = "2026-06-19T15:42:33.246Z"

[[record]]
name = "confusion_apply_keys_became"
file = "liveplay/sweep_reconcile.py"
confidence = "settled"
rationale = "check_log_events confusion VOLATILE_APPLY constraint keys on STRINGID_PKMNWASCONFUSED ('became confused!'), not PKMNISCONFUSED ('is confused!', per-turn reminder). The reminder fires every turn a confused mon acts; keying on it pruned all candidates."
updated = "2026-06-14T23:01:19.236Z"

[[record]]
name = "trust_observed_levelups"
file = "liveplay/sweep_reconcile.py"
confidence = "settled"
rationale = "Sweep trusts OCR PKMNGREWTOLV: level-up check requires sim levels be a sub-multiset of observed (tolerates low live-seed extras, prunes sim-invented); _apply_observed_levelups forces player mons up to observed level so carried state stays consistent."
updated = "2026-06-15T00:38:29.342Z"

[[record]]
name = "stress_failure_outcome"
file = "SCRIPTS/stress_test.py"
confidence = "requirement"
rationale = "A team that cannot win the position (no winning luck tier) raises TeamFailureError, recorded as the FAILURE outcome; unlike other non-OK outcomes the loop continues so the run isn't aborted."
updated = "2026-06-15T05:01:22.877Z"

[[record]]
name = "psywave_injectable_roll"
file = "engine/src/move_exec_damage.cpp"
confidence = "settled"
rationale = "Psywave damage uses injectable RNGEvent.PSYWAVE_ROLL (0..1) mapped to 50+round(r*100) pct of level damage, mirroring DAMAGE_ROLL; _compute_fixed_damage takes luck_atk. Sweep mirrors s.roll into PSYWAVE_ROLL so its range enumerates like normal damage."
updated = "2026-06-15T19:40:54.323Z"

[[record]]
name = "fixed_damage_attacker_identity"
file = "engine/src/move_exec_damage.cpp"
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
file = "engine/src/post_hit.cpp"
confidence = "requirement"
rationale = "Burn Up drops the Fire type entirely (dual-type keeps remaining types; mono-Fire becomes (Type.TYPELESS,), never NORMAL). Emits LogEvent.TYPE_CHANGE source=burn_up with old/new types. (user decisions 2026-06-15)"
updated = "2026-06-15T20:23:10.124Z"

[[record]]
name = "dynamic_turn_queue"
file = "engine/src/core_leaf.cpp"
confidence = "settled"
rationale = "Turn order is dynamic: after each action the next un-acted actor is re-selected via _select_next_action, recomputing priority bracket + speed from current state (Showdown speedSort). turn_order appended incrementally; QC/Custap resolved at build."
updated = "2026-06-15T22:11:08.992Z"

[[record]]
name = "quick_claw_dedicated_event"
file = "engine/src/core_leaf.cpp"
confidence = "settled"
rationale = "Quick Claw uses RNGEvent.QUICK_CLAW + quick_claw_threshold (resolve_quick_claw, 20%), decoupled from secondary_threshold. On proc bumps holder to front-of-bracket (speed=9999), gated priority<=0, emits QUICK_CLAW_ACTIVATE. Custap stays deterministic."
updated = "2026-06-15T22:11:29.249Z"

[[record]]
name = "quick_claw_observed_pinning"
file = "liveplay/sweep_run.py"
confidence = "settled"
rationale = "Quick Claw observed via STRINGID_QUICKCLAWACTIVATE: pin QUICK_CLAW=True per holder slot when seen, else False for QC holders that used a priority<=0 move with no QC message (always shown on proc). Keyed on used-priority0 slots only. No enumeration."
updated = "2026-06-15T22:11:47.849Z"

[[record]]
name = "struggle_recoil"
file = "engine/src/post_hit.cpp"
confidence = "requirement"
rationale = "Struggle recoil = max(1, user.max_hp//4), a dedicated post_hit branch (MOVE_DATA recoil stays None). Magic Guard blocks it; Rock Head does NOT (matches Showdown struggleRecoil). Logged DAMAGE source=recoil. (user decisions 2026-06-15)"
updated = "2026-06-15T22:41:00.571Z"

[[record]]
name = "battle_start_sendout_forced"
file = "liveplay/sweep_actions.py"
confidence = "settled"
rationale = "_extract_known_actions skips both sides' send-outs when STRINGID_INTROMSG is in the batch: opening lead-ins are forced, not voluntary. Recording them tripped the opponent-action filter (switch p=0 vs move preds) and crashed the sweep."
updated = "2026-06-16T17:21:47.081Z"

[[record]]
name = "hitcount_side_attrib"
file = "liveplay/sweep_actions.py"
confidence = "settled"
rationale = "HITXTIMES count filters HITCOUNT by attacker SIDE (USEDMOVE 'Foe' prefix via _msg_is_foe), not species alone; species-only conflated both mons in same-species mirrors. core.py logs HITCOUNT with side=side_idx."
updated = "2026-06-16T17:21:51.466Z"

[[record]]
name = "opp_action_filter"
file = "liveplay/sweep_actions.py"
confidence = "requirement"
rationale = "_validate_known_opponent_action filters a candidate if an OCR-identified opponent action had p=0 in compute_action_probabilities (per-candidate UnexpectedOpponentActionError; all-filtered => no survivors). Surfaces AI prediction gaps as crashes."
updated = "2026-06-16T17:21:55.172Z"

[[record]]
name = "battle_start_no_enum"
file = "liveplay/sweep_run.py"
confidence = "requirement"
rationale = "Opening sweep (STRINGID_INTROMSG) short-circuits: neither side acted, so emit each lead state unchanged as one child candidate, no enumeration/sim. Enumeration invented opponent switch->bench branches that diverged observed active, crashing sweep."
updated = "2026-06-16T18:05:03.585Z"

[[record]]
name = "multi_hit_aware_damage"
file = "engine/src/ai_damage.cpp"
confidence = "requirement"
rationale = "Query+AI KO/damage decisions must use expected_damage (multi-hit aware), not single-hit calculate_damage; calculate_damage stays single-hit for the engine's per-hit loop. Undercounting Double Slap made the AI mispredict and crash the sweep."
updated = "2026-06-16T18:47:39.773Z"

[[record]]
name = "setup_routing_self_only"
file = "engine/src/ai_scorer_dist.cpp"
confidence = "requirement"
rationale = "Offensive-setup scoring (_dist_setup via SETUP+STATUS tag) only applies to target==SELF moves. Opponent-targeting moves (Swagger, Flatter, Curse, Decorate) are confusion/debuffs, not self-buffs; routing them as setup gave p=0 and crashed the sweep."
updated = "2026-06-16T19:16:00.953Z"

[[record]]
name = "kill_bonus_joint_highest"
file = "engine/src/ai_scorer_dist.cpp"
confidence = "requirement"
rationale = "KO bonus is computed jointly with highest-damage odds on the same damage roll (correlated), using uncapped damage for KO. Kill bonus applies only when the move is also highest-damage. Replaces the buggy max-roll guaranteed-kill flag."
updated = "2026-06-16T20:43:40.476Z"

[[record]]
name = "belch_excluded_from_rank"
file = "engine/src/ai_damage.cpp"
confidence = "requirement"
rationale = "Belch is skipped in _build_damage_context when consumed_berry==NONE (unusable per engine core.py:1571), so it falls to the status-branch scorer instead of being ranked at 120 BP and predicted as the opponent's move."
updated = "2026-06-16T22:58:54.286Z"

[[record]]
name = "analytical_joint_roll_enum"
file = "engine/src/ai_analytic.cpp"
confidence = "settled"
rationale = "compute_action_probabilities enumerates all 16^m damage-roll combos using the same capped-rank/uncapped-kill formula as _sample_highest_slots, so analytical and sim paths agree. Co-highest moves share p_highest; switches excluded from enumeration."
updated = "2026-06-16T22:59:02.482Z"

[[record]]
name = "voluntary_switch_single_tgt"
file = "engine/src/ai_scorer.cpp"
confidence = "requirement"
rationale = "Voluntary switch gives the full 0.5 to ONE Cond2-filtered post-KO target (not split across benches); switches get 0 otherwise. HP gate is >=50% (not strict >). Target selection replicates the found_faster Cond2 bug."
updated = "2026-06-16T22:59:03.927Z"

[[record]]
name = "forced_switch_post_ko_check"
file = "liveplay/sweep_actions.py"
confidence = "requirement"
rationale = "Forced post-faint opponent switch-ins (fainted active) skip the beginning-of-turn compute_action_probabilities check; _validate_forced_opponent_switch strictly asserts send-out equals select_post_ko_switch (singles only)."
updated = "2026-06-16T23:35:08.189Z"

[[record]]
name = "per_roll_damage_index_override"
file = "engine/src/damage.cpp"
confidence = "settled"
rationale = "calculate_damage takes opt-in roll_index (0..15) for an exact roll; roll applied before STAB/type with flooring, so per-roll damage is nonlinear (Wing Attack 8x15 then 12), not a linear rescale of max. Default callers unchanged."
updated = "2026-06-17T01:23:54.357Z"

[[record]]
name = "ai_true_per_roll_damage"
file = "engine/src/ai_damage.cpp"
confidence = "settled"
rationale = "AI scoring uses true 16-element per-roll damage arrays from damage_roll_values, not max_damage*(85+r)//100 rescale. The old rescale collapsed low rolls upward, hiding marginal-KO branches and giving status moves p=0 (crashed sweeps)."
updated = "2026-06-17T01:23:58.855Z"

[[record]]
name = "harvest_proc_side_hint"
file = "liveplay/sweep_secondaries.py"
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
file = "liveplay/sweep_secondaries.py"
confidence = "settled"
rationale = "Matcher injects ATTRACT_IMMOBILIZE only on an observed PKMNIMMOBILIZEDBYLOVE message (=False, immobilized). SWEEP_LUCK's silent default is can-act, so an infatuated mon that acted needs no injection. Old PKMNINLOVE-keyed can-act reconstruction gone."
updated = "2026-06-19T15:42:38.596Z"

[[record]]
name = "multihit_heal_segmenting"
file = "liveplay/sweep_run.py"
confidence = "requirement"
rationale = "HP-delta walk segments bar readings at heal deltas (to>from): a heal resets the cumulative anchor, consumes no hit. Heal legitimacy is NOT judged here (no message-count guard); _hp_count_detail decides via observed-vs-sim HP-delta sequence match."
updated = "2026-06-23T20:15:31.122Z"

[[record]]
name = "fixed_damage_hd_ranking"
file = "engine/src/ai_scorer_dist.cpp"
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
file = "liveplay/sweep_run.py"
confidence = "requirement"
rationale = "Per-hit damage discovery keys on the ATTACKER (side+team-slot) via _attacker_per_hit_damages, not the defender's pre-turn species. Switch-robust: a mid-turn switch-in leaves the old species stale; the attacker is fixed. Single+multi-hit both use it."
updated = "2026-06-17T15:50:16.798Z"

[[record]]
name = "single_hit_scalar_override"
file = "liveplay/sweep_run.py"
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
file = "engine/src/exp.cpp"
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
file = "liveplay/sweep_secondaries.py"
confidence = "settled"
rationale = "Per-mon message-driven overrides (FULL_PARALYSIS, ACCURACY, ATTRACT_IMMOBILIZE, CONFUSION_SNAP/SELF_HIT, MULTI_HIT_COUNT) written per-slot keyed by acting slot in doubles, scalar in singles. Global scalar let two same-turn movers clobber each other."
updated = "2026-06-19T15:42:53.604Z"

[[record]]
name = "prev_turn_order_field"
file = "liveplay/state/battle.py"
confidence = "settled"
rationale = "prev_turn_order holds the PREVIOUS turn's move order (captured in simulator._finalize_turn), so AI scoring can replicate Bug #8 (AI judges order-dependent damage by last turn's order). MUST stay in __hash__; empty () on turn 1."
updated = "2026-06-18T18:26:08.113Z"

[[record]]
name = "ai_scoring_view_prev_turn"
file = "engine/src/damage.cpp"
confidence = "requirement"
rationale = "calculate_damage's ai_scoring_view replicates Bug #8: when True, Analytic (1.3x) is judged by prev_turn_order, not the current turn. Engine default False stays current-turn-correct (core.py _compute_variable_bp is the engine path)."
updated = "2026-06-18T18:26:34.965Z"

[[record]]
name = "ai_damage_prev_turn_screens"
file = "engine/src/ai_damage.cpp"
confidence = "requirement"
rationale = "expected_damage drives AI scoring with ai_scoring_view=True: Analytic/Payback/Bolt Beak/Fishious Rend judged by prev_turn_order (Bug #8). Also passes def_side_idx so screens+Friend Guard now apply in AI scoring (in-game calc factors screens)."
updated = "2026-06-18T18:26:46.604Z"

[[record]]
name = "rollout_switch_in_480bp"
file = "engine/src/ai_damage.cpp"
confidence = "requirement"
rationale = "rollout_max_bp (on expected_damage/can_ko/best_damage_move) reads Rollout at max 480 BP, replicating Bug #25 (switch-in AI sees Rollout as 480 BP). Passed True ONLY by switch scoring, ONLY for Rollout; active-move scoring stays flat +7."
updated = "2026-06-18T18:26:57.576Z"

[[record]]
name = "coaching_doubles_scoring"
file = "engine/src/ai_scorer_dist.cpp"
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
file = "engine/src/move_exec_guards.cpp"
confidence = "requirement"
rationale = "Opponent-targeting STATUS moves miss a semi-invuln target (emit MOVE_MISS) like the damaging path. No Guard (either side) bypasses the miss on both paths and the Magic Bounce branch. Other bypasses (Toxic/Gust/Thunder/Gravity) are out of scope."
updated = "2026-06-18T20:08:03.127Z"

[[record]]
name = "status_type_immune_electric"
file = "engine/src/move_exec_guards.cpp"
confidence = "requirement"
rationale = "Type-chart immunity for STATUS moves is scoped to Electric moves vs Ground (Thunder Wave) only. Broader 0x type immunity is intentionally NOT applied to status moves (Ghost Curse vs Normal still works). Mold Breaker does not bypass type immunity."
updated = "2026-06-18T20:08:12.992Z"

[[record]]
name = "status_substitute_gate"
file = "engine/src/move_exec_guards.cpp"
confidence = "requirement"
rationale = "Opponent-targeting STATUS effects are blocked by an active Substitute, bypassed only by SOUND-tagged moves, the Infiltrator ability, and Move.PLAY_NICE (its documented special case). Growl is SOUND-tagged so it bypasses Sub."
updated = "2026-06-18T20:08:16.455Z"

[[record]]
name = "status_path_guard_parity"
file = "engine/src/move_exec_guards.cpp"
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
name = "fuzzy_match_display_name"
file = "liveplay/sweep_driver.py"
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
file = "engine/src/move_exec_premove.cpp"
confidence = "settled"
rationale = "Two-turn moves spend PP only on the charge turn. PP block gated by _two_turn_release (charging_move_slot==effective_slot, still set on release turn before _handle_pre_damage_checks clears it). Stops inferred opp PP draining 2x."
updated = "2026-06-19T07:45:37.845Z"

[[record]]
name = "fake_out_bonus_stacks"
file = "engine/src/ai_scorer_dist.cpp"
confidence = "requirement"
rationale = "Fake Out scores as a normal damaging move (HD odds + kill bonus) with +9 STACKED on top (like Acid Spray's +6) when first-turn, target lacks Shield Dust/Inner Focus, and not type-immune; else -40. Flat +9 made a KOing Fake Out lose to rival KO moves."
updated = "2026-06-19T16:55:47.482Z"

[[record]]
name = "player_damage_no_crit"
file = "engine/src/ai_scorer.cpp"
confidence = "requirement"
rationale = "AI player-damage threat checks never assume crits (AI.md de-crits the player's highest roll). Recovery/nhko/Belly Drum use AVERAGE_LUCK; post-KO switch checks use _MAX_DAMAGE_LUCK to match neighbors. GOOD_LUCK (forced crit) removed."
updated = "2026-06-19T17:32:30.793Z"

[[record]]
name = "gen_training_source"
file = "SCRIPTS/nn_iterative_train.py"
confidence = "requirement"
rationale = "Generated battles REPLACE fixed fixtures as training source; real fixtures (Test3) are validation-only. Curriculum label_fn generates a fresh batch each round from the current model's value head so difficulty adapts. User decision."
updated = "2026-06-20T20:23:48.351Z"

[[record]]
name = "gap_species_manual"
file = "liveplay/data/generated_abilities.json"
confidence = "requirement"
rationale = "CELEBI/STARYU/STARMIE/DURALUDON have NO ability lines in the RnB source txt; abilities were filled in MANUALLY in this JSON. Re-running extract_abilities.py blindly WIPES them (resets to empty -> excluded from pool). Pool=554."
updated = "2026-06-21T00:15:56.361Z"

[[record]]
name = "struggle_no_pp_spend"
file = "engine/src/move_exec_premove.cpp"
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
file = "liveplay/sweep_reconcile.py"
confidence = "settled"
rationale = "_check_hp_match same-species: a delta ending at 0 (faint) prefers the matching mon with hp==0, not the active-slot mon. A same-species faint+replacement puts the replacement in the active slot, so slot matching falsely rejects the faint (Issue 29)."
updated = "2026-06-21T20:57:27.510Z"

[[record]]
name = "per-survivor prune log"
file = "liveplay/sweep_reconcile.py"
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
file = "liveplay/sweep_actions.py"
confidence = "settled"
rationale = "Metronome AND Sleep Talk collapse via _collapse_metronome_calls (shared 2-USEDMOVE/1-MOVE_USE shape); injection routes to METRONOME_MOVE or SLEEP_TALK_MOVE keyed on the wrapper via _CALLED_MOVE_EVENTS. Add new wrappers to that map, not a parallel fn."
updated = "2026-06-22T22:17:40.445Z"

[[record]]
name = "action_order_prefix_floor"
file = "liveplay/sweep_actions.py"
confidence = "settled"
rationale = "_check_action_order requires sim MOVE_USE sides == observed prefix AND len(sim)>=len(observed). Sim is legitimately LONGER (MOVE_USE for unobserved opponent moves), so only a SHORTER sim prunes. Collapse called-move wrappers first or 2:1 over-prunes."
updated = "2026-06-22T22:17:55.939Z"

[[record]]
name = "single_hit_no_enum_constraint"
file = "liveplay/sweep_run.py"
confidence = "settled"
rationale = "Single-hit movers keep ALL damage values at enum time; only multi-hit applies the per-hit cumulative constraint. Enum sim omits final-sim secondary RNG, so a single-hit enum constraint false-over-prunes (B1 pt2 deferred)."
updated = "2026-06-23T20:15:36.391Z"

[[record]]
name = "dedup_by_state_not_hash"
file = "liveplay/sweep_run.py"
confidence = "settled"
rationale = "Sweep candidate dedup stores BattleState objects in a set (collision-proof via __eq__), NOT hash(rs) ints. A 64-bit hash collision would silently drop a distinct candidate (F2). Don't revert to storing hashes."
updated = "2026-06-22T22:18:15.734Z"

[[record]]
name = "event_side_attribution"
file = "liveplay/sweep_reconcile.py"
confidence = "settled"
rationale = "check_log_events attributes STATUS/STAT_BOOST/VOLATILE events by matching engine event side (=side_idx) vs the observed side from _msg_is_foe ('Foe ' prefix) plus species via emulator_species_name. Collision-proof in mirrors; keep the side filter."
updated = "2026-06-22T22:18:27.316Z"

[[record]]
name = "slot_map_single_pass"
file = "liveplay/sweep_run.py"
confidence = "settled"
rationale = "One _build_attacker_slot_map cursor pass assigns (side,slot) per USEDMOVE msg id; consumers do slot_map.get(id(msg)) and SKIP on miss (no per-consumer cursor). Prevents action-extraction vs order-validation cursor disagreement (D3 parity)."
updated = "2026-06-22T22:18:36.683Z"

[[record]]
name = "unreproducible_move_filter"
file = "liveplay/sweep_actions.py"
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
file = "liveplay/sweep_reconcile.py"
confidence = "settled"
rationale = "check_log_events no-opponent-deltas guard sums ALL move damage to defender_side=1 (_total_side_move_damage), not just opp_species/slot-0, so doubles slot-1 opponents of another species are constrained (E2). opp_species kept as known-opponent gate."
updated = "2026-06-22T22:53:06.423Z"

[[record]]
name = "damage_attacker_slot_via_swap"
file = "engine/src/move_exec_damage.cpp"
confidence = "settled"
rationale = "Move-damage DAMAGE uses attacker_slot=active_indices[0]; CORRECT in doubles because _handle_damage_loop runs inside _active_slot_swapped(side, source_slot), swapping the acting mon's team index into slot 0. Do not 'fix' to a hardcoded slot (G1)."
updated = "2026-06-22T22:53:25.319Z"

[[record]]
name = "berry_consume_corroboration"
file = "liveplay/sweep_reconcile.py"
confidence = "settled"
rationale = "check_log_events matches observed berry-restore messages (berry-only string ids) one-for-one per side vs sim HEAL source='berry', pruning rolls that trip/skip a berry even when final HP coincides (B1 pt2). Side via msg.side_hint."
updated = "2026-06-23T00:16:58.787Z"

[[record]]
name = "berry_heal_side_kwarg"
file = "engine/src/effects.cpp"
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
file = "engine/src/move_exec_premove.cpp"
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
file = "liveplay/sweep_reconcile.py"
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
file = "liveplay/sweep_run.py"
confidence = "settled"
rationale = "Same-species ambiguity is reduced then fanned out into branches pruned by validation: switch-ins via _opponent_switch_in_actions->list[tuple], attackers via _build_attacker_slot_maps->list[dict]. Capped at _SWEEP_BRANCH_CAP=1000, fail loud."
updated = "2026-06-23T14:18:15.558Z"

[[record]]
name = "recipient_slot_hp_reduction"
file = "liveplay/sweep_actions.py"
confidence = "settled"
rationale = "_slot_for_name reduces same-species recipient ambiguity by per-slot HP delta (flinch/damage recipient changed HP), else raises. _inject_non_move_rng resolves attacker pos via slot_map for doubles parity, not the raising _slot_for_name."
updated = "2026-06-23T14:18:19.342Z"

[[record]]
name = "hp_delta_count_check"
file = "liveplay/sweep_reconcile.py"
confidence = "settled"
rationale = "Sweep checks COUNT of HP-bar transitions (observed vs sim), not just endpoint, to catch a phantom/extra residual tick a value-only check hides. Player=exact HP, opp=k-pixel. Consistency guard SKIPs (never false-prunes) on unaccounted HP changes."
updated = "2026-06-23T15:10:31.641Z"

[[record]]
name = "wrap_release_override"
file = "liveplay/sweep_reconcile.py"
confidence = "settled"
rationale = "Observed PKMNFREEDFROM ('freed from Wrap') is ground truth: _apply_observed_wrap_release clears BOUND+BOUND_SOURCE_SLOT on the named mon at turn start so a too-long carried duration roll can't keep it trapped or add a tick. Needs Foe side_hint."
updated = "2026-06-23T15:10:56.112Z"

[[record]]
name = "centralized_opponent_faint_exp"
file = "engine/src/exp.cpp"
confidence = "requirement"
rationale = "Opponent-faint EXP triggers from the faint itself, not a move/event path. flush_opponent_faint_exp scans side-1 active mons for fainted ones, called per causing-event. Simultaneous player faint => no EXP (skips fainted winners). Idempotent."
updated = "2026-06-23T16:50:45.760Z"

[[record]]
name = "move_exp_flush_after_recoil"
file = "engine/src/move_exec.cpp"
confidence = "requirement"
rationale = "Move-action opponent KOs award EXP via _flush_opponent_faint_exp at end of _execute_action, after the move body (incl. recoil) resolves. Covers attacker self-KO (Struggle/Double-Edge recoil) old inline paths missed. Switch path flushes too."
updated = "2026-06-23T16:50:57.347Z"

[[record]]
name = "residual_exp_flush_points"
file = "engine/src/residuals.cpp"
confidence = "requirement"
rationale = "Residual KOs award EXP after each battler's per-battler chain + after Future Sight; no inline distribute_exp. Residual flushes use allow_fainted_winners=True so a player fainted earlier keeps EXP from a later opponent KO. Idempotent, no double-award."
updated = "2026-06-25T17:54:35.055Z"

[[record]]
name = "Persistent calc server"
file = "SCRIPTS/ai_decision.py"
confidence = "requirement"
rationale = "User chose persistent Node server (AIDecision.js itself, no new JS, no Calculator.js changes): loads calc once, reused across calls so only first request pays startup. Returns both probs and damage rolls. Needed for a faster downstream script."
updated = "2026-06-24T05:47:56.040Z"

[[record]]
name = "residual_per_battler_order"
file = "engine/src/residuals.cpp"
confidence = "settled"
rationale = "Residuals process per-battler in fixed Speed order (fastest first); each battler runs its full chain (_BAND_TABLE + _LATE_PER_SLOT_HANDLERS, stop on faint) before the next. Within-battler order unchanged. Matches Emerald; fixes Unnerve phantom-heal."
updated = "2026-06-25T17:54:32.153Z"

[[record]]
name = "residual_order_fixed"
file = "engine/src/residuals.cpp"
confidence = "provisional"
rationale = "Per-battler residual order computed ONCE at phase start; mid-phase speed changes (Speed Boost) do NOT reorder remaining battlers this turn. Chosen for simplicity; unconfirmed vs dynamic order. Revisit if a dynamic-order case appears."
updated = "2026-06-25T17:54:33.578Z"

[[record]]
name = "faint_active_canonical_setter"
file = "engine/src/orchestrate.cpp"
confidence = "requirement"
rationale = "All faint sites route through faint_active(sides,side_idx,*,notify_soul_heart,slot). Idempotent (early-return if fainted). Does NOT own log(FAINT); callers keep it to preserve order. Hook for faint side-effects (trap release before soul-heart)."
updated = "2026-06-28T20:14:44.095Z"

[[record]]
name = "trap_release_pull_identity"
file = "engine/src/orchestrate.cpp"
confidence = "requirement"
rationale = "Traps release when inflictor leaves (faint OR switch). Inflictor id=team_idx in BOUND/TRAPPED_SOURCE_ID (side derived; cross-side). Eager release in faint_active + _apply_switch_out_reset. NO_RETREAT self-trap has no source id, never releases."
updated = "2026-06-28T20:14:55.429Z"

[[record]]
name = "switch_reset_releases_traps"
file = "engine/src/effects.cpp"
confidence = "settled"
rationale = "_apply_switch_out_reset(sides,side_idx,old_idx) is the shared switch-out choke-point (voluntary/forced/pivot/post-faint). After self-reset it calls release_inflicted_traps to free opponents the departed mon trapped."
updated = "2026-06-28T20:15:00.903Z"

[[record]]
name = "bound_tick_inflictor_skip"
file = "engine/src/residuals.cpp"
confidence = "settled"
rationale = "_band_late_damage skips the BOUND tick when BOUND_SOURCE_ID's inflictor is gone (inflictor_gone), covering an inflictor that faints earlier in the same residual phase before its slot reset. SOURCE_ID entries preserved in _res_tick (not decremented)."
updated = "2026-06-28T20:15:03.333Z"

[[record]]
name = "bad_dreams_faint_logging"
file = "engine/src/residuals.cpp"
confidence = "settled"
rationale = "Bad Dreams KO now logs DAMAGE+FAINT and fires Soul-Heart via faint_active (previously a silent inline HP write), making it consistent with all other residual faint paths."
updated = "2026-06-28T20:15:08.752Z"

[[record]]
name = "bound_counter_exact_ticks"
file = "engine/src/residuals.cpp"
confidence = "requirement"
rationale = "BOUND counter = EXACT ticks remaining (4/5/7). _band_late_damage ticks every turn counter>=1, incl the final counter==1 turn, so duration-N deals N ticks. On BOUND expiry, _res_tick_timed_volatiles strips its BOUND_SOURCE_SLOT/ID companions."
updated = "2026-06-28T21:27:14.744Z"

[[record]]
name = "sweep_assume_max_trap"
file = "liveplay/sweep_run.py"
confidence = "requirement"
rationale = "SWEEP_LUCK sets binding_duration_roll=rampage_duration_roll=1.0 so the sweep assumes MAX hidden duration (Bind=5, Thrash=3); Grip Claw still forces 7. Assuming shortest under-counts ticks and crashes on a real tick. Trimmed by observed end-messages."
updated = "2026-06-28T21:27:22.647Z"

[[record]]
name = "rampage_end_observed_trim"
file = "liveplay/sweep_reconcile.py"
confidence = "settled"
rationale = "_apply_observed_rampage_end (keyed on PKMNFATIGUECONFUSION, side_hint from B_ATK_NAME prefix) clears RAMPAGING+LOCKED_MOVE and sets CONFUSED on the named mon at turn start, trimming the assumed-max rampage. Mirrors _apply_observed_wrap_release."
updated = "2026-06-28T21:27:22.693Z"

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
file = "liveplay/sweep_actions.py"
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
file = "liveplay/cpp_driver.py"
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
name = "sortkey_neg_slot_prio0"
file = "engine/src/core_leaf.cpp"
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
file = "engine/src/ai_policy.cpp"
confidence = "requirement"
rationale = "Voluntary switch (user 2026-07-04): ALL move scores <= +5 (not -5), HP >= 50%, Cond2 candidate, singles; 50% gate. Priority over move scoring: SWITCH excluded from move tie-break. Target = Cond2-filtered post-KO scoring. Mirrored in cpp."
updated = "2026-07-04T16:03:33.036Z"

[[record]]
name = "faint_queue_no_rebuild_bug"
file = ""
confidence = "requirement"
rationale = "FIXED 2026-07-11 (C++): cpp_drain_faint_queue rebuilds via cpp_build_faint_queue each pass until no fainted active w/ live bench; hazard-killed replacements re-prompted. Forward-sim/solver only; sweep boundary unchanged. See FaintQueueBug.md."
updated = "2026-07-12T05:30:31.371Z"

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
file = "engine/src/damage.cpp"
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
name = "parity_corpus_species_prune"
file = "SCRIPTS/random_battle_fuzz.py"
confidence = "settled"
rationale = "Golisopod/Wimpod are pruned from all parity corpora (_parity_species_pool): their only ability is Emergency Exit/Wimp Out, whose mid-turn switch path is unported in C++ and double-residual-buggy (frozen) in Python. INTENTIONAL_DIVERGENCES #2."
updated = "2026-07-07T05:22:44.952Z"

[[record]]
name = "golden_corpus_freeze"
file = "tests/fixtures/golden_traces/"
confidence = "requirement"
rationale = "User: 1000-game gate slice (seed 20260706) + 27 scenario_* rare-interaction traces (record_scenario_traces.py) in-repo, run via test_golden_trace_corpus.py (slow, ~6s). 100k local corpus (seed 20260707, gitignored) verified before milestones."
updated = "2026-07-07T16:50:41.101Z"

[[record]]
name = "forced_trace_mega_threading"
file = "liveplay/cpp_driver.py"
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
file = "engine/src/move_exec_guards.cpp"
confidence = "settled"
rationale = "Moves (damaging AND status) with no live target fail (MOVE_FAIL no_target) BEFORE any rolls via draw-free _move_has_target; side/field/self targets exempt. Guard sits before the STATUS dispatch. C++ mirror: cpp_move_has_target."
updated = "2026-07-08T05:47:40.353Z"

[[record]]
name = "doubles_faint_showdown_gen8"
file = "engine/src/move_exec_guards.cpp"
confidence = "requirement"
rationale = "User (2026-07-07): doubles moves into a slot that fainted mid-turn follow Showdown Gen 8 — single-target retargets to survivor, spread skips corpse, fail only when no live target. Fixed-damage moves resolve targets too (were hitting slot 0 blindly)."
updated = "2026-07-08T05:47:49.749Z"

[[record]]
name = "apply_damage_fainted_raises"
file = "engine/src/move_exec_damage.cpp"
confidence = "settled"
rationale = "_apply_damage / cpp_apply_damage raise on an already-fainted defender: no legit path damages a corpse post no-target+doubles fixes; silent corpse damage caused the Focus Band revival divergence class. Fail loudly over corrupting state."
updated = "2026-07-08T05:47:52.413Z"

[[record]]
name = "charging_move_payload_volatile"
file = "liveplay/state/pokemon.py"
confidence = "settled"
rationale = "CHARGING_MOVE(34) stores the charged move id ONLY when it differs from the slot move (Metronome/Copycat two-turn); conditional keeps normal two-turn traces byte-identical. Mirrors Showdown twoturnmove.onLockMove. Tick-exempt; cleared on switch."
updated = "2026-07-08T05:48:27.466Z"

[[record]]
name = "stage_c_engine_liveplay_split"
file = ""
confidence = "requirement"
rationale = "User-approved Stage C layout: engine/ = C++ (src/bindings/tests/CMake), liveplay/ = Python live-play package, tests/SCRIPTS/RECORDS at top level. Clean git history, one commit per task, each gate-verified."
updated = "2026-07-08T19:39:05.217Z"

[[record]]
name = "greedy_search_dropped"
file = ""
confidence = "requirement"
rationale = "User: ignore greedy completely; it will be replaced by a better search method (planned RNG-bucketing guaranteed-win search). Greedy/MixedPolicy and src/search/ did not carry; stress_test runs 100% RandomPolicy."
updated = "2026-07-08T19:39:05.270Z"

[[record]]
name = "oversized_splits_stage_d"
file = ""
confidence = "requirement"
rationale = "Stage C carries files verbatim (identical behavior, new home); oversized-unit splits deferred to Stage D, where the trace-corpus gate protects splits equally well. User-approved over split-during-move."
updated = "2026-07-08T19:39:05.320Z"

[[record]]
name = "catch2_native_tests"
file = "engine/"
confidence = "settled"
rationale = "Native C++ tests use Catch2 v3.7.1 via FetchContent, linking the nuzlocke_core static lib (PIC); the pybind module stays a thin wrapper so tests build and run without Python. ctest target: native_tests."
updated = "2026-07-08T19:39:18.409Z"

[[record]]
name = "stage_e_seam_signatures"
file = "liveplay/engine_select.py"
confidence = "settled"
rationale = "run_candidate_sweep/enumerate_legal_actions stubs keep the old callables' exact signatures so Stage E is a body swap; they raise NotImplementedError until the C++ sweep is wired. SimulationError moved here from simulation_runner."
updated = "2026-07-08T19:39:18.452Z"

[[record]]
name = "pickled_sessions_lost"
file = "liveplay/sweep_recorder.py"
confidence = "requirement"
rationale = "User accepted loss of pickle-era sweep sessions when payloads moved to sweep_io JSON; no legacy reader. load_session detects .pkl files and rejects the session loudly rather than decoding."
updated = "2026-07-08T19:39:18.497Z"

[[record]]
name = "records_store_seeding"
file = ""
confidence = "settled"
rationale = "Stage C seeded the full 296-record store from the old repo (SCRIPTS/migrate_records.py): scopes remapped cpp/->engine/, src/->liveplay/ where moved; records for old-repo code (sweep, Python engine, ai, nn, search) keep src/ paths until Stage E."
updated = "2026-07-08T19:39:26.882Z"

[[record]]
name = "corpus_100k_gitignored"
file = "golden_traces_100k/"
confidence = "requirement"
rationale = "100k trace corpus is rsync-copied and git-ignored (862MB); the full replay gate (--jobs 0) runs in this repo from day one alongside the committed frozen 1028-trace gate in tests/fixtures/golden_traces."
updated = "2026-07-08T19:39:26.935Z"

[[record]]
name = "effect_duration_int8"
file = "engine/src/state.h"
confidence = "requirement"
rationale = "USER 2026-07-09: effect durations are 0-8 turns or infinite (weather/terrain/binding set by ability/battle script, encoded -1). Duration fields fit int8_t. TimedVolatile.turns stays int32 (doubles as payload: source id / move slot)."
updated = "2026-07-10T02:05:27.980Z"

[[record]]
name = "trivially_copyable_state"
file = "engine/src/state.h"
confidence = "settled"
rationale = "D2: BattleState is memcpy-able (static_assert). All state vectors -> fixed-cap InlineVec (fail-loud abort on overflow); baton_pass json evicted to typed BatonPassData (codec wire unchanged). Enables slab NodePool + cheap solver copies."
updated = "2026-07-10T02:05:29.448Z"

[[record]]
name = "solver_state_projection"
file = "engine/src/state_eq.cpp"
confidence = "requirement"
rationale = "USER 2026-07-09: solver equal/hash track everything a mechanic reads; exclude ONLY inert bookkeeping (turn_number, prev_turn_order, exp_participants). No more exclusions without proof+approval; over-merge silently breaks the guaranteed-win search."
updated = "2026-07-10T02:05:33.846Z"

[[record]]
name = "sorted_set_invariant"
file = "engine/src/state_eq.cpp"
confidence = "settled"
rationale = "imprisoned_moves/exp_participants inner sets are codec pre-sorted; equality compares ordered vectors, hash mixes order-independent. Unsorted writer = silent equal/hash disagreement, so state_equal aborts loudly on violation."
updated = "2026-07-10T02:05:35.543Z"

[[record]]
name = "oracle_consume_once"
file = "engine/src/oracle.h"
confidence = "settled"
rationale = "D3: OracleOverrides re-fire replaced by consume-once queues (+SPEED_TIE) mirroring Python _rng_inject; each occurrence pops one, exhaustion throws NeedsRNG (loud). Scalar override JSON still accepted for back-compat."
updated = "2026-07-10T02:05:40.721Z"

[[record]]
name = "catb_occurrence_injection"
file = "engine/src/logger.h"
confidence = "settled"
rationale = "D3: occurrence-keyed Cat-B injection ((event,occ)->outcome) checked before threshold/RNG; verify_exhausted throws on leftovers. GameDriver resets occurrence counters each turn start so injection indices cannot silently drift."
updated = "2026-07-10T02:05:42.620Z"

[[record]]
name = "rng_logger_participants"
file = "engine/src/logger.h"
confidence = "settled"
rationale = "D3 impl of cpp_analytical_rng_logger: global-ptr toggle (nullptr=off), POD entries. Participants plumbed to all Cat-B det-wrappers (both-sides where known; self-only for Endure/Protect/self-draws); SPEED_TIE encoded side*10+slot."
updated = "2026-07-10T02:05:46.961Z"

[[record]]
name = "solver_direct_turn_entry"
file = "engine/src/solver_turn.h"
confidence = "settled"
rationale = "D4: cpp_run_one_turn_solver is a thin non-throwing wrapper over cpp_run_one_turn (pre-loaded overrides, no policies, no JSON). Unanswered Cat-A pause -> ok=false (solver enumerated RNG wrong = bug). Live-play/bridge path unchanged."
updated = "2026-07-10T02:05:50.229Z"

[[record]]
name = "batched_seam_api_deferred"
file = "engine/bindings/module.cpp"
confidence = "settled"
rationale = "D5 bench: batching amortizes only the ~53ns pybind crossing, not the ~139us/state codec (each still decodes). D4 direct path (cpp_run_one_turn_solver) already pays zero JSON on the hot path, so a batched JSON API is unjustified; deferred."
updated = "2026-07-10T02:05:54.727Z"

[[record]]
name = "ffp_contract_off_kept"
file = "engine/"
confidence = "settled"
rationale = "-ffp-contract=off stays: traces record Python IEEE doubles w/o FMA; contraction fuses a*b+c in the damage chain -> off-by-1 -> trace divergence. Also needed for reproducible solver bucket replays. Perf cost negligible (integer-heavy engine)."
updated = "2026-07-10T02:05:56.617Z"

[[record]]
name = "rich_event_log_pod_tags"
file = "engine/src/event_log.h"
confidence = "requirement"
rationale = "E1 rich LogEvent logger (separate from D3 RNG logger). Tagged-POD RichEventEntry vector OUTSIDE BattleState; string kwargs are int tags expanded only in the Python shim (from_cpp). Emits nullptr-guarded pure observation: no RNG/behavior change."
updated = "2026-07-10T17:41:38.056Z"

[[record]]
name = "rich_event_charge_split"
file = "engine/src/event_log.h"
confidence = "requirement"
rationale = "CHARGE_TURN fires for ALL two-turn charge moves; SEMI_INVULNERABLE_ENTER/EXIT only for semi-invuln moves (Fly/Dig/Dive/Bounce/Phantom Force/Sky Drop). Power Herb / harsh-sun Solar Beam skip both. Silent events carry minimal identity."
updated = "2026-07-10T17:41:45.734Z"

[[record]]
name = "rich_event_clear_python_driven"
file = "engine/src/event_log.h"
confidence = "requirement"
rationale = "Rich-event stream reset is Python-driven clear(): GameDriver does NOT auto-reset per turn. VOLATILE_APPLY emits only for confusion (consumer reads only volatile=confused). EXP_GAIN shows GROSS exp when net>0 else 0; one LEVEL_UP per level crossed."
updated = "2026-07-10T17:41:54.334Z"

[[record]]
name = "sweep_forced_speed_tie"
file = "engine/src/core_leaf.cpp"
confidence = "settled"
rationale = "Plain-mode forced_tie (SpeedTieOrder) resolves controlled cross-side MOVE ties, sticky per turn (mirrors OLD sweep pre_rng_inject re-fire). Needed since SortKey::top_two_equal ignores tie, so these always throw NeedsRNG. Oracle mode takes precedence."
updated = "2026-07-11T01:36:23.830Z"

[[record]]
name = "per_slot_attacker_luck"
file = "engine/src/turn.cpp"
confidence = "settled"
rationale = "luck_pX_slot1 (nullptr default) is the ATTACKER damage-loop luck only when the acting entry's source_slot==1, at the 3 attacker sites. Defender/residual/TurnLuck stay side-level — mirrors OLD sweep per-slot roll/crit keys. nullptr = byte-identical."
updated = "2026-07-11T01:36:36.120Z"

[[record]]
name = "sweep_error_classification"
file = "liveplay/sweep_driver.py"
confidence = "settled"
rationale = "run_with_capture: UnportedTurn re-raises (fatal gap); RuntimeError with 'NeedsRNG' = candidate filtered (None), once-per-key stderr log (OLD UninjectedRNGError analog); other exceptions traceback-once + None; adapter errors raise before the try."
updated = "2026-07-11T01:36:49.087Z"

[[record]]
name = "sweep_boundary_flow"
file = "liveplay/sweep_driver.py"
confidence = "settled"
rationale = "Boundary=one run_one_turn_cpp(finalize_on_post_faint=True); faints snapshotted ONCE, <=1 replacement/side/boundary, no re-scan. Hazard-killed replacements re-prompt next boundary; Step-0 always intercepts fainted-active-with-bench, so no free turn."
updated = "2026-07-12T06:57:02.399Z"

[[record]]
name = "extra_pre_inject_deferred"
file = "liveplay/sweep_driver.py"
confidence = "settled"
rationale = "RESOLVED (Task 6d): extra_pre_inject now converts via pre_inject_payload to the C++ plain-mode pre_inject hook (6 Category-A events, name-keyed ints). Unmapped events / wrong value types raise ValueError before the sweep try-block."
updated = "2026-07-11T06:32:14.067Z"

[[record]]
name = "sweep_luck_preset_port"
file = "liveplay/rng.py"
confidence = "settled"
rationale = "SWEEP_LUCK ported from OLD simulation_runner.py:32-60 (BAD_LUCK base, accuracy/paralysis/attract/confusion-self-hit forced ON, binding/rampage rolls maxed). OLD-only warn/strict fields have no NEW equivalent and were dropped."
updated = "2026-07-11T01:37:26.668Z"

[[record]]
name = "plain_mode_pre_inject"
file = "engine/src/oracle.h"
confidence = "settled"
rationale = "pre_inject_or_oracle: sticky non-consuming map (RngEventC int->engine int), consulted ONLY when overrides==nullptr; else oracle_resolve. Mirrors OLD sweep pre_rng_inject + forced_tie precedent. Absent key -> nullptr -> byte-identical (100k-verified)."
updated = "2026-07-11T06:32:30.994Z"

[[record]]
name = "ancient_power_boost_dead"
file = "liveplay/sweep_driver.py"
confidence = "settled"
rationale = "ANCIENT_POWER_BOOST is dead in BOTH engines: OLD resolve_ancient_power_boost has zero call sites; the 10% self-boost is a SecondaryEffect riding SECONDARY_FIRES/secondary_threshold. Kept fail-loud in _DEAD_EVENTS; never remap it."
updated = "2026-07-11T06:32:41.484Z"

[[record]]
name = "tri_attack_group_path_quirk"
file = "liveplay/sweep_secondaries.py"
confidence = "settled"
rationale = "Faithful OLD quirk: Tri Attack's secondary has status=None, so the grouped path reports fired=False when USEDMOVE is present and the TRI_ATTACK_STATUS injection block is unreachable with real data; Tri Attack status resolves via pre_inject/oracle."
updated = "2026-07-11T06:32:58.257Z"

[[record]]
name = "rich_log_hp_completeness"
file = "engine/src/"
confidence = "settled"
rationale = "Every C++ HP write must emit rich_log_damage/heal: _sim_hp_changes rebuilds HP trajectories from ALL DAMAGE/HEAL events. Non-move damage must NOT be SourceTag::MOVE (sweep sums filter source=='move'). Crash/recoil->RECOIL; OLD fine sources->broad."
updated = "2026-07-11T16:59:24.784Z"

[[record]]
name = "post_faint_boundary_step0"
file = "liveplay/sweep_driver.py"
confidence = "settled"
rationale = "run_to_decision_boundary Step 0: fainted active + living bench = party prompt, so actions ARE replacement switches; apply via apply_switch_cpp, never run_one_turn_cpp (action1=None TypeErrors). Mirrors OLD AWAIT_POST_FAINT_SWITCH inference."
updated = "2026-07-11T16:59:31.809Z"

[[record]]
name = "uninjected_rng_filters_cand"
file = "liveplay/sweep_driver.py"
confidence = "requirement"
rationale = "UninjectedRNGError in run_to_decision_boundary filters the candidate (return None + log once) instead of aborting the sweep: it means the branch diverged from observed reality. All-filtered still raises the no-candidate SimulationError."
updated = "2026-07-11T17:34:34.784Z"

[[record]]
name = "hpbox_name_stops_at_lv"
file = "liveplay/vision/ocr.py"
confidence = "settled"
rationale = "HP-box name pass must include the 'Lv' token and truncate the name at the first 'Lv': FONT_SMALL digit 0 == letter O pixel-exactly, so an alpha-only pass reads Lv10's 0 as a trailing O, splitting name-keyed HP logs (Allen1 sweep crash 2026-07-11)."
updated = "2026-07-11T21:38:02.943Z"

[[record]]
name = "hp_log_key_canonicalization"
file = "SCRIPTS/play.py"
confidence = "requirement"
rationale = "Both sides' HP-log/buffer keys are canonicalized to the resolved species display name (_canonical_team_key) so OCR jitter collapses to one key and unresolvable names fail loud. Empty team (pre-battle stub) falls back to raw lowercased name, no raise."
updated = "2026-07-12T05:47:36.783Z"

[[record]]
name = "exc_move_kill_bonus_kb"
file = "engine/src/ai_scorer_dist.cpp"
confidence = "requirement"
rationale = "Exception moves (Relic Song/Meteor Beam/Future Sight/trapping) excluded from HD: a KO scores kill bonus ONLY (fixed kb 6/3, +1 Moxie), no +6/+8 base, no variance; additive stacks. Matches ai.ts, AI.md [3,6]. Fixed 2026-07-11 (was flat / 6+kb var)."
updated = "2026-07-12T07:44:22.031Z"

[[record]]
name = "cpp_manifest_gate"
file = "SCRIPTS/record_cpp_manifest.py"
confidence = "requirement"
rationale = "User 2026-07-12: gate = C++ self-regression manifest (full final state + fingerprint); 1M games mixed even=ai/ai odd=random/random, seed 20260712; commit only first 2k (tests/fixtures/cpp_manifest). Random parity traces retired; 28 scenario kept."
updated = "2026-07-12T15:41:49.495Z"

[[record]]
name = "question_conjunctive_semantics"
file = "engine/src/solver/"
confidence = "requirement"
rationale = "Question positively asserts ALL required terminal state; unasserted = unconstrained. requireNoFaint only means player not fainted at terminal - NO simultaneous-KO special case (both-faint = WIN when off and requireOppFaint holds). User decision."
updated = "2026-07-13T06:36:20.425Z"

[[record]]
name = "oracle_no_zero_prob_branches"
file = "engine/src/solver/transition_oracle.cpp"
confidence = "requirement"
rationale = "Oracle must NOT enumerate zero-prob branches: p=0 AI actions and p=0 branch options skipped (user instruction). Sound: zero-measure children contribute nothing. Leaf probs sum to 1 in EXACT mode only; NaN under collapse (collapse_probs_nan_poison)."
updated = "2026-07-14T17:41:53.695Z"

[[record]]
name = "oracle_dfs_prefix_replay"
file = "engine/src/solver/transition_oracle.cpp"
confidence = "settled"
rationale = "DFS prefix-replay chosen over act-branch over-enumeration: completeness by construction, one turn execution per leaf, zero mechanics duplication. Cat-A prob table is oracle-owned and fail-loud; MC-verified vs random-mode sampling."
updated = "2026-07-13T06:36:29.956Z"

[[record]]
name = "solver_turn_luck_overrides"
file = "engine/src/solver_turn.cpp"
confidence = "settled"
rationale = "cpp_run_one_turn_solver MUST set luck_p0/p1.overrides = &overrides (mirrors GameDriver lp*_tmpl_). cpp_run_one_turn threads pre_inject but NOT overrides into luck; without this, sites reached via luck.overrides (Starf check_berry) pause forever."
updated = "2026-07-13T06:36:48.242Z"

[[record]]
name = "oracle_depth_guard"
file = "engine/src/solver/transition_oracle.cpp"
confidence = "settled"
rationale = "MAX_PREFIX_DEPTH=128 fail-loud guard: runaway prefix extension (prefix/log misalignment) throws with prefix dump instead of stack-overflow segfault. Quick Draw (ability 259) excluded phase 1 (uninstrumented); preconditions throw on it."
updated = "2026-07-13T06:36:54.956Z"

[[record]]
name = "keepitem_item_id_no_earlyfail"
file = "engine/src/solver/question.cpp"
confidence = "settled"
rationale = "keepItem is a positive terminal assertion: player.item must EQUAL the given item id at terminal. Harvest-restored berry counts as kept; Trick/Knock Off swap fails. NOT monotone (Harvest restores, residuals.cpp:373) so no non-terminal early-LOSS."
updated = "2026-07-13T06:36:56.965Z"

[[record]]
name = "psywave_truthful_truncation"
file = "engine/src/rng_resolver.h"
confidence = "settled"
rationale = "Psywave logs options_count=101 with options_truncated=1 (true domain k=0..100 exceeds inline capacity 16). Log consumers must NEVER enumerate truncated options; the oracle owns the domain (1/200 endpoints, 1/100 interior)."
updated = "2026-07-13T06:37:13.940Z"

[[record]]
name = "pchosen_saturated_occurrence"
file = "engine/src/logger.h"
confidence = "settled"
rationale = "p_chosen (default -1.0) set at each resolution site. Saturated draws (p_chosen==1.0) log but do NOT bump_occurrence: Cat-B injection occurrence index = count of prior NON-saturated draws for that event. Oracle log-scan mirrors this exactly."
updated = "2026-07-13T06:37:19.997Z"

[[record]]
name = "matchupgen_conventions"
file = "engine/src/solver/matchup_gen.cpp"
confidence = "settled"
rationale = "Level 50, PP=40 sentinel, teams of one, Quick Draw blocklisted. OPPONENT always holds the class item (Uniform: GENERAL_ITEMS; SashSturdy: Sash/Band/Sturdy 1/3); player may be item-free. Generate-then-filter sharding: RNG stream identical all shards."
updated = "2026-07-14T17:42:38.721Z"

[[record]]
name = "audit_budget_and_stats"
file = "engine/src/solver/audit/"
confidence = "settled"
rationale = "Budget-exceeded (max_leaves, default 1e6) is SKIPPED not failed in both selfcheck and mc (truncated support cannot prove holes). mc: per-child 5-sigma binomial, expected-count floor 5, actions pinned; engine random policy is uniform, NOT the AI dist."
updated = "2026-07-13T06:37:31.211Z"

[[record]]
name = "solver_lib_provisionals"
file = "engine/src/solver/"
confidence = "provisional"
rationale = "Separate nuzlocke_solver lib (settled; one-way dep on core). Provisional: PP included in packed context (measure growth); leaf budget 1e6; AdverseFirst ordering best-effort heuristic; no leaf dedup in oracle (aggregation happens in consumers)."
updated = "2026-07-13T06:37:38.561Z"

[[record]]
name = "enum_names_emitter"
file = "SCRIPTS/gen_cpp_data.py"
confidence = "settled"
rationale = "engine/generated/enum_names.h (species/move/ability name-to-id tables for matchup_gen) is emitted by _emit_enum_names_h and drift-checked via --check. Never hand-edit; regenerate with gen_cpp_data.py."
updated = "2026-07-13T06:37:40.203Z"

[[record]]
name = "collapse_probs_nan_poison"
file = "engine/src/solver/transition_oracle.cpp"
confidence = "settled"
rationale = "Pessimal/Coarse collapse: ALL branch/leaf probs are quiet_NaN (collapsed subsets are not distributions; fail-loud on arithmetic misuse). Sigma=1 check skipped iff NaN present. AI-action probs stay REAL (p==0 filter). Exact untouched, locked by test."
updated = "2026-07-14T17:42:07.916Z"

[[record]]
name = "bsolver_dedicated_stack_thread"
file = "engine/src/solver/bsolver.cpp"
confidence = "settled"
rationale = "b_win recurses inside oracle emit callbacks (~80-150KB/level), so bsolver_certify runs it on a dedicated pthread with explicit stack (BsolverConfig::stack_size, default 256MB ~ 2000+ levels). Exceptions cross via exception_ptr; all pthread rcs throw."
updated = "2026-07-14T17:42:13.790Z"

[[record]]
name = "matchupgen_player_item_free"
file = "engine/src/solver/matchup_gen.cpp"
confidence = "requirement"
rationale = "USER decision: player side (side0) item is NONE with 30% probability in EVERY class (unconditional rng_ draw after all class item logic, keeping the stream aligned); opponent always holds the class item. Mirrors prototype calibration generator."
updated = "2026-07-14T17:42:20.657Z"

[[record]]
name = "audit_referee_seam"
file = "engine/src/solver/audit/"
confidence = "settled"
rationale = "AnalyticAuditConfig has injected fixtures + CertifierFn seam (mutually exclusive with repo_root; throws if both). Tests inject wrong verdicts to prove all 5 verification paths incl. loss_vs_exact_win print-first. Keep the pattern for future solvers."
updated = "2026-07-14T17:42:51.422Z"

[[record]]
name = "gen_fixtures_self_locating"
file = "engine/tests/"
confidence = "settled"
rationale = "Never pin (seed,index) generator fixtures: generator changes shift the RNG stream and break them. Scan the stream for the first matchup with the needed property (fail loud if absent). Pattern set by the Starf regression in test_solver_audit.cpp."
updated = "2026-07-14T17:43:12.426Z"

[[record]]
name = "pessimal_loss_pruner_only"
file = "engine/src/solver/"
confidence = "requirement"
rationale = "USER: pessimal collapse is a LOSS-pruner ONLY. Pessimal LOSS is conclusive; pessimal WIN is NEVER evidence (adversarial subset). Pipelines using pessimal must send non-LOSS outcomes to an exact certifier. Rule survives into the new solver."
updated = "2026-07-14T17:43:27.661Z"

[[record]]
name = "solver_transition_2026_07"
file = "engine/src/solver/"
confidence = "requirement"
rationale = "USER 2026-07-14: pivot to a new user-designed solver (bsolver-like, faster; keeps oracle, MatchupGen, audits, pessimal pruning). Analytic likely retired; Phase 2 Task 7 PAUSED at wave-1 (SOLVER_PHASE2_STATE.md). Old-code disposition decided after."
updated = "2026-07-14T17:43:44.699Z"

[[record]]
name = "overkill_coupling_throw"
file = "engine/src/solver/bucket/"
confidence = "requirement"
rationale = "Overkill cross-axis coupling (drain/recoil/Shell Bell/Leech Seed/Innards Out scale with min(dmg,hp)): THROW for now (USER 2026-07-15, supersedes plan amendment 20b concede-tag). Promote to concede tag only if Task 10 rcheck throw census is noisy."
updated = "2026-07-15T17:17:38.343Z"

[[record]]
name = "fixed_damage_supported"
file = "engine/src/solver/bucket/"
confidence = "requirement"
rationale = "Fixed-damage moves (Seismic Toss/Night Shade/Dragon Rage/Sonic Boom/Psywave) are SUPPORTED, not 5.2 concessions (USER 2026-07-15): HP-independent, cannot crit; ordinary derived splits handle them. They stay on the Task 1 crit-audit allowlist."
updated = "2026-07-15T17:17:47.450Z"

[[record]]
name = "gluttony_full_impl_task8"
file = "engine/src/solver/bucket/"
confidence = "requirement"
rationale = "Gluttony: implement FULLY in Task 8, no hacks (USER 2026-07-15) - extend hp_thresholds() with ability-conditional denominator (/2) plus the Custap action-order site (core_leaf.cpp:726). Silently delegating to quarter-only hp_thresholds is unsound."
updated = "2026-07-15T17:17:48.838Z"

[[record]]
name = "substitute_axis_postponed"
file = "engine/src/solver/bucket/"
confidence = "requirement"
rationale = "Substitute: prototype concedes (tag on VOLATILE_SUBSTITUTE); long-run design is a TRUE THIRD interval axis (USER 2026-07-15) - post-Sub healing extends space by max_hp/4. Player CAN use Substitute (niche but real); postponed, not dropped."
updated = "2026-07-15T17:18:05.423Z"

[[record]]
name = "stunlock_concede_player_only"
file = "engine/src/solver/bucket/"
confidence = "requirement"
rationale = "5.1 stunlock/confusion concession is PLAYER-side only (USER 2026-07-15). Opponent confusion self-hits are adversarial AND-branches (they only help the certificate) and must NOT be conceded."
updated = "2026-07-15T17:18:18.713Z"

[[record]]
name = "destiny_bond_direct_faint"
file = "engine/src/move_exec_damage.cpp"
confidence = "requirement"
rationale = "Destiny Bond drag-down must faint the attacker DIRECTLY - survival mechanics (Endure/Focus Band/Sash/Sturdy) must NOT apply (USER 2026-07-15, Task R2). Do not route through cpp_apply_damage survival checks."
updated = "2026-07-15T17:18:29.108Z"

[[record]]
name = "explosion_always_self_faint"
file = "engine/src/post_hit.cpp"
confidence = "requirement"
rationale = "Explosion/Self-Destruct family must self-faint even on miss/Protect/zero damage (USER 2026-07-15, Task R2). No damage>0 gate on the self-faint."
updated = "2026-07-15T17:18:30.303Z"

[[record]]
name = "curse_ghost_below_half"
file = "engine/src/effects.cpp"
confidence = "requirement"
rationale = "Ghost Curse at/below half HP must still curse the target and SELF-FAINT the user (pays all remaining HP), not silently no-op (USER 2026-07-15, Task R2). Boundary at max_hp/2 stays a solver breakpoint."
updated = "2026-07-15T17:18:37.046Z"

[[record]]
name = "memento_faint_iff_activates"
file = "engine/src/effects.cpp"
confidence = "requirement"
rationale = "Memento faints the user iff the move ACTIVATES: no faint on miss/Protect/Substitute; still faints on Clear Body or -6 stages (USER 2026-07-15). Faint-first-then-drop order verified correct; guard-path gating verified in Task R2."
updated = "2026-07-15T17:18:38.643Z"

[[record]]
name = "embargo_absent_from_engine"
file = "engine/src/"
confidence = "requirement"
rationale = "Embargo exists in Run & Bun but is ABSENT from this engine (zero grep matches) - known gap, postponed (USER 2026-07-15). When ported it negates held-item effects (berries/Leftovers/Black Sludge/Life Orb); pure d-flag for the solver, no HP breakpoint."
updated = "2026-07-15T17:18:45.185Z"

[[record]]
name = "expand_throw_never_bisect"
file = "engine/src/solver/bucket/expand.cpp"
confidence = "settled"
rationale = "Expand THROWS staged ExpandError on any verification mismatch, NEVER auto-bisects (self-healing would mask under-splitting). Chip/heal kinks are derived splits at Expand time (single convention, USER item 7: fastest of the sound options)."
updated = "2026-07-15T17:18:47.289Z"

[[record]]
name = "seed_zero_maxhp_unconditional"
file = "engine/src/solver/bucket/breakpoints.cpp"
confidence = "settled"
rationale = "BreakpointRegistry::instantiate seeds {0, max_hp} UNCONDITIONALLY before hp_thresholds()+keepHp. This neutralizes hp_thresholds' cur_hp==max_hp gating on FullHp entries (inventory 11 item 2) - do not remove the seeding."
updated = "2026-07-15T17:18:55.782Z"

[[record]]
name = "level_is_question_param"
file = "engine/src/solver/bucket/"
confidence = "requirement"
rationale = "Player LEVEL is an input parameter of the Question (staying under level cap manipulates AI - viable tactic, USER amendment 20c). Level-up applies AFTER matchup end, BEFORE end-state check. EXP/level-up handling deferred to Solver C / 6v6 design."
updated = "2026-07-15T17:18:57.703Z"

[[record]]
name = "move_scope_shared_extraction"
file = "engine/src/solver/move_scope.cpp"
confidence = "settled"
rationale = "SCOPE_* constants + check_move_scope + HP_DEP/BINDING lists extracted from analytic.cpp so bucket concede reuses (never forks) the classifier; analytic.h re-includes it. Extraction fixed a latent OOB read (N_HP_DEP_MOVES=45 vs 44 elements)."
updated = "2026-07-15T18:40:52.957Z"

[[record]]
name = "concede_conventions"
file = "engine/src/solver/bucket/concede.cpp"
confidence = "settled"
rationale = "concede_tags = f(lo)|f(hi) union (sound: FAIL-only; needed for the one HP-reading detector MULTI_HIT_HARD). Quick Claw/Draw always tag when present (conservative). Opponent SELECTING Substitute not scanned: child carries volatile, concedes later."
updated = "2026-07-15T18:41:16.457Z"

[[record]]
name = "multi_hit_hard_condition"
file = "engine/src/solver/bucket/concede.cpp"
confidence = "settled"
rationale = "MULTI_HIT_HARD fires iff max_hits>1 AND defender has live Half/Quarter consumable threshold t (never FullHp) AND max single-hit damage > t - amendment 8(b) single-hit-spans-threshold-to-KO. Precise: rcheck census decides per-hit enumeration."
updated = "2026-07-15T18:41:24.030Z"

[[record]]
name = "bucket_onstack_fail_semantics"
file = "engine/src/solver/bucket/win_solver.cpp"
confidence = "settled"
rationale = "Repeated on-stack bucket = FAIL (amendment 16a), deliberately diverging from bsolver INDETERMINATE(Cycle). Repeats currently unreachable via real dynamics (PP-in-d changes every turn), so the mechanism is tested via the cfg.expand_override seam."
updated = "2026-07-15T19:28:09.299Z"

[[record]]
name = "bucket_win_tri_valued_local"
file = "engine/src/solver/bucket/win_solver.cpp"
confidence = "settled"
rationale = "INDETERMINATE propagates locally (per action/child), never as global abort - a depth-capped branch cannot destroy a WIN via another action; root FAIL requires all actions failing. FAIL is NOT a LOSS certificate; pipeline maps both to UNKNOWN."
updated = "2026-07-15T19:28:19.121Z"

[[record]]
name = "bucket_win_root_and_caps"
file = "engine/src/solver/bucket/win_solver.cpp"
confidence = "provisional"
rationale = "Root bucket = singleton HP intervals at initial state (sound, simplest; segment-wide roots are a later sweep-reuse optimization). visit_cap 1e6 -> INDETERMINATE(VisitCap) added beyond the required depth cap as insurance since there is no memoization."
updated = "2026-07-15T19:28:21.077Z"

[[record]]
name = "registry_vs_delta_convention"
file = "engine/src/solver/bucket/breakpoints.cpp"
confidence = "settled"
rationale = "Residual/on-hit fraction-of-max shifts live ONLY in residual_delta_candidates (both signs; item-7 single mechanism). Move/status-parameterized heal-caps (recovery/Swallow/Heal Pulse/Sap/Wish/Absorb) + hazard chips = STATIC registry entries (20d)."
updated = "2026-07-15T21:23:53.524Z"

[[record]]
name = "form_change_throw_instantiate"
file = "engine/src/solver/bucket/breakpoints.cpp"
confidence = "settled"
rationale = "Form-change abilities {211,208,197,161,241} THROW runtime_error containing 'form-change' at instantiate (14 #8): loud beats silent thresholds whose max_hp rescale Expand cannot honor. Struggle delta omitted (PP=40 corpus; loud throw if reached)."
updated = "2026-07-15T21:23:55.224Z"

[[record]]
name = "ai_bp_scorer_blind_fixed_dmg"
file = "engine/src/solver/bucket/ai_breakpoints.cpp"
confidence = "settled"
rationale = "PlayerKoEstimate SKIPS base_power==0 player moves: the scorer threat loops (ai_scorer_internal.h:333/347/371) continue on base_power==0, so the AI is BLIND to fixed-damage player moves. Do NOT fix to emit level damage - no flip, no breakpoint needed."
updated = "2026-07-16T03:07:08.241Z"

[[record]]
name = "ai_bp_root_d_only"
file = "engine/src/solver/bucket/ai_breakpoints.cpp"
confidence = "settled"
rationale = "AI breakpoints derive from the ROOT d only; d-drift flips stay accepted SupportFlip throws (rcheck census sizes them). Per-move player estimates (not just max) emitted to survive PP exhaustion. Refinement = per-d recomputation (module is per-state)."
updated = "2026-07-16T03:07:14.506Z"

[[record]]
name = "ai_bp_estimates_and_throws"
file = "engine/src/solver/bucket/ai_breakpoints.cpp"
confidence = "settled"
rationale = "Estimates via ai_damage functions with the scorer's own LuckProfiles on state copies; pct thresholds by flip-pair bisection over verbatim expressions (both values). Throws ai-final-gambit (two-axis diagonal) and ai-bench (switch scoring), postponed."
updated = "2026-07-16T03:07:24.122Z"

[[record]]
name = "pipeline_verdict_lattice"
file = "engine/src/solver/bucket/pipeline.cpp"
confidence = "settled"
rationale = "Pessimal-LOSS short-circuits to LOSS (B skipped); pessimal WIN/INDET treated identically (never evidence); B-WIN -> WIN; else UNKNOWN; exceptions always propagate (rcheck is the catcher). Amendment 18 + pessimal_loss_pruner_only."
updated = "2026-07-16T03:57:45.253Z"

[[record]]
name = "rcheck_classification_bins"
file = "engine/src/solver/audit/rcheck_core.cpp"
confidence = "settled"
rationale = "9-bin taxonomy; THROWN precedes referee check; REFEREE_INDET counted, excluded from soundness evidence; UNKNOWN+exact-LOSS = SOUND conservatism; CONSERVATIVE_UNTAGGED sub-split by B reason (cap != modeling gap). Referee budgets = CLI flags."
updated = "2026-07-16T03:58:08.096Z"

[[record]]
name = "transition_cache_next_priority"
file = "engine/src/solver/bucket/"
confidence = "requirement"
rationale = "USER 2026-07-16: transition-edge caching (DAG search) is the FIRST post-gate task - speed unjudgeable and deep matchups unverifiable without it. Design: (bucket,action)->ExpandResult edge cache (question-independent) + per-question verdict memo."
updated = "2026-07-16T07:01:46.560Z"

[[record]]
name = "memo_lowlink_cycle_safety"
file = "engine/src/solver/bucket/win_solver.cpp"
confidence = "settled"
rationale = "Verdict memo: on-stack repeat FAILs w/ lowlink=ancestor depth; node memoizes FAIL only if subtree lowlink>=own depth (else suppressed); WIN always memoized, propagates +INF; INDET never. Keeps 16(a) sound under DAG revisits."
updated = "2026-07-16T16:50:07.818Z"

[[record]]
name = "edge_cache_owns_interner"
file = "engine/src/solver/bucket/transition_cache.h"
confidence = "settled"
rationale = "TransitionCache owns oracle+ContextInterner: cached child d only valid under that interner. Entries scoped by bp_fp (BpSet folds Question HP thresholds; edges question-independent only modulo grid). Override-fed caches never reused for real runs."
updated = "2026-07-16T16:50:29.516Z"

[[record]]
name = "memo_exact_key_v1"
file = "engine/src/solver/bucket/win_solver.cpp"
confidence = "requirement"
rationale = "USER 2026-07-16: verdict memo is exact-BucketKey v1; containment matching (WIN-superset/FAIL-subset hits, both sound) deferred until memo_containment_missed sizes the gap on corpus. Grid-cell widening noted as max-hit option w/ false LOSSes."
updated = "2026-07-16T16:50:46.296Z"

[[record]]
name = "pp_canon_measure_first"
file = "engine/src/solver/bucket/win_solver.cpp"
confidence = "requirement"
rationale = "USER 2026-07-16: measure cache w/ full PP-in-d first, but 'we will probably have to switch' to PP tracked only for cycle-capable moves (heal/Harvest/Leftovers; Splash via self-cycle check) + total-PP turn cap. Full PP hides cycles + fragments reuse."
updated = "2026-07-16T16:51:04.096Z"

[[record]]
name = "rcheck_local_cache_only"
file = "engine/src/solver/audit/rcheck_core.cpp"
confidence = "provisional"
rationale = "rcheck leaves win_cfg.cache=nullptr (per-certify local cache): one question per matchup and matchups never share d, so a shard-lifetime shared cache = unbounded memory for zero cross-matchup hits. Revisit when same-matchup question batches exist."
updated = "2026-07-16T17:11:35.717Z"
