# Tests for inject_non_move_rng and build_sweep_injected_overrides in sweep_secondaries.py.
# All tests use NEW-native constructs: no OLD imports, no Simulator.
from __future__ import annotations

import pytest

from liveplay.battle_types import ActionGroup, MatchResult
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status
from liveplay.rng import RNGEvent
from liveplay.sweep_secondaries import (
    inject_non_move_rng,
    build_sweep_injected_overrides,
)
from tests.state_builders import make_battle, make_mon, make_doubles_battle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AUTO_SIDE_HINT = object()


def _foe_prefix_hint(var_values):
    if not var_values:
        return None
    first = str(var_values[0])
    first_word = first.split()[0].lower() if first.strip() else ""
    return 1 if first_word == "foe" else 0


def _mr(string_id, *, var_values=None, side_hint=_AUTO_SIDE_HINT, metronome_called=None):
    vals = var_values or []
    if side_hint is _AUTO_SIDE_HINT:
        side_hint = _foe_prefix_hint(vals)
    mr = MatchResult(
        string_id=string_id,
        id_value=0,
        constant_name="",
        var_values=vals,
        score=0,
        matched_text="",
        slot_labels=[],
        side_hint=side_hint,
    )
    if metronome_called is not None:
        mr = MatchResult(
            string_id=mr.string_id,
            id_value=mr.id_value,
            constant_name=mr.constant_name,
            var_values=mr.var_values,
            score=mr.score,
            matched_text=mr.matched_text,
            slot_labels=mr.slot_labels,
            side_hint=mr.side_hint,
            metronome_called=metronome_called,
        )
    return mr


def _usedmove(name, move_name, *, side_hint=_AUTO_SIDE_HINT):
    return _mr("STRINGID_USEDMOVE", var_values=[name, move_name], side_hint=side_hint)


def _simple_state():
    muk = make_mon(Species.MUK, moves=(Move.SLUDGE_BOMB,))
    corsola = make_mon(Species.CORSOLA, moves=(Move.SPLASH,))
    return make_battle(muk, corsola)


def _run_inject(messages, state=None, *, slot_map=None, hp_changed_by_slot=None):
    """Call inject_non_move_rng; return (ovr0, ovr1, pre_inject, self_hit_slots)."""
    if state is None:
        state = _simple_state()
    ovr0: dict = {}
    ovr1: dict = {}
    pre: dict = {}
    hits = inject_non_move_rng(
        ovr0, ovr1, pre, messages, state,
        slot_map=slot_map,
        hp_changed_by_slot=hp_changed_by_slot,
    )
    return ovr0, ovr1, pre, hits


# ---------------------------------------------------------------------------
# ACCURACY
# ---------------------------------------------------------------------------

class TestAccuracy:
    def _state(self):
        player = make_mon(Species.ROOKIDEE, moves=(Move.PECK,), level=7)
        foe = make_mon(Species.ROOKIDEE, moves=(Move.SWAGGER,), level=6)
        return make_battle(player, foe)

    def test_miss_message_injects_false_on_correct_side(self):
        state = self._state()
        msgs = [_mr("STRINGID_ATTACKMISSED", var_values=["Rookidee"], side_hint=1)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        # side_hint=1 → opponent missed, not player
        assert ovr1.get(RNGEvent.ACCURACY) is False
        assert RNGEvent.ACCURACY not in ovr0

    def test_player_miss_credited_to_player_side(self):
        state = self._state()
        msgs = [_mr("STRINGID_ATTACKMISSED", var_values=["Rookidee"], side_hint=0)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        assert ovr0.get(RNGEvent.ACCURACY) is False
        assert RNGEvent.ACCURACY not in ovr1

    def test_no_miss_message_nothing_injected(self):
        state = self._state()
        ovr0, ovr1, _, _ = _run_inject([], state)
        assert RNGEvent.ACCURACY not in ovr0
        assert RNGEvent.ACCURACY not in ovr1


# ---------------------------------------------------------------------------
# FULL_PARALYSIS
# ---------------------------------------------------------------------------

class TestFullParalysis:
    def _state(self):
        player = make_mon(Species.PIKACHU, moves=(Move.TACKLE,), status=Status.PARALYSIS)
        foe = make_mon(Species.RATTATA, moves=(Move.QUICK_ATTACK,))
        return make_battle(player, foe)

    def test_paralysis_message_injects_false(self):
        # PKMNISPARALYZED = the mon was fully paralyzed (blocked from acting)
        state = self._state()
        msgs = [_mr("STRINGID_PKMNISPARALYZED", var_values=["Pikachu"], side_hint=0)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        assert ovr0.get(RNGEvent.FULL_PARALYSIS) is False
        assert RNGEvent.FULL_PARALYSIS not in ovr1

    def test_no_paralysis_message_nothing_injected(self):
        state = self._state()
        ovr0, ovr1, _, _ = _run_inject([], state)
        assert RNGEvent.FULL_PARALYSIS not in ovr0
        assert RNGEvent.FULL_PARALYSIS not in ovr1


# ---------------------------------------------------------------------------
# WAKE / DEFROST
# ---------------------------------------------------------------------------

class TestWake:
    def _state(self):
        player = make_mon(Species.SNORLAX, moves=(Move.SPLASH,), status=Status.SLEEP)
        foe = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
        return make_battle(player, foe)

    def test_woke_up_injects_wake_true(self):
        state = self._state()
        msgs = [_mr("STRINGID_PKMNWOKEUP", var_values=["Snorlax"], side_hint=0)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        assert ovr0.get(RNGEvent.WAKE) is True
        assert RNGEvent.WAKE not in ovr1

    def test_fast_asleep_injects_wake_false(self):
        state = self._state()
        msgs = [_mr("STRINGID_PKMNFASTASLEEP", var_values=["Snorlax"], side_hint=0)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        assert ovr0.get(RNGEvent.WAKE) is False

    def test_no_sleep_message_nothing_injected(self):
        state = self._state()
        ovr0, ovr1, _, _ = _run_inject([], state)
        assert RNGEvent.WAKE not in ovr0


class TestDefrost:
    def _state(self):
        player = make_mon(Species.LAPRAS, moves=(Move.SURF,), status=Status.FREEZE)
        foe = make_mon(Species.CHARMANDER, moves=(Move.EMBER,))
        return make_battle(player, foe)

    def test_defrosted_injects_defrost_true(self):
        state = self._state()
        msgs = [_mr("STRINGID_PKMNWASDEFROSTED", var_values=["Lapras"], side_hint=0)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        assert ovr0.get(RNGEvent.DEFROST) is True

    def test_defrosted2_injects_defrost_true(self):
        state = self._state()
        msgs = [_mr("STRINGID_PKMNWASDEFROSTED2", var_values=["Lapras"], side_hint=0)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        assert ovr0.get(RNGEvent.DEFROST) is True

    def test_still_frozen_injects_defrost_false(self):
        state = self._state()
        msgs = [_mr("STRINGID_PKMNISFROZEN", var_values=["Lapras"], side_hint=0)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        assert ovr0.get(RNGEvent.DEFROST) is False

    def test_no_freeze_message_nothing_injected(self):
        state = self._state()
        ovr0, ovr1, _, _ = _run_inject([], state)
        assert RNGEvent.DEFROST not in ovr0


# ---------------------------------------------------------------------------
# CONFUSION_SNAP / CONFUSION_SELF_HIT
# ---------------------------------------------------------------------------

class TestConfusionSnap:
    def _state(self):
        player = make_mon(Species.EEVEE, moves=(Move.TACKLE,))
        foe = make_mon(Species.JIGGLYPUFF, moves=(Move.SING,))
        return make_battle(player, foe)

    def test_snapped_out_injects_confusion_snap_true(self):
        state = self._state()
        msgs = [_mr("STRINGID_PKMNHEALEDCONFUSION", var_values=["Eevee"], side_hint=0)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        assert ovr0.get(RNGEvent.CONFUSION_SNAP) is True
        assert RNGEvent.CONFUSION_SNAP not in ovr1

    def test_no_snap_message_nothing_injected(self):
        state = self._state()
        ovr0, ovr1, _, _ = _run_inject([], state)
        assert RNGEvent.CONFUSION_SNAP not in ovr0


class TestConfusionSelfHit:
    def _state(self):
        player = make_mon(Species.MACHOP, moves=(Move.KARATE_CHOP,))
        foe = make_mon(Species.DROWZEE, moves=(Move.PSYBEAM,))
        return make_battle(player, foe)

    def _self_hit_messages(self, name, side_hint):
        """PKMNISCONFUSED ("is confused!") precedes ITHURTCONFUSION."""
        return [
            _mr("STRINGID_PKMNISCONFUSED", var_values=[name], side_hint=side_hint),
            _mr("STRINGID_ITHURTCONFUSION", var_values=[], side_hint=None),
        ]

    def test_self_hit_injects_self_hit_false_and_returns_slot(self):
        state = self._state()
        msgs = self._self_hit_messages("Machop", side_hint=0)
        ovr0, ovr1, _, hits = _run_inject(msgs, state)
        assert ovr0.get(RNGEvent.CONFUSION_SELF_HIT) is False
        assert (0, 0) in hits

    def test_self_hit_foe_correct_side(self):
        state = self._state()
        msgs = self._self_hit_messages("Foe Drowzee", side_hint=1)
        ovr0, ovr1, _, hits = _run_inject(msgs, state)
        assert ovr1.get(RNGEvent.CONFUSION_SELF_HIT) is False
        assert (1, 0) in hits
        assert RNGEvent.CONFUSION_SELF_HIT not in ovr0

    def test_no_self_hit_nothing_injected(self):
        state = self._state()
        ovr0, ovr1, _, hits = _run_inject([], state)
        assert RNGEvent.CONFUSION_SELF_HIT not in ovr0
        assert len(hits) == 0


# ---------------------------------------------------------------------------
# ATTRACT_IMMOBILIZE
# ---------------------------------------------------------------------------

class TestAttractImmobilize:
    def _state(self):
        player = make_mon(Species.CLEFAIRY, moves=(Move.SING,))
        foe = make_mon(Species.JIGGLYPUFF, moves=(Move.ATTRACT,))
        return make_battle(player, foe)

    def test_immobilized_by_love_injects_false(self):
        state = self._state()
        msgs = [_mr("STRINGID_PKMNIMMOBILIZEDBYLOVE", var_values=["Clefairy"], side_hint=0)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        assert ovr0.get(RNGEvent.ATTRACT_IMMOBILIZE) is False
        assert RNGEvent.ATTRACT_IMMOBILIZE not in ovr1

    def test_no_attract_message_nothing_injected(self):
        state = self._state()
        ovr0, ovr1, _, _ = _run_inject([], state)
        assert RNGEvent.ATTRACT_IMMOBILIZE not in ovr0


# ---------------------------------------------------------------------------
# QUICK_CLAW
# ---------------------------------------------------------------------------

class TestQuickClaw:
    def _qc_state(self):
        player = make_mon(Species.RATTATA, moves=(Move.TACKLE,), item=Item.QUICK_CLAW)
        foe = make_mon(Species.PIDGEY, moves=(Move.GUST,))
        return make_battle(player, foe)

    def test_activation_message_injects_true(self):
        state = self._qc_state()
        msgs = [
            _mr("STRINGID_QUICKCLAWACTIVATE", var_values=["Rattata"], side_hint=0),
            _usedmove("Rattata", "Tackle", side_hint=0),
        ]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        qc = ovr0.get(RNGEvent.QUICK_CLAW)
        assert isinstance(qc, dict)
        assert qc.get(0) is True

    def test_silent_holder_priority0_injects_false(self):
        # Rattata holds Quick Claw and used a priority-0 move, but no QC message appeared.
        state = self._qc_state()
        msgs = [_usedmove("Rattata", "Tackle", side_hint=0)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        qc = ovr0.get(RNGEvent.QUICK_CLAW)
        assert isinstance(qc, dict)
        assert qc.get(0) is False

    def test_no_quick_claw_holder_nothing_injected(self):
        # Rattata does NOT hold Quick Claw — no injection even if it moved.
        player = make_mon(Species.RATTATA, moves=(Move.TACKLE,))  # no item
        foe = make_mon(Species.PIDGEY, moves=(Move.GUST,))
        state = make_battle(player, foe)
        msgs = [_usedmove("Rattata", "Tackle", side_hint=0)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        assert RNGEvent.QUICK_CLAW not in ovr0

    def test_priority_move_holder_not_injected_false(self):
        # Quick Claw holder used a +1 priority move; silent QC absence is NOT injected
        # (QC only competes for priority 0; +1 priority moves don't use QC).
        player = make_mon(Species.RATTATA, moves=(Move.QUICK_ATTACK,), item=Item.QUICK_CLAW)
        foe = make_mon(Species.PIDGEY, moves=(Move.GUST,))
        state = make_battle(player, foe)
        msgs = [_usedmove("Rattata", "Quick Attack", side_hint=0)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        qc = ovr0.get(RNGEvent.QUICK_CLAW)
        # No False injection expected for priority > 0 move
        assert qc is None or (isinstance(qc, dict) and 0 not in qc)


# ---------------------------------------------------------------------------
# MULTI_HIT_COUNT
# ---------------------------------------------------------------------------

class TestMultiHitCount:
    _MIDPOINTS = {2: 0.175, 3: 0.525, 4: 0.775, 5: 0.925}

    def _state(self):
        player = make_mon(Species.CLOYSTER, moves=(Move.SPIKE_CANNON,))
        foe = make_mon(Species.TENTACOOL, moves=(Move.BUBBLE,))
        return make_battle(player, foe)

    def test_hitxtimes_2_hits_injects_midpoint(self):
        state = self._state()
        msgs = [
            _usedmove("Cloyster", "Spike Cannon", side_hint=0),
            _mr("STRINGID_HITXTIMES", var_values=["2"]),
        ]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        mh = ovr0.get(RNGEvent.MULTI_HIT_COUNT)
        assert isinstance(mh, dict)
        assert abs(mh[0] - self._MIDPOINTS[2]) < 1e-9

    def test_hitxtimes_5_hits_injects_midpoint(self):
        state = self._state()
        msgs = [
            _usedmove("Cloyster", "Spike Cannon", side_hint=0),
            _mr("STRINGID_HITXTIMES", var_values=["5"]),
        ]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        mh = ovr0.get(RNGEvent.MULTI_HIT_COUNT)
        assert isinstance(mh, dict)
        assert abs(mh[0] - self._MIDPOINTS[5]) < 1e-9

    @pytest.mark.parametrize("n", [2, 3, 4, 5])
    def test_all_hit_counts_map_to_correct_midpoints(self, n):
        state = self._state()
        msgs = [
            _usedmove("Cloyster", "Spike Cannon", side_hint=0),
            _mr("STRINGID_HITXTIMES", var_values=[str(n)]),
        ]
        ovr0, _, _, _ = _run_inject(msgs, state)
        mh = ovr0.get(RNGEvent.MULTI_HIT_COUNT)
        assert isinstance(mh, dict)
        assert abs(mh[0] - self._MIDPOINTS[n]) < 1e-9

    def test_no_hitxtimes_nothing_injected(self):
        state = self._state()
        ovr0, ovr1, _, _ = _run_inject([], state)
        assert RNGEvent.MULTI_HIT_COUNT not in ovr0


# ---------------------------------------------------------------------------
# FLINCH (per attacker slot)
# ---------------------------------------------------------------------------

class TestFlinch:
    def _state(self):
        player = make_mon(Species.RATTATA, moves=(Move.BITE,))
        foe = make_mon(Species.JIGGLYPUFF, moves=(Move.SING,))
        return make_battle(player, foe)

    def test_flinch_message_injects_true_on_attacker_slot(self):
        state = self._state()
        # var_values carry the bare species name (no "Foe " prefix); side is encoded in side_hint
        msgs = [
            _usedmove("Rattata", "Bite", side_hint=0),
            _mr("STRINGID_PKMNFLINCHED", var_values=["Jigglypuff"], side_hint=1),
        ]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        fl = ovr0.get(RNGEvent.FLINCH)
        assert isinstance(fl, dict)
        assert fl.get(0) is True
        assert RNGEvent.FLINCH not in ovr1

    def test_flinch_side_mismatch_raises(self):
        """Flinched mon on side 1, but preceding mover is also on side 1 — should raise."""
        state = self._state()
        # USEDMOVE is side 1, PKMNFLINCHED also side 1 — attacker_side=0 but seg_side=1.
        msgs = [
            _usedmove("Jigglypuff", "Sing", side_hint=1),
            _mr("STRINGID_PKMNFLINCHED", var_values=["Jigglypuff"], side_hint=1),
        ]
        with pytest.raises(Exception):
            _run_inject(msgs, state)

    def test_no_flinch_message_nothing_injected(self):
        state = self._state()
        ovr0, ovr1, _, _ = _run_inject([], state)
        assert RNGEvent.FLINCH not in ovr0


# ---------------------------------------------------------------------------
# Pre-inject: Metronome / Sleep Talk sub-move
# ---------------------------------------------------------------------------

class TestPreInjectMetronome:
    def _state(self):
        player = make_mon(Species.CLEFAIRY, moves=(Move.METRONOME,))
        foe = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
        return make_battle(player, foe)

    def _tagged_usedmove(self, wrapper_name, called_move):
        """Build a USEDMOVE tagged with metronome_called (as from _collapse_metronome_calls)."""
        return _mr(
            "STRINGID_USEDMOVE",
            var_values=[wrapper_name, "Metronome"],
            side_hint=0,
            metronome_called=called_move,
        )

    def test_metronome_tagged_message_injects_sub_move(self):
        state = self._state()
        msgs = [self._tagged_usedmove("Clefairy", Move.WATER_GUN)]
        ovr0, ovr1, pre, _ = _run_inject(msgs, state)
        assert pre.get(RNGEvent.METRONOME_MOVE) == Move.WATER_GUN

    def test_plain_usedmove_does_not_inject_sub_move(self):
        state = self._state()
        msgs = [_usedmove("Clefairy", "Tackle", side_hint=0)]
        ovr0, ovr1, pre, _ = _run_inject(msgs, state)
        assert RNGEvent.METRONOME_MOVE not in pre

    def test_sleep_talk_tagged_injects_sleep_talk_move(self):
        player = make_mon(Species.SNORLAX, moves=(Move.SLEEP_TALK,), status=Status.SLEEP)
        foe = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
        state = make_battle(player, foe)
        msg = _mr(
            "STRINGID_USEDMOVE",
            var_values=["Snorlax", "Sleep Talk"],
            side_hint=0,
            metronome_called=Move.BODY_SLAM,
        )
        ovr0, ovr1, pre, _ = _run_inject([msg], state)
        assert pre.get(RNGEvent.SLEEP_TALK_MOVE) == Move.BODY_SLAM
        assert RNGEvent.METRONOME_MOVE not in pre


# ---------------------------------------------------------------------------
# Pre-inject: EFFECT_SPORE_WHICH
# ---------------------------------------------------------------------------

class TestPreInjectEffectSpore:
    def _state(self):
        player = make_mon(Species.HERACROSS, moves=(Move.MEGAHORN,))
        foe = make_mon(Species.BRELOOM, moves=(Move.MACH_PUNCH,), ability=Ability.EFFECT_SPORE)
        return make_battle(player, foe)

    def test_pkmnwasparalyzedby_with_effect_spore_injects_status(self):
        state = self._state()
        msgs = [
            _usedmove("Heracross", "Megahorn", side_hint=0),
            _mr(
                "STRINGID_PKMNWASPARALYZEDBY",
                var_values=["Breloom", "Effect Spore", "Heracross"],
                side_hint=0,
            ),
        ]
        ovr0, ovr1, pre, _ = _run_inject(msgs, state)
        assert pre.get(RNGEvent.EFFECT_SPORE_WHICH) == Status.PARALYSIS

    def test_pkmnpoisonedby_with_effect_spore_injects_status(self):
        state = self._state()
        msgs = [
            _usedmove("Heracross", "Megahorn", side_hint=0),
            _mr(
                "STRINGID_PKMNPOISONEDBY",
                var_values=["Breloom", "Effect Spore", "Heracross"],
                side_hint=0,
            ),
        ]
        ovr0, ovr1, pre, _ = _run_inject(msgs, state)
        assert pre.get(RNGEvent.EFFECT_SPORE_WHICH) == Status.POISON

    def test_pkmnmadesleep_with_effect_spore_injects_status(self):
        state = self._state()
        msgs = [
            _usedmove("Heracross", "Megahorn", side_hint=0),
            _mr(
                "STRINGID_PKMNMADESLEEP",
                var_values=["Breloom", "Effect Spore", "Heracross"],
                side_hint=0,
            ),
        ]
        ovr0, ovr1, pre, _ = _run_inject(msgs, state)
        assert pre.get(RNGEvent.EFFECT_SPORE_WHICH) == Status.SLEEP

    def test_paralyzedby_without_effect_spore_does_not_inject_effect_spore(self):
        # Static paralysis — no Effect Spore in var_values
        state = self._state()
        msgs = [
            _usedmove("Heracross", "Megahorn", side_hint=0),
            _mr(
                "STRINGID_PKMNWASPARALYZEDBY",
                var_values=["Breloom", "Static", "Heracross"],
                side_hint=0,
            ),
        ]
        ovr0, ovr1, pre, _ = _run_inject(msgs, state)
        assert RNGEvent.EFFECT_SPORE_WHICH not in pre


# ---------------------------------------------------------------------------
# Pre-inject: ACUPRESSURE_STAT
# ---------------------------------------------------------------------------

class TestPreInjectAcupressure:
    def _state(self):
        player = make_mon(Species.SHUCKLE, moves=(Move.ACUPRESSURE,))
        foe = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
        return make_battle(player, foe)

    def test_acupressure_stat_rose_injects_stat_index(self):
        state = self._state()
        msgs = [
            _usedmove("Shuckle", "Acupressure", side_hint=0),
            _mr(
                "STRINGID_ATTACKERSSTATROSE",
                var_values=["Shuckle", "Speed", "sharply rose"],
                side_hint=0,
            ),
        ]
        ovr0, ovr1, pre, _ = _run_inject(msgs, state)
        # Speed is index 4 in _ACUPRESSURE_STAT_MAP
        assert pre.get(RNGEvent.ACUPRESSURE_STAT) == 4

    def test_acupressure_attack_stat(self):
        state = self._state()
        msgs = [
            _usedmove("Shuckle", "Acupressure", side_hint=0),
            _mr(
                "STRINGID_ATTACKERSSTATROSE",
                var_values=["Shuckle", "Attack", "rose"],
                side_hint=0,
            ),
        ]
        ovr0, ovr1, pre, _ = _run_inject(msgs, state)
        assert pre.get(RNGEvent.ACUPRESSURE_STAT) == 0

    def test_non_acupressure_stat_message_not_injected(self):
        # Stat rose from a different move — no ACUPRESSURE_STAT
        state = self._state()
        msgs = [
            _usedmove("Shuckle", "Splash", side_hint=0),
            _mr(
                "STRINGID_ATTACKERSSTATROSE",
                var_values=["Shuckle", "Speed", "rose"],
                side_hint=0,
            ),
        ]
        ovr0, ovr1, pre, _ = _run_inject(msgs, state)
        assert RNGEvent.ACUPRESSURE_STAT not in pre


# ---------------------------------------------------------------------------
# Pre-inject: ROAR_TARGET
# ---------------------------------------------------------------------------

class TestPreInjectRoarTarget:
    def _state(self):
        player = make_mon(Species.ARCANINE, moves=(Move.ROAR,))
        foe_lead = make_mon(Species.RATTATA, moves=(Move.TACKLE,))
        foe_bench = make_mon(Species.PIDGEY, moves=(Move.GUST,))
        return make_battle(player, foe_lead, team1=[foe_lead, foe_bench])

    def test_roar_drags_out_target_pre_injected(self):
        state = self._state()
        msgs = [
            _mr("STRINGID_PKMNWASDRAGGEDOUT", var_values=["Pidgey"], side_hint=1),
        ]
        ovr0, ovr1, pre, _ = _run_inject(msgs, state)
        # Pidgey is team slot 1 on side 1
        assert pre.get(RNGEvent.ROAR_TARGET) == 1


# ---------------------------------------------------------------------------
# PROC_FIRES (contact ability / Harvest)
# ---------------------------------------------------------------------------

class TestProcFires:
    def _state(self):
        player = make_mon(Species.FLETCHLING, moves=(Move.TACKLE,), ability=Ability.KEEN_EYE)
        foe = make_mon(Species.CROAGUNK, moves=(Move.ROCK_SMASH,), ability=Ability.POISON_TOUCH)
        return make_battle(player, foe)

    def test_proc_fires_injected_on_attacker(self):
        # PKMNWASPARALYZEDBY: contact ability fires on most-recent move attacker
        state = self._state()
        # var_values carry bare species names; Croagunk is side 1, side_hint=1 for the attacker
        msgs = [
            _usedmove("Croagunk", "Rock Smash", side_hint=1),
            _mr(
                "STRINGID_PKMNWASPARALYZEDBY",
                var_values=["Croagunk", "Static", "Fletchling"],
                side_hint=0,
            ),
        ]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        assert ovr1.get(RNGEvent.PROC_FIRES) == {0: True}
        assert RNGEvent.PROC_FIRES not in ovr0

    def test_harvest_forces_proc_on_harvester(self):
        player = make_mon(Species.SKITTY, moves=(Move.TACKLE,))
        foe = make_mon(Species.EXEGGCUTE, moves=(Move.CONFUSION,), ability=Ability.HARVEST)
        state = make_battle(player, foe)
        msgs = [_mr("STRINGID_HARVESTADDITEM", var_values=["Exeggcute", "Oran Berry"], side_hint=1)]
        ovr0, ovr1, _, _ = _run_inject(msgs, state)
        assert ovr1.get(RNGEvent.PROC_FIRES) == {0: True}
        assert RNGEvent.PROC_FIRES not in ovr0


# ---------------------------------------------------------------------------
# build_sweep_injected_overrides — combo builder
# ---------------------------------------------------------------------------

class TestBuildSweepInjectedOverrides:
    def _state(self):
        player = make_mon(Species.MACHOP, moves=(Move.KARATE_CHOP,))
        foe = make_mon(Species.EEVEE, moves=(Move.TACKLE,))
        return make_battle(player, foe)

    def test_no_flinch_capable_movers_one_combo(self):
        """No flinch-capable movers → exactly 1 combo (empty dict)."""
        state = self._state()
        # Karate Chop has no flinch secondary; Tackle has no secondary
        used_moves = {(0, 0): Move.KARATE_CHOP, (1, 0): Move.TACKLE}
        ovr0, ovr1, pre, combos, hits = build_sweep_injected_overrides(
            [], state, used_moves, None
        )
        assert len(combos) == 1
        assert combos[0] == {}

    def test_one_flinch_capable_mover_two_combos(self):
        """One flinch-capable mover → 2 combos (True/False for that slot)."""
        player = make_mon(Species.RATTATA, moves=(Move.BITE,))
        foe = make_mon(Species.EEVEE, moves=(Move.TACKLE,))
        state = make_battle(player, foe)
        # Bite has flinch secondary → non-attributable
        used_moves = {(0, 0): Move.BITE, (1, 0): Move.TACKLE}
        ovr0, ovr1, pre, combos, hits = build_sweep_injected_overrides(
            [], state, used_moves, None
        )
        assert len(combos) == 2
        keys = [(0, 0, RNGEvent.FLINCH)]
        vals = {combo[keys[0]] for combo in combos}
        assert True in vals
        assert False in vals

    def test_two_flinch_capable_movers_four_combos(self):
        """Two flinch-capable movers → 4 combos (cross-product)."""
        player = make_mon(Species.RATTATA, moves=(Move.BITE,))
        foe = make_mon(Species.JIGGLYPUFF, moves=(Move.HEADBUTT,))
        state = make_battle(player, foe)
        used_moves = {(0, 0): Move.BITE, (1, 0): Move.HEADBUTT}
        ovr0, ovr1, pre, combos, hits = build_sweep_injected_overrides(
            [], state, used_moves, None
        )
        assert len(combos) == 4

    def test_observed_flinch_pins_mover_one_combo(self):
        """If flinch was observed for a mover, it's pinned True and not in combo."""
        player = make_mon(Species.RATTATA, moves=(Move.BITE,))
        foe = make_mon(Species.EEVEE, moves=(Move.TACKLE,))
        state = make_battle(player, foe)
        # var_values carry bare species name; side_hint encodes which side the flinched mon is on
        msgs = [
            _usedmove("Rattata", "Bite", side_hint=0),
            _mr("STRINGID_PKMNFLINCHED", var_values=["Eevee"], side_hint=1),
        ]
        used_moves = {(0, 0): Move.BITE, (1, 0): Move.TACKLE}
        ovr0, ovr1, pre, combos, hits = build_sweep_injected_overrides(
            msgs, state, used_moves, None
        )
        # Observed flinch pins the mover → only 1 combo
        assert len(combos) == 1
        # The injected override has FLINCH=True for side 0 slot 0
        flinch_ovr = ovr0.get(RNGEvent.FLINCH)
        assert isinstance(flinch_ovr, dict)
        assert flinch_ovr.get(0) is True

    def test_returns_self_hit_slots_frozenset(self):
        player = make_mon(Species.MACHOP, moves=(Move.KARATE_CHOP,))
        foe = make_mon(Species.EEVEE, moves=(Move.TACKLE,))
        state = make_battle(player, foe)
        msgs = [
            _mr("STRINGID_PKMNISCONFUSED", var_values=["Machop"], side_hint=0),
            _mr("STRINGID_ITHURTCONFUSION", var_values=[], side_hint=None),
        ]
        used_moves = {(0, 0): Move.KARATE_CHOP}
        ovr0, ovr1, pre, combos, hits = build_sweep_injected_overrides(
            msgs, state, used_moves, None
        )
        assert isinstance(hits, frozenset)
        assert (0, 0) in hits

    def test_action_groups_path_injects_attributable_secondaries(self):
        """Action-groups path: attributable secondaries inject correctly per group."""
        player = make_mon(Species.GENGAR, moves=(Move.SLUDGE_BOMB,))
        foe = make_mon(Species.EEVEE, moves=(Move.TACKLE,))
        state = make_battle(player, foe)
        # Build an ActionGroup for Gengar using Sludge Bomb with no poison message
        usedmove_msg = _mr("STRINGID_USEDMOVE", var_values=["Gengar", "Sludge Bomb"], side_hint=0)
        group = ActionGroup(primary=usedmove_msg, secondaries=[], hp_readings=[])
        used_moves = {(0, 0): Move.SLUDGE_BOMB, (1, 0): Move.TACKLE}
        ovr0, ovr1, pre, combos, hits = build_sweep_injected_overrides(
            [], state, used_moves, [group]
        )
        # Sludge Bomb poison secondary should be False (USEDMOVE present, no status msg)
        assert ovr0.get(RNGEvent.SECONDARY_FIRES, {}).get(0) is False
