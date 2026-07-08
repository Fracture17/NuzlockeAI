# Stage A3: native-RNG ports of the remaining Category-A uncontrolled oracles.
#
# Each oracle previously fail-loud ("unported: ...") whenever it would fire. In random_mode they
# now resolve natively via NativeRng, mirroring the Python `else random.*` fallback branch:
#   - Effect Spore   (post_hit): rng.randint(1,30) -> SLEEP(<=11)/PARALYSIS(<=21)/POISON
#   - Tri Attack     (post_hit): rng.choice([BURN, FREEZE, PARALYSIS])
#   - Acupressure    (effects) : rng.randint(0,6) -> +2 to that stat
#   - Moody          (residual): boost=rng.randint(0,6) +2, drop=(boost+1)%5 (adjusted) -1
#   - Starf Berry    (berry)   : rng.randint(0,4) -> +2 to that stat
#
# Controlled (non-random) mode is UNCHANGED: every oracle still throws so the Phase-1 bridge
# delegates the pick to Python. These tests exercise the random_mode path via run_game, reading
# the returned final_state to confirm the effect actually resolved (not just "didn't throw").
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
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


def _run(state, seed, turn_random_mode=True, max_turns=6):
    payload = json.dumps({
        "state": sweep_io.to_jsonable(state),
        "seed": seed,
        "luck_p0": _damage_luck(), "luck_p1": _damage_luck(),
        "turn_luck_p0": _turn_luck(turn_random_mode), "turn_luck_p1": _turn_luck(turn_random_mode),
        "max_turns": max_turns,
    })
    r = json.loads(cpp.run_game(payload))
    assert not r["status"].startswith("unported:"), f"seed={seed} boundary: {r['status']}"
    return r


def _mon0(state):
    return sweep_io.from_jsonable(state).sides[0].team[0]


def _mon1(state):
    return sweep_io.from_jsonable(state).sides[1].team[0]


# ---------------------------------------------------------------------------
# Acupressure — +2 to a random stat (0..6)
# ---------------------------------------------------------------------------

def _acupressure_battle():
    m0 = make_mon(Species.MACHOP, moves=(Move.ACUPRESSURE,), level=50)
    m1 = make_mon(Species.CATERPIE, moves=(Move.TACKLE,), level=5)
    return make_battle(m0, m1)


def test_acupressure_random_mode_boosts_a_stat():
    state = _acupressure_battle()
    boosted_indices = set()
    for seed in range(30):
        r = _run(state, seed, max_turns=1)
        stages = _mon0(r["final_state"]).stat_stages
        plus2 = [i for i, v in enumerate(stages) if v == 2]
        assert len(plus2) == 1, f"seed={seed}: expected exactly one +2 stat, got {stages}"
        boosted_indices.add(plus2[0])
    # Native RNG must select varying stats, not a fixed one.
    assert len(boosted_indices) >= 3, f"acupressure not varying: {boosted_indices}"


def test_acupressure_random_mode_deterministic():
    state = _acupressure_battle()
    for seed in (2, 40, 88):
        a = _mon0(_run(state, seed, max_turns=1)["final_state"]).stat_stages
        b = _mon0(_run(state, seed, max_turns=1)["final_state"]).stat_stages
        assert a == b, f"seed={seed} non-deterministic acupressure"


def test_acupressure_controlled_run_game_fail_loud():
    # The plain run_game path carries no OracleOverrides, so a Category-A event in controlled
    # mode is fail-loud: oracle_resolve throws NeedsRNG (surfaced as a RuntimeError). Deterministic
    # resolution of Acupressure now lives on the GameDriver pause/resume path
    # (see tests/test_cpp_oracle_acupressure.py).
    state = _acupressure_battle()
    payload = json.dumps({
        "state": sweep_io.to_jsonable(state), "seed": 1,
        "luck_p0": {**_damage_luck(), "random_mode": False},
        "luck_p1": {**_damage_luck(), "random_mode": False},
        "turn_luck_p0": _turn_luck(False), "turn_luck_p1": _turn_luck(False),
        "max_turns": 1,
    })
    with pytest.raises(RuntimeError, match="NeedsRNG"):
        json.loads(cpp.run_game(payload))


# ---------------------------------------------------------------------------
# Moody — +2 to one stat (0..6), -1 to a different one (0..6 excl boost), each end of turn
# ---------------------------------------------------------------------------

def _moody_battle():
    # Passive mirror so the game runs several residual turns without a quick KO.
    m0 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), ability=Ability.MOODY, level=50)
    m1 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    return make_battle(m0, m1)


def test_moody_random_mode_one_up_one_down():
    # R&B: both boost and drop span 0-6 (acc/eva included); boost != drop always.
    state = _moody_battle()
    seen_boost = set()
    seen_drop = set()
    for seed in range(50):
        r = _run(state, seed, max_turns=1)
        stages = _mon0(r["final_state"]).stat_stages
        plus2 = [i for i, v in enumerate(stages) if v == 2]
        minus1 = [i for i, v in enumerate(stages) if v == -1]
        assert len(plus2) == 1, f"seed={seed}: expected one +2, got {stages}"
        assert len(minus1) == 1, f"seed={seed}: expected one -1, got {stages}"
        assert plus2[0] != minus1[0], f"seed={seed}: boost==drop at {plus2[0]}"
        seen_boost.add(plus2[0])
        seen_drop.add(minus1[0])
    assert len(seen_boost) >= 3, f"moody boost not varying: {seen_boost}"
    # Drop must eventually reach indices 5 and 6 (acc/eva) across enough seeds.
    assert 5 in seen_drop or 6 in seen_drop, (
        f"drop never reached acc/eva indices over 50 seeds: {seen_drop}"
    )


def test_moody_random_mode_deterministic():
    state = _moody_battle()
    for seed in (3, 19, 71):
        a = _mon0(_run(state, seed, max_turns=1)["final_state"]).stat_stages
        b = _mon0(_run(state, seed, max_turns=1)["final_state"]).stat_stages
        assert a == b, f"seed={seed} non-deterministic moody"


# ---------------------------------------------------------------------------
# Starf Berry — +2 to a random stat (0..4) when HP drops to <=25%
# ---------------------------------------------------------------------------

def _starf_battle():
    # Holder sits at its 25% Starf threshold; a weak attacker chips it so check_berry fires.
    holder = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), item=Item.STARF_BERRY, level=50)
    holder = holder._replace(hp=max(1, holder.max_hp // 4))
    attacker = make_mon(Species.CATERPIE, moves=(Move.TACKLE,), level=5)
    return make_battle(holder, attacker)


def test_starf_berry_random_mode_boosts_and_consumes():
    state = _starf_battle()
    boosted = set()
    consumed = 0
    for seed in range(30):
        r = _run(state, seed, max_turns=1)
        mon = _mon0(r["final_state"])
        if mon.consumed_berry == Item.STARF_BERRY:
            consumed += 1
            plus = [i for i, v in enumerate(mon.stat_stages) if v == 2]
            assert len(plus) == 1, f"seed={seed}: expected one +2, got {mon.stat_stages}"
            assert plus[0] <= 4, f"seed={seed}: Starf stat must be 0..4, got {plus[0]}"
            boosted.add(plus[0])
    assert consumed >= 20, f"Starf rarely fired ({consumed}/30) — scenario broken"
    assert len(boosted) >= 3, f"Starf stat not varying: {boosted}"


# ---------------------------------------------------------------------------
# Tri Attack — secondary inflicts BURN / FREEZE / PARALYSIS
# ---------------------------------------------------------------------------

def _tri_attack_battle():
    atk = make_mon(Species.PORYGON, moves=(Move.TRI_ATTACK,), level=50)
    df = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    return make_battle(atk, df)


def test_tri_attack_random_mode_inflicts_status():
    state = _tri_attack_battle()
    seen = set()
    for seed in range(40):
        r = _run(state, seed, max_turns=1)
        st = _mon1(r["final_state"]).status
        if st != Status.NONE:
            assert st in (Status.BURN, Status.FREEZE, Status.PARALYSIS), st
            seen.add(st)
    # Over 40 seeds the ~20% secondary should land at least twice and hit >1 status kind.
    assert len(seen) >= 2, f"Tri Attack statuses not varied: {seen}"


def test_tri_attack_controlled_run_game_fail_loud():
    # The plain run_game path carries no OracleOverrides, so a Category-A event in controlled
    # mode is fail-loud: oracle_resolve throws NeedsRNG (surfaced as a RuntimeError). Deterministic
    # resolution of Tri Attack now lives on the GameDriver pause/resume path
    # (see tests/test_cpp_oracle_tri_attack.py).
    state = _tri_attack_battle()
    payload = json.dumps({
        "state": sweep_io.to_jsonable(state), "seed": 1,
        "luck_p0": {**_damage_luck(), "random_mode": False, "secondary_threshold": 0.0},
        "luck_p1": {**_damage_luck(), "random_mode": False, "secondary_threshold": 0.0},
        "turn_luck_p0": _turn_luck(False), "turn_luck_p1": _turn_luck(False),
        "max_turns": 1,
    })
    with pytest.raises(RuntimeError, match="NeedsRNG"):
        json.loads(cpp.run_game(payload))


# ---------------------------------------------------------------------------
# Effect Spore — contact attacker gets SLEEP / PARALYSIS / POISON
# ---------------------------------------------------------------------------

def _effect_spore_battle():
    # Attacker uses a contact move; tanky Effect Spore defender survives to proc repeatedly.
    atk = make_mon(Species.MACHOP, moves=(Move.TACKLE,), level=30)
    df = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), ability=Ability.EFFECT_SPORE, level=50)
    return make_battle(atk, df)


def test_effect_spore_random_mode_inflicts_status():
    state = _effect_spore_battle()
    seen = set()
    for seed in range(40):
        r = _run(state, seed, max_turns=4)
        st = _mon0(r["final_state"]).status
        if st != Status.NONE:
            assert st in (Status.SLEEP, Status.PARALYSIS, Status.POISON), st
            seen.add(st)
    assert len(seen) >= 2, f"Effect Spore statuses not varied: {seen}"
