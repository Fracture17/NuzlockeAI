# Logger Guide for Testing Agents

## Overview

The logger captures structured events emitted by the engine during a turn. Tests use it to verify *what happened* (move order, damage amounts, sources, sequences) rather than just *final state*.

The global logger is `None` by default (zero-cost no-op). `capture_turn` installs a `CapturingLogger`, drives the simulator until the next turn boundary, then restores the previous logger. `capture_battle` does the same across an arbitrary sequence of turns.

The logger lives at `liveplay/logger.py` (`LogEvent`, `CapturingLogger`). The harness functions `capture_turn`, `run_turn`, and `make_sim` *(_italicized note below_)* live in the old repo until Stage E; new-repo tests import assertion helpers from `tests/state_builders.py`.

---

## Standard Pattern — Single Turn

```python
from tests.battle_harness import (
    make_mon, make_battle, slot, switch_to,
    capture_turn, capture_battle, GOOD, BAD,
    assert_event, assert_no_event, assert_event_count,
    assert_event_sequence, assert_event_sequence_exact,
)
from liveplay.logger import LogEvent
from liveplay.data.species import Species
from liveplay.data.moves import Move
from liveplay.data.status import Status

muk     = make_mon(Species.MUK,     moves=(Move.SLUDGE_BOMB,))
corsola = make_mon(Species.CORSOLA, moves=(Move.SPLASH,))
state   = make_battle(muk, corsola)

final, log = capture_turn(state, slot(0), slot(0), luck0=GOOD, luck1=GOOD)

assert_event(log, LogEvent.DAMAGE, target=Species.CORSOLA, source="move")
assert_event(log, LogEvent.STATUS_APPLY, target=Species.CORSOLA, status=Status.POISON)
```

*Note: `capture_turn`, `run_turn`, and `make_sim` are harness functions that live in the old repo (PycharmProjects/NuzlockeAI) until Stage E. New-repo tests import assertion helpers from `tests/state_builders.py` instead.*

## Multi-Turn Pattern

Use `capture_battle` as a context manager. All `run_turn` calls inside the block share one logger. Use `TURN_START` events to identify turn boundaries.

```python
with capture_battle() as log:
    state1 = run_turn(state0, slot(0), slot(0), luck0=GOOD)
    state2 = run_turn(state1, slot(0), slot(0), luck0=GOOD)

assert_event_count(log, LogEvent.TURN_START, 2)
assert_event_sequence(log,
    (LogEvent.TURN_START, {"turn": 1}),
    LogEvent.MOVE_USE,
    (LogEvent.TURN_START, {"turn": 2}),
    LogEvent.MOVE_USE,
)
```

---

## CapturingLogger Query Interface

All methods are available on the logger returned by `capture_turn`.

```python
log.events                              # raw list of (LogEvent, dict) pairs, in order
log.of(LogEvent.DAMAGE)                 # list of all DAMAGE kwargs dicts
log.all_of(LogEvent.DAMAGE, source="move")  # filtered list
log.first(LogEvent.DAMAGE, source="move")   # first match or None
log.fired(LogEvent.DAMAGE, source="move")   # bool
log.count(LogEvent.DAMAGE, source="move")   # int
```

Filtering is a **partial match**: only the specified fields are checked; extra fields in the event are ignored.

---

## Assertion Helpers

All helpers raise `AssertionError` with the full event list on failure.

```python
# At least one matching event exists
assert_event(log, LogEvent.DAMAGE, target=Species.CORSOLA, source="move")

# No matching event
assert_no_event(log, LogEvent.CRIT)

# Exactly N matching events
assert_event_count(log, LogEvent.DAMAGE, 2)

# All specs appear in this relative order (non-contiguous)
assert_event_sequence(log,
    (LogEvent.MOVE_USE,    {"user": Species.MUK}),
    (LogEvent.DAMAGE,      {"target": Species.CORSOLA, "source": "move"}),
    (LogEvent.STATUS_APPLY,{"target": Species.CORSOLA}),
)

# All specs appear as a contiguous block (nothing between them)
assert_event_sequence_exact(log,
    (LogEvent.DAMAGE, {"source": "move"}),
    LogEvent.CRIT,
)
```

Each spec in a sequence is a bare `LogEvent` (match any kwargs) or a `(LogEvent, dict)` tuple (partial match).

---

## Key Events and Their Fields

| Event | Key fields |
|---|---|
| `TURN_START` | `turn=int` |
| `MOVE_USE` | `user=Species, move=Move, targets=list, called_by=str\|None` |
| `MOVE_MISS` | `user=Species` |
| `MOVE_FAIL` | `user=Species, reason=str` |
| `MOVE_IMMUNE` | `user=Species, target=Species, reason=str` |
| `MOVE_BLOCKED` | `user=Species, target=Species, blocker=str` |
| `PP_USE` | `pokemon=Species, move=Move, pp_remaining=int` |
| `DAMAGE` | `target=Species, amount=int, hp_before=int, hp_after=int, source=str, source_detail=str\|None` |
| `CRIT` | `target=Species` |
| `EFFECTIVENESS` | `target=Species, multiplier=float` |
| `HEAL` | `target=Species, amount=int, hp_before=int, hp_after=int, source=str` |
| `STAT_BOOST` | `target=Species, stat=int, stages=int, new_stage=int, source=str` |
| `STATUS_APPLY` | `target=Species, status=Status, source=str, source_detail=str\|None` |
| `STATUS_CURE` | `target=Species, status=Status, source=str` |
| `VOLATILE_APPLY` | `target=Species, volatile=str, source=str, duration=int\|None` |
| `VOLATILE_END` | `target=Species, volatile=str, reason=str` |
| `FAINT` | `pokemon=Species, side=int, cause=str` |
| `SWITCH_OUT` | `pokemon=Species, side=int, reason=str` |
| `SWITCH_IN` | `pokemon=Species, side=int, hp=int, status=Status` |
| `ABILITY_ACTIVATE` | `pokemon=Species, ability=str, trigger=str, effect=str` |
| `ITEM_CONSUME` | `pokemon=Species, item=str, trigger=str` |
| `WEATHER_START` | `weather=str, source=str, source_detail=str, duration=int` |
| `TERRAIN_START` | `terrain=str, source=str, source_detail=str, duration=int` |
| `HAZARD_APPLY` | `side=str, hazard=str, layer_count=int, source=Species` |
| `WIN` | `winner_side=int` |
| `TIE` | *(no fields)* |

**`stat` in STAT_BOOST is an integer index**: 0=Atk, 1=Def, 2=SpA, 3=SpD, 4=Spe, 5=Acc, 6=Eva.

**`DAMAGE` source strings**: `"move"`, `"recoil"`, `"life_orb"`, `"residual_burn"`, `"residual_poison"`, `"residual_toxic"`, `"residual_weather"`, `"residual_leech_seed"`, `"residual_binding"`, `"entry_hazard"`, `"ability"`, `"item"`, `"confusion_self_hit"`, `"crash"`.

---

## Limitations and Workarounds

### 1. Custom RNG injection with `sim=`

`capture_turn` accepts a `sim=` argument directly. Pass a pre-configured `Simulator` when you need `_rng_inject` (e.g. to control Tri Attack's status roll). When `sim=` is provided, `luck0`/`luck1` are ignored.

```python
sim = make_sim(luck0=GOOD, luck1=GOOD)
sim._rng_inject[RNGEvent.TRI_ATTACK_STATUS] = Status.BURN

final, log = capture_turn(state, slot(0), slot(0), sim=sim)
assert_event(log, LogEvent.STATUS_APPLY, status=Status.BURN)
```

For multi-turn RNG injection, use `capture_battle` with the same sim passed to each `run_turn` call:

```python
sim = make_sim(luck0=GOOD, luck1=GOOD)
with capture_battle() as log:
    state1 = run_turn(state0, slot(0), slot(0), sim=sim)
    sim._rng_inject[RNGEvent.TRI_ATTACK_STATUS] = Status.FREEZE
    state2 = run_turn(state1, slot(0), slot(0), sim=sim)
```

### 2. Not all events are implemented

Two-turn moves (Fly, Dig, etc.) are implemented in the engine — they correctly set the SEMI_INVULNERABLE volatile and execute the two-phase attack — but the `CHARGE_TURN`, `SEMI_INVULNERABLE_ENTER`, and `SEMI_INVULNERABLE_EXIT` log events have no call sites yet (the events exist in the `LogEvent` enum but are never emitted). Do not expect these three events to fire when testing two-turn moves; assert on state changes (volatile presence, damage, etc.) instead.

Several other rare events exist in the enum but also lack call sites:
- `BATON_PASS_TRANSFER` — no call site found in `engine/` or old `src/engine/`.
- `STAT_COPY` — no call site found.
- `PURSUIT_INTERCEPT` — no call site found.
- `FUTURE_SIGHT_HIT` — **has a call site** (`src/engine/residuals.py`); this event does fire.

If an event you expect is missing, verify whether a call site exists before debugging the test.

### 3. Filter matching uses `==` — watch enum vs. string

Fields like `status=` hold `Status` enum members, `move=` holds `Move` enum members, `target=` and `pokemon=` hold `Species` enum members. Pass the same type you expect:

```python
# Correct
assert_event(log, LogEvent.STATUS_APPLY, status=Status.BURN)

# Wrong — will never match
assert_event(log, LogEvent.STATUS_APPLY, status="burn")
```

### 4. Forced switches must be pre-specified

`capture_turn` errors if a forced switch pause occurs (post-KO replacement, U-turn, Eject Button, Red Card, Roar/Dragon Tail) and no input was pre-supplied. This is intentional — it forces the test to fully specify what happens.

```python
# Will error if corsola faints and side 1 needs a replacement
final, log = capture_turn(state, slot(0), slot(0))

# Correct: pre-specify the replacement
final, log = capture_turn(state, slot(0), slot(0),
                          extra_inputs=[(None, switch_to(1))])
# extra_inputs is a list of (action_side0, action_side1) tuples,
# consumed in order as forced-switch pauses arise. Pass None for
# a side that does not need to act.
```

RNG pauses (Acupressure, Moody, etc.) and sub-move pauses (Metronome/Sleep Talk) are still auto-resolved — control those via luck profiles and `_rng_inject`.

`capture_turn` stops at `AWAIT_ACTIONS` (the start of the next turn). Everything within the current turn — both actions, mid-turn forced switches, the full residual phase — is captured in a single logger.

### 5. Event ordering within the same mechanic

Some events share a call site (e.g., `DAMAGE` then `FAINT` are emitted back-to-back). Use `assert_event_sequence_exact` only when you are certain nothing fires between them. Prefer `assert_event_sequence` (non-contiguous) when the relative order matters but other events may intervene.

### 6. `log.first()` with no filters

`log.first(LogEvent.DAMAGE)` returns the first DAMAGE event regardless of source. In turns with multiple damage events (recoil, residuals, multi-hit), be explicit:

```python
log.first(LogEvent.DAMAGE, source="move")      # first move hit
log.first(LogEvent.DAMAGE, source="life_orb")  # Life Orb recoil
```
