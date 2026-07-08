# Item enum and display-name data. Effect logic lives in the engine layer.
# Generated from Showdown items.ts; Z-crystals and Past items excluded.
from dataclasses import dataclass
from enum import IntEnum

from liveplay.data.types import Type


class Item(IntEnum):
    NONE = 0
    VILE_VIAL = -2
    MASTER_BALL = 1
    ULTRA_BALL = 2
    GREAT_BALL = 3
    POKE_BALL = 4
    SAFARI_BALL = 5
    BERRY_JUICE = 34
    NET_BALL = 6
    DIVE_BALL = 7
    NEST_BALL = 8
    REPEAT_BALL = 9
    TIMER_BALL = 10
    LUXURY_BALL = 11
    PREMIER_BALL = 12
    DUSK_BALL = 13
    HEAL_BALL = 14
    QUICK_BALL = 15
    CHERISH_BALL = 16
    SUN_STONE = 80
    MOON_STONE = 81
    FIRE_STONE = 82
    THUNDER_STONE = 83
    WATER_STONE = 84
    LEAF_STONE = 85
    RARE_BONE = 106
    SHINY_STONE = 107
    DUSK_STONE = 108
    DAWN_STONE = 109
    OVAL_STONE = 110
    GRISEOUS_ORB = 112
    ADAMANT_ORB = 135
    LUSTROUS_ORB = 136
    LEEK = 259
    THICK_CLUB = 260

    # Mega stones and primal orbs (Showdown item IDs)
    BLUE_ORB = 41
    RED_ORB = 40
    GARCHOMPITE = 573
    ABOMASITE = 575
    ABSOLITE = 576
    AERODACTYLITE = 577
    AGGRONITE = 578
    ALAKAZITE = 579
    AMPHAROSITE = 580
    BANETTITE = 582
    BLASTOISINITE = 583
    BLAZIKENITE = 584
    CHARIZARDITE_X = 585
    CHARIZARDITE_Y = 586
    GARDEVOIRITE = 587
    GENGARITE = 588
    GYARADOSITE = 589
    HERACRONITE = 590
    HOUNDOOMINITE = 591
    KANGASKHANITE = 592
    LUCARIONITE = 594
    MANECTITE = 596
    MAWILITE = 598
    MEDICHAMITE = 599
    PINSIRITE = 602
    SCIZORITE = 605
    TYRANITARITE = 607
    VENUSAURITE = 608
    SWAMPERTITE = 612
    SCEPTILITE = 613
    SABLENITE = 614
    ALTARIANITE = 615
    GALLADITE = 616
    AUDINITE = 617
    METAGROSSITE = 618
    SHARPEDONITE = 619
    SLOWBRONITE = 620
    STEELIXITE = 621
    PIDGEOTITE = 622
    GLALITITE = 623
    CAMERUPTITE = 625
    LOPUNNITE = 626
    SALAMENCITE = 627
    BEEDRILLITE = 628
    LATIASITE = 629
    LATIOSITE = 630

    CHERI_BERRY = 149
    CHESTO_BERRY = 150
    PECHA_BERRY = 151
    RAWST_BERRY = 152
    ASPEAR_BERRY = 153
    LEPPA_BERRY = 154
    ORAN_BERRY = 155
    PERSIM_BERRY = 156
    LUM_BERRY = 157
    SITRUS_BERRY = 158
    FIGY_BERRY = 159
    WIKI_BERRY = 160
    MAGO_BERRY = 161
    AGUAV_BERRY = 162
    IAPAPA_BERRY = 163
    POMEG_BERRY = 169
    KELPSY_BERRY = 170
    QUALOT_BERRY = 171
    HONDEW_BERRY = 172
    GREPA_BERRY = 173
    TAMATO_BERRY = 174
    OCCA_BERRY = 184
    PASSHO_BERRY = 185
    WACAN_BERRY = 186
    RINDO_BERRY = 187
    YACHE_BERRY = 188
    CHOPLE_BERRY = 189
    KEBIA_BERRY = 190
    SHUCA_BERRY = 191
    COBA_BERRY = 192
    PAYAPA_BERRY = 193
    TANGA_BERRY = 194
    CHARTI_BERRY = 195
    KASIB_BERRY = 196
    HABAN_BERRY = 197
    COLBUR_BERRY = 198
    BABIRI_BERRY = 199
    CHILAN_BERRY = 200
    LIECHI_BERRY = 201
    GANLON_BERRY = 202
    SALAC_BERRY = 203
    PETAYA_BERRY = 204
    APICOT_BERRY = 205
    LANSAT_BERRY = 206
    STARF_BERRY = 207
    ENIGMA_BERRY = 208
    MICLE_BERRY = 209
    CUSTAP_BERRY = 210
    JABOCA_BERRY = 211
    ROWAP_BERRY = 212
    BRIGHT_POWDER = 213
    WHITE_HERB = 214
    QUICK_CLAW = 217
    MENTAL_HERB = 219
    CHOICE_BAND = 220
    KING_S_ROCK = 221
    SILVER_POWDER = 222
    SOUL_DEW = 225
    FOCUS_BAND = 230
    SCOPE_LENS = 232
    METAL_COAT = 233
    LEFTOVERS = 234
    DRAGON_SCALE = 235
    LIGHT_BALL = 236
    SOFT_SAND = 237
    HARD_STONE = 238
    MIRACLE_SEED = 239
    BLACK_GLASSES = 240
    BLACK_BELT = 241
    MAGNET = 242
    MYSTIC_WATER = 243
    SHARP_BEAK = 244
    POISON_BARB = 245
    NEVER_MELT_ICE = 246
    SPELL_TAG = 247
    TWISTED_SPOON = 248
    CHARCOAL = 249
    DRAGON_FANG = 250
    SILK_SCARF = 251
    UP_GRADE = 252
    SHELL_BELL = 253
    WIDE_LENS = 265
    MUSCLE_BAND = 266
    WISE_GLASSES = 267
    EXPERT_BELT = 268
    LIGHT_CLAY = 269
    LIFE_ORB = 270
    POWER_HERB = 271
    TOXIC_ORB = 272
    FLAME_ORB = 273
    FOCUS_SASH = 275
    ZOOM_LENS = 276
    METRONOME = 277
    IRON_BALL = 278
    LAGGING_TAIL = 279
    DESTINY_KNOT = 280
    BLACK_SLUDGE = 281
    ICY_ROCK = 282
    SMOOTH_ROCK = 283
    HEAT_ROCK = 284
    DAMP_ROCK = 285
    GRIP_CLAW = 286
    CHOICE_SCARF = 287
    STICKY_BARB = 288
    POWER_BRACER = 289
    POWER_BELT = 290
    POWER_LENS = 291
    POWER_BAND = 292
    POWER_ANKLET = 293
    POWER_WEIGHT = 294
    SHED_SHELL = 295
    BIG_ROOT = 296
    CHOICE_SPECS = 297
    FLAME_PLATE = 298
    SPLASH_PLATE = 299
    ZAP_PLATE = 300
    MEADOW_PLATE = 301
    ICICLE_PLATE = 302
    FIST_PLATE = 303
    TOXIC_PLATE = 304
    EARTH_PLATE = 305
    SKY_PLATE = 306
    MIND_PLATE = 307
    INSECT_PLATE = 308
    STONE_PLATE = 309
    SPOOKY_PLATE = 310
    DRACO_PLATE = 311
    DREAD_PLATE = 312
    IRON_PLATE = 313
    PROTECTOR = 321
    ELECTIRIZER = 322
    MAGMARIZER = 323
    DUBIOUS_DISC = 324
    REAPER_CLOTH = 325
    RAZOR_CLAW = 326
    RAZOR_FANG = 327
    FAST_BALL = 492
    LEVEL_BALL = 493
    LURE_BALL = 494
    HEAVY_BALL = 495
    LOVE_BALL = 496
    FRIEND_BALL = 497
    MOON_BALL = 498
    SPORT_BALL = 499
    PARK_BALL = 500
    PRISM_SCALE = 537
    EVIOLITE = 538
    FLOAT_STONE = 539
    ROCKY_HELMET = 540
    AIR_BALLOON = 541
    RED_CARD = 542
    RING_TARGET = 543
    BINDING_BAND = 544
    ABSORB_BULB = 545
    CELL_BATTERY = 546
    EJECT_BUTTON = 547
    NORMAL_GEM = 564
    FIRE_GEM = 4001
    WATER_GEM = 4002
    GRASS_GEM = 4003
    ELECTRIC_GEM = 4004
    ICE_GEM = 4005
    FIGHTING_GEM = 4006
    POISON_GEM = 4007
    GROUND_GEM = 4008
    FLYING_GEM = 4009
    PSYCHIC_GEM = 4010
    BUG_GEM = 4011
    ROCK_GEM = 4012
    GHOST_GEM = 4013
    DRAGON_GEM = 4014
    DARK_GEM = 4015
    STEEL_GEM = 4016
    FAIRY_GEM = 4017
    PRETTY_FEATHER = 571
    DREAM_BALL = 576
    BIG_NUGGET = 581
    WEAKNESS_POLICY = 639
    ASSAULT_VEST = 640
    PIXIE_PLATE = 644
    LUMINOUS_MOSS = 648
    SNOWBALL = 649
    SAFETY_GOGGLES = 650
    ROSELI_BERRY = 686
    KEE_BERRY = 687
    MARANGA_BERRY = 688
    BOTTLE_CAP = 795
    GOLD_BOTTLE_CAP = 796
    ADRENALINE_ORB = 846
    ICE_STONE = 849
    BEAST_BALL = 851
    TERRAIN_EXTENDER = 879
    PROTECTIVE_PADS = 880
    ELECTRIC_SEED = 881
    PSYCHIC_SEED = 882
    MISTY_SEED = 883
    GRASSY_SEED = 884
    RUSTED_SWORD = 1103
    RUSTED_SHIELD = 1104
    STRAWBERRY_SWEET = 1109
    LOVE_SWEET = 1110
    BERRY_SWEET = 1111
    CLOVER_SWEET = 1112
    FLOWER_SWEET = 1113
    STAR_SWEET = 1114
    RIBBON_SWEET = 1115
    SWEET_APPLE = 1116
    TART_APPLE = 1117
    THROAT_SPRAY = 1118
    EJECT_PACK = 1119
    HEAVY_DUTY_BOOTS = 1120
    BLUNDER_POLICY = 1121
    ROOM_SERVICE = 1122
    UTILITY_UMBRELLA = 1123
    CRACKED_POT = 1253
    CHIPPED_POT = 1254
    GALARICA_CUFF = 1582
    GALARICA_WREATH = 1592
    ADAMANT_CRYSTAL = 1777
    LUSTROUS_GLOBE = 1778
    GRISEOUS_CORE = 1779
    STRANGE_BALL = 1785
    MALICIOUS_ARMOR = 1861
    PUNCHING_GLOVE = 1884
    COVERT_CLOAK = 1885
    LOADED_DICE = 1886
    AUSPICIOUS_ARMOR = 2344
    FAIRY_FEATHER = 2401
    SYRUPY_APPLE = 2402
    UNREMARKABLE_TEACUP = 2403
    MASTERPIECE_TEACUP = 2404
    CORNERSTONE_MASK = 2406
    WELLSPRING_MASK = 2407
    HEARTHFLAME_MASK = 2408
    METAL_ALLOY = 2482
    # Silvally Memory items (Gen 7; change Silvally's type via RKS System)
    FIRE_MEMORY = 901
    WATER_MEMORY = 902
    GRASS_MEMORY = 903
    ELECTRIC_MEMORY = 904
    ICE_MEMORY = 905
    FIGHTING_MEMORY = 906
    POISON_MEMORY = 907
    GROUND_MEMORY = 908
    FLYING_MEMORY = 909
    PSYCHIC_MEMORY = 910
    BUG_MEMORY = 911
    ROCK_MEMORY = 912
    GHOST_MEMORY = 913
    DRAGON_MEMORY = 914
    DARK_MEMORY = 915
    STEEL_MEMORY = 916
    FAIRY_MEMORY = 917


@dataclass(frozen=True)
class ItemData:
    name: str  # display name for logging


ITEM_DATA: dict[Item, ItemData] = {
    Item.NONE: ItemData("None"),
    Item.BERRY_JUICE: ItemData("Berry Juice"),
    Item.VILE_VIAL: ItemData("Vile Vial"),
    Item.MASTER_BALL: ItemData("Master Ball"),
    Item.ULTRA_BALL: ItemData("Ultra Ball"),
    Item.GREAT_BALL: ItemData("Great Ball"),
    Item.POKE_BALL: ItemData("Poke Ball"),
    Item.SAFARI_BALL: ItemData("Safari Ball"),
    Item.NET_BALL: ItemData("Net Ball"),
    Item.DIVE_BALL: ItemData("Dive Ball"),
    Item.NEST_BALL: ItemData("Nest Ball"),
    Item.REPEAT_BALL: ItemData("Repeat Ball"),
    Item.TIMER_BALL: ItemData("Timer Ball"),
    Item.LUXURY_BALL: ItemData("Luxury Ball"),
    Item.PREMIER_BALL: ItemData("Premier Ball"),
    Item.DUSK_BALL: ItemData("Dusk Ball"),
    Item.HEAL_BALL: ItemData("Heal Ball"),
    Item.QUICK_BALL: ItemData("Quick Ball"),
    Item.CHERISH_BALL: ItemData("Cherish Ball"),
    Item.SUN_STONE: ItemData("Sun Stone"),
    Item.MOON_STONE: ItemData("Moon Stone"),
    Item.FIRE_STONE: ItemData("Fire Stone"),
    Item.THUNDER_STONE: ItemData("Thunder Stone"),
    Item.WATER_STONE: ItemData("Water Stone"),
    Item.LEAF_STONE: ItemData("Leaf Stone"),
    Item.RARE_BONE: ItemData("Rare Bone"),
    Item.SHINY_STONE: ItemData("Shiny Stone"),
    Item.DUSK_STONE: ItemData("Dusk Stone"),
    Item.DAWN_STONE: ItemData("Dawn Stone"),
    Item.OVAL_STONE: ItemData("Oval Stone"),
    Item.GRISEOUS_ORB: ItemData("Griseous Orb"),
    Item.ADAMANT_ORB: ItemData("Adamant Orb"),
    Item.LUSTROUS_ORB: ItemData("Lustrous Orb"),
    Item.LEEK: ItemData("Leek"),
    Item.THICK_CLUB: ItemData("Thick Club"),
    Item.CHERI_BERRY: ItemData("Cheri Berry"),
    Item.CHESTO_BERRY: ItemData("Chesto Berry"),
    Item.PECHA_BERRY: ItemData("Pecha Berry"),
    Item.RAWST_BERRY: ItemData("Rawst Berry"),
    Item.ASPEAR_BERRY: ItemData("Aspear Berry"),
    Item.LEPPA_BERRY: ItemData("Leppa Berry"),
    Item.ORAN_BERRY: ItemData("Oran Berry"),
    Item.PERSIM_BERRY: ItemData("Persim Berry"),
    Item.LUM_BERRY: ItemData("Lum Berry"),
    Item.SITRUS_BERRY: ItemData("Sitrus Berry"),
    Item.FIGY_BERRY: ItemData("Figy Berry"),
    Item.WIKI_BERRY: ItemData("Wiki Berry"),
    Item.MAGO_BERRY: ItemData("Mago Berry"),
    Item.AGUAV_BERRY: ItemData("Aguav Berry"),
    Item.IAPAPA_BERRY: ItemData("Iapapa Berry"),
    Item.POMEG_BERRY: ItemData("Pomeg Berry"),
    Item.KELPSY_BERRY: ItemData("Kelpsy Berry"),
    Item.QUALOT_BERRY: ItemData("Qualot Berry"),
    Item.HONDEW_BERRY: ItemData("Hondew Berry"),
    Item.GREPA_BERRY: ItemData("Grepa Berry"),
    Item.TAMATO_BERRY: ItemData("Tamato Berry"),
    Item.OCCA_BERRY: ItemData("Occa Berry"),
    Item.PASSHO_BERRY: ItemData("Passho Berry"),
    Item.WACAN_BERRY: ItemData("Wacan Berry"),
    Item.RINDO_BERRY: ItemData("Rindo Berry"),
    Item.YACHE_BERRY: ItemData("Yache Berry"),
    Item.CHOPLE_BERRY: ItemData("Chople Berry"),
    Item.KEBIA_BERRY: ItemData("Kebia Berry"),
    Item.SHUCA_BERRY: ItemData("Shuca Berry"),
    Item.COBA_BERRY: ItemData("Coba Berry"),
    Item.PAYAPA_BERRY: ItemData("Payapa Berry"),
    Item.TANGA_BERRY: ItemData("Tanga Berry"),
    Item.CHARTI_BERRY: ItemData("Charti Berry"),
    Item.KASIB_BERRY: ItemData("Kasib Berry"),
    Item.HABAN_BERRY: ItemData("Haban Berry"),
    Item.COLBUR_BERRY: ItemData("Colbur Berry"),
    Item.BABIRI_BERRY: ItemData("Babiri Berry"),
    Item.CHILAN_BERRY: ItemData("Chilan Berry"),
    Item.LIECHI_BERRY: ItemData("Liechi Berry"),
    Item.GANLON_BERRY: ItemData("Ganlon Berry"),
    Item.SALAC_BERRY: ItemData("Salac Berry"),
    Item.PETAYA_BERRY: ItemData("Petaya Berry"),
    Item.APICOT_BERRY: ItemData("Apicot Berry"),
    Item.LANSAT_BERRY: ItemData("Lansat Berry"),
    Item.STARF_BERRY: ItemData("Starf Berry"),
    Item.ENIGMA_BERRY: ItemData("Enigma Berry"),
    Item.MICLE_BERRY: ItemData("Micle Berry"),
    Item.CUSTAP_BERRY: ItemData("Custap Berry"),
    Item.JABOCA_BERRY: ItemData("Jaboca Berry"),
    Item.ROWAP_BERRY: ItemData("Rowap Berry"),
    Item.BRIGHT_POWDER: ItemData("Bright Powder"),
    Item.WHITE_HERB: ItemData("White Herb"),
    Item.QUICK_CLAW: ItemData("Quick Claw"),
    Item.MENTAL_HERB: ItemData("Mental Herb"),
    Item.CHOICE_BAND: ItemData("Choice Band"),
    Item.KING_S_ROCK: ItemData("King's Rock"),
    Item.SILVER_POWDER: ItemData("Silver Powder"),
    Item.SOUL_DEW: ItemData("Soul Dew"),
    Item.FOCUS_BAND: ItemData("Focus Band"),
    Item.SCOPE_LENS: ItemData("Scope Lens"),
    Item.METAL_COAT: ItemData("Metal Coat"),
    Item.LEFTOVERS: ItemData("Leftovers"),
    Item.DRAGON_SCALE: ItemData("Dragon Scale"),
    Item.LIGHT_BALL: ItemData("Light Ball"),
    Item.SOFT_SAND: ItemData("Soft Sand"),
    Item.HARD_STONE: ItemData("Hard Stone"),
    Item.MIRACLE_SEED: ItemData("Miracle Seed"),
    Item.BLACK_GLASSES: ItemData("Black Glasses"),
    Item.BLACK_BELT: ItemData("Black Belt"),
    Item.MAGNET: ItemData("Magnet"),
    Item.MYSTIC_WATER: ItemData("Mystic Water"),
    Item.SHARP_BEAK: ItemData("Sharp Beak"),
    Item.POISON_BARB: ItemData("Poison Barb"),
    Item.NEVER_MELT_ICE: ItemData("Never-Melt Ice"),
    Item.SPELL_TAG: ItemData("Spell Tag"),
    Item.TWISTED_SPOON: ItemData("Twisted Spoon"),
    Item.CHARCOAL: ItemData("Charcoal"),
    Item.DRAGON_FANG: ItemData("Dragon Fang"),
    Item.SILK_SCARF: ItemData("Silk Scarf"),
    Item.UP_GRADE: ItemData("Up-Grade"),
    Item.SHELL_BELL: ItemData("Shell Bell"),
    Item.WIDE_LENS: ItemData("Wide Lens"),
    Item.MUSCLE_BAND: ItemData("Muscle Band"),
    Item.WISE_GLASSES: ItemData("Wise Glasses"),
    Item.EXPERT_BELT: ItemData("Expert Belt"),
    Item.LIGHT_CLAY: ItemData("Light Clay"),
    Item.LIFE_ORB: ItemData("Life Orb"),
    Item.POWER_HERB: ItemData("Power Herb"),
    Item.TOXIC_ORB: ItemData("Toxic Orb"),
    Item.FLAME_ORB: ItemData("Flame Orb"),
    Item.FOCUS_SASH: ItemData("Focus Sash"),
    Item.ZOOM_LENS: ItemData("Zoom Lens"),
    Item.METRONOME: ItemData("Metronome"),
    Item.IRON_BALL: ItemData("Iron Ball"),
    Item.LAGGING_TAIL: ItemData("Lagging Tail"),
    Item.DESTINY_KNOT: ItemData("Destiny Knot"),
    Item.BLACK_SLUDGE: ItemData("Black Sludge"),
    Item.ICY_ROCK: ItemData("Icy Rock"),
    Item.SMOOTH_ROCK: ItemData("Smooth Rock"),
    Item.HEAT_ROCK: ItemData("Heat Rock"),
    Item.DAMP_ROCK: ItemData("Damp Rock"),
    Item.GRIP_CLAW: ItemData("Grip Claw"),
    Item.CHOICE_SCARF: ItemData("Choice Scarf"),
    Item.STICKY_BARB: ItemData("Sticky Barb"),
    Item.POWER_BRACER: ItemData("Power Bracer"),
    Item.POWER_BELT: ItemData("Power Belt"),
    Item.POWER_LENS: ItemData("Power Lens"),
    Item.POWER_BAND: ItemData("Power Band"),
    Item.POWER_ANKLET: ItemData("Power Anklet"),
    Item.POWER_WEIGHT: ItemData("Power Weight"),
    Item.SHED_SHELL: ItemData("Shed Shell"),
    Item.BIG_ROOT: ItemData("Big Root"),
    Item.CHOICE_SPECS: ItemData("Choice Specs"),
    Item.FLAME_PLATE: ItemData("Flame Plate"),
    Item.SPLASH_PLATE: ItemData("Splash Plate"),
    Item.ZAP_PLATE: ItemData("Zap Plate"),
    Item.MEADOW_PLATE: ItemData("Meadow Plate"),
    Item.ICICLE_PLATE: ItemData("Icicle Plate"),
    Item.FIST_PLATE: ItemData("Fist Plate"),
    Item.TOXIC_PLATE: ItemData("Toxic Plate"),
    Item.EARTH_PLATE: ItemData("Earth Plate"),
    Item.SKY_PLATE: ItemData("Sky Plate"),
    Item.MIND_PLATE: ItemData("Mind Plate"),
    Item.INSECT_PLATE: ItemData("Insect Plate"),
    Item.STONE_PLATE: ItemData("Stone Plate"),
    Item.SPOOKY_PLATE: ItemData("Spooky Plate"),
    Item.DRACO_PLATE: ItemData("Draco Plate"),
    Item.DREAD_PLATE: ItemData("Dread Plate"),
    Item.IRON_PLATE: ItemData("Iron Plate"),
    Item.PROTECTOR: ItemData("Protector"),
    Item.ELECTIRIZER: ItemData("Electirizer"),
    Item.MAGMARIZER: ItemData("Magmarizer"),
    Item.DUBIOUS_DISC: ItemData("Dubious Disc"),
    Item.REAPER_CLOTH: ItemData("Reaper Cloth"),
    Item.RAZOR_CLAW: ItemData("Razor Claw"),
    Item.RAZOR_FANG: ItemData("Razor Fang"),
    Item.FAST_BALL: ItemData("Fast Ball"),
    Item.LEVEL_BALL: ItemData("Level Ball"),
    Item.LURE_BALL: ItemData("Lure Ball"),
    Item.HEAVY_BALL: ItemData("Heavy Ball"),
    Item.LOVE_BALL: ItemData("Love Ball"),
    Item.FRIEND_BALL: ItemData("Friend Ball"),
    Item.MOON_BALL: ItemData("Moon Ball"),
    Item.SPORT_BALL: ItemData("Sport Ball"),
    Item.PARK_BALL: ItemData("Park Ball"),
    Item.PRISM_SCALE: ItemData("Prism Scale"),
    Item.EVIOLITE: ItemData("Eviolite"),
    Item.FLOAT_STONE: ItemData("Float Stone"),
    Item.ROCKY_HELMET: ItemData("Rocky Helmet"),
    Item.AIR_BALLOON: ItemData("Air Balloon"),
    Item.RED_CARD: ItemData("Red Card"),
    Item.RING_TARGET: ItemData("Ring Target"),
    Item.BINDING_BAND: ItemData("Binding Band"),
    Item.ABSORB_BULB: ItemData("Absorb Bulb"),
    Item.CELL_BATTERY: ItemData("Cell Battery"),
    Item.EJECT_BUTTON: ItemData("Eject Button"),
    Item.NORMAL_GEM: ItemData("Normal Gem"),
    Item.FIRE_GEM: ItemData("Fire Gem"),
    Item.WATER_GEM: ItemData("Water Gem"),
    Item.GRASS_GEM: ItemData("Grass Gem"),
    Item.ELECTRIC_GEM: ItemData("Electric Gem"),
    Item.ICE_GEM: ItemData("Ice Gem"),
    Item.FIGHTING_GEM: ItemData("Fighting Gem"),
    Item.POISON_GEM: ItemData("Poison Gem"),
    Item.GROUND_GEM: ItemData("Ground Gem"),
    Item.FLYING_GEM: ItemData("Flying Gem"),
    Item.PSYCHIC_GEM: ItemData("Psychic Gem"),
    Item.BUG_GEM: ItemData("Bug Gem"),
    Item.ROCK_GEM: ItemData("Rock Gem"),
    Item.GHOST_GEM: ItemData("Ghost Gem"),
    Item.DRAGON_GEM: ItemData("Dragon Gem"),
    Item.DARK_GEM: ItemData("Dark Gem"),
    Item.STEEL_GEM: ItemData("Steel Gem"),
    Item.FAIRY_GEM: ItemData("Fairy Gem"),
    Item.PRETTY_FEATHER: ItemData("Pretty Feather"),
    Item.DREAM_BALL: ItemData("Dream Ball"),
    Item.BIG_NUGGET: ItemData("Big Nugget"),
    Item.WEAKNESS_POLICY: ItemData("Weakness Policy"),
    Item.ASSAULT_VEST: ItemData("Assault Vest"),
    Item.PIXIE_PLATE: ItemData("Pixie Plate"),
    Item.LUMINOUS_MOSS: ItemData("Luminous Moss"),
    Item.SNOWBALL: ItemData("Snowball"),
    Item.SAFETY_GOGGLES: ItemData("Safety Goggles"),
    Item.ROSELI_BERRY: ItemData("Roseli Berry"),
    Item.KEE_BERRY: ItemData("Kee Berry"),
    Item.MARANGA_BERRY: ItemData("Maranga Berry"),
    Item.BOTTLE_CAP: ItemData("Bottle Cap"),
    Item.GOLD_BOTTLE_CAP: ItemData("Gold Bottle Cap"),
    Item.ADRENALINE_ORB: ItemData("Adrenaline Orb"),
    Item.ICE_STONE: ItemData("Ice Stone"),
    Item.BEAST_BALL: ItemData("Beast Ball"),
    Item.TERRAIN_EXTENDER: ItemData("Terrain Extender"),
    Item.PROTECTIVE_PADS: ItemData("Protective Pads"),
    Item.ELECTRIC_SEED: ItemData("Electric Seed"),
    Item.PSYCHIC_SEED: ItemData("Psychic Seed"),
    Item.MISTY_SEED: ItemData("Misty Seed"),
    Item.GRASSY_SEED: ItemData("Grassy Seed"),
    Item.RUSTED_SWORD: ItemData("Rusted Sword"),
    Item.RUSTED_SHIELD: ItemData("Rusted Shield"),
    Item.STRAWBERRY_SWEET: ItemData("Strawberry Sweet"),
    Item.LOVE_SWEET: ItemData("Love Sweet"),
    Item.BERRY_SWEET: ItemData("Berry Sweet"),
    Item.CLOVER_SWEET: ItemData("Clover Sweet"),
    Item.FLOWER_SWEET: ItemData("Flower Sweet"),
    Item.STAR_SWEET: ItemData("Star Sweet"),
    Item.RIBBON_SWEET: ItemData("Ribbon Sweet"),
    Item.SWEET_APPLE: ItemData("Sweet Apple"),
    Item.TART_APPLE: ItemData("Tart Apple"),
    Item.THROAT_SPRAY: ItemData("Throat Spray"),
    Item.EJECT_PACK: ItemData("Eject Pack"),
    Item.HEAVY_DUTY_BOOTS: ItemData("Heavy-Duty Boots"),
    Item.BLUNDER_POLICY: ItemData("Blunder Policy"),
    Item.ROOM_SERVICE: ItemData("Room Service"),
    Item.UTILITY_UMBRELLA: ItemData("Utility Umbrella"),
    Item.CRACKED_POT: ItemData("Cracked Pot"),
    Item.CHIPPED_POT: ItemData("Chipped Pot"),
    Item.GALARICA_CUFF: ItemData("Galarica Cuff"),
    Item.GALARICA_WREATH: ItemData("Galarica Wreath"),
    Item.ADAMANT_CRYSTAL: ItemData("Adamant Crystal"),
    Item.LUSTROUS_GLOBE: ItemData("Lustrous Globe"),
    Item.GRISEOUS_CORE: ItemData("Griseous Core"),
    Item.STRANGE_BALL: ItemData("Strange Ball"),
    Item.MALICIOUS_ARMOR: ItemData("Malicious Armor"),
    Item.PUNCHING_GLOVE: ItemData("Punching Glove"),
    Item.COVERT_CLOAK: ItemData("Covert Cloak"),
    Item.LOADED_DICE: ItemData("Loaded Dice"),
    Item.AUSPICIOUS_ARMOR: ItemData("Auspicious Armor"),
    Item.FAIRY_FEATHER: ItemData("Fairy Feather"),
    Item.SYRUPY_APPLE: ItemData("Syrupy Apple"),
    Item.UNREMARKABLE_TEACUP: ItemData("Unremarkable Teacup"),
    Item.MASTERPIECE_TEACUP: ItemData("Masterpiece Teacup"),
    Item.CORNERSTONE_MASK: ItemData("Cornerstone Mask"),
    Item.WELLSPRING_MASK: ItemData("Wellspring Mask"),
    Item.HEARTHFLAME_MASK: ItemData("Hearthflame Mask"),
    Item.METAL_ALLOY: ItemData("Metal Alloy"),
    # Silvally Memory items
    Item.FIRE_MEMORY: ItemData("Fire Memory"),
    Item.WATER_MEMORY: ItemData("Water Memory"),
    Item.GRASS_MEMORY: ItemData("Grass Memory"),
    Item.ELECTRIC_MEMORY: ItemData("Electric Memory"),
    Item.ICE_MEMORY: ItemData("Ice Memory"),
    Item.FIGHTING_MEMORY: ItemData("Fighting Memory"),
    Item.POISON_MEMORY: ItemData("Poison Memory"),
    Item.GROUND_MEMORY: ItemData("Ground Memory"),
    Item.FLYING_MEMORY: ItemData("Flying Memory"),
    Item.PSYCHIC_MEMORY: ItemData("Psychic Memory"),
    Item.BUG_MEMORY: ItemData("Bug Memory"),
    Item.ROCK_MEMORY: ItemData("Rock Memory"),
    Item.GHOST_MEMORY: ItemData("Ghost Memory"),
    Item.DRAGON_MEMORY: ItemData("Dragon Memory"),
    Item.DARK_MEMORY: ItemData("Dark Memory"),
    Item.STEEL_MEMORY: ItemData("Steel Memory"),
    Item.FAIRY_MEMORY: ItemData("Fairy Memory"),

    # Mega stones and primal orbs
    Item.BLUE_ORB: ItemData("Blue Orb"),
    Item.RED_ORB: ItemData("Red Orb"),
    Item.GARCHOMPITE: ItemData("Garchompite"),
    Item.ABOMASITE: ItemData("Abomasite"),
    Item.ABSOLITE: ItemData("Absolite"),
    Item.AERODACTYLITE: ItemData("Aerodactylite"),
    Item.AGGRONITE: ItemData("Aggronite"),
    Item.ALAKAZITE: ItemData("Alakazite"),
    Item.AMPHAROSITE: ItemData("Ampharosite"),
    Item.BANETTITE: ItemData("Banettite"),
    Item.BLASTOISINITE: ItemData("Blastoisinite"),
    Item.BLAZIKENITE: ItemData("Blazikenite"),
    Item.CHARIZARDITE_X: ItemData("Charizardite X"),
    Item.CHARIZARDITE_Y: ItemData("Charizardite Y"),
    Item.GARDEVOIRITE: ItemData("Gardevoirite"),
    Item.GENGARITE: ItemData("Gengarite"),
    Item.GYARADOSITE: ItemData("Gyaradosite"),
    Item.HERACRONITE: ItemData("Heracronite"),
    Item.HOUNDOOMINITE: ItemData("Houndoominite"),
    Item.KANGASKHANITE: ItemData("Kangaskhanite"),
    Item.LUCARIONITE: ItemData("Lucarionite"),
    Item.MANECTITE: ItemData("Manectite"),
    Item.MAWILITE: ItemData("Mawilite"),
    Item.MEDICHAMITE: ItemData("Medichamite"),
    Item.PINSIRITE: ItemData("Pinsirite"),
    Item.SCIZORITE: ItemData("Scizorite"),
    Item.TYRANITARITE: ItemData("Tyranitarite"),
    Item.VENUSAURITE: ItemData("Venusaurite"),
    Item.SWAMPERTITE: ItemData("Swampertite"),
    Item.SCEPTILITE: ItemData("Sceptilite"),
    Item.SABLENITE: ItemData("Sablenite"),
    Item.ALTARIANITE: ItemData("Altarianite"),
    Item.GALLADITE: ItemData("Galladite"),
    Item.AUDINITE: ItemData("Audinite"),
    Item.METAGROSSITE: ItemData("Metagrossite"),
    Item.SHARPEDONITE: ItemData("Sharpedonite"),
    Item.SLOWBRONITE: ItemData("Slowbronite"),
    Item.STEELIXITE: ItemData("Steelixite"),
    Item.PIDGEOTITE: ItemData("Pidgeotite"),
    Item.GLALITITE: ItemData("Glalitite"),
    Item.CAMERUPTITE: ItemData("Cameruptite"),
    Item.LOPUNNITE: ItemData("Lopunnite"),
    Item.SALAMENCITE: ItemData("Salamencite"),
    Item.BEEDRILLITE: ItemData("Beedrillite"),
    Item.LATIASITE: ItemData("Latiasite"),
    Item.LATIOSITE: ItemData("Latiosite"),
}

# Natural Gift: berry item → (move type, base power)
# Source: Showdown items.ts naturalGift entries (Gen 6+ table)
NATURAL_GIFT_TABLE: dict["Item", tuple[Type, int]] = {
    # 60 BP berries
    Item.CHERI_BERRY:   (Type.FIRE,     60),
    Item.CHESTO_BERRY:  (Type.WATER,    60),
    Item.PECHA_BERRY:   (Type.ELECTRIC, 60),
    Item.RAWST_BERRY:   (Type.GRASS,    60),
    Item.ASPEAR_BERRY:  (Type.ICE,      60),
    Item.LEPPA_BERRY:   (Type.FIGHTING, 60),
    Item.ORAN_BERRY:    (Type.POISON,   60),
    Item.PERSIM_BERRY:  (Type.GROUND,   60),
    # 80 BP berries
    Item.LUM_BERRY:     (Type.FLYING,   80),
    Item.SITRUS_BERRY:  (Type.PSYCHIC,  80),
    Item.FIGY_BERRY:    (Type.FIRE,     80),
    Item.WIKI_BERRY:    (Type.WATER,    80),
    Item.MAGO_BERRY:    (Type.GRASS,    80),
    Item.AGUAV_BERRY:   (Type.DRAGON,   80),
    Item.IAPAPA_BERRY:  (Type.DARK,     80),
    Item.OCCA_BERRY:    (Type.FIRE,     80),
    Item.PASSHO_BERRY:  (Type.WATER,    80),
    Item.WACAN_BERRY:   (Type.ELECTRIC, 80),
    Item.RINDO_BERRY:   (Type.GRASS,    80),
    Item.YACHE_BERRY:   (Type.ICE,      80),
    Item.CHOPLE_BERRY:  (Type.FIGHTING, 80),
    Item.KEBIA_BERRY:   (Type.POISON,   80),
    Item.SHUCA_BERRY:   (Type.GROUND,   80),
    Item.COBA_BERRY:    (Type.FLYING,   80),
    Item.PAYAPA_BERRY:  (Type.PSYCHIC,  80),
    Item.TANGA_BERRY:   (Type.BUG,      80),
    Item.CHARTI_BERRY:  (Type.ROCK,     80),
    Item.KASIB_BERRY:   (Type.GHOST,    80),
    Item.HABAN_BERRY:   (Type.DRAGON,   80),
    Item.COLBUR_BERRY:  (Type.DARK,     80),
    Item.BABIRI_BERRY:  (Type.STEEL,    80),
    Item.CHILAN_BERRY:  (Type.NORMAL,   80),
    Item.ROSELI_BERRY:  (Type.FAIRY,    80),
    # 100 BP berries
    Item.LIECHI_BERRY:  (Type.GRASS,    100),
    Item.GANLON_BERRY:  (Type.ICE,      100),
    Item.SALAC_BERRY:   (Type.FIGHTING, 100),
    Item.PETAYA_BERRY:  (Type.POISON,   100),
    Item.APICOT_BERRY:  (Type.GROUND,   100),
    Item.LANSAT_BERRY:  (Type.FLYING,   100),
    Item.STARF_BERRY:   (Type.PSYCHIC,  100),
    Item.CUSTAP_BERRY:  (Type.GHOST,    100),
    Item.MICLE_BERRY:   (Type.ROCK,     100),
    Item.JABOCA_BERRY:  (Type.DRAGON,   100),
    Item.ROWAP_BERRY:   (Type.DARK,     100),
    Item.KEE_BERRY:     (Type.FAIRY,    100),
    Item.MARANGA_BERRY: (Type.DARK,     100),
    Item.ENIGMA_BERRY:  (Type.BUG,      100),
}

BERRY_ITEMS: frozenset["Item"] = frozenset(i for i in Item if i.name.endswith("_BERRY"))
