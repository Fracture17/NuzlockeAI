# Deterministic tests for cpp_apply_turn_start_effects: RKS/Silvally type sync + Castform Forecast.
# Uses controlled mode (random_mode=False) since this is purely deterministic logic.
import json

import pytest

import nuzlocke_engine_cpp as cpp
import liveplay.sweep_io as sweep_io
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.types import Type
from liveplay.state.battle import WeatherEnum

from tests.state_builders import make_mon, make_battle


def _luck_controlled() -> dict:
    return {
        "accuracy_threshold": 50.0, "crit_threshold": 50.0, "damage_roll": 0.5,
        "proc_threshold": 50.0, "secondary_threshold": 50.0, "multi_hit_roll": 0.5,
        "rampage_duration_roll": 0.5, "psywave_roll": 0.5, "flinch_threshold": 50.0,
        "binding_duration_roll": 0.5, "wake_threshold": 50.0, "defrost_threshold": 20.0,
        "paralysis_threshold": 50.0, "confusion_snap_threshold": 50.0,
        "confusion_self_hit_threshold": 50.0, "attract_threshold": 50.0,
        "damage_rolls_per_hit": None, "crits_per_hit": None, "random_mode": False,
    }


def _turn_luck_controlled() -> dict:
    return {"quick_claw_threshold": 50.0, "secondary_threshold": 50.0,
            "luck_tier": 1, "random_mode": False}


def _run(state, seed=0, max_turns=2):
    payload = json.dumps({
        "state": sweep_io.to_jsonable(state),
        "seed": seed,
        "luck_p0": _luck_controlled(), "luck_p1": _luck_controlled(),
        "turn_luck_p0": _turn_luck_controlled(), "turn_luck_p1": _turn_luck_controlled(),
        "max_turns": max_turns,
    })
    r = json.loads(cpp.run_game(payload))
    assert not r["status"].startswith("unported:"), f"seed={seed} hit unported: {r['status']}"
    return r


def _mon0(result):
    return sweep_io.from_jsonable(result["final_state"]).sides[0].team[0]


def _mon1(result):
    return sweep_io.from_jsonable(result["final_state"]).sides[1].team[0]


# ---------------------------------------------------------------------------
# RKS System / Silvally type sync
# ---------------------------------------------------------------------------

def _silvally_battle(item):
    """Silvally (RKS System + given memory item) vs a tanky Normal mon, both using Splash."""
    silvally = make_mon(
        Species.SILVALLY,
        moves=(Move.SPLASH,),
        ability=Ability.RKS_SYSTEM,
        item=item,
        level=50,
    )
    # Silvally starts with NORMAL type from make_mon regardless of held item;
    # turn_start should sync it to the memory item's type.
    opponent = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    return make_battle(silvally, opponent)


def test_silvally_fire_memory_syncs_to_fire():
    # Silvally + FIRE_MEMORY: type must become (FIRE,) after first turn start.
    state = _silvally_battle(Item.FIRE_MEMORY)
    r = _run(state)
    assert _mon0(r).types == (Type.FIRE,), f"expected FIRE, got {_mon0(r).types}"


def test_silvally_water_memory_syncs_to_water():
    state = _silvally_battle(Item.WATER_MEMORY)
    r = _run(state)
    assert _mon0(r).types == (Type.WATER,), f"expected WATER, got {_mon0(r).types}"


def test_silvally_no_memory_becomes_normal():
    # No memory item → type must be (NORMAL,) (default via _MEMORY_TYPE.get(item, NORMAL)).
    silvally = make_mon(
        Species.SILVALLY,
        moves=(Move.SPLASH,),
        ability=Ability.RKS_SYSTEM,
        item=Item.NONE,
        level=50,
    )
    opponent = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    state = make_battle(silvally, opponent)
    r = _run(state)
    assert _mon0(r).types == (Type.NORMAL,), f"expected NORMAL, got {_mon0(r).types}"


# ---------------------------------------------------------------------------
# Castform Forecast
# ---------------------------------------------------------------------------

def _castform_battle(weather: WeatherEnum, form: Species):
    """Castform (Forecast) starting as `form` under `weather` vs a tanky mon."""
    castform = make_mon(
        form,
        moves=(Move.SPLASH,),
        ability=Ability.FORECAST,
        level=50,
    )
    opponent = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    state = make_battle(castform, opponent)
    # Set raw weather permanently (weather_turns=-1) so it doesn't expire mid-battle and revert
    # Castform via EOT form changes. Parity-critical: cpp_apply_turn_start_effects uses s.weather.
    state = state.__replace__(weather=weather, weather_turns=-1 if weather != WeatherEnum.NONE else 0)
    return state


def test_castform_rainy_weather_becomes_rainy_form():
    # Base Castform under RAINY → CASTFORM_RAINY after turn start.
    state = _castform_battle(WeatherEnum.RAINY, Species.CASTFORM)
    r = _run(state)
    assert _mon0(r).species == Species.CASTFORM_RAINY, f"got {_mon0(r).species}"
    assert _mon0(r).types == (Type.WATER,), f"expected WATER types, got {_mon0(r).types}"


def test_castform_rainy_form_reverts_to_base_in_no_weather():
    # CASTFORM_RAINY under no weather → reverts to base CASTFORM.
    state = _castform_battle(WeatherEnum.NONE, Species.CASTFORM_RAINY)
    r = _run(state)
    assert _mon0(r).species == Species.CASTFORM, f"expected base Castform, got {_mon0(r).species}"


def test_castform_hail_becomes_snowy_form():
    state = _castform_battle(WeatherEnum.HAIL, Species.CASTFORM)
    r = _run(state)
    assert _mon0(r).species == Species.CASTFORM_SNOWY, f"got {_mon0(r).species}"


def test_castform_sunny_becomes_sunny_form():
    state = _castform_battle(WeatherEnum.SUNNY, Species.CASTFORM)
    r = _run(state)
    assert _mon0(r).species == Species.CASTFORM_SUNNY, f"got {_mon0(r).species}"


def test_castform_no_weather_stays_base():
    # Castform in no weather should stay as base form.
    state = _castform_battle(WeatherEnum.NONE, Species.CASTFORM)
    r = _run(state)
    assert _mon0(r).species == Species.CASTFORM, f"got {_mon0(r).species}"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_silvally_deterministic():
    state = _silvally_battle(Item.FIRE_MEMORY)
    a = _mon0(_run(state, seed=0))
    b = _mon0(_run(state, seed=0))
    assert a.types == b.types, "non-deterministic silvally type sync"


def test_castform_deterministic():
    state = _castform_battle(WeatherEnum.RAINY, Species.CASTFORM)
    a = _mon0(_run(state, seed=0))
    b = _mon0(_run(state, seed=0))
    assert a.species == b.species, "non-deterministic castform form change"
