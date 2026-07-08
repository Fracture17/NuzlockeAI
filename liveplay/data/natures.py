# Nature enum, stat enum, and per-nature boost/lower data.
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class Stat(IntEnum):
    HP = 0
    ATK = 1
    DEF = 2
    SPA = 3
    SPD = 4
    SPE = 5


class Nature(IntEnum):
    HARDY = 0
    LONELY = 1
    BRAVE = 2
    ADAMANT = 3
    NAUGHTY = 4
    BOLD = 5
    DOCILE = 6
    RELAXED = 7
    IMPISH = 8
    LAX = 9
    TIMID = 10
    HASTY = 11
    SERIOUS = 12
    JOLLY = 13
    NAIVE = 14
    MODEST = 15
    MILD = 16
    QUIET = 17
    BASHFUL = 18
    RASH = 19
    CALM = 20
    GENTLE = 21
    SASSY = 22
    CAREFUL = 23
    QUIRKY = 24


@dataclass(frozen=True)
class NatureData:
    """Boosted and lowered stat for a nature; None for neutral natures."""
    boosted: Optional[Stat]
    lowered: Optional[Stat]

    @property
    def boost_multiplier(self) -> float:
        return 1.1 if self.boosted is not None else 1.0

    @property
    def lower_multiplier(self) -> float:
        return 0.9 if self.lowered is not None else 1.0


NATURE_DATA: dict[Nature, NatureData] = {
    Nature.HARDY:   NatureData(None, None),
    Nature.LONELY:  NatureData(Stat.ATK, Stat.DEF),
    Nature.BRAVE:   NatureData(Stat.ATK, Stat.SPE),
    Nature.ADAMANT: NatureData(Stat.ATK, Stat.SPA),
    Nature.NAUGHTY: NatureData(Stat.ATK, Stat.SPD),
    Nature.BOLD:    NatureData(Stat.DEF, Stat.ATK),
    Nature.DOCILE:  NatureData(None, None),
    Nature.RELAXED: NatureData(Stat.DEF, Stat.SPE),
    Nature.IMPISH:  NatureData(Stat.DEF, Stat.SPA),
    Nature.LAX:     NatureData(Stat.DEF, Stat.SPD),
    Nature.TIMID:   NatureData(Stat.SPE, Stat.ATK),
    Nature.HASTY:   NatureData(Stat.SPE, Stat.DEF),
    Nature.SERIOUS: NatureData(None, None),
    Nature.JOLLY:   NatureData(Stat.SPE, Stat.SPA),
    Nature.NAIVE:   NatureData(Stat.SPE, Stat.SPD),
    Nature.MODEST:  NatureData(Stat.SPA, Stat.ATK),
    Nature.MILD:    NatureData(Stat.SPA, Stat.DEF),
    Nature.QUIET:   NatureData(Stat.SPA, Stat.SPE),
    Nature.BASHFUL: NatureData(None, None),
    Nature.RASH:    NatureData(Stat.SPA, Stat.SPD),
    Nature.CALM:    NatureData(Stat.SPD, Stat.ATK),
    Nature.GENTLE:  NatureData(Stat.SPD, Stat.DEF),
    Nature.SASSY:   NatureData(Stat.SPD, Stat.SPE),
    Nature.CAREFUL: NatureData(Stat.SPD, Stat.SPA),
    Nature.QUIRKY:  NatureData(None, None),
}
