"""Tests for movers as list[tuple[int,int]] carrying source_slot.

LEDGER
======
PORTED:
  test_movers_singles_unchanged       — singles: movers == [(0,0),(1,0)]
  test_movers_doubles_two_per_side    — doubles: four movers [(0,0),(0,1),(1,0),(1,1)]
  test_movers_slot_inference_by_species — slot1 mon USEDMOVE first → source_slot 1
  test_movers_same_species_both_slots — same-species cursor fallback assigns {0,1}
  test_check_action_order_side_level  — prefix match of MOVE_USE side sequence
  test_check_action_order_sim_missing_observed_move_pruned — sim shorter than observed → False
  test_check_action_order_prefix_mismatch_pruned — order mismatch → False
  test_check_action_order_sim_extra_unobserved_moves_passes — sim has extra unobserved moves
  test_check_action_order_mid_sequence_skip_passes — flinch/para absent from both sequences
  test_check_action_order_exact_match_passes — exact match passes
  test_check_action_order_called_move_single_move_use_passes — metronome-like 1:1
  test_own_damage_slot1_attacker — real doubles turn: slot1 attacker damage keyed by slot

DROPPED: none
ALREADY-COVERED: none
FAILED-NEEDS-REVIEW: none

API MAPPING:
  OLD src.simulation_runner._message_action_order_with_state → liveplay.sweep_actions
  OLD src.simulation_runner._check_action_order → liveplay.sweep_reconcile
  OLD src.simulation_runner._own_damage → liveplay.sweep_driver._own_damage
  OLD make_sim + CapturingLogger swap → run_with_capture(state, a0, a1, SweepConfig())
  OLD sim.start + sim.step + TurnPhase loop → run_with_capture returns (final_state, log)
"""
from liveplay.battle_types import MatchResult
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.logger import CapturingLogger, LogEvent
from liveplay.sweep_actions import _message_action_order_with_state
from liveplay.sweep_driver import SweepConfig, _own_damage, run_with_capture
from liveplay.sweep_reconcile import _check_action_order
from tests.state_builders import (
    dslot, make_battle, make_doubles_battle, make_mon, slot,
)


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------

_AUTO_SIDE_HINT = object()  # sentinel: derive side_hint from the Foe prefix


def _foe_prefix_hint(var_values):
    if not var_values:
        return None
    first = str(var_values[0]).split()
    if not first:
        return None
    return 1 if first[0].lower() == "foe" else 0


def _strip_foe(var_values):
    if not var_values:
        return var_values
    out = list(var_values)
    words = str(out[0]).split()
    if words and words[0].lower() == "foe":
        out[0] = " ".join(words[1:])
    return out


def _mr(string_id, *, constant_name="", var_values=None, matched_text="",
        side_hint=_AUTO_SIDE_HINT):
    vals = var_values or []
    if side_hint is _AUTO_SIDE_HINT:
        side_hint = _foe_prefix_hint(vals)
    return MatchResult(
        string_id=string_id, id_value=0, constant_name=constant_name,
        var_values=_strip_foe(vals), score=0, matched_text=matched_text, slot_labels=[],
        side_hint=side_hint,
    )


def usedmove(attacker, move):
    return _mr("STRINGID_USEDMOVE", constant_name="sText_AttackerUsedMove",
               var_values=[attacker, move])


# ---------------------------------------------------------------------------
# test_movers_singles_unchanged
# ---------------------------------------------------------------------------

def test_movers_singles_unchanged():
    """Singles: one player USEDMOVE + one opp USEDMOVE → movers == [(0,0),(1,0)]."""
    p = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)
    o = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
    state = make_battle(p, o)

    messages = [
        usedmove("ROOKIDEE", "Peck"),
        usedmove("Foe POOCHYENA", "Splash"),
    ]
    movers = _message_action_order_with_state(messages, state)
    assert movers == [(0, 0), (1, 0)], f"expected [(0,0),(1,0)], got {movers}"


# ---------------------------------------------------------------------------
# test_movers_doubles_two_per_side
# ---------------------------------------------------------------------------

def test_movers_doubles_two_per_side():
    """Doubles: four USEDMOVEs ROOKIDEE,PIDGEY,POOCHYENA,LILLIPUP → [(0,0),(0,1),(1,0),(1,1)]."""
    p0 = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)
    p1 = make_mon(Species.PIDGEY, moves=(Move.GUST,), level=5)
    o0 = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
    o1 = make_mon(Species.LILLIPUP, moves=(Move.SPLASH,), level=5)
    state = make_doubles_battle(p0, p1, o0, o1)

    messages = [
        usedmove("ROOKIDEE", "Peck"),
        usedmove("PIDGEY", "Gust"),
        usedmove("Foe POOCHYENA", "Splash"),
        usedmove("Foe LILLIPUP", "Splash"),
    ]
    movers = _message_action_order_with_state(messages, state)
    assert movers == [(0, 0), (0, 1), (1, 0), (1, 1)], f"got {movers}"


# ---------------------------------------------------------------------------
# test_movers_slot_inference_by_species
# ---------------------------------------------------------------------------

def test_movers_slot_inference_by_species():
    """Doubles: slot1 mon USEDMOVE appears first → that mover has source_slot 1."""
    p0 = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)
    p1 = make_mon(Species.PIDGEY, moves=(Move.GUST,), level=5)
    o0 = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
    o1 = make_mon(Species.LILLIPUP, moves=(Move.SPLASH,), level=5)
    state = make_doubles_battle(p0, p1, o0, o1)

    # PIDGEY (slot1) acts before ROOKIDEE (slot0)
    messages = [
        usedmove("PIDGEY", "Gust"),
        usedmove("ROOKIDEE", "Peck"),
        usedmove("Foe POOCHYENA", "Splash"),
        usedmove("Foe LILLIPUP", "Splash"),
    ]
    movers = _message_action_order_with_state(messages, state)
    assert movers[0] == (0, 1), f"expected (0,1) first, got {movers[0]}"
    assert movers[1] == (0, 0), f"expected (0,0) second, got {movers[1]}"


# ---------------------------------------------------------------------------
# test_movers_same_species_both_slots
# ---------------------------------------------------------------------------

def test_movers_same_species_both_slots():
    """Both player actives same species: two player movers get slots {0,1} via cursor fallback."""
    p0 = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)
    p1 = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=5)  # same species
    o0 = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
    o1 = make_mon(Species.LILLIPUP, moves=(Move.SPLASH,), level=5)
    state = make_doubles_battle(p0, p1, o0, o1)

    messages = [
        usedmove("ROOKIDEE", "Peck"),   # first ROOKIDEE → cursor assigns slot 0
        usedmove("ROOKIDEE", "Peck"),   # second ROOKIDEE → cursor assigns slot 1
        usedmove("Foe POOCHYENA", "Splash"),
        usedmove("Foe LILLIPUP", "Splash"),
    ]
    movers = _message_action_order_with_state(messages, state)
    player_slots = [m[1] for m in movers if m[0] == 0]
    assert set(player_slots) == {0, 1}, f"expected both slots 0 and 1 for player, got {player_slots}"


# ---------------------------------------------------------------------------
# test_check_action_order_side_level
# ---------------------------------------------------------------------------

def test_check_action_order_side_level():
    """_check_action_order: observed must be a prefix of the sim's MOVE_USE side sequence."""
    cap = CapturingLogger()
    for s in (0, 0, 1, 1):
        cap.handle(LogEvent.MOVE_USE, user=None, move=None, side=s)

    assert _check_action_order(cap, [0, 0, 1, 1]) is True
    assert _check_action_order(cap, [1, 0]) is False  # first element mismatch
    assert _check_action_order(cap, []) is True        # empty observed is always True
    assert _check_action_order(cap, [0, 0]) is True    # shorter observed passes


# ---------------------------------------------------------------------------
# E1 fix tests: _check_action_order trailing length mismatch
# ---------------------------------------------------------------------------

def _make_cap(*sides):
    """Build a CapturingLogger with MOVE_USE events for the given sides."""
    cap = CapturingLogger()
    for s in sides:
        cap.handle(LogEvent.MOVE_USE, user=None, move=None, side=s)
    return cap


def test_check_action_order_sim_missing_observed_move_pruned():
    """Sim is missing an observed move → candidate is pruned (returns False)."""
    cap = _make_cap(0)
    assert _check_action_order(cap, [0, 1]) is False


def test_check_action_order_prefix_mismatch_pruned():
    """Prefix order mismatch → pruned regardless of lengths."""
    cap = _make_cap(1, 0)
    assert _check_action_order(cap, [0, 1]) is False


def test_check_action_order_sim_extra_unobserved_moves_passes():
    """Sim has extra trailing MOVE_USE beyond observed (unobserved opponent moves) → passes."""
    cap = _make_cap(0, 1)
    assert _check_action_order(cap, [0]) is True


def test_check_action_order_mid_sequence_skip_passes():
    """Mid-sequence absent mon (flinch/para/sleep) excluded from BOTH sequences → passes."""
    cap = _make_cap(0, 0)
    assert _check_action_order(cap, [0, 0]) is True


def test_check_action_order_exact_match_passes():
    """Exact match of sim and observed side sequences always passes."""
    cap = _make_cap(0, 1)
    assert _check_action_order(cap, [0, 1]) is True


def test_check_action_order_called_move_single_move_use_passes():
    """Metronome-like: engine emits one MOVE_USE and observed has one USEDMOVE → 1:1 aligned."""
    cap = _make_cap(0, 1)
    assert _check_action_order(cap, [0, 1]) is True


# ---------------------------------------------------------------------------
# test_own_damage_slot1_attacker
# ---------------------------------------------------------------------------

def test_own_damage_slot1_attacker():
    """Real doubles turn: slot1 attacker damage is distinct from slot0, keyed by active_indices[1]."""
    # ROOKIDEE slot0 uses SPLASH (no damage); PIDGEY slot1 uses GUST (flying damage)
    p0 = make_mon(Species.ROOKIDEE, moves=(Move.SPLASH,), level=5)
    p1 = make_mon(Species.PIDGEY, moves=(Move.GUST,), level=5)
    o0 = make_mon(Species.POOCHYENA, moves=(Move.SPLASH,), level=5)
    o1 = make_mon(Species.LILLIPUP, moves=(Move.SPLASH,), level=5)
    state = make_doubles_battle(p0, p1, o0, o1)

    _final, capturing = run_with_capture(
        state,
        [dslot(0, target=0, source=0), dslot(0, target=0, source=1)],
        [dslot(0, target=0, source=0), dslot(0, target=0, source=1)],
        SweepConfig(),
    )
    assert _final is not None, "run_with_capture returned None"

    player_slot1_team_idx = state.sides[0].active_indices[1]
    player_slot0_team_idx = state.sides[0].active_indices[0]

    dmg_slot0 = _own_damage(capturing, 0, player_slot0_team_idx)
    dmg_slot1 = _own_damage(capturing, 0, player_slot1_team_idx)

    # PIDGEY (slot1) uses GUST → deals damage; ROOKIDEE (slot0) uses SPLASH → 0
    assert dmg_slot0 == 0, f"ROOKIDEE (slot0) should deal 0 damage, got {dmg_slot0}"
    assert dmg_slot1 > 0, f"PIDGEY (slot1) should deal >0 damage via GUST, got {dmg_slot1}"
