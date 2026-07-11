# Roll/crit enumeration core for the vision-reconciliation sweep. Ports the per-mover
# damage-roll enumeration and per-turn phase loop from OLD src/simulation_runner.py.
# Pure leaf: imports only liveplay.* and stdlib. Returns (rolls, crits, BattleState, CapturingLogger)
# tuples; downstream callers (_sweep_evaluate_pairs) apply HP/log/action-order validation.
from __future__ import annotations

import itertools
from typing import Optional

from liveplay.candidate import PartialCandidate
from liveplay.hp_stability import hp_range
from liveplay.sweep_driver import (
    SideOverrides, SweepConfig,
    run_with_capture,
    _attacker_per_hit_damages,
    _self_hit_damage,
)
from liveplay.sweep_actions import _acting_action
from liveplay.sweep_reconcile import _check_action_order
from liveplay.rng import RNGEvent


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
