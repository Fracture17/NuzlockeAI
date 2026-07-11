"""Engine-verified integration tests for doubles secondary-effect sweep paths.

LEDGER
======
PORTED:
  test_doubles_two_attackers_each_secondary — BODY_SLAM paralysis + MUD_SHOT speed drop
  test_doubles_spread_move_with_secondary   — ICY_WIND spread + speed drop secondary
  test_doubles_flinch                       — STOMP flinch on one foe, not the other
  test_doubles_proc_plus_secondary          — Static proc + Body Slam secondary simultaneously
  test_singles_secondary_regression         — singles BODY_SLAM paralysis still works

DROPPED: none
ALREADY-COVERED: none
FAILED-NEEDS-REVIEW: none

API MAPPING:
  OLD make_sim(luck0=GOOD) → SweepConfig(side0=SideOverrides(crit=True, roll=1.0,
      extra_overrides={RNGEvent.SECONDARY_FIRES: True, RNGEvent.PROC_FIRES: True,
                       RNGEvent.FLINCH: True}))
  OLD make_sim(luck0=BAD)  → SweepConfig()
"""
import copy
import math

from liveplay.battle_types import MatchResult
from liveplay.candidate import Candidate
from liveplay.data.abilities import Ability
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status
from liveplay.logger import LogEvent
from liveplay.rng import RNGEvent
from liveplay.sweep_driver import SideOverrides, SweepConfig, run_with_capture
from liveplay.sweep_run import run_candidate_sweep
from tests.state_builders import (
    BAD, dslot, make_battle, make_doubles_battle, make_mon, odelta, slot,
)


# ---------------------------------------------------------------------------
# Luck configs
# ---------------------------------------------------------------------------

# GOOD luck: force all secondaries, procs, flinches, crits, and max damage roll.
_GOOD_SIDE = SideOverrides(
    crit=True,
    roll=1.0,
    extra_overrides={
        RNGEvent.SECONDARY_FIRES: True,
        RNGEvent.PROC_FIRES: True,
        RNGEvent.FLINCH: True,
    },
)

_BAD_SIDE = SideOverrides()  # default SWEEP_LUCK = BAD for crits/secondaries/procs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mr(string_id, *, constant_name="", var_values=None, matched_text="", side_hint=None):
    return MatchResult(
        string_id=string_id, id_value=0, constant_name=constant_name,
        var_values=var_values or [], score=0, matched_text=matched_text, slot_labels=[],
        side_hint=side_hint,
    )


def _usedmove(attacker_upper, move_display, *, foe=False):
    return _mr(
        "STRINGID_USEDMOVE",
        constant_name="sText_AttackerUsedMove",
        var_values=[attacker_upper, move_display],
        side_hint=1 if foe else 0,
    )


def _hp_to_k(hp: int, max_hp: int) -> int:
    if hp == 0:
        return 0
    return max(1, math.floor(hp * 48 / max_hp))


def _side_of(state, species) -> int:
    """Return battle side (0=player, 1=opponent) containing species."""
    for side_idx in (0, 1):
        if any(mon.species == species for mon in state.sides[side_idx].team):
            return side_idx
    raise AssertionError(f"{species} is on neither side")


def _build_messages_from_events(capturing, state) -> list:
    """Translate engine log events to sweep-consumable MatchResult messages."""
    messages = []
    for ev, kw in capturing.events:
        if ev == LogEvent.MOVE_USE:
            messages.append(_usedmove(
                kw["user"].name,
                kw["move"].name.replace("_", " ").title(),
                foe=(kw["side"] == 1),
            ))
        elif ev == LogEvent.CRIT:
            messages.append(_mr("STRINGID_CRITICALHIT"))
        elif ev == LogEvent.STATUS_APPLY:
            status_to_id = {
                Status.PARALYSIS: "STRINGID_PKMNWASPARALYZED",
                Status.BURN:      "STRINGID_PKMNWASBURNED",
                Status.FREEZE:    "STRINGID_PKMNWASFROZEN",
                Status.POISON:    "STRINGID_PKMNWASPOISONED",
                Status.SLEEP:     "STRINGID_PKMNFELLASLEEP",
            }
            sid = status_to_id.get(kw["status"])
            if sid:
                target_side = _side_of(state, kw["target"])
                target_name = kw["target"].name
                mtext = (
                    f"Foe {target_name} {sid}!"
                    if target_side == 1
                    else f"{target_name} {sid}!"
                )
                messages.append(_mr(sid, var_values=[target_name],
                                    side_hint=target_side, matched_text=mtext))
        elif ev == LogEvent.STAT_BOOST:
            if kw["stages"] < 0:
                sid = "STRINGID_STATHARSHLY" if abs(kw["stages"]) >= 2 else "STRINGID_STATFELL"
            else:
                sid = "STRINGID_STATSHARPLY" if kw["stages"] >= 2 else "STRINGID_STATROSE"
            messages.append(_mr(sid, var_values=[kw["target"].name],
                                side_hint=_side_of(state, kw["target"])))
        elif ev == LogEvent.CANT_PARALYSIS:
            messages.append(_mr("STRINGID_PKMNISPARALYZED", var_values=[kw["pokemon"].name],
                                side_hint=_side_of(state, kw["pokemon"])))
        elif ev == LogEvent.CANT_FLINCH:
            messages.append(_mr("STRINGID_PKMNFLINCHED", var_values=[kw["pokemon"].name],
                                side_hint=_side_of(state, kw["pokemon"])))
        elif ev == LogEvent.FAINT:
            side = kw.get("side", 1)
            if side == 1:
                messages.append(_mr(
                    "STRINGID_TARGETFAINTED",
                    var_values=[kw["pokemon"].name],
                    matched_text=f"Foe {kw['pokemon'].name.title()}",
                    side_hint=1,
                ))
            else:
                messages.append(_mr("STRINGID_ATTACKERFAINTED", var_values=[kw["pokemon"].name],
                                    side_hint=0))
        elif ev == LogEvent.EXP_GAIN:
            messages.append(_mr(
                "STRINGID_PKMNGAINEDEXP",
                var_values=[kw["pokemon"].name, str(kw["amount"])],
            ))
    return messages


def _opp_delta_records(pristine, final, n_slots=2):
    """Build identity-bound HpDeltaSeq records for opponent slots that changed HP."""
    records = []
    for pos in range(n_slots):
        mon = pristine.sides[1].team[pristine.sides[1].active_indices[pos]]
        start_hp = mon.hp
        final_hp = final.sides[1].team[final.sides[1].active_indices[pos]].hp
        k_before = _hp_to_k(start_hp, mon.max_hp)
        k_after = _hp_to_k(final_hp, mon.max_hp)
        if k_before != k_after:
            records.append(odelta(mon.species, (k_before, k_after), max_hp=mon.max_hp, slot=pos))
    return records


# ---------------------------------------------------------------------------
# Test 1: Two attackers each with a different attributable secondary
# ---------------------------------------------------------------------------

def test_doubles_two_attackers_each_secondary():
    """CHARIZARD BODY_SLAM → SNORLAX (paralysis) + PIDGEOT MUD_SHOT → BLISSEY (speed drop)."""
    p0 = make_mon(Species.CHARIZARD, moves=(Move.BODY_SLAM,), level=50)
    p1 = make_mon(Species.PIDGEOT, moves=(Move.MUD_SHOT,), level=50)
    o0 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    o1 = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)

    pristine = make_doubles_battle(p0, p1, o0, o1)
    state_for_engine = copy.deepcopy(pristine)

    config = SweepConfig(side0=_GOOD_SIDE, side1=_BAD_SIDE)
    final, capturing = run_with_capture(
        state_for_engine,
        [dslot(0, target=0, source=0), dslot(0, target=1, source=1)],
        [dslot(0, target=0, source=0), dslot(0, target=0, source=1)],
        config,
    )
    assert final is not None, "run_with_capture returned None"

    assert capturing.fired(LogEvent.STATUS_APPLY, status=Status.PARALYSIS), (
        "Engine did not apply paralysis — GOOD luck should have forced Body Slam secondary"
    )
    assert capturing.fired(LogEvent.STAT_BOOST, stat=4, stages=-1), (
        "Engine did not apply speed drop — MUD_SHOT 100% secondary should always fire"
    )
    # Note: SWEEP_LUCK default has paralysis_threshold=0.0 (can act), so SNORLAX still acts
    # after being paralyzed this turn. CANT_PARALYSIS is only emitted when the mon is blocked.
    # The paralysis status IS applied; we only check that both effects are in the final state.

    messages = _build_messages_from_events(capturing, pristine)

    candidates = run_candidate_sweep(
        messages=messages,
        hp_deltas=_opp_delta_records(pristine, final),
        initial_candidates=[Candidate(state=pristine)],
    )
    assert len(candidates) >= 1, "Sweep returned no candidates"

    def _effects_reproduced(cand):
        s1 = cand.state.sides[1]
        snorlax_idx = s1.active_indices[0]
        blissey_idx = s1.active_indices[1]
        paralyzed = s1.team[snorlax_idx].status == Status.PARALYSIS
        speed_dropped = s1.team[blissey_idx].stat_stages[4] == -1
        return paralyzed and speed_dropped

    assert any(_effects_reproduced(c) for c in candidates), (
        "No candidate reproduced both SNORLAX paralysis and BLISSEY speed drop"
    )


# ---------------------------------------------------------------------------
# Test 2: Spread move with attributable secondary (ICY_WIND speed drop)
# ---------------------------------------------------------------------------

def test_doubles_spread_move_with_secondary():
    """ICY_WIND hits both foes; 100% speed drop fires on primary target (SNORLAX)."""
    p0 = make_mon(Species.CHARIZARD, moves=(Move.ICY_WIND,), level=50)
    p1 = make_mon(Species.PIDGEOT, moves=(Move.SPLASH,), level=50)
    o0 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)
    o1 = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)

    pristine = make_doubles_battle(p0, p1, o0, o1)
    state_for_engine = copy.deepcopy(pristine)

    config = SweepConfig(side0=_GOOD_SIDE, side1=_BAD_SIDE)
    final, capturing = run_with_capture(
        state_for_engine,
        [dslot(0, target=0, source=0), dslot(0, target=0, source=1)],
        [dslot(0, target=0, source=0), dslot(0, target=0, source=1)],
        config,
    )
    assert final is not None, "run_with_capture returned None"

    assert capturing.fired(LogEvent.DAMAGE, target=Species.SNORLAX), "ICY_WIND must hit SNORLAX"
    assert capturing.fired(LogEvent.DAMAGE, target=Species.BLISSEY), "ICY_WIND must hit BLISSEY"
    assert capturing.fired(LogEvent.STAT_BOOST, stat=4, stages=-1), (
        "ICY_WIND 100%-chance speed drop must fire on primary target"
    )

    messages = _build_messages_from_events(capturing, pristine)

    candidates = run_candidate_sweep(
        messages=messages,
        hp_deltas=_opp_delta_records(pristine, final),
        initial_candidates=[Candidate(state=pristine)],
    )
    assert len(candidates) >= 1, "Sweep returned no candidates"

    def _hp_matches(cand):
        for pos in range(2):
            exp_idx = final.sides[1].active_indices[pos]
            act_idx = cand.state.sides[1].active_indices[pos]
            if cand.state.sides[1].team[act_idx].hp != final.sides[1].team[exp_idx].hp:
                return False
        return True

    assert any(_hp_matches(c) for c in candidates), (
        "No candidate matched engine final per-target HP after ICY_WIND spread"
    )


# ---------------------------------------------------------------------------
# Test 3: Flinch — one foe flinches, partner does not
# ---------------------------------------------------------------------------

def test_doubles_flinch():
    """STOMP flinch on ARCANINE; BLISSEY does not flinch; sweep recovers HP."""
    # Speed ordering: CHARIZARD(120) > ARCANINE(115) > BLISSEY(75) > SLOWBRO(50)
    p0 = make_mon(Species.CHARIZARD, moves=(Move.STOMP,), level=50)
    p1 = make_mon(Species.SLOWBRO, moves=(Move.SPLASH,), level=50)
    o0 = make_mon(Species.ARCANINE, moves=(Move.SPLASH,), level=50)
    o1 = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)

    pristine = make_doubles_battle(p0, p1, o0, o1)
    state_for_engine = copy.deepcopy(pristine)

    config = SweepConfig(side0=_GOOD_SIDE, side1=_BAD_SIDE)
    final, capturing = run_with_capture(
        state_for_engine,
        [dslot(0, target=0, source=0), dslot(0, target=0, source=1)],
        [dslot(0, target=0, source=0), dslot(0, target=0, source=1)],
        config,
    )
    assert final is not None, "run_with_capture returned None"

    assert capturing.fired(LogEvent.CANT_FLINCH, pokemon=Species.ARCANINE), (
        "ARCANINE must have flinched with GOOD luck on STOMP"
    )
    assert not capturing.fired(LogEvent.CANT_FLINCH, pokemon=Species.BLISSEY), (
        "BLISSEY must NOT flinch (CHARIZARD only targeted ARCANINE)"
    )
    assert not final.sides[1].team[final.sides[1].active_indices[0]].fainted, (
        "ARCANINE must survive STOMP"
    )

    move_use_events = [(kw["user"], kw["move"]) for ev, kw in capturing.events if ev == LogEvent.MOVE_USE]
    assert move_use_events[0][0] == Species.CHARIZARD, "CHARIZARD must act first"
    assert Species.ARCANINE not in [sp for sp, _ in move_use_events], (
        "ARCANINE must NOT have a MOVE_USE event (it flinched)"
    )

    messages = _build_messages_from_events(capturing, pristine)

    candidates = run_candidate_sweep(
        messages=messages,
        hp_deltas=_opp_delta_records(pristine, final),
        initial_candidates=[Candidate(state=pristine)],
    )
    assert len(candidates) >= 1, "Sweep returned no candidates"

    def _flinch_reproduced(cand):
        s1 = cand.state.sides[1]
        expected_arcanine = final.sides[1].team[final.sides[1].active_indices[0]].hp
        expected_blissey = final.sides[1].team[final.sides[1].active_indices[1]].hp
        return (
            s1.team[s1.active_indices[0]].hp == expected_arcanine
            and s1.team[s1.active_indices[1]].hp == expected_blissey
        )

    assert any(_flinch_reproduced(c) for c in candidates), (
        "No candidate reproduced the flinch-consistent HP outcome"
    )


# ---------------------------------------------------------------------------
# Test 4: Move-secondary AND ability proc (Static) in the same turn
# ---------------------------------------------------------------------------

def test_doubles_proc_plus_secondary():
    """CHARIZARD BODY_SLAM → SNORLAX (Static): both SNORLAX paralysis and CHARIZARD paralysis."""
    p0 = make_mon(Species.CHARIZARD, moves=(Move.BODY_SLAM,), level=50)
    p1 = make_mon(Species.PIDGEOT, moves=(Move.SPLASH,), level=50)
    o0 = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50, ability=Ability.STATIC)
    o1 = make_mon(Species.BLISSEY, moves=(Move.SPLASH,), level=50)

    pristine = make_doubles_battle(p0, p1, o0, o1)
    state_for_engine = copy.deepcopy(pristine)

    config = SweepConfig(side0=_GOOD_SIDE, side1=_BAD_SIDE)
    final, capturing = run_with_capture(
        state_for_engine,
        [dslot(0, target=0, source=0), dslot(0, target=0, source=1)],
        [dslot(0, target=0, source=0), dslot(0, target=0, source=1)],
        config,
    )
    assert final is not None, "run_with_capture returned None"

    all_paralysis = capturing.all_of(LogEvent.STATUS_APPLY, status=Status.PARALYSIS)
    assert len(all_paralysis) >= 2, (
        f"Expected ≥2 STATUS_APPLY paralysis events (proc + secondary), got {len(all_paralysis)}"
    )
    charizard_paralyzed = any(e["target"] == Species.CHARIZARD for e in all_paralysis)
    snorlax_paralyzed = any(e["target"] == Species.SNORLAX for e in all_paralysis)
    assert charizard_paralyzed, "CHARIZARD must be paralyzed by Static proc (GOOD luck)"
    assert snorlax_paralyzed, "SNORLAX must be paralyzed by Body Slam secondary (GOOD luck)"

    # Build messages manually: CHARIZARD uses PKMNWASPARALYZEDBY variant (ability proc),
    # SNORLAX uses PKMNWASPARALYZED variant (move secondary).
    messages = []
    for ev, kw in capturing.events:
        if ev == LogEvent.MOVE_USE:
            messages.append(_usedmove(
                kw["user"].name,
                kw["move"].name.replace("_", " ").title(),
                foe=(kw["side"] == 1),
            ))
        elif ev == LogEvent.CRIT:
            messages.append(_mr("STRINGID_CRITICALHIT"))
        elif ev == LogEvent.STATUS_APPLY and kw["status"] == Status.PARALYSIS:
            target_name = kw["target"].name
            if kw["target"] == Species.CHARIZARD:
                # Proc variant: "Foe Snorlax's Static paralyzed Charizard!"
                messages.append(_mr(
                    "STRINGID_PKMNWASPARALYZEDBY",
                    var_values=["SNORLAX", "STATIC", target_name],
                    matched_text="Foe Snorlax's Static paralyzed Charizard!",
                ))
            else:
                # Move secondary: "Foe Snorlax was paralyzed!"
                messages.append(_mr(
                    "STRINGID_PKMNWASPARALYZED",
                    var_values=[target_name],
                    matched_text=f"Foe {target_name.title()} was paralyzed!",
                ))
        elif ev == LogEvent.CANT_PARALYSIS:
            messages.append(_mr("STRINGID_PKMNISPARALYZED", var_values=[kw["pokemon"].name],
                                side_hint=_side_of(pristine, kw["pokemon"])))

    candidates = run_candidate_sweep(
        messages=messages,
        hp_deltas=_opp_delta_records(pristine, final),
        initial_candidates=[Candidate(state=pristine)],
    )
    assert len(candidates) >= 1, "Sweep returned no candidates"

    def _both_paralyzed(cand):
        s0 = cand.state.sides[0]
        s1 = cand.state.sides[1]
        charizard_idx = s0.active_indices[0]
        snorlax_idx = s1.active_indices[0]
        return (
            s0.team[charizard_idx].status == Status.PARALYSIS
            and s1.team[snorlax_idx].status == Status.PARALYSIS
        )

    assert any(_both_paralyzed(c) for c in candidates), (
        "No candidate reproduced both CHARIZARD paralysis (proc) and SNORLAX paralysis (secondary)"
    )


# ---------------------------------------------------------------------------
# Test 5: Singles regression — attributable secondary on the scalar legacy path
# ---------------------------------------------------------------------------

def test_singles_secondary_regression():
    """Singles: CHARIZARD BODY_SLAM → SNORLAX; paralysis secondary fires with GOOD luck."""
    p = make_mon(Species.CHARIZARD, moves=(Move.BODY_SLAM,), level=50)
    o = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), level=50)

    pristine = make_battle(p, o)
    state_for_engine = copy.deepcopy(pristine)

    config = SweepConfig(side0=_GOOD_SIDE, side1=_BAD_SIDE)
    final, capturing = run_with_capture(state_for_engine, slot(0), slot(0), config)
    assert final is not None, "run_with_capture returned None"

    assert not final.sides[1].team[final.sides[1].active_indices[0]].fainted, (
        "SNORLAX should survive CHARIZARD Body Slam"
    )
    assert capturing.fired(LogEvent.STATUS_APPLY, status=Status.PARALYSIS), (
        "GOOD luck must have forced Body Slam paralysis secondary to fire"
    )
    assert final.sides[1].team[final.sides[1].active_indices[0]].status == Status.PARALYSIS, (
        "SNORLAX must be paralyzed in the final state"
    )

    messages = _build_messages_from_events(capturing, pristine)

    opp_max_hp = pristine.sides[1].team[pristine.sides[1].active_indices[0]].max_hp
    opp_start_hp = pristine.sides[1].team[pristine.sides[1].active_indices[0]].hp
    opp_final_hp = final.sides[1].team[final.sides[1].active_indices[0]].hp
    k_before = _hp_to_k(opp_start_hp, opp_max_hp)
    k_after = _hp_to_k(opp_final_hp, opp_max_hp)

    opp_species = pristine.sides[1].team[pristine.sides[1].active_indices[0]].species
    candidates = run_candidate_sweep(
        messages=messages,
        hp_deltas=[odelta(opp_species, (k_before, k_after), max_hp=opp_max_hp)],
        initial_candidates=[Candidate(state=pristine)],
    )
    assert len(candidates) >= 1, "Sweep returned no candidates"

    def _paralysis_and_hp(cand):
        s1 = cand.state.sides[1]
        idx = s1.active_indices[0]
        return (
            s1.team[idx].status == Status.PARALYSIS
            and s1.team[idx].hp == opp_final_hp
        )

    assert any(_paralysis_and_hp(c) for c in candidates), (
        "No candidate reproduced SNORLAX paralysis and final HP (singles secondary regression)"
    )
