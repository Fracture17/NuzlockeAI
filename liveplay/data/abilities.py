# Ability enum and display-name data. Effect logic lives in the engine layer.
# Generated from Showdown abilities.ts; CAP abilities excluded.
from dataclasses import dataclass
from enum import IntEnum


class Ability(IntEnum):
    NONE = 0
    NO_ABILITY = 0
    STENCH = 1
    DRIZZLE = 2
    SPEED_BOOST = 3
    BATTLE_ARMOR = 4
    STURDY = 5
    DAMP = 6
    LIMBER = 7
    SAND_VEIL = 8
    STATIC = 9
    VOLT_ABSORB = 10
    WATER_ABSORB = 11
    OBLIVIOUS = 12
    CLOUD_NINE = 13
    COMPOUND_EYES = 14
    INSOMNIA = 15
    COLOR_CHANGE = 16
    IMMUNITY = 17
    FLASH_FIRE = 18
    SHIELD_DUST = 19
    OWN_TEMPO = 20
    SUCTION_CUPS = 21
    INTIMIDATE = 22
    SHADOW_TAG = 23
    ROUGH_SKIN = 24
    WONDER_GUARD = 25
    LEVITATE = 26
    EFFECT_SPORE = 27
    SYNCHRONIZE = 28
    CLEAR_BODY = 29
    NATURAL_CURE = 30
    LIGHTNING_ROD = 31
    SERENE_GRACE = 32
    SWIFT_SWIM = 33
    CHLOROPHYLL = 34
    ILLUMINATE = 35
    TRACE = 36
    HUGE_POWER = 37
    POISON_POINT = 38
    INNER_FOCUS = 39
    MAGMA_ARMOR = 40
    WATER_VEIL = 41
    MAGNET_PULL = 42
    SOUNDPROOF = 43
    RAIN_DISH = 44
    SAND_STREAM = 45
    PRESSURE = 46
    THICK_FAT = 47
    EARLY_BIRD = 48
    FLAME_BODY = 49
    RUN_AWAY = 50
    KEEN_EYE = 51
    HYPER_CUTTER = 52
    PICKUP = 53
    TRUANT = 54
    HUSTLE = 55
    CUTE_CHARM = 56
    PLUS = 57
    MINUS = 58
    FORECAST = 59
    STICKY_HOLD = 60
    SHED_SKIN = 61
    GUTS = 62
    MARVEL_SCALE = 63
    LIQUID_OOZE = 64
    OVERGROW = 65
    BLAZE = 66
    TORRENT = 67
    SWARM = 68
    ROCK_HEAD = 69
    DROUGHT = 70
    ARENA_TRAP = 71
    VITAL_SPIRIT = 72
    WHITE_SMOKE = 73
    PURE_POWER = 74
    SHELL_ARMOR = 75
    AIR_LOCK = 76
    TANGLED_FEET = 77
    MOTOR_DRIVE = 78
    RIVALRY = 79
    STEADFAST = 80
    SNOW_CLOAK = 81
    GLUTTONY = 82
    ANGER_POINT = 83
    UNBURDEN = 84
    HEATPROOF = 85
    SIMPLE = 86
    DRY_SKIN = 87
    DOWNLOAD = 88
    IRON_FIST = 89
    POISON_HEAL = 90
    ADAPTABILITY = 91
    SKILL_LINK = 92
    HYDRATION = 93
    SOLAR_POWER = 94
    QUICK_FEET = 95
    NORMALIZE = 96
    SNIPER = 97
    MAGIC_GUARD = 98
    NO_GUARD = 99
    STALL = 100
    TECHNICIAN = 101
    LEAF_GUARD = 102
    KLUTZ = 103
    MOLD_BREAKER = 104
    SUPER_LUCK = 105
    AFTERMATH = 106
    ANTICIPATION = 107
    FOREWARN = 108
    UNAWARE = 109
    TINTED_LENS = 110
    FILTER = 111
    SLOW_START = 112
    SCRAPPY = 113
    STORM_DRAIN = 114
    ICE_BODY = 115
    SOLID_ROCK = 116
    SNOW_WARNING = 117
    HONEY_GATHER = 118
    FRISK = 119
    RECKLESS = 120
    MULTITYPE = 121
    FLOWER_GIFT = 122
    BAD_DREAMS = 123
    PICKPOCKET = 124
    SHEER_FORCE = 125
    CONTRARY = 126
    UNNERVE = 127
    DEFIANT = 128
    DEFEATIST = 129
    CURSED_BODY = 130
    HEALER = 131
    FRIEND_GUARD = 132
    WEAK_ARMOR = 133
    HEAVY_METAL = 134
    LIGHT_METAL = 135
    MULTISCALE = 136
    TOXIC_BOOST = 137
    FLARE_BOOST = 138
    HARVEST = 139
    TELEPATHY = 140
    MOODY = 141
    OVERCOAT = 142
    POISON_TOUCH = 143
    REGENERATOR = 144
    BIG_PECKS = 145
    SAND_RUSH = 146
    WONDER_SKIN = 147
    ANALYTIC = 148
    ILLUSION = 149
    IMPOSTER = 150
    INFILTRATOR = 151
    MUMMY = 152
    MOXIE = 153
    JUSTIFIED = 154
    RATTLED = 155
    MAGIC_BOUNCE = 156
    SAP_SIPPER = 157
    PRANKSTER = 158
    SAND_FORCE = 159
    IRON_BARBS = 160
    ZEN_MODE = 161
    VICTORY_STAR = 162
    TURBOBLAZE = 163
    TERAVOLT = 164
    AROMA_VEIL = 165
    FLOWER_VEIL = 166
    CHEEK_POUCH = 167
    PROTEAN = 168
    FUR_COAT = 169
    MAGICIAN = 170
    BULLETPROOF = 171
    COMPETITIVE = 172
    STRONG_JAW = 173
    REFRIGERATE = 174
    SWEET_VEIL = 175
    STANCE_CHANGE = 176
    GALE_WINGS = 177
    MEGA_LAUNCHER = 178
    GRASS_PELT = 179
    SYMBIOSIS = 180
    TOUGH_CLAWS = 181
    PIXILATE = 182
    GOOEY = 183
    AERILATE = 184
    PARENTAL_BOND = 185
    DARK_AURA = 186
    FAIRY_AURA = 187
    AURA_BREAK = 188
    PRIMORDIAL_SEA = 189
    DESOLATE_LAND = 190
    DELTA_STREAM = 191
    STAMINA = 192
    WIMP_OUT = 193
    EMERGENCY_EXIT = 194
    WATER_COMPACTION = 195
    MERCILESS = 196
    SHIELDS_DOWN = 197
    WATER_BUBBLE = 199
    STEELWORKER = 200
    BERSERK = 201
    SLUSH_RUSH = 202
    LONG_REACH = 203
    LIQUID_VOICE = 204
    TRIAGE = 205
    GALVANIZE = 206
    SURGE_SURFER = 207
    SCHOOLING = 208
    DISGUISE = 209
    BATTLE_BOND = 210
    POWER_CONSTRUCT = 211
    CORROSION = 212
    COMATOSE = 213
    QUEENLY_MAJESTY = 214
    INNARDS_OUT = 215
    DANCER = 216
    BATTERY = 217
    FLUFFY = 218
    DAZZLING = 219
    SOUL_HEART = 220
    TANGLING_HAIR = 221
    RECEIVER = 222
    POWER_OF_ALCHEMY = 223
    BEAST_BOOST = 224
    RKS_SYSTEM = 225
    ELECTRIC_SURGE = 226
    PSYCHIC_SURGE = 227
    MISTY_SURGE = 228
    GRASSY_SURGE = 229
    FULL_METAL_BODY = 230
    SHADOW_SHIELD = 231
    PRISM_ARMOR = 232
    NEUROFORCE = 233
    INTREPID_SWORD = 234
    DAUNTLESS_SHIELD = 235
    LIBERO = 236
    BALL_FETCH = 237
    COTTON_DOWN = 238
    PROPELLER_TAIL = 239
    MIRROR_ARMOR = 240
    GULP_MISSILE = 241
    STALWART = 242
    STEAM_ENGINE = 243
    PUNK_ROCK = 244
    SAND_SPIT = 245
    ICE_SCALES = 246
    RIPEN = 247
    ICE_FACE = 248
    POWER_SPOT = 249
    MIMICRY = 250
    SCREEN_CLEANER = 251
    STEELY_SPIRIT = 252
    PERISH_BODY = 253
    WANDERING_SPIRIT = 254
    GORILLA_TACTICS = 255
    NEUTRALIZING_GAS = 256
    PASTEL_VEIL = 257
    HUNGER_SWITCH = 258
    QUICK_DRAW = 259
    UNSEEN_FIST = 260
    CURIOUS_MEDICINE = 261
    TRANSISTOR = 262
    DRAGON_S_MAW = 263
    CHILLING_NEIGH = 264
    GRIM_NEIGH = 265
    AS_ONE_GLASTRIER = 266
    AS_ONE_SPECTRIER = 267
    LINGERING_AROMA = 268
    SEED_SOWER = 269
    THERMAL_EXCHANGE = 270
    ANGER_SHELL = 271
    PURIFYING_SALT = 272
    WELL_BAKED_BODY = 273
    WIND_RIDER = 274
    GUARD_DOG = 275
    ROCKY_PAYLOAD = 276
    WIND_POWER = 277
    ZERO_TO_HERO = 278
    COMMANDER = 279
    ELECTROMORPHOSIS = 280
    PROTOSYNTHESIS = 281
    QUARK_DRIVE = 282
    GOOD_AS_GOLD = 283
    BEADS_OF_RUIN = 284
    TABLETS_OF_RUIN = 286
    VESSEL_OF_RUIN = 287
    SWORD_OF_RUIN = 285
    ORICHALCUM_PULSE = 288
    HADRON_ENGINE = 289
    OPPORTUNIST = 290
    CUD_CHEW = 291
    SHARPNESS = 292
    SUPREME_OVERLORD = 293
    COSTAR = 294
    TOXIC_DEBRIS = 295
    ARMOR_TAIL = 296
    EARTH_EATER = 297
    MYCELIUM_MIGHT = 298
    HOSPITALITY = 299
    MIND_S_EYE = 300
    EMBODY_ASPECT_TEAL = 301
    EMBODY_ASPECT_WELLSPRING = 302
    EMBODY_ASPECT_HEARTHFLAME = 303
    EMBODY_ASPECT_CORNERSTONE = 304
    TOXIC_CHAIN = 305
    SUPERSWEET_SYRUP = 306
    TERA_SHIFT = 307
    TERA_SHELL = 308
    TERAFORM_ZERO = 309
    POISON_PUPPETEER = 310
    PIERCING_DRILL = 311
    DRAGONIZE = 312
    MEGA_SOL = 315
    SPICY_SPRAY = 318


@dataclass(frozen=True)
class AbilityData:
    name: str  # display name for logging


ABILITY_DATA: dict[Ability, AbilityData] = {
    Ability.NO_ABILITY: AbilityData("No Ability"),
    Ability.STENCH: AbilityData("Stench"),
    Ability.DRIZZLE: AbilityData("Drizzle"),
    Ability.SPEED_BOOST: AbilityData("Speed Boost"),
    Ability.BATTLE_ARMOR: AbilityData("Battle Armor"),
    Ability.STURDY: AbilityData("Sturdy"),
    Ability.DAMP: AbilityData("Damp"),
    Ability.LIMBER: AbilityData("Limber"),
    Ability.SAND_VEIL: AbilityData("Sand Veil"),
    Ability.STATIC: AbilityData("Static"),
    Ability.VOLT_ABSORB: AbilityData("Volt Absorb"),
    Ability.WATER_ABSORB: AbilityData("Water Absorb"),
    Ability.OBLIVIOUS: AbilityData("Oblivious"),
    Ability.CLOUD_NINE: AbilityData("Cloud Nine"),
    Ability.COMPOUND_EYES: AbilityData("Compound Eyes"),
    Ability.INSOMNIA: AbilityData("Insomnia"),
    Ability.COLOR_CHANGE: AbilityData("Color Change"),
    Ability.IMMUNITY: AbilityData("Immunity"),
    Ability.FLASH_FIRE: AbilityData("Flash Fire"),
    Ability.SHIELD_DUST: AbilityData("Shield Dust"),
    Ability.OWN_TEMPO: AbilityData("Own Tempo"),
    Ability.SUCTION_CUPS: AbilityData("Suction Cups"),
    Ability.INTIMIDATE: AbilityData("Intimidate"),
    Ability.SHADOW_TAG: AbilityData("Shadow Tag"),
    Ability.ROUGH_SKIN: AbilityData("Rough Skin"),
    Ability.WONDER_GUARD: AbilityData("Wonder Guard"),
    Ability.LEVITATE: AbilityData("Levitate"),
    Ability.EFFECT_SPORE: AbilityData("Effect Spore"),
    Ability.SYNCHRONIZE: AbilityData("Synchronize"),
    Ability.CLEAR_BODY: AbilityData("Clear Body"),
    Ability.NATURAL_CURE: AbilityData("Natural Cure"),
    Ability.LIGHTNING_ROD: AbilityData("Lightning Rod"),
    Ability.SERENE_GRACE: AbilityData("Serene Grace"),
    Ability.SWIFT_SWIM: AbilityData("Swift Swim"),
    Ability.CHLOROPHYLL: AbilityData("Chlorophyll"),
    Ability.ILLUMINATE: AbilityData("Illuminate"),
    Ability.TRACE: AbilityData("Trace"),
    Ability.HUGE_POWER: AbilityData("Huge Power"),
    Ability.POISON_POINT: AbilityData("Poison Point"),
    Ability.INNER_FOCUS: AbilityData("Inner Focus"),
    Ability.MAGMA_ARMOR: AbilityData("Magma Armor"),
    Ability.WATER_VEIL: AbilityData("Water Veil"),
    Ability.MAGNET_PULL: AbilityData("Magnet Pull"),
    Ability.SOUNDPROOF: AbilityData("Soundproof"),
    Ability.RAIN_DISH: AbilityData("Rain Dish"),
    Ability.SAND_STREAM: AbilityData("Sand Stream"),
    Ability.PRESSURE: AbilityData("Pressure"),
    Ability.THICK_FAT: AbilityData("Thick Fat"),
    Ability.EARLY_BIRD: AbilityData("Early Bird"),
    Ability.FLAME_BODY: AbilityData("Flame Body"),
    Ability.RUN_AWAY: AbilityData("Run Away"),
    Ability.KEEN_EYE: AbilityData("Keen Eye"),
    Ability.HYPER_CUTTER: AbilityData("Hyper Cutter"),
    Ability.PICKUP: AbilityData("Pickup"),
    Ability.TRUANT: AbilityData("Truant"),
    Ability.HUSTLE: AbilityData("Hustle"),
    Ability.CUTE_CHARM: AbilityData("Cute Charm"),
    Ability.PLUS: AbilityData("Plus"),
    Ability.MINUS: AbilityData("Minus"),
    Ability.FORECAST: AbilityData("Forecast"),
    Ability.STICKY_HOLD: AbilityData("Sticky Hold"),
    Ability.SHED_SKIN: AbilityData("Shed Skin"),
    Ability.GUTS: AbilityData("Guts"),
    Ability.MARVEL_SCALE: AbilityData("Marvel Scale"),
    Ability.LIQUID_OOZE: AbilityData("Liquid Ooze"),
    Ability.OVERGROW: AbilityData("Overgrow"),
    Ability.BLAZE: AbilityData("Blaze"),
    Ability.TORRENT: AbilityData("Torrent"),
    Ability.SWARM: AbilityData("Swarm"),
    Ability.ROCK_HEAD: AbilityData("Rock Head"),
    Ability.DROUGHT: AbilityData("Drought"),
    Ability.ARENA_TRAP: AbilityData("Arena Trap"),
    Ability.VITAL_SPIRIT: AbilityData("Vital Spirit"),
    Ability.WHITE_SMOKE: AbilityData("White Smoke"),
    Ability.PURE_POWER: AbilityData("Pure Power"),
    Ability.SHELL_ARMOR: AbilityData("Shell Armor"),
    Ability.AIR_LOCK: AbilityData("Air Lock"),
    Ability.TANGLED_FEET: AbilityData("Tangled Feet"),
    Ability.MOTOR_DRIVE: AbilityData("Motor Drive"),
    Ability.RIVALRY: AbilityData("Rivalry"),
    Ability.STEADFAST: AbilityData("Steadfast"),
    Ability.SNOW_CLOAK: AbilityData("Snow Cloak"),
    Ability.GLUTTONY: AbilityData("Gluttony"),
    Ability.ANGER_POINT: AbilityData("Anger Point"),
    Ability.UNBURDEN: AbilityData("Unburden"),
    Ability.HEATPROOF: AbilityData("Heatproof"),
    Ability.SIMPLE: AbilityData("Simple"),
    Ability.DRY_SKIN: AbilityData("Dry Skin"),
    Ability.DOWNLOAD: AbilityData("Download"),
    Ability.IRON_FIST: AbilityData("Iron Fist"),
    Ability.POISON_HEAL: AbilityData("Poison Heal"),
    Ability.ADAPTABILITY: AbilityData("Adaptability"),
    Ability.SKILL_LINK: AbilityData("Skill Link"),
    Ability.HYDRATION: AbilityData("Hydration"),
    Ability.SOLAR_POWER: AbilityData("Solar Power"),
    Ability.QUICK_FEET: AbilityData("Quick Feet"),
    Ability.NORMALIZE: AbilityData("Normalize"),
    Ability.SNIPER: AbilityData("Sniper"),
    Ability.MAGIC_GUARD: AbilityData("Magic Guard"),
    Ability.NO_GUARD: AbilityData("No Guard"),
    Ability.STALL: AbilityData("Stall"),
    Ability.TECHNICIAN: AbilityData("Technician"),
    Ability.LEAF_GUARD: AbilityData("Leaf Guard"),
    Ability.KLUTZ: AbilityData("Klutz"),
    Ability.MOLD_BREAKER: AbilityData("Mold Breaker"),
    Ability.SUPER_LUCK: AbilityData("Super Luck"),
    Ability.AFTERMATH: AbilityData("Aftermath"),
    Ability.ANTICIPATION: AbilityData("Anticipation"),
    Ability.FOREWARN: AbilityData("Forewarn"),
    Ability.UNAWARE: AbilityData("Unaware"),
    Ability.TINTED_LENS: AbilityData("Tinted Lens"),
    Ability.FILTER: AbilityData("Filter"),
    Ability.SLOW_START: AbilityData("Slow Start"),
    Ability.SCRAPPY: AbilityData("Scrappy"),
    Ability.STORM_DRAIN: AbilityData("Storm Drain"),
    Ability.ICE_BODY: AbilityData("Ice Body"),
    Ability.SOLID_ROCK: AbilityData("Solid Rock"),
    Ability.SNOW_WARNING: AbilityData("Snow Warning"),
    Ability.HONEY_GATHER: AbilityData("Honey Gather"),
    Ability.FRISK: AbilityData("Frisk"),
    Ability.RECKLESS: AbilityData("Reckless"),
    Ability.MULTITYPE: AbilityData("Multitype"),
    Ability.FLOWER_GIFT: AbilityData("Flower Gift"),
    Ability.BAD_DREAMS: AbilityData("Bad Dreams"),
    Ability.PICKPOCKET: AbilityData("Pickpocket"),
    Ability.SHEER_FORCE: AbilityData("Sheer Force"),
    Ability.CONTRARY: AbilityData("Contrary"),
    Ability.UNNERVE: AbilityData("Unnerve"),
    Ability.DEFIANT: AbilityData("Defiant"),
    Ability.DEFEATIST: AbilityData("Defeatist"),
    Ability.CURSED_BODY: AbilityData("Cursed Body"),
    Ability.HEALER: AbilityData("Healer"),
    Ability.FRIEND_GUARD: AbilityData("Friend Guard"),
    Ability.WEAK_ARMOR: AbilityData("Weak Armor"),
    Ability.HEAVY_METAL: AbilityData("Heavy Metal"),
    Ability.LIGHT_METAL: AbilityData("Light Metal"),
    Ability.MULTISCALE: AbilityData("Multiscale"),
    Ability.TOXIC_BOOST: AbilityData("Toxic Boost"),
    Ability.FLARE_BOOST: AbilityData("Flare Boost"),
    Ability.HARVEST: AbilityData("Harvest"),
    Ability.TELEPATHY: AbilityData("Telepathy"),
    Ability.MOODY: AbilityData("Moody"),
    Ability.OVERCOAT: AbilityData("Overcoat"),
    Ability.POISON_TOUCH: AbilityData("Poison Touch"),
    Ability.REGENERATOR: AbilityData("Regenerator"),
    Ability.BIG_PECKS: AbilityData("Big Pecks"),
    Ability.SAND_RUSH: AbilityData("Sand Rush"),
    Ability.WONDER_SKIN: AbilityData("Wonder Skin"),
    Ability.ANALYTIC: AbilityData("Analytic"),
    Ability.ILLUSION: AbilityData("Illusion"),
    Ability.IMPOSTER: AbilityData("Imposter"),
    Ability.INFILTRATOR: AbilityData("Infiltrator"),
    Ability.MUMMY: AbilityData("Mummy"),
    Ability.MOXIE: AbilityData("Moxie"),
    Ability.JUSTIFIED: AbilityData("Justified"),
    Ability.RATTLED: AbilityData("Rattled"),
    Ability.MAGIC_BOUNCE: AbilityData("Magic Bounce"),
    Ability.SAP_SIPPER: AbilityData("Sap Sipper"),
    Ability.PRANKSTER: AbilityData("Prankster"),
    Ability.SAND_FORCE: AbilityData("Sand Force"),
    Ability.IRON_BARBS: AbilityData("Iron Barbs"),
    Ability.ZEN_MODE: AbilityData("Zen Mode"),
    Ability.VICTORY_STAR: AbilityData("Victory Star"),
    Ability.TURBOBLAZE: AbilityData("Turboblaze"),
    Ability.TERAVOLT: AbilityData("Teravolt"),
    Ability.AROMA_VEIL: AbilityData("Aroma Veil"),
    Ability.FLOWER_VEIL: AbilityData("Flower Veil"),
    Ability.CHEEK_POUCH: AbilityData("Cheek Pouch"),
    Ability.PROTEAN: AbilityData("Protean"),
    Ability.FUR_COAT: AbilityData("Fur Coat"),
    Ability.MAGICIAN: AbilityData("Magician"),
    Ability.BULLETPROOF: AbilityData("Bulletproof"),
    Ability.COMPETITIVE: AbilityData("Competitive"),
    Ability.STRONG_JAW: AbilityData("Strong Jaw"),
    Ability.REFRIGERATE: AbilityData("Refrigerate"),
    Ability.SWEET_VEIL: AbilityData("Sweet Veil"),
    Ability.STANCE_CHANGE: AbilityData("Stance Change"),
    Ability.GALE_WINGS: AbilityData("Gale Wings"),
    Ability.MEGA_LAUNCHER: AbilityData("Mega Launcher"),
    Ability.GRASS_PELT: AbilityData("Grass Pelt"),
    Ability.SYMBIOSIS: AbilityData("Symbiosis"),
    Ability.TOUGH_CLAWS: AbilityData("Tough Claws"),
    Ability.PIXILATE: AbilityData("Pixilate"),
    Ability.GOOEY: AbilityData("Gooey"),
    Ability.AERILATE: AbilityData("Aerilate"),
    Ability.PARENTAL_BOND: AbilityData("Parental Bond"),
    Ability.DARK_AURA: AbilityData("Dark Aura"),
    Ability.FAIRY_AURA: AbilityData("Fairy Aura"),
    Ability.AURA_BREAK: AbilityData("Aura Break"),
    Ability.PRIMORDIAL_SEA: AbilityData("Primordial Sea"),
    Ability.DESOLATE_LAND: AbilityData("Desolate Land"),
    Ability.DELTA_STREAM: AbilityData("Delta Stream"),
    Ability.STAMINA: AbilityData("Stamina"),
    Ability.WIMP_OUT: AbilityData("Wimp Out"),
    Ability.EMERGENCY_EXIT: AbilityData("Emergency Exit"),
    Ability.WATER_COMPACTION: AbilityData("Water Compaction"),
    Ability.MERCILESS: AbilityData("Merciless"),
    Ability.SHIELDS_DOWN: AbilityData("Shields Down"),
    Ability.WATER_BUBBLE: AbilityData("Water Bubble"),
    Ability.STEELWORKER: AbilityData("Steelworker"),
    Ability.BERSERK: AbilityData("Berserk"),
    Ability.SLUSH_RUSH: AbilityData("Slush Rush"),
    Ability.LONG_REACH: AbilityData("Long Reach"),
    Ability.LIQUID_VOICE: AbilityData("Liquid Voice"),
    Ability.TRIAGE: AbilityData("Triage"),
    Ability.GALVANIZE: AbilityData("Galvanize"),
    Ability.SURGE_SURFER: AbilityData("Surge Surfer"),
    Ability.SCHOOLING: AbilityData("Schooling"),
    Ability.DISGUISE: AbilityData("Disguise"),
    Ability.BATTLE_BOND: AbilityData("Battle Bond"),
    Ability.POWER_CONSTRUCT: AbilityData("Power Construct"),
    Ability.CORROSION: AbilityData("Corrosion"),
    Ability.COMATOSE: AbilityData("Comatose"),
    Ability.QUEENLY_MAJESTY: AbilityData("Queenly Majesty"),
    Ability.INNARDS_OUT: AbilityData("Innards Out"),
    Ability.DANCER: AbilityData("Dancer"),
    Ability.BATTERY: AbilityData("Battery"),
    Ability.FLUFFY: AbilityData("Fluffy"),
    Ability.DAZZLING: AbilityData("Dazzling"),
    Ability.SOUL_HEART: AbilityData("Soul-Heart"),
    Ability.TANGLING_HAIR: AbilityData("Tangling Hair"),
    Ability.RECEIVER: AbilityData("Receiver"),
    Ability.POWER_OF_ALCHEMY: AbilityData("Power of Alchemy"),
    Ability.BEAST_BOOST: AbilityData("Beast Boost"),
    Ability.RKS_SYSTEM: AbilityData("RKS System"),
    Ability.ELECTRIC_SURGE: AbilityData("Electric Surge"),
    Ability.PSYCHIC_SURGE: AbilityData("Psychic Surge"),
    Ability.MISTY_SURGE: AbilityData("Misty Surge"),
    Ability.GRASSY_SURGE: AbilityData("Grassy Surge"),
    Ability.FULL_METAL_BODY: AbilityData("Full Metal Body"),
    Ability.SHADOW_SHIELD: AbilityData("Shadow Shield"),
    Ability.PRISM_ARMOR: AbilityData("Prism Armor"),
    Ability.NEUROFORCE: AbilityData("Neuroforce"),
    Ability.INTREPID_SWORD: AbilityData("Intrepid Sword"),
    Ability.DAUNTLESS_SHIELD: AbilityData("Dauntless Shield"),
    Ability.LIBERO: AbilityData("Libero"),
    Ability.BALL_FETCH: AbilityData("Ball Fetch"),
    Ability.COTTON_DOWN: AbilityData("Cotton Down"),
    Ability.PROPELLER_TAIL: AbilityData("Propeller Tail"),
    Ability.MIRROR_ARMOR: AbilityData("Mirror Armor"),
    Ability.GULP_MISSILE: AbilityData("Gulp Missile"),
    Ability.STALWART: AbilityData("Stalwart"),
    Ability.STEAM_ENGINE: AbilityData("Steam Engine"),
    Ability.PUNK_ROCK: AbilityData("Punk Rock"),
    Ability.SAND_SPIT: AbilityData("Sand Spit"),
    Ability.ICE_SCALES: AbilityData("Ice Scales"),
    Ability.RIPEN: AbilityData("Ripen"),
    Ability.ICE_FACE: AbilityData("Ice Face"),
    Ability.POWER_SPOT: AbilityData("Power Spot"),
    Ability.MIMICRY: AbilityData("Mimicry"),
    Ability.SCREEN_CLEANER: AbilityData("Screen Cleaner"),
    Ability.STEELY_SPIRIT: AbilityData("Steely Spirit"),
    Ability.PERISH_BODY: AbilityData("Perish Body"),
    Ability.WANDERING_SPIRIT: AbilityData("Wandering Spirit"),
    Ability.GORILLA_TACTICS: AbilityData("Gorilla Tactics"),
    Ability.NEUTRALIZING_GAS: AbilityData("Neutralizing Gas"),
    Ability.PASTEL_VEIL: AbilityData("Pastel Veil"),
    Ability.HUNGER_SWITCH: AbilityData("Hunger Switch"),
    Ability.QUICK_DRAW: AbilityData("Quick Draw"),
    Ability.UNSEEN_FIST: AbilityData("Unseen Fist"),
    Ability.CURIOUS_MEDICINE: AbilityData("Curious Medicine"),
    Ability.TRANSISTOR: AbilityData("Transistor"),
    Ability.DRAGON_S_MAW: AbilityData("Dragon's Maw"),
    Ability.CHILLING_NEIGH: AbilityData("Chilling Neigh"),
    Ability.GRIM_NEIGH: AbilityData("Grim Neigh"),
    Ability.AS_ONE_GLASTRIER: AbilityData("As One (Glastrier)"),
    Ability.AS_ONE_SPECTRIER: AbilityData("As One (Spectrier)"),
    Ability.LINGERING_AROMA: AbilityData("Lingering Aroma"),
    Ability.SEED_SOWER: AbilityData("Seed Sower"),
    Ability.THERMAL_EXCHANGE: AbilityData("Thermal Exchange"),
    Ability.ANGER_SHELL: AbilityData("Anger Shell"),
    Ability.PURIFYING_SALT: AbilityData("Purifying Salt"),
    Ability.WELL_BAKED_BODY: AbilityData("Well-Baked Body"),
    Ability.WIND_RIDER: AbilityData("Wind Rider"),
    Ability.GUARD_DOG: AbilityData("Guard Dog"),
    Ability.ROCKY_PAYLOAD: AbilityData("Rocky Payload"),
    Ability.WIND_POWER: AbilityData("Wind Power"),
    Ability.ZERO_TO_HERO: AbilityData("Zero to Hero"),
    Ability.COMMANDER: AbilityData("Commander"),
    Ability.ELECTROMORPHOSIS: AbilityData("Electromorphosis"),
    Ability.PROTOSYNTHESIS: AbilityData("Protosynthesis"),
    Ability.QUARK_DRIVE: AbilityData("Quark Drive"),
    Ability.GOOD_AS_GOLD: AbilityData("Good as Gold"),
    Ability.BEADS_OF_RUIN: AbilityData("Beads of Ruin"),
    Ability.TABLETS_OF_RUIN: AbilityData("Tablets of Ruin"),
    Ability.VESSEL_OF_RUIN: AbilityData("Vessel of Ruin"),
    Ability.SWORD_OF_RUIN: AbilityData("Sword of Ruin"),
    Ability.ORICHALCUM_PULSE: AbilityData("Orichalcum Pulse"),
    Ability.HADRON_ENGINE: AbilityData("Hadron Engine"),
    Ability.OPPORTUNIST: AbilityData("Opportunist"),
    Ability.CUD_CHEW: AbilityData("Cud Chew"),
    Ability.SHARPNESS: AbilityData("Sharpness"),
    Ability.SUPREME_OVERLORD: AbilityData("Supreme Overlord"),
    Ability.COSTAR: AbilityData("Costar"),
    Ability.TOXIC_DEBRIS: AbilityData("Toxic Debris"),
    Ability.ARMOR_TAIL: AbilityData("Armor Tail"),
    Ability.EARTH_EATER: AbilityData("Earth Eater"),
    Ability.MYCELIUM_MIGHT: AbilityData("Mycelium Might"),
    Ability.HOSPITALITY: AbilityData("Hospitality"),
    Ability.MIND_S_EYE: AbilityData("Mind's Eye"),
    Ability.EMBODY_ASPECT_TEAL: AbilityData("Embody Aspect (Teal)"),
    Ability.EMBODY_ASPECT_WELLSPRING: AbilityData("Embody Aspect (Wellspring)"),
    Ability.EMBODY_ASPECT_HEARTHFLAME: AbilityData("Embody Aspect (Hearthflame)"),
    Ability.EMBODY_ASPECT_CORNERSTONE: AbilityData("Embody Aspect (Cornerstone)"),
    Ability.TOXIC_CHAIN: AbilityData("Toxic Chain"),
    Ability.SUPERSWEET_SYRUP: AbilityData("Supersweet Syrup"),
    Ability.TERA_SHIFT: AbilityData("Tera Shift"),
    Ability.TERA_SHELL: AbilityData("Tera Shell"),
    Ability.TERAFORM_ZERO: AbilityData("Teraform Zero"),
    Ability.POISON_PUPPETEER: AbilityData("Poison Puppeteer"),
    Ability.PIERCING_DRILL: AbilityData("Piercing Drill"),
    Ability.DRAGONIZE: AbilityData("Dragonize"),
    Ability.MEGA_SOL: AbilityData("Mega Sol"),
    Ability.SPICY_SPRAY: AbilityData("Spicy Spray"),
}

# Abilities that bypass defender ability immunities
MOLD_BREAKER_ABILITIES = frozenset({
    Ability.MOLD_BREAKER, Ability.TURBOBLAZE, Ability.TERAVOLT,
})
