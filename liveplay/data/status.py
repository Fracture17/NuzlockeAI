# Non-volatile status condition enum used in PokemonState and move effects.
from enum import IntEnum


class Status(IntEnum):
    NONE = 0
    BURN = 1
    FREEZE = 2
    PARALYSIS = 3
    POISON = 4
    TOXIC = 5   # badly poisoned
    SLEEP = 6
