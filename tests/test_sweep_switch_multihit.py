# Port of OLD tests/test_sweep_switch_multihit.py — regression for multi-hit move
# landing on a Pokémon that switched in this turn.
#
# Bug: the sweep's multi-hit enumeration read its target's species from the pre-turn
# state (the active mon *before* the switch). When the player switched Rookidee→Pidgey
# and then Pineco's 3-hit Pin Missile hit Pidgey, the enumeration looked for damage
# dealt to Rookidee (who had left), found none, produced zero candidates, and the sweep
# raised "No candidates survived sweep". The fix unifies both paths onto attacker-keyed
# damage discovery.
from __future__ import annotations

import pytest

from liveplay.battle_types import MatchResult
from liveplay.candidate import Candidate
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.sweep_run import run_candidate_sweep
from liveplay.state.battle import BattleState
from liveplay.state.side import SideState
from tests.state_builders import make_mon, pdelta


def _mr(string_id, *, constant_name="", var_values=None, matched_text="", side_hint=None):
    return MatchResult(
        string_id=string_id, id_value=0, constant_name=constant_name,
        var_values=var_values or [], score=0, matched_text=matched_text, slot_labels=[],
        side_hint=side_hint,
    )


def test_multihit_on_mon_that_switched_in_this_turn():
    """Player switches Rookidee→Pidgey, then opponent's 3-hit Pin Missile (1 crit, NVE) hits Pidgey.

    Pre-fix this raised SimulationError because the multi-hit enumeration keyed damage on the
    pre-switch active (Rookidee). Post-fix it keys on the attacker, so ≥1 candidate survives.
    """
    rookidee = make_mon(Species.ROOKIDEE, moves=(Move.TACKLE,), level=10)
    pidgey = make_mon(Species.PIDGEY, moves=(Move.GUST, Move.TACKLE), level=10)
    pineco = make_mon(Species.PINECO, moves=(Move.PIN_MISSILE,), level=6)
    side0 = SideState(team=[rookidee, pidgey], active_indices=[0])
    side1 = SideState(team=[pineco], active_indices=[0])
    state = BattleState(sides=(side0, side1))

    messages = [
        _mr("STRINGID_RETURNMON", constant_name="sText_PkmnThatsEnough",
            var_values=["ROOKIDEE"], matched_text="ROOKIDEE , that's enough! Come back!"),
        _mr("STRINGID_PLAYER_INTROSENDOUT", constant_name="sText_GoPkmn",
            var_values=["PIDGEY"], matched_text="Go! PIDGEY!"),
        _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
            var_values=["PINECO", "PIN MISSILE"], matched_text="Foe PINECO used PIN MISSILE!",
            side_hint=1),
        _mr("STRINGID_CRITICALHIT", matched_text="A critical hit!"),
        _mr("STRINGID_NOTVERYEFFECTIVE", matched_text="It's not very effective"),
        _mr("STRINGID_HITXTIMES", var_values=["3"], matched_text="Hit 3 time(s)!"),
    ]
    # Pidgey takes 3 hits: 2 (non-crit), 3 (crit), 2 (non-crit). Bug→Flying is 0.5×.
    mh = pidgey.max_hp
    deltas = [pdelta(Species.PIDGEY, (mh, mh - 2), (mh - 2, mh - 5), (mh - 5, mh - 7),
                     slot=0, max_hp=mh)]

    candidates = run_candidate_sweep(
        messages=messages,
        hp_deltas=deltas,
        initial_candidates=[Candidate(state=state)],
    )
    assert len(candidates) >= 1
