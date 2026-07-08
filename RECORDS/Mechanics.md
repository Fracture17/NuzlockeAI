<Element name="Damage Formula">
## Overview
The full damage pipeline, in order of application. All fractional steps use integer arithmetic with Game Freak's rounding rules.

## pokeRound
Game Freak rounds DOWN on exactly 0.5: `pokeRound(n) = n % 1 > 0.5 ? ceil(n) : floor(n)`.
A value of exactly X.5 rounds to X (down), not X+1.

## OF16 / OF32 (Overflow)
Intermediate products simulate 16-bit and 32-bit integer overflow:
- `OF16(n) = n > 65535 ? n % 65536 : n`
- `OF32(n) = n > 4294967295 ? n % 4294967296 : n`
Applied before division steps throughout the calculation.

## chainMods
All modifier stacks use `chainMods(mods, lowerBound, upperBound)`:
```
M = 4096
for each mod in mods:
    if mod != 4096:
        M = (M * mod + 2048) >> 12    # multiply, round to nearest, then divide by 4096
return clamp(M, lowerBound, upperBound)
```
The `+2048` before the bit-shift is rounding (equivalent to pokeRound). Bounds are typically 41–131072 for attack/defense/final mods, and 41–2097152 for BP mods.

## Step 1: Base Damage
```
baseDamage = floor(OF32(
    floor(OF32(OF32(floor((2 * level / 5 + 2)) * basePower) * attack) / defense)
    / 50 + 2
))
```
All overflows applied before each division. Results in an integer.

## Step 2: Spread Move Reduction (Doubles/Triples only)
If the move targets `allAdjacent` or `allAdjacentFoes` and the game type is not Singles:
```
baseDamage = pokeRound(OF32(baseDamage * 3072) / 4096)   # ×0.75
```

## Step 3: Parental Bond Child Hit
If the attacker has `Parental Bond (Child)` pseudo-ability:
```
baseDamage = pokeRound(OF32(baseDamage * 1024) / 4096)   # ×0.25
```

## Step 4: Weather Modifier
Applied only if defender is NOT holding Utility Umbrella:
- Sun or Harsh Sunshine + Fire-type move: `×6144/4096` (×1.5)
- Rain or Heavy Rain + Water-type move: `×6144/4096` (×1.5)
- Sun (not Harsh Sunshine) + Water-type move: `×2048/4096` (×0.5)
- Rain (not Heavy Rain) + Fire-type move: `×2048/4096` (×0.5)

Applied as: `baseDamage = pokeRound(OF32(baseDamage * modifier) / 4096)`.

Separate early-exit cases (move deals 0 damage):
- Harsh Sunshine + Water-type move: returns 0 (no damage at all)
- Heavy Rain + Fire-type move: returns 0

## Step 5: Critical Hit Multiplier
If the hit is a critical: `baseDamage = floor(OF32(baseDamage * 1.5))`.
Note: uses `floor` (not pokeRound) and runs before the random roll loop.

## Steps 6–11: Per-Roll Loop (runs 16 times, i = 0..15)

### Step 6: Random Roll
```
damageAmount = floor(OF32(baseDamage * (85 + i)) / 100)
```
This produces 16 damage values with multipliers 85/100 through 100/100. The actual in-game random pick is uniform across these 16 values.

### Step 7: STAB Modifier
If `stabMod != 4096`:
```
damageAmount = OF32(damageAmount * stabMod) / 4096
```
Note: **no floor here**; result is a float passed to the next step.

### Step 8: Type Effectiveness
```
damageAmount = floor(OF32(pokeRound(damageAmount) * typeEffectiveness))
```
pokeRound applied to the STAB result before multiplying by effectiveness.
typeEffectiveness is an exact rational (0.25, 0.5, 1, 2, 4, etc.) stored as a float.

### Step 9: Burn Halving
If attacker is burned AND move is Physical AND attacker lacks Guts AND move is not Facade:
```
damageAmount = floor(damageAmount / 2)
```

### Step 10: Protect vs Z/Dynamax
If `field.defenderSide.isProtected` AND (`move.isZ` OR `attacker.isDynamaxed`):
```
damageAmount = pokeRound(OF32(damageAmount * 1024) / 4096)   # ×0.25
```

### Step 11: Final Mods
```
return OF16(pokeRound(max(1, OF32(damageAmount * finalMod) / 4096)))
```
Minimum damage is 1 (before OF16 overflow). finalMod is the chainMods result from all final modifiers.

## Minimum Damage
After all calculations the final damage is at least 1 (unless the move deals 0 by design or is blocked).

## Explosion / Self-Destruct / Misty Explosion Defense Halving
These three moves halve the defender's effective defense stat during the damage calculation:
```
dfMods.push(2048)   # ×0.5 to defense
```
Applied as a defense modifier (chainMods), so it interacts multiplicatively with other defense modifiers.
Note: this is present in the Gen 7/8/9 calculator. Vanilla Gen 5+ removed the defense halving from Explosion/Self-Destruct, so this may be a RnB-specific restoration of the older mechanic. The calculator takes precedent, so the simulator should halve defense.
Misty Explosion also receives this halving in addition to its ×1.5 BP boost in Misty Terrain (when grounded).

## Fixed Damage Moves
These bypass the entire formula:
- Seismic Toss, Night Shade, Psywave: damage = attacker's level
- Dragon Rage: damage = 40
- Sonic Boom: damage = 20
- Final Gambit: damage = attacker's current HP
- Super Fang / Nature's Madness: damage = floor(defender's current HP / 2) (0 if Protected)
- Guardian of Alola: damage = floor(defender's current HP × 3 / 4); quarter that if Protected against Z-crystal

Parental Bond doubles fixed-damage moves: both hits deal the full fixed amount.
</Element>

<Element name="Stat Stages">
## Overview
Stat boosts (stages) range from -6 to +6. They multiply the raw stat before use in damage calculations.

## Boost Multiplier Table (Gen 3+)
| Stage | Numerator | Denominator | Multiplier |
|-------|-----------|-------------|------------|
| -6    | 2         | 8           | 0.25       |
| -5    | 2         | 7           | ≈0.286     |
| -4    | 2         | 6           | ≈0.333     |
| -3    | 2         | 5           | 0.4        |
| -2    | 2         | 4           | 0.5        |
| -1    | 2         | 3           | ≈0.667     |
|  0    | 2         | 2           | 1.0        |
| +1    | 3         | 2           | 1.5        |
| +2    | 4         | 2           | 2.0        |
| +3    | 5         | 2           | 2.5        |
| +4    | 6         | 2           | 3.0        |
| +5    | 7         | 2           | 3.5        |
| +6    | 8         | 2           | 4.0        |

## Implementation
```
modifiedStat = floor(OF16(rawStat * numerator) / denominator)
```
OF16 overflow applies to the multiplication before the floor/divide.

## Clamping
Boosts are clamped to [-6, +6] at the point they are applied. Attempts to boost beyond +6 or drop below -6 have no effect.

## Critical Hit Interaction
- If a critical hit AND attacker has a negative attack boost → attack boost is ignored (use raw stat)
- If a critical hit AND defender has a positive defense boost → defense boost is ignored (use raw stat)
- Negative defense boosts and positive attack boosts still apply on a crit

## Unaware
Defender with Unaware: attacker's attack boost is ignored (raw stat used).
Attacker with Unaware: defender's defense boost is ignored (raw stat used).
Both apply independently.

## Simple
Simple doubles the magnitude of all stat stage changes applied to the holder (e.g., +1 becomes +2, -1 becomes -2). Still capped at ±6.

## Contrary
Contrary inverts all stat changes for the holder (+1 becomes -1, etc.).

## Spectral Thief
Steals all positive stat boosts from the defender and adds them to the attacker (capped at +6 per stat). Contrary on the attacker inverts the stolen boosts.

## Countable Boosts (for Stored Power, Power Trip, Punishment)
`countBoosts` sums only **positive** boosts across Atk, Def, SpA, SpD, Spe (HP not included).
Punishment uses the **defender's** positive boosts; Stored Power/Power Trip use the **attacker's**.

## Accuracy/Evasion Stages
These follow the same table structure but are not used in the damage formula.
</Element>

<Element name="Stat Calculation">
## Overview
How a Pokémon's raw (unmodified by stage) stat values are computed from base stats, IVs, EVs (note: EVs removed in RnB), level, and nature.

## RnB Note
EVs are removed from the game. All EV values are 0.

## HP Formula
```
HP = floor(((base * 2 + iv + floor(ev / 4)) * level / 100)) + level + 10
```
With ev=0:
```
HP = floor(((base * 2 + iv) * level / 100)) + level + 10
```
Special case: if base stat == 1 (Shedinja), HP = 1 regardless.

## Other Stats Formula
```
rawStat = floor((floor(((base * 2 + iv + floor(ev / 4)) * level / 100)) + 5) * natureMultiplier)
```
With ev=0:
```
rawStat = floor((floor(((base * 2 + iv) * level / 100)) + 5) * natureMultiplier)
```

## Nature Multiplier
- Boosted stat: ×1.1
- Hindered stat: ×0.9
- Neutral: ×1.0
- If nature.plus == nature.minus (Neutral nature): always ×1.0

## Nature List
Each nature has at most one boosted stat and one hindered stat. A nature with plus == minus is effectively neutral.

## IVs
Range: 0–31. Max IVs = 31.

## Protosynthesis / Quark Drive (Most Proficient Stat)
`getMostProficientStat` compares all stats after applying their current boosts. In case of ties, priority order is: Atk > Def > SpA > SpD > Spe.
</Element>

<Element name="Type Effectiveness">
## Overview
Type matchups determine how effective a move is against a target. The final multiplier is applied as an integer multiply against the rounded damage value.

## Dual-Type Combination
For a defender with two types, the effectiveness is the product of each type's matchup:
```
typeEffectiveness = getMoveEffectiveness(move, type1) * getMoveEffectiveness(move, type2)
```
Common combined results: 0, 0.25, 0.5, 1, 2, 4.

## Tera Type Override
If the defender has a Tera type active, only that single type is used:
```
typeEffectiveness = getMoveEffectiveness(move, defender.teraType)
```
The original typing is completely ignored.

## Normal/Fighting vs. Ghost
Ghost immunity to Normal/Fighting is removed if ANY of:
- Attacker has Scrappy ability
- `field.defenderSide.isForesight` is set

## Ground vs. Flying
Flying immunity to Ground is removed if ANY of:
- `field.isGravity` is active
- Defender holds Iron Ball (without Klutz)
- Defender has Ring Target (without Klutz)

## Special Cases
- **Freeze-Dry** is always super-effective (×2) against Water-type, regardless of the normal type chart.
- **Flying Press** uses the product of Fighting-effectiveness and Flying-effectiveness against the target type.
- **Thousand Arrows**: if it would normally hit for ×0 (against Flying), typeEffectiveness is overridden to 1.
- **Iron Ball** on Flying defender: Ground moves that would be immune due to Flying type instead deal neutral damage (typeEffectiveness forced to 1).

## Ring Target
Defender holding Ring Target (without Klutz): immunities to Normal and Fighting (for Ghost-type) and Ground (for Flying-type) are removed.

## Strong Winds
When Strong Winds weather is active and the defender has the Flying type, any move that would be super-effective against Flying has its type effectiveness halved (divided by 2). This is the Δ Epsilon form weather introduced in ORAS.

## Wonder Guard
Wonder Guard: only super-effective moves (typeEffectiveness > 1) deal damage; all others return 0.

## Zero Effectiveness
If typeEffectiveness == 0 the move deals no damage and the result is returned early.

## Application in Damage Formula
Type effectiveness is applied as: `floor(OF32(pokeRound(priorResult) * typeEffectiveness))`.
The effectiveness is a floating-point value (0.25, 0.5, 1, 2, 4, etc.) multiplied directly.
</Element>

<Element name="STAB">
## Overview
Same-Type Attack Bonus. Added to `stabMod` (base 4096) before the random roll loop.

## Standard STAB
If attacker's original typing includes the move's type: `stabMod += 2048` → total 6144/4096 = ×1.5.

## Protean / Libero
If attacker has Protean or Libero AND does NOT have a Tera type active: `stabMod += 2048` → ×1.5.

## Tera STAB
If `attacker.teraType == move.type`: `stabMod += 2048` (stacks with original-type STAB if applicable).

## Adaptability
If attacker has Adaptability AND has the move's type (original or tera):
```
stabMod += (teraType && attacker.hasOriginalType(teraType)) ? 1024 : 2048
```
- Without tera, with matching original type: +2048 (total 4096+2048+2048 = 8192/4096 = ×2.0)
- With tera matching move type, and tera matches original type: +1024 (total: 4096+2048+2048+1024 = 9216/4096 = ×2.25)
- With tera matching move type, tera does NOT match original type: +2048 (total: 4096+0+2048+2048 = 8192/4096 = ×2.0)

## Application
```
damageAmount = OF32(damageAmount * stabMod) / 4096
```
No floor at this step; result passes as float to type effectiveness multiplication.

## Stacking
All applicable STAB modifiers (original type, tera, Adaptability) are **added** to `stabMod` before application; they do not chain separately.

## Normalize
Normalize changes the move type to Normal (regardless of original type), which then qualifies for Normal-type STAB.
</Element>

<Element name="Critical Hits">
## RnB Values
- Critical hit chance: **1/16** (vanilla gen 8 is also 1/24 normally, but RnB explicitly sets 1/16)
- Critical hit damage multiplier: **×1.5** (same as vanilla gen 8)

## Determination
A hit is critical if:
1. `move.isCrit` is set (e.g., high-crit moves, Focus Energy etc. handled upstream), AND
2. Attacker does NOT have Merciless **or** (attacker has Merciless AND defender is poisoned/toxic), AND
3. Defender does NOT have Battle Armor or Shell Armor, AND
4. `move.timesUsed === 1` — crits only apply on the first sequential use of a move. This affects moves like Rollout or Draco Meteor when the calculator accumulates damage across multiple uses (timesUsed > 1 for subsequent turns). For single-use moves timesUsed is always 1, so this check has no effect on them.

Merciless grants a guaranteed crit against poisoned (psn) or toxic (tox) targets, but is still blocked by Battle Armor/Shell Armor.

## Magma Armor (RnB)
Magma Armor prevents critical hits on the holder, in addition to its existing effect of preventing freeze.

## Crit Effects on Stats
- Negative attacker attack stage: ignored (raw stat used instead)
- Positive defender defense stage: ignored (raw stat used instead)
- Negative defense stages and positive attack stages still apply

## Crit Multiplier Application
```
baseDamage = floor(OF32(baseDamage * 1.5))
```
Applied before the random roll loop, using `floor` (not pokeRound).

## Sniper
If attacker has Sniper and the hit is critical: additional ×1.5 finalMod (6144/4096), stacking multiplicatively with the 1.5× from the base crit.

## Multiscale / Shadow Shield
Multiscale and Shadow Shield halve incoming damage when the Pokémon is at full HP (`curHP === maxHP` at the moment the attack lands). A Parental Bond child hit bypasses Multiscale regardless of HP. Critical hits do NOT bypass Multiscale or Shadow Shield.

## Focus Energy / isFocusEnergy
`side.isFocusEnergy` is tracked in the field state but crit stage calculation (1/16 base chance, with stage raises reducing it to guaranteed at stage 3+) is handled upstream outside the calculator.
</Element>

<Element name="Random Damage Roll">
## Overview
Damage is calculated as 16 discrete values, corresponding to random multipliers 85/100 through 100/100.

## Loop
```
for i in 0..15:
    damageAmount[i] = floor(OF32(baseDamage * (85 + i)) / 100)
```
Multipliers are: 85%, 86%, 87%, ..., 100%.

## Application Order
The random roll is applied AFTER the crit multiplier and BEFORE STAB, type effectiveness, burn halving, and final mods.

## In-Game Behavior
The game picks one of the 16 values uniformly at random. The calculator displays the full range [min, max] and all 16 intermediate values.

## Floor Rounding
The division by 100 uses `floor`, not pokeRound. This means 0.5 results truncate downward.

## Overflow
OF32 is applied to `baseDamage * (85 + i)` before the divide.
</Element>

<Element name="Weather">
## Weather Types
Valid values: `'Sun'`, `'Harsh Sunshine'`, `'Rain'`, `'Heavy Rain'`, `'Sand'`, `'Hail'`, `'Snow'`, `'Strong Winds'`.

## RnB Changes
- **Weather abilities** (Drought, Drizzle, Sand Stream, Snow Warning, etc.) set their weather **permanently** (no turn limit).
- Overworld weather also exists:
  - Rainy routes: permanent Rain Dance
  - Thunderstorm routes: permanent Rain Dance + Electric Terrain
  - Drought routes: permanent Sunny Day
  - Snow area (Sootopolis Gym underground): permanent Hail

## Damage Modifiers (applied to baseDamage BEFORE random roll)
- `Sun` or `Harsh Sunshine` + Fire-type move (no Utility Umbrella): `×6144/4096` ≈ ×1.5
- `Rain` or `Heavy Rain` + Water-type move (no Utility Umbrella): `×6144/4096` ≈ ×1.5
- `Sun` (not Harsh Sunshine) + Water-type move (no Utility Umbrella): `×2048/4096` = ×0.5
- `Rain` (not Heavy Rain) + Fire-type move (no Utility Umbrella): `×2048/4096` = ×0.5

## Complete Suppression (Move Deals 0 Damage)
- `Harsh Sunshine` + Water-type move: move fails entirely (0 damage, returned early)
- `Heavy Rain` + Fire-type move: move fails entirely (0 damage, returned early)

## Defense Modifiers
Applied directly to the defense stat before further modifiers:
- `Sand` weather: Rock-type defenders get Special Defense ×1.5 on special hits
  `defense = pokeRound(defense * 3 / 2)`
- `Snow` weather: Ice-type defenders get Defense ×1.5 on physical hits
  `defense = pokeRound(defense * 3 / 2)`

## Utility Umbrella
Holder is immune to all damage and defense boosts from Sun/Rain/Harsh Sunshine/Heavy Rain.
The complete suppression cases (Harsh Sunshine+Water, Heavy Rain+Fire) are NOT bypassed by Utility Umbrella — but the holder treats the weather as absent for damage/defense purposes, so the move simply hits at normal power.

## Air Lock / Cloud Nine
These abilities suppress all weather effects during the damage calculation (weather is set to `undefined` for the calculation). Both attacker and defender are checked; either one being present eliminates weather.

## Strong Winds
When Strong Winds is active and the defending Pokémon has the Flying type, any move that would be super-effective vs. Flying has its type effectiveness divided by 2 (e.g., Electric vs. Flying goes from ×2 to ×1).

## Weather Ball
In any weather except Strong Winds and no weather:
- BP doubles: 50 → 100
- Type changes: Sun/Harsh Sunshine → Fire; Rain/Heavy Rain → Water; Sand → Rock; Hail/Snow → Ice
If holder has Utility Umbrella in Sun/Rain/Harsh Sunshine/Heavy Rain: BP stays at 50, type stays Normal.

## Solar Beam / Solar Blade
In `Rain`, `Heavy Rain`, `Sand`, `Hail`, or `Snow`: BP halved (×0.5, 2048/4096).
Not halved in Sun; charges/fires in one turn in Sun.

## Sand Residual Damage
Pokémon without Rock/Ground/Steel typing take 1/16 of their max HP at end of each turn in Sandstorm. (Handled in residuals, not in damage calc.)

## Hail Residual Damage
Non-Ice types take 1/16 max HP per turn in Hail. In Snow (gen 9) no residual damage; Snow grants the Def boost instead.
</Element>

<Element name="Terrain">
## Terrain Types
Valid values: `'Electric'`, `'Grassy'`, `'Misty'`, `'Psychic'`.

## RnB Changes
- **Terrain abilities** (Electric Surge, Grassy Surge, Misty Surge, Psychic Surge) set terrain **permanently**.
- Terrain damage boost is **×1.5** (matching the calculator: 6144/4096).
- Terrain is **NOT removed by Defog** (unlike vanilla). Still removed by Steel Roller.
- Overworld: Thunderstorm routes set Electric Terrain permanently.

## Damage Boosts (attacker must be grounded)
Applied in BP mods as `6144/4096` (×1.5):
- Electric Terrain + Electric-type move: ×1.5
- Grassy Terrain + Grass-type move: ×1.5
- Psychic Terrain + Psychic-type move: ×1.5

## Damage Reductions (defender must be grounded)
Applied in BP mods as `2048/4096` (×0.5):
- Misty Terrain + Dragon-type move: ×0.5
- Grassy Terrain + Bulldoze or Earthquake: ×0.5

## Priority Move Blocking (Psychic Terrain)
If `field.hasTerrain('Psychic')` and `move.priority > 0` and defender is grounded: move fails (returns 0 damage), regardless of type.

## Grounded Requirement
All terrain effects require the affected Pokémon to be grounded (see Grounding mechanic). Flying types, Air Balloon holders, and Levitate users are unaffected by terrain boosts/reductions UNLESS Gravity is active or they hold Iron Ball.

## Nature Power (terrain-based transformation)
| Terrain   | Becomes       | BP | Category |
|-----------|---------------|----|----------|
| Electric  | Thunderbolt   | 90 | Special  |
| Grassy    | Energy Ball   | 90 | Special  |
| Misty     | Moonblast     | 95 | Special  |
| Psychic   | Psychic       | 90 | Special  |
| None      | Tri Attack    | 80 | Special  |

## Terrain Pulse
If attacker is grounded and any terrain is active: BP doubles.

## Rising Voltage
If defender is grounded AND Electric Terrain is active: BP doubles.

## Expanding Force
If attacker is grounded AND Psychic Terrain active: BP ×1.5 (6144/4096); also changes target to `allAdjacentFoes` (spread move).

## Misty Explosion
If attacker is grounded AND Misty Terrain active: BP ×1.5 (6144/4096).

## Terrain Pulses (Terrain Pulse, Rising Voltage, Expanding Force, Misty Explosion)
All the above are BP modifier effects (applied in the basePower phase), not final mods.

## Terrain Seeds
When a Pokémon switches in or the terrain is set:
- Electric Seed: +1 Def (or -1 Def with Contrary)
- Grassy Seed: +1 Def (or -1 Def with Contrary)
- Misty Seed: +1 SpD (or -1 SpD with Contrary)
- Psychic Seed: +1 SpD (or -1 SpD with Contrary)
Seed is consumed on activation.

## Surge Surfer
Speed ×2 in Electric Terrain (see Speed Calculation).

## Hadron Engine
Special Attack ×5461/4096 (≈×1.333) in Electric Terrain when attacker is grounded.
</Element>

<Element name="Burn">
## Effect on Damage
Physical moves used by a burned Pokémon deal half damage:
```
damageAmount = floor(damageAmount / 2)
```
Applied after type effectiveness, before final mods.

Exceptions (burn damage halving does NOT apply):
- Attacker has Guts ability
- Move is Facade (Facade's BP doubles instead; halving is not applied)

## Residual Damage
At end of each turn: `damage = floor(baseMaxHP / 16)`.
Note: uses **baseMaxHP** (the undynamaxed HP), not current max HP.

## Interaction with Special Moves
Burn only halves Physical move damage. Special moves are unaffected by burn.

## Flare Boost
Attacker with Flare Boost + burned + Special move: attack modifier ×1.5 (6144/4096). No interaction with the physical halving (different category).

## Status Move Interactions
Smelling Salts has doubled BP against paralyzed targets (not burned).
Wake-Up Slap has doubled BP against sleeping targets.
Hex has doubled BP against any status condition including burn.
Facade doubles BP when holder has burn, paralysis, or poison.
</Element>

<Element name="Paralysis">
## Speed Reduction (RnB)
Speed is reduced to **25%** of the fully-modified speed value (75% speed decrease):
```
speed = floor(OF32(speed * 25) / 100)
```
Applied AFTER all other speed modifiers (Choice Scarf, Tailwind, ability modifiers, etc.).

## RnB vs. Vanilla
Vanilla gen 8: 50% speed reduction (speed × 50 / 100).
RnB: 75% speed reduction (speed × 25 / 100). The calculator already uses 25/100 for both gen <7 and gen 7+.

## Move Failure
25% chance (1 in 4) to be fully paralyzed and unable to act each turn.

## Quick Feet Interaction
Quick Feet bypasses the speed reduction (and instead grants ×1.5 speed when any status is present). The 25% failure chance still applies regardless.

## Smelling Salts
Deals double BP against paralyzed targets (70 × 2 = 140 BP). Cures paralysis after hitting.

## Interaction with Damage Calc
Paralysis has no direct effect on damage output other than via the speed reduction affecting turn order and speed-dependent move BPs (Gyro Ball, Electro Ball).
</Element>

<Element name="Sleep">
## Duration
On infliction: `startTime = random(2, 5)` (i.e., 2, 3, or 4 — exclusive of 5). Decremented each turn before the action check:
- startTime=2 → wakes after 1 turn (can act on turn 2)
- startTime=3 → wakes after 2 turns
- startTime=4 → wakes after 3 turns

## Turn Resolution
Each turn the sleeping Pokémon would act:
1. If Early Bird: time decremented by 1 (extra decrement), then 1 again below = 2 total decrements
2. time is decremented by 1 (always)
3. If time ≤ 0: Pokémon wakes up and can act normally that turn
4. Otherwise: Pokémon is unable to act (except for sleep-usable moves: Sleep Talk, Snore)

## RnB Change
If a Pokémon **enters battle** while already asleep (e.g., switched in), its sleep turn counter is **reset** to a new random value (startTime = random(2, 5) again). This prevents sleeping Pokémon from being "sleep-banked" across multiple switch-ins.

## Sleep-Usable Moves
Sleep Talk and Snore can be used while asleep. Other moves cannot.

## Wake-Up Slap
Wake-Up Slap has doubled BP (60 → 120) against sleeping targets (including Comatose). Wakes the target after hitting.
Dream Eater only works on sleeping targets (or Comatose ability holders).

## Hex
Deals double BP against any status condition including sleep.

## Comatose Ability
Treated as always-asleep for interaction purposes (Wake-Up Slap, Hex, Dream Eater) but the Pokémon can still act normally.
</Element>

<Element name="Freeze">
## Thaw Chance
20% chance (1 in 5) to thaw at the start of each turn the frozen Pokémon would act.

## Thaw Triggers
A frozen Pokémon immediately thaws when:
- Hit by a Fire-type damaging move (not status moves, and not Polar Flare specifically)
- The frozen Pokémon itself uses a move with the `defrost` flag (e.g., Flare Blitz, Sacred Fire, Scald — these thaw the user before executing)
- Hit by a move that has `thawsTarget` (e.g., Steam Eruption, Scald)

## Cannot Act While Frozen
The Pokémon cannot use most moves while frozen. Moves with the `defrost` flag are exceptions (they proceed and thaw the user simultaneously).

## Shaymin-Sky
Shaymin-Sky reverts to Shaymin form upon being frozen.

## Freeze Prevention
Pokémon cannot be frozen in Sun/Harsh Sunshine weather or if already frozen.
Fire-types are immune to being frozen.

## Magma Armor (RnB)
Magma Armor prevents freeze AND prevents critical hits (in addition to existing effects).
</Element>

<Element name="Poison and Toxic">
## Poison (psn)
Residual damage at end of each turn:
```
damage = floor(baseMaxHP / 8)
```

## Toxic / Bad Poison (tox)
Residual damage scales each turn:
```
stage increments each turn (max 15)
damage = clamp(floor(baseMaxHP / 16), 1) * stage
```
- Turn 1: 1/16
- Turn 2: 2/16 = 1/8
- Turn 3: 3/16
- ...
- Turn 15+: 15/16 (capped, stage does not increment beyond 15)

**Stage resets to 0 on switch-out/switch-in** (`onSwitchIn` resets `stage = 0`).

## Poison-Type Immunity
Poison-type Pokémon cannot be poisoned or toxiced normally.

## Steel-Type Immunity
Steel-type Pokémon cannot be poisoned or toxiced normally.

## Toxic Spikes Interaction
1 layer of Toxic Spikes inflicts Poison (psn); 2 layers inflict Toxic (tox) on grounded switchins.
A Poison-type switchin absorbs all Toxic Spikes (removes them from the field).
Steel-types and Heavy-Duty Boots ignore Toxic Spikes.

## Damage Calc Interactions
- Merciless: guaranteed critical hit against poisoned (psn) or toxic (tox) targets.
- Venoshock: doubled BP (80 → 160) against poisoned or toxic targets.
- Barb Barrage: doubled BP (60 → 120) against poisoned or toxic targets.
- Hex: doubled BP against any status condition including poison/toxic.
- Facade: doubled BP when holder has poison, toxic, burn, or paralysis (without halving from burn).
- Toxic Boost: Physical move power ×1.5 when user is poisoned or toxic.

## Poison Heal
If the Pokémon has Poison Heal: residual damage is replaced with healing (1/8 max HP per turn). The Pokémon still counts as having a status for interaction purposes.

## RnB Overworld
Pokémon with Magic Guard or Poison Heal do NOT take overworld damage from being poisoned.
</Element>

<Element name="Confusion">
## Duration
On infliction: `time = random(2, 6)` (i.e., 2, 3, 4, or 5 — exclusive of 6).
Exception: Axe Kick confusion starts at minimum 3 (`random(3, 6)` = 3, 4, or 5).
The time counter is decremented **before** each check. When it reaches 0, the Pokémon snaps out and acts normally that turn — no confusion effect on the wake turn. This means the effective number of turns on which confusion can trigger = stored_time − 1:
- stored time 2 → 1 turn of possible confusion
- stored time 3 → 2 turns
- stored time 4 → 3 turns
- stored time 5 → 4 turns
So confusion lasts **1–4 effective turns** (or 2–4 for Axe Kick).

## Turn Resolution
Each turn:
1. Decrement confusion time
2. If time reaches 0: confusion ends (Pokémon snaps out), acts normally
3. Otherwise: 33% chance to hit itself (see below)
4. If not hitting itself: proceed with intended move

## Self-Hit Damage
Confusion self-hit: 40 BP, Physical, typeless (`'???'` type), no STAB, no type effectiveness.
Uses the confused Pokémon's **boosted** Attack and **boosted** Defense:
```
attack = calculateStat('atk', pokemon.boosts['atk'])
defense = calculateStat('def', pokemon.boosts['def'])
baseDamage = trunc(trunc(trunc(trunc(2 * level / 5 + 2) * 40 * attack) / defense) / 50) + 2
damage = trunc(baseDamage, 16)  # 16-bit truncation
damage = randomize(damage)      # applies standard 85-100 random roll
damage = max(1, damage)
```
No critical hits possible. The Pokémon is both attacker and defender for this hit.

## Infatuation (RnB Change)
Vanilla: Infatuation only works between Pokémon of opposite gender.
RnB: Infatuation is NOT limited by gender — any Pokémon can be infatuated with any other, regardless of gender.

## Infatuation Mechanics
50% chance to be unable to act each turn while infatuated (separate from confusion).
</Element>

<Element name="Screens">
## Overview
Reflect, Light Screen, and Aurora Veil are side conditions on the defending side. They apply final modifiers to incoming damage.

## Reflect
- Applies to: Physical moves only
- Final modifier: ×0.5 in Singles (2048/4096); ×2732/4096 ≈ ×0.667 in Doubles/Triples
- Does NOT apply when the hit is a critical hit
- Does NOT stack with Aurora Veil (if Aurora Veil is active, Reflect does not apply)
- Infiltrator ignores Reflect

## Light Screen
- Applies to: Special moves only
- Final modifier: ×0.5 in Singles (2048/4096); ×2732/4096 ≈ ×0.667 in Doubles/Triples
- Does NOT apply when the hit is a critical hit
- Does NOT stack with Aurora Veil (if Aurora Veil is active, Light Screen does not apply)
- Infiltrator ignores Light Screen

## Aurora Veil
- Applies to: Both Physical AND Special moves
- Final modifier: ×0.5 in Singles (2048/4096); ×2732/4096 ≈ ×0.667 in Doubles/Triples
- Does NOT apply when the hit is a critical hit
- Overrides Reflect and Light Screen — those do not apply when Aurora Veil is active
- Infiltrator ignores Aurora Veil

## Stacking
Reflect/Light Screen do NOT stack with Aurora Veil. Only one multiplier is applied.
Screens DO stack with Friend Guard (separate final mod of ×0.75).

## Doubles Multiplier
In non-Singles formats: `2732/4096 = ~0.6674` instead of `0.5`. This is approximate (not exact ×2/3).

## Infiltrator
Attacker with Infiltrator: before damage calculation, `isReflect`, `isLightScreen`, and `isAuroraVeil` are all set to `false` on the defender's side. The attacker always penetrates all three screens.

## Critical Hit Bypass
All three screens are bypassed on critical hits (the `!isCritical` condition gates all screen modifiers).

## RnB Overworld
Aurora Veil is permanently set for the opponent in Seafloor Cavern (can still be Defogged or broken).
</Element>

<Element name="Entry Hazards">
## Overview
Side conditions that deal damage or apply effects when the opposing Pokémon switches in. All hazards are bypassed by Heavy-Duty Boots.

## Heavy-Duty Boots
All entry hazards are completely ignored by the holder of Heavy-Duty Boots.

## Stealth Rock
- Type: Rock (takes full type effectiveness from the Gen 8 type chart)
- Maximum layers: 1
- Damage formula:
  ```
  typeMod = clamp(typeEffectiveness(Rock vs defender's type(s)), -6, 6)
  damage = maxHP * (2 ^ typeMod) / 8
  ```
  Where `typeMod` is the exponent: 0 for neutral (1× effective → damage = maxHP/8), +1 for 2× (maxHP/4), +2 for 4× (maxHP/2), -1 for 0.5× (maxHP/16), -2 for 0.25× (maxHP/32).
- Standard damage table:
  | Effectiveness vs. Rock | Damage     |
  |------------------------|------------|
  | 4×                     | 1/2 max HP |
  | 2×                     | 1/4 max HP |
  | 1×                     | 1/8 max HP |
  | 0.5×                   | 1/16 max HP|
  | 0.25×                  | 1/32 max HP|
- Common type matchups vs. Rock: Flying/Fire/Ice/Bug = 2× (1/4 HP); Rock/Normal/Poison/etc. = 1× (1/8 HP); Fighting/Ground/Steel/Water/Grass = 0.5× (1/16 HP). Notable: Flying-type Pokémon take **2× (super-effective)** damage from Stealth Rock, receiving 1/4 max HP.
- Can only have 1 layer (re-using has no effect).
- Multiscale/Shadow Shield: these abilities only apply while the Pokémon is at full HP. In the actual battle engine, Stealth Rock deals damage during switch-in, which reduces HP below full before any attack lands — so Multiscale will not be active after a Stealth Rock switch-in unless the Pokémon healed back to full. The ability simply checks `curHP === maxHP` at the time of the incoming attack.

## Spikes
- Only affects grounded Pokémon (Flying types, Levitate, Air Balloon, and Gravity interactions apply — see Grounding).
- Maximum layers: 3
- Damage formula: `damage = damageAmounts[layers] * maxHP / 24`
  | Layers | Raw fraction | Actual      |
  |--------|--------------|-------------|
  | 1      | 3/24         | 1/8 max HP  |
  | 2      | 4/24         | 1/6 max HP  |
  | 3      | 6/24         | 1/4 max HP  |
- Poison-types are NOT immune. Only grounding status matters.
- Multiscale/Shadow Shield: same as Stealth Rock — Spikes deal damage on switch-in, reducing HP below full before any attack. The ability checks `curHP === maxHP` at attack time. A Flying-type Pokémon that is grounded (via Gravity or Iron Ball) would take Spikes damage and thus also lose Multiscale.

## Toxic Spikes
- Only affects grounded Pokémon.
- Maximum layers: 2
- On switch-in of a grounded non-Poison, non-Steel type:
  - 1 layer: inflicts Poison (psn)
  - 2 layers: inflicts Bad Poison (tox)
- **Poison-type Pokémon landing on Toxic Spikes:** absorbs them entirely (removes the side condition), no status inflicted.
- Steel-type Pokémon: unaffected (not absorbed, just ignored).
- Heavy-Duty Boots: bypasses entirely.

## Sticky Web
- Only affects grounded Pokémon.
- Maximum layers: 1
- Effect: lowers Speed by 1 stage on switch-in.
- The boost is applied as if from the opposing side's active Pokémon (for Defiant/Competitive interactions).
- Does NOT deal damage.

## G-Max Steelsurge
- Type: Steel (takes type effectiveness, identical formula to Stealth Rock but with Steel typing)
- Maximum layers: 1
- Damage formula:
  ```
  typeMod = clamp(typeEffectiveness(Steel vs defender's type(s)), -6, 6)
  damage = maxHP * (2 ^ typeMod) / 8
  ```
- Steel type chart vs. common types: Fire/Water/Electric/Steel resistances, Fairy/Ice resistances, Poison/Bug weaknesses, Rock neutral.
- Note: Does NOT use the defender's Disguise or Ice Face for typed damage (unlike Stealth Rock) — it bypasses those effects.

## G-Max Vine Lash (vinelash)
Side condition set by G-Max Vine Lash (Rillaboom). Deals 1/6 max HP at end of each turn for 4 turns to non-Grass types on the opposing side.

## G-Max Wildfire (wildfire)
Side condition set by G-Max Wildfire (Charizard). Deals 1/6 max HP at end of each turn for 4 turns to non-Fire types.

## G-Max Cannonade (cannonade)
Side condition set by G-Max Cannonade (Blastoise). Deals 1/6 max HP at end of each turn for 4 turns to non-Water types.

## G-Max Volcalith (volcalith)
Side condition set by G-Max Volcalith (Coalossal). Deals 1/6 max HP at end of each turn for 4 turns to non-Rock types.

## Rapid Spin / Defog
Rapid Spin removes hazards from the user's side. Defog removes hazards from BOTH sides (including terrain in vanilla — but in RnB, Defog does NOT remove terrain).
</Element>

<Element name="Spread Move Penalty">
## Overview
In non-Singles formats (Doubles, Triples), moves that target multiple Pokémon simultaneously have reduced power.

## Trigger Condition
Move must have target `'allAdjacent'` or `'allAdjacentFoes'` AND the game type must NOT be `'Singles'`.

## Modifier
```
baseDamage = pokeRound(OF32(baseDamage * 3072) / 4096)   # ×0.75
```
Applied after base damage calculation and before other multipliers.

## Parental Bond Interaction
Parental Bond's second hit does NOT trigger this penalty even for spread moves — but spread moves with Parental Bond do NOT get the second hit at all (the `isSpread` check blocks Parental Bond from creating a child hit).

## Expanding Force
Expanding Force in Psychic Terrain becomes a spread move (target changes to `allAdjacentFoes`) AND gets the ×1.5 BP boost. The spread penalty (×0.75) then applies on top of the BP boost in doubles. Net: ×1.5 × 0.75 = ×1.125.
</Element>

<Element name="Turn Order and Priority">
## Priority Brackets
Moves are sorted by their `priority` field first. Higher priority acts before lower priority within the same turn. Common priorities:
- +5: Helping Hand (in doubles)
- +4: Protect, Detect, Spiky Shield, etc.
- +3: Fake Out, Quick Guard, etc.
- +2: Extreme Speed
- +1: Quick Attack, Mach Punch, etc.
- 0: Most moves
- -1: Vital Throw
- -3: Focus Punch
- -6: Trick Room, Whirlpool (forced last)
- -7: Counter, Mirror Coat (forced last)

## Within a Priority Bracket
The faster Pokémon acts first. Speed is compared after all modifiers (see Speed Calculation).

## Speed Tie
If both Pokémon have identical final Speed, turn order is determined randomly (50/50).

## Trick Room
When `field.isTrickRoom` is active, the order within each priority bracket is **reversed**: slower acts first.
Trick Room does NOT change which priority brackets go first — +1 priority moves still beat 0 priority moves even in Trick Room.

## Payback / Bolt Beak / Fishious Rend
These moves compare speed-derived turn order for BP modification:
- `turnOrder = attacker.stats.spe > defender.stats.spe ? 'first' : 'last'`
  - Payback: BP doubles if attacker goes LAST (opponent faster)
  - Bolt Beak / Fishious Rend: BP doubles if attacker goes FIRST (user faster)
  - Note: ties resolve as `'last'` for the attacker (speed NOT strictly greater)

## Pursuit
BP doubles when the target is switching out (`field.defenderSide.isSwitching === 'out'`).

## Analytic
BP ×1.3 (5325/4096) if the attacker moves LAST (turnOrder !== 'first') OR if the defender is switching out.

## Priority Move Blocking (Psychic Terrain)
When Psychic Terrain is active and the defender is grounded, all moves with `priority > 0` directed at the grounded defender are blocked entirely (0 damage, returned early). See Terrain.

## Gale Wings (RnB)
In RnB, Gale Wings ALWAYS boosts Flying-type moves to +1 priority, regardless of current HP.
Vanilla gen 8: only at full HP.
**Note:** The damage calculator still checks full HP for Gale Wings (`attacker.curHP() === attacker.maxHP()`). The RnB Mechanic Changes document explicitly overrides this. The simulator should use the always-active version per the RnB change.

## Triage
Healing moves (moves with `drain` flag) get +3 priority when the user has Triage.
Note: code uses `move.drain` as a proxy for healing flag (acknowledged as a FIXME in the source).

## Queenly Majesty / Dazzling / Armor Tail
These abilities cause the holder's side to be immune to all priority moves (moves with `priority > 0`). A move with priority > 0 targeting a Pokémon protected by these abilities deals 0 damage (returned early).
</Element>

<Element name="Speed Calculation">
## Overview
Final speed is computed from the raw (boost-modified) speed plus a chain of speed modifiers, with paralysis applied last.

## Step 1: Boost-Modified Speed
```
speed = getModifiedStat(rawStats.spe, boosts.spe)
```
Uses the standard stat stage table (see Stat Stages).

## Step 2: Speed Modifiers (chainMods)
All speed multipliers are chained:
| Condition                                          | Modifier (fraction) | chainMods value |
|----------------------------------------------------|---------------------|-----------------|
| Tailwind active on user's side                     | ×2                  | 8192            |
| Unburden (abilityOn = true, item was consumed)     | ×2                  | 8192            |
| Chlorophyll + Sun/Harsh Sunshine                   | ×2                  | 8192            |
| Sand Rush + Sand                                   | ×2                  | 8192            |
| Swift Swim + Rain/Heavy Rain                       | ×2                  | 8192            |
| Slush Rush + Hail or Snow                          | ×2                  | 8192            |
| Surge Surfer + Electric Terrain                    | ×2                  | 8192            |
| Quick Feet + any status condition                  | ×1.5                | 6144            |
| Protosynthesis/Quark Drive (Speed is highest stat) | ×1.5                | 6144            |
| Slow Start (abilityOn = true)                      | ×0.5                | 2048            |
| Choice Scarf                                       | ×1.5                | 6144            |
| Iron Ball or EV-training items                     | ×0.5                | 2048            |
| Quick Powder (held by Ditto only)                  | ×2                  | 8192            |

`chainMods` uses bounds 410 to 131172.

```
speed = OF32(pokeRound((speed * chainMods(speedMods, 410, 131172)) / 4096))
```

## Step 3: Paralysis Reduction
Applied AFTER chainMods, if Pokémon has `par` status and does NOT have Quick Feet:
```
speed = floor(OF32(speed * 25) / 100)   # 25% of current speed (RnB: 75% reduction)
```

## Step 4: Cap
```
speed = min(10000, speed)    # for gen 3+
speed = max(0, speed)
```

## Trick Room Speed Comparison
Trick Room reverses the comparison: the Pokémon with LOWER final speed acts first. The speed values themselves are unchanged.

## EV-Training Items
Macho Brace, Power Anklet, Power Band, Power Belt, Power Bracer, Power Lens, Power Weight all halve speed (×0.5). Klutz does NOT suppress these items.
</Element>

<Element name="Grounding">
## Definition
A Pokémon is grounded if ANY of the following is true:
1. `field.isGravity` is active (Gravity grounds all Pokémon unconditionally)
2. The Pokémon holds an **Iron Ball** (and does not have Klutz)
3. AND simultaneously:
   - Does NOT have the Flying type
   - Does NOT have the Levitate ability
   - Does NOT hold an Air Balloon

In code: `isGrounded = field.isGravity || pokemon.hasItem('Iron Ball') || (!hasFlying && !hasLevitate && !hasAirBalloon)`

## Impact
Grounding status determines:
- Whether Spikes, Toxic Spikes, and Sticky Web affect the Pokémon on switch-in
- Whether terrain damage boosts/reductions apply
- Whether Nature Power, Terrain Pulse, Rising Voltage, Expanding Force, Misty Explosion get terrain effects
- Whether Psychic Terrain blocks priority moves targeting the Pokémon
- Whether Ground-type moves can hit the Pokémon (combined with type effectiveness — this is handled separately in getMoveEffectiveness)

## Gravity
Gravity forces ALL Pokémon to be grounded, regardless of type, ability, or item. This means:
- Flying-types take damage from Spikes/Toxic Spikes
- Flying-types are affected by terrain
- Ground-type moves can hit Flying-types and Levitators
- Pokémon with Air Balloon become grounded

## Levitate
Levitate grants non-grounded status unless Gravity is active or the Pokémon holds Iron Ball.

## Air Balloon
Air Balloon grants non-grounded status unless Gravity is active. The balloon pops when the holder takes damage.
Note: in the damage calc, Air Balloon grants immunity to Ground-type moves (separately returned early as 0 damage).

## Thousand Arrows
Thousand Arrows overrides the Ground immunity for Flying-types (typeEffectiveness is forced to 1), and also grounds the target. However, it does NOT use the isGrounded check for this — it bypasses that entirely.

## Magic Guard / Klutz
Klutz: suppresses most item effects but NOT Iron Ball's speed reduction or its grounding effect (Iron Ball halves speed even with Klutz). However, Iron Ball's grounding effect may still apply — check Klutz interactions carefully; in the calculator, `checkItem` removes the item for damage purposes if Klutz is active, but the grounding function checks `pokemon.hasItem('Iron Ball')` directly.
</Element>

<Element name="Protect">
## Standard Protect
If `field.defenderSide.isProtected` is true and the move does NOT break protect, damage calculation is skipped entirely (0 damage returned).

## Protect-Breaking Conditions
A move breaks through Protect if ANY of:
- `move.breaksProtect` is set (Feint, Phantom Force, Shadow Force, etc.)
- `move.isZ` is true (Z-moves break Protect, but deal reduced damage — see below)
- `attacker.isDynamaxed` is true (Dynamax moves break Protect, also with reduced damage)
- Attacker has Unseen Fist AND the move makes contact

## Z-Move / Dynamax vs. Protect
Z-moves and Dynamax moves DO break Protect but deal **25% damage**:
```
damageAmount = pokeRound(OF32(damageAmount * 1024) / 4096)   # ×0.25
```
This is applied in the per-roll damage step (after burn halving, before final mods).

## Guardian of Alola vs. Protect
Guardian of Alola against Protect with a Z-crystal:
```
zLostHP = ceil(zLostHP / 4 - 0.5)
```
(where zLostHP = floor(defender.curHP() * 3 / 4)). This is a separate fixed-damage path.

## Infiltrator
Infiltrator bypasses Reflect, Light Screen, and Aurora Veil but does NOT bypass Protect.

## Wide Guard / Quick Guard
These are not modeled directly in the damage calculator (they set `isProtected` on the side level).
</Element>

<Element name="Wonder Room">
## Effect
Swaps the physical Defense and Special Defense stats of all Pokémon on the field:
```
[pokemon.rawStats.def, pokemon.rawStats.spd] = [pokemon.rawStats.spd, pokemon.rawStats.def]
```

## Implementation
Applied at the start of the damage calculation via `checkWonderRoom`. The rawStats are physically swapped before any boost modifications.

## Download Interaction
Download ignores Wonder Room when determining which stat to boost. If Wonder Room is active, Download recalculates using the un-swapped (real) Def and SpD values.

## Duration
5 turns in battle (not modeled in the damage calculator — tracked externally).
</Element>

<Element name="Magic Room">
## Effect
Suppresses all held items for all Pokémon on the field.
```
checkItem: if magicRoomActive → pokemon.item = ''
```

## Klutz Interaction
Klutz ability also suppresses the item (same `checkItem` function). EV-training items (Macho Brace, Power Anklet, etc.) are NOT suppressed by Klutz (but ARE suppressed by Magic Room).

## Duration
5 turns (tracked externally).
</Element>

<Element name="Gravity">
## Effect
Forces all Pokémon to be grounded (see Grounding).
Additionally:
- Ground-type moves can hit Flying-types and Levitate users
- Flying-types and Levitators become susceptible to Spikes, Toxic Spikes, Sticky Web
- All terrain effects apply to previously airborne Pokémon
- Sky Drop fails to pick up targets (defender weighs ≥200 OR is Flying OR Gravity is active = returns 0)

## Priority Moves
Gravity does NOT block priority moves itself (that is Psychic Terrain).

## Duration
5 turns (tracked externally).
</Element>

<Element name="Trick Room">
## Effect
Reverses turn order within each priority bracket: the **slowest** Pokémon acts first.

## Does Not Affect Priority Brackets
Higher priority moves still go before lower priority moves. Trick Room only flips the ordering within each bracket.

## Speed Comparison Under Trick Room
When determining turn order, speed is compared normally and then the order is reversed. The speed values themselves are not changed. Gyro Ball, Electro Ball, and other speed-dependent move BPs still use raw speed values.

## Trick Room vs. Speed Ties
If two Pokémon have equal speed in Trick Room, order is still determined randomly (50/50).

## Duration
5 turns, with reuse resetting/ending the effect (tracked externally).
</Element>

<Element name="Parental Bond">
## Overview
Parental Bond causes single-hit moves to hit twice. The second hit (child) deals reduced damage.

## Trigger Conditions
Parental Bond creates a child hit if ALL of:
- Attacker has Parental Bond ability
- `move.hits === 1` (not already a multi-hit move)
- Move is NOT a spread move (isSpread = false)

## Child Hit Modifier
The child hit receives a ×0.25 modifier to base damage:
```
baseDamage = pokeRound(OF32(baseDamage * 1024) / 4096)
```
This is applied via the `Parental Bond (Child)` pseudo-ability.

## Fixed Damage Moves
Fixed-damage moves (Seismic Toss, Dragon Rage, etc.) both hits deal the full fixed damage (no 0.25× reduction).

## Multi-Hit Boosts
Between the parent and child hit, `checkMultihitBoost` is called. This can update attacker/defender stats (e.g., Stamina boosts on the defender, Power-Up Punch boost on the attacker, White Herb consumption).

## Assurance
Assurance doubles BP if the defender has the `Parental Bond (Child)` pseudo-ability active (i.e., Parental Bond's second hit always triggers Assurance's bonus).

## Multiscale Interaction
Multiscale is bypassed on the child hit (the `!attacker.hasAbility('Parental Bond (Child)')` check in Multiscale's condition).

## Spread Moves
Parental Bond does NOT generate a second hit for spread moves. The move applies normally (with spread penalty) as a single hit.
</Element>

<Element name="Doubles Support Modifiers">
## Helping Hand
Boosts the ally's move BP by ×1.5 (6144/4096):
```
if (field.attackerSide.isHelpingHand)
    bpMods.push(6144)
```
Applied in the BP modifier phase.

## Battery
Boosts Special moves used by the ally by ×1.3 (5325/4096):
```
if (field.attackerSide.isBattery && move.category === 'Special')
    bpMods.push(5325)
```

## Power Spot
Boosts all moves used by the ally by ×1.3 (5325/4096):
```
if (field.attackerSide.isPowerSpot)
    bpMods.push(5325)
```

## Friend Guard
Reduces damage dealt to the ally by ×0.75 (3072/4096):
```
if (field.defenderSide.isFriendGuard)
    finalMods.push(3072)
```
Applied in the final modifier phase. Stacks multiplicatively with screens.

## Flower Gift (Doubles)
When a Cherrim with Flower Gift or a field-wide Flower Gift condition is active in Sun:
- Physical Attack of allies: ×1.5 (6144/4096)
- Special Defense of allies: ×1.5 (6144/4096)
These are applied as attack/defense modifiers, not BP mods.
</Element>

<Element name="Foresight and Odor Sleuth">
## Effect
`field.defenderSide.isForesight = true` removes the Ghost-type's immunity to Normal and Fighting type moves.

## Implementation
In `getMoveEffectiveness`:
```
if ((isRingTarget || isGhostRevealed) && type === 'Ghost' && move.hasType('Normal', 'Fighting'))
    return 1   # neutral, not immune
```
`isGhostRevealed = attacker.hasAbility('Scrappy') || field.defenderSide.isForesight`

## Scrappy
Scrappy ability has the same effect as Foresight for Normal and Fighting moves vs. Ghost-types.
</Element>

<Element name="Flinch">
## Effect
A flinched Pokémon cannot move that turn. Duration is 1 turn.

## Timing
Flinch only works if the flinch-causing move hits BEFORE the flinched Pokémon would act. If the flinched Pokémon moves first (higher speed or priority), the flinch has no effect for that turn.

## Inner Focus (Gen 8+)
In Gen 8+, Inner Focus blocks flinching entirely (and also blocks Intimidate).
</Element>

<Element name="Partial Trap">
## Effect
Binding moves (Wrap, Fire Spin, Clamp, etc.) trap the target for 5-6 turns and deal residual damage each turn.

## Duration
- Normal binding: 5 or 6 turns (`random(5, 7)` = 5 or 6)
- With Grip Claw: 8 turns

## Residual Damage Per Turn
- Normal: 1/8 of base max HP
- With Binding Band (user holds it): 1/6 of base max HP

Formula: `damage = baseMaxHP / effectState.boundDivisor` (8 or 6).

## Trapping
The target cannot switch out while bound (unless they use a switching move, have Shed Shell, etc.).

## G-Max Centiferno / G-Max Sandblast
Continue to deal damage even after the user leaves the field (unlike regular binding moves which end when the user switches out).
</Element>

<Element name="Hidden Power">
## Overview
Hidden Power's type is determined by the holder's IV spread. Power is fixed at 60 in Gen 6+.

## Gen 3-8 Type Determination
```
hpTypeX = sum(i * (ivs[stat_i] % 2)) for i = 1, 2, 4, 8, 16, 32 (HP, Atk, Def, Spe, SpA, SpD)
type = HP_TYPES[floor(hpTypeX * 15 / 63)]
```
Type index maps to: Fighting, Flying, Poison, Ground, Rock, Bug, Ghost, Steel, Fire, Water, Grass, Electric, Psychic, Ice, Dragon, Dark (0–15).

## Power
Gen 6+: always 60 BP.

## RnB (Gen 8)
Hidden Power is always 60 BP. Type determined by IVs as above.
Hidden Power cannot be Fire, Ground, Water, Grass, Electric, Psychic, Ice, Dragon, or Dark if those IVs are set to even values for the low bit.

## Normal/Fairy Excluded
Hidden Power can never be Normal or Fairy type.
</Element>

<Element name="Nature">
## Effect
Natures apply a ×1.1 or ×0.9 multiplier to one non-HP stat each. Neutral natures apply ×1.0 to all stats.

## Application
Applied in stat calculation:
```
rawStat = floor(floor((...base formula...)) * natureMultiplier)
```
where natureMultiplier = 1.1 if the stat is `nature.plus`, 0.9 if `nature.minus`, 1.0 otherwise.

## Neutral Natures
If `nature.plus === nature.minus` (e.g., Hardy, Docile, Serious, Bashful, Quirky), the multiplier is 1.0 for all stats.

## Impact on Damage
Natures affect raw stats, which then feed into getModifiedStat and ultimately attack/defense values. A +nature in Attack gives effectively ×1.1 to all physical damage output (compared to neutral).

## RnB
Natures work as in Gen 8. The Synchronize leading mechanic (50% chance to force wild encounter nature) applies but does not affect battle damage calculations.
</Element>

<Element name="Leech Seed">
## Effect
At the end of each turn, the seeded Pokémon loses 1/8 of its max HP, which is transferred to the Pokémon that planted it.

## Implementation
`field.defenderSide.isSeeded` tracks the seeded state. Residual drain: 1/8 max HP.

## Grass-Type Immunity
Grass-type Pokémon cannot be affected by Leech Seed.

## Liquid Ooze
If the seeded Pokémon has Liquid Ooze, the HP is drained from the recipient instead of healing it.

## Magic Guard
Magic Guard blocks Leech Seed damage on the holder.

## Switching Out
Leech Seed is removed when the seeded Pokémon switches out.
</Element>

<Element name="Substitute">
## Effect
`field.defenderSide.isSubstitute = true` indicates the defending side has a Substitute active.
Most moves target the Substitute instead of the Pokémon. The Substitute absorbs damage until its HP is depleted (= 1/4 of creator's max HP).

## Substitute vs. Status
Most status-inflicting moves and secondary effects are blocked by Substitute. Sound-based moves (flag `sound`) bypass Substitute.

## Infiltrator
Infiltrator bypasses Substitute in addition to screens.

## Multi-Hit and Substitute
Each hit of a multi-hit move can be absorbed/broken by Substitute independently.
</Element>
