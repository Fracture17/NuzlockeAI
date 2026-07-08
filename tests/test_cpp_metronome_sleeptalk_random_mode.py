# Tests for native random_mode resolution of Metronome and Sleep Talk sub-move selection.
#
# In random_mode, these moves pick sub-moves via NativeRng::choice (uniform). In controlled
# mode (random_mode=False) they remain fail-loud so the Phase-1 bridge still delegates to Python.
# Python _phase_await_sub_move is oracle-only (no else-random branch) so uniform is correct.
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status

from tests.state_builders import make_mon, make_battle


def _damage_luck() -> dict:
    return {
        "accuracy_threshold": 50.0, "crit_threshold": 50.0, "damage_roll": 0.5,
        "proc_threshold": 50.0, "secondary_threshold": 50.0, "multi_hit_roll": 0.5,
        "rampage_duration_roll": 0.5, "psywave_roll": 0.5, "flinch_threshold": 50.0,
        "binding_duration_roll": 0.5, "wake_threshold": 50.0, "defrost_threshold": 20.0,
        "paralysis_threshold": 50.0, "confusion_snap_threshold": 50.0,
        "confusion_self_hit_threshold": 50.0, "attract_threshold": 50.0,
        "damage_rolls_per_hit": None, "crits_per_hit": None, "random_mode": True,
    }


def _turn_luck(random_mode: bool = True) -> dict:
    return {"quick_claw_threshold": 50.0, "secondary_threshold": 50.0,
            "luck_tier": 1, "random_mode": random_mode}


def _run(state, seed, random_mode=True, max_turns=4):
    """Run game via cpp.run_game; does NOT assert on unported status (caller checks)."""
    payload = json.dumps({
        "state": sweep_io.to_jsonable(state),
        "seed": seed,
        "luck_p0": {**_damage_luck(), "random_mode": random_mode},
        "luck_p1": {**_damage_luck(), "random_mode": random_mode},
        "turn_luck_p0": _turn_luck(random_mode),
        "turn_luck_p1": _turn_luck(random_mode),
        "max_turns": max_turns,
    })
    return json.loads(cpp.run_game(payload))


def _mon0(final_state_json):
    return sweep_io.from_jsonable(final_state_json).sides[0].team[0]


def _mon1(final_state_json):
    return sweep_io.from_jsonable(final_state_json).sides[1].team[0]


# ---------------------------------------------------------------------------
# Metronome: tanky attacker uses Metronome; bulky defender never faints.
# ---------------------------------------------------------------------------

def _metronome_battle():
    # Snorlax uses Metronome; Blissey is extremely bulky to survive most sub-moves.
    m0 = make_mon(Species.SNORLAX, moves=(Move.METRONOME,), level=50)
    m1 = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)
    return make_battle(m0, m1)


def test_metronome_random_mode_resolves_and_varies():
    """Over 30 seeds Metronome completes (no unported) and produces varying outcomes."""
    state = _metronome_battle()
    outcomes = set()
    for seed in range(30):
        r = _run(state, seed, max_turns=1)
        assert not r["status"].startswith("unported:"), f"seed={seed}: {r['status']}"
        # Capture final HP of defender as a proxy for which sub-move fired.
        mon1 = _mon1(r["final_state"])
        outcomes.add(mon1.hp)
    # Sub-move selection is random — should produce varying HP outcomes across 30 seeds.
    assert len(outcomes) >= 5, f"Metronome outcomes not varying: {outcomes}"


def test_metronome_random_mode_deterministic():
    """Same seed produces identical final state."""
    state = _metronome_battle()
    for seed in (0, 7, 19):
        a = _run(state, seed, max_turns=1)["final_state"]
        b = _run(state, seed, max_turns=1)["final_state"]
        assert a == b, f"seed={seed}: non-deterministic Metronome"


def test_metronome_controlled_still_unported():
    """Controlled mode (random_mode=False) keeps Metronome fail-loud."""
    state = _metronome_battle()
    r = _run(state, seed=1, random_mode=False, max_turns=1)
    assert r["status"] == "unported: sub_move", r["status"]


def test_metronome_pp_consumed_from_metronome_slot():
    """PP is consumed from the Metronome slot (slot 0), not the sub-move's slot."""
    state = _metronome_battle()
    # Use multiple turns so PP consumption is visible.
    r = _run(state, seed=0, max_turns=2)
    assert not r["status"].startswith("unported:"), r["status"]
    mon0 = _mon0(r["final_state"])
    # Slot 0 is Metronome; its PP should have decreased by at least 1.
    from liveplay.data.moves import MOVE_DATA
    metronome_max_pp = MOVE_DATA[Move.METRONOME].pp
    assert mon0.move_pp[0] < metronome_max_pp, (
        f"Metronome slot PP not consumed: still {mon0.move_pp[0]}/{metronome_max_pp}"
    )


# ---------------------------------------------------------------------------
# Sleep Talk: asleep mon uses Sleep Talk to call one of its own moves.
# ---------------------------------------------------------------------------

def _sleep_talk_battle():
    # Mon 0 is asleep and knows Sleep Talk + Tackle. Tackle is the only callable move.
    m0 = make_mon(Species.SNORLAX, moves=(Move.SLEEP_TALK, Move.TACKLE), level=50,
                  status=Status.SLEEP)
    m1 = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)
    return make_battle(m0, m1)


def test_sleep_talk_random_mode_executes_own_move():
    """Sleep Talk fires (no unported) and defender takes damage (Tackle called)."""
    state = _sleep_talk_battle()
    blissey_max_hp = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50).max_hp
    took_damage = False
    for seed in range(20):
        r = _run(state, seed, max_turns=1)
        assert not r["status"].startswith("unported:"), f"seed={seed}: {r['status']}"
        mon1 = _mon1(r["final_state"])
        if mon1.hp < blissey_max_hp:
            took_damage = True
    # Tackle should deal damage in at least some seeds.
    assert took_damage, "Sleep Talk never called Tackle (no damage dealt across 20 seeds)"


def test_sleep_talk_mon_stays_asleep():
    """After Sleep Talk fires, the user remains asleep (sleep status restored)."""
    state = _sleep_talk_battle()
    for seed in range(15):
        r = _run(state, seed, max_turns=1)
        assert not r["status"].startswith("unported:"), f"seed={seed}: {r['status']}"
        mon0 = _mon0(r["final_state"])
        if not mon0.fainted:
            assert mon0.status == Status.SLEEP, (
                f"seed={seed}: Snorlax should still be asleep after Sleep Talk, "
                f"got {mon0.status}"
            )


def test_sleep_talk_pp_consumed_from_sleep_talk_slot():
    """PP is consumed from the Sleep Talk slot, not the sub-move (Tackle) slot."""
    state = _sleep_talk_battle()
    r = _run(state, seed=0, max_turns=1)
    assert not r["status"].startswith("unported:"), r["status"]
    mon0 = _mon0(r["final_state"])
    from liveplay.data.moves import MOVE_DATA
    sleep_talk_max_pp = MOVE_DATA[Move.SLEEP_TALK].pp
    tackle_max_pp = MOVE_DATA[Move.TACKLE].pp
    # Sleep Talk slot (slot 0) PP should decrease.
    assert mon0.move_pp[0] < sleep_talk_max_pp, (
        f"Sleep Talk PP not consumed: {mon0.move_pp[0]}/{sleep_talk_max_pp}"
    )
    # Tackle slot (slot 1) PP should be unchanged.
    assert mon0.move_pp[1] == tackle_max_pp, (
        f"Tackle PP incorrectly consumed: {mon0.move_pp[1]}/{tackle_max_pp}"
    )


# ---------------------------------------------------------------------------
# Sleep Talk with no usable options: mon knows only Sleep Talk (excluded moves).
# ---------------------------------------------------------------------------

def _sleep_talk_no_options_battle():
    # Mon 0 is asleep and knows only Sleep Talk — no callable sub-move.
    m0 = make_mon(Species.SNORLAX, moves=(Move.SLEEP_TALK,), level=50, status=Status.SLEEP)
    m1 = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)
    return make_battle(m0, m1)


def test_sleep_talk_no_options_fails_cleanly():
    """Sleep Talk with no usable moves fails without crash or unported error."""
    state = _sleep_talk_no_options_battle()
    for seed in range(5):
        r = _run(state, seed, max_turns=1)
        assert not r["status"].startswith("unported:"), f"seed={seed}: {r['status']}"


def test_sleep_talk_no_options_mon_still_asleep():
    """After failed Sleep Talk (no options), user remains asleep."""
    state = _sleep_talk_no_options_battle()
    for seed in range(5):
        r = _run(state, seed, max_turns=1)
        mon0 = _mon0(r["final_state"])
        if not mon0.fainted:
            assert mon0.status == Status.SLEEP, (
                f"seed={seed}: Snorlax should be asleep after failed Sleep Talk, "
                f"got {mon0.status}"
            )


# ---------------------------------------------------------------------------
# Sleep Talk controlled mode.
# ---------------------------------------------------------------------------

def test_sleep_talk_controlled_still_unported():
    """Controlled mode (random_mode=False) keeps Sleep Talk fail-loud."""
    state = _sleep_talk_battle()
    r = _run(state, seed=1, random_mode=False, max_turns=1)
    assert r["status"] == "unported: sub_move", r["status"]
