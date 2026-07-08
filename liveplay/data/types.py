# Type enum and effectiveness chart for Gen 8. Includes TYPELESS sentinel (index 18).
# Showdown damageTaken values: 0=neutral(1x), 1=super(2x), 2=resist(0.5x), 3=immune(0x).
# TYPELESS mirrors Showdown's '???' type: always 1.0x on attack and defense.

from enum import IntEnum


class Type(IntEnum):
    NORMAL = 0
    FIRE = 1
    WATER = 2
    ELECTRIC = 3
    GRASS = 4
    ICE = 5
    FIGHTING = 6
    POISON = 7
    GROUND = 8
    FLYING = 9
    PSYCHIC = 10
    BUG = 11
    ROCK = 12
    GHOST = 13
    DRAGON = 14
    DARK = 15
    STEEL = 16
    FAIRY = 17
    TYPELESS = 18  # Sentinel: Struggle's type, and Burn Up user after losing last Fire slot.


# Source: Showdown typechart.ts — damageTaken[AttackingType] value for each defending type.
_DT_MULT: dict[int, float] = {0: 1.0, 1: 2.0, 2: 0.5, 3: 0.0}

_DT_RAW: dict[str, dict[str, int]] = {
    "Normal":   {"Normal":0,"Fire":0,"Water":0,"Electric":0,"Grass":0,"Ice":0,"Fighting":1,"Poison":0,"Ground":0,"Flying":0,"Psychic":0,"Bug":0,"Rock":0,"Ghost":3,"Dragon":0,"Dark":0,"Steel":0,"Fairy":0},
    "Fire":     {"Normal":0,"Fire":2,"Water":1,"Electric":0,"Grass":2,"Ice":2,"Fighting":0,"Poison":0,"Ground":1,"Flying":0,"Psychic":0,"Bug":2,"Rock":1,"Ghost":0,"Dragon":0,"Dark":0,"Steel":2,"Fairy":2},
    "Water":    {"Normal":0,"Fire":2,"Water":2,"Electric":1,"Grass":1,"Ice":2,"Fighting":0,"Poison":0,"Ground":0,"Flying":0,"Psychic":0,"Bug":0,"Rock":0,"Ghost":0,"Dragon":0,"Dark":0,"Steel":2,"Fairy":0},
    "Electric": {"Normal":0,"Fire":0,"Water":0,"Electric":2,"Grass":0,"Ice":0,"Fighting":0,"Poison":0,"Ground":1,"Flying":2,"Psychic":0,"Bug":0,"Rock":0,"Ghost":0,"Dragon":0,"Dark":0,"Steel":2,"Fairy":0},
    "Grass":    {"Normal":0,"Fire":1,"Water":2,"Electric":2,"Grass":2,"Ice":1,"Fighting":0,"Poison":1,"Ground":2,"Flying":1,"Psychic":0,"Bug":1,"Rock":0,"Ghost":0,"Dragon":0,"Dark":0,"Steel":0,"Fairy":0},
    "Ice":      {"Normal":0,"Fire":1,"Water":0,"Electric":0,"Grass":0,"Ice":2,"Fighting":1,"Poison":0,"Ground":0,"Flying":0,"Psychic":0,"Bug":0,"Rock":1,"Ghost":0,"Dragon":0,"Dark":0,"Steel":1,"Fairy":0},
    "Fighting": {"Normal":0,"Fire":0,"Water":0,"Electric":0,"Grass":0,"Ice":0,"Fighting":0,"Poison":0,"Ground":0,"Flying":1,"Psychic":1,"Bug":2,"Rock":2,"Ghost":0,"Dragon":0,"Dark":2,"Steel":0,"Fairy":1},
    "Poison":   {"Normal":0,"Fire":0,"Water":0,"Electric":0,"Grass":2,"Ice":0,"Fighting":2,"Poison":2,"Ground":1,"Flying":0,"Psychic":1,"Bug":2,"Rock":0,"Ghost":0,"Dragon":0,"Dark":0,"Steel":0,"Fairy":2},
    "Ground":   {"Normal":0,"Fire":0,"Water":1,"Electric":3,"Grass":1,"Ice":1,"Fighting":0,"Poison":2,"Ground":0,"Flying":0,"Psychic":0,"Bug":0,"Rock":2,"Ghost":0,"Dragon":0,"Dark":0,"Steel":0,"Fairy":0},
    "Flying":   {"Normal":0,"Fire":0,"Water":0,"Electric":1,"Grass":2,"Ice":1,"Fighting":2,"Poison":0,"Ground":3,"Flying":0,"Psychic":0,"Bug":2,"Rock":1,"Ghost":0,"Dragon":0,"Dark":0,"Steel":0,"Fairy":0},
    "Psychic":  {"Normal":0,"Fire":0,"Water":0,"Electric":0,"Grass":0,"Ice":0,"Fighting":2,"Poison":0,"Ground":0,"Flying":0,"Psychic":2,"Bug":1,"Rock":0,"Ghost":1,"Dragon":0,"Dark":1,"Steel":0,"Fairy":0},
    "Bug":      {"Normal":0,"Fire":1,"Water":0,"Electric":0,"Grass":2,"Ice":0,"Fighting":2,"Poison":0,"Ground":2,"Flying":1,"Psychic":0,"Bug":0,"Rock":1,"Ghost":0,"Dragon":0,"Dark":0,"Steel":0,"Fairy":0},
    "Rock":     {"Normal":2,"Fire":2,"Water":1,"Electric":0,"Grass":1,"Ice":0,"Fighting":1,"Poison":2,"Ground":1,"Flying":2,"Psychic":0,"Bug":0,"Rock":0,"Ghost":0,"Dragon":0,"Dark":0,"Steel":1,"Fairy":0},
    "Ghost":    {"Normal":3,"Fire":0,"Water":0,"Electric":0,"Grass":0,"Ice":0,"Fighting":3,"Poison":2,"Ground":0,"Flying":0,"Psychic":0,"Bug":2,"Rock":0,"Ghost":1,"Dragon":0,"Dark":1,"Steel":0,"Fairy":0},
    "Dragon":   {"Normal":0,"Fire":2,"Water":2,"Electric":2,"Grass":2,"Ice":1,"Fighting":0,"Poison":0,"Ground":0,"Flying":0,"Psychic":0,"Bug":0,"Rock":0,"Ghost":0,"Dragon":1,"Dark":0,"Steel":0,"Fairy":1},
    "Dark":     {"Normal":0,"Fire":0,"Water":0,"Electric":0,"Grass":0,"Ice":0,"Fighting":1,"Poison":0,"Ground":0,"Flying":0,"Psychic":3,"Bug":1,"Rock":0,"Ghost":2,"Dragon":0,"Dark":2,"Steel":0,"Fairy":1},
    "Steel":    {"Normal":2,"Fire":1,"Water":0,"Electric":0,"Grass":2,"Ice":2,"Fighting":1,"Poison":3,"Ground":1,"Flying":2,"Psychic":2,"Bug":2,"Rock":2,"Ghost":0,"Dragon":2,"Dark":0,"Steel":2,"Fairy":2},
    "Fairy":    {"Normal":0,"Fire":0,"Water":0,"Electric":0,"Grass":0,"Ice":0,"Fighting":2,"Poison":1,"Ground":0,"Flying":0,"Psychic":0,"Bug":2,"Rock":0,"Ghost":0,"Dragon":3,"Dark":2,"Steel":1,"Fairy":0},
}

# Build [attacking_idx][defending_idx] lookup table. Size 19 so TYPELESS (index 18)
# row and column default to 1.0 — the real 18x18 data is untouched.
_TYPE_CHART: list[list[float]] = [[1.0] * 19 for _ in range(19)]
for _def_name, _atk_map in _DT_RAW.items():
    _def_idx = Type[_def_name.upper()].value
    for _atk_name, _dt_val in _atk_map.items():
        _atk_idx = Type[_atk_name.upper()].value
        _TYPE_CHART[_atk_idx][_def_idx] = _DT_MULT[_dt_val]


def type_effectiveness(attacking: Type, defending: Type) -> float:
    """Returns the damage multiplier: 0.0, 0.5, 1.0, or 2.0."""
    return _TYPE_CHART[attacking.value][defending.value]
