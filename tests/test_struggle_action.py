"""Port of OLD tests/test_struggle_action.py — forced-Struggle action tests.

Background (Issue 28): when a Pokemon has NO usable move (all PP=0, etc.), the ROM
forces it to use Struggle. Tests are organized as:
  * DEFENSIVE — pin current correct behavior we must not break.
  * NEW STRUGGLE enumeration — forced-Struggle action enumeration.
  * NEW STRUGGLE execution — Struggle dealing damage and recoil.
  * NEW STRUGGLE extraction + scoring + sweep — full pipeline.

Execution tests use run_with_capture (NEW analog for OLD capture_turn) with
SideOverrides(crit=False) to match the BAD_LUCK approach used in the OLD tests.
"""
from __future__ import annotations

import pytest

from liveplay.battle_types import MatchResult
from liveplay.data.items import Item
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.actions import Action, ActionKind, enumerate_legal_actions
from liveplay.engine_select import SimulationError, compute_action_probabilities
from liveplay.logger import LogEvent
from liveplay.state.battle import PseudoWeather
from liveplay.state.pokemon import Volatile
from liveplay.sweep_actions import _extract_known_actions, _sweep_resolve_candidate_actions
from liveplay.sweep_driver import SideOverrides, SweepConfig, run_with_capture
from liveplay.sweep_run import run_candidate_sweep
from liveplay.candidate import Candidate
from tests.state_builders import (
    make_mon, make_battle, slot, switch_to,
    active, assert_event, assert_no_event, odelta, pdelta,
)

STRUGGLE_ACTION = Action(kind=ActionKind.MOVE, move_slot=-2, move_override=Move.STRUGGLE)
_NO_CRIT_CONFIG = SweepConfig(
    side0=SideOverrides(crit=False),
    side1=SideOverrides(crit=False),
)


def _struggle_actions(legal):
    return [a for a in legal if a.kind == ActionKind.MOVE and a.move_override == Move.STRUGGLE]


def _move_actions(legal):
    return [a for a in legal if a.kind == ActionKind.MOVE]


def _switch_actions(legal):
    return [a for a in legal if a.kind == ActionKind.SWITCH]


def _usedmove(attacker_name, move_name, *, side_hint):
    return MatchResult(
        string_id="STRINGID_USEDMOVE",
        id_value=0,
        constant_name="sText_AttackerUsedMove",
        var_values=[attacker_name, move_name],
        score=0,
        matched_text=f"{attacker_name} used {move_name}!",
        slot_labels=[],
        side_hint=side_hint,
    )


# ===========================================================================
# DEFENSIVE — must PASS (no Struggle, current behavior preserved)
# ===========================================================================

class TestDefensiveNoStruggle:
    def test_recharge_enumerates_bare_recharge_not_struggle(self):
        """A recharging mon returns exactly the recharge action (move_slot=-1, no override)."""
        mon = make_mon(Species.SNORLAX, moves=(Move.HYPER_BEAM,))
        mon = mon._replace(volatiles=mon.volatiles | Volatile.RECHARGING)
        opp = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        state = make_battle(mon, opp)

        legal = enumerate_legal_actions(state, 0)
        assert legal == [Action(kind=ActionKind.MOVE, move_slot=-1)]
        assert legal[0].move_override is None
        assert _struggle_actions(legal) == []

    def test_charging_move_not_struggle_even_if_pp_zero(self):
        """A mon mid-charge is forced to complete the charging move, never Struggle."""
        mon = make_mon(Species.PIDGEOT, moves=(Move.FLY, Move.TACKLE))
        mon = mon._replace(charging_move_slot=0, move_pp=(0, 0, 0, 0))
        opp = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        state = make_battle(mon, opp)

        legal = enumerate_legal_actions(state, 0)
        assert legal == [Action(kind=ActionKind.MOVE, move_slot=0)]
        assert _struggle_actions(legal) == []

    def test_mon_with_usable_move_gets_no_struggle(self):
        """A mon with at least one PP-positive move must NOT be offered Struggle."""
        mon = make_mon(Species.PIKACHU, moves=(Move.THUNDERBOLT, Move.TACKLE))
        opp = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(mon, opp, team0=[mon, make_mon(Species.EEVEE)])

        legal = enumerate_legal_actions(state, 0)
        assert _struggle_actions(legal) == []
        assert len(_move_actions(legal)) >= 1


# ===========================================================================
# NEW STRUGGLE — enumeration
# ===========================================================================

class TestStruggleEnumeration:
    def test_all_pp_zero_emits_struggle_plus_switch(self):
        """All moves out of PP, a healthy bench mon present: enumerate Struggle AND the switch."""
        mon = make_mon(Species.MAGIKARP, moves=(Move.BOUNCE,))._replace(move_pp=(0, 0, 0, 0))
        bench = make_mon(Species.GYARADOS, moves=(Move.SPLASH,))
        opp = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        state = make_battle(mon, opp, team0=[mon, bench])

        legal = enumerate_legal_actions(state, 0)
        struggles = _struggle_actions(legal)
        assert len(struggles) == 1, f"expected exactly one Struggle action, got {legal}"
        assert struggles[0].move_slot == -2
        assert any(a.switch_to_slot == 1 for a in _switch_actions(legal))
        assert all(a.move_override == Move.STRUGGLE for a in _move_actions(legal))

    def test_all_pp_zero_no_bench_emits_struggle_only(self):
        mon = make_mon(Species.MAGIKARP, moves=(Move.BOUNCE,))._replace(move_pp=(0, 0, 0, 0))
        opp = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        state = make_battle(mon, opp)

        legal = enumerate_legal_actions(state, 0)
        assert legal == [STRUGGLE_ACTION]

    def test_taunt_only_status_emits_struggle(self):
        """Taunt blocks the only (status) moves, which still have PP → forced Struggle."""
        mon = make_mon(Species.MEOWTH, moves=(Move.GROWL, Move.TAIL_WHIP))
        mon = mon._replace(volatiles=mon.volatiles | Volatile.TAUNT_ACTIVE)
        opp = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        state = make_battle(mon, opp)

        legal = enumerate_legal_actions(state, 0)
        assert len(_struggle_actions(legal)) == 1

    def test_assault_vest_only_status_emits_struggle(self):
        """Assault Vest forbids status moves; a status-only moveset → forced Struggle."""
        mon = make_mon(Species.MEOWTH, moves=(Move.GROWL, Move.TAIL_WHIP), item=Item.ASSAULT_VEST)
        opp = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        state = make_battle(mon, opp)

        legal = enumerate_legal_actions(state, 0)
        assert len(_struggle_actions(legal)) == 1

    def test_gravity_blocked_only_move_emits_struggle(self):
        """Under Gravity, a gravity-blocked move (High Jump Kick) is unselectable; if it is the
        only PP-positive move, the mon is forced to Struggle."""
        mon = make_mon(Species.HITMONLEE, moves=(Move.HIGH_JUMP_KICK,))
        opp = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        state = make_battle(mon, opp)
        state.pseudo_weather.append((PseudoWeather.GRAVITY, 5))

        legal = enumerate_legal_actions(state, 0)
        assert len(_struggle_actions(legal)) == 1, f"got {legal}"
        assert all(a.move_override == Move.STRUGGLE for a in _move_actions(legal))

    def test_gravity_filters_blocked_move_but_keeps_others(self):
        """Gravity removes only the blocked move; a normal move stays selectable and no
        Struggle is offered."""
        mon = make_mon(Species.HITMONLEE, moves=(Move.HIGH_JUMP_KICK, Move.TACKLE))
        opp = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        state = make_battle(mon, opp)
        state.pseudo_weather.append((PseudoWeather.GRAVITY, 5))

        legal = enumerate_legal_actions(state, 0)
        move_slots = {a.move_slot for a in _move_actions(legal)}
        assert move_slots == {1}, f"only Tackle (slot 1) should remain, got {move_slots}"
        assert _struggle_actions(legal) == []

    def test_no_gravity_blocked_move_is_offered(self):
        """Defensive: without Gravity the same move is a normal legal action."""
        mon = make_mon(Species.HITMONLEE, moves=(Move.HIGH_JUMP_KICK,))
        opp = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        state = make_battle(mon, opp)

        legal = enumerate_legal_actions(state, 0)
        assert any(a.move_slot == 0 for a in _move_actions(legal))
        assert _struggle_actions(legal) == []

    def test_choice_locked_zero_pp_emits_struggle_plus_switch(self):
        """Choice-locked onto a move that is now out of PP → Struggle + switches (not switch-only)."""
        mon = make_mon(Species.MAGIKARP, moves=(Move.TACKLE, Move.SPLASH), item=Item.CHOICE_BAND)
        mon = mon._replace(volatiles=mon.volatiles | Volatile.CHOICE_LOCKED,
                           locked_slot=0, move_pp=(0, 10, 0, 0))
        bench = make_mon(Species.GYARADOS, moves=(Move.SPLASH,))
        opp = make_mon(Species.PIKACHU, moves=(Move.SPLASH,))
        state = make_battle(mon, opp, team0=[mon, bench])

        legal = enumerate_legal_actions(state, 0)
        assert len(_struggle_actions(legal)) == 1, f"got {legal}"
        assert any(a.switch_to_slot == 1 for a in _switch_actions(legal))


# ===========================================================================
# NEW STRUGGLE — engine execution (run_with_capture)
# ===========================================================================

class TestStruggleExecution:
    def test_struggle_deals_damage_and_recoil_no_pp(self):
        """Struggle deals damage to the defender and recoil (1/4 max_hp) to the attacker."""
        attacker = make_mon(Species.MAGIKARP, moves=(Move.BOUNCE,))._replace(move_pp=(0, 0, 0, 0))
        defender = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        # side 0 = defender (uses slot(0)=Splash), side 1 = attacker (uses Struggle)
        state = make_battle(defender, attacker)

        final, log = run_with_capture(state, slot(0), STRUGGLE_ACTION, _NO_CRIT_CONFIG)
        assert final is not None, "run_with_capture returned None — engine may have NeedsRNG"

        assert_event(log, LogEvent.MOVE_USE, move=Move.STRUGGLE)
        # Defender (side 0) took damage.
        assert active(final, 0).hp < defender.max_hp
        # Recoil = 1/4 of the Struggler's max HP.
        expected_recoil = max(1, attacker.max_hp // 4)
        assert_event(log, LogEvent.DAMAGE, source="recoil", amount=expected_recoil)
        assert active(final, 1).hp == attacker.max_hp - expected_recoil
        # Struggle consumes no PP.
        assert active(final, 1).move_pp == (0, 0, 0, 0)
        assert_no_event(log, LogEvent.PP_USE, move=Move.STRUGGLE)

    def test_struggle_action_consumes_no_pp_from_any_slot(self):
        """A Struggle action must touch NO move_pp slot (regression for _consume_pp(slot=-2))."""
        attacker = make_mon(Species.SNORLAX, moves=(Move.TACKLE, Move.HEADBUTT, Move.BODY_SLAM, Move.REST))
        defender = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        pp_before = attacker.move_pp
        state = make_battle(defender, attacker)

        final, _ = run_with_capture(state, slot(0), STRUGGLE_ACTION, _NO_CRIT_CONFIG)
        assert final is not None
        assert active(final, 1).move_pp == pp_before

    def test_struggle_sets_negative_last_used_slot(self):
        """Struggle is not a real slot, so last_used_slot must not point at a move (stays <0)."""
        attacker = make_mon(Species.MAGIKARP, moves=(Move.BOUNCE,))._replace(move_pp=(0, 0, 0, 0))
        defender = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
        state = make_battle(defender, attacker)

        final, _ = run_with_capture(state, slot(0), STRUGGLE_ACTION, _NO_CRIT_CONFIG)
        assert final is not None
        assert active(final, 1).last_used_slot < 0


# ===========================================================================
# NEW STRUGGLE — action extraction + AI scoring + sweep
# ===========================================================================

class TestStruggleExtractionAndScoring:
    def test_extract_known_actions_builds_struggle(self):
        player = make_mon(Species.LILLIPUP, moves=(Move.TACKLE,))
        opp = make_mon(Species.MAGIKARP, moves=(Move.BOUNCE,))._replace(move_pp=(0, 0, 0, 0))
        bench = make_mon(Species.MAGIKARP, moves=(Move.SPLASH,))
        state = make_battle(player, opp, team1=[opp, bench])

        messages = [_usedmove("Magikarp", "Struggle", side_hint=1)]
        known = _extract_known_actions(messages, state)
        act = known[1][0]
        assert act is not None, "observed 'used Struggle!' must produce a known action, not None"
        assert act.kind == ActionKind.MOVE
        assert act.move_slot == -2
        assert act.move_override == Move.STRUGGLE

    def test_compute_action_probabilities_scores_struggle_positive(self):
        player = make_mon(Species.LILLIPUP, moves=(Move.TACKLE,))
        opp = make_mon(Species.MAGIKARP, moves=(Move.BOUNCE,))._replace(move_pp=(0, 0, 0, 0))
        bench = make_mon(Species.MAGIKARP, moves=(Move.SPLASH,))
        state = make_battle(player, opp, team1=[opp, bench])

        probs = compute_action_probabilities(state, ai_idx=1)
        struggle = [(a, p) for a, p in probs
                    if a.kind == ActionKind.MOVE and a.move_override == Move.STRUGGLE]
        assert struggle, f"Struggle absent from action probabilities: {probs}"
        assert struggle[0][1] > 0.0

    def test_sweep_chain_offers_struggle_for_opponent(self):
        """extract → _sweep_resolve_candidate_actions: the opp candidate list contains Struggle."""
        player = make_mon(Species.LILLIPUP, moves=(Move.TACKLE,))
        opp = make_mon(Species.MAGIKARP, moves=(Move.BOUNCE,))._replace(move_pp=(0, 0, 0, 0))
        bench = make_mon(Species.MAGIKARP, moves=(Move.SPLASH,))
        state = make_battle(player, opp, team1=[opp, bench])

        messages = [_usedmove("Lillipup", "Tackle", side_hint=0),
                    _usedmove("Magikarp", "Struggle", side_hint=1)]
        known = _extract_known_actions(messages, state)
        _c0, c1 = _sweep_resolve_candidate_actions(state, messages, known)
        assert any(a.kind == ActionKind.MOVE and a.move_override == Move.STRUGGLE for a in c1), \
            f"opp candidate actions never offered Struggle: {c1}"

    def test_full_sweep_struggle_candidate_survives(self):
        """End-to-end Issue 28: opp's only move is out of PP, it Struggles (recoil), and the
        sweep must yield a surviving candidate instead of 'No candidates survived sweep'."""
        player = make_mon(Species.LILLIPUP, moves=(Move.SPLASH,))
        opp = make_mon(Species.MAGIKARP, moves=(Move.BOUNCE,))._replace(move_pp=(0, 0, 0, 0))
        bench = make_mon(Species.MAGIKARP, moves=(Move.SPLASH,))
        state = make_battle(player, opp, team1=[opp, bench])

        # Observe the real outcome using _NO_CRIT_CONFIG so the hit doesn't crit
        # (the sweep enumerates non-crit damage rolls; a crit would be unreproducible).
        final, _ = run_with_capture(state, slot(0), STRUGGLE_ACTION, _NO_CRIT_CONFIG)
        assert final is not None, "setup run failed — cannot determine expected deltas"

        opp_hp_after = active(final, 1).hp
        player_hp_after = active(final, 0).hp
        opp_max = opp.max_hp

        def k(hp):
            return hp * 48 // opp_max

        # Magikarp (faster) Struggles first, then Lillipup Splashes.
        messages = [_usedmove("Magikarp", "Struggle", side_hint=1),
                    _usedmove("Lillipup", "Splash", side_hint=0)]
        hp_deltas = [
            odelta(opp.species, (k(opp.max_hp), k(opp_hp_after)), max_hp=opp_max),
            pdelta(player.species, (player.max_hp, player_hp_after), max_hp=player.max_hp),
        ]
        candidates = run_candidate_sweep(
            messages=messages,
            hp_deltas=hp_deltas,
            initial_candidates=[Candidate(state=state)],
        )
        assert len(candidates) >= 1
