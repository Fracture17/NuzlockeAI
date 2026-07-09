# TODO

## 2b. Doubles same-species target identification
Damage events and HP-delta matching key off the target's *species* (`_sum_damage`,
`_per_hit_damages`, candidate filtering). In doubles, two opposing Pokémon can share the
same species (e.g. two Zubats), so species-keyed lookups sum/mix damage across both
targets and cannot tell them apart. Need a per-slot target identifier rather than a bare
species key. Deferred — no chosen solution yet.

## 4. Trainer species name alias map (I-047) — MOSTLY RESOLVED
RESOLVED: `liveplay/data/name_aliases.py` adds `SPECIES_ALIASES` (47 confident mappings),
consulted by `_lookup_enum` (play.py) before normalized lookup, and a reverse
`SPECIES_TO_EMULATOR_NAME` map (form → base name) wired into `liveplay/state_transition.py`
so OCR'd opponent forms match their base name. `_lookup_enum` now raises on any unmatched
name (no silent NONE). The 47 mapped forms (all `_Galarian/_Alolan/_Hisuian`, apostrophe
`_U2019D`, `_Female`→`_F`, Calyrex_Ice_Rider, Urshifu_Rapid_Strike_Style,
Zygarde_50_Power_Construct→ZYGARDE, Greninja_Battle_Bond→GRENINJA_BOND,
Oricorio_Pau→ORICORIO_PA_U, Floette_Eternal_Flower→FLOETTE_ETERNAL, Wormadam cloaks,
Pikachu_World_Cap→PIKACHU_WORLD) resolve.

REMAINING — 7 cosmetic forms skipped (uncertain which numbered enum variant matches the
pkl pattern name; our enum only has `_1.._N` with no name key). These will RAISE if they
appear in a trainer until mapped. They are stat-identical to base, so the mapping is
cosmetic only:
  Furfrou_Heart_Trim → FURFROU_1..9 (which?)
  Florges_Orange_Flower → FLORGES_1..4 (which?)
  Alcremie_Caramel_Swirl → ALCREMIE_1..8 (which?)
  Vivillon_Elegant, Vivillon_Modern, Vivillon_Sun, Vivillon_Garden → VIVILLON_1..19 (which?)
Fix when known: add to `SPECIES_ALIASES` (and `SPECIES_TO_EMULATOR_NAME` → base name).
Run `SCRIPTS/validate_trainer_data.py` to confirm zero HARD failures after.


## BUG — Doubles multiple speed ties per turn share one SPEED_TIE answer (deferred)
The dynamic turn queue can encounter more than one speed tie within a single DOUBLES turn
(up to one per re-selection of the next un-acted actor). The current injection model carries
a single SPEED_TIE answer per turn, so every tie in that turn resolves the same way instead
of being decided independently. Correct for SINGLES (at most one tie per turn); silently
wrong in doubles.

Where: `_select_next_action` (engine/src/core_leaf.cpp / old src/engine/core.py) raises
`_NeedsRNG(SPEED_TIE)` on a full-key tie; `_advance_queue` (old src/simulator.py) injects
the answer from `self._rng_inject`. Both treat SPEED_TIE as a single per-turn event.

Fix: make SPEED_TIE a per-tie sequence or keyed answer (key on the tied slot set / a tie
index), so each tie consumes its own injected outcome; the sweep must enumerate/inject one
answer per tie. Built on the dynamic-queue work (see NOTE above, record `dynamic_turn_queue`).

Status: DEFERRED (owner decision) — singles-correct now; revisit when doubles is enabled.
Related doubles-gated items: TODO 2b, TODO 10 (I-031), TODO 11.


## 10. Doubles-gated fatal raises (latent, currently unreachable in singles) (I-030/031/032/033)
[old-repo until Stage E]
All four raise only when doubles states reach the sweep. Currently blocked by
`_build_battle_state` hardcoding `active_indices=[0]` (singles only).

  I-030: Spread + multi-hit unsupported — `_expand_action_targets` (sim_runner.py:1913-1919).
    A spread move with >1 hit raises. Needs ≥2 active slots.

  I-031: Same-species ambiguous recipient — `_slot_for_name` (sim_runner.py:279).
    A message recipient matches both active mons (mirror-species doubles) → can't
    disambiguate → raise. Related to TODO 2b (same-species target identification).

  I-032: HP-delta slot overflow — `_check_hp_match` (sim_runner.py:1294-1300).
    An opponent slot has HP deltas but `opponent_max_hp` has fewer entries → raise.
    Per-slot doubles indexing assumption not yet built.

  I-033: Flinch cross-side attribution mismatch — sim_runner.py:561-570.
    The mover preceding a PKMNFLINCHED is on the wrong side vs. expected attacker → raise.
    May fire in unusual singles turn orders too; doubles makes it more likely.

## 11. RANDOM_NORMAL targeting uses raw random.choice in doubles — no oracle (I-044)
`_resolve_targets` (engine/src/core_leaf.cpp): `chosen = random.choice(foe_slots)`.
In singles, foe_slots has exactly one entry so this is deterministic. In doubles, it
silently picks one of two foe slots with no oracle, no RNGEvent, no simulator pause.
The sweep can't enumerate which target was chosen; candidates that simulated the wrong
target will have mismatched HP deltas but no signal indicating why. Currently gated
by singles-only stress states, but will silently mis-track in doubles.
Fix: route through the oracle as a Category-A event before enabling doubles (analogous
to ROAR_TARGET). Note: in the C++ GameDriver (oracle pause/resume), this is tracked
as `random_normal_oracle_deferred` — a doubles-oracle phase handles it.


## 15. Random-move-selection moves need result back-injection from observed messages (I-036)
[old-repo until Stage E]
Metronome, Sleep Talk, Assist, Mirror Move, and Copycat all resolve to a randomly chosen
move. The simulator pauses at `AWAIT_MOVE_RNG` for METRONOME_MOVE / SLEEP_TALK_MOVE /
ASSIST_MOVE with no pre-injected answer → `UninjectedRNGError` → branch filtered → if the
real turn used one of these moves, all branches filter → no-survivors → CRASHED.
The matcher already sets `unconstrained_moves=True` for Metronome/Assist; the sweep has
no equivalent bypass.
Fix: back-resolve the chosen move from observed battle messages (the "used X" line that
follows the random-move-selection), then inject it as the oracle answer for the pause so
the correct branch survives. Each of these moves produces a visible USEDMOVE message for
the sub-move chosen — that is the injection source.

## 17. Residual-phase Category-A RNG (Moody, Starf Berry) needs injection support (I-038)
[old-repo until Stage E]
`_run_to_decision_boundary` (sim_runner.py:925-930) unconditionally raises
`UninjectedRNGError` for any `AWAIT_RESIDUAL_RNG` pause, with no pre-injected set and no
event check. The simulator emits this phase when `_apply_residuals` calls `oracle(event)`
for a Category-A event (Moody's random stat pair, Starf Berry's random stat) and gets
`_NeedsRNG`. If either fires in the real battle, all candidates are filtered →
no-survivors → CRASHED.
Fix: back-resolve the outcome from the observed end-of-turn message (the "X's [stat] rose
sharply!" notification), then inject it as the oracle answer before the residual phase
re-runs. Requires a pre-residual snapshot/re-execute flow analogous to the move-phase
injection, but scoped to the residual step.

## 18. Implement effects for kept-but-unimplemented status moves
These STATUS moves are retained in the Move enum but currently have NO engine effect
(no NN primitive and no real effect logic — they execute as no-ops). They were kept
(rather than commented out with the other 67 unimplemented moves) because they are
plausible to encounter and worth implementing properly:
- EMBARGO — block the target's item use for 5 turns (VolatileEffect.EMBARGO exists but
  is not referenced by the engine).
- PAIN_SPLIT — average the user's and target's current HP.
- STRING_SHOT — lower the target's Speed by 2 stages.
- HARDEN — raise the user's Defense by 1 stage. (Currently only AI-classified via
  DEFENSIVE_SETUP_MOVES; the engine applies no boost, so it is a no-op in battle.)

---

## Doubles-gated open findings (mined from *Issues.md, Stage C)

Entries below were extracted from RECORDS/AbilityIssues.md, RECORDS/AIIssues.md,
RECORDS/ItemIssues.md, RECORDS/MechanicIssues.md, and RECORDS/MoveIssues.md in the
old repo. Each entry is either explicitly doubles-only, explicitly deferred until doubles
is enabled, or is a bug whose impact is zero in singles but real in doubles.

### MechanicIssues.md — Aurora Veil Doubles Multiplier (`aurora_veil_doubles_multiplier`)
Aurora Veil uses 0.5× in doubles instead of the correct 2732/4096 (~0.667×); Reflect and
Light Screen already use the correct doubles multiplier. Affected mechanic: screen damage
reduction in doubles format.

### MechanicIssues.md — Spread Move 0.75× Penalty Applied Even When Only One Target Is Alive (`spread_move_penalty_one_target`)
The 0.75× spread-move reduction is applied based on move target type alone, not the live
target count; if one opponent has fainted, the reduction should be lifted. Affected
mechanic: spread-move damage calculation in doubles.

### MechanicIssues.md — Rage Powder Missing Grass-Type and Safety Goggles Bypass (verify)
Rage Powder/Follow Me redirect logic may not exempt Grass-types and Safety Goggles holders
from redirection. Doubles-only mechanic; no singles impact.

### MechanicIssues.md — Leech Seed Doubles Heals Wrong Slot (`leech_seed_doubles_heals_wrong_slot`)
Leech Seed drain always heals `active_indices[0]` on the opponent's side; in doubles the
healing should go to the slot that used Leech Seed. Affected mechanic: residual Leech Seed
heal routing in doubles.

### MechanicIssues.md — Doubles Speed Ties Not Properly Randomized (`doubles_speed_tie_not_randomized`)
Same-side speed ties always resolve by slot order (stable sort); the speed-tie
detection/logging fires only in singles (len==2 check). Both picks should be random in
doubles. Affected mechanic: turn-order tiebreaking in doubles.

### MechanicIssues.md — Binding Band in Doubles Always Checks Opponent Slot 0 (`binding_band_doubles_wrong_slot`)
End-of-turn bound damage checks `active_indices[0]` for a Binding Band; if the trapper
was in slot 1 the check is wrong. Affected mechanic: bound residual damage item lookup in
doubles.

### MechanicIssues.md — Doubles: Slot 1 Switch Applies Entry Hazards and Entry Effects to Slot 0 (`doubles_slot1_switch_wrong_hazard_target`)
`_apply_entry_hazards` and `_apply_entry_effects` unconditionally read `active_indices[0]`;
a slot 1 switch-in causes hazard damage and entry abilities to target the existing slot 0
Pokémon. Affected mechanic: switch-in entry effects and hazards in doubles.

### MechanicIssues.md — Wish and Future Sight Heal/Damage Slot 0 in Doubles (`wish_future_sight_doubles_wrong_slot`)
Wish and Future Sight residuals always resolve against `active_indices[0]`; in doubles
the recipient should be the slot that used/targeted the move. Affected mechanic: delayed
heal/damage slot routing in doubles.

### AbilityIssues.md — Dancer (Teeter Dance / Lunar Dance in doubles)
Dancer copies dance moves by applying a predefined stat-change table rather than
re-executing the move; Teeter Dance and Lunar Dance require actual move execution (ally
heal, confusion spread) that only matters in doubles. Affected mechanic: Dancer ability
copy execution in doubles.

### AbilityIssues.md — Friend Guard Missing Mold Breaker Bypass (`Friend Guard`)
Friend Guard reduces damage by 0.75× with no Mold Breaker check; explicitly noted as
doubles-only (no ally in singles). Affected mechanic: Friend Guard damage reduction in
doubles.

### AIIssues.md — switch_ai_doubles_no_switching
In doubles the AI should never voluntarily switch; `select_ai_action` has no
doubles-awareness and may trigger a voluntary switch. Affected mechanic: AI action
selection in doubles.

### AIIssues.md — doubles_no_target_selection
The AI is entirely singles-only; in doubles no target selection or partner-aware scoring
is performed (`active_pokemon` always returns slot 0). Affected mechanic: AI move scoring
and targeting in doubles.

### AIIssues.md — earthquake_magnitude_doubles
Earthquake/Magnitude have no partner-based modifier (grounding check, type-penalty) in
the AI. Affected mechanic: AI scoring for spread moves in doubles.

### AIIssues.md — doubles_weakness_policy_moves
Shadow Sneak/Aqua Jet/Ice Shard targeting a WP partner for +12 score not implemented.
Affected mechanic: AI scoring for priority moves aimed at allies in doubles.

### AIIssues.md — fling_doubles_not_handled
Fling doubles scoring around Weakness Policy partners not implemented. Affected mechanic:
AI Fling scoring in doubles.

### AIIssues.md — coaching_singles_never_used
Coaching scores +6 always; should be -20 in singles and partner-stat-based in doubles.
Affected mechanic: AI Coaching scoring (singles and doubles).

### AIIssues.md — role_play_doubles_not_handled
Role Play defaults to +6 STATUS; in doubles it should score based on partner ability.
Affected mechanic: AI Role Play scoring in doubles.

### AIIssues.md — tailwind_trick_room_doubles_partner
Tailwind/Trick Room scoring considers only the AI mon's speed; in doubles the partner's
speed should also be checked. Affected mechanic: AI field-move scoring in doubles.

### AIIssues.md — speed_reduction_move_scoring (doubles addendum)
Icy Wind and Electroweb get an extra +1 in doubles when not the HD move; the entire
speed-reduction special-scoring path is unimplemented. Affected mechanic: AI
speed-reducing move scoring (singles and doubles).

### AIIssues.md — stat_reduction_damage_move_scoring (doubles addendum)
Spread damaging moves with guaranteed stat reductions get an extra +1 in doubles; the
path is unimplemented. Affected mechanic: AI stat-reducing move scoring in doubles.

## Pursuit switch-interception unimplemented (both engines)

R&B keeps vanilla gen-8 Pursuit: if the target switches out, Pursuit executes before the
switch at 80 BP and never misses (RECORDS/Moves.md). Neither the retired Python engine nor
engine/src/ implements the interception — Pursuit is a plain 40 BP move; only the AI scorer
references the mechanic (engine/src/ai_scorer.cpp:1006). Implementing it changes battle
behavior, so it breaks golden-trace parity: schedule post-old-repo-retirement with an
INTENTIONAL_DIVERGENCES entry. The dead-silent LogEvent PURSUIT_INTERCEPT (44) lands with
the mechanic. See RECORDS/StageE.md §2.

---

---

## Dropped at Stage C

The following entries from the old-repo TODO.md were dropped because they are exclusively
about the NN/greedy/search subsystems that were removed and will not be carried forward:

- (No entries were exclusively about nn/greedy/search in the original 116-line TODO.md;
  all entries are engine/sweep/mechanic issues retained above.)
