<Element name="Sucker Punch">
Type: Dark
Category: Physical
Base Power: 70
Accuracy: 100
PP: 5
Priority: +1
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Moves with +1 priority. Fails unless the target has a damaging move queued for this turn.

Failure conditions (move fails outright, no damage):
- Target is not using a move this turn (switching, using an item, etc.)
- Target is using a status move (category == Status), EXCEPT Me First
- Target has the "must recharge" volatile (e.g. after Hyper Beam)

Edge cases:
- Against Me First: succeeds. Me First is classified as a status move but is explicitly exempted from the failure check because it will result in a damaging attack being used.
- Priority +1 means Sucker Punch usually resolves before the target's move, which is intentional—the user is "jumping" the target before they act. But it still fails even if the target's status move would have been used after Sucker Punch resolved.
- If the target faints before Sucker Punch is used in the same turn (e.g. due to entry hazards, weather, or a faster move), behavior depends on whether there is a valid target remaining.
- Does NOT fail against multi-turn moves being executed (e.g. Solar Beam charging, Fly in the air)—those count as damaging moves queued. Only the "must recharge" volatile is an explicit exception.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Bolt Strike">
Type: Electric
Category: Physical
Base Power: 130
Accuracy: 90 (vanilla: 85)
PP: 5
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
High-power Electric physical attack. 20% chance to paralyze the target.

Paralysis secondary:
- 20% chance to inflict paralysis.
- Electric-type targets are immune to paralysis.
- Limber ability prevents paralysis.
- Already-statused targets cannot be paralyzed.

Edge cases:
- Makes contact; triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Electric type; no effect against Ground types (immune).
- Can be used even in Electric Terrain without any special interaction beyond standard Electric power boosts (Electric Terrain boosts Electric-type moves from grounded Pokémon by 1.3x).
- Lightning Rod / Volt Absorb / Motor Drive abilities grant immunity and may trigger their effects.

R&B Changes:
- Accuracy increased from 85% to 90%.
</Element>

<Element name="Quick Attack">
Type: Normal
Category: Physical
Base Power: 40
Accuracy: 100
PP: 30
Priority: +1
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Simple priority attack. No additional effect.

Edge cases:
- Normal type; no effect against Ghost types.
- Affected by type-changing abilities (Pixilate, Aerilate, Refrigerate, Galvanize) which convert Normal moves to another type and add 1.2x boost.
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, static/flame body/etc. on hit; affected by Long Reach (suppresses contact on user).
- At +1 priority, ties with Sucker Punch, Bullet Punch, Mach Punch, Shadow Sneak, etc.—speed determines order within the same priority bracket.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fishious Rend">
Type: Water
Category: Physical
Base Power: 85 (170 if user moves first or target just switched in)
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Contact: Yes
Flags: contact, protect, mirror, metronome, bite

Effect:
Water physical bite attack that doubles in power if the user acts before the target or if the target just switched in.

Double BP condition:
- Activates (170 BP) when:
  - The user moves before the target this turn (target's move hasn't occurred yet), OR
  - The target just switched in this turn (newlySwitched).
- Does NOT activate (85 BP) when:
  - The target has already moved this turn (user is moving last).

Bite flag:
- Strong Jaw ability boosts Base Power by 1.5× (127.5 → 127 at base, or 255 at double BP).

Speed implications:
- Faster Pokémon naturally benefit from the double BP (they move first).
- Trick Room reverses this: under Trick Room, slower Pokémon move first, so a slower Fishious Rend user would get the boost instead.
- Paralysis (reducing user's speed) can prevent the double BP by making the user act after the target.

Edge cases:
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Water type: Storm Drain/Water Absorb/Dry Skin absorb the move; boosted in Rain, halved in Sun.
- Companion to Bolt Beak (Electric, same mechanic for Dracozolt/Arctozolt).
- Against a just-switched-in target: even if the user is slower, the double BP applies because `newlySwitched` is set.
- Quick Attack / priority moves: if the user uses a priority move that hits before the target's turn, the target hasn't moved yet → Fishious Rend from the user would still get double BP if used that turn.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Blaze Kick">
Type: Fire
Category: Physical
Base Power: 85
Accuracy: 100 (vanilla: 90)
PP: 10
Priority: 0
Target: Single target
Contact: Yes
Flags: contact, protect, mirror, metronome

Effect:
Fire physical attack with an elevated critical hit ratio and a 10% chance to burn.

Critical hit ratio:
- critRatio: 2 — inherent +1 stage (1/8 base crit chance instead of 1/24).
- Combined with Focus Energy or Scope Lens/Razor Claw: guaranteed crits.

Burn secondary:
- 10% chance to inflict burn.
- Fire-type Pokémon are immune to burn.
- Water Veil / Thermal Exchange prevent burn.
- Sheer Force: removes the 10% burn chance, boosts Base Power to ~110 (85 × 1.3). Also removes the elevated crit ratio? Actually no — critRatio is a base property, not a secondary, so Sheer Force does NOT remove the elevated crit chance. Sheer Force only removes secondaries (the `secondary` key in the move definition).

Edge cases:
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Fire type: Flash Fire absorbs it; halved in Rain/Heavy Rain; boosted 1.5× in Harsh Sun/Desolate Land.

R&B Changes:
- Accuracy increased from 90% to 100%.
</Element>

<Element name="Nature Power">
Type: Normal (but calls a different move based on terrain)
Category: Status (delegates to called move's category)
Base Power: 0 (delegates to called move)
Accuracy: Always hits (delegates to called move's accuracy)
PP: 20
Priority: 0
Target: Single target
Contact: No
Flags: failencore, nosleeptalk, noassist, failcopycat, failmimic, failinstruct

Effect:
Calls a specific move depending on the active terrain. The called move's stats, type, and effects all apply as if that move were used directly.

Terrain-to-move mapping:
- No active terrain: Tri Attack (Normal, Special, 80 BP, 20% chance to paralyze/burn/freeze)
- Electric Terrain: Thunderbolt (Electric, Special, 90 BP, 10% paralysis)
- Grassy Terrain: Energy Ball (Grass, Special, 90 BP, 10% SpD drop)
- Misty Terrain: Moonblast (Fairy, Special, 95 BP, 30% SpA drop)
- Psychic Terrain: Psychic (Psychic, Special, 90 BP, 10% SpD drop)

Move call mechanics:
- The called move is used as if the Pokémon used it directly (callsMove: true).
- All of the called move's effects, type matchups, and ability interactions apply normally.
- The called move's own contact/protect flags apply (e.g., Thunderbolt has protect/mirror).

Restrictions:
- Cannot be called by Encore (failencore), Sleep Talk (nosleeptalk), Assist (noassist), Copycat (failcopycat), Mimic (failmimic), or Instruct (failinstruct).

Edge cases:
- If terrain expires after Nature Power's turn order but before it fires (unlikely), it would use the no-terrain version.
- The called move uses Normal PP? No—Nature Power's own PP is consumed; the called move does not lose PP.
- Sketch cannot sketch Nature Power (given failmimic flag, and Sketch is similar).
- Electric Terrain boost: Thunderbolt called from Nature Power is boosted by Electric Terrain if the user is grounded (as normal for Electric Terrain + Electric moves).
- In Grassy Terrain, Energy Ball is additionally boosted by Grassy Terrain if applicable (though Grassy Terrain boosts Grass moves of grounded Pokémon).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Leaf Blade">
Type: Grass
Category: Physical
Base Power: 90
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Contact: Yes
Flags: contact, protect, mirror, metronome, slicing

Effect:
Grass physical slicing attack with an elevated critical hit ratio.

Critical hit ratio:
- critRatio: 2 — inherent +1 stage to crit ratio (like Night Slash, Cross Chop, etc.).
- Base crit chance: 1/8 (12.5%) instead of the normal 1/24 (~4.2%).
- Combined with Focus Energy or Scope Lens/Razor Claw: stage 3 or higher → guaranteed crits.
- Battle Armor / Shell Armor: still prevents crits even with elevated critRatio.

Slicing flag:
- Sharpness ability boosts Base Power by 1.5× (to 135 effective BP).

Edge cases:
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Grass type: Sap Sipper absorbs it.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Play Rough">
Type: Fairy
Category: Physical
Base Power: 90
Accuracy: 100 (vanilla: 90)
PP: 10
Priority: 0
Target: Single target
Contact: Yes
Flags: contact, protect, mirror, metronome

Effect:
Fairy physical attack. 10% chance to lower the target's Attack by 1 stage.

Attack drop secondary:
- 10% activation rate.
- Blocked by Clear Body, White Smoke, Full Metal Body (stat-drop immunity).
- Mirror Armor: reflects the -1 Atk drop back onto the user.
- Sheer Force (on the user): removes the secondary, boosts Base Power to ~117 (90 × 1.3).

Edge cases:
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Fairy type: super effective vs Dragon, Dark, Fighting; Steel and Poison resist; no immunities to Fairy.

R&B Changes:
- Accuracy increased from 90% to 100%.
</Element>

<Element name="Super Fang">
Type: Dark (vanilla: Normal)
Category: Physical
Base Power: N/A (fixed damage: 50% of target's current HP)
Accuracy: 100 (vanilla: 90)
PP: 10
Priority: 0
Target: Single target
Contact: Yes
Flags: contact, protect, mirror, metronome

Effect:
Deals damage equal to half the target's current HP (rounded down, minimum 1). Fixed damage, not affected by type effectiveness, stat stages, or most modifiers.

Damage formula:
  damage = floor(target.currentHP / 2)  (minimum 1)

The damage uses the target's current HP (not max HP), so repeated uses deal diminishing absolute damage as the target's HP decreases.

Type and immunity:
- In R&B: Dark type. No Pokémon is immune to Dark-type moves. Ghost types (formerly immune as Normal type) CAN be hit by Super Fang in R&B.
- Despite being fixed damage, the move still "has a type" — Wonder Guard would block it if Dark is not super effective against the target.

Makes contact:
- Triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.

Edge cases:
- Normal-type Pokémon that rely on Ghost immunity for protection cannot avoid Super Fang in R&B (type changed to Dark).
- If the defender is Protected (Protect/Detect/etc.): calculator returns 0 damage.
- The minimum damage is 1, so Super Fang can never reduce a Pokémon below 1 HP from this move alone (e.g., if target is at 1 HP: floor(1/2) = 0, but clamped to 1... actually `clampIntRange(hp/2, 1)` ensures minimum 1).
- Disguise ability (Mimikyu): the Disguise absorbs the hit and pops, dealing 1 damage to Disguise. Super Fang's damage is then 0 to the real HP? Or does it damage real HP? In Showdown, Disguise absorbs hits before damage. The fixed damage system may interact differently — should be tested.

R&B Changes:
- Type changed from Normal to Dark (Super Fang now hits Ghost types).
- Accuracy increased from 90% to 100%.
</Element>

<Element name="Protect">
Type: Normal
Category: Status
Base Power: —
Accuracy: Always hits (but see consecutive-use reduction)
PP: 10
Priority: +4
Target: Self
Contact: No
Flags: noassist, failcopycat (no protect, no metronome, no mirror)

Effect:
Protects the user from all moves targeted at it for the turn. Moves with the `protect` flag in their flags are blocked; moves with `breaksProtect: true` bypass it.

Priority: +4 — goes before nearly all moves.

Consecutive-use probability reduction:
- Uses the 'stall' volatile with an exponentially decreasing success rate.
- First use: 100% success (no stall volatile present).
- Second consecutive use: 1/3 (~33%) chance to succeed.
- Third consecutive use: 1/9 (~11%) chance.
- Each additional consecutive use: denominator multiplies by 3 (capped at 729).
- If the stall check fails, Protect itself fails. The volatile resets on failure (next use is again 100%).
- A "consecutive" use means the stall volatile is still active (duration: 2). Using a non-stalling move in between resets the counter.

Moves that bypass Protect (breaksProtect: true or other bypass):
- Feint, Hyperspace Fury, Hyperspace Hole, Phantom Force, Shadow Force (all have breaksProtect or bypass flags).
- Moves with the 'infiltrates' property (Infiltrator ability) bypass Protect as well.

What Protect blocks:
- All moves with the `protect` flag targeting the user.
- Status moves with the reflectable flag aimed at the user are also blocked.
- Does NOT block: entry hazards, weather damage, residual damage, arena/field effects.

Locked move interaction:
- If a Pokémon using a locked move (Outrage, Thrash, Petal Dance) hits into Protect, the lock counter may be reset.

Edge cases:
- Protect does not block the effect of King's Shield/Spiky Shield on moves that contact; those have their own volatile.
- Protect combined with Stall ability or Trick Room doesn't change its PP or effect.
- Cannot be called by Assist or Copycat (failcopycat, noassist flags).
- Priority +4 means it goes before almost all moves, including +1/-1/-3 priority moves and most normal moves.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Rock Tomb">
Type: Rock
Category: Physical
Base Power: 60
Accuracy: 95
PP: 15
Priority: 0
Target: Single target
Contact: No
Flags: protect, mirror, metronome

Effect:
Rock physical attack. Guaranteed 100% chance to lower the target's Speed by 1 stage.

Speed drop secondary:
- 100% activation rate — always lowers Speed by 1 if the move hits.
- Blocked by Clear Body, White Smoke, Full Metal Body (stat-drop immunity).
- Mirror Armor: reflects the -1 Speed drop back onto the user.
- Sheer Force (on the user): removes the secondary but raises Base Power to ~78 (60 × 1.3).

Edge cases:
- Does not make contact: no Rocky Helmet, Iron Barbs, etc.
- Rock type: super effective vs Fire, Flying, Bug, Ice; resisted by Fighting, Ground, Steel.
- The Speed drop accumulates; multiple Rock Tombs can bring a target to -6 Speed over time.
- Sand stream / Sand weather does not boost Rock Tomb for regular Pokémon (only the Sp. Def boost for Rock types in Sand affects defense, not attack).
- Sandstorm boosted special defense of Rock-type Pokémon is irrelevant to this physical move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Wicked Blow">
Type: Dark
Category: Physical
Base Power: 75
Accuracy: 100
PP: 5
Priority: 0
Target: Single target
Contact: Yes
Flags: contact, protect, mirror, punch (no metronome)

Effect:
Dark physical punch that always lands a critical hit.

Guaranteed critical hit (willCrit: true):
- Ignores positive defensive stat boosts on the target (e.g., Calm Mind raises).
- Ignores negative offensive stat drops on the user (e.g., Intimidate drops).
- Deals 1.5× damage from the critical hit multiplier.
- Bypasses Light Screen/Reflect/Aurora Veil (screens do not apply on crits).

Critical hit immunity:
- Battle Armor / Shell Armor: these abilities prevent critical hits entirely. Even with willCrit, Wicked Blow deals non-critical damage against Pokémon with Battle Armor or Shell Armor.

Punch flag:
- Iron Fist boosts Base Power by 1.2× (to 90 effective BP before crit multiplier).

No metronome:
- Cannot be called by Metronome or similar random-move effects.

Edge cases:
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Dark type: Fairy resists Dark; no type immunities.
- Wicked Blow's critical hit is still subject to Sniper ability (if user has Sniper, crits deal 2.25× instead of 1.5×).
- Merciless ability also forces crits on poisoned targets, but that's separate from willCrit.
- Does not bypass type immunity: Ghost types are immune to... Dark? No, Ghost is not immune to Dark. Dark has no type immunity interactions in gen 8. Fairy resists but is not immune.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Light Screen">
Type: Psychic
Category: Status
Base Power: —
Accuracy: Always hits
PP: 30
Priority: 0
Target: Ally side (team-wide)
Contact: No
Flags: snatch, metronome

Effect:
Sets up the Light Screen side condition on the user's side, lasting 5 turns. Reduces all Special-type damage taken by Pokémon on the user's side.

Damage reduction:
- Singles: incoming Special damage is multiplied by 0.5 (halved).
- Doubles: incoming Special damage is multiplied by 2732/4096 ≈ 0.667 (reduced by ~1/3).

Bypass conditions (screen does NOT reduce damage if):
- The incoming move is a critical hit.
- The move has the 'infiltrates' property (Infiltrator ability on the attacker bypasses screens).
- Aurora Veil is active on the same side: Light Screen does NOT stack with Aurora Veil (the calculator uses an else-if, so only one of the two applies — Aurora Veil takes precedence when both are active).

Duration:
- 5 turns normally.
- 8 turns if the user holds Light Clay.

Removal:
- Brick Break: removes Light Screen (and Reflect) before dealing damage.
- Defog: removes all hazards and screens on both sides.

Edge cases:
- Can be Snatched (snatch flag): the Snatch user sets up Light Screen on their own side instead.
- Does not reduce damage from non-damaging moves (entry hazards, weather residual, etc.).
- Using Light Screen when it is already active resets the duration.
- Aurora Veil (set by Hail/Snow) provides both Physical and Special reduction but is distinct from Light Screen; they do NOT stack.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Rock Polish">
Type: Rock
Category: Status
Base Power: —
Accuracy: Always hits
PP: 20
Priority: 0
Target: Self
Contact: No
Flags: snatch, metronome

Effect:
Raises the user's Speed by +2 stages.

Edge cases:
- Can be Snatched (snatch flag): the Snatch user gains the +2 Speed boost.
- Contrary ability (on the user): turns the +2 Speed into -2 Speed.
- Simple ability: doubles the boost to +4 Speed.
- Speed boost is capped at +6.
- Trick Room: does not prevent the Speed boost, but in Trick Room the boost now makes the user "slower" in move order (Trick Room reverses Speed order).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Electro Ball">
Type: Electric
Category: Special
Base Power: 40–150 (depends on user's Speed relative to target's)
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Contact: No
Flags: protect, mirror, metronome, bullet

Effect:
Electric special attack. Base power increases with the user's Speed advantage over the target.

Base power formula:
  ratio = floor(user.effectiveSpe / target.effectiveSpe)
  - ratio < 1 (user slower or same speed): 40 BP
  - ratio = 1: 60 BP
  - ratio = 2: 80 BP
  - ratio = 3: 120 BP
  - ratio ≥ 4: 150 BP
  - Special: if target's Speed = 0, BP = 40.

Speed used is the final in-battle Speed (including stat stages, paralysis halving, Tailwind doubling, items like Choice Scarf, Trick Room irrelevant to Speed stat itself, etc.).

Bullet flag:
- Bulletproof ability (on the target): blocks Electro Ball entirely (immune to ball/bomb moves).

Edge cases:
- Electric type: Ground types are immune; Lightning Rod/Volt Absorb/Motor Drive absorb the move.
- Does not make contact: no Rocky Helmet etc.
- Trick Room: Trick Room reverses Speed order but does NOT change the Speed stats themselves. The ratio calculation still uses actual Speed values, not Trick Room priority order.
- Paralysis (on user): reduces user's effective Speed to 50%, potentially reducing the ratio and thus BP.
- Tailwind (on user): doubles user's Speed, potentially increasing the ratio and BP.
- Paralysis (on target): halves target's Speed, increasing the ratio (user appears faster relative to target) → higher BP.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Anchor Shot">
Type: Steel
Category: Physical
Base Power: 80
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Contact: Yes
Flags: contact, protect, mirror, metronome

Effect:
Steel physical attack. 100% chance to trap the target (prevent switching) while the user remains on the field.

Trap mechanic (volatile: 'trapped'):
- Applied via the secondary's onHit, only if the user (`source`) is still active.
- The 'trapped' volatile prevents the target from switching out.
- Unlike partiallytrapped (Bind, Wrap, etc.), this trap deals NO residual damage per turn.
- The trap is released when the user switches out or faints.
- noCopy: the trapped volatile cannot be copied by Baton Pass.

Escape methods for the target:
- Ghost types can escape even while trapped (Ghost types are never truly trapped by these mechanics).
- Shed Shell item allows the trapped target to switch out.
- Teleport (in gen 8) fails when trapped.
- Baton Pass, U-turn, Volt Switch, Flip Turn, Parting Shot bypass the trap (they're active switches, not regular switches).

Edge cases:
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Steel type: Poison and Steel are resistant to Steel; Ghost is immune to... wait, Steel is not immune to Ghost. Steel moves hit Ghost types normally (Ghost has no immunity to Steel).
- The `if (source.isActive)` check: if by some unusual interaction the source is no longer active when onHit fires (highly unlikely in a standard turn), the trap would not be applied.
- Arena Trap / Shadow Tag: these are ability-based traps that stack independently with Anchor Shot's trap.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Reversal">
Type: Fighting
Category: Physical
Base Power: 20–200 (depends on user's remaining HP)
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Fighting physical attack whose base power is inversely proportional to the user's remaining HP percentage.

Base power table:
  ratio = floor(48 × currentHP / maxHP)
  - ratio ≤ 1  (≤ ~2.1% HP):  200 BP
  - ratio ≤ 4  (≤ ~8.3% HP):  150 BP
  - ratio ≤ 9  (≤ ~18.75% HP): 100 BP
  - ratio ≤ 16 (≤ ~33.3% HP):  80 BP
  - ratio ≤ 32 (≤ ~66.7% HP):  40 BP
  - ratio > 32 (> ~66.7% HP):   20 BP

At 1 HP: always 200 BP (maximum).
At full HP: 20 BP (minimum).

Flail is the Normal-type equivalent with the same formula.

Edge cases:
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Fighting type: Ghost types are immune; super effective vs Normal, Rock, Steel, Ice, Dark.
- The HP ratio is computed at the time of damage resolution (not at the start of the turn), so damage dealt before Reversal executes affects the BP.
- Sturdy / Focus Sash: if the user is at 1 HP (via Focus Sash triggering or Endure), Reversal reaches maximum 200 BP.
- Endure: using Endure the previous turn to survive at 1 HP, then Reversal the next turn is a classic setup.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Dual Wingbeat">
Type: Flying
Category: Physical
Base Power: 40 per hit (always 2 hits; effective total: 80)
Accuracy: 100 (vanilla: 90)
PP: 10
Priority: 0
Target: Single target
Contact: Yes
Flags: contact, protect, mirror, metronome

Effect:
Flying physical attack that always strikes exactly twice. Unlike Triple Axel, there is NO per-hit accuracy check (no multiaccuracy flag). A single accuracy roll covers both hits.

Multi-hit mechanics:
- One accuracy check. If it passes, both hits land with no further rolls.
- Each hit is calculated and applied separately.
- Each hit can independently trigger contact-based effects (Rocky Helmet, Iron Barbs, Rough Skin, etc.).
- Each hit rolls for critical hits independently.
- Substitute: if first hit breaks the Substitute, second hit strikes the Pokémon directly.
- Sturdy / Focus Sash: if first hit reduces HP to 1 (or Sturdy activates), second hit can KO.

Edge cases:
- Makes contact per hit: two Rocky Helmet triggers, two Iron Barbs procs, etc.
- Flying type: does not affect Ground-type Pokémon... wait, Flying is not immune to Ground. Ground doesn't hit Flying (Ground moves miss Flying types). Dual Wingbeat is Flying, so no type immunity concerns except for Rock, Electric, Ice resist/SE issues.
- Skill Link has no effect (move is always exactly 2 hits, not variable).
- King's Rock / Stench: each hit independently rolls flinch chance.
- Parental Bond does NOT add extra hits to multi-hit moves.

R&B Changes:
- Accuracy increased from 90% to 100%.
</Element>

<Element name="Burning Jealousy">
Type: Fire
Category: Special
Base Power: 70
Accuracy: 100
PP: 5
Priority: 0
Target: All adjacent foes (spread move)
Contact: No
Flags: protect, mirror, metronome

Effect:
Fire special attack that hits all adjacent foes. Burns any target that had at least one stat raised during the current turn.

Conditional burn mechanic:
- The secondary fires with 100% chance (always runs), but burn is only applied via `trySetStatus('brn')` if `target.statsRaisedThisTurn` is true.
- "Stats raised this turn" includes: boosts from moves (Dragon Dance, Calm Mind, etc.), ability-triggered boosts (Moxie, Beast Boost, Anger Point, Download, etc.), and item-triggered boosts (e.g., from White Herb if it would raise).
- If the target had no stats raised this turn, the move still deals damage but applies no burn.

Burn application:
- `trySetStatus('brn')` respects all burn immunity checks.
- Fire-type Pokémon cannot be burned.
- Water Veil, Thermal Exchange, and similar abilities prevent burn.
- Already-statused Pokémon cannot be burned.

Spread mechanics:
- Hits all adjacent foes in doubles simultaneously.
- Spread moves receive a 0.75× damage multiplier when hitting multiple targets in doubles.
- Burn check runs per-target independently.

Edge cases:
- If a target used a stat-raising move this turn AND has a fire immunity (Flash Fire): damage is absorbed and no burn check applies.
- Sheer Force: this secondary has a conditional `onHit` function, not a standard chance/status secondary. Whether Sheer Force removes this secondary should be tested; based on Showdown's implementation (conditional onHit), Sheer Force likely does NOT remove it.
- If the user goes first and the target raises stats in the same turn after taking damage but before end of turn residual: the statsRaisedThisTurn flag would be set, but Burning Jealousy was already used; the burn check happens at use time.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Thunder Fang">
Type: Electric
Category: Physical
Base Power: 65
Accuracy: 100 (vanilla: 95)
PP: 15
Priority: 0
Target: Single target
Contact: Yes
Flags: contact, protect, mirror, metronome, bite

Effect:
Electric physical bite attack with two independent secondary effects: 10% chance to paralyze and 10% chance to flinch.

Dual secondaries:
- Both the paralysis and flinch rolls are separate and independent.
- Either, both, or neither can trigger on a single use.
- Chance of at least one effect: ~19% (1 − 0.9²).
- Electric-type Pokémon are immune to paralysis, but not to flinch.
- Flinch only applies if the target has not yet moved this turn.

Bite flag:
- Strong Jaw ability boosts Base Power by 1.5× (to 97.5 → effectively 97 effective BP).

Edge cases:
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Electric type: Ground types are immune; Lightning Rod/Volt Absorb/Motor Drive absorb the move.
- Sheer Force: removes BOTH secondaries and boosts Base Power by 1.3× (to ~84 BP).
- Shield Dust: blocks both secondary effects simultaneously.

R&B Changes:
- Accuracy increased from 95% to 100%.
</Element>

<Element name="Leech Seed">
Type: Grass
Category: Status
Base Power: —
Accuracy: 100 (vanilla: 90)
PP: 10
Priority: 0
Target: Single opponent
Contact: No
Flags: protect, reflectable, mirror, metronome

Effect:
Plants a seed on the target. Each turn at residual (order 8), the seeded Pokémon loses 1/8 of its max HP, and that HP is transferred to the Pokémon occupying the slot that used Leech Seed.

Type immunity:
- Grass-type Pokémon are completely immune to Leech Seed (onTryImmunity returns false for Grass types).
- Even if a Pokémon temporarily loses its Grass typing (e.g., via Forest's Curse adding another type), it remains immune if it retains the Grass type.

Drain mechanic:
- Damage: 1/8 of seeded Pokémon's MAXIMUM HP (not current HP).
- The heal goes to the Pokémon currently in the SOURCE SLOT (slot-based, not Pokémon-based). If the original user switches out, the new Pokémon in that slot receives the heal.
- If the source slot is empty or the current occupant is fainted: the drain damage to the seeded Pokémon does NOT occur (the entire residual is skipped).
- Big Root (held by the source Pokémon): increases the heal received by 30% (drain damage to target is unchanged).
- Liquid Ooze (on the seeded Pokémon): the source takes damage instead of healing (not blocking the drain damage, but reversing the healing direction).
- Heal Block (on the source Pokémon): prevents the HP recovery but does NOT prevent the drain damage to the seeded target.

Other interactions:
- reflectable flag: Magic Bounce and Magic Coat redirect Leech Seed back at the user.
- The volatile is cleared when the seeded Pokémon switches out.
- A Pokémon already seeded cannot be seeded again (fails with existing volatile).
- In doubles: the seed tracks the source's slot index on their side; if the source switches, the new Pokémon in that slot gets the heal.

Edge cases:
- Ingrain prevents the seeded Pokémon from switching out... wait, Ingrain is a separate volatile. Leech Seed does not prevent switching; the seeded Pokémon can switch out freely (clearing the seed upon switching).
- Grassy Terrain heals the seeded Pokémon by 1/16 at residual as well, but does not interact with Leech Seed directly.
- Substitute: if the target is behind a Substitute, Leech Seed is blocked (protect flag means it can't pierce sub through protect interaction, but actually reflectable and protect flags handle this differently—Leech Seed can't be used while the target has a Substitute).

R&B Changes:
- Accuracy increased from 90% to 100%.
</Element>

<Element name="Leaf Storm">
Type: Grass
Category: Special
Base Power: 130
Accuracy: 100 (vanilla: 90)
PP: 5
Priority: 0
Target: Single target
Contact: No
Flags: protect, mirror, metronome

Effect:
High-power Grass special attack. After use, the user's Special Attack is lowered by 2 stages.

Self-drop mechanic:
- The -2 SpA is a `self` effect (not a secondary), applied unconditionally after the move resolves.
- Does NOT interact with Sheer Force (Sheer Force only boosts moves that have secondaries targeting opponents).
- Contrary ability (on the user): reverses the -2 SpA drop into +2 SpA — makes Leaf Storm a spammable nuke that boosts itself.
- White Herb: triggers after the drop, clearing the -2 SpA to restore SpA to pre-use level. White Herb is consumed.
- Simple ability (on the user): doubles the self-drop to -4 SpA (or +4 SpA with Contrary).

Edge cases:
- Does not make contact: no Rocky Helmet etc.
- Grass type: Sap Sipper absorbs it; no damage, +1 Atk on Sap Sipper user.
- The SpA drop occurs even if the target is immune to the move (type immunity); wait—actually the `self` effect is part of the move resolving. If the move fails entirely (type immune), does the self-drop still apply? In Showdown, `self` effects typically only apply when the move hits. So if Ghost is immune to Grass (no, Grass has no type immunities except... actually Grass is not immune to any type)... but Sap Sipper absorbs Leaf Storm entirely and no damage is dealt — does the SpA drop still apply? In vanilla gen 8, when a move is absorbed by an ability like Sap Sipper, the move "hits" the target via the ability trigger; the self-drop likely still applies. This needs verification.

R&B Changes:
- Accuracy increased from 90% to 100%.
</Element>

<Element name="Focus Punch">
Type: Fighting
Category: Physical
Base Power: 150
Accuracy: 100
PP: 20
Priority: -3
Target: Single target
Contact: Yes
Flags: contact, protect, punch, failmefirst, nosleeptalk, noassist, failcopycat, failinstruct

Effect:
Extremely powerful Fighting punch with -3 priority. At the start of the turn, the user enters a "focusing" state. If the user is hit by any damaging move before Focus Punch executes, it loses focus and the move fails.

Execution sequence:
1. Turn start: the 'focuspunch' volatile is applied to the user (`priorityChargeCallback`). A "-singleturn" message is shown.
2. All other moves resolve first (Focus Punch has -3 priority; only moves with even lower priority execute after it, which there are none in practice).
3. During the turn, if any non-status move hits the user: `lostFocus = true` is set on the volatile.
4. When Focus Punch executes: if `lostFocus` → the move fails with "lost its focus" message; else → deals 150 BP damage.

Flinch immunity while focusing:
- `onTryAddVolatile` prevents the flinch volatile from being applied to the focusing user.
- Even if hit by a flinch-inducing move, Focus Punch is not disrupted by flinch specifically (only by the hit itself setting lostFocus).

Punch move:
- Iron Fist boosts Base Power by 1.2× (to 180 effective BP).

Restrictions (cannot be called by):
- failmefirst: Me First cannot copy it.
- nosleeptalk: Sleep Talk cannot select it.
- noassist: Assist cannot call it.
- failcopycat: Copycat cannot copy it.
- failinstruct: Instruct cannot call it.

Edge cases:
- No mirror flag: Mirror Move cannot copy Focus Punch.
- Status moves do NOT break focus (only `move.category !== 'Status'` sets lostFocus).
- If the user is behind a Substitute: hits to the Substitute do NOT set lostFocus (the Substitute absorbs the hit; the user themselves didn't take damage).
- Ghost type immunity: Focus Punch cannot hit Ghost types.
- Using Focus Punch from behind a Substitute is the classic interaction that makes it reliably land.
- -3 priority means it fires after almost everything, including Trick Room (which reverses speed but does not affect priority brackets).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Swagger">
Type: Normal
Category: Status
Base Power: —
Accuracy: 90 (vanilla: 85)
PP: 15
Priority: 0
Target: Opponent
Contact: No
Flags: protect, reflectable, mirror, allyanim, metronome

Effect:
Raises the target's Attack by +2 stages and confuses the target simultaneously.

Combined effect:
- Atk: +2 on the target.
- Confusion: applied as a volatileStatus (lasts 2–5 turns).
- Both effects apply together; the Atk boost makes confusion self-hits more dangerous since confusion damage scales with the target's Atk.

Ability interactions:
- Own Tempo (on the target): prevents the confusion from being applied, but the +2 Atk still occurs.
- Contrary (on the target): turns the +2 Atk boost into -2 Atk. The confusion still applies.
- Magic Bounce (on the target): reflects Swagger back at the user (due to reflectable flag).

Edge cases:
- Magic Coat: can manually reflect Swagger, directing it back at the opponent.
- The Atk boost on the target can be used against them if confusion self-hits land.
- In the Swagger + Foul Play strategy: boosting the opponent's Atk and then using Foul Play (which uses the target's Atk stat) deals more damage to the opponent.
- If the target is already confused, reapplying Swagger refreshes or overwrites the confusion timer.

R&B Changes:
- Accuracy increased from 85% to 90%.
</Element>

<Element name="Power-Up Punch">
Type: Fighting
Category: Physical
Base Power: 40
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Contact: Yes
Flags: contact, protect, mirror, punch, metronome

Effect:
Fighting punch attack. Guaranteed 100% chance to raise the user's own Attack by +1 stage after hitting.

Self-boost secondary:
- 100% activation — user's Atk always goes up +1 after a successful hit.
- This is a `secondary` with `self.boosts.atk: +1`, so it IS affected by Sheer Force: using Sheer Force removes the boost but raises Base Power to 52 (40 × 1.3).
- Contrary ability (on the user): the +1 Atk self-boost becomes -1 Atk.

Punch move:
- Iron Fist ability boosts Base Power by 1.2x (to 48 effective BP before other modifiers).
- Iron Fist stacks with other modifiers but not with Sheer Force (single ability).

Edge cases:
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Fighting type: Ghost types are immune; super effective vs Normal, Rock, Steel, Ice, Dark.
- The self-Atk boost makes this move snowball in damage over multiple turns.
- If the user is at max Atk stage (+6), the secondary has no effect but still "fires."

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Body Slam">
Type: Normal
Category: Physical
Base Power: 85 (170 vs Minimized target)
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome, minimize, nonsky

Effect:
Normal physical attack. 30% chance to paralyze the target. Deals double damage to a target that has used Minimize.

Paralysis secondary:
- 30% chance to inflict paralysis.
- Electric-type Pokémon are immune to paralysis.
- Limber ability prevents paralysis.
- Already-statused targets cannot be paralyzed.

Minimize interaction (minimize flag):
- If the target has used Minimize and the Minimize volatile is active, Body Slam deals double damage (170 effective BP).
- This bypasses evasion from Minimize as well.

Edge cases:
- Normal type: no effect against Ghost types; affected by type-changing abilities (Pixilate, etc.).
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Sheer Force (on the user): removes the 30% paralysis chance but raises Base Power to ~110 (85 × 1.3). Minimize interaction is NOT removed by Sheer Force (it's not a secondary in that sense; wait—is the double damage vs Minimize a 'secondary'? In Showdown, the Minimize interaction is handled separately by the engine's isMoveInvulnerable logic, not as a secondary. So Sheer Force only removes the paralysis secondary).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Vine Whip">
Type: Grass
Category: Physical
Base Power: 45
Accuracy: 100
PP: 25
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Basic Grass physical attack with no secondary effect.

Edge cases:
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Grass type: Sap Sipper absorbs it.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Mystical Fire">
Type: Fire
Category: Special
Base Power: 75
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Contact: No
Flags: protect, mirror, metronome

Effect:
Fire special attack. Guaranteed 100% chance to lower the target's Special Attack by 1 stage.

SpA drop secondary:
- 100% activation rate — always lowers SpA by 1 if the move hits.
- Blocked by Clear Body, White Smoke, Full Metal Body (opponent's stat-drop immunity).
- Mirror Armor: reflects the -1 SpA drop back onto the Mystical Fire user.
- Sheer Force (on the user): removes the secondary but raises Base Power to ~97 (75 × 1.3).

Edge cases:
- Does not make contact: no Rocky Helmet, Iron Barbs, etc.
- Fire type: Flash Fire absorbs it; halved in Rain/Heavy Rain; boosted 1.5x in Harsh Sun/Desolate Land.
- The SpA drop occurs even if the target's SpA is already at -6 (the drop is blocked at cap, but the move itself still connects).
- Similar to Energy Ball (which lowers SpD) but lowers SpA instead, making it useful for reducing the opponent's offensive capability.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Final Gambit">
Type: Fighting
Category: Special
Base Power: N/A (fixed damage equal to user's current HP)
Accuracy: 100
PP: 5
Priority: 0
Target: Single target
Contact: No
Flags: protect, metronome, noparentalbond (no mirror flag)

Effect:
The user deals damage equal to its current HP, then immediately faints. The user only faints if the move successfully hits (selfdestruct: "ifHit").

Damage formula:
  damage = user.currentHP (at the time the move resolves)

Self-faint condition:
- User faints ONLY if the move actually deals damage.
- If the target is immune (e.g., Ghost type), the move fails → user does NOT faint.
- If the target uses Protect/Detect/King's Shield: move is blocked → user does NOT faint.
- If the move misses (which is unlikely given 100% accuracy): user does NOT faint.

Edge cases:
- Fighting type, Special category: unusual for Fighting (most Fighting moves are Physical).
- Ghost types are immune to Fighting moves → Final Gambit fails, user survives.
- noparentalbond: Parental Bond cannot add a second hit.
- No mirror flag: Mirror Move cannot copy Final Gambit.
- Fixed damage: bypasses Defense/SpD stats, weather modifiers, and most damage multipliers. Type effectiveness still applies (Fighting resistances apply; Ghost immunity applies).
- If the user is at 1 HP: deals 1 damage to the target, then faints. Useful for guaranteed KO via combination if target already at low HP.
- Damp ability (on user's side): Damp is expected to block this move since it has the selfdestruct property (prevents Explosion/Selfdestruct family).
- The user's HP is captured at the moment of the damage callback; any damage dealt to the user earlier in the same turn (from priority moves, etc.) is already reflected.
- Wonder Guard: blocks Final Gambit if Fighting is not super effective against the target's type (Shedinja: Bug/Ghost → Ghost immune to Fighting → fails).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Natural Gift">
Type: Varies (depends on held berry)
Category: Physical
Base Power: Varies (depends on held berry)
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Contact: No
Flags: protect, mirror, metronome

Effect:
Physical attack whose type and base power are determined by the user's held berry. The berry is consumed on use. Fails if the user is not holding a berry, or if the user's item is being suppressed.

Type and power:
- Each berry has a fixed (type, power) pair for Natural Gift.
- The lookup is from the game's own berry data (gen database `naturalGift` field).
- Examples of common berries: Cheri Berry → Fire/80, Chesto Berry → Water/80, Pecha Berry → Electric/80, Rawst Berry → Fire/80, Aspear Berry → Ice/80, Leppa Berry → Fighting/80, Oran Berry → Poison/80, Persim Berry → Ghost/80, Lum Berry → Psychic/80, Sitrus Berry → Grass/80.
- Specific resist berries (Occa, Passho, etc.) and power berries (Liechi, Ganlon, etc.) have BP 80 or 100; pinch berries (Salac, Petaya, etc.) also 80 or 100. The exact mapping should be verified from game data for each berry.

Berry consumption:
- The berry is removed from the user's held item slot on use (`setItem('')`).
- Subsequent use of Natural Gift in the same battle fails (no item).

Failure conditions:
- No berry held: fails entirely.
- Item-ignoring effects (Klutz, Magic Room, Embargo): the berry is ignored → move fails (the `ignoringItem()` check causes a false return).
- Fling or Knock Off removing the berry before Natural Gift resolves: fails.

Edge cases:
- The type change happens before damage, so type-based immunities and resistances apply to the berry's type.
- Does not make contact: no contact-dependent effects.
- Unnerve ability (on the opponent): only prevents eating berries; Natural Gift's use of the berry is not affected by Unnerve (Natural Gift uses the item as a weapon, not as a consumable trigger).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Giga Drain">
Type: Grass
Category: Special
Base Power: 75
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Contact: No
Flags: protect, mirror, heal, metronome

Effect:
Grass special attack. The user recovers HP equal to 50% of the damage dealt.

Drain mechanic:
- Heals user for ½ of damage inflicted (rounded down).
- Big Root item: increases drain recovery to 65% of damage dealt (1.3× multiplier on the drain amount).
- Liquid Ooze (on the target): instead of healing, the user takes damage equal to the drain amount.
- Heal Block (on the user): prevents the HP recovery from the drain; the damage to the target still occurs normally.

Edge cases:
- Does not make contact: no Rocky Helmet, Iron Barbs, etc.
- Grass type: Sap Sipper absorbs it (user takes no damage, Sap Sipper user gains +1 Atk); drain never occurs.
- If the user is at full HP, drain healing still "occurs" mechanically but has no visible effect.
- Rain halves all Water moves and is unrelated; however, sun/rain have no effect on Grass moves directly.
- The heal flag: interacts with Heal Block and indicates this move involves healing.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Hyperspace Fury">
Type: Dark
Category: Physical
Base Power: 100
Accuracy: Never misses
PP: 5
Priority: 0
Target: Single target
Contact: No
Flags: mirror, bypasssub, nosketch

Effect:
Exclusive to Hoopa-Unbound. Dark physical attack that always hits and breaks through all protection moves. Lowers the user's own Defense by 1 stage after use.

User restriction:
- Only Hoopa-Unbound can use this move successfully.
- If Hoopa (Confined form) attempts it: move fails with a special '[forme]' fail message.
- All other Pokémon: move fails outright.
- Acquired via level-up or move list; Smeargle cannot Sketch it (nosketch flag).

Protection bypass:
- breaksProtect: true — bypasses Protect, Detect, King's Shield, Spiky Shield, Baneful Bunker, and similar protection moves. The protecting Pokémon takes full damage (and King's Shield/Spiky Shield stat-drop effects do NOT trigger on a bypassed protect).

Substitute bypass:
- bypasssub flag: damage is dealt directly to the Pokémon even if they are behind a Substitute.

Self-Defense drop:
- After a successful use, the user's Defense falls by -1 stage.
- This occurs even if the target is immune to the damage (e.g., Ghost type vs Dark... wait, Ghost is not immune to Dark. Dark has no native type immunity against it except... Fairy resists Dark but isn't immune).
- The Defense drop is a `self` effect, classified as part of the move itself (not a secondary), so it is not blocked by Shield Dust or Sheer Force.

Edge cases:
- Does not make contact: Rocky Helmet, Iron Barbs, etc. do NOT trigger.
- The Defense drop applies every use, accumulating to -6 over 6 uses (if the user survives).
- Can still be Mirrored (mirror flag): if the opponent uses Mirror Move, they would use Hyperspace Fury but fail (unless they are also Hoopa-Unbound).
- Dark type: Fairy resists it; no type immunities to Dark in gen 6+.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Focus Energy">
Type: Normal
Category: Status
Base Power: —
Accuracy: Always hits
PP: 30
Priority: 0
Target: Self
Contact: No
Flags: snatch, metronome

Effect:
Raises the user's critical hit ratio by +2 stages for the remainder of the time it remains on the field (until switching out).

Critical hit stage table (gen 8):
- Stage 0 (base): 1/24 (~4.2%)
- Stage 1 (+1): 1/8 (12.5%)
- Stage 2 (+2): 1/2 (50%)
- Stage 3+ (≥+3): guaranteed (100%)

Focus Energy: +2 stages → 50% crit chance from base.

Combined with other crit-boosting sources:
- Scope Lens / Razor Claw: +1 each → Stage 3 with Focus Energy → guaranteed crits.
- Super Luck ability: +1 → Stage 3 with Focus Energy → guaranteed crits.
- High crit ratio moves (like Night Slash, Cross Poison): +1 → Stage 3 with Focus Energy → guaranteed crits.

Interaction with Dragon Cheer (if in game):
- If the 'dragoncheer' volatile is already active on the user, Focus Energy fails to apply (the onStart returns false). They do not stack.

Edge cases:
- Volatile status: cleared when the user switches out.
- Can be Snatched (snatch flag): the Snatch user gains the +2 crit stage boost.
- Psych Up: copies Focus Energy volatile from the target to the user.
- Can be copied by Imposter and Transform.
- Using Focus Energy again while it's already active: the onStart would return false (no re-application / no stacking). Crit stage stays at +2 from a single Focus Energy.
- Battle Armor / Shell Armor: completely negates critical hits regardless of crit ratio.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Arm Thrust">
Type: Fighting
Category: Physical
Base Power: 15 per hit
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Strikes the target 2–5 times per use, each hit dealing 15 BP Fighting physical damage.

Hit count probabilities (gen 8):
- 2 hits: 1/3 (~33.3%)
- 3 hits: 1/3 (~33.3%)
- 4 hits: 1/6 (~16.7%)
- 5 hits: 1/6 (~16.7%)
- Expected hits: ~3.167; expected total BP: ~47.5

Accuracy:
- The accuracy check is performed once. All hits land if the move connects; there is no per-hit accuracy roll (unlike Triple Axel, Arm Thrust uses multihit [2,5] not multiaccuracy).

Skill Link:
- Skill Link ability guarantees 5 hits (75 total effective BP), making it significantly more reliable.

Edge cases:
- Makes contact per hit: Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities trigger for each hit.
- Substitute: each hit damages the Substitute; if broken mid-sequence, subsequent hits reach the Pokémon.
- Sturdy / Focus Sash: first hit may trigger Sturdy (surviving at 1 HP), but subsequent hits can KO through it.
- King's Rock / Stench: each hit independently rolls for flinch.
- Parental Bond does NOT add extra hits to multi-hit moves.
- Fighting type: immune to Ghost types; super effective vs Normal, Rock, Steel, Ice, Dark.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Moongeist Beam">
Type: Ghost
Category: Special
Base Power: 100
Accuracy: 100
PP: 5
Priority: 0
Target: Single target
Contact: No
Flags: protect, mirror (no metronome)

Effect:
Ghost special attack that ignores the target's ability when dealing damage.

Ability-ignoring mechanic:
- ignoreAbility: true — for the purposes of this move's damage and type-effectiveness, the target's ability is treated as if it does not exist.
- Examples of bypassed abilities: Levitate, Flash Fire, Volt Absorb, Water Absorb, Sturdy, Multiscale, Shadow Shield, Marvel Scale, Fur Coat, Thick Fat, Wonder Guard, and most other passive defensive abilities.
- Exception: Poison Heal is specifically NOT cleared in the calculator's implementation; this edge case should be verified in actual game behavior.
- The attacker's own ability is NOT suppressed (only the defender's ability is bypassed).
- Type-based immunities (from typing, not abilities) still apply: Normal-type Pokémon are immune to Ghost-type moves.

No metronome flag:
- Cannot be called by Metronome, Assist, or similar random-move selectors.

Edge cases:
- Ghost type: Normal-type Pokémon are immune regardless of ability-ignoring (type immunity is separate from ability immunity).
- Does not make contact: no Rocky Helmet etc.
- Even with ignoreAbility, type immunities from the target's types are respected (Ghost immune to Normal, etc.).
- Because Wonder Guard is bypassed: can hit Shedinja (normally Wonder Guard blocks all non-super-effective moves, but Moongeist Beam ignores Wonder Guard, and Ghost is super effective against Ghost/Bug anyway).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Stored Power">
Type: Psychic
Category: Special
Base Power: 20 + 20 × (sum of all positive stat boosts on the user)
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Contact: No
Flags: protect, mirror, metronome

Effect:
Psychic special attack whose power scales with the user's accumulated positive stat boosts. Only positive boost stages count; negative stages are ignored. Identical formula to Power Trip (which is Physical/Dark).

Base power formula:
  BP = 20 + 20 × (sum of positive boosts across all stats)

Examples:
- No boosts: 20 BP
- +1 one stat: 40 BP
- +6 all six combat stats: 20 + 20×12 = 260 BP (maximum)

Edge cases:
- Contrary ability (on the user): typical "boost" moves apply drops to the user, so stats will be negative, resulting in very low (base 20) BP.
- Boosts from any source count: Swords Dance, Calm Mind, Beast Boost, Download, stat-boosting items that raise stages, etc.
- Does not make contact: no Rocky Helmet etc.
- Psychic type: super effective vs Poison and Fighting; resisted by Psychic and Steel; immune to Dark types (Dark is immune to Psychic-type moves).
- Unaware (on the defender): ignores the attacker's offensive stat boosts for damage calculation, but does NOT reduce the base power of Stored Power (the BP is determined by positiveBoosts, not by the final attack stat).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Growth">
Type: Normal
Category: Status
Base Power: —
Accuracy: Always hits
PP: 20
Priority: 0
Target: Self
Contact: No
Flags: snatch, metronome

Effect:
Raises the user's Attack and Special Attack by +1 each. In harsh sunlight (Sunny Day or Desolate Land), both stats are raised by +2 instead.

Stat boosts:
- Normal/Rain/Sand/Hail/Snow weather: +1 Atk, +1 SpA
- Sunny Day / Desolate Land: +2 Atk, +2 SpA

Megasol ability interaction (RnB custom ability, documented in RnB Showdown):
- If the user has the 'megasol' ability and there is no active sunlight: Growth fails to give any stat boosts (boosts are deleted before applying).
- If the user has 'megasol' and it IS sunny: normal sun behavior applies (+2 Atk, +2 SpA).
- This makes Growth a sun-dependent move for any Pokémon with the megasol ability.

Edge cases:
- Can be Snatched (snatch flag): the Snatch user gains the stat boosts instead.
- Simple ability: doubles all boosts → +2/+4 in normal weather, +4/+4 in sun (for non-megasol users).
- Contrary ability: reverses the boosts → -1 Atk, -1 SpA (or -2/-2 in sun).
- Boosts are capped at +6 per stat.

R&B Changes: None listed in move changes CSV; megasol ability interaction adds conditional behavior (see above).
</Element>

<Element name="Dynamic Punch">
Type: Fighting
Category: Physical
Base Power: 100
Accuracy: 50
PP: 5
Priority: 0
Target: Single target
Contact: Yes
Flags: contact, protect, mirror, punch, metronome

Effect:
High-power Fighting punch with only 50% accuracy. If it hits, the target is guaranteed to become confused (100% secondary).

Confusion secondary:
- 100% chance to confuse the target if the move hits.
- Classified as a secondary effect, so Shield Dust (on the target) blocks the confusion.
- Sheer Force (on the user) removes the guaranteed confusion but raises Base Power to 130 (100 × 1.3).
- Own Tempo ability: target cannot be confused; confusion is blocked entirely.

Punch move:
- Iron Fist ability boosts Base Power by 1.2x (to 120 before other modifiers).
- Iron Fist + Sheer Force do not stack (they're both user abilities; a Pokémon has one ability).

Accuracy interactions:
- No Guard (on user or target): Dynamic Punch always hits. This is the classic Machamp/No Guard Dynamic Punch combo.
- Compound Eyes: boosts accuracy from 50% to 65%.
- Wide Lens: boosts accuracy from 50% to 55%.

Edge cases:
- Fighting type: immune to Ghost types; super effective vs Normal, Rock, Steel, Ice, Dark.
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- The confusion is applied as a volatileStatus, lasting 2-5 turns.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Force Palm">
Type: Fighting
Category: Physical
Base Power: 60
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Fighting-type physical attack. 30% chance to paralyze the target.

Paralysis secondary:
- 30% chance to inflict paralysis.
- Electric-type Pokémon are immune to paralysis in gen 6+.
- Limber ability prevents paralysis.
- Already-statused targets cannot be paralyzed.
- Paralysis reduces Speed to 50% and has a 25% chance to prevent action each turn.

Edge cases:
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Fighting type: immune to Ghost types; super effective vs Normal, Rock, Steel, Ice, Dark.
- Sheer Force (on the user): removes the paralysis chance, boosts Base Power to 78 (60 × 1.3).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Night Daze">
Type: Dark
Category: Special
Base Power: 85
Accuracy: 100 (vanilla: 95)
PP: 10
Priority: 0
Target: Single target
Contact: No
Flags: protect, mirror, metronome

Effect:
Dark-type special attack. 30% chance to lower the target's Accuracy by 1 stage.

Accuracy drop secondary:
- 30% activation rate (vanilla: 40%).
- Blocked by Keen Eye ability (target's Accuracy cannot be lowered).
- Mirror Armor reflects the Accuracy drop back onto the user.
- Sheer Force (on the user): removes the secondary, boosts Base Power to ~110 (85 × 1.3).
- The accuracy drop affects the target's future move accuracy rolls.

Edge cases:
- Dark type: no contact, no special immunities beyond type chart.
- Does not make contact: Rocky Helmet etc. do not trigger.
- Accuracy stat stages are shared by evasion interaction: a -1 Accuracy on the target is equivalent in effect to +1 Evasion on the user when attacking that target.

R&B Changes:
- Accuracy increased from 95% to 100%.
- Effect chance reduced from 40% to 30%.
</Element>

<Element name="Fire Lash">
Type: Fire
Category: Physical
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Fire-type physical attack. Guaranteed 100% chance to lower the target's Defense by 1 stage.

Defense drop secondary:
- 100% activation rate — always lowers Def by 1 if the move hits.
- Blocked by Mist, Clear Body, White Smoke, Full Metal Body (opponent's stat-drop immunity).
- Mirror Armor: reflects the -1 Def drop back onto the Fire Lash user.
- Sheer Force (on the user): removes the secondary effect but raises Base Power to 104 (80 × 1.3); target's Def is not lowered.

Edge cases:
- Makes contact: Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities trigger.
- Fire type: halved by Rain/Heavy Rain; boosted 1.5x in Harsh Sun/Desolate Land.
- Flash Fire ability: absorbs Fire moves and boosts the user's own Fire-type moves; no damage to the Flash Fire user.
- Water Veil / Thermal Exchange: these prevent burn but are irrelevant since Fire Lash doesn't inflict burn.
- The Def drop occurs even if the target is already at -6 Def (the drop is prevented at cap, but the move still hits).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Endeavor">
Type: Normal
Category: Physical
Base Power: N/A (fixed damage)
Accuracy: 100
PP: 5
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome, noparentalbond

Effect:
Deals damage equal to (target's current HP - user's current HP), bringing the target's HP down to match the user's. Fails if the user's HP is greater than or equal to the target's HP.

Damage formula:
  damage = target.currentHP - user.currentHP

This is fixed damage — it is not reduced by type effectiveness, stat stages, or most modifiers. The target's HP is reduced to match the user's HP exactly (if the target has enough HP remaining to make that happen).

Failure condition:
- `onTryImmunity` returns false (fails) when user.HP >= target.HP.
- Fails against Ghost types (Normal-type immunity).
- Fails if the target is protected.

Edge cases:
- Normal type: fails against Ghost types (type immunity).
- noparentalbond flag: Parental Bond cannot add a second hit.
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities on the single hit.
- Sash / Sturdy: if this move reduces a target's HP to match the user's, it doesn't "KO" (it leaves the target at the user's HP), so Sturdy and Focus Sash are irrelevant unless the user's HP is 0 (which can't happen if the user is alive).
- If the user is at 1 HP and the target is at 2+ HP: Endeavor deals damage leaving the target at 1 HP. Combined with a priority move or hazards, this can be a KO setup.
- Fixed damage moves bypass most defensive modifiers but are still blocked by type immunity and protection moves.
- Wonder Guard: blocks Endeavor because Normal does not hit Ghost types, but also Wonder Guard only blocks non-super-effective moves; however since this is Normal vs a non-Normal/non-Ghost type, Wonder Guard would block it regardless.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Triple Axel">
Type: Ice
Category: Physical
Base Power: 20 / 40 / 60 (escalates each hit; total 120 if all 3 land)
Accuracy: 90 per hit (checked independently for each hit)
PP: 10
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Strikes the target up to 3 times. Each successive hit is more powerful than the last. Each hit rolls its own accuracy check (multiaccuracy: true).

Hit-by-hit breakdown:
- Hit 1: 20 BP, 90% accuracy
- Hit 2: 40 BP, 90% accuracy (only reached if hit 1 connected)
- Hit 3: 60 BP, 90% accuracy (only reached if hits 1 and 2 connected)
- Maximum total: 120 effective BP if all 3 land
- Each hit independently rolls: P(all 3 land) = 0.9³ = 72.9%

Multiaccuracy mechanics:
- The accuracy check is rolled separately for each hit. If any hit misses, the move stops immediately (subsequent hits don't fire).
- This means it's possible to land 0, 1, 2, or 3 hits.
- Accuracy/evasion modifiers apply to each roll independently.

Edge cases:
- Makes contact per hit: Rocky Helmet, Iron Barbs, Rough Skin, and contact-triggered abilities activate for each hit landed.
- Substitute: each hit that lands damages the Substitute. If the Substitute breaks on hit 1 or 2, subsequent hits strike the Pokémon directly.
- Sturdy / Focus Sash: if the first hit brings HP to exactly 1 (or triggers Sturdy), the second hit can KO through it.
- Skill Link ability: forces all 3 hits to land regardless of accuracy rolls — the multiaccuracy check is bypassed, guaranteeing 3 hits. (Effectively 120 BP with Skill Link plus 3 contact procs.)
- No Flinch secondary: unlike some multi-hit moves, Triple Axel has no built-in flinch chance.
- King's Rock / Stench: each hit can independently roll for flinch from these items/abilities.
- Ice type: super effective vs Dragon, Flying, Grass, Ground; resisted by Ice, Steel, Water, Fire.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Solar Blade">
Type: Grass
Category: Physical
Base Power: 125 (62 when halved by non-sun weather)
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Contact: Yes
Flags: charge, protect, mirror, metronome, nosleeptalk, failinstruct, slicing

Effect:
Two-turn charging move. On turn 1, the user "soaks up sunlight" (charges). On turn 2, it attacks. In harsh sunlight (Sunny Day or Desolate Land), the charging turn is skipped and the move fires immediately. In rain, heavy rain, sandstorm, hail, or snow, the base power is halved to approximately 62.

Two-turn mechanics:
- Turn 1: The user adds the 'twoturnmove' volatile and does nothing else (vulnerable to attacks).
- Turn 2: The volatile is consumed, and Solar Blade fires.
- If the move is fully charged but the user is forced to switch or faints before turn 2, the charge is lost.

Weather interactions:
- Harsh Sun / Desolate Land: skips the charging turn entirely. Full 125 BP.
- Rain / Heavy Rain / Sandstorm / Hail / Snow: the move still requires two turns AND deals halved base power (~62 BP, via 0.5x modifier).
- Normal weather (no weather): standard two-turn sequence, full 125 BP.
- Weather changes between turns can change behavior (e.g., sun activates → skips charge; then rain comes in → would halve BP if currently in charging, but charge is already skipped).

Slicing move:
- The slicing flag means Sharpness boosts the power by 1.5x.
- No effect from Sound-related abilities (it's not a sound move).

Power Herb:
- Holding Power Herb allows the user to fire Solar Blade on the first turn (consumed on use), but does NOT prevent the BP halving in non-sun weather.

Edge cases:
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Cannot be called by Sleep Talk (nosleeptalk flag) or Instruct (failinstruct flag) during the charge turn.
- Grass type: Sap Sipper absorbs it; does not affect Flying/Grass/Poison/Bug/Steel/Dragon (resistance chart normal).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Shell Smash">
Type: Normal
Category: Status
Base Power: —
Accuracy: Always hits
PP: 15
Priority: 0
Target: Self
Contact: No
Flags: snatch, metronome

Effect:
Raises the user's Attack, Special Attack, and Speed by +2 stages each. Lowers the user's Defense and Special Defense by -1 stage each.

Stat changes (all applied simultaneously):
- Atk: +2
- SpA: +2
- Spe: +2
- Def: -1
- SpD: -1

Ability interactions:
- Contrary: reverses all changes → Atk/SpA/Spe go DOWN by 2, Def/SpD go UP by 1.
- Simple: doubles all changes → Atk/SpA/Spe go up by 4, Def/SpD go down by 2.
- Clear Body / White Smoke / Full Metal Body: these prevent stat drops from opponents, but Shell Smash is self-applied. They do NOT block the Def/SpD drops.

Item interactions:
- White Herb: triggers after Shell Smash, clearing the -1 Def and -1 SpD drops. The White Herb is consumed on use.
- Power Herb, Choice items, etc.: no interaction.

Edge cases:
- Can be Snatched (snatch flag): the Snatch user gains the stat changes (the boosts and drops apply to the Snatch user, not the original Shell Smash user).
- The stat boosts are capped at +6 and the drops are capped at -6. If the user is already at -6 Def/SpD or +6 Atk/SpA/Spe, the relevant stat changes have no effect (but the move still succeeds).
- Baton Pass can pass the stat boosts (and remaining drops) to a switch-in.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="High Horsepower">
Type: Ground
Category: Physical
Base Power: 95
Accuracy: 100 (vanilla: 95)
PP: 10
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Strong Ground-type physical attack with no additional effect.

Edge cases:
- Ground type: does not affect Flying-type Pokémon, or Pokémon with Levitate. Also blocked by Magnet Rise and Air Balloon.
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Earth Power is its Special counterpart (same type, different category and base power).
- Grounded by Gravity or Ingrain: Flying types and Levitate users that are grounded by Gravity or Ingrain CAN be hit.

R&B Changes:
- Accuracy increased from 95% to 100%.
</Element>

<Element name="Aromatherapy">
Type: Grass
Category: Status
Base Power: —
Accuracy: Always hits
PP: 5
Priority: 0
Target: Ally team (all Pokémon on the user's side, including benched)
Contact: No
Flags: snatch, distance, metronome

Effect:
Cures all non-volatile status conditions (burn, freeze, paralysis, poison, badly poisoned, sleep) from all Pokémon on the user's side of the field, including benched Pokémon.

Cure mechanic:
- The user itself is always cured (no ability or substitute checks applied to the user).
- Benched allies are included and cured without restriction.
- For active non-user allies:
  - Sap Sipper: grants immunity to Aromatherapy (it is a Grass-type move); that ally is skipped.
  - Good as Gold: grants immunity to status-affecting moves on allies; that ally is skipped.
  - Substitute: if an ally is behind a Substitute, they are skipped (Aromatherapy does not infiltrate).
- The move returns "fail" if no Pokémon had a status cured.

Edge cases:
- Can be Snatched (snatch flag): the Snatch user steals the effect and cures their own team's statuses instead.
- Heal Bell is functionally similar but is Normal-type and has slightly different ability interaction text; Aromatherapy is Grass-type, so Sap Sipper immunity applies.
- Does not cure volatile status (confusion, infatuation, flinch, etc.)—only non-volatile (persistent) statuses.
- Pokémon with Comatose are considered permanently "asleep" via ability, not via a status condition; Aromatherapy does not interact with Comatose.
- Using Aromatherapy when the entire team has no statuses still uses the PP (but fails in terms of the success flag).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Volt Switch">
Type: Electric
Category: Special
Base Power: 70
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Contact: No
Flags: protect, mirror, metronome

Effect:
Electric special attack. After dealing damage, the user immediately switches out to another Pokémon in the party (selfSwitch: true).

Switch mechanics:
- The switch is triggered after damage is dealt, even if the target faints.
- If the user is the last Pokémon in the party (no eligible switch-ins), the move still deals damage but the switch does not occur.
- If the user is trapped (Arena Trap, Shadow Tag, Mean Look, partiallytrapped/Bind, Ingrain), the damage is still dealt but the self-switch is blocked.
- The user switching out removes all volatile status conditions from the user (confusion, infatuation, Leech Seed volatile, etc.).
- Entry hazards are triggered on the switch-in of the replacement Pokémon.

Edge cases:
- Ground types are immune to Electric; Volt Switch fails to deal damage against them, and the self-switch does NOT occur (since the move was blocked).
- Lightning Rod / Volt Absorb / Motor Drive: the move is absorbed/redirected before damage, so no switch occurs.
- Electric Terrain: boosts the power of Electric moves used by grounded Pokémon by 1.3x.
- Does not make contact: no Rocky Helmet, Iron Barbs, etc.
- Emergency Exit / Wimp Out (if the defender's HP drops to 50% or below from the hit): the defender's ability may also trigger a switch for the opposing side.
- In doubles, the user switches out to a reserve (benched) Pokémon.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Seed Flare">
Type: Grass
Category: Special
Base Power: 120
Accuracy: 90 (vanilla: 85)
PP: 5
Priority: 0
Target: Single target
Contact: No
Flags: protect, mirror, metronome

Effect:
High-power Grass special attack. 40% chance to lower the target's Special Defense by 2 stages.

SpD drop secondary:
- 40% chance to apply -2 Special Defense to the target.
- Blocked by Mist, Clear Body, White Smoke, Full Metal Body, and similar SpD-drop-immunity effects.
- Mirror Armor reflects the stat drop back to the user.
- Sheer Force (on the user) removes the secondary but boosts Base Power by 1.3x.

Edge cases:
- Grass type: not effective against Grass, Poison, Dragon, Bug, Flying, Steel; immune to Water, Ground, Rock types absorb Grass (via abilities only—no native type immunity to Grass).
- Sap Sipper: Grass-type moves are absorbed, triggering the ability and granting +1 Atk to the target; no damage dealt.
- No contact: does not trigger contact-dependent abilities.
- Despite the high secondary rate (40%), it is still classified as a secondary, so it is subject to Shield Dust and Sheer Force interactions.

R&B Changes:
- Accuracy increased from 85% to 90%.
</Element>

<Element name="Poltergeist">
Type: Ghost
Category: Physical
Base Power: 110
Accuracy: 90
PP: 5
Priority: 0
Target: Single target
Contact: No
Flags: protect, mirror, metronome

Effect:
High-power Ghost physical attack. Fails entirely if the target is not holding an item.

Failure condition:
- The move calls `onTry` which returns `!!target.item`. If target.item is empty/falsy, the move fails before damage is dealt.
- Fails if the target's item has been consumed (berry eaten, gem used, Air Balloon popped, etc.).
- Fails if the target has no item equipped at all.

Item status nuances:
- Klutz ability: the Pokémon cannot use its held item, but still holds it. Poltergeist succeeds against Klutz users.
- Magic Room: items are suppressed from functioning, but still held. Poltergeist succeeds in Magic Room.
- Embargo: same as Klutz/Magic Room — item is still held, Poltergeist succeeds.
- Corrosive Gas or Knock Off that have removed the item: target.item is now empty, so Poltergeist fails.

Edge cases:
- Ghost type: Normal-type Pokémon are immune to Ghost-type moves (Poltergeist fails against Normal types due to type immunity, independently of the item check).
- Does not make contact: Rocky Helmet, Iron Barbs, and contact-dependent abilities do NOT trigger.
- Despite being Physical, Ghost-type moves can hit Foresighted or Odor Sleuthed targets regardless of Normal type.
- The item name is shown to the player in the activation message, revealing what item the target holds.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Retaliate">
Type: Normal
Category: Physical
Base Power: 70 (140 if a teammate fainted last turn)
Accuracy: 100
PP: 5
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Normal-type physical attack. Base power doubles to 140 if any Pokémon on the user's side fainted on the previous turn.

Double BP condition:
- Checks `pokemon.side.faintedLastTurn` — a side-wide flag set when any Pokémon on the side fainted during the previous turn.
- "Last turn" means the turn immediately before this one. If the ally fainted two or more turns ago, the bonus does not apply.
- In singles: only the user's own Pokémon can set this flag (since there's only one Pokémon per side).
- In doubles: either ally fainting on the prior turn triggers the bonus.

Edge cases:
- Normal type: no effect against Ghost types; affected by type-changing abilities (Pixilate, etc.).
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- The faintedLastTurn flag resets each turn, so Retaliate only gets the bonus for exactly one turn after an ally faints.
- If the user itself is switched in on the turn after an ally fainted (and faintedLastTurn is still set), the bonus applies.
- Using Retaliate multiple times in one turn (e.g. via Parental Bond) does not reset the flag; both hits get the doubled BP on that turn.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fiery Wrath">
Type: Dark
Category: Special
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: All adjacent foes (spread move)
Contact: No
Flags: protect, mirror (no metronome)

Effect:
Dark-type special attack that hits all adjacent foes. 20% chance to flinch each target hit.

Spread mechanics:
- In doubles, hits both opposing Pokémon simultaneously.
- Spread moves receive a 0.75x damage multiplier when hitting multiple targets in doubles.

Flinch secondary:
- 20% flinch chance applied to each target independently.
- Flinch only takes effect if the target has not yet moved this turn.
- Inner Focus and Shield Dust prevent flinching.
- Sheer Force (on the user) removes the flinch secondary but boosts power by 1.3x.

Edge cases:
- Does NOT have the metronome flag; cannot be called by Metronome, Sleep Talk (as a spread/restricted move? actually Sleep Talk doesn't exclude by metronome flag—check separately), or Copycat in standard rules.
- Dark type: not resisted by any type, super effective vs Psychic and Ghost, resisted by Dark/Fighting/Fairy.
- No contact: does not trigger Rocky Helmet, Iron Barbs, Rough Skin, etc.
- King's Rock / Stench: flinch chance does not stack with or add to the built-in secondary flinch.
- Flinch rolls are per-target in doubles (each target rolls independently).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Dual Chop">
Type: Dragon
Category: Physical
Base Power: 40 per hit (always 2 hits; effective total: 80)
Accuracy: 100 (vanilla: 90)
PP: 15
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Strikes the target exactly twice in one turn. Each hit is calculated and applied independently.

Multi-hit mechanics:
- The accuracy check is performed once at the start. If the move misses, neither hit lands.
- Each hit deals its own damage roll (subject to the damage formula separately).
- Each hit can independently trigger contact-based effects (Rocky Helmet, Iron Barbs, Rough Skin, static/flame body, etc.).
- Each hit rolls independently for critical hits.
- Sturdy / Focus Sash: if the first hit reduces HP to exactly 1 (or Sturdy activates), the second hit can still KO.
- Substitute: if the first hit breaks the Substitute, the second hit strikes the Pokémon directly.
- Sheer Force does not apply (no secondary effect to remove).
- Skill Link has no effect (Dual Chop is always exactly 2 hits, not a variable multi-hit).
- King's Rock / Stench: flinch chance applies per hit, slightly increasing the effective chance over two rolls.

Edge cases:
- Dragon type; Dragon-type immunity: Fairy types are immune to Dragon moves.
- Each hit activates Anger Point separately if a critical hit occurs.
- Makes contact per hit: two Rocky Helmet triggers, two Iron Barbs procs, etc.
- Parental Bond (if the user has it): does NOT add an extra hit to a move that already hits multiple times.

R&B Changes:
- Accuracy increased from 90% to 100%.
</Element>

<Element name="Power Trip">
Type: Dark
Category: Physical
Base Power: 20 + 20 × (sum of all positive stat boosts on the user)
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Power scales with the user's accumulated positive stat boosts. Only positive boost stages count; negative stages are ignored.

Base power formula:
  BP = 20 + 20 × (sum of positive boosts across all stats)

Stat stages included: Atk, Def, SpA, SpD, Spe, Accuracy, Evasion — any stat stage that is positive contributes.

Examples:
- No boosts: 20 BP
- +1 Atk: 40 BP
- +2 Atk: 60 BP
- +2 Atk, +2 Spe: 100 BP
- +6 all six combat stats: 20 + 20×12 = 260 BP (maximum)

Note: Power Trip and Stored Power share the same formula. Power Trip is Physical/Dark; Stored Power is Special/Psychic.

Edge cases:
- Negative stat stages do NOT subtract from the count.
- Boosts gained via Unaware by the attacker: Unaware ignores the opponent's boosts, not the user's own boosts—Power Trip is based on the user's boosts, so Unaware on the defender does not reduce Power Trip's base power.
- Contrary ability (on the user): since Contrary turns all boosts into drops, stats will be negative after typical "boost" effects, leading to very low BP when used under Contrary.
- Stat boosts from abilities (Anger Point, Download, Beast Boost, etc.) count toward the BP just like move-applied boosts.
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sand Tomb">
Type: Ground
Category: Physical
Base Power: 35
Accuracy: 100 (vanilla: 85)
PP: 15
Priority: 0
Target: Single target
Contact: No
Flags: protect, mirror, metronome

Effect:
Deals damage and traps the target in a sandstorm vortex for 4–5 turns (the 'partiallytrapped' volatile). While trapped, the target takes residual damage each turn and cannot switch out as long as the user remains active.

Binding duration:
- Normally lasts 5 or 6 turns (random; the volatile starts with this duration, so the binding includes the turn it is applied plus 4 or 5 additional turns).
- With Grip Claw held by the user: always 8 turns.

Residual damage per turn:
- 1/8 of the target's maximum HP per turn (applied at end of each turn while bound).
- With Binding Band held by the user: 1/6 of maximum HP per turn.

Trapping:
- Target cannot switch out while partiallytrapped and the user is still active on the field.
- If the user switches out, faints, or has not had a turn (activeTurns == 0), the trap is immediately released.
- Ghost types can escape regardless of trapping (Ghost types are never truly trapped).
- Shed Shell item allows the trapped target to switch out.
- Baton Pass, U-turn, Volt Switch, Flip Turn, and Parting Shot bypass the trap (these force switches or are self-initiated).

Edge cases:
- Ground type: cannot hit Flying types or Pokémon with Levitate while airborne; does not hit if the target uses Magnet Rise.
- The binding damage is separate from the initial hit damage—an attack that KOs on the initial hit does not apply any residual bind damage.
- Arena Trap, Shadow Tag, Mean Look do NOT stack with partiallytrapped; they operate independently, but partiallytrapped alone is sufficient to prevent switching.
- If the user Transforms or changes form, the volatile source updates (the source reference still tracks the same battle slot).
- Does not make contact: contact-dependent abilities (Rocky Helmet, Iron Barbs, Rough Skin) do NOT trigger.

R&B Changes:
- Accuracy increased from 85% to 100%.
</Element>

<Element name="Feint Attack">
Type: Dark
Category: Physical
Base Power: 60
Accuracy: Never misses
PP: 20
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Dark-type physical attack that never misses.

Edge cases:
- Always hits regardless of accuracy/evasion modifiers (Minimize, Double Team, Sand/Snow evasion, etc.) — accuracy is 'true' (bypasses accuracy check entirely).
- Still blocked by Wonder Guard (no type effectiveness) and type immunities.
- NOT blocked by Bright Powder or Lax Incense (those reduce accuracy check rolls; since there is no accuracy roll, they are irrelevant).
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Dark type: immune to Prankster-boosted status moves; no type immunities against it except Fairy (if Gen 6+ rule applied—Dark has no immunities in gen 8).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Wake-Up Slap">
Type: Fighting
Category: Physical
Base Power: 70 (140 against sleeping targets or Comatose)
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Deals damage. Base power doubles if the target is asleep or has the Comatose ability. If the target is asleep (status == 'slp'), the hit also cures that sleep.

Base power scaling:
- Normal: 70
- Target asleep (slp): 140
- Target has Comatose ability: 140 (Comatose acts as perpetual sleep for move-interaction purposes)

Sleep cure mechanic:
- The sleep cure triggers in onHit (after damage), so the doubled BP from sleeping is applied first, THEN sleep is cured.
- Only cures via the actual 'slp' status. Does NOT cure Comatose (that is an ability, not a status condition).

Edge cases:
- If Comatose target: BP doubles to 140, but sleep is NOT cured (onHit only checks status === 'slp', not the ability).
- A sleeping target that woke up at the start of the turn (natural wake from sleep turns expiring): if the status has already been cleared, Wake-Up Slap deals the base 70 BP.
- Makes contact: triggers Rocky Helmet, Iron Barbs, Rough Skin, etc.
- Fighting type; no effect against Normal, Ice, Rock, Steel, Dark types (not immune—those are type matchup notes). Ghost types are immune to Fighting.
- Sheer Force removes... wait, Wake-Up Slap's BP-doubling is not a "secondary effect" in the Sheer Force sense—it's a basePowerCallback. Sheer Force does NOT remove the sleep-curing onHit. Actually Sheer Force only boosts moves that have a `secondary` or certain `self`/`target` effects; the sleep-cure is an onHit effect, not a secondary, so Sheer Force does NOT interact with this move.
- The sleep cure happens even if the Pokémon faints from the hit (if target.status === 'slp' and it survives, it cures; if it faints, cureStatus is called but doesn't matter).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Imprison">
Type: Psychic
Category: Status
Base Power: —
Accuracy: Always hits
PP: 10
Priority: 0
Target: Self
Contact: No
Flags: snatch, bypasssub, metronome, mustpressure

Effect:
Applies the 'imprison' volatile to the user. While active, all opposing Pokémon are prevented from using any move that also appears in the Imprison user's moveset (matched by move ID).

Disable mechanic:
- onFoeDisableMove: marks matching moves as disabled on foes (for UI/display).
- onFoeBeforeMove: prevents execution if the foe's chosen move matches a move in the Imprison user's current moveset.
- Only applies to opponents, not allies (doubles partners are unaffected).

Edge cases:
- Struggle ignores Imprison (explicitly exempted).
- Z-moves and Max moves (Dynamax) bypass Imprison even if the base move is shared.
- noCopy: the volatile cannot be copied by Baton Pass or similar effects.
- Can be Snatched: the Snatch user gains the Imprison effect instead.
- mustpressure flag: Pressure ability always activates PP drain even through Imprison (the flag ensures pressure applies to the move user's PP).
- If the Imprison user faints or switches out, the volatile presumably ends (the effectState.source becomes invalid).
- In doubles/multi-battle: locks out ALL opponents that share a move, not just one.
- The check is against the user's current moveslots—if the user loses a move (e.g., Mimic, Transform), the locked-out set changes accordingly.
- Imprison itself can be Imprisoned if the opponent also knows Imprison.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Roost">
Type: Flying
Category: Status
Base Power: —
Accuracy: —
PP: 5 (vanilla: 10)
Priority: 0
Target: Self
Contact: No
Flags: snatch, heal, metronome

Effect:
Heals the user for 50% of its maximum HP. Also applies the 'roost' volatile status for the remainder of the turn, which removes the Flying type from the user's type(s) until end of turn.

Type suppression mechanic:
- The Flying type is filtered out of the user's effective type list for the current turn only.
- Pure Flying types (e.g., a Pokémon with only the Flying type) become typeless for the turn.
- Dual-type Pokémon with Flying lose only that type (e.g., Charizard Fire/Flying → Fire-only for the turn).
- The type removal is checked at lowest type-determination priority, so all type-dependent effects during that turn (incoming moves, abilities, hazards) see the non-Flying version.

Edge cases:
- Failing at full HP: Roost fails if the user is already at full HP.
- Ground/Rock/Electric immunity removed: while the roost volatile is active, a normally-immune Flying type can be hit by Ground, or take super-effective Rock/Electric damage (if pure Flying → typeless).
- Entry hazards: a pure Flying type under the roost volatile is affected by Spikes/Toxic Spikes/Sticky Web for the rest of that turn (normally immune).
- Gravity: the roost volatile's type suppression still applies; Gravity separately grounds Pokémon so Ground moves hit regardless.
- Terastallized Pokémon: if the Pokémon is Terastallized and has the Flying Tera type, the type-suppression portion of the volatile does NOT apply (the onStart returns early). The HP heal still occurs.
- Can be Snatched (snatch flag): if a Snatch user steals it, the Snatch user heals and applies the roost volatile to themselves.
- Heal Block: Roost fails entirely when Heal Block is active on the user.

R&B Changes:
- PP reduced from 10 to 5.
</Element>

<Element name="Waterfall">
Type: Water
Category: Physical
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Contact: Yes
Flags: protect, mirror, metronome

Effect:
Water physical attack. 20% chance to cause the target to flinch.

Flinch secondary:
- 20% chance to flinch.
- Flinch only applies if the target has not yet moved this turn.
- Inner Focus and Shield Dust abilities prevent flinching.
- Sheer Force (on the user) removes the flinch chance but boosts Base Power by 1.3x.

Edge cases:
- Makes contact; triggers Rocky Helmet, Iron Barbs, Rough Skin, and contact-dependent abilities.
- Water type; no special immunities, but Storm Drain / Water Absorb / Dry Skin absorb the move.
- Boosted 1.5x in Rain; halved in Sun.
- Swift Swim, Rain-boosted Pokémon etc. have no direct interaction with Waterfall itself, but weather context matters for damage.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Shell Side Arm">
Type: Poison
Category: Special (by default; see category determination below)
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Contact: Only when Physical (see below)
Flags: protect, mirror, metronome (contact added dynamically when Physical)

Effect:
Deals damage and has a 20% chance to poison the target.

Category determination:
Before dealing damage, the move compares which category would deal more damage to the target, using the final in-battle stats (including stat stage modifiers):
  - Physical damage proxy: attacker.Atk / defender.Def
  - Special damage proxy: attacker.SpA / defender.SpD
  - If physicalProxy > specialProxy → the move is Physical for this use
  - If specialProxy >= physicalProxy → the move is Special for this use (ties go Special per the calculator; Showdown uses a 50/50 coin flip on exact ties)

This means:
- Attack/Defense stat stages on either side can flip the category mid-battle.
- When Physical: uses Atk vs Def for damage, and the move gains the contact flag.
- When Special: uses SpA vs SpD for damage, no contact.

Poison secondary:
- 20% chance to inflict regular poison (not badly poisoned).
- Blocked by Poison- and Steel-type immunity.
- Blocked by abilities such as Immunity, Pastel Veil, etc.
- A Poison-type user applying this move still triggers the secondary (Poison types can poison via their own moves).

Edge cases:
- Contact-dependent effects (Rocky Helmet, Iron Barbs, Rough Skin, static/flame body, etc.) only trigger when the move resolves as Physical.
- Unburden/Gooey/Tangling Hair and other on-contact abilities similarly only fire when Physical.
- Sneak Attack / Punk Rock / etc. that care about contact or category use the resolved category for this turn.
- Against a target behind a Substitute: still hits (no bypasssub flag, so it does NOT bypass sub—wait: Showdown flags are protect, mirror, metronome only, no bypasssub). Poison chance does not apply through Substitute.
- Corrosion (Salandit line): allows poisoning Steel/Poison types with the secondary.
- The category is determined using the attacker's and defender's FINAL stats (post-boost), not base stats, so mid-battle boosts actively change which category is used.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Boomburst">
Type: Normal
Category: Special
Base Power: 140
Accuracy: 100
PP: 10
Priority: 0
Target: All adjacent (hits all adjacent Pokémon, including allies in doubles)
Contact: No
Flags: protect, mirror, sound, bypasssub, metronome

Effect:
High-power Normal-type special attack that hits all adjacent targets simultaneously.

Sound move interactions:
- Bypasses Substitute (bypasssub flag)
- Blocked entirely by Soundproof ability (no damage dealt)
- Boosted by Punk Rock (+30% power when used by a Punk Rock user; incoming Boomburst damage halved for Punk Rock users)
- Triggers Throat Spray on use (raises Sp. Atk by 1 if the user holds it)

Doubles interactions:
- Hits all adjacent Pokémon, including the user's own ally. Ally damage is not reduced by a spread modifier in RnB (verify if RnB applies spread damage reduction—vanilla gen 8 applies 0.75x to spread moves).

Edge cases:
- Normal type, so immune to Ghost types; no effect against Ghost-type targets.
- Affected by Pixilate/Aerilate/Refrigerate/Galvanize (converts Normal moves to another type), gaining both the type change and the 1.2x boost.
- Does not make contact, so no contact-triggered effects (Rocky Helmet, Iron Barbs, etc.).
- Metronome can call it; no restrictions aside from standard Metronome exclusions.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Origin Pulse">
Type: Water
Category: Special
Base Power: 110
Accuracy: 100 (R&B change; vanilla 85%)
PP: 10
Priority: 0
Target: allAdjacentFoes (spread)
Flags: pulse, protect, mirror

Mechanics:
- Spread move targeting all adjacent foes. In doubles, deals 0.75× damage to all targets.
- Pulse flag: boosted 1.5× by Mega Launcher ability.
- No contact; does not trigger contact-based effects.
- No secondary effects.

R&B Changes: Accuracy increased from 85% to 100%.
</Element>

<Element name="Incinerate">
Type: Fire
Category: Special
Base Power: 60
Accuracy: 100
PP: 15
Priority: 0
Target: allAdjacentFoes (spread)
Flags: protect, mirror, metronome

Mechanics:
- Spread move targeting all adjacent foes. In doubles, deals 0.75× damage to all targets.
- No contact.
- On hit: destroys the target's Berry or Gem (item is removed and cannot be recovered via Recycle or similar).
- Does not destroy other held items, only Berries and Gems specifically.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Slash">
Type: Normal
Category: Physical
Base Power: 70
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: contact, slicing, protect, mirror, metronome

Mechanics:
- High critical hit ratio (critRatio: 2 = +1 crit stage, approximately 12.5% crit chance).
- Slicing flag: boosted 1.5× by Sharpness ability.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Psycho Cut">
Type: Psychic
Category: Physical
Base Power: 70
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: slicing, protect, mirror, metronome

Mechanics:
- High critical hit ratio (critRatio: 2 = +1 crit stage, approximately 12.5% crit chance).
- Slicing flag: boosted 1.5× by Sharpness ability.
- No contact despite being a physical move; does not trigger contact-based effects.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Hidden Power Ice">
Type: Ice (fixed; determined by user's IVs in practice)
Category: Special
Base Power: 60 (always 60, regardless of IVs)
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: protect, mirror

Mechanics:
- Hidden Power's type is determined by the Pokémon's IVs. "Hidden Power Ice" represents the Ice-typed variant.
- Base power is always 60 in gen 6+. Type is the only variable.
- No contact; no secondary effects.
- Not boosted by type-enhancing abilities or items that reference the base "Hidden Power" move name specifically — it uses its actual typing (Ice) for all damage calculations, STAB, and type effectiveness.

R&B Changes: None. Vanilla gen 8 mechanics apply (always 60 BP, type from IVs).
</Element>

<Element name="Gyro Ball">
Type: Steel
Category: Physical
Base Power: Variable (see formula)
Accuracy: 100
PP: 5
Priority: 0
Target: Single target
Flags: contact, bullet, protect, mirror, metronome

Mechanics:
- BP formula: min(150, floor(25 × targetSpe / userSpe) + 1)
  - Rewards low user speed relative to target speed; higher BP the slower the user.
  - If userSpe = 0, BP = 1.
  - Example: target has 2× user's speed → floor(25×2) + 1 = 51 BP.
  - Capped at 150 BP.
- Bullet flag: blocked entirely by Bulletproof ability.
- Contact move.
- Speed used is the stat after modifiers (Trick Room does not affect the ratio; raw speed values are compared).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Storm Throw">
Type: Fighting
Category: Physical
Base Power: 60
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- willCrit: true — always deals a critical hit.
- The guaranteed critical hit is blocked by Battle Armor and Shell Armor abilities (and Lucky Chant side condition).
- Contact move.
- No secondary effects.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Will O Wisp">
Type: Fire
Category: Status
Base Power: —
Accuracy: 85
PP: 15
Priority: 0
Target: Single target
Flags: protect, reflectable, mirror, metronome

Mechanics:
- Inflicts Burn status on the target.
- reflectable: bounced back by Magic Coat or Magic Bounce ability.
- Fire-type immunity: Pokémon with Fire type or the Flash Fire ability are immune.
- No contact; no damage.

AI edge cases (from AI.md):
- Base AI score: +6.
- ~37% of the time: additionally checks if target has a physical attacking move (+1 more) and if the AI's side has a Hex user (+1 more).
- The other ~63% of the time: no extra bonuses beyond the base +6.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Liquidation">
Type: Water
Category: Physical
Base Power: 85
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- 20% chance to lower target's Defense by 1 stage.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Nasty Plot">
Type: Dark
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Self
Flags: snatch, metronome

Mechanics:
- Raises the user's Special Attack by 2 stages.
- snatch flag: can be stolen by a Snatch user, in which case the Snatch user receives the +2 SpAtk boost instead.

AI edge cases (from AI.md):
- Base AI score: +6.
- If target is incapacitated (frozen with no thaw move, asleep, recharging, or Truant): +3.
- If target cannot 3HKO the AI mon: +1; and another +1 if AI is faster than target.
- If AI is slower than target and target can 2HKO: -5.
- If AI is already at +2 SpAtk or higher: -1.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Lash Out">
Type: Dark
Category: Physical
Base Power: 75 (150 if condition met)
Accuracy: 100
PP: 5
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- BP doubles to 150 if the user had its stats lowered this turn (Showdown: tracks `statsLoweredThisTurn`).
- Calculator condition: BP doubles when the user's net stat stages (sum of all boosts) are negative (`countBoosts(gen, attacker.boosts) < 0`). This differs from Showdown's per-turn tracking.
- Contact move.

Note: The calculator and Showdown differ on when Lash Out doubles its BP. The calculator uses current net negative stat stages; Showdown uses whether any stat drop occurred this turn. Use the calculator's behavior for damage calculation tests.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Rock Blast">
Type: Rock
Category: Physical
Base Power: 25 per hit
Accuracy: 100 (R&B change; vanilla 90%)
PP: 10
Priority: 0
Target: Single target
Flags: bullet, protect, mirror, metronome

Mechanics:
- multihit: [2, 5] — hits 2–5 times. Distribution: 2 or 3 hits at 3/8 probability each, 4 or 5 hits at 1/8 each. With Skill Link ability: always 5 hits.
- Bullet flag: blocked entirely by Bulletproof ability.
- No contact; each hit can independently break Sturdy or a Focus Sash.
- Each hit rolls separately for any triggered effects.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Misty Explosion">
Type: Fairy
Category: Special
Base Power: 200 (R&B change; vanilla 100)
Accuracy: 100
PP: 5
Priority: 0
Target: allAdjacent (hits all adjacent Pokémon, including ally)
Flags: protect, mirror, metronome

Mechanics:
- selfdestruct: "always" — user faints after use regardless of whether the move hits.
- Misty Terrain boost: BP multiplied by 1.5× if the user is grounded and Misty Terrain is active (calculator: dfMods; actual BP shown as 1.5× in calc output).
- Halves target's defense in damage calculation (R&B mechanic, also applies to Explosion and Self-Destruct): defense modifier ×0.5 applied during damage formula. This restores the gen 4 Explosion mechanic that was removed in gen 5.
- In doubles, hits all adjacent targets (both foes and ally); each takes 0.75× damage from the spread modifier.
- No contact.

AI edge cases (from AI.md, shared with Explosion and Self-Destruct):
- Below 10% HP: +10 score.
- Below 33% HP: +8 (~70%) or +0 (~30%).
- Below 66% HP: +7 (50%) or +0 (50%).
- Otherwise: +7 (~5%) or +0 (~95%).
- AI will not use a boom move if target is immune, or if the AI's mon is the last remaining and the player still has multiple mons.
- If both AI and player are on their last mon: -1 applied to score.

R&B Changes: Base power increased from 100 to 200. Defense-halving in damage calculation added (R&B mechanic shared with Explosion and Self-Destruct).
</Element>

<Element name="Baton Pass">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 40
Priority: 0
Target: Self
Flags: metronome

Mechanics:
- selfSwitch: 'copyvolatile' — user switches out and the incoming Pokémon inherits the user's stat stage changes and most volatile statuses (Substitute, Leech Seed, Confusion, Magnet Rise, Ingrain, Power Trick, Aqua Ring, etc.).
- Fails if the user's side has no available switches, or if the user is under the Commanded volatile (Dondozo controlled by Tatsugiri).

AI edge cases (from AI.md):
- If AI has a switchable mon AND (is behind a Substitute OR has a stat raised): +14.
- If AI mon is the last remaining mon: never use (-20).
- If AI has a switchable mon but no Substitute or stat boosts: +0.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Yawn">
Type: Normal
Category: Status
Base Power: —
Accuracy: —(always succeeds if it contacts the target)
PP: 10
Priority: 0
Target: Single target
Flags: protect, reflectable, mirror, metronome

Mechanics:
- Applies the 'yawn' volatile status to the target. After 2 turns (end of the following turn's residual phase), inflicts Sleep if all sleep conditions are still met.
- Fails immediately if the target already has a non-volatile status or is immune to sleep (Electric Terrain, Insomnia, Vital Spirit, etc.).
- reflectable: bounced by Magic Coat or Magic Bounce.
- noCopy: yawn volatile is NOT passed via Baton Pass.
- Switching out after being hit by Yawn removes the volatile before Sleep is applied.

AI edge cases (from AI.md, applies to all non-damaging sleep moves including Yawn):
- Base score: +6.
- 25% of the time: additional +1 if target can be put to sleep; another +1 if AI has Dream Eater/Nightmare and target lacks Snore/Sleep Talk; another +1 if AI/partner has Hex.
- The other 75% of the time: no additional bonuses.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Metronome">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Self
Flags: failencore, nosleeptalk, noassist, failcopycat, failmimic, failinstruct

Mechanics:
- Randomly selects and executes any move that has the `metronome` flag in its definition. The called move is used with all of its normal properties and effects.
- Excluded from: Encore, Sleep Talk, Assist, Copycat, Mimic, and Instruct.
- callsMove: true — the called move's own flags, effects, and accuracy apply; Metronome itself does not have protect, mirror, etc.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Low Sweep">
Type: Fighting
Category: Physical
Base Power: 65
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- 100% chance to lower the target's Speed by 1 stage.
- Contact move.

AI edge cases (from AI.md, shared with Icy Wind, Electroweb, Rock Tomb, Mud Shot):
- If Low Sweep is the highest-damage move available: scored as a regular damaging move (+6 at 80% or +8 at 20%); speed reduction bonus not applied.
- Otherwise, if AI is slower than target and target lacks Contrary/Clear Body/White Smoke: +6.
- Otherwise: +5.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sludge Wave">
Type: Poison
Category: Special
Base Power: 95
Accuracy: 100
PP: 10
Priority: 0
Target: allAdjacent (hits all adjacent Pokémon including ally in doubles)
Flags: protect, mirror, metronome

Mechanics:
- 10% chance to poison each target hit.
- Spread move; in doubles, deals 0.75× damage to all targets and can hit the ally.
- No contact.
- Poison-type Pokémon are immune.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sleep Talk">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Self
Flags: failencore, nosleeptalk, noassist, failcopycat, failmimic, failinstruct

Mechanics:
- sleepUsable: true — can only be selected while the user has Sleep status (or has Comatose ability).
- Randomly selects and executes one of the user's other moves (excluding moves with `nosleeptalk` flag, charge/two-turn moves, Z-moves, and Max moves).
- The called move is executed with all its normal properties.
- callsMove: true.
- Excluded from Encore, Assist, Copycat, Mimic, and Instruct; cannot call itself via Sleep Talk.

AI edge cases: The AI factors in whether the target has Sleep Talk when evaluating sleep-inducing moves (e.g., Yawn); if the target has Sleep Talk, the bonus for dream-based follow-ups (Dream Eater, Nightmare) is not applied.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Wring Out">
Type: Normal
Category: Special
Base Power: Variable (see formula)
Accuracy: 100
PP: 5
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- BP formula (same as Crush Grip): `floor(floor((120 × floor(targetHP × 4096 / targetMaxHP) + 2048 - 1) / 4096) / 100)`, minimum 1.
  - At 100% HP: BP ≈ 120.
  - At 50% HP: BP ≈ 60.
  - At 1 HP: BP = 1.
  - Higher BP when target has more remaining HP.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Shock Wave">
Type: Electric
Category: Special
Base Power: 60
Accuracy: — (never misses)
PP: 20
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- Never misses (accuracy: true). Still blocked by type immunity (Ground types) and abilities like Lightning Rod and Volt Absorb.
- No contact; no secondary effects.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Earth Power">
Type: Ground
Category: Special
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: protect, mirror, nonsky, metronome

Mechanics:
- 10% chance to lower the target's Special Defense by 1 stage.
- nonsky flag: cannot hit Pokémon in a semi-invulnerable aerial state (e.g., Sky Drop).
- No contact.
- Ground type: does not affect Flying-type Pokémon or those with the Levitate ability.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Mean Look">
Type: Normal
Category: Status
Base Power: —
Accuracy: — (never misses)
PP: 5
Priority: 0
Target: Single target
Flags: reflectable, mirror, metronome

Mechanics:
- Applies the 'trapped' volatile to the target, preventing it from switching out or fleeing.
- The trapped volatile is removed if the trapper (Mean Look user) switches out or faints.
- Ghost-type Pokémon ignore the trapping effect and can switch out freely.
- reflectable: bounced by Magic Coat or Magic Bounce.
- noCopy: trapped volatile is not passed by Baton Pass.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Blue Flare">
Type: Fire
Category: Special
Base Power: 130
Accuracy: 90 (R&B change; vanilla 85%)
PP: 5
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 20% chance to burn the target.
- No contact.

R&B Changes: Accuracy increased from 85% to 90%.
</Element>

<Element name="Hyperspace Hole">
Type: Psychic
Category: Special
Base Power: 80
Accuracy: — (never misses)
PP: 5
Priority: 0
Target: Single target
Flags: mirror, bypasssub

Mechanics:
- breaksProtect: true — bypasses Protect, Detect, Spiky Shield, Baneful Bunker, and similar protection moves.
- bypasssub: hits through Substitute.
- Never misses (accuracy: true).
- No contact; no protect flag (cannot be blocked by protect, consistent with breaksProtect).
- Companion to Hyperspace Fury (Hoopa-Unbound's Dark Physical equivalent).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Superpower">
Type: Fighting
Category: Physical
Base Power: 120
Accuracy: 100
PP: 5
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- After use, lowers the user's Attack and Defense each by 1 stage.
- Contact move.
- With Contrary ability: the self-drop becomes +1 Attack and +1 Defense instead.

AI edge cases (from AI.md):
- For Contrary users: Superpower is treated as a setup move (equivalent to Bulk Up) if it is not the highest-damage move available AND does not KO the target. Gets the same AI score as Bulk Up.
- Unlike normal Bulk Up, Contrary-Superpower used as a setup move has no penalties for using it against Unaware Pokémon or when threatened by OHKO/faster 2HKO.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Dizzy Punch">
Type: Normal
Category: Physical
Base Power: 70
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: contact, punch, protect, mirror, metronome

Mechanics:
- 20% chance to confuse the target.
- punch flag: boosted 1.2× by Iron Fist ability.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Thrash">
Type: Normal
Category: Physical
Base Power: 120
Accuracy: 100
PP: 10
Priority: 0
Target: randomNormal (random foe in doubles)
Flags: contact, protect, mirror, metronome, failinstruct

Mechanics:
- Applies lockedmove volatile: user is locked into Thrash for 2–3 turns. After the rampage ends, user becomes confused.
- target: randomNormal — in doubles, hits a random foe each turn during the rampage.
- Cannot be called by Instruct while locked in.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Coil">
Type: Poison
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Self
Flags: snatch, metronome

Mechanics:
- Raises the user's Attack, Defense, and Accuracy each by 1 stage.
- snatch flag: can be stolen by a Snatch user.

AI edge cases (from AI.md):
- General setup rules apply: AI won't use Coil if the player mon can KO the AI (-20) or has Unaware (-20).
- Treated as Defensive Setup if the player mon has at least one physical attack and no special attacking moves; otherwise treated as Offensive Setup.
- Defensive Setup scoring: base +6; -5 if AI is slower and 2HKO'd; ~95% of the time adds +2 if target is incapacitated.
- Offensive Setup scoring: base +6; +3 if target is incapacitated; -5 if AI is slower and 2HKO'd.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Circle Throw">
Type: Fighting
Category: Physical
Base Power: 60
Accuracy: 95 (R&B change; vanilla 90%)
PP: 10
Priority: -6
Target: Single target
Flags: contact, protect, mirror, metronome, noassist, failcopycat

Mechanics:
- forceSwitch: true — if it hits, forces the target to switch out, replaced by a random Pokémon from the opponent's party.
- Priority -6: executes very late in the turn order, typically after all other moves.
- Fails to force the switch if: the target is trapped (partially trapped, Mean Look, etc.), the opponent has no other Pokémon to switch in, or the target has Suction Cups ability.
- Contact move.
- Cannot be called by Assist or Copycat.

R&B Changes: Accuracy increased from 90% to 95%.
</Element>

<Element name="Bullet Seed">
Type: Grass
Category: Physical
Base Power: 25 per hit
Accuracy: 100
PP: 30
Priority: 0
Target: Single target
Flags: bullet, protect, mirror, metronome

Mechanics:
- multihit: [2, 5] — hits 2–5 times. Distribution: 2 or 3 hits at 3/8 each, 4 or 5 hits at 1/8 each. With Skill Link: always 5 hits.
- bullet flag: blocked entirely by Bulletproof ability.
- No contact; each hit can independently break Sturdy or a Focus Sash.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Snipe Shot">
Type: Water
Category: Special
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- critRatio: 2 — high critical hit ratio (+1 crit stage, ~12.5% crit chance).
- tracksTarget: true — ignores move redirection effects (Follow Me, Rage Powder, Storm Drain, Lightning Rod). Still targets the intended Pokémon even in doubles.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Flame Wheel">
Type: Fire
Category: Physical
Base Power: 60
Accuracy: 100
PP: 25
Priority: 0
Target: Single target
Flags: contact, defrost, protect, mirror, metronome

Mechanics:
- 10% chance to burn the target.
- defrost flag: if the user is frozen, it thaws before using this move.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Confusion">
Type: Psychic
Category: Special
Base Power: 50
Accuracy: 100
PP: 25
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 10% chance to confuse the target.
- No contact; no secondary damage.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Poison Tail">
Type: Poison
Category: Physical
Base Power: 50
Accuracy: 100
PP: 25
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- High critical hit ratio (critRatio: 2 = +1 crit stage, ~12.5% crit chance).
- 10% chance to poison the target.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Air Slash">
Type: Flying
Category: Special
Base Power: 75
Accuracy: 100 (R&B change; vanilla 95%)
PP: 15
Priority: 0
Target: Any (distance flag; can target any Pokémon on the field in doubles)
Flags: slicing, distance, protect, mirror, metronome

Mechanics:
- 30% chance to flinch the target.
- slicing flag: boosted 1.5× by Sharpness ability.
- No contact.

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Metal Sound">
Type: Steel
Category: Status
Base Power: —
Accuracy: 100 (R&B change; vanilla 85%)
PP: 5 (R&B change; vanilla 40)
Priority: 0
Target: Single target
Flags: sound, bypasssub, reflectable, protect, mirror, metronome

Mechanics:
- Lowers the target's Special Defense by 2 stages.
- sound flag: bypasses Substitute; blocked by Soundproof ability.
- reflectable: bounced by Magic Coat or Magic Bounce.
- No contact.

R&B Changes: Accuracy increased from 85% to 100%. PP reduced from 40 to 5.
</Element>

<Element name="Head Smash">
Type: Rock
Category: Physical
Base Power: 150
Accuracy: 85 (R&B change; vanilla 80%)
PP: 5
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- recoil: [1, 2] — user takes 1/2 of the damage dealt as recoil.
- Contact move.

R&B Changes: Accuracy increased from 80% to 85%.
</Element>

<Element name="Drill Run">
Type: Ground
Category: Physical
Base Power: 80
Accuracy: 100 (R&B change; vanilla 95%)
PP: 10
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- High critical hit ratio (critRatio: 2 = +1 crit stage, ~12.5% crit chance).
- Contact move.
- Ground type: does not affect Flying-type Pokémon or those with Levitate.

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Double Edge">
Type: Normal
Category: Physical
Base Power: 120
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- recoil: [33, 100] — user takes 1/3 of the damage dealt as recoil.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Jaw Lock">
Type: Dark
Category: Physical
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: contact, bite, protect, mirror, metronome

Mechanics:
- bite flag: boosted 1.5× by Strong Jaw ability.
- On hit: applies the 'trapped' volatile to BOTH the user and the target — neither can switch out until one of them faints.
- Ghost-type Pokémon ignore the trapped volatile and can switch out freely.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Synthesis">
Type: Grass
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: 0
Target: Self
Flags: snatch, heal, metronome

Mechanics:
- Heals the user based on weather:
  - Sun (Sunny Day, Desolate Land): 2/3 max HP.
  - No weather: 1/2 max HP.
  - Rain (Rain Dance, Primordial Sea), Sand, Hail, Snow: 1/4 max HP.
- snatch flag: can be stolen by a Snatch user.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Frost Breath">
Type: Ice
Category: Special
Base Power: 60
Accuracy: 100 (R&B change; vanilla 90%)
PP: 10
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- willCrit: true — always deals a critical hit.
- The guaranteed critical hit is blocked by Battle Armor and Shell Armor abilities.
- No contact; no secondary effects.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Dragon Hammer">
Type: Dragon
Category: Physical
Base Power: 90
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- Contact move; no secondary effects.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Thunderbolt">
Type: Electric
Category: Special
Base Power: 90
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 10% chance to paralyze the target.
- No contact.
- Called by Nature Power in Electric Terrain.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Spark">
Type: Electric
Category: Physical
Base Power: 65
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- 30% chance to paralyze the target.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Flare Blitz">
Type: Fire
Category: Physical
Base Power: 120
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: contact, defrost, protect, mirror, metronome

Mechanics:
- recoil: [33, 100] — user takes 1/3 of the damage dealt as recoil.
- 10% chance to burn the target.
- defrost flag: if the user is frozen, it thaws before using this move.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sweet Kiss">
Type: Fairy
Category: Status
Base Power: —
Accuracy: 80 (R&B change; vanilla 75%)
PP: 10
Priority: 0
Target: Single target
Flags: protect, reflectable, mirror, metronome

Mechanics:
- Inflicts the confusion volatile on the target.
- reflectable: bounced by Magic Coat or Magic Bounce.
- No contact.

R&B Changes: Accuracy increased from 75% to 80%.
</Element>

<Element name="Dragon Breath">
Type: Dragon
Category: Special
Base Power: 60
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 30% chance to paralyze the target.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Spirit Shackle">
Type: Ghost
Category: Physical
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 100% chance to apply the 'trapped' volatile to the target, preventing it from switching out (provided the user is still active on the field when the effect resolves).
- No contact despite being a physical move.
- Trapped volatile is removed if the trapper (Spirit Shackle user) leaves the field.
- Ghost-type Pokémon ignore the trapping effect and can switch freely.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Acid">
Type: Poison
Category: Special
Base Power: 40
Accuracy: 100
PP: 30
Priority: 0
Target: allAdjacentFoes (spread)
Flags: protect, mirror, metronome

Mechanics:
- 10% chance to lower each hit target's Special Defense by 1 stage.
- Spread move; in doubles, deals 0.75× damage to all foes.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Rock Smash">
Type: Fighting
Category: Physical
Base Power: 40
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- 100% chance to lower the target's Defense by 1 stage (R&B change; vanilla 50%).
- Contact move.

R&B Changes: Defense-lowering effect chance increased from 50% to 100% (guaranteed).
</Element>

<Element name="Last Resort">
Type: Normal
Category: Physical
Base Power: 140
Accuracy: 100
PP: 5
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- Fails unless: (1) the user knows at least 2 moves, AND (2) every other move in the user's moveset has been used at least once during the battle.
- The `used` flag on move slots tracks whether each move has been selected; all non-Last Resort moves must be marked used for Last Resort to succeed.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Facade">
Type: Normal
Category: Physical
Base Power: 70 (140 if user has a status condition)
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- BP doubles to 140 if the user has Burn, Paralysis, Poison, or Toxic status (not Sleep, not Freeze).
- When user is Burned: the normal Attack halving from burn is bypassed for Facade's damage calculation. Facade deals full damage as if the user were not burned (140 BP, no Attack penalty).
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Wish">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Self
Flags: snatch, heal, metronome

Mechanics:
- slotCondition: 'Wish' — placed on the user's slot. At the end of the following turn, the Pokémon occupying that slot is healed (may be a different Pokémon if the wisher switched out).
- Healing amount: 1/2 of the WISHER'S max HP (not the recipient's). Fixed at use time.
- If the slot is empty or the occupying Pokémon has fainted, no healing occurs.
- snatch flag: can be stolen by a Snatch user (who then places the Wish on their own slot).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Counter">
Type: Fighting
Category: Physical
Base Power: — (2× physical damage received)
Accuracy: 100
PP: 20
Priority: -5
Target: Scripted (the last foe that hit with a physical move this turn)
Flags: contact, protect, failmefirst, noassist, failcopycat

Mechanics:
- Deals 2× the physical damage the user received from a foe this turn.
- Fails if: the user was not hit by a physical move from a foe this turn, OR the attacker is no longer on the field.
- Minimum damage: 1 if Counter would deal 0 (counter volatile had 0 damage).
- Priority -5: resolves very late in the turn, after most other moves.
- Cannot be called by Me First, Assist, or Copycat.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Dive">
Type: Water
Category: Physical
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: contact, charge, nonsky, protect, mirror, metronome, nosleeptalk, noassist, failinstruct

Mechanics:
- Two-turn move. Turn 1: user submerges underwater (semi-invulnerable state). Turn 2: attacks.
- While submerged: immune to residual damage from Sandstorm and Hail. Only Surf and Whirlpool can hit the user during this state (both dealing 2× damage).
- charge flag: cannot be called by Sleep Talk, Assist, or Instruct.
- Contact move.
- Cramorant with Gulp Missile changes to a gorging/gulping form when using Dive (if applicable).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Whirlwind">
Type: Normal
Category: Status
Base Power: —
Accuracy: — (never misses)
PP: 20
Priority: -6
Target: Single target
Flags: reflectable, mirror, bypasssub, wind, metronome, noassist, failcopycat

Mechanics:
- forceSwitch: true — forces the target to switch to a random Pokémon from the opponent's party.
- Never misses (accuracy: true). Can still fail if: opponent has no other Pokémon, target has Suction Cups, or target is trapped.
- reflectable: bounced by Magic Coat or Magic Bounce (the user is then forced to switch instead).
- bypasssub: works through Substitute.
- Priority -6: resolves very late in the turn order.
- Cannot be called by Assist or Copycat.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Vice Grip">
Type: Normal
Category: Physical
Base Power: 55
Accuracy: 100
PP: 30
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- Contact move; no secondary effects.
- Known as "Vise Grip" in Showdown data.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fire Fang">
Type: Fire
Category: Physical
Base Power: 65
Accuracy: 100 (R&B change; vanilla 95%)
PP: 15
Priority: 0
Target: Single target
Flags: contact, bite, protect, mirror, metronome

Mechanics:
- Two independent secondary effects: 10% chance to burn AND 10% chance to flinch (each rolls separately; both can trigger on the same hit).
- bite flag: boosted 1.5× by Strong Jaw ability.
- Contact move.

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Poison Jab">
Type: Poison
Category: Physical
Base Power: 80
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- 30% chance to poison the target.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Throat Chop">
Type: Dark
Category: Physical
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- 100% chance to apply the throatchop volatile for 2 turns: while active, the target cannot use any move with the `sound` flag.
- Z-moves and Max Moves are not blocked by throatchop, even if the underlying move is a sound move.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Steel Wing">
Type: Steel
Category: Physical
Base Power: 70
Accuracy: 100 (R&B change; vanilla 90%)
PP: 25
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- 10% chance to raise the user's Defense by 1 stage.
- Contact move.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="No Retreat">
Type: Fighting
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: 0
Target: Self
Flags: snatch, metronome

Mechanics:
- Raises all of the user's stats (Attack, Defense, Sp. Atk, Sp. Def, Speed) by 1 stage each.
- Applies noretreat volatile: the user is trapped and cannot switch out.
- Fails if the user already has the noretreat volatile (can only be used once per battle encounter).
- If the user is already trapped when No Retreat is used, the trapping effect is skipped but the stat boosts still apply.
- snatch flag: can be stolen by a Snatch user.

AI edge cases (from AI.md):
- AI treats No Retreat identically to Bulk Up (ignoring the SpD boost).
- Treated as Defensive Setup if player has only physical attacking moves; otherwise Offensive Setup (same logic as Coil/Bulk Up).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Blizzard">
Type: Ice
Category: Special
Base Power: 110
Accuracy: 80 (R&B change; vanilla 70%); never misses in Hail or Snow
PP: 5
Priority: 0
Target: allAdjacentFoes (spread)
Flags: wind, protect, mirror, metronome

Mechanics:
- 10% chance to freeze each target hit.
- In Hail or Snowscape weather: accuracy becomes true (never misses).
- Spread move; in doubles, deals 0.75× damage to all foes.
- wind flag.
- No contact.

R&B Changes: Accuracy increased from 70% to 80%.
</Element>

<Element name="Hidden Power Ground">
Type: Ground (fixed; determined by user's IVs in practice)
Category: Special
Base Power: 60 (always 60)
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: protect, mirror

Mechanics:
- The Ground-typed variant of Hidden Power. All mechanics are identical to Hidden Power Ice: 60 BP always, type from IVs, no contact, no secondary effects.
- Ground type: does not affect Flying types or Pokémon with Levitate.

R&B Changes: None. Vanilla gen 8 mechanics apply (always 60 BP, type from IVs).
</Element>

<Element name="Stuff Cheeks">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Self
Flags: snatch, metronome

Mechanics:
- Fails (and is disabled in the move selection menu) if the user is not holding a Berry.
- Consumes the held Berry without triggering its normal eat effect, then raises the user's Defense by 2 stages.
- snatch flag: can be stolen by a Snatch user.

AI edge cases: Part of the General Setup group (same scoring as Swords Dance and similar setup moves).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Rock Slide">
Type: Rock
Category: Physical
Base Power: 75
Accuracy: 100 (R&B change; vanilla 90%)
PP: 10
Priority: 0
Target: allAdjacentFoes (spread)
Flags: protect, mirror, metronome

Mechanics:
- 30% chance to flinch each target hit.
- Spread move; in doubles, deals 0.75× damage to all foes.
- No contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Razor Shell">
Type: Water
Category: Physical
Base Power: 75
Accuracy: 100 (R&B change; vanilla 95%)
PP: 10
Priority: 0
Target: Single target
Flags: contact, slicing, protect, mirror, metronome

Mechanics:
- 50% chance to lower the target's Defense by 1 stage.
- slicing flag: boosted 1.5× by Sharpness ability.
- Contact move.

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Signal Beam">
Type: Bug
Category: Special
Base Power: 75
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 10% chance to confuse the target.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sludge">
Type: Poison
Category: Special
Base Power: 65
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 30% chance to poison the target.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Return">
Type: Normal
Category: Physical
Base Power: 102 (R&B fixed; vanilla: floor(happiness × 10 / 25), min 1, max 102)
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- Vanilla: BP = floor(happiness × 10 / 25), minimum 1, maximum 102 (at 255 happiness).
- Contact move.

R&B Changes: BP fixed at 102 (maximum, equivalent to full happiness). Happiness mechanic is ignored; Return always deals 102 BP in R&B.
</Element>

<Element name="U Turn">
Type: Bug
Category: Physical
Base Power: 70
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- selfSwitch: true — after dealing damage, the user switches out and the trainer sends in a replacement.
- The switch happens only if the move successfully deals damage; if the target is immune or the move misses, no switch occurs.
- Contact move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fly">
Type: Flying
Category: Physical
Base Power: 90
Accuracy: 100 (R&B change; vanilla 95%)
PP: 15
Priority: 0
Target: Any (distance flag; can target any Pokémon in doubles)
Flags: contact, charge, gravity, distance, protect, mirror, metronome, nosleeptalk, noassist, failinstruct

Mechanics:
- Two-turn move. Turn 1: user flies into the air (semi-invulnerable state). Turn 2: attacks.
- During fly state: only Gust, Twister, Sky Uppercut, Thunder, Hurricane, Smack Down, and Thousand Arrows can hit. Gust and Twister deal 2× damage during this state.
- gravity flag: Gravity prevents using Fly; also grounds the user immediately if in-flight.
- charge flag: cannot be called by Sleep Talk, Assist, or Instruct.
- Contact move.

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Draco Meteor">
Type: Dragon
Category: Special
Base Power: 130
Accuracy: 100 (R&B change; vanilla 90%)
PP: 5
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- After use, lowers the user's Sp. Atk by 2 stages.
- With Contrary ability: the self-drop becomes +2 Sp. Atk instead.
- No contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Skitter Smack">
Type: Bug
Category: Physical
Base Power: 70
Accuracy: 100 (R&B change; vanilla 90%)
PP: 10
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- 100% chance to lower the target's Sp. Atk by 1 stage.
- Contact move.

AI edge cases (from AI.md, shared with Trop Kick):
- If Skitter Smack is the highest-damage move: scored as a regular damaging move (+6 at 80% or +8 at 20%); stat-drop bonus not applied.
- Otherwise, if target is not Contrary/Clear Body/White Smoke AND target has at least one special attacking move: +6.
- Otherwise: +5.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Mega Drain">
Type: Grass
Category: Special
Base Power: 60 (R&B change; vanilla 40)
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: heal, protect, mirror, metronome

Mechanics:
- drain: [1, 2] — heals the user for 1/2 of the damage dealt. Boosted to 3/4 with Big Root item.
- No contact.

R&B Changes: Base power increased from 40 to 60.
</Element>

<Element name="Recover">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: 0
Target: Self
Flags: snatch, heal, metronome

Mechanics:
- Heals the user for 50% of its max HP.
- Snatched by Snatch.

AI Edge Cases (AI.md):
- Recovery Moves group (Recover, Slack Off, Heal Order, Soft-Boiled, Roost, Strength Sap): +7 if AI decides it should recover, +5 otherwise.
- Will not use if at full HP (−20) or at 85%+ HP (−6).
- "Should AI Recover" function for 50% recovery moves: returns False if Toxic'd or if player deals as much or more than would be healed. If AI is faster: True if player can kill but can't after healing, or probabilistic True/False below 66%/40%. If AI is slower: True (75%) below 70%, always True below 50%.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Breaking Swipe">
Type: Dragon
Category: Physical
Base Power: 60
Accuracy: 100
PP: 15
Priority: 0
Target: All adjacent foes (spread)
Flags: contact, protect, mirror

Mechanics:
- Hits all adjacent foes. In doubles, damage is multiplied by 0.75×.
- 100% chance to lower Attack by 1 on each target hit.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Hydro Pump">
Type: Water
Category: Special
Base Power: 110
Accuracy: 85 (R&B change; vanilla 80%)
PP: 5
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- Standard high-power Water-type special attack. No secondary effect.

R&B Changes: Accuracy increased from 80% to 85%.
</Element>

<Element name="Shadow Bone">
Type: Ghost
Category: Physical
Base Power: 85
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 20% chance to lower the target's Defense by 1.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Pyro Ball">
Type: Fire
Category: Physical
Base Power: 120
Accuracy: 90
PP: 5
Priority: 0
Target: Single target
Flags: protect, mirror, defrost, bullet

Mechanics:
- 10% chance to burn the target.
- defrost: thaws a frozen target on hit.
- bullet: blocked by Bulletproof ability.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fairy Wind">
Type: Fairy
Category: Special
Base Power: 40
Accuracy: 100
PP: 30
Priority: 0
Target: Single target
Flags: protect, mirror, metronome, wind

Mechanics:
- No secondary effect.
- wind flag: triggers Wind Rider ability on ally Pokémon.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Stomping Tantrum">
Type: Ground
Category: Physical
Base Power: 75 (150 if user's last move failed)
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- Base power doubles to 150 if the user's move on the previous turn failed (missed, blocked by protection, or otherwise prevented from executing).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Pluck">
Type: Flying
Category: Physical
Base Power: 60
Accuracy: 100
PP: 20
Priority: 0
Target: Any (including non-adjacent in doubles)
Flags: contact, protect, mirror, distance, metronome

Mechanics:
- If the target is holding a Berry, the user steals and consumes it, gaining the Berry's effect as if the user ate it.
- Makes contact.
- distance flag: can target any Pokémon on the field in doubles.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Headbutt">
Type: Normal
Category: Physical
Base Power: 70
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- 30% chance to cause the target to flinch.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Brick Break">
Type: Fighting
Category: Physical
Base Power: 75
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- Before hitting, removes Reflect, Light Screen, and Aurora Veil from the target's side. This screen removal occurs even if the target is behind a Substitute.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Ice Shard">
Type: Ice
Category: Physical
Base Power: 40
Accuracy: 100
PP: 30
Priority: +1
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- Priority +1; moves before normal-priority moves.
- No secondary effect.
- No contact.

AI Edge Cases (AI.md):
- In doubles: if the ally partner has Weakness Policy and Ice Shard is super effective on the partner, score is +12 total (intentional chip for WP activation).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Infestation">
Type: Bug
Category: Special
Base Power: 20
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- Inflicts the partiallytrapped volatile on the target: traps it for 4-5 turns and deals 1/8 of its max HP each turn at end of turn. Target cannot switch out while trapped (Ghost types are immune to the trapping).
- Makes contact.

AI Edge Cases (AI.md):
- Damaging Trapping moves group (Fire Spin, Whirlpool, Sand Tomb, Magma Storm, Infestation, etc.): +6 (~80% of the time), +8 (~20% of the time).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Hammer Arm">
Type: Fighting
Category: Physical
Base Power: 100
Accuracy: 100 (R&B change; vanilla 90%)
PP: 10
Priority: 0
Target: Single target
Flags: contact, protect, mirror, punch, metronome

Mechanics:
- Lowers the user's Speed by 1 after use.
- punch flag: boosted by Iron Fist ability.
- Makes contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Clanging Scales">
Type: Dragon
Category: Special
Base Power: 110
Accuracy: 100
PP: 5
Priority: 0
Target: All adjacent foes (spread)
Flags: protect, mirror, sound, bypasssub, metronome

Mechanics:
- Hits all adjacent foes. In doubles, damage is multiplied by 0.75×.
- Lowers the user's Defense by 1 after use.
- sound flag: blocked by Soundproof; passes through Substitute.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Peck">
Type: Flying
Category: Physical
Base Power: 35
Accuracy: 100
PP: 35
Priority: 0
Target: Any (including non-adjacent in doubles)
Flags: contact, protect, mirror, distance, metronome

Mechanics:
- No secondary effect.
- Makes contact.
- distance flag: can target any Pokémon on the field in doubles.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Aura Sphere">
Type: Fighting
Category: Special
Base Power: 80
Accuracy: — (never misses)
PP: 20
Priority: 0
Target: Any (including non-adjacent in doubles)
Flags: protect, mirror, distance, metronome, bullet, pulse

Mechanics:
- Never misses (accuracy: true).
- bullet flag: blocked by Bulletproof ability.
- pulse flag: boosted 1.5× by Mega Launcher ability.
- No contact.
- distance flag: can target any Pokémon on the field in doubles.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Gunk Shot">
Type: Poison
Category: Physical
Base Power: 120
Accuracy: 85 (R&B change; vanilla 80%)
PP: 5
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 30% chance to poison the target.
- No contact.

R&B Changes: Accuracy increased from 80% to 85%.
</Element>

<Element name="Fire Blast">
Type: Fire
Category: Special
Base Power: 110
Accuracy: 85
PP: 5
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 10% chance to burn the target.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Aurora Beam">
Type: Ice
Category: Special
Base Power: 65
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 10% chance to lower the target's Attack by 1.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Assurance">
Type: Dark
Category: Physical
Base Power: 60 (120 if target already took damage this turn)
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- Base power doubles to 120 if the target has already taken damage this turn (from any source).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Accelerock">
Type: Rock
Category: Physical
Base Power: 40
Accuracy: 100
PP: 20
Priority: +1
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- Priority +1; moves before normal-priority moves.
- No secondary effect.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Roar">
Type: Normal
Category: Status
Base Power: —
Accuracy: — (never misses)
PP: 20
Priority: -6
Target: Single target
Flags: reflectable, mirror, sound, bypasssub, metronome, noassist, failcopycat

Mechanics:
- forceSwitch: true — forces the target to switch out to a random party member. Fails if target has no valid switch-ins.
- Priority −6; used last among negative-priority moves.
- sound flag: bypasses Substitute.
- bypasssub: bypasses Substitute.
- reflectable: reversed by Magic Coat or Magic Bounce — forces the Roar user to switch out instead.
- Cannot be called by Assist (noassist) or copied by Copycat (failcopycat).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Iron Defense">
Type: Steel
Category: Status
Base Power: —
Accuracy: —
PP: 15
Priority: 0
Target: Self
Flags: snatch, metronome

Mechanics:
- Raises the user's Defense by 2 stages.
- Snatched by Snatch.

AI Edge Cases (AI.md):
- General Setup rules apply first: AI will not set up if player can KO it (−20); AI will not set up if player has Unaware (−20).
- Defensive Setup group scoring: base +6; −5 if AI is slower and player 2HKOs it; ~95% of the time, additional +2 if player is incapacitated.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Leech Life">
Type: Bug
Category: Physical
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: contact, protect, mirror, heal, metronome

Mechanics:
- drain: [1, 2] — heals the user for 1/2 of the damage dealt. Boosted to 3/4 with Big Root item.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Howl">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 40
Priority: 0
Target: Allies (user + ally in doubles)
Flags: snatch, sound, metronome

Mechanics:
- Raises the user's Attack by 1 (and ally's Attack by 1 in doubles).
- sound flag: blocked by Soundproof on the user (or ally in doubles).
- Snatched by Snatch.

AI Edge Cases (AI.md):
- General Setup rules apply first: AI will not use if player can KO it (−20). Exception: Unaware does NOT suppress Howl (unlike most General Setup moves).
- Offensive Setup scoring: base +6; +3 if player is incapacitated; −5 if AI is slower and player 2HKOs it.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Ice Beam">
Type: Ice
Category: Special
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 10% chance to freeze the target.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Hyper Fang">
Type: Normal
Category: Physical
Base Power: 80
Accuracy: 100 (R&B change; vanilla 90%)
PP: 15
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome, bite

Mechanics:
- 10% chance to cause the target to flinch.
- bite flag: boosted by Strong Jaw ability.
- Makes contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Tri Attack">
Type: Normal
Category: Special
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 20% chance to inflict one of burn, paralysis, or freeze, chosen randomly with equal probability.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Dragon Claw">
Type: Dragon
Category: Physical
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- No secondary effect.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Shadow Ball">
Type: Ghost
Category: Special
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: protect, mirror, metronome, bullet

Mechanics:
- 20% chance to lower the target's Special Defense by 1.
- bullet flag: blocked by Bulletproof ability.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Water Shuriken">
Type: Water
Category: Special
Base Power: 15 per hit (20 per hit for Ash-Greninja with Battle Bond)
Accuracy: 100
PP: 20
Priority: +1
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- multihit [2, 5]: hits 2–5 times. Distribution: 3/8 chance for 2 hits, 3/8 for 3 hits, 1/8 for 4 hits, 1/8 for 5 hits. Skill Link ability forces 5 hits.
- Priority +1; moves before normal-priority moves.
- Ash-Greninja (Battle Bond, not transformed): base power per hit is 20 instead of 15.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Flip Turn">
Type: Water
Category: Physical
Base Power: 60
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- selfSwitch: true — after dealing damage, the user switches out to a party member chosen by the player. If no valid switch-in is available, the user stays in.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Flash Cannon">
Type: Steel
Category: Special
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 10% chance to lower the target's Special Defense by 1.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Shadow Punch">
Type: Ghost
Category: Physical
Base Power: 60
Accuracy: — (never misses)
PP: 20
Priority: 0
Target: Single target
Flags: contact, protect, mirror, punch, metronome

Mechanics:
- Never misses (accuracy: true).
- punch flag: boosted by Iron Fist ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Mega Kick">
Type: Normal
Category: Physical
Base Power: 120
Accuracy: 85 (R&B change; vanilla 75%)
PP: 5
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- No secondary effect.
- Makes contact.

R&B Changes: Accuracy increased from 75% to 85%.
</Element>

<Element name="Mat Block">
Type: Fighting
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Ally side
Flags: snatch, nonsky, noassist, failcopycat

Mechanics:
- Usable only on the user's first turn on the field. Fails if the user has already acted this switch-in.
- Sets a side condition for 1 turn that blocks all damaging moves targeting either Pokémon on the user's side (similar to Wide Guard but limited to first turn out).
- Does not block status moves or self-targeting moves.
- stallingMove: true.
- Cannot be called by Assist (noassist) or copied by Copycat (failcopycat).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Stealth Rock">
Type: Rock
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Foe's side
Flags: reflectable, metronome, mustpressure

Mechanics:
- Sets Stealth Rock on the opponent's side. On switch-in, deals Rock-type effectiveness-scaled damage: 1/8 max HP at neutral, doubled or halved per type weakness/resistance step. Bypassed by Heavy-Duty Boots.
- reflectable: Magic Coat or Magic Bounce redirects it to the user's own side.
- mustpressure: consumes 2 PP when the target has Pressure.
- Fails if Stealth Rock is already set on the target's side.

AI Edge Cases (AI.md):
- On first turn out: +8 (25%), +9 (75%).
- Otherwise: +6 (25%), +7 (75%).
- Won't use if Stealth Rock is already set (treated as a "bad move").

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Dig">
Type: Ground
Category: Physical
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: contact, charge, protect, mirror, nonsky, metronome, nosleeptalk, noassist, failinstruct

Mechanics:
- Two-turn move. Turn 1: user burrows underground (invulnerable to most moves). Turn 2: strikes the target.
- While underground: Earthquake and Magnitude can still hit and deal double damage; all other moves miss.
- charge flag: cannot be called by Sleep Talk, Assist, or Instruct.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Trop Kick">
Type: Grass
Category: Physical
Base Power: 70
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- 100% chance to lower the target's Attack by 1.
- Makes contact.

AI Edge Cases (AI.md):
- Damaging Attack-reduction moves with guaranteed effect group (Trop Kick, Skitter Smack, etc.): if this is the highest-damage move, standard highest-damage scoring applies with no extra bonuses. Otherwise: +6 if target is not Contrary/Clear Body/White Smoke and has a physical attacking move; +5 otherwise.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Aurora Veil">
Type: Ice
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Ally side
Flags: snatch, metronome

Mechanics:
- Fails unless Hail or Snowscape is active.
- Sets Aurora Veil on the user's side for 5 turns (8 turns with Light Clay).
- While active: reduces damage from all moves (both physical and special) to the user's side by 50% in singles, or by ~33% in doubles. Does not apply if the corresponding Reflect or Light Screen is also active for that damage category, on a crit, or from moves with the Infiltrator flag.
- Snatched by Snatch.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Iron Head">
Type: Steel
Category: Physical
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- 30% chance to cause the target to flinch.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Wrap">
Type: Normal
Category: Physical
Base Power: 15
Accuracy: 100 (R&B change; vanilla 90%)
PP: 20
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- Inflicts the partiallytrapped volatile on the target: traps it for 4-5 turns and deals 1/8 of its max HP each turn at end of turn. Target cannot switch out while trapped (Ghost types are immune to the trapping).
- Makes contact.

AI Edge Cases (AI.md):
- Damaging Trapping moves group: +6 (~80% of the time), +8 (~20% of the time).

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Energy Ball">
Type: Grass
Category: Special
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: protect, mirror, metronome, bullet

Mechanics:
- 10% chance to lower the target's Special Defense by 1.
- bullet flag: blocked by Bulletproof ability.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Nightmare">
Type: Ghost
Category: Status
Base Power: —
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- Fails unless the target is asleep (or has Comatose).
- Inflicts the nightmare volatile: deals 1/4 of the target's max HP at end of each turn while the target remains asleep.
- noCopy: not transferred by Baton Pass.

AI Edge Cases (AI.md):
- Having Nightmare in the moveset gives the AI an extra +1 when scoring sleep-inflicting moves (if the player can be put to sleep and does not have Snore or Sleep Talk).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Magma Storm">
Type: Fire
Category: Special
Base Power: 100
Accuracy: 90 (R&B change; vanilla 75%)
PP: 5
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- Inflicts the partiallytrapped volatile on the target: traps it for 4-5 turns and deals 1/8 of its max HP each turn at end of turn. Target cannot switch out while trapped (Ghost types are immune to the trapping).
- No contact.

AI Edge Cases (AI.md):
- Damaging Trapping moves group: +6 (~80% of the time), +8 (~20% of the time).

R&B Changes: Accuracy increased from 75% to 90%.
</Element>

<Element name="Dazzling Gleam">
Type: Fairy
Category: Special
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: All adjacent foes (spread)
Flags: protect, mirror, metronome

Mechanics:
- Hits all adjacent foes. In doubles, damage is multiplied by 0.75×.
- No secondary effect.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Autotomize">
Type: Steel
Category: Status
Base Power: —
Accuracy: —
PP: 15
Priority: 0
Target: Self
Flags: snatch, metronome

Mechanics:
- Raises the user's Speed by 2 stages.
- Also reduces the user's weight by 100 kg (minimum 0.1 kg), which affects weight-based damage calculations.
- Fails if user is already at +6 Speed.
- Snatched by Snatch.

AI Edge Cases (AI.md):
- Agility/Rock Polish/Autotomize group: +7 if AI is slower than the player; never used (−20) if AI is already faster.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Weather Ball">
Type: Normal (changes based on weather — see below)
Category: Special
Base Power: 50 (100 in any weather)
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: protect, mirror, metronome, bullet

Mechanics:
- In Sun or Harsh Sun: type becomes Fire, BP doubles to 100.
- In Rain or Heavy Rain: type becomes Water, BP doubles to 100.
- In Sandstorm: type becomes Rock, BP doubles to 100.
- In Hail or Snowscape: type becomes Ice, BP doubles to 100.
- In no weather: Normal type, BP 50.
- bullet flag: blocked by Bulletproof ability.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Oblivion Wing">
Type: Flying
Category: Special
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Any (including non-adjacent in doubles)
Flags: protect, mirror, distance, heal, metronome

Mechanics:
- drain: [3, 4] — heals the user for 3/4 of the damage dealt (unique; standard drain moves heal 1/2). Boosted further by Big Root.
- distance flag: can target any Pokémon on the field in doubles.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Expanding Force">
Type: Psychic
Category: Special
Base Power: 80 (120 in Psychic Terrain if user is grounded)
Accuracy: 100
PP: 10
Priority: 0
Target: Single target normally; all adjacent foes (spread) in Psychic Terrain when user is grounded
Flags: protect, mirror, metronome

Mechanics:
- In Psychic Terrain with grounded user: base power becomes 120 (×1.5) and target changes to all adjacent foes. In doubles, the spread modifier (0.75×) applies on top.
- Outside Psychic Terrain: 80 BP, single target.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Plasma Fists">
Type: Electric
Category: Physical
Base Power: 100
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: contact, protect, mirror, punch

Mechanics:
- Sets the Ion Deluge pseudo-weather for the rest of the turn: all Normal-type moves used by any Pokémon become Electric-type.
- punch flag: boosted by Iron Fist ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Mirror Coat">
Type: Psychic
Category: Special
Base Power: — (damage-based)
Accuracy: 100
PP: 20
Priority: -5
Target: Scripted (the last foe that dealt special damage to the user this turn)
Flags: protect, failmefirst, noassist

Mechanics:
- Deals 2× the special damage the user received from a foe during the current turn. Fails if the user took no special damage this turn.
- Priority −5; executes very late in the turn order.
- Cannot be called by Assist (noassist).

AI Edge Cases (AI.md):
- Counter/Mirror Coat group: base +6; −20 if player can KO AI; +2 if player has Sturdy/Sash at full HP and only special moves; +2 (~80%) if player cannot KO AI and only has special moves; −1 (25%) if AI is faster; −1 (25%) if player has status moves.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Hone Claws">
Type: Dark
Category: Status
Base Power: —
Accuracy: —
PP: 15
Priority: 0
Target: Self
Flags: snatch, metronome

Mechanics:
- Raises the user's Attack by 1 and Accuracy by 1.
- Snatched by Snatch.

AI Edge Cases (AI.md):
- General Setup rules apply first: AI will not use if player can KO it (−20); AI will not use if player has Unaware (−20).
- Offensive Setup group (same as Dragon Dance, Shift Gear, Swords Dance): base +6; +3 if player is incapacitated; −5 if AI is slower and player 2HKOs it.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Hurricane">
Type: Flying
Category: Special
Base Power: 110
Accuracy: 80 (R&B change; vanilla 70%)
PP: 10
Priority: 0
Target: Any (including non-adjacent in doubles)
Flags: protect, mirror, distance, metronome, wind

Mechanics:
- 30% chance to confuse the target.
- Accuracy is affected by weather: never misses in Rain or Primordial Sea; accuracy becomes 50% in Sun or Desolate Land.
- distance flag: can target any Pokémon on the field in doubles.
- wind flag: triggers Wind Rider ability on ally Pokémon.
- No contact.

R&B Changes: Accuracy increased from 70% to 80%.
</Element>

<Element name="Memento">
Type: Dark
Category: Status
Base Power: —
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- Lowers the target's Attack and Special Attack by 2 stages each.
- selfdestruct: "ifHit" — the user faints upon hitting (but not if the move misses or is blocked).
- Fails if target's Attack and Special Attack are both already at −6.

AI Edge Cases (AI.md):
- Won't use if AI is on its last Pokémon.
- Below 10% HP: +16; below 33% HP: +14 (~70%) or +6 (~30%); below 66% HP: +13 (50%) or +6 (50%); otherwise: +13 (~5%) or +6 (~95%).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Giga Impact">
Type: Normal
Category: Physical
Base Power: 150
Accuracy: 100 (R&B change; vanilla 90%)
PP: 5
Priority: 0
Target: Single target
Flags: contact, recharge, protect, mirror, metronome

Mechanics:
- After using this move, the user must recharge on the following turn and cannot act.
- Makes contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Guillotine">
Type: Normal
Category: Physical
Base Power: — (one-hit KO)
Accuracy: 30
PP: 5
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- ohko: true — if it hits, the target is instantly KO'd regardless of HP.
- Fails if the target's level is higher than the user's level.
- Accuracy = 30 + (user's level − target's level) when user's level ≥ target's level. Immune to accuracy/evasion modifiers.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Revelation Dance">
Type: Matches user's primary type (Normal if typeless)
Category: Special
Base Power: 90
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: protect, mirror, dance, metronome

Mechanics:
- Type becomes the user's first type at time of use. If the first type is Bird/???, uses the second type instead.
- dance flag: triggers Dancer ability (ally with Dancer copies the move immediately after).
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Extrasensory">
Type: Psychic
Category: Special
Base Power: 80
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 10% chance to cause the target to flinch.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Psybeam">
Type: Psychic
Category: Special
Base Power: 65
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 10% chance to confuse the target.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Electroweb">
Type: Electric
Category: Special
Base Power: 55
Accuracy: 100 (R&B change; vanilla 95%)
PP: 15
Priority: 0
Target: All adjacent foes (spread)
Flags: protect, mirror, metronome

Mechanics:
- 100% chance to lower the Speed of each target hit by 1.
- Hits all adjacent foes. In doubles, damage is multiplied by 0.75×.
- No contact.

AI Edge Cases (AI.md):
- Damaging speed-reduction moves group (Icy Wind, Electroweb, Rock Tomb, Mud Shot, Low Sweep): if this is the highest-damage move, standard highest-damage scoring only. Otherwise: +6 if AI is slower and target is not Contrary/Clear Body/White Smoke; +5 otherwise. In doubles, additional +1 for Electroweb (spread move).

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Water Pulse">
Type: Water
Category: Special
Base Power: 60
Accuracy: 100
PP: 20
Priority: 0
Target: Any (including non-adjacent in doubles)
Flags: protect, mirror, distance, metronome, pulse

Mechanics:
- 20% chance to confuse the target.
- pulse flag: boosted 1.5× by Mega Launcher ability.
- distance flag: can target any Pokémon on the field in doubles.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Metal Claw">
Type: Steel
Category: Physical
Base Power: 50
Accuracy: 100 (R&B change; vanilla 95%)
PP: 35
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- 10% chance to raise the user's own Attack by 1.
- Makes contact.

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Icy Wind">
Type: Ice
Category: Special
Base Power: 55
Accuracy: 100 (R&B change; vanilla 95%)
PP: 15
Priority: 0
Target: All adjacent foes (spread)
Flags: protect, mirror, metronome, wind

Mechanics:
- 100% chance to lower the Speed of each target hit by 1.
- Hits all adjacent foes. In doubles, damage is multiplied by 0.75×.
- wind flag: triggers Wind Rider ability on ally Pokémon.
- No contact.

AI Edge Cases (AI.md):
- Damaging speed-reduction moves group (Icy Wind, Electroweb, Rock Tomb, Mud Shot, Low Sweep): if this is the highest-damage move, standard highest-damage scoring only. Otherwise: +6 if AI is slower and target is not Contrary/Clear Body/White Smoke; +5 otherwise. In doubles, additional +1 for Icy Wind (spread move).

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Bulldoze">
Type: Ground
Category: Physical
Base Power: 60
Accuracy: 100
PP: 20
Priority: 0
Target: All adjacent (foes and ally in doubles)
Flags: protect, mirror, nonsky, metronome

Mechanics:
- 100% chance to lower the Speed of each target hit by 1.
- Hits all adjacent Pokémon including the user's ally in doubles. Standard Ground-type immunities (Flying types, Levitate, Air Balloon) apply.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Strength Sap">
Type: Grass
Category: Status
Base Power: —
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: protect, reflectable, mirror, heal, metronome

Mechanics:
- Lowers the target's Attack by 1 and heals the user for an amount equal to the target's Attack stat (after boosts, before the drop is applied).
- Fails if the target's Attack is already at −6.
- reflectable: reversed by Magic Coat or Magic Bounce.

AI Edge Cases (AI.md):
- Recovery Moves group (Recover, Slack Off, Heal Order, Soft-Boiled, Roost, Strength Sap): +7 if AI decides it should recover, +5 otherwise.
- Will not use if at full HP (−20) or at 85%+ HP (−6).
- "Should AI Recover" function treats Strength Sap as 50% recovery for scoring purposes.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Cross Poison">
Type: Poison
Category: Physical
Base Power: 70
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome, slicing

Mechanics:
- 10% chance to poison the target.
- critRatio: 2 — increased critical hit ratio (1/8 chance instead of 1/24).
- slicing flag: boosted 1.5× by Sharpness ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Wild Charge">
Type: Electric
Category: Physical
Base Power: 90
Accuracy: 100
PP: 15
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- recoil [1, 4]: user takes 1/4 of the damage dealt as recoil.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Freeze-Dry">
Type: Ice
Category: Special
Base Power: 70
Accuracy: 100
PP: 20
Priority: 0
Target: Single target
Flags: protect, mirror, metronome

Mechanics:
- 10% chance to freeze the target.
- onEffectiveness override: Water-type targets take super effective (2×) damage from this move, regardless of normal Ice-vs-Water neutrality.
- No contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Encore">
Type: Normal
Category: Status
Base Power: —
Accuracy: 100
PP: 5
Priority: 0
Target: Single target
Flags: protect, reflectable, mirror, bypasssub, metronome, failencore

Mechanics:
- Inflicts the encore volatile for 3 turns: forces the target to repeat its last used move. Ends early if the encored move runs out of PP.
- Fails if the target hasn't used a move yet, used a Z-move or Max Move, or the last move has the failencore flag.
- bypasssub: bypasses Substitute.
- reflectable: reversed by Magic Coat or Magic Bounce.

AI Edge Cases (AI.md):
- Won't use if target is already Encored or if it is the target's first turn on the field.
- If AI is faster and Encore targets a non-damaging move: +7. If AI is slower: +6 (50%) or +5 (50%).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Extreme Speed">
Type: Normal
Category: Physical
Base Power: 80
Accuracy: 100
PP: 5
Priority: +2
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- Priority +2; moves before Quick Attack (+1) and all normal-priority moves. Overrides most other priority moves.
- No secondary effect.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Bounce">
Type: Flying
Category: Physical
Base Power: 85
Accuracy: 95 (R&B change; vanilla 85%)
PP: 5
Priority: 0
Target: Any (including non-adjacent in doubles)
Flags: contact, charge, protect, mirror, gravity, distance, metronome, nosleeptalk, noassist, failinstruct

Mechanics:
- Two-turn move. Turn 1: user bounces into the air (invulnerable to most moves). Turn 2: strikes the target.
- While airborne: Gust, Twister, Thunder, Hurricane, Sky Uppercut, Smack Down, and Thousand Arrows can still hit; Gust and Twister deal double damage.
- 30% chance to paralyze the target on hit.
- gravity flag: fails if Gravity is active.
- charge flag: cannot be called by Sleep Talk, Assist, or Instruct.
- Makes contact.
- distance flag: can target any Pokémon on the field in doubles.

R&B Changes: Accuracy increased from 85% to 95%.
</Element>

<Element name="Sticky Web">
Type: Bug
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Foe's side
Flags: reflectable, metronome

Mechanics:
- Sets Sticky Web on the opponent's side. When a grounded Pokémon switches in, its Speed is lowered by 1. Bypassed by Heavy-Duty Boots.
- reflectable: reversed by Magic Coat or Magic Bounce, setting Sticky Web on the user's own side.
- Fails if Sticky Web is already set on the target's side.

AI Edge Cases (AI.md):
- On first turn out: +9 (25%), +12 (75%).
- Otherwise: +6 (25%), +9 (75%).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Bolt Beak">
Type: Electric
Category: Physical
Base Power: 85 (170 if the user moves before the target)
Accuracy: 100
PP: 10
Priority: 0
Target: Single target
Flags: contact, protect, mirror, metronome

Mechanics:
- Base power doubles to 170 if the target has not yet moved this turn, or if the target just switched in this turn.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Psych Up">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Single target
Flags: bypasssub, allyanim, metronome

Mechanics:
- Copies all of the target's current stat stages to the user (replacing the user's existing stages). Also copies crit-stage volatiles (Focus Energy, Dragon Cheer, etc.).
- bypasssub: bypasses Substitute to read the target's boosts.
- Not affected by accuracy or evasion.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Rage Powder">
Type: Bug
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: +2
Target: Self
Flags: noassist, failcopycat, powder

Mechanics:
- Doubles only; fails in singles.
- For the rest of the turn, all single-target moves from foes that would target the ally are redirected to the Rage Powder user instead.
- Redirection does not apply to: Pokémon immune to powder moves (Grass-types, Overcoat ability, Safety Goggles item), moves that cannot be redirected (spread moves, etc.).
- Priority +2 to ensure it is set up before most moves resolve.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fake Tears">
Type: Dark
Category: Status
Base Power: —
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: reflectable

Mechanics:
- Lowers the target's Special Defense by 2 stages.
- Reflectable: reversed by Magic Coat or Magic Bounce (hits the user instead).

R&B Changes: PP reduced from 20 to 5.
</Element>

<Element name="Bite">
Type: Dark
Category: Physical
Base Power: 60
Accuracy: 100
PP: 25
Priority: 0
Target: Normal
Flags: contact, bite

Mechanics:
- 30% chance to cause the target to flinch.
- Bite flag: boosted by Strong Jaw ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Poison Sting">
Type: Poison
Category: Physical
Base Power: 15
Accuracy: 100
PP: 35
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- 30% chance to poison the target.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sandstorm">
Type: Rock
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: All (field)
Flags: wind

Mechanics:
- Sets the Sandstorm weather condition for 5 turns (8 turns if user holds Smooth Rock).
- In Sandstorm: Rock, Ground, and Steel types are immune to chip damage; all other types lose 1/16 max HP at end of each turn.
- Sandstorm boosts the Special Defense of Rock-type Pokémon by 50%.
- Fails if Sandstorm is already active.
- Wind flag: triggers Wind Rider ability on allies.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Rollout">
Type: Rock
Category: Physical
Base Power: 30 (doubles each consecutive hit)
Accuracy: 90
PP: 20
Priority: 0
Target: Normal
Flags: contact, failinstruct, noparentalbond

Mechanics:
- Locks the user into Rollout for up to 5 consecutive turns.
- Base Power doubles each hit: 30 → 60 → 120 → 240 → 480 (hits 1–5).
- If the user previously used Defense Curl, the BP is doubled at each step.
- If the user is put to sleep mid-sequence, Rollout is paused; it resumes from the current hit count when they wake up.
- Parental Bond does not apply (noparentalbond flag).
- Cannot be called by Instruct (failinstruct flag).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Icicle Crash">
Type: Ice
Category: Physical
Base Power: 85
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- 30% chance to cause the target to flinch.
- No contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Switcheroo">
Type: Dark
Category: Status
Base Power: —
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: noassist, failcopycat

Mechanics:
- Swaps the held items of the user and target.
- Fails if: both Pokémon have no item, or neither item can be transferred (the move returns false in those cases).
- Fails if the target has Sticky Hold ability.
- Items that cannot be removed from their holder (e.g., Mega Stones) block the swap.

AI Scoring:
- +6 (50%) or +7 (50%) if AI holds a Toxic Orb, Flame Orb, or Black Sludge.
- +7 if AI holds an Iron Ball, Lagging Tail, or Sticky Barb.
- +5 otherwise.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Astonish">
Type: Ghost
Category: Physical
Base Power: 40
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- 30% chance to cause the target to flinch.
- Makes contact.

R&B Changes: Base Power increased from 30 to 40.
</Element>

<Element name="Focus Blast">
Type: Fighting
Category: Special
Base Power: 120
Accuracy: 80
PP: 5
Priority: 0
Target: Normal
Flags: bullet

Mechanics:
- 10% chance to lower the target's Special Defense by 1 stage.
- Bullet flag: blocked by Bulletproof ability.

R&B Changes: Accuracy increased from 70% to 80%.
</Element>

<Element name="Thunderous Kick">
Type: Fighting
Category: Physical
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Always lowers the target's Defense by 1 stage after dealing damage (100% secondary effect, not blocked by Sheer Force).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Draining Kiss">
Type: Fairy
Category: Special
Base Power: 50
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact, heal

Mechanics:
- Drains 3/4 (75%) of the damage dealt, healing the user. This is higher than standard drain moves (which heal 1/2).
- Big Root boosts the drain fraction further (by ×1.3).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Laser Focus">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 30
Priority: 0
Target: Self
Flags: snatch

Mechanics:
- The user becomes focused; its next move is guaranteed to be a critical hit (critRatio set to 5, effectively always crits).
- The laserfocus volatile lasts until end of the following turn (duration 2). If used again before it expires, the duration resets to 2.
- Critical hits are still blocked by Battle Armor and Shell Armor.
- Snatch-able.

AI Scoring:
- Base +7 if the AI has Super Luck or Sniper ability, holds Scope Lens, or has a move with high crit chance; otherwise +6.
- Will not use if the opposing Pokémon has Shell Armor or Battle Armor.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Stun Spore">
Type: Grass
Category: Status
Base Power: —
Accuracy: 90
PP: 30
Priority: 0
Target: Normal
Flags: reflectable, powder

Mechanics:
- Paralyzes the target, reducing their Speed by 50% and giving a 25% chance to be fully immobilized each turn.
- Powder flag: Grass-types, Pokémon with Overcoat, and those holding Safety Goggles are immune.
- Reflectable: reversed by Magic Coat or Magic Bounce.

AI Scoring:
- Base +8 if any of the following: player is faster but would be slower after paralysis, AI has Hex or a flinch move, player is infatuated or confused.
- +7 otherwise.
- Additional -1 applied 50% of the time.
- Will not attempt to paralyze an already-paralyzed target.

R&B Changes: Accuracy increased from 75% to 90%.
</Element>

<Element name="Helping Hand">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: +5
Target: Adjacent Ally
Flags: bypasssub, noassist, failcopycat

Mechanics:
- Doubles only; has no valid target in singles.
- Boosts the ally's next move's base power by ×1.5 for that turn.
- If used twice on the same ally before they move, the multiplier stacks (×1.5 × ×1.5 = ×2.25).
- Fails if the ally has already moved this turn.
- Priority +5 ensures it almost always goes before the ally's move.

AI Scoring:
- +6.
- Will not use if the partner is also using Helping Hand or Follow Me, or if the partner is using a Status move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Zing Zap">
Type: Electric
Category: Physical
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- 30% chance to cause the target to flinch.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Work Up">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 30
Priority: 0
Target: Self
Flags: snatch

Mechanics:
- Raises the user's Attack and Special Attack each by 1 stage.
- Snatch-able.

AI Scoring (grouped with Tail Glow and Nasty Plot):
- Starts at +6.
- Additional +3 if the opposing Pokémon is incapacitated (frozen with no thawing move, asleep, recharging, or loafing from Truant).
- Otherwise: +1 if the opponent cannot 3HKO the AI; additional +1 if the AI is also faster.
- Additional -5 if the AI is slower and the opponent can 2HKO it.
- Additional -1 if the AI's Special Attack is already at +2 or higher.
- General setup prevention: no setup if the player can OHKO or achieve a faster 2HKO (see General Setup rules).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fake Out">
Type: Normal
Category: Physical
Base Power: 40
Accuracy: 100
PP: 5
Priority: +3
Target: Normal
Flags: contact

Mechanics:
- Can only be used on the user's first turn after switching in (fails otherwise).
- Always causes the target to flinch (100% secondary effect).
- Priority +3.
- Makes contact.

AI Scoring:
- +9 if it is the AI's first turn out and the target does not have Shield Dust or Inner Focus.
- Not scored (implicitly low or fails) on subsequent turns.

R&B Changes: PP reduced from 10 to 5.
</Element>

<Element name="Double Iron Bash">
Type: Steel
Category: Physical
Base Power: 60 per hit
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: contact, punch

Mechanics:
- Always hits exactly twice (multihit: 2); not affected by Skill Link (already fixed at 2 hits).
- 30% chance to cause the target to flinch, checked per hit.
- Punch flag: boosted by Iron Fist ability (×1.2 per hit).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Snarl">
Type: Dark
Category: Special
Base Power: 55
Accuracy: 100
PP: 10
Priority: 0
Target: All Adjacent Foes
Flags: sound, bypasssub

Mechanics:
- Always lowers the Special Attack of all adjacent foes by 1 stage (100% secondary effect on each target).
- Spread move (allAdjacentFoes): hits both foes in doubles, with the standard ×0.75 damage modifier in doubles.
- Sound flag: blocked by Soundproof; bypasses Substitute.

R&B Changes: PP reduced from 15 to 10; Accuracy increased from 95% to 100%.
</Element>

<Element name="Sleep Powder">
Type: Grass
Category: Status
Base Power: —
Accuracy: 80
PP: 15
Priority: 0
Target: Normal
Flags: reflectable, powder

Mechanics:
- Puts the target to sleep.
- Powder flag: Grass-types, Pokémon with Overcoat, and those holding Safety Goggles are immune.
- Reflectable: reversed by Magic Coat or Magic Bounce.
- Fails if the target already has a status condition or if Electric Terrain/Misty Terrain is active (terrain blocks sleep).

AI Scoring (grouped with all non-damaging sleep moves):
- Starts at +6.
- 25% of the time: +1 if the target can be put to sleep; +1 more if the AI has Dream Eater or Nightmare and the target lacks Snore/Sleep Talk; +1 more if the AI or partner has Hex.
- 75% of the time: no additional bonuses (stays at +6).

R&B Changes: Accuracy increased from 75% to 80%.
</Element>

<Element name="Shadow Sneak">
Type: Ghost
Category: Physical
Base Power: 40
Accuracy: 100
PP: 30
Priority: +1
Target: Normal
Flags: contact

Mechanics:
- Priority +1: moves before most other moves.
- Makes contact.

AI Scoring:
- Doubles special case: if the AI's partner holds Weakness Policy and Shadow Sneak is super effective on that partner, this move scores +12 total (intentional Weakness Policy activation).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Kings Shield">
Type: Steel
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: +4
Target: Self
Flags: noassist, failcopycat, failinstruct

Mechanics:
- Protects the user from most moves for the turn (same protection as Protect).
- If a contact move hits through King's Shield's protection check (i.e., attacker uses a contact move), the attacker's Attack is lowered by 1 stage.
- Stalling move: succeeds less reliably if used on consecutive turns (50% chance to fail after one use, always fails after two consecutive uses).

AI Scoring (identical to Protect):
- Base +6.
- Additional -2 if the AI is poisoned, burned, cursed, infatuated, Perish Songed, Leech Seeded, or Yawned.
- Additional +1 if the opposing Pokémon has any of the above conditions.
- Additional -1 if it's the AI's first turn out and not a double battle.
- Will not use if the AI would faint to residual damage (weather, status, etc.) after protecting.
- -20 (effectively never) if used two consecutive turns; 50% chance of -20 if used the previous turn.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Pin Missile">
Type: Bug
Category: Physical
Base Power: 25 per hit
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- Hits 2–5 times per use. Hit distribution: 3/8 for 2 hits, 3/8 for 3 hits, 1/8 for 4 hits, 1/8 for 5 hits.
- Skill Link ability forces 5 hits.
- Each hit is calculated independently (damage, substitute HP, etc.).
- Does not make contact.

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Thunder Punch">
Type: Electric
Category: Physical
Base Power: 75
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact, punch

Mechanics:
- 10% chance to paralyze the target.
- Punch flag: boosted by Iron Fist ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Rock Throw">
Type: Rock
Category: Physical
Base Power: 50
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- Simple damage-dealing move with no secondary effects.
- Does not make contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Natures Madness">
Type: Fairy
Category: Special
Base Power: —
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- Deals damage equal to half the target's current HP (rounded down, minimum 1).
- Cannot KO on its own.
- Does not make contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Struggle Bug">
Type: Bug
Category: Special
Base Power: 50
Accuracy: 100
PP: 10
Priority: 0
Target: All Adjacent Foes
Flags: (none special)

Mechanics:
- Always lowers the Special Attack of all adjacent foes by 1 stage (100% secondary effect on each target).
- Spread move (allAdjacentFoes): hits both foes in doubles with the standard ×0.75 damage modifier in doubles.
- Does not make contact.

R&B Changes: PP reduced from 20 to 10.
</Element>

<Element name="Ancient Power">
Type: Rock
Category: Special
Base Power: 60
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- 10% chance to raise the user's Attack, Defense, Special Attack, Special Defense, and Speed each by 1 stage simultaneously.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Detect">
Type: Fighting
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: +4
Target: Self
Flags: noassist, failcopycat

Mechanics:
- Mechanically identical to Protect: shields the user from all moves that turn.
- Shares the stall counter with Protect (consecutive use increases failure chance; stallingMove).
- Priority +4.

AI Scoring (same as Protect):
- Base +6.
- Additional -2 if the AI is poisoned, burned, cursed, infatuated, Perish Songed, Leech Seeded, or Yawned.
- Additional +1 if the opposing Pokémon has any of the above conditions.
- Additional -1 if it's the AI's first turn out and not a double battle.
- Will not use if the AI would faint to residual damage after protecting.
- -20 (effectively never) if used two consecutive turns; 50% chance of -20 if used the previous turn.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Supersonic">
Type: Normal
Category: Status
Base Power: —
Accuracy: 70
PP: 20
Priority: 0
Target: Normal
Flags: reflectable, sound, bypasssub

Mechanics:
- Confuses the target.
- Sound flag: blocked by Soundproof; bypasses Substitute (bypasssub).
- Reflectable: reversed by Magic Coat or Magic Bounce.
- Fails if the target is already confused.

R&B Changes: Accuracy increased from 55% to 70%.
</Element>

<Element name="Flamethrower">
Type: Fire
Category: Special
Base Power: 90
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- 10% chance to burn the target.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Vacuum Wave">
Type: Fighting
Category: Special
Base Power: 40
Accuracy: 100
PP: 30
Priority: +1
Target: Normal
Flags: (none special)

Mechanics:
- Priority +1: moves before most other moves.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Mud Shot">
Type: Ground
Category: Special
Base Power: 55
Accuracy: 95
PP: 15
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- Always lowers the target's Speed by 1 stage (100% secondary effect).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Hex">
Type: Ghost
Category: Special
Base Power: 65 (130 if target has a status condition)
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- Base Power doubles to 130 if the target has any status condition (burn, freeze, paralysis, poison, badly poisoned, or sleep), or if the target has the Comatose ability.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Heat Wave">
Type: Fire
Category: Special
Base Power: 95
Accuracy: 100
PP: 10
Priority: 0
Target: All Adjacent Foes
Flags: wind

Mechanics:
- 10% chance to burn each target hit.
- Spread move (allAdjacentFoes): hits both foes in doubles, with the standard ×0.75 damage modifier in doubles.
- Wind flag: triggers Wind Rider on allies.
- Does not make contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Slack Off">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: 0
Target: Self
Flags: snatch, heal

Mechanics:
- Heals the user for 1/2 of its max HP.
- Snatch-able.

AI Scoring (Recovery Moves group):
- +7 if the AI "should recover" (HP at or below 50%); +5 otherwise.
- Additional -20 if at full HP.
- Additional -6 if HP is 85% or above.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Freezing Glare">
Type: Psychic
Category: Special
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- 10% chance to freeze the target.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Steel Roller">
Type: Steel
Category: Physical
Base Power: 130
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Fails if no terrain (Electric, Grassy, Misty, or Psychic Terrain) is currently active.
- On hit, clears the active terrain (also clears terrain if it hits through a Substitute).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Scald">
Type: Water
Category: Special
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: defrost

Mechanics:
- 30% chance to burn the target.
- defrost flag: if the target is frozen, Scald thaws them before damage is dealt. The burn chance still applies normally.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Overdrive">
Type: Electric
Category: Special
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: All Adjacent Foes
Flags: sound, bypasssub

Mechanics:
- Spread move (allAdjacentFoes): hits both foes in doubles, with the standard ×0.75 damage modifier in doubles.
- Sound flag: blocked by Soundproof; bypasses Substitute (bypasssub).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Acid Armor">
Type: Poison
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Self
Flags: snatch

Mechanics:
- Raises the user's Defense by 2 stages.
- Snatch-able.

AI Scoring (Defensive Setup group):
- Starts at +6.
- Additional -5 if the AI is slower and the opponent can 2HKO it.
- ~95% of the time: additional +2 if the opponent is incapacitated.
- General setup prevention: no setup if the player can OHKO or achieve a faster 2HKO.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Rest">
Type: Psychic
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: 0
Target: Self
Flags: snatch, heal

Mechanics:
- The user falls asleep for 2 turns and fully restores its HP and cures any existing status condition.
- Fails if the user is already asleep, has the Comatose ability, is at full HP, or has the Insomnia/Vital Spirit ability.
- Sleep lasts exactly 2 turns (wakes up at the start of the 3rd turn after using Rest).
- Snatch-able.

AI Scoring:
- If the AI decides it should recover:
  - +8 if any of: holding a sleep-curing item (Lum Berry, Chesto Berry), has Sleep Talk or Snore, has Shed Skin or Early Bird, or has Hydration in Rain.
  - +7 otherwise.
- +5 if the AI decides it should not recover.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Baneful Bunker">
Type: Poison
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: +4
Target: Self
Flags: noassist, failcopycat

Mechanics:
- Protects the user from most moves for the turn (same protection as Protect).
- If a contact move hits through Baneful Bunker's protection check, the attacker is poisoned.
- Stalling move: succeeds less reliably on consecutive turns (50% chance to fail after one use, always fails after two consecutive uses).

AI Scoring (same as Protect):
- Base +6.
- Additional -2 if the AI is poisoned, burned, cursed, infatuated, Perish Songed, Leech Seeded, or Yawned.
- Additional +1 if the opposing Pokémon has any of the above conditions.
- Additional -1 if it's the AI's first turn out and not a double battle.
- Will not use if the AI would faint to residual damage after protecting.
- -20 (effectively never) if used two consecutive turns; 50% chance of -20 if used the previous turn.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Hidden Power Grass">
Type: Grass
Category: Special
Base Power: 60
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- A Grass-typed Hidden Power (type determined by the Pokémon's IVs at time of learning).
- Always 60 BP in gen 8.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Photon Geyser">
Type: Psychic
Category: Special (or Physical if Attack > Sp. Attack)
Base Power: 100
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- Before calculating damage, compares the user's Attack stat (ignoring stat stages? — actually uses effective stat with stages) to their Special Attack stat. If Attack is strictly higher, the move becomes Physical category.
- Ignores the target's ability when dealing damage (ignoreAbility: true), similar to Mold Breaker.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Obstruct">
Type: Dark
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: +4
Target: Self
Flags: failinstruct

Mechanics:
- Protects the user from most moves for the turn (same protection as Protect).
- If a contact move hits through Obstruct's protection check, the attacker's Defense is lowered by 2 stages (stronger penalty than King's Shield's -1 Attack).
- Stalling move: succeeds less reliably on consecutive turns (50% chance to fail after one use, always fails after two consecutive uses).

AI Scoring (same as Protect):
- Base +6.
- Additional -2 if the AI is poisoned, burned, cursed, infatuated, Perish Songed, Leech Seeded, or Yawned.
- Additional +1 if the opposing Pokémon has any of the above conditions.
- Additional -1 if it's the AI's first turn out and not a double battle.
- Will not use if the AI would faint to residual damage after protecting.
- -20 (effectively never) if used two consecutive turns; 50% chance of -20 if used the previous turn.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Thunder">
Type: Electric
Category: Special
Base Power: 110
Accuracy: 80
PP: 10
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- 30% chance to paralyze the target.
- Accuracy varies by weather:
  - Rain or Primordial Sea: never misses (accuracy = true).
  - Sun or Desolate Land: accuracy reduced to 50%.
  - Other weather (or no weather): 80% (R&B value).
- Does not make contact.

R&B Changes: Accuracy increased from 70% to 80%.
</Element>

<Element name="Round">
Type: Normal
Category: Special
Base Power: 60
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: sound, bypasssub

Mechanics:
- Sound flag: blocked by Soundproof; bypasses Substitute (bypasssub).
- If another Pokémon on either side uses Round this same turn, it moves immediately after the first user, and its Round's BP doubles to 120.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Rising Voltage">
Type: Electric
Category: Special
Base Power: 70 (140 if target is grounded in Electric Terrain)
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- Base Power doubles to 140 if Electric Terrain is active and the target is grounded.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Close Combat">
Type: Fighting
Category: Physical
Base Power: 120
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- After dealing damage, lowers the user's own Defense and Special Defense each by 1 stage.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Payback">
Type: Dark
Category: Physical
Base Power: 50 (100 if user moves after the target)
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Base Power doubles to 100 if the target has already moved this turn (or switched in this turn) — i.e., the user acts after the target.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Bulk Up">
Type: Fighting
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Self
Flags: snatch

Mechanics:
- Raises the user's Attack and Defense each by 1 stage.
- Snatch-able.

AI Scoring (Coil/Bulk Up group):
- Starts at +6.
- Treated as Defensive Setup if the opponent only has physical attacking moves (no special attacks); otherwise treated as Offensive Setup.
- For Defensive Setup scoring: +2 if opponent is incapacitated (~95% of the time); -5 if AI is slower and 2HKO'd.
- For Offensive Setup scoring: +3 if opponent is incapacitated; +1 if opponent can't 3HKO and user is faster; -5 if slower and 2HKO'd.
- General setup prevention applies.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Thousand Arrows">
Type: Ground
Category: Physical
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: All Adjacent Foes
Flags: (none special)

Mechanics:
- Spread move (allAdjacentFoes): hits all foes in doubles with the standard ×0.75 damage modifier.
- Bypasses Ground immunity: hits Flying-type Pokémon and those with Levitate/Air Balloon/etc. that would normally be immune to Ground.
- Against Flying-types that are immune to Ground, it deals neutral (1×) damage instead of being super effective or immune.
- On hit, applies the Smack Down effect: the target is grounded for the rest of the battle, losing their Ground immunity (Flying type immunity, Levitate, Air Balloon, etc.).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Dragon Rush">
Type: Dragon
Category: Physical
Base Power: 100
Accuracy: 85
PP: 10
Priority: 0
Target: Normal
Flags: contact, minimize

Mechanics:
- 20% chance to cause the target to flinch.
- minimize flag: BP doubles (to 200) against a target that has used Minimize.
- Makes contact.

R&B Changes: Accuracy increased from 75% to 85%.
</Element>

<Element name="Smelling Salts">
Type: Normal
Category: Physical
Base Power: 70 (140 if target is paralyzed)
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Base Power doubles to 140 if the target is paralyzed.
- On hit, cures the target's paralysis (even if the doubled-BP damage is dealt first).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Covet">
Type: Fairy
Category: Physical
Base Power: 60
Accuracy: 100
PP: 25
Priority: 0
Target: Normal
Flags: contact, noassist, failcopycat, failmefirst

Mechanics:
- After dealing damage, steals the target's held item if the user is not holding an item.
- If the target's item cannot be removed (e.g., Z-Crystals, Mega Stones for the holder), the steal fails.
- Makes contact.

R&B Changes: Type changed from Normal to Fairy.
</Element>

<Element name="Drain Punch">
Type: Fighting
Category: Physical
Base Power: 75
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact, punch, heal

Mechanics:
- Drains 1/2 of the damage dealt, healing the user. Big Root boosts drain to 3/4.
- Punch flag: boosted by Iron Fist ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fire Spin">
Type: Fire
Category: Special
Base Power: 35
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- Traps the target in the partiallytrapped volatile for 4–5 turns. At end of each trapped turn, the target loses 1/8 of its max HP. Ghost-type Pokémon are immune to being trapped.
- Binding Band increases the end-of-turn damage to 1/6 max HP.
- The trapped condition ends immediately if either Pokémon switches out (target can't switch normally; Baton Pass, Dragon Tail, etc. bypass the trap).
- Does not make contact.

R&B Changes: Accuracy increased from 85% to 100%.
</Element>

<Element name="Feather Dance">
Type: Flying
Category: Status
Base Power: —
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: reflectable, dance

Mechanics:
- Lowers the target's Attack by 2 stages.
- Reflectable: reversed by Magic Coat or Magic Bounce.
- Dance flag: triggers Dancer ability on allies (copies the move).

R&B Changes: PP reduced from 15 to 5.
</Element>

<Element name="Fling">
Type: Dark
Category: Physical
Base Power: Varies by held item
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: noparentalbond

Mechanics:
- The user flings its held item at the target. The BP and effect depend on the item flung.
- Fails if the user has no item, the item cannot be flung, or the user is under an effect that removes the item (e.g., Embargo).
- The user's item is consumed after use.
- If a Berry is flung, the target receives the Berry's on-eat effect.
- Other items have specific Fling BPs and secondary effects (e.g., Toxic Orb inflicts bad poison, King's Rock flinches, etc.).

AI Scoring:
- +12 if the Fling's effect raises the target's Speed (e.g., Salac Berry) AND the AI's partner has Weakness Policy AND Fling is super effective on the target.
- +9 if the Fling's effect raises the target's Speed but the above conditions aren't all met.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Pursuit">
Type: Dark
Category: Physical
Base Power: 40 (80 if target is switching out)
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- If the target attempts to switch out this turn, Pursuit executes before the switch, deals double damage (80 BP), and never misses.
- The target takes the hit before leaving the field; if it faints, no replacement is sent out immediately.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Knock Off">
Type: Dark
Category: Physical
Base Power: 65 (97 if target holds a removable item)
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- If the target holds a removable item, BP is increased by ×1.5 (to 97) before damage is dealt.
- On hit, removes the target's held item (item is lost for the battle; not consumed or transferred).
- Items that cannot be removed (e.g., Mega Stones, Z-Crystals, items held by Pokémon with Sticky Hold) are not knocked off.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Megahorn">
Type: Bug
Category: Physical
Base Power: 120
Accuracy: 90
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Simple high-power move with no secondary effects.
- Makes contact.

R&B Changes: Accuracy increased from 85% to 90%.
</Element>

<Element name="Mach Punch">
Type: Fighting
Category: Physical
Base Power: 40
Accuracy: 100
PP: 30
Priority: +1
Target: Normal
Flags: contact, punch

Mechanics:
- Priority +1: moves before most other moves.
- Punch flag: boosted by Iron Fist ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Surf">
Type: Water
Category: Special
Base Power: 90
Accuracy: 100
PP: 15
Priority: 0
Target: All Adjacent (foes and ally)
Flags: (none special)

Mechanics:
- allAdjacent target: hits both foes AND the ally in doubles, with the standard ×0.75 damage modifier in doubles.
- Deals double damage to a target currently using Dive.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Volt Tackle">
Type: Electric
Category: Physical
Base Power: 120
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- User takes recoil damage equal to 33% of the damage dealt (recoil [33, 100]).
- 10% chance to paralyze the target.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Chatter">
Type: Flying
Category: Special
Base Power: 65
Accuracy: 100
PP: 20
Priority: 0
Target: Any (distance)
Flags: sound, bypasssub, distance, nosleeptalk, noassist, failcopycat, failmimic, failinstruct

Mechanics:
- Always confuses the target (100% secondary effect).
- Sound flag: blocked by Soundproof; bypasses Substitute (bypasssub).
- Distance flag: can target any Pokémon in doubles.
- Cannot be called by Sleep Talk, Assist, Copycat, Mimic, or Instruct.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Apple Acid">
Type: Grass
Category: Special
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- Always lowers the target's Special Defense by 1 stage (100% secondary effect).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Air Cutter">
Type: Flying
Category: Special
Base Power: 60
Accuracy: 100
PP: 25
Priority: 0
Target: All Adjacent Foes
Flags: slicing, wind

Mechanics:
- High critical hit ratio (critRatio 2: ~1/8 chance).
- Spread move (allAdjacentFoes): hits all foes in doubles, with the standard ×0.75 damage modifier in doubles.
- Slicing flag: boosted by Sharpness ability (×1.5).
- Wind flag: triggers Wind Rider on allies.
- Does not make contact.

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Life Dew">
Type: Water
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Self + Ally (allies)
Flags: snatch, heal, bypasssub

Mechanics:
- Restores 1/4 of max HP to both the user and their ally in doubles. In singles, only affects the user.
- Snatch-able.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Cosmic Power">
Type: Psychic
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Self
Flags: snatch

Mechanics:
- Raises the user's Defense and Special Defense each by 1 stage.
- Snatch-able.

AI Scoring (Defensive Setup group):
- Starts at +6.
- Additional -5 if the AI is slower and the opponent can 2HKO it.
- ~95% of the time: additional +2 if the opponent is incapacitated; additional +2 if Defense and SpDef are both below +2.
- General setup prevention applies.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sand Attack">
Type: Ground
Category: Status
Base Power: —
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: reflectable

Mechanics:
- Lowers the target's Accuracy by 1 stage.
- Reflectable: reversed by Magic Coat or Magic Bounce.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Zap Cannon">
Type: Electric
Category: Special
Base Power: 120
Accuracy: 50
PP: 5
Priority: 0
Target: Normal
Flags: bullet

Mechanics:
- Always paralyzes the target on hit (100% secondary effect).
- Bullet flag: blocked by Bulletproof ability.
- Does not make contact.

AI Scoring (grouped with Thunder Wave and Stun Spore for paralysis):
- Base +8 if any of: player is faster but would be slower after paralysis, AI has Hex or a flinch move, player is infatuated or confused.
- +7 otherwise.
- Additional -1 applied 50% of the time.
- Will not attempt to paralyze an already-paralyzed target.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Meteor Beam">
Type: Rock
Category: Special
Base Power: 120
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: charge

Mechanics:
- Two-turn move: on turn 1, the user charges and raises its own Special Attack by 1 stage; on turn 2, fires the beam.
- charge flag: cannot be called by Sleep Talk, Assist, or Instruct.
- Does not make contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Attack Order">
Type: Bug
Category: Physical
Base Power: 90
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- High critical hit ratio (critRatio 2: ~1/8 chance).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Leer">
Type: Normal
Category: Status
Base Power: —
Accuracy: 100
PP: 10
Priority: 0
Target: All Adjacent Foes
Flags: reflectable

Mechanics:
- Lowers the Defense of all adjacent foes by 1 stage.
- Spread move (allAdjacentFoes): hits both foes in doubles.
- Reflectable: reversed by Magic Coat or Magic Bounce.

R&B Changes: PP reduced from 30 to 10.
</Element>

<Element name="Venoshock">
Type: Poison
Category: Special
Base Power: 65 (130 if target is poisoned or badly poisoned)
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- Base Power doubles to 130 if the target is poisoned (psn) or badly poisoned (tox).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Psychic Fangs">
Type: Psychic
Category: Physical
Base Power: 85
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact, bite

Mechanics:
- Destroys Reflect, Light Screen, and Aurora Veil on the target's side before dealing damage (bypasses the screens, then hits).
- Bite flag: boosted by Strong Jaw ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Heavy Slam">
Type: Steel
Category: Physical
Base Power: Varies (40–120, based on weight ratio)
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact, minimize

Mechanics:
- BP depends on how much heavier the user is than the target:
  - ≥5× heavier: 120 BP
  - ≥4× heavier: 100 BP
  - ≥3× heavier: 80 BP
  - ≥2× heavier: 60 BP
  - <2× heavier: 40 BP
- minimize flag: BP doubles against a target that has used Minimize.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sheer Cold">
Type: Ice
Category: Special
Base Power: —
Accuracy: 30
PP: 5
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- OHKO move: if it hits, the target is knocked out instantly.
- ohko: 'Ice' — fails immediately against Ice-type targets (they are immune).
- Fails if the target's level is higher than the user's level.
- Accuracy is always 30% (not affected by accuracy/evasion stages).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Electric Terrain">
Type: Electric
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: All (field)
Flags: (none special)

Mechanics:
- Sets Electric Terrain for 5 turns (8 turns if user holds Terrain Extender).
- Effects while active: boosts Electric-type moves used by grounded Pokémon by ×1.3; prevents grounded Pokémon from falling asleep; Rising Voltage doubles BP against grounded targets.
- Terrain expires or is replaced by another terrain move.

AI Scoring:
- +9 if AI holds Terrain Extender; +8 otherwise.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sacred Sword">
Type: Fighting
Category: Physical
Base Power: 90
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact, slicing

Mechanics:
- Ignores the target's Defense stat boosts (ignoreDefensive: true) and evasion boosts (ignoreEvasion: true).
- Slicing flag: boosted by Sharpness ability (×1.5).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Dragon Dance">
Type: Dragon
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Self
Flags: snatch, dance

Mechanics:
- Raises the user's Attack and Speed each by 1 stage.
- Dance flag: triggers Dancer ability on allies.
- Snatch-able.

AI Scoring (Offensive Setup group):
- Starts at +6.
- Additional +3 if the opposing Pokémon is incapacitated (frozen with no thawing move, asleep, recharging, or loafing from Truant).
- Additional -5 if the AI is slower and the opponent can 2HKO it.
- General setup prevention applies (no setup if player can OHKO or faster 2HKO).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Echoed Voice">
Type: Normal
Category: Special
Base Power: 40 (escalates each consecutive turn)
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: sound, bypasssub

Mechanics:
- On the first use: 40 BP. Each consecutive turn any Pokémon uses Echoed Voice (field pseudo-weather tracks this), the multiplier increases by 1 (up to 5×): 40 → 80 → 120 → 160 → 200 BP.
- If Echoed Voice is not used for a full turn, the multiplier resets.
- Sound flag: blocked by Soundproof; bypasses Substitute (bypasssub).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Crabhammer">
Type: Water
Category: Physical
Base Power: 100
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- High critical hit ratio (critRatio 2: ~1/8 chance).
- Makes contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Strange Steam">
Type: Fairy
Category: Special
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- 20% chance to confuse the target.
- Does not make contact.

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Confuse Ray">
Type: Ghost
Category: Status
Base Power: —
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: reflectable

Mechanics:
- Confuses the target.
- Reflectable: reversed by Magic Coat or Magic Bounce.
- Fails if the target is already confused.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Water Spout">
Type: Water
Category: Special
Base Power: 150 at full HP (scales down)
Accuracy: 100
PP: 5
Priority: 0
Target: All Adjacent Foes
Flags: (none special)

Mechanics:
- BP = 150 × (user's current HP / user's max HP), rounded down (minimum 1).
- Spread move (allAdjacentFoes): hits all foes in doubles with the standard ×0.75 damage modifier.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Role Play">
Type: Psychic
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Normal
Flags: bypasssub

Mechanics:
- Copies the target's ability, replacing the user's current ability.
- Fails if the user and target have the same ability, the target's ability has the failroleplay flag (certain signature abilities), or the user's ability has cantsuppress.

AI Scoring:
- +9 if the AI's partner has Huge Power, Pure Power, Protean, or Tough Claws AND the AI does not already have any of those abilities.
- -20 otherwise.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Dragon Tail">
Type: Dragon
Category: Physical
Base Power: 60
Accuracy: 95
PP: 10
Priority: -6
Target: Normal
Flags: contact, noassist, failcopycat

Mechanics:
- Deals damage and forces the target to switch to a random Pokémon in its party (forceSwitch: true).
- Priority -6: moves last.
- Fails against targets with Suction Cups or that are rooted (Ingrain).
- Hits through Substitute (damage dealt first, then forceSwitch).
- Makes contact.

R&B Changes: Accuracy increased from 90% to 95%.
</Element>

<Element name="Ice Hammer">
Type: Ice
Category: Physical
Base Power: 100
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact, punch

Mechanics:
- After dealing damage, lowers the user's own Speed by 1 stage.
- Punch flag: boosted by Iron Fist ability.
- Makes contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Taunt">
Type: Dark
Category: Status
Base Power: —
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: reflectable, bypasssub

Mechanics:
- The target is Taunted for 3 turns (extended to 4 if used before the target acts this turn).
- While Taunted, the target cannot use Status moves (they fail if selected), except Me First.
- Bypasses Substitute (bypasssub).
- Reflectable: reversed by Magic Coat or Magic Bounce.

AI Scoring:
- +9 if the target has Trick Room and TR is not currently active.
- +9 if the target has Defog, Aurora Veil is currently active, and the AI is faster.
- +5 otherwise.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fusion Bolt">
Type: Electric
Category: Physical
Base Power: 100 (200 if Fusion Flare was used this turn)
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: (none special)

Mechanics:
- BP doubles to 200 if Fusion Flare was the last successful move used this turn (by either side).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Bind">
Type: Normal
Category: Physical
Base Power: 15
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Traps the target in the partiallytrapped volatile for 4–5 turns. At end of each trapped turn, the target loses 1/8 of its max HP (1/6 with Binding Band).
- Ghost-type Pokémon are immune to being trapped.
- Makes contact.

R&B Changes: Accuracy increased from 85% to 100%.
</Element>

<Element name="Hypnosis">
Type: Psychic
Category: Status
Base Power: —
Accuracy: 70
PP: 20
Priority: 0
Target: Normal
Flags: reflectable

Mechanics:
- Puts the target to sleep.
- Reflectable: reversed by Magic Coat or Magic Bounce.
- Fails if the target already has a status condition, or if Electric/Misty Terrain is active.

AI Scoring (grouped with all non-damaging sleep moves):
- Starts at +6.
- 25% of the time: +1 if target can be put to sleep; +1 more if AI has Dream Eater or Nightmare and target lacks Snore/Sleep Talk; +1 more if AI or partner has Hex.
- 75% of the time: no additional bonuses.

R&B Changes: Accuracy increased from 60% to 70%.
</Element>

<Element name="Pollen Puff">
Type: Bug
Category: Special
Base Power: 90 (vs foes) / heals ally
Accuracy: 100
PP: 15
Priority: 0
Target: Normal or Ally
Flags: bullet

Mechanics:
- If targeting a foe: deals 90 BP Bug-type Special damage. Blocked by Bulletproof ability.
- If targeting an ally (doubles): heals the ally for 50% of their max HP instead of dealing damage. Blocked by Heal Block.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Bullet Punch">
Type: Steel
Category: Physical
Base Power: 40
Accuracy: 100
PP: 30
Priority: +1
Target: Normal
Flags: contact, punch

Mechanics:
- Priority +1: moves before most other moves.
- Punch flag: boosted by Iron Fist ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Heal Pulse">
Type: Psychic
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Any (any Pokémon on the field, including foes)
Flags: reflectable, heal, pulse, distance

Mechanics:
- Restores the target's HP by 50% of their max HP.
- If the user has Mega Launcher: heals 75% of the target's max HP instead (pulse flag).
- Blocked by Heal Block on the target.
- Blocked by Protect: if the target is behind Protect, Heal Pulse fails.
- Reflectable: reversed by Magic Coat/Magic Bounce; if a foe reflects it, the user gets healed instead.
- distance flag: can target any slot in doubles (not limited to adjacent).
- Does not make contact.
- Can be used on foes (heals them); practically used to support an ally in doubles.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Seed Bomb">
Type: Grass
Category: Physical
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: bullet

Mechanics:
- Deals 80 BP Grass-type Physical damage.
- Bullet flag: blocked by Bulletproof ability.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Coaching">
Type: Fighting
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Adjacent Ally
Flags: bypasssub

Mechanics:
- Raises the target ally's Attack and Defense by 1 stage each.
- Can only target an adjacent ally; useless in singles.
- bypasssub: bypasses the ally's Substitute (if any).
- Does not make contact.

AI Scoring:
- Starts at +6.
- If in a double battle and the partner does NOT have Contrary:
  - If partner's Attack stage < +2: score += (1 − current Attack stage) [e.g. +1 if unboosted, +2 if at −1]
  - If partner's Defense stage < +2: score += (1 − current Defense stage)
  - Additional +1 applied ~80% of the time regardless of partner's stages.
  - Example: partner at +0/+0 → score is +8 (20%) or +9 (80%).
- If not in a double battle, or partner has Contrary: never used (score −20).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Gear Grind">
Type: Steel
Category: Physical
Base Power: 50 per hit (×2 hits)
Accuracy: 100 (85% → 100% in R&B)
PP: 15
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Always hits exactly twice; total damage is 2 × 50 BP.
- Each hit is calculated independently (each can be a critical hit, each can trigger secondary effects from abilities/items).
- Makes contact.

R&B Changes: Accuracy increased from 85% to 100%.
</Element>

<Element name="Glacial Lance">
Type: Ice
Category: Physical
Base Power: 120
Accuracy: 100
PP: 5
Priority: 0
Target: All Adjacent Foes
Flags: none

Mechanics:
- Deals 120 BP Ice-type Physical damage to all adjacent foes.
- Spread move: ×0.75 damage modifier in doubles (vs. each foe).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="X-Scissor">
Type: Bug
Category: Physical
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact, slicing

Mechanics:
- Deals 80 BP Bug-type Physical damage.
- Slicing flag: damage boosted ×1.5 by Sharpness ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Whirlpool">
Type: Water
Category: Special
Base Power: 35
Accuracy: 100 (85% → 100% in R&B)
PP: 15
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 35 BP Water-type Special damage and traps the target with the partiallytrapped volatile.
- Trapping lasts 4-5 turns; at the end of each turn the trapped Pokémon loses 1/8 of its max HP.
- Binding Band held by user: trap damage increases to 1/6 max HP per turn.
- Ghost-type targets are immune to the trapping effect.
- Trapped Pokémon cannot switch or flee.
- Does not make contact.

AI Scoring: +6 (~80%) or +8 (~20%) — treated as a damaging trapping move.

R&B Changes: Accuracy increased from 85% to 100%.
</Element>

<Element name="Dragon Pulse">
Type: Dragon
Category: Special
Base Power: 85
Accuracy: 100
PP: 10
Priority: 0
Target: Any (any slot in doubles)
Flags: pulse, distance

Mechanics:
- Deals 85 BP Dragon-type Special damage.
- Pulse flag: boosted ×1.5 by Mega Launcher ability.
- distance flag: can target any Pokémon on the field, not just adjacent ones.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Body Press">
Type: Fighting
Category: Physical
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 80 BP Fighting-type Physical damage.
- Uses the user's Defense stat (not Attack) as the offensive stat for damage calculation.
- Still targets the foe's Defense. Effectively: damage ∝ user's Def vs. target's Def.
- Stat boosts/drops to the user's Defense are reflected in damage (e.g., after Iron Defense, Body Press hits very hard).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Shift Gear">
Type: Steel
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Self
Flags: snatch

Mechanics:
- Raises user's Speed by 2 stages and Attack by 1 stage.
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

AI Scoring: Offensive Setup group (with Dragon Dance, Swords Dance, Hone Claws, etc.).
- Starts at +6.
- If the opposing Pokémon is incapacitated (frozen, asleep, recharging, Truant loafing): +3.
- If AI is slower and is 2HKO'd by the opponent: −5.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Power Gem">
Type: Rock
Category: Special
Base Power: 80
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 80 BP Rock-type Special damage.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Head Charge">
Type: Normal
Category: Physical
Base Power: 120
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 120 BP Normal-type Physical damage.
- Recoil: user takes 1/4 of damage dealt as recoil.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Terrain Pulse">
Type: Normal (changes based on terrain)
Category: Special
Base Power: 50 (100 in terrain while grounded)
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: pulse

Mechanics:
- Base type is Normal and BP is 50 with no terrain, or if the user is not grounded.
- If the user is grounded and a terrain is active:
  - Type becomes Electric (Electric Terrain), Grass (Grassy Terrain), Fairy (Misty Terrain), or Psychic (Psychic Terrain).
  - BP doubles to 100.
- Pulse flag: boosted ×1.5 by Mega Launcher ability.
- Does not make contact.
- "Grounded" means the Pokémon is not Flying-type (or has lost Flying via Roost/Ring Target), not under Levitate, not holding Air Balloon, and not under Magnet Rise/Telekinesis.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Shore Up">
Type: Ground
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: 0
Target: Self
Flags: snatch, heal

Mechanics:
- Restores user's HP by 50% of their max HP.
- In Sandstorm: restores 2/3 (~66.7%) of max HP instead.
- Blocked by Heal Block.
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

AI Scoring: Follows standard Recovery Move scoring (Recover, Slack Off, etc.).
- If AI decides it should recover: +7.
- Otherwise: +5.
- Will not use if at full HP (−20), or at 85%+ HP (−6).
(Note: No separate AI scoring entry for the sandstorm boost; treated as standard 50% recovery by the AI.)

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Agility">
Type: Psychic
Category: Status
Base Power: —
Accuracy: —
PP: 30
Priority: 0
Target: Self
Flags: snatch

Mechanics:
- Raises user's Speed by 2 stages.
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

AI Scoring:
- If AI is slower than the opposing Pokémon: +7.
- Otherwise: never used (score −20).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Psywave">
Type: Psychic
Category: Special
Base Power: Variable
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals damage equal to: floor(random(50, 150) × user's level / 100) HP.
  - Random value is in the range [50, 150] inclusive, giving damage from 0.5× to 1.5× the user's level.
  - Ignores Stat stages and type effectiveness modifiers; damage is fixed HP regardless of types.
  - Still affected by type immunity (Normal/Dark immune to Psychic? No — Psywave is Psychic type, so Dark types are immune and Normal types are immune).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Poison Fang">
Type: Poison
Category: Physical
Base Power: 50
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact, bite

Mechanics:
- Deals 50 BP Poison-type Physical damage.
- 50% chance to badly poison (toxic) the target.
- Bite flag: boosted by Strong Jaw ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Low Kick">
Type: Fighting
Category: Physical
Base Power: Varies by target weight
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- BP is determined by the target's weight in kg:
  - < 10 kg: 20 BP
  - 10–24.9 kg: 40 BP
  - 25–49.9 kg: 60 BP
  - 50–99.9 kg: 80 BP
  - 100–199.9 kg: 100 BP
  - ≥ 200 kg: 120 BP
- Autotomize halves the target's effective weight for this calculation.
- Fails against Dynamax targets.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Relic Song">
Type: Normal
Category: Special
Base Power: 75
Accuracy: 100
PP: 10
Priority: 0
Target: All Adjacent Foes
Flags: sound, bypasssub

Mechanics:
- Deals 75 BP Normal-type Special damage to all adjacent foes.
- Spread move: ×0.75 damage modifier in doubles (vs. each foe).
- 10% chance to inflict Sleep on each target hit.
- Sound flag: blocked by Soundproof ability; bypasses Substitute.
- bypasssub: explicitly bypasses Substitute in addition to sound.
- Meloetta forme change: after using Relic Song, Meloetta alternates between its base form (Special attacker) and Pirouette form (Physical attacker). Does not apply to transformed Meloetta.
- Does not make contact.

AI Scoring (Meloetta-specific):
- If Meloetta is in base form: additional +10 (stacks with standard damaging move bonuses).
- If Meloetta is in Pirouette form: never used (score −20).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Curse">
Type: Ghost
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Varies (self if non-Ghost; foe if Ghost)
Flags: bypasssub

Mechanics (non-Ghost user):
- Target changes to self; raises user's Attack by 1 and Defense by 1, lowers Speed by 1.
- No HP cost.

Mechanics (Ghost-type user):
- User loses 1/2 of its max HP.
- Inflicts the "curse" volatile status on the target (a foe); target takes 1/4 of its max HP as damage at the end of each turn.
- Fails if the target already has the Curse volatile.
- bypasssub: bypasses Substitute on the target.

AI Scoring (non-Ghost — acts as Bulk Up variant):
- Follows Coil/Bulk Up group scoring (starts +6).
- Since Curse boosts physical stats (Atk + Def), AI checks if opponent has only physical attacks → treated as Defensive Setup; otherwise treated as Offensive Setup.
- See Defensive/Offensive Setup entries for scoring details.
(Ghost-type Curse scoring not explicitly documented in AI.md.)

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Milk Drink">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: 0
Target: Self
Flags: snatch, heal

Mechanics:
- Restores user's HP by 50% of their max HP.
- Blocked by Heal Block.
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

AI Scoring: Follows standard Recovery Move scoring (Recover, Slack Off, etc.).
- If AI decides it should recover: +7.
- Otherwise: +5.
- Will not use if at full HP (−20), or at 85%+ HP (−6).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Meteor Mash">
Type: Steel
Category: Physical
Base Power: 90
Accuracy: 100 (90% → 100% in R&B)
PP: 10
Priority: 0
Target: Normal
Flags: contact, punch

Mechanics:
- Deals 90 BP Steel-type Physical damage.
- 20% chance to raise user's Attack by 1 stage.
- Punch flag: boosted by Iron Fist ability.
- Makes contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Feint">
Type: Normal
Category: Physical
Base Power: 30
Accuracy: 100
PP: 10
Priority: +2
Target: Normal
Flags: none (noassist, failcopycat — cannot be called by Assist or Copycat)

Mechanics:
- Priority +2: moves very early in the turn order.
- Breaks Protect/Detect: lifts the target's protection effect (Protect, Detect, Baneful Bunker, King's Shield, Obstruct, Spiky Shield, etc.) and then hits. The protection is removed for the remainder of the turn, allowing follow-up moves to hit as well.
- Does not make contact (despite being a Physical move).
- Cannot be called by Assist or Copycat.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Zen Headbutt">
Type: Psychic
Category: Physical
Base Power: 80
Accuracy: 100 (90% → 100% in R&B)
PP: 15
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 80 BP Psychic-type Physical damage.
- 20% chance to cause the target to flinch.
- Makes contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Bug Buzz">
Type: Bug
Category: Special
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: sound, bypasssub

Mechanics:
- Deals 90 BP Bug-type Special damage.
- 10% chance to lower the target's Special Defense by 1 stage.
- Sound flag: blocked by Soundproof ability; bypasses Substitute.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Cross Chop">
Type: Fighting
Category: Physical
Base Power: 100
Accuracy: 90 (80% → 90% in R&B)
PP: 5
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 100 BP Fighting-type Physical damage.
- High critical hit ratio (critRatio 2 — 1/8 crit chance).
- Makes contact.

R&B Changes: Accuracy increased from 80% to 90%.
</Element>

<Element name="Phantom Force">
Type: Ghost
Category: Physical
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact, charge

Mechanics:
- Two-turn move: on turn 1 the user vanishes (invulnerable state); on turn 2 it emerges and attacks.
- While vanished, the user cannot be hit by any moves.
- breaksProtect: on the attack turn, bypasses and lifts Protect/Detect/similar protection effects, hitting through them.
- charge flag: cannot be called by Sleep Talk, Assist, or Instruct.
- Makes contact.
- Power Herb does NOT work on Phantom Force (charge flag prevents item shortcut).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fell Stinger">
Type: Bug
Category: Physical
Base Power: 50
Accuracy: 100
PP: 25
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 50 BP Bug-type Physical damage.
- If the target faints after being hit by Fell Stinger: user's Attack rises by 3 stages.
- The +3 Atk boost triggers only on KO, not on a non-KO hit.
- Makes contact.

AI Scoring:
- If AI is not at max Attack stage (+6) and Fell Stinger will KO the target:
  - If AI is faster: total score +21 (~80%) or +23 (~20%).
  - If AI is slower: total score +15 (~80%) or +17 (~20%).
- Otherwise: treated as a normal damaging move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Acid Spray">
Type: Poison
Category: Special
Base Power: 40
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: bullet

Mechanics:
- Deals 40 BP Poison-type Special damage.
- 100% chance to lower the target's Special Defense by 2 stages.
- Bullet flag: blocked by Bulletproof ability.
- Does not make contact.

AI Scoring: Additional +6 on top of standard damage scoring, regardless of whether this is the highest-damage move. Stacks with standard kill/damage bonuses.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="High Jump Kick">
Type: Fighting
Category: Physical
Base Power: 130
Accuracy: 90
PP: 10
Priority: 0
Target: Normal
Flags: contact, gravity

Mechanics:
- Deals 130 BP Fighting-type Physical damage.
- gravity flag: fails if Gravity is in effect on the field.
- Crash damage: if High Jump Kick misses or fails (e.g., target has Ghost typing, Protect, Gravity, etc.), user takes 1/2 of its max HP as crash damage.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Double Team">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 15
Priority: 0
Target: Self
Flags: snatch

Mechanics:
- Raises user's Evasion by 1 stage.
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Stomp">
Type: Normal
Category: Physical
Base Power: 65
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact, minimize

Mechanics:
- Deals 65 BP Normal-type Physical damage.
- 30% chance to cause the target to flinch.
- minimize flag: BP doubles to 130 against a target that has used Minimize.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Glare">
Type: Normal
Category: Status
Base Power: —
Accuracy: 100
PP: 30
Priority: 0
Target: Normal
Flags: reflectable

Mechanics:
- Inflicts paralysis on the target.
- Unlike Thunder Wave, Glare is Normal type and bypasses Normal-type immunity for Ghost-type targets (i.e., can paralyze Ghost types; changed in gen 6+).
- Reflectable: reversed by Magic Coat/Magic Bounce.
- Fails if target already has a non-volatile status condition, or is immune to paralysis (e.g., Limber ability, Electric type vs Thunder Wave — but not relevant here since Glare is Normal type).
- Does not make contact.

AI Scoring: Paralysis group (Thunder Wave, Stun Spore, Glare, Nuzzle, Zap Cannon).
- If player mon is faster than AI but would be slower after paralysis, OR AI has Hex or a flinch move, OR player is infatuated/confused: +8.
- Otherwise: +7.
- Additional −1 applied ~50% of the time regardless.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Flame Charge">
Type: Fire
Category: Physical
Base Power: 50
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 50 BP Fire-type Physical damage.
- 100% chance to raise user's Speed by 1 stage after hitting.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Water Pledge">
Type: Water
Category: Special
Base Power: 80 (standalone) / 150 (combined)
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: pledgecombo

Mechanics:
- Standalone: deals 80 BP Water-type Special damage.
- Combo mechanics (doubles only — ally must use a compatible Pledge move same turn):
  - Water + Fire Pledge: combined move deals 150 BP Water-type damage; creates a "Rainbow" (Water Pledge condition) on the user's side for 4 turns, doubling secondary effect chances for the user's team.
  - Water + Grass Pledge: combined move deals 150 BP Grass-type damage; creates a "Swamp" (Grass Pledge condition) on the opponent's side for 4 turns, reducing all opponent Pokémon's Speed to 25% of their normal Speed.
- In singles: can only be used standalone (no ally to combine with).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Metal Burst">
Type: Steel
Category: Physical
Base Power: Variable (1.5× damage received)
Accuracy: 100
PP: 10
Priority: 0
Target: Scripted (the Pokémon that last damaged the user this turn)
Flags: none

Mechanics:
- Deals 1.5× the damage the user received from the last hit this turn.
- Fails if the user was not damaged this turn (must have taken damage in the same turn).
- Automatically targets whoever last damaged the user; requires no manual target.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Muddy Water">
Type: Water
Category: Special
Base Power: 90
Accuracy: 95 (85% → 95% in R&B)
PP: 10
Priority: 0
Target: All Adjacent Foes
Flags: none

Mechanics:
- Deals 90 BP Water-type Special damage to all adjacent foes.
- Spread move: ×0.75 damage modifier in doubles (vs. each foe).
- 30% chance to lower each target's Accuracy by 1 stage.
- Does not make contact.

R&B Changes: Accuracy increased from 85% to 95%.
</Element>

<Element name="Ice Fang">
Type: Ice
Category: Physical
Base Power: 65
Accuracy: 100 (95% → 100% in R&B)
PP: 15
Priority: 0
Target: Normal
Flags: contact, bite

Mechanics:
- Deals 65 BP Ice-type Physical damage.
- Two independent secondary effects: 10% chance to freeze the target; 10% chance to flinch the target (each rolls separately).
- Bite flag: boosted by Strong Jaw ability.
- Makes contact.

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Trick Room">
Type: Psychic
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: -7
Target: All (field-wide)
Flags: mirror

Mechanics:
- Priority −7: moves last, even after all other negative-priority moves.
- Sets up the Trick Room pseudo-weather for 5 turns (7 with Persistent ability).
- While Trick Room is active, Speed order is reversed: slower Pokémon move first.
- If Trick Room is already active, using it again cancels it immediately.
- Does not make contact.

AI Scoring:
- If AI or its partner is slower than any player Pokémon on the field: +10.
- Otherwise: +5.
- If Trick Room is already active: −20.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Self Destruct">
Type: Normal
Category: Physical
Base Power: 200
Accuracy: 100
PP: 5
Priority: 0
Target: All Adjacent (both foes AND ally in doubles)
Flags: noparentalbond

Mechanics:
- User faints immediately after using this move, regardless of whether it hits (selfdestruct: "always").
- Hits all adjacent Pokémon (both foes and the user's ally in doubles). ×0.75 modifier does NOT apply here (allAdjacent does apply the spread modifier for each target).
- noparentalbond: cannot be doubled by Parental Bond.
- Does not make contact.
- R&B mechanic: halves the target's Defense stat for damage calculation (×0.5 defensive modifier). This effectively makes the move deal damage as if target has half its Defense.

AI Scoring: Boom move group (Explosion, Self-Destruct, Misty Explosion).
- < 10% HP: +10.
- < 33% HP: +8 (~70%) or +0 (~30%).
- < 66% HP: +7 (50%) or +0 (50%).
- Otherwise: +7 (~5%) or +0 (~95%).
- Will not use if target is immune, or if the AI mon is the last remaining and player has multiple Pokémon alive.
- −1 to score if both AI and player are on their last Pokémon.

R&B Changes: Self-Destruct halves the target's Defense in damage calculation (restoring gen 4 mechanic).
</Element>

<Element name="Petal Blizzard">
Type: Grass
Category: Physical
Base Power: 90
Accuracy: 100
PP: 15
Priority: 0
Target: All Adjacent (both foes AND ally in doubles)
Flags: wind

Mechanics:
- Deals 90 BP Grass-type Physical damage to all adjacent Pokémon (both foes and ally in doubles).
- Spread modifier: ×0.75 applied to each target in doubles.
- wind flag: triggers the Wind Rider ability on the user's ally if they have it.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Avalanche">
Type: Ice
Category: Physical
Base Power: 60 (120 if hit by target this turn)
Accuracy: 100
PP: 10
Priority: -4
Target: Normal
Flags: contact

Mechanics:
- Priority −4: moves after nearly all other moves.
- Deals 60 BP Ice-type Physical damage.
- BP doubles to 120 if the user was damaged by the target during the same turn.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Foul Play">
Type: Dark
Category: Physical
Base Power: 95
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 95 BP Dark-type Physical damage.
- Uses the TARGET's Attack stat (not the user's) for damage calculation, including the target's Attack boosts/drops.
- Still uses the user's level and the target's Defense stat as normal.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Spiky Shield">
Type: Grass
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: +4
Target: Self
Flags: none (noassist, failcopycat — cannot be called by Assist or Copycat)

Mechanics:
- Priority +4: moves very early in the turn order.
- Protects the user from all moves targeting it for that turn (like Protect).
- If a contact move hits through Spiky Shield (or attacker makes contact), the attacker loses 1/8 of its max HP.
- stallingMove: fails 50% after 1 consecutive use; always fails after 2 consecutive uses.
- Does not make contact.

AI Scoring: Follows Protect group scoring (same as Protect/King's Shield).
- Base: +6.
- −2 if AI has a chip-damage status (Poison, Burn, Curse, Leech Seed, Yawn, Infatuation, Perish Song).
- +1 if player has one of the above statuses.
- −1 if AI's first turn out and not in doubles.
- AI will not use Protect if it would die to residual damage afterwards.
- 50% chance to skip if used last turn; always skips if used the last 2 turns.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Hyper Voice">
Type: Normal
Category: Special
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: All Adjacent Foes
Flags: sound, bypasssub

Mechanics:
- Deals 90 BP Normal-type Special damage to all adjacent foes.
- Spread move: ×0.75 damage modifier in doubles (vs. each foe).
- Sound flag: blocked by Soundproof ability; bypasses Substitute.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Psyshock">
Type: Psychic
Category: Special
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 80 BP Psychic-type Special damage.
- Uses the TARGET's Defense stat (not Special Defense) for damage calculation, while the user's Special Attack is still used as the offensive stat.
- Stat stage changes to the target's Defense apply.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Thunder Wave">
Type: Electric
Category: Status
Base Power: —
Accuracy: 90
PP: 20
Priority: 0
Target: Normal
Flags: reflectable

Mechanics:
- Inflicts paralysis on the target.
- 90% base accuracy.
- Electric type: Ground-type Pokémon and Pokémon with Lightning Rod/Motor Drive/Volt Absorb are immune.
- ignoreImmunity: false — type immunities apply (Ground types cannot be paralyzed by Thunder Wave).
- Reflectable: reversed by Magic Coat/Magic Bounce.
- Does not make contact.

R&B Changes: When the user is an Electric-type Pokémon, Thunder Wave never misses (accuracy becomes effectively 100%). Ground-type immunity still applies.

AI Scoring: Paralysis group (Thunder Wave, Stun Spore, Glare, Nuzzle, Zap Cannon).
- If player mon is faster than AI but would be slower after paralysis, OR AI has Hex or a flinch move, OR player is infatuated/confused: +8.
- Otherwise: +7.
- Additional −1 applied ~50% of the time regardless.
</Element>

<Element name="Rain Dance">
Type: Water
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: 0
Target: All (field-wide)
Flags: none

Mechanics:
- Sets rain weather for 5 turns (8 turns if user holds Damp Rock).
- Rain effects:
  - Water-type moves deal ×1.5 damage.
  - Fire-type moves deal ×0.5 damage.
  - Thunder and Hurricane hit with 100% accuracy.
  - Solar Beam/Solar Blade: BP halved (charge turn still required).
  - Synthesis/Morning Sun/Moonlight: heal only 1/4 max HP.
  - Swift Swim doubles Speed; Rain Dish heals 1/16 HP/turn; Hydration cures status each turn; Dry Skin heals 1/8 HP/turn.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Precipice Blades">
Type: Ground
Category: Physical
Base Power: 120
Accuracy: 85
PP: 10
Priority: 0
Target: All Adjacent Foes
Flags: none

Mechanics:
- Deals 120 BP Ground-type Physical damage to all adjacent foes.
- Spread move: ×0.75 damage modifier in doubles (vs. each foe).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Wood Hammer">
Type: Grass
Category: Physical
Base Power: 120
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 120 BP Grass-type Physical damage.
- Recoil: user takes 1/3 of damage dealt as recoil.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Grass Pledge">
Type: Grass
Category: Special
Base Power: 80 (standalone) / 150 (combined)
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: pledgecombo

Mechanics:
- Standalone: deals 80 BP Grass-type Special damage.
- Combo mechanics (doubles only — ally must use a compatible Pledge move same turn):
  - Grass + Water Pledge: combined move deals 150 BP Grass-type damage; creates "Swamp" (Grass Pledge condition) on the opponent's side for 4 turns, reducing all opponent Pokémon's Speed to 25% of their normal Speed.
  - Grass + Fire Pledge: combined move deals 150 BP Fire-type damage; creates "Sea of Fire" (Fire Pledge condition) on the opponent's side for 4 turns, dealing 1/8 max HP damage per turn to all non-Fire-type Pokémon on that side.
- In singles: can only be used standalone (no ally to combine with).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Power Whip">
Type: Grass
Category: Physical
Base Power: 120
Accuracy: 90 (85% → 90% in R&B)
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 120 BP Grass-type Physical damage.
- Makes contact.

R&B Changes: Accuracy increased from 85% to 90%.
</Element>

<Element name="Icicle Spear">
Type: Ice
Category: Physical
Base Power: 25 per hit
Accuracy: 100
PP: 30
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Hits 2–5 times in a single turn. Each hit deals 25 BP Ice-type Physical damage.
- Hit distribution: 2 hits (35.5%), 3 hits (35.5%), 4 hits (14.5%), 5 hits (14.5%).
- Each hit is calculated independently for critical hits and ability triggers.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Grav Apple">
Type: Grass
Category: Physical
Base Power: 80 (120 in Gravity)
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 80 BP Grass-type Physical damage.
- If Gravity is active on the field: BP is boosted ×1.5 to 120.
- 100% chance to lower the target's Defense by 1 stage.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sky Uppercut">
Type: Fighting
Category: Physical
Base Power: 85
Accuracy: 100 (90% → 100% in R&B)
PP: 15
Priority: 0
Target: Normal
Flags: contact, punch

Mechanics:
- Deals 85 BP Fighting-type Physical damage.
- Punch flag: boosted by Iron Fist ability.
- Makes contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Substitute">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Self
Flags: snatch

Mechanics:
- User spends 1/4 of its max HP to create a Substitute with HP equal to that same 1/4.
- Fails if the user already has a Substitute, or if the user's current HP ≤ 1/4 of max HP (would faint from cost), or if max HP = 1 (Shedinja clause).
- While active, the Substitute absorbs damage from incoming moves (protecting the user). When Substitute HP reaches 0, it breaks.
- Most status moves and moves without the bypasssub flag are blocked by Substitute.
- snatch: can be stolen by Snatch (though rare use case).
- Does not make contact.

AI Scoring:
- Starts at +6.
- If player mon is asleep: +2.
- If player mon is Leech Seeded and AI is faster: +2.
- Additional −1 applied ~50% of the time.
- If player has any sound-based move: −8.
- If AI is at ≤50% HP, or player has Infiltrator: never used (score −20).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fire Punch">
Type: Fire
Category: Physical
Base Power: 75
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact, punch

Mechanics:
- Deals 75 BP Fire-type Physical damage.
- 10% chance to burn the target.
- Punch flag: boosted by Iron Fist ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Shadow Claw">
Type: Ghost
Category: Physical
Base Power: 70
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 70 BP Ghost-type Physical damage.
- High critical hit ratio (critRatio 2 — 1/8 crit chance).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Psychic">
Type: Psychic
Category: Special
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 90 BP Psychic-type Special damage.
- 10% chance to lower the target's Special Defense by 1 stage.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Swords Dance">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Self
Flags: snatch, dance

Mechanics:
- Raises user's Attack by 2 stages.
- dance flag: triggers Dancer ability on allies.
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

AI Scoring: Offensive Setup group (Dragon Dance, Shift Gear, Swords Dance, Howl, etc.).
- Starts at +6.
- If the opposing Pokémon is incapacitated (frozen, asleep, recharging, Truant loafing): +3.
- If AI is slower and is 2HKO'd by the opponent: −5.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Future Sight">
Type: Psychic
Category: Special
Base Power: 120
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: futuremove

Mechanics:
- Delayed attack: sets up a hit that lands 2 turns later on the target's current slot (not on the specific Pokémon).
- The setup always succeeds (ignores type immunity checks during setup).
- When the delayed hit lands 2 turns later: uses the original user's Special Attack stat and the current occupant's Special Defense stat at time of hit. The hit bypasses screens (Reflect/Light Screen) and Substitutes.
- The stored hit targets the slot, so if the original target switches out, the new Pokémon in that slot takes the hit instead.
- Type effectiveness applies normally on the hit; the Psychic type can be resisted/nullified by Dark, Psychic, and Steel types.
- Does not make contact.

AI Scoring:
- If AI is faster than the target and is KO'd by the target: +8.
- Otherwise: +6.
- Stacks with standard kill bonuses from the "All damaging moves" section.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Grass Knot">
Type: Grass
Category: Special
Base Power: Varies by target weight
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- BP is determined by the target's weight in kg:
  - < 10 kg: 20 BP
  - 10–24.9 kg: 40 BP
  - 25–49.9 kg: 60 BP
  - 50–99.9 kg: 80 BP
  - 100–199.9 kg: 100 BP
  - ≥ 200 kg: 120 BP
- Autotomize halves the target's effective weight for this calculation.
- Fails against Dynamax targets.
- Makes contact (despite being a Special move).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Scale Shot">
Type: Dragon
Category: Physical
Base Power: 25 per hit
Accuracy: 100 (90% → 100% in R&B)
PP: 20
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Hits 2–5 times in a single turn. Each hit deals 25 BP Dragon-type Physical damage.
- Hit distribution: 2 hits (35.5%), 3 hits (35.5%), 4 hits (14.5%), 5 hits (14.5%).
- After all hits: user's Defense drops by 1 stage and Speed rises by 1 stage (selfBoost).
- Does not make contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Steel Beam">
Type: Steel
Category: Special
Base Power: 140
Accuracy: 100 (95% → 100% in R&B)
PP: 5
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 140 BP Steel-type Special damage.
- User takes 1/2 of its max HP as recoil after use (mind-blown style recoil — triggers regardless of hit/miss).
- If the user's HP crosses below 50% due to recoil, Emergency Exit/Wimp Out ability triggers.
- Does not make contact.

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Bug Bite">
Type: Bug
Category: Physical
Base Power: 60
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 60 BP Bug-type Physical damage.
- If the target is holding a Berry: the user steals and consumes it. The Berry's effect activates for the user (not the original holder).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Hidden Power Fire">
Type: Fire
Category: Special
Base Power: 60
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: none

Mechanics:
- A typed variant of Hidden Power (type determined by user's IV combination).
- "Hidden Power Fire" specifically means the user's IVs give the Fire type.
- Always 60 BP regardless of IVs.
- In R&B, Hidden Power is re-added to gen 8 (it was removed in vanilla gen 8). Type is determined by IVs, always 60 BP.
- Does not make contact.

R&B Changes: Hidden Power restored from gen 7 (not available in vanilla gen 8). Type = Fire (determined by IVs). 60 BP.
</Element>

<Element name="Magnet Rise">
Type: Electric
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Self
Flags: snatch, gravity

Mechanics:
- User gains the "Magnet Rise" volatile for 5 turns, granting immunity to Ground-type moves.
- Fails if the user has the Smack Down or Ingrain volatile (already grounded by those effects).
- gravity flag: fails if Gravity is in effect on the field.
- snatch: can be stolen by a foe using Snatch.
- The immunity is overridden by Iron Ball, Gravity, or Smack Down during the duration.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Dark Pulse">
Type: Dark
Category: Special
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: Any (any Pokémon on the field)
Flags: pulse, distance

Mechanics:
- Deals 80 BP Dark-type Special damage.
- 20% chance to cause the target to flinch.
- Pulse flag: boosted ×1.5 by Mega Launcher ability.
- distance flag: can target any slot in doubles (not limited to adjacent).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Smack Down">
Type: Rock
Category: Physical
Base Power: 50
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 50 BP Rock-type Physical damage.
- If the target is in a non-grounded state (Flying type, Levitate, Magnet Rise, Telekinesis, or mid-Fly/Bounce), it grounds them and removes those levitation effects.
- The "smackdown" volatile makes the target grounded for the remainder of the battle (or until it switches out), removing Ground immunity from Flying types and Levitate.
- If the target is already grounded with no levitation effects, the volatile still deals damage but has no grounding effect.
- Also interrupts a Fly or Bounce in progress (cancels the move, forces the target down immediately).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Grassy Glide">
Type: Grass
Category: Physical
Base Power: 55
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 55 BP Grass-type Physical damage.
- Priority increases to +1 (moves first among normal-priority moves) when Grassy Terrain is active and the user is grounded.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Grass Whistle">
Type: Grass
Category: Status
Base Power: —
Accuracy: 70 (55% → 70% in R&B)
PP: 15
Priority: 0
Target: Normal
Flags: sound, bypasssub, reflectable

Mechanics:
- Inflicts Sleep on the target.
- Sound flag: blocked by Soundproof ability; bypasses Substitute.
- bypasssub: explicitly bypasses Substitute.
- Reflectable: reversed by Magic Coat/Magic Bounce.
- Does not make contact.

AI Scoring: Non-damaging sleep move group.
- Starts at +6. Conditional +1s based on context (see Sleep Powder entry for details).

R&B Changes: Accuracy increased from 55% to 70%.
</Element>

<Element name="Scorching Sands">
Type: Ground
Category: Special
Base Power: 70
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: defrost

Mechanics:
- Deals 70 BP Ground-type Special damage.
- defrost flag: thaws a frozen target before dealing damage (removes Frozen status).
- 30% chance to burn the target. If the target was just thawed, the burn can apply since the Frozen status is gone.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Spikes">
Type: Normal (hazard, not typed for damage)
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Foe's Side
Flags: reflectable, mustpressure

Mechanics:
- Lays a layer of Spikes on the opponent's side of the field (max 3 layers).
- When a grounded foe switches in, they take damage based on layers:
  - 1 layer: 1/8 max HP
  - 2 layers: 1/6 max HP
  - 3 layers: 1/4 max HP
- Flying-type Pokémon and those with Levitate/Magic Guard/Heavy Duty Boots are unaffected.
- Reflectable: reversed by Magic Coat/Magic Bounce (places Spikes on the user's side instead).

AI Scoring:
- First turn out: +8 (25%) or +9 (75%).
- Otherwise: +6 (25%) or +7 (75%).
- −1 always if at least 1 layer of Spikes is already up on the opponent's side.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fusion Flare">
Type: Fire
Category: Special
Base Power: 100 (200 if Fusion Bolt used this turn)
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: defrost

Mechanics:
- Deals 100 BP Fire-type Special damage.
- If Fusion Bolt was the last successful move used this turn (by the user or an ally): BP doubles to 200.
- defrost flag: thaws a frozen target before dealing damage.
- Does not make contact.
- Pair move with Fusion Bolt: in doubles, if the ally uses Fusion Bolt, then this move hits for 200 BP (and vice versa for Fusion Bolt if Fusion Flare goes first).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Calm Mind">
Type: Psychic
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Self
Flags: snatch

Mechanics:
- Raises user's Special Attack and Special Defense each by 1 stage.
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

AI Scoring: Coil/Bulk Up group (conditional Offensive/Defensive).
- Starts at +6.
- Calm Mind boosts special stats: if the opposing Pokémon has a special attacking move and no physical attacking moves → treated as Defensive Setup. Otherwise → treated as Offensive Setup.
- See Offensive/Defensive Setup entries for scoring details.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Disable">
Type: Normal
Category: Status
Base Power: —
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: bypasssub, reflectable

Mechanics:
- Disables the target's last used move for 5 turns. The disabled move cannot be selected or called during this period.
- Fails if: the target has not yet moved this battle, the target's last move is out of PP, or the last move was Struggle or a Z/Max move.
- bypasssub: bypasses Substitute.
- Reflectable: reversed by Magic Coat/Magic Bounce.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Block">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: 0
Target: Normal
Flags: reflectable

Mechanics:
- Prevents the target from switching out or fleeing (traps the target).
- The trap persists until the user leaves the field (switches out or faints).
- Ghost-type targets can escape trapping regardless.
- Reflectable: reversed by Magic Coat/Magic Bounce.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Tackle">
Type: Normal
Category: Physical
Base Power: 40
Accuracy: 100
PP: 35
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 40 BP Normal-type Physical damage.
- Makes contact.
- No additional effects.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Brave Bird">
Type: Flying
Category: Physical
Base Power: 120
Accuracy: 100
PP: 15
Priority: 0
Target: Any
Flags: contact, distance

Mechanics:
- Deals 120 BP Flying-type Physical damage.
- User takes recoil damage equal to 1/3 of the damage dealt.
- distance flag: can target any Pokémon on the field in doubles (including ally or far foe).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Aqua Tail">
Type: Water
Category: Physical
Base Power: 90
Accuracy: 95
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 90 BP Water-type Physical damage.
- Makes contact.
- No additional effects.

R&B Changes: Accuracy increased from 90% to 95%.
</Element>

<Element name="Acupressure">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 30
Priority: 0
Target: Self or Adjacent Ally

Mechanics:
- Randomly selects one stat among Attack, Defense, Special Attack, Special Defense, Speed, Accuracy, Evasion that is not already at +6, and raises it by +2 stages.
- Can target the user or an adjacent ally.
- Fails if all applicable stats for the target are already at +6.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Double Kick">
Type: Fighting
Category: Physical
Base Power: 30
Accuracy: 100
PP: 30
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 30 BP Fighting-type Physical damage, hitting exactly 2 times.
- Each hit is calculated independently for damage, critical hits, and secondary effects.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Lava Plume">
Type: Fire
Category: Special
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: All Adjacent
Flags: none

Mechanics:
- Deals 80 BP Fire-type Special damage to all adjacent Pokémon (both foes and ally in doubles).
- 30% chance to inflict burn on each target hit.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Crunch">
Type: Dark
Category: Physical
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact, bite

Mechanics:
- Deals 80 BP Dark-type Physical damage.
- bite flag: boosted by Strong Jaw ability.
- 20% chance to lower the target's Defense by 1 stage.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Charge Beam">
Type: Electric
Category: Special
Base Power: 40
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 40 BP Electric-type Special damage.
- 100% chance to raise the user's Special Attack by 1 stage after dealing damage.
- Does not make contact.

R&B Changes: Base Power reduced from 50 to 40. Accuracy increased from 90% to 100%. Effect chance increased from 70% to 100% (always raises Special Attack).
</Element>

<Element name="Dream Eater">
Type: Psychic
Category: Special
Base Power: 100
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: heal

Mechanics:
- Deals 100 BP Psychic-type Special damage.
- Only works if the target is asleep (or has the Comatose ability); otherwise fails.
- Heals the user for 50% of the damage dealt (drain).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Eruption">
Type: Fire
Category: Special
Base Power: 150 × (user HP / user max HP)
Accuracy: 100
PP: 5
Priority: 0
Target: All Adjacent Foes
Flags: none

Mechanics:
- Deals Fire-type Special damage to all adjacent foes.
- Base Power = 150 × (current HP / max HP). At full HP: 150 BP. As the user takes damage, BP decreases proportionally (e.g. at 50% HP = 75 BP, at 1 HP ≈ 1 BP minimum).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Ice Punch">
Type: Ice
Category: Physical
Base Power: 75
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact, punch

Mechanics:
- Deals 75 BP Ice-type Physical damage.
- punch flag: boosted by Iron Fist ability.
- 10% chance to freeze the target.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Revenge">
Type: Fighting
Category: Physical
Base Power: 60 (120 if damaged by the target this turn)
Accuracy: 100
PP: 10
Priority: -4
Target: Normal
Flags: contact

Mechanics:
- Deals 60 BP Fighting-type Physical damage.
- If the user was damaged by the target during the current turn (before this move executes), BP doubles to 120.
- Priority −4: acts very late in the turn order.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Belly Drum">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Self
Flags: snatch

Mechanics:
- The user sacrifices 50% of its max HP to maximize its Attack stat (sets Attack to +6 regardless of current boost level).
- Fails if the user's current HP is ≤ 50% of max HP, if Attack is already at +6, or if max HP = 1 (Shedinja clause).
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

AI Scoring:
- +9 if the opposing Pokémon is incapacitated (frozen, asleep, or recharging).
- +8 if the opposing Pokémon cannot KO the AI after a Belly Drum (accounting for Sitrus Berry).
- +4 otherwise.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Screech">
Type: Normal
Category: Status
Base Power: —
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: sound, bypasssub, reflectable

Mechanics:
- Lowers the target's Defense by 2 stages.
- sound flag: bypasses Substitute; blocked by Soundproof.
- bypasssub: hits through Substitute.
- Reflectable: reversed by Magic Coat/Magic Bounce.
- Does not make contact.

R&B Changes: PP reduced from 15 to 5. Accuracy increased from 85% to 100%.
</Element>

<Element name="Light Of Ruin">
Type: Fairy
Category: Special
Base Power: 140
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 140 BP Fairy-type Special damage.
- User takes recoil damage equal to 1/2 of the damage dealt.
- Does not make contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Transform">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: Normal
Flags: failencore, failcopycat, failmimic, failinstruct

Mechanics:
- The user transforms into the target, copying its current stat stages, type(s), ability, and moves (each with 5 PP). The user's HP does not change.
- Cannot be called by Encore, Copycat, Mimic, or Instruct.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Double Hit">
Type: Normal
Category: Physical
Base Power: 35
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 35 BP Normal-type Physical damage, hitting exactly 2 times.
- Each hit is calculated independently.
- Makes contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Dragon Darts">
Type: Dragon
Category: Physical
Base Power: 50
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: noparentalbond, smartTarget

Mechanics:
- Deals 50 BP Dragon-type Physical damage, hitting exactly 2 times.
- smartTarget: in doubles, if two foes are present, each dart targets a different foe; if only one foe is present, both darts hit that foe.
- noparentalbond: Parental Bond does not add an extra hit.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Take Down">
Type: Normal
Category: Physical
Base Power: 90
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 90 BP Normal-type Physical damage.
- User takes recoil damage equal to 1/4 of the damage dealt.
- Makes contact.

R&B Changes: Accuracy increased from 85% to 100%.
</Element>

<Element name="Spore">
Type: Grass
Category: Status
Base Power: —
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: powder, reflectable

Mechanics:
- Inflicts sleep on the target.
- powder flag: blocked by Grass-type Pokémon, Overcoat ability, and Safety Goggles item.
- Reflectable: reversed by Magic Coat/Magic Bounce.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Aerial Ace">
Type: Flying
Category: Physical
Base Power: 60
Accuracy: —
PP: 20
Priority: 0
Target: Any
Flags: contact, slicing, distance

Mechanics:
- Deals 60 BP Flying-type Physical damage.
- Never misses (bypasses accuracy checks).
- slicing flag: boosted by Sharpness ability.
- distance flag: can target any Pokémon on the field in doubles.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Follow Me">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: +2
Target: Self
Flags: failcopycat

Mechanics:
- The user becomes the center of attention for this turn, redirecting all single-target moves from foes to itself.
- Only works in doubles/multi battles (fails in singles).
- Priority +2: acts early in the turn to redirect before foes attack.
- Does not make contact.

AI Scoring: +6. AI will not use if partner is also using Follow Me/Helping Hand, or if partner is using a Status move.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Hail">
Type: Ice
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: 0
Target: All (field-wide)
Flags: none

Mechanics:
- Sets Hail weather for 5 turns (8 turns if the user holds an Icy Rock).
- During Hail: damages all non-Ice-type Pokémon by 1/16 of their max HP at the end of each turn.
- During Hail: Blizzard's accuracy becomes 100%. Certain Ice-type moves gain additional effects.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Petal Dance">
Type: Grass
Category: Special
Base Power: 120
Accuracy: 100
PP: 10
Priority: 0
Target: Random Foe
Flags: contact, dance, failinstruct

Mechanics:
- Deals 120 BP Grass-type Special damage to a randomly selected foe.
- Locks the user into using Petal Dance for 2-3 turns (lockedmove). After the rampage ends, the user becomes confused.
- Confusion can be avoided if the move runs out of PP or is cancelled.
- dance flag: can trigger the Dancer ability on allies.
- failinstruct: cannot be called by Instruct.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Night Shade">
Type: Ghost
Category: Special
Base Power: — (level-based)
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals fixed damage equal to the user's level, regardless of stats, type matchups, or modifiers.
- Ignores type effectiveness and stat stages.
- Does not affect Normal-type Pokémon (Ghost immunity applies).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Meteor Assault">
Type: Fighting
Category: Physical
Base Power: 150
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: recharge, failinstruct

Mechanics:
- Deals 150 BP Fighting-type Physical damage.
- After attacking, the user must spend the next turn recharging and cannot act.
- recharge flag: user gains mustrecharge volatile status after use.
- failinstruct: cannot be called by Instruct.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Destiny Bond">
Type: Ghost
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: 0
Target: Self
Flags: bypasssub, failcopycat

Mechanics:
- The user sets a Destiny Bond volatile. If the user then faints from a direct attack by the target before the user's next turn, the attacker also faints.
- The volatile is removed when the user selects a different move or takes any other action.
- Does not affect Dynamax Pokémon (they are immune).
- Does not make contact.

AI Scoring:
- If AI is faster and dies to the player's Pokémon: +7 (~81%), +6 (~19%).
- If AI is slower: +5 (50%), +6 (50%).

R&B Changes: Can be used multiple times consecutively without failing (vanilla gen 8 fails if used back-to-back).
</Element>

<Element name="Multi Attack">
Type: Normal (changes to match held Memory)
Category: Physical
Base Power: 120
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 120 BP Physical damage.
- Type matches the Memory item held by the user (e.g. Fire Memory → Fire-type). Defaults to Normal if no Memory is held or item is suppressed.
- Silvally's signature move.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Bonemerang">
Type: Ground
Category: Physical
Base Power: 50
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 50 BP Ground-type Physical damage, hitting exactly 2 times.
- Each hit is calculated independently.
- Does not make contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Tail Glow">
Type: Bug
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Self
Flags: snatch

Mechanics:
- Raises the user's Special Attack by 3 stages.
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

AI Scoring: Offensive Setup (Tail Glow / Nasty Plot / Work Up group).
- Starts at +6.
- +3 additional if the opposing Pokémon is incapacitated (frozen without a thawing move, asleep, recharging, or Truant loafing).
- +1 additional if opponent cannot 3HKO the AI; +1 more if AI is faster.
- −5 if AI is slower and is 2HKO'd by the opposing Pokémon.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Solar Beam">
Type: Grass
Category: Special
Base Power: 120 (60 in non-Sun weather)
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: charge, nosleeptalk, failinstruct

Mechanics:
- Two-turn move: on the first turn the user charges (absorbs sunlight); on the second turn it fires for 120 BP Grass-type Special damage.
- In Sunny Day or Desolate Land: skips the charge turn and fires immediately.
- In rain, sandstorm, or hail: BP is halved to 60.
- nosleeptalk: cannot be called by Sleep Talk during the charge turn.
- failinstruct: cannot be called by Instruct.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sacred Fire">
Type: Fire
Category: Physical
Base Power: 100
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: defrost

Mechanics:
- Deals 100 BP Fire-type Physical damage.
- defrost flag: thaws a frozen target before dealing damage.
- 50% chance to inflict burn on the target.
- Does not make contact.

R&B Changes: Accuracy increased from 95% to 100%.
</Element>

<Element name="Darkest Lariat">
Type: Dark
Category: Physical
Base Power: 85
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 85 BP Dark-type Physical damage.
- Ignores the target's Defense and Special Defense stat boosts (but not drops).
- Ignores the target's Evasion boosts.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Night Slash">
Type: Dark
Category: Physical
Base Power: 70
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact, slicing

Mechanics:
- Deals 70 BP Dark-type Physical damage.
- High critical hit ratio (critRatio 2; ~12.5% chance).
- slicing flag: boosted by Sharpness ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Iron Tail">
Type: Steel
Category: Physical
Base Power: 100
Accuracy: 85
PP: 15
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 100 BP Steel-type Physical damage.
- 30% chance to lower the target's Defense by 1 stage.
- Makes contact.

R&B Changes: Accuracy increased from 75% to 85%.
</Element>

<Element name="Drill Peck">
Type: Flying
Category: Physical
Base Power: 80
Accuracy: 100
PP: 20
Priority: 0
Target: Any
Flags: contact, distance

Mechanics:
- Deals 80 BP Flying-type Physical damage.
- distance flag: can target any Pokémon on the field in doubles.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Stone Edge">
Type: Rock
Category: Physical
Base Power: 100
Accuracy: 85
PP: 5
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 100 BP Rock-type Physical damage.
- High critical hit ratio (critRatio 2; ~12.5% chance).
- Does not make contact.

R&B Changes: Accuracy increased from 80% to 85%.
</Element>

<Element name="Reflect">
Type: Psychic
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Ally Side
Flags: snatch

Mechanics:
- Sets the Reflect screen on the user's side of the field for 5 turns (8 turns if the user holds Light Clay).
- Halves Physical damage taken by Pokémon on the user's side: ×0.5 in singles, ×0.667 (approx.) in doubles.
- Critical hits bypass Reflect.
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

AI Scoring: +6 base. +1 if the opposing Pokémon has a physical move (relevant for Reflect) and AI holds Light Clay. +1 additional 50% of the time under the same condition.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Heat Crash">
Type: Fire
Category: Physical
Base Power: Weight-based
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact, minimize

Mechanics:
- Deals Fire-type Physical damage. BP is determined by the ratio of the user's weight to the target's weight:
  - User ≥ 5× target weight: 120 BP
  - User ≥ 4× target weight: 100 BP
  - User ≥ 3× target weight: 80 BP
  - User ≥ 2× target weight: 60 BP
  - Otherwise: 40 BP
- minimize flag: deals double damage against a Minimized target.
- Fails against Dynamax Pokémon.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Aqua Jet">
Type: Water
Category: Physical
Base Power: 40
Accuracy: 100
PP: 20
Priority: +1
Target: Normal
Flags: contact

Mechanics:
- Deals 40 BP Water-type Physical damage.
- Priority +1: strikes before normal-priority moves.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Quiver Dance">
Type: Bug
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Self
Flags: snatch, dance

Mechanics:
- Raises the user's Special Attack, Special Defense, and Speed each by 1 stage.
- snatch: can be stolen by a foe using Snatch.
- dance flag: can trigger the Dancer ability on allies.
- Does not make contact.

AI Scoring: Coil/Bulk Up/Calm Mind/Quiver Dance group (conditional Offensive/Defensive).
- Starts at +6.
- If the opposing Pokémon has a special attacking move and no physical attacking moves → treated as Defensive Setup.
- Otherwise → treated as Offensive Setup.
- See Offensive/Defensive Setup entries for scoring details.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Surging Strikes">
Type: Water
Category: Physical
Base Power: 25
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: contact, punch

Mechanics:
- Deals 25 BP Water-type Physical damage, hitting exactly 3 times.
- Each hit always lands a critical hit (willCrit).
- punch flag: boosted by Iron Fist ability.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Pain Split">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Normal
Flags: none

Mechanics:
- The user and target's HP are each set to the average of their combined HP: floor((userHP + targetHP) / 2), minimum 1.
- Effectively transfers HP from the higher-HP side to the lower-HP side.
- Never misses.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Magical Leaf">
Type: Grass
Category: Special
Base Power: 60
Accuracy: —
PP: 20
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 60 BP Grass-type Special damage.
- Never misses (bypasses accuracy checks).
- No additional effects.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Acrobatics">
Type: Flying
Category: Physical
Base Power: 55 (110 if user holds no item)
Accuracy: 100
PP: 15
Priority: 0
Target: Any
Flags: contact, distance

Mechanics:
- Deals 55 BP Flying-type Physical damage. If the user is not holding any item, BP doubles to 110.
- distance flag: can target any Pokémon on the field in doubles.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Outrage">
Type: Dragon
Category: Physical
Base Power: 120
Accuracy: 100
PP: 10
Priority: 0
Target: Random Foe
Flags: contact, failinstruct

Mechanics:
- Deals 120 BP Dragon-type Physical damage to a randomly selected foe.
- Locks the user into using Outrage for 2-3 turns (lockedmove). After the rampage ends, the user becomes confused.
- Confusion can be avoided if the move runs out of PP or is cancelled.
- failinstruct: cannot be called by Instruct.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Nuzzle">
Type: Electric
Category: Physical
Base Power: 20
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 20 BP Electric-type Physical damage.
- 100% chance to inflict paralysis on the target.
- Makes contact.

AI Scoring: Paralysis group (Thunder Wave / Stun Spore / Glare / Nuzzle / Zap Cannon).
- +8 if: the player's Pokémon is faster than the AI but slower than the AI after paralysis (1/4 speed), or the AI has Hex or a flinching move, or the player is infatuated/confused.
- +7 otherwise.
- Additional −1 applied 50% of the time.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Octazooka">
Type: Water
Category: Special
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: bullet

Mechanics:
- Deals 80 BP Water-type Special damage.
- 30% chance to lower the target's Accuracy by 1 stage.
- bullet flag: blocked by Bulletproof ability.
- Does not make contact.

R&B Changes: Base Power increased from 65 to 80. Accuracy increased from 85% to 100%. Effect chance reduced from 50% to 30%.
</Element>

<Element name="Soft Boiled">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: 0
Target: Self
Flags: snatch, heal

Mechanics:
- Heals the user for 50% of its max HP.
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

AI Scoring: Recovery group (Recover / Slack Off / Heal Order / Soft-Boiled / Roost / Strength Sap).
- +7 if the AI decides it should recover.
- +5 otherwise.
- −20 if at full HP; −6 if at 85% HP or higher.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Silver Wind">
Type: Bug
Category: Special
Base Power: 60
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 60 BP Bug-type Special damage.
- 10% chance to raise all of the user's stats (+1 Attack, +1 Defense, +1 Special Attack, +1 Special Defense, +1 Speed).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Dragon Rage">
Type: Dragon
Category: Special
Base Power: — (fixed 40 damage)
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Always deals exactly 40 HP of damage to the target, ignoring all stats, type effectiveness, and modifiers.
- Does not affect Dragon-immune targets (Normal-type is not immune, but Fairy-type is).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Scary Face">
Type: Normal
Category: Status
Base Power: —
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: reflectable

Mechanics:
- Lowers the target's Speed by 2 stages.
- Reflectable: reversed by Magic Coat/Magic Bounce.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Moonblast">
Type: Fairy
Category: Special
Base Power: 95
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 95 BP Fairy-type Special damage.
- 30% chance to lower the target's Special Attack by 1 stage.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Swift">
Type: Normal
Category: Special
Base Power: 60
Accuracy: —
PP: 20
Priority: 0
Target: All Adjacent Foes
Flags: none

Mechanics:
- Deals 60 BP Normal-type Special damage to all adjacent foes.
- Never misses (bypasses accuracy checks).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sludge Bomb">
Type: Poison
Category: Special
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: bullet

Mechanics:
- Deals 90 BP Poison-type Special damage.
- bullet flag: blocked by Bulletproof ability.
- 30% chance to inflict poison on the target.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Wing Attack">
Type: Flying
Category: Physical
Base Power: 60
Accuracy: 100
PP: 35
Priority: 0
Target: Any
Flags: contact, distance

Mechanics:
- Deals 60 BP Flying-type Physical damage.
- distance flag: can target any Pokémon on the field in doubles.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fiery Dance">
Type: Fire
Category: Special
Base Power: 80
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: dance

Mechanics:
- Deals 80 BP Fire-type Special damage.
- 50% chance to raise the user's Special Attack by 1 stage.
- dance flag: can trigger the Dancer ability on allies.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Aura Wheel">
Type: Electric (Full Belly Morpeko) / Dark (Hangry Morpeko)
Category: Physical
Base Power: 110
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 110 BP Physical damage. Type is Electric if the user is Morpeko (Full Belly form) or Dark if the user is Morpeko-Hangry.
- 100% chance to raise the user's Speed by 1 stage after dealing damage.
- Only usable by Morpeko (any form); fails otherwise.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Horn Leech">
Type: Grass
Category: Physical
Base Power: 75
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact, heal

Mechanics:
- Deals 75 BP Grass-type Physical damage.
- Heals the user for 50% of the damage dealt (drain).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Smart Strike">
Type: Steel
Category: Physical
Base Power: 70
Accuracy: —
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 70 BP Steel-type Physical damage.
- Never misses (bypasses accuracy checks).
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Barrier">
Type: Psychic
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Self
Flags: snatch

Mechanics:
- Raises the user's Defense by 2 stages.
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

AI Scoring: Defensive Setup group (Acid Armor / Barrier / Cotton Guard / Harden / Iron Defense / Stockpile / Cosmic Power).
- Starts at +6.
- −5 if AI is slower and is 2HKO'd by the opposing Pokémon.
- ~95% of the time: +2 additional if opponent is incapacitated; +2 additional if the move boosts both Def and SpDef and AI is below +2 in either.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="First Impression">
Type: Bug
Category: Physical
Base Power: 90
Accuracy: 100
PP: 10
Priority: +2
Target: Normal
Flags: contact

Mechanics:
- Deals 90 BP Bug-type Physical damage.
- Priority +2: strikes very early in the turn.
- Only works on the user's first action after being sent out; fails if the user has already used a move this battle switch-in.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Dark Void">
Type: Dark
Category: Status
Base Power: —
Accuracy: 80
PP: 10
Priority: 0
Target: All Adjacent Foes
Flags: reflectable

Mechanics:
- Inflicts sleep on all adjacent foes (both foes in doubles).
- Reflectable: reversed by Magic Coat/Magic Bounce.
- Does not make contact.

AI Scoring: Non-damaging sleep move group (Yawn / Dark Void / Grass Whistle / Sing / etc.).
- Starts at +6.
- 25% of the time: +1 if target can be put to sleep; +1 more if AI has Dream Eater/Nightmare and target lacks Snore/Sleep Talk; +1 more if AI/partner has Hex.
- 75% of the time: no additional bonuses (+6 flat).

R&B Changes: Accuracy increased from 50% to 80%. Can now be used by any Pokémon that can learn it (not just Darkrai).
</Element>

<Element name="V Create">
Type: Fire
Category: Physical
Base Power: 180
Accuracy: 95
PP: 5
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 180 BP Fire-type Physical damage.
- After use: the user's Speed, Defense, and Special Defense each drop by 1 stage.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Soak">
Type: Water
Category: Status
Base Power: —
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: reflectable

Mechanics:
- Changes the target's type to pure Water-type, overriding its original type(s).
- Fails if the target is already pure Water-type.
- Reflectable: reversed by Magic Coat/Magic Bounce.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Endure">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 10
Priority: +4
Target: Self
Flags: failcopycat

Mechanics:
- The user braces itself; any hit that would KO it this turn will instead leave 1 HP.
- Priority +4: activates before most other moves.
- stallingMove: consecutive uses have reduced success chance (stall counter mechanic).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Secret Sword">
Type: Fighting
Category: Special
Base Power: 85
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: slicing

Mechanics:
- Deals 85 BP Fighting-type Special damage, but targets the foe's Physical Defense (Defense stat) instead of Special Defense for the damage calculation.
- slicing flag: boosted by Sharpness ability.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Trick">
Type: Normal
Category: Status
Base Power: —
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: failcopycat

Mechanics:
- The user and target swap their held items.
- Fails if the target has Sticky Hold, if both sides have no item, or if neither item can be given away.
- Does not make contact.

AI Scoring:
- +6 or +7 (50/50) if AI holds Toxic Orb, Flame Orb, or Black Sludge.
- +7 if AI holds Iron Ball, Lagging Tail, or Sticky Barb.
- +5 otherwise.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Submission">
Type: Fighting
Category: Physical
Base Power: 80
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 80 BP Fighting-type Physical damage.
- User takes recoil damage equal to 1/4 of the damage dealt.
- Makes contact.

R&B Changes: Accuracy increased from 80% to 100%.
</Element>

<Element name="Earthquake">
Type: Ground
Category: Physical
Base Power: 100
Accuracy: 100
PP: 10
Priority: 0
Target: All Adjacent
Flags: nonsky

Mechanics:
- Deals 100 BP Ground-type Physical damage to all adjacent Pokémon (both foes and ally in doubles).
- nonsky: does not hit Pokémon that are in the air (Fly, Bounce, Sky Drop), but does hit Pokémon using Dig (doubles damage in that case).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Tailwind">
Type: Flying
Category: Status
Base Power: —
Accuracy: —
PP: 15
Priority: 0
Target: Ally Side
Flags: snatch, wind

Mechanics:
- Sets the Tailwind condition on the user's side for 4 turns (6 turns if the user has the Persistent ability).
- During Tailwind: doubles the Speed of all Pokémon on the user's side.
- wind flag: affected by Wind Rider ability.
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

AI Scoring:
- +9 if the AI or its partner are slower than any player Pokémon on the field.
- +5 otherwise.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Belch">
Type: Poison
Category: Special
Base Power: 120
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: failinstruct, nosleeptalk, failcopycat, failmimic

Mechanics:
- Deals 120 BP Poison-type Special damage.
- Can only be used if the user has consumed a Berry at some point during the battle. If no Berry has been consumed, the move is disabled and cannot be selected.
- Does not make contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Tail Slap">
Type: Normal
Category: Physical
Base Power: 25
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 25 BP Normal-type Physical damage, hitting 2–5 times per use.
- Each hit is calculated independently.
- Makes contact.

R&B Changes: Accuracy increased from 85% to 100%.
</Element>

<Element name="Lovely Kiss">
Type: Normal
Category: Status
Base Power: —
Accuracy: 80
PP: 10
Priority: 0
Target: Normal
Flags: reflectable

Mechanics:
- Inflicts sleep on the target.
- Reflectable: reversed by Magic Coat/Magic Bounce.
- Does not make contact.

AI Scoring: Non-damaging sleep move group (same as Yawn / Dark Void / Grass Whistle / Sing).
- Starts at +6.
- 25% of the time: +1 if target can be put to sleep; +1 more if AI has Dream Eater/Nightmare and target lacks Snore/Sleep Talk; +1 more if AI/partner has Hex.
- 75% of the time: no additional bonuses (+6 flat).

R&B Changes: Accuracy increased from 75% to 80%.
</Element>

<Element name="Toxic">
Type: Poison
Category: Status
Base Power: —
Accuracy: 90
PP: 10
Priority: 0
Target: Normal
Flags: reflectable

Mechanics:
- Inflicts badly poisoned (toxic) status on the target. Badly poisoned damage starts at 1/16 max HP and increases by 1/16 each turn.
- Poison-type users never miss with Toxic (bypasses accuracy check).
- Reflectable: reversed by Magic Coat/Magic Bounce.
- Does not make contact.

AI Scoring: Poisoning move group.
- Starts at +6.
- ~38% of the time: +2 additional if player can be poisoned, is above 20% HP, and AI has Hex/Venom Drench/Venoshock or Merciless ability while player has no damaging moves.
- ~62% of the time: no additional bonuses (+6 flat).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Burn Up">
Type: Fire
Category: Special
Base Power: 130
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: defrost

Mechanics:
- Deals 130 BP Fire-type Special damage.
- Only usable by Fire-type Pokémon; fails otherwise.
- After use: removes the Fire type from the user (the Fire type is replaced by ???/typeless, or the Pokémon becomes purely the remaining type if dual-typed).
- defrost flag: thaws a frozen target before dealing damage.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Jump Kick">
Type: Fighting
Category: Physical
Base Power: 100
Accuracy: 95
PP: 10
Priority: 0
Target: Normal
Flags: contact, gravity

Mechanics:
- Deals 100 BP Fighting-type Physical damage.
- If the move misses, the user takes crash damage equal to 50% of its max HP.
- gravity flag: fails if Gravity is active.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Explosion">
Type: Normal
Category: Physical
Base Power: 250
Accuracy: 100
PP: 5
Priority: 0
Target: All Adjacent
Flags: noparentalbond

Mechanics:
- Deals 250 BP Normal-type Physical damage to all adjacent Pokémon (both foes and ally in doubles).
- The user faints after using (selfdestruct).
- noparentalbond: Parental Bond does not add an extra hit.
- Does not make contact.

AI Scoring: Boom move group (Explosion / Self-Destruct / Misty Explosion).
- +10 if AI is below 10% HP.
- +8 (~70%) or +0 (~30%) if below 33% HP.
- +7 (50%) or +0 (50%) if below 66% HP.
- +7 (~5%) or +0 (~95%) otherwise.
- AI will not use if target is immune, or if AI is last mon and player has multiple mons left.
- −1 if both AI and player are on their last Pokémon.

R&B Changes: Halves the target's Defense stat for the damage calculation (restores gen 4 mechanic).
</Element>

<Element name="Flail">
Type: Normal
Category: Physical
Base Power: HP-based (20–200)
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals Normal-type Physical damage. BP scales inversely with the user's remaining HP:
  - ≤~4% HP (ratio < 2): 200 BP
  - ≤~10% HP (ratio < 5): 150 BP
  - ≤~20% HP (ratio < 10): 100 BP
  - ≤~35% HP (ratio < 17): 80 BP
  - ≤~68% HP (ratio < 33): 40 BP
  - Otherwise: 20 BP
  (ratio = floor(HP × 48 / maxHP), min 1)
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Teeter Dance">
Type: Normal
Category: Status
Base Power: —
Accuracy: 100
PP: 20
Priority: 0
Target: All Adjacent
Flags: dance

Mechanics:
- Inflicts confusion on all adjacent Pokémon (both foes and ally in doubles).
- dance flag: can trigger the Dancer ability on allies.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Overheat">
Type: Fire
Category: Special
Base Power: 130
Accuracy: 100
PP: 5
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 130 BP Fire-type Special damage.
- After use: lowers the user's Special Attack by 2 stages.
- Does not make contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Bone Rush">
Type: Ground
Category: Physical
Base Power: 25
Accuracy: 90
PP: 10
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 25 BP Ground-type Physical damage, hitting 2–5 times per use.
- Each hit is calculated independently.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Fissure">
Type: Ground
Category: Physical
Base Power: — (OHKO)
Accuracy: 30
PP: 5
Priority: 0
Target: Normal
Flags: nonsky

Mechanics:
- One-hit KO move: if it hits, the target faints instantly regardless of HP.
- Base accuracy is 30%, modified by level difference: effective accuracy = (user's level − target's level + 30)%. Fails if user's level is lower than the target's.
- nonsky: does not hit airborne Pokémon (Flying-type immune to Ground moves, Levitate, etc.).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Ember">
Type: Fire
Category: Special
Base Power: 40
Accuracy: 100
PP: 25
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 40 BP Fire-type Special damage.
- 10% chance to inflict burn on the target.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Spirit Break">
Type: Fairy
Category: Physical
Base Power: 75
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: contact

Mechanics:
- Deals 75 BP Fairy-type Physical damage.
- 100% chance to lower the target's Special Attack by 1 stage.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sonic Boom">
Type: Normal
Category: Special
Base Power: — (fixed 20 damage)
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Always deals exactly 20 HP of damage to the target, ignoring all stats, type effectiveness, and modifiers.
- Does not make contact.

R&B Changes: Accuracy increased from 90% to 100%.
</Element>

<Element name="Morning Sun">
Type: Normal
Category: Status
Base Power: —
Accuracy: —
PP: 5
Priority: 0
Target: Self
Flags: snatch, heal

Mechanics:
- Heals the user for a percentage of its max HP based on current weather:
  - No weather: 50%
  - Sunny Day / Desolate Land: 67%
  - Rain Dance / Primordial Sea / Sandstorm / Hail / Snow: 25%
- snatch: can be stolen by a foe using Snatch.
- Does not make contact.

AI Scoring: Sun-based recovery group (Morning Sun / Synthesis / Moonlight).
- In Sun: +7 if AI decides it should recover; otherwise treated as a standard 50% recovery move.
- Without Sun (50% heal): +7 if AI decides it should recover; +5 otherwise.
- −20 at full HP; −6 at 85% HP or higher.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Sing">
Type: Normal
Category: Status
Base Power: —
Accuracy: 70
PP: 15
Priority: 0
Target: Normal
Flags: sound, bypasssub, reflectable

Mechanics:
- Inflicts sleep on the target.
- sound flag: bypasses Substitute; blocked by Soundproof ability.
- bypasssub: hits through Substitute.
- Reflectable: reversed by Magic Coat/Magic Bounce.
- Does not make contact.

AI Scoring: Non-damaging sleep move group (same as Yawn / Dark Void / Grass Whistle / Sing).
- Starts at +6.
- 25% of the time: +1 if target can be put to sleep; +1 more if AI has Dream Eater/Nightmare and target lacks Snore/Sleep Talk; +1 more if AI/partner has Hex.
- 75% of the time: no additional bonuses (+6 flat).

R&B Changes: Accuracy increased from 55% to 70%.
</Element>

<Element name="Octolock">
Type: Normal
Category: Status
Base Power: —
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Traps the target, preventing it from switching out or fleeing (similar to partial-trap moves but a volatile status).
- At the end of each turn while the Octolock volatile is active: the target's Defense and Special Defense are each lowered by 1 stage.
- The volatile ends if the user switches out or faints.
- Fails against Ghost-type Pokémon (immune to trapping).
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Seismic Toss">
Type: Fighting
Category: Physical
Base Power: — (level-based)
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact, nonsky

Mechanics:
- Deals fixed damage equal to the user's level, ignoring stat modifiers and type matchups.
- Ghost-type Pokémon are immune.
- nonsky: does not hit airborne Pokémon.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Discharge">
Type: Electric
Category: Special
Base Power: 80
Accuracy: 100
PP: 15
Priority: 0
Target: All Adjacent
Flags: none

Mechanics:
- Deals 80 BP Electric-type Special damage to all adjacent Pokémon (both foes and ally in doubles).
- 30% chance to inflict paralysis on each target hit.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Bubble Beam">
Type: Water
Category: Special
Base Power: 65
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: none

Mechanics:
- Deals 65 BP Water-type Special damage.
- 10% chance to lower the target's Speed by 1 stage.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Toxic Spikes">
Type: Poison
Category: Status
Base Power: —
Accuracy: —
PP: 20
Priority: 0
Target: Foe's Side
Flags: none

Mechanics:
- Sets up a layer of Toxic Spikes on the opposing side of the field. Up to 2 layers can be set.
- Pokémon that switch in while Toxic Spikes are present are poisoned (1 layer) or badly poisoned (2 layers).
- Poison-type Pokémon that switch in absorb Toxic Spikes, removing them from the field.
- Flying-type Pokémon and those with Levitate are unaffected by Toxic Spikes.
- Steel-type Pokémon are immune to poisoning and are not absorbed by Toxic Spikes.
- Pokémon holding Heavy-Duty Boots are unaffected.
- Does not directly target or damage any Pokémon.

AI Scoring:
- First turn out: +8 (25%) or +9 (75%).
- Other turns: +6 (25%) or +7 (75%).
- If at least 1 layer of Toxic Spikes is already active on the opposing side: -1 to score.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Mega Punch">
Type: Normal
Category: Physical
Base Power: 80
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: punch, contact

Mechanics:
- Deals 80 BP Normal-type Physical damage.
- Makes contact.
- Boosted by Iron Fist ability (+30% damage).

R&B Changes: Accuracy increased from 85% to 100%.
</Element>

<Element name="Vital Throw">
Type: Fighting
Category: Physical
Base Power: 70
Accuracy: —
PP: 10
Priority: -1
Target: Normal
Flags: contact, protect, mirror, metronome

Mechanics:
- Deals 70 BP Fighting-type Physical damage.
- Never misses (bypasses accuracy and evasion checks entirely).
- Has priority −1, so it moves after most moves.
- Makes contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Attract">
Type: Normal
Category: Status
Base Power: —
Accuracy: 100
PP: 15
Priority: 0
Target: Normal
Flags: protect, reflectable, mirror, bypasssub, metronome

Mechanics:
- Inflicts the infatuation (Attract) volatile status on the target.
- Only succeeds if the target is the opposite gender of the user (male vs. female); fails on genderless Pokémon.
- Infatuated Pokémon have a 50% chance each turn to be unable to use a move.
- The infatuation lasts as long as the user remains on the field; it ends if the user switches out.
- If the infatuated Pokémon holds a Destiny Knot, the user also becomes infatuated.
- Can also be inflicted by the Cute Charm ability on contact.
- Bypasses Substitute.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Brine">
Type: Water
Category: Special
Base Power: 65
Accuracy: 100
PP: 10
Priority: 0
Target: Normal
Flags: protect, mirror, metronome

Mechanics:
- Deals 65 BP Water-type Special damage.
- If the target's current HP is 50% or less of its maximum HP, base power doubles to 130.
- Does not make contact.

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Thousand Waves">
Type: Ground
Category: Physical
Base Power: 90
Accuracy: 100
PP: 10
Priority: 0
Target: All Adjacent Foes
Flags: protect, mirror, nonsky

Mechanics:
- Deals 90 BP Ground-type Physical damage to all adjacent foes.
- Traps all hit targets, preventing them from switching out or fleeing.
- The trap lasts as long as the user remains on the field.
- Does not make contact.
- Cannot hit Pokémon in the air (nonsky).

R&B Changes: None. Vanilla gen 8 mechanics apply.
</Element>

<Element name="Frustration">
Type: Normal
Category: Physical
Base Power: 102
Accuracy: 100
PP: 20
Priority: 0
Target: Normal
Flags: contact, protect, mirror, metronome

Mechanics:
- Deals Normal-type Physical damage.
- In vanilla, base power scales with the user's unhappiness: floor((255 − happiness) × 10 / 25), minimum 1, maximum 102.
- In R&B, base power is fixed at 102.
- Makes contact.

R&B Changes: Base Power fixed at 102 (max value; happiness mechanic removed).
</Element>

