# Faint-queue rebuild after hazard-killed replacements (RECORDS/FaintQueueBug.md,
# record faint_queue_no_rebuild_bug).
#
# Bug: when a post-KO replacement died to entry hazards during the post-faint drain,
# the engine did NOT re-prompt for another replacement — the next turn began with a
# fainted active on the field (unreachable in real Run&Bun, which re-prompts until a
# replacement survives entry or the side is out of mons).
#
# Fix under test: cpp_drain_faint_queue rebuilds the queue (cpp_build_faint_queue)
# after each drain pass and keeps draining until no fainted active with live bench
# remains. GameDriver's constructor runs an initial drain, which these tests exploit:
# start with a fainted active + Stealth Rock on the same side.
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.state.battle import BattleState
from liveplay.state.side import SideState, SideCondition

from tests.state_builders import make_mon


def _controlled_luck() -> dict:
    return {
        "accuracy_threshold": 0.0,
        "crit_threshold": 50.0,
        "damage_roll": 0.5,
        "proc_threshold": 50.0,
        "secondary_threshold": 50.0,
        "multi_hit_roll": 0.5,
        "rampage_duration_roll": 0.5,
        "psywave_roll": 0.5,
        "flinch_threshold": 50.0,
        "binding_duration_roll": 0.5,
        "wake_threshold": 50.0,
        "defrost_threshold": 20.0,
        "paralysis_threshold": 50.0,
        "confusion_snap_threshold": 50.0,
        "confusion_self_hit_threshold": 50.0,
        "attract_threshold": 50.0,
        "damage_rolls_per_hit": None,
        "crits_per_hit": None,
        "random_mode": False,
    }


def _controlled_turn_luck() -> dict:
    return {"quick_claw_threshold": 50.0, "secondary_threshold": 50.0,
            "luck_tier": 1, "random_mode": False}


def _fainted(mon):
    return mon._replace(hp=0, fainted=True)


def _make_state(bench_hp: int | None, n_bench: int = 2) -> BattleState:
    """Side 0: fainted active + n_bench Snorlax bench mons at bench_hp (None = full),
    Stealth Rock on side 0's field. Side 1: healthy Snorlax."""
    fainted_active = _fainted(make_mon(Species.SNORLAX, moves=(Move.SPLASH,)))
    bench = [make_mon(Species.SNORLAX, moves=(Move.SPLASH,), hp=bench_hp)
             for _ in range(n_bench)]
    side0 = SideState(team=[fainted_active] + bench, active_indices=[0],
                      side_conditions=[(SideCondition.STEALTH_ROCK, -1)])
    # Different level → different speed → no SPEED_TIE oracle pause in controlled mode.
    opp = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=40)
    side1 = SideState(team=[opp], active_indices=[0])
    return BattleState(sides=(side0, side1))


def _drive(state, max_turns: int = 1) -> dict:
    args = {
        "state": sweep_io.to_jsonable(state),
        "seed": 0,
        "luck_p0": _controlled_luck(),
        "luck_p1": _controlled_luck(),
        "turn_luck_p0": _controlled_turn_luck(),
        "turn_luck_p1": _controlled_turn_luck(),
        "max_turns": max_turns,
    }
    driver = cpp.GameDriver(json.dumps(args))
    return json.loads(driver.step())


def _post_faint_entries(result) -> list:
    return [e for e in result["action_log"] if e.get("phase") == "post_faint"]


def _side0_active_fainted(result) -> bool:
    state = sweep_io.from_jsonable(result["state"])
    idx = state.sides[0].active_indices[0]
    return state.sides[0].team[idx].fainted


class TestFaintQueueRebuild:
    def test_hazard_killed_replacements_are_reprompted_until_bench_exhausts(self):
        """Both bench mons at 1 HP die to Stealth Rock on entry. The drain must
        re-prompt after each hazard death: two post_faint entries for side 0,
        battle over immediately with winner = side 1."""
        result = _drive(_make_state(bench_hp=1))
        entries = _post_faint_entries(result)
        assert len(entries) == 2, (
            f"Expected 2 post_faint entries (re-prompt after hazard death), "
            f"got {len(entries)}: {entries}")
        # The battle must resolve entirely inside the initial drain: NO turn may
        # run in between (a turn here means the opponent got a free turn against
        # an empty slot — the original bug's symptom, p0=[] in the actions entry).
        turns = [e for e in result["action_log"] if e.get("phase") == "actions"]
        assert turns == [], (
            f"A turn ran with a fainted active on the field: {turns}")
        assert result["status"] == "done"
        assert result["winner"] == 1

    def test_no_fainted_active_ever_starts_a_turn(self):
        """With a live bench remaining, the drain must never leave a fainted
        active on the field (mixed bench: 1-HP mons + one healthy)."""
        state = _make_state(bench_hp=1, n_bench=2)
        # Add a healthy third bench mon.
        healthy = make_mon(Species.SNORLAX, moves=(Move.SPLASH,))
        side0 = state.sides[0]
        side0 = SideState(team=side0.team + [healthy], active_indices=[0],
                          side_conditions=list(side0.side_conditions))
        state = BattleState(sides=(side0, state.sides[1]))
        result = _drive(state, max_turns=1)
        assert not _side0_active_fainted(result), (
            "A fainted active was left on the field despite a live bench")
        # No turn may have run with an empty side-0 action list (free turn for
        # the opponent against an empty slot).
        for e in result["action_log"]:
            if e.get("phase") == "actions":
                assert e["p0"] != [], f"Turn ran with fainted side-0 active: {e}"
        # Game must not be over: side 0 still has a live mon.
        assert result["winner"] != 1

    def test_surviving_replacement_drains_once(self):
        """Control: healthy bench mons survive Stealth Rock — exactly one
        post_faint entry, no over-rebuilding, game continues."""
        result = _drive(_make_state(bench_hp=None))
        entries = _post_faint_entries(result)
        assert len(entries) == 1, (
            f"Expected exactly 1 post_faint entry, got {len(entries)}: {entries}")
        assert not _side0_active_fainted(result)
        assert result["winner"] is None or result["winner"] != 1
