# Engine-free C++ bridge helpers. Serializes Python types to the C++ binding's expected payload
# shapes and routes single deterministic turns through the C++ run_one_turn binding.
# Does NOT import Simulator or any Python engine module.
from __future__ import annotations

import json
import os
from typing import Sequence, Union

import liveplay.sweep_io as sweep_io
from liveplay.actions import Action, ActionKind
from liveplay.rng import LuckProfile
from liveplay.state.battle import BattleState


# ---------------------------------------------------------------------------
# Serialization to the C++ run_one_turn payload (single source of truth; the C1.7e
# parity test demonstrates the exact shapes the binding expects).
# ---------------------------------------------------------------------------

def damage_luck_payload(luck: LuckProfile) -> dict:
    """Serialize a LuckProfile to the DamageLoopLuck dict the C++ binding expects."""
    return {
        "accuracy_threshold": luck.accuracy_threshold,
        "crit_threshold": luck.crit_threshold,
        "damage_roll": luck.damage_roll,
        "proc_threshold": luck.proc_threshold,
        "secondary_threshold": luck.secondary_threshold,
        "multi_hit_roll": luck.multi_hit_roll,
        "rampage_duration_roll": luck.rampage_duration_roll,
        "psywave_roll": luck.psywave_roll,
        "flinch_threshold": luck.flinch_threshold,
        "binding_duration_roll": luck.binding_duration_roll,
        "wake_threshold": luck.wake_threshold,
        "defrost_threshold": luck.defrost_threshold,
        "paralysis_threshold": luck.paralysis_threshold,
        "confusion_snap_threshold": luck.confusion_snap_threshold,
        "confusion_self_hit_threshold": luck.confusion_self_hit_threshold,
        "attract_threshold": luck.attract_threshold,
        "damage_rolls_per_hit": list(luck.damage_rolls_per_hit) if luck.damage_rolls_per_hit is not None else None,
        "crits_per_hit": list(luck.crits_per_hit) if luck.crits_per_hit is not None else None,
        "random_mode": luck.random_mode,
    }


def turn_luck_payload(luck: LuckProfile) -> dict:
    """Serialize a LuckProfile to the TurnLuck dict the C++ binding expects."""
    return {
        "quick_claw_threshold": luck.quick_claw_threshold,
        "secondary_threshold": luck.secondary_threshold,
        "luck_tier": luck.luck_tier,
        "random_mode": luck.random_mode,
    }


def action_payload(action: Action) -> dict:
    """Serialize a Python Action to the flat action dict the C++ binding expects.

    move_override is an enum (or None); the binding takes its int value or -1.
    source_slot identifies which active slot within the side this action originates from
    (0 for singles; 0 or 1 for doubles). Omitting it causes the C++ codec to default to 0,
    silently breaking doubles slot-1 actions.
    """
    override = action.move_override
    override_int = int(override) if override is not None else -1
    return {
        "kind": int(action.kind),
        "move_slot": action.move_slot,
        "move_override": override_int,
        "switch_to_slot": action.switch_to_slot,
        "target_side": action.target_side,
        "target_slot": action.target_slot,
        # mega rides on the action so forced-trace replay (GameDriver) can rebuild the
        # per-turn mega_pX scalars; run_one_turn callers still pass mega_p0/p1 separately.
        "mega": bool(action.mega),
        "source_slot": action.source_slot,
    }


# ---------------------------------------------------------------------------
# Per-turn C++ driver
# ---------------------------------------------------------------------------

class UnportedTurn(RuntimeError):
    """Raised when the C++ core reports an `unported:` boundary for this turn."""


def run_one_turn_cpp(
    state: BattleState,
    action_p0: Union[Action, Sequence[Action]],
    action_p1: Union[Action, Sequence[Action]],
    luck_p0: LuckProfile,
    luck_p1: LuckProfile,
    *,
    mega_p0: bool = False,
    mega_p1: bool = False,
    speed_tie_order: list[tuple[int, int]] | None = None,
    finalize_on_post_faint: bool = False,
    luck_p0_slot1: LuckProfile | None = None,
    luck_p1_slot1: LuckProfile | None = None,
    pre_inject: dict[str, int] | None = None,
) -> BattleState:
    """Run one deterministic turn through the C++ run_one_turn binding.

    action_p0 / action_p1 accept either a single Action (singles, back-compat) or a
    sequence of Actions (doubles). A single Action produces a flat dict; a sequence
    produces a JSON array — both shapes are accepted by the binding.

    speed_tie_order: optional forced act-order for a controlled cross-side speed tie, as a
    list of (side, slot) pairs (earlier = acts first). None → binding throws on unresolved tie.

    finalize_on_post_faint: when True, a fainted active with a live bench finalizes in place
    instead of raising UnportedTurn("unported: post_faint_switch"). Use apply_switch_cpp
    between turns to bring in the replacement.

    luck_p0_slot1 / luck_p1_slot1: optional per-slot-1 attacker luck for doubles. When None,
    the key is omitted from the payload entirely → C++ uses the side-level luck for all slots
    (absent key → nullptr → byte-identical engine path).

    pre_inject: optional plain-mode sweep hook for Category-A RNG events. Maps event name
    strings to engine-native int values. Supported names: METRONOME_MOVE, SLEEP_TALK_MOVE,
    EFFECT_SPORE_WHICH, ACUPRESSURE_STAT, ROAR_TARGET, TRI_ATTACK_STATUS. Sticky/non-consuming.
    None → key omitted → nullptr → byte-identical engine path.

    Raises UnportedTurn for an `unported:` boundary; re-raises anything else.
    """
    import nuzlocke_engine_cpp as cpp

    def _encode_actions(actions: Union[Action, Sequence[Action]]):
        if isinstance(actions, Action):
            return action_payload(actions)
        return [action_payload(a) for a in actions]

    payload = {
        "state": sweep_io.to_jsonable(state),
        "action_p0": _encode_actions(action_p0),
        "action_p1": _encode_actions(action_p1),
        "luck_p0": damage_luck_payload(luck_p0),
        "luck_p1": damage_luck_payload(luck_p1),
        "turn_luck_p0": turn_luck_payload(luck_p0),
        "turn_luck_p1": turn_luck_payload(luck_p1),
        "mega_p0": mega_p0,
        "mega_p1": mega_p1,
        "finalize_on_post_faint": finalize_on_post_faint,
    }
    if speed_tie_order is not None:
        payload["speed_tie_order"] = [[int(side), int(slot)] for side, slot in speed_tie_order]
    # Omit slot-1 luck keys entirely when None — absent key → nullptr → identical C++ path.
    if luck_p0_slot1 is not None:
        payload["luck_p0_slot1"] = damage_luck_payload(luck_p0_slot1)
    if luck_p1_slot1 is not None:
        payload["luck_p1_slot1"] = damage_luck_payload(luck_p1_slot1)
    # Omit pre_inject key entirely when None — absent key → nullptr → byte-identical C++ path.
    if pre_inject is not None:
        payload["pre_inject"] = {str(k): int(v) for k, v in pre_inject.items()}
    try:
        out_json = cpp.run_one_turn(json.dumps(payload))
    except Exception as exc:  # noqa: BLE001 — classify by message, re-raise non-unported.
        if str(exc).startswith("unported:"):
            raise UnportedTurn(str(exc)) from exc
        raise
    decoded = json.loads(out_json)
    return sweep_io.from_jsonable(decoded["state"])


def apply_switch_cpp(
    state: BattleState,
    side_idx: int,
    new_slot: int,
    source_slot: int,
) -> BattleState:
    """Apply a post-faint switch via the C++ binding and return the updated BattleState.

    Runs switch-out reset, entry hazards, and entry effects. Transfers Baton Pass state
    if has_baton_pass_data is set. The binding returns the mutated state JSON directly
    (not wrapped in {"state": ...}).
    """
    import nuzlocke_engine_cpp as cpp

    state_json = json.dumps(sweep_io.to_jsonable(state))
    out_json = cpp.apply_switch(state_json, side_idx, new_slot, source_slot)
    return sweep_io.from_jsonable(json.loads(out_json))


def bridge_strict_enabled() -> bool:
    """True when BRIDGE_STRICT is set to a truthy value."""
    val = os.environ.get("BRIDGE_STRICT", "")
    return val not in ("", "0", "false", "False")
