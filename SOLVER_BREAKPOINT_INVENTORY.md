# SOLVER_BREAKPOINT_INVENTORY — Engine HP-Breakpoint Mechanics

**SIGNED OFF by USER 2026-07-15** (review decisions in SOLVER_BUCKET_PLAN amendment 21;
§11 items all resolved; engine-fidelity bugs found during review → Task R2). Task 8 is
unblocked and builds against this document.

Research inventory for the bucket solver's BreakpointRegistry (SOLVER_BUCKET_PLAN Part 1
amendment 6, Part 3.5 Task 2). Enumerates every HP value at which the C++ battle engine's
behavior can change: transition semantics, triggers, damage, or move legality/failure.
Err-on-inclusion: entries that turn out redundant are cheap; a missed one is unsound.

**OUT OF SCOPE:** AI-scorer breakpoints (kill-estimate flips, cap-ties, Pursuit/Explosion/
Substitute/recovery AI thresholds from `ai_scorer.cpp` / `ai_damage.cpp`) are Task 9, a
separate inventory. Nothing from the AI scorer files is inventoried here.

**Classification legend**

- `REGISTRY` — closed-form threshold; implementable as a BreakpointRegistry entry.
- `COVERED-BY-hp_thresholds` — already computed with engine-exact arithmetic by
  `hp_thresholds()` in `engine/src/solver/engine_queries.cpp:219-302`; the registry
  delegates. Caveats listed in §12.
- `SPECIAL-CASE-§5.2` — HP-dependent/non-monotone map; conceded per plan §5.2, never
  interval-collapsed.
- `NOT-A-BREAKPOINT` — pure constant shift on the HP axis (or not HP-triggered at all);
  explanation given. Clamp kinks of shifts are broken out as separate rows.

**Arithmetic conventions used below:** all divisions are C++ `int32_t` floor division
(toward zero; all quantities non-negative here). `hp <= max_hp / 2` is NOT the same as
`2*hp <= max_hp` for odd `max_hp`; every formula is copied from code. `mhp` = `max_hp`
(engine reads `has_max_hp ? max_hp : stat_hp` in damage paths).

---

## 1. Transition-semantics boundaries (faint and survive-at-1)

| mechanic | trigger ID(s) | axis | engine formula | source | classification |
|---|---|---|---|---|---|
| Faint at 0 (move damage) | — | defender HP | `new_hp = max(0, hp - damage); fainted = (new_hp == 0)` after survival checks | move_exec_helpers.cpp:96-127 | REGISTRY (hp = 0 is a mandatory boundary; preimage `hp <= damage` handled by Expand's derived splits at `b + dmg`) |
| Faint at 0 (residual chips) | — | payer HP | every band: `p.hp = max(0, p.hp - c); if (p.hp == 0) faint` | residuals.cpp:109,125,146,154,235,278,327,334,350,460,472,485,513 | REGISTRY (same boundary; per-band chip `c` gives preimage kink at `hp = c`, see §7) |
| Endure survive | VOLATILE_ENDURE_ACTIVE (bit 2097152) | defender HP | `if (new_hp == 0 && (volatiles & ENDURE_ACTIVE)) new_hp = 1` | move_exec_helpers.cpp:99-100; residuals.cpp:602 (Future Sight path) | NOT-A-BREAKPOINT on HP axis (fires exactly at the faint boundary, already in B; Endure flag is d) |
| Focus Band survive | item 230 | defender HP | `new_hp == 0 && item == FOCUS_BAND` then 10% proc → `new_hp = 1` | move_exec_helpers.cpp:101-102; residuals.cpp:603-609 | NOT-A-BREAKPOINT on HP axis (faint-boundary member; adds an RNG flag-split, and `hp_thresholds` sets `residual_unknown` for it) |
| Focus Sash survive | item 275 | defender HP | `new_hp == 0 && item == FOCUS_SASH && hp == max_hp` → `new_hp = 1; item = NONE` | move_exec_helpers.cpp:103-105; residuals.cpp:611 | COVERED-BY-hp_thresholds (FullHp kind; see §12 caveat: only emitted when currently at full HP) |
| Sturdy survive | ability 5 | defender HP | `new_hp == 0 && ability == STURDY && !mold_breaker && hp == max_hp` → `new_hp = 1` | move_exec_helpers.cpp:106-109; residuals.cpp:612 (FS path has NO mold-breaker check) | COVERED-BY-hp_thresholds (FullHp) |
| Destiny Bond drag-down | VOLATILE_DESTINY_BOND | attacker HP | attacker takes `atk.max_hp` damage via `cpp_apply_damage` (own Endure/Band/Sash/Sturdy checks apply) — **ENGINE BUG (USER 2026-07-15): DB must faint directly, survival mechanics must NOT apply → Task R2** | move_exec_damage.cpp:248-251 | NOT-A-BREAKPOINT (constant lethal shift; faint boundary already in B; DB flag is d) |
| Explosion/Self-Destruct family self-faint | moves 120,153,720,802 | attacker HP | `cpp_faint_active` gated on `damage > 0` — **ENGINE BUG (USER 2026-07-15): must self-faint even on miss/Protect/zero damage → Task R2** | post_hit.cpp:875-878 | NOT-A-BREAKPOINT (HP-independent faint; d/transition event) |
| Memento self-faint | MOVE_MEMENTO | attacker HP | faints first, then attempts stat drops (Clear Body / −6 still faints ✓); USER spec: NO faint if move fails to activate (miss/Protect/Substitute) — **guard-path gating to be VERIFIED in Task R2** | effects.cpp:1492-1497 | NOT-A-BREAKPOINT (HP-independent) |
| Perish Song faint | VE_PERISH_SONG expiry | holder HP | counter expiry → `p.fainted = true; p.hp = 0` | residuals.cpp:547,589 | NOT-A-BREAKPOINT (counter-driven, d) |

## 2. Full-HP triggers (hp == max_hp)

| mechanic | trigger ID(s) | axis | engine formula | source | classification |
|---|---|---|---|---|---|
| Multiscale halves damage | ability 136 | defender HP | `cur == mhp` → `damage = floor(damage * 0.5)` (skipped if mold-breaker / ignore-ability move) | damage.cpp:1401-1407 | COVERED-BY-hp_thresholds (FullHp; §12 caveat) |
| Shadow Shield halves damage | ability 231 | defender HP | `cur == mhp` → `damage = floor(damage * 0.5)` (NOT mold-breakable; ignore-ability moves bypass) | damage.cpp:1409-1416 | COVERED-BY-hp_thresholds (FullHp) |
| Focus Sash / Sturdy eligibility | item 275 / ability 5 | defender HP | `hp == max_hp` (see §1) | move_exec_helpers.cpp:103-109 | COVERED-BY-hp_thresholds (FullHp) |
| Recovery moves fail at full | moves 105,303,456,135,355,236,234,235,208,659 (+ Life Dew) | user HP | `if (mon.hp >= mon.max_hp) { last_move_failed = true; return; }` | effects.cpp:1231-1233 | REGISTRY (full-HP boundary; also flips `last_move_failed`, which feeds Stomping Tantrum BP — d effect) |
| Swallow fails at full | MOVE_SWALLOW | user HP | `if (mon.hp >= mon.max_hp) { last_move_failed = true; return; }` | effects.cpp:1271-1273 | REGISTRY |
| Rest | MOVE_REST | user HP | `if (m.hp >= m.max_hp) { last_move_failed = true; return; }` else `m.hp = m.max_hp; m.status = SLEEP` — **FIXED by Task R (2026-07-14, amendment 20a)**: full-HP failure check added per USER decision | effects.cpp:1586-1597 | REGISTRY (full-HP legality boundary, same family as recovery-fail rows above) |

## 3. Item HP triggers (consumables)

Berry trigger chokepoint `check_berry` (effects.cpp:434-470): trigger iff
`mon.hp <= max_hp / threshold_denom` — literally `threshold_hp = mon.max_hp / threshold_denom;
if (mon.hp > threshold_hp) return false;` (effects.cpp:441-442). Gluttony (ability 82)
rewrites `threshold_denom == 4` to `2` (effects.cpp:439-440). Suppressed by opposing
Unnerve-family (abilities 127,266,267; effects.cpp:147-154). `check_berry` runs after
**every** `cpp_apply_damage` (move_exec_helpers.cpp:148-153 — i.e. after each hit of a
multi-hit), after residual poison/burn bands and the late-damage band
(residuals.cpp:340,356,520), and after Future Sight damage (residuals.cpp:624).

**Embargo note (USER review 2026-07-15):** Embargo (negates held-item effects, incl.
berries / Leftovers / Black Sludge) exists in Run & Bun but is **absent from this engine**
(`grep -rn -i embargo engine/src/` → zero matches). Known engine gap, postponed (§14);
no inventory rows are conditioned on it.

| mechanic | trigger ID(s) | axis | engine formula | source | classification |
|---|---|---|---|---|---|
| Sitrus Berry | item 158 | holder HP | trigger `hp <= max_hp / 2`; heal `max_hp / 4` (Ripen 247: `(int32_t)((long long)max_hp * 2 / 4)`); clamp `min(max_hp, hp + heal)` | effects.cpp:406,441-458 | COVERED-BY-hp_thresholds (Half). Heal-cap kink at `max_hp - heal`: REGISTRY |
| Oran Berry | item 155 | holder HP | trigger `hp <= max_hp / 2`; heal flat 10 (Ripen: 20); clamp | effects.cpp:407,449-458 | COVERED-BY-hp_thresholds (Half). Clamp kink at `max_hp - 10` only reachable if `max_hp/2 + 10 > max_hp` (tiny mons): REGISTRY |
| Berry Juice | item 34 | holder HP | trigger `hp <= max_hp / 2`; heal flat 20 (Ripen does NOT double Berry Juice); clamp | effects.cpp:408,449-458 | COVERED-BY-hp_thresholds (Half) |
| Stat pinch berries (Liechi 201, Ganlon 202, Salac 203, Petaya 204, Apicot 205) | items 201-205 | holder HP | trigger `hp <= max_hp / 4` (Gluttony: `/ 2`); +1 stage (Ripen +2) | effects.cpp:409-413,439-442 | COVERED-BY-hp_thresholds (Quarter) — **Gluttony variant NOT covered** (§11 item 1) |
| Lansat Berry (crit) / Starf Berry (random +2) | items 206, 207 | holder HP | trigger `hp <= max_hp / 4` (Gluttony `/ 2`); Starf consumes an oracle stat pick (NeedsRNG) | effects.cpp:414-415,462-468 | COVERED-BY-hp_thresholds (Quarter); Starf adds an RNG flag-split |
| Flavour berries (Figy 159, Wiki 160, Mago 161, Aguav 162, Iapapa 163) | items 159-163 | holder HP | trigger `hp <= max_hp / 4` (Gluttony `/ 2`); heal `max_hp / 2` (Ripen `max_hp * 2 / 2`); confuse if nature lowers the flavour stat; clamp | effects.cpp:416-420,449-461 | COVERED-BY-hp_thresholds (Quarter). Heal-cap kink at `max_hp - max_hp/2`: REGISTRY |
| Custap Berry (priority) | item 210 | holder HP (read at action-order time) | `threshold = (ability == GLUTTONY 82) ? max_hp / 2 : max_hp / 4; if (hp <= threshold) { item = NONE; goes first }` — suppressed by opposing Unnerve family | core_leaf.cpp:721-733 | COVERED-BY-hp_thresholds (Quarter) — **Gluttony variant NOT covered**; changes turn ORDER = transition semantics |
| Status/confusion-cure berries (Cheri 151, Chesto 149, Pecha 150, Rawst 152, Aspear 153, Persim 156, Lum 157), Leppa 154, White Herb 214, Focus Band 230 | items listed | — | status/PP/stat-triggered, not HP-triggered | effects.cpp:138-205,376-386; move_exec_helpers.cpp:288-294 | NOT-A-BREAKPOINT (no HP threshold) — `hp_thresholds` sets `residual_unknown=true` for these (engine_queries.cpp:61-69) |
| Type-resist berries (incl. Chilan) | resist_berry_type items | — | trigger on move type + SE; halves damage (Ripen ×0.25) | move_exec_damage.cpp:553-565 | NOT-A-BREAKPOINT (type-triggered; damage change lands in damage_table only if modeled — note it is applied OUTSIDE cpp_calculate_damage, see §11 item 11) |
| Leftovers / Black Sludge | items 234 / 281 | holder HP | see residual table §7 | residuals.cpp:214-243 | see §7 |

## 4. Ability HP thresholds

| mechanic | trigger ID(s) | axis | engine formula | source | classification |
|---|---|---|---|---|---|
| Berserk (+1 SpA on crossing half) | ability 201 | defender HP | `hp_before = hp + actual_damage; half = max_hp / 2; crossed = hp_before > half && half >= hp` (suppressed by attacker Sheer Force w/ secondary; not on sub hits) | post_hit.cpp:911-927 | REGISTRY (crossing breakpoint at `max_hp / 2`) |
| Emergency Exit / Wimp Out (post-hit) | abilities 194 / 193 | defender HP | same `crossed` formula; queues pending switch if bench exists | post_hit.cpp:928-931 | REGISTRY (transition-semantics change: forced switch) |
| Emergency Exit / Wimp Out (residual phase) | abilities 194 / 193 | holder HP | `half = max_hp / 2; hp_before > half && half >= hp` where `hp_before` is the snapshot BEFORE the whole residual phase | residuals.cpp:646-661,712-717,770-771 | REGISTRY |
| Emergency Exit / Wimp Out (entry hazards) | abilities 194 / 193 | switch-in HP | same formula vs pre-hazard HP; loops per re-entry | orchestrate.cpp:480-540 (`cpp_entry_ee_step`:494-496) | REGISTRY |
| Blaze / Torrent / Overgrow / Swarm (pinch 1.5× after STAB) | abilities 66 / 67 / 65 / 68 | attacker HP | `cur <= mhp / 3` and move type matches → ×1.5 | damage.cpp:1613-1630 | REGISTRY (attacker-axis breakpoint at `max_hp / 3`; damage_table reflects it per state, so it must be a bucket boundary for the ATTACKER) |
| Defeatist | ability 129 | attacker HP | `cur <= mhp / 2` → halves the attacking stat the move uses (Atk for physical, Sp.Atk for special — engine applies it to whichever `atk` was selected; verified correct per USER review 2026-07-15) | damage.cpp:1143-1148 | REGISTRY (attacker-axis at `max_hp / 2`) |
| Multiscale / Shadow Shield | 136 / 231 | defender HP | see §2 | damage.cpp:1401-1416 | COVERED-BY-hp_thresholds |
| Sturdy (survival) | 5 | defender HP | see §1 | move_exec_helpers.cpp:106-109 | COVERED-BY-hp_thresholds |
| Sturdy (OHKO immunity) | 5 | — | OHKO move breaks loop if defender Sturdy (any HP, not full-HP-gated) | move_exec_damage.cpp:533 | NOT-A-BREAKPOINT (HP-independent immunity, d) |
| Power Construct (Zygarde → Complete) | ability 211 | holder HP (EOT) | `hp <= max_hp / 2` → form change; **max_hp increases and hp += delta** | effects.cpp:1716-1721; post_hit.cpp:30-49 (`apply_form_change` HP adjust) | REGISTRY breakpoint at `max_hp / 2`; the resulting max_hp change is an axis-rescaling event (§11 item 6) |
| Schooling (Wishiwashi) | ability 208 | holder HP (EOT) | `hp > max_hp / 4` → School form; `hp <= max_hp / 4` → solo form (reversible) | effects.cpp:1726-1731 | REGISTRY (breakpoint at `max_hp / 4`; max_hp changes on form swap) |
| Shields Down (Minior) | ability 197 | holder HP (EOT) | `hp <= max_hp / 2` → core; `hp > half` → meteor (reversible) | effects.cpp:1732-1737 | REGISTRY |
| Zen Mode (Darmanitan/Galar) | ability 161 | holder HP (EOT) | `hp <= max_hp / 2` → Zen; else revert (reversible) | effects.cpp:1738-1745 | REGISTRY |
| Gulp Missile form pick (after Surf/Dive) | ability 241 | attacker HP | `form = (atk.hp > atk.max_hp / 2) ? GULPING : GORGING` | post_hit.cpp:290-297 | REGISTRY (attacker-axis at `max_hp / 2`; only if Cramorant in matchup) |
| Ice Face / Disguise absorb | abilities 248 / 209 | — | hit-triggered form flags, no HP read | move_exec_guards.cpp:874-882; move_exec_damage.cpp:393-402 | NOT-A-BREAKPOINT (d-flags) |
| Anger Shell | — | — | **not present in engine** (grep: no matches) | — | NOT-A-BREAKPOINT (absent) |

## 5. HP-preconditioned moves (legality / failure thresholds)

| mechanic | trigger ID(s) | axis | engine formula | source | classification |
|---|---|---|---|---|---|
| Substitute creation | MOVE_SUBSTITUTE | user HP | `cost = max_hp / 4; if (hp > cost && !has_sub) { hp -= cost; sub_hp = cost; }` — silently no-ops at `hp <= cost` | effects.cpp:1013-1019 | REGISTRY (breakpoint at `max_hp / 4`, strict `>` required) |
| Belly Drum | MOVE_BELLY_DRUM | user HP | `cost = max_hp / 2; if (hp <= cost) return; hp -= cost; Atk → +6` | effects.cpp:1327-1335 | REGISTRY (breakpoint at `max_hp / 2`, strict `>` required) |
| Curse (Ghost-type user) | MOVE_CURSE | user HP | `cost = max_hp / 2; if (hp <= cost) return; hp -= cost` + defender CURSED — **ENGINE BUG (USER 2026-07-15): at/below half HP Curse must still curse the target and the user self-faints (pays all remaining HP), not silently no-op → Task R2** | effects.cpp:1500-1506 | REGISTRY (boundary at `max_hp / 2` remains; semantics on the low side change with R2: curse+self-faint instead of fail) |
| Recovery-at-full fail / Swallow fail | see §2 | user HP | `hp >= max_hp` | effects.cpp:1233,1273 | REGISTRY |
| Endeavor fail | MOVE_ENDEAVOR | both HP | `dmg = defender.hp - attacker.hp; if (dmg <= 0) return -2` (fail) | core_leaf.cpp:423-426 | SPECIAL-CASE-§5.2 (equalizer; also a two-axis comparison) |

## 6. HP-dependent move power / fixed damage — §5.2 special cases

Variable BP resolved by `cpp_compute_variable_bp` (core_leaf.cpp:194-412, called from
move_exec_damage.cpp:441); fixed damage by `cpp_compute_fixed_damage`
(core_leaf.cpp:414-440, called from move_exec.cpp:805).

| mechanic | trigger ID(s) | axis | engine formula | source | classification |
|---|---|---|---|---|---|
| Brine | MOVE_BRINE | defender HP | `defender.hp <= defender.max_hp / 2 ? base * 2 : 0(=base)` | core_leaf.cpp:236-237 | REGISTRY (single boundary at defender `max_hp / 2`; two-valued BP, monotone within each side — unlike the continuous scalers below, this is registry-implementable) |
| Eruption / Water Spout | MOVE_ERUPTION, MOVE_WATER_SPOUT | attacker HP | `bp = max(1, 150 * attacker.hp / attacker.max_hp)` | core_leaf.cpp:271-272 | SPECIAL-CASE-§5.2 (every floor step of `150*hp/max_hp` is a boundary) |
| Wring Out | MOVE_WRING_OUT | defender HP | `bp = max(1, 120 * defender.hp / defender.max_hp + 1)` | core_leaf.cpp:274-275 | SPECIAL-CASE-§5.2 |
| Crush Grip | MOVE_CRUSH_GRIP | defender HP | `bp = max(1, 120 * defender.hp / defender.max_hp)` | core_leaf.cpp:277-278 | SPECIAL-CASE-§5.2 |
| Flail / Reversal | MOVE_FLAIL, MOVE_REVERSAL | attacker HP | `ratio = attacker.hp * 48 / attacker.max_hp;` bp = 200 (`ratio < 2`), 150 (`< 6`), 100 (`< 13`), 80 (`< 22`), 40 (`< 30`), else 20 | core_leaf.cpp:280-287 | SPECIAL-CASE-§5.2 (5 tier boundaries; note prototype conceded) |
| Super Fang / Nature's Madness | MOVE_SUPER_FANG, MOVE_NATURES_MADNESS | defender HP | `damage = max(1, defender.hp / 2)` | core_leaf.cpp:420-421 | SPECIAL-CASE-§5.2 (fractional-current-HP; image compression) |
| Final Gambit | MOVE_FINAL_GAMBIT | both HP | `damage = attacker.hp` (+ attacker self-faint) | core_leaf.cpp:422 | SPECIAL-CASE-§5.2 |
| Endeavor | MOVE_ENDEAVOR | both HP | `damage = defender.hp - attacker.hp` (fail if `<= 0`) | core_leaf.cpp:423-426 | SPECIAL-CASE-§5.2 (equalizer) |
| Counter / Mirror Coat / Metal Burst | ids per core_leaf | attacker d-state | `last_physical*2` / `last_special*2` / `last_damage*3/2`; fail if stored value `<= 0`. Stored values are ACTUAL damage taken (clamped by own HP at the time: `actual_taken = min(damage, hp)`) | core_leaf.cpp:427-438; move_exec_helpers.cpp:112-121 | SPECIAL-CASE-§5.2 (reflect; the clamp makes stored damage HP-history-dependent) |
| OHKO moves | Guillotine, Horn Drill, Fissure, Sheer Cold (move_exec_damage.cpp:112) | defender HP | `damage = defender.hp` (Sturdy immune regardless of HP) | move_exec_damage.cpp:532-535 | SPECIAL-CASE-§5.2 — **infrastructure-limited, not semantically hard (USER review 2026-07-15)**: behaves like a 1M-BP move (always-kill collapses the interval to the faint boundary), but the `damage = hp` override is applied OUTSIDE `cpp_calculate_damage`, so damage_table does not model it (§11 item 11 family). Prototype THROWS; an always-kill fast path is the documented refinement (§14) |
| Innards Out (on KO) | ability 215 | defender HP → attacker HP | attacker takes `hp_before` damage = defender's HP before the killing hit | move_exec_damage.cpp:253-264 | SPECIAL-CASE-§5.2 (defender-HP-valued damage to attacker) |
| Fixed-damage moves | Dragon Rage 40, Sonic Boom 20, Seismic Toss/Night Shade = level, Psywave (random) | — | constants / level-scaled / RNG — independent of defender HP and cannot crit | core_leaf.cpp:417-419,439+ | **SUPPORTED (reclassified per USER review 2026-07-15)** — not §5.2: damage is HP-independent, so the §5.2 corner damage-table-equality screen passes legitimately; crit-ordering is vacuous (no crit). Expand handles these via ordinary derived splits at `b + dmg` |
| Pain Split / Ruination / Hard Press | — | — | **not present in engine** (grep: no matches outside plan docs) | — | absent; would arrive only via new port |

## 7. Residual-phase chips and heals (end of turn)

All applied per battler in speed order, full chain per battler
(residuals.cpp:720-777; band order: weather, grassy terrain, status-cure, item heal,
aqua ring, ingrain, leech seed, poison, burn, late; then sticky-barb/nightmare/curse/bound,
timed-volatile tick, emergency-exit check). Every damage clamps at 0 (faint), every heal
clamps at max_hp. For a fixed d each is a constant shift `±c` with:

- **kink at `hp = c`** for damage (below it the image is pinned at 0 / faint), and
- **kink at `hp = max_hp − c`** for heals (above it the image is pinned at max_hp).

Both kinks are REGISTRY entries per plan amendment 6 (heal-cap kinks explicitly required).
The shift itself is NOT-A-BREAKPOINT.

| mechanic | trigger ID(s) | axis | exact amount `c` | source | classification |
|---|---|---|---|---|---|
| Sandstorm chip | weather, non-immune | holder HP | `max(1, max_hp / 16)` | residuals.cpp:104-113 | shift; kinks REGISTRY |
| Hail chip | weather, non-immune | holder HP | `max(1, max_hp / 16)` | residuals.cpp:122-129 | shift; kinks REGISTRY |
| Ice Body heal (hail) | ability 115 | holder HP | `max(1, max_hp / 16)` | residuals.cpp:115-121 | shift; heal-cap kink REGISTRY |
| Rain Dish heal | ability 44 | holder HP | `max(1, max_hp / 16)` | residuals.cpp:131-136 | shift; kink REGISTRY |
| Dry Skin (rain heal / sun chip) | ability 87 | holder HP | `max(1, max_hp / 8)` each way | residuals.cpp:137-151 | shift; kinks REGISTRY |
| Solar Power chip (sun) | ability 94 | holder HP | `max(1, max_hp / 8)` | residuals.cpp:152-158 | shift; kink REGISTRY |
| Grassy Terrain heal (grounded) | terrain | holder HP | `max(1, max_hp / 16)` | residuals.cpp:171-182 | shift; kink REGISTRY |
| Leftovers heal | item 234 (blocked by Klutz 103 / Magic Room; Embargo would also block but is absent from engine — §3 note) | holder HP | `max(1, max_hp / 16)` | residuals.cpp:216-224 | shift; **heal-cap kink at `max_hp − max(1, max_hp/16)` REGISTRY** (canonical Leftovers-loop kink) |
| Black Sludge (Poison-type heal / else chip) | item 281 | holder HP | heal `max(1, max_hp / 16)` or chip `max(1, max_hp / 8)` | residuals.cpp:225-240 | shift; kinks REGISTRY |
| Aqua Ring / Ingrain heal | volatiles 32768 / 65536 | holder HP | `max(1, max_hp / 16)` each | residuals.cpp:246-267 | shift; kinks REGISTRY |
| Leech Seed drain | volatile 2 (Magic Guard immune) | holder HP → opponent HP | `drain = max(1, max_hp / 8); drain = min(drain, p.hp)`; opponent heals `drain` (Big Root 296: `(int32_t)(drain * 1.3)`), Liquid Ooze 64 damages instead | residuals.cpp:270-313 | chip kink REGISTRY. **Opponent-heal amount depends on leecher HP when `hp < max_hp/8`** — cross-axis coupling below the leecher's chip kink (§11 item 5) |
| Poison Heal | ability 90 | holder HP | heal `max(1, max_hp / 8)` | residuals.cpp:318-323 | shift; kink REGISTRY |
| Toxic damage | STATUS_TOXIC | holder HP | `max(1, (int32_t)((long long)max_hp * toxic_turns / 16))`; `toxic_turns = min(toxic_turns + 1, 15)` | residuals.cpp:324-331 | shift PER toxic_turns value (toxic_turns ∈ d); kink at `c(t)` REGISTRY |
| Poison damage | STATUS_POISON | holder HP | `max(1, max_hp / 8)` | residuals.cpp:332-338 | shift; kink REGISTRY |
| Burn damage | STATUS_BURN | holder HP | `max(1, max_hp / divisor)`, divisor = 32 if Heatproof (85) else 16 | residuals.cpp:345-354 | shift; kink REGISTRY |
| Bad Dreams | ability 123 (vs sleeping/Comatose opp) | opponent HP | `max(1, opp.max_hp / 8)` | residuals.cpp:416-430 | shift; kink REGISTRY |
| Sticky Barb | item 288 | holder HP | `max(1, max_hp / 8)` | residuals.cpp:458-465 | shift; kink REGISTRY |
| Nightmare | VE_NIGHTMARE (while asleep) | holder HP | `max(1, max_hp / 4)` | residuals.cpp:470-477 | shift; kink REGISTRY |
| Curse (residual) | volatile 4 | holder HP | `max(1, max_hp / 4)` | residuals.cpp:483-490 | shift; kink REGISTRY |
| Bound (Wrap family) | VE_BOUND | holder HP | `max(1, max_hp / 6)` if inflictor holds Binding Band 544 else `max(1, max_hp / 8)`; skipped if inflictor gone | residuals.cpp:492-518 | shift; kink REGISTRY |
| Wish resolution | side.wish_hp | recipient HP | `hp = min(max_hp, hp + wish_hp)` where `wish_hp = caster.max_hp / 2` fixed at cast (effects.cpp:1201) | residuals.cpp:780-802 | shift; heal-cap kink at `max_hp − wish_hp` REGISTRY (wish_hp must live in d) |
| Future Sight damage | side.fs_damage | target HP | fixed stored damage via `apply_damage_fs` (Endure/Band/Sash/Sturdy checks apply) | residuals.cpp:597-625,805-830 | shift; faint boundary + full-HP (Sash/Sturdy) already in B |
| Flame Orb / Toxic Orb | items 273 / 272 | — | status infliction, no HP read | residuals.cpp:432-440 | NOT-A-BREAKPOINT (d) |

## 8. On-hit chip / recoil / drain (fraction-of-max vs fraction-of-damage)

Fraction-of-max entries are constant shifts (kink at `hp = c`, REGISTRY, same logic as §7).
Fraction-of-DEALT-damage entries are shifts whose size depends on the damage cell, and —
critically — on `actual_damage = min(damage, defender.hp_before)`: in the overkill region
(defender HP < damage) the attacker-axis image varies with defender HP (§11 item 5).

| mechanic | trigger ID(s) | axis | engine formula | source | classification |
|---|---|---|---|---|---|
| Move recoil (Double-Edge etc.) | `md.recoil_num/recoil_den` (Rock Head 69 / Magic Guard immune) | attacker HP | `max(1, (int32_t)((long long)actual_damage * recoil_num / recoil_den))` | post_hit.cpp:850-863 | shift per cell; NOT-A-BREAKPOINT on defender axis above kill boundary; **overkill region couples to defender HP** (§11 item 5) |
| Struggle recoil | move 165 | attacker HP | `max(1, max_hp / 4)` | post_hit.cpp:865-873 | shift; kink REGISTRY |
| Life Orb recoil | item 270 (Magic Guard / Sheer Force-with-secondary / Magic Room suppress) | attacker HP | `max(1, max_hp / 10)`; fires when `damage > 0` (even full-overkill) | post_hit.cpp:938-948 | shift; kink REGISTRY |
| Shell Bell heal | item (I_SHELL_BELL) | attacker HP | `max(1, actual_damage / 8)`, clamp at max_hp | post_hit.cpp:950-957 | shift per cell; heal-cap kink; overkill coupling (§11 item 5) |
| Drain moves (Absorb family, Drain Punch, etc.) | `md.drain_num/drain_den` | attacker HP | `drain_heal = max(1, (int)((long long)hit_actual * drain_num / drain_den))`; Big Root: `(int)(drain_heal * 1.3)`; Liquid Ooze 64 reverses to damage; clamp at max_hp | move_exec_damage.cpp:601-628 | shift per cell; heal-cap kink; overkill coupling (§11 item 5); per-HIT for multi-hit |
| Rough Skin / Iron Barbs | abilities 24 / 160 (contact) | attacker HP | `max(1, max_hp / 8)` per hit | move_exec_damage.cpp:632-648 | shift; kink REGISTRY |
| Rocky Helmet | defender item (contact) | attacker HP | `max(1, max_hp / 6)` per hit | move_exec_helpers.cpp:160-193 (recoil at 177) | shift; kink REGISTRY |
| Aftermath (on KO, contact) | ability 106 (Damp suppress) | attacker HP | `max_hp / 4` (no max(1,·)) | move_exec_damage.cpp:275-286 | shift; kink REGISTRY |
| Spiky Shield contact | protect move | attacker HP | `max(1, max_hp / 8)` | move_exec_guards.cpp:330-340 | shift; kink REGISTRY |
| HJK / Jump Kick / Supercell Slam crash (on miss) | HJK_MOVES | attacker HP | `max(1, max_hp / 2)` | move_exec_guards.cpp:702-717 | shift; kink REGISTRY (miss branch is an AND-branch already) |
| Steel Beam self-damage (hit AND miss paths) | move 796 | attacker HP | `max(1, max_hp / 2)` | post_hit.cpp:758-766; move_exec_guards.cpp:719-726 | shift; kink REGISTRY |
| Gulp Missile projectile | defender Cramorant forms | attacker HP | `max_hp / 4` (no max(1,·)) | move_exec_helpers.cpp:197-215 | shift; kink REGISTRY |
| Cheek Pouch (on berry consume) | ability 167 | holder HP | heal `max(1, max_hp / 3)`, clamp | effects.cpp:158-166; post_hit.cpp:233-243; move_exec_helpers.cpp:297-303 | shift; heal-cap kink REGISTRY |
| Liquid Ooze (drain/Leech Seed/Strength Sap reversal) | ability 64 | attacker/opponent HP | damage equal to would-be heal, clamp 0 | move_exec_damage.cpp:610-618; residuals.cpp:296-301; effects.cpp:1212-1218 | shift per amount; faint boundary in B |

## 9. Other heals and switch/entry effects

| mechanic | trigger ID(s) | axis | engine formula | source | classification |
|---|---|---|---|---|---|
| Recovery moves heal amount | RECOVERY_HALF list (effects.cpp:1152) | user HP | sun (or Shore Up in sand): `max_hp * 2 / 3`; rain/sand/hail: `max_hp / 4`; else `max_hp / 2`; Life Dew `max_hp / 4`; clamp | effects.cpp:1235-1252 | shift; heal-cap kink at `max_hp − heal` REGISTRY (weather ∈ d) |
| Swallow heal | MOVE_SWALLOW | user HP | denom 4/2/1 by stockpile_count (1/2/3): `max_hp / denom`; clamp | effects.cpp:1270-1283 | shift; heal-cap kink REGISTRY (stockpile ∈ d) |
| Heal Pulse | MOVE_HEAL_PULSE | target HP | `heal = target.max_hp / 2`; clamp | effects.cpp:1189-1193 | shift; heal-cap kink REGISTRY |
| Strength Sap | MOVE_STRENGTH_SAP | user HP (heal) / target Atk (amount) | `heal_amount = cpp_effective_stat(target, 1)`; fail if `target.stage0 == -6`; Liquid Ooze reverses; clamp | effects.cpp:1204-1229 | shift; heal-cap kink at `max_hp − heal_amount` REGISTRY (heal_amount from opponent d, not HP) |
| Absorb abilities heal (Volt/Water Absorb, Earth Eater, Dry Skin on-hit) | type-immunity abilities | defender HP | `min(max_hp, hp + max_hp / 4)` | move_exec_guards.cpp:360-370 | shift; heal-cap kink REGISTRY (trigger is move-type, not HP) |
| Regenerator (switch-out) | ability 144 | switcher HP | `heal = max_hp / 3`; clamp | effects.cpp:637-643 | shift; heal-cap kink REGISTRY (fires on switch transition) |
| Stealth Rock (entry) | SC_STEALTH_ROCK (Magic Guard / Heavy-Duty Boots immune) | switch-in HP | `damage = max(1, (int32_t)(max_hp * effv / 8.0))` — **double-precision multiply then truncate**; effv = product of type effectiveness vs Rock | effects_entry.cpp:36-47 | shift; kink at `hp = damage` REGISTRY (must mirror the double arithmetic exactly) |
| Spikes (entry, grounded) | SC_SPIKES_1/2/3 | switch-in HP | `max_hp / 8`, `/ 6`, `/ 4` by layer; `max(1, ·)` | effects_entry.cpp:69-84 | shift; kink REGISTRY |
| Toxic Spikes / Sticky Web | SC_* | — | status / stat, no HP read | effects_entry.cpp:50-67,86-90 | NOT-A-BREAKPOINT |
| Rest full heal | MOVE_REST | user HP | `hp = max_hp` (image collapses to max_hp) | effects.cpp:1586-1595 | NOT-A-BREAKPOINT as a threshold, but the map is non-injective (image compression to a point) — trivially interval-safe |
| Confusion self-hit | 40-BP typeless self-damage | user HP | routed through `cpp_apply_damage` (Endure/Band/Sash/Sturdy apply) | move_exec_premove.cpp (self-hit); move_exec_helpers.cpp:96+ | shift per cell. §5.1 stunlock concession is **PLAYER-side only** (USER 2026-07-15): opponent confusion self-hits are adversarial AND-branches (opponent hurting itself only helps the certificate), NOT conceded |

## 10. HP-axis structural events (not thresholds, but registry-relevant)

| mechanic | trigger ID(s) | axis | engine formula | source | classification |
|---|---|---|---|---|---|
| Level-up on opponent faint (EXP) | side-0 only | max_hp itself | `new_hp = min(new_max_hp, hp + (new_max_hp − max_hp))` | exp.cpp:74-93 | axis rescale: ALL fraction-of-max breakpoints move (§11 item 6) |
| Form change stat swap | Power Construct / Schooling / Zen / Shields Down / Cramorant / etc. | max_hp itself | `new_hp = (new_max_hp > max_hp) ? hp + delta : min(hp, new_max_hp)` | post_hit.cpp:30-49 | axis rescale (§11 item 6) |
| Substitute sub_hp | VOLATILE_SUBSTITUTE | separate sub_hp axis | created at `max_hp / 4`; absorb: `damage >= sub_hp` breaks else `sub_hp -= damage`; bypassed by sound/Infiltrator/Hyperspace | effects.cpp:1013-1019; move_exec_damage.cpp:538-551 | second HP-like axis — needs an owner decision (§11 item 12) |
| Faint → forced switch prompts / post-faint rounds | — | — | hp==0 drives pending switches, post-faint replacement rounds, EE entry loops | orchestrate.cpp:565-600; turn.cpp:195-330 | transition semantics anchored at hp = 0 (already in B) |

## 11. Uncertain / needs owner decision — ALL RESOLVED (USER review 2026-07-15)

1. **Gluttony NOT modeled by `hp_thresholds`** — **RESOLVED: implement fully in Task 8**
   (USER: "simplest full impl, no hacks"): extend `hp_thresholds()` with the
   ability-conditional denominator (`/ 2` for Gluttony holders) and add the Custap
   action-order site. No registry-side workaround.
2. **`hp_thresholds` FullHp entries gated on `cur_hp == max_hp`** — **RESOLVED:
   neutralized by design**: `BreakpointRegistry::instantiate` seeds `{0, max_hp}`
   UNCONDITIONALLY (Task 4, plan amendment), so the max_hp boundary exists regardless of
   the gating. No change to `hp_thresholds` needed.
3. **`residual_unknown` routing** — **RESOLVED: THROW confirmed** (USER item 3: throw for
   unimplemented is OK). Skeleton behavior stands.
4. **Rest full-HP failure** — **RESOLVED: engine gap, FIXED by Task R** (amendment 20a).
   Full-HP is now a Rest-legality breakpoint (§2 row updated).
5. **Overkill cross-axis coupling** — **RESOLVED: THROW for now** (USER 2026-07-15,
   supersedes amendment 20(b)'s concede-tag). Expand's shift-assert throws in the
   coupled fainting cell; promote to concede tag only if the Task 10 rcheck census is
   noisy. Postponed refinement in §14.
6. **max_hp not battle-constant** — **RESOLVED: postponed** (USER item 6: testing at
   L100, no level-ups; form-change species excluded from prototype scope). Registry
   instantiation is still per-d as recommended. §14.
7. **Chip-kink mechanism** — **RESOLVED: derived splits at Expand time** (USER item 7:
   "if both are sound, pick the fastest one"; Expand already computes residual delta
   candidates, making it the fast convention — one mechanism, no double-splitting).
8. **Wish/Strength Sap heal amounts in d** — **RESOLVED: confirmed fine** (USER item 8);
   ordinary status-parameterized entries, values live in d.
9. **Mid-sequence berry checks in multi-hit** — **RESOLVED**: Expand's cumulative
   convolution covers the faint boundary; the full per-hit berry/trigger interaction is
   precomputable per USER's outline (per-hit deltas enumerable beforehand → finite set of
   cumulative damage values). Documented as refinement in §14; amendment-8 multi-hit
   concede tag stands for the hard sub-case meanwhile.
10. **Toxic counter in d-hash** — **RESOLVED: verified**, `toxic_turns` is in the ctx
    d-hash; per-bucket chip amounts constant.
11. **damage_table caveat inheritance** — **RESOLVED: Task 6 reuses the analytic scope
    bits**, which cover these damage-side caveats (Parental Bond, Metronome ramp,
    Minimize, OHKO override, type-resist berries). OHKO additionally noted
    infrastructure-limited in §6.
12. **Substitute sub_hp axis** — **RESOLVED: excluded from prototype** (USER item 11:
    separate axis long-run, exclude now). Concede tag on VOLATILE_SUBSTITUTE. True third
    axis is the long-run design — note post-Sub healing extends the reachable space by
    `max_hp / 4`, so the axis is genuinely needed for exactness. §14.

## 12. hp_thresholds coverage map

`hp_thresholds()` (engine_queries.cpp:219-302) covers, with engine-exact arithmetic:
Focus Sash / Sturdy / Multiscale / Shadow Shield at `max_hp` (FullHp — but only when
currently at full, item 2 above); Sitrus / Oran / Berry Juice at `max_hp / 2` (Half);
the 12 quarter berries and Custap at `max_hp / 4` (Quarter — no Gluttony, item 1 above);
`residual_unknown` for status berries / Lum / Persim / Leppa / Focus Band / White Herb.
Everything else in this inventory (Berserk / Emergency Exit / Wimp Out crossings, pinch
abilities, Defeatist, Brine, form-change thresholds, move HP-preconditions, all heal-cap
and chip kinks, §5.2 moves) is NOT in `hp_thresholds` today.

## 13. Completeness statement

Searched, in `/home/Fracture/CLionProjects/NuzlockeAI/engine/src/` (AI scorer files
`ai_scorer*.cpp`, `ai_damage.cpp`, `ai_analytic.cpp`, `ai_policy.cpp` deliberately
excluded per task scope):

- **Full reads**: residuals.cpp (all 832 lines), engine_queries.cpp/.h; targeted full-block
  reads of damage.cpp (all 4 `.hp` read sites: 1146, 1404, 1413, 1625, plus compute_bp
  913-1010), core_leaf.cpp (variable BP 194-412, fixed damage 414-440, priority item
  700-740), effects.cpp (berries 130-470, Regenerator 620-660, move effects 1000-1600,
  EOT form changes 1700-1750), post_hit.cpp (items/abilities 220-310, on-hit tail
  740-960 incl. recoil/Berserk/Life Orb/Shell Bell), move_exec_helpers.cpp (apply_damage
  85-215, Cheek Pouch 297-303), move_exec_guards.cpp (protect penalties, absorb heal,
  miss consequences, Ice Face), move_exec_damage.cpp (damage loop 390-660, faint effects
  240-290), effects_entry.cpp (hazards 20-90), orchestrate.cpp (EE entry loop 480-540),
  turn.cpp (forced-switch hooks), exp.cpp (level-up stat commit 74-93), post_hit.cpp:30-49
  (form-change HP adjust).
- **Grep patterns over every non-AI .cpp/.h**: `max_hp`, `\.hp\b`, `->hp\b`, `hp <=`,
  `hp <`, `hp >=`, `hp ==`, `/ 2`, `/ 3`, `/ 4`, `/ 6`, `/ 8`, `/ 16`, `/ 32`,
  `PAIN_SPLIT`, `RUINATION`, `HARD_PRESS`, `ANGER_SHELL`, `OHKO`, `FALSE_SWIPE`,
  `ICE_FACE`, `DISGUISE`, `Gluttony`, `Ripen`. Final catch-all: `grep -l max_hp` over all
  engine sources — every hit file is covered above (codec.cpp / state_eq.cpp are
  serialization/equality only; lookup*, stats.cpp, forced_trace.cpp, game_driver.cpp,
  solver_turn.cpp have no HP-threshold logic).
- **Absent mechanics confirmed by grep**: Pain Split, Ruination, Hard Press, Anger Shell,
  False Swipe (no matches). Magic Room's Leftovers/Life Orb suppression and Klutz are
  d-conditions, not HP conditions.

Reviewer spot-check suggestions: the four damage.cpp `.hp` sites (only HP-dependence in
the damage formula), `check_berry`'s single trigger comparison (effects.cpp:441-442), and
the three Emergency Exit crossing sites (post_hit.cpp:917, residuals.cpp:653,
orchestrate.cpp:496) which all share the `hp_before > half && half >= hp` idiom.

## 14. Postponed mechanics (USER-approved deferrals, 2026-07-15)

Canonical list of everything deliberately NOT handled by the prototype. Each entry says
what the prototype does today and what the eventual fix is. Nothing here is a soundness
hole: every deferral either throws (loud) or concedes (tagged), never silently collapses.

| # | mechanic | prototype behavior | eventual handling |
|---|---|---|---|
| 1 | Overkill cross-axis coupling (drain/recoil/Shell Bell/Leech Seed heal/Innards Out scaling with `min(damage, hp)`) | THROW (Expand shift-assert fires in the coupled fainting cell; USER: "throw for now", supersedes amendment 20(b) concede-tag) | Per-endpoint transition + survivor-axis image assertion within the fainting cell; promote to concede tag first if rcheck census is noisy |
| 2 | Substitute `sub_hp` axis | Concede tag on VOLATILE_SUBSTITUTE | True third interval axis (USER item 11). Note: post-Sub healing extends reachable space by `max_hp / 4`, so the axis is required for exactness |
| 3 | Multi-hit hard sub-case (per-hit berry/trigger interactions mid-sequence) | Amendment-8 concede tag | USER's outline: per-hit deltas (berry heals, trigger effects) are enumerable beforehand → precompute the finite set of cumulative damage values and split on all of them |
| 4 | §5.2 continuous HP scalers (Eruption/Water Spout, Wring Out, Crush Grip, Flail/Reversal, Super Fang, Final Gambit, Endeavor) | Conceded per §5.2 (never interval-collapsed) | Piecewise-constant tier splitting (every floor step / tier boundary as breakpoints) if ever needed; Flail/Reversal only has 5 tiers |
| 5 | Counter / Mirror Coat / Metal Burst | Conceded §5.2 (stored damage is HP-history-dependent via the actual-damage clamp) | Carry stored-damage value in d, or concede permanently (niche) |
| 6 | OHKO moves | THROW (infrastructure-limited: `damage = hp` override applied outside `cpp_calculate_damage`, not in damage_table) | Always-kill fast path: collapse the interval image to the faint boundary (semantically a 1M-BP move); Sturdy immunity is d |
| 7 | `residual_unknown` holders (status berries, Lum, Persim, Leppa, Focus Band, White Herb) | THROW (Task 4 skeleton; USER confirmed) | Model the status-triggered consumption in d (not HP-triggered, so no interval split needed — just d-transition fidelity) |
| 8 | Form-change species (Zygarde, Wishiwashi, Darmanitan, Minior, Cramorant, Eiscue, Morpeko) + max_hp rescaling | Out of prototype scope (L100 testing, no such species in fixtures); registry is per-d so thresholds recompute if hit | Axis-rescale event handling: remap `[lo, hi]` through the `new_hp` formula (post_hit.cpp:30-49) and re-instantiate breakpoints for the new max_hp |
| 9 | EXP / level-up (player side, opponent faint) | Out of prototype scope (L100 = no level-ups) | USER requirement (recorded): level is a Question parameter; level-up applied after the matchup, before the state check — same axis-rescale mechanism as #8 |
| 10 | Embargo | ABSENT FROM ENGINE (Run & Bun has it; engine has zero matches) — known gap, nothing to model | Port the mechanic into the engine (negates held-item effects: berries, Leftovers, Black Sludge, Life Orb, ...), then it is a pure d-flag, no HP breakpoint |
| 11 | Mid-turn switch encoding (pending switches, EE/faint replacement rounds inside a bucket step) | Prototype buckets are per-(state,action) with forced switches resolved by the oracle as separate steps | Revisit when 6v6 chain integration lands; may need explicit switch-phase bucket states |
| 12 | Opponent confusion / stunlock branches | Adversarial AND-branches (opponent self-hits only help the certificate) — NOT conceded; only PLAYER-side stunlock is conceded per §5.1 | Player-side: possible partial modeling of self-hit damage cells if concession rate is too high in practice |
