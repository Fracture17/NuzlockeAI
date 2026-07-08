# Quick Draw micro-stage: INTENTIONAL C++-only divergence.
#
# Python's _action_sort_key fires Quick Draw only when secondary_threshold <= 30.0 and has NO
# random_mode branch; under LuckGroup.RANDOM the profile keeps secondary_threshold=50.0, so
# Python NEVER fires Quick Draw in random_mode. C++ intentionally diverges: in random_mode it
# fires Quick Draw with a 30% native-RNG draw. Controlled (non-random) mode is UNCHANGED and
# matches Python (fires only when secondary_threshold <= 30.0). See
# RECORDS/INTENTIONAL_DIVERGENCES.md.
#
# Ordering is observed via a slow Quick Draw mon (side 0) vs a fast opponent (side 1), both hp=1
# with Tackle. Without Quick Draw the fast side moves first and KOs -> winner == 1. When Quick
# Draw fires, side 0 jumps ahead (speed forced to 9999) and wins -> winner == 0.
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.abilities import Ability
from liveplay.data.moves import Move
from liveplay.data.species import Species

from tests.state_builders import make_mon, make_battle


def _random_luck_dict() -> dict:
    return {
        "accuracy_threshold": 50.0, "crit_threshold": 50.0, "damage_roll": 0.5,
        "proc_threshold": 50.0, "secondary_threshold": 50.0, "multi_hit_roll": 0.5,
        "rampage_duration_roll": 0.5, "psywave_roll": 0.5, "flinch_threshold": 50.0,
        "binding_duration_roll": 0.5, "wake_threshold": 50.0, "defrost_threshold": 20.0,
        "paralysis_threshold": 50.0, "confusion_snap_threshold": 50.0,
        "confusion_self_hit_threshold": 50.0, "attract_threshold": 50.0,
        "damage_rolls_per_hit": None, "crits_per_hit": None, "random_mode": True,
    }


def _turn_luck_dict(random_mode: bool, secondary_threshold: float = 50.0) -> dict:
    return {
        "quick_claw_threshold": 50.0,
        "secondary_threshold": secondary_threshold,
        "luck_tier": 1,
        "random_mode": random_mode,
    }


def _run_game(state, seed, turn_random_mode, secondary_threshold=50.0, max_turns=50):
    payload = json.dumps({
        "state": sweep_io.to_jsonable(state),
        "seed": seed,
        "luck_p0": _random_luck_dict(),
        "luck_p1": _random_luck_dict(),
        "turn_luck_p0": _turn_luck_dict(turn_random_mode, secondary_threshold),
        "turn_luck_p1": _turn_luck_dict(turn_random_mode, secondary_threshold),
        "max_turns": max_turns,
    })
    return json.loads(cpp.run_game(payload))


def _qd_vs_fast_battle():
    """Slow Quick Draw mon (side 0) vs fast opponent (side 1); both hp=1, Tackle.
    No Quick Draw -> side 1 (faster) moves first and wins. Quick Draw fires -> side 0 wins."""
    qd = make_mon(Species.MACHOP, moves=(Move.TACKLE,), ability=Ability.QUICK_DRAW, level=5, hp=1)
    fast = make_mon(Species.MACHOP, moves=(Move.TACKLE,), level=50, hp=1)
    return make_battle(qd, fast)


# ---------------------------------------------------------------------------
# 1. random_mode: Quick Draw fires ~30% (intentional divergence), no boundary
# ---------------------------------------------------------------------------

def test_quick_draw_random_mode_fires_about_30pct():
    state = _qd_vs_fast_battle()
    winners = [_run_game(state, s, turn_random_mode=True)["winner"] for s in range(300)]
    # side 0 wins iff Quick Draw fired that game.
    frac_qd = winners.count(0) / len(winners)
    assert 0 in winners, "Quick Draw never fired in random_mode"
    assert 1 in winners, "Quick Draw fired every game — should be ~30%, not 100%"
    assert 0.20 < frac_qd < 0.40, f"Quick Draw fire-rate {frac_qd:.2f} not ~0.30"


def test_quick_draw_random_mode_no_unported():
    state = _qd_vs_fast_battle()
    for seed in range(20):
        result = _run_game(state, seed, turn_random_mode=True)
        assert not result["status"].startswith("unported:"), result["status"]
        assert result["status"] == "completed"
        assert result["winner"] in (0, 1)


def test_quick_draw_random_mode_deterministic():
    state = _qd_vs_fast_battle()
    for seed in (3, 17, 99):
        r1 = _run_game(state, seed, turn_random_mode=True)
        r2 = _run_game(state, seed, turn_random_mode=True)
        assert r1["winner"] == r2["winner"], f"seed={seed} non-deterministic"


# ---------------------------------------------------------------------------
# 2. controlled mode UNCHANGED (matches Python): fires iff secondary_threshold <= 30
# ---------------------------------------------------------------------------

def test_quick_draw_controlled_high_threshold_never_fires():
    # secondary_threshold=50 (>30) -> Quick Draw never fires -> fast side 1 always wins.
    state = _qd_vs_fast_battle()
    for seed in range(10):
        result = _run_game(state, seed, turn_random_mode=False, secondary_threshold=50.0)
        assert result["status"] == "completed", result["status"]
        assert result["winner"] == 1, f"seed={seed}: QD must NOT fire at threshold 50"


def test_quick_draw_controlled_low_threshold_always_fires():
    # secondary_threshold=0 (<=30, GOOD) -> Quick Draw always fires -> slow side 0 always wins.
    state = _qd_vs_fast_battle()
    for seed in range(10):
        result = _run_game(state, seed, turn_random_mode=False, secondary_threshold=0.0)
        assert result["status"] == "completed", result["status"]
        assert result["winner"] == 0, f"seed={seed}: QD must fire at threshold 0 (GOOD)"
