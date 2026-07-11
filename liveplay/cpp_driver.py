# Engine-free C++ bridge helpers. Serializes Python types to the C++ binding's expected payload
# shapes and routes single deterministic turns through the C++ run_one_turn binding.
# Does NOT import Simulator or any Python engine module.
from __future__ import annotations

import json
import os

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
    }


# ---------------------------------------------------------------------------
# Per-turn C++ driver
# ---------------------------------------------------------------------------

class UnportedTurn(RuntimeError):
    """Raised when the C++ core reports an `unported:` boundary for this turn."""


def run_one_turn_cpp(state: BattleState,
                     action_p0: Action, action_p1: Action,
                     luck_p0: LuckProfile, luck_p1: LuckProfile,
                     *, mega_p0: bool = False, mega_p1: bool = False,
                     speed_tie_order: list[tuple[int, int]] | None = None) -> BattleState:
    """Run one deterministic single turn through the C++ run_one_turn binding.

    speed_tie_order: optional forced act-order for a controlled cross-side speed tie, as a list
    of (side, slot) pairs (earlier = acts first). When given, the tie is resolved by this ordering
    instead of the binding throwing NeedsRNG — the sweep replay layer's SPEED_TIE force-injection
    (mirrors OLD pre_rng_inject[SPEED_TIE]). None → the binding throws on an unresolved tie.

    Raises UnportedTurn for an `unported:` boundary; re-raises anything else.
    """
    import nuzlocke_engine_cpp as cpp

    payload = {
        "state": sweep_io.to_jsonable(state),
        "action_p0": action_payload(action_p0),
        "action_p1": action_payload(action_p1),
        "luck_p0": damage_luck_payload(luck_p0),
        "luck_p1": damage_luck_payload(luck_p1),
        "turn_luck_p0": turn_luck_payload(luck_p0),
        "turn_luck_p1": turn_luck_payload(luck_p1),
        "mega_p0": mega_p0,
        "mega_p1": mega_p1,
    }
    if speed_tie_order is not None:
        payload["speed_tie_order"] = [[int(side), int(slot)] for side, slot in speed_tie_order]
    try:
        out_json = cpp.run_one_turn(json.dumps(payload))
    except Exception as exc:  # noqa: BLE001 — classify by message, re-raise non-unported.
        if str(exc).startswith("unported:"):
            raise UnportedTurn(str(exc)) from exc
        raise
    decoded = json.loads(out_json)
    return sweep_io.from_jsonable(decoded["state"])


def bridge_strict_enabled() -> bool:
    """True when BRIDGE_STRICT is set to a truthy value."""
    val = os.environ.get("BRIDGE_STRICT", "")
    return val not in ("", "0", "false", "False")
