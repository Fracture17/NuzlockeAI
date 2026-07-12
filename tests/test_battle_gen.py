# Tests for liveplay/battle_gen.py — random battle generator port.
import json
import random

import pytest

import liveplay.sweep_io as sweep_io
from liveplay.data.moves import Move, MOVE_DATA, MoveCategory

# _LUCK / _TURN_LUCK shapes taken from SCRIPTS/replay_golden_traces.py (authoritative example).
_LUCK = {
    "accuracy_threshold": 50.0, "crit_threshold": 50.0, "damage_roll": 0.5,
    "proc_threshold": 50.0, "secondary_threshold": 50.0, "multi_hit_roll": 0.5,
    "rampage_duration_roll": 0.5, "psywave_roll": 0.5, "flinch_threshold": 50.0,
    "binding_duration_roll": 0.5, "wake_threshold": 50.0, "defrost_threshold": 20.0,
    "paralysis_threshold": 50.0, "confusion_snap_threshold": 50.0,
    "confusion_self_hit_threshold": 50.0, "attract_threshold": 50.0,
    "damage_rolls_per_hit": None, "crits_per_hit": None, "random_mode": True,
}
_TURN_LUCK = {"quick_claw_threshold": 50.0, "secondary_threshold": 50.0,
              "luck_tier": 1, "random_mode": True}


def test_determinism():
    """Same seed must produce identical serialized BattleState and identical params."""
    from liveplay.battle_gen import make_random_battle

    state1, params1 = make_random_battle(random.Random(12345))
    state2, params2 = make_random_battle(random.Random(12345))

    assert json.dumps(sweep_io.to_jsonable(state1), sort_keys=True) == \
           json.dumps(sweep_io.to_jsonable(state2), sort_keys=True)
    assert params1 == params2


def test_different_seeds_differ():
    """Different seeds must produce different serialized states."""
    from liveplay.battle_gen import make_random_battle

    state1, _ = make_random_battle(random.Random(1))
    state2, _ = make_random_battle(random.Random(2))

    assert json.dumps(sweep_io.to_jsonable(state1), sort_keys=True) != \
           json.dumps(sweep_io.to_jsonable(state2), sort_keys=True)


def test_team_shape_and_legality():
    """Generated battles satisfy structural and legality invariants across seeds 0..9."""
    from liveplay.battle_gen import make_random_battle, move_candidate_weights, CORPUS_BANNED_SPECIES

    for seed in range(10):
        state, params = make_random_battle(random.Random(seed))

        assert len(state.sides) == 2

        player_team = state.sides[0].team
        opp_team = state.sides[1].team

        assert len(player_team) == params["player_size"]
        assert len(opp_team) == params["opp_size"]

        for side_idx, (team, level_key, is_player) in enumerate([
            (player_team, "player_level", True),
            (opp_team, "opp_level", False),
        ]):
            expected_level = params[level_key]
            for mon in team:
                assert 5 <= mon.level <= 100, f"seed={seed} level={mon.level}"
                assert mon.level == expected_level
                assert mon.ivs == (31, 31, 31, 31, 31, 31)
                assert len(mon.move_ids) == 4
                assert any(m != Move.NONE for m in mon.move_ids), \
                    f"seed={seed} {mon.species} has no moves"
                assert mon.species.name not in CORPUS_BANNED_SPECIES, \
                    f"seed={seed} banned species {mon.species.name} appeared"

                # If any candidate damaging move exists, moveset must contain >=1 damaging move.
                candidates = move_candidate_weights(mon.species.name, mon.level, is_player)
                has_damaging_candidate = any(
                    MOVE_DATA[m].category in (MoveCategory.PHYSICAL, MoveCategory.SPECIAL)
                    for m in candidates
                )
                if has_damaging_candidate:
                    has_damaging_move = any(
                        m != Move.NONE and MOVE_DATA[m].category in (MoveCategory.PHYSICAL, MoveCategory.SPECIAL)
                        for m in mon.move_ids
                    )
                    assert has_damaging_move, \
                        f"seed={seed} {mon.species.name} has damaging candidates but no damaging move"


def test_cpp_run_game_roundtrip():
    """Generated battles can be run through the C++ engine without errors, seeds 0..4."""
    import nuzlocke_engine_cpp as cpp
    from liveplay.battle_gen import make_random_battle

    for seed in range(5):
        state, _ = make_random_battle(random.Random(seed))
        args = {
            "state": sweep_io.to_jsonable(state),
            "seed": 42,
            "luck_p0": _LUCK, "luck_p1": _LUCK,
            "turn_luck_p0": _TURN_LUCK, "turn_luck_p1": _TURN_LUCK,
            "max_turns": 500,
            "policy_p0": "random",
            "policy_p1": "random",
        }
        res = json.loads(cpp.run_game(json.dumps(args)))
        assert res["status"] in ("completed", "max_turns"), \
            f"seed={seed} unexpected status: {res['status']}"


def test_generatable_species_nonempty_and_sorted():
    """generatable_species() returns a non-empty sorted list of strings."""
    from liveplay.battle_gen import generatable_species

    pool = generatable_species()
    assert len(pool) > 0
    assert pool == sorted(pool)
    assert all(isinstance(s, str) for s in pool)
