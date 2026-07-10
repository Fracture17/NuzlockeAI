# C1.7h Stage 2 tests: cpp_enumerate_legal_actions parity and Policy unit checks.
# Oracle: Python enumerate_legal_actions (mega variants filtered out).
# Each test constructs a state, runs both sides through Python and C++, and compares
# the ordered action list as tuples (kind, move_slot, move_override, switch_to_slot,
# target_side, target_slot). Policy tests use the binding or C++-side checks where
# the policies are not exposed to Python.
import json
import copy

import pytest

import liveplay.sweep_io as sweep_io
import nuzlocke_engine_cpp as cpp

from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.moves import Move, MOVE_DATA, MoveCategory
from liveplay.data.species import Species
from liveplay.data.types import Type
from liveplay.actions import enumerate_legal_actions, Action, ActionKind, STRUGGLE_SLOT
from liveplay.state.battle import BattleState, PseudoWeather
from liveplay.state.pokemon import PokemonState, Volatile, VolatileEffect, GenderEnum
from liveplay.state.side import SideState

from tests.state_builders import make_mon, make_battle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _encode(state: BattleState) -> str:
    return json.dumps(sweep_io.to_jsonable(state))


def _cpp_legal(state: BattleState, side_idx: int, slot: int = 0) -> list[dict]:
    """Call the C++ binding and return a list of action dicts."""
    return cpp.enumerate_legal_actions(_encode(state), side_idx, slot)


def _action_tuple(a: Action) -> tuple:
    """Normalize a Python Action to a comparable tuple."""
    move_override = int(a.move_override) if a.move_override is not None else -1
    return (int(a.kind), a.move_slot, move_override, a.switch_to_slot,
            a.target_side, a.target_slot)


def _cpp_tuple(d: dict) -> tuple:
    return (d["kind"], d["move_slot"], d["move_override"],
            d["switch_to_slot"], d["target_side"], d["target_slot"])


def _py_legal_no_mega(state: BattleState, side_idx: int, slot: int = 0) -> list[tuple]:
    """Python oracle filtered to exclude mega variants."""
    actions = enumerate_legal_actions(state, side_idx, slot)
    return [_action_tuple(a) for a in actions if not a.mega]


def _cpp_legal_tuples(state: BattleState, side_idx: int, slot: int = 0) -> list[tuple]:
    return [_cpp_tuple(d) for d in _cpp_legal(state, side_idx, slot)]


def _assert_equal(state: BattleState, side_idx: int = 0, slot: int = 0) -> None:
    py = _py_legal_no_mega(state, side_idx, slot)
    cpp_result = _cpp_legal_tuples(state, side_idx, slot)
    assert cpp_result == py, f"side={side_idx} slot={slot}\nPy:  {py}\nC++: {cpp_result}"


def _make_mon_with_pp(species, moves, pp_list) -> PokemonState:
    """Make a mon with explicit PP values per slot."""
    mon = make_mon(species, moves=moves)
    return mon._replace(move_pp=tuple(pp_list) + (0,) * (4 - len(pp_list)))


# ---------------------------------------------------------------------------
# 1. RECHARGING → single MOVE with move_slot=-1
# ---------------------------------------------------------------------------

def test_recharging():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
    mon = mon._replace(volatiles=int(Volatile.RECHARGING))
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)))
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 2. charging_move_slot >= 0 → forced completion of the charge turn
# ---------------------------------------------------------------------------

def test_charging_move():
    mon = make_mon(Species.RATTATA, moves=(Move.FLY, Move.TACKLE))
    mon = mon._replace(charging_move_slot=0)
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)))
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 3. LOCKED_MOVE (Outrage/Thrash/Petal Dance)
# ---------------------------------------------------------------------------

def test_locked_move():
    mon = make_mon(Species.RATTATA, moves=(Move.OUTRAGE, Move.TACKLE))
    mon = mon._replace(volatiles=int(Volatile.LOCKED_MOVE), locked_slot=0)
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)))
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 4. ENCORE_ACTIVE → forced locked_slot
# ---------------------------------------------------------------------------

def test_encore_active():
    mon = make_mon(Species.RATTATA, moves=(Move.SPLASH, Move.TACKLE))
    mon = mon._replace(volatiles=int(Volatile.ENCORE_ACTIVE), locked_slot=0)
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)))
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 5. CHOICE_LOCKED with PP > 0 → locked move + switches
# ---------------------------------------------------------------------------

def test_choice_locked_with_pp():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE, Move.SPLASH),
                   item=Item.CHOICE_BAND)
    mon = mon._replace(volatiles=int(Volatile.CHOICE_LOCKED), locked_slot=0)
    bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)),
                        team0=[mon, bench])
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 6. CHOICE_LOCKED with PP = 0 → Struggle + switches
# ---------------------------------------------------------------------------

def test_choice_locked_no_pp_struggle_plus_switches():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE, Move.SPLASH),
                   item=Item.CHOICE_BAND)
    mon = mon._replace(volatiles=int(Volatile.CHOICE_LOCKED), locked_slot=0,
                       move_pp=(0, 5, 0, 0))
    bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)),
                        team0=[mon, bench])
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 7. Normal multi-move — all slots with PP
# ---------------------------------------------------------------------------

def test_normal_multi_move():
    mon = make_mon(Species.RATTATA,
                   moves=(Move.TACKLE, Move.GROWL, Move.SPLASH))
    bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)),
                        team0=[mon, bench])
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 8. PP-zero slots are skipped
# ---------------------------------------------------------------------------

def test_pp_zero_skipped():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE, Move.GROWL, Move.SPLASH))
    # Deplete PP on slot 1 (GROWL)
    mon = mon._replace(move_pp=(35, 0, 40, 0))
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)))
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 9. Gravity blocks gravity-blocked moves
# ---------------------------------------------------------------------------

def test_gravity_blocks_fly():
    mon = make_mon(Species.RATTATA, moves=(Move.FLY, Move.TACKLE))
    opp = make_mon(Species.RATTATA, moves=(Move.SPLASH,))
    state = make_battle(mon, opp)
    # Inject GRAVITY pseudo-weather
    state.pseudo_weather = [(PseudoWeather.GRAVITY, 3)]
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 10. Taunt blocks STATUS moves
# ---------------------------------------------------------------------------

def test_taunt_blocks_status():
    mon = make_mon(Species.RATTATA, moves=(Move.GROWL, Move.TACKLE))
    mon = mon._replace(volatiles=int(Volatile.TAUNT_ACTIVE))
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)))
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 11. Assault Vest blocks STATUS moves
# ---------------------------------------------------------------------------

def test_assault_vest_blocks_status():
    mon = make_mon(Species.RATTATA, moves=(Move.GROWL, Move.TACKLE),
                   item=Item.ASSAULT_VEST)
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)))
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 12. BOUND prevents switching (Shed Shell DOES bypass BOUND)
# ---------------------------------------------------------------------------

def test_bound_no_switch():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
    mon = mon._replace(timed_volatiles=[(VolatileEffect.BOUND, 3)])
    bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)),
                        team0=[mon, bench])
    _assert_equal(state, 0)


def test_shed_shell_bypasses_bound():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE,), item=Item.SHED_SHELL)
    mon = mon._replace(timed_volatiles=[(VolatileEffect.BOUND, 3)])
    bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)),
                        team0=[mon, bench])
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 13. TRAPPED prevents switching (Shed Shell does NOT bypass TRAPPED)
# ---------------------------------------------------------------------------

def test_trapped_no_switch():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
    mon = mon._replace(timed_volatiles=[(VolatileEffect.TRAPPED, 3)])
    bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)),
                        team0=[mon, bench])
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 14. Shadow Tag traps non-Ghost (normal case)
# ---------------------------------------------------------------------------

def test_shadow_tag_traps():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
    bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    # Opponent with Shadow Tag
    opp = make_mon(Species.WOBBUFFET, moves=(Move.SPLASH,), ability=Ability.SHADOW_TAG)
    state = make_battle(mon, opp, team0=[mon, bench])
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 15. Shadow Tag does NOT trap Ghost-type
# ---------------------------------------------------------------------------

def test_shadow_tag_ghost_immune():
    # Gengar is Ghost-type; force its types explicitly so species lookup doesn't interfere
    mon = make_mon(Species.GENGAR, moves=(Move.TACKLE,))
    mon = mon._replace(types=(Type.GHOST, Type.POISON))
    bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    opp = make_mon(Species.WOBBUFFET, moves=(Move.SPLASH,), ability=Ability.SHADOW_TAG)
    state = make_battle(mon, opp, team0=[mon, bench])
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 16. Magnet Pull traps Steel-type
# ---------------------------------------------------------------------------

def test_magnet_pull_traps_steel():
    mon = make_mon(Species.MAGNEMITE, moves=(Move.TACKLE,))
    mon = mon._replace(types=(Type.ELECTRIC, Type.STEEL))
    bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    opp = make_mon(Species.RATTATA, moves=(Move.SPLASH,), ability=Ability.MAGNET_PULL)
    state = make_battle(mon, opp, team0=[mon, bench])
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 17. Magnet Pull does NOT trap non-Steel
# ---------------------------------------------------------------------------

def test_magnet_pull_no_trap_non_steel():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
    bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    opp = make_mon(Species.RATTATA, moves=(Move.SPLASH,), ability=Ability.MAGNET_PULL)
    state = make_battle(mon, opp, team0=[mon, bench])
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 18. Arena Trap traps grounded non-Ghost
# ---------------------------------------------------------------------------

def test_arena_trap_traps_grounded():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
    bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    opp = make_mon(Species.DIGLETT, moves=(Move.SPLASH,), ability=Ability.ARENA_TRAP)
    state = make_battle(mon, opp, team0=[mon, bench])
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 19. Mold Breaker bypasses ability trapping
# ---------------------------------------------------------------------------

def test_mold_breaker_escapes_shadow_tag():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE,), ability=Ability.MOLD_BREAKER)
    bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    opp = make_mon(Species.WOBBUFFET, moves=(Move.SPLASH,), ability=Ability.SHADOW_TAG)
    state = make_battle(mon, opp, team0=[mon, bench])
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 20. All PP zero → forced Struggle (no switches if also trapped)
# ---------------------------------------------------------------------------

def test_all_pp_zero_forced_struggle():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE, Move.GROWL))
    mon = mon._replace(move_pp=(0, 0, 0, 0))
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)))
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 21. All moves STATUS + Taunt → Struggle (since no MOVE action left)
# ---------------------------------------------------------------------------

def test_taunt_all_status_struggle():
    mon = make_mon(Species.RATTATA, moves=(Move.GROWL, Move.SPLASH))
    mon = mon._replace(volatiles=int(Volatile.TAUNT_ACTIVE))
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)))
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 22. Gravity-blocked only moves → Struggle
# ---------------------------------------------------------------------------

def test_gravity_all_blocked_struggle():
    mon = make_mon(Species.RATTATA, moves=(Move.FLY, Move.BOUNCE))
    opp = make_mon(Species.RATTATA, moves=(Move.SPLASH,))
    state = make_battle(mon, opp)
    state.pseudo_weather = [(PseudoWeather.GRAVITY, 3)]
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 23. Bench slot with fainted member is skipped in switch list
# ---------------------------------------------------------------------------

def test_fainted_bench_skipped():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
    bench_alive = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    bench_fainted = make_mon(Species.RATTATA, moves=(Move.SPLASH,))
    bench_fainted = bench_fainted._replace(fainted=True)
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)),
                        team0=[mon, bench_fainted, bench_alive])
    _assert_equal(state, 0)


# ---------------------------------------------------------------------------
# 24. Mixed: some PP-zero, some valid, plus switches
# ---------------------------------------------------------------------------

def test_mixed_pp_and_switches():
    mon = make_mon(Species.RATTATA, moves=(Move.TACKLE, Move.GROWL, Move.SPLASH))
    mon = mon._replace(move_pp=(0, 40, 40, 0))
    bench = make_mon(Species.PIDGEY, moves=(Move.SPLASH,))
    state = make_battle(mon, make_mon(Species.RATTATA, moves=(Move.SPLASH,)),
                        team0=[mon, bench])
    _assert_equal(state, 0)
