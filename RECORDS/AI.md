# AI Move Selection — Run & Bun v1.07

Sources:
- `AI.md` (Croven, v1.07 documentation)
- `Post-KO Switch-in AI.csv`
- `syl-rnb-calc-main/calc/src/ai.ts` (authoritative implementation)

The AI calculates a score for every move, then picks the highest. Ties are broken randomly (uniform over all tied moves). In Doubles the AI calculates a score per-move per-target.

---

## 1. Core Scoring Baselines

These numbers are the foundation everything else stacks on.

| Situation | Score |
|---|---|
| Highest-damage move (HD), no kill | +6 (80%) or +8 (20%) |
| Default status move (no special rule) | +6 |
| Non-HD damaging move | +0 |

### Kill Bonuses (additive on top of HD or base score)

Applied to every damaging move that kills — regardless of whether it is the HD move:

| AI speed vs player | Kill bonus |
|---|---|
| AI faster (or move has priority) | +6 |
| AI slower | +3 |

If the AI has **Moxie, Beast Boost, Chilling Neigh, or Grim Neigh**: add an additional **+1** on top of the kill bonus.

Multiple killing moves all receive the HD base (+6/+8) in addition to the kill bonus.

### Common Total Kill Scores

| AI speed | HD roll | Base kill score |
|---|---|---|
| Faster | +6 | 12 |
| Faster | +8 | 14 |
| Slower | +6 | 9 |
| Slower | +8 | 11 |

With Moxie/Beast Boost/Chilling Neigh/Grim Neigh, add 1 to each of the above.

---

## 2. Highest-Damage (HD) Exclusions

The following moves are **never** included in the HD competition — they do not receive the +6/+8 HD base score, and never count as "the highest damaging move" when multiple moves exist:

- Explosion, Self-Destruct, Misty Explosion  
- Final Gambit  
- Rollout  
- Relic Song  
- Meteor Beam  
- Future Sight  
- Counter, Mirror Coat  ← **not in AI.md; code-only**
- All damaging trapping moves (Whirlpool, Fire Spin, Sand Tomb, Magma Storm, Infestation, Wrap, Bind)

**Kill bonuses still apply** to all of the above (except Explosion, Final Gambit, and Rollout — those skip kill-bonus scoring entirely as well, per the code). Relic Song, Meteor Beam, Future Sight, and trapping moves do receive kill bonuses when they kill.

---

## 3. Kill Detection (`getAISeesKill`)

Used to suppress conditional bonuses on sleep and poison moves when the AI already sees a kill. Checks the final post-boost score of each move against a threshold list.

**Standard kill-score thresholds:** `[9, 11, 12, 14]`

**Exception-move kill-score thresholds** (for Relic Song, Meteor Beam, Future Sight, and trapping moves — these skip HD, so their kill scores are lower): `[3, 6]`

**With Moxie / Beast Boost / Chilling Neigh / Grim Neigh**, all thresholds shift up by 1:
- Standard: `[10, 12, 13, 15]`
- Exception: `[4, 7]`

---

## 4. "AI Dead to Player" Check (`aiDeadToPlayer`)

`aiDeadToPlayer = playerHighestRoll >= aiCurrentHP`

**Exception:** If AI has **Sturdy** or is holding a **Focus Sash** and is at **exactly 100% HP**, `aiDeadToPlayer` is always false regardless of player damage.

The player's "highest roll" is calculated as:
- Take the maximum value from that move's damage rolls
- If the player's move is flagged as a crit, de-crit it: `max_roll / 1.5` (or `/ 2.25` if player has Sniper)
- For multi-hit moves, multiply by hit count (Skill Link → 5 hits for 3-hit moves)

`aiTwoHKOd = playerHighestRoll * 2 >= aiCurrentHP`  
`aiThreeHKOd = playerHighestRoll * 3 >= aiCurrentHP`

---

## 5. Player Incapacitation Check

```
playerIncapacitated = (playerStatus == "frz") OR (playerStatus == "slp")
```

**Code-only caveat:** The AI.md also lists "recharging" (e.g. after Hyper Beam) and "loafing around due to Truant" as incapacitation triggers. **These are not implemented in the code.** Only frozen and sleeping count.

---

## 6. Priority-Move Special Rules

### +11 bonus for priority when AI is dead and slower
If `aiDeadToPlayer AND !aiFaster`, every damaging priority move gets **+11** additively.

Moves with `move.priority > 0` qualify. **Grassy Glide in Grassy Terrain** also qualifies (treated as priority for this bonus only).

### Psychic Terrain blocks priority (−40)
Any move with `move.priority > 0` in **Psychic Terrain** receives an additional **−40**. This is not mentioned in AI.md. Note: the Grassy Glide special case does NOT use `move.priority > 0`, so Grassy Glide is not blocked by Psychic Terrain.

---

## 7. Move Scoring Reference

Scores listed are the final additive bonus on top of whatever the HD calc already gave the move. Start from the HD score (0 if not HD, 6/8 if HD) and add the values below.

### Acid Spray
Always **+6** (regardless of HD status — stacks with HD and kill bonuses).

### Agility / Rock Polish / Autotomize
- AI slower: **+7**
- AI faster: **−20**

### Baton Pass
- AI is last mon out: **−20**
- AI behind Substitute OR has any positive stat stage: **+14**
- Otherwise (no sub, no boosts): **+0** ← the default status +6 is suppressed; score stays at 0

### Belly Drum
Checked before the move scores:
- AI at max Attack stage (+6) → **−40** (useless)
- Using Belly Drum would leave AI at ≤0 HP → **−40** (useless)
- Player incapacitated: **+9**
- Player is NOT incapacitated and AI is not dead after Belly Drum (factoring in Sitrus Berry recovery): **+8**
- Otherwise: **+4**

Sitrus Berry: recovery = `floor(maxHP / 4)` added to current HP when checking survival.

### Counter / Mirror Coat
Excluded from HD. Never used (−20) if:
- AI dead to player and no Sturdy/Focus Sash at full HP
- Target immune (Ghost type for Counter; Dark type for Mirror Coat)
- Player has NO moves of the corresponding split (all-status moveset, or 0-BP moves only for the split)

Otherwise, base score: **+6**

Conditional bonuses (all stackable):
- Player has Sturdy/Focus Sash at full HP and player can OHKO AI and player only has moves of the corresponding split: **+2**
- Player cannot OHKO AI and player only has moves of the corresponding split: **+2** (80% of the time)
- AI is faster: **−1** (25% of the time)
- Player has any status move: **−1** (25% of the time)

### Damaging Speed-Reduction Moves (Icy Wind, Electroweb, Rock Tomb, Mud Shot, Low Sweep, Bulldoze)
**Only applied when this move is NOT the HD move.** If it is the HD move, it receives the normal +6/+8 HD score and none of the below applies.

When not HD:
- Player does NOT have Contrary / Clear Body / White Smoke AND AI is slower: **+6**
- Otherwise (player has one of those abilities, or AI is faster): **+5**

Note: **Bulldoze** is included in this list in the code but is absent from AI.md.

Doubles only (not implemented in singles calc): Icy Wind and Electroweb get an additional +1.

### Damaging Atk/SpAtk Reduction Moves (Skitter Smack, Trop Kick, Snarl, Mystical Fire, Breaking Swipe)
**Only applied when this move is NOT the HD move.**

- Trop Kick and Breaking Swipe check for Physical moves on the player
- Skitter Smack, Snarl, and Mystical Fire check for Special moves on the player

When not HD:
- Player does NOT have Contrary / Clear Body / White Smoke AND player has at least one damaging move of the corresponding split (BP > 0 or in zeroBPButNotStatus): **+6**
- Otherwise: **+5**

Note: **Breaking Swipe** (Physical, lowers Atk) and **Snarl / Mystical Fire** (Special-lowering) are in the code but absent from AI.md.

### Destiny Bond
- AI faster and dead to player: base **+6**, then **+1** additional at 81% rate → effective **+6** (19%) or **+7** (81%)
- AI slower: base **+5**, then **+1** additional at 50% rate → effective **+5** (50%) or **+6** (50%)

### Encore
- Player first turn out (or already Encored): **−40**
- AI faster and "encore incentive" (player's last move is something worth Encoring — mostly non-damaging moves): **+7**
- AI faster and NOT encore incentive: **+6** (falls through to default status score; no modifier applied)
- AI slower: base **+5**, +1 additional at 50% rate → effective **+5** (50%) or **+6** (50%)

### Explosion / Self-Destruct / Misty Explosion
Never used (−40) if:
- Target is immune (no valid damage rolls)
- AI is last mon and player is NOT also on last mon

When usable, score based on AI's current HP%:
- Below 10%: **+10** (100%)
- Below 33%: **+8** (70%) → else 0
- Below 66%: **+7** (50%) → else 0
- Otherwise: **+7** (5%) → else 0

If both AI and player are on their last mon: additional **−1** always.

### Fake Out
- First turn out AND player does NOT have Shield Dust or Inner Focus AND move has valid damage rolls (target not type-immune): scored as a **normal damaging move** (highest-damage odds + kill bonus when it KOs, faster→+6/slower→+3), with an **additional +9** stacked on every score (mirrors Acid Spray's +6). So a faster first-turn KO scores 12/14 **+9** = 21/23.
- Otherwise (not first turn, blocked by Shield Dust / Inner Focus, or no valid damage): **−40**

### Fell Stinger
When AI is NOT at max Attack (+6) and Fell Stinger kills:
- AI faster: scores are forced to a **total of +21** (80%) or **+23** (20%) — code adjusts by computing `21 - currentScore` and adds **+2** at 20%
- AI slower: **total of +15** (80%) or **+17** (20%)

When AI IS at max Attack, or Fell Stinger does not kill: treated as a normal damaging move.

### Final Gambit
Excluded from HD. Score:
- AI faster AND AI's current HP (raw number) strictly greater than player's current HP: **+8**
- AI faster AND dead to player (but HP ≤ player HP): **+7**
- Otherwise: **+6**

### Flame Charge
When Flame Charge is NOT the HD move, AI is slower, and has valid damage rolls: **+6** (treated like a speed-reduction move). Not in AI.md.

### Focus Energy / Laser Focus
Never used (−40) if:
- Focus Energy already active on AI's side (Focus Energy only)
- Player has Shell Armor or Battle Armor
- AI is dead to player

Otherwise:
- AI has Super Luck or Sniper, or holds Scope Lens, or has a high-crit-rate move: **+7**
- Otherwise: **+6**

### Future Sight
Excluded from HD. Score (before kill bonuses):
- AI faster AND dead to player: **+8**
- Otherwise: **+6**

Kill bonuses stack on top.

### Helping Hand / Follow Me
In singles (current calc): **−6** always. (Score is −6 because the default +6 is suppressed when these moves are added to moveStringsToAdd.) Effectively disabled in singles.

### Imprison
- AI and player share at least one move AND player is not already Imprisoned: **+9**
- Otherwise: **−20**

### Light Screen / Reflect
Never used (−40) if the corresponding screen is already active.

Otherwise, base score: **+6**
- Player has at least one damaging move of the corresponding split (Physical for Reflect, Special for Light Screen), with BP > 0 or in zeroBPButNotStatus:
  - If AI holds Light Clay: additional +1 (always)
  - Additional +1 at 50% probability

Maximum possible score: **+8** (if player has corresponding move, AI has Light Clay, and 50% RNG fires).

### Magnet Rise
Not in AI.md. From code:
- Already Magnet Risen: **−40**
- AI faster AND player has a damaging Ground-type move: **+8**
- Otherwise: **+5**

### Memento
Never used (−40) if AI is last mon.

When usable, score based on AI's current HP%:
- Below 10%: **+16** (100%)
- Below 33%: base **+6** always, +8 additional at 70% → effective **+6** (30%) or **+14** (70%)
- Below 66%: base **+6** always, +7 additional at 50% → effective **+6** (50%) or **+13** (50%)
- Otherwise: base **+6** always, +7 additional at 5% → effective **+6** (95%) or **+13** (5%)

### Meteor Beam
Excluded from HD.
- Holding Power Herb: **+9** (kill bonuses stack if it kills)
- Otherwise: **−20**

### Poisoning Moves (Toxic, Poison Gas, Poison Powder)
Never used (−40) if:
- Player already has a status condition
- Player is Poison or Steel type AND AI does not have Corrosion

Otherwise, base score: **+6**

Additional bonus (38% of the time), only when AI does NOT see a kill AND player is above 20% HP:
- If all player moves deal 0 damage AND AI has Hex, Venom Drench, or ability Merciless: **+2**
- Otherwise: **+0** (no additional bonus in this branch)

**Code discrepancy:** AI.md lists Venoshock as a qualifying combo move alongside Hex and Venom Drench. **Venoshock is not in the code.** Only Hex, Venom Drench, and ability Merciless are checked.

**[C++ status: resolved/not applicable — the entire Hex/Venom Drench/Merciless +2 combo bonus is absent from the C++ implementation; dist_poison_move returns a flat +6 (ai_scorer_dist.cpp:218). The ai.ts combo-bonus block was not ported; Venoshock's absence within it is moot.]**

### Protect / King's Shield / Spiky Shield / Baneful Bunker / Detect / Obstruct
All scored identically.

Never used (−20) if:
- Protect used last **two** consecutive turns
- AI would be killed by secondary damage (status damage + weather damage) after protecting (see Secondary Damage section below)

Otherwise, base score: **+6**

Modifiers:
- AI has burn, poison (regular or toxic), or `protectDisincentive` flag is set (covers cursed, infatuated, Perish Songed, Leech Seeded, Yawned): **−2**
- Player has burn, poison, or `protectIncentive` flag is set: **+1**
- AI's first turn out (singles only): **−1**

50% chance of −20 if Protect was used last turn (but not two consecutive turns).

**Secondary damage check for Protect veto:**  
`statusDamage + weatherDamage >= aiCurrentHP`  
- Burn: `floor(maxHP / 16)` per turn  
- Poison (psn): `floor(maxHP / 8)` per turn  
- Toxic (tox): `floor(maxHP / 16) * toxicCounter` per turn  
- Sand damage: `floor(maxHP / 16)` — immune: Rock, Steel, Ground types; Sand Force, Sand Rush, Sand Veil, Magic Guard, Overcoat abilities; Safety Goggles  
- Hail damage: `floor(maxHP / 16)` — immune: Ice type; Ice Body, Snow Cloak, Magic Guard, Overcoat; Safety Goggles  

Special doubles note (Clifford + Macey fight): Passimian's Detect gets an additional **+8** because its partner has Huge Power and it has Receiver — total score +14.

### Pursuit
Scores stack additively with kill bonuses from HD calc:
- Can kill player: additional **+10**
- Cannot kill but player HP < 20%: additional **+10**
- Cannot kill but player HP < 40%: additional **+8** (50% of the time)
- AI faster (regardless of above): additional **+3**

### Recovery Moves (Recover, Slack Off, Heal Order, Soft-Boiled, Roost, Strength Sap)
- At exactly 100% HP: **−20**
- At ≥85% HP (and < 100%): **−6**
- Below 85%: base **+5**, then **+2** at a rate equal to `shouldAIRecover(0.5)` probability (see Recovery Logic below)

### Sun-Based Recovery (Morning Sun, Synthesis, Moonlight)
- At exactly 100% HP: **−20**
- At ≥85% HP: **−6**
- Below 85% and Sun is active: uses `shouldAIRecover(1.0)` for the recovery check. **Bug:** the heal rate is hardcoded as 1.0 (100%) rather than the actual 2/3 (67%). This inflates the recovery probability in Sun.
- Below 85% and Sun is NOT active: falls through to standard recovery move scoring (50% heal rate).

Combined rate when Sun is active: `sunRate + (1 - sunRate) * standardRate` where `sunRate = shouldAIRecover(1.0)` and `standardRate = shouldAIRecover(0.5)`.

### Recovery Logic (`shouldAIRecover`)

Immediate returns 0 (don't recover):
- AI has Toxic status
- `playerMaxRoll >= floor(maxHP * recoveryPercentage)` — if player can deal in one hit as much as or more than the recovery would restore

When AI is **faster**:
- Player can kill AI right now BUT cannot kill after recovery: return 1.0
- Player cannot kill AI AND 40% < AI HP% < 66%: return 0.5
- Player cannot kill AI AND AI HP% ≤ 40%: return 1.0
- All other cases: return 0

When AI is **slower**:
- AI HP% < 50%: return 1.0
- AI HP% < 70% (and ≥50%): return 0.75
- At exactly 70% or above: return 0

Default: return 0

### Relic Song
Excluded from HD.
- Meloetta base form: **+10** (kill bonuses stack)
- Meloetta-Pirouette form: **−20**

### Rest
- At exactly 100% HP: **−20**
- At ≥85% HP: **−6**
- Below 85%: base **+5**, then +2 at `shouldAIRecover(1.0)` probability, then an additional +1 at `shouldAIRecover(1.0) * restIncentive` probability

`restIncentive = 1` if any of the following:
- Holding Lum Berry or Chesto Berry
- AI has Sleep Talk or Snore
- AI has Shed Skin or Early Bird
- AI has Hydration and weather is any Rain variant

### Rollout
Always **+7** (no other modifications).

### Scary Face
Not in AI.md. From code:
- AI slower: **+6**
- AI faster: **−20**

### Setup Moves — General Rules

All of the following are **never used (−40)** if `aiDeadToPlayer` is true — **with exceptions:**
- Power-Up Punch, Swords Dance, and Howl are NOT blocked by `aiDeadToPlayer`
- All setup moves are blocked by **Unaware** on the player EXCEPT Power-Up Punch, Swords Dance, and Howl

Full list of moves subject to general setup rules:
Power-Up Punch, Swords Dance, Howl, Stuff Cheeks, Barrier, Acid Armor, Iron Defense, Cotton Guard, Charge Beam, Tail Glow, Nasty Plot, Cosmic Power, Bulk Up, Calm Mind, Dragon Dance, Coil, Hone Claws, Quiver Dance, Shift Gear, Shell Smash, Growth, Work Up, Curse, No Retreat

Charge Beam and Power-Up Punch are additionally treated as useless (−40) if they have no valid damage rolls (e.g. Ground-immune target for Charge Beam; Ghost-immune target for Power-Up Punch).

### Setup Moves — Offensive Setup
Applies to: Dragon Dance, Shift Gear, Swords Dance, Howl, Sharpen, Meditate, Hone Claws, Charge Beam, Power-Up Punch, Growth

Base score: **+6**
- Player incapacitated (frozen or sleeping only — see note above): **+3**
- AI slower AND 2HKOd by player: **−5**

Note: Contrary bypasses the 2HKO penalty (see Contrary section).

### Setup Moves — Defensive Setup
Applies to: Acid Armor, Barrier, Cotton Guard, Harden, Iron Defense, Stockpile, Cosmic Power

Base score: **+6**
- AI slower AND 2HKOd by player: **−5**

95% of the time, additionally:
- Player incapacitated: **+2**
- Move boosts both Def and SpDef (Stockpile, Cosmic Power) AND AI is below +2 in either: **+2**

### Setup Moves — Coil / Bulk Up / Calm Mind / Quiver Dance / No Retreat
(Curse when AI is not Ghost type is treated identically to Bulk Up here)

These are classified as Defensive Setup or Offensive Setup depending on the player's moveset:

- **Coil, Bulk Up, No Retreat, Curse (non-Ghost):** Defensive if player has Physical but NO Special attacking moves; Offensive otherwise.
- **Calm Mind, Quiver Dance:** Defensive if player has Special but NO Physical attacking moves; Offensive otherwise.

After classification, apply the corresponding Offensive or Defensive scoring.

"Attacking moves" for this check means moves with BP > 0, OR moves in the `zeroBPButNotStatus` list (excluding `(No Move)`), AND the move must not be a status move.

### Setup Moves — Agility / Rock Polish / Autotomize
Separate category:
- AI slower: **+7**
- AI faster: **−20**

### Setup Moves — Tail Glow / Nasty Plot / Work Up
Base score: **+6**
- Player incapacitated: **+3**
- Player NOT incapacitated AND player cannot 3HKO AI: **+1** additional; if AI is also faster: **+1** more
- AI slower AND 2HKOd: **−5**
- AI at ≥ +2 SpAtk: **−1**

### Setup Moves — Shell Smash
Base score: **+6**
- Player incapacitated: **+3**
- Survival check (see below): +2 or −2
- AI at +1 or higher Attack stage: **−20** (never used)
- AI at +6 SpAtk: **−20** (never used)
  - Asymmetric condition: SpAtk at +1–+5 does NOT block Shell Smash; only full +6 does

Survival check:
- If AI has Focus Sash and is at full HP: treated as not dead → **+2**
- If AI has White Herb OR AI is slower: use `playerHighestRoll` directly; if roll kills → **−2**, else → **+2**
- If AI is faster (and no White Herb): recalculate player damage vs AI stat line boosted by +2 Atk/SpAtk/Spe and −1 Def/SpDef; if that kills → **−2**, else → **+2**

### Substitute
Never used (−40) if:
- Player has Infiltrator
- AI HP% ≤ 50%
- Substitute already active on AI's side  ← **not in AI.md**

Otherwise, base score: **+6**
- Player sleeping: **+2**
- Player Leech Seeded AND AI faster: **+2**
- Player has any sound-based move: **−8**
- Additional **−1** at 50% probability (always)

### Sucker Punch
If Sucker Punch was used last turn: additional **−20** (50% of the time). The other 50% there is no penalty. Whether the move failed or not does not matter.

### Tailwind
- Already active: **−40**
- AI slower: **+9**
- AI faster: **+5**

### Taunt
- Player already Taunted: **−40**
- Player has Trick Room AND Trick Room is not active: **+9**
- Player has Defog AND Aurora Veil is active AND AI faster: **+9**
- Otherwise: **+5**

### Terrain Moves (Electric Terrain, Psychic Terrain, Grassy Terrain, Misty Terrain)
- Terrain already active: **−40**
- Holding Terrain Extender: **+9**
- Otherwise: **+8**

### Thunder Wave / Stun Spore / Glare / Nuzzle
Never used (−40) if any of the following:
- Player already has a status condition
- Move is Electric type AND player is Ground or Electric type
- Player has Limber
- Move is Stun Spore AND player is Electric type ← see Bug below
- Move is Glare ← **Always triggers −40 due to operator precedence bug** (see Bugs section)

Otherwise:
- AI is slower but would be faster after paralysis (player speed > AI speed > floor(player speed / 4)), OR AI has Hex, OR player is infatuated or confused: **+8**
- Otherwise: **+7**

Additional **−1** at 50% probability (always applied after the above).

### Trick Room
- Already active: **−20**
- AI slower: **+10**
- AI faster: **+5**

### Trick / Switcheroo
- Holding Toxic Orb, Flame Orb, or Black Sludge: base **+6**, then **+1** at 50% → effective +6 (50%) or +7 (50%)
- Holding Iron Ball, Lagging Tail, or Sticky Barb: **+7**
- Any other item: **+5**

### Will-O-Wisp
Never used (−20) if:
- Player already has a status condition
- Player is Fire type

Otherwise, base score: **+6**

37% of the time, conditional bonuses:
- AI has Hex: **+1**
- Player has a Physical move with BP > 0: **+1**

These two can both apply, so the 37% path can add 0, 1, or 2 to the base.

### Yawn / Dark Void / Grass Whistle / Sing / Hypnosis
Never used (−20) if:
- Player has Insomnia, Vital Spirit, or Sweet Veil
- Player already has a status condition
- Terrain is Electric or Misty

Otherwise, base score: **+6**

25% of the time, if AI does NOT see a kill, add:
- +1 base
- AI has Dream Eater or Nightmare AND player does NOT have Snore or Sleep Talk: additional **+1**
- AI has Hex: additional **+1**

Note: **Hypnosis** is handled by the same code block as Yawn/Dark Void/Grass Whistle/Sing but is absent from the AI.md list.

### Smack Down / Thousand Arrows
Not in AI.md. From code:
- Player is Flying type OR has Levitate, AND player is not already grounded: additional **+6**

### Leech Seed
Never used (−20) if player is Grass type or already Leech Seeded (no explicit score, just suppressed).

### First Impression
Never used (−50) unless it is the AI's first turn out.

### Spikes / Toxic Spikes
Never used (−40) if maximum layers already set (Spikes ≥ 3, Toxic Spikes ≥ 2).

Otherwise:
- First turn out: base **+8**
- Not first turn out: base **+6**

Then +1 at 75% probability.

If the player's side already has at least one layer of the corresponding spike: additional **−1** always.

Minimum possible score (first turn, own side already has layer): 8+1−1 = 8 (75%) or 8+0−1 = 7 (25%)

### Stealth Rock
Never used (−40) if already set.

Otherwise:
- First turn out: base **+8**
- Not first turn out: base **+6**

Then +1 at 75% probability.

### Sticky Web
Never used if already set (falls under general useless-move logic).

Otherwise:
- First turn out: base **+9**
- Not first turn out: base **+6**

Then +3 at 75% probability.

### Sleep Talk
Never used (−40) if AI is not sleeping.

### Weather Moves (Sunny Day, Rain Dance, Sandstorm, Hail)
Never used (−40) if the corresponding weather is already active.

---

## 8. Contrary Ability Interactions (AI has Contrary)

Overheat and Leaf Storm (when NOT the HD move and NOT killing): treated as **Offensive Setup** (same score as Nasty Plot).

Superpower (when NOT the HD move, NOT killing, and has valid damage rolls): treated as **Bulk Up** (i.e. Defensive or Offensive Setup depending on player moveset, same as Bulk Up scoring).

**Contrary bypasses all of the following restrictions** that normally apply to setup moves:
- Does NOT get the −5 penalty when AI is slower and 2HKOd
- Does NOT get blocked by player having Unaware
- Does NOT get blocked by `aiDeadToPlayer` (Overheat/Leaf Storm/Superpower specifically)

If the Contrary move IS the HD move, it is scored as a normal damaging move (no setup scoring applied).

---

## 9. Ability-Specific Scoring Interactions

### Player Abilities That Affect AI Scores

| Player Ability | Effect on AI |
|---|---|
| **Contrary** | Speed-reducing moves and stat-reducing moves score +5 instead of +6 when not HD |
| **Clear Body** | Same as Contrary for score reduction |
| **White Smoke** | Same as Contrary for score reduction |
| **Limber** | Thunder Wave, Stun Spore, Nuzzle, Glare → −40 (never use) |
| **Insomnia / Vital Spirit / Sweet Veil** | Yawn, Dark Void, Grass Whistle, Sing, Hypnosis → −20 |
| **Shield Dust** | Fake Out → −40 (blocks the first-turn +9) |
| **Inner Focus** | Fake Out → −40 (same as Shield Dust) |
| **Shell Armor / Battle Armor** | Focus Energy, Laser Focus → −40 |
| **Unaware** | All general setup moves → −40 EXCEPT Power-Up Punch, Swords Dance, and Howl |
| **Levitate** (or Flying type) | Smack Down, Thousand Arrows get +6 bonus if player not already grounded |
| **Infiltrator** | Substitute → −40 |
| **Overcoat** | Powder moves → −50 |

### AI Abilities That Affect Scores

| AI Ability | Effect |
|---|---|
| **Moxie / Beast Boost / Chilling Neigh / Grim Neigh** | +1 on every killing move. Kill detection thresholds shift up by 1 |
| **Contrary** | Overheat/Leaf Storm/Superpower become setup moves when not HD/killing (see section 8) |
| **Corrosion** | Toxic, Poison Gas, Poison Powder can target Poison and Steel types (no −40 immune veto) |
| **Sturdy** | At full HP: `aiDeadToPlayer` = false (setup moves not blocked, Counter/Mirror Coat get +8 instead of +6 under kill conditions) |
| **Super Luck / Sniper** | Focus Energy, Laser Focus → +7 instead of +6 |
| **Sand Force / Sand Rush / Sand Veil** | AI immune to sand secondary damage for Protect veto check |
| **Ice Body / Snow Cloak** | AI immune to hail secondary damage for Protect veto check |
| **Magic Guard** | AI immune to both sand and hail secondary damage |
| **Overcoat** | AI immune to both sand and hail secondary damage |
| **Shed Skin / Early Bird** | Rest `restIncentive = 1` → Rest gets the additional +1 on top of +8 |
| **Hydration** (in Rain) | Rest `restIncentive = 1` |
| **Merciless** | Counts as having Hex/Venom Drench for the Toxic/Poison Gas/Poison Powder combo bonus check |
| **Receiver** (Passimian w/ Huge Power partner) | Special: Detect/Protect gets +8 extra in the Clifford+Macey double fight |

### Role Play (doubles)
- AI partner has Huge Power, Pure Power, Protean, or Tough Claws AND AI does not already have one of those: **+9**
- Otherwise: **−20**

### High Crit Rate Move Bonus
Moves in the high-crit-rate list (Aeroblast, Air Cutter, Attack Order, Blaze Kick, Crabhammer, Cross Chop, Cross Poison, Drill Run, Karate Chop, Leaf Blade, Night Slash, Poison Tail, Psycho Cut, Razor Leaf, Razor Wind, Shadow Claw, Sky Attack, Slash, Spacial Rend, Stone Edge) receive an additional **+1** (50% chance) when they are Super Effective on the target.

This is also the qualification for Focus Energy/Laser Focus +7 bonus.

### Skill Link (AI ability)
3-hit moves (Arm Thrust, Barrage, Bone Rush, Bullet Seed, Comet Punch, Double Slap, Fury Attack, Icicle Spear, Pin Missile, Rock Blast, Scale Shot, Spike Cannon, Surging Strikes, Tail Slap, Triple Dive, Water Shuriken) hit 5 times instead of 3 when AI has Skill Link. Damage is multiplied accordingly for HD calculation.

---

## 10. In-Battle Switch AI (Singles Only)

The AI may switch mid-battle (without a KO) only in Singles; in Doubles, AI never switches except for specific moves like Perish Song.

### Conditions Required for a Potential Switch (all must be true)
1. AI can only use moves scoring ≤ −5 (usually due to Encore, PP stall, or a Choice item locking into a useless move)
2. AI's current HP is > 50%
3. At least one party member can survive and threaten: specifically faster than player and not OHKOd, OR slower and not 2HKOd. **Bug:** the code's 2HKO path doesn't work properly — once the AI sees one mon that is faster, it treats all subsequent mons as faster regardless of their speed.

### Switch Execution
If all conditions met: 50% chance to switch.

The replacement mon is chosen using the Post-KO Switch-In scoring below, excluding any mon that fails condition 3.

---

## 11. Post-KO Switch-In AI

When a Pokémon faints, the AI sends in the party member with the highest switch-in score. Ties go to the first Pokémon in party order.

### Scoring

| Score | Condition |
|---|---|
| +5 | AI's Pokémon is **faster** and **OHKOs** the player's Pokémon |
| +4 | AI's Pokémon is **slower** but **OHKOs** it **and is not itself OHKOd** |
| +3 | AI's Pokémon is **faster** and **deals more damage (%)** than it takes |
| +2 | AI's Pokémon is **slower** and **deals more damage (%)** than it takes |
| +1 | AI's Pokémon is **faster** than the player's Pokémon |
| 0 | Default (none of the above) |
| −1 | AI's Pokémon is **slower** and is **OHKOd** by the player's Pokémon |

Damage comparison is done in percentage terms (% of max HP), not raw numbers.

### Special Cases (override normal scoring)

| Score | Condition |
|---|---|
| +2 | Pokémon is **Ditto** (always) |
| +2 | Pokémon is **Wynaut or Wobbuffet**, as long as it is not both slower than the player AND OHKOd by the player |

### Doubles

In Doubles, the AI uses the same switch-in scoring but slot-matched: AI's slot 1 evaluates against player's slot 1, and AI's slot 2 evaluates against player's slot 2.

---

## 12. Bugs and Doc Discrepancies

These are differences between the AI.md documentation and the actual code, or bugs found in the code itself.

### BUG: Glare Always Scores −40
**File:** `ai.ts` near the paralysis move block  
**Issue:** Operator precedence bug. The condition reads:
```
moveName == "Glare" || moveName == "Stun Spore" && playerTypes.includes("Electric")
```
Due to `&&` having higher precedence than `||`, this evaluates as:
```
moveName == "Glare" || (moveName == "Stun Spore" && playerTypes.includes("Electric"))
```
When `moveName == "Glare"`, this is always `true`, so Glare **always** receives −40 regardless of the player's type. The intent was likely to block Glare on Electric-type players only (since Glare is Normal type, not caught by the Electric-type immunity check). **Glare is functionally never used by the AI.**

**[C++ status: fixed — ai_scorer_dist.cpp:114. C++ routes all PARALYSIS_MOVES through dist_paralysis, which only gates on Electric type when the move's own type is Electric (line 120). Glare (Normal type) skips that branch and receives the standard speed-based score (6 or 7). Not in divergence logs; this is an intentional correction.]**

### BUG: Stun Spore Incorrectly Blocked on Electric Types
The code blocks Stun Spore on Electric-type players (`moveName == "Stun Spore" && playerTypes.includes("Electric")`). In Gen 8, Electric types are NOT immune to Stun Spore (which is a Grass-type move); only Electric-type paralysis moves are blocked by Electric typing in Gen 6+. This is an AI misplay that benefits the player.

**[C++ status: fixed — ai_scorer_dist.cpp:120. The Electric-type block is conditioned on `md.move_type == TYPE_ELECTRIC`; Stun Spore is Grass type and is not blocked. Not in divergence logs; this is an intentional correction.]**

### BUG: Venoshock Missing from Poison Combo Bonus
**AI.md says:** "AI mon has Hex, Venom Drench, Venoshock or the ability Merciless" triggers the +2 bonus.  
**Code checks:** Only Hex, Venom Drench, and ability Merciless. Venoshock is absent.

**[C++ status: resolved/not applicable — the entire combo bonus block was not ported to C++; dist_poison_move returns a flat +6 (ai_scorer_dist.cpp:218). Venoshock's absence is subsumed by the block being omitted entirely.]**

### BUG: Sun Recovery Uses 100% Heal Rate
Morning Sun / Synthesis / Moonlight in Sun call `shouldAIRecover(1.0)` but the actual heal is 2/3 (67%). This inflates the AI's willingness to recover in Sun and has a TODO comment in the code.

**[C++ status: fixed — ai_scorer.cpp:80. C++ passes `0.67` as the heal fraction for these moves in sun, matching the actual 2/3 heal rate. Not in divergence logs; this is an intentional correction of the TODO.]**

### BUG: Incapacitation Check Is Incomplete
Code: `playerIncapacitated = playerStatus == "frz" || playerStatus == "slp"`  
AI.md also lists recharging (after Hyper Beam etc.) and Truant loafing. Neither is implemented.

**[C++ status: fixed — ai_scorer_internal.h:270. C++ `is_incapacitated` covers freeze, sleep, `VOL_RECHARGING`, and Truant loafing (`AB_TRUANT` + `VOL_TRUANT_LOAFING`). Intentional correction of the ai.ts TODO (ai.ts:894); tests in tests/test_ai_sleep_truant.py.]**

### DOC OMISSION: Counter and Mirror Coat Excluded from HD
AI.md does not mention that Counter and Mirror Coat are excluded from the highest-damage competition. They are listed in the `calculateHighestDamage` exclusion array in code.

**[C++ status: resolved/not applicable — Counter and Mirror Coat have their own scoring branch in dist_status_special (ai_scorer_dist.cpp:380) and are never routed through the highest-damage path. The omission is a doc gap only; C++ behavior is correct.]**

### DOC OMISSION: Bulldoze Is a Speed-Reducing Move
AI.md lists Icy Wind, Electroweb, Rock Tomb, Mud Shot, Low Sweep — but not Bulldoze. Bulldoze is in the code's `isDamagingSpeedReducing` check.

**[C++ status: resolved/not applicable — Bulldoze (ID 523) is in SPEED_REDUCTION_MOVES (engine/generated/ai_move_sets.h:134) and handled at ai_scorer_dist.cpp:625. Doc omission only; C++ is correct.]**

### DOC OMISSION: Breaking Swipe, Snarl, Mystical Fire Are Stat-Reducing Moves
AI.md only mentions "Trop Kick, Skitter Smack, etc." for the Atk/SpAtk reduction category. Code explicitly includes Breaking Swipe (Physical, Atk-reducing), Snarl, and Mystical Fire (Special-reducing).

**[C++ status: resolved/not applicable — Breaking Swipe (784), Snarl (555), Mystical Fire (595) are all in STAT_REDUCTION_DAMAGE_MOVES (engine/generated/ai_move_sets.h:139), handled at ai_scorer_dist.cpp:640. Doc omission only; C++ is correct.]**

### DOC OMISSION: Hypnosis Is in the Sleep Group
AI.md lists Yawn, Dark Void, Grass Whistle, Sing. Hypnosis uses the same code block.

**[C++ status: fixed — ai_scorer_dist.cpp:302: unified sleep-move branch covers Yawn, Hypnosis, Sing, Grass Whistle, and Dark Void with the full −20 gating (existing status, Electric/Misty terrain, Insomnia/Vital Spirit/Sweet Veil — Sweet Veil was also missing from the old Yawn-only branch). Tests in tests/test_ai_sleep_truant.py. KNOWN SIMPLIFICATION: the ai.ts 25%-rate sleep-synergy bonus (+1 base, +1 Dream Eater/Nightmare, +1 Hex; ai.ts:1791-1810) is NOT implemented — it needs an aiSeesKill concept the status path lacks; the analogous Toxic 38%-rate bonus was likewise never ported.]**

### DOC OMISSION: Spiky Shield, Baneful Bunker, Detect, Obstruct
AI.md says "King's Shield has no unique AI" but doesn't mention Spiky Shield, Baneful Bunker, Detect, or Obstruct. All five are handled identically to Protect in the code.

**[C++ status: resolved/not applicable — all five (plus Wide Guard and Quick Guard) are in PROTECT_MOVES (engine/generated/ai_move_sets.h:10) and all route through dist_protect. Doc omission only; C++ is correct.]**

### DOC OMISSION: Magnet Rise, Scary Face, Flame Charge
These moves have AI scoring in the code but are not listed in AI.md:
- Magnet Rise: +8 (AI faster + player has Ground move), +5 otherwise, −40 if already risen
- Scary Face: +6 (AI slower), −20 (AI faster)
- Flame Charge: +6 when not HD, AI slower, valid damage rolls

**[C++ status: resolved/not applicable — all three have explicit handling in dist_status_special: Magnet Rise at ai_scorer_dist.cpp:444 (−40 if active, +8 if AI faster+player has Ground, +5 otherwise), Scary Face at ai_scorer_dist.cpp:309, Flame Charge at ai_scorer_dist.cpp:649. Doc omission only; C++ is correct.]**

### DOC OMISSION: Smack Down / Thousand Arrows Grounding Bonus
Not in AI.md. +6 bonus when player is Flying type or has Levitate and is not already grounded.

**[C++ status: resolved/not applicable — implemented at ai_scorer_dist.cpp:658. Doc omission only; C++ is correct.]**

### DOC OMISSION: Substitute — Sub Already Active Is a Useless Condition
AI.md does not list "Substitute already active" as a reason to score −40. The code does.

**[C++ status: resolved/not applicable — implemented at ai_scorer.cpp:134 (`VOL_SUBSTITUTE` check). Doc omission only; C++ is correct.]**

### DOC OMISSION: Tailwind Already Active → −40
AI.md does not explicitly list the "already active" case for Tailwind. Code gives −40.

**[C++ status: resolved/not applicable — implemented at ai_scorer_dist.cpp:178 (`SC_TAILWIND` check → −40). Doc omission only; C++ is correct.]**

### DOC CLARIFICATION: Shell Smash SpAtk Condition Is Asymmetric
AI.md says "If AI mon's attack stat is +1 or higher, or either attacking stat is at +6." The code confirms: the check is `boosts.atk >= 1 OR boosts.spatk >= 6`. Physical attack at +1 blocks Shell Smash; Special attack at +1 through +5 does not.

**[C++ status: resolved/not applicable — confirmed at ai_scorer.cpp:161 (`ai_mon.stage0 >= 1 || ai_mon.stage2 >= 6`). Behavior matches ai.ts; doc clarification only.]**

### DOC CLARIFICATION: Encore When Faster but Not Encouraged → +6
AI.md's developer noted uncertainty here. Confirmed via code: when AI is faster but the move is not "encouraged," no modifier is pushed, so the default status score of +6 applies.

**[C++ status: resolved/not applicable — confirmed at ai_scorer_dist.cpp:376: when `ai_fst`, C++ returns `{{6, 1.0}}`. Doc clarification only; C++ behavior matches.]**

### DOC CLARIFICATION: Tailwind −20 vs −40
AI.md does not give a score for Tailwind already being active. Code applies −40 (not −20).

**[C++ status: resolved/not applicable — confirmed at ai_scorer_dist.cpp:178. Matches ai.ts; doc clarification only.]**

### DOC CLARIFICATION: Terrain Moves Already Active → −40
Not explicit in AI.md. Code applies −40 when the terrain is already set.

**[C++ status: resolved/not applicable — confirmed in dist_terrain (ai_scorer_dist.cpp). Doc clarification only; C++ matches.]**

### NUMERICAL DISCREPANCY: Helping Hand / Follow Me
AI.md says "+6" for these moves. In singles, the calc gives them −6 (score of 0 − 6 = −6 net, with the default +6 suppressed). These moves are effectively disabled in singles.

**[C++ status: resolved/not applicable — ai_scorer_dist.cpp:315 returns `{{0, 1.0}}` in singles (doubles returns `{{6, 1.0}}`). The "−6 net" framing from ai.ts is replaced by a direct 0 return; effective behavior matches (moves are not chosen in singles). Doc discrepancy only.]**

### NUMERICAL DISCREPANCY: Recovery Move Threshold
AI.md says "at 85% or higher" the AI gets a −6 penalty. Code uses `aiHealthPercentage >= 85`, confirming 85% exactly incurs the −6 penalty.

**[C++ status: resolved/not applicable — confirmed at ai_scorer_dist.cpp:31 (`hp_pct >= 0.85`). Behavior matches ai.ts exactly; numerical discrepancy note is now confirmed correct and documented.]**
