# Roll/crit enumeration core and top-level sweep orchestration.
# Ports per-mover roll enumeration, per-turn phase loop, and run_candidate_sweep from
# OLD src/simulation_runner.py. _sweep_evaluate_pairs and run_candidate_sweep are the
# two orchestration functions; everything below them is pure enumeration support.
from __future__ import annotations

import itertools
import time
from typing import Optional

from liveplay.candidate import Candidate, PartialCandidate
from liveplay.hp_stability import hp_range
from liveplay.sweep_driver import (
    SideOverrides, SweepConfig,
    run_with_capture,
    _attacker_per_hit_damages,
    _self_hit_damage,
)
from liveplay.sweep_actions import (
    _acting_action,
    _fmt_action,
    _sweep_build_flat_messages,
    _build_attacker_slot_maps,
    _extract_known_actions,
    UnreproducibleObservedMoveError,
    _extract_used_moves_from_groups,
    _message_action_order_with_state,
    _sweep_resolve_candidate_actions,
    _validate_forced_opponent_switch,
    PostFaintMovePhaseError,
    _collapse_metronome_calls,
    _opponent_switch_in_actions,
    message_crit_counts_with_state,
    _message_hit_counts_with_state,
    _validate_known_opponent_action,
    UnexpectedOpponentActionError,
)
from liveplay.sweep_reconcile import (
    _hp_match_detail,
    _hp_count_detail,
    check_log_events,
    _apply_observed_levelups,
    _apply_observed_wrap_release,
    _apply_observed_rampage_end,
    _records_to_perslot,
    _check_action_order,
)
from liveplay.sweep_secondaries import build_sweep_injected_overrides
from liveplay.rng import RNGEvent, aggregate_uninjected_warnings
from liveplay.engine_select import SimulationError


# Maximum total branch count before the sweep fails loudly instead of exploding.
_SWEEP_BRANCH_CAP = 1000


# ---------------------------------------------------------------------------
# Enumeration-time HP-delta pruning helpers
# ---------------------------------------------------------------------------

def _segment_hp_deltas_into_hits(mh_hp_deltas: list) -> tuple:
    """Split consecutive bar readings into per-hit damage constraints, anchored across heals.

    Returns (hit_anchor, hit_new_val, hit_seg_start): three parallel lists, one entry per
    damage delta (to <= from). A heal delta (to > from) consumes no hit slot but resets the
    segment anchor so the cumulative-damage model holds within each segment.
    """
    hit_anchor: list[int] = []
    hit_new_val: list[int] = []
    hit_seg_start: list[int] = []
    seg_anchor = mh_hp_deltas[0][0] if mh_hp_deltas else None
    seg_start = 0
    for frm, to in mh_hp_deltas:
        if to > frm:
            # Heal: reset segment anchor without consuming a hit slot.
            seg_anchor = to
            seg_start = len(hit_anchor)
        else:
            hit_anchor.append(seg_anchor)
            hit_new_val.append(to)
            hit_seg_start.append(seg_start)
    return hit_anchor, hit_new_val, hit_seg_start


def _hit_passes_constraint(
    cumulative: int,
    anchor: int,
    new_val: int,
    use_hp_range: bool,
    opponent_max_hp: int,
) -> bool:
    """True if cumulative segment damage is consistent with the observed reading.

    KO (new_val == 0) may overkill, so the upper bound is skipped. Opponent-side readings
    use a k-pixel range; player-side readings are exact.
    """
    if use_hp_range:
        hp_min_old, hp_max_old = hp_range(anchor, opponent_max_hp)
        hp_min_new, hp_max_new = hp_range(new_val, opponent_max_hp)
        lower_ok = hp_max_new + cumulative >= hp_min_old
        upper_ok = new_val == 0 or hp_min_new + cumulative <= hp_max_old
        return lower_ok and upper_ok
    # Exact player-side: KO may overkill; otherwise remaining HP must match exactly.
    if new_val == 0:
        return anchor - cumulative <= 0
    return anchor - cumulative == new_val


# ---------------------------------------------------------------------------
# SweepConfig builder from partial candidate
# ---------------------------------------------------------------------------

def make_sweep_config(
    partial: PartialCandidate,
    movers: list[tuple[int, int]],
    mover_iteration: int,
    current_roll,
    current_crit,
    tie_winner: int,
    combo_ovr_0: dict,
    combo_ovr_1: dict,
    injected_pre: dict,
    self_hit_roll: Optional[tuple[int, int, float]] = None,
) -> SweepConfig:
    """Build a SweepConfig from a partial candidate, current mover, and per-side overrides.

    Assembles slot-keyed roll/crit dicts from decided movers (partial.rolls/crits), the
    current mover (current_roll/current_crit), and placeholder 0.5/False for future movers.
    Singles (exactly one mover at slot 0) use scalar SideOverrides for backward compat.
    Doubles (multiple movers or non-zero slot) use dict-keyed SideOverrides.
    self_hit_roll: optional (side, slot, roll) for confusion self-hit, independent of the
    mover sequence.
    """
    per_side_rolls: dict[int, dict[int, object]] = {0: {}, 1: {}}
    per_side_crits: dict[int, dict[int, object]] = {0: {}, 1: {}}

    for i, (side, source_slot) in enumerate(movers):
        if i < mover_iteration:
            roll = partial.rolls[i]
            crit = partial.crits[i]
        elif i == mover_iteration:
            roll = current_roll
            crit = current_crit
        else:
            roll = 0.5
            crit = False
        per_side_rolls[side][source_slot] = roll
        per_side_crits[side][source_slot] = crit

    if self_hit_roll is not None:
        sh_side, sh_slot, sh_roll = self_hit_roll
        per_side_rolls[sh_side][sh_slot] = sh_roll
        # No crit entry: confusion self-hit does not consume the crit slot.

    def _build_side_overrides(rolls_dict, crits_dict, combo_ovr) -> SideOverrides:
        if not rolls_dict:
            return SideOverrides(extra_overrides=combo_ovr or None)

        # Singles backward-compat: exactly one mover at slot 0 → scalar/tuple SideOverrides.
        if len(rolls_dict) == 1 and 0 in rolls_dict:
            roll_val = rolls_dict[0]
            crit_val = crits_dict.get(0, False)
            if isinstance(roll_val, tuple):
                # Multi-hit: crits stored as float-threshold tuple.
                crits_tuple = (
                    tuple(crit_val)
                    if isinstance(crit_val, tuple)
                    else (crit_val,) * len(roll_val)
                )
                return SideOverrides(
                    crits_per_hit=crits_tuple,
                    rolls_per_hit=roll_val,
                    extra_overrides=combo_ovr or None,
                )
            return SideOverrides(
                crit=crit_val,
                roll=roll_val,
                extra_overrides=combo_ovr or None,
            )

        # Doubles: dict-keyed by source_slot.
        return SideOverrides(
            rolls_per_hit={slot: v for slot, v in rolls_dict.items()},
            crits_per_hit={slot: c for slot, c in crits_dict.items()},
            extra_overrides=combo_ovr or None,
        )

    return SweepConfig(
        tie_winner=tie_winner,
        extra_pre_inject=injected_pre or None,
        side0=_build_side_overrides(per_side_rolls[0], per_side_crits[0], combo_ovr_0),
        side1=_build_side_overrides(per_side_rolls[1], per_side_crits[1], combo_ovr_1),
    )


# ---------------------------------------------------------------------------
# Per-mover roll enumeration
# ---------------------------------------------------------------------------

def _enumerate_mover_rolls(
    partial: PartialCandidate,
    movers: list[tuple[int, int]],
    mover_iteration: int,
    state,
    action0,
    action1,
    n_hits: int,
    n_crits: int,
    attacker_side: int,
    attacker_slot: int,
    tie_winner: int,
    combo_ovr_0: dict,
    combo_ovr_1: dict,
    injected_pre: dict,
    mh_hp_deltas: list,
    opponent_max_hp: int,
    use_hp_range: bool = True,
    opp_switch_actions: tuple = (),
    apply_hp_prune: bool = True,
) -> list[tuple]:
    """Enumerate per-hit crit assignments and rolls for one mover (single- or multi-hit).

    Returns list of (rolls_per_hit_tuple, crit_assignment_tuple) pairs. Damage is discovered
    by varying each hit's roll across all 16 values while pinning other hits to 0.0, then
    deduplicating by damage value. The multi-hit cartesian product is pruned via the observed
    bar readings when apply_hp_prune=True. attacker_slot is the team index of the attacker.
    """
    # Generate all crit-index combinations for this mover's hit count.
    crit_index_combos = list(itertools.combinations(range(n_hits), n_crits))
    crit_assignments: list[tuple] = []
    for crit_indices in crit_index_combos:
        crit_set = set(crit_indices)
        # Float thresholds: 0.0 = always crit, 101.0 = never crit.
        crit_assignments.append(tuple(0.0 if i in crit_set else 101.0 for i in range(n_hits)))

    results: list[tuple] = []

    for crit_assignment in crit_assignments:
        hit_damage_sets: list[set] = [set() for _ in range(n_hits)]
        hit_roll_map: list[dict[int, float]] = [{} for _ in range(n_hits)]

        # Discover each hit's damage range by varying hit i's roll across 16 values while
        # pinning all other hits to 0.0 (minimum damage). This ensures hit i survives to
        # land even when higher rolls on other hits would KO early.
        for i in range(n_hits):
            for roll_idx in range(16):
                roll = roll_idx / 15.0
                rolls_per_hit = tuple(roll if j == i else 0.0 for j in range(n_hits))

                # Single-hit: use scalar path for fixed-damage moves (Psywave etc.)
                if n_hits == 1:
                    cur_roll = roll
                    cur_crit = (crit_assignment[0] == 0.0)
                else:
                    cur_roll = rolls_per_hit
                    cur_crit = crit_assignment

                config = make_sweep_config(
                    partial, movers, mover_iteration, cur_roll, cur_crit,
                    tie_winner, combo_ovr_0, combo_ovr_1, injected_pre,
                )
                rs, capturing = run_with_capture(
                    state, action0, action1, config, opp_switch_actions
                )
                if rs is None:
                    continue

                per_hit = _attacker_per_hit_damages(capturing, attacker_side, attacker_slot)
                if len(per_hit) <= i:
                    # Non-damaging or early-KO for hit i.
                    if i == 0 and not apply_hp_prune:
                        dmg = 0
                    else:
                        continue
                else:
                    dmg = per_hit[i]

                if dmg not in hit_roll_map[i]:
                    hit_roll_map[i][dmg] = roll
                    hit_damage_sets[i].add(dmg)

        if not all(hit_damage_sets):
            continue

        # Segment bar readings into per-hit constraints and prune the cartesian product.
        hit_anchor, hit_new_val, hit_seg_start = _segment_hp_deltas_into_hits(mh_hp_deltas)
        apply_constraint = apply_hp_prune

        partials: list[tuple[int, ...]] = [()]
        for i in range(n_hits):
            next_partials: list[tuple[int, ...]] = []
            has_constraint = apply_constraint and i < len(hit_anchor)
            for hp_partial in partials:
                for dmg_val in hit_damage_sets[i]:
                    if has_constraint:
                        cumulative = sum(hp_partial[hit_seg_start[i]:]) + dmg_val
                        if not _hit_passes_constraint(
                            cumulative, hit_anchor[i], hit_new_val[i],
                            use_hp_range, opponent_max_hp,
                        ):
                            continue
                    next_partials.append(hp_partial + (dmg_val,))
            partials = next_partials
            if not partials:
                break

        seen_pairs: set[tuple] = set()
        for combo in partials:
            per_hit_rolls = []
            for i in range(n_hits):
                roll = hit_roll_map[i].get(combo[i])
                if roll is None:
                    raise AssertionError(
                        f"No roll found for hit {i} damage {combo[i]} — "
                        f"value in hit_damage_sets but missing from hit_roll_map"
                    )
                per_hit_rolls.append(roll)
            rolls_per_hit = tuple(per_hit_rolls)
            pair = (rolls_per_hit, crit_assignment)
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                results.append(pair)

    return results


# ---------------------------------------------------------------------------
# Acting-action helper (used by _run_phase_loop to derive target_slot)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Per-turn phase loop
# ---------------------------------------------------------------------------

def _run_phase_loop(
    state,
    action0,
    action1,
    movers: list[tuple[int, int]],
    mover_hit_counts: list[int],
    tie_winner: int,
    combo_ovr_0: dict,
    combo_ovr_1: dict,
    injected_pre: dict,
    opponent_hp_deltas: list,
    player_hp_deltas: list,
    opponent_max_hp: list[int],
    crit_counts: list[int],
    opp_switch_actions: tuple = (),
    self_hit_slots: frozenset = frozenset(),
) -> list[tuple]:
    """Enumerate valid (rolls, crits, rs, capturing) sequences over all movers in the turn.

    Returns list of (rolls_tuple, crits_tuple, rs, capturing). Each mover's roll/crit is
    decided sequentially; multi-hit movers get per-hit tuple entries. Self-hit confusion rolls
    are enumerated as a separate dimension after the mover loop.
    """
    # Side list for action-order checking (doubles order-checking is side-level).
    observed_sides = [m[0] for m in movers]

    # Each active element: (PartialCandidate, Optional[BattleState], Optional[CapturingLogger]).
    # rs/capturing are None until a final sim is run (after all movers decided).
    active: list[tuple] = [(PartialCandidate(rolls=(), crits=(), mover_iteration=0), None, None)]

    for iteration in range(len(movers)):
        mover_side, source_slot = movers[iteration]
        mover_n_hits = mover_hit_counts[iteration] if iteration < len(mover_hit_counts) else 1
        next_active: list[tuple] = []

        # Resolve attacker team index and target HP deltas for this mover.
        mover_non_side = 1 - mover_side
        active_indices = state.sides[mover_side].active_indices
        safe_slot = source_slot if source_slot < len(active_indices) else 0
        attacker_team_idx = active_indices[safe_slot]

        act = _acting_action(action0, action1, mover_side, source_slot)
        target_slot = act.target_slot if act is not None else 0
        perslot = opponent_hp_deltas if mover_non_side == 1 else player_hp_deltas
        target_hp_deltas = perslot[target_slot] if target_slot < len(perslot) else []
        use_hp_range = (mover_non_side == 1)
        max_hp_for_target = (
            opponent_max_hp[target_slot]
            if target_slot < len(opponent_max_hp)
            else opponent_max_hp[0]
        )

        # HP-delta pruning applies only to genuine multi-hit movers.
        apply_hp_prune = mover_n_hits > 1

        # Single-hit: clamp crit count to 0/1 (it's a per-move roll, not per-hit).
        mover_crit_count = crit_counts[iteration] if iteration < len(crit_counts) else 0
        if not apply_hp_prune:
            mover_crit_count = 1 if mover_crit_count > 0 else 0

        for partial, _prev_rs, _prev_capturing in active:
            mover_results = _enumerate_mover_rolls(
                partial, movers, iteration,
                state, action0, action1,
                mover_n_hits, mover_crit_count,
                mover_side, attacker_team_idx, tie_winner,
                combo_ovr_0, combo_ovr_1, injected_pre,
                target_hp_deltas, max_hp_for_target, use_hp_range,
                opp_switch_actions,
                apply_hp_prune=apply_hp_prune,
            )
            for rolls_per_hit, crit_assignment in mover_results:
                if apply_hp_prune:
                    # Multi-hit: store per-hit tuples.
                    roll_entry = rolls_per_hit
                    crit_entry = crit_assignment
                else:
                    # Single-hit: fold length-1 tuples back to scalar form.
                    roll_entry = rolls_per_hit[0]
                    crit_entry = (crit_assignment[0] == 0.0)
                extended = PartialCandidate(
                    rolls=partial.rolls + (roll_entry,),
                    crits=partial.crits + (crit_entry,),
                    mover_iteration=iteration + 1,
                )
                next_active.append((extended, None, None))

        active = next_active

    # Self-hit roll expansion: enumerate 16 rolls for any confused mon that hit itself.
    # The self-hitter has no USEDMOVE so it is absent from movers; partial shape stays fixed.
    if self_hit_slots:
        expanded: list[tuple] = []
        for sh_side, sh_slot in self_hit_slots:
            for partial, _prev_rs, _prev_capturing in active:
                seen_self_dmg: set = set()
                for roll_idx in range(16):
                    sh_roll = roll_idx / 15.0
                    config = make_sweep_config(
                        partial, movers, len(movers), 0.5, False,
                        tie_winner, combo_ovr_0, combo_ovr_1, injected_pre,
                        self_hit_roll=(sh_side, sh_slot, sh_roll),
                    )
                    rs, capturing = run_with_capture(
                        state, action0, action1, config, opp_switch_actions
                    )
                    if rs is None:
                        continue
                    if not _check_action_order(capturing, observed_sides):
                        continue
                    self_dmg = _self_hit_damage(capturing, sh_side)
                    if self_dmg in seen_self_dmg:
                        continue
                    seen_self_dmg.add(self_dmg)
                    expanded.append((partial, rs, capturing))
        active = [(partial, rs, capturing) for partial, rs, capturing in expanded]

    # Run final sims for partials that haven't been simulated yet.
    # Self-hit-expanded partials already carry concrete rs/capturing; skip them.
    survivors: list[tuple] = []
    for partial, rs, capturing in active:
        if rs is None:
            config = make_sweep_config(
                partial, movers, len(movers), 0.5, False,
                tie_winner, combo_ovr_0, combo_ovr_1, injected_pre,
            )
            rs, capturing = run_with_capture(
                state, action0, action1, config, opp_switch_actions
            )
            if rs is None:
                continue
            if not _check_action_order(capturing, observed_sides):
                continue
        survivors.append((partial.rolls, partial.crits, rs, capturing))

    return survivors


# ---------------------------------------------------------------------------
# Active-species helper
# ---------------------------------------------------------------------------

def _active_species(bs, side: int):
    """Return the species of the active mon on the given side, or None."""
    s = bs.sides[side]
    if not s.active_indices:
        return None
    idx = s.active_indices[0]
    return s.team[idx].species if idx < len(s.team) else None


# ---------------------------------------------------------------------------
# Pair evaluator: all secondary combos for one (action0, action1) pair
# ---------------------------------------------------------------------------

def _sweep_evaluate_pairs(
    state,
    action0,
    action1,
    secondary_combos: list[dict],
    injected_overrides_0: dict,
    injected_overrides_1: dict,
    injected_pre: dict,
    all_messages_flat: list,
    opponent_hp_deltas: list,
    player_hp_deltas: list,
    initial_candidate: Candidate,
    seen_states: set,
    tie_winner: int,
    crit_counts: list[int],
    movers: list[tuple[int, int]],
    opp_species,
    mover_hit_counts: list[int],
    opponent_max_hp: list[int],
    pair_idx: int,
    n_pairs: int,
    hp_deltas: list,
    opp_switch_actions: tuple = (),
    self_hit_slots: frozenset = frozenset(),
) -> list[Candidate]:
    """Evaluate all secondary combos for one (action0, action1) pair, returning new candidates.

    Mutates seen_states in place (passed by reference — mutations are visible to caller).
    movers is list[tuple[int,int]] of (side, source_slot); observed_order is derived internally.
    mover_hit_counts[i] is the hit count for movers[i]; >1 triggers multi-hit enumeration.
    opponent_max_hp: per-slot list[int] (normalised by caller).
    hp_deltas: identity-bound HpDeltaSeq list passed through to _check_hp_match.
    """
    result: list[Candidate] = []

    print(
        f"[sweep]   pair {pair_idx}/{n_pairs}: "
        f"{_fmt_action(action0)} vs {_fmt_action(action1)}",
        flush=True,
    )

    for combo in secondary_combos:
        # Build per-side combo overrides merged on top of injected overrides.
        # Combo keys are (side, slot, event); the merge writes each per-slot into a dict value
        # so multiple movers' entries coexist without overwriting each other. The existing
        # injected value is either a dict (from per-slot attributable/flinch injection) — into
        # which we merge a COPY (never mutate the shared injected dict across combos) — or
        # absent/scalar-False, which we upgrade to a per-slot dict. A scalar-True existing value
        # for a per-slot event is a logic error (it should already be a per-slot dict) → fail loud.
        combo_ovr_0 = dict(injected_overrides_0)
        combo_ovr_1 = dict(injected_overrides_1)
        for (side, slot, event), val in combo.items():
            combo_ovr = combo_ovr_0 if side == 0 else combo_ovr_1
            existing = combo_ovr.get(event)
            if isinstance(existing, dict):
                # Copy then merge — don't overwrite already-forced slots (observed effect wins),
                # and don't mutate the dict shared with injected_overrides / other combos.
                merged = dict(existing)
                merged.setdefault(slot, val)
                combo_ovr[event] = merged
            elif existing is None or existing is False:
                # Upgrade scalar False / absent to per-slot dict
                combo_ovr[event] = {slot: val}
            elif existing is True:
                # Scalar True means the whole side was forced — a per-slot override
                # on top of that is a logic error (injected True should be per-slot already).
                raise SimulationError(
                    reason=(
                        f"Combo tries to set per-slot override for side {side} slot {slot} "
                        f"event {event}, but existing injected value is scalar True. "
                        f"Injected per-slot overrides must already be dicts."
                    )
                )

        loop_survivors = _run_phase_loop(
            state, action0, action1,
            movers,
            mover_hit_counts,
            tie_winner,
            combo_ovr_0, combo_ovr_1, injected_pre,
            opponent_hp_deltas, player_hp_deltas,
            opponent_max_hp, crit_counts,
            opp_switch_actions,
            self_hit_slots=self_hit_slots,
        )

        print(
            f"[sweep]   loop survivors: {len(loop_survivors)}",
            flush=True,
        )

        fail_hp = fail_log = fail_cnt = 0
        # Per-survivor prune reasons: (survivor_index, stage, detail). The HP detail comes
        # from _hp_match_detail, which reports the SAME mon the match actually compared — so
        # the diagnostic never names a different mon than the one that failed (the old
        # "first HP fail" printed the active-slot foe regardless of which record failed,
        # which mis-diagnosed faint+replacement turns — Issue 29).
        prune_reasons: list[tuple[int, str, str]] = []

        for surv_idx, (rolls, crits, rs, capturing) in enumerate(loop_survivors):
            hp_ok, hp_reason = _hp_match_detail(rs, hp_deltas)
            if not hp_ok:
                fail_hp += 1
                prune_reasons.append((surv_idx, "HP", hp_reason))
                continue

            # HP-delta COUNT check: endpoint matching alone can't distinguish a wrong final
            # HP caused by an extra residual tick (e.g. a phantom Wrap tick on the release
            # turn) from a different damage roll. Compare the number of HP-bar transitions.
            cnt_ok, cnt_reason = _hp_count_detail(rs, capturing, hp_deltas)
            if not cnt_ok:
                fail_cnt += 1
                prune_reasons.append((surv_idx, "HPCNT", cnt_reason))
                continue

            if not check_log_events(capturing, all_messages_flat, opponent_hp_deltas, opp_species):
                fail_log += 1
                prune_reasons.append((surv_idx, "LOG", "log-event mismatch"))
                continue

            # HP/log validation runs on the pre-level-up state: the end-of-turn HP bar the
            # camera reads shows the PRE-bump value (a battle level-up's HP gain isn't drawn
            # until the bar is next refreshed). Now trust observed level-ups (PKMNGREWTOLV) and
            # apply them to the carried-forward candidate so it stays consistent for future turns
            # — see Issue 13 (benched EXP-Share recipient kept under threshold by a low exp seed).
            _apply_observed_levelups(rs, all_messages_flat)

            # Dedup on the state itself (set keyed on __eq__), NOT hash(rs): a 64-bit hash
            # collision would silently drop a genuinely-distinct candidate (F2). BattleState
            # is hashable, so a set of states buckets by __hash__ and disambiguates by __eq__.
            if rs in seen_states:
                continue
            seen_states.add(rs)

            # Build interleaved rng_sequence: (DAMAGE_ROLL, CRIT) per mover, then SPEED_TIE
            rng_sequence = []
            for i in range(len(movers)):
                rng_sequence.append((RNGEvent.DAMAGE_ROLL, rolls[i]))
                rng_sequence.append((RNGEvent.CRIT, crits[i]))
            rng_sequence.append((RNGEvent.SPEED_TIE, tie_winner))

            result.append(Candidate(
                state=rs,
                rng_sequence=rng_sequence,
                unknown_actions={0: action0, 1: action1},
                parent_candidate=initial_candidate,
            ))

        if fail_hp or fail_log or fail_cnt:
            print(
                f"[sweep]   pair {pair_idx}/{n_pairs} hp={fail_hp} hpcnt={fail_cnt} "
                f"log={fail_log} (survivors={len(loop_survivors)})",
                flush=True,
            )
            # Per-survivor prune reasons (capped to keep the log readable). Each line states
            # the survivor index, which stage it died at (HP vs LOG), and the mismatch detail.
            _CAP = 16
            for surv_idx, stage, detail in prune_reasons[:_CAP]:
                print(f"[sweep]     #{surv_idx} {stage}: {detail}", flush=True)
            if len(prune_reasons) > _CAP:
                print(
                    f"[sweep]     … {len(prune_reasons) - _CAP} more "
                    f"({fail_hp} HP, {fail_log} LOG total)",
                    flush=True,
                )
            print(f"[sweep]     hp_deltas={hp_deltas}", flush=True)

    return result


# ---------------------------------------------------------------------------
# Top-level sweep orchestration
# ---------------------------------------------------------------------------

@aggregate_uninjected_warnings()
def run_candidate_sweep(
    messages: list,
    hp_deltas: list,
    initial_candidates: list[Candidate],
    action_groups: Optional[list] = None,
) -> list[Candidate]:
    """Enumerate RNG/action combos for each initial candidate and return survivors.

    Filters by HP delta match, action order match, and log-event consistency.
    Uses sequential per-side roll enumeration with damage-value deduplication.
    Returns deduplicated Candidate list (one per unique final BattleState).

    hp_deltas: list of HpDeltaSeq records — identity-bound (side, species, slot, deltas, max_hp).
    action_groups: optional structured message groups for secondary effect injection.
    """

    all_new_candidates: list[Candidate] = []
    seen_states: set = set()
    t_start = time.time()

    # Metronome (Issue 21): collapse each "used Metronome!" + "used <called>!" USEDMOVE
    # pair into a single tagged message so the engine's single-move-use model matches the
    # observed stream. Hard-crashes if a called move isn't in the Move enum.
    _dropped_ids: set[int] = set()
    if initial_candidates:
        _orig_messages = messages
        messages = _collapse_metronome_calls(messages, initial_candidates[0].state)
        _kept_ids = {id(m) for m in messages}
        _dropped_ids = {id(m) for m in _orig_messages if id(m) not in _kept_ids}

    all_messages_flat = _sweep_build_flat_messages(messages, action_groups)
    if _dropped_ids:
        # _sweep_build_flat_messages re-appends action_group primaries/secondaries by
        # identity; drop any collapsed called-move message it reintroduced so the flat
        # mover-count path stays consistent with the collapsed base.
        all_messages_flat = [m for m in all_messages_flat if id(m) not in _dropped_ids]

    # Battle-start opening: INTROMSG present means both leads were just sent out and
    # NEITHER side has chosen an action yet (no USEDMOVE / voluntary switch this turn).
    # There is no turn to simulate — the observed opening state IS the candidate. Running
    # the normal action-enumeration + step machinery would invent phantom branches (notably
    # opponent switch->bench hypotheses that diverge the visibly-observed opponent active
    # species and later crash slot resolution). Emit each initial state unchanged as its own
    # child candidate and skip enumeration/simulation entirely.
    if any(m.string_id == "STRINGID_INTROMSG" for m in messages):
        for initial_candidate in initial_candidates:
            # Dedup on the state object (collision-proof via __eq__), not its int hash (F2).
            if initial_candidate.state in seen_states:
                continue
            seen_states.add(initial_candidate.state)
            all_new_candidates.append(Candidate(
                state=initial_candidate.state,
                rng_sequence=[],
                unknown_actions={0: None, 1: None},
                parent_candidate=initial_candidate,
            ))
        elapsed = time.time() - t_start
        print(
            f"[sweep] battle-start opening: {len(all_new_candidates)} candidate(s) "
            f"(no actions enumerated)",
            flush=True,
        )
        if not all_new_candidates:
            raise SimulationError(messages, hp_deltas, initial_candidates)
        return all_new_candidates

    for c_idx, initial_candidate in enumerate(initial_candidates):
        state = initial_candidate.state
        # Honor an observed Wrap/binding release: if the game freed a mon this turn, clear its
        # carried-forward BOUND (which may be misaligned-long from the cast-turn duration roll)
        # so the engine deals no residual tick and the mon acts freely. No-op when not observed.
        state = _apply_observed_wrap_release(state, messages)
        # Same for an observed rampage end (fatigue-confusion): trim the assumed-max RAMPAGING
        # so the engine doesn't keep the mon locked into Thrash/Outrage when the game freed it.
        state = _apply_observed_rampage_end(state, messages)

        # --- Slot-independent quantities (same across every attacker slot_map) -----------
        # Derive per-slot views for internal consumers (action enumeration, multi-hit, etc.)
        player_hp_deltas, opponent_hp_deltas, opponent_max_hp = _records_to_perslot(
            hp_deltas, state
        )
        # Per-slot "did this active slot change HP this turn" flags — used to reduce
        # same-species recipient ambiguity (the recipient of a damage/heal/flinch effect
        # took an HP change). Slot-map-independent, so derive once per initial candidate.
        hp_changed_by_slot: dict[tuple[int, int], bool] = {}
        for _pos, _deltas in enumerate(player_hp_deltas):
            hp_changed_by_slot[(0, _pos)] = any(b != a for (b, a) in _deltas)
        for _pos, _deltas in enumerate(opponent_hp_deltas):
            hp_changed_by_slot[(1, _pos)] = any(b != a for (b, a) in _deltas)
        # Opponent post-faint switch-ins to auto-apply mid-turn (not decision boundaries).
        # Each branch is a distinct candidate slot assignment for unreduced duplicate
        # switch-ins; the cartesian product with the action pairs is tried and pruned.
        opp_switch_branches = _opponent_switch_in_actions(messages, state)
        crit_counts = message_crit_counts_with_state(messages, state)
        # Per-mover hit counts: index-aligned with movers; default 1.
        mover_hit_counts = _message_hit_counts_with_state(messages, state)
        opp_species = _active_species(state, 1)

        # Attacker slot assignments: one map for singles / distinct species; multiple when
        # same-species doubles attackers are ambiguous. Each map is a separate branch.
        slot_maps = _build_attacker_slot_maps(all_messages_flat, state)

        for sm_idx, slot_map in enumerate(slot_maps):
            # --- Slot-dependent: re-derived per attacker slot assignment -----------------
            # Extract known actions and validate against predicted AI probabilities.
            # An unexpected action filters this branch only; if all are filtered,
            # all_new_candidates stays empty and SimulationError fires below.
            try:
                known_actions = _extract_known_actions(messages, state, slot_map=slot_map)
            except UnreproducibleObservedMoveError as exc:
                print(
                    f"[sweep] candidate {c_idx + 1}/{len(initial_candidates)} "
                    f"slot_map {sm_idx + 1}/{len(slot_maps)} filtered — "
                    f"unreproducible observed move: {exc}",
                    flush=True,
                )
                continue
            try:
                _validate_known_opponent_action(known_actions, state)
                _validate_forced_opponent_switch(messages, state)
            except UnexpectedOpponentActionError as exc:
                print(
                    f"[sweep] candidate {c_idx + 1}/{len(initial_candidates)} "
                    f"slot_map {sm_idx + 1}/{len(slot_maps)} filtered — "
                    f"unexpected opponent action: {exc}",
                    flush=True,
                )
                continue

            try:
                candidates0, candidates1 = _sweep_resolve_candidate_actions(
                    state, messages, known_actions,
                    opponent_hp_deltas=opponent_hp_deltas,
                    player_hp_deltas=player_hp_deltas,
                    slot_map=slot_map,
                )
            except PostFaintMovePhaseError as exc:
                print(
                    f"[sweep] candidate {c_idx + 1}/{len(initial_candidates)} "
                    f"slot_map {sm_idx + 1}/{len(slot_maps)} filtered — "
                    f"post-faint/move-phase disagreement: {exc}",
                    flush=True,
                )
                continue

            # Extract move enums used each side (for secondary injection/classification)
            used_moves = _extract_used_moves_from_groups(
                action_groups, state, flat_messages=all_messages_flat, slot_map=slot_map
            )

            injected_overrides_0, injected_overrides_1, injected_pre, secondary_combos, self_hit_slots = (
                build_sweep_injected_overrides(all_messages_flat, state, used_moves, action_groups, slot_map=slot_map, hp_changed_by_slot=hp_changed_by_slot)
            )

            # Fan-out safety valve: the total branch count for this slot_map must stay
            # within the cap, else the combinatorics could blow up. Fail loud naming the
            # contributing factors rather than silently exploding.
            n_combos = (
                len(slot_maps) * len(candidates0) * len(candidates1)
                * len(opp_switch_branches) * max(1, len(secondary_combos))
            )
            if n_combos > _SWEEP_BRANCH_CAP:
                raise SimulationError(
                    reason=(
                        f"Candidate sweep branch count {n_combos} exceeds cap "
                        f"{_SWEEP_BRANCH_CAP}: slot_maps={len(slot_maps)} "
                        f"candidates0={len(candidates0)} candidates1={len(candidates1)} "
                        f"opp_switch_branches={len(opp_switch_branches)} "
                        f"secondary_combos={len(secondary_combos)}"
                    )
                )

            n_pairs = len(candidates0) * len(candidates1) * len(opp_switch_branches)
            print(
                f"[sweep] candidate {c_idx + 1}/{len(initial_candidates)} "
                f"slot_map {sm_idx + 1}/{len(slot_maps)}: "
                f"{len(candidates0)}×{len(candidates1)} pairs × "
                f"{len(opp_switch_branches)} switch-in branches × "
                f"{len(secondary_combos)} secondary combos",
                flush=True,
            )

            # Use observed move order as the mover list; tie_winner is first mover's side
            movers = _message_action_order_with_state(messages, state, slot_map=slot_map)  # list[tuple[int,int]]

            # No detected movers (battle intro / pure switch / post-faint) flows through the
            # normal path: the mover loop iterates zero times and candidates are filtered by
            # HP deltas, action order, and log events (including faint identity/ordering).
            tie_winner = movers[0][0] if movers else 0

            # Log active-mon speeds for diagnosing order failures
            def _mon_summary(side_idx: int) -> str:
                side = state.sides[side_idx]
                idx = side.active_indices[0] if side.active_indices else 0
                mon = side.team[idx] if idx < len(side.team) else None
                if mon is None:
                    return "?"
                return f"{mon.species.name} lv{mon.level} spe={mon.stats[5]}"

            n_crits = sum(crit_counts) if crit_counts else 0
            print(
                f"[sweep]   mover_hit_counts={mover_hit_counts} crits={n_crits}  "
                f"tie_winner={tie_winner}  movers={movers}  "
                f"opp_max_hp={opponent_max_hp}\n"
                f"[sweep]   p0={_mon_summary(0)}  p1={_mon_summary(1)}",
                flush=True,
            )

            pair_idx = 0
            for action0 in candidates0:
                for action1 in candidates1:
                    for opp_switch_actions in opp_switch_branches:
                        pair_idx += 1
                        all_new_candidates.extend(
                            _sweep_evaluate_pairs(
                                state, action0, action1,
                                secondary_combos,
                                injected_overrides_0, injected_overrides_1, injected_pre,
                                all_messages_flat, opponent_hp_deltas, player_hp_deltas,
                                initial_candidate, seen_states,
                                tie_winner, crit_counts, movers, opp_species,
                                mover_hit_counts, opponent_max_hp,
                                pair_idx, n_pairs,
                                hp_deltas,
                                opp_switch_actions,
                                self_hit_slots=self_hit_slots,
                            )
                        )

    elapsed = time.time() - t_start
    print(
        f"[sweep] done in {elapsed:.1f}s — {len(all_new_candidates)} candidate(s) survived",
        flush=True,
    )
    if not all_new_candidates:
        raise SimulationError(messages, hp_deltas, initial_candidates)
    return all_new_candidates
