# Identity-bound HP change record for a single mon in a single turn.
from dataclasses import dataclass
from typing import Optional
from liveplay.data.species import Species


@dataclass(frozen=True)
class HpDeltaSeq:
    """One mon's observed HP-change sequence in a single turn, bound to its identity.

    side:    0 = player, 1 = opponent.
    species: identity key — the delta is validated against the result-state mon of this species.
    slot:    active-slot position the mon occupied while these deltas occurred (singles: always 0).
    deltas:  ordered (before, after) pairs. Player side: exact HP ints. Opponent side: k-pixel values.
    max_hp:  the mon's max HP. Used for the opponent k-pixel→HP range check; ignored for the player.
    """
    side: int
    species: Species
    slot: int
    deltas: tuple
    max_hp: int


def build_faint_record_from_klog(
    klog: list, species: Species, max_hp: int, *, side: int = 1, slot: int = 0,
) -> Optional["HpDeltaSeq"]:
    """Bind a fainted foe's accumulated k-pixel HP log into an HpDeltaSeq.

    Called at the opponent send-out reset (SCRIPTS/play.py), BEFORE the dead mon's
    name-keyed k-log is cleared for a replacement. Necessary because the opponent
    log is keyed by species name: a SAME-NAME replacement (e.g. a 2nd Magikarp)
    otherwise wipes the fainted mon's readings before the end-of-turn sweep builds
    its record, leaving the sweep with no HP constraint on the killing move (Issue 29).

    Truncates at the faint (the first k=0): the dead mon's trajectory ends when its
    bar empties. Any reading after the 0 belongs to the replacement (whose full bar
    may already have been appended under the shared name key) and must not be folded
    into the dead mon's record — that would create a bogus 0→full "heal" delta.

    Returns None when fewer than two readings remain (no trajectory to record).
    """
    if 0 in klog:
        readings = list(klog[: klog.index(0) + 1])
    else:
        readings = list(klog)
    if len(readings) < 2:
        return None
    return HpDeltaSeq(
        side=side, species=species, slot=slot,
        deltas=tuple(zip(readings, readings[1:])), max_hp=max_hp,
    )
