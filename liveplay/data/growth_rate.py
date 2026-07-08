# Growth rate enum and EXP threshold function. Curves ported from Gen III/VI Lua reference.
import math
from enum import IntEnum


class GrowthRate(IntEnum):
    MEDIUM_FAST  = 0
    ERRATIC      = 1
    FLUCTUATING  = 2
    MEDIUM_SLOW  = 3
    FAST         = 4
    SLOW         = 5


def exp_for_level(growth_rate: GrowthRate, level: int) -> int:
    """Return total EXP required to reach `level` for the given growth rate."""
    n = level
    if growth_rate == GrowthRate.MEDIUM_FAST:
        result = n ** 3
    elif growth_rate == GrowthRate.ERRATIC:
        if n <= 50:
            result = math.floor(((100 - n) * n ** 3) / 50)
        elif n <= 68:
            result = math.floor(((150 - n) * n ** 3) / 100)
        elif n <= 98:
            result = math.floor(math.floor((1911 - 10 * n) / 3) * n ** 3 / 500)
        else:
            result = math.floor((160 - n) * n ** 3 / 100)
    elif growth_rate == GrowthRate.FLUCTUATING:
        if n < 15:
            result = math.floor((math.floor((n + 1) / 3) + 24) * n ** 3 / 50)
        elif n <= 36:
            result = math.floor((n + 14) * n ** 3 / 50)
        else:
            result = math.floor((math.floor(n / 2) + 32) * n ** 3 / 50)
    elif growth_rate == GrowthRate.MEDIUM_SLOW:
        result = math.floor(6 * n ** 3 / 5) - 15 * n ** 2 + 100 * n - 140
    elif growth_rate == GrowthRate.FAST:
        result = math.floor(4 * n ** 3 / 5)
    elif growth_rate == GrowthRate.SLOW:
        result = math.floor(5 * n ** 3 / 4)
    else:
        raise ValueError(f"Unknown growth rate: {growth_rate}")
    return max(0, result)


def level_from_exp(growth_rate: GrowthRate, experience: int) -> int:
    """Return the level for total accumulated EXP (inverse of exp_for_level).

    Used for box pokemon, whose level is not stored in memory and must be
    reconstructed from experience."""
    if experience < 0:
        raise ValueError(f"experience must be non-negative, got {experience}")
    level = 1
    for candidate in range(2, 101):
        if exp_for_level(growth_rate, candidate) > experience:
            break
        level = candidate
    return level
