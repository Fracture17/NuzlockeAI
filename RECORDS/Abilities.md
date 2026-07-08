<Element name="Arena Trap">
## Description
Prevents grounded adjacent opponents from switching out or fleeing.

## Mechanics
- Traps any opposing Pokémon that is **grounded** (i.e., not immune to Ground-type moves via elevation).
- A Pokémon is grounded (trappable) if it lacks any of the following:
  - Flying type
  - Levitate ability (while not suppressed)
  - Air Balloon item
  - Magnet Rise volatile
  - Telekinesis volatile
- A Pokémon is **forced** grounded (overriding the above immunities) by:
  - Gravity field condition
  - Ingrain volatile (gen 4+)
  - Smack Down volatile
  - Iron Ball item
- In doubles, only adjacent opponents are affected.
- Ghost types are **not** immune to trapping in gen 8 (immunity was removed in gen 6).
- Has no effect on damage calculation; purely a trapping/switching mechanic.

## Edge Cases
- If the opponent's type is unknown (e.g. before it acts), `maybeTrapped` is set assuming it could be grounded, using `isGrounded(!knownType)` which negates Flying-type immunity for the check.
- Levitate grants a null return from `isGrounded()` (neither true nor false), which is treated as non-grounded (immune to trapping).
- Pokémon using Fly, Bounce, or other semi-invulnerable moves are still considered to have their types for grounding purposes; trapping evaluates on the type/ability/item, not invulnerability state.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Truant">
## Description
The Pokémon can only act every other turn; on alternating turns it loafs around and cannot move.

## Mechanics
- On the turn Truant activates, the Pokémon is prevented from moving (fails at `onBeforeMove` priority 9). The game message reads "X is loafing around!"
- The truant volatile is toggled each turn:
  - After successfully moving → the truant volatile is added (will loaf next turn).
  - At the start of the next turn → the volatile is removed and the Pokémon cannot act; then a new volatile is added to resume the cycle.
- On switch-in (`onStart`): if the Pokémon has already acted at least once this battle AND it already moved (or won't move) this turn, the truant volatile is immediately set so it loafs on its very next turn.
- Loafing is not a status condition; it is a volatile and cannot be cured by Aromatherapy/Heal Bell.
- Has no effect on damage calculation.

## Edge Cases
- If the Pokémon switches out and back in, `onStart` re-evaluates whether to immediately apply the volatile (based on `activeTurns` and `moveThisTurnResult`), so the cycle can be disrupted by switching.
- Entrainment and Skill Swap can transfer Truant mid-battle, inflicting the loafing cycle on the recipient.
- Skill Swap or Role Play acquiring Truant will trigger `onStart` logic immediately.

## RnB Changes
None documented.

## AI Notes
- The AI treats a player Pokémon that is "loafing around due to Truant" as **incapacitated** for the purpose of scoring Offensive Setup moves (Dragon Dance, Shift Gear, Swords Dance, Howl, Sharpen, Meditate, Hone Claws, Tail Glow, Nasty Plot, Work Up): +3 bonus score.
- Shell Smash's incapacitation check does **not** include Truant loafing (only frozen, asleep, or recharging count).
- Defensive Setup moves (Acid Armor, Barrier, etc.) grant +2 for player incapacitation ~95% of the time, and Truant loafing is included as incapacitation for this check.
</Element>

<Element name="Rough Skin">
## Description
When the holder is hit by a contact move, the attacker takes damage equal to 1/8 of the holder's maximum HP.

## Mechanics
- Triggers on `onDamagingHit` (order priority 1, runs early among post-hit effects).
- Damage is 1/8 of the **holder's base max HP** (`baseMaxhp`), not the attacker's HP and not affected by current HP.
- Only triggers if the move makes contact (checked from the target's perspective: `checkMoveMakesContact(move, source, target, true)`).
- The damage is dealt to the attacking Pokémon (the source).
- Has no interaction with damage calculation; purely a post-hit recoil effect.
- Iron Barbs shares the identical effect.

## Edge Cases
- Does not trigger on non-contact moves (e.g. Earthquake, Surf, most special moves without the contact flag).
- Long Reach on the attacker suppresses contact, so Rough Skin will not activate.
- Protective Pads item on the attacker suppresses contact, so Rough Skin will not activate.
- Can KO the attacker if they have low enough HP remaining.
- Triggers even if the holder faints from the hit (but only if the holder is still on the field when damage resolution runs — in practice this means hits that KO the holder still trigger Rough Skin before fainting).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Grassy Surge">
## Description
On switch-in, sets Grassy Terrain. In RnB, the terrain is permanent (no turn limit).

## Mechanics
- Activates `onStart`: calls `field.setTerrain('grassyterrain')`.
- **RnB change:** Terrain set by a terrain ability is permanent (never expires). In vanilla gen 8, Grassy Terrain lasts 5 turns (8 with Terrain Extender).
- **RnB change:** Terrain is not removed by Defog. Still removed by Steel Roller.

### Grassy Terrain Effects
- **Grass-type move boost:** Multiplies the base power of Grass-type moves by **1.5x** (6144/4096) for grounded attackers. RnB change from vanilla 1.3x (5325/4096).
- **Earthquake/Bulldoze/Magnitude weakening:** Halves (0.5x, 2048/4096) the base power of Earthquake, Bulldoze, and Magnitude when the defender is grounded.
- **End-of-turn healing:** All grounded Pokémon recover 1/16 of their max HP at end of each turn (`onResidual`, order 5, sub-order 2).
- **Nature Power:** Uses Energy Ball (90 BP) in Grassy Terrain.
- **Grass Pelt:** Grassy Terrain boosts the Defense of a Pokémon with Grass Pelt by 1.5x (6144/4096) against physical moves.
- **Grassy Seed:** When Grassy Terrain is active, a Pokémon holding Grassy Seed consumes it and gains +1 Defense.

## Edge Cases
- Only grounded Pokémon receive the end-of-turn heal and the attack/defense modifiers. Flying types, Levitate, Magnet Rise, Air Balloon holders are unaffected by terrain boosts and healing unless forced grounded (Iron Ball, Gravity, Smack Down, Ingrain).
- Terrain Extender has no effect in RnB since terrain from abilities is already permanent.

## RnB Changes
- Terrain is permanent when set by a terrain ability (no expiration).
- Terrain damage boost is 50% (1.5x) instead of vanilla 30% (1.3x).
- Not removed by Defog; still removed by Steel Roller.

## AI Notes
None documented.
</Element>

<Element name="Battle Armor">
## Description
The holder cannot be hit by critical hits.

## Mechanics
- Blocks critical hits via `onCriticalHit: false` (short-circuits the critical hit check).
- In the calculator: `isCritical` is set to false if `defender.hasAbility('Battle Armor', 'Shell Armor')` — same as Shell Armor, identical effect.
- Is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze, allowing critical hits to land.

## Edge Cases
- Even if the move has a guaranteed crit (Frost Breath, Storm Throw, or move with `alwaysCrit`), Battle Armor blocks it — unless suppressed by Mold Breaker.
- Merciless's guaranteed crit on poisoned targets is also blocked by Battle Armor (checked at the same `isCritical` line in the calculator).

## RnB Changes
None documented.

## AI Notes
- The AI will **not** use Focus Energy or Laser Focus if the player's active Pokémon has Battle Armor (crits are impossible, so crit-boosting moves are never selected).

</Element>

<Element name="Sand Rush">
## Description
Doubles the holder's Speed stat in a Sandstorm. The holder is also immune to Sandstorm damage.

## Mechanics
- Speed modifier: 8192/4096 (2x) applied in the speed calculation when weather is `'Sand'`.
- Sandstorm immunity: `onImmunity` returns false for the 'sandstorm' damage type, preventing end-of-turn sandstorm chip damage.
- The speed doubling applies during damage calculation (stat calculation phase in util.ts).

## Edge Cases
- The immunity to sandstorm damage is separate from type-based sandstorm immunity (Rock, Ground, Steel types). Sand Rush provides the immunity explicitly regardless of typing.
- Speed doubling is not applied if the weather is nullified (e.g. by a Utility Umbrella holder being the attacker/defender — but Utility Umbrella only affects weather-based power, not speed).
- The doubling is a speed modifier applied in the speed chain; it stacks multiplicatively with other speed modifiers (Choice Scarf, Tailwind, etc.).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Infiltrator">
## Description
The holder's moves bypass the effects of Reflect, Light Screen, Aurora Veil, Substitute, and Safeguard.

## Mechanics
- Sets `move.infiltrates = true` on every move used by the holder (`onModifyMove`).
- In the calculator (`checkInfiltrator`): nullifies `isReflect`, `isLightScreen`, and `isAuroraVeil` on the opposing side — those screen multipliers are not applied to the damage calculation.
- Substitute bypass (gen 6+): moves with `infiltrates` hit through the opponent's Substitute, dealing damage directly to the Pokémon rather than the substitute.
- Safeguard bypass: moves with `infiltrates` ignore Safeguard's `onSetStatus` and `onTryAddVolatile` protections, allowing status and confusion to be applied through Safeguard.
- Does not grant any accuracy or power bonus — purely a protection bypass.

## Edge Cases
- The screen bypass only removes the screen's damage reduction during the calc; the screen itself remains on the field and still protects against other moves.
- In doubles, `checkInfiltrator` is called for both the attacker's side and the defender's side (both sides checked in gen789.ts lines 79–80).
- Substitute bypass does not trigger Substitute-based effects (the Substitute itself is not hit and not broken).
- Safeguard bypass applies to status-inflicting moves and confusion (Confuse Ray, Sweet Kiss, etc.) but NOT to Yawn (Safeguard's condition explicitly exempts `yawn` at line 15602).

## RnB Changes
None documented.

## AI Notes
- If the player's active Pokémon has Infiltrator, the AI will **never** use Substitute (score -20, effectively blocked). This is because Substitute provides no protection against Infiltrator users.
</Element>

<Element name="Oblivious">
## Description
The holder is immune to infatuation (Attract), Taunt, and Captivate. Also blocks Intimidate's Attack drop.

## Mechanics
- Blocks Attract, Taunt, and Captivate entirely via `onTryHit` (returns null).
- Provides immunity to the 'attract' volatile via `onImmunity`.
- `onUpdate`: if the holder is already afflicted with Attract or Taunt when it gains Oblivious (e.g., via ability change), those volatiles are immediately removed.
- Blocks Intimidate's Attack stat drop via `onTryBoost` (deletes the `atk` boost entry, preventing the drop).
- In the calculator (util.ts): Oblivious is listed alongside Inner Focus, Own Tempo, and Scrappy as abilities that block Intimidate in gen 8.
- Is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze.

## Edge Cases
- Does not prevent status conditions or other volatile effects beyond infatuation and Taunt.
- When Oblivious blocks Intimidate, Competitive and Defiant do **not** trigger (the Attack drop never registers, so there's nothing to react to).
- Captivate targets only Pokémon of the opposite gender; Oblivious blocks it regardless of gender.
- If Oblivious is suppressed by Mold Breaker, the holder can be affected by Attract, Taunt, and Intimidate normally.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Simple">
## Description
All stat stage changes applied to the holder are doubled (both boosts and drops), to a maximum of ±6.

## Mechanics
- In Showdown (`onChangeBoost`): every stat change in a boost object is multiplied by 2 before being applied. Z-Power stat changes are explicitly excluded.
- In the calculator:
  - Self-inflicted stat drops from moves with `dropsStats` (e.g., Overheat -2 SpAtk becomes -4) are doubled.
  - Intimidate Attack drop is doubled: -1 becomes -2 (hardcoded in util.ts Intimidate check).
- Is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze.
- The resulting stage is still capped at ±6.

## Edge Cases
- Z-Power stat boosts (from Z-Moves) are **not** doubled by Simple.
- Both positive and negative changes are doubled: stat drops from moves like Close Combat (-1 Def/-1 SpDef becomes -2/-2) and boosts from Swords Dance (+2 Atk becomes +4).
- Stat drops from Intimidate are doubled to -2 Attack.
- If the holder also has Contrary, Simple's doubling applies first (in Showdown), then Contrary reversal occurs — in practice Showdown's `onChangeBoost` is called once and both effects would need careful ordering (Contrary replaces the double-and-flip logic; in practice, Simple+Contrary doesn't exist on the same Pokémon naturally).
- White Herb activation is calculated against the Simple-doubled drop (e.g., after Overheat with Simple, White Herb restores the -4 drop).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Poison Touch">
## Description
When the holder uses a contact move, there is a 30% chance to poison the target.

## Mechanics
- Triggers on `onSourceDamagingHit` (runs from the attacker's perspective when the holder lands a hit).
- Contact check uses `checkMoveMakesContact(move, target, source)` where source is the Poison Touch holder.
- 30% chance (3/10) to call `target.trySetStatus('psn', source)`.
- Despite not being coded as a secondary effect, **Shield Dust** on the target and **Covert Cloak** held by the target both block Poison Touch's poison application (explicitly checked before the contact/chance roll).
- Has no effect on damage calculation.

## Edge Cases
- Does not trigger on non-contact moves.
- Long Reach on the holder suppresses contact, so Poison Touch will not activate even if the holder uses a normally-contact move.
- Protective Pads on the holder does NOT block Poison Touch (it's an attacker's ability, not a contact-triggered defender ability).
- Targets already with a status condition cannot be poisoned (`trySetStatus` fails if the target already has a status).
- Poison-type and Steel-type targets are immune to poison and cannot be poisoned by this ability.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Filter">
## Description
Reduces damage received from super effective moves by 25%.

## Mechanics
- Applied as a final damage modifier: multiplies incoming damage by 3072/4096 (0.75x) when the type effectiveness is super effective (`typeEffectiveness > 1`).
- Groups with Solid Rock and Prism Armor in the calculator — all three share the same 0.75x reduction for super effective hits.
- Filter is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze. If suppressed, Filter provides no damage reduction.
- Prism Armor shares the same damage reduction but is **not** breakable (it protects itself from suppression).

## Edge Cases
- Does not reduce damage from neutral or resisted hits — only super effective (typeMod > 0 in Showdown / typeEffectiveness > 1 in calculator).
- Does not stack with Solid Rock (they are listed together, and only one is active at a time per Pokémon).
- Friend Guard stacks multiplicatively with Filter (both are finalMods applied separately).
- If the attacker has Mold Breaker/Teravolt/Turboblaze AND the defender has Filter (not Prism Armor), Filter is nullified and the full super effective damage is dealt.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Poison Heal">
## Description
When the holder is poisoned or badly poisoned, end-of-turn damage is replaced with healing of 1/8 max HP.

## Mechanics
- `onDamage` (priority 1): intercepts poison/toxic damage events (`psn` or `tox`). Heals holder by `baseMaxhp / 8` and returns `false` to cancel the damage entirely.
- The holder still has the poison status condition — it just doesn't take damage from it.
- Poison Heal is **not** suppressed by Mold Breaker, Teravolt, or Turboblaze (no `breakable: 1` flag in Showdown; confirmed in the calculator which explicitly exempts Poison Heal from ability nullification even when `attackerIgnoresAbility` is true).
- Toxic's escalating damage is also converted to healing (the damage amount would increase each turn, but Poison Heal replaces it with a flat 1/8 heal regardless).

## Edge Cases
- The holder retains the poison/toxic status and can still be affected by other status-dependent effects (e.g., Synchronize spreading poison, Purify move, Smelling Salts not boosted since it only applies to paralysis).
- If the holder is at full HP, the heal still "happens" but has no effect (heal amount of 0 HP consumed).
- Being poisoned with Poison Heal is effectively beneficial; strategies involving Toxic Orb exploit this deliberately.
- Corrosion can poison Poison/Steel types; if a Steel or Poison type gains Poison Heal and is then poisoned, the healing still applies.

## RnB Changes
- Pokémon with Poison Heal will not take overworld damage from being poisoned (same as Magic Guard).

## AI Notes
None documented.
</Element>

<Element name="Volt Absorb">
## Description
The holder is immune to Electric-type moves and recovers 1/4 of its max HP when targeted by one.

## Mechanics
- In the calculator: Electric-type moves targeting a Volt Absorb holder return the result immediately (no damage), grouping with Lightning Rod and Motor Drive as Electric immunity.
- In Showdown (`onTryHit`): heals the holder by `baseMaxhp / 4`. If the holder is already at full HP, the move shows an immune message instead of healing.
- The move is fully absorbed — no damage, no secondary effects trigger.
- Is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze.

## Edge Cases
- Does not absorb Electric-type moves that target all Pokémon (e.g. if the holder uses a self-Electric move — `target !== source` check in Showdown).
- If suppressed by Mold Breaker, the Electric move deals normal damage with no healing.
- Lightning Rod and Motor Drive are grouped with Volt Absorb for damage immunity in the calculator; however, their additional effects (SpAtk boost for Lightning Rod, Speed boost for Motor Drive) differ from Volt Absorb's healing.
- Volt Absorb does not provide immunity outside of Electric-type moves (e.g., paralysis from Nuzzle? — Nuzzle is Electric-type so the move is fully absorbed including the paralysis secondary).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Tangled Feet">
## Description
While the holder is confused, moves targeting it have their accuracy halved.

## Mechanics
- Hooks into `onModifyAccuracy` at priority -1 (runs late, after most other accuracy modifiers).
- When the holder has the `confusion` volatile, incoming move accuracy is multiplied by 0.5 (chainModify(0.5)).
- Only affects moves where `accuracy` is a number (passes through moves that bypass accuracy checks).
- Is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze.
- Has no effect on damage calculation.

## Edge Cases
- Only active while the holder is confused — if confusion clears, Tangled Feet no longer applies.
- Does not affect moves that always hit (accuracy = true) or those that bypass accuracy checks.
- If suppressed by Mold Breaker, the accuracy halving does not apply.
- Confusion self-damage is unaffected (Tangled Feet only modifies incoming move accuracy, not the confusion self-hit).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Static">
## Description
When the holder is hit by a contact move, there is a 30% chance the attacker becomes paralyzed.

## Mechanics
- Triggers on `onDamagingHit` (no explicit order priority, runs at default).
- Activates only if the move makes contact (`checkMoveMakesContact(move, source, target)`).
- 30% chance (3/10) to call `source.trySetStatus('par', target)` on the attacker.
- `trySetStatus` respects normal paralysis immunities (Electric types are immune to paralysis in gen 6+).
- Has no effect on damage calculation.

## Edge Cases
- Does not trigger on non-contact moves.
- Long Reach and Protective Pads suppress contact, preventing Static from activating.
- If the attacker is already statused, `trySetStatus` will fail (cannot overwrite an existing status).
- Electric-type Pokémon are immune to paralysis and will not be paralyzed even on a successful roll.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Unseen Fist">
## Description
The holder's contact moves bypass protection effects (Protect, Detect, King's Shield, Spiky Shield, etc.).

## Mechanics
- `onModifyMove`: if the move has the `contact` flag, deletes the `protect` flag from the move, allowing it to hit through protection moves.
- In the calculator: `(attacker.hasAbility('Unseen Fist') && move.flags.contact)` is included in the `breaksProtect` condition, enabling contact moves to bypass protection.
- Only affects contact moves — non-contact moves (even if normally blocked by Protect) are not affected.

## Edge Cases
- Bypasses all standard protect-based effects: Protect, Detect, Spiky Shield, Baneful Bunker, King's Shield, Obstruct, Silk Trap, Burning Bulwark, Max Guard.
- Contact moves that hit through Protect still trigger secondary protection effects:
  - Spiky Shield still deals 1/8 HP recoil to the attacker (since the attacker is still "making contact" with Spiky Shield's effect).
  - Baneful Bunker still poisons the attacker.
  - King's Shield still lowers Attack by 2 stages (gen 8 behavior).
  - Obstruct still lowers Defense by 2 stages.
- Long Reach suppresses the contact flag, so Unseen Fist would not bypass protection (no contact flag, no bypass).
- Does not bypass Wonder Guard.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Triage">
## Description
Healing moves used by the holder gain +3 priority.

## Mechanics
- In Showdown: `onModifyPriority` — adds +3 to the priority of any move with the `heal` flag (Recover, Roost, Synthesis, Moonlight, Soft-Boiled, Healing Wish, etc., and drain moves like Drain Punch, Giga Drain, Leech Life).
- In the calculator: grants +1 priority to drain moves specifically (`move.drain`). Note: the calculator has a FIXME comment acknowledging this is incorrect (should check `move.flags.heal` and use +3). The Showdown value (+3 to all heal-flagged moves) is the accurate implementation.
- Priority +3 places healing moves above almost all other moves, allowing the holder to heal before the opponent attacks.

## Edge Cases
- Drain moves (Drain Punch, Giga Drain, Leech Life, etc.) also have the `heal` flag and gain +3 priority, making them very fast.
- Triage does not affect non-healing Recovery/Rest moves that go through different mechanics (e.g., Rest's priority is not boosted since it may not have the `heal` flag — but Showdown indicates it does).
- Moves boosted to +3 by Triage can still be blocked by Dazzling, Queenly Majesty, and Armor Tail (which block priority > 0).
- Triage priority stacks with other priority modifiers if applicable.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Stench">
## Description
Damaging moves used by the holder have a 10% chance to cause the target to flinch.

## Mechanics
- `onModifyMove` (priority -1): adds a secondary effect `{ chance: 10, volatileStatus: 'flinch' }` to all non-Status moves.
- If the move already has a flinch secondary (Iron Head, Bite, Air Slash, etc.), the existing flinch secondary takes precedence and Stench does not add a duplicate.
- Has no effect on damage calculation.

## Edge Cases
- The 10% flinch only applies if the target moves after the holder (the holder must move first for flinch to matter).
- Shield Dust and Covert Cloak block secondary effects, preventing Stench's flinch from activating.
- Stench's flinch stacks with naturally occurring flinch moves — but if the move already has flinch as a secondary, Stench's secondary is not added.
- Inner Focus and Steadfast (on the target) prevent flinching from Stench.
- Overworld effect: Stench also reduces wild Pokémon encounter rate when the holder leads the party (not relevant in battle).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Dazzling">
## Description
Prevents opposing Pokémon from using priority moves that target the holder or its allies.

## Mechanics
- `onFoeTryMove`: when an opponent attempts a move with priority > 0.1 that targets the Dazzling holder or an ally (not a field-wide move or side-targeting move), the move is blocked.
- In the calculator: grouped with Queenly Majesty and Armor Tail — `(move.priority > 0 && defender.hasAbility('Queenly Majesty', 'Dazzling', 'Armor Tail'))` causes the move to return early with no damage.
- Exceptions — the following targeting types are NOT blocked:
  - `foeSide` targets (e.g., Spikes, Stealth Rock)
  - `all` targets with exceptions: Perish Song, Flower Shield, Rototiller are allowed through
- Is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze.

## Edge Cases
- The threshold is `> 0.1` not `> 0`, so exactly 0 priority moves pass through. Moves with priority +1 and higher are blocked.
- Blocked priority moves include: Quick Attack, Extreme Speed, Aqua Jet, Bullet Punch, Fake Out, Sucker Punch (before resolution), Prankster-boosted status moves, etc.
- Sucker Punch specifically: in Showdown, Sucker Punch's condition check happens after priority — if Dazzling blocks it at the priority move stage, it fails entirely (no damage, no wasted turn in terms of Sucker Punch's "hit only if opponent uses a damaging move" mechanic).
- Moves with negative priority (Trick Room, etc.) have priority ≤ 0 and are not blocked.
- If suppressed by Mold Breaker, priority moves can hit the holder and allies normally.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Water Absorb">
## Description
The holder is immune to Water-type moves and recovers 1/4 of its max HP when targeted by one.

## Mechanics
- `onTryHit`: if targeted by a Water-type move from another Pokémon, heals the holder by `baseMaxhp / 4` and returns null (fully blocking the move). If already at full HP, shows an immune message instead.
- In the calculator: Water-type moves targeting a Water Absorb (or Dry Skin/Storm Drain) holder return the result early — no damage calculated.
- Is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze.

## Edge Cases
- Absorbs all Water-type moves, including status Water moves if any exist.
- Does not absorb Water-type moves the holder uses on itself (`target !== source` check).
- If suppressed by Mold Breaker, Water-type moves deal normal damage with no healing.
- Dry Skin and Storm Drain are grouped with Water Absorb in the calculator for immunity.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Unnerve">
## Description
Prevents opposing Pokémon from eating their held berries while the holder is on the field.

## Mechanics
- On switch-in (`onStart`, priority 1): announces Unnerve and sets `unnerved = true`.
- `onFoeTryEatItem`: returns false (blocking berry consumption) when `unnerved` is active.
- `onEnd`: resets `unnerved` to false when the holder switches out or faints.
- In the calculator: grouped with As One (Glastrier) and As One (Spectrier) — all three prevent berry activation on super-effective hits (the `getBerryResistType` check is skipped if the attacker has Unnerve/As One).
- Has no effect on damage calculation beyond the berry suppression.

## Edge Cases
- Prevents ALL berry consumption by opponents: damage-reduction berries (Occa Berry, Shuca Berry, etc.), HP-restoration berries (Sitrus Berry, etc.), status-curing berries (Lum Berry, Chesto Berry, etc.), and stat-boosting berries (Salac Berry, etc.).
- Does not prevent Fling (throwing a berry as a move) or forced berry consumption from Pluck/Bug Bite.
- If Unnerve switches out, the `unnerved` state resets and opponents can eat berries again on their next opportunity.
- Unnerve does not prevent the holder's own berry consumption.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Snow Cloak">
## Description
The holder is immune to Hail damage. In Hail, incoming moves have their accuracy reduced by approximately 20%.

## Mechanics
- `onImmunity`: returns false for 'hail' damage type, preventing Hail chip damage.
- `onModifyAccuracy` (priority -1): in Hail weather, multiplies incoming move accuracy by 3277/4096 (≈0.8x, ~80% of original accuracy).
- The accuracy reduction applies to all moves with a numeric accuracy value; moves that always hit (accuracy = true) are unaffected.
- Is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze.

## Edge Cases
- Only activates in Hail (`hail`) in gen 8 (gen 9 Snow is `snowscape`, but gen 8 only uses `hail`).
- Like all accuracy modifiers, the final accuracy is clamped to valid values; Swift and similar always-hit moves are unaffected.
- If Mold Breaker suppresses Snow Cloak, the accuracy reduction is removed for that move.
- Similar to Sand Veil (same mechanic in Sandstorm).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Multiscale">
## Description
When the holder is at full HP, incoming damage is halved.

## Mechanics
- In Showdown: `onSourceModifyDamage` — if `target.hp >= target.maxhp`, applies `chainModify(0.5)` to halve damage.
- In the calculator: applies a `finalMods.push(2048)` (0.5x) final modifier when:
  - Defender is at full HP (`curHP() === maxHP()`).
  - No Stealth Rocks on the defender's side.
  - No Spikes on the defender's side (unless defender is Flying-type, which would be immune to Spikes).
  - The attacker does not have Parental Bond (Child) (second hit of Parental Bond does not benefit from Multiscale).
- Is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze.
- Shadow Shield (Lunala's equivalent) shares the same mechanic but is **not** breakable.

## Edge Cases
- Any prior damage (even 1 HP of chip) disables Multiscale for that turn.
- Entry hazards: if Stealth Rocks or Spikes are active, the calculator treats Multiscale as inactive since those hazards chip HP before the first attack.
- The second hit of Parental Bond does not receive the Multiscale reduction (explicitly excluded: `!attacker.hasAbility('Parental Bond (Child)')`).
- If suppressed by Mold Breaker, the full damage is dealt even at full HP.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Sap Sipper">
## Description
The holder is immune to Grass-type moves; when hit by one, its Attack rises by 1 stage.

## Mechanics
- `onTryHit` (priority 1): if targeted by a Grass-type move from another Pokémon, boosts Attack by +1 and returns null (fully blocking the move). If already at +6 Attack, shows an immune message instead.
- In the calculator: Grass-type moves targeting a Sap Sipper holder return the result early (no damage), nullifying the move entirely.
- In doubles (`onAllyTryHitSide`): if an ally uses a Grass-type move and it would hit the Sap Sipper holder's side, the Sap Sipper holder gains +1 Attack (absorbing the friendly fire).
- Is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze.

## Edge Cases
- Fully blocks all Grass-type moves, including status moves (Stun Spore, Spore, Powder, Sleep Powder — though these are not Grass-type; but Grass-type moves like Leech Seed are blocked).
- Leech Seed: Sap Sipper blocks Leech Seed (it's a Grass-type move) and grants +1 Attack instead.
- If suppressed by Mold Breaker, Grass-type moves deal normal damage with no boost.
- Nature Power (Energy Ball in Grassy Terrain) is Grass-type and is absorbed by Sap Sipper.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Minus">
## Description
In doubles, if an ally has Plus or Minus, the holder's Special Attack is boosted by 50%.

## Mechanics
- In Showdown: `onModifySpA` (priority 5) — checks all active allies; if any ally has Minus or Plus, applies 1.5x SpA modifier.
- In the calculator: when `attacker.abilityOn` is true and the attacker has Plus or Minus, applies a 6144/4096 (1.5x) attack modifier for special moves. `abilityOn` represents the ally condition being satisfied.
- In singles: has no effect (no allies).

## Edge Cases
- Two Pokémon both with Minus (or both Plus) still activate each other's ability in gen 6+ — the ability now works when an ally has Minus OR Plus (no longer requires one of each).
- In doubles, if the ally with Plus/Minus faints or switches out, the boost is lost.
- The boost applies to the SpA stat, not a base power modifier — it's applied during the attacker modifier phase.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Ice Body">
## Description
The holder recovers 1/16 of its max HP each turn in Hail. Also immune to Hail damage.

## Mechanics
- `onWeather`: when weather is `hail` or `snowscape`, heals `target.baseMaxhp / 16`.
- `onImmunity`: returns false for the 'hail' damage type, preventing end-of-turn Hail chip damage.
- Has no effect on damage calculation.

## Edge Cases
- The immunity to hail damage is separate from Ice-type immunity to Hail (Ice types are also immune). Ice Body provides it explicitly regardless of typing.
- In gen 8 only Hail is relevant (`snowscape` is the gen 9 Snow weather; in gen 8 only `hail` applies).
- If hail is suppressed (e.g., by Utility Umbrella on the target), `onWeather` is not called and no healing occurs.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Steely Spirit">
## Description
Boosts the power of the holder's Steel-type moves by 50%. In doubles, also boosts allies' Steel-type moves.

## Mechanics
- In the calculator: `(attacker.hasAbility('Steely Spirit') && move.hasType('Steel'))` pushes a 6144/4096 (1.5x) base power modifier.
- In Showdown: `onAllyBasePowerPriority: 22`, `onAllyBasePower` — boosts base power of Steel-type moves used by any Pokémon on the holder's side (including itself).
- In doubles, the ally's Steel-type moves are also boosted by the same 1.5x multiplier.

## Edge Cases
- The boost applies to all Steel-type moves regardless of category (physical or special).
- Stacks with other base power modifiers (e.g., STAB, terrain boosts) multiplicatively.
- In doubles, the ally must be actively on the field; switching out removes the boost for that slot.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Teravolt">
## Description
The holder's moves ignore the abilities of opposing Pokémon. Functionally identical to Mold Breaker.

## Mechanics
- Announces on switch-in (`onStart`).
- Sets `move.ignoreAbility = true` on every move via `onModifyMove`.
- In the calculator: grouped with Mold Breaker and Turboblaze as `attackerIgnoresAbility`. When the attacker has any of these, the defender's ability is set to `''` (nullified) for the duration of the damage calculation.
- Suppresses all **breakable** defender abilities (`flags: { breakable: 1 }`), allowing moves to bypass them.

### Abilities that CANNOT be suppressed by Teravolt (in the calculator):
- Full Metal Body
- Neutralizing Gas
- Prism Armor
- Shadow Shield
- Poison Heal (special exemption in the calculator)

## Edge Cases
- Teravolt suppresses the defender's ability for the entire move resolution, including secondary effects (e.g., bypasses Limber to allow paralysis from Thunder Wave).
- Does not affect the attacker's own abilities or any field-wide ability effects already in play.
- In doubles, Teravolt suppresses the ability of the specific target being attacked, not all opponents.
- The suppression is per-move: abilities are suppressed only for the turn the move resolves.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Justified">
## Description
When the holder is hit by a Dark-type move, its Attack stat rises by 1 stage.

## Mechanics
- Triggers on `onDamagingHit` (no explicit order priority).
- Checks `move.type === 'Dark'` and calls `this.boost({ atk: 1 })`.
- The boost applies regardless of whether the hit deals full damage, reduced damage, or even if the holder faints.
- Has no effect on damage calculation.

## Edge Cases
- Triggers on any Dark-type move that hits the holder (not just contact moves).
- Boosts Attack to a max of +6.
- Does not trigger on Dark-type moves that miss or are blocked by immunity/protection.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Unburden">
## Description
When the holder's held item is consumed or removed, its Speed doubles as long as it holds no item.

## Mechanics
- `onAfterUseItem`: after the holder uses (consumes) its own item, adds the `unburden` volatile.
- `onTakeItem`: when the holder's item is removed by any source, adds the `unburden` volatile.
- Unburden volatile `onModifySpe`: while active, if the holder has no item (`!pokemon.item`) and is not ignoring its ability, doubles Speed (2x, chainModify(2)).
- If the holder receives a new item (Trick, Thief, Covet, etc.), the speed doubling stops immediately (condition requires `!pokemon.item`).
- `onEnd`: removes the volatile when the ability ends (e.g., suppressed by Mold Breaker, Neutralizing Gas).
- In the calculator: `(pokemon.hasAbility('Unburden') && pokemon.abilityOn)` applies 8192/4096 (2x) Speed modifier. `abilityOn` represents the item-lost state.

## Edge Cases
- The Speed double persists through switch-out and back in, as long as the Pokémon still holds no item (the volatile is NOT removed on switch-out — only on `onEnd` when the ability is suppressed).
- Re-equipping an item (via Recycle or Pickup finding an item) stops the Speed doubling.
- If the item is knocked off by Knock Off but the holder also has Sticky Hold, Knock Off fails and Unburden does not activate.
- **RnB note:** Items that get consumed or removed in battle will not be restored (no Recycle, no Berry Juice restoration after use), making Unburden a permanent Speed boost once activated.

## RnB Changes
None documented in the changes file. However, note that items are never restored in RnB, meaning once the Speed boost activates it cannot be ended by re-obtaining the item through normal means.

## AI Notes
None documented.
</Element>

<Element name="Libero">
## Description
Before using a move, the holder changes its type to match the move's type, granting STAB on every move.

## Mechanics
- `onPrepareHit`: before the move is executed, if the holder's current type doesn't already match the move type, it changes to that type via `source.setType(type)`.
- In the calculator: when `attacker.hasAbility('Protean', 'Libero')`, the STAB modifier is always applied (`stabMod += 2048` = 1.5x STAB), regardless of original typing.
- **Gen 8 behavior (no once-per-entrance limit):** In gen 8, Libero can change the holder's type on EVERY move used. The gen 9 restriction (only once per switch-in) does NOT apply in gen 8.

### Move exceptions that do NOT trigger the type change:
- Bounced moves (`move.hasBounced`)
- Future move effects (`move.flags['futuremove']`) — Future Sight, Doom Desire
- Snatched moves (`move.sourceEffect === 'snatch'`)
- Moves that call other moves (`move.callsMove`) — Metronome, Sleep Talk, etc.

## Edge Cases
- Changes the holder's actual type — affects its defensive type matchups for that turn (e.g., if it uses a Water-type move, it becomes Water-type and is resistant to Fire/Water while on the field until it uses another move).
- Type change persists until the next move is used or the holder switches out.
- If the holder already matches the move's type (e.g., a Water-type using Surf), no type change occurs and the effect is not announced.
- Moves of type `???` do not trigger the type change.
- Protean is functionally identical to Libero; both grant STAB on every move in gen 8.

## RnB Changes
None documented.

## AI Notes
- Protean is listed as a desirable target ability for Role Play by the AI (the AI will use Role Play to copy Protean from a partner in doubles). Libero is not specifically listed but shares the same mechanic.

</Element>

<Element name="Innards Out">
## Description
When the holder is KO'd by a damaging move, it deals damage to the attacker equal to its remaining HP before fainting.

## Mechanics
- `onDamagingHit` (order priority 1): if the holder's HP drops to 0 (`!target.hp`), deals damage to the source equal to `target.getUndynamaxedHP(damage)`.
- `damage` in this context is the actual HP the holder lost from the killing hit (not overkill amount — capped by remaining HP).
- For non-smart-target spread moves in doubles: `damage += Number(move.totalDamage)` to account for the full spread damage.
- The counter-damage is dealt to the attacker with the holder as the "source" of the damage.
- Has no effect on damage calculation for the incoming hit.

## Edge Cases
- Only activates from damaging moves — does NOT trigger from indirect damage (poison, burn, entry hazards, weather) or passive effects.
- If the attacker is also at low HP, Innards Out can KO the attacker simultaneously.
- Multi-hit moves: each hit is processed separately; Innards Out triggers only when the fatal hit connects (when HP reaches 0), so the damage dealt is based on the HP remaining before the final hit.
- Does not trigger if the holder faints from recoil (recoil is not `onDamagingHit`).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Torrent">
## Description
When the holder's HP drops to 1/3 or less, Water-type moves deal 50% more damage.

## Mechanics
- In Showdown: `onModifyAtk` and `onModifySpA` (priority 5) — when HP ≤ 1/3 max HP, applies 1.5x to the relevant attacking stat for Water-type moves.
- In the calculator: grouped with Overgrow and Blaze — `(attacker.hasAbility('Torrent') && move.hasType('Water'))` with the `attacker.curHP() <= attacker.maxHP() / 3` condition pushes 6144/4096 (1.5x) attack modifier.
- Applies to both physical (Waterfall, Crabhammer) and special (Surf, Hydro Pump) Water-type moves.

## Edge Cases
- The 1/3 HP threshold is checked against `maxhp` — exactly 1/3 or below triggers the boost.
- Stacks multiplicatively with STAB, weather rain boost, and other modifiers.
- Does not affect type or move power — only the attacking stat multiplier.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Natural Cure">
## Description
When the holder switches out, its status condition is cured.

## Mechanics
- `onSwitchOut`: if the holder has a status condition, clears it via `pokemon.clearStatus()`.
- Cures all major statuses: burn, freeze, paralysis, poison, toxic, and sleep.
- Has no effect on damage calculation.

## Edge Cases
- Only triggers on switch-out — does not cure status while the holder remains on the field.
- Triggers on all switch-out scenarios: voluntary switch, forced switch (Roar, Whirlwind, Dragon Tail, Circle Throw), U-turn/Volt Switch/Flip Turn self-switch, and Baton Pass.
- Does NOT cure volatile status conditions (confusion, attraction, flinch, etc.) — only persistent status conditions.
- If the holder is KO'd (fainting is not a switch), Natural Cure does NOT trigger.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Inner Focus">
## Description
Prevents the holder from flinching. Also blocks Intimidate's Attack drop in gen 8.

## Mechanics
- `onTryAddVolatile`: returns null if the status being applied is `flinch`, completely preventing flinching.
- `onTryBoost` (gen 8): if Intimidate would lower the holder's Attack, deletes the `atk` entry from the boost, preventing the drop.
- In the calculator (util.ts): listed with Own Tempo, Oblivious, and Scrappy as abilities that block Intimidate in gen 8+.
- Is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze.

## Edge Cases
- Completely immune to all flinch sources (King's Rock/Razor Fang proc, high-flinch-chance moves like Iron Head, etc.).
- The Intimidate block prevents Competitive and Defiant from triggering (the drop never registers).
- If suppressed by Mold Breaker, the holder can be flinched and Intimidated normally.
- When Intimidate is blocked, the game displays a failure message.

## RnB Changes
None documented.

## AI Notes
- The AI does **not** use Fake Out when targeting a Pokémon with Inner Focus (the +9 Fake Out bonus is only applied if the target does NOT have Shield Dust or Inner Focus). If the target has Inner Focus, Fake Out receives no scoring bonus and will generally not be selected.

</Element>

<Element name="As One (Glastrier)">
## Description
Combines Unnerve and Chilling Neigh. Prevents opposing Pokémon from eating berries, and raises the holder's Attack by 1 stage when it KOs an opponent with a move.

## Mechanics
- **Unnerve component:** On switch-in, announces "As One" then "Unnerve". While active (`unnerved` state), opposing Pokémon cannot eat their held berries (`onFoeTryEatItem` returns false).
- **Chilling Neigh component:** `onSourceAfterFaint` — when the holder's move KOs one or more Pokémon, boosts Attack by `length` stages (1 per KO, e.g. 2 in a double KO). The boost is attributed to the Chilling Neigh effect.
- In the calculator: grouped with Unnerve and As One (Spectrier) for suppressing berry activation on super-effective hits.
- Cannot be copied, suppressed, transferred, or reversed: `failroleplay`, `noreceiver`, `noentrain`, `notrace`, `failskillswap`, `cantsuppress`.
- `onEnd` resets the `unnerved` state when the holder leaves the field.

## Edge Cases
- The Unnerve component prevents ALL berry consumption by the opponent (both automatic berries like Sitrus Berry and reactively-eaten berries like Lum Berry).
- The Chilling Neigh boost stacks with existing Attack boosts (capped at +6).
- If the holder is KO'd by recoil after KOing the opponent, Chilling Neigh still triggers (KO happens before recoil faint).
- `length` in `onSourceAfterFaint` refers to the number of Pokémon KO'd in that event, allowing multi-KO scenarios (e.g., via Parental Bond or spread moves in doubles) to give multiple boosts.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Liquid Ooze">
## Description
When the holder is drained by a move (drain moves, Leech Seed, Strength Sap), the attacker takes damage equal to the amount that would have been healed instead of healing.

## Mechanics
- `onSourceTryHeal`: fires when the source (attacker/drainer) is about to be healed from the holder's HP.
- Checks if the effect is one of: `drain` (all drain moves), `leechseed`, or `strengthsap`.
- If matched: deals `damage` to the drainer (same amount as the intended heal) and returns 0 to cancel the healing.
- Has no effect on damage calculation; only affects the post-move healing step.

## Edge Cases
- Affects all drain moves: Giga Drain, Leech Life, Drain Punch, Absorb, Mega Drain, Horn Leech, Parabolic Charge, Draining Kiss, Dream Eater, Oblivion Wing, etc.
- Leech Seed: each turn the draining tick would deal damage to the seeded holder's target instead of healing.
- Strength Sap: Strength Sap heals based on the target's Attack stat; with Liquid Ooze, it instead damages the user by that amount.
- Does not affect HP restoration from items, abilities, or other sources — only the specific drain effects listed.
- Can KO the attacker if their HP is low enough when the drain damage is applied.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Disguise">
## Description
Mimikyu's ability. The first damaging move directed at Mimikyu is blocked entirely; the Disguise then breaks, changing Mimikyu to Busted form. In RnB, no damage is dealt when the Disguise breaks.

## Mechanics
- `onDamage` (priority 1): if the target is Mimikyu (or Mimikyu-Totem) and the damage source is a move, returns 0 (no damage) and sets `busted = true`.
- `onUpdate`: after being hit and `busted = true`, changes forme to Mimikyu-Busted. In vanilla gen 8, also deals 1/8 max HP damage. In RnB, **no damage is taken** when the Disguise breaks.
- `onCriticalHit`: returns false while Mimikyu is undisguised — the hit cannot be a critical hit.
- `onEffectiveness`: returns 0 while Mimikyu is undisguised — hides the true type effectiveness (appears neutral regardless of actual matchup).
- Is a **breakable** ability, but also has flags preventing its transfer: `failroleplay`, `noreceiver`, `noentrain`, `notrace`, `failskillswap`, `cantsuppress`, `notransform`.

## Edge Cases
- The Disguise blocks exactly ONE damaging hit, then breaks. Multi-hit moves only have their first hit blocked (subsequent hits deal normal damage).
- While Disguised, Mimikyu shows neutral type effectiveness to the attacker, masking its true weaknesses.
- Status moves and non-damaging effects still apply through the Disguise (Disguise only blocks `effectType === 'Move'` damage).
- Indirect damage (weather, poison, burn, recoil) is NOT blocked by Disguise.
- The ability cannot be transferred or copied via Skill Swap, Entrainment, Role Play, Trace, Receiver, or Transform.
- Gen 8 adds `pokemon.formeRegression = true` on busting, which may affect how forme changes interact.
- In vanilla gen 8: deals 1/8 max HP damage when Disguise breaks. In RnB: no damage dealt.

## RnB Changes
- When Disguise breaks, Mimikyu takes **no damage** (vanilla gen 8 deals 1/8 max HP).

## AI Notes
None documented.
</Element>

<Element name="Regenerator">
## Description
When the holder switches out of battle, it recovers 1/3 of its maximum HP.

## Mechanics
- `onSwitchOut`: heals `pokemon.baseMaxhp / 3` when the holder is withdrawn.
- Healing occurs before the next Pokémon switches in.
- Has no effect on damage calculation.

## Edge Cases
- Does not trigger if the holder is forced out via fainting (only voluntary or forced switches while alive).
- Triggers on all switch-out scenarios: voluntary switch, U-turn/Volt Switch/Flip Turn self-switch, Baton Pass, and forced out by Roar, Whirlwind, Dragon Tail, Circle Throw.
- If the holder is at full HP when switching out, the heal still "happens" but has no visible effect.
- The heal is applied to the Pokémon's HP before it exits, so it benefits from any HP it had remaining.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Hydration">
## Description
At the end of each turn, cures the holder's status condition if rain is active.

## Mechanics
- `onResidual` (order 5, sub-order 3): if the holder has any status (`pokemon.status` is truthy) and the effective weather is `raindance` or `primordialsea`, calls `pokemon.cureStatus()`.
- Cures all major status conditions: burn, freeze, paralysis, poison, toxic, and sleep.
- Requires active rain — does not activate in other weather or no weather.

## Edge Cases
- With permanent rain (from Drizzle in RnB), Hydration cures status every single end-of-turn as long as rain persists.
- Rest + Hydration in rain: the Pokémon uses Rest (goes to sleep, restores HP), then Hydration immediately cures the sleep at end of turn. This makes Rest a reliable full-heal in permanent rain.
- Utility Umbrella on the holder suppresses weather-based effects on the holder specifically; Hydration may still activate since it checks `effectiveWeather()`, which for the holder ignoring umbrella... actually the `effectiveWeather()` call is on the Pokémon itself, not the move, so Utility Umbrella would not block Hydration (Umbrella only suppresses weather effects for moves, not passive abilities).

## RnB Changes
None documented.

## AI Notes
- The AI uses Rest with a +8 score (instead of the normal +7 for "should recover" situations) if it has Hydration AND it is raining, because Hydration will immediately cure the sleep.

</Element>

<Element name="Cute Charm">
## Description
When the holder is hit by a contact move, there is a 30% chance the attacker becomes infatuated with the holder.

## Mechanics
- Triggers on `onDamagingHit` (no explicit order priority).
- Activates only if the move makes contact (`checkMoveMakesContact(move, source, target)`).
- 30% chance (3/10) to call `source.addVolatile('attract', this.effectState.target)`, infatuating the attacker toward the Cute Charm holder.
- Has no effect on damage calculation.

## Edge Cases
- **RnB change:** Infatuation in RnB is not limited by gender — Cute Charm can infatuate any Pokémon regardless of gender matchup (unlike vanilla gen 8 where Attract/Cute Charm only works between Pokémon of opposite genders).
- Does not trigger on non-contact moves.
- Long Reach and Protective Pads suppress contact, preventing Cute Charm from activating.
- Oblivious, Own Tempo, and Aroma Veil holders are immune to infatuation and cannot be infatuated by Cute Charm.

## RnB Changes
- Infatuation (Attract) is not gender-limited in RnB, so Cute Charm can trigger against any Pokémon regardless of gender.

## AI Notes
None documented.
</Element>

<Element name="Competitive">
## Description
When a foe lowers any of the holder's stats, the holder's Special Attack rises by 2 stages.

## Mechanics
- `onAfterEachBoost`: after each individual stat boost application from a non-ally source, if any stat in the boost was lowered (negative value), raises the holder's Special Attack by +2.
- Only triggers when the source of the stat drop is a different Pokémon that is not an ally.
- In the calculator (util.ts): after Intimidate applies its -1 Attack drop, if the target has Competitive, SpA is immediately raised by +2.
- The +2 SpA boost is applied per stat-drop event — if multiple stats are lowered simultaneously in one event, Competitive still only triggers once (+2 total, not +2 per stat).

## Edge Cases
- Does **not** trigger from self-inflicted stat drops (e.g., Close Combat's Defense/SpDef drop, Overheat's SpAtk drop).
- Does **not** trigger from ally-inflicted stat drops (in doubles, e.g., a partner using Icy Wind).
- In gen 8, Sticky Web placed via Court Change is treated as a self-lowering effect and does **not** trigger Competitive.
- Mist and Clear Amulet prevent the stat drop from reaching the holder, so Competitive won't trigger.
- If Intimidate lowers Attack by 1 and the holder has Competitive, the +2 SpA applies even though the holder may not use special attacks.
- The boost caps at +6 Special Attack.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Sticky Hold">
## Description
Prevents the holder's item from being removed by external sources.

## Mechanics
- `onTakeItem`: returns false (blocks item removal) when:
  - The item-taking source is a different Pokémon (Trick, Covet, Knock Off, Thief, etc.) OR the move is specifically Knock Off.
  - AND the holder still has HP (not fainted).
  - AND the holder's current item is NOT Sticky Barb.
- Is a **breakable** ability: Mold Breaker, Teravolt, and Turboblaze suppress it, allowing item removal to proceed normally.

## Edge Cases
- **Sticky Barb is explicitly exempt**: even with Sticky Hold, Sticky Barb can still be removed or transferred (e.g., via contact).
- Fainted Pokémon lose Sticky Hold protection (HP = 0 check returns before the block).
- Magician and Pickpocket are blocked by Sticky Hold.
- Incinerate and Corrosive Gas bypass item removal differently (they consume or remove items without going through `onTakeItem`) — behavior may differ; needs testing.
- If Sticky Hold is suppressed by Mold Breaker, Knock Off removes the item and deals the boosted 1.5x damage.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Misty Surge">
## Description
On switch-in, sets Misty Terrain. In RnB, the terrain is permanent (no turn limit).

## Mechanics
- Activates `onStart`: calls `field.setTerrain('mistyterrain')`.
- **RnB change:** Terrain set by a terrain ability is permanent (never expires). In vanilla gen 8, Misty Terrain lasts 5 turns (8 with Terrain Extender).
- **RnB change:** Terrain is not removed by Defog. Still removed by Steel Roller.

### Misty Terrain Effects
- **Status prevention:** Blocks all status conditions from being applied to grounded Pokémon from move-based sources (`onSetStatus` returns false if grounded and effect has `.status` or is Yawn).
- **Confusion prevention:** Blocks confusion from being applied to grounded Pokémon (`onTryAddVolatile` returns null for `confusion`).
- **Dragon-type weakening:** Halves (0.5x, 2048/4096) Dragon-type move base power when the defender is grounded.
- **Nature Power:** Uses Moonblast (95 BP) in Misty Terrain.
- **Misty Seed:** When Misty Terrain is active, a Pokémon holding Misty Seed consumes it and gains +1 Special Defense.

## Edge Cases
- Misty Terrain does NOT boost Fairy-type moves (unlike Electric/Grass/Psychic Terrains). The RnB 50% terrain boost only applies to Electric, Grass, and Psychic types.
- Only grounded Pokémon benefit from the status and confusion protection. Non-grounded Pokémon (Flying type, Levitate, Air Balloon, Magnet Rise, Telekinesis) are unaffected.
- Pokémon that are semi-invulnerable (using Dig, Fly, etc.) are also not protected.
- Terrain Extender has no effect in RnB since terrain from abilities is already permanent.
- Existing status conditions are NOT cured by Misty Terrain — it only prevents new ones.

## RnB Changes
- Terrain is permanent when set by a terrain ability (no expiration).
- Not removed by Defog; still removed by Steel Roller.
- (No damage boost change; Misty Terrain does not boost any move type.)

## AI Notes
None documented.
</Element>

<Element name="Pastel Veil">
## Description
On switch-in, cures poison and toxic from all Pokémon on the holder's side. Prevents the holder and its allies from being poisoned or badly poisoned.

## Mechanics
- `onStart`: when the holder switches in, iterates through all allies (including self) and cures any with `psn` or `tox` status.
- `onAnySwitchIn`: re-runs the `onStart` check whenever any Pokémon switches in on the holder's side, potentially curing a newly switched-in ally who was poisoned.
- `onUpdate`: if the holder itself gains poison/toxic status while active (e.g., from Toxic Spikes on entry before ability activates), immediately cures itself.
- `onSetStatus`: blocks poison and toxic from being applied to the holder entirely (returns false). Adds an `-immune` message if it came from a move.
- `onAllySetStatus`: blocks poison and toxic from being applied to allies (returns false). Adds a `-block` message if it came from a move.
- Is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze.

## Edge Cases
- Cures existing poison on switch-in but does not remove Toxic Spikes from the field (the cure is applied after entry, not the hazard itself).
- If Pastel Veil is suppressed by Mold Breaker, both the immunity and the switch-in cure are bypassed.
- The ally immunity (`onAllySetStatus`) blocks all sources of poison/toxic, not just move-based poison (e.g., also blocks poison from Poison Point, Poison Touch, Effect Spore).
- In doubles, the ally protection is active for the partner Pokémon.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Sweet Veil">
## Description
Prevents the holder and its allies from falling asleep, and blocks Yawn from being applied to the holder's side.

## Mechanics
- `onAllySetStatus`: if the status being set is sleep (`slp`), returns null to block it. Applies to all Pokémon on the holder's side (including the holder itself).
- `onAllyTryAddVolatile`: if the volatile being applied is Yawn, returns null to block it. Applies to all Pokémon on the holder's side.
- In doubles, Sweet Veil protects both the holder and its active partner.
- Is a **breakable** ability: can be suppressed by Mold Breaker, Teravolt, and Turboblaze (allowing sleep to be applied despite Sweet Veil).
- Has no effect on damage calculation.

## Edge Cases
- Does not cure existing sleep — only prevents new sleep from being inflicted. If a Pokémon is already asleep when Sweet Veil switches in, it remains asleep.
- Blocks Rest as well (since Rest puts the user to sleep via `setStatus('slp')`), preventing the holder or its ally from using Rest while Sweet Veil is active.
- If suppressed by Mold Breaker, sleep can be applied normally.
- In doubles, the ally is also protected from sleep and Yawn regardless of their own ability.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Soul-Heart">
## Description
When any Pokémon faints (ally or opponent), Soul-Heart raises the holder's Special Attack by 1 stage.

## Mechanics
- Triggers via `onAnyFaint` with priority 1, meaning it fires before lower-priority faint effects.
- The boost applies to the holder regardless of which side's Pokémon fainted.
- Works every time any Pokémon on the field faints — can stack across multiple faints in a battle.
- The boost is a standard stat stage change and can be negated by Contrary (would lower Sp. Atk instead) or blocked by Clear Body/White Smoke/Full Metal Body/Sword of Ruin etc.

## Edge Cases
- Fires when an ally faints as well as when an opponent faints.
- Priority 1 means if multiple faint-triggered effects exist, Soul-Heart resolves before standard priority-0 effects.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Fluffy">
## Description
Halves damage taken from contact moves, but doubles damage taken from Fire-type moves.

## Mechanics
- Contact move damage is multiplied by 0.5x (`finalMods.push(2048)`).
- Fire-type move damage is multiplied by 2x (`finalMods.push(8192)`).
- A Fire-type contact move triggers both: 0.5x × 2x = 1x (neutral damage).
- The contact halving is bypassed if the attacker has Long Reach or is holding Protective Pads — only the contact check is bypassed, not the Fire doubling.
- Has `breakable` flag: suppressed by Mold Breaker, Teravolt, and Turboblaze.

## Edge Cases
- Long Reach or Protective Pads only nullify the contact damage reduction; a Fire-type move from a Long Reach user still deals 2x damage.
- Fire-type contact moves (e.g., Fire Punch) deal neutral damage overall (the 0.5x and 2x cancel out). If attacker has Long Reach, Fire Punch would instead deal 2x (contact halving skipped, Fire doubling still applies).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Emergency Exit">
## Description
When the holder's HP drops to 50% or below (crossing the threshold from above), it immediately switches out. Identical to Wimp Out in function.

## Mechanics
- Triggers via the `EmergencyExit` event, which fires after residual damage effects when HP crosses from above 50% to at or below 50% in a turn.
- Also checked after a switch-in action (`runSwitch`) to catch cases where the Pokémon arrives with HP already at or below 50%.
- Sets `switchFlag` on the holder so it is forced to switch out; clears switch flags from all other active Pokémon first so only this Pokémon switches.
- Does not trigger if the side cannot switch (no remaining party members) or if the Pokémon already has a switch/force-switch flag pending.
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Does not trigger if HP is already at or below 50% when switching in (from a prior turn's damage); it only fires when the HP crosses the 50% boundary during the current turn.
- In doubles, if the holder is already marked for switching (e.g., from a previous effect), the ability does not additionally re-trigger.
- Trigger check uses `getUndynamaxedHP()` to compare against the non-Dynamax max HP.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Magic Bounce">
## Description
Reflects status moves and other moves with the `reflectable` flag back at the attacker instead of being affected by them.

## Mechanics
- Triggers via `onTryHit` (priority 1) and `onAllyTryHitSide` in doubles.
- A move is reflected if: it has the `reflectable` flag, it hasn't already been bounced (`hasBounced` is false), the target is not the same as the source (can't reflect your own move), and the target is not semi-invulnerable (in Fly/Dig/etc.).
- When reflecting: creates a new instance of the move with `hasBounced = true` (prevents infinite loops) and `pranksterBoosted = false`, then uses it back against the original user.
- Has `breakable` flag: suppressed by Mold Breaker, Teravolt, Turboblaze. This means moves that should be reflected instead hit normally when the attacker has Mold Breaker.
- Common reflectable moves include status moves like Stealth Rock, Spikes, Leech Seed, Thunder Wave, Encore, Taunt, etc. Moves without the `reflectable` flag (e.g., most damaging moves, Yawn) are not reflected.

## Edge Cases
- A bounced move cannot be bounced again (`hasBounced = true`), so two Magic Bounce users do not create an infinite loop.
- `pranksterBoosted` is cleared on the reflected move, so a Prankster-boosted status move that bounces loses the priority boost on the return.
- In doubles, `onAllyTryHitSide` also fires if a reflectable move targets the user's ally — the bounce originates from the Magic Bounce holder's position.
- Target must not be semi-invulnerable for the reflection to occur; if the holder is mid-Fly when a status move is used, it won't reflect.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Sand Force">
## Description
In sandstorm, boosts the power of Rock-, Ground-, and Steel-type moves by 1.3x. Also grants immunity to sandstorm damage.

## Mechanics
- `onBasePower` (priority 21): multiplies base power by 5325/4096 (≈ 1.3x) when weather is sandstorm and the move is Rock, Ground, or Steel type.
- `onImmunity` for type 'sandstorm': returns false, preventing the holder from taking end-of-turn sandstorm damage.
- No `breakable` flag — not suppressed by Mold Breaker.
- Applied as a base power modifier (`bpMods.push(5325)` in the calculator).

## Edge Cases
- The boost only applies during sandstorm weather; does not apply under other weather conditions.
- The sandstorm immunity is unconditional — the holder never takes sandstorm chip damage regardless of type.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Punk Rock">
## Description
Boosts the power of sound-based moves by 1.3x when the holder uses them, and halves the damage the holder takes from sound-based moves.

## Mechanics
- `onBasePower` (priority 7): when the holder uses a move with the `sound` flag, multiplies base power by 5325/4096 (≈ 1.3x).
- `onSourceModifyDamage`: when the holder is targeted by a move with the `sound` flag, multiplies incoming damage by 0.5x.
- In the calculator: offensive Punk Rock applies `bpMods.push(5325)`; defensive applies `finalMods.push(2048)`.
- Has `breakable` flag: suppressed by Mold Breaker, Teravolt, Turboblaze (the damage reduction can be bypassed).

## Edge Cases
- Both effects can apply simultaneously in a scenario where two Punk Rock users face each other — the attacker gets 1.3x offense and the defender gets 0.5x defense.
- Soundproof vs Punk Rock: Soundproof blocks the sound move entirely (immune), so the 0.5x Punk Rock reduction never comes into play.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Scrappy">
## Description
Allows Normal- and Fighting-type moves to hit Ghost-type Pokémon. Also prevents Intimidate from lowering the holder's Attack.

## Mechanics
- `onModifyMove` (priority -5): sets `move.ignoreImmunity['Fighting'] = true` and `move.ignoreImmunity['Normal'] = true`, overriding the Ghost-type immunity to those move types.
- `onTryBoost`: blocks Intimidate's Attack drop by deleting `boost.atk` when the source effect is Intimidate.
- In the calculator: `isGhostRevealed = attacker.hasAbility('Scrappy') || field.defenderSide.isForesight` — passed to `getMoveEffectiveness` so Normal/Fighting moves calculate correctly against Ghost types. Also applied for Collision Course and Electro Drift effectiveness.
- No `breakable` flag — not suppressed by Mold Breaker.
- In the Intimidate util logic (gen 8+): Scrappy is included alongside Inner Focus, Own Tempo, Oblivious as abilities that block Intimidate.

## Edge Cases
- Only Normal and Fighting moves ignore Ghost immunity; other typings that would normally be immune to Ghost are unaffected.
- The Ghost immunity bypass works even if the Ghost type is on a Pokémon with a secondary type.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Levitate">
## Description
Grants immunity to Ground-type moves and makes the holder airborne (ungrounded), preventing damage from Spikes/Toxic Spikes/Sticky Web on entry and granting terrain immunity.

## Mechanics
- In the calculator: Ground-type moves return early (0 damage) when `defender.hasAbility('Levitate') && !field.isGravity && !move.named('Thousand Arrows') && !defender.hasItem('Iron Ball')`.
- In `isGrounded()` (util.ts): `!pokemon.hasAbility('Levitate')` is required to be grounded — Levitate keeps the holder ungrounded (alongside Flying type and Air Balloon).
- Has `breakable` flag: suppressed by Mold Breaker, Teravolt, Turboblaze — a Mold Breaker Ground move hits the Levitate holder normally.
- Airborneness is implemented in the sim's `Pokemon#isGrounded` function; the ability entry itself has no `onTryHit` — the ground immunity is a side effect of the Pokémon being ungrounded.

## Edge Cases
- Gravity negates Levitate — the holder becomes grounded and can be hit by Ground moves.
- Iron Ball negates Levitate — the holder is grounded despite the ability.
- Thousand Arrows bypasses Levitate; it always hits even airborne targets.
- Ingrain and Smack Down (which ground the target) override Levitate.
- Ungrounded Pokémon do not receive terrain boosts (Electric/Grassy/Psychic Terrain) even if they have a relevant move or ability.
- Spikes, Toxic Spikes, and Sticky Web do not affect ungrounded Pokémon on entry.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Weak Armor">
## Description
When the holder is hit by a physical move, its Defense drops by 1 stage and its Speed rises by 2 stages.

## Mechanics
- `onDamagingHit`: triggers only on physical category moves that deal damage.
- Applies `-1 Defense` and `+2 Speed` to the holder via `this.boost({ def: -1, spe: 2 })`.
- No `breakable` flag — not suppressed by Mold Breaker.
- In the calculator (util.ts), the Defense drop is skipped in damage calculations if the attacker has Unaware (since Unaware ignores defensive stat changes), but the Speed boost is still applied regardless.
- White Herb can negate the Defense drop (consumes the herb); the Speed boost still applies.

## Edge Cases
- Only triggers on physical damaging moves; special moves and status moves do not activate Weak Armor.
- The Speed and Defense changes happen even if the holder faints from the hit (though they won't be usable after fainting).
- Contrary would reverse the stat changes (Defense +1, Speed -2) instead.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Galvanize">
## Description
Converts the holder's Normal-type moves to Electric-type and boosts their power by 1.2x.

## Mechanics
- `onModifyType` (priority -1): changes move type from Normal to Electric and sets `move.typeChangerBoosted = this.effect`.
- `onBasePower` (priority 23): applies 4915/4096 (≈ 1.2x) boost only to moves that were type-changed by this ability (i.e., `move.typeChangerBoosted === this.effect`).
- Excluded moves (not converted): Revelation Dance, Judgment, Nature Power, Techno Blast, Multi Attack, Natural Gift, Weather Ball, Terrain Pulse. Z-moves (non-status) and Tera Blast (when terastallized) are also excluded.
- No `breakable` flag — not suppressed by Mold Breaker.
- The type change allows converted Normal moves to gain STAB if the holder is Electric-type, resulting in an effective multiplier from Normal-type STAB to Electric-type STAB.

## Edge Cases
- The 1.2x boost only applies to converted moves. If a move is excluded from conversion (e.g., Judgment), it receives no boost and stays Normal-type.
- Normalize overrides Galvanize if the holder somehow had both (Normalize converts all types to Normal); in the calculator they are mutually exclusive branches.
- Galvanize-boosted moves interact with Electric immunities and type chart normally after the conversion.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Merciless">
## Description
Moves used by the holder always result in critical hits when the target is poisoned or badly poisoned.

## Mechanics
- `onModifyCritRatio`: returns 5 (guaranteed crit) when the target has `psn` or `tox` status.
- In the calculator: `isCritical` is set true when `attacker.hasAbility('Merciless') && defender.hasStatus('psn', 'tox')` AND `move.timesUsed === 1`.
- Does not bypass Battle Armor or Shell Armor — a poisoned target with Shell Armor or Battle Armor will not take critical hit damage from Merciless (Showdown: crit ratio returns 5 but those abilities block crits; calculator explicitly notes this: "Merciless does not ignore Shell Armor").
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Only requires the target to have any poison status (regular or toxic); the severity of bad poison stacking does not matter.
- The `timesUsed === 1` check in the calculator means multi-hit moves only treat the first hit as a crit for damage calculation display purposes, though in actual gameplay each hit would crit.

## RnB Changes
None documented.

## AI Notes
When evaluating poisoning moves: if the AI has Merciless and the player Pokémon can be poisoned and is above 20% HP with no damaging moves, the poisoning move score receives an additional +2 bonus (applied during the ~38% chance sub-check, not guaranteed each turn).
</Element>

<Element name="Contrary">
## Description
Inverts all stat stage changes applied to the holder — boosts become drops and drops become boosts.

## Mechanics
- `onChangeBoost`: iterates over all stat changes in the boost object and multiplies each by -1, reversing direction. Exception: Z-Power effects (`effect.id === 'zpower'`) are not reversed.
- Has `breakable` flag: suppressed by Mold Breaker, Teravolt, Turboblaze.
- Intimidate interaction: if the holder has Contrary, Intimidate's −1 Attack becomes a +1 Attack boost (util.ts line 214 handles this case).
- Moves with `dropsStats` (e.g., Overheat, Leaf Storm): in the calculator (util.ts), Contrary reverses these so the attacker gains `+move.dropsStats` in the relevant stat instead of losing it.

## Edge Cases
- Contrary reverses ALL stat changes, including those from allies (e.g., Coaching would drop the holder's stats), terrain or weather effects that change stats, etc.
- A Contrary holder using Shell Smash loses the Attack/SpAtk/Speed gains but gains Defense/SpDef instead of losing them.
- Z-Move power boost stat effects are explicitly excluded from reversal.

## RnB Changes
None documented.

## AI Notes
- When scoring damaging speed-reduction moves (Icy Wind, Electroweb, etc.) or stat-drop moves (Trop Kick, Skitter Smack, etc.): if the target has Contrary (or Clear Body/White Smoke), the score bonus is reduced by 1 point (e.g., +5 instead of +6 for being slower or having the corresponding move type).
- Coaching: never used by the AI if the partner has Contrary (the partner would receive stat drops instead of boosts).
- Attacking moves that lower the user's stats (Overheat, Leaf Storm, Superpower) are treated as setup moves when the AI Pokémon has Contrary, provided the move is not the highest damaging option and does not KO the opponent. These are scored equivalently to Nasty Plot/Bulk Up but without the normal setup-safety checks — they can be used even against Unaware targets or when threatened with a KO.
</Element>

<Element name="Prism Armor">
## Description
Reduces damage received from super-effective moves by 25%. Unlike Filter and Solid Rock, this ability cannot be suppressed by Mold Breaker.

## Mechanics
- `onSourceModifyDamage`: if `typeMod > 0` (super-effective), multiplies incoming damage by 0.75x.
- No `breakable` flag — Mold Breaker, Teravolt, and Turboblaze cannot suppress it.
- In the calculator: `finalMods.push(3072)` (3072/4096 = 0.75x) when `defender.hasAbility('Solid Rock', 'Filter', 'Prism Armor') && typeEffectiveness > 1`.
- Also appears in `defenderIgnoresAbility` list in the calculator alongside Full Metal Body, Neutralizing Gas, and Shadow Shield — attackers with Mold Breaker cannot suppress the defender's Prism Armor.

## Edge Cases
- Functionally identical to Filter and Solid Rock (0.75x super-effective reduction), but Prism Armor is not bypassed by Mold Breaker while the others are.
- Applies to all super-effective hits regardless of the multiplier (2x or 4x super-effective both get 0.75x applied).
- Does not affect neutral or resisted hits.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Gorilla Tactics">
## Description
Boosts the holder's Attack by 1.5x, but locks the holder into the first move it uses each time it enters the field (like a Choice Band).

## Mechanics
- `onModifyAtk` (priority 1): returns `chainModify(1.5)` to boost Attack by 1.5x. No effect during Dynamax (`pokemon.volatiles['dynamax']`).
- `onModifyMove`: when the holder uses a move for the first time (not locked, not Z/Max/Struggle), sets `abilityState.choiceLock = move.id`.
- `onBeforeMove`: if the holder is locked into a different move than the one being used, the move fails (no PP consumed). Z-moves and Max moves bypass the lock.
- `onDisableMove`: actively disables all move slots except the locked move (except during Dynamax).
- `onEnd` (when leaving the field): clears the choice lock.
- No `breakable` flag — not suppressed by Mold Breaker.
- In the calculator: `atMods.push(6144)` (1.5x) when `attacker.hasAbility('Gorilla Tactics') && move.category === 'Physical' && !attacker.isDynamaxed`.

## Edge Cases
- During Dynamax, both the Attack boost and the move lock are suspended — the holder can use any Dynamax move, and the lock persists from before Dynamax but is not enforced while Dynamaxed.
- Struggle is never subject to the lock (can always be used when out of PP).
- The Attack boost only benefits physical moves in the calculator, though the stat is boosted universally.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Thick Fat">
## Description
Halves the effective Attack and Special Attack of opponents using Fire- or Ice-type moves against the holder, reducing those moves' damage by 50%.

## Mechanics
- `onSourceModifyAtk` (priority 6) and `onSourceModifySpA` (priority 5): if the move is Fire or Ice type, returns `chainModify(0.5)`, halving the respective offensive stat used for damage calculation.
- In the calculator: `atMods.push(2048)` (0.5x applied to Attack stat) when `defender.hasAbility('Thick Fat') && move.hasType('Fire', 'Ice')`.
- Has `breakable` flag: suppressed by Mold Breaker, Teravolt, Turboblaze.

## Edge Cases
- Applies to both physical and special Fire/Ice moves by halving the relevant offensive stat (Atk for physical, SpA for special).
- The reduction is to the attacker's effective stat during calculation, not a final damage modifier, so it interacts correctly with all other modifiers.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Limber">
## Description
Prevents the holder from being paralyzed. If paralysis is gained while Limber is active (e.g., via Skill Swap), it is immediately cured.

## Mechanics
- `onSetStatus`: if the incoming status is paralysis (`par`), returns false to block it. Logs `-immune` if the paralysis was from a move's status effect.
- `onUpdate`: cures paralysis if the holder currently has it and Limber is active (handles cases like Skill Swap granting Limber to a paralyzed Pokémon).
- Has `breakable` flag: suppressed by Mold Breaker, Teravolt, Turboblaze.

## Edge Cases
- Does not protect against any other status conditions.
- If Limber is suppressed by Mold Breaker, paralysis can be inflicted normally.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="RKS System">
## Description
Silvally's signature ability. Changes Silvally's type to match the type of its held Memory item (e.g., Fire Memory → Fire type).

## Mechanics
- The type-changing mechanic is implemented in the sim's status system, not within the ability entry itself.
- Has extensive restriction flags: `failroleplay`, `noreceiver`, `noentrain`, `notrace`, `failskillswap`, `cantsuppress`.
  - Cannot be copied via Role Play, Entrainment, Trace, or Skill Swap.
  - Cannot be passed to another Pokémon via Receiver.
  - Cannot be suppressed by Neutralizing Gas (`cantsuppress`).
- Without a Memory item, Silvally remains Normal type.

## Edge Cases
- Because of `cantsuppress`, Neutralizing Gas cannot remove or suppress RKS System.
- If Silvally loses its Memory item mid-battle (e.g., Knock Off, Trick), the type change from the Memory would no longer be sustained on the next switch-in.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Queenly Majesty">
## Description
Prevents all opposing Pokémon from using priority moves that target the holder or its allies. Functionally identical to Dazzling and Armor Tail.

## Mechanics
- `onFoeTryMove`: if the move has `priority > 0.1` and targets a Pokémon on the holder's side (not `foeSide`), returns false to block the move entirely.
- Exceptions for moves targeting `all`: Perish Song, Flower Shield, and Rototiller are not blocked even if they have priority.
- Has `breakable` flag: suppressed by Mold Breaker, Teravolt, Turboblaze.
- In the calculator: priority moves return early (0 damage/no effect) when `defender.hasAbility('Queenly Majesty', 'Dazzling', 'Armor Tail')`.

## Edge Cases
- The threshold is `priority > 0.1`, so Quick Draw's fractional priority of 0.1 is not blocked (0.1 is not > 0.1). Only moves with priority ≥ 1 (like Fake Out, Quick Attack, Sucker Punch, etc.) are blocked.
- Applies to all opponents — not just those targeting the Queenly Majesty holder directly. Any priority move aimed at an ally is also blocked.
- In doubles, if the holder is on the field, all priority moves from the opponent's side toward either the holder or its partner are blocked.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Refrigerate">
## Description
Converts the holder's Normal-type moves to Ice-type and boosts their power by 1.2x.

## Mechanics
- `onModifyType` (priority -1): changes move type from Normal to Ice and sets `move.typeChangerBoosted = this.effect`.
- `onBasePower` (priority 23): applies 4915/4096 (≈ 1.2x) boost only to moves that were type-changed by this ability.
- Excluded moves (not converted): Revelation Dance, Judgment, Nature Power, Techno Blast, Multi Attack, Natural Gift, Weather Ball, Terrain Pulse. Z-moves (non-status) and Tera Blast (when terastallized) are also excluded.
- No `breakable` flag — not suppressed by Mold Breaker.
- In the calculator: `isRefrigerate = attacker.hasAbility('Refrigerate') && normal` drives the type change, and `bpMods.push(4915)` (≈ 1.2x) is applied to converted moves via the `hasAteAbilityTypeChange` flag.

## Edge Cases
- The 1.2x boost only applies to converted moves; non-converted Normal-excluded moves get no boost.
- Ice-type converted moves interact with Ice-type resistances/immunities and gain Ice STAB if the holder is Ice-type.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Moxie">
## Description
When the holder KOs a Pokémon with a damaging move, raises its Attack by 1 stage.

## Mechanics
- `onSourceAfterFaint`: fires when a Pokémon faints due to the holder's move (`effect.effectType === 'Move'`). Boosts `atk` by `length` (number of Pokémon fainted by that move — normally 1, but in special circumstances like multi-hit could be higher).
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Only triggers when a Pokémon faints due to a move from the holder; indirect KOs (poison, hazards, weather) do not trigger it.
- The `length` parameter means if somehow multiple faints occur from one move hit, the Attack boost could exceed +1 (though this is uncommon in standard play).

## RnB Changes
None documented.

## AI Notes
When a damaging move KOs the target, the AI receives an additional +1 score bonus for that move if the user has Moxie (alongside Beast Boost, Chilling Neigh, or Grim Neigh). This bonus stacks with other kill-score bonuses.
</Element>

<Element name="Sheer Force">
## Description
Removes the secondary effects of moves (additional effects, self-effects) and boosts their power by 1.3x in exchange.

## Mechanics
- `onModifyMove`: if the move has `secondaries`, deletes `move.secondaries`, `move.self`, and (for Clangorous Soulblaze) `move.selfBoost`. Sets `move.hasSheerForce = true`.
- `onBasePower` (priority 21): returns `chainModify([5325, 4096])` (≈ 1.3x) if `move.hasSheerForce || move.hasSheerForceBoost`.
- In the calculator: `(attacker.hasAbility('Sheer Force') && (move.secondaries || move.named('Jet Punch', 'Order Up')) && !move.isMax)` → `bpMods.push(5325)` (1.3x).
- No `breakable` flag — not suppressed by Mold Breaker.
- Does not apply to Max/G-Max moves.

## Edge Cases
- The secondary effect removal includes both effects on the target (e.g., burn from Flamethrower) and self-effects (e.g., stat drop on the user from moves like Overheat or Draco Meteor). Both are removed and replaced with the power boost.
- Life Orb interaction: moves boosted by Sheer Force do not incur Life Orb recoil (the recoil is tied to `AfterMoveSecondary`, which is negated along with other secondary effects).
- Jet Punch and Order Up are explicitly included in the calculator's Sheer Force check even though they may not have traditional `secondaries` fields.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Skill Link">
## Description
Makes multi-hit moves always hit the maximum number of times. Also removes accuracy checks for moves that normally require accuracy per hit.

## Mechanics
- `onModifyMove`: if the move's `multihit` property is an array (variable range like `[2, 5]`), sets `move.multihit = move.multihit[1]` (the maximum value). Also deletes `move.multiaccuracy` if present.
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Only affects moves with an array `multihit` (variable hit counts like 2–5 or 2–3). Moves with a fixed hit count (e.g., Double Hit = 2) already have `multihit` as a plain number, so they are unaffected.
- `multiaccuracy` removal affects moves like Triple Kick, where each successive hit normally has increasing accuracy checks. With Skill Link, all three hits of Triple Kick always connect (assuming the first hit lands).
- The maximum hit count for typical 2–5 hit moves is 5 (Icicle Spear, Bullet Seed, Rock Blast, Pin Missile, Tail Slap, etc.).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Dancer">
## Description
When any Pokémon on the field uses a move with the `dance` flag, the holder immediately copies and uses that same move (without consuming PP).

## Mechanics
- Implemented in `battle-actions.ts:runMove`. After a dance move successfully executes (`moveDidSomething && !move.isExternal`), all Dancer holders on the field that are not semi-invulnerable are collected and each immediately copies the move.
- Dancer activation order: sorted by lowest Speed stat first. Ties are broken by who has had the ability for the least amount of time (`abilityState.effectOrder`).
- The copied move targets: if the original dance's target is an enemy of the Dancer user AND the original user is an ally, the Dancer targets the original target; otherwise the Dancer targets the original user (the one who used the dance).
- Copied moves are executed as `externalMove: true`, so no PP is deducted and no move lock is applied. The copied move also cannot trigger another Dancer chain (`!move.isExternal` guard prevents loops).
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Dancer activates from ANY Pokémon using a dance move — including the opponent. For example, if the opponent uses Swords Dance, the Dancer holder also gets +2 Attack.
- Dance moves include: Swords Dance, Dragon Dance, Quiver Dance, Fiery Dance, Lunar Dance, Petal Dance, Teeter Dance, Feather Dance, Victory Dance, etc. — any move with the `dance` flag.
- Petal Dance has special handling (the "Dancer Petal Dance hack" comment in code) to prevent unintended lock-in.
- If the Dancer user is semi-invulnerable (e.g., mid-Fly), it does not copy the dance.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Imposter">
## Description
On switch-in, the holder immediately transforms into the opposing Pokémon across from it, copying its species, moves, stats, type, and ability.

## Mechanics
- `onSwitchIn`: calls `pokemon.transformInto(target, ...)` where target is the Pokémon at the opposing position. The second argument (Imposter ability) prevents Transform from being overwritten by Neutralizing Gas and from responding to Skill Swap.
- Does not activate when Skill Swapped or when Neutralizing Gas leaves the field.
- In doubles/triples, copies across to the directly opposite position.
- Flags: `failroleplay`, `noreceiver`, `noentrain`, `notrace` — Imposter cannot be copied via Role Play, Receiver, Entrainment, or Trace.

## Edge Cases
- The holder's HP stat is NOT transformed — Imposter retains its own HP and max HP (so Ditto uses Ditto's HP, not the target's HP).
- Each copied move has 5 PP (regardless of the original move's PP).
- Imposter does not activate if the opposing slot is empty.
- If the target is behind a Substitute, Imposter transforms into the Substitute'd Pokémon's actual form (the Substitute is irrelevant to the transform target).
- The transformation changes the holder's moves, ability, base stats (except HP), type, and forme. The holder's actual EVs and IVs still matter for the transformed stats.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Heavy Metal">
## Description
Doubles the holder's weight, increasing damage taken from Low Kick and Grass Knot, and increasing damage dealt by Heat Crash and Heavy Slam (if the holder is heavier than the target).

## Mechanics
- `onModifyWeight` (priority 1): returns `weighthg * 2`, doubling the Pokémon's effective weight.
- In the calculator (`getWeightFactor`): returns 2 for Heavy Metal holders (vs 0.5 for Light Metal/Float Stone, 1 otherwise).
- Has `breakable` flag: suppressed by Mold Breaker, Teravolt, Turboblaze.

## Edge Cases
- Doubled weight affects Low Kick and Grass Knot (heavier Pokémon take more damage), but also benefits Heat Crash and Heavy Slam when the user is heavier relative to the target.
- Autotomize reduces weight by 100kg per use, which applies after Heavy Metal's doubling.
- Suppressed by Mold Breaker — the attacker can ignore the doubled weight when Mold Breaker is in play.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Sturdy">
## Description
Grants immunity to OHKO moves (Sheer Cold, Fissure, etc.) and allows the holder to survive any single move that would otherwise KO it from full HP, leaving it at 1 HP.

## Mechanics
- `onTryHit`: if the move has the `ohko` flag, returns null (immunity). OHKO moves always fail against a Sturdy Pokémon.
- `onDamage` (priority -30): if the holder is at exactly full HP (`target.hp === target.maxhp`) and the incoming damage would exceed or equal the holder's HP, caps the damage at `target.hp - 1` (leaves 1 HP). Only applies to moves (`effect.effectType === 'Move'`).
- Has `breakable` flag: suppressed by Mold Breaker, Teravolt, Turboblaze.

## Edge Cases
- The 1 HP survival only works when the holder is at full HP. If the holder has taken any prior damage in that turn (e.g., from hazards on switch-in, a multi-hit move's first hit, etc.), the `target.hp === target.maxhp` check fails and Sturdy does not save it.
- The OHKO immunity is unconditional regardless of current HP.
- Indirect damage (sandstorm, burn, poison, entry hazards) does not interact with Sturdy's survival mechanic.
- Mold Breaker suppresses Sturdy entirely — both OHKO immunity and the 1 HP survival.

## RnB Changes
None documented.

## AI Notes
- General setup moves: the AI will not use setup moves if the player can KO it (unless Sturdy/Focus Sash is active at full HP).
- Counter/Mirror Coat scoring: if the player can KO the AI and the AI has Sturdy/Focus Sash at 100% HP, and the player only has moves of the corresponding split, the move score gains +2. If the player can KO the AI without Sturdy/Sash, Counter/Mirror Coat receives a −20 penalty.
</Element>

<Element name="Motor Drive">
## Description
Grants immunity to Electric-type moves. When an Electric-type move would hit the holder, it is absorbed and the holder's Speed rises by 1 stage instead.

## Mechanics
- `onTryHit`: if the incoming move is Electric-type and not self-targeted, calls `this.boost({ spe: 1 })`. If the boost succeeds, returns null (move absorbed). If Speed cannot be raised (already +6), logs `-immune` and still returns null (move still blocked).
- Has `breakable` flag: suppressed by Mold Breaker, Teravolt, Turboblaze.
- In the calculator: `defender.hasAbility('Lightning Rod', 'Motor Drive', 'Volt Absorb')` in the immunity check — all three cause Electric moves to return 0 damage.

## Edge Cases
- The Speed boost is granted even if at -6 Speed (the `this.boost` call attempts the boost, and if already at max +6 the immune message is shown, but the move is still blocked regardless).
- Being in Gravity or holding an Iron Ball does not affect Motor Drive's Electric immunity — those only affect airborne status.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Reckless">
## Description
Boosts the power of moves that deal recoil damage or crash damage to the user by 1.2x.

## Mechanics
- `onBasePower` (priority 23): returns `chainModify([4915, 4096])` (≈ 1.2x) if `move.recoil || move.hasCrashDamage`.
- In the calculator: `bpMods.push(4915)` when `attacker.hasAbility('Reckless') && (move.recoil || move.hasCrashDamage)`.
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Affects recoil moves (Double-Edge, Head Smash, Brave Bird, Flare Blitz, Volt Tackle, Take Down, Submission, Wild Charge, etc.) and crash damage moves (High Jump Kick, Jump Kick).
- Does NOT boost Struggle — Struggle uses `struggleRecoil: true` which is a separate field from `recoil`, so it is not detected.
- The recoil damage itself is not reduced or increased — only the base power is boosted.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Tinted Lens">
## Description
Doubles the damage of not-very-effective moves, effectively neutralizing the type disadvantage penalty.

## Mechanics
- `onModifyDamage`: if `typeMod < 0` (not-very-effective hit), returns `chainModify(2)` to double the damage.
- In the calculator: `finalMods.push(8192)` (2x) when `attacker.hasAbility('Tinted Lens') && typeEffectiveness < 1`.
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Does not affect type immunities (`typeMod === 0`); Tinted Lens only fires when `typeMod < 0` (resisted). A Ghost-type move against a Normal-type still does 0 damage.
- A 0.5x-resisted move becomes effectively 1x (neutral) after Tinted Lens doubles it. A 0.25x-resisted move (e.g., 4x-resisted) becomes 0.5x (still resisted but less so).
- The 2x boost stacks with STAB, other boosts, etc.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Screen Cleaner">
## Description
On switch-in, removes Reflect, Light Screen, and Aurora Veil from both the holder's side and all opposing sides.

## Mechanics
- `onStart`: iterates over `['reflect', 'lightscreen', 'auroraveil']` and removes each from all sides — both the holder's own side and all foe sides. The `-activate` message only appears once even if multiple screens are cleared.
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Removes screens from BOTH sides simultaneously, so it can clear the holder's own team's screens as well as the opponent's.
- Does not affect Mist, Safeguard, or other side conditions.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Harvest">
## Description
At the end of each turn, the holder has a 50% chance to restore a consumed berry (100% chance in sunny weather).

## Mechanics
- `onResidual` (order 28, suborder 2): if weather is Sun or Desolate Land, or if a 50% random chance succeeds, attempts to restore the holder's last consumed item — provided the holder is alive, has no item, and the last consumed item was a berry (`isBerry`).
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Only restores berries — non-berry items cannot be harvested.
- In Sun, the restore is guaranteed (no random check). Outside of Sun, it's 50% per turn.
- If the holder currently has an item (e.g., hasn't consumed the berry yet), Harvest does nothing.

## RnB Changes
In RnB, consumed or removed items are not restored during battle (Mechanic Changes.txt line 33). This means Harvest does not restore berries in RnB — the ability is non-functional for its primary purpose.

## AI Notes
None documented.
</Element>

<Element name="Healer">
## Description
At the end of each turn, adjacent ally Pokémon (in doubles/multi battles) have a 30% chance to have their status condition cured.

## Mechanics
- `onResidual` (order 5, suborder 3): for each `adjacentAlly` of the holder that has a status condition, a 30% random chance (`randomChance(3, 10)`) triggers to cure that ally's status.
- Has no effect in singles (no adjacent allies exist).
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Each adjacent ally is checked independently with its own 30% roll.
- The holder itself is not affected — only allies benefit.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Chlorophyll">
## Description
Doubles the holder's Speed stat when the weather is sunny (Sun or Harsh Sunshine/Desolate Land).

## Mechanics
- `onModifySpe`: if `effectiveWeather()` is `sunnyday` or `desolateland`, returns `chainModify(2)` to double Speed.
- In the calculator: `speedMods.push(8192)` (2x) when `pokemon.hasAbility('Chlorophyll') && weather.includes('Sun')`.
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Only applies in Sun — does not activate under other weather conditions.
- The Utility Umbrella does not affect the ability holder; Utility Umbrella only affects the attacker/defender in damage calculations, not weather-based ability checks for the holder.

## RnB Changes
In RnB, weather from weather-setting abilities is permanent. This means Chlorophyll is permanently active as long as a Drought Pokémon is on the field, giving the holder a permanent 2x Speed bonus against sun teams.

## AI Notes
None documented.
</Element>

<Element name="Sand Veil">
## Description
In sandstorm, reduces the accuracy of moves targeting the holder by 20%. Also grants immunity to sandstorm damage.

## Mechanics
- `onModifyAccuracy` (priority -1): in sandstorm weather, multiplies move accuracy by 3277/4096 (≈ 0.8x), reducing it by 20%.
- `onImmunity` for 'sandstorm': returns false, preventing end-of-turn sandstorm chip damage.
- Has `breakable` flag: suppressed by Mold Breaker, Teravolt, Turboblaze.

## Edge Cases
- Only applies in sandstorm; does not reduce accuracy in other weather.
- The accuracy reduction works multiplicatively (e.g., a 100% accurate move becomes 80% accuracy, a 90% accurate move becomes 72%).
- Always-accurate moves (accuracy set to `true`) are not affected — the `typeof accuracy !== 'number'` check excludes them.

## RnB Changes
In RnB, Sandstream creates permanent sandstorm. Against a sand team, Sand Veil's 20% evasion boost is permanently active whenever sandstorm is the current weather.

## AI Notes
None documented.
</Element>

<Element name="Aura Break">
## Description
Reverses the effects of Fairy Aura and Dark Aura, turning their 1.33x boost into a 0.75x reduction for the corresponding move types.

## Mechanics
- `onStart`: announces the ability on switch-in.
- `onAnyTryPrimaryHit`: sets `move.hasAuraBreak = true` for all non-Status damaging moves, informing Fairy/Dark Aura handlers to apply the nerf.
- Fairy Aura and Dark Aura check `move.hasAuraBreak`: without Aura Break they apply `chainModify([5448, 4096])` (≈ 1.33x); with Aura Break they apply `chainModify([3072, 4096])` (0.75x, a 25% reduction).
- In the calculator: `isUserAuraBreak = attacker.hasAbility('Aura Break') || defender.hasAbility('Aura Break')`; when an aura is active and aura break is also active, `bpMods.push(3072)` (0.75x) instead of `bpMods.push(5448)` (1.33x).
- Has `breakable` flag: suppressed by Mold Breaker, Teravolt, Turboblaze.

## Edge Cases
- Aura Break reverses auras from either side — it doesn't matter if Fairy Aura is on the attacker or defender, Aura Break on either active Pokémon negates and reverses it.
- If Aura Break is suppressed by Mold Breaker, the aura boost applies normally (1.33x).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Prankster">
## Description
Gives the holder's status moves +1 priority. In gen 7+, status moves boosted by Prankster fail against Dark-type Pokémon when targeting an opponent.

## Mechanics
- `onModifyPriority`: if the move category is Status, returns `priority + 1` and sets `move.pranksterBoosted = true`.
- No `breakable` flag — not suppressed by Mold Breaker.
- Dark-type immunity (gen 7+): if `move.pranksterBoosted` is true and the user has Prankster and the target is an opponent, the move fails against Dark-type targets (checked via `dex.getImmunity('prankster', target)`).
- The `pranksterBoosted` flag is cleared when a Prankster-boosted move is reflected by Magic Bounce (to prevent the reflected move from getting priority again).

## Edge Cases
- Only applies to Status category moves; damaging moves (even if they have secondary effects) get no priority boost.
- In doubles, Prankster-boosted status moves that target allies are NOT blocked by Dark-type immunity (only opponent targets are blocked).
- Ally-targeting Prankster moves (e.g., Helping Hand, Tailwind) work normally even against Dark-type partners.
- A Pokémon behind a Substitute with Dark type is still immune to Prankster-boosted status moves.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Sniper">
## Description
Boosts the power of critical hits from 1.5x to 2.25x by applying an additional 1.5x multiplier on top of the standard critical hit damage.

## Mechanics
- `onModifyDamage`: if the move hit data shows a critical hit (`crit`), returns `chainModify(1.5)`.
- Standard critical hit applies 1.5x to base damage in the calculator. Sniper then applies an additional 1.5x via final mods (`finalMods.push(6144)`), resulting in 1.5 × 1.5 = 2.25x total damage relative to a normal hit.
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Sniper only applies when a critical hit occurs. Non-critical hits are unaffected.
- In RnB, the critical hit rate is 1/16 (more frequent than standard gen 8's 1/24), meaning Sniper benefits from more frequent crits.

## RnB Changes
None documented (critical hit rate is 1/16 in RnB, making Sniper activations more frequent than standard).

## AI Notes
When scoring Focus Energy or Laser Focus: the AI scores it at +7 (instead of +6) if the user has Sniper (alongside Super Luck, Scope Lens, or a move with a high crit chance).
</Element>

<Element name="Quick Draw">
## Description
Gives damaging moves a 30% chance to move at fractional priority (+0.1), causing the holder to act first within normal priority brackets but before most priority abilities can detect it.

## Mechanics
- `onFractionalPriority` (priority -1): for non-Status moves, 30% chance (`randomChance(3, 10)`) to return `0.1`, giving the move fractional priority of +0.1.
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- The +0.1 fractional priority puts the move before other priority-0 moves but does NOT reach the +1 threshold, so Queenly Majesty/Dazzling/Armor Tail's `priority > 0.1` check is not triggered — Quick Draw moves are not blocked by those abilities.
- If the holder already has a move with positive priority (e.g., Quick Attack at +1), Quick Draw would push it to 1.1, still safe from the 0.1 guard but above other +1 priority moves with normal fractional priority.
- Status moves are excluded; Quick Draw only applies to damaging moves.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Early Bird">
## Description
The holder wakes up from sleep in half the number of turns (rounds up), making sleep last 1 turn instead of the usual 1–3 turns.

## Mechanics
- Implemented in `statuses.js` (not visible in the ability entry). The ability causes the holder's sleep counter to decrement twice as fast.
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Reduces the sleep duration: a Pokémon would normally sleep 1–3 turns; with Early Bird it effectively sleeps for 1 turn in practice.
- Also applies to Rest-induced sleep, cutting the standard 2-turn Rest recovery to 1 turn.

## RnB Changes
None documented.

## AI Notes
When scoring Rest: if the AI has Early Bird (alongside Shed Skin, sleep-curing items, Sleep Talk/Snore, or Hydration in rain), Rest receives a +8 score instead of the base +7.
</Element>

<Element name="Tough Claws">
## Description
Boosts the power of contact moves by 1.3x.

## Mechanics
- `onBasePower` (priority 21): if the move has the `contact` flag, returns `chainModify([5325, 4096])` (≈ 1.3x).
- In the calculator: `bpMods.push(5325)` when `attacker.hasAbility('Tough Claws') && move.flags.contact`.
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Applies to any move with the `contact` flag, regardless of damage category (most contact moves are physical, but some special moves like Grass Knot make contact).
- Does not affect non-contact moves (e.g., Fire Blast, Earthquake).

## RnB Changes
None documented.

## AI Notes
Role Play scoring: if the AI's partner has Tough Claws (or Huge Power, Pure Power, Protean) and the AI itself does NOT have any of those abilities, Role Play scores +9 (to acquire that ability). If the AI already has Tough Claws, Role Play scores −20.
</Element>

<Element name="Gulp Missile">
## Description
Cramorant's signature ability. When Cramorant uses Surf or Dive, it transforms into a forme holding prey. If that forme is hit by a damaging move, it spits the prey at the attacker dealing damage and applying a secondary effect, then reverts to normal forme.

## Mechanics
- `onSourceTryPrimaryHit`: if Cramorant uses Surf and has Gulp Missile, transforms into Gulping (HP > 50%) or Gorging (HP ≤ 50%) forme.
- Dive's transformation is implemented in moves.ts (`onTryMove` for Dive).
- `onDamagingHit`: if Cramorant is in Gulping or Gorging forme and is hit:
  - Deals 25% of attacker's max HP as damage.
  - Gulping: lowers attacker's Defense by 1 stage.
  - Gorging: attempts to paralyze the attacker.
  - Then transforms Cramorant back to its base forme.
- Does not trigger if the source is already fainted or inactive, or if Cramorant is semi-invulnerable when hit.
- Flags: `cantsuppress` (Neutralizing Gas cannot suppress it), `notransform`, `failroleplay`, `noreceiver`, `noentrain`, `notrace`, `failskillswap`.

## Edge Cases
- The forme change from Surf/Dive persists until Cramorant is hit by a damaging move, even across turns.
- Gulping forme uses Arrokuda as prey; Gorging uses Pikachu. The forme determines the secondary effect (Defense drop vs paralysis).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Cotton Down">
## Description
When the holder is hit by a damaging move, lowers the Speed of all other active Pokémon (on all sides) by 1 stage.

## Mechanics
- `onDamagingHit`: iterates over all active Pokémon except the holder and fainted ones, calling `this.boost({ spe: -1 })` for each. The `-ability` activation message appears only once even if multiple Pokémon are affected.
- No `breakable` flag — not suppressed by Mold Breaker.

## Edge Cases
- Affects ALL other active Pokémon — both opponents and allies in doubles. The holder's own allies take the Speed drop as well.
- Does not affect the holder itself.
- Only triggers on damaging moves; status moves do not activate Cotton Down.
- Each Pokémon's Speed drop is independent — abilities that react to stat drops (Defiant, Competitive, Contrary) can activate.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Power Construct">
## Description
Zygarde's signature ability. When Zygarde's HP drops to 50% or below at the end of a turn, it transforms into Zygarde-Complete forme, dramatically increasing its HP and bulk.

## Mechanics
- `onResidual` (order 29): if the Pokémon is Zygarde (not transformed), is not already in Complete forme, is alive, and HP is at or below 50% of max HP → triggers forme change to Zygarde-Complete.
- `formeRegression = true` is set, indicating the forme should revert when the Pokémon is no longer active.
- Flags: `failroleplay`, `noreceiver`, `noentrain`, `notrace`, `failskillswap`, `cantsuppress` — cannot be copied, received, entrained, traced, skill swapped, or suppressed by Neutralizing Gas.

## Edge Cases
- Triggers at end of turn; does not activate mid-turn (even if HP drops below 50% from a damaging move during the turn).
- The HP threshold check uses `pokemon.hp > pokemon.maxhp / 2`, so exactly 50% HP does trigger the transformation.
- Will not re-trigger once already in Complete forme.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>




<Element name="Hyper Cutter">
## Description
Prevents the holder's Attack stat from being lowered by external sources. Does not prevent self-induced Attack drops.

## Mechanics
- `onTryBoost`: if the source is different from the target and `boost.atk < 0`, removes the Attack drop from the boost object.
- If the causing effect has no secondaries, a "-fail" message is added (explicit fail). If the effect has secondaries (e.g., a move with a secondary chance to drop Attack), the drop is silently ignored with no fail message.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- In the calculator (`util.ts`): listed alongside Clear Body, White Smoke, and Full Metal Body as blockers of Intimidate's Attack drop in `checkIntimidate`.

## Edge Cases
- Only blocks external Attack drops; moves or effects that lower the holder's own Attack (e.g., Superpower) are not blocked.
- Mold Breaker can bypass Hyper Cutter and successfully lower the holder's Attack.
- Secondary stat drops on damaging moves (e.g., a move with 10% chance to drop Attack) are silently blocked — no fail message is shown.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Pure Power">
## Description
Doubles the holder's Attack stat, effectively doubling physical damage output. Identical in effect to Huge Power.

## Mechanics
- `onModifyAtk` (priority 5): multiplies Attack by 2x via `this.chainModify(2)`.
- `flags: {}` — not breakable; Mold Breaker cannot suppress Pure Power.
- In the calculator (`gen789.ts`): `atMods.push(8192)` (2x) is applied when the attacker has Huge Power or Pure Power and the move is Physical.
- The 2x modifier applies to the Attack stat used in the damage formula, not as a damage multiplier directly.

## Edge Cases
- Applies only to physical moves; Special moves are unaffected.
- Not suppressed by Mold Breaker (no `breakable` flag).

## RnB Changes
None documented.

## AI Notes
- Role Play: scores +9 if the AI's partner has Huge Power, Pure Power, Protean, or Tough Claws and the AI itself does not have one of those abilities. Scores -20 if the AI already has one of those abilities (role-playing away from it is bad).
</Element>

<Element name="Water Veil">
## Description
Prevents the holder from being burned. Cures burn if the holder somehow already has it when the ability activates.

## Mechanics
- `onUpdate`: if the holder has burn status, activates and calls `cureStatus()` (handles cases where burn was inflicted before the ability was active, e.g., via Skill Swap).
- `onSetStatus`: if the incoming status is burn, returns `false` to block it. If the burn attempt came from a move's direct status (not a secondary), also shows an immune message.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- Not referenced in the damage calculator — burn prevention does not affect damage output directly.

## Edge Cases
- Only blocks burn; other status conditions (paralysis, poison, sleep, freeze) are not affected.
- Mold Breaker bypasses Water Veil and can inflict burn.
- Flame Orb cannot burn a holder with Water Veil.
- Secondary burn chances (e.g., from Flamethrower's 10% burn) are blocked silently (no immune message shown for secondaries).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Plus">
## Description
In doubles, if an ally has Plus or Minus, the holder's Special Attack is boosted by 1.5x. Only relevant in multi-battle formats.

## Mechanics
- `onModifySpA` (priority 5): iterates over allies; if any ally has Plus or Minus, applies `this.chainModify(1.5)`.
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`gen789.ts`): `atMods.push(6144)` (1.5x) is applied when `attacker.abilityOn` is `true` and the move is Special. `abilityOn` must be manually set to indicate the ally condition is met.
- Showdown: Plus and Minus are symmetric — either ability triggers the other's boost (both check for allies with `['minus', 'plus']`).

## Edge Cases
- Has no effect in singles (no allies to trigger the condition).
- Both Plus and Minus on different allies will boost each other's SpA simultaneously.
- The ally must be active on the field; a fainted or undeployed partner does not count.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Cheek Pouch">
## Description
When the holder eats a berry (for any reason), it restores 1/3 of its maximum HP in addition to the berry's normal effect.

## Mechanics
- `onEatItem`: heals the holder for `pokemon.baseMaxhp / 3` whenever any berry is consumed.
- `flags: {}` — not breakable by Mold Breaker.
- The heal is additive with the berry's own effect (e.g., eating a Sitrus Berry restores 25% HP from the berry plus 33% from Cheek Pouch).
- Not referenced in the damage calculator.

## Edge Cases
- Triggers on any berry consumption, regardless of what triggered it (held item trigger, Stuff Cheeks, Bug Bite, Teatime, etc.).
- The heal can overflow if the berry + Cheek Pouch heal would exceed max HP; excess is lost.

## RnB Changes
- Consumed berries are not restored in RnB (no Harvest, no item restoration), so Cheek Pouch's heal is available once per berry carried into battle.

## AI Notes
None documented.
</Element>

<Element name="Color Change">
## Description
When the holder is hit by a damaging move, it changes its type to match the type of the move used against it.

## Mechanics
- `onAfterMoveSecondary`: fires after the holder is hit. If the holder is still alive, the move is a damaging move (not Status), and the move's type is different from the holder's current type (and not ???), calls `setType(type)` to change the holder's type.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.

## Edge Cases
- Does not trigger if the holder faints from the hit.
- Does not trigger if the holder already has the move's type (type change would be redundant).
- Does not trigger on Status moves.
- In doubles, there is a special "Curse Glitch" interaction: if the holder is in position 1 and was about to use Curse, the Curse target is redirected to self (position -1) after the type change.
- Multi-hit moves trigger the type change after all hits complete (fires in `onAfterMoveSecondary`).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Pixilate">
## Description
Converts Normal-type moves to Fairy-type and grants them a 1.2x base power boost. One of the four ATE abilities.

## Mechanics
- `onModifyType` (priority -1): if the move is Normal-type and not in the exclusion list (Judgment, Multi-Attack, Natural Gift, Revelation Dance, Techno Blast, Terrain Pulse, Weather Ball), and not a damaging Z-move or Tera Blast while Terastallized, changes move type to Fairy and sets `move.typeChangerBoosted = this.effect`.
- `onBasePower` (priority 23): if `move.typeChangerBoosted === this.effect`, applies `[4915, 4096]` (≈1.2x) boost.
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`gen789.ts`): sets `isPixilate = true`, type becomes Fairy, `hasAteAbilityTypeChange = true` → `bpMods.push(4915)` (1.2x).
- Does not apply to Z-moves (damaging) or Normalize-type interactions.

## Edge Cases
- Status Normal-type Z-moves (Z-Status) still get the type conversion (the check excludes only `move.isZ && move.category !== 'Status'`).
- The 1.2x boost applies in addition to STAB if the holder is Fairy-type.
- Moves excluded from conversion (Judgment, Multi-Attack, etc.) are not converted even if they are typed Normal.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Tangling Hair">
## Description
When the holder is hit by a contact move, the attacker's Speed is lowered by 1 stage. Functions identically to Gooey.

## Mechanics
- `onDamagingHit`: if the move makes contact with the holder, announces the ability and boosts the attacker by `{ spe: -1 }`.
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`util.ts`): for Gyro Ball and Electro Ball (which make contact into Gooey/Tangling Hair when hitting multiple times via Parental Bond), applies a -1 Speed boost to the attacker per hit, recalculating the attacker's speed for subsequent hit calculations.

## Edge Cases
- Requires the move to make contact; non-contact moves do not trigger the Speed drop.
- Long Reach and Protective Pads on the attacker prevent the contact classification, blocking the Speed drop.
- Mold Breaker does not suppress Tangling Hair (no breakable flag).
- Gyro Ball / Electro Ball interactions with Parental Bond multi-hit apply the Speed drop after each hit, reducing the attacker's Speed before recalculating the second hit's power.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Pressure">
## Description
When an opponent targets the holder with a move, that move costs 1 extra PP. Announces itself on entry.

## Mechanics
- `onStart`: displays the ability activation message.
- `onDeductPP`: if the target is not an ally of the move's user, returns 1 (extra PP deducted in addition to normal cost).
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator (PP mechanics are not modeled).

## Edge Cases
- Applies to all moves used against the holder by opponents, including status moves.
- Ally moves (in doubles) are not affected — Pressure only triggers for opposing Pokémon's moves.
- Moves blocked by redirection or that miss still have the extra PP deducted if they targeted the holder.
- If a move has only 1 PP remaining, the extra deduction still occurs (moves can reach 0 PP).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Steadfast">
## Description
When the holder flinches, its Speed is raised by 1 stage.

## Mechanics
- `onFlinch`: boosts the holder's Speed by +1 (`{ spe: 1 }`).
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.

## Edge Cases
- Only triggers when the holder actually flinches (i.e., the flinch condition was applied and the holder's move is suppressed). Does not trigger if flinch immunity prevents the flinch itself.
- Inner Focus prevents flinching entirely, so a Pokémon with both Inner Focus and Steadfast (if such a combination were possible) would never flinch and never gain the Speed boost.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Immunity">
## Description
Prevents the holder from being poisoned or badly poisoned. Cures poison if somehow already afflicted when the ability activates.

## Mechanics
- `onUpdate`: if the holder has `psn` or `tox` status, activates and calls `cureStatus()`.
- `onSetStatus`: if the incoming status is `psn` or `tox`, returns `false` to block it. If from a move's direct status effect, shows an immune message.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- Not referenced in the damage calculator.

## Edge Cases
- Only blocks poison (psn) and toxic poison (tox); other status conditions are not affected.
- Mold Breaker can bypass Immunity and inflict poison.
- Toxic Orb cannot poison a holder with Immunity.
- Secondary poison chances (e.g., Sludge Bomb's 30% poison) are silently blocked with no immune message.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Heatproof">
## Description
Halves the base power of Fire-type moves targeting the holder, and halves burn damage the holder receives.

## Mechanics
- **Gen 8 implementation** (overrides base): `onSourceBasePower` (priority 18): if move is Fire-type, applies `this.chainModify(0.5)` to halve base power.
- `onDamage`: if the damage source is burn (`effect.id === 'brn'`), returns `damage / 2`.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- In the calculator (`gen789.ts`): `bpMods.push(2048)` (0.5x) when defender has Heatproof and move is Fire-type.

## Edge Cases
- Base Showdown (pre-Gen 8) used `onSourceModifyAtk`/`onSourceModifySpA` to halve the attacker's offensive stat. Gen 8 switched to `onSourceBasePower`, which halves base power instead — a subtle difference in calculation order.
- Mold Breaker suppresses Heatproof, allowing full-power Fire moves.
- Does not grant Fire immunity; it only halves Fire damage.
- Burn damage reduction is independent of the Fire move reduction; both apply if the holder is burned and hit by a Fire move.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Overcoat">
## Description
Grants immunity to weather chip damage (sandstorm, hail/snowscape) and to powder-based moves (e.g., Sleep Powder, Spore, Stun Spore, Powder).

## Mechanics
- `onImmunity`: returns `false` for sandstorm, hail, and powder immunity types, preventing weather damage from affecting the holder.
- `onTryHit` (priority 1): if the move has the `powder` flag and the target is not the move's source, blocks the move entirely and shows an immune message.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- Not referenced in the damage calculator.

## Edge Cases
- Only blocks weather chip damage; weather-boosted moves (e.g., Blizzard in Hail) still function normally.
- Grass-type Pokémon are already immune to powder moves; Overcoat provides redundant coverage for them.
- Mold Breaker can bypass Overcoat and allow powder moves to land.
- The powder immunity check uses `this.dex.getImmunity('powder', target)` — Grass-type targets with Overcoat will still show immunity (but it comes from type, not ability).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Receiver">
## Description
In doubles, when an ally faints, the holder copies that ally's ability (as long as the ally's ability can be received).

## Mechanics
- `onAllyFaint`: when an ally faints, if the holder is still alive and the ally's ability does not have the `noreceiver` flag (and is not `noability`), calls `setAbility()` on the holder to copy the fainted ally's ability.
- `flags: { failroleplay: 1, noreceiver: 1, noentrain: 1, notrace: 1 }` — Receiver itself cannot be copied by Role Play, received by another Receiver, entrained, or traced. However, it can be Skill Swapped (no `failskillswap`).
- Not referenced in the damage calculator.

## Edge Cases
- Abilities with the `noreceiver` flag cannot be copied (e.g., Comatose, Battle Bond, Multitype, etc.).
- The `noability` check prevents copying Pokémon with no ability (Pokémon: Let's Go Pokémon).
- Has no effect in singles (no allies).
- The holder must be alive when the ally faints — if both faint simultaneously, Receiver does not trigger.

## RnB Changes
None documented.

## AI Notes
- In the Clifford and Macey double battle, Passimian (which has Receiver) scores Detect at +14 specifically because its partner has Huge Power. This is a trainer-specific behavior where Receiver's potential to copy Huge Power raises Detect's value.
</Element>

<Element name="Shield Dust">
## Description
Blocks secondary effects of moves targeting the holder. Also blocks certain ability-triggered effects (Poison Touch, Toxic Chain) even though those technically aren't secondaries.

## Mechanics
- `onModifySecondaries`: filters the secondaries list to retain only effects where `effect.self` is set (i.e., self-targeting effects like recoil or self-stat boosts that the attacker applies to themselves). All secondary effects targeting the holder are removed.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- Poison Touch and Toxic Chain have explicit checks: `if (target.hasAbility('shielddust') || target.hasItem('covertcloak')) return;` — these block their effects even though they are implemented as ability hooks rather than secondaries.
- Not referenced in the damage calculator.

## Edge Cases
- Does not block the primary damage of a move — only secondary effects (stat drops, status, flinch, etc.) targeting the holder.
- Mold Breaker suppresses Shield Dust, allowing secondary effects to land.
- Covert Cloak item provides identical secondary blocking; they stack redundantly.
- Self-targeting effects (e.g., a move's self-buff on the attacker) are NOT blocked — `effect.self` effects pass through.

## RnB Changes
None documented.

## AI Notes
- Fake Out scores +9 on the AI's first turn out, but only when not targeting a Shield Dust or Inner Focus Pokémon (flinch would fail, making Fake Out useless).
</Element>

<Element name="Solar Power">
## Description
In sun, boosts Special Attack by 1.5x but drains 1/8 max HP at the end of each turn.

## Mechanics
- `onModifySpA` (priority 5): if current weather is sunnyday or desolateland, applies `this.chainModify(1.5)` to Special Attack.
- `onWeather`: if the current weather is sunnyday or desolateland, deals `target.baseMaxhp / 8` damage to the holder each turn.
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`gen789.ts`): `atMods.push(6144)` (1.5x) when attacker has Solar Power, weather is Sun or Harsh Sunshine, and move is Special.

## Edge Cases
- Only affects Special moves; Physical moves receive no boost.
- The HP drain occurs each residual phase while sun is active, regardless of whether the holder attacks.
- Does not grant any benefit in non-sunny weather.

## RnB Changes
- Weather abilities set weather permanently in RnB. If a Drought user is on the field, Solar Power's 1.5x SpA boost and 1/8 HP drain are constant throughout the battle.

## AI Notes
None documented.
</Element>

<Element name="Chilling Neigh">
## Description
When the holder KOs an opponent with a move, raises its Attack by 1 stage. Glastrier's signature ability; also incorporated into As One (Glastrier).

## Mechanics
- `onSourceAfterFaint`: if the KO was caused by a move (`effect.effectType === 'Move'`), boosts the holder's Attack by `length` (number of Pokémon fainted from that hit, typically 1).
- `flags: {}` — not breakable by Mold Breaker.
- As One (Glastrier) uses Chilling Neigh's effect explicitly: `this.boost({ atk: length }, source, source, this.dex.abilities.get('chillingneigh'))`.
- Not referenced in the damage calculator.

## Edge Cases
- Only triggers when the holder's move KOs an opponent — indirect damage (poison, burn, etc.) does not trigger it.
- In doubles, if one move KOs both opponents simultaneously, `length` would be 2 and the holder gains +2 Attack.

## RnB Changes
None documented.

## AI Notes
- When a damaging move kills the target, the AI adds +1 to that move's score if it has Moxie, Beast Boost, Chilling Neigh, or Grim Neigh (on top of the standard kill bonus).
</Element>

<Element name="Cursed Body">
## Description
When the holder is hit by a damaging move, there is a 30% chance to Disable the attacker's move.

## Mechanics
- `onDamagingHit`: if the attacker does not already have the `disable` volatile condition, and the move is not a Max move, not a future move (Future Sight/Doom Desire), and not Struggle, rolls a 30% chance (`randomChance(3, 10)`) to apply `disable` to the attacker.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.

## Edge Cases
- Does not trigger if the attacker is already under Disable.
- Max moves, future moves, and Struggle are excluded from triggering or being disabled.
- The Disable effect locks the attacker out of the specific move that hit the holder.
- Applies even if the holder faints from the hit (the check is `onDamagingHit`, not after survival).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Rattled">
## Description
When hit by a Dark-, Bug-, or Ghost-type move, or when Intimidated, raises the holder's Speed by 1 stage.

## Mechanics
- `onDamagingHit`: if the move is Dark, Bug, or Ghost type, boosts the holder's Speed by `{ spe: 1 }`.
- `onAfterBoost`: if the effect name is Intimidate and `boost.atk` is set (Attack was lowered), boosts Speed by `{ spe: 1 }`.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.

## Edge Cases
- The Intimidate trigger fires even if the Attack drop was partially or fully blocked (e.g., by Hyper Cutter or Clear Body) — `boost.atk` just needs to be present in the boost object; the check is not whether the drop succeeded.
- Move type must be Dark, Bug, or Ghost; a Pokémon with Scrappy using a Normal move as Ghost-typed does not trigger this.
- Does not trigger on status moves of those types, only on damaging hits.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="White Smoke">
## Description
Prevents all of the holder's stats from being lowered by external sources. Functionally identical to Clear Body.

## Mechanics
- `onTryBoost`: if the source is different from the target, removes any negative stat changes from the boost object (`delete boost[i]` for all `boost[i] < 0`). If any negatives were found and the effect is not a secondary or Octolock, displays a fail message.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- In the calculator (`util.ts`): listed alongside Clear Body, Hyper Cutter, and Full Metal Body as a blocker of Intimidate's Attack drop in `checkIntimidate`.

## Edge Cases
- Blocks all external stat drops, not just Attack (unlike Hyper Cutter which only blocks Attack drops).
- Octolock is exempted from the fail message but the stat drop is still blocked.
- Secondary effects (e.g., a move's 10% chance to lower a stat) are blocked silently — no fail message shown.
- Mold Breaker bypasses White Smoke and can lower the holder's stats.
- Does not prevent self-induced stat drops.

## RnB Changes
None documented.

## AI Notes
- Speed-reduction moves and Attack/SpAtk reduction moves score +5 (instead of +6) against targets with Contrary, Clear Body, or White Smoke, since the stat drop will fail.
</Element>

<Element name="Insomnia">
## Description
Prevents the holder from falling asleep and blocks Yawn. Cures sleep if the holder already has it when the ability activates.

## Mechanics
- `onUpdate`: if the holder has sleep status, activates and calls `cureStatus()`.
- `onSetStatus`: if the incoming status is sleep, returns `false` to block it. Shows immune message if from a move's direct status.
- `onTryAddVolatile`: if the volatile is Yawn, returns `null` to block it and shows immune message.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- Not referenced in the damage calculator.

## Edge Cases
- Also blocks Yawn from taking effect — both the immediate infliction and the delayed-sleep volatile are blocked.
- Mold Breaker bypasses Insomnia, allowing sleep and Yawn to land.
- Rest is blocked by Insomnia — the user cannot sleep, so Rest fails.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Sand Stream">
## Description
Sets sandstorm weather when the holder enters the field. In RnB, this sandstorm is permanent.

## Mechanics
- `onStart`: calls `this.field.setWeather('sandstorm')`.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator directly, but sandstorm weather influences Sand Force, Sand Rush, Sand Veil, and Rock-type SpDef boost.

## Edge Cases
- If multiple weather-setting abilities are present, the last one to activate (determined by speed) sets the final weather.
- In standard play, sandstorm lasts 8 turns (5 without Smooth Rock); in RnB it is permanent.

## RnB Changes
- Weather abilities set weather permanently. Sand Stream's sandstorm never ends, making all sandstorm-related effects (chip damage, Rock SpDef boost, Sand Rush/Force/Veil) constant for the remainder of the battle.

## AI Notes
None documented.
</Element>

<Element name="Overgrow">
## Description
When the holder's HP is at or below 1/3, Grass-type moves deal 1.5x damage.

## Mechanics
- `onModifyAtk` and `onModifySpA` (both priority 5): if move is Grass-type and `attacker.hp <= attacker.maxhp / 3`, applies `this.chainModify(1.5)`.
- Boosts both Physical and Special Grass moves.
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`gen789.ts`): `atMods.push(6144)` (1.5x) when attacker has Overgrow, `curHP() <= maxHP() / 3`, and move is Grass type.

## Edge Cases
- The HP threshold is exactly 1/3 — if HP is exactly 1/3 of max HP, the boost applies.
- Applies regardless of weather or terrain; does not stack with Grassy Terrain's boost (separate modifier).
- Does not grant STAB; STAB and Overgrow are separate multipliers.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Clear Body">
## Description
Prevents all of the holder's stats from being lowered by external sources. Functionally identical to White Smoke.

## Mechanics
- `onTryBoost`: if the source is different from the target, removes any negative stat changes from the boost object (`delete boost[i]` for all `boost[i] < 0`). If any negatives were found and the effect is not a secondary or Octolock, displays a fail message.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- In the calculator (`util.ts`): listed alongside White Smoke, Hyper Cutter, and Full Metal Body as a blocker of Intimidate's Attack drop in `checkIntimidate`.

## Edge Cases
- Blocks all external stat drops, not just Attack.
- Octolock is exempted from the fail message but stat drops are still blocked.
- Secondary effects that lower stats are blocked silently — no fail message shown.
- Mold Breaker bypasses Clear Body.
- Does not prevent self-induced stat drops.

## RnB Changes
None documented.

## AI Notes
- Speed-reduction moves and Attack/SpAtk reduction moves score +5 (instead of +6) against targets with Contrary, Clear Body, or White Smoke.
</Element>

<Element name="Poison Point">
## Description
When the holder is hit by a contact move, there is a 30% chance to inflict regular poison on the attacker.

## Mechanics
- `onDamagingHit`: if the move makes contact (`checkMoveMakesContact`), rolls a 30% chance (`randomChance(3, 10)`) to call `source.trySetStatus('psn', target)`.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.

## Edge Cases
- Only triggers on contact moves; non-contact moves do not risk poisoning the attacker.
- Long Reach and Protective Pads on the attacker prevent the contact classification, blocking the trigger.
- The attacker must be susceptible to poison — Poison- and Steel-type Pokémon, and those with Immunity or similar abilities, cannot be poisoned.
- Inflicts regular poison, not badly poisoned (toxic).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Super Luck">
## Description
Raises the holder's critical hit ratio by 1 stage, increasing the chance of scoring a critical hit.

## Mechanics
- `onModifyCritRatio`: adds +1 to the critical hit ratio.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator (crit probability is not modeled in static damage calculations).

## Edge Cases
- In RnB, the base crit rate is 1/16 (stage 0). Super Luck raises it to stage 1, which corresponds to 1/8 chance.
- Stacks with Scope Lens (+1 stage), high-crit moves (+1 stage), and Focus Energy (+2 stages).
- Does not guarantee a crit; only increases the probability.

## RnB Changes
- Base crit rate in RnB is 1/16 (vs. 1/24 in standard Gen 8). Super Luck raises this to 1/8.

## AI Notes
- Focus Energy and Laser Focus score +7 (instead of +6) if the AI has Super Luck or Sniper, holds Scope Lens, or has a move with high crit chance.
</Element>

<Element name="Normalize">
## Description
Converts all of the holder's moves to Normal type and grants them a 1.2x base power boost.

## Mechanics
- `onModifyType` (priority 1): converts the move's type to Normal and sets `move.typeChangerBoosted = this.effect`. Exclusions: Hidden Power, Judgment, Multi-Attack, Natural Gift, Revelation Dance, Struggle, Techno Blast, Terrain Pulse, Weather Ball (and not damaging Z-moves or Tera Blast + terastallized).
- `onBasePower` (priority 23): if `move.typeChangerBoosted === this.effect`, applies `[4915, 4096]` (≈1.2x).
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`gen789.ts`): `isNormalize` is set to true for any move type (not just Normal moves), type becomes Normal, `hasAteAbilityTypeChange = true` → `bpMods.push(4915)` (1.2x).
- Priority 1 means it fires before ATE abilities (priority -1), ensuring Normalize takes precedence.

## Edge Cases
- Unlike ATE abilities, Normalize converts ALL move types to Normal — not only moves that are originally Normal-type.
- Struggle and Hidden Power are excluded from conversion (unique to Normalize's exclusion list).
- Converting moves to Normal can remove type-based resistances or immunities (e.g., Ghost-type Pokémon become immune to Normalize-converted moves).
- The 1.2x boost applies to all converted moves, which may partially compensate for coverage loss.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Beast Boost">
## Description
When the holder KOs an opponent with a move, raises the holder's highest base stat (excluding HP) by 1 stage.

## Mechanics
- `onSourceAfterFaint`: if the KO was caused by a move (`effect.effectType === 'Move'`), calls `source.getBestStat(true, true)` to find the highest raw base stat (unboosted, unmodified, excluding HP), then boosts that stat by `length`.
- `getBestStat(true, true)` checks stats in order: `['atk', 'def', 'spa', 'spd', 'spe']`. In case of a tie, the first stat in that order wins.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.

## Edge Cases
- Uses raw base stats (not current modified stats) to determine which stat to boost — a holder that has boosted its Speed via items/moves will still boost based on its base stat distribution.
- In doubles, KOing multiple opponents in one hit gives `length` = 2, boosting the best stat by +2.
- Only triggers on move-induced KOs; indirect damage KOs do not trigger it.

## RnB Changes
None documented.

## AI Notes
- When a damaging move kills the target, the AI adds +1 to that move's score if it has Moxie, Beast Boost, Chilling Neigh, or Grim Neigh.
</Element>

<Element name="Steelworker">
## Description
Boosts the power of Steel-type moves by 1.5x. Applies to both Physical and Special Steel moves.

## Mechanics
- `onModifyAtk` and `onModifySpA` (both priority 5): if the move is Steel-type, applies `this.chainModify(1.5)`.
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`gen789.ts`): `atMods.push(6144)` (1.5x) when attacker has Steelworker and move is Steel type.

## Edge Cases
- Applies to both Physical and Special Steel moves.
- Does not stack with other multiplicative Steel boosts via the same modifier slot, but stacks normally with STAB, items, etc.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Dark Aura">
## Description
While the holder is on the field, all Dark-type moves used by any Pokémon deal 1.33x (4/3) damage. If Aura Break is also active, this instead becomes 0.75x (3/4).

## Mechanics
- `onStart`: announces the ability (suppressed if ability is being suppressed).
- `onAnyBasePower` (priority 20): if move is Dark-type and not self-targeting and not Status:
  - Tracks `move.auraBooster` to prevent double-boosting if multiple Dark Aura users are on the field (sets to self if not yet set; skips if already set to another instance).
  - If `move.hasAuraBreak`: applies `[3072, 4096]` (0.75x, 3/4).
  - Otherwise: applies `[5448, 4096]` (≈1.33x, 4/3).
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`gen789.ts`): Dark Aura is detected via attacker ability, defender ability, or `field.isDarkAura`. Without Aura Break: `bpMods.push(5448)` (≈1.33x). With Aura Break: `bpMods.push(3072)` (0.75x).

## Edge Cases
- Boosts ALL Dark moves on the field — including moves used against the holder.
- In doubles, only one Dark Aura instance counts even if both active Pokémon have the ability (`move.auraBooster` tracking prevents double-stacking).
- Aura Break (from either side) inverts the effect to 0.75x instead of 1.33x.
- Field flag `isDarkAura` must be set in the calculator if a Dark Aura user is present but is neither the attacker nor defender.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Snow Warning">
## Description
Sets Hail weather when the holder enters the field. In RnB, this Hail is permanent.

## Mechanics
- `onStart`: sets Hail weather (`this.field.setWeather('hail')`) — Gen 8 override; base Showdown (Gen 9) sets Snowscape instead.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator directly, but Hail weather influences Ice Body, Blizzard accuracy, and chip damage.

## Edge Cases
- In Gen 8 (what RnB uses), Hail deals 1/16 chip damage per turn to non-Ice types and gives Blizzard perfect accuracy. It does NOT grant Ice-type Defense boost (that's the Gen 9 Snowscape effect).
- Pokémon with Ice Body, Overcoat, or Ice type are immune to Hail chip damage.

## RnB Changes
- Weather abilities set weather permanently. Snow Warning's Hail never ends, making all Hail-related effects (chip damage, Blizzard accuracy, Ice Body) constant.

## AI Notes
None documented.
</Element>

<Element name="Stance Change">
## Description
Aegislash's signature ability. Changes Aegislash between Shield Forme (defensive) and Blade Forme (offensive) based on the move used.

## Mechanics
- `onModifyMove` (priority 1): fires before move execution. If the holder is Aegislash (not transformed):
  - Using King's Shield: formeChanges to `Aegislash` (Shield Forme).
  - Using a damaging move: formeChanges to `Aegislash-Blade` (Blade Forme).
  - Using another Status move: no forme change.
- `flags: { failroleplay: 1, noreceiver: 1, noentrain: 1, notrace: 1, failskillswap: 1, cantsuppress: 1 }` — cannot be copied, received, entrained, traced, skill swapped, or suppressed by Neutralizing Gas.

## Edge Cases
- The forme change occurs via `onModifyMove`, before damage is dealt, so Aegislash attacks in Blade Forme's stats.
- Transformed Aegislash is exempt from Stance Change.
- Only Aegislash can have this ability (the species check `baseSpecies !== 'Aegislash'` returns early otherwise).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Solid Rock">
## Description
Reduces damage from super-effective moves by 25% (to 0.75x). Can be suppressed by Mold Breaker, unlike Prism Armor.

## Mechanics
- `onSourceModifyDamage`: if `target.getMoveHitData(move).typeMod > 0` (move is super effective), applies `this.chainModify(0.75)`.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- In the calculator (`gen789.ts`): `finalMods.push(3072)` (0.75x) when defender has Solid Rock (also Filter or Prism Armor) and `typeEffectiveness > 1`.

## Edge Cases
- Reduces super-effective damage only — neutral and not-very-effective hits are not affected.
- Mold Breaker bypasses Solid Rock (unlike Prism Armor which has no breakable flag).
- Solid Rock, Filter, and Prism Armor all use the same `finalMods.push(3072)` in the calculator but differ in Mold Breaker interaction.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Psychic Surge">
## Description
Sets Psychic Terrain when the holder enters the field. In RnB, this terrain is permanent.

## Mechanics
- `onStart`: calls `this.field.setTerrain('psychicterrain')`.
- `flags: {}` — not breakable by Mold Breaker.
- Psychic Terrain effects (from the calculator):
  - Boosts Psychic-type moves by 1.5x (`bpMods.push(6144)`) for grounded attackers.
  - Blocks priority moves (`move.priority > 0`) from affecting grounded defenders — the move returns without dealing damage.
- Not referenced directly in the damage calculator for the ability itself; terrain is set on the field.

## Edge Cases
- Psychic Terrain boost only applies to grounded Pokémon (those not airborne via Levitate, Flying type, Magnet Rise, etc.).
- Priority move protection also only applies to grounded targets — airborne Pokémon can still be hit by priority moves in Psychic Terrain.
- In RnB, Psychic Terrain is permanent once set.

## RnB Changes
- Terrain abilities set terrain permanently. Psychic Surge's Psychic Terrain never ends; the 1.5x Psychic boost and priority move protection are constant.

## AI Notes
None documented.
</Element>

<Element name="Shell Armor">
## Description
Prevents the holder from being hit by critical hits. Functionally identical to Battle Armor.

## Mechanics
- `onCriticalHit: false` — sets the critical hit hook to `false`, preventing any critical hit against the holder.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- In the calculator (`gen789.ts`): `isCritical` is set to `false` if `defender.hasAbility('Battle Armor', 'Shell Armor')`.

## Edge Cases
- Mold Breaker can bypass Shell Armor, allowing critical hits to land.
- Regardless of crit ratio or abilities like Merciless or Storm Drain, no critical hit can occur against the holder.

## RnB Changes
None documented.

## AI Notes
- The AI will not use Focus Energy or Laser Focus if the target has Shell Armor or Battle Armor (investing in crit setup is pointless when crits cannot land).
</Element>

<Element name="Flash Fire">
## Description
Grants immunity to Fire-type moves; upon absorbing a Fire move, boosts the holder's own Fire-type moves by 1.5x until switched out.

## Mechanics
- `onTryHit`: if a Fire-type move targets the holder (not self), sets move accuracy to `true` (always hits), tries to add the `flashfire` volatile condition, shows immune if already activated, then returns `null` to negate the move.
- The `flashfire` volatile condition:
  - `noCopy: true` — not passed by Baton Pass.
  - `onModifyAtk`/`onModifySpA` (priority 5): while the holder has this volatile and uses a Fire move, applies `this.chainModify(1.5)` (1.5x).
- `onEnd`: removes the volatile when the ability ends.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- In the calculator (`gen789.ts`):
  - Fire moves targeting a Flash Fire holder return early (absorbed, no damage).
  - `atMods.push(6144)` (1.5x) when attacker has Flash Fire and `abilityOn = true` (volatile activated) and move is Fire type. `abilityOn` must be set manually to represent the activated state.

## Edge Cases
- Mold Breaker bypasses Flash Fire, allowing Fire moves to deal damage (but does not activate the boost).
- If the holder absorbs a Fire move while already activated, it shows an immune message without applying an additional boost.
- The boost is lost if the holder is switched out or the ability is changed.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Storm Drain">
## Description
Draws all Water-type moves in doubles to the holder, grants Water immunity, and raises SpA by 1 when hit by a Water move.

## Mechanics
- `onTryHit`: if a Water-type move targets the holder (not self), attempts `this.boost({ spa: 1 })`. If the boost cannot apply (already at +6), shows an immune message. Returns `null` to negate the move entirely.
- `onAnyRedirectTarget`: in doubles, redirects all single-target Water-type moves to the holder if it's a valid target (not pledge combos). Announces activation if the holder was not the original target.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- In the calculator (`gen789.ts`): Water moves targeting a Storm Drain holder return early (absorbed, no damage).

## Edge Cases
- Mold Breaker bypasses Storm Drain — Water moves deal damage and do not trigger the SpA boost.
- If SpA is already at +6, the move is still absorbed (no damage) but no immune message is shown for the absorption itself; instead the boost fail shows.
- In doubles, redirection applies to moves targeting either ally or foe if Storm Drain can redirect — this includes moves aimed at the holder's own partner.
- Pledge-combo moves are excluded from redirection.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Moody">
## Description
At the end of each turn, randomly raises one of the holder's stats by +2 and randomly lowers a different stat by -1.

## Mechanics
- `onResidual` (order 28, sub-order 2): each turn:
  1. Collects all stats not at +6 (in base Showdown Gen 8, excludes accuracy and evasion). Randomly selects one and boosts it by +2.
  2. Collects all stats not at -6 that aren't the stat just raised (in base Showdown Gen 8, also excludes accuracy and evasion). Randomly selects one and lowers it by -1.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.

## Edge Cases
- If all eligible stats for raising are at +6, no stat is raised.
- If all eligible stats for lowering are at -6 (or only the raised stat is eligible), no stat is lowered.
- The raised and lowered stats are always different.

## RnB Changes
- In standard Gen 8, Moody cannot raise or lower Accuracy or Evasion. In RnB, Moody "can still raise Accuracy and Evasion," reverting to pre-Gen-8 behavior where accuracy and evasion are included in the stat pool.

## AI Notes
None documented.
</Element>

<Element name="Strong Jaw">
## Description
Boosts the power of biting moves by 1.5x.

## Mechanics
- `onBasePower` (priority 19): if the move has the `bite` flag, applies `this.chainModify(1.5)`.
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`gen789.ts`): `bpMods.push(6144)` (1.5x) when attacker has Strong Jaw and move has `bite` flag.
- Bite-flagged moves include: Bite, Crunch, Fire Fang, Ice Fang, Thunder Fang, Poison Fang, Hyper Fang, Super Fang, Fishious Rend, Jaw Lock, among others.

## Edge Cases
- The boost applies to all bite moves regardless of type or category.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Water Compaction">
## Description
When the holder is hit by a Water-type move, raises its Defense by 2 stages.

## Mechanics
- `onDamagingHit`: if the move is Water-type, boosts the holder's Defense by `{ def: 2 }`.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.

## Edge Cases
- Triggers on any Water-type damaging hit, regardless of whether the holder is immune to Water damage via type or other abilities.
- The Defense boost applies even if the holder faints from the hit (though it would be pointless at that stage).
- Does not grant Water immunity — the holder still takes full Water damage.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Swarm">
## Description
When the holder's HP is at or below 1/3, Bug-type moves deal 1.5x damage.

## Mechanics
- `onModifyAtk` and `onModifySpA` (both priority 5): if move is Bug-type and `attacker.hp <= attacker.maxhp / 3`, applies `this.chainModify(1.5)`.
- Boosts both Physical and Special Bug moves.
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`gen789.ts`): `atMods.push(6144)` (1.5x) when attacker has Swarm, `curHP() <= maxHP() / 3`, and move is Bug type.

## Edge Cases
- The HP threshold is exactly 1/3 — if HP is exactly 1/3 of max HP, the boost applies.
- Applies regardless of terrain or weather.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Victory Star">
## Description
Boosts the accuracy of the holder and its allies by approximately 10% (1.1x).

## Mechanics
- `onAnyModifyAccuracy` (priority -1): if the move's user is an ally of (or is) the holder, and accuracy is a numeric value (not `true`/always-hit), applies `[4506, 4096]` (≈1.1x) to accuracy.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator (accuracy not modeled).

## Edge Cases
- Applies to the holder's own moves as well as ally moves in doubles.
- Does not affect moves with `accuracy: true` (guaranteed-hit moves like Aerial Ace, Teleport, etc.).
- The 10% accuracy boost can push high-accuracy moves past 100%, giving additional buffer against evasion.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Surge Surfer">
## Description
Doubles the holder's Speed when Electric Terrain is active.

## Mechanics
- `onModifySpe`: if `this.field.isTerrain('electricterrain')`, applies `this.chainModify(2)` (2x Speed).
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`util.ts`): `speedMods.push(8192)` (2x) when holder has Surge Surfer and terrain is Electric.

## Edge Cases
- Only activates in Electric Terrain — no benefit in other terrains or without terrain.
- Grounded status does not affect Surge Surfer's activation (Speed boost applies regardless of whether the holder is grounded).

## RnB Changes
- Terrain abilities set terrain permanently in RnB. If an Electric Surge user is present, Surge Surfer's 2x Speed boost is constant for the duration of the battle.

## AI Notes
None documented.
</Element>

<Element name="Unaware">
## Description
Ignores opponents' stat boosts when taking or dealing damage: when attacking, ignores the target's defensive boosts and evasion; when defending, ignores the attacker's offensive boosts and accuracy.

## Mechanics
- `onAnyModifyBoost`: zeroes relevant boosts in the current damage calculation:
  - When the holder is attacking: zeroes the target's Def, SpDef, and Evasion boosts.
  - When the holder is defending: zeroes the attacker's Atk, SpA, and Accuracy boosts.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- In the calculator (`gen789.ts`):
  - `defender.hasAbility('Unaware')` → use `attackSource.rawStats[attackStat]` (ignores attacker's offensive boosts).
  - `attacker.hasAbility('Unaware')` → use `defender.rawStats[defenseStat]` (ignores defender's defensive boosts).
- In the calculator (`util.ts`): if attacker has Unaware, Stamina's Def boost is skipped; Weak Armor's Def drop is skipped (but Weak Armor's Speed boost still applies); `move.dropsStats` stat drops on the attacker are skipped.

## Edge Cases
- Mold Breaker bypasses Unaware.
- Unaware does NOT ignore all boosts — only relevant ones: defensive boosts/evasion (when attacking) and offensive boosts/accuracy (when defending).
- Weak Armor interaction: Unaware ignores the Def drop from Weak Armor, but the Speed boost from Weak Armor still applies (the Speed calculation is outside the Unaware check).

## RnB Changes
None documented.

## AI Notes
- If the target has Unaware, the AI scores all setup moves at -20 (will not set up), EXCEPT for: Power-up Punch, Swords Dance, Howl (and other moves with 100% stat-raising effects that fall into a special category such as Bulk Up, Calm Mind, Dragon Dance, Shell Smash, etc.).
</Element>

<Element name="Defiant">
## Description
When any of the holder's stats are lowered by an opponent, raises the holder's Attack by 2 stages.

## Mechanics
- `onAfterEachBoost`: if the source of the stat change is different from the holder AND is not an ally, checks if any boost in the change was negative. If so, boosts the holder's Attack by +2 via `this.boost({ atk: 2 }, target, target)`.
- `flags: {}` — not breakable by Mold Breaker.
- In Gen 8: ally-sourced drops do NOT trigger Defiant. A special hint is shown for Sticky Web applied via Court Change (treated as self-inflicted, not foe-inflicted).
- In the calculator (`util.ts`): against Intimidate, Defiant results in a net +1 Attack (`target.boosts.atk + 1`), reflecting the Intimidate -1 followed by Defiant +2.

## Edge Cases
- Defiant triggers once per stat-drop event, not once per stat dropped. If Intimidate lowers Attack by -1 and Sticky Web lowers Speed by -1 in the same trigger, each triggers a separate +2 Attack boost.
- In doubles, ally-sourced stat drops (e.g., from Icy Wind, Snarl used by ally) do NOT trigger Defiant — only opponent-sourced drops trigger it.
- Applies to any stat being lowered, not just Attack.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Symbiosis">
## Description
When an ally consumes its held item, the holder gives its own item to that ally. Only relevant in doubles.

## Mechanics
- `onAllyAfterUseItem`: fires when an ally uses/consumes its item. If the holder has an item and the ally is not switching out, the holder calls `takeItem()` to remove its own item, then attempts to give it to the ally via `setItem()`. If the transfer fails (the ally can't receive it), the item is returned to the holder.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.

## Edge Cases
- Has no effect in singles.
- Triggers on any consumed item (berries, gems, focus sash, etc.), not just berries.
- If the ally is switching out on the same turn, the transfer does not occur (the `switchFlag` check).
- The holder loses its item permanently — the transferred item is the holder's item, not a copy.

## RnB Changes
- Consumed items are not restored in RnB. This doesn't directly affect Symbiosis's transfer mechanic, but means the item the ally consumed (triggering Symbiosis) is gone for good, and the item Symbiosis transfers will similarly not be restored if later consumed.

## AI Notes
None documented.
</Element>

<Element name="Magician">
## Description
When the holder uses a damaging move, it steals the held item of one of its targets (if the holder has no item).

## Mechanics
- `onAfterMoveSecondarySelf`: after the holder uses a move, checks that: the holder has no item, is not switching, has hit targets, has no gem volatile, and the move is not Fling or a Status move. If conditions are met, sorts hit targets by speed and steals the item from the first target that has an item.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.

## Edge Cases
- Only steals if the holder is itemless at the time — if the holder already has an item, Magician does not activate.
- In doubles, if multiple targets were hit, the item is stolen from the fastest target with an item.
- Items that cannot be taken (e.g., Z-Crystals, certain Mega Stones, items with `undroppable` flags) cannot be stolen.
- The stolen item is immediately active on the holder.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Friend Guard">
## Description
Reduces damage dealt to ally Pokémon (not the holder itself) by 25%. Only relevant in doubles.

## Mechanics
- `onAnyModifyDamage`: if the target is NOT the holder but IS an ally of the holder, applies `this.chainModify(0.75)` (0.75x damage reduction).
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze on the attacker targeting the protected ally.
- In the calculator (`gen789.ts`): `finalMods.push(3072)` (0.75x) when `field.defenderSide.isFriendGuard` is set. This field flag must be manually enabled.

## Edge Cases
- The holder itself does not benefit from Friend Guard — only allies do.
- In singles, Friend Guard has no effect (no allies).
- Mold Breaker bypasses Friend Guard when attacking the protected ally.
- Stacks multiplicatively with other damage-reducing effects (e.g., defensive Reflect/Light Screen, Wide Guard).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Mummy">
## Description
When the holder is hit by a contact move, the attacker's ability is replaced with Mummy.

## Mechanics
- `onDamagingHit`: checks if the attacking move makes contact with the holder. If the attacker's ability does not have the `cantsuppress` flag and is not already Mummy, calls `source.setAbility('mummy', target)` to replace the attacker's ability.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.

## Edge Cases
- Abilities with the `cantsuppress` flag (e.g., Neutralizing Gas, As One, Battle Bond, Multitype) cannot be replaced by Mummy.
- If the attacker already has Mummy, no change occurs.
- Long Reach and Protective Pads prevent the contact classification on the attacker's move, blocking Mummy's spread.
- The Mummy-ified ability is lost when the affected Pokémon switches out.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Shields Down">
## Description
Minior's signature ability. While above 50% HP (Meteor Form), grants immunity to all status conditions. Below 50% HP, Minior transforms to its colored Core Form and loses the immunity.

## Mechanics
- `onStart` / `onResidual` (order 29): checks HP vs 50% threshold. If HP > 50% and not in Meteor forme, changes to Meteor. If HP ≤ 50% and in Meteor forme, changes to the colored core forme.
- `onSetStatus`: if Minior is in Meteor forme (`species.id === 'miniormeteor'`), blocks all status conditions.
- `onTryAddVolatile`: if Minior is in Meteor forme, blocks Yawn.
- `flags: { failroleplay: 1, noreceiver: 1, noentrain: 1, notrace: 1, failskillswap: 1, cantsuppress: 1 }` — cannot be copied, received, entrained, traced, skill swapped, or suppressed by Neutralizing Gas.
- Not referenced in the damage calculator.

## Edge Cases
- Forme changes are checked each residual phase — if HP is healed back above 50% (e.g., via recovery move), Minior returns to Meteor forme on the next residual.
- Status immunity only applies in Meteor forme; Core forme has no special status immunity.
- Transformed Pokémon (via Transform/Imposter) cannot trigger the forme change logic.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Shed Skin">
## Description
At the end of each turn, has a 33% chance to cure the holder's status condition.

## Mechanics
- `onResidual` (order 5, sub-order 3): if the holder is alive and has any status condition, rolls a 33% chance (`randomChance(33, 100)`) and calls `cureStatus()` if successful.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.

## Edge Cases
- Cures all status conditions (burn, freeze, paralysis, poison, toxic, sleep).
- Rolls independently each turn — the holder may not self-cure for many consecutive turns despite the 33% rate.

## RnB Changes
None documented.

## AI Notes
- Rest scores +8 (instead of +7) when the AI decides it should recover AND has Shed Skin (or Early Bird, a sleep-curing held item, Sleep Talk/Snore, or Hydration in rain). Scores +5 if the AI doesn't think it needs recovery.
</Element>

<Element name="Huge Power">
## Description
Doubles the holder's Attack stat, effectively doubling physical damage output. Identical in effect to Pure Power.

## Mechanics
- `onModifyAtk` (priority 5): multiplies Attack by 2x via `this.chainModify(2)`.
- `flags: {}` — not breakable; Mold Breaker cannot suppress Huge Power.
- In the calculator (`gen789.ts`): `atMods.push(8192)` (2x) when attacker has Huge Power or Pure Power and the move is Physical.

## Edge Cases
- Applies only to physical moves; Special moves are unaffected.
- Not suppressed by Mold Breaker (no `breakable` flag).

## RnB Changes
None documented.

## AI Notes
- Role Play: scores +9 if the AI's partner has Huge Power, Pure Power, Protean, or Tough Claws and the AI itself does not have one of those abilities. Scores -20 if the AI already has one of those abilities.
</Element>

<Element name="Intimidate">
## Description
Upon entering the field, lowers the Attack of all adjacent opponents by 1 stage. Blocked by Substitute and several abilities.

## Mechanics
- `onStart`: for each adjacent foe, if the foe has a Substitute, shows immune (no effect). Otherwise calls `this.boost({ atk: -1 }, target, pokemon, null, true)`.
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`util.ts`, `checkIntimidate`):
  - Blocked entirely by: Clear Body, White Smoke, Hyper Cutter, Full Metal Body; in Gen 8+: Inner Focus, Own Tempo, Oblivious, Scrappy; Clear Amulet item.
  - If not blocked: Contrary/Defiant/Guard Dog → +1 Attack; Simple → -2 Attack; standard → -1 Attack.
  - Competitive holders also gain +2 SpA when Intimidated.

## Edge Cases
- Substitute blocks Intimidate — foes behind a Substitute are immune.
- In doubles, Intimidate lowers Attack on both adjacent opponents simultaneously.
- Rattled holders gain +1 Speed when Intimidated.
- The Attack drop is applied on switch-in, before the Intimidate holder moves.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Marvel Scale">
## Description
When the holder has a status condition, its Defense is boosted by 1.5x against Physical moves.

## Mechanics
- `onModifyDef` (priority 6): if the holder has any status condition, applies `this.chainModify(1.5)` to Defense.
- `flags: { breakable: 1 }` — can be suppressed by Mold Breaker, Teravolt, Turboblaze.
- In the calculator (`gen789.ts`): `dfMods.push(6144)` (1.5x) when defender has Marvel Scale, has a status condition, and the move is Physical.

## Edge Cases
- Only applies to Physical moves (Defense stat); Special moves use SpDef and are not affected.
- Any status condition triggers it: burn, paralysis, poison, toxic, sleep, freeze.
- Mold Breaker bypasses Marvel Scale.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Gooey">
## Description
When the holder is hit by a contact move, the attacker's Speed is lowered by 1 stage. Functionally identical to Tangling Hair.

## Mechanics
- `onDamagingHit`: if the move makes contact with the holder (`checkMoveMakesContact` with `obvious = true`), announces the ability and applies `this.boost({ spe: -1 }, source, target, null, true)` to the attacker.
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`util.ts`): handled identically to Tangling Hair — Gyro Ball/Electro Ball with Parental Bond multi-hit apply the Speed drop per hit.

## Edge Cases
- Requires the move to make contact; non-contact moves do not trigger the Speed drop.
- Long Reach and Protective Pads on the attacker prevent the contact classification.
- Mold Breaker does not suppress Gooey (no breakable flag).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Rain Dish">
## Description
Restores 1/16 of the holder's max HP each turn while rain is active.

## Mechanics
- `onWeather`: if the weather is Rain Dance (`raindance`) or Primordial Sea (`primordialsea`), heals `target.baseMaxhp / 16`.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.

## Edge Cases
- Only activates in rain — no healing in other weather conditions.
- The effective weather check (`target.effectiveWeather()`) ensures Cloud Nine / Air Lock suppresses the heal.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Stamina">
## Description
When the holder is hit by a damaging move, raises its Defense by 1 stage.

## Mechanics
- `onDamagingHit`: boosts the holder's Defense by `{ def: 1 }`.
- `flags: {}` — not breakable by Mold Breaker.
- In the calculator (`util.ts`): after a damaging hit, `defender.boosts.def += 1` and the stat is recalculated. If the attacker has Unaware, this boost is skipped (not applied to subsequent damage calculations in the same exchange).

## Edge Cases
- Triggers on every damaging hit, including multi-hit moves (each hit triggers a separate +1 Def).
- Not suppressed by Mold Breaker — the Defense boost occurs even when hit by Mold Breaker users.
- Unaware on the attacker ignores the Stamina boost for damage calculation purposes.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Suction Cups">
## Description
Prevents the holder from being forcibly switched out by moves such as Whirlwind, Roar, Dragon Tail, and Circle Throw.

## Mechanics
- `onDragOutPriority: 1` / `onDragOut`: returns `null`, blocking the forced switch-out. Announces "Suction Cups" via `-activate` message when triggered.
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- Not referenced in the damage calculator (gen789.ts or util.ts); purely a switch-prevention effect.

## Edge Cases
- Only blocks *forced* switches (drag moves). Voluntary switches and self-triggered U-turn/Volt Switch are unaffected.
- Mold Breaker users can bypass Suction Cups and force the switch normally.
- The note on line 15 of the gen8 mod abilities.ts ("ex. Light Metal, Suction Cups") is a rating-tier comment only; there is no mechanic override for Suction Cups in the Gen 8 mod.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Hustle">
## Description
Raises the holder's Attack by 1.5× but reduces the accuracy of its Physical moves to 80% (×0.8).

## Mechanics
- **Showdown** (`onModifyAtkPriority: 5` / `onModifyAtk`): multiplies the Attack stat by 1.5× before other modifiers. High priority (5) ensures it runs before most other Atk modifiers.
- **Showdown** (`onSourceModifyAccuracyPriority: -1` / `onSourceModifyAccuracy`): for Physical moves where accuracy is a number (not `true`), applies [3277, 4096] ≈ 0.8× accuracy chain-modifier.
- **Calculator (gen789.ts)**: Hustle is applied *directly* to the raw attack value before chaining with other atMods — `attack = pokeRound((attack * 3) / 2)` — only for `move.category === 'Physical'`. A comment explicitly notes "unlike all other attack modifiers, Hustle gets applied directly."
- No gen8 mod override.
- `flags: {}` — not breakable by Mold Breaker.

## Edge Cases
- The accuracy penalty only applies to Physical moves with numeric accuracy. Moves with `true` accuracy (never-miss moves) are not penalized.
- In the calculator, the 1.5× is applied after boost resolution but before the atMods chain — the direct multiplication means it interacts differently with rounding vs. a standard chained modifier.
- The accuracy reduction is not modeled in the calculator (accuracy is not simulated).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Leaf Guard">
## Description
In harsh sunlight (sunny day / desolate land), prevents the holder from gaining a non-volatile status condition and blocks Yawn.

## Mechanics
- `onSetStatus`: if `effectiveWeather()` is `'sunnyday'` or `'desolateland'`, blocks status application and emits `-immune` if the source was a status move.
- `onTryAddVolatile`: if the volatile being added is `'yawn'` and the weather is sunny, returns `null` (blocks it) and emits `-immune`.
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- Not referenced in the damage calculator.
- The gen8 mod entry only adjusts the rating; no mechanic change.

## Edge Cases
- Uses `effectiveWeather()` — Cloud Nine / Air Lock suppresses sun and therefore disables Leaf Guard entirely.
- In RnB, sun from Drought is permanent, so Leaf Guard holders with a Drought teammate effectively have permanent status immunity.
- Does not cure existing status conditions; only blocks new ones while the weather is active.
- Blocks Yawn's volatile (sleep countdown) but does not affect an already-active sleep or other existing status.

## RnB Changes
None documented. Weather permanence (from Drought) means sun is reliable, making Leaf Guard more consistently useful in RnB.

## AI Notes
None documented.
</Element>

<Element name="Speed Boost">
## Description
At the end of each turn (after the first turn of being active), raises the holder's Speed by 1 stage.

## Mechanics
- `onResidualOrder: 28`, `onResidualSubOrder: 2` / `onResidual`: if `pokemon.activeTurns` is truthy (i.e., not the very first turn the Pokémon was active this switch-in), calls `this.boost({ spe: 1 })`.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator (gen789.ts or util.ts).
- Gen8 mod entry is rating-only; no mechanic difference.

## Edge Cases
- Does not trigger on the turn the Pokémon switches in (`activeTurns` is falsy/0 that turn).
- Accumulates each subsequent turn without a cap beyond the normal +6 stage ceiling.
- In RnB, Speed Boost interacts normally with the -75% Speed paralysis modifier; the stage boosts still apply but on top of the quartered base.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Electric Surge">
## Description
On entry, sets Electric Terrain, which lasts for 5 turns (permanent in RnB). While active, Electric Terrain boosts Electric-type moves used by grounded Pokémon by 1.5× and prevents grounded Pokémon from falling asleep.

## Mechanics
- `onStart`: calls `this.field.setTerrain('electricterrain')`.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts)**: When `field.hasTerrain('Electric')` and the attacker is grounded and uses an Electric-type move, `bpMods.push(6144)` (6144/4096 = 1.5×). This is applied in the field-effects block alongside Grassy and Psychic terrain boosts.
- The gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- The 1.5× boost only applies when the attacker is grounded (`isGrounded(attacker, field)`). Airborne attackers (Levitate, Air Balloon, Flying-type, etc.) do not benefit.
- Electric Terrain prevents sleep for grounded Pokémon — grounded Pokémon already asleep are not cured; only new sleep is blocked.
- In RnB, Terrain set by terrain abilities is permanent (Mechanic Changes.txt line 29). Electric Surge therefore sets *permanent* Electric Terrain.
- Terrain is not removed by Defog in RnB (Mechanic Changes.txt line 31); only Steel Roller can remove it.
- Surge Surfer doubles Speed in Electric Terrain (modeled separately in util.ts: `speedMods.push(8192)`).

## RnB Changes
- Electric Terrain set by Electric Surge is permanent (does not expire after turns).
- Terrain damage boost is 1.5× (not 1.3×) — RnB explicitly changed Electric/Grass/Psychic terrain to 50% boost.

## AI Notes
None documented.
</Element>

<Element name="Aftermath">
## Description
When the holder faints from a contact move, deals 1/4 of the attacker's max HP as damage.

## Mechanics
- `onDamagingHitOrder: 1` / `onDamagingHit`: if `!target.hp` (holder fainted) and the move made contact (`checkMoveMakesContact`), deals `source.baseMaxhp / 4` damage to the attacker.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator (gen789.ts or util.ts).
- **Damp interaction**: Damp's `onAnyDamage` returns `false` for Aftermath damage, completely blocking it.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Only triggers on contact moves. Non-contact moves (e.g., most Special attacks) do not activate Aftermath even if they KO the holder.
- Uses `baseMaxhp` (not current HP) for the damage calculation — always 1/4 of the attacker's max HP.
- Damp on any Pokémon on the field (any side) fully suppresses the Aftermath damage.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Lightning Rod">
## Description
Draws all single-target Electric-type moves to the holder, granting immunity and raising Special Attack by 1 stage when hit.

## Mechanics
- `onTryHit`: when an Electric-type move targets anyone other than the holder itself, boosts SpA by 1 (`this.boost({ spa: 1 })`); if the boost fails (already at +6), shows `-immune`. Returns `null` (move does no damage).
- `onAnyRedirectTarget`: redirects single-target or adjacent-foe Electric moves toward the holder if it's a valid target; announces `-activate` if redirection changes the target.
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- **Calculator (gen789.ts)**: when `defender.hasAbility('Lightning Rod', 'Motor Drive', 'Volt Absorb')` and the move is Electric-type, the calc returns an empty result (0 damage), modeling the immunity.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Redirection only applies to moves with appropriate target types (`randomNormal`, `adjacentFoe`); spread moves and multi-target moves are not redirected.
- `pledgecombo` moves are excluded from redirection.
- The SpA boost triggers even if the redirected Electric move was not originally aimed at the holder.
- Suppressed by Mold Breaker: Mold Breaker users bypass the immunity and do not trigger the SpA boost or redirection.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Ripen">
## Description
Doubles the effect of Berries: healing berries restore twice as much HP, stat-boosting berries give twice the boosts, and resistance berries halve damage twice (0.25× instead of 0.5×).

## Mechanics
- `onTryHeal`: if the healing source is a berry (`effect.isBerry`), applies `chainModify(2)` to double the heal. Berry Juice and Leftovers trigger the `-activate` announcement but are NOT doubled by this hook.
- `onChangeBoost`: if the boost source is a berry, multiplies all boost values by 2 (doubling stat-boosting berry effects).
- `onEatItem`: sets `abilityState.berryWeaken = true` if the berry eaten is a resistance-weakening berry (Occa, Passho, Wacan, etc.).
- `onSourceModifyDamage` (priority -1): if `berryWeaken` is true, applies `chainModify(0.5)` to the incoming move's damage — this stacks with the berry's own halving to give 0.25× total.
- `onTryEatItem` (priority -1): announces `-activate` whenever any item is eaten.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts)**: for resistance berries (`getBerryResistType`), normally pushes `finalMods.push(2048)` (0.5×), but if `defender.hasAbility('Ripen')` pushes `finalMods.push(1024)` (0.25×) instead, modeling the doubled resistance.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- The 2× healing only applies to berries. Berry Juice and Leftovers are explicitly mentioned in the code but only receive a cosmetic `-activate` message, not a doubled heal.
- Resistance berry + Ripen: damage is 0.25× (two halvings applied), modeled in the calc as a `finalMods` adjustment.
- In RnB, consumed items are not restored (Mechanic Changes.txt line 33). Ripen doubles the one-time berry effect but cannot recover the berry afterward.
- Stat-boost doubling applies to all boost IDs in the berry's boost object, including negative boosts (e.g., a berry that lowers one stat to raise another would have both effects doubled).

## RnB Changes
None documented. Note: since items are not restored in RnB, Ripen's value is limited to a single amplified use per berry.

## AI Notes
None documented.
</Element>

<Element name="Shadow Shield">
## Description
While the holder is at full HP, all incoming damage is halved (identical to Multiscale but exclusive to Lunala).

## Mechanics
- `onSourceModifyDamage`: if `target.hp >= target.maxhp`, applies `chainModify(0.5)` (halves damage).
- `flags: {}` — NOT breakable by Mold Breaker, Teravolt, or Turboblaze.
- **Calculator (gen789.ts)**: `defender.hasAbility('Multiscale', 'Shadow Shield')` triggers `finalMods.push(2048)` (0.5×) when `defender.curHP() === defender.maxHP()`, and the defender side has no Stealth Rock and no effective Spikes. Also excluded if the attacker has `'Parental Bond (Child)'`.
- `defenderIgnoresAbility` list in the calc includes Shadow Shield, meaning even if `attackerIgnoresAbility` (Mold Breaker etc.) is true, the defender's ability is NOT cleared — ensuring Shadow Shield always applies regardless of attacker ability.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Not breakable by Mold Breaker (unlike most abilities that halve damage). The `defenderIgnoresAbility` flag ensures this in the calculator.
- The calc also gates activation on Stealth Rock/Spikes presence: if the defender side has SR (or Spikes and defender isn't Flying), the calc assumes the Pokémon is not at full HP and doesn't apply the modifier.
- Parental Bond's child hit does not trigger the halving (Parental Bond Child is explicitly excluded).
- Moves that ignore ability (Moongeist Beam, Photon Geyser, Sunsteel Strike, etc.) do bypass Shadow Shield despite the `defenderIgnoresAbility` protection, because `moveIgnoresAbility` is handled separately.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Iron Fist">
## Description
Boosts the power of punching moves by 1.2× (approximately).

## Mechanics
- `onBasePowerPriority: 23` / `onBasePower`: if `move.flags['punch']` is set, applies `chainModify([4915, 4096])` ≈ 1.2× boost.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts)**: `bpMods.push(4915)` when `attacker.hasAbility('Iron Fist') && move.flags.punch`. Grouped in the same block as Reckless (both use 4915).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Applies to any move with the `punch` flag: Fire Punch, Ice Punch, Thunder Punch, Mach Punch, Bullet Punch, Shadow Punch, Drain Punch, Focus Punch, Meteor Mash, Power-Up Punch, etc.
- Punching Glove also boosts punching moves (`bpMods.push(4506)` ≈ 1.1×) — Iron Fist and Punching Glove stack multiplicatively.
- Does not stack with itself; the ability's flag check is a single `move.flags.punch` condition.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Iron Barbs">
## Description
When the holder is hit by a contact move, damages the attacker for 1/8 of the attacker's max HP.

## Mechanics
- `onDamagingHitOrder: 1` / `onDamagingHit`: if `checkMoveMakesContact` is true, deals `source.baseMaxhp / 8` damage to the attacker.
- `flags: {}` — not breakable by Mold Breaker.
- Functionally identical to Rough Skin; Iron Barbs is the Ferrothorn-family version.
- Not referenced in the damage calculator (gen789.ts or util.ts) as a damage modifier.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Only triggers on contact moves. Non-contact moves (most Special attacks, moves with Long Reach, Protective Pads item) do not trigger Iron Barbs.
- Uses `baseMaxhp` of the attacker — always 1/8 of their max HP, independent of current HP.
- Triggers on every hit of a multi-hit contact move.
- Magic Guard on the attacker prevents the Iron Barbs damage.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Fur Coat">
## Description
Halves damage taken from Physical moves by doubling the holder's effective Defense stat.

## Mechanics
- `onModifyDefPriority: 6` / `onModifyDef`: applies `chainModify(2)` to the Defense stat, doubling it.
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- **Calculator (gen789.ts)**: when `defender.hasAbility('Fur Coat') && hitsPhysical`, pushes `dfMods.push(8192)` (8192/4096 = 2×), applied in the `dfMods` block alongside Grass Pelt and Fluffy.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Doubles Defense, not directly halving damage — so stat stages and other Defense modifiers still apply on top of the doubled base.
- Affected by Mold Breaker: Mold Breaker users ignore Fur Coat entirely.
- Only applies to Physical moves (`hitsPhysical` in the calc); Special and status moves are not affected.
- Fluffy is separately handled in the calc (same `dfMods` block); they don't stack with each other since a Pokémon can only have one ability.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Mold Breaker">
## Description
On entry, announces itself. While active, the holder's moves ignore the target's ability if that ability would interfere with the move (any ability with `breakable: 1`, plus select others).

## Mechanics
- `onStart`: announces via `-ability` message.
- `onModifyMove`: sets `move.ignoreAbility = true` on every move used by the holder.
- `flags: {}` — not itself suppressed by another Mold Breaker.
- **Calculator (gen789.ts)**: `attackerIgnoresAbility = attacker.hasAbility('Mold Breaker', 'Teravolt', 'Turboblaze')`. When true and the defender does NOT have a `defenderIgnoresAbility` ability (Full Metal Body, Neutralizing Gas, Prism Armor, Shadow Shield) and does NOT have Poison Heal, the calc sets `defender.ability = ''`, nullifying any defensive ability effects in the damage calculation.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Abilities with `breakable: 1` in Showdown (approximately 83 abilities) are suppressed. Abilities with `flags: {}` are generally NOT suppressed.
- Full Metal Body, Neutralizing Gas, Prism Armor, and Shadow Shield (`defenderIgnoresAbility`) cannot be suppressed — those Pokémon always keep their ability active.
- Poison Heal is also protected in the calc (explicitly excluded: `!defender.hasAbility('Poison Heal')`).
- Mold Breaker does NOT suppress abilities on the attacker's own side — only the target's defensive abilities are ignored.
- `move.ignoreAbility = true` is set on the move object; this is also how Moongeist Beam, Photon Geyser, and Sunsteel Strike bypass abilities without the user having Mold Breaker.
- Turboblaze and Teravolt are mechanically identical to Mold Breaker in the calc.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Comatose">
## Description
The holder is treated as permanently asleep but can still act normally. It cannot receive any status condition.

## Mechanics
- `onStart`: announces `-ability` message on entry.
- `onSetStatus`: blocks all status conditions entirely, showing `-immune` for move-sourced statuses. Returns `false` to prevent the status.
- The sleep state is implemented externally in sleep-checking effects; Comatose Pokémon are treated as `slp` by moves and abilities that check for sleep.
- `flags: { failroleplay: 1, noreceiver: 1, noentrain: 1, notrace: 1, failskillswap: 1, cantsuppress: 1 }` — cannot be copied by Role Play, Trace, Receiver, or Entrainment; cannot be Skill Swapped; cannot be suppressed.
- **Calculator (gen789.ts)**:
  - Dream Eater: succeeds against Comatose users (`defender.hasAbility('Comatose')`).
  - Hex: deals double base power if `defender.status || defender.hasAbility('Comatose')` (line 664).
  - Wake-Up Slap: deals double base power if `defender.hasStatus('slp') || defender.hasAbility('Comatose')` (line 694).
  - Bad Dreams: damages Comatose users each residual turn (1/8 max HP per turn).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Comatose Pokémon cannot be put to sleep, burned, paralyzed, frozen, or poisoned.
- They ARE treated as asleep by moves that check sleep: Dream Eater hits them, Hex doubles, Wake-Up Slap doubles, Bad Dreams damages them, Sleep Talk would allow them to use random moves.
- Cannot be Skill Swapped, Entrailed, Traced, or Role Played — meaning opponents can't gain Comatose.
- `cantsuppress: 1` means Neutralizing Gas cannot suppress it.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Berserk">
## Description
When the holder's HP drops to or below 50% from a hit, raises its Special Attack by 1 stage. Also prevents healing berries from activating mid-multi-hit move.

## Mechanics
- `onDamage`: sets `checkedBerserk = false` (deferring the berry check) if the damage source is a move that is not multi-hit and not a Sheer Force-boosted move on a Sheer Force user. Otherwise, `checkedBerserk = true` (berry activation is allowed).
- `onTryEatItem`: for healing berries (Sitrus, Oran, Berry Juice, Wiki, Iapapa, Figy, Mago, Aguav, Enigma), returns `checkedBerserk` — if false (in the middle of a non-multi-hit move hit), the berry is suppressed until after the move resolves.
- `onAfterMoveSecondary`: resets `checkedBerserk = true`. If a hit caused HP to cross from above 50% to at or below 50% (evaluating `target.hp + damage > target.maxhp / 2`), boosts SpA by +1. For multi-hit moves, uses `move.totalDamage`.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator (no SpA boost applied in calc for Berserk specifically).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Only triggers once per switch-in: the HP threshold check is `target.hp <= target.maxhp / 2 && target.hp + damage > target.maxhp / 2` — after the HP drops below 50%, subsequent hits won't trigger again unless the Pokémon heals back above 50%.
- For multi-hit moves, `move.totalDamage` is used to ensure the entire move's damage is considered rather than a single-hit portion.
- Sheer Force moves: if the source has Sheer Force and the move has Sheer Force interaction, `checkedBerserk` is set to true (berry suppression doesn't apply).
- In RnB, items are not restored once consumed. Healing berries used alongside Berserk are single-use only.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Bulletproof">
## Description
Makes the holder immune to ball and bomb moves (moves with the `bullet` flag).

## Mechanics
- `onTryHit`: if `move.flags['bullet']` is set, returns `null` (move fails) and announces `-immune`.
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- **Calculator (gen789.ts)**: `move.flags.bullet && defender.hasAbility('Bulletproof')` causes the calc to return an empty result (0 damage/immunity).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Bullet-flagged moves include: Aura Sphere, Focus Blast, Shadow Ball, Energy Ball, Sludge Bomb, Electro Ball, Gyro Ball, Rock Blast, Pin Missile, Bullet Seed, Acid Spray, Zap Cannon, Weather Ball, Beak Blast, Mist Ball, Pollen Puff, Mud Bomb, etc.
- Suppressed by Mold Breaker: Mold Breaker users' bullet moves can hit Bulletproof targets.
- Only checks the `bullet` flag; moves that happen to have "ball" or "bomb" in their name but lack the flag are not blocked.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Liquid Voice">
## Description
Converts all sound-based moves to Water-type.

## Mechanics
- `onModifyTypePriority: -1` / `onModifyType`: if `move.flags['sound']` and not Dynamaxed, sets `move.type = 'Water'`.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts)**: `isLiquidVoice = attacker.hasAbility('Liquid Voice') && !!move.flags.sound`. When true, sets `type = 'Water'` and records the ability in `desc`. Critically, `hasAteAbilityTypeChange` is NOT set to true — Liquid Voice does **not** receive the 1.2× ATE-style boost that Galvanize/Pixilate/Refrigerate/Aerilate/Normalize get.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Liquid Voice converts sound moves to Water but does NOT boost them by 1.2×. This distinguishes it from ATE-family abilities (Aerilate, Galvanize, Pixilate, Refrigerate) and Normalize.
- Sound moves include: Hyper Voice, Boomburst, Disarming Voice, Round, Bug Buzz, Uproar, Echoed Voice, Chatter, Perish Song, Supersonic, etc.
- Soundproof defenders still block sound-based moves even after type conversion to Water.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Dry Skin">
## Description
Absorbs Water-type moves (healing 1/4 max HP), takes 25% extra damage from Fire-type moves, heals 1/8 max HP in rain, and loses 1/8 max HP in sun each residual turn.

## Mechanics
- `onTryHit`: Water-type moves targeting the holder heal `baseMaxhp / 4` and return `null` (immunity). If already at full HP, shows `-immune`.
- `onSourceBasePower` (priority 17): for Fire-type moves, applies `chainModify(1.25)` — 1.25× Fire damage increase.
- `onWeather`: in rain (`raindance` / `primordialsea`), heals `baseMaxhp / 8`. In sun (`sunnyday` / `desolateland`), deals `baseMaxhp / 8` damage to the holder.
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- **Calculator (gen789.ts)**:
  - Water immunity: `move.hasType('Water') && defender.hasAbility('Dry Skin', 'Storm Drain', 'Water Absorb')` → returns 0 damage.
  - Fire extra damage: `bpMods.push(5120)` (5120/4096 = 1.25×) when `defender.hasAbility('Dry Skin') && move.hasType('Fire')`.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Uses `effectiveWeather()` for the weather heal/damage check — Cloud Nine / Air Lock suppresses all weather effects.
- In RnB, rain from Drizzle is permanent — Dry Skin holders receive persistent 1/8 healing per turn in rain.
- In RnB, sun from Drought is permanent — Dry Skin holders take persistent 1/8 damage per turn in sun.
- Mold Breaker bypasses the Water immunity — Mold Breaker Water moves deal normal damage and do not heal.
- The Fire damage increase (1.25×) applies to the base power via `bpMods` in the calc.

## RnB Changes
None documented. Permanent weather means Dry Skin's rain/sun effects are consistent for the whole battle.

## AI Notes
None documented.
</Element>

<Element name="Turboblaze">
## Description
On entry, announces itself. While active, the holder's moves ignore the target's ability if that ability would interfere (identical to Mold Breaker and Teravolt in effect).

## Mechanics
- `onStart`: announces via `-ability` message.
- `onModifyMove`: sets `move.ignoreAbility = true` on every move used by the holder.
- `flags: {}` — not itself suppressed by Mold Breaker or another Teravolt/Turboblaze.
- **Calculator (gen789.ts)**: `attackerIgnoresAbility = attacker.hasAbility('Mold Breaker', 'Teravolt', 'Turboblaze')`. Behaves identically to Mold Breaker in the calc — sets `defender.ability = ''` when the conditions are met (defender doesn't have Full Metal Body, Neutralizing Gas, Prism Armor, or Shadow Shield; defender doesn't have Poison Heal).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Mechanically identical to Mold Breaker and Teravolt in terms of ability suppression.
- Full Metal Body, Neutralizing Gas, Prism Armor, and Shadow Shield are not suppressed by Turboblaze.
- Poison Heal is also not cleared in the calc (explicit protection).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Technician">
## Description
Boosts the power of moves with 60 base power or less by 1.5×.

## Mechanics
- `onBasePowerPriority: 30` / `onBasePower` (Showdown): checks `basePowerAfterMultiplier` — the base power after any previously-applied `onBasePower` modifiers. If ≤ 60, applies `chainModify(1.5)`. Priority 30 is high, so it tends to run after most other `onBasePower` hooks.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts)**: checks `basePower <= 60` where `basePower` is the move's effective BP after custom-BP moves (Low Kick, Gyro Ball, multi-hit totals, etc.) but before the `bpMods` chain. If ≤ 60, pushes `bpMods.push(6144)` (1.5×).
  - Comment in calc: "Use BasePower after moves with custom BP to determine if Technician should boost."
- Grouped in the bpMods block alongside Flare Boost, Toxic Boost, Mega Launcher, Strong Jaw, Steely Spirit, Sharpness (all push 6144).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Showdown uses `basePowerAfterMultiplier` (post-prior-modifier BP), while the calc uses the pre-bpMods base power. Practically the same for most moves, but edge cases exist if another modifier raises a sub-60 BP move to >60 before Technician's check.
- Multi-hit moves: each hit is checked at its base power per hit (e.g., 25-BP hits each qualify). The calc uses the effective BP of a single hit.
- Moves that scale BP dynamically (Low Kick, Gyro Ball, Electro Ball) use their calculated BP for the check; if that calculated BP is ≤ 60, Technician applies.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Bad Dreams">
## Description
At the end of each turn, damages all sleeping foes for 1/8 of their max HP.

## Mechanics
- `onResidualOrder: 28`, `onResidualSubOrder: 2` / `onResidual`: iterates over all foes. For each foe with `status === 'slp'` OR `hasAbility('comatose')`, deals `target.baseMaxhp / 8` damage to that foe (attributed to the holder).
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator (gen789.ts or util.ts).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Uses `baseMaxhp` for damage — always 1/8 of the target's max HP regardless of current HP.
- Comatose users are treated as permanently sleeping and take Bad Dreams damage each turn.
- Magic Guard on a sleeping foe prevents Bad Dreams damage.
- Does not wake the target; only inflicts residual damage while asleep.
- Multi-foe in doubles: damages all sleeping opponents simultaneously each turn.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Run Away">
## Description
Guarantees the ability to flee from wild Pokémon battles. Has no effect in trainer battles.

## Mechanics
- `flags: {}` — no battle hooks; purely a wild-encounter escape mechanic.
- Has no hooks in Showdown (battle simulator context); `rating: 0`.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Completely non-functional in trainer battles and standard competitive play.
- No battle-relevant mechanics to test in the NuzlockeAI context.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Flame Body">
## Description
When the holder is hit by a contact move, has a 30% chance to burn the attacker.

## Mechanics
- `onDamagingHit`: if `checkMoveMakesContact` is true, has a 3/10 (30%) chance to call `source.trySetStatus('brn', target)`.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator (gen789.ts or util.ts).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Only triggers on contact moves. Non-contact moves (most Special attacks, moves with Long Reach user, Protective Pads holder) do not trigger Flame Body.
- Burn chance is rolled per hit on multi-hit moves.
- `trySetStatus('brn', target)` checks if the target is already statused, is Fire-type, or otherwise immune to burn — the burn only applies if those checks pass.
- Fire-type attackers cannot be burned.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Analytic">
## Description
Boosts move power by approximately 1.3× if the holder moves last (after all other active Pokémon have already moved).

## Mechanics
- `onBasePowerPriority: 21` / `onBasePower` (Showdown): checks all active Pokémon. If none of the non-self active Pokémon will still move (`!queue.willMove(target)` for all), applies `chainModify([5325, 4096])` ≈ 1.3×.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts)**: condition `attacker.hasAbility('Analytic') && (turnOrder !== 'first' || field.defenderSide.isSwitching === 'out')`. If the attacker is not moving first, OR the defender is switching out, pushes `bpMods.push(5325)` ≈ 1.3×. Grouped alongside Sheer Force, Sand Force, Tough Claws, and Punk Rock (all push 5325).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Activated when the holder moves second in a 1v1 turn, or if the opponent switches out.
- In singles, "moving last" is the most common trigger. In doubles, all four Pokémon are checked.
- The calc's `turnOrder !== 'first'` condition is a simplified check relative to Showdown's dynamic queue check.
- Does not apply when the holder moves first (even if faster), only when it moves after all opponents.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Magnet Pull">
## Description
Prevents Steel-type Pokémon from switching out or fleeing.

## Mechanics
- `onFoeTrapPokemon`: if the foe has Steel type and is adjacent, calls `pokemon.tryTrap(true)` to trap it.
- `onFoeMaybeTrapPokemon`: if the foe's type is unknown or has Steel type, sets `maybeTrapped = true` for prediction UI purposes.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Only traps Steel-type Pokémon. Non-Steel types are unaffected.
- Trapping is bypassed by Shed Shell, Ghost type (can pass through trapping effects), or switching via U-turn/Volt Switch/Flip Turn/Baton Pass.
- `tryTrap(true)` — the `true` argument means the trap is "strong" (prevents switching even without a trapping move).
- In RnB NPC battles: Magnet Pull keeps Steel-type opponents locked in, potentially relevant for AI switch-out decisions.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Wonder Skin">
## Description
Reduces the accuracy of all Status moves that target the holder to 50%.

## Mechanics
- `onModifyAccuracyPriority: 10` / `onModifyAccuracy`: if the move is a Status category move and has numeric accuracy (not `true`), returns 50 (sets accuracy to exactly 50%).
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- Not referenced in the damage calculator (accuracy not simulated in calc).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Only affects status moves with numeric accuracy. Never-miss status moves (`true` accuracy, e.g., Spore vs. targets without Overcoat) are not affected by Wonder Skin.
- Mold Breaker bypasses Wonder Skin — status moves from Mold Breaker users use their normal accuracy.
- Sets accuracy TO 50% (not halves the accuracy from whatever it was). A 100% accurate status move is reduced to 50%, and a 70% accurate one is also set to 50%.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Perish Body">
## Description
When hit by a contact move, applies Perish Song to both the attacker and the holder (both faint after 3 turns unless they switch out).

## Mechanics
- `onDamagingHit`: if `checkMoveMakesContact` is true AND the attacker does not already have the `perishsong` volatile:
  - Announces `-ability Perish Body`.
  - Adds `perishsong` volatile to the attacker (`source.addVolatile('perishsong')`).
  - Adds `perishsong` volatile to the holder (`target.addVolatile('perishsong')`).
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Does not trigger if the attacker already has the `perishsong` volatile (prevents resetting the counter).
- Only triggers on contact moves. Non-contact moves do not activate Perish Body.
- Both Pokémon are subject to standard Perish Song rules: they faint after their Perish count reaches 0, but switching out removes the volatile.
- The holder also gets Perish Song applied to itself — using Perish Body is a mutual KO risk.
- Magic Guard does NOT protect against fainting from Perish Song (Perish Song bypasses Magic Guard).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Compound Eyes">
## Description
Increases the holder's move accuracy by approximately 30% (multiplies accuracy by 1.3×).

## Mechanics
- `onSourceModifyAccuracyPriority: -1` / `onSourceModifyAccuracy`: for moves with numeric accuracy (not `true`), applies `chainModify([5325, 4096])` ≈ 1.3× to the accuracy value.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator (accuracy not simulated).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Only boosts numeric accuracy moves. Never-miss moves (`true` accuracy like Swift, Aerial Ace, Aura Sphere) are unaffected.
- A 70% accuracy move becomes 91% (70 × 1.3 = 91), an 80% becomes 104% (effectively 100%), etc. Accuracy cannot exceed 100% in the hit-check calculation.
- Does not affect evasion of the target; only the accuracy of the user's moves.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Own Tempo">
## Description
Prevents the holder from being confused and cures existing confusion. In Gen 8+, also blocks Intimidate's Attack drop.

## Mechanics
- `onUpdate`: if the holder has the `confusion` volatile, removes it (cures confusion on entry or when ability is gained).
- `onTryAddVolatile`: if the volatile being added is `'confusion'`, returns `null` (blocks it).
- `onHit`: if a move has `volatileStatus === 'confusion'`, announces `-immune confusion` (cosmetic).
- `onTryBoost`: if the boost source is Intimidate and it's lowering Attack (`boost.atk`), deletes the Attack drop and shows `-fail unboost`.
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- **Calculator (util.ts `checkIntimidate`)**: In Gen 8+, Own Tempo is in the Intimidate-blocked list alongside Inner Focus, Oblivious, and Scrappy — Intimidate's Attack drop is not applied if the target has Own Tempo.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Confusion immunity works even if caused by a move (Supersonic, Swagger) or by Outrage/Petal Dance end-of-use confusion.
- The Intimidate block applies in Gen 8+ (NuzlockeAI uses Gen 8 mechanics, so this is active).
- Mold Breaker bypasses Own Tempo entirely — confusion from Mold Breaker users can be applied normally.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Protean">
## Description
Before using a move, the holder changes its type to match the move's type, gaining STAB on every move used.

## Mechanics
- `onPrepareHit` (base Showdown, Gen 9 behavior): if `effectState.protean` is already set, returns early — can only trigger ONCE per switch-in. Also skips for bounced moves, future moves, snatch-sourced moves, and call-moves. Sets `effectState.protean = true` after changing type.
- **Gen8 mod override**: removes the `effectState.protean` guard — Protean triggers EVERY TURN in Gen 8 (can change type before each move). All other conditions (bounced, future moves, snatch, callsMove) still apply.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts)**: `attacker.hasAbility('Protean', 'Libero') && !attacker.teraType` gives STAB modifier (`stabMod += 2048`, i.e., +0.5× multiplier added to base 4096, making total 6144 = 1.5×).
- Gen8 mod entry changes rating to 4.5 and removes the once-per-switch-in restriction.

## Edge Cases
- In Gen 8 (RnB), Protean activates before every move — the user always has STAB on the move being used.
- Does not activate for: moves that have already bounced (Magic Coat), future moves (Future Sight, Doom Desire), moves used via Snatch, or moves that call other moves (Sleep Talk, Metronome).
- Type change is permanent within the battle turn — if Protean user is hit before it can move next turn, it will be hit as its new type.
- Only changes type if the user's current type does not already match the move's type (`source.getTypes().join() !== type`).

## RnB Changes
None documented. Uses Gen 8 behavior (activates every turn, not once per switch-in).

## AI Notes
Protean is listed as a high-value ability: Role Play gets +9 if the AI's partner has Protean (and the AI doesn't already have it). AI won't use Role Play if it already has Protean (−20 penalty instead).
</Element>

<Element name="Ice Face">
## Description
Eiscue-only. In its ice form (Eiscue), absorbs any Physical hit with no damage taken, then transforms to Noice form. Restores the ice face when hail or snowscape is active (immediately on switch-in or when weather starts).

## Mechanics
- `onStart` (priority -2): if weather is hail or snowscape and Eiscue is in Noice form (`eiscuenoice`), announces activation, sets `busted = false`, and transforms to Eiscue form.
- `onDamage` (priority 1): if the source is a Physical move and target is in ice form (`eiscue`), announces activation, sets `busted = true`, returns 0 (nullifies damage).
- `onCriticalHit`: if Physical move vs ice form Eiscue (not substituted), returns `false` (blocks the crit).
- `onEffectiveness`: if Physical move vs ice form Eiscue, returns 0 (neutralizes type effectiveness display).
- `onUpdate`: if Eiscue and `busted = true`, transforms to Eiscue-Noice form.
- `onWeatherChange`: if hail/snowscape starts and Eiscue is in Noice form, restores the ice face. Does NOT trigger if the weather change was from Cloud Nine/Air Lock ending.
- `flags: { failroleplay: 1, noreceiver: 1, noentrain: 1, notrace: 1, failskillswap: 1, cantsuppress: 1, breakable: 1, notransform: 1 }` — highly restricted. `breakable: 1` means Mold Breaker suppresses all Ice Face hooks.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Ice Face only blocks Physical moves. Special moves deal full damage even in ice form.
- When Mold Breaker suppresses Ice Face, Physical moves deal normal damage and the face is NOT broken.
- In RnB, Snow Warning sets permanent hail — Eiscue restores its ice face on every switch-in (the `onStart` check sees active hail and restores immediately), making Ice Face much more durable.
- The restoration does NOT trigger if weather resumed from Cloud Nine/Air Lock ending (explicit `if (sourceEffect?.suppressWeather) return` guard).
- Cannot be Role Played, Traced, Received, Skill Swapped, Entrained, or suppressed by Neutralizing Gas.

## RnB Changes
None documented. Snow Warning's permanent hail means Ice Face is restored on every switch-in, giving Eiscue an effectively unlimited number of physical absorption uses across the battle.

## AI Notes
None documented.
</Element>

<Element name="Blaze">
## Description
When the holder's HP is at or below 1/3 of its max HP, boosts the power of Fire-type moves by 1.5×.

## Mechanics
- `onModifyAtkPriority: 5` / `onModifyAtk`: if the move is Fire-type and HP ≤ maxhp/3, applies `chainModify(1.5)` to Attack. Applies to both Physical (`onModifyAtk`) and Special (`onModifySpA`) Fire moves.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts)**: when `attacker.curHP() <= attacker.maxHP() / 3 && attacker.hasAbility('Blaze') && move.hasType('Fire')`, pushes `atMods.push(6144)` (1.5×). Grouped alongside Overgrow, Torrent, Swarm (all fire at 1/3 HP or lower).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Strictly HP at or below 1/3 (`<= maxhp / 3`). Exactly 1/3 HP counts; above 1/3 does not.
- The boost applies to both Physical and Special Fire moves (both `onModifyAtk` and `onModifySpA` hooks).
- Does not require `abilityOn` flag — activates automatically based on HP threshold.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Telepathy">
## Description
In doubles/triples, the holder is immune to damaging moves from allies.

## Mechanics
- `onTryHit`: if the source is an ally (`target.isAlly(source)`) and the move is not Status category, returns `null` (immunity) and announces `-activate Telepathy`.
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- Not referenced in the damage calculator (gen789.ts or util.ts).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Only relevant in doubles/triples formats. In singles, there are no ally moves to block.
- Does not block status moves from allies (only `move.category !== 'Status'` moves are blocked).
- Mold Breaker on an ally would bypass Telepathy, allowing ally spread moves to hit.
- Rating of 0 — not useful in singles (NuzlockeAI primarily uses singles format).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Drizzle">
## Description
On entry, sets Rain Dance weather (permanent in RnB; 5 turns in standard Gen 8).

## Mechanics
- `onStart`: unless the holder is Kyogre with Blue Orb (which triggers Primordial Sea instead), calls `this.field.setWeather('raindance')`.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts) — Rain effects**:
  - Water-type moves: `field.hasWeather('Rain', 'Heavy Rain') && move.hasType('Water')` → `baseDamage × 6144/4096` = 1.5× boost.
  - Fire-type moves in rain (not Heavy Rain): `field.hasWeather('Rain') && move.hasType('Fire')` → `baseDamage × 2048/4096` = 0.5× reduction.
  - Utility Umbrella holder is immune to both the boost and reduction.
- Gen8 mod entry is rating-only; no mechanic difference from base.

## Edge Cases
- In standard Gen 8, Drizzle sets rain for 5 turns (or 8 with Damp Rock). In RnB, rain from weather abilities is permanent (Mechanic Changes.txt line 28).
- Rain is `raindance` (standard rain) not `primordialsea` (Primordial Sea from Kyogre+Blue Orb).
- Other rain effects: Thunder has 100% accuracy in rain, Hurricane has 100% accuracy in rain, Solar Beam/Blade deals half damage; these are separate from the damage modifier.
- Hydration cures status in rain, Rain Dish heals 1/16 per turn, Dry Skin heals 1/8 per turn — all active in Drizzle's rain.

## RnB Changes
- Drizzle sets permanent rain (does not expire). Mechanic Changes.txt line 28: "Weather abilities: Will set Weather permanently."

## AI Notes
None documented.
</Element>

<Element name="Serene Grace">
## Description
Doubles the chance of secondary effects on the holder's moves.

## Mechanics
- `onModifyMovePriority: -2` / `onModifyMove`: for each entry in `move.secondaries`, doubles `secondary.chance` (if it exists). Also doubles `move.self.chance` if the move has a self-effect with a chance.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator (gen789.ts or util.ts); purely a secondary-effect probability modifier.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Doubles `secondary.chance` in place — a 10% flinch chance becomes 20%, a 30% burn chance becomes 60%, a 100% stat-drop chance stays 100% (already guaranteed).
- Also doubles `move.self.chance` for self-targeting secondary effects (e.g., moves that have a chance to raise the user's own stat).
- Does not affect moves without secondaries (moves that always do their effect unconditionally; those have no `chance` field to double).
- Flinch from King's Rock/Razor Fang: these items add a secondary flinch chance via their own hook, not through `move.secondaries`, so Serene Grace does not double the item-added flinch chance (it only doubles chances already in `move.secondaries`).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Quick Feet">
## Description
When the holder has a status condition, raises its Speed by 1.5×. Also bypasses the Speed reduction from paralysis.

## Mechanics
- `onModifySpe`: if the holder has any status (`pokemon.status` is truthy), applies `chainModify(1.5)` to Speed.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (util.ts)**:
  - `speedMods.push(6144)` (1.5×) when `pokemon.hasAbility('Quick Feet') && pokemon.status`.
  - Paralysis speed reduction: `if (pokemon.hasStatus('par') && !pokemon.hasAbility('Quick Feet'))` — the paralysis halving/quartering is skipped for Quick Feet holders. In RnB, paralysis reduces Speed to 25% of its value (−75%); Quick Feet users immune to this also receive the 1.5× boost on top.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Applies to all non-volatile statuses: paralysis, burn, poison, toxic, sleep, freeze.
- Specifically exempts Quick Feet from the paralysis Speed penalty (`!pokemon.hasAbility('Quick Feet')` guard).
- A paralyzed Quick Feet user gets the 1.5× Speed boost and does NOT suffer the −75% paralysis penalty (effectively +50% Speed vs normal).
- Does not prevent the damage/accuracy effects of other statuses (burn still halves Physical damage, etc.).

## RnB Changes
None documented. Paralysis reduces Speed by 75% in RnB (vs 50% in standard Gen 8), making Quick Feet's bypass even more valuable in RnB.

## AI Notes
None documented.
</Element>

<Element name="Magic Guard">
## Description
Prevents the holder from taking damage from anything other than direct moves (blocks all indirect/chip damage).

## Mechanics
- `onDamage`: if the damage source is NOT a Move (`effect.effectType !== 'Move'`), returns `false` (cancels the damage). If the source is an Ability, also announces `-activate` for that ability.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator (indirect damage not modeled in the damage calc context).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Blocks all non-move damage: poison, burn, Leech Seed, weather damage (sandstorm, hail), entry hazards (Stealth Rock, Spikes), recoil from items (Rocky Helmet, Life Orb), Curse, Nightmare, trap damage (Bind, Wrap), etc.
- Does NOT block damage from moves — Magic Guard holders still take full damage from damaging moves.
- Recoil from the holder's own moves (e.g., Take Down, Flare Blitz): Magic Guard DOES protect against self-recoil as well, since recoil is applied as a non-move `effect`.
- Perish Song fainting: Magic Guard does NOT protect against Perish Song (Perish Song is implemented as a direct HP drop that bypasses Magic Guard).
- Life Orb recoil is blocked by Magic Guard — the holder can use a Life Orb without taking 10% recoil.

## RnB Changes
- Mechanic Changes.txt line 40: Pokémon with Magic Guard will not take overworld damage from being poisoned. (Overworld effect only; no in-battle difference.)

## AI Notes
None documented.
</Element>

<Element name="Damp">
## Description
Prevents Explosion, Self-Destruct, Mind Blown, and Misty Explosion from being used while the holder is on the field. Also blocks Aftermath damage.

## Mechanics
- `onAnyTryMove`: if any Pokémon attempts to use Explosion, Self-Destruct, Mind Blown, or Misty Explosion, cancels the move with `'cant'` message.
- `onAnyDamage`: if the damage source is Aftermath, returns `false` (cancels the damage entirely).
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Blocks the move regardless of which Pokémon is using it (uses `onAnyTryMove` — triggers for any active Pokémon's move attempt, not just the Damp user's opponents).
- Mold Breaker bypasses Damp — a Mold Breaker user CAN use Explosion/Self-Destruct despite Damp.
- Aftermath damage (from a fainted contact attacker) is also fully suppressed on any Pokémon on the field when Damp is active.
- Does NOT prevent the holder itself from using self-damaging moves other than the listed four.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Toxic Boost">
## Description
When the holder is poisoned or badly poisoned, raises the power of its Physical moves by 1.5×.

## Mechanics
- `onBasePowerPriority: 19` / `onBasePower`: if the holder's status is `'psn'` or `'tox'` and the move is Physical, applies `chainModify(1.5)`.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts)**: `attacker.hasAbility('Toxic Boost') && attacker.hasStatus('psn', 'tox') && move.category === 'Physical'` → `bpMods.push(6144)` (1.5×). Grouped in the same block as Technician, Flare Boost, Mega Launcher, etc.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Only boosts Physical moves. Special moves are not affected.
- Works with both regular poison (`psn`) and badly poisoned (`tox`); the strength of the poison doesn't matter for the boost.
- Burn halves Physical damage while Guts boosts it — Toxic Boost's 1.5× stacks independently of other modifiers.
- The 1.5× damage boost typically outweighs the residual poison damage cost.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Effect Spore">
## Description
When hit by a contact move, has a 30% chance (total) to inflict sleep (11%), paralysis (10%), or poison (9%) on the attacker.

## Mechanics
- `onDamagingHit`: if `checkMoveMakesContact` is true and the attacker passes `runStatusImmunity('powder')`:
  - Random number 0–99: `r < 11` → Sleep (11%), `r < 21` → Paralysis (10%), `r < 30` → Poison (9%).
  - 30% combined chance of some status; 70% chance of nothing.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- `runStatusImmunity('powder')` — Grass-type Pokémon, Overcoat holders, and Safety Goggles holders are immune to powder moves and therefore cannot be affected by Effect Spore.
- Only triggers on contact moves. Non-contact moves (most Special attacks, Long Reach users, Protective Pads holders) do not trigger it.
- `trySetStatus` checks normal status immunities — a Fire-type cannot be burned, Grass-types can't be poisoned, Electric-types can't be paralyzed, etc.
- Each hit of a multi-hit contact move independently has a 30% roll.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Neutralizing Gas">
## Description
While the holder is on the field, suppresses all abilities of every active Pokémon (including the holder's). When it leaves, all suppressed abilities restart.

## Mechanics
- Suppression is implemented in `Pokemon#ignoringAbility` — when any Pokémon's ability is checked, if a Neutralizing Gas user is active, that ability is ignored.
- `onSwitchInPriority: 2` / `onSwitchIn`: announces `-ability Neutralizing Gas`. Iterates all active Pokémon; for Illusion holders, triggers `Illusion:End`. Clears `slowstart` volatile. For Primordial Sea / Desolate Land / Delta Stream holders, triggers their `End` event (removes extreme weather).
- `onEnd`: if no other Neutralizing Gas user remains, announces `-end Neutralizing Gas`, sets `abilityState.ending = true`, then triggers `Start` events for all other active Pokémon's abilities (re-activating them). Abilities with `cantsuppress: 1` (Ice Face, Zen Mode, etc.) are skipped. Ability Shield holders' abilities were never suppressed, so they're skipped too.
- `flags: { failroleplay: 1, noreceiver: 1, noentrain: 1, notrace: 1, failskillswap: 1, notransform: 1 }` — highly restricted. Cannot be copied, swapped, received, or traced.
- **Calculator (gen789.ts)**: `defenderIgnoresAbility` includes `'Neutralizing Gas'` — the holder's defensive ability cannot be suppressed by Mold Breaker (the holder suppresses everyone else, but Mold Breaker cannot suppress the holder's own Neutralizing Gas).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Suppresses all abilities, including the holder's own. The holder effectively has no ability while Neutralizing Gas is active.
- Ability Shield blocks the suppression for the holder of that item.
- Extreme weather (Primoridal Sea/Desolate Land/Delta Stream) ends when the responsible Pokémon's ability is suppressed on Neutralizing Gas entry.
- When Neutralizing Gas ends, abilities re-trigger in Speed order. This means weather abilities, terrain abilities, and entry abilities restart.
- Does not suppress `cantsuppress: 1` abilities (Comatose, Ice Face, Zen Mode, etc.).
- In RnB, permanent weather from weather abilities would restart if Neutralizing Gas ends, restoring the permanent weather.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Guts">
## Description
When the holder has a status condition, raises its Attack by 1.5×. Also ignores the burn penalty on Physical moves.

## Mechanics
- `onModifyAtkPriority: 5` / `onModifyAtk`: if the holder has any status (`pokemon.status` is truthy), applies `chainModify(1.5)` to Attack.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts)**:
  - `atMods.push(6144)` (1.5×) when `attacker.hasAbility('Guts') && attacker.status && move.category === 'Physical'`.
  - Burn halving: `applyBurn` guard includes `!attacker.hasAbility('Guts')` — a burned Guts user does NOT suffer the 0.5× burn penalty on Physical moves. The Guts 1.5× still applies.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Guts applies to any non-volatile status: burn, paralysis, poison, toxic, sleep, freeze.
- Crucially, a burned Guts user gets the 1.5× Atk boost AND ignores the burn's 0.5× physical damage penalty — this is modeled explicitly in the calc (`!attacker.hasAbility('Guts')` in the `applyBurn` check).
- Facade with Guts: Facade doubles base power when the user is statused, and Guts boosts Attack — these stack multiplicatively, making Guts+Facade a common combo.
- Does not remove the status — the holder still takes residual damage from burn/poison etc.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Forecast">
## Description
Castform-only. Changes Castform's form and type based on the current weather: Fire in sun, Water in rain, Ice in hail/snow, Normal otherwise.

## Mechanics
- `onSwitchInPriority: -2` / `onStart`: triggers a WeatherChange event to apply the current weather's forme immediately on switch-in.
- `onWeatherChange`: if the Pokémon is Castform (base species) and not transformed, changes forme to match `effectiveWeather()`. Maps: sunnyday/desolateland → Castform-Sunny; raindance/primordialsea → Castform-Rainy; hail/snowscape → Castform-Snowy; other → Castform (Normal). Uses `effectiveWeather()`, so Cloud Nine / Air Lock suppresses the change.
- `flags: { failroleplay: 1, noreceiver: 1, noentrain: 1, notrace: 1 }` — cannot be copied, received, or traced; Role Play can't copy it.
- **Calculator (util.ts `checkForecast`)**: called for both attacker and defender at the start of calc. If `pokemon.hasAbility('Forecast') && pokemon.named('Castform')`, sets `pokemon.types` based on weather (maps `'Sun'`/`'Harsh Sunshine'` → Fire, `'Rain'`/`'Heavy Rain'` → Water, `'Hail'`/`'Snow'` → Ice, default → Normal). This ensures STAB and type effectiveness are calculated correctly.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- `effectiveWeather()` is used in Showdown — Cloud Nine / Air Lock Pokémon on the field suppress the weather, causing Castform to revert to Normal form.
- In RnB, weather from abilities is permanent, so Castform's form stays fixed for the whole battle as long as the weather setter is on the field and alive.
- Castform in hail uses `hail` (set by Snow Warning in Gen 8); the gen8 mod Snow Warning sets `hail`, and Forecast checks `'hail'` and `'snowscape'`, so both work.
- Transformed Castform does not trigger Forecast (explicit `|| pokemon.transformed` check).

## RnB Changes
None documented. Permanent weather means Castform's type is stable for the entire battle when a weather ability is present.

## AI Notes
None documented.
</Element>

<Element name="Aroma Veil">
## Description
Protects the holder and all allies from moves and effects that restrict their choices (Attract, Disable, Encore, Heal Block, Taunt, Torment).

## Mechanics
- `onAllyTryAddVolatile`: if any allied Pokémon would receive `attract`, `disable`, `encore`, `healblock`, `taunt`, or `torment` from a move, returns `null` (blocks the volatile) and announces `-block` via the Aroma Veil holder.
- Only triggers if the source is a Move (`effect.effectType === 'Move'`); does not block the volatile if added by other means.
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Protects all allied Pokémon, not just the holder itself.
- Uses `onAllyTryAddVolatile` — triggers when the volatile is being applied to an ally (including the holder).
- Mold Breaker bypasses Aroma Veil — Taunt/Encore from Mold Breaker users can affect the team normally.
- In singles format (most RnB battles), Aroma Veil only protects the holder itself (no ally to protect).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Defeatist">
## Description
When the holder's HP is at or below 50%, halves both its Attack and Special Attack.

## Mechanics
- `onModifyAtkPriority: 5` / `onModifyAtk`: if HP ≤ maxhp/2, applies `chainModify(0.5)`.
- `onModifySpAPriority: 5` / `onModifySpA`: same condition, applies `chainModify(0.5)`.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts)**: when `attacker.hasAbility('Defeatist') && attacker.curHP() <= attacker.maxHP() / 2`, pushes `atMods.push(2048)` (0.5×), applied to both Physical and Special moves.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Halves at exactly 50% HP — the condition is `<= maxhp / 2` (at half HP the penalty is active).
- Affects both Physical (Attack) and Special (Special Attack) damage equally.
- Rating −1 (negative) — considered detrimental ability.
- `Slow Start` uses the same `atMods.push(2048)` block in the calc (grouped together with Defeatist).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Rock Head">
## Description
Prevents the holder from taking recoil damage from its own moves (except from Struggle).

## Mechanics
- `onDamage`: if the damage source is `'recoil'`, returns `null` (cancels the damage). Exception: if the active move is Struggle, the recoil IS applied (does not block Struggle recoil).
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator (recoil not modeled in calc).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Blocks standard recoil moves: Flare Blitz, Take Down, Double-Edge, Head Smash, Brave Bird, Volt Tackle, etc.
- Does NOT block Struggle recoil (explicit `this.activeMove.id !== 'struggle'` check — Struggle recoil is allowed through).
- Does not block crash damage (High Jump Kick miss damage) — crash damage uses a different source, not `'recoil'`.
- Life Orb recoil: Life Orb's 10% HP loss is not flagged as `'recoil'` effect type in Showdown — Rock Head does NOT protect against Life Orb recoil (that's Magic Guard's territory).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Hunger Switch">
## Description
Morpeko-only. At the end of each turn, alternates between Morpeko's Full Belly Mode and Hangry Mode.

## Mechanics
- `onResidualOrder: 29` / `onResidual`: if the Pokémon is Morpeko (base species) and not Terastallized, toggles the forme: Morpeko → Morpeko-Hangry, Morpeko-Hangry → Morpeko.
- `flags: { failroleplay: 1, noreceiver: 1, noentrain: 1, notrace: 1, failskillswap: 1, notransform: 1 }` — cannot be copied, swapped, received, or traced; Transform does not copy it.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- The forme change alternates every end-of-turn — Morpeko switches each turn without needing any action.
- The main in-battle effect: Morpeko's signature move Aura Wheel changes type based on the current forme (Electric in Full Belly, Dark in Hangry Mode).
- Terastallized Morpeko does not switch formes (`pokemon.terastallized` check).
- Since Transform is blocked (`notransform: 1`), Ditto cannot transform into Morpeko with Hunger Switch.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Download">
## Description
On entry, boosts Attack by 1 stage if the opponent's Defense is lower than its Special Defense, or boosts Special Attack by 1 stage if Defense is equal to or higher than Special Defense.

## Mechanics
- `onStart` (Showdown): sums foes' Defense and Special Defense using `getStat('def'/'spd', false, true)` (unboosted, modified stat). If total Def ≥ total SpD → `boost({ spa: 1 })`. Otherwise → `boost({ atk: 1 })`.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (util.ts `checkDownload`)**: called for both attacker and defender at calc start. Compares `target.stats.def` vs `target.stats.spd` (the calc's modified/effective stats). If `spd <= def` → `source.boosts.spa += 1`. Otherwise → `source.boosts.atk += 1`. Handles Wonder Room by re-swapping the stats (Download ignores Wonder Room — it always checks actual defense stats, not the swapped ones).
- Calc calls `checkDownload(attacker, defender, field.isWonderRoom)` and `checkDownload(defender, attacker, field.isWonderRoom)`.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- In Showdown, uses modified (item-boosted) but unboosted (no stage boosts) stats. The calc uses `target.stats.def/spd` which incorporate items/EVs but not boost stages.
- Wonder Room reversal: Download explicitly re-swaps in Wonder Room to check the correct (original) defense stats.
- In doubles, sums ALL foes' Defense and Special Defense; the total comparison determines which stat is boosted.
- Exactly equal Def = SpD triggers the `totaldef >= totalspd` branch → SpA boost.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Corrosion">
## Description
Allows the holder to inflict poison or bad poison on Steel-type and Poison-type Pokémon, which are normally immune to being poisoned.

## Mechanics
- Implemented in `sim/pokemon.ts:Pokemon#setStatus`. When checking type immunity for poison/toxic: `!(source?.hasAbility('corrosion') && ['tox', 'psn'].includes(status.id))` — if the source has Corrosion and the status is poison or toxic, the type immunity check is bypassed entirely. Steel and Poison types can then receive the poison status.
- `flags: {}` — not breakable by Mold Breaker. The ability has no hooks in the abilities file; it's a passive override in the status-setting logic.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Only bypasses TYPE immunity to poison (Steel and Poison types). Other immunity sources (Immunity ability, full status already active, etc.) are not bypassed.
- Once poisoned by Corrosion, the Steel or Poison type takes normal poison/badly poisoned residual damage each turn.
- A Poison-type poisoned by Corrosion does NOT get the Bad Poison → Poison conversion immunity that normally applies.
- Ability immunity (e.g., Immunity ability) still blocks the poison even with Corrosion.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Sand Spit">
## Description
When the holder is hit by a damaging move, sets a Sandstorm.

## Mechanics
- `onDamagingHit`: calls `this.field.setWeather('sandstorm')` whenever the holder takes damage from a move.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Triggers on any damaging hit, including multi-hit moves (each hit triggers the weather call, though it's a no-op if sandstorm is already active).
- In RnB, weather from weather abilities is permanent. However, Sand Spit is not listed as a weather ability in RnB (only: Drought, Drizzle, Sandstorm, Snow Warning). Sand Spit's sandstorm is reactive (triggered by taking a hit), not on switch-in, so it is likely subject to normal 5-turn duration (or 8 with Smooth Rock).
- Sandstorm damages all non-Rock/Steel/Ground types (and holders of Safety Goggles) by 1/16 max HP per turn.

## RnB Changes
None documented. Sand Spit itself likely sets a non-permanent sandstorm (it's not a "terrain ability" under Mechanic Changes.txt line 28-29 which refers to weather/terrain abilities setting on entry).

## AI Notes
None documented.
</Element>

<Element name="Flower Veil">
## Description
Prevents Grass-type allies from having their stats lowered by opponents, and protects them from status conditions and Yawn.

## Mechanics
- `onAllyTryBoost`: if the target is a Grass-type and the boost is from an opponent (source ≠ target), removes all negative boosts from the boost object and shows `-block` if any were deleted (only for primary effects, not secondaries).
- `onAllySetStatus`: if the ally is a Grass-type and the source is external (not itself), returns `null` (blocks status). Shows `-block` for Synchronize or primary move effects.
- `onAllyTryAddVolatile`: if the ally is a Grass-type and the volatile is `yawn`, returns `null` (blocks Yawn).
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Protects ONLY Grass-type Pokémon among allies. Non-Grass allies are not protected.
- Stat drops from secondaries (e.g., Crunch's Defense drop chance) are NOT blocked — the `-block` only shows for non-secondary moves, though the drops are still deleted.
- Does NOT protect against stat drops caused by the Pokémon itself (self-inflicted drops pass through).
- In singles, Flower Veil only protects the holder itself if it's Grass-type; without a Grass-type ally, it's useless.
- Rating 0 — considered non-functional in singles.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Soundproof">
## Description
Makes the holder immune to sound-based moves (moves with the `sound` flag).

## Mechanics
- `onTryHit`: if the move has `flags['sound']` and the source is not the holder itself, returns `null` (immunity) and announces `-immune`.
- `onAllyTryHitSide`: if a sound move would hit the holder's side, announces `-immune` for the holder (prevents it from being affected by sound moves spread to its side).
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- **Calculator (gen789.ts)**: `move.flags.sound && !move.named('Clangorous Soul') && defender.hasAbility('Soundproof')` → returns 0 damage (immunity). Note: Clangorous Soul is explicitly excluded (it targets the user itself and is still usable by Soundproof users).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Blocks all sound-flagged moves: Hyper Voice, Boomburst, Bug Buzz, Disarming Voice, Uproar, Echoed Voice, Round, Perish Song, Supersonic, Growl, Roar, Snarl, Screech, etc.
- Clangorous Soul is explicitly carved out in the calc — a Soundproof Kommo-o can still use its own Clangorous Soul.
- Liquid Voice converts sound moves to Water-type; Soundproof still blocks these converted moves (the `sound` flag remains even after type conversion).
- Mold Breaker bypasses Soundproof — sound moves from Mold Breaker users hit normally.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Slush Rush">
## Description
Doubles the holder's Speed in hail or snow.

## Mechanics
- `onModifySpe`: if the field weather is `hail` or `snowscape`, applies `chainModify(2)` (doubles Speed).
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (util.ts)**: `pokemon.hasAbility('Slush Rush') && ['Hail', 'Snow'].includes(weather)` → `speedMods.push(8192)` (8192/4096 = 2×). Grouped alongside Chlorophyll, Sand Rush, Swift Swim, and Surge Surfer (all push 8192).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Activates in both `hail` (standard/Snow Warning-set in Gen 8) and `snowscape` (Gen 9). The calc maps hail → `'Hail'` and snowscape → `'Snow'`.
- In RnB, Snow Warning sets permanent hail. Slush Rush users thus have permanently doubled Speed when a Snow Warning ally is on the field.
- Does not protect against hail damage — Ice-type Slush Rush users are naturally immune to hail damage, but non-Ice types would still take residual damage.

## RnB Changes
None documented. Permanent hail from Snow Warning makes Slush Rush effectively always-on in that team composition.

## AI Notes
None documented.
</Element>

<Element name="Adaptability">
## Description
Raises the STAB bonus from 1.5× to 2×.

## Mechanics
- `onModifySTAB` (Showdown): if the move has STAB (`forceSTAB` or `source.hasType(move.type)`), returns 2 (instead of the default 1.5). Special case: if `stab === 2` (which can occur with Tera + original type stacking), returns 2.25 instead.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts)**: STAB is built as `stabMod` starting at 4096. Normal STAB adds 2048 (total 6144 = 1.5×). Adaptability adds another 2048 (total 8192 = 2×) when the attacker has the move's type. Tera interactions (adds 1024 instead of 2048 if the tera type is an original type) are modeled but not relevant in RnB (no Tera).
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- The 2× STAB applies to all moves matching the holder's type(s), not just one type.
- Stacks with other modifiers (weather, terrain, abilities) in the normal chain.
- In Showdown, if some mechanic results in `stab === 2` before Adaptability (like Tera + original type), Adaptability pushes it to 2.25×.
- Protean/Libero + Adaptability: Protean gives STAB on every move, and if the user somehow also had Adaptability (through Trace, etc.), every move would be 2× STAB.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Wandering Spirit">
## Description
When hit by a contact move, swaps abilities with the attacker (equivalent to Skill Swap).

## Mechanics
- `onDamagingHit`: if `checkMoveMakesContact` is true, calls `this.skillSwap(source, target)` — swapping the abilities of the holder and the attacker.
- `flags: {}` — not breakable by Mold Breaker.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Uses the same logic as Skill Swap: abilities with `failskillswap: 1` flag cannot be swapped (e.g., Comatose, Wonder Guard, Neutralizing Gas, etc.).
- Only triggers on contact moves. Non-contact moves do not trigger the ability swap.
- After the swap, the former Wandering Spirit holder now has the attacker's original ability, and vice versa. Appropriate `onStart`/`onEnd` events fire for the swapped abilities.
- Mold Breaker users: despite `flags: {}` (not breakable), Mold Breaker bypasses the ability for damage purposes, but the contact trigger itself comes from `onDamagingHit` which still fires even for Mold Breaker users. The swap still happens.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Vital Spirit">
## Description
Prevents the holder from falling asleep and cures existing sleep immediately.

## Mechanics
- `onUpdate`: if the holder is sleeping (`status === 'slp'`), cures it immediately and announces activation.
- `onSetStatus`: if the status being applied is sleep, returns `false` (blocks it). Shows `-immune` for move-sourced sleep.
- `onTryAddVolatile`: if the volatile is `yawn`, returns `null` (blocks it) and shows `-immune`.
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Cures existing sleep via `onUpdate` — if Vital Spirit is granted mid-battle (e.g., via Skill Swap), a sleeping holder wakes immediately.
- Blocks Yawn's volatile, preventing the delayed sleep trigger.
- Mold Breaker bypasses Vital Spirit — sleep moves from Mold Breaker users CAN put the holder to sleep.
- Functionally identical to Insomnia; both prevent sleep and block Yawn. The only difference is the Pokémon species that can have each.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Keen Eye">
## Description
Prevents the holder's Accuracy from being lowered by opponents, and ignores the target's Evasion boosts when attacking.

## Mechanics
- `onTryBoost`: if the boost source is an opponent (not self) and `boost.accuracy < 0`, deletes the accuracy drop and shows `-fail` for non-secondary move effects.
- `onModifyMove`: sets `move.ignoreEvasion = true` on every move used by the holder — the target's positive evasion stages are ignored when calculating hit chance.
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- Not referenced in the damage calculator.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- `move.ignoreEvasion = true` does not ignore accuracy drops on the attacker — only evasion boosts on the defender are ignored.
- Accuracy drops from secondary effects (e.g., if a move had a secondary that lowered accuracy) are still blocked but don't show the `-fail` message.
- Mold Breaker bypasses Keen Eye — accuracy drops from Mold Breaker users apply normally, and those users also have their evasion respected.
- Does not interact with Wonder Room (which swaps Def/SpDef stats, not accuracy/evasion).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Ice Scales">
## Description
Halves damage taken from Special moves.

## Mechanics
- `onSourceModifyDamage`: if the move is Special category, applies `chainModify(0.5)` (halves damage).
- `flags: { breakable: 1 }` — suppressed by Mold Breaker, Teravolt, Turboblaze.
- **Calculator (gen789.ts)**: `defender.hasAbility('Ice Scales') && move.category === 'Special'` → `finalMods.push(2048)` (0.5×). Grouped alongside Punk Rock (also pushes 2048 for sound moves). Both push 2048 in the same `else if` block.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Only halves Special damage. Physical moves deal full damage.
- Mold Breaker bypasses Ice Scales — Special moves from Mold Breaker users are not halved.
- Differs from Fur Coat (doubles Defense) in that Ice Scales directly modifies damage rather than a stat — so stat stages don't interact with Ice Scales the same way they do with Fur Coat.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Mega Launcher">
## Description
Boosts the power of aura and pulse moves by 1.5×.

## Mechanics
- `onBasePowerPriority: 19` / `onBasePower`: if `move.flags['pulse']` is set, applies `chainModify(1.5)`.
- `flags: {}` — not breakable by Mold Breaker.
- **Calculator (gen789.ts)**: `attacker.hasAbility('Mega Launcher') && move.flags.pulse` → `bpMods.push(6144)` (1.5×). Grouped in the same block as Technician, Strong Jaw, etc.
- Gen8 mod entry is rating-only; no mechanic change.

## Edge Cases
- Applies to all moves with the `pulse` flag: Aura Sphere, Dark Pulse, Dragon Pulse, Origin Pulse, Heal Pulse, Water Pulse, Oblivion Wing, etc.
- Heal Pulse boosted by Mega Launcher heals the target for 75% of their max HP instead of 50%.
- Does not boost moves that have "aura" in the name but lack the `pulse` flag (e.g., Fairy Aura, Dark Aura abilities).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Swift Swim">
## Description
Doubles the holder's Speed stat when rain is active.

## Mechanics
- **Calculator (util.ts)**: `pokemon.hasAbility('Swift Swim') && weather.includes('Rain')` → `speedMods.push(8192)` (2×). The `weather.includes('Rain')` check catches both regular rain (`'Rain'`) and Primordial Sea (`'Rain'`). In practice, any weather string containing `'Rain'` triggers the boost.
- **Showdown**: `onModifySpe` checks `['raindance', 'primordialsea'].includes(pokemon.effectiveWeather())` → `chainModify(2)`. `flags: {}` — not breakable.
- Gen 8 mod entry is rating-only (`inherit: true`); no mechanic changes.

## Edge Cases
- Only active during rain; does not stack with other speed-doubling effects at the formula level, but multiple `speedMods` entries are all chained together.
- Does not grant any type immunity or damage modification — speed only.
- In RnB, Drizzle-based rain is permanent, so Swift Swim bearers have a persistent ×2 Speed advantage when paired with a Drizzle user.

## RnB Changes
None documented. Rain set by Drizzle/Primordial Sea is permanent in RnB (Mechanic Changes.txt line 28), making Swift Swim substantially more reliable than in standard play.

## AI Notes
None documented.
</Element>

<Element name="Battle Bond">
## Description
Exclusive to Greninja-Bond. After knocking out an opponent, triggers a forme change to Greninja-Ash. In Ash-Greninja form, Water Shuriken always hits 3 times.

## Mechanics
- **Showdown (base)**: `onSourceAfterFaint` — if `source.species.id === 'greninjabond'` and `source.hp` and not transformed and `source.side.foePokemonLeft()`, boosts Atk/SpA/Spe by +1 and sets `bondTriggered = true`. Does NOT actually form-change in base Showdown (Gen 9 behavior — stat boosts instead).
- **Gen 8 mod override**: `onSourceAfterFaint` — performs actual `formeChange('Greninja-Ash', ...)` and sets `formeRegression = true` (Greninja reverts to base form on switch-out). `isNonstandard: null` makes it available in Gen 8 formats.
- `onModifyMove`: if move is `watershuriken` and attacker is `Greninja-Ash` and not transformed → `move.multihit = 3`.
- `flags: { failroleplay: 1, noreceiver: 1, noentrain: 1, notrace: 1, failskillswap: 1, cantsuppress: 1 }` — cannot be copied, transferred, or suppressed.
- **Calculator (gen789.ts)**: Water Shuriken base power is 20 when `attacker.named('Greninja-Ash') && attacker.hasAbility('Battle Bond')`, otherwise 15.

## Edge Cases
- `bondTriggered = true` prevents the ability from firing more than once per switch-in (prevents repeated forme changes on multiple KOs in Gen 8).
- Ability won't trigger if Greninja faints simultaneously with the opponent or if no foes remain.
- In Gen 8, Greninja-Ash reverts to base form on switch-out (`formeRegression = true`).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Steam Engine">
## Description
When hit by a Fire- or Water-type move, raises Speed by 6 stages.

## Mechanics
- **Showdown**: `onDamagingHit` — if `['Water', 'Fire'].includes(move.type)`, calls `this.boost({ spe: 6 })`. `flags: {}` — not breakable.
- Gen 8 mod is rating-only; no mechanic change.
- **Calculator (gen789.ts)**: No special handling — Steam Engine's effect is a stat boost triggered in-battle, not a damage modifier that the calc models.

## Edge Cases
- Triggers on any damaging Fire or Water hit, including multi-hit moves (each hit can trigger it separately up to the +6 cap).
- Since the boost is `spe: 6`, it can raise Speed to the maximum of +6 stages in a single hit.
- Does not activate from indirect Fire/Water damage (e.g., burn), only direct damaging moves.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Drought">
## Description
On switch-in, summons harsh sunlight (Sunny Day weather). In RnB, the weather is permanent for the battle.

## Mechanics
- **Showdown**: `onStart` — calls `this.field.setWeather('sunnyday')`. Exception: if `source.species.id === 'groudon'` and `source.item === 'redorb'`, skips (Red Orb Groudon uses Desolate Land instead). `flags: {}` — not breakable.
- Gen 8 mod is rating-only; no mechanic change.
- **Calculator (gen789.ts)**: Caller sets `field.weather = 'Sun'`. Calc applies:
  - `field.hasWeather('Sun', 'Harsh Sunshine') && move.hasType('Fire')` → `baseDamage * 6144 / 4096` (×1.5)
  - `field.hasWeather('Sun') && move.hasType('Water')` → `baseDamage * 2048 / 4096` (×0.5)
  - These are applied as final weather modifiers, not BP mods. Blocked by Utility Umbrella.

## Edge Cases
- Blocked by Utility Umbrella on the defender; Fire boost and Water reduction do not apply.
- Harsh Sunshine (Desolate Land) fully neutralizes Water moves (`hasWeather('Harsh Sunshine')` — Water deals 0 damage, not just 0.5×).
- In sun, Solar Beam/Solar Blade require no charge turn; Thunder/Hurricane accuracy drops.

## RnB Changes
Drought sets weather **permanently** (Mechanic Changes.txt line 28: "Weather abilities: Will set Weather permanently."). This means any team fielding a Drought user has guaranteed sun for the entire battle. Fire-type moves deal 1.5× and Water-type moves deal 0.5× throughout the match.

## AI Notes
None documented.
</Element>

<Element name="Power Spot">
## Description
Boosts the base power of allies' moves by approximately 1.3× in doubles. Does not boost the holder's own moves.

## Mechanics
- **Showdown**: `onAllyBasePowerPriority: 22` / `onAllyBasePower` — if `attacker !== this.effectState.target` (i.e., a partner, not self), applies `chainModify([5325, 4096])` ≈ 1.3×.
- `flags: {}` — not breakable.
- Gen 8 mod is rating-only; no mechanic change.
- **Calculator (gen789.ts)**: No direct handling found. Power Spot is a doubles-only ally boost; single-target calc does not model it.

## Edge Cases
- Only affects allies, not the holder itself.
- Doubles/multi-battle mechanic — irrelevant in singles.
- The multiplier `[5325, 4096]` ≈ 1.3003× (Battery and Power Spot share this ratio).

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Wonder Guard">
## Description
The holder can only be damaged by super-effective moves. Status moves still work normally.

## Mechanics
- **Showdown**: `onTryHit` — if `move.category !== 'Status'` and `move.id !== 'struggle'` and `target.runEffectiveness(move) <= 0`, the move is immune.
- `flags: { failroleplay: 1, noreceiver: 1, failskillswap: 1, breakable: 1 }` (Gen 8) — cannot be Role Play'd or Skill Swap'd, but IS breakable by Mold Breaker.
- Gen 8 mod removes `noentrain` from flags (base Showdown has it), meaning Wonder Guard can be Entrained in Gen 8.
- **Calculator (gen789.ts)**: `defender.hasAbility('Wonder Guard') && typeEffectiveness <= 1` → returns 0 damage. This check occurs AFTER `attackerIgnoresAbility` clears `defender.ability` to `''` — so Mold Breaker/Teravolt/Turboblaze correctly bypass Wonder Guard (ability is cleared before the check, so `hasAbility('Wonder Guard')` returns false).
- `breakable: 1` — breakable by Mold Breaker, Teravolt, Turboblaze, and moves like Moongeist Beam.

## Edge Cases
- Status moves, indirect damage (weather, burn, entry hazards), and Struggle still deal damage.
- Moves that have variable typing (e.g., Hidden Power, Judgment) may or may not be super-effective depending on type matchup.
- In Gen 8, Wonder Guard can be transferred via Entrainment (the `noentrain` flag was removed).
- Mold Breaker and similar abilities bypass Wonder Guard completely.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Shadow Tag">
## Description
Prevents adjacent opponents from switching out or fleeing, unless they also have Shadow Tag.

## Mechanics
- **Showdown**: `onFoeTrapPokemon` — if the opponent does not have `shadowtag` and is adjacent, calls `pokemon.tryTrap(true)`. `onFoeMaybeTrapPokemon` — if opponent lacks `shadowtag` and is adjacent, sets `pokemon.maybeTrapped = true`.
- Pokémon with Shadow Tag are immune to being trapped by another Shadow Tag user.
- `flags: {}` — not breakable.
- Gen 8 mod is rating-only; no mechanic change.
- **Calculator (gen789.ts)**: No damage calculation involvement. Shadow Tag is a trapping mechanic not modeled in the damage calc.

## Edge Cases
- Does not prevent switching via items (e.g., Shed Shell) or moves that allow switching regardless of trapping.
- Ghosttypes can still switch/flee despite Shadow Tag (they are immune to trapping effects in standard Gen 8).
- In doubles, Shadow Tag traps all adjacent foes who don't have the ability.
- Shadow Tag vs. Shadow Tag: both are free to switch.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Synchronize">
## Description
When inflicted with poison, burn, or paralysis by an opponent, passes the same status condition back to that opponent. In RnB (and overworld), leading with a Synchronize Pokémon gives a 50% chance to force the wild Pokémon's nature to match the leader's nature.

## Mechanics
- **Showdown**: `onAfterSetStatus` — if `source` exists and is not `target`, and the effect is not Toxic Spikes, and the status is not Sleep or Freeze, calls `source.trySetStatus(status, target, ...)` to reflect the status back.
- Reflected statuses: poison (`psn`), toxic (`tox`), burn (`brn`), paralysis (`par`). Sleep and freeze are excluded.
- `flags: {}` — not breakable.
- Gen 8 mod is rating-only; no mechanic change.
- **Calculator (gen789.ts)**: No damage calculation involvement.

## Edge Cases
- Synchronize does NOT reflect statuses caused by Toxic Spikes (entry hazard), by the holder itself, or by non-direct causes.
- The reflected status can be blocked by the opponent's type immunities (e.g., Fire-types are immune to burn from Synchronize).
- Sleep and Freeze are deliberately excluded from Synchronize's reflection effect.
- The "hack" in Showdown passes a fake `{ status: status.id, id: 'synchronize' }` effect object to trigger status-prevention ability messages properly.

## RnB Changes
Synchronize has an overworld effect: leading with a Synchronize Pokémon gives a **50% chance to force a wild encounter's nature** to match the leader's nature (Mechanic Changes.txt line 27). This is an overworld feature only, not relevant to battle AI.

## AI Notes
None documented.
</Element>

<Element name="No Guard">
## Description
Every move used by or against the holder will always hit, ignoring accuracy and evasion checks. Additionally, the holder can hit Pokémon in invulnerable states (e.g., during Fly, Dig).

## Mechanics
- **Showdown**: Two hooks:
  - `onAnyInvulnerability` (priority 1) — if the move's source or target is the holder, returns `0` (negates invulnerability, allowing the move to hit).
  - `onAnyAccuracy` — if source or target is the holder, returns `true` (bypasses accuracy check entirely).
- `flags: {}` — not breakable.
- Gen 8 mod is rating-only; no mechanic change.
- **Calculator (gen789.ts)**: No explicit handling — the calc assumes moves hit. No Guard's accuracy guarantee is not modeled as a damage modifier.

## Edge Cases
- Applies in both directions: the holder's moves always hit opponents, AND opponents' moves always hit the holder.
- Allows moves like Thunder, Blizzard, and Hurricane to hit in any weather without accuracy reduction.
- OHKO moves still fail against higher-level opponents regardless of No Guard.
- Moves that don't have accuracy (status moves with `—` accuracy) are unaffected.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Gale Wings">
## Description
Gives Flying-type moves +1 priority. In standard Gen 8, this only works at full HP. In RnB, it works at any HP.

## Mechanics
- **Showdown (standard Gen 8)**: `onModifyPriority` — if `move.type === 'Flying'` and `pokemon.hp === pokemon.maxhp`, returns `priority + 1`. Gen 8 mod is rating-only; no mechanic change to HP condition.
- `flags: {}` — not breakable.
- **Calculator (gen789.ts)**: `attacker.hasAbility('Gale Wings') && move.hasType('Flying') && attacker.curHP() === attacker.maxHP()` → sets `move.priority = 1`. **Note**: The RnB calc still applies the full-HP check even though RnB removes it — the calc has not been updated to reflect RnB's change.

## Edge Cases
- +1 priority can still be blocked by Queenly Majesty, Dazzling, and Armor Tail.
- Applies to all Flying-type moves including status moves (e.g., Roost, Tailwind) that have the Flying type.
- Does not boost Z-moves or Max Moves that are Flying-type (they have fixed priority).

## RnB Changes
**Gale Wings always boosts priority regardless of HP** (Mechanic Changes.txt line 23: "Gale Wings: Will always boost the priority of Flying-type moves, regardless of HP."). This is a major buff: in standard play, a single hit removes the priority boost; in RnB the holder permanently enjoys +1 priority on all Flying-type moves. **The RnB calculator still applies the full-HP check and does not reflect this change.**

## AI Notes
None documented.
</Element>

<Element name="Water Bubble">
## Description
Doubles the power of the holder's Water-type moves, halves incoming Fire-type damage, and prevents the holder from being burned (cures burn if already burned).

## Mechanics
- **Showdown**:
  - `onModifyAtk`/`onModifySpA`: Water-type moves → `chainModify(2)` (×2 attack stat for Water moves).
  - `onSourceModifyAtk`/`onSourceModifySpA` (priority 5): When an attacker attacks the holder with Fire → `chainModify(0.5)` (halves attacker's Atk/SpA for Fire moves).
  - `onSetStatus`: If status would be burn → returns `false` (immune to burn).
  - `onUpdate`: If already burned, cures the burn immediately.
- `flags: { breakable: 1 }` — breakable by Mold Breaker.
- Gen 8 mod is rating-only; no mechanic change.
- **Calculator (gen789.ts)**:
  - Attacker has Water Bubble + Water move: `atMods.push(8192)` (×2) — grouped with Huge Power/Pure Power.
  - Defender has Water Bubble + Fire move: `atMods.push(2048)` (×0.5) — grouped with Thick Fat.

## Edge Cases
- The attack doubling applies to both physical and special Water moves (modifies Atk AND SpA).
- Fire damage halving applies regardless of attacker's physical/special split.
- Burn immunity is absolute — Flare Blitz's secondary burn chance cannot apply.
- Breakable by Mold Breaker: all three effects can be suppressed.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Illusion">
## Description
The holder disguises itself as the last Pokémon in the party upon switching in. The disguise breaks when the holder takes direct damage.

## Mechanics
- **Showdown**: `onBeforeSwitchIn` — scans party from the end backward, finds the last non-fainted Pokémon (past the holder's position), and sets `pokemon.illusion = possibleTarget`. If no valid Pokémon found, illusion is null.
- `onDamagingHit` — if holder has an active illusion, calls `this.singleEvent('End', ...)` to break the disguise.
- `onEnd` — clears illusion, reveals true species (`pokemon.getUpdatedDetails()`), broadcasts `replace` and `-end Illusion` events.
- `onFaint` — clears illusion on faint.
- `flags: { failroleplay: 1, noreceiver: 1, noentrain: 1, notrace: 1, failskillswap: 1 }` — cannot be copied or transferred.
- Gen 8 mod is rating-only; no mechanic change.
- **Calculator (gen789.ts)**: No damage calculation involvement.

## Edge Cases
- Illusion only disguises as Pokémon to the holder's right in party order (index > `pokemon.position`).
- Status moves, weather damage, entry hazards, and other indirect damage do NOT break Illusion.
- Only direct damaging moves break the disguise (via `onDamagingHit`).
- The disguised appearance includes type display, potentially misleading opponents about type matchups.
- Ogerpon/Terapagos in the last slot is excluded from Illusion targets when the Illusion user is Terastallized.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>

<Element name="Gluttony">
## Description
Allows the holder to eat its held berry at 50% HP (half HP) instead of the usual 25% threshold.

## Mechanics
- **Showdown**: Sets `pokemon.abilityState.gluttony = true` on start and on damage. The actual berry-consumption logic (checking `abilityState.gluttony`) is in the item scripts, not here. When Neutralizing Gas ends, `abilityState.gluttony` is reset to false and then re-set when Gluttony's `onStart` fires again.
- `flags: {}` — not breakable.
- Gen 8 mod is rating-only; no mechanic change.
- **Calculator (util.ts)**: Berry threshold calculation notes Gluttony as complex to implement; comment at line 302 indicates Gluttony's berry threshold is not fully modeled in the calc.

## Edge Cases
- Gluttony raises the berry activation threshold from 25% HP to 50% HP for healing berries (Sitrus, Oran, Figy, etc.).
- If Neutralizing Gas suppresses Gluttony mid-battle, `abilityState.gluttony` is reset; the berry reverts to triggering at 25%.
- In RnB, Mechanic Changes.txt mentions confuse-inducing berries restore half HP triggering at 1/4 HP — this is the standard berry activation, not Gluttony-related.

## RnB Changes
None documented.

## AI Notes
None documented.
</Element>
