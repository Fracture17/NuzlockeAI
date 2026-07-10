# Log-event reconciliation layer: pure consistency checks between a CapturingLogger,
# observed emulator MatchResult messages, and a BattleState. No engine/driver dependencies.
from __future__ import annotations

import dataclasses
from typing import Optional

from rapidfuzz.distance import Levenshtein as _Lev

from liveplay.logger import CapturingLogger, LogEvent
from liveplay.battle_types import MatchResult, ActionGroup
from liveplay.state.battle import BattleState
from liveplay.state.pokemon import Volatile, VolatileEffect, Stat, compute_stat, PokemonState
from liveplay.data.species import Species, SPECIES_DATA
from liveplay.data.status import Status
from liveplay.data.growth_rate import exp_for_level
from liveplay.data.name_aliases import emulator_species_name
from liveplay.hp_stability import hp_range
from liveplay.engine_select import SimulationError
from liveplay.state_transition import _species_match_threshold
# Shared pure predicates/constants (re-exported for callers that import them from here).
from liveplay.sweep_common import _SPREAD_TARGETS, _msg_is_foe, _move_is_spread

# ---------------------------------------------------------------------------
# Module-level constant tables (ported verbatim from old simulation_runner.py)
# ---------------------------------------------------------------------------

_USEDMOVE_ID = "STRINGID_USEDMOVE"

_FAINT_MSG_IDS = frozenset({"STRINGID_ATTACKERFAINTED", "STRINGID_TARGETFAINTED"})

_STATUS_APPLY_IDS: dict[str, Status] = {
    "STRINGID_PKMNFELLASLEEP": Status.SLEEP,
    "STRINGID_PKMNMADESLEEP": Status.SLEEP,
    "STRINGID_PKMNWASPOISONED": Status.POISON,
    "STRINGID_PKMNBADLYPOISONED": Status.TOXIC,
    "STRINGID_PKMNWASBURNED": Status.BURN,
    "STRINGID_PKMNWASFROZEN": Status.FREEZE,
    "STRINGID_PKMNWASPARALYZED": Status.PARALYSIS,
    "STRINGID_PKMNWASPARALYZEDBY": Status.PARALYSIS,
}

_STAT_CHANGE_IDS: frozenset[str] = frozenset({
    "STRINGID_STATROSE", "STRINGID_STATSHARPLY",
    "STRINGID_STATFELL", "STRINGID_STATHARSHLY",
    "STRINGID_ATTACKERSSTATROSE", "STRINGID_DEFENDERSSTATROSE",
    "STRINGID_ATTACKERSSTATFELL", "STRINGID_DEFENDERSSTATFELL",
    "STRINGID_ATTACKERSTATROSTEDRASTICALLY", "STRINGID_DEFENDERSTATROSTEDRASTICALLY",
    "STRINGID_ATTACKERSTATFELLSEVERELY", "STRINGID_DEFENDERSTATFELLSEVERELY",
    "STRINGID_STATROSEFROMITEM", "STRINGID_STATSHARPLYROSEFROMITEM",
    "STRINGID_STATFELLFROMITEM", "STRINGID_STATHARSHLYFELLFROMIITEM",
    "STRINGID_USINGITEMSTATOFPKMNROSE",
})

_STAT_ROSE_WITH_NAME_IDS: frozenset[str] = frozenset({
    "STRINGID_ATTACKERSSTATROSE", "STRINGID_DEFENDERSSTATROSE",
    "STRINGID_ATTACKERSTATROSTEDRASTICALLY", "STRINGID_DEFENDERSTATROSTEDRASTICALLY",
    "STRINGID_STATROSEFROMITEM", "STRINGID_STATSHARPLYROSEFROMITEM",
})
_STAT_FELL_WITH_NAME_IDS: frozenset[str] = frozenset({
    "STRINGID_ATTACKERSSTATFELL", "STRINGID_DEFENDERSSTATFELL",
    "STRINGID_ATTACKERSTATFELLSEVERELY", "STRINGID_DEFENDERSTATFELLSEVERELY",
    "STRINGID_STATFELLFROMITEM", "STRINGID_STATHARSHLYFELLFROMIITEM",
})
_STAT_USING_ITEM_ID = "STRINGID_USINGITEMSTATOFPKMNROSE"
_STAT_FRAGMENT_IDS: frozenset[str] = frozenset({
    "STRINGID_STATROSE", "STRINGID_STATSHARPLY",
    "STRINGID_STATFELL", "STRINGID_STATHARSHLY",
})

_STATUS_MULTIVAR_IDS: frozenset[str] = frozenset({
    "STRINGID_PKMNMADESLEEP",
    "STRINGID_PKMNWASPARALYZEDBY",
})

_CONFUSION_APPLY_ID = "STRINGID_PKMNWASCONFUSED"
_CONFUSION_ACTING_ID = "STRINGID_PKMNISCONFUSED"

_BINDING_FREED_ID = "STRINGID_PKMNFREEDFROM"
_RAMPAGE_END_ID = "STRINGID_PKMNFATIGUECONFUSION"

# HP-restore messages emitted by held berries.
_HEAL_RESTORE_STRING_IDS = frozenset({
    "STRINGID_PKMNSITEMRESTOREDHEALTH",
    "STRINGID_PKMNSITEMRESTOREDHPALITTLE",
})

_CHEEK_POUCH_LABEL = "CHEEK POUCH"

# HP-changing log events: (mon-identity kwarg, amount kwarg, sign).
_HP_CHANGE_EVENTS = {
    LogEvent.DAMAGE: ("target", "amount", -1),
    LogEvent.HEAL: ("target", "amount", +1),
    LogEvent.HIT_SELF_CONFUSION: ("pokemon", "damage", -1),
}


# ---------------------------------------------------------------------------
# Local helper: recalc stats after a level-up (no engine dependency)
# ---------------------------------------------------------------------------

def _recalc_stats(mon: PokemonState) -> PokemonState:
    """Recompute stats for mon's current level; HP increases by the max_hp delta."""
    sp = SPECIES_DATA[mon.species]
    bases = (sp.base_hp, sp.base_atk, sp.base_def, sp.base_spa, sp.base_spd, sp.base_spe)
    new_stats = tuple(
        compute_stat(Stat(i), bases[i], mon.ivs[i], mon.nature, mon.level)
        for i in range(6)
    )
    if mon.species == Species.SHEDINJA:
        new_stats = (1,) + new_stats[1:]
        new_max_hp = 1
        new_hp = min(1, mon.hp)
    else:
        new_max_hp = new_stats[0]
        new_hp = min(new_max_hp, mon.hp + (new_max_hp - mon.max_hp))
    return mon._replace(stats=new_stats, max_hp=new_max_hp, hp=new_hp)


# ---------------------------------------------------------------------------
# Skeleton / consistency helpers
# ---------------------------------------------------------------------------

def _species_name_matches(bare_name: str, species) -> bool:
    """Fuzzy-match an OCR'd name against a Species enum (same tolerance as _fuzzy_find_side)."""
    if species is None:
        return False
    species_name = emulator_species_name(species)
    return _Lev.distance(bare_name.upper(), species_name) <= _species_match_threshold(species_name)


def _apply_observed_levelups(result_state: BattleState, all_messages: list) -> None:
    """Force player mons up to their observed levels (PKMNGREWTOLV), in place.

    Observed level-ups are ground truth. Raises SimulationError on genuine ambiguity.
    """
    observed_max: dict[str, int] = {}
    for msg in all_messages:
        if msg.string_id == "STRINGID_PKMNGREWTOLV" and len(msg.var_values) >= 2:
            name = msg.var_values[0]
            level = int(msg.var_values[1])
            if level > observed_max.get(name, 0):
                observed_max[name] = level
    if not observed_max:
        return

    team = result_state.sides[0].team
    for name, target_level in observed_max.items():
        candidates = [
            i for i, mon in enumerate(team)
            if mon is not None and _species_name_matches(name, mon.species)
            and mon.level < target_level
        ]
        if not candidates:
            continue
        if len(candidates) > 1:
            raise SimulationError(
                reason=f"observed level-up {name!r}->L{target_level} matches multiple "
                       f"player mons below that level: indices {candidates}"
            )
        idx = candidates[0]
        mon = team[idx]
        growth = SPECIES_DATA[mon.species].growth_rate
        new_exp = max(mon.exp, exp_for_level(growth, target_level))
        mon = mon._replace(level=target_level, exp=new_exp)
        team[idx] = _recalc_stats(mon)


def _apply_observed_wrap_release(state: BattleState, messages: list) -> BattleState:
    """Force-expire BOUND for any mon named in an observed PKMNFREEDFROM message.

    Returns a new BattleState, or the same object unchanged when there is nothing to release.
    """
    freed_sides: set[int] = set()
    for msg in messages:
        if msg.string_id != _BINDING_FREED_ID or not msg.var_values:
            continue
        if msg.side_hint is None:
            continue
        freed_sides.add(msg.side_hint)
    if not freed_sides:
        return state

    new_sides = list(state.sides)
    changed = False
    for side_idx in freed_sides:
        side = state.sides[side_idx]
        new_team = list(side.team)
        side_changed = False
        for team_idx in side.active_indices:
            mon = side.team[team_idx]
            if mon is None:
                continue
            if not any(e == VolatileEffect.BOUND for e, _ in mon.timed_volatiles):
                continue
            kept = [(e, t) for e, t in mon.timed_volatiles
                    if e not in (VolatileEffect.BOUND, VolatileEffect.BOUND_SOURCE_SLOT,
                                 VolatileEffect.BOUND_SOURCE_ID)]
            new_team[team_idx] = mon._replace(timed_volatiles=kept)
            side_changed = True
        if side_changed:
            new_sides[side_idx] = dataclasses.replace(side, team=new_team)
            changed = True
    if not changed:
        return state
    return dataclasses.replace(state, sides=tuple(new_sides))


def _apply_observed_rampage_end(state: BattleState, messages: list) -> BattleState:
    """Force-end a rampage for any mon named in an observed PKMNFATIGUECONFUSION message.

    Returns a new BattleState, or the same object unchanged when there is nothing to end.
    """
    ended_sides: set[int] = set()
    for msg in messages:
        if msg.string_id != _RAMPAGE_END_ID or not msg.var_values:
            continue
        if msg.side_hint is None:
            continue
        ended_sides.add(msg.side_hint)
    if not ended_sides:
        return state

    new_sides = list(state.sides)
    changed = False
    for side_idx in ended_sides:
        side = state.sides[side_idx]
        new_team = list(side.team)
        side_changed = False
        for team_idx in side.active_indices:
            mon = side.team[team_idx]
            if mon is None:
                continue
            if not any(e == VolatileEffect.RAMPAGING for e, _ in mon.timed_volatiles):
                continue
            kept = [(e, t) for e, t in mon.timed_volatiles if e != VolatileEffect.RAMPAGING]
            new_vol = (mon.volatiles & ~Volatile.LOCKED_MOVE) | Volatile.CONFUSED
            new_team[team_idx] = mon._replace(
                timed_volatiles=kept, volatiles=new_vol, locked_slot=-1)
            side_changed = True
        if side_changed:
            new_sides[side_idx] = dataclasses.replace(side, team=new_team)
            changed = True
    if not changed:
        return state
    return dataclasses.replace(state, sides=tuple(new_sides))


def _observed_event_skeleton(all_messages: list[MatchResult]) -> list[tuple]:
    """Ordered tokens from observed messages: ('M', side, name) and ('F', side, name)."""
    skel: list[tuple] = []
    for msg in all_messages:
        if msg.string_id == _USEDMOVE_ID and msg.var_values:
            skel.append(("M", 1 if _msg_is_foe(msg) else 0, msg.var_values[0]))
        elif msg.string_id in _FAINT_MSG_IDS and msg.var_values:
            skel.append(("F", 1 if _msg_is_foe(msg) else 0, msg.var_values[0]))
    return skel


def _sim_event_skeleton(capturing: CapturingLogger) -> list[tuple]:
    """Ordered tokens from the sim log: ('M', None, Species) and ('F', side, Species)."""
    skel: list[tuple] = []
    for ev, kw in capturing.events:
        if ev == LogEvent.MOVE_USE:
            skel.append(("M", None, kw.get("user")))
        elif ev == LogEvent.FAINT:
            skel.append(("F", kw.get("side"), kw.get("pokemon")))
    return skel


def _faint_skeleton_consistent(observed_skel: list[tuple], sim_skel: list[tuple]) -> bool:
    """Compare observed vs sim move/faint skeletons; enforce faint identity and ordering.

    Passes unconditionally when no faint is present in either stream.
    """
    obs_has_faint = any(t[0] == "F" for t in observed_skel)
    sim_has_faint = any(t[0] == "F" for t in sim_skel)
    if not obs_has_faint and not sim_has_faint:
        return True
    if len(observed_skel) != len(sim_skel):
        return False
    for (o_kind, o_side, o_name), (s_kind, s_side, s_species) in zip(observed_skel, sim_skel):
        if o_kind != s_kind:
            return False
        if o_kind == "F":
            if o_side != s_side:
                return False
            if not _species_name_matches(o_name, s_species):
                return False
    return True


def _status_msg_target(msg: MatchResult) -> "tuple[int, str] | None":
    """Return (side_idx, bare_name) of the mon receiving the status from an observed message."""
    if not msg.var_values:
        return None
    if msg.string_id in _STATUS_MULTIVAR_IDS:
        if len(msg.var_values) < 3:
            return None
        source_is_foe = _msg_is_foe(msg)
        return (0 if source_is_foe else 1, msg.var_values[-1])
    return (1 if _msg_is_foe(msg) else 0, msg.var_values[0])


def _event_attributed_to(
    capturing: CapturingLogger,
    event: "LogEvent",
    side: int,
    name: str,
    **filters,
) -> int:
    """Count captured events of type event attributed to the given side and species name."""
    count = 0
    for kw in capturing.of(event):
        if kw.get("side") != side:
            continue
        if not _species_name_matches(name, kw.get("target")):
            continue
        if not all(kw.get(k) == v for k, v in filters.items()):
            continue
        count += 1
    return count


def _restore_msg_is_cheek_pouch(msg) -> bool:
    """True if a generic HP-restore message names Cheek Pouch in its source-name var."""
    if not msg.var_values or len(msg.var_values) < 2:
        return False
    return _Lev.distance(msg.var_values[1].upper(), _CHEEK_POUCH_LABEL) <= _species_match_threshold(_CHEEK_POUCH_LABEL)


# ---------------------------------------------------------------------------
# Main reconciliation function
# ---------------------------------------------------------------------------

def check_log_events(
    capturing: CapturingLogger,
    all_messages: list[MatchResult],
    opponent_hp_deltas: list,
    opp_species,
) -> bool:
    """Return True if the sim log is consistent with all observed messages.

    Checks presence constraints (observed message → log event must have fired) and
    the HP no-change constraint when opponent_hp_deltas is empty.
    opponent_hp_deltas: per-slot list[list[tuple]] (or legacy flat list[tuple]).
    """
    msg_ids = {msg.string_id for msg in all_messages}

    # Presence constraints
    if "STRINGID_CRITICALHIT" in msg_ids:
        if not capturing.fired(LogEvent.CRIT):
            return False

    if "STRINGID_PKMNFLINCHED" in msg_ids:
        if not capturing.fired(LogEvent.CANT_FLINCH):
            return False

    if "STRINGID_PKMNISPARALYZED" in msg_ids:
        if not capturing.fired(LogEvent.CANT_PARALYSIS):
            return False

    if "STRINGID_PKMNFASTASLEEP" in msg_ids:
        if not capturing.fired(LogEvent.CANT_SLEEP):
            return False

    if "STRINGID_PKMNISFROZEN" in msg_ids:
        if not capturing.fired(LogEvent.CANT_FROZEN):
            return False

    if "STRINGID_PKMNIMMOBILIZEDBYLOVE" in msg_ids:
        if not capturing.fired(LogEvent.CANT_INFATUATION):
            return False

    if "STRINGID_ITHURTCONFUSION" in msg_ids:
        if not capturing.fired(LogEvent.HIT_SELF_CONFUSION):
            return False

    if "STRINGID_ATTACKMISSED" in msg_ids:
        if not capturing.fired(LogEvent.MOVE_MISS):
            return False

    # A1 — Status-apply constraints
    for msg in all_messages:
        status = _STATUS_APPLY_IDS.get(msg.string_id)
        if status is None:
            continue
        target = _status_msg_target(msg)
        if target is None:
            if not capturing.fired(LogEvent.STATUS_APPLY, status=status):
                return False
            continue
        target_side, target_name = target
        if _event_attributed_to(capturing, LogEvent.STATUS_APPLY,
                                target_side, target_name, status=status) < 1:
            return False

    # A2 — Stat-change constraints
    _any_fragment_stat = False
    for msg in all_messages:
        sid = msg.string_id
        if sid in _STAT_ROSE_WITH_NAME_IDS and msg.var_values:
            name = msg.var_values[0]
            target_side = 1 if _msg_is_foe(msg) else 0
            if not any(
                kw.get("side") == target_side
                and _species_name_matches(name, kw.get("target"))
                and (kw.get("stages") or 0) > 0
                for kw in capturing.of(LogEvent.STAT_BOOST)
            ):
                return False
        elif sid in _STAT_FELL_WITH_NAME_IDS and msg.var_values:
            name = msg.var_values[0]
            target_side = 1 if _msg_is_foe(msg) else 0
            if sum(
                1 for kw in capturing.of(LogEvent.STAT_BOOST)
                if kw.get("side") == target_side
                and _species_name_matches(name, kw.get("target"))
                and (kw.get("stages") or 0) < 0
            ) < 1:
                return False
        elif sid == _STAT_USING_ITEM_ID:
            if len(msg.var_values) >= 3:
                bare_name = msg.var_values[2]
                target_side = msg.side_of_name_slot(2)
                if target_side is None:
                    raise SimulationError(
                        reason=(
                            f"USINGITEMSTATOFPKMNROSE: cannot determine side for mon "
                            f"'{bare_name}' at var_values[2] — name_side_slots[2] is absent. "
                            f"Cannot attribute pinch-berry stat boost to a side."
                        )
                    )
                if not any(
                    kw.get("side") == target_side
                    and _species_name_matches(bare_name, kw.get("target"))
                    and (kw.get("stages") or 0) > 0
                    for kw in capturing.of(LogEvent.STAT_BOOST)
                ):
                    return False
            else:
                raise SimulationError(
                    reason=(
                        f"USINGITEMSTATOFPKMNROSE has fewer than 3 var_values "
                        f"({msg.var_values!r}): the mon name at index 2 is missing, so the "
                        f"pinch-berry stat boost cannot be attributed to a side."
                    )
                )
        elif sid in _STAT_FRAGMENT_IDS:
            _any_fragment_stat = True
    if _any_fragment_stat and not capturing.fired(LogEvent.STAT_BOOST):
        return False

    # A3 — Confusion-apply constraint
    for msg in all_messages:
        if msg.string_id != "STRINGID_PKMNWASCONFUSED":
            continue
        if not msg.var_values:
            if not capturing.fired(LogEvent.VOLATILE_APPLY, volatile="confused"):
                return False
            continue
        target_side = 1 if _msg_is_foe(msg) else 0
        target_name = msg.var_values[0]
        if _event_attributed_to(capturing, LogEvent.VOLATILE_APPLY,
                                target_side, target_name, volatile="confused") < 1:
            return False

    # Multi-hit count constraint
    for i, msg in enumerate(all_messages):
        if msg.string_id == "STRINGID_HITXTIMES" and msg.var_values:
            try:
                expected_hits = int(msg.var_values[0])
            except (ValueError, IndexError):
                continue
            attacker_msg = None
            for prev in reversed(all_messages[:i]):
                if prev.string_id == _USEDMOVE_ID and prev.var_values:
                    attacker_msg = prev
                    break
            if attacker_msg is None:
                raise SimulationError(
                    reason=f"HITXTIMES message with no preceding USEDMOVE: {msg!r}"
                )
            attacker_name = attacker_msg.var_values[0]
            attacker_side = 1 if _msg_is_foe(attacker_msg) else 0
            actual_hits = sum(
                1 for kw in capturing.of(LogEvent.HITCOUNT)
                if kw.get("side") == attacker_side
                and _species_name_matches(attacker_name, kw.get("user"))
            )
            if actual_hits != expected_hits:
                return False

    # HP no-change constraint
    if not any(opponent_hp_deltas) and opp_species is not None:
        if _total_side_move_damage(capturing, target_side=1) != 0:
            return False

    # Item/ability-restore corroboration
    obs_berry = {0: 0, 1: 0}
    obs_pouch = {0: 0, 1: 0}
    for msg in all_messages:
        if msg.string_id in _HEAL_RESTORE_STRING_IDS:
            side = msg.side_hint if msg.side_hint is not None else (1 if _msg_is_foe(msg) else 0)
            if _restore_msg_is_cheek_pouch(msg):
                obs_pouch[side] += 1
            else:
                obs_berry[side] += 1
    for _source, _obs in (("berry", obs_berry), ("cheek_pouch", obs_pouch)):
        if _obs[0] or _obs[1] or capturing.fired(LogEvent.HEAL, source=_source):
            _sim = {0: 0, 1: 0}
            for ev, kw in capturing.events:
                if ev == LogEvent.HEAL and kw.get("source") == _source:
                    _hside = kw.get("side")
                    if _hside not in (0, 1):
                        raise SimulationError(
                            reason=(
                                f"HEAL event (source={_source!r}) is missing a valid side "
                                f"kwarg (got {_hside!r}); cannot corroborate consumption."
                            )
                        )
                    _sim[_hside] += 1
            if _obs != _sim:
                return False

    # EXP gain constraints
    exp_messages = [msg for msg in all_messages if msg.string_id == "STRINGID_PKMNGAINEDEXP"]
    sim_exp_gains = [kw["amount"] for kw in capturing.of(LogEvent.EXP_GAIN)]

    if len(exp_messages) != len(sim_exp_gains):
        return False

    for msg, sim_amount in zip(exp_messages, sim_exp_gains):
        observed_amount = int(msg.var_values[1])
        if observed_amount != sim_amount:
            return False

    # Level-up constraint
    observed_levels = {int(msg.var_values[1]) for msg in all_messages
                       if msg.string_id == "STRINGID_PKMNGREWTOLV"}
    sim_level_ups = [kw["new_level"] for kw in capturing.of(LogEvent.LEVEL_UP)]
    for lvl in sim_level_ups:
        if lvl not in observed_levels:
            return False

    # Faint identity + ordering
    if not _faint_skeleton_consistent(
        _observed_event_skeleton(all_messages), _sim_event_skeleton(capturing)
    ):
        return False

    return True


# ---------------------------------------------------------------------------
# Action-order + HP checks
# ---------------------------------------------------------------------------

def _check_action_order(capturing: CapturingLogger, observed_order: list[int]) -> bool:
    """Return True if the observed move-execution order is a prefix of the sim's order."""
    if not observed_order:
        return True
    sim_order = [kw.get("side") for ev, kw in capturing.events if ev == LogEvent.MOVE_USE]
    n = len(observed_order)
    if len(sim_order) < n:
        return False
    return sim_order[:n] == observed_order


def _resolve_record_team_idx(result_state: BattleState, record) -> int:
    """Resolve which result_state team slot an HpDeltaSeq record validates against.

    Raises SimulationError for unknown species or unresolved ambiguity.
    """
    side = record.side
    species = record.species
    team = result_state.sides[side].team
    final_val = record.deltas[-1][1]

    matching = [i for i, mon in enumerate(team) if mon.species == species]
    if not matching:
        raise SimulationError(
            reason=(
                f"_check_hp_match: species {species.name} not found in result_state "
                f"side {side} team. Cannot validate HP delta."
            )
        )
    if len(matching) == 1:
        return matching[0]

    side_state = result_state.sides[side]
    if final_val == 0:
        fainted = [i for i in matching if team[i].hp == 0]
        if len(fainted) == 1:
            return fainted[0]
    active_idx = (side_state.active_indices[record.slot]
                  if record.slot < len(side_state.active_indices) else None)
    if active_idx is not None and active_idx in matching:
        return active_idx
    raise SimulationError(
        reason=(
            f"_check_hp_match: species {species.name} appears {len(matching)} times "
            f"in result_state side {side} team and none is active in slot "
            f"{record.slot}. Same-species ambiguity — cannot determine which "
            f"mon's HP to validate."
        )
    )


def _hp_to_k(hp: int, max_hp: int) -> int:
    """Forward map exact HP → k-pixel bar value (pokeemerald battle_interface.c)."""
    if hp <= 0:
        return 0
    return max(1, (hp * 48) // max_hp)


def _event_target_side(kw: dict):
    """Best-effort side of the mon whose HP a DAMAGE/HEAL event changed, or None."""
    if "defender_side" in kw:
        return kw["defender_side"]
    if "side" in kw:
        return kw["side"]
    return None


def _sim_hp_changes(capturing: CapturingLogger, side: int, species, max_hp: int) -> list[int]:
    """Ordered signed HP changes the simulation applied to one mon."""
    changes: list[int] = []
    for ev, kw in capturing.events:
        spec = _HP_CHANGE_EVENTS.get(ev)
        if spec is None:
            continue
        id_key, amt_key, sign = spec
        if kw.get(id_key) != species:
            continue
        ev_side = _event_target_side(kw)
        if ev_side is not None and ev_side != side:
            continue
        amount = kw.get(amt_key, 0) or 0
        if amount == 0:
            continue
        changes.append(sign * amount)
    return changes


def _hp_count_detail(result_state: BattleState, capturing: CapturingLogger, hp_deltas: list) -> tuple:
    """Compare the COUNT of HP-change transitions (observed vs simulated) per mon.

    Returns (ok, reason); reason names the mon and the two counts on the first mismatch.
    """
    for record in hp_deltas:
        if not record.deltas:
            continue
        observed_count = sum(1 for (b, a) in record.deltas if b != a)
        team_idx = _resolve_record_team_idx(result_state, record)
        species = record.species
        final_hp = result_state.sides[record.side].team[team_idx].hp

        changes = _sim_hp_changes(capturing, record.side, species, record.max_hp)
        traj = [final_hp]
        hp = final_hp
        for delta in reversed(changes):
            hp = hp - delta
            traj.append(hp)
        traj.reverse()

        observed_start = record.deltas[0][0]
        recon_start = traj[0] if record.side == 0 else _hp_to_k(traj[0], record.max_hp)
        if recon_start != observed_start:
            continue

        if record.side == 0:
            sim_count = sum(1 for x, y in zip(traj, traj[1:]) if x != y)
        else:
            ks = [_hp_to_k(h, record.max_hp) for h in traj]
            sim_count = sum(1 for x, y in zip(ks, ks[1:]) if x != y)

        if sim_count != observed_count:
            return False, (
                f"{species.name}(side{record.side} slot{record.slot}): sim HP-change "
                f"count {sim_count} != observed {observed_count}"
            )
    return True, None


def _check_hp_count(result_state: BattleState, capturing: CapturingLogger, hp_deltas: list) -> bool:
    """Boolean wrapper over _hp_count_detail."""
    ok, _ = _hp_count_detail(result_state, capturing, hp_deltas)
    return ok


def _hp_match_detail(result_state: BattleState, hp_deltas: list) -> tuple:
    """Check HP deltas and return (ok, reason)."""
    for record in hp_deltas:
        if not record.deltas:
            continue
        side = record.side
        species = record.species
        team = result_state.sides[side].team
        final_val = record.deltas[-1][1]

        team_idx = _resolve_record_team_idx(result_state, record)
        actual_hp = team[team_idx].hp

        if side == 0:
            if actual_hp != final_val:
                return False, (
                    f"{species.name}(side0 slot{record.slot}): actual_hp={actual_hp} "
                    f"!= expected {final_val}"
                )
        else:
            hp_min, hp_max = hp_range(final_val, record.max_hp)
            if not (hp_min <= actual_hp <= hp_max):
                return False, (
                    f"{species.name}(side1 slot{record.slot}): actual_hp={actual_hp} "
                    f"not in hp_range(k={final_val},max={record.max_hp})=[{hp_min},{hp_max}]"
                )

    return True, None


def _check_hp_match(result_state: BattleState, hp_deltas: list) -> bool:
    """Check simulated HP changes against identity-bound HpDeltaSeq records."""
    ok, _ = _hp_match_detail(result_state, hp_deltas)
    return ok


def _records_to_perslot(hp_deltas: list, initial_state: BattleState) -> tuple:
    """Derive legacy per-slot views from identity-bound HpDeltaSeq records.

    Returns (player_perslot, opponent_perslot, opponent_max_hp_list).
    """
    n_slots_0 = len(initial_state.sides[0].active_indices)
    n_slots_1 = len(initial_state.sides[1].active_indices)

    player_perslot: list[list[tuple]] = [[] for _ in range(n_slots_0)]
    opponent_perslot: list[list[tuple]] = [[] for _ in range(n_slots_1)]
    opponent_max_hp_list: list[int] = [0] * n_slots_1

    for record in hp_deltas:
        slot = record.slot
        if record.side == 0:
            if slot < n_slots_0:
                player_perslot[slot] = list(record.deltas)
        else:
            if slot < n_slots_1:
                opponent_perslot[slot] = list(record.deltas)
                opponent_max_hp_list[slot] = record.max_hp

    for i in range(n_slots_1):
        if opponent_max_hp_list[i] == 0:
            idx = initial_state.sides[1].active_indices[i] if i < n_slots_1 else 0
            if idx < len(initial_state.sides[1].team):
                opponent_max_hp_list[i] = initial_state.sides[1].team[idx].max_hp or 1
            else:
                opponent_max_hp_list[i] = 1

    return player_perslot, opponent_perslot, opponent_max_hp_list


# ---------------------------------------------------------------------------
# Damage-sum helpers
# ---------------------------------------------------------------------------

def _sum_damage(capturing: CapturingLogger, target_species, target_side: Optional[int] = None) -> int:
    """Sum all move-source damage dealt to target_species in one captured turn."""
    if target_species is None:
        return 0
    return sum(
        e["amount"]
        for e in capturing.all_of(LogEvent.DAMAGE, target=target_species, source="move")
        if target_side is None or e.get("defender_side") == target_side
    )


def _total_side_move_damage(capturing: CapturingLogger, target_side: int) -> int:
    """Sum all move-source damage dealt to ANY mon on target_side in one captured turn."""
    return sum(
        e["amount"]
        for e in capturing.all_of(LogEvent.DAMAGE, source="move")
        if e.get("defender_side") == target_side
    )


def _per_hit_damages(capturing: CapturingLogger, target_species, target_side: Optional[int] = None) -> list[int]:
    """Return ordered list of per-hit move-source damage amounts for target_species."""
    if target_species is None:
        return []
    return [
        e["amount"]
        for e in capturing.all_of(LogEvent.DAMAGE, target=target_species, source="move")
        if target_side is None or e.get("defender_side") == target_side
    ]


def _own_damage(capturing: CapturingLogger, attacker_side: int, attacker_slot: int) -> int:
    """Sum move-source damage emitted by the specific attacker (side + slot)."""
    return sum(_attacker_per_hit_damages(capturing, attacker_side, attacker_slot))


def _attacker_per_hit_damages(capturing: CapturingLogger, attacker_side: int, attacker_slot: int) -> list[int]:
    """Return the ordered per-hit move-source damages emitted BY a specific attacker (side + slot)."""
    return [
        e["amount"]
        for e in capturing.all_of(
            LogEvent.DAMAGE, source="move",
            attacker_side=attacker_side, attacker_slot=attacker_slot,
        )
    ]


def _self_hit_damage(capturing: CapturingLogger, side: int) -> int:
    """Sum HIT_SELF_CONFUSION damage for the given side. Returns 0 when none fired."""
    return sum(e["damage"] for e in capturing.all_of(LogEvent.HIT_SELF_CONFUSION, side=side))


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

def has_fainted_active(state: BattleState) -> bool:
    """Return True if any side has a fainted active Pokemon AND living bench members."""
    for si, side in enumerate(state.sides):
        bench_available = any(
            i not in side.active_indices and not m.fainted
            for i, m in enumerate(side.team)
        )
        if not bench_available:
            continue
        if any(side.team[team_idx].fainted for team_idx in side.active_indices):
            return True
    return False
