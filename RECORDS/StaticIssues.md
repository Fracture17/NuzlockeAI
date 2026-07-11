# Static Issues — carried audit index (C++ repo)

**Mined at Stage E §7 (2026-07-11)** from the old repo's audit
`~/PycharmProjects/NuzlockeAI/RECORDS/StaticIssues.md` (853 lines, findings Groups A–M,
2026-06-21 adversarial verification appendix). That file is the historical source; this is
the working index for the new repo. Old IDs are kept. Severities below are the **corrected**
ones from the 2026-06-21 appendix (several SILENT-DESYNC labels were re-verified as LOUD
over-prunes; the corrected labels are authoritative).

Key migration fact discovered while mining: **most engine-mechanic findings (H1–H4, I, J,
K1–K3, L, M) were fixed in the old Python engine AFTER the audit**, and the C++ port mirrors
the fixed engine — so they did NOT carry over as bugs. The old repo's 18 repro tests in
`tests/test_static_issues_audit.py` had their xfail markers removed (they now assert canonical
behavior and pass); they were NOT ported to this repo and are prime regression-test candidates.
Neither `RECORDS/CPP_CORRECT_DIVERGENCES.md` (1 entry: binding release) nor
`RECORDS/INTENTIONAL_DIVERGENCES.md` (Quick Draw random_mode; residual-switch unported)
covers any Group A–M finding.

Severity legend (from the old doc): SILENT-DESYNC (worst) > DISCARDED-INFO > LOUD-CRASH
(safe) > DEDUP (parity risk) > VERIFY.

---

## Still-open findings (CARRIED)

### B1 — candidate-level HP check validates only the final endpoint (single-hit movers)
**Severity:** DISCARDED-INFO (SAFE class — over-keeps candidates, never silently desyncs).
`_hp_match_detail` (`liveplay/sweep_reconcile.py:692`) compares only `record.deltas[-1][1]`
to final HP; the rigorous trajectory walk in `_enumerate_mover_rolls` is still gated on
`mover_n_hits > 1` (`liveplay/sweep_run.py:388`, `apply_hp_prune`). Single-hit intermediate
readings (e.g. an Absorb dip before an Oran heal) are dropped, so disambiguating info is lost.
**Narrowed vs old:** the new `_hp_count_detail` (`sweep_reconcile.py:646`, run at
`sweep_run.py:599`) now constrains the COUNT of HP-change transitions per mon, and the berry
sub-case is closed (see B1p2 below) — the remaining gap is intermediate-VALUE disambiguation
for single-hit drain/heal interplay.
**Status:** CARRIED (narrowed). **Old repro test:** none XFAIL;
`test_single_hit_hp_trajectory.py::TestSingleHitCorroboratedHealDoesNotRaise` covers the
adjacent fixed berry case.

### D3 — same-species cursor disambiguation duplicated across extraction passes
**Severity:** DEDUP (parity risk). The old repo had four independent `cursor=[0,0]` walks.
The new repo centralizes slot assignment on a shared `slot_map`, but keeps **fallback cursors**
used when `slot_map is None`: `liveplay/sweep_actions.py:225,312,357,615,686` and
`liveplay/sweep_secondaries.py:642`. If a fallback path's message list/order ever differs from
the slot_map pass, same-species slot attribution can drift between passes.
**Status:** CARRIED (narrowed — fallback-only). **Old repro test:** none.

### E1 — `_check_action_order` tolerates extra trailing sim moves
**Severity:** DISCARDED-INFO. Old code truncated to `min(len)` both ways. New
`_check_action_order` (`liveplay/sweep_reconcile.py:559-567`) now FAILS when the sim produced
fewer moves than observed (`len(sim_order) < n`) — that half is fixed — but still only checks
the observed sequence as a PREFIX of the sim order, so a trailing sim move the emulator never
showed is tolerated (deliberate for the flinch case, but also hides genuine extra moves).
**Status:** CARRIED (narrowed). **Old repro test:** none.

### F1 — level-up tolerance can mask a wrong-mon level-up
**Severity:** DISCARDED-INFO (by-design trade-off, recorded). `check_log_events`
(`liveplay/sweep_reconcile.py:538-544`) accepts any sim level-up whose new level appears in the
observed set, even for the wrong mon (documented EXP-seed-drift tolerance).
**Status:** CARRIED (by design). **Old repro test:** none.

### H5 — Bulletproof guard exists only on the damaging path
**Severity:** VERIFY / latent (no active desync). C++ has the Bulletproof block only in the
damaging pre-damage guards (`engine/src/move_exec_guards.cpp:868-869`); `handle_status_action`
(`engine/src/move_exec.cpp:338`) has no equivalent. Harmless while no STATUS move carries the
BULLET tag in the data; becomes a silent immunity miss if one is ever added.
**Status:** CARRIED (latent). **Old repro test:** none.

### H-DEDUP — STATUS vs damaging guard chains are still two implementations
**Severity:** DEDUP (parity risk; a recurring bug class per project memory). The structural
split survives the port: `handle_status_action` (`engine/src/move_exec.cpp:338`) vs the
damaging guard chain (`engine/src/move_exec_guards.cpp`). The specific back-port gaps found by
the audit (H1/H2 type-immunity, H4 semi-invuln flag) are fixed — both paths now share
`check_type_immunity` (`move_exec.cpp:474`) and the accuracy-modifier helper — but any NEW
guard must still be added in two places.
**Status:** CARRIED (structural). **Old repro test:** none (H1/H2 tests cover the fixed gaps).

---

## Closed findings

### Group A / C / D / F / G — reconciliation layer (fixed in the port)
- **A1** (STATUS_APPLY presence-only; genuinely silent only for non-HP-ticking statuses) —
  CLOSED: now attributed per target side+name via `_status_msg_target` + `_event_attributed_to`
  (`sweep_reconcile.py:383-396`). Residual nit: requires ≥1 attributed event per message, not an
  exact aggregate count.
- **A2** (stat-change pure presence; SILENT — stages are never observed off-screen) — CLOSED:
  direction (+/−) and target side+name now checked (`sweep_reconcile.py:398-452`); pinch-berry
  boosts fail loud when unattributable. Residual nit: magnitude (sharply/severely) unchecked.
- **A3** (confusion-apply ignores target) — CLOSED: attributed (`sweep_reconcile.py:454-466`).
- **A-DEDUP** — CLOSED: implemented as `_event_attributed_to` (`sweep_reconcile.py:305`).
- **B1 part 2** (berry restore corroboration) — was already FIXED in old repo; carried:
  per-side berry/Cheek Pouch corroboration at `sweep_reconcile.py:499-524`.
- **C1** (unmatched observed move silently dropped) — CLOSED: raises
  `UnreproducibleObservedMoveError` (`liveplay/sweep_actions.py:729-743`).
- **C2** (switch-in to unknown team slot silently dropped) — CLOSED: raises `SimulationError`
  (`sweep_actions.py:762-765`, also 949-952, 1092-1095).
- **D1** (first same-species slot picked silently) — CLOSED: switch-eligibility reduction +
  `RosterAmbiguityError` / caller fan-out (`liveplay/state_transition.py:138-177`).
- **D2** (side hint trusted when name matches neither active) — CLOSED: `reference_kind="actor"`
  raises `ActorNotActiveError` for recognizable names; garble still trusts the hint
  (`state_transition.py:84-135`).
- **E2** (HP-no-change guard opponent slot 0 only) — was already FIXED in old repo; carried:
  `_total_side_move_damage(target_side=1)` (`sweep_reconcile.py:494-497`).
- **F2** (dedup on `hash(rs)`, collision risk) — CLOSED: dedup keyed on the state itself
  (`liveplay/sweep_run.py:617`).
- **G1** (attacker_slot hardcode) — stale finding, already fixed pre-audit. Closed.
- **G2** (incomplete heal whitelist → loud crash on legitimate mid-multihit heals) — CLOSED:
  redesigned; heal deltas reset the segment anchor without a whitelist
  (`_segment_hp_deltas_into_hits`, `sweep_run.py:61-82`).

### Group H — status-move path parity (fixed post-audit in Python; C++ mirrors)
- **H1** (Thunder Wave vs Volt Absorb/Motor Drive/Lightning Rod; LOUD except boost-suppressed
  corner) — CLOSED: status path routes through `check_type_immunity`
  (`engine/src/move_exec.cpp:474` → `move_exec_guards.cpp:356-390`, full absorb table).
  Old tests: `TestH1_ElectricAbsorbVsThunderWave` (3 tests).
- **H2** (Sap Sipper only blocked Leech Seed; LOUD except A2-suppressed corner) — CLOSED: same
  fix; Sap Sipper is in the absorb table. Old tests: `TestH2_SapSipperVsGrassStatusMoves` (2).
- **H3** (accuracy modifiers duplicated verbatim) — CLOSED: shared
  `_apply_item_ability_accuracy_modifiers`-equivalent helper used by both paths.
- **H4** (semi-invuln miss didn't set `last_move_failed` on damaging path) — CLOSED: damaging
  path sets it (old core.py:2150 comment "H4"; ported).

### Groups I / L — residual order (engine rebanded post-audit; C++ mirrors)
The whole residual phase was rewritten (old-repo commits 272004c, 2ebf312, a4bc66f):
per-battler **speed-descending** order, each battler running a canonical band chain —
weather(0) → grassy(1) → **status_cure(2)** → **item_heal(3)** → aqua_ring(4) → ingrain(5) →
leech_seed(6) → poison(7) → burn(8) → late(9, incl. orbs) (`engine/src/residuals.cpp:748-760`).
- **I1** (Leftovers/Aqua Ring/Ingrain healed after drains; LOUD) — CLOSED. Heals are bands 3-5,
  before drains 6-8. Old tests: `TestI1_ResidualHealBeforeDrain` (2).
- **I2** (Rain Dish/Dry Skin/Solar Power in late ability band; LOUD) — CLOSED: moved into
  `band_weather` (band 0). Old tests: `TestI2_WeatherAbilityHealBeforeDrain` (2).
- **I3** (Shed Skin/Hydration cured after the tick; LOUD at HP level) — CLOSED:
  `band_status_cure` is band 2, before poison/burn. Old test:
  `TestI3_StatusCureAbilityBeforeTick::test_hydration_in_rain_takes_no_poison_tick`.
- **I3-status** (orb status cured same turn it lands — the one TRUE silent desync in I–M) —
  CLOSED: orbs apply in `band_late` (band 9), after the cure band. Old test:
  `test_hydration_in_rain_does_not_cure_flame_orb_burn_same_turn`.
- **L1** (cross-mon: side 0's whole chain ran before side 1's; LOUD) — CLOSED: superseded by
  the per-battler speed-order rework. Note the engine is deliberately battler-major (each
  battler's full chain, pokeemerald semantics), NOT Showdown's field-wide band-major — this is
  the modeled real-game behavior, validated by parity probes; do not re-file it as a bug.
  Old test: `TestL1_CrossMonResidualBandOrder` (passes under speed order).
- **L2** (within-band speed order ignored) — CLOSED by the same rework (speed sort computed
  once at phase start, `residuals.cpp:719-735`).

### Groups J / M — post-hit self-effect order (fixed post-audit; C++ mirrors)
- **J1** (Life Orb recoil before drain, fainting attackers that should survive; LOUD) — CLOSED:
  Life Orb/Shell Bell moved to the final `onAfterMoveSecondarySelf` position
  (`engine/src/post_hit.cpp:951`, after recoil at 855). Old test: `TestJ1_LifeOrbRecoilBeforeDrain`.
- **M1/M2** (drain applied LAST instead of during the hit; LOUD) — CLOSED: drain now applied
  inside the per-hit loop, before contact recoil and Life Orb
  (`engine/src/move_exec_damage.cpp:615-620`; Big Root/Liquid Ooze handled there). Old tests:
  `TestM1_LifeOrbAppliedBeforeDrain`, `TestM2_DrainAppliedAfterContactRecoil`.

### Group K — forced-switch reset parity (fixed post-audit; C++ mirrors)
- **K1/K2/K3** (forced switch skipped stat-stage reset / Regenerator / Natural Cure;
  SILENT-DESYNC) — CLOSED: both switch paths now share one full reset,
  `cpp_apply_switch_out_reset` (`engine/src/effects.cpp:629-640`; Natural Cure + Regenerator
  fire there). Old tests: `TestK1_ForcedSwitchResetsStatStages`,
  `TestK2_ForcedSwitchAppliesRegenerator`, `TestK3_ForcedSwitchAppliesNaturalCure`.
- **K4** (`crit_stage`/`locked_slot` leaks) — resolved in the old audit as provably INERT
  (crit no-crit sentinel 101.0 > max chance 100.0; locked_slot reads all volatile-gated).
  Moot anyway now that the shared reset clears everything. Closed.
- **K-DEDUP** — CLOSED (the shared reset IS the requested unification).

---

## Verified-correct (carried to prevent re-investigation)

- **Defender on-hit reactions fire on a lethal hit** (Cotton Down/Sand Spit apply; Weak
  Armor/Color Change guarded) — matches Showdown's deferred `.fainted` semantics. Not a bug.
- **Multi-hit moves fire Life Orb/drain/recoil ONCE after the hit loop** (per-hit contact
  recoil correctly inside the loop) — matches canonical.
- **Multi-hit secondary rolled once, not per hit** — reconciliation-equivalent: the only
  affected move is Double Iron Bash (flinch-only, binary, outcome dictated by observation).
  Data note: Twineedle modeled as 1 hit vs canonical 2 — would surface in HP-delta validation.
- **K4 crit sentinel**: reconciliation no-crit sentinel is 101.0 and max achievable crit chance
  is 100.0; changing either would make stale-crit-stage leaks live. (Now defense-in-depth only.)

---

## Pending (not yet analyzed) — re-pointed at new-repo paths

- `engine/src/post_hit.cpp` / `effects.cpp`: relative order of contact-ability `onDamagingHit`
  vs item reactions vs drain/recoil for **multi-target / multi-hit** moves (the single-target
  order was fixed by J/M; the doubles/multi-hit interleaving was never audited).
- The old doc's other two pending items are resolved: orb status timing (→ I3-status, CLOSED
  via rebanding) and the K4 follow-ups (→ verified inert, then mooted by the shared reset).

## Follow-up (separate task)

Port the 18 old-repo tests in `tests/test_static_issues_audit.py` (all now asserting canonical
behavior, xfail markers removed) as C++ / liveplay regression tests so the fixed H/I/J/K/L/M
orderings cannot silently regress in future engine edits.
