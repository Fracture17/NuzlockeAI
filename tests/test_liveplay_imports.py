# Import sweep, seam stub, sweep_io round-trip, and cpp_driver payload tests for liveplay/.
import importlib
import json
import pkgutil
import sys

import pytest


# ---------------------------------------------------------------------------
# a) Import sweep: every module in liveplay/ must import without error.
# ---------------------------------------------------------------------------

def _liveplay_module_names() -> list[str]:
    """Collect all importable module names under the liveplay package."""
    import liveplay
    names = ["liveplay"]
    for finder, modname, _ in pkgutil.walk_packages(
        path=liveplay.__path__,
        prefix="liveplay.",
        onerror=lambda name: None,
    ):
        names.append(modname)
    return names


def test_import_sweep():
    """All liveplay modules import without raising."""
    names = _liveplay_module_names()
    assert names, "No liveplay modules found — package not installed or empty."
    errors = []
    for name in names:
        try:
            importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")
    assert not errors, "Import failures:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# b) engine_select exports are callable (run_candidate_sweep is now wired, not a stub).
# ---------------------------------------------------------------------------

def test_enumerate_legal_actions_importable():
    # enumerate_legal_actions is now a real implementation (not a stub); verify it is importable.
    from liveplay.engine_select import enumerate_legal_actions
    assert callable(enumerate_legal_actions)


# ---------------------------------------------------------------------------
# c) sweep_io round-trip: BattleState + Candidate containing an Action.
# ---------------------------------------------------------------------------

def _make_minimal_pokemon():
    from liveplay.state.pokemon import PokemonState, GenderEnum
    from liveplay.data.species import Species
    from liveplay.data.natures import Nature
    from liveplay.data.moves import Move, MOVE_DATA
    from liveplay.data.abilities import Ability
    from liveplay.data.items import Item
    from liveplay.data.status import Status

    move = Move.TACKLE
    padded = (move, Move.NONE, Move.NONE, Move.NONE)
    move_pp = (MOVE_DATA[move].pp, 0, 0, 0)
    return PokemonState(
        species=Species.BULBASAUR,
        nature=Nature.HARDY,
        ivs=(31, 31, 31, 31, 31, 31),
        gender=GenderEnum.MALE,
        level=5,
        ability=Ability.NONE,
        item=Item.NONE,
        status=Status.NONE,
        move_ids=padded,
        move_pp=move_pp,
    )


def _make_minimal_battle():
    from liveplay.state.battle import BattleState
    from liveplay.state.side import SideState

    mon = _make_minimal_pokemon()
    side0 = SideState(team=[mon], active_indices=[0])
    side1 = SideState(team=[mon], active_indices=[0])
    return BattleState(sides=(side0, side1))


def test_sweep_io_round_trip():
    from liveplay.sweep_io import to_jsonable, from_jsonable
    from liveplay.candidate import Candidate
    from liveplay.actions import Action, ActionKind

    state = _make_minimal_battle()
    action = Action(kind=ActionKind.MOVE, move_slot=0, mega=False)
    candidate = Candidate(state=state, rng_sequence=[], unknown_actions={})

    encoded = to_jsonable(candidate)
    serialized = json.dumps(encoded)
    decoded_raw = json.loads(serialized)
    restored = from_jsonable(decoded_raw)

    assert isinstance(restored, Candidate)
    assert restored.state == candidate.state
    assert restored.rng_sequence == candidate.rng_sequence


# ---------------------------------------------------------------------------
# d) cpp_driver.action_payload on a mega action returns expected keys.
# ---------------------------------------------------------------------------

def test_action_payload_mega():
    from liveplay.cpp_driver import action_payload
    from liveplay.actions import Action, ActionKind

    action = Action(kind=ActionKind.MOVE, move_slot=1, mega=True)
    payload = action_payload(action)

    expected_keys = {
        "kind", "move_slot", "move_override", "switch_to_slot",
        "target_side", "target_slot", "mega", "source_slot",
    }
    assert set(payload.keys()) == expected_keys
    assert payload["mega"] is True
    assert payload["kind"] == int(ActionKind.MOVE)
    assert payload["move_slot"] == 1
    assert payload["move_override"] == -1  # None encodes as -1
