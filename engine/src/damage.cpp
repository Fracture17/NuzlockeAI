// C++ port of src/engine/damage.py. Mirrors Python operation-for-operation.
// All floor() calls match Python's math.floor(). Integer division matches Python's //.
// Constants are hardcoded from Python source; sets implemented as sorted arrays + binary search.
#include "damage.h"
#include "rng_resolver.h"       // rng_resolve_crit
#include "effects_internal.h"  // shared eff_internal::effective_weather
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <string>
#include <unordered_set>

// Include only move_data.h (which defines Type); type_chart in separate TU to avoid enum redefinition.
#include <move_data.h>
#include "type_chart_lookup.h"

// ---------------------------------------------------------------------------
// Enum integer constants (mirroring Python IntEnum values)
// ---------------------------------------------------------------------------

// Ability values
static constexpr int32_t AB_NONE            = 0;
static constexpr int32_t AB_FLASH_FIRE      = 18;
static constexpr int32_t AB_THICK_FAT       = 47;
static constexpr int32_t AB_HUSTLE          = 55;
static constexpr int32_t AB_GUTS            = 62;
static constexpr int32_t AB_MARVEL_SCALE    = 63;
static constexpr int32_t AB_OVERGROW        = 65;
static constexpr int32_t AB_BLAZE           = 66;
static constexpr int32_t AB_TORRENT         = 67;
static constexpr int32_t AB_SWARM           = 68;
static constexpr int32_t AB_AIR_LOCK        = 76;
static constexpr int32_t AB_SUPER_LUCK      = 105;
static constexpr int32_t AB_ADAPTABILITY    = 91;
static constexpr int32_t AB_SKILL_LINK      = 92;
static constexpr int32_t AB_SNIPER          = 97;
static constexpr int32_t AB_TECHNICIAN      = 101;
static constexpr int32_t AB_SAND_FORCE      = 159;
static constexpr int32_t AB_MOLD_BREAKER    = 104;
static constexpr int32_t AB_SCRAPPY         = 113;
static constexpr int32_t AB_HUGE_POWER      = 37;
static constexpr int32_t AB_PURE_POWER      = 74;
static constexpr int32_t AB_NORMALIZE       = 96;
static constexpr int32_t AB_PIXILATE        = 182;
static constexpr int32_t AB_REFRIGERATE     = 174;
static constexpr int32_t AB_AERILATE        = 184;
static constexpr int32_t AB_GALVANIZE       = 206;
static constexpr int32_t AB_LIQUID_VOICE    = 204;
static constexpr int32_t AB_UNAWARE         = 109;
static constexpr int32_t AB_SLOW_START      = 112;
static constexpr int32_t AB_TOXIC_BOOST     = 137;
static constexpr int32_t AB_GORILLA_TACTICS = 255;
static constexpr int32_t AB_SOLAR_POWER     = 94;
static constexpr int32_t AB_FLOWER_GIFT     = 122;
static constexpr int32_t AB_PLUS            = 57;
static constexpr int32_t AB_MINUS           = 58;
static constexpr int32_t AB_DEFEATIST       = 129;
static constexpr int32_t AB_FUR_COAT        = 169;
static constexpr int32_t AB_GRASS_PELT      = 179;
static constexpr int32_t AB_BATTLE_ARMOR    = 4;
static constexpr int32_t AB_SHELL_ARMOR     = 75;
static constexpr int32_t AB_MAGMA_ARMOR     = 40;
static constexpr int32_t AB_TURBOBLAZE      = 163;
static constexpr int32_t AB_TERAVOLT        = 164;
static constexpr int32_t AB_STRONG_JAW      = 173;
static constexpr int32_t AB_MEGA_LAUNCHER   = 178;
static constexpr int32_t AB_PUNK_ROCK       = 244;
static constexpr int32_t AB_SHEER_FORCE     = 125;
static constexpr int32_t AB_IRON_FIST       = 89;
static constexpr int32_t AB_SHARPNESS       = 292;
static constexpr int32_t AB_TOUGH_CLAWS     = 181;
static constexpr int32_t AB_RECKLESS        = 120;
static constexpr int32_t AB_WATER_BUBBLE    = 199;
static constexpr int32_t AB_STEELY_SPIRIT   = 252;
static constexpr int32_t AB_STEELWORKER     = 200;
static constexpr int32_t AB_TRANSISTOR      = 262;
static constexpr int32_t AB_DRAGON_S_MAW    = 263;
static constexpr int32_t AB_POWER_SPOT      = 249;
static constexpr int32_t AB_BATTERY         = 217;
static constexpr int32_t AB_TINTED_LENS     = 110;
static constexpr int32_t AB_NEUROFORCE      = 233;
static constexpr int32_t AB_FILTER          = 111;
static constexpr int32_t AB_SOLID_ROCK      = 116;
static constexpr int32_t AB_PRISM_ARMOR     = 232;
static constexpr int32_t AB_DARK_AURA       = 186;
static constexpr int32_t AB_FAIRY_AURA      = 187;
static constexpr int32_t AB_AURA_BREAK      = 188;
static constexpr int32_t AB_HEATPROOF       = 85;
static constexpr int32_t AB_DRY_SKIN        = 87;
static constexpr int32_t AB_MULTISCALE      = 136;
static constexpr int32_t AB_SHADOW_SHIELD   = 231;
static constexpr int32_t AB_ICE_SCALES      = 246;
static constexpr int32_t AB_FLUFFY          = 218;
static constexpr int32_t AB_LONG_REACH      = 203;
static constexpr int32_t AB_ANALYTIC        = 148;
static constexpr int32_t AB_FRIEND_GUARD    = 132;
static constexpr int32_t AB_INFILTRATOR     = 151;
static constexpr int32_t AB_MERCILESS       = 196;
static constexpr int32_t AB_CLOUD_NINE      = 13;
static constexpr int32_t AB_LEVITATE        = 26;
static constexpr int32_t AB_STICKY_HOLD     = 60;
static constexpr int32_t AB_PARENTAL_BOND   = 185;
static constexpr int32_t AB_BATTLE_BOND     = 210;

// Item values
static constexpr int32_t ITEM_NONE          = 0;
static constexpr int32_t ITEM_SCOPE_LENS    = 232;
static constexpr int32_t ITEM_RAZOR_CLAW    = 326;
static constexpr int32_t ITEM_LEEK          = 259;
static constexpr int32_t ITEM_IRON_BALL     = 278;
static constexpr int32_t ITEM_AIR_BALLOON   = 541;
static constexpr int32_t ITEM_LIFE_ORB      = 270;
static constexpr int32_t ITEM_EXPERT_BELT   = 268;
static constexpr int32_t ITEM_RING_TARGET   = 543;
static constexpr int32_t ITEM_PROTECTIVE_PADS = 880;
static constexpr int32_t ITEM_WISE_GLASSES  = 267;
static constexpr int32_t ITEM_MUSCLE_BAND   = 266;
static constexpr int32_t ITEM_GRISEOUS_ORB  = 112;
static constexpr int32_t ITEM_GRISEOUS_CORE = 1779;
static constexpr int32_t ITEM_LIGHT_BALL    = 236;
static constexpr int32_t ITEM_THICK_CLUB    = 260;
static constexpr int32_t ITEM_CHOICE_BAND   = 220;
static constexpr int32_t ITEM_CHOICE_SPECS  = 297;
static constexpr int32_t ITEM_EVIOLITE      = 538;
static constexpr int32_t ITEM_ASSAULT_VEST  = 640;

// Type values (matches Type enum in generated headers)
static constexpr int32_t TYPE_NORMAL   = 0;
static constexpr int32_t TYPE_FIRE     = 1;
static constexpr int32_t TYPE_WATER    = 2;
static constexpr int32_t TYPE_ELECTRIC = 3;
static constexpr int32_t TYPE_GRASS    = 4;
static constexpr int32_t TYPE_ICE      = 5;
static constexpr int32_t TYPE_FIGHTING = 6;
static constexpr int32_t TYPE_POISON   = 7;
static constexpr int32_t TYPE_GROUND   = 8;
static constexpr int32_t TYPE_FLYING   = 9;
static constexpr int32_t TYPE_PSYCHIC  = 10;
static constexpr int32_t TYPE_BUG      = 11;
static constexpr int32_t TYPE_ROCK     = 12;
static constexpr int32_t TYPE_GHOST    = 13;
static constexpr int32_t TYPE_DRAGON   = 14;
static constexpr int32_t TYPE_DARK     = 15;
static constexpr int32_t TYPE_STEEL    = 16;
static constexpr int32_t TYPE_FAIRY    = 17;
static constexpr int32_t TYPE_TYPELESS = 18;

// Weather values
// WeatherEnum values match Python's src/state/battle.py WeatherEnum ordering exactly.
static constexpr int32_t WEATHER_NONE        = 0;
static constexpr int32_t WEATHER_SUNNY       = 1;
static constexpr int32_t WEATHER_RAINY       = 2;
static constexpr int32_t WEATHER_SANDSTORM   = 3;
static constexpr int32_t WEATHER_HAIL        = 4;
static constexpr int32_t WEATHER_HEAVY_RAIN  = 5;
static constexpr int32_t WEATHER_HARSH_SUN   = 6;
static constexpr int32_t WEATHER_STRONG_WIND = 7;

// Terrain values
static constexpr int32_t TERRAIN_NONE     = 0;
static constexpr int32_t TERRAIN_ELECTRIC = 1;
static constexpr int32_t TERRAIN_GRASSY   = 2;
static constexpr int32_t TERRAIN_PSYCHIC  = 3;
static constexpr int32_t TERRAIN_MISTY    = 4;

// PseudoWeather values
static constexpr int32_t PW_GRAVITY    = 2;
static constexpr int32_t PW_MAGIC_ROOM = 3;
static constexpr int32_t PW_WONDER_ROOM= 4;

// SideCondition values
static constexpr int32_t SC_REFLECT     = 1;
static constexpr int32_t SC_LIGHT_SCREEN= 2;
static constexpr int32_t SC_AURORA_VEIL = 3;

// Status values
static constexpr int32_t STATUS_NONE     = 0;
static constexpr int32_t STATUS_BURN     = 1;
static constexpr int32_t STATUS_POISON   = 4;
static constexpr int32_t STATUS_TOXIC    = 5;

// Volatile bitmask values
static constexpr int32_t VOLATILE_FLASH_FIRE    = 1048576;
static constexpr int32_t VOLATILE_HELPING_HAND  = 33554432;
static constexpr int32_t VOLATILE_IDENTIFIED    = 134217728;

// VolatileEffect (timed_volatiles effect field) values
static constexpr int32_t VE_LASER_FOCUS       = 25;
static constexpr int32_t VE_GROUNDED          = 24;
static constexpr int32_t VE_SEMI_INVULNERABLE = 27;
static constexpr int32_t VE_CHARGING_MOVE = 34;  // payload: called-move id (effects_consts.h)
static constexpr int32_t VE_MAGNET_RISE       = 8;
static constexpr int32_t VE_TELEKINESIS       = 29;

// MoveCategory values
static constexpr int32_t CAT_PHYSICAL = 0;
static constexpr int32_t CAT_SPECIAL  = 1;
static constexpr int32_t CAT_STATUS   = 2;

// MoveTarget values
static constexpr int32_t TARGET_ALL_ADJACENT_FOES = 2;
static constexpr int32_t TARGET_ALL_ADJACENT      = 3;

// MoveTag bitmask values
static constexpr int32_t TAG_SOUND    = 256;
static constexpr int32_t TAG_BITING   = 2048;
static constexpr int32_t TAG_PULSE    = 1024;
static constexpr int32_t TAG_PUNCHING = 4096;
static constexpr int32_t TAG_SLICING  = 8192;
static constexpr int32_t TAG_CONTACT  = 128;

// Format value
static constexpr int32_t FORMAT_DOUBLES = 1;

// Move IDs (special-cased moves)
static constexpr int32_t MOVE_NONE            = 0;
static constexpr int32_t MOVE_EARTHQUAKE      = 89;
static constexpr int32_t MOVE_HIDDEN_POWER    = 237;
static constexpr int32_t MOVE_NATURAL_GIFT    = 363;
static constexpr int32_t MOVE_WEATHER_BALL    = 311;
static constexpr int32_t MOVE_TERRAIN_PULSE   = 805;
static constexpr int32_t MOVE_AURA_WHEEL      = 783;
static constexpr int32_t MOVE_MULTI_ATTACK    = 718;
static constexpr int32_t MOVE_REVELATION_DANCE= 686;
static constexpr int32_t MOVE_KNOCK_OFF       = 282;
static constexpr int32_t MOVE_BODY_PRESS      = 776;
static constexpr int32_t MOVE_FOUL_PLAY       = 492;
static constexpr int32_t MOVE_SHELL_SIDE_ARM  = 801;
static constexpr int32_t MOVE_PHOTON_GEYSER   = 722;
static constexpr int32_t MOVE_PSYSHOCK        = 473;
static constexpr int32_t MOVE_PSYSTRIKE       = 540;
static constexpr int32_t MOVE_SECRET_SWORD    = 548;
static constexpr int32_t MOVE_FLYING_PRESS    = 560;
static constexpr int32_t MOVE_FREEZE_DRY      = 573;
static constexpr int32_t MOVE_THOUSAND_ARROWS = 614;
static constexpr int32_t MOVE_FACADE          = 263;
static constexpr int32_t MOVE_BULLDOZE        = 523;
static constexpr int32_t MOVE_MAGNITUDE       = 222;
static constexpr int32_t MOVE_MISTY_EXPLOSION = 802;
static constexpr int32_t MOVE_SACRED_SWORD    = 533;
static constexpr int32_t MOVE_DARKEST_LARIAT  = 663;
static constexpr int32_t MOVE_CHIP_AWAY       = 498;
static constexpr int32_t MOVE_MOONGEIST_BEAM  = 714;
static constexpr int32_t MOVE_SUNSTEEL_STRIKE = 713;

// Species IDs
static constexpr int32_t SPECIES_MORPEKO_HANGRY = 1226;
static constexpr int32_t SPECIES_GIRATINA       = 487;
static constexpr int32_t SPECIES_GIRATINA_ORIGIN= 1071;
static constexpr int32_t SPECIES_GRENINJA_ASH   = 1113;

// ---------------------------------------------------------------------------
// Sorted constant sets (for fast membership tests via std::binary_search)
// ---------------------------------------------------------------------------

static const int32_t MOLD_BREAKER_ABILITIES[] = {104, 163, 164};
static constexpr int MB_COUNT = 3;

static const int32_t LEEK_SPECIES[]       = {83, 865, 979};
static const int32_t THICK_CLUB_SPECIES[] = {104, 105, 973};
static const int32_t PIKACHU_SPECIES[]    = {25, 1009, 1010, 1011, 1012, 1013, 1014, 1015, 1016, 1017, 1018, 1019, 1020, 1021, 1022};
static constexpr int PIKACHU_COUNT = 15;

// Silvally family species
static const int32_t SILVALLY_SPECIES[] = {773, 1176, 1177, 1178, 1179, 1180, 1181, 1182, 1183, 1184, 1185, 1186, 1187, 1188, 1189, 1190, 1191, 1192};
static constexpr int SILVALLY_COUNT = 18;

// Silvally Memory items
static const int32_t MEMORY_ITEMS[] = {901, 902, 903, 904, 905, 906, 907, 908, 909, 910, 911, 912, 913, 914, 915, 916, 917};
static constexpr int MEMORY_COUNT = 17;

// Mega items (cannot be knocked off)
static const int32_t MEGA_ITEMS[] = {
    40, 41, 573, 575, 576, 577, 578, 579, 580, 582, 583, 584, 585, 586, 587, 588, 589, 590, 591,
    592, 594, 596, 598, 599, 602, 605, 607, 608, 612, 613, 614, 615, 616, 617, 618, 619, 620,
    621, 622, 623, 625, 626, 627, 628, 629, 630
};
static constexpr int MEGA_COUNT = 46;

// Explosion-type moves
static const int32_t EXPLOSION_MOVES[] = {120, 153, 720, 802};  // EXPLOSION, SELF_DESTRUCT, MIND_BLOWN, MISTY_EXPLOSION

// Moves that bypass defender ability-based damage modifiers
static const int32_t IGNORE_ABILITY_MOVES[] = {713, 714, 722};  // SUNSTEEL_STRIKE, MOONGEIST_BEAM, PHOTON_GEYSER

// Ignore positive defensive stat stage moves
static const int32_t IGNORE_DEF_BOOST_MOVES[] = {498, 533, 663};  // CHIP_AWAY, SACRED_SWORD, DARKEST_LARIAT

// Reckless-boosted moves (recoil moves not in move_data.recoil)
static const int32_t RECKLESS_MOVES[] = {26, 36, 38, 66, 136, 344, 394, 413, 457, 528};

// Normalize no-boost moves
static const int32_t NORMALIZE_NO_BOOST[] = {311, 686};  // WEATHER_BALL, REVELATION_DANCE

// Unevolved species (493 entries, sorted)
static const int32_t UNEVOLVED_SPECIES[] = {
    1, 2, 4, 5, 7, 8, 10, 11, 13, 14, 16, 17, 19, 21, 23, 25, 27, 29, 30, 32, 33, 35, 37, 39,
    41, 42, 43, 44, 46, 48, 50, 52, 54, 56, 58, 60, 61, 63, 64, 66, 67, 69, 70, 72, 74, 75, 77,
    79, 81, 82, 83, 84, 86, 88, 90, 92, 93, 95, 96, 98, 100, 102, 104, 108, 109, 111, 112, 113,
    114, 116, 117, 118, 120, 123, 127, 129, 131, 133, 137, 138, 140, 142, 147, 148, 152, 153, 155,
    156, 158, 159, 161, 163, 165, 167, 170, 172, 173, 174, 175, 176, 177, 179, 180, 183, 187, 188,
    190, 191, 193, 194, 200, 203, 204, 206, 207, 209, 211, 213, 214, 215, 216, 218, 220, 221, 222,
    223, 225, 228, 231, 233, 234, 236, 238, 239, 240, 241, 246, 247, 252, 253, 255, 256, 258, 259,
    261, 263, 265, 266, 268, 270, 271, 273, 274, 276, 278, 280, 281, 283, 285, 287, 288, 290, 293,
    294, 296, 298, 299, 300, 302, 303, 304, 305, 307, 309, 311, 312, 313, 314, 315, 316, 318, 320,
    322, 325, 327, 328, 329, 331, 333, 335, 336, 337, 338, 339, 341, 343, 345, 347, 349, 351, 352,
    353, 355, 356, 357, 358, 359, 361, 363, 364, 366, 369, 370, 371, 372, 374, 375, 387, 388, 390,
    391, 393, 394, 396, 397, 399, 401, 403, 404, 406, 408, 410, 412, 415, 417, 418, 420, 422, 425,
    427, 431, 433, 434, 436, 438, 439, 440, 441, 442, 443, 444, 446, 447, 449, 451, 453, 455, 456,
    458, 459, 479, 495, 496, 498, 499, 501, 502, 504, 506, 507, 509, 519, 520, 522, 524, 525, 527,
    529, 532, 533, 535, 536, 538, 539, 540, 541, 543, 544, 546, 548, 550, 551, 552, 554, 556, 557,
    558, 559, 561, 562, 564, 566, 568, 570, 572, 574, 575, 577, 578, 580, 582, 583, 585, 587, 588,
    590, 592, 594, 595, 596, 597, 599, 600, 602, 603, 605, 607, 608, 610, 611, 613, 615, 616, 618,
    619, 621, 622, 624, 625, 626, 627, 629, 631, 632, 633, 634, 636, 637, 650, 651, 653, 654, 656,
    657, 661, 662, 664, 665, 667, 670, 672, 674, 677, 679, 680, 686, 688, 689, 690, 692, 694, 696,
    698, 701, 702, 703, 704, 705, 707, 708, 710, 712, 714, 722, 723, 725, 726, 728, 729, 731, 732,
    734, 736, 737, 742, 744, 746, 747, 749, 751, 753, 755, 757, 759, 761, 762, 767, 769, 775, 776,
    777, 778, 779, 780, 781, 782, 783, 810, 811, 813, 814, 816, 817, 819, 821, 822, 824, 825, 840,
    843, 845, 846, 848, 850, 851, 852, 854, 856, 857, 859, 860, 868, 870, 871, 872, 875, 876, 877,
    878, 880, 881, 882, 883, 885, 886, 956, 959, 961, 963, 965, 967, 968, 970, 974, 975, 977, 979,
    986, 987, 989, 991, 992, 993, 995, 998, 999, 1002, 1005, 1009, 1010, 1011, 1012, 1013, 1014,
    1015, 1016, 1017, 1018, 1019, 1020, 1021, 1022, 1023
};
static constexpr int UNEVOLVED_COUNT = 493;

// ---------------------------------------------------------------------------
// Natural Gift table: item_id -> (type_id, bp)
// ---------------------------------------------------------------------------
struct NGEntry { int32_t item; int8_t type; uint8_t bp; };
static const NGEntry NATURAL_GIFT_TABLE[] = {
    {149, 1, 60}, {150, 2, 60}, {151, 3, 60}, {152, 4, 60}, {153, 5, 60}, {154, 6, 60},
    {155, 7, 60}, {156, 8, 60}, {157, 9, 80}, {158, 10, 80}, {159, 1, 80}, {160, 2, 80},
    {161, 4, 80}, {162, 14, 80}, {163, 15, 80}, {184, 1, 80}, {185, 2, 80}, {186, 3, 80},
    {187, 4, 80}, {188, 5, 80}, {189, 6, 80}, {190, 7, 80}, {191, 8, 80}, {192, 9, 80},
    {193, 10, 80}, {194, 11, 80}, {195, 12, 80}, {196, 13, 80}, {197, 14, 80}, {198, 15, 80},
    {199, 16, 80}, {200, 0, 80}, {201, 4, 100}, {202, 5, 100}, {203, 6, 100}, {204, 7, 100},
    {205, 8, 100}, {206, 9, 100}, {207, 10, 100}, {208, 11, 100}, {209, 12, 100}, {210, 13, 100},
    {211, 14, 100}, {212, 15, 100}, {686, 17, 80}, {687, 17, 100}, {688, 15, 100},
};
static constexpr int NG_COUNT = 47;

// Type-boosting items: item_id -> type_id (1.2x for matching type)
struct TBEntry { int32_t item; int8_t type; };
static const TBEntry TYPE_BOOST_ITEMS[] = {
    {222, 11},  // SILVER_POWDER -> BUG
    {233, 16},  // METAL_COAT -> STEEL
    {235, 14},  // DRAGON_SCALE -> DRAGON
    {237, 8},   // SOFT_SAND -> GROUND
    {238, 12},  // HARD_STONE -> ROCK
    {239, 4},   // MIRACLE_SEED -> GRASS
    {240, 15},  // BLACK_GLASSES -> DARK
    {241, 6},   // BLACK_BELT -> FIGHTING
    {242, 3},   // MAGNET -> ELECTRIC
    {243, 2},   // MYSTIC_WATER -> WATER
    {244, 9},   // SHARP_BEAK -> FLYING
    {245, 7},   // POISON_BARB -> POISON
    {246, 5},   // NEVER_MELT_ICE -> ICE
    {247, 13},  // SPELL_TAG -> GHOST
    {248, 10},  // TWISTED_SPOON -> PSYCHIC
    {249, 1},   // CHARCOAL -> FIRE
    {250, 14},  // DRAGON_FANG -> DRAGON
    {251, 0},   // SILK_SCARF -> NORMAL
    {267, 10},  // MIND_PLATE -> PSYCHIC (wait, let me check)
    // Actually let me just list by item ID from Python output
    // {item: type} from Python: 249:1,243:2,239:4,242:3,246:5,244:9,247:13,248:10,251:0,238:12,237:8,241:6,245:7,233:16,250:14,240:15,2401:17,222:11,235:14,644:17,312:15,...
};
// The above approach won't work cleanly with the large set. Use a flat lookup instead.

// ---------------------------------------------------------------------------
// Helper: sorted array membership test
// ---------------------------------------------------------------------------
template<typename T, int N>
static bool in_set(const T (&arr)[N], T val) {
    return std::binary_search(arr, arr + N, val);
}

static bool is_mold_breaker(int32_t ability) {
    return in_set(MOLD_BREAKER_ABILITIES, ability);
}

// ---------------------------------------------------------------------------
// Type-boost items: item -> type (1.2x). Built as a lookup array (sorted by item id).
// ---------------------------------------------------------------------------
// Store all entries sorted by item id. Use linear scan; the set is small enough.
struct TypeBoostEntry { int32_t item; int8_t type; };
static const TypeBoostEntry TYPE_BOOST_MAP[] = {
    // From Python _TYPE_BOOST_ITEMS dict (sorted by item value)
    {222, 11},   // SILVER_POWDER -> BUG
    {233, 16},   // METAL_COAT -> STEEL
    {235, 14},   // DRAGON_SCALE -> DRAGON
    {237, 8},    // SOFT_SAND -> GROUND
    {238, 12},   // HARD_STONE -> ROCK
    {239, 4},    // MIRACLE_SEED -> GRASS
    {240, 15},   // BLACK_GLASSES -> DARK
    {241, 6},    // BLACK_BELT -> FIGHTING
    {242, 3},    // MAGNET -> ELECTRIC
    {243, 2},    // MYSTIC_WATER -> WATER
    {244, 9},    // SHARP_BEAK -> FLYING
    {245, 7},    // POISON_BARB -> POISON
    {246, 5},    // NEVER_MELT_ICE -> ICE
    {247, 13},   // SPELL_TAG -> GHOST
    {248, 10},   // TWISTED_SPOON -> PSYCHIC
    {249, 1},    // CHARCOAL -> FIRE
    {250, 14},   // DRAGON_FANG -> DRAGON
    {251, 0},    // SILK_SCARF -> NORMAL
    {298, 1},    // FLAME_PLATE -> FIRE
    {299, 2},    // SPLASH_PLATE -> WATER
    {300, 3},    // ZAP_PLATE -> ELECTRIC
    {301, 4},    // MEADOW_PLATE -> GRASS
    {302, 5},    // ICICLE_PLATE -> ICE
    {303, 6},    // FIST_PLATE -> FIGHTING
    {304, 7},    // TOXIC_PLATE -> POISON
    {305, 8},    // EARTH_PLATE -> GROUND
    {306, 9},    // SKY_PLATE -> FLYING
    {307, 10},   // MIND_PLATE -> PSYCHIC
    {308, 11},   // INSECT_PLATE -> BUG
    {309, 12},   // STONE_PLATE -> ROCK
    {310, 13},   // SPOOKY_PLATE -> GHOST
    {311, 14},   // DRACO_PLATE -> DRAGON (wait, 311 is WEATHER_BALL move id - no! item IDs != move IDs)
    // Re-check: from Python output TYPE_BOOST_ITEMS: ...311:14, 312:15, 313:16...
    // These are Arceus plates: Draco Plate=311, Dread Plate=312, Iron Plate=313
    {311, 14},   // DRACO_PLATE -> DRAGON
    {312, 15},   // DREAD_PLATE -> DARK
    {313, 16},   // IRON_PLATE -> STEEL
    {644, 17},   // PIXIE_PLATE -> FAIRY
    {901, 1},    // FIRE_MEMORY -> FIRE
    {902, 2},    // WATER_MEMORY -> WATER
    {903, 4},    // GRASS_MEMORY -> GRASS
    {904, 3},    // ELECTRIC_MEMORY -> ELECTRIC
    {905, 5},    // ICE_MEMORY -> ICE
    {906, 6},    // FIGHTING_MEMORY -> FIGHTING
    {907, 7},    // POISON_MEMORY -> POISON
    {908, 8},    // GROUND_MEMORY -> GROUND
    {909, 9},    // FLYING_MEMORY -> FLYING
    {910, 10},   // PSYCHIC_MEMORY -> PSYCHIC
    {911, 11},   // BUG_MEMORY -> BUG
    {912, 12},   // ROCK_MEMORY -> ROCK
    {913, 13},   // GHOST_MEMORY -> GHOST
    {914, 14},   // DRAGON_MEMORY -> DRAGON
    {915, 15},   // DARK_MEMORY -> DARK
    {916, 16},   // STEEL_MEMORY -> STEEL
    {917, 17},   // FAIRY_MEMORY -> FAIRY
    {2401, 17},  // FAIRY_FEATHER -> FAIRY
};
static constexpr int TB_COUNT = 52;

static int8_t type_boost_item_type(int32_t item) {
    // Linear scan since this set isn't sorted by item id cleanly
    for (int i = 0; i < TB_COUNT; ++i) {
        if (TYPE_BOOST_MAP[i].item == item) return TYPE_BOOST_MAP[i].type;
    }
    return -1;  // not found
}

// Gem items: item -> type (1.5x)
static const TypeBoostEntry GEM_MAP[] = {
    {564, 0},    // NORMAL_GEM -> NORMAL
    {4001, 1},   // FIRE_GEM
    {4002, 2},   // WATER_GEM
    {4003, 4},   // GRASS_GEM
    {4004, 3},   // ELECTRIC_GEM
    {4005, 5},   // ICE_GEM
    {4006, 6},   // FIGHTING_GEM
    {4007, 7},   // POISON_GEM
    {4008, 8},   // GROUND_GEM
    {4009, 9},   // FLYING_GEM
    {4010, 10},  // PSYCHIC_GEM
    {4011, 11},  // BUG_GEM
    {4012, 12},  // ROCK_GEM
    {4013, 13},  // GHOST_GEM
    {4014, 14},  // DRAGON_GEM
    {4015, 15},  // DARK_GEM
    {4016, 16},  // STEEL_GEM
    {4017, 17},  // FAIRY_GEM
};
static constexpr int GEM_COUNT = 18;

static int8_t gem_type(int32_t item) {
    for (int i = 0; i < GEM_COUNT; ++i) {
        if (GEM_MAP[i].item == item) return GEM_MAP[i].type;
    }
    return -1;
}

// ---------------------------------------------------------------------------
// Move table lookup
// ---------------------------------------------------------------------------
static constexpr int MOVE_COUNT = 813;

static const MoveData& lookup_move(int32_t move_id) {
    int lo = 0, hi = MOVE_COUNT;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        if (MOVE_TABLE[mid].move_id < move_id) lo = mid + 1;
        else hi = mid;
    }
    if (lo >= MOVE_COUNT || MOVE_TABLE[lo].move_id != move_id)
        throw std::runtime_error("lookup_move: id " + std::to_string(move_id) + " not found");
    return MOVE_TABLE[lo];
}

// ---------------------------------------------------------------------------
// PseudoWeather / SideCondition helpers
// ---------------------------------------------------------------------------
static bool has_pseudo_weather(const BattleState& state, int32_t pw) {
    for (const auto& e : state.pseudo_weather)
        if (e.effect == pw) return true;
    return false;
}

static bool has_timed_volatile(const PokemonState& mon, int32_t ve) {
    for (const auto& tv : mon.timed_volatiles)
        if (tv.effect == ve) return true;
    return false;
}

static bool has_side_condition(const SideState& side, int32_t cond) {
    for (const auto& sc : side.side_conditions)
        if (sc.condition == cond) return true;
    return false;
}

// ---------------------------------------------------------------------------
// Effective weather (suppressed by Air Lock / Cloud Nine on any active mon)
// ---------------------------------------------------------------------------
using eff_internal::effective_weather;

// ---------------------------------------------------------------------------
// Grounded check
// ---------------------------------------------------------------------------
static bool is_grounded(const PokemonState& mon, const BattleState& state) {
    if (has_pseudo_weather(state, PW_GRAVITY)) return true;
    if (mon.item == ITEM_IRON_BALL) return true;
    if (has_timed_volatile(mon, VE_GROUNDED)) return true;
    // Check types
    for (int32_t t : mon.types) {
        if (t == TYPE_FLYING) return false;
    }
    if (mon.ability == AB_LEVITATE) return false;
    if (mon.item == ITEM_AIR_BALLOON) return false;
    if (has_timed_volatile(mon, VE_MAGNET_RISE)) return false;
    if (has_timed_volatile(mon, VE_TELEKINESIS)) return false;
    return true;
}

// ---------------------------------------------------------------------------
// Hidden Power type from IVs
// ---------------------------------------------------------------------------
static const int32_t HP_TYPE_TABLE[16] = {
    TYPE_FIGHTING, TYPE_FLYING, TYPE_POISON, TYPE_GROUND,
    TYPE_ROCK, TYPE_BUG, TYPE_GHOST, TYPE_STEEL,
    TYPE_FIRE, TYPE_WATER, TYPE_GRASS, TYPE_ELECTRIC,
    TYPE_PSYCHIC, TYPE_ICE, TYPE_DRAGON, TYPE_DARK,
};

int32_t hidden_power_type(const PokemonState& mon) {
    // ivs: (hp_iv, atk_iv, def_iv, spa_iv, spd_iv, spe_iv)
    int bits = (mon.iv_hp % 2)
             | ((mon.iv_atk % 2) << 1)
             | ((mon.iv_def % 2) << 2)
             | ((mon.iv_spe % 2) << 3)
             | ((mon.iv_spa % 2) << 4)
             | ((mon.iv_spd % 2) << 5);
    int type_index = (bits * 15) / 63;
    return HP_TYPE_TABLE[type_index];
}

// ---------------------------------------------------------------------------
// Stage multiplier (index = stage + 6)
// ---------------------------------------------------------------------------
static double stage_multiplier(int stage) {
    // _STAGE_MULT = [2/8, 2/7, 2/6, 2/5, 2/4, 2/3, 1.0, 3/2, 4/2, 5/2, 6/2, 7/2, 8/2]
    static const double MULT[13] = {
        2.0/8, 2.0/7, 2.0/6, 2.0/5, 2.0/4, 2.0/3,
        1.0,
        3.0/2, 4.0/2, 5.0/2, 6.0/2, 7.0/2, 8.0/2
    };
    return MULT[stage + 6];
}

// stat_stages indices: 0=ATK, 1=DEF, 2=SPA, 3=SPD, 4=SPE, 5=ACC, 6=EVA
// stats indices: 0=HP, 1=ATK, 2=DEF, 3=SPA, 4=SPD, 5=SPE
// Mapping stat_idx -> stage_idx: 1->0, 2->1, 3->2, 4->3, 5->4
static int stage_idx_for_stat(int stat_idx) {
    switch (stat_idx) {
        case 1: return 0;
        case 2: return 1;
        case 3: return 2;
        case 4: return 3;
        case 5: return 4;
        default: return -1;
    }
}

static int32_t get_stage(const PokemonState& mon, int stage_idx) {
    switch (stage_idx) {
        case 0: return mon.stage0;
        case 1: return mon.stage1;
        case 2: return mon.stage2;
        case 3: return mon.stage3;
        case 4: return mon.stage4;
        default: return 0;
    }
}

static int32_t get_stat(const PokemonState& mon, int stat_idx) {
    switch (stat_idx) {
        case 1: return mon.stat_atk;
        case 2: return mon.stat_def;
        case 3: return mon.stat_spa;
        case 4: return mon.stat_spd;
        case 5: return mon.stat_spe;
        default: return mon.stat_hp;
    }
}

int32_t cpp_effective_stat(const PokemonState& mon, int stat_idx, bool is_crit) {
    int sidx = stage_idx_for_stat(stat_idx);
    int32_t stage = get_stage(mon, sidx);
    if (is_crit) {
        if (stat_idx == 1 || stat_idx == 3) stage = std::max(stage, 0);  // ATK/SPA: ignore negative
        else if (stat_idx == 2 || stat_idx == 4) stage = std::min(stage, 0);  // DEF/SPD: ignore positive
    }
    double mult = stage_multiplier(stage);
    int32_t base = get_stat(mon, stat_idx);
    int32_t result = static_cast<int32_t>(base * mult);
    return std::max(1, result);
}

// ---------------------------------------------------------------------------
// Crit chance resolution
// ---------------------------------------------------------------------------
static float get_crit_chance(const PokemonState& attacker, const PokemonState& defender,
                              int crit_boost, bool magic_room) {
    // Magma Armor always blocks crits (not bypassed by Mold Breaker)
    if (defender.ability == AB_MAGMA_ARMOR) return 0.0f;
    bool breaks_mold = is_mold_breaker(attacker.ability);
    if ((defender.ability == AB_BATTLE_ARMOR || defender.ability == AB_SHELL_ARMOR)
            && !breaks_mold) return 0.0f;
    // Laser Focus: always crit (check after immunity)
    if (has_timed_volatile(attacker, VE_LASER_FOCUS)) return 1.0f;

    int stage = attacker.crit_stage;
    if (attacker.ability == AB_SUPER_LUCK) stage += 1;
    if (!magic_room && (attacker.item == ITEM_SCOPE_LENS || attacker.item == ITEM_RAZOR_CLAW))
        stage += 1;
    if (!magic_room && attacker.item == ITEM_LEEK
            && in_set(LEEK_SPECIES, attacker.species))
        stage += 2;
    stage += crit_boost;
    stage = std::min(stage, 3);

    static const float CRIT_CHANCE[4] = {1.0f/16, 1.0f/8, 1.0f/2, 100.0f};
    return CRIT_CHANCE[stage];
}


// ---------------------------------------------------------------------------
// Type effectiveness
// ---------------------------------------------------------------------------
static float type_eff(int32_t atk_type, int32_t def_type) {
    return cpp_type_effectiveness(atk_type, def_type);
}

static bool has_type(const PokemonState& mon, int32_t t) {
    for (int32_t v : mon.types)
        if (v == t) return true;
    return false;
}

static double type_effectiveness_product(
    const PokemonState& attacker, int32_t move_id, int32_t move_type,
    const PokemonState& defender, const BattleState& state)
{
    double effectiveness = 1.0;
    bool breaks_mold = is_mold_breaker(attacker.ability);  // (unused here; scrappy/identified handle ghost)

    for (int32_t def_type : defender.types) {
        float factor = type_eff(move_type, def_type);
        // Scrappy: Normal/Fighting vs Ghost → 1.0
        if (factor == 0.0f && def_type == TYPE_GHOST
                && (move_type == TYPE_NORMAL || move_type == TYPE_FIGHTING)
                && attacker.ability == AB_SCRAPPY)
            factor = 1.0f;
        // IDENTIFIED volatile: Normal/Fighting vs Ghost → 1.0
        if (factor == 0.0f && def_type == TYPE_GHOST
                && (move_type == TYPE_NORMAL || move_type == TYPE_FIGHTING)
                && (defender.volatiles & VOLATILE_IDENTIFIED))
            factor = 1.0f;
        effectiveness *= factor;
    }

    // Flying Press: multiply by Flying effectiveness too
    if (move_id == MOVE_FLYING_PRESS) {
        for (int32_t def_type : defender.types)
            effectiveness *= type_eff(TYPE_FLYING, def_type);
    }

    // Freeze-Dry: override Ice vs Water to ×2 (normally 0.5, so multiply by 4)
    if (move_id == MOVE_FREEZE_DRY && has_type(defender, TYPE_WATER))
        effectiveness *= 4.0;

    // Gravity: Ground immunity removed if any gravity pseudo-weather active
    if (effectiveness == 0.0 && move_type == TYPE_GROUND
            && has_pseudo_weather(state, PW_GRAVITY))
        effectiveness = 1.0;

    // Thousand Arrows: overrides Ground immunity
    if (move_id == MOVE_THOUSAND_ARROWS && effectiveness == 0.0)
        effectiveness = 1.0;

    // Ring Target: remove type immunities
    if (defender.item == ITEM_RING_TARGET && effectiveness == 0.0) {
        double recomputed = 1.0;
        for (int32_t def_type : defender.types) {
            float primary = type_eff(move_type, def_type);
            recomputed *= (primary == 0.0f ? 1.0 : primary);
            if (move_id == MOVE_FLYING_PRESS) {
                float flying = type_eff(TYPE_FLYING, def_type);
                recomputed *= (flying == 0.0f ? 1.0 : flying);
            }
        }
        effectiveness = recomputed;
    }

    return effectiveness;
}

// Public wrapper so post_hit.cpp (Weakness Policy) can reuse the effectiveness calc.
double cpp_check_type_immunity(
    const PokemonState& attacker, int32_t move_id, int32_t move_type,
    const PokemonState& defender, const BattleState& state)
{
    return type_effectiveness_product(attacker, move_id, move_type, defender, state);
}

// ---------------------------------------------------------------------------
// Semi-invulnerable double-damage interaction
// ---------------------------------------------------------------------------
// Python _semi_invuln_interaction returns (can_hit, double_dmg)
// We only need the double_dmg flag here.
// The Python table from moves.py (check if we can duplicate the logic):
// - Gust/Twister vs FLY/BOUNCE: double damage
// - Earthquake/Magnitude vs DIG: double damage
// - Surf/Whirlpool vs DIVE: double damage
// We identify charging moves by their move_id.
static bool semi_invuln_double_dmg(int32_t charging_move_id, int32_t attacking_move_id) {
    // FLY=19, BOUNCE=340, SKY_DROP=507
    // GUST=16, TWISTER=239
    static const int32_t FLY_MOVES[] = {19, 340, 507};  // sorted
    // DIG=91
    // EARTHQUAKE=89, MAGNITUDE=222
    static const int32_t DIG_MOVES[] = {91};
    // DIVE=291
    // SURF=57, WHIRLPOOL=250
    static const int32_t DIVE_MOVES[] = {291};

    // Gust/Twister vs airborne
    if ((attacking_move_id == 16 || attacking_move_id == 239)
            && in_set(FLY_MOVES, charging_move_id)) return true;
    // Earthquake/Magnitude vs underground
    if ((attacking_move_id == MOVE_EARTHQUAKE || attacking_move_id == MOVE_MAGNITUDE)
            && charging_move_id == 91) return true;
    // Surf/Whirlpool vs underwater
    if ((attacking_move_id == 57 || attacking_move_id == 250)
            && charging_move_id == 291) return true;

    return false;
}

// ---------------------------------------------------------------------------
// Natural Gift lookup
// ---------------------------------------------------------------------------
static bool natural_gift_lookup(int32_t item, int8_t& out_type, uint8_t& out_bp) {
    for (int i = 0; i < NG_COUNT; ++i) {
        if (NATURAL_GIFT_TABLE[i].item == item) {
            out_type = NATURAL_GIFT_TABLE[i].type;
            out_bp   = NATURAL_GIFT_TABLE[i].bp;
            return true;
        }
    }
    return false;
}

// Natural Gift type lookup for pdg_resolve_move_type (guards need the berry type before immunity checks).
int32_t cpp_natural_gift_type(int32_t item_id) {
    int8_t ng_type; uint8_t ng_bp;
    if (!natural_gift_lookup(item_id, ng_type, ng_bp)) return -1;
    return static_cast<int32_t>(ng_type);
}

// ---------------------------------------------------------------------------
// Resolve move type and BP
// ---------------------------------------------------------------------------
static void resolve_move_type_and_bp(
    const PokemonState& attacker, int32_t move_id, const MoveData& md,
    const BattleState& state, int32_t bp_override,
    int32_t& out_type, int32_t& out_bp)
{
    int32_t move_type = md.move_type;

    // Hidden Power: type from IVs
    if (move_id == MOVE_HIDDEN_POWER)
        move_type = hidden_power_type(attacker);

    // Liquid Voice: sound → Water
    if (attacker.ability == AB_LIQUID_VOICE && (md.tags & TAG_SOUND))
        move_type = TYPE_WATER;

    int32_t base_bp = bp_override ? bp_override : static_cast<int32_t>(md.base_power);

    // Normalize
    if (attacker.ability == AB_NORMALIZE) {
        move_type = TYPE_NORMAL;
        bool no_boost = (move_id == MOVE_WEATHER_BALL || move_id == MOVE_REVELATION_DANCE);
        out_bp = no_boost ? base_bp : static_cast<int32_t>(std::floor(base_bp * 1.2));
        out_type = move_type;
        // Continue below for Natural Gift, WeatherBall, etc. but keep type=NORMAL
        // Actually we must still process Natural Gift and other special moves after
        // We need to replicate Python's exact flow. In Python, after Normalize sets type=NORMAL
        // and bp, it falls through to Natural Gift check etc. Let's replicate:
        // (set out_bp here, then fall through)
        base_bp = out_bp;  // use the Normalized bp for subsequent steps
        // But in Python, Normalize is an if/else with ate: so after Normalize branch,
        // bp is set and we proceed to Natural Gift check etc.
        // We'll just store and continue after the ate block.
    } else {
        // -ate abilities: Normal-type moves become the specified type with ×1.2 BP
        struct AteEntry { int32_t ability; int32_t type; };
        static const AteEntry ATE[] = {
            {AB_PIXILATE,    TYPE_FAIRY},
            {AB_REFRIGERATE, TYPE_ICE},
            {AB_AERILATE,    TYPE_FLYING},
            {AB_GALVANIZE,   TYPE_ELECTRIC},
        };
        bool ate_applied = false;
        for (const auto& a : ATE) {
            if (attacker.ability == a.ability && move_type == TYPE_NORMAL) {
                move_type = a.type;
                base_bp = static_cast<int32_t>(std::floor(base_bp * 1.2));
                ate_applied = true;
                break;
            }
        }
        out_bp = base_bp;
    }
    out_type = move_type;
    out_bp = base_bp;

    // Natural Gift
    if (move_id == MOVE_NATURAL_GIFT) {
        int8_t ng_type; uint8_t ng_bp;
        if (!natural_gift_lookup(attacker.item, ng_type, ng_bp)) {
            out_bp = 0;  // signal: no berry
            return;
        }
        out_type = static_cast<int32_t>(ng_type);
        out_bp = static_cast<int32_t>(ng_bp);
        return;
    }

    // Weather Ball
    if (move_id == MOVE_WEATHER_BALL) {
        int32_t wb_weather = effective_weather(state);
        if (wb_weather != WEATHER_NONE && wb_weather != WEATHER_STRONG_WIND) {
            out_bp = out_bp * 2;
            switch (wb_weather) {
                case WEATHER_SUNNY: case WEATHER_HARSH_SUN:  out_type = TYPE_FIRE;   break;
                case WEATHER_RAINY: case WEATHER_HEAVY_RAIN: out_type = TYPE_WATER;  break;
                case WEATHER_SANDSTORM:                       out_type = TYPE_ROCK;   break;
                case WEATHER_HAIL:                            out_type = TYPE_ICE;    break;
            }
        }
        // Fall through to Technician (mirrors Python: variable-power moves are not early-returned).
    }

    // Revelation Dance: first type of attacker
    if (move_id == MOVE_REVELATION_DANCE) {
        if (!attacker.types.empty()) out_type = attacker.types[0];
    }

    // Terrain Pulse
    if (move_id == MOVE_TERRAIN_PULSE && state.terrain != TERRAIN_NONE
            && is_grounded(attacker, state)) {
        out_bp = out_bp * 2;
        switch (state.terrain) {
            case TERRAIN_ELECTRIC: out_type = TYPE_ELECTRIC; break;
            case TERRAIN_GRASSY:   out_type = TYPE_GRASS;    break;
            case TERRAIN_PSYCHIC:  out_type = TYPE_PSYCHIC;  break;
            case TERRAIN_MISTY:    out_type = TYPE_FAIRY;    break;
        }
    }

    // Aura Wheel
    if (move_id == MOVE_AURA_WHEEL) {
        out_type = (attacker.species == SPECIES_MORPEKO_HANGRY) ? TYPE_DARK : TYPE_ELECTRIC;
    }

    // Multi-Attack: attacker's first type
    if (move_id == MOVE_MULTI_ATTACK) {
        if (!attacker.types.empty()) out_type = attacker.types[0];
    }

    // Technician: 1.5x for moves with base_power <= 60 (skip variable-power with bp=0)
    if (attacker.ability == AB_TECHNICIAN && md.base_power > 0 && md.base_power <= 60) {
        out_bp = static_cast<int32_t>(std::floor(out_bp * 1.5));
    }
}

// ---------------------------------------------------------------------------
// Compute BP multipliers
// ---------------------------------------------------------------------------
static int32_t compute_bp(
    const PokemonState& attacker, const PokemonState& defender,
    int32_t move_id, const MoveData& md, int32_t move_type, int32_t bp,
    const BattleState& state, int32_t def_side_idx, bool is_physical)
{
    bool breaks_mold = is_mold_breaker(attacker.ability);

    // Flash Fire: Fire moves get 1.5x when activated
    if (move_type == TYPE_FIRE && (attacker.volatiles & VOLATILE_FLASH_FIRE))
        bp = static_cast<int32_t>(bp * 1.5);  // int multiplication (not floor)

    // Helping Hand: 1.5x
    if (attacker.volatiles & VOLATILE_HELPING_HAND)
        bp = static_cast<int32_t>(std::floor(bp * 1.5));

    // Power Spot (doubles only): ally with Power Spot boosts BP ×1.3
    if (def_side_idx >= 0) {
        int32_t atk_side_idx = 1 - def_side_idx;
        const SideState& atk_side = (atk_side_idx == 0) ? state.side0 : state.side1;
        for (int32_t ally_idx : atk_side.active_indices) {
            const PokemonState& ally = atk_side.team[ally_idx];
            if (&ally != &attacker && ally.ability == AB_POWER_SPOT) {
                bp = static_cast<int32_t>(std::floor(bp * 1.3));
                break;
            }
        }
    }

    // Battery (doubles only): special move BP ×(5325/4096)
    static constexpr double BATTERY_MULT = 5325.0 / 4096.0;
    if (!is_physical && def_side_idx >= 0) {
        int32_t atk_side_idx = 1 - def_side_idx;
        const SideState& atk_side = (atk_side_idx == 0) ? state.side0 : state.side1;
        for (int32_t ally_idx : atk_side.active_indices) {
            const PokemonState& ally = atk_side.team[ally_idx];
            if (&ally != &attacker && ally.ability == AB_BATTERY) {
                bp = static_cast<int32_t>(std::floor(bp * BATTERY_MULT));
                break;
            }
        }
    }

    // Terrain modifiers
    if (state.terrain == TERRAIN_MISTY && move_type == TYPE_DRAGON) {
        if (is_grounded(defender, state)) bp = bp / 2;
    } else if (state.terrain == TERRAIN_GRASSY
               && (move_id == MOVE_EARTHQUAKE || move_id == MOVE_BULLDOZE || move_id == MOVE_MAGNITUDE)) {
        bp = bp / 2;
    } else if (is_grounded(attacker, state)) {
        if (state.terrain == TERRAIN_ELECTRIC && move_type == TYPE_ELECTRIC)
            bp = static_cast<int32_t>(std::floor(bp * 1.5));
        else if (state.terrain == TERRAIN_GRASSY && move_type == TYPE_GRASS)
            bp = static_cast<int32_t>(std::floor(bp * 1.5));
        else if (state.terrain == TERRAIN_PSYCHIC && move_type == TYPE_PSYCHIC)
            bp = static_cast<int32_t>(std::floor(bp * 1.5));
        else if (state.terrain == TERRAIN_MISTY && move_id == MOVE_MISTY_EXPLOSION)
            bp = static_cast<int32_t>(std::floor(bp * 1.5));
    }

    if (attacker.ability == AB_STRONG_JAW && (md.tags & TAG_BITING))
        bp = static_cast<int32_t>(std::floor(bp * 1.5));
    if (attacker.ability == AB_MEGA_LAUNCHER && (md.tags & TAG_PULSE))
        bp = static_cast<int32_t>(std::floor(bp * 1.5));
    if (attacker.ability == AB_PUNK_ROCK && (md.tags & TAG_SOUND))
        bp = static_cast<int32_t>(std::floor(bp * 1.3));
    if (attacker.ability == AB_SHEER_FORCE && md.secondary.chance != 0)
        bp = static_cast<int32_t>(std::floor(bp * 1.3));
    if (attacker.ability == AB_IRON_FIST && (md.tags & TAG_PUNCHING))
        bp = static_cast<int32_t>(std::floor(bp * 1.2));
    if (attacker.ability == AB_SHARPNESS && (md.tags & TAG_SLICING))
        bp = static_cast<int32_t>(std::floor(bp * 1.5));
    if (attacker.ability == AB_TOUGH_CLAWS && (md.tags & TAG_CONTACT))
        bp = static_cast<int32_t>(std::floor(bp * 1.3));
    if (attacker.ability == AB_RECKLESS) {
        bool has_recoil = (md.recoil_num >= 0);
        bool is_reckless = in_set(RECKLESS_MOVES, move_id);
        if (has_recoil || is_reckless)
            bp = static_cast<int32_t>(std::floor(bp * 1.2));
    }
    if (attacker.ability == AB_SAND_FORCE
            && effective_weather(state) == WEATHER_SANDSTORM
            && (move_type == TYPE_ROCK || move_type == TYPE_GROUND || move_type == TYPE_STEEL))
        bp = static_cast<int32_t>(std::floor(bp * 1.3));
    if (move_type == TYPE_WATER && attacker.ability == AB_WATER_BUBBLE)
        bp = bp * 2;  // int
    if (attacker.ability == AB_STEELY_SPIRIT && move_type == TYPE_STEEL)
        bp = static_cast<int32_t>(std::floor(bp * 1.5));
    if (attacker.ability == AB_STEELWORKER && move_type == TYPE_STEEL)
        bp = static_cast<int32_t>(std::floor(bp * 1.5));
    if (attacker.ability == AB_TRANSISTOR && move_type == TYPE_ELECTRIC)
        bp = static_cast<int32_t>(std::floor(bp * 1.5));
    if (attacker.ability == AB_DRAGON_S_MAW && move_type == TYPE_DRAGON)
        bp = static_cast<int32_t>(std::floor(bp * 1.5));

    // Thick Fat: defender takes 0.5x from Fire/Ice (breakable)
    if (defender.ability == AB_THICK_FAT && (move_type == TYPE_FIRE || move_type == TYPE_ICE)
            && !breaks_mold
            && !in_set(IGNORE_ABILITY_MOVES, move_id))
        bp = bp / 2;

    bool magic_room = has_pseudo_weather(state, PW_MAGIC_ROOM);

    // Wise Glasses: 1.1x special
    if (attacker.item == ITEM_WISE_GLASSES && !is_physical && !magic_room)
        bp = static_cast<int32_t>(std::floor(bp * 1.1));
    // Muscle Band: 1.1x physical
    if (attacker.item == ITEM_MUSCLE_BAND && is_physical && !magic_room)
        bp = static_cast<int32_t>(std::floor(bp * 1.1));

    // Type-boosting items: 1.2x
    if (!magic_room) {
        int8_t tb_type = type_boost_item_type(attacker.item);
        if (tb_type >= 0 && static_cast<int32_t>(tb_type) == move_type)
            bp = static_cast<int32_t>(std::floor(bp * 1.2));
    }

    // Griseous Orb / Core: 1.2x Ghost/Dragon for Giratina
    if (!magic_room
            && (attacker.item == ITEM_GRISEOUS_ORB || attacker.item == ITEM_GRISEOUS_CORE)
            && (attacker.species == SPECIES_GIRATINA || attacker.species == SPECIES_GIRATINA_ORIGIN)
            && (move_type == TYPE_GHOST || move_type == TYPE_DRAGON))
        bp = static_cast<int32_t>(std::floor(bp * 1.2));

    // Gems: 1.5x for matching type
    if (!magic_room) {
        int8_t g_type = gem_type(attacker.item);
        if (g_type >= 0 && static_cast<int32_t>(g_type) == move_type)
            bp = static_cast<int32_t>(std::floor(bp * 1.5));
    }

    return bp;
}

// ---------------------------------------------------------------------------
// Compute attack stat
// ---------------------------------------------------------------------------
static int32_t compute_attack_stat(
    const PokemonState& attacker, const PokemonState& defender,
    int32_t move_id, const MoveData& md, bool is_physical, bool is_crit,
    const BattleState& state, int32_t def_side_idx)
{
    bool magic_room = has_pseudo_weather(state, PW_MAGIC_ROOM);
    bool breaks_mold = is_mold_breaker(attacker.ability);

    int32_t atk;
    if (is_physical) {
        // Defender Unaware zeroes attacker's Atk stage
        int32_t stage_val = attacker.stage0;  // ATK stage
        if (defender.ability == AB_UNAWARE && !breaks_mold) stage_val = 0;
        if (is_crit && stage_val < 0) stage_val = 0;  // crit: ignore negative
        double mult = stage_multiplier(stage_val);
        atk = std::max(1, static_cast<int32_t>(attacker.stat_atk * mult));
    } else {
        // Defender Unaware zeroes attacker's SpA stage
        int32_t stage_val = attacker.stage2;  // SPA stage
        if (defender.ability == AB_UNAWARE && !breaks_mold) stage_val = 0;
        if (is_crit && stage_val < 0) stage_val = 0;
        double mult = stage_multiplier(stage_val);
        atk = std::max(1, static_cast<int32_t>(attacker.stat_spa * mult));
    }

    // Body Press: uses attacker's Defense as attack stat
    if (move_id == MOVE_BODY_PRESS)
        atk = cpp_effective_stat(attacker, 2, is_crit);

    // Foul Play: uses defender's Attack as attack stat
    if (move_id == MOVE_FOUL_PLAY)
        atk = cpp_effective_stat(defender, 1, is_crit);

    // Slow Start: halve Attack (physical only) for first 5 turns
    if (is_physical && attacker.ability == AB_SLOW_START && attacker.turns_in_battle < 5)
        atk = atk / 2;

    // Huge Power / Pure Power: double Attack for physical
    if (is_physical && (attacker.ability == AB_HUGE_POWER || attacker.ability == AB_PURE_POWER))
        atk = atk * 2;

    // Hustle: 1.5x physical Attack
    if (is_physical && attacker.ability == AB_HUSTLE)
        atk = static_cast<int32_t>(std::floor(atk * 1.5));

    // Guts: 1.5x when statused
    if (is_physical && attacker.ability == AB_GUTS && attacker.status != STATUS_NONE)
        atk = static_cast<int32_t>(std::floor(atk * 1.5));

    // Toxic Boost: 1.5x physical when poisoned
    if (is_physical && attacker.ability == AB_TOXIC_BOOST
            && (attacker.status == STATUS_POISON || attacker.status == STATUS_TOXIC))
        atk = static_cast<int32_t>(std::floor(atk * 1.5));

    // Gorilla Tactics: 1.5x physical
    if (is_physical && attacker.ability == AB_GORILLA_TACTICS)
        atk = static_cast<int32_t>(std::floor(atk * 1.5));

    // Solar Power: 1.5x SpA in sun
    if (!is_physical && attacker.ability == AB_SOLAR_POWER) {
        int32_t ew = effective_weather(state);
        if (ew == WEATHER_SUNNY || ew == WEATHER_HARSH_SUN)
            atk = static_cast<int32_t>(std::floor(atk * 1.5));
    }

    // Flower Gift: 1.5x physical in sunny
    if (is_physical && attacker.ability == AB_FLOWER_GIFT) {
        int32_t ew = effective_weather(state);
        if (ew == WEATHER_SUNNY || ew == WEATHER_HARSH_SUN)
            atk = static_cast<int32_t>(std::floor(atk * 1.5));
    }

    // Plus / Minus (doubles only): 1.5x SpA
    if (!is_physical && def_side_idx >= 0) {
        int32_t atk_side_idx = 1 - def_side_idx;
        const SideState& atk_side = (atk_side_idx == 0) ? state.side0 : state.side1;
        bool has_plus = (attacker.ability == AB_PLUS);
        bool has_minus= (attacker.ability == AB_MINUS);
        if (has_plus || has_minus) {
            bool ally_has_other = false;
            for (int32_t ally_idx : atk_side.active_indices) {
                const PokemonState& ally = atk_side.team[ally_idx];
                if (&ally == &attacker) continue;
                if ((has_plus && ally.ability == AB_MINUS)
                        || (has_minus && ally.ability == AB_PLUS)) {
                    ally_has_other = true;
                    break;
                }
            }
            if (ally_has_other)
                atk = static_cast<int32_t>(std::floor(atk * 1.5));
        }
    }

    // Defeatist: halve both when HP ≤ 50%
    if (attacker.ability == AB_DEFEATIST) {
        int32_t mhp = attacker.has_max_hp ? attacker.max_hp : attacker.stat_hp;
        int32_t cur = attacker.has_hp ? attacker.hp : mhp;
        if (cur <= mhp / 2) atk = atk / 2;
    }

    // Light Ball: double Pikachu's Atk or SpA
    if (!magic_room && attacker.item == ITEM_LIGHT_BALL
            && in_set(PIKACHU_SPECIES, attacker.species))
        atk *= 2;

    // Thick Club: double Cubone/Marowak physical
    if (!magic_room && is_physical && attacker.item == ITEM_THICK_CLUB
            && in_set(THICK_CLUB_SPECIES, attacker.species))
        atk *= 2;

    // Choice Band / Specs
    if (!magic_room && attacker.item == ITEM_CHOICE_BAND && is_physical)
        atk = static_cast<int32_t>(std::floor(atk * 1.5));
    if (!magic_room && attacker.item == ITEM_CHOICE_SPECS && !is_physical)
        atk = static_cast<int32_t>(std::floor(atk * 1.5));

    return atk;
}

// ---------------------------------------------------------------------------
// Compute defense stat
// ---------------------------------------------------------------------------
static int32_t compute_defense_stat(
    const PokemonState& attacker, const PokemonState& defender,
    int32_t move_id, const MoveData& md, bool is_physical, bool is_crit,
    const BattleState& state)
{
    bool breaks_mold = is_mold_breaker(attacker.ability);
    bool magic_room = has_pseudo_weather(state, PW_MAGIC_ROOM);

    int32_t def_val;
    if (is_physical) {
        // Attacker Unaware zeroes defender's Def stage
        int32_t stage_val = defender.stage1;  // DEF stage
        if (attacker.ability == AB_UNAWARE) stage_val = 0;
        // Ignore-def-boost moves: clamp to min(stage, 0)
        if (in_set(IGNORE_DEF_BOOST_MOVES, move_id)) stage_val = std::min(stage_val, 0);
        if (is_crit && stage_val > 0) stage_val = 0;  // crit: ignore positive def stages
        double mult = stage_multiplier(stage_val);
        def_val = std::max(1, static_cast<int32_t>(defender.stat_def * mult));
    } else {
        // Attacker Unaware zeroes defender's SpD stage
        int32_t stage_val = defender.stage3;  // SPD stage
        if (attacker.ability == AB_UNAWARE) stage_val = 0;
        if (in_set(IGNORE_DEF_BOOST_MOVES, move_id)) stage_val = std::min(stage_val, 0);
        if (is_crit && stage_val > 0) stage_val = 0;
        double mult = stage_multiplier(stage_val);
        def_val = std::max(1, static_cast<int32_t>(defender.stat_spd * mult));
    }

    // Wonder Room: swap Def and SpD
    if (has_pseudo_weather(state, PW_WONDER_ROOM)) {
        if (is_physical)
            def_val = cpp_effective_stat(defender, 4, is_crit);
        else
            def_val = cpp_effective_stat(defender, 2, is_crit);
    }

    // Psyshock / Psystrike / Secret Sword: use physical defense
    if (move_id == MOVE_PSYSHOCK || move_id == MOVE_PSYSTRIKE || move_id == MOVE_SECRET_SWORD)
        def_val = cpp_effective_stat(defender, 2, is_crit);

    // Sandstorm: Rock-type SpD boost
    if (!is_physical && effective_weather(state) == WEATHER_SANDSTORM
            && has_type(defender, TYPE_ROCK))
        def_val = static_cast<int32_t>(std::floor(def_val * 3.0 / 2));

    // Flower Gift: 1.5x SpD in sun
    if (!is_physical && defender.ability == AB_FLOWER_GIFT) {
        int32_t ew = effective_weather(state);
        if (ew == WEATHER_SUNNY || ew == WEATHER_HARSH_SUN)
            def_val = static_cast<int32_t>(std::floor(def_val * 1.5));
    }

    // Eviolite: 1.5x Def/SpD for unevolved
    if (!magic_room && defender.item == ITEM_EVIOLITE
            && in_set(UNEVOLVED_SPECIES, defender.species))
        def_val = static_cast<int32_t>(std::floor(def_val * 1.5));

    // Assault Vest: 1.5x SpD
    if (!is_physical && !magic_room && defender.item == ITEM_ASSAULT_VEST)
        def_val = static_cast<int32_t>(std::floor(def_val * 1.5));

    // Fur Coat: double Def (breakable)
    if (is_physical && defender.ability == AB_FUR_COAT && !breaks_mold)
        def_val = def_val * 2;

    // Marvel Scale: 1.5x Def when statused (breakable)
    if (is_physical && defender.ability == AB_MARVEL_SCALE
            && defender.status != STATUS_NONE && !breaks_mold)
        def_val = static_cast<int32_t>(std::floor(def_val * 1.5));

    // Grass Pelt: 1.5x Def in Grassy Terrain (breakable)
    if (is_physical && defender.ability == AB_GRASS_PELT
            && state.terrain == TERRAIN_GRASSY && !breaks_mold)
        def_val = static_cast<int32_t>(std::floor(def_val * 1.5));

    // Explosion/Self-Destruct: halve defender's Defense
    if (in_set(EXPLOSION_MOVES, move_id))
        def_val = std::max(1, def_val / 2);

    return def_val;
}

// ---------------------------------------------------------------------------
// Weather damage modifier
// ---------------------------------------------------------------------------
static int32_t apply_weather(int32_t damage, int32_t move_type,
                              int32_t weather, const BattleState& state) {
    if (effective_weather(state) == WEATHER_NONE) return damage;
    if (weather == WEATHER_RAINY || weather == WEATHER_HEAVY_RAIN) {
        if (move_type == TYPE_WATER) return static_cast<int32_t>(std::floor(damage * 1.5));
        if (move_type == TYPE_FIRE)  return static_cast<int32_t>(std::floor(damage * 0.5));
    } else if (weather == WEATHER_SUNNY || weather == WEATHER_HARSH_SUN) {
        if (move_type == TYPE_FIRE)  return static_cast<int32_t>(std::floor(damage * 1.5));
        if (move_type == TYPE_WATER) return static_cast<int32_t>(std::floor(damage * 0.5));
    }
    return damage;
}

// ---------------------------------------------------------------------------
// Post-roll modifier chain context and helper
// ---------------------------------------------------------------------------

// All context needed by the post-roll modifier chain.
// Populated from cpp_calculate_damage's locals before the roll draw.
struct PostRollCtx {
    // Mutable copy: Delta Stream can lower effectiveness inside the chain.
    double      effectiveness;
    int32_t     move_type;
    int32_t     move_id;
    bool        pinch_active;
    bool        breaks_mold;
    bool        is_physical;
    bool        is_crit;
    bool        magic_room;
    bool        ai_scoring_view;
    int32_t     def_side_idx;
    int32_t     md_tags;        // MoveData::tags bitmask
    const PokemonState* attacker;
    const PokemonState* defender;
    const BattleState*  state;
};

// Apply roll and full post-roll modifier chain to pre_roll_damage.
// INVARIANT: nothing in this function reads roll_int except to compute the initial
// rolled damage (damage * (85 + roll_int) / 100). Every subsequent step depends only
// on the resulting damage integer. This was verified by inspection of lines 1443–1619
// of the original code: roll_int is not referenced after line 1443.
// All modifiers are deterministic functions of the context — no RNG is consumed here.
static int32_t apply_roll_and_modifiers(int32_t pre_roll_damage, int32_t roll_int,
                                         PostRollCtx ctx) {
    // Take a mutable copy of effectiveness (Delta Stream may modify it below).
    double effectiveness = ctx.effectiveness;

    // Apply roll: integer division matching Python's // operator (truncation for positive).
    int32_t damage = pre_roll_damage * (85 + roll_int) / 100;

    // STAB (TYPELESS never STABs)
    if (ctx.move_type != TYPE_TYPELESS) {
        bool has_stab = has_type(*ctx.attacker, ctx.move_type);
        if (has_stab) {
            double stab_mult = (ctx.attacker->ability == AB_ADAPTABILITY) ? 2.0 : 1.5;
            damage = static_cast<int32_t>(std::floor(damage * stab_mult));
        }
    }

    // Pinch abilities: 1.5x after STAB
    if (ctx.pinch_active)
        damage = static_cast<int32_t>(std::floor(damage * 1.5));

    // Delta Stream: cap SE vs Flying to 1x
    if (ctx.state->weather == WEATHER_STRONG_WIND
            && has_type(*ctx.defender, TYPE_FLYING)
            && effectiveness > 1.0)
        effectiveness = 1.0;

    // Type effectiveness
    damage = static_cast<int32_t>(std::floor(damage * effectiveness));

    // Tinted Lens: 2x for resisted
    if (ctx.attacker->ability == AB_TINTED_LENS && effectiveness < 1.0)
        damage *= 2;

    // Neuroforce: 1.25x for SE
    if (ctx.attacker->ability == AB_NEUROFORCE && effectiveness > 1.0)
        damage = static_cast<int32_t>(std::floor(damage * 1.25));

    // Filter / Solid Rock / Prism Armor: 0.75x from SE
    if (effectiveness > 1.0) {
        if ((ctx.defender->ability == AB_FILTER || ctx.defender->ability == AB_SOLID_ROCK)
                && !ctx.breaks_mold && !in_set(IGNORE_ABILITY_MOVES, ctx.move_id))
            damage = static_cast<int32_t>(std::floor(damage * 0.75));
        else if (ctx.defender->ability == AB_PRISM_ARMOR
                 && !in_set(IGNORE_ABILITY_MOVES, ctx.move_id))
            damage = static_cast<int32_t>(std::floor(damage * 0.75));
    }

    // Aura Break / Dark Aura / Fairy Aura
    std::vector<int32_t> all_active_abilities;
    for (int s = 0; s < 2; ++s) {
        const SideState& side = (s == 0) ? ctx.state->side0 : ctx.state->side1;
        for (int32_t idx : side.active_indices)
            all_active_abilities.push_back(side.team[idx].ability);
    }
    bool has_dark_aura  = false, has_fairy_aura = false, has_aura_break = false;
    for (int32_t ab : all_active_abilities) {
        if (ab == AB_DARK_AURA)  has_dark_aura  = true;
        if (ab == AB_FAIRY_AURA) has_fairy_aura = true;
        if (ab == AB_AURA_BREAK) has_aura_break = true;
    }
    bool aura_break_active = has_aura_break && !ctx.breaks_mold;
    static constexpr double AURA_MULT = 4.0 / 3.0;
    if (ctx.move_type == TYPE_DARK && has_dark_aura)
        damage = static_cast<int32_t>(std::floor(
            damage * (aura_break_active ? 0.75 : AURA_MULT)));
    if (ctx.move_type == TYPE_FAIRY && has_fairy_aura)
        damage = static_cast<int32_t>(std::floor(
            damage * (aura_break_active ? 0.75 : AURA_MULT)));

    // Punk Rock (defender): halve incoming sound damage (breakable)
    if (ctx.defender->ability == AB_PUNK_ROCK
            && (ctx.md_tags & TAG_SOUND) && !ctx.breaks_mold)
        damage = static_cast<int32_t>(std::floor(damage * 0.5));

    // Heatproof: halve Fire damage (breakable)
    if (ctx.defender->ability == AB_HEATPROOF
            && ctx.move_type == TYPE_FIRE && !ctx.breaks_mold)
        damage = static_cast<int32_t>(std::floor(damage * 0.5));

    // Water Bubble (defender): halve Fire damage (breakable)
    if (ctx.defender->ability == AB_WATER_BUBBLE
            && ctx.move_type == TYPE_FIRE && !ctx.breaks_mold)
        damage = static_cast<int32_t>(std::floor(damage * 0.5));

    // Dry Skin: 1.25x from Fire (breakable)
    if (ctx.defender->ability == AB_DRY_SKIN
            && ctx.move_type == TYPE_FIRE && !ctx.breaks_mold)
        damage = static_cast<int32_t>(std::floor(damage * 1.25));

    // Life Orb: 1.3x (suppressed by Magic Room)
    if (ctx.attacker->item == ITEM_LIFE_ORB && !ctx.magic_room)
        damage = static_cast<int32_t>(std::floor(damage * 1.3));

    // Expert Belt: 1.2x on SE
    if (ctx.attacker->item == ITEM_EXPERT_BELT && effectiveness > 1.0 && !ctx.magic_room) {
        static constexpr double EXPERT_BELT_MULT = 4915.0 / 4096.0;
        damage = static_cast<int32_t>(std::floor(damage * EXPERT_BELT_MULT + 0.5));
    }

    // Multiscale: halve at full HP (breakable by MB or ignore-ability moves)
    if (ctx.defender->ability == AB_MULTISCALE && !ctx.breaks_mold
            && !in_set(IGNORE_ABILITY_MOVES, ctx.move_id)) {
        int32_t mhp = ctx.defender->has_max_hp ? ctx.defender->max_hp : ctx.defender->stat_hp;
        int32_t cur = ctx.defender->has_hp    ? ctx.defender->hp    : mhp;
        if (cur == mhp)
            damage = static_cast<int32_t>(std::floor(damage * 0.5));
    }

    // Shadow Shield: halve at full HP
    if (ctx.defender->ability == AB_SHADOW_SHIELD
            && !in_set(IGNORE_ABILITY_MOVES, ctx.move_id)) {
        int32_t mhp = ctx.defender->has_max_hp ? ctx.defender->max_hp : ctx.defender->stat_hp;
        int32_t cur = ctx.defender->has_hp    ? ctx.defender->hp    : mhp;
        if (cur == mhp)
            damage = static_cast<int32_t>(std::floor(damage * 0.5));
    }

    // Ice Scales: halve special damage (breakable)
    if (!ctx.is_physical && ctx.defender->ability == AB_ICE_SCALES && !ctx.breaks_mold
            && !in_set(IGNORE_ABILITY_MOVES, ctx.move_id))
        damage = static_cast<int32_t>(std::floor(damage * 0.5));

    // Fluffy: halve contact; double Fire
    if (ctx.defender->ability == AB_FLUFFY && !in_set(IGNORE_ABILITY_MOVES, ctx.move_id)) {
        if (!ctx.breaks_mold) {
            bool is_contact = (ctx.md_tags & TAG_CONTACT) != 0;
            bool contact_suppressed = (ctx.attacker->ability == AB_LONG_REACH
                                       || ctx.attacker->item == ITEM_PROTECTIVE_PADS);
            int fluffy_num = 1, fluffy_den = 1;
            if (is_contact && !contact_suppressed) fluffy_den *= 2;
            if (ctx.move_type == TYPE_FIRE) fluffy_num *= 2;
            if (fluffy_num != fluffy_den)
                damage = static_cast<int32_t>(std::floor(
                    damage * fluffy_num / static_cast<double>(fluffy_den)));
        }
    }

    // Burn: halve physical damage
    if (ctx.is_physical && ctx.attacker->status == STATUS_BURN
            && ctx.attacker->ability != AB_GUTS && ctx.move_id != MOVE_FACADE)
        damage = static_cast<int32_t>(std::floor(damage * 0.5));

    // Screens, Analytic, Friend Guard (require side context)
    if (ctx.def_side_idx >= 0) {
        int32_t atk_side_idx = 1 - ctx.def_side_idx;
        const SideState& def_side = (ctx.def_side_idx == 0)
                                    ? ctx.state->side0 : ctx.state->side1;

        // Screens and Aurora Veil (bypassed by crits and Infiltrator)
        if (!ctx.is_crit && ctx.attacker->ability != AB_INFILTRATOR) {
            bool is_doubles = (ctx.state->format == FORMAT_DOUBLES);
            static constexpr double SCREEN_DOUBLES = 2732.0 / 4096.0;
            double screen_mult = is_doubles ? SCREEN_DOUBLES : 0.5;

            if (has_side_condition(def_side, SC_AURORA_VEIL))
                damage = static_cast<int32_t>(std::floor(damage * screen_mult));
            else if (ctx.is_physical && has_side_condition(def_side, SC_REFLECT))
                damage = static_cast<int32_t>(std::floor(damage * screen_mult));
            else if (!ctx.is_physical && has_side_condition(def_side, SC_LIGHT_SCREEN))
                damage = static_cast<int32_t>(std::floor(damage * screen_mult));
        }

        // Analytic: 1.3x when moving last
        if (ctx.attacker->ability == AB_ANALYTIC) {
            bool acted_last = false;
            if (ctx.ai_scoring_view) {
                acted_last = (ctx.state->prev_turn_order.size() >= 2
                              && ctx.state->prev_turn_order.back() == atk_side_idx);
            } else {
                acted_last = (ctx.state->turn_order.size() >= 2
                              && ctx.state->turn_order.back() == atk_side_idx);
            }
            if (acted_last)
                damage = static_cast<int32_t>(std::floor(damage * 1.3));
        }

        // Friend Guard (doubles only)
        if (!ctx.breaks_mold) {
            for (int32_t ally_idx : def_side.active_indices) {
                const PokemonState& ally = def_side.team[ally_idx];
                if (&ally != ctx.defender && ally.ability == AB_FRIEND_GUARD) {
                    damage = static_cast<int32_t>(std::floor(damage * 0.75));
                    break;
                }
            }
        }
    }

    return std::max(1, damage);
}

// ---------------------------------------------------------------------------
// Main calculate_damage
// ---------------------------------------------------------------------------
int32_t cpp_calculate_damage(
    const PokemonState& attacker,
    int32_t             move_id,
    const PokemonState& defender,
    const BattleState&  state,
    const LuckProfileC& atk_luck,
    const LuckProfileC& def_luck,
    int32_t             bp_override,
    int32_t             def_side_idx,
    bool                spread_hit,
    int32_t             roll_index,
    bool                ai_scoring_view,
    int32_t             crit_override)
{
    const MoveData& md = lookup_move(move_id);
    bool breaks_mold = is_mold_breaker(attacker.ability);

    // Status moves → 0; zero base_power with no override → 0
    if (md.category == CAT_STATUS) return 0;
    if (md.base_power == 0 && bp_override == 0) return 0;

    // Resolve move type and BP
    int32_t move_type, bp;
    resolve_move_type_and_bp(attacker, move_id, md, state, bp_override, move_type, bp);

    // Semi-invulnerable double damage
    if (has_timed_volatile(defender, VE_SEMI_INVULNERABLE)
            && defender.charging_move_slot >= 0) {
        int32_t charging_move_id = 0;
        switch (defender.charging_move_slot) {
            case 0: charging_move_id = defender.move_id0; break;
            case 1: charging_move_id = defender.move_id1; break;
            case 2: charging_move_id = defender.move_id2; break;
            case 3: charging_move_id = defender.move_id3; break;
        }
        // VE_CHARGING_MOVE wins (called two-turn: slot holds the caller).
        for (const TimedVolatile& tv : defender.timed_volatiles) {
            if (tv.effect == VE_CHARGING_MOVE) { charging_move_id = tv.turns; break; }
        }
        if (semi_invuln_double_dmg(charging_move_id, move_id))
            bp *= 2;
    }

    // Natural Gift with no berry → 0
    if (move_id == MOVE_NATURAL_GIFT && bp == 0) return 0;

    // Knock Off: 1.5x BP when defender holds a knockable item
    if (move_id == MOVE_KNOCK_OFF && defender.item != ITEM_NONE) {
        bool sticky = (defender.ability == AB_STICKY_HOLD && !breaks_mold);
        bool is_mega = in_set(MEGA_ITEMS, defender.item);
        bool is_silvally_memory = (in_set(SILVALLY_SPECIES, defender.species)
                                   && in_set(MEMORY_ITEMS, defender.item));
        bool knockable = !is_mega && !is_silvally_memory && !sticky;
        if (knockable)
            bp = static_cast<int32_t>(std::floor(bp * 1.5));
    }

    // Type immunity
    double effectiveness = type_effectiveness_product(attacker, move_id, move_type, defender, state);
    if (effectiveness == 0.0) return 0;

    bool is_physical = (md.category == CAT_PHYSICAL);

    // Photon Geyser: acts physical if attacker's effective Atk > effective SpA
    if (move_id == MOVE_PHOTON_GEYSER) {
        if (cpp_effective_stat(attacker, 1) > cpp_effective_stat(attacker, 3))
            is_physical = true;
    }

    bool magic_room = has_pseudo_weather(state, PW_MAGIC_ROOM);

    // Determine crit: when crit_override >= 0 the caller pre-resolved crit (and already applied
    // Merciless), so skip both rng_resolve_crit and the Merciless override here.
    bool is_crit;
    if (crit_override >= 0) {
        is_crit = (crit_override == 1);
    } else {
        float crit_chance = get_crit_chance(attacker, defender, md.crit_boost, magic_room);
        const int atk_side_idx_ = (def_side_idx == 0) ? 1 : 0;
        const SideState& atk_ss = (atk_side_idx_ == 0) ? state.side0 : state.side1;
        const SideState& def_ss = (def_side_idx == 0)  ? state.side0 : state.side1;
        const RngLogCtx catb_ctx{
            RngParticipants{
                (int8_t)atk_side_idx_, (int8_t)atk_ss.active_indices[0],
                (int8_t)def_side_idx,  (int8_t)def_ss.active_indices[0]},
            state.turn_number};
        is_crit = rng_resolve_crit(crit_chance, atk_luck.crit_threshold,
                                   atk_luck.random_mode, atk_luck.rng, &catb_ctx);

        // Merciless: always crits poisoned targets (unless defender has crit immunity)
        if (attacker.ability == AB_MERCILESS
                && (defender.status == STATUS_POISON || defender.status == STATUS_TOXIC)
                && defender.ability != AB_BATTLE_ARMOR
                && defender.ability != AB_SHELL_ARMOR
                && defender.ability != AB_MAGMA_ARMOR)
            is_crit = true;
    }

    // Shell Side Arm: compare physical vs special product
    if (move_id == MOVE_SHELL_SIDE_ARM) {
        int32_t phys_atk = cpp_effective_stat(attacker, 1, false);
        int32_t phys_def = cpp_effective_stat(defender, 2, false);
        int32_t spec_atk = cpp_effective_stat(attacker, 3, false);
        int32_t spec_def = cpp_effective_stat(defender, 4, false);
        int64_t phys_product = static_cast<int64_t>(phys_atk) * spec_def;
        int64_t spec_product = static_cast<int64_t>(spec_atk) * phys_def;
        if (phys_product > spec_product) is_physical = true;
        else if (spec_product > phys_product) is_physical = false;
        else {
            // 50/50 tie: use proc_threshold (≥50 → true means physical)
            is_physical = (atk_luck.proc_threshold <= 50.0);
        }
    }

    int32_t atk  = compute_attack_stat(attacker, defender, move_id, md, is_physical, is_crit, state, def_side_idx);
    int32_t def_ = compute_defense_stat(attacker, defender, move_id, md, is_physical, is_crit, state);
    bp = compute_bp(attacker, defender, move_id, md, move_type, bp, state, def_side_idx, is_physical);

    // Pinch abilities: 1.5x after STAB when HP ≤ 1/3 and matching type
    struct PinchEntry { int32_t ability; int32_t type; };
    static const PinchEntry PINCH[] = {
        {AB_BLAZE,   TYPE_FIRE},
        {AB_TORRENT, TYPE_WATER},
        {AB_OVERGROW,TYPE_GRASS},
        {AB_SWARM,   TYPE_BUG},
    };
    bool pinch_active = false;
    for (const auto& p : PINCH) {
        if (attacker.ability == p.ability && move_type == p.type) {
            int32_t mhp = attacker.has_max_hp ? attacker.max_hp : attacker.stat_hp;
            int32_t cur = attacker.has_hp ? attacker.hp : mhp;
            if (cur <= mhp / 3) pinch_active = true;
            break;
        }
    }

    // Base damage formula: Gen 8 exact 4-step integer truncation
    int32_t level = attacker.level;
    int32_t step1 = static_cast<int32_t>(2 * level / 5 + 2);  // int division
    int64_t step2 = static_cast<int64_t>(step1) * bp;
    int64_t step3 = step2 * atk;
    int64_t step4 = step3 / def_;
    int32_t damage = static_cast<int32_t>(step4 / 50 + 2);

    // Spread reduction (doubles): 0.75x
    if (spread_hit
            && (md.target == TARGET_ALL_ADJACENT_FOES || md.target == TARGET_ALL_ADJACENT)
            && state.format == FORMAT_DOUBLES)
        damage = static_cast<int32_t>(std::floor(damage * 0.75));

    // Weather
    damage = apply_weather(damage, move_type, state.weather, state);

    // Crit (1.5x); Sniper adds another 1.5x
    if (is_crit) {
        damage = static_cast<int32_t>(std::floor(damage * 1.5));
        if (attacker.ability == AB_SNIPER)
            damage = static_cast<int32_t>(std::floor(damage * 1.5));
    }

    // Build context for the post-roll modifier chain (all state beyond the roll draw).
    PostRollCtx prc;
    prc.effectiveness  = effectiveness;
    prc.move_type      = move_type;
    prc.move_id        = move_id;
    prc.pinch_active   = pinch_active;
    prc.breaks_mold    = breaks_mold;
    prc.is_physical    = is_physical;
    prc.is_crit        = is_crit;
    prc.magic_room     = magic_room;
    prc.ai_scoring_view = ai_scoring_view;
    prc.def_side_idx   = def_side_idx;
    prc.md_tags        = md.tags;
    prc.attacker       = &attacker;
    prc.defender       = &defender;
    prc.state          = &state;

    // Damage roll: integer arithmetic matching Python: damage * (85 + roll_int) // 100.
    // 16 equiprobable outcomes (roll_int = 0..15); p_chosen = 1/16.
    // roll_index >= 0 = per-hit override from multi-hit loop (bypasses occurrence-keying).
    int32_t roll_int;
    if (roll_index >= 0) {
        roll_int = roll_index;
    } else {
        roll_int = rng_resolve_damage_roll(atk_luck.random_mode, atk_luck.rng,
                                           atk_luck.damage_roll);
        // Annotate the just-logged DAMAGE_ROLL entry with all 16 final damages.
        // This consumes NO RNG: apply_roll_and_modifiers is purely deterministic.
        // Only done when the log is active (solver mode) AND it is the main 16-outcome site.
        AnalyticalRngLog* log_sink = get_analytical_rng_log();
        if (log_sink && !log_sink->entries.empty()) {
            const AnalyticalRngEntry& last = log_sink->entries.back();
            if (last.options_count == 16 && last.options_truncated == 0) {
                int32_t dmg_by_roll[16];
                for (int ri = 0; ri < 16; ++ri)
                    dmg_by_roll[ri] = apply_roll_and_modifiers(damage, ri, prc);
                annotate_last_damage_roll(*log_sink, dmg_by_roll);
            }
        }
    }

    return apply_roll_and_modifiers(damage, roll_int, prc);
}
