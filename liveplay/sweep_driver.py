# Per-trial turn driver for the vision-reconciliation sweep. Pure leaf: no engine_select,
# no sibling sweep leaves. Wraps run_one_turn_cpp + apply_switch_cpp in a decision-boundary
# loop and exposes RNG-config adapters that map SweepConfig → per-slot LuckProfiles.
from __future__ import annotations

import dataclasses
import sys
import traceback
from dataclasses import dataclass, field
from typing import Optional

from liveplay.actions import Action
import liveplay.cpp_driver as _cpp_driver
from liveplay.cpp_driver import UnportedTurn
from liveplay.logger import CapturingLogger, LogEvent
from liveplay.rng import LuckProfile, RNGEvent, SWEEP_LUCK
from liveplay.state.battle import BattleState


# ---------------------------------------------------------------------------
# Public config types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SideOverrides:
    """Per-side RNG overrides for one sweep trial."""
    crit: bool = False
    roll: float = 0.5
    crits_per_hit: Optional[tuple | dict] = None   # dict = keyed by source_slot (doubles)
    rolls_per_hit: Optional[tuple | dict] = None   # dict values: scalar or per-hit tuple
    extra_overrides: Optional[dict] = None         # RNGEvent -> value (value may be slot-keyed dict)


@dataclass(frozen=True)
class SweepConfig:
    """Full configuration for one sweep trial."""
    tie_winner: int = 0
    extra_pre_inject: Optional[dict] = None        # MUST be None/empty, else NotImplementedError
    side0: SideOverrides = field(default_factory=SideOverrides)
    side1: SideOverrides = field(default_factory=SideOverrides)


@dataclass(frozen=True)
class SweepLuck:
    """Per-side (and optionally per-slot-1) LuckProfiles for one sweep trial."""
    p0: LuckProfile
    p1: LuckProfile
    p0_slot1: Optional[LuckProfile] = None
    p1_slot1: Optional[LuckProfile] = None


# ---------------------------------------------------------------------------
# RNGEvent → LuckProfile field mappings
# ---------------------------------------------------------------------------

# bool events: field name, good (True) value, bad (False) value
_BOOL_EVENT_MAP = {
    RNGEvent.ACCURACY:           ('accuracy_threshold',            0.0,   101.0),
    RNGEvent.SECONDARY_FIRES:    ('secondary_threshold',           0.0,   101.0),
    RNGEvent.PROC_FIRES:         ('proc_threshold',                0.0,   101.0),
    RNGEvent.WAKE:               ('wake_threshold',                0.0,   101.0),
    RNGEvent.CONFUSION_SNAP:     ('confusion_snap_threshold',      0.0,   101.0),
    RNGEvent.DEFROST:            ('defrost_threshold',             0.0,   101.0),
    RNGEvent.CONFUSION_SELF_HIT: ('confusion_self_hit_threshold',  0.0,   101.0),
    RNGEvent.ATTRACT_IMMOBILIZE: ('attract_threshold',             0.0,   101.0),
    RNGEvent.FULL_PARALYSIS:     ('paralysis_threshold',           0.0,   101.0),
    RNGEvent.FLINCH:             ('flinch_threshold',              0.0,   101.0),
    RNGEvent.QUICK_CLAW:         ('quick_claw_threshold',          0.0,   101.0),
}

# Category B events not supported in extra_overrides (handled specially or dead in C++)
_DEAD_EVENTS = frozenset({RNGEvent.ANCIENT_POWER_BOOST})

# Category A events (uncontrolled; always fatal to inject via extra_overrides)
_CATEGORY_A_EVENTS = frozenset({
    RNGEvent.ACTION_SELECT, RNGEvent.FORCED_SWITCH, RNGEvent.POST_FAINT_SWITCH,
    RNGEvent.METRONOME_MOVE, RNGEvent.SLEEP_TALK_MOVE, RNGEvent.ASSIST_MOVE,
    RNGEvent.ACUPRESSURE_STAT, RNGEvent.ROAR_TARGET, RNGEvent.EFFECT_SPORE_WHICH,
    RNGEvent.TRI_ATTACK_STATUS, RNGEvent.MOODY_STATS, RNGEvent.STARF_BERRY_STAT,
    RNGEvent.SPEED_TIE, RNGEvent.SPEED_TIEBREAKER, RNGEvent.RANDOM_TARGET,
})


def _crit_threshold(v) -> float:
    """Convert a bool or float crit value to a LuckProfile crit_threshold."""
    if v is True:
        return 0.0
    if v is False:
        return 101.0
    return float(v)


def _apply_extra_override(event: RNGEvent, value, kwargs: dict, slot1_kwargs: dict) -> None:
    """Map one extra_overrides entry into LuckProfile kwargs for slot-0 (and optionally slot-1).

    Raises ValueError for unsupported/dead events; raises ValueError for QUICK_CLAW
    slot-keyed dict with conflicting values.
    """
    if event in _DEAD_EVENTS:
        raise ValueError(
            f"ANCIENT_POWER_BOOST is dead in C++ (modeled as secondary); "
            f"Task 6 decides remap. Do not inject {event.name} via extra_overrides."
        )
    if event in _CATEGORY_A_EVENTS:
        raise ValueError(
            f"{event.name} is a Category-A event and cannot be injected via extra_overrides "
            f"(use extra_pre_inject for Category-A pre-injection, Task 6/7)."
        )

    if event == RNGEvent.CRIT:
        if isinstance(value, (list, tuple)):
            per_hit = tuple(_crit_threshold(v) for v in value)
            kwargs['crits_per_hit'] = per_hit
        elif isinstance(value, dict):
            _apply_slot_keyed(event, value, lambda v: _crit_threshold(v),
                              'crit_threshold', 'crits_per_hit', kwargs, slot1_kwargs)
        else:
            kwargs['crit_threshold'] = _crit_threshold(value)

    elif event in _BOOL_EVENT_MAP:
        field_name, good_val, bad_val = _BOOL_EVENT_MAP[event]
        if event == RNGEvent.QUICK_CLAW and isinstance(value, dict):
            # QUICK_CLAW is side-level (TurnLuck); conflicting slot values → ValueError
            vals = list(value.values())
            if len(set(bool(v) for v in vals)) > 1:
                raise ValueError(
                    f"QUICK_CLAW slot-keyed dict has conflicting values {value}; "
                    f"quick_claw is a side-level TurnLuck field and cannot differ per slot."
                )
            kwargs[field_name] = good_val if vals[0] else bad_val
        elif isinstance(value, dict):
            _apply_slot_keyed(event, value, lambda v: good_val if v else bad_val,
                              field_name, None, kwargs, slot1_kwargs)
        else:
            kwargs[field_name] = good_val if value else bad_val

    elif event == RNGEvent.DAMAGE_ROLL:
        if isinstance(value, (list, tuple)):
            kwargs['damage_rolls_per_hit'] = tuple(float(v) for v in value)
        elif isinstance(value, dict):
            _apply_slot_keyed(event, value,
                              lambda v: tuple(float(x) for x in v) if isinstance(v, (list, tuple)) else float(v),
                              'damage_roll', 'damage_rolls_per_hit', kwargs, slot1_kwargs)
        else:
            kwargs['damage_roll'] = float(value)

    elif event == RNGEvent.PSYWAVE_ROLL:
        if isinstance(value, dict):
            _apply_slot_keyed(event, value, float, 'psywave_roll', None, kwargs, slot1_kwargs)
        else:
            kwargs['psywave_roll'] = float(value)

    elif event == RNGEvent.MULTI_HIT_COUNT:
        if isinstance(value, dict):
            conv = lambda v: float(v) if isinstance(v, float) else (1.0 if v else 0.0)
            _apply_slot_keyed(event, value, conv, 'multi_hit_roll', None, kwargs, slot1_kwargs)
        elif isinstance(value, float):
            kwargs['multi_hit_roll'] = value
        else:
            kwargs['multi_hit_roll'] = 1.0 if value else 0.0

    elif event == RNGEvent.BINDING_DURATION:
        kwargs['binding_duration_roll'] = 1.0 if value else 0.0

    elif event == RNGEvent.RAMPAGE_DURATION:
        kwargs['rampage_duration_roll'] = 1.0 if value else 0.0

    else:
        raise ValueError(
            f"{event.name} is not supported in extra_overrides "
            f"(unrecognized Category-A or unimplemented event)."
        )


def _apply_slot_keyed(event, slot_dict: dict, convert, scalar_field: str,
                      tuple_field: Optional[str], kwargs: dict, slot1_kwargs: dict) -> None:
    """Route slot-keyed dict: slot 0 value → kwargs; slot 1 value → slot1_kwargs."""
    for slot_idx, raw_val in slot_dict.items():
        converted = convert(raw_val)
        target = kwargs if slot_idx == 0 else slot1_kwargs
        if tuple_field is not None and isinstance(converted, tuple):
            target[tuple_field] = converted
        elif tuple_field is not None and isinstance(converted, (list,)):
            target[tuple_field] = tuple(converted)
        else:
            target[scalar_field] = converted


def _build_side_profile(side: SideOverrides) -> tuple[LuckProfile, Optional[LuckProfile]]:
    """Build (base_profile, slot1_profile_or_None) from a SideOverrides.

    Both profiles start from SWEEP_LUCK. The base profile uses slot-0 values; the slot-1
    profile is only created when slot-keyed crits/rolls/extra_overrides supply slot-1 data.
    """
    kwargs: dict = {}
    slot1_kwargs: dict = {}

    # crit override
    if side.crits_per_hit is not None:
        if isinstance(side.crits_per_hit, dict):
            for slot_idx, v in side.crits_per_hit.items():
                target = kwargs if slot_idx == 0 else slot1_kwargs
                if isinstance(v, (list, tuple)):
                    target['crits_per_hit'] = tuple(_crit_threshold(x) for x in v)
                else:
                    target['crit_threshold'] = _crit_threshold(v)
        else:
            kwargs['crits_per_hit'] = tuple(_crit_threshold(v) for v in side.crits_per_hit)
    else:
        kwargs['crit_threshold'] = _crit_threshold(side.crit)

    # damage roll override
    if side.rolls_per_hit is not None:
        if isinstance(side.rolls_per_hit, dict):
            for slot_idx, v in side.rolls_per_hit.items():
                target = kwargs if slot_idx == 0 else slot1_kwargs
                if isinstance(v, (list, tuple)):
                    target['damage_rolls_per_hit'] = tuple(float(x) for x in v)
                else:
                    target['damage_roll'] = float(v)
        else:
            kwargs['damage_rolls_per_hit'] = tuple(float(v) for v in side.rolls_per_hit)
    else:
        kwargs['damage_roll'] = float(side.roll)

    # Psywave always mirrors the scalar roll (even when rolls_per_hit is set)
    kwargs['psywave_roll'] = float(side.roll)

    # extra_overrides
    if side.extra_overrides:
        for event, value in side.extra_overrides.items():
            _apply_extra_override(event, value, kwargs, slot1_kwargs)

    base = dataclasses.replace(SWEEP_LUCK, **kwargs)
    slot1 = dataclasses.replace(SWEEP_LUCK, **slot1_kwargs) if slot1_kwargs else None
    return base, slot1


def build_sweep_luck(config: SweepConfig) -> SweepLuck:
    """Build per-side (and optionally per-slot-1) LuckProfiles from a SweepConfig.

    Raises NotImplementedError if extra_pre_inject is non-empty (Category-A injection
    is Task 6/7). Raises ValueError for unsupported or dead extra_overrides events.
    """
    if config.extra_pre_inject:
        raise NotImplementedError(
            "plain-mode Category-A pre-inject (Task 6/7): "
            f"extra_pre_inject must be None/empty, got {config.extra_pre_inject!r}"
        )
    p0, p0_slot1 = _build_side_profile(config.side0)
    p1, p1_slot1 = _build_side_profile(config.side1)
    return SweepLuck(p0=p0, p1=p1, p0_slot1=p0_slot1, p1_slot1=p1_slot1)


# ---------------------------------------------------------------------------
# Speed tie order
# ---------------------------------------------------------------------------

def build_speed_tie_order(state: BattleState, tie_winner: int) -> list[tuple[int, int]]:
    """Return forced act-order for a cross-side speed tie.

    Winner side's active slots (in slot order) come first, then loser side's active slots.
    Covers all active slots so the C++ rank lookup never misses a tying actor.
    """
    loser = 1 - tie_winner
    order = []
    for slot in range(len(state.sides[tie_winner].active_indices)):
        order.append((tie_winner, slot))
    for slot in range(len(state.sides[loser].active_indices)):
        order.append((loser, slot))
    return order


# ---------------------------------------------------------------------------
# Faint helpers
# ---------------------------------------------------------------------------

def has_fainted_active(state: BattleState) -> bool:
    """Return True if any side has a fainted active Pokemon AND living bench members.

    Mirrors the condition under which the engine enters a post-faint switch boundary:
    a side whose active slot is fainted but whose bench is not yet exhausted still needs
    a replacement. A side with no living bench members is a battle-over condition.
    """
    for side in state.sides:
        bench_available = any(
            i not in side.active_indices and not m.fainted
            for i, m in enumerate(side.team)
        )
        if not bench_available:
            continue
        if any(side.team[team_idx].fainted for team_idx in side.active_indices):
            return True
    return False


def _side_has_fainted_active(side) -> bool:
    """Return True if this side has any fainted active slot."""
    return any(side.team[team_idx].fainted for team_idx in side.active_indices)


def _side_has_living_bench(side) -> bool:
    """Return True if this side has at least one living non-active mon."""
    return any(
        i not in side.active_indices and not m.fainted
        for i, m in enumerate(side.team)
    )


# ---------------------------------------------------------------------------
# Error deduplication
# ---------------------------------------------------------------------------

_seen_unexpected_errors: set[tuple[str, str]] = set()


def reset_seen_errors() -> None:
    """Clear the dedup set for unexpected-error tracebacks (use between test cases)."""
    _seen_unexpected_errors.clear()


# ---------------------------------------------------------------------------
# Core turn driver
# ---------------------------------------------------------------------------

def run_to_decision_boundary(
    state: BattleState,
    action0,
    action1,
    config: SweepConfig,
    opp_switch_actions=(),
) -> Optional[BattleState]:
    """Drive one turn to the next decision boundary and return the resulting BattleState.

    A decision boundary is where the player provides input: the battle menu or a party
    prompt. Opponent-only post-faint switches are applied automatically via opp_switch_actions.

    Returns None on uninjected-RNG or unexpected errors (candidate filtered); re-raises
    UnportedTurn (fatal engine gap). ValueError/NotImplementedError from build_sweep_luck
    propagate before the try-wrapped call.
    """
    # Build luck profiles (may raise ValueError/NotImplementedError — propagate before try block)
    luck = build_sweep_luck(config)
    order = build_speed_tie_order(state, config.tie_winner)

    try:
        # Step 1: run the turn
        post_turn = _cpp_driver.run_one_turn_cpp(
            state, action0, action1,
            luck.p0, luck.p1,
            luck_p0_slot1=luck.p0_slot1,
            luck_p1_slot1=luck.p1_slot1,
            finalize_on_post_faint=True,
            speed_tie_order=order,
        )

        # Step 2: snapshot faint state once
        side0 = post_turn.sides[0]
        side1 = post_turn.sides[1]

        player_needs = (
            _side_has_fainted_active(side0) and _side_has_living_bench(side0)
        )

        # Ordered active-slot positions of side 1 fainted mons (only if bench available)
        opp_fainted_slots = []
        if _side_has_living_bench(side1):
            for slot_pos, team_idx in enumerate(side1.active_indices):
                if side1.team[team_idx].fainted:
                    opp_fainted_slots.append(slot_pos)

        # Step 3: if player needs replacement, return at party-prompt boundary
        if player_needs:
            return post_turn

        # Step 4: apply opponent replacement switches (using snapshot slot positions)
        current = post_turn
        opp_idx = 0
        for slot_pos in opp_fainted_slots:
            if opp_idx >= len(opp_switch_actions):
                return current
            action = opp_switch_actions[opp_idx]
            opp_idx += 1
            current = _cpp_driver.apply_switch_cpp(current, 1, action.switch_to_slot, source_slot=slot_pos)

        return current

    except UnportedTurn:
        raise  # fatal: identical engine gap across all candidates

    except RuntimeError as e:
        if "NeedsRNG" in str(e):
            key = (type(e).__name__, str(e))
            if key not in _seen_unexpected_errors:
                _seen_unexpected_errors.add(key)
                print(f"[sweep] uninjected RNG (skipping candidate): {e}", file=sys.stderr, flush=True)
            return None
        # Non-NeedsRNG RuntimeError — treat as unexpected
        key = (type(e).__name__, str(e))
        if key not in _seen_unexpected_errors:
            _seen_unexpected_errors.add(key)
            print(f"[sweep] unexpected error (skipping candidate):\n{traceback.format_exc()}", file=sys.stderr, flush=True)
        return None

    except Exception as e:
        key = (type(e).__name__, str(e))
        if key not in _seen_unexpected_errors:
            _seen_unexpected_errors.add(key)
            print(f"[sweep] unexpected error (skipping candidate):\n{traceback.format_exc()}", file=sys.stderr, flush=True)
        return None


def run_with_capture(
    state: BattleState,
    action0,
    action1,
    config: SweepConfig,
    opp_switch_actions=(),
) -> tuple[Optional[BattleState], CapturingLogger]:
    """Run one turn with C++ rich event log capture. Returns (result_state, capturing).

    The event log sink is registered before run_to_decision_boundary (capturing switch-in
    hazard damage) and unregistered in a finally block even on error. Partial capture is
    returned when result is None.
    """
    import nuzlocke_engine_cpp as cpp

    log = cpp.RichEventLog()
    cpp.set_rich_event_log(log)
    result = None
    try:
        result = run_to_decision_boundary(state, action0, action1, config, opp_switch_actions)
    finally:
        cpp.set_rich_event_log(None)

    return result, CapturingLogger.from_cpp(log)


# ---------------------------------------------------------------------------
# Damage helpers (ported verbatim from OLD simulation_runner.py :2732-2799)
# ---------------------------------------------------------------------------

def _sum_damage(capturing: CapturingLogger, target_species, target_side: Optional[int] = None) -> int:
    """Sum all move-source damage dealt to target_species in one captured turn.

    target_side disambiguates same-species mirror matchups: when given, only damage
    whose defender is on that side counts (the move-damage event records defender_side).
    """
    if target_species is None:
        return 0
    return sum(
        e["amount"]
        for e in capturing.all_of(LogEvent.DAMAGE, target=target_species, source="move")
        if target_side is None or e.get("defender_side") == target_side
    )


def _total_side_move_damage(capturing: CapturingLogger, target_side: int) -> int:
    """Sum all move-source damage dealt to ANY mon on target_side in one captured turn.

    Species-agnostic: unlike _sum_damage this counts every defender on the side, so the
    'no opponent deltas ⇒ no opponent damage' guard covers all doubles slots, not just
    slot 0's active species (finding E2).
    """
    return sum(
        e["amount"]
        for e in capturing.all_of(LogEvent.DAMAGE, source="move")
        if e.get("defender_side") == target_side
    )


def _per_hit_damages(capturing: CapturingLogger, target_species, target_side: Optional[int] = None) -> list[int]:
    """Return ordered list of per-hit move-source damage amounts for target_species.

    target_side disambiguates same-species mirror matchups (see _sum_damage).
    """
    if target_species is None:
        return []
    return [
        e["amount"]
        for e in capturing.all_of(LogEvent.DAMAGE, target=target_species, source="move")
        if target_side is None or e.get("defender_side") == target_side
    ]


def _own_damage(capturing: CapturingLogger, attacker_side: int, attacker_slot: int) -> int:
    """Sum move-source damage emitted by the specific attacker (side + slot)."""
    return sum(_attacker_per_hit_damages(capturing, attacker_side, attacker_slot))


def _attacker_per_hit_damages(capturing: CapturingLogger, attacker_side: int, attacker_slot: int) -> list[int]:
    """Return the ordered per-hit move-source damages emitted BY a specific attacker (side + slot).

    Keying on the attacker (rather than the defender's species) is switch-robust: when the
    defender switched in mid-turn, the pre-turn active species is stale, but the attacker's
    identity is fixed. attacker_slot is the active mon's team index (matches the DAMAGE log's
    attacker_slot field).
    """
    return [
        e["amount"]
        for e in capturing.all_of(
            LogEvent.DAMAGE, source="move",
            attacker_side=attacker_side, attacker_slot=attacker_slot,
        )
    ]


def _self_hit_damage(capturing: CapturingLogger, side: int) -> int:
    """Sum HIT_SELF_CONFUSION damage for the given side. Returns 0 when none fired."""
    return sum(e["damage"] for e in capturing.all_of(LogEvent.HIT_SELF_CONFUSION, side=side))
