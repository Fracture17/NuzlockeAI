# Simulator Guide

Reference for RNG control and state inspection when writing tests with the battle harness. For how to run turns and assert on events, see LOGGER_GUIDE.md.

*Note: The Simulator itself (`Simulator.step`, `make_sim`, `run_turn`, `capture_turn`) lives in the old repo (PycharmProjects/NuzlockeAI) until Stage E. This document is carried as the semantic reference — the State Structure and Luck Control sections apply directly to the new repo: `liveplay/rng.py` (`LuckProfile`, `GOOD_LUCK`, `BAD_LUCK`, `AVERAGE_LUCK`), `liveplay/state/battle.py`, `liveplay/state/side.py`, `liveplay/state/pokemon.py`. References to `src/simulator.py` below describe old-repo code.*

---

## Luck Control

Luck governs all Category B RNG: accuracy, crits, secondary effect chance, damage rolls, multi-hit count, status durations (sleep wakeup, confusion snap, defrost), per-turn status checks (confusion self-hit, attract, full paralysis), flinch, binding duration, and rampage duration. These never cause a simulator pause.

### Presets

```python
from liveplay.rng import GOOD_LUCK, BAD_LUCK, AVERAGE_LUCK
# Aliases in battle_harness: GOOD, BAD, AVERAGE
```

| Preset | Effect |
|---|---|
| `GOOD` | Always hits, max damage, secondaries always fire, never wakes/snaps/thaws early, never self-hits from confusion, never fully paralyzed, max hits, max duration |
| `BAD` | Opposite of everything above |
| `AVERAGE` | Threshold-based: a 60% chance fires, a 40% chance does not. Max damage roll. |
| `LuckGroup.RANDOM` | True randomness via `random.random()` |

Pass as `luck0`/`luck1` to `run_turn`, `capture_turn`, or `make_sim`.

### Per-Event Overrides

Override a specific event while keeping the rest of the group's behavior. Set on the `Simulator` via `make_sim`:

```python
from liveplay.rng import RNGEvent

sim = make_sim(luck0=GOOD, luck1=GOOD)
sim.overrides_0[RNGEvent.CRIT] = False        # side 0 never crits
sim.overrides_0[RNGEvent.DAMAGE_ROLL] = 0.85  # specific damage roll (0.0–1.0)
sim.overrides_1[RNGEvent.SECONDARY_FIRES] = True
```

Boolean overrides: `True` = favorable outcome for the acting side, `False` = unfavorable.
`DAMAGE_ROLL` takes a float `0.0`–`1.0`. `MULTI_HIT_COUNT`, `BINDING_DURATION`, and `RAMPAGE_DURATION` take `True` (max) or `False` (min).

Overridable events: `ACCURACY`, `CRIT`, `SECONDARY_FIRES`, `WAKE`, `CONFUSION_SNAP`, `DEFROST`, `CONFUSION_SELF_HIT`, `ATTRACT_IMMOBILIZE`, `FULL_PARALYSIS`, `FLINCH`, `ANCIENT_POWER_BOOST`, `DAMAGE_ROLL`, `MULTI_HIT_COUNT`, `BINDING_DURATION`, `RAMPAGE_DURATION`.

### Direct `LuckProfile`

For fine-grained threshold control, assign a `LuckProfile` directly. This takes priority over `luck_*` and `overrides_*`.

```python
import dataclasses
from liveplay.rng import GOOD_LUCK

sim.luck_profile_0 = dataclasses.replace(GOOD_LUCK, damage_roll=0.75, crit_threshold=5.0)
```

---

## AI and Action Control

### Default game AI

`select_ai_action(state, ai_idx)` (`src/ai.py`, old-repo resident until Stage E) implements the game's NPC AI. Assign it to `decision_logic_0/1` on the simulator to automate a side's main action selection each turn. Both sides can be independently automated or left as manual.

```python
from src.ai import select_ai_action  # old repo

sim = make_sim(luck0=GOOD, luck1=GOOD)
sim.decision_logic_1 = lambda state, legal: select_ai_action(state, 1)

# Side 0 action supplied manually; side 1 picks automatically via AI
final = run_turn(state, slot(0), sim=sim)
```

The callable signature is `(BattleState, list[Action]) -> Action`. The `legal` list reflects all constraints (PP, choice lock, encore, etc.) — always pick from it.

### Direct action control

Without `decision_logic` set, the simulator pauses at `AWAIT_ACTIONS` and the harness expects both actions passed to `run_turn`/`capture_turn` explicitly. This is the default for most tests.

### Mid-turn forced switches

Mid-turn forced switches (U-turn, Eject Button, Red Card, Roar/Dragon Tail) and post-faint replacements require explicit input. **`capture_turn` raises `ValueError`** if one of these pauses occurs and `extra_inputs` is empty.

Supply `extra_inputs` as a list of `(action_side0, action_side1)` tuples consumed in order as switch pauses arise. Pass `None` for a side that does not need to switch.

```python
# Side 1 uses U-turn; side 1 sends in team slot 2
final, log = capture_turn(state, slot(0), slot(0),
                          extra_inputs=[(None, switch_to(2))])

# Both sides need a replacement after a double KO
final, log = capture_turn(state, slot(0), slot(0),
                          extra_inputs=[(switch_to(1), switch_to(1))])
```

For post-KO switches, `select_post_ko_switch(state, ai_idx)` returns the slot the game AI would choose given the current state:

```python
from src.ai import select_post_ko_switch  # old repo

# Compute AI's preferred switch-in before the turn
slot_choice = select_post_ko_switch(state, 1)
final, log = capture_turn(state, slot(0), slot(0),
                          extra_inputs=[(None, switch_to(slot_choice))])
```

Note that `select_post_ko_switch` scores based on the pre-turn state, not the mid-turn state after the KO occurs, so it is an approximation for complex turns.

`run_turn` (without `capture_turn`) auto-resolves all forced switches by picking the first available bench slot.

---

## Category A Event Injection

Category A events are genuinely random outcomes. The harness raises an exception if one occurs without a pre-injected answer, so any test involving these mechanics must inject the expected value into `sim._rng_inject` before calling `capture_turn` with `sim=`:

```python
sim = make_sim(luck0=GOOD, luck1=GOOD)
sim._rng_inject[RNGEvent.TRI_ATTACK_STATUS] = Status.BURN

final, log = capture_turn(state, slot(0), slot(0), sim=sim)
```

The simulator consumes the injected value when it reaches that event. `_rng_inject` is a dict with one value per key, so if the same event fires more than once in a turn only the first occurrence is controlled — the second will raise an exception. In singles this is rarely an issue since most Category A events fire at most once per turn. `_rng_inject` is reset on each `start()` call, so inject after `make_sim` but before `run_turn`/`capture_turn`.

### Mid-Move Events (`AWAIT_MOVE_RNG`)

| Event | Injected value | Notes |
|---|---|---|
| `ACUPRESSURE_STAT` | `int` 0–6 | 0=Atk, 1=Def, 2=SpA, 3=SpD, 4=Spe, 5=Acc, 6=Eva |
| `ROAR_TARGET` | `int` (bench slot index) | |
| `TRI_ATTACK_STATUS` | `Status` | `BURN`, `FREEZE`, or `PARALYSIS` |
| `EFFECT_SPORE_WHICH` | `Status` | `PARALYSIS`, `POISON`, or `SLEEP` |

### End-of-Turn Events (`AWAIT_RESIDUAL_RNG`)

| Event | Injected value | Notes |
|---|---|---|
| `MOODY_STATS` | `(int, int)` | `(boost_stat_idx, drop_stat_idx)`, each taken `%7` — all 7 boostable stats eligible for both picks (0=Atk … 4=Spe, 5=Acc, 6=Eva); raises `ValueError` if boost==drop after `%7`. Uninjected path: boost `randint(0,6)`, drop `randint(0,5)` bumped +1 when `>= boost` |
| `STARF_BERRY_STAT` | `int` 0–4 | Stat index to boost (Atk/Def/SpA/SpD/Spe only) |

### Sub-Move Events (`AWAIT_SUB_MOVE`)

Metronome and Sleep Talk also accept pre-injection. Pass a `Move` to force a specific outcome, or `None` to make the action fail (PP still consumed):

```python
sim._rng_inject[RNGEvent.METRONOME_MOVE]  = Move.EARTHQUAKE
sim._rng_inject[RNGEvent.SLEEP_TALK_MOVE] = Move.FLAMETHROWER
```

---

## State Structure

State snapshots are read-only from the test's perspective. The final state returned by `run_turn` reflects the battle after all actions and residuals.

### `BattleState`

| Field | Type | Notes |
|---|---|---|
| `sides` | `(SideState, SideState)` | Index 0 = side 0, index 1 = side 1 |
| `weather` | `WeatherEnum` | `NONE`, `SUNNY`, `RAINY`, `SANDSTORM`, `HAIL`, `HEAVY_RAIN`, `HARSH_SUN`, `STRONG_WIND` |
| `weather_turns` | `int` | Turns remaining; `-1` = permanent |
| `terrain` | `TerrainEnum` | `NONE`, `ELECTRIC`, `GRASSY`, `PSYCHIC`, `MISTY` |
| `terrain_turns` | `int` | Turns remaining; `-1` = permanent |
| `pseudo_weather` | `list[(PseudoWeather, int)]` | `TRICK_ROOM`, `GRAVITY`, `MAGIC_ROOM`, `WONDER_ROOM`, `TAILWIND_FIELD` with turns remaining |
| `turn_number` | `int` | Increments at the end of each turn |

### `SideState`

| Field | Type | Notes |
|---|---|---|
| `team` | `list[PokemonState]` | Up to 6; ordered by team slot |
| `active_indices` | `list[int]` | `[0]` in singles; indices into `team` |
| `side_conditions` | `list[(SideCondition, int)]` | Active hazards/screens with turns remaining; `-1` = permanent |
| `mega_used` | `bool` | Whether this side has mega evolved this battle |

`SideCondition` values: `REFLECT`, `LIGHT_SCREEN`, `AURORA_VEIL`, `STEALTH_ROCK`, `SPIKES_1/2/3`, `TOXIC_SPIKES_1/2`, `STICKY_WEB`, `TAILWIND`.

To get the active Pokemon: `side.team[side.active_indices[0]]`.

### `PokemonState`

| Field | Type | Notes |
|---|---|---|
| `species` | `Species` | |
| `level` | `int` | |
| `ability` | `Ability` | Current ability (may differ from `base_ability` if suppressed by Neutralizing Gas) |
| `item` | `Item` | |
| `status` | `Status` | `NONE`, `BURN`, `FREEZE`, `PARALYSIS`, `POISON`, `TOXIC`, `SLEEP` |
| `hp` | `int` | Current HP |
| `max_hp` | `int` | |
| `stats` | `tuple` | `(hp, atk, def, spa, spd, spe)` base computed values (no stages applied) |
| `stat_stages` | `tuple` | 7 values: Atk, Def, SpA, SpD, Spe, Acc, Eva |
| `move_ids` | `tuple[Move, ...]` | 4 slots; unused slots are `Move.NONE` |
| `move_pp` | `tuple[int, ...]` | Current PP per slot |
| `types` | `tuple[Type, ...]` | Current types (can change via Soak, Roost, etc.) |
| `volatiles` | `int` | `Volatile` bitfield |
| `timed_volatiles` | `list[(VolatileEffect, int)]` | Timed effects with turns remaining |
| `fainted` | `bool` | |
| `is_mega` | `bool` | |

Common `Volatile` flags: `CONFUSED`, `LEECH_SEEDED`, `CURSED`, `ENCORE_ACTIVE`, `TAUNT_ACTIVE`, `TORMENT`, `FLINCHED`, `RECHARGING`, `LOCKED_MOVE`, `SUBSTITUTE`, `DESTINY_BOND`, `PERISH_SONG_ACTIVE`, `AQUA_RING`, `INGRAIN`, `CHOICE_LOCKED`, `ATTRACTED`, `PROTECT_USED`.

`VolatileEffect` values (timed): `ENCORE`, `TAUNT`, `PERISH_SONG`, `BOUND`, `DISABLE`, `EMBARGO`, `MAGNET_RISE`, `SLOW_START`, `STOCKPILE`, `ROOST`, `RAMPAGING`.
