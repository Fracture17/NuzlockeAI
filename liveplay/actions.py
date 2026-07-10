# Action dataclass, legal action enumeration, and grounding helper for a single side. Engine-free.
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from liveplay.state.battle import BattleState, PseudoWeather
from liveplay.state.pokemon import Volatile, VolatileEffect, PokemonState
from liveplay.data.moves import Move, MOVE_DATA, MoveCategory, GRAVITY_BLOCKED_MOVES
from liveplay.data.items import Item
from liveplay.data.abilities import Ability, MOLD_BREAKER_ABILITIES as _MOLD_BREAKER_ABILITIES
from liveplay.data.types import Type
from liveplay.data.mega import MEGA_DATA

# Sentinel move_slot for the forced Struggle action. Distinct from recharge (-1) so
# every `move_slot == -1` / `< 0` site that means "recharge" stays unambiguous and any
# unhandled Struggle site fails loudly rather than being mis-read as a recharge. The
# move itself is carried by move_override=Move.STRUGGLE.
STRUGGLE_SLOT = -2


class ActionKind(IntEnum):
    MOVE = 0
    SWITCH = 1


@dataclass
class Action:
    kind: ActionKind     # MOVE or SWITCH
    move_slot: int = -1  # -1 = recharge (no real move chosen)
    target_slot: int = 0 # for doubles: which opponent slot to target
    switch_to_slot: int = -1
    mega: bool = False
    move_override: Optional[object] = None  # sub-move override (Metronome, Sleep Talk, Assist); Move enum in practice
    source_slot: int = 0    # which active slot within the side this action comes from (0 or 1)
    target_side: int = -1   # for ANY-targeting: 0=own side, 1=foe side, -1=default foe side


def _is_grounded(pokemon: PokemonState, state: BattleState) -> bool:
    """Returns True if the Pokemon is grounded (affected by terrain/hazards/gravity).
    GROUNDED volatile (Thousand Arrows/Smack Down) forces grounded regardless of type/ability."""
    if any(pw == PseudoWeather.GRAVITY for pw, _ in state.pseudo_weather):
        return True
    # Iron Ball grounds the holder even if Flying-type or Levitate
    if pokemon.item == Item.IRON_BALL:
        return True
    # GROUNDED volatile (from Thousand Arrows or Smack Down) always grounds
    if any(ve == VolatileEffect.GROUNDED for ve, _ in pokemon.timed_volatiles):
        return True
    if Type.FLYING in pokemon.types:
        return False
    if pokemon.ability == Ability.LEVITATE:
        return False
    if pokemon.item == Item.AIR_BALLOON:
        return False
    if any(ve == VolatileEffect.MAGNET_RISE for ve, _ in pokemon.timed_volatiles):
        return False
    if any(ve == VolatileEffect.TELEKINESIS for ve, _ in pokemon.timed_volatiles):
        return False
    return True


def _struggle_action() -> "Action":
    """The forced Struggle action used when a side has a move-phase but no usable move."""
    return Action(kind=ActionKind.MOVE, move_slot=STRUGGLE_SLOT, move_override=Move.STRUGGLE)


def enumerate_legal_actions(state: BattleState, side_idx: int, slot: int = 0) -> list[Action]:
    """Returns all Actions the active Pokemon on the given side may legally take this turn."""
    side = state.sides[side_idx]
    active_idx = side.active_indices[slot]
    pokemon = side.team[active_idx]

    if pokemon.volatiles & Volatile.RECHARGING:
        return [Action(kind=ActionKind.MOVE, move_slot=-1)]

    # Mid two-turn move (Bounce/Fly/Dig/Solar Beam etc.): the attack turn is forced
    # to complete the charging move. This overrides Choice lock, PP (already spent on
    # the charge turn), and switching — a charging mon cannot do anything else.
    if pokemon.charging_move_slot >= 0:
        return [Action(kind=ActionKind.MOVE, move_slot=pokemon.charging_move_slot)]

    if pokemon.volatiles & Volatile.LOCKED_MOVE:
        return [Action(kind=ActionKind.MOVE, move_slot=pokemon.locked_slot)]

    if pokemon.volatiles & Volatile.ENCORE_ACTIVE:
        return [Action(kind=ActionKind.MOVE, move_slot=pokemon.locked_slot)]

    if pokemon.volatiles & Volatile.CHOICE_LOCKED:
        locked_move_actions = []
        if pokemon.move_pp[pokemon.locked_slot] > 0:
            locked_move_actions.append(Action(kind=ActionKind.MOVE, move_slot=pokemon.locked_slot))
        switch_actions = [
            Action(kind=ActionKind.SWITCH, switch_to_slot=i)
            for i, member in enumerate(side.team)
            if i != active_idx and not member.fainted
        ]
        # Locked move out of PP → forced Struggle (in addition to any legal switch).
        if not locked_move_actions:
            locked_move_actions.append(_struggle_action())
        return locked_move_actions + switch_actions

    # Under Gravity, airborne/levitation moves (Fly, Bounce, High Jump Kick, Magnet Rise, ...)
    # are unselectable. Filtering them here (rather than letting them fail at execution) keeps
    # them out of the legal set, so a mon whose only PP-positive moves are all gravity-blocked
    # falls through to the forced-Struggle branch instead of looping on a move that fails
    # without spending PP. Matches the Taunt/Assault-Vest selection-block pattern below.
    gravity_active = any(pw == PseudoWeather.GRAVITY for pw, _ in state.pseudo_weather)

    actions = []
    for move_slot, (move, pp) in enumerate(zip(pokemon.move_ids, pokemon.move_pp)):
        if pp <= 0:
            continue
        if gravity_active and move in GRAVITY_BLOCKED_MOVES:
            continue
        if (pokemon.volatiles & Volatile.TAUNT_ACTIVE
                and move in MOVE_DATA
                and MOVE_DATA[move].category == MoveCategory.STATUS):
            continue
        if (pokemon.item == Item.ASSAULT_VEST
                and move in MOVE_DATA
                and MOVE_DATA[move].category == MoveCategory.STATUS):
            continue
        actions.append(Action(kind=ActionKind.MOVE, move_slot=move_slot))

    # BOUND or TRAPPED: prevent voluntary switching (Shed Shell only bypasses BOUND)
    bound = any(e == VolatileEffect.BOUND for e, _ in pokemon.timed_volatiles)
    trapped = any(e == VolatileEffect.TRAPPED for e, _ in pokemon.timed_volatiles)

    opp_side = state.sides[1 - side_idx]
    _mold_breaker_active = pokemon.ability in _MOLD_BREAKER_ABILITIES
    _shed_shell = pokemon.item == Item.SHED_SHELL
    _is_steel = Type.STEEL in pokemon.types

    # Check all active non-fainted opponents for trapping abilities
    opp_active_mons = [opp_side.team[i] for i in opp_side.active_indices if not opp_side.team[i].fainted]

    # Shadow Tag: traps all non-Ghost unless holder also has Shadow Tag or has Shed Shell
    shadow_tag_trapped = any(
        m.ability == Ability.SHADOW_TAG
        and Type.GHOST not in pokemon.types
        and not _shed_shell
        and pokemon.ability != Ability.SHADOW_TAG
        and not _mold_breaker_active
        for m in opp_active_mons
    )
    # Magnet Pull: traps any Steel-type (including dual-types like Flying/Steel)
    magnet_pull_trapped = any(
        m.ability == Ability.MAGNET_PULL
        and _is_steel
        and not _shed_shell
        and not _mold_breaker_active
        for m in opp_active_mons
    )
    # Arena Trap: traps grounded Pokemon; Ghost types are always immune (gen 6+ rule)
    arena_trap_trapped = any(
        m.ability == Ability.ARENA_TRAP
        and _is_grounded(pokemon, state)
        and Type.GHOST not in pokemon.types
        and not _shed_shell
        and not _mold_breaker_active
        for m in opp_active_mons
    )

    ability_trapped = shadow_tag_trapped or magnet_pull_trapped or arena_trap_trapped
    # Shed Shell bypasses BOUND but not move-based TRAPPED or ability trapping
    can_switch = (not trapped and not ability_trapped) and (not bound or _shed_shell)
    if can_switch:
        for i, member in enumerate(side.team):
            if i == active_idx:
                continue
            if member.fainted:
                continue
            actions.append(Action(kind=ActionKind.SWITCH, switch_to_slot=i))

    can_mega = (
        pokemon.item in MEGA_DATA
        and not pokemon.is_mega
        and not side.mega_used
    )
    if can_mega:
        mega_variants = [
            Action(kind=ActionKind.MOVE, move_slot=a.move_slot, mega=True)
            for a in actions if a.kind == ActionKind.MOVE
        ]
        actions.extend(mega_variants)

    # No usable move (every slot out of PP, or only Taunt/Assault-Vest-blocked status
    # moves remain) → the side is forced to Struggle. Appended AFTER the mega block so
    # Struggle never spawns a mega variant; switches remain available alongside it.
    if not any(a.kind == ActionKind.MOVE for a in actions):
        actions.append(_struggle_action())

    return actions
