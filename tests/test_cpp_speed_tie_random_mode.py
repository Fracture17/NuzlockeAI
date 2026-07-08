# Stage A2: native-RNG turn-luck oracle ports (speed-tie tiebreaker + Quick Claw).
#
# These tests are written BEFORE implementation; they fail loudly until A2 is done.
# Scope (see RECORDS/C++Transition.md Stage A2):
#   - cpp_build_queue must resolve a genuine speed tie via NativeRng when the tying
#     side is in turn-luck random_mode (no "unported: SPEED_TIE oracle").
#   - resolve_quick_claw must draw rng->random() < 0.2 in random_mode.
#   - NON-random_mode ties MUST still throw "unported: SPEED_TIE oracle" so the
#     Phase-1 bridge keeps delegating injected ties to Python (bridge contract).
#
# Ordering is observed via a hp=1 mirror match: identical mons, identical speed,
# identical priority-0 move (Tackle, 100% acc -> saturated, no accuracy draw).
# The first mover's Tackle KOs the other before it acts, so winner == first mover.
# Parity is behavioural (RNG-broken ordering varies across seeds), NOT bitwise.
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.items import Item
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


def _turn_luck_dict(random_mode: bool = False, quick_claw_threshold: float = 50.0) -> dict:
    return {
        "quick_claw_threshold": quick_claw_threshold,
        "secondary_threshold": 50.0,
        "luck_tier": 1,
        "random_mode": random_mode,
    }


def _run_game(state, seed, turn_random_mode, quick_claw_threshold=50.0, max_turns=50):
    payload = json.dumps({
        "state": sweep_io.to_jsonable(state),
        "seed": seed,
        "luck_p0": _random_luck_dict(),
        "luck_p1": _random_luck_dict(),
        "turn_luck_p0": _turn_luck_dict(turn_random_mode, quick_claw_threshold),
        "turn_luck_p1": _turn_luck_dict(turn_random_mode, quick_claw_threshold),
        "max_turns": max_turns,
    })
    return json.loads(cpp.run_game(payload))


def _mirror_tie_battle():
    """Two identical mons, hp=1, both Tackle => guaranteed speed tie; winner == first mover."""
    m0 = make_mon(Species.MACHOP, moves=(Move.TACKLE,), level=50, hp=1)
    m1 = make_mon(Species.MACHOP, moves=(Move.TACKLE,), level=50, hp=1)
    return make_battle(m0, m1)


# ---------------------------------------------------------------------------
# 1. random_mode speed tie resolves cleanly (no unported boundary)
# ---------------------------------------------------------------------------

def test_speed_tie_random_mode_no_unported():
    state = _mirror_tie_battle()
    for seed in range(20):
        result = _run_game(state, seed, turn_random_mode=True)
        status = result["status"]
        assert not status.startswith("unported:"), f"seed={seed} hit boundary: {status}"
        assert status == "completed", f"seed={seed} unexpected status: {status}"
        assert result["winner"] in (0, 1)


# ---------------------------------------------------------------------------
# 2. deterministic by seed
# ---------------------------------------------------------------------------

def test_speed_tie_random_mode_deterministic():
    state = _mirror_tie_battle()
    for seed in (7, 42, 123):
        r1 = _run_game(state, seed, turn_random_mode=True)
        r2 = _run_game(state, seed, turn_random_mode=True)
        assert r1["winner"] == r2["winner"], f"seed={seed} non-deterministic"


# ---------------------------------------------------------------------------
# 3. ordering is RNG-broken (both sides win across seeds ~50/50), NOT always player
# ---------------------------------------------------------------------------

def test_speed_tie_random_mode_both_orders_occur():
    state = _mirror_tie_battle()
    winners = [_run_game(state, s, turn_random_mode=True)["winner"] for s in range(60)]
    assert 0 in winners, "side 0 never moved first — tie not RNG-broken (always player?)"
    assert 1 in winners, "side 1 never moved first — tie not RNG-broken"
    # Loose balance sanity: neither side wins literally every tie.
    frac0 = winners.count(0) / len(winners)
    assert 0.2 < frac0 < 0.8, f"ordering badly skewed: side0 first-fraction={frac0:.2f}"


# ---------------------------------------------------------------------------
# 4. CONTROLLED CONTRACT: non-random_mode tie must STILL fail loud
# ---------------------------------------------------------------------------

def test_speed_tie_non_random_mode_fail_loud():
    # The plain run_game path carries no OracleOverrides, so a controlled cross-side speed tie is
    # a Category-A oracle event: cpp_select_next_action throws NeedsRNG (surfaced as RuntimeError).
    # Deterministic resolution now lives on the GameDriver speed_tie ordering-override / pause-resume
    # path (see tests/test_cpp_oracle_speed_tie.py).
    state = _mirror_tie_battle()
    with pytest.raises(RuntimeError, match="NeedsRNG"):
        _run_game(state, seed=1, turn_random_mode=False)


# ---------------------------------------------------------------------------
# 5. Quick Claw in random_mode resolves cleanly (draw, no unported boundary)
# ---------------------------------------------------------------------------

def test_quick_claw_random_mode_no_unported():
    m0 = make_mon(Species.MACHOP, moves=(Move.TACKLE,), level=50, item=Item.QUICK_CLAW)
    m1 = make_mon(Species.CATERPIE, moves=(Move.TACKLE,), level=5)
    state = make_battle(m0, m1)
    for seed in range(15):
        result = _run_game(state, seed, turn_random_mode=True)
        status = result["status"]
        assert not status.startswith("unported:"), f"seed={seed} quick-claw boundary: {status}"
        assert status in ("completed", "max_turns")
