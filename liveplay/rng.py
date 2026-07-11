# RNG control layer: deterministic outcome resolution via LuckProfile thresholds and rolls.
import logging
import math
import random
from collections import Counter
from contextlib import contextmanager
import dataclasses
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import liveplay.rng_trace as rng_trace

logger = logging.getLogger(__name__)

# Stack of per-context Counters for deduping warn_uninjected log lines. While non-empty,
# _strict_check buffers each uninjected-event warning (keyed by its exact rendered text)
# into the innermost counter instead of logging it eagerly; the context flushes one
# WARNING per unique text with its occurrence count on exit. The sweep wraps each decision
# boundary so the hundreds of identical per-candidate re-simulation warnings collapse into
# a single deduped summary. Empty stack ⇒ unchanged eager per-call logging.
_warn_aggregation_stack: list = []


@contextmanager
def aggregate_uninjected_warnings():
    """Collapse warn_uninjected log lines emitted within the block into a per-text summary.

    Each unique rendered warning (event name + side) is counted; on exit one WARNING per
    unique text is logged, tagged with how many times it occurred during the block. Nesting
    is supported (each context owns its own counter and flushes independently)."""
    counter: Counter = Counter()
    _warn_aggregation_stack.append(counter)
    try:
        yield
    finally:
        _warn_aggregation_stack.pop()
        for text, count in counter.items():
            logger.warning("%s [x%d]", text, count)


# ε-mixture flattening: in random_mode, Bernoullis/categoricals mix in a uniform draw with
# probability ε. At ε=0 the path is never entered, preserving exact draw order.
_flatten_eps: float = 0.0


def set_flatten_eps(eps: float) -> None:
    """Set the global ε for mixture flattening. Must be in [0.0, 1.0]."""
    global _flatten_eps
    if not (0.0 <= eps <= 1.0):
        raise ValueError(f"eps must be in [0.0, 1.0], got {eps!r}")
    _flatten_eps = eps


def get_flatten_eps() -> float:
    """Return the current global ε."""
    return _flatten_eps


def _maybe_record(event: "RNGEvent", outcome: object) -> object:
    """Record outcome to the active TraceRecorder (if any) and return it unchanged."""
    rec = rng_trace.get_recorder()
    if rec is not None:
        rec.record(event, outcome)
    return outcome


def _roll_bernoulli(event: "RNGEvent", chance_pct: float) -> bool:
    """Single Bernoulli draw: True with probability chance_pct/100. Supports ε-flattening.
    Saturated cases (chance_pct <= 0 or >= 100) bypass flattening — callers must guard."""
    if _flatten_eps > 0.0 and 0.0 < chance_pct < 100.0 and random.random() < _flatten_eps:
        outcome = random.random() < 0.5
    else:
        outcome = random.random() * 100 < chance_pct
    return _maybe_record(event, outcome)


def _roll_categorical(event: "RNGEvent", options: list, weights: list = None) -> object:
    """Categorical draw from options (with optional weights). Supports ε-flattening to uniform.
    Raises ValueError if len(options) < 2 — callers must short-circuit single-option cases."""
    if len(options) < 2:
        raise ValueError(f"_roll_categorical requires at least 2 options, got {len(options)}")
    if _flatten_eps > 0.0 and random.random() < _flatten_eps:
        outcome = random.choice(options)
    elif weights is not None:
        outcome = random.choices(options, weights=weights)[0]
    else:
        outcome = random.choice(options)
    return _maybe_record(event, outcome)


def _roll_uniform(event: "RNGEvent") -> float:
    """Uniform [0, 1) draw. Not flattened — uniform IS its own flat distribution."""
    return _maybe_record(event, random.random())


def _saturated(chance: float, *, high: bool, low: bool) -> "bool | None":
    """Saturation short-circuit shared by resolve_* rolls.
    Returns `high` when chance>=100, `low` when chance<=0, else None (a roll is needed)."""
    if chance >= 100:
        return high
    if chance <= 0:
        return low
    return None


class UninjectedRNGError(Exception):
    """Raised when a strict LuckProfile encounters an RNG event that was not pre-injected."""

    def __init__(self, event: "RNGEvent", side: "Optional[int]" = None, context: "Optional[str]" = None):
        self.event = event
        self.side = side
        self.context = context
        side_str = f" (side {side})" if side is not None else ""
        super().__init__(f"Uninjected RNG event: {event.name}{side_str}")


class LuckGroup(Enum):
    """High-level luck category; maps to a LuckProfile preset via luck_group_to_profile."""
    GOOD = "good"
    BAD = "bad"
    AVERAGE = "average"
    RANDOM = "random"


class RNGEvent(Enum):
    """Enumeration of all RNG events, split by simulator break behavior.

    Category B events are controlled by LuckProfile and produce no break.
    Category A events are uncontrolled (use random.randint/choice) and cause simulator breaks.
    """
    # Category B — controlled by luck groups (no break)
    ACCURACY = auto()
    CRIT = auto()
    SECONDARY_FIRES = auto()
    PROC_FIRES = auto()           # ability/item/misc procs (Focus Band, Shed Skin, etc.)
    DAMAGE_ROLL = auto()
    PSYWAVE_ROLL = auto()
    MULTI_HIT_COUNT = auto()
    WAKE = auto()
    CONFUSION_SNAP = auto()
    DEFROST = auto()
    CONFUSION_SELF_HIT = auto()
    ATTRACT_IMMOBILIZE = auto()
    FULL_PARALYSIS = auto()
    FLINCH = auto()
    QUICK_CLAW = auto()
    ANCIENT_POWER_BOOST = auto()
    BINDING_DURATION = auto()
    RAMPAGE_DURATION = auto()

    # Category A — uncontrolled (cause breaks in Simulator)
    ACTION_SELECT = auto()
    FORCED_SWITCH = auto()
    POST_FAINT_SWITCH = auto()
    METRONOME_MOVE = auto()
    SLEEP_TALK_MOVE = auto()
    ASSIST_MOVE = auto()
    ACUPRESSURE_STAT = auto()
    ROAR_TARGET = auto()
    EFFECT_SPORE_WHICH = auto()
    TRI_ATTACK_STATUS = auto()
    MOODY_STATS = auto()
    STARF_BERRY_STAT = auto()
    SPEED_TIE = auto()         # Which side moves first on an equal-speed tie (0 or 1)

    # Category B; appended out of section order because RngEventC (cpp/src/oracle.h) requires stable int values.
    SPEED_TIEBREAKER = auto()  # Per-action uniform tiebreaker replacing resolve_speed_tie_between in the engine
    RANDOM_TARGET = auto()     # RANDOM_NORMAL move target selection (uniform over foe slots)


@dataclass
class LuckProfile:
    accuracy_threshold: float = 50.0
    crit_threshold: float = 50.0
    secondary_threshold: float = 50.0
    proc_threshold: float = 50.0    # ability/item proc rolls; independently injectable from secondary
    damage_roll: float = 0.5        # 0.0=min, 1.0=max
    psywave_roll: float = 0.5       # 0.0→roll 50, 1.0→roll 150
    damage_rolls_per_hit: Optional[tuple[float, ...]] = None  # per-hit override; None = use damage_roll
    crits_per_hit: Optional[tuple[float, ...]] = None  # per-hit crit threshold; None = use crit_threshold
    multi_hit_roll: float = 0.5     # 0.0=min hits, 1.0=max hits
    luck_tier: int = 1              # 0=bad, 1=average, 2=good; higher tier wins speed ties

    # Per-turn duration checks (threshold: fire if chance >= threshold)
    wake_threshold: float = 50.0
    confusion_snap_threshold: float = 50.0
    defrost_threshold: float = 20.0

    # Per-turn status checks (threshold: fire if chance >= threshold)
    confusion_self_hit_threshold: float = 50.0
    attract_threshold: float = 50.0
    paralysis_threshold: float = 50.0

    # Duration-as-roll (determined on application)
    binding_duration_roll: float = 0.5   # 0.0→4 turns, 1.0→5 turns
    rampage_duration_roll: float = 0.5   # 0.0→2 turns, 1.0→3 turns

    flinch_threshold: float = 50.0
    quick_claw_threshold: float = 50.0
    ancient_power_boost_threshold: float = 50.0

    # When True, all resolve functions use random.random() instead of threshold comparisons
    random_mode: bool = False

    # Strict mode: raise UninjectedRNGError for any event not in `injected`.
    strict: bool = False
    # Warn mode: un-injected Category-B events log WARNING and resolve via base defaults,
    # EXCEPT ACCURACY which still raises. Mutually exclusive with strict in practice.
    warn_uninjected: bool = False
    injected: frozenset = field(default_factory=frozenset)  # RNGEvent members pre-injected for this turn
    side: Optional[int] = None      # which side this profile belongs to (for error attribution)


# Preset profiles
GOOD_LUCK = LuckProfile(
    accuracy_threshold=0.0,
    crit_threshold=0.0,
    secondary_threshold=0.0,
    proc_threshold=0.0,
    damage_roll=1.0,
    psywave_roll=1.0,
    multi_hit_roll=1.0,
    luck_tier=2,
    wake_threshold=0.0,
    confusion_snap_threshold=0.0,
    defrost_threshold=0.0,
    confusion_self_hit_threshold=0.0,
    attract_threshold=0.0,
    paralysis_threshold=0.0,
    binding_duration_roll=1.0,
    rampage_duration_roll=1.0,
    flinch_threshold=0.0,
    quick_claw_threshold=0.0,
    ancient_power_boost_threshold=0.0,
)

BAD_LUCK = LuckProfile(
    accuracy_threshold=101.0,
    crit_threshold=100.0,
    secondary_threshold=101.0,
    proc_threshold=101.0,
    damage_roll=0.0,
    psywave_roll=0.0,
    multi_hit_roll=0.0,
    luck_tier=0,
    wake_threshold=101.0,
    confusion_snap_threshold=101.0,
    defrost_threshold=101.0,
    confusion_self_hit_threshold=101.0,
    attract_threshold=101.0,
    paralysis_threshold=101.0,
    binding_duration_roll=0.0,
    rampage_duration_roll=0.0,
    flinch_threshold=101.0,
    quick_claw_threshold=101.0,
    ancient_power_boost_threshold=101.0,
)

AVERAGE_LUCK = LuckProfile(
    accuracy_threshold=50.0,
    crit_threshold=50.0,
    secondary_threshold=50.0,
    proc_threshold=50.0,
    damage_roll=1.0,
    psywave_roll=0.5,
    multi_hit_roll=0.5,
    luck_tier=1,
    wake_threshold=50.0,
    confusion_snap_threshold=50.0,
    defrost_threshold=50.0,
    confusion_self_hit_threshold=50.0,
    attract_threshold=50.0,
    paralysis_threshold=50.0,
    binding_duration_roll=0.5,
    rampage_duration_roll=0.5,
    flinch_threshold=50.0,
    quick_claw_threshold=50.0,
    ancient_power_boost_threshold=50.0,
)


STRICT_LUCK = LuckProfile(strict=True)


# Sweep base: a SILENT-default profile. Every Category-B RNG event defaults to the
# outcome that produces NO visible battle message; the message matcher then injects
# only the VISIBLE (message-bearing) outcomes it actually observes. warn_uninjected
# keeps un-injected events logging instead of crashing.
#
# Built from BAD_LUCK (whose no-fire defaults are already silent for crit/secondary/
# proc/flinch/wake/snap/defrost/etc.), flipping the 4 events whose BAD default EMITS a
# message to their silent direction:
#   accuracy_threshold=0.0          -> hit (BAD=miss, "It missed!")
#   paralysis_threshold=0.0         -> can act (BAD="is fully paralyzed!")
#   attract_threshold=0.0           -> can act (BAD="immobilized by love!")
#   confusion_self_hit_threshold=0.0-> no self-hit (BAD="hurt itself in confusion!")
#
# Hidden-duration rolls (Bind/Rampage) are NOT silent-vs-visible: the duration is invisible
# until an END message fires (PKMNFREEDFROM / PKMNFATIGUECONFUSION). Assuming the SHORTEST
# duration under-counts ticks and crashes the sweep on a real tick the engine thinks is over.
# So assume the MAXIMUM duration and trim via the observed end-message handlers instead:
#   binding_duration_roll=1.0  -> Bind lasts 5 turns (Grip Claw still forces 7 regardless)
#   rampage_duration_roll=1.0  -> Thrash/Outrage/Petal Dance lasts 3 turns
#
# warn_uninjected/strict/injected are NEW LuckProfile fields (present in this codebase).
# In OLD Python-path code these were Simulator-internal; here they live directly on the profile.
# The sweep wrapper should still configure warn_uninjected=True to collapse un-injected-event
# warnings per boundary.
SWEEP_LUCK = dataclasses.replace(
    BAD_LUCK,
    warn_uninjected=True,
    accuracy_threshold=0.0,
    paralysis_threshold=0.0,
    attract_threshold=0.0,
    confusion_self_hit_threshold=0.0,
    binding_duration_roll=1.0,
    rampage_duration_roll=1.0,
)


def _strict_check(event: "RNGEvent", profile: LuckProfile) -> bool:
    """Guard for un-injected Category-B events. Returns True if the caller should fall through to base default.

    - strict mode: raises UninjectedRNGError for any un-injected event.
    - warn mode: logs WARNING and returns True for every event so callers skip resolution.
    - Normal profiles: no-op, returns False.

    Note: warn mode no longer special-cases ACCURACY. Under the silent-default sweep
    profile (SWEEP_LUCK) accuracy defaults to a HIT (the no-message outcome), so the
    old ACCURACY raise — which existed only because BAD's miss default was wrong-way —
    is obsolete. Observed misses are still injected (ACCURACY=False) by the matcher.
    """
    if event in profile.injected:
        return False
    if profile.strict:
        raise UninjectedRNGError(event, profile.side)
    if profile.warn_uninjected:
        text = (
            "Uninjected Category-B RNG event consumed under warn profile: "
            f"{event.name} (side {profile.side})"
        )
        if _warn_aggregation_stack:
            # Inside an aggregation context: buffer by exact text, flush as a counted
            # summary on context exit (see aggregate_uninjected_warnings).
            _warn_aggregation_stack[-1][text] += 1
        else:
            logger.warning("%s", text)
        return True
    return False


def luck_group_to_profile(group: LuckGroup) -> LuckProfile:
    """Maps a LuckGroup enum to the corresponding LuckProfile preset."""
    _MAP = {
        LuckGroup.GOOD: GOOD_LUCK,
        LuckGroup.BAD: BAD_LUCK,
        LuckGroup.AVERAGE: AVERAGE_LUCK,
        LuckGroup.RANDOM: LuckProfile(random_mode=True),
    }
    return _MAP[group]


def resolve_accuracy(effective_accuracy: Optional[float], profile: LuckProfile) -> bool:
    """Returns True if the move hits. effective_accuracy=None means never-misses."""
    if effective_accuracy is None:
        return True           # always-hit moves (Swift, Aerial Ace, etc.)
    if effective_accuracy >= 100:
        return True           # can't miss
    if effective_accuracy <= 0:
        return False          # can't hit
    _strict_check(RNGEvent.ACCURACY, profile)
    if profile.random_mode:
        return _roll_bernoulli(RNGEvent.ACCURACY, effective_accuracy)
    return effective_accuracy >= profile.accuracy_threshold


def resolve_crit(effective_crit_chance: float, profile: LuckProfile) -> bool:
    """Returns True if the hit is a critical hit.
    effective_crit_chance of 1.0 is the Laser Focus sentinel from _get_crit_chance
    (damage.py returns 1.0 instead of 100.0 for Laser Focus); treated as guaranteed
    unless the profile has crit_threshold > 100 (i.e. Lucky Chant suppression)."""
    if effective_crit_chance <= 0:
        return False          # ability blocks crits entirely (e.g. Shell Armor)
    # Laser Focus sentinel: 1.0 means guaranteed crit, but Lucky Chant (threshold > 100) still blocks it
    if effective_crit_chance == 1.0 and profile.crit_threshold <= 100.0:
        return True
    _strict_check(RNGEvent.CRIT, profile)
    if profile.random_mode:
        return _roll_bernoulli(RNGEvent.CRIT, effective_crit_chance)
    return effective_crit_chance >= profile.crit_threshold


def resolve_secondary(chance: int, profile: LuckProfile,
                      event: "RNGEvent" = None) -> bool:
    """Returns True if the secondary effect fires. chance is 0-100.
    Pass event=RNGEvent.PROC_FIRES at ability/item proc sites to keep them independently injectable."""
    if event is None:
        event = RNGEvent.SECONDARY_FIRES
    sat = _saturated(chance, high=True, low=False)
    if sat is not None:
        return sat
    _strict_check(event, profile)
    if profile.random_mode:
        return _roll_bernoulli(event, chance)
    return chance >= profile.secondary_threshold


def resolve_proc(chance: int, profile: LuckProfile) -> bool:
    """Ability/item proc rolls. Uses proc_threshold (not secondary_threshold) for independent injection."""
    sat = _saturated(chance, high=True, low=False)
    if sat is not None:
        return sat
    _strict_check(RNGEvent.PROC_FIRES, profile)
    if profile.random_mode:
        return _roll_bernoulli(RNGEvent.PROC_FIRES, chance)
    return chance >= profile.proc_threshold


def resolve_damage_roll(profile: LuckProfile) -> float:
    """Returns the damage roll as a float 0.0-1.0 (0.0=min, 1.0=max)."""
    _strict_check(RNGEvent.DAMAGE_ROLL, profile)
    if profile.random_mode:
        return _roll_uniform(RNGEvent.DAMAGE_ROLL)
    return profile.damage_roll


def resolve_psywave_roll(profile: LuckProfile) -> float:
    """Returns the Psywave roll as a float 0.0-1.0 (0.0→roll 50, 1.0→roll 150)."""
    _strict_check(RNGEvent.PSYWAVE_ROLL, profile)
    if profile.random_mode:
        return _roll_uniform(RNGEvent.PSYWAVE_ROLL)
    return profile.psywave_roll


def resolve_multi_hit(min_hits: int, max_hits: int, profile: LuckProfile) -> int:
    """Returns the number of hits for multi-hit moves.
    For the standard 2–5 range, uses Gen 5+ weighted distribution: 35/35/15/15.
    Other ranges use linear interpolation (round-half-up)."""
    if min_hits == max_hits:
        return min_hits
    _strict_check(RNGEvent.MULTI_HIT_COUNT, profile)
    if min_hits == 2 and max_hits == 5:
        if profile.random_mode:
            return _roll_categorical(RNGEvent.MULTI_HIT_COUNT, [2, 3, 4, 5], weights=[35, 35, 15, 15])
        r = profile.multi_hit_roll
        if r < 0.35:
            return 2
        if r < 0.70:
            return 3
        if r < 0.85:
            return 4
        return 5
    if profile.random_mode:
        return _roll_categorical(RNGEvent.MULTI_HIT_COUNT, list(range(min_hits, max_hits + 1)))
    span = max_hits - min_hits
    return math.floor(min_hits + profile.multi_hit_roll * span + 0.5)


def resolve_speed_tie_between(profile_a: LuckProfile, profile_b: LuckProfile, a_is_player: bool) -> bool:
    """Returns True if side A moves first on a speed tie.
    Higher luck_tier wins. If equal, the player (a_is_player=True for side A) goes first.
    In random_mode (either profile), 50/50.
    """
    if profile_a.random_mode or profile_b.random_mode:
        return _roll_bernoulli(RNGEvent.SPEED_TIE, 50.0)
    if profile_a.luck_tier != profile_b.luck_tier:
        return profile_a.luck_tier > profile_b.luck_tier
    return a_is_player  # player goes first on equal tier


def resolve_wake(wake_chance: float, profile: LuckProfile) -> bool:
    """Returns True if the Pokemon wakes up this turn. Per-turn check."""
    sat = _saturated(wake_chance, high=True, low=False)
    if sat is not None:
        return sat
    _strict_check(RNGEvent.WAKE, profile)
    if profile.random_mode:
        return _roll_bernoulli(RNGEvent.WAKE, wake_chance)
    return wake_chance >= profile.wake_threshold


def resolve_confusion_snap(snap_chance: float, profile: LuckProfile) -> bool:
    """Returns True if the Pokemon snaps out of confusion this turn. Per-turn check."""
    sat = _saturated(snap_chance, high=True, low=False)
    if sat is not None:
        return sat
    _strict_check(RNGEvent.CONFUSION_SNAP, profile)
    if profile.random_mode:
        return _roll_bernoulli(RNGEvent.CONFUSION_SNAP, snap_chance)
    return snap_chance >= profile.confusion_snap_threshold


def resolve_defrost(thaw_chance: float, profile: LuckProfile) -> bool:
    """Returns True if the Pokemon thaws this turn. Per-turn check."""
    sat = _saturated(thaw_chance, high=True, low=False)
    if sat is not None:
        return sat
    _strict_check(RNGEvent.DEFROST, profile)
    if profile.random_mode:
        return _roll_bernoulli(RNGEvent.DEFROST, thaw_chance)
    return thaw_chance >= profile.defrost_threshold


_CONFUSION_NO_SELF_HIT_CHANCE = 66.7  # base probability of NOT hitting yourself in confusion


def resolve_confusion_self_hit(profile: LuckProfile) -> bool:
    """Returns True if the Pokemon does NOT hit itself in confusion (good outcome).
    Base probability: 66.7% chance of not self-hitting.
    GOOD_LUCK threshold=0.0: 66.7 >= 0.0 → True (never self-hits).
    BAD_LUCK threshold=101.0: 66.7 >= 101.0 → False (always self-hits).
    """
    _strict_check(RNGEvent.CONFUSION_SELF_HIT, profile)
    if profile.random_mode:
        return _roll_bernoulli(RNGEvent.CONFUSION_SELF_HIT, _CONFUSION_NO_SELF_HIT_CHANCE)
    return _CONFUSION_NO_SELF_HIT_CHANCE >= profile.confusion_self_hit_threshold


def resolve_attract(chance: float, profile: LuckProfile) -> bool:
    """Returns True if the Pokemon CAN act despite Attract (good outcome).
    chance is the probability of being blocked (0–100).
    GOOD_LUCK threshold=0.0: chance >= 0.0 → True (never blocked).
    BAD_LUCK threshold=101.0: chance >= 101.0 → False (always blocked).
    """
    sat = _saturated(chance, high=False, low=True)
    if sat is not None:
        return sat
    _strict_check(RNGEvent.ATTRACT_IMMOBILIZE, profile)
    if profile.random_mode:
        return not _roll_bernoulli(RNGEvent.ATTRACT_IMMOBILIZE, chance)
    return chance >= profile.attract_threshold


def resolve_paralysis(chance: float, profile: LuckProfile) -> bool:
    """Returns True if the Pokemon CAN act despite full paralysis (good outcome).
    GOOD_LUCK threshold=0.0: always can act.
    BAD_LUCK threshold=101.0: always fully paralyzed.
    """
    sat = _saturated(chance, high=False, low=True)
    if sat is not None:
        return sat
    _strict_check(RNGEvent.FULL_PARALYSIS, profile)
    if profile.random_mode:
        return not _roll_bernoulli(RNGEvent.FULL_PARALYSIS, chance)
    return chance >= profile.paralysis_threshold


def resolve_binding_duration(profile: LuckProfile, attacker_item=None) -> int:
    """Returns the number of turns a binding move lasts (4 or 5; 7 if attacker holds Grip Claw)."""
    from liveplay.data.items import Item
    if attacker_item == Item.GRIP_CLAW:
        return 7
    _strict_check(RNGEvent.BINDING_DURATION, profile)
    if profile.random_mode:
        return _roll_categorical(RNGEvent.BINDING_DURATION, [4, 5])
    return 5 if profile.binding_duration_roll >= 0.5 else 4


def resolve_rampage_duration(profile: LuckProfile) -> int:
    """Returns turns for Thrash/Outrage/Petal Dance lock (2 or 3)."""
    _strict_check(RNGEvent.RAMPAGE_DURATION, profile)
    if profile.random_mode:
        return _roll_categorical(RNGEvent.RAMPAGE_DURATION, [2, 3])
    return 3 if profile.rampage_duration_roll >= 0.5 else 2


def resolve_flinch(chance: int, profile: LuckProfile) -> bool:
    """Returns True if the target flinches (King's Rock, Stench, etc.)."""
    sat = _saturated(chance, high=True, low=False)
    if sat is not None:
        return sat
    _strict_check(RNGEvent.FLINCH, profile)
    if profile.random_mode:
        return _roll_bernoulli(RNGEvent.FLINCH, chance)
    return chance >= profile.flinch_threshold


def resolve_quick_claw(profile: LuckProfile) -> bool:
    """Returns True if the Quick Claw item triggers (20% chance to move first in bracket)."""
    _strict_check(RNGEvent.QUICK_CLAW, profile)
    if profile.random_mode:
        return _roll_bernoulli(RNGEvent.QUICK_CLAW, 20.0)
    return profile.quick_claw_threshold <= 20.0


def resolve_ancient_power_boost(chance: int, profile: LuckProfile) -> bool:
    """Returns True if Ancient Power / Silver Wind / Ominous Wind boosts all stats."""
    sat = _saturated(chance, high=True, low=False)
    if sat is not None:
        return sat
    _strict_check(RNGEvent.ANCIENT_POWER_BOOST, profile)
    if profile.random_mode:
        return _roll_bernoulli(RNGEvent.ANCIENT_POWER_BOOST, chance)
    return chance >= profile.ancient_power_boost_threshold


def resolve_speed_tiebreaker(profile: LuckProfile) -> float:
    """Per-action speed-tie tiebreaker: uniform [0,1) in random_mode, else float(luck_tier)."""
    if profile.random_mode:
        return _roll_uniform(RNGEvent.SPEED_TIEBREAKER)
    return float(profile.luck_tier)


def resolve_random_target(foe_slots: list) -> object:
    """RANDOM_NORMAL target pick. len==1 → return it with no draw and no record;
    len>=2 → uniform categorical draw (no profile needed — uniform is its true distribution);
    empty list → ValueError (callers guard)."""
    if len(foe_slots) == 0:
        raise ValueError("resolve_random_target: foe_slots must be non-empty")
    if len(foe_slots) == 1:
        return foe_slots[0]
    return _roll_categorical(RNGEvent.RANDOM_TARGET, foe_slots)
