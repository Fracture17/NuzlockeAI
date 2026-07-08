"""Pure state builders and assertion helpers for battle tests.

Extracted from the old repo's tests/battle_harness.py (Stage C migration):
everything here is engine-free — no Simulator, no sim_helpers. The
Simulator-dependent harness half (make_sim, run_turn, capture_turn,
capture_battle) stays in the old repo until the Stage E sweep re-point.

Quick pattern:
    muk     = make_mon(Species.MUK,     moves=(Move.SLUDGE_BOMB,))
    corsola = make_mon(Species.CORSOLA, moves=(Move.SPLASH,))
    state   = make_battle(muk, corsola)
"""
from liveplay.hp_delta import HpDeltaSeq
from liveplay.logger import CapturingLogger, LogEvent  # noqa: F401 (re-export for tests)
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.moves import Move, MOVE_DATA
from liveplay.data.natures import Nature
from liveplay.data.species import Species
from liveplay.data.status import Status
from liveplay.actions import Action, ActionKind
from liveplay.rng import LuckProfile, GOOD_LUCK, BAD_LUCK, AVERAGE_LUCK, RNGEvent  # noqa: F401
from liveplay.state.battle import BattleState
from liveplay.state.pokemon import GenderEnum, PokemonState, Volatile  # noqa: F401
from liveplay.state.side import SideState

GOOD = GOOD_LUCK
BAD = BAD_LUCK
AVERAGE = AVERAGE_LUCK


def pdelta(species: Species, *pairs, slot: int = 0, max_hp: int = 0) -> HpDeltaSeq:
    """Player-side (exact HP) identity-bound record. pairs are (before, after) int tuples."""
    return HpDeltaSeq(side=0, species=species, slot=slot, deltas=tuple(pairs), max_hp=max_hp)


def odelta(species: Species, *pairs, max_hp: int, slot: int = 0) -> HpDeltaSeq:
    """Opponent-side (k-pixel) identity-bound record. pairs are (before, after) k-pixel tuples."""
    return HpDeltaSeq(side=1, species=species, slot=slot, deltas=tuple(pairs), max_hp=max_hp)


def make_mon(
    species,
    moves=None,
    ability=Ability.NONE,
    item=Item.NONE,
    level=50,
    nature=Nature.HARDY,
    ivs=(31,) * 6,
    hp=None,
    status=Status.NONE,
    stat_stages=None,
) -> PokemonState:
    """Construct a PokemonState with sensible defaults for battle tests."""
    if moves is None:
        moves = (Move.SPLASH, Move.NONE, Move.NONE, Move.NONE)

    # Pad moves tuple to 4 slots
    padded = tuple(moves) + (Move.NONE,) * (4 - len(moves))
    move_pp = tuple(MOVE_DATA[m].pp if m != Move.NONE else 0 for m in padded)

    mon = PokemonState(
        species=species,
        nature=nature,
        ivs=ivs,
        gender=GenderEnum.MALE,
        level=level,
        ability=ability,
        item=item,
        status=status,
        move_ids=padded,
        move_pp=move_pp,
    )

    if hp is not None:
        mon = mon._replace(hp=hp)
    if stat_stages is not None:
        mon = mon._replace(stat_stages=stat_stages)

    return mon


def make_battle(mon0, mon1, *, team0=None, team1=None) -> BattleState:
    """Construct a BattleState from two active Pokemon, with optional full teams."""
    t0 = team0 if team0 is not None else [mon0]
    t1 = team1 if team1 is not None else [mon1]
    side0 = SideState(team=t0, active_indices=[0])
    side1 = SideState(team=t1, active_indices=[0])
    return BattleState(sides=(side0, side1))


def make_doubles_battle(mon0a, mon0b, mon1a, mon1b, *, team0=None, team1=None) -> BattleState:
    """Construct a doubles BattleState with two active mons per side.

    side 0 = player (mon0a active index 0, mon0b active index 1)
    side 1 = AI    (mon1a active index 0, mon1b active index 1)
    """
    from liveplay.state.side import FormatEnum
    t0 = team0 if team0 is not None else [mon0a, mon0b]
    t1 = team1 if team1 is not None else [mon1a, mon1b]
    side0 = SideState(team=t0, active_indices=[0, 1], format=FormatEnum.DOUBLES)
    side1 = SideState(team=t1, active_indices=[0, 1], format=FormatEnum.DOUBLES)
    return BattleState(sides=(side0, side1), format=FormatEnum.DOUBLES)


def slot(n: int, *, target=0) -> Action:
    """Return a move action for the given slot index."""
    return Action(kind=ActionKind.MOVE, move_slot=n, target_slot=target)


def dslot(n: int, *, target=0, source=0) -> Action:
    """Move action for a doubles slot: move_slot n, targeting opp slot `target`, acting from own slot `source`."""
    return Action(kind=ActionKind.MOVE, move_slot=n, target_slot=target, source_slot=source)


def switch_to(n: int) -> Action:
    """Return a switch action for the given team slot index."""
    return Action(kind=ActionKind.SWITCH, switch_to_slot=n)


def _active(state: BattleState, side: int) -> PokemonState:
    """Get the active Pokemon on the given side."""
    s = state.sides[side]
    return s.team[s.active_indices[0]]


active = _active  # public alias


def assert_hp(state: BattleState, side: int, expected: int) -> None:
    """Assert the active Pokemon's HP equals expected."""
    actual = _active(state, side).hp
    assert actual == expected, f"Side {side} HP: expected {expected}, got {actual}"


def assert_hp_range(state: BattleState, side: int, lo: int, hi: int) -> None:
    """Assert the active Pokemon's HP is in [lo, hi] inclusive."""
    actual = _active(state, side).hp
    assert lo <= actual <= hi, f"Side {side} HP: expected {lo}–{hi}, got {actual}"


def assert_status(state: BattleState, side: int, expected: Status) -> None:
    """Assert the active Pokemon's status equals expected."""
    actual = _active(state, side).status
    assert actual == expected, f"Side {side} status: expected {expected.name}, got {actual.name}"


def assert_stages(state: BattleState, side: int, expected: dict) -> None:
    """Check stat stages. expected is {stat_idx: value}. Stat indices: 0=Atk 1=Def 2=SpA 3=SpD 4=Spe 5=Acc 6=Eva."""
    stages = _active(state, side).stat_stages
    for idx, val in expected.items():
        assert stages[idx] == val, f"Side {side} stage[{idx}]: expected {val}, got {stages[idx]}"


def assert_fainted(state: BattleState, side: int) -> None:
    """Assert the active Pokemon has fainted."""
    assert _active(state, side).fainted, f"Side {side} should be fainted but is not"


def assert_not_fainted(state: BattleState, side: int) -> None:
    """Assert the active Pokemon has not fainted."""
    assert not _active(state, side).fainted, f"Side {side} should not be fainted but is"


def assert_damage(state: BattleState, side: int, mon: PokemonState, expected: int) -> None:
    """Assert that the active Pokemon took exactly `expected` damage from its starting HP.

    `mon` should be the PokemonState before the turn (to read max_hp / starting hp).
    """
    actual_hp = _active(state, side).hp
    actual_damage = mon.max_hp - actual_hp
    assert actual_damage == expected, (
        f"Side {side} damage: expected {expected}, got {actual_damage} "
        f"(HP {actual_hp}/{mon.max_hp}, diff {actual_damage - expected:+d})"
    )


def assert_item(state: BattleState, side: int, expected: Item) -> None:
    """Assert the active Pokemon holds the given item."""
    actual = _active(state, side).item
    assert actual == expected, (
        f"Side {side} item: expected {expected.name}, got {actual.name}"
    )


def assert_volatile(state: BattleState, side: int, flag: int, *, present: bool = True) -> None:
    """Assert a Volatile flag is (or is not) set on the active Pokemon.

    Use Volatile.PROTECT_ACTIVE, Volatile.FLINCHED, etc. as the flag argument.
    Pass present=False to assert the flag is absent.
    """
    has = bool(_active(state, side).volatiles & flag)
    if present:
        assert has, f"Side {side} should have volatile flag {flag!r} but does not"
    else:
        assert not has, f"Side {side} should not have volatile flag {flag!r} but does"


def _matches(kwargs: dict, filters: dict) -> bool:
    return all(kwargs.get(k) == v for k, v in filters.items())


def _fmt_events(logger) -> str:
    lines = [f"  {ev.name}({kw})" for ev, kw in logger.events]
    return "\n".join(lines) if lines else "  (no events)"


def assert_event(logger, event_type, **expected_kwargs):
    """Assert at least one event of the given type matches all expected kwargs."""
    matches = logger.all_of(event_type, **expected_kwargs)
    if not matches:
        raise AssertionError(
            f"Expected {event_type.name}({expected_kwargs}) but no matching event found.\n"
            f"Events:\n{_fmt_events(logger)}"
        )


def assert_no_event(logger, event_type, **filters):
    """Assert no event of the given type (with optional kwargs filter) was fired."""
    matches = logger.all_of(event_type, **filters) if filters else logger.of(event_type)
    if matches:
        raise AssertionError(
            f"Expected no {event_type.name}({filters}) but found {len(matches)} match(es): {matches}\n"
            f"Events:\n{_fmt_events(logger)}"
        )


def assert_event_count(logger, event_type, expected_count, **filters):
    """Assert exactly expected_count events of the given type (with optional filter) were fired."""
    actual = logger.count(event_type, **filters)
    if actual != expected_count:
        raise AssertionError(
            f"Expected {expected_count} {event_type.name}({filters}) events, got {actual}.\n"
            f"Events:\n{_fmt_events(logger)}"
        )


def assert_event_sequence(logger, *event_specs):
    """Assert each spec appears in order (non-contiguous subsequence).

    Each spec is a bare LogEvent or a (LogEvent, dict) tuple for partial kwargs matching.
    """
    remaining = list(logger.events)
    for spec in event_specs:
        if isinstance(spec, tuple):
            ev_type, filters = spec
        else:
            ev_type, filters = spec, {}
        found = False
        for i, (ev, kw) in enumerate(remaining):
            if ev == ev_type and _matches(kw, filters):
                remaining = remaining[i + 1:]
                found = True
                break
        if not found:
            raise AssertionError(
                f"Event {ev_type.name}({filters}) not found in order.\n"
                f"Events:\n{_fmt_events(logger)}"
            )


def assert_event_sequence_exact(logger, *event_specs):
    """Assert specs appear as a contiguous subsequence of the event list.

    Each spec is a bare LogEvent or a (LogEvent, dict) tuple for partial kwargs matching.
    """
    events = logger.events
    specs = []
    for spec in event_specs:
        if isinstance(spec, tuple):
            specs.append(spec)
        else:
            specs.append((spec, {}))
    n = len(specs)
    for start in range(len(events) - n + 1):
        window = events[start:start + n]
        if all(ev == sp[0] and _matches(kw, sp[1]) for (ev, kw), sp in zip(window, specs)):
            return
    raise AssertionError(
        f"Event sequence {[s[0].name for s in specs]} not found as consecutive subsequence.\n"
        f"Events:\n{_fmt_events(logger)}"
    )
