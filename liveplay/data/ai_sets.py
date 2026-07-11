# AI move/ability classification sets — Python source for SCRIPTS/gen_cpp_data.py.
#
# Ported verbatim from the old repo's src/ai.py (Stage E §5). The C++ AI
# (engine/src/ai_scorer*.cpp, via the generated engine/src/gen/ai_move_sets.h)
# is the runtime AUTHORITY; these sets exist only so gen_cpp_data.py can
# regenerate the header without importing from the retired repo. Any change
# here must be followed by re-running gen_cpp_data.py and the full parity gates.
from __future__ import annotations

from liveplay.data.abilities import Ability
from liveplay.data.moves import Move
from liveplay.state.battle import WeatherEnum

# Abilities that boost on KO (Moxie family)
MOXIE_ABILITIES: frozenset[Ability] = frozenset({
    Ability.MOXIE, Ability.BEAST_BOOST, Ability.CHILLING_NEIGH, Ability.GRIM_NEIGH,
})

HIGH_CRIT_MOVES: frozenset[Move] = frozenset({
    Move.AEROBLAST, Move.AIR_CUTTER, Move.ATTACK_ORDER, Move.BLAZE_KICK,
    Move.CRABHAMMER, Move.CROSS_CHOP, Move.CROSS_POISON, Move.DRILL_RUN,
    Move.KARATE_CHOP, Move.LEAF_BLADE, Move.NIGHT_SLASH, Move.POISON_TAIL,
    Move.PSYCHO_CUT, Move.RAZOR_LEAF, Move.RAZOR_WIND, Move.SHADOW_CLAW,
    Move.SKY_ATTACK, Move.SLASH, Move.SPACIAL_REND, Move.STONE_EDGE,
})

WEATHER_MOVE_TO_WEATHER: dict[Move, WeatherEnum] = {
    Move.SUNNY_DAY: WeatherEnum.SUNNY,
    Move.RAIN_DANCE: WeatherEnum.RAINY,
    Move.SANDSTORM: WeatherEnum.SANDSTORM,
    Move.HAIL: WeatherEnum.HAIL,
}

SPEED_REDUCTION_MOVES: frozenset[Move] = frozenset({
    Move.ICY_WIND, Move.ELECTROWEB, Move.ROCK_TOMB,
    Move.MUD_SHOT, Move.LOW_SWEEP, Move.BULLDOZE,
})

STAT_REDUCTION_DAMAGE_MOVES: frozenset[Move] = frozenset({
    Move.SKITTER_SMACK, Move.TROP_KICK, Move.SNARL,
    Move.MYSTICAL_FIRE, Move.BREAKING_SWIPE,
})

STAT_REDUCTION_ABILITIES: frozenset[Ability] = frozenset({
    Ability.CONTRARY, Ability.CLEAR_BODY, Ability.WHITE_SMOKE,
})

ROLE_PLAY_VALUABLE_ABILITIES: frozenset[Ability] = frozenset({
    Ability.HUGE_POWER, Ability.PURE_POWER, Ability.SPEED_BOOST,
    Ability.DROUGHT, Ability.DRIZZLE, Ability.SAND_STREAM, Ability.SNOW_WARNING,
})

# Setup moves that are not blocked by the opponent's Unaware ability
UNAWARE_SETUP_EXCEPTIONS: frozenset[Move] = frozenset({
    Move.SWORDS_DANCE, Move.POWER_UP_PUNCH, Move.HOWL,
})
