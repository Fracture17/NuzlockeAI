# Move enum, category, target, tag, and secondary-effect data.
# Generated from Showdown moves.ts. Z-moves excluded.
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum, IntFlag
from typing import Optional
from liveplay.data.types import Type
from liveplay.data.status import Status


class Move(IntEnum):
    NONE = 0
    POUND = 1
    KARATE_CHOP = 2
    DOUBLE_SLAP = 3
    COMET_PUNCH = 4
    MEGA_PUNCH = 5
    PAY_DAY = 6
    FIRE_PUNCH = 7
    ICE_PUNCH = 8
    THUNDER_PUNCH = 9
    SCRATCH = 10
    VISE_GRIP = 11
    GUILLOTINE = 12
    RAZOR_WIND = 13
    SWORDS_DANCE = 14
    CUT = 15
    GUST = 16
    WING_ATTACK = 17
    WHIRLWIND = 18
    FLY = 19
    BIND = 20
    SLAM = 21
    VINE_WHIP = 22
    STOMP = 23
    DOUBLE_KICK = 24
    MEGA_KICK = 25
    JUMP_KICK = 26
    ROLLING_KICK = 27
    SAND_ATTACK = 28
    HEADBUTT = 29
    HORN_ATTACK = 30
    FURY_ATTACK = 31
    HORN_DRILL = 32
    TACKLE = 33
    BODY_SLAM = 34
    WRAP = 35
    TAKE_DOWN = 36
    THRASH = 37
    DOUBLE_EDGE = 38
    TAIL_WHIP = 39
    POISON_STING = 40
    TWINEEDLE = 41
    PIN_MISSILE = 42
    LEER = 43
    BITE = 44
    GROWL = 45
    ROAR = 46
    SING = 47
    SUPERSONIC = 48
    SONIC_BOOM = 49
    DISABLE = 50
    ACID = 51
    EMBER = 52
    FLAMETHROWER = 53
    # REMOVED(unimplemented status move) MIST = 54
    WATER_GUN = 55
    HYDRO_PUMP = 56
    SURF = 57
    ICE_BEAM = 58
    BLIZZARD = 59
    PSYBEAM = 60
    BUBBLE_BEAM = 61
    AURORA_BEAM = 62
    HYPER_BEAM = 63
    PECK = 64
    DRILL_PECK = 65
    SUBMISSION = 66
    LOW_KICK = 67
    COUNTER = 68
    SEISMIC_TOSS = 69
    STRENGTH = 70
    ABSORB = 71
    MEGA_DRAIN = 72
    LEECH_SEED = 73
    GROWTH = 74
    RAZOR_LEAF = 75
    SOLAR_BEAM = 76
    POISON_POWDER = 77
    STUN_SPORE = 78
    SLEEP_POWDER = 79
    PETAL_DANCE = 80
    STRING_SHOT = 81
    DRAGON_RAGE = 82
    FIRE_SPIN = 83
    THUNDER_SHOCK = 84
    THUNDERBOLT = 85
    THUNDER_WAVE = 86
    THUNDER = 87
    ROCK_THROW = 88
    EARTHQUAKE = 89
    FISSURE = 90
    DIG = 91
    TOXIC = 92
    CONFUSION = 93
    PSYCHIC = 94
    HYPNOSIS = 95
    MEDITATE = 96
    AGILITY = 97
    QUICK_ATTACK = 98
    RAGE = 99
    TELEPORT = 100
    NIGHT_SHADE = 101
    # REMOVED(unimplemented status move) MIMIC = 102
    SCREECH = 103
    DOUBLE_TEAM = 104
    RECOVER = 105
    HARDEN = 106
    MINIMIZE = 107
    SMOKESCREEN = 108
    CONFUSE_RAY = 109
    # REMOVED(unimplemented status move) WITHDRAW = 110
    DEFENSE_CURL = 111
    BARRIER = 112
    LIGHT_SCREEN = 113
    HAZE = 114
    REFLECT = 115
    FOCUS_ENERGY = 116
    METRONOME = 118
    MIRROR_MOVE = 119
    SELF_DESTRUCT = 120
    EGG_BOMB = 121
    LICK = 122
    SMOG = 123
    SLUDGE = 124
    BONE_CLUB = 125
    FIRE_BLAST = 126
    WATERFALL = 127
    CLAMP = 128
    SWIFT = 129
    SKULL_BASH = 130
    SPIKE_CANNON = 131
    CONSTRICT = 132
    AMNESIA = 133
    KINESIS = 134
    SOFT_BOILED = 135
    HIGH_JUMP_KICK = 136
    GLARE = 137
    DREAM_EATER = 138
    POISON_GAS = 139
    BARRAGE = 140
    LEECH_LIFE = 141
    LOVELY_KISS = 142
    SKY_ATTACK = 143
    TRANSFORM = 144
    BUBBLE = 145
    DIZZY_PUNCH = 146
    SPORE = 147
    FLASH = 148
    PSYWAVE = 149
    SPLASH = 150
    ACID_ARMOR = 151
    CRABHAMMER = 152
    EXPLOSION = 153
    FURY_SWIPES = 154
    BONEMERANG = 155
    REST = 156
    ROCK_SLIDE = 157
    HYPER_FANG = 158
    SHARPEN = 159
    # REMOVED(unimplemented status move) CONVERSION = 160
    TRI_ATTACK = 161
    SUPER_FANG = 162
    SLASH = 163
    SUBSTITUTE = 164
    STRUGGLE = 165
    # REMOVED(unimplemented status move) SKETCH = 166
    TRIPLE_KICK = 167
    THIEF = 168
    # REMOVED(unimplemented status move) SPIDER_WEB = 169
    NIGHTMARE = 171
    FLAME_WHEEL = 172
    SNORE = 173
    CURSE = 174
    FLAIL = 175
    # REMOVED(unimplemented status move) CONVERSION_2 = 176
    AEROBLAST = 177
    COTTON_SPORE = 178
    REVERSAL = 179
    # REMOVED(unimplemented status move) SPITE = 180
    POWDER_SNOW = 181
    PROTECT = 182
    MACH_PUNCH = 183
    SCARY_FACE = 184
    FEINT_ATTACK = 185
    SWEET_KISS = 186
    BELLY_DRUM = 187
    SLUDGE_BOMB = 188
    MUD_SLAP = 189
    OCTAZOOKA = 190
    SPIKES = 191
    ZAP_CANNON = 192
    FORESIGHT = 193
    DESTINY_BOND = 194
    PERISH_SONG = 195
    ICY_WIND = 196
    DETECT = 197
    BONE_RUSH = 198
    OUTRAGE = 200
    SANDSTORM = 201
    GIGA_DRAIN = 202
    ENDURE = 203
    CHARM = 204
    ROLLOUT = 205
    FALSE_SWIPE = 206
    SWAGGER = 207
    MILK_DRINK = 208
    SPARK = 209
    FURY_CUTTER = 210
    STEEL_WING = 211
    MEAN_LOOK = 212
    ATTRACT = 213
    SLEEP_TALK = 214
    HEAL_BELL = 215
    RETURN = 216
    PRESENT = 217
    FRUSTRATION = 218
    SAFEGUARD = 219
    PAIN_SPLIT = 220
    SACRED_FIRE = 221
    MAGNITUDE = 222
    DYNAMIC_PUNCH = 223
    MEGAHORN = 224
    DRAGON_BREATH = 225
    BATON_PASS = 226
    ENCORE = 227
    PURSUIT = 228
    RAPID_SPIN = 229
    SWEET_SCENT = 230
    IRON_TAIL = 231
    METAL_CLAW = 232
    VITAL_THROW = 233
    MORNING_SUN = 234
    SYNTHESIS = 235
    MOONLIGHT = 236
    HIDDEN_POWER = 237
    # Typed variants get unique values above Showdown's ~900 max to avoid aliasing.
    HIDDEN_POWER_BUG = 10001
    HIDDEN_POWER_DARK = 10002
    HIDDEN_POWER_DRAGON = 10003
    HIDDEN_POWER_ELECTRIC = 10004
    HIDDEN_POWER_FIGHTING = 10005
    HIDDEN_POWER_FIRE = 10006
    HIDDEN_POWER_FLYING = 10007
    HIDDEN_POWER_GHOST = 10008
    HIDDEN_POWER_GRASS = 10009
    HIDDEN_POWER_GROUND = 10010
    HIDDEN_POWER_ICE = 10011
    HIDDEN_POWER_POISON = 10012
    HIDDEN_POWER_PSYCHIC = 10013
    HIDDEN_POWER_ROCK = 10014
    HIDDEN_POWER_STEEL = 10015
    HIDDEN_POWER_WATER = 10016
    CROSS_CHOP = 238
    TWISTER = 239
    RAIN_DANCE = 240
    SUNNY_DAY = 241
    CRUNCH = 242
    MIRROR_COAT = 243
    PSYCH_UP = 244
    EXTREME_SPEED = 245
    ANCIENT_POWER = 246
    SHADOW_BALL = 247
    FUTURE_SIGHT = 248
    ROCK_SMASH = 249
    WHIRLPOOL = 250
    BEAT_UP = 251
    FAKE_OUT = 252
    UPROAR = 253
    STOCKPILE = 254
    SPIT_UP = 255
    SWALLOW = 256
    HEAT_WAVE = 257
    HAIL = 258
    TORMENT = 259
    FLATTER = 260
    WILL_O_WISP = 261
    MEMENTO = 262
    FACADE = 263
    FOCUS_PUNCH = 264
    SMELLING_SALTS = 265
    FOLLOW_ME = 266
    NATURE_POWER = 267
    # REMOVED(unimplemented status move) CHARGE = 268
    TAUNT = 269
    HELPING_HAND = 270
    TRICK = 271
    ROLE_PLAY = 272
    WISH = 273
    ASSIST = 274
    INGRAIN = 275
    SUPERPOWER = 276
    MAGIC_COAT = 277
    # REMOVED(unimplemented status move) RECYCLE = 278
    REVENGE = 279
    BRICK_BREAK = 280
    YAWN = 281
    KNOCK_OFF = 282
    ENDEAVOR = 283
    ERUPTION = 284
    SKILL_SWAP = 285
    IMPRISON = 286
    # REMOVED(unimplemented status move) REFRESH = 287
    # REMOVED(unimplemented status move) GRUDGE = 288
    SNATCH = 289
    SECRET_POWER = 290
    DIVE = 291
    ARM_THRUST = 292
    # REMOVED(unimplemented status move) CAMOUFLAGE = 293
    TAIL_GLOW = 294
    LUSTER_PURGE = 295
    MIST_BALL = 296
    FEATHER_DANCE = 297
    TEETER_DANCE = 298
    BLAZE_KICK = 299
    # REMOVED(unimplemented status move) MUD_SPORT = 300
    ICE_BALL = 301
    NEEDLE_ARM = 302
    SLACK_OFF = 303
    HYPER_VOICE = 304
    POISON_FANG = 305
    CRUSH_CLAW = 306
    BLAST_BURN = 307
    HYDRO_CANNON = 308
    METEOR_MASH = 309
    ASTONISH = 310
    WEATHER_BALL = 311
    AROMATHERAPY = 312
    FAKE_TEARS = 313
    AIR_CUTTER = 314
    OVERHEAT = 315
    ODOR_SLEUTH = 316
    ROCK_TOMB = 317
    SILVER_WIND = 318
    METAL_SOUND = 319
    GRASS_WHISTLE = 320
    TICKLE = 321
    COSMIC_POWER = 322
    WATER_SPOUT = 323
    SIGNAL_BEAM = 324
    SHADOW_PUNCH = 325
    EXTRASENSORY = 326
    SKY_UPPERCUT = 327
    SAND_TOMB = 328
    SHEER_COLD = 329
    MUDDY_WATER = 330
    BULLET_SEED = 331
    AERIAL_ACE = 332
    ICICLE_SPEAR = 333
    IRON_DEFENSE = 334
    BLOCK = 335
    HOWL = 336
    DRAGON_CLAW = 337
    FRENZY_PLANT = 338
    BULK_UP = 339
    BOUNCE = 340
    MUD_SHOT = 341
    POISON_TAIL = 342
    COVET = 343
    VOLT_TACKLE = 344
    MAGICAL_LEAF = 345
    # REMOVED(unimplemented status move) WATER_SPORT = 346
    CALM_MIND = 347
    LEAF_BLADE = 348
    DRAGON_DANCE = 349
    ROCK_BLAST = 350
    SHOCK_WAVE = 351
    WATER_PULSE = 352
    DOOM_DESIRE = 353
    PSYCHO_BOOST = 354
    ROOST = 355
    GRAVITY = 356
    # REMOVED(unimplemented status move) MIRACLE_EYE = 357
    WAKE_UP_SLAP = 358
    HAMMER_ARM = 359
    GYRO_BALL = 360
    HEALING_WISH = 361
    BRINE = 362
    NATURAL_GIFT = 363
    FEINT = 364
    PLUCK = 365
    TAILWIND = 366
    ACUPRESSURE = 367
    METAL_BURST = 368
    U_TURN = 369
    CLOSE_COMBAT = 370
    PAYBACK = 371
    ASSURANCE = 372
    EMBARGO = 373
    FLING = 374
    # REMOVED(unimplemented status move) PSYCHO_SHIFT = 375
    TRUMP_CARD = 376
    WRING_OUT = 378
    POWER_TRICK = 379
    # REMOVED(unimplemented status move) GASTRO_ACID = 380
    LUCKY_CHANT = 381
    ME_FIRST = 382
    COPYCAT = 383
    # REMOVED(unimplemented status move) POWER_SWAP = 384
    # REMOVED(unimplemented status move) GUARD_SWAP = 385
    PUNISHMENT = 386
    LAST_RESORT = 387
    # REMOVED(unimplemented status move) WORRY_SEED = 388
    SUCKER_PUNCH = 389
    TOXIC_SPIKES = 390
    # REMOVED(unimplemented status move) HEART_SWAP = 391
    AQUA_RING = 392
    MAGNET_RISE = 393
    FLARE_BLITZ = 394
    FORCE_PALM = 395
    AURA_SPHERE = 396
    ROCK_POLISH = 397
    POISON_JAB = 398
    DARK_PULSE = 399
    NIGHT_SLASH = 400
    AQUA_TAIL = 401
    SEED_BOMB = 402
    AIR_SLASH = 403
    X_SCISSOR = 404
    BUG_BUZZ = 405
    DRAGON_PULSE = 406
    DRAGON_RUSH = 407
    POWER_GEM = 408
    DRAIN_PUNCH = 409
    VACUUM_WAVE = 410
    FOCUS_BLAST = 411
    ENERGY_BALL = 412
    BRAVE_BIRD = 413
    EARTH_POWER = 414
    SWITCHEROO = 415
    GIGA_IMPACT = 416
    NASTY_PLOT = 417
    BULLET_PUNCH = 418
    AVALANCHE = 419
    ICE_SHARD = 420
    SHADOW_CLAW = 421
    THUNDER_FANG = 422
    ICE_FANG = 423
    FIRE_FANG = 424
    SHADOW_SNEAK = 425
    MUD_BOMB = 426
    PSYCHO_CUT = 427
    ZEN_HEADBUTT = 428
    MIRROR_SHOT = 429
    FLASH_CANNON = 430
    ROCK_CLIMB = 431
    DEFOG = 432
    TRICK_ROOM = 433
    DRACO_METEOR = 434
    DISCHARGE = 435
    LAVA_PLUME = 436
    LEAF_STORM = 437
    POWER_WHIP = 438
    ROCK_WRECKER = 439
    CROSS_POISON = 440
    GUNK_SHOT = 441
    IRON_HEAD = 442
    MAGNET_BOMB = 443
    STONE_EDGE = 444
    CAPTIVATE = 445
    STEALTH_ROCK = 446
    GRASS_KNOT = 447
    CHATTER = 448
    JUDGMENT = 449
    BUG_BITE = 450
    CHARGE_BEAM = 451
    WOOD_HAMMER = 452
    AQUA_JET = 453
    ATTACK_ORDER = 454
    DEFEND_ORDER = 455
    HEAL_ORDER = 456
    HEAD_SMASH = 457
    DOUBLE_HIT = 458
    ROAR_OF_TIME = 459
    SPACIAL_REND = 460
    LUNAR_DANCE = 461
    CRUSH_GRIP = 462
    MAGMA_STORM = 463
    DARK_VOID = 464
    SEED_FLARE = 465
    OMINOUS_WIND = 466
    HONE_CLAWS = 468
    WIDE_GUARD = 469
    # REMOVED(unimplemented status move) GUARD_SPLIT = 470
    # REMOVED(unimplemented status move) POWER_SPLIT = 471
    # REMOVED(unimplemented status move) WONDER_ROOM = 472
    PSYSHOCK = 473
    VENOSHOCK = 474
    AUTOTOMIZE = 475
    RAGE_POWDER = 476
    TELEKINESIS = 477
    # REMOVED(unimplemented status move) MAGIC_ROOM = 478
    SMACK_DOWN = 479
    STORM_THROW = 480
    FLAME_BURST = 481
    SLUDGE_WAVE = 482
    QUIVER_DANCE = 483
    HEAVY_SLAM = 484
    SYNCHRONOISE = 485
    ELECTRO_BALL = 486
    SOAK = 487
    FLAME_CHARGE = 488
    COIL = 489
    LOW_SWEEP = 490
    ACID_SPRAY = 491
    FOUL_PLAY = 492
    # REMOVED(unimplemented status move) SIMPLE_BEAM = 493
    # REMOVED(unimplemented status move) ENTRAINMENT = 494
    # REMOVED(unimplemented status move) AFTER_YOU = 495
    ROUND = 496
    ECHOED_VOICE = 497
    CHIP_AWAY = 498
    CLEAR_SMOG = 499
    STORED_POWER = 500
    QUICK_GUARD = 501
    ALLY_SWITCH = 502
    SCALD = 503
    SHELL_SMASH = 504
    HEAL_PULSE = 505
    HEX = 506
    SKY_DROP = 507
    SHIFT_GEAR = 508
    CIRCLE_THROW = 509
    INCINERATE = 510
    # REMOVED(unimplemented status move) QUASH = 511
    ACROBATICS = 512
    # REMOVED(unimplemented status move) REFLECT_TYPE = 513
    RETALIATE = 514
    FINAL_GAMBIT = 515
    # REMOVED(unimplemented status move) BESTOW = 516
    INFERNO = 517
    WATER_PLEDGE = 518
    FIRE_PLEDGE = 519
    GRASS_PLEDGE = 520
    VOLT_SWITCH = 521
    STRUGGLE_BUG = 522
    BULLDOZE = 523
    FROST_BREATH = 524
    DRAGON_TAIL = 525
    WORK_UP = 526
    ELECTROWEB = 527
    WILD_CHARGE = 528
    DRILL_RUN = 529
    DUAL_CHOP = 530
    HEART_STAMP = 531
    HORN_LEECH = 532
    SACRED_SWORD = 533
    RAZOR_SHELL = 534
    HEAT_CRASH = 535
    LEAF_TORNADO = 536
    STEAMROLLER = 537
    COTTON_GUARD = 538
    NIGHT_DAZE = 539
    PSYSTRIKE = 540
    TAIL_SLAP = 541
    HURRICANE = 542
    HEAD_CHARGE = 543
    GEAR_GRIND = 544
    SEARING_SHOT = 545
    TECHNO_BLAST = 546
    RELIC_SONG = 547
    SECRET_SWORD = 548
    GLACIATE = 549
    BOLT_STRIKE = 550
    BLUE_FLARE = 551
    FIERY_DANCE = 552
    FREEZE_SHOCK = 553
    ICE_BURN = 554
    SNARL = 555
    ICICLE_CRASH = 556
    V_CREATE = 557
    FUSION_FLARE = 558
    FUSION_BOLT = 559
    FLYING_PRESS = 560
    MAT_BLOCK = 561
    BELCH = 562
    # REMOVED(unimplemented status move) ROTOTILLER = 563
    STICKY_WEB = 564
    FELL_STINGER = 565
    PHANTOM_FORCE = 566
    # REMOVED(unimplemented status move) TRICK_OR_TREAT = 567
    NOBLE_ROAR = 568
    ION_DELUGE = 569
    PARABOLIC_CHARGE = 570
    # REMOVED(unimplemented status move) FOREST_S_CURSE = 571
    PETAL_BLIZZARD = 572
    FREEZE_DRY = 573
    DISARMING_VOICE = 574
    PARTING_SHOT = 575
    # REMOVED(unimplemented status move) TOPSY_TURVY = 576
    DRAINING_KISS = 577
    CRAFTY_SHIELD = 578
    # REMOVED(unimplemented status move) FLOWER_SHIELD = 579
    GRASSY_TERRAIN = 580
    MISTY_TERRAIN = 581
    # REMOVED(unimplemented status move) ELECTRIFY = 582
    PLAY_ROUGH = 583
    FAIRY_WIND = 584
    MOONBLAST = 585
    BOOMBURST = 586
    # REMOVED(unimplemented status move) FAIRY_LOCK = 587
    KING_S_SHIELD = 588
    PLAY_NICE = 589
    CONFIDE = 590
    DIAMOND_STORM = 591
    STEAM_ERUPTION = 592
    HYPERSPACE_HOLE = 593
    WATER_SHURIKEN = 594
    MYSTICAL_FIRE = 595
    SPIKY_SHIELD = 596
    # REMOVED(unimplemented status move) AROMATIC_MIST = 597
    EERIE_IMPULSE = 598
    # REMOVED(unimplemented status move) VENOM_DRENCH = 599
    POWDER = 600
    # REMOVED(unimplemented status move) GEOMANCY = 601
    # REMOVED(unimplemented status move) MAGNETIC_FLUX = 602
    # REMOVED(unimplemented status move) HAPPY_HOUR = 603
    ELECTRIC_TERRAIN = 604
    DAZZLING_GLEAM = 605
    # REMOVED(unimplemented status move) CELEBRATE = 606
    # REMOVED(unimplemented status move) HOLD_HANDS = 607
    BABY_DOLL_EYES = 608
    NUZZLE = 609
    HOLD_BACK = 610
    INFESTATION = 611
    POWER_UP_PUNCH = 612
    OBLIVION_WING = 613
    THOUSAND_ARROWS = 614
    THOUSAND_WAVES = 615
    LAND_S_WRATH = 616
    LIGHT_OF_RUIN = 617
    ORIGIN_PULSE = 618
    PRECIPICE_BLADES = 619
    DRAGON_ASCENT = 620
    HYPERSPACE_FURY = 621
    SHORE_UP = 659
    FIRST_IMPRESSION = 660
    BANEFUL_BUNKER = 661
    SPIRIT_SHACKLE = 662
    DARKEST_LARIAT = 663
    SPARKLING_ARIA = 664
    ICE_HAMMER = 665
    FLORAL_HEALING = 666
    HIGH_HORSEPOWER = 667
    STRENGTH_SAP = 668
    SOLAR_BLADE = 669
    LEAFAGE = 670
    SPOTLIGHT = 671
    TOXIC_THREAD = 672
    LASER_FOCUS = 673
    # REMOVED(unimplemented status move) GEAR_UP = 674
    THROAT_CHOP = 675
    POLLEN_PUFF = 676
    ANCHOR_SHOT = 677
    PSYCHIC_TERRAIN = 678
    LUNGE = 679
    FIRE_LASH = 680
    POWER_TRIP = 681
    BURN_UP = 682
    # REMOVED(unimplemented status move) SPEED_SWAP = 683
    SMART_STRIKE = 684
    # REMOVED(unimplemented status move) PURIFY = 685
    REVELATION_DANCE = 686
    CORE_ENFORCER = 687
    TROP_KICK = 688
    # REMOVED(unimplemented status move) INSTRUCT = 689
    BEAK_BLAST = 690
    CLANGING_SCALES = 691
    DRAGON_HAMMER = 692
    BRUTAL_SWING = 693
    AURORA_VEIL = 694
    SHELL_TRAP = 704
    FLEUR_CANNON = 705
    PSYCHIC_FANGS = 706
    STOMPING_TANTRUM = 707
    SHADOW_BONE = 708
    ACCELEROCK = 709
    LIQUIDATION = 710
    PRISMATIC_LASER = 711
    SPECTRAL_THIEF = 712
    SUNSTEEL_STRIKE = 713
    MOONGEIST_BEAM = 714
    TEARFUL_LOOK = 715
    ZING_ZAP = 716
    NATURE_S_MADNESS = 717
    MULTI_ATTACK = 718
    MIND_BLOWN = 720
    PLASMA_FISTS = 721
    PHOTON_GEYSER = 722
    ZIPPY_ZAP = 729
    SPLISHY_SPLASH = 730
    FLOATY_FALL = 731
    PIKA_PAPOW = 732
    BOUNCY_BUBBLE = 733
    BUZZY_BUZZ = 734
    SIZZLY_SLIDE = 735
    GLITZY_GLOW = 736
    BADDY_BAD = 737
    SAPPY_SEED = 738
    FREEZY_FROST = 739
    SPARKLY_SWIRL = 740
    VEEVEE_VOLLEY = 741
    DOUBLE_IRON_BASH = 742
    MAX_GUARD = 743
    DYNAMAX_CANNON = 744
    SNIPE_SHOT = 745
    JAW_LOCK = 746
    STUFF_CHEEKS = 747
    NO_RETREAT = 748
    # REMOVED(unimplemented status move) TAR_SHOT = 749
    # REMOVED(unimplemented status move) MAGIC_POWDER = 750
    DRAGON_DARTS = 751
    # REMOVED(unimplemented status move) TEATIME = 752
    OCTOLOCK = 753
    BOLT_BEAK = 754
    FISHIOUS_REND = 755
    # REMOVED(unimplemented status move) COURT_CHANGE = 756
    MAX_FLARE = 757
    MAX_FLUTTERBY = 758
    MAX_LIGHTNING = 759
    MAX_STRIKE = 760
    MAX_KNUCKLE = 761
    MAX_PHANTASM = 762
    MAX_HAILSTORM = 763
    MAX_OOZE = 764
    MAX_GEYSER = 765
    MAX_AIRSTREAM = 766
    MAX_STARFALL = 767
    MAX_WYRMWIND = 768
    MAX_MINDSTORM = 769
    MAX_ROCKFALL = 770
    MAX_QUAKE = 771
    MAX_DARKNESS = 772
    MAX_OVERGROWTH = 773
    MAX_STEELSPIKE = 774
    CLANGOROUS_SOUL = 775
    BODY_PRESS = 776
    DECORATE = 777
    DRUM_BEATING = 778
    SNAP_TRAP = 779
    PYRO_BALL = 780
    BEHEMOTH_BLADE = 781
    BEHEMOTH_BASH = 782
    AURA_WHEEL = 783
    BREAKING_SWIPE = 784
    BRANCH_POKE = 785
    OVERDRIVE = 786
    APPLE_ACID = 787
    GRAV_APPLE = 788
    SPIRIT_BREAK = 789
    STRANGE_STEAM = 790
    LIFE_DEW = 791
    OBSTRUCT = 792
    FALSE_SURRENDER = 793
    METEOR_ASSAULT = 794
    ETERNABEAM = 795
    STEEL_BEAM = 796
    EXPANDING_FORCE = 797
    STEEL_ROLLER = 798
    SCALE_SHOT = 799
    METEOR_BEAM = 800
    SHELL_SIDE_ARM = 801
    MISTY_EXPLOSION = 802
    GRASSY_GLIDE = 803
    RISING_VOLTAGE = 804
    TERRAIN_PULSE = 805
    SKITTER_SMACK = 806
    BURNING_JEALOUSY = 807
    LASH_OUT = 808
    POLTERGEIST = 809
    # REMOVED(unimplemented status move) CORROSIVE_GAS = 810
    COACHING = 811
    FLIP_TURN = 812
    TRIPLE_AXEL = 813
    DUAL_WINGBEAT = 814
    SCORCHING_SANDS = 815
    JUNGLE_HEALING = 816
    WICKED_BLOW = 817
    SURGING_STRIKES = 818
    THUNDER_CAGE = 819
    DRAGON_ENERGY = 820
    FREEZING_GLARE = 821
    FIERY_WRATH = 822
    THUNDEROUS_KICK = 823
    GLACIAL_LANCE = 824
    ASTRAL_BARRAGE = 825
    EERIE_SPELL = 826
    DIRE_CLAW = 827
    PSYSHIELD_BASH = 828
    # REMOVED(unimplemented status move) POWER_SHIFT = 829
    STONE_AXE = 830
    SPRINGTIDE_STORM = 831
    MYSTICAL_POWER = 832
    RAGING_FURY = 833
    WAVE_CRASH = 834
    CHLOROBLAST = 835
    MOUNTAIN_GALE = 836
    # REMOVED(unimplemented status move) VICTORY_DANCE = 837
    HEADLONG_RUSH = 838
    BARB_BARRAGE = 839
    ESPER_WING = 840
    BITTER_MALICE = 841
    # REMOVED(unimplemented status move) SHELTER = 842
    TRIPLE_ARROWS = 843
    INFERNAL_PARADE = 844
    CEASELESS_EDGE = 845
    BLEAKWIND_STORM = 846
    WILDBOLT_STORM = 847
    SANDSEAR_STORM = 848
    LUNAR_BLESSING = 849
    # REMOVED(unimplemented status move) TAKE_HEART = 850
    TERA_BLAST = 851
    SILK_TRAP = 852
    AXE_KICK = 853
    LAST_RESPECTS = 854
    LUMINA_CRASH = 855
    ORDER_UP = 856
    JET_PUNCH = 857
    # REMOVED(unimplemented status move) SPICY_EXTRACT = 858
    SPIN_OUT = 859
    POPULATION_BOMB = 860
    ICE_SPINNER = 861
    GLAIVE_RUSH = 862
    # REMOVED(unimplemented status move) REVIVAL_BLESSING = 863
    SALT_CURE = 864
    TRIPLE_DIVE = 865
    MORTAL_SPIN = 866
    # REMOVED(unimplemented status move) DOODLE = 867
    # REMOVED(unimplemented status move) FILLET_AWAY = 868
    KOWTOW_CLEAVE = 869
    FLOWER_TRICK = 870
    TORCH_SONG = 871
    AQUA_STEP = 872
    RAGING_BULL = 873
    MAKE_IT_RAIN = 874
    PSYBLADE = 875
    HYDRO_STEAM = 876
    RUINATION = 877
    COLLISION_COURSE = 878
    ELECTRO_DRIFT = 879
    SHED_TAIL = 880
    # REMOVED(unimplemented status move) CHILLY_RECEPTION = 881
    # REMOVED(unimplemented status move) TIDY_UP = 882
    # REMOVED(unimplemented status move) SNOWSCAPE = 883
    POUNCE = 884
    TRAILBLAZE = 885
    CHILLING_WATER = 886
    HYPER_DRILL = 887
    TWIN_BEAM = 888
    RAGE_FIST = 889
    ARMOR_CANNON = 890
    BITTER_BLADE = 891
    DOUBLE_SHOCK = 892
    GIGATON_HAMMER = 893
    COMEUPPANCE = 894
    AQUA_CUTTER = 895
    BLAZING_TORQUE = 896
    WICKED_TORQUE = 897
    NOXIOUS_TORQUE = 898
    COMBAT_TORQUE = 899
    MAGICAL_TORQUE = 900
    BLOOD_MOON = 901
    MATCHA_GOTCHA = 902
    SYRUP_BOMB = 903
    IVY_CUDGEL = 904
    ELECTRO_SHOT = 905
    TERA_STARSTORM = 906
    FICKLE_BEAM = 907
    BURNING_BULWARK = 908
    THUNDERCLAP = 909
    MIGHTY_CLEAVE = 910
    TACHYON_CUTTER = 911
    HARD_PRESS = 912
    # REMOVED(unimplemented status move) DRAGON_CHEER = 913
    ALLURING_VOICE = 914
    TEMPER_FLARE = 915
    SUPERCELL_SLAM = 916
    PSYCHIC_NOISE = 917
    UPPER_HAND = 918
    MALIGNANT_CHAIN = 919
    NIHIL_LIGHT = 920
    G_MAX_BEFUDDLE = 1000
    G_MAX_CANNONADE = 1000
    G_MAX_CENTIFERNO = 1000
    G_MAX_CHI_STRIKE = 1000
    G_MAX_CUDDLE = 1000
    G_MAX_DEPLETION = 1000
    G_MAX_DRUM_SOLO = 1000
    G_MAX_FINALE = 1000
    G_MAX_FIREBALL = 1000
    G_MAX_FOAM_BURST = 1000
    G_MAX_GOLD_RUSH = 1000
    G_MAX_GRAVITAS = 1000
    G_MAX_HYDROSNIPE = 1000
    G_MAX_MALODOR = 1000
    G_MAX_MELTDOWN = 1000
    G_MAX_ONE_BLOW = 1000
    G_MAX_RAPID_FLOW = 1000
    G_MAX_REPLENISH = 1000
    G_MAX_RESONANCE = 1000
    G_MAX_SANDBLAST = 1000
    G_MAX_SMITE = 1000
    G_MAX_SNOOZE = 1000
    G_MAX_STEELSURGE = 1000
    G_MAX_STONESURGE = 1000
    G_MAX_STUN_SHOCK = 1000
    G_MAX_SWEETNESS = 1000
    G_MAX_TARTNESS = 1000
    G_MAX_TERROR = 1000
    G_MAX_VINE_LASH = 1000
    G_MAX_VOLCALITH = 1000
    G_MAX_VOLT_CRASH = 1000
    G_MAX_WILDFIRE = 1000
    G_MAX_WIND_RAGE = 1000


class MoveCategory(IntEnum):
    PHYSICAL = 0
    SPECIAL = 1
    STATUS = 2


class MoveTarget(IntEnum):
    NORMAL = 0
    SELF = 1
    ALL_ADJACENT_FOES = 2
    ALL_ADJACENT = 3
    ALLY = 4
    ANY = 5
    ALLY_SIDE = 6
    FOE_SIDE = 7
    ALL = 8
    RANDOM_NORMAL = 9


class MoveTag(IntFlag):
    NONE = 0
    DAMAGE = 1
    SETUP = 2
    RECOVERY = 4
    STATUS = 8
    PIVOT = 16
    HAZARD = 32
    SCREEN = 64
    CONTACT = 128   # move makes physical contact (triggers abilities like Rough Skin, Static)
    SOUND  = 256    # blocked by Soundproof; boosted by Punk Rock; converted by Liquid Voice
    BULLET = 512    # blocked by Bulletproof
    PULSE  = 1024   # boosted by Mega Launcher
    BITING   = 2048  # boosted by Strong Jaw
    PUNCHING = 4096  # boosted by Iron Fist
    SLICING  = 8192  # boosted by Sharpness
    POWDER   = 16384  # powder/spore moves; blocked by Safety Goggles and Grass-type immunity


@dataclass(frozen=True)
class SecondaryEffect:
    chance: int  # 0-100 percentage
    status: Optional[Status] = None
    flinch: bool = False
    stat_changes: tuple = ()
    volatile: Optional[str] = None


@dataclass(frozen=True)
class MoveData:
    move_type: Type
    category: MoveCategory
    base_power: int
    accuracy: Optional[int]  # None = always hits
    pp: int
    priority: int
    target: MoveTarget
    tags: MoveTag
    secondary: Optional[SecondaryEffect] = None
    drain: Optional[tuple] = None  # (numerator, denominator)
    recoil: Optional[tuple] = None  # (numerator, denominator)
    flags: int = 0
    min_hits: int = 1
    max_hits: int = 1
    crit_boost: int = 0  # added to stage before clamp; 1=high-crit, 3=always-crit
    secondary2: Optional[SecondaryEffect] = None  # second independent secondary (e.g. Fang moves)
    self_stat_changes: tuple = ()
    # Each entry is (stat_index, delta) applied to user after dealing damage; not suppressed by Sheer Force


MOVE_DATA: dict[Move, MoveData] = {
    Move.NONE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 0, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.POUND: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 40, 100, 35, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.KARATE_CHOP: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 50, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.DOUBLE_SLAP: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 15, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 5),
    Move.COMET_PUNCH: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 18, 90, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, None, None, None, 0, 2, 5),
    Move.MEGA_PUNCH: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 80, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, None, None, None),
    Move.PAY_DAY: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 40, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FIRE_PUNCH: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 75, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, SecondaryEffect(10, Status.BURN, False), None, None),
    Move.ICE_PUNCH: MoveData(Type.ICE, MoveCategory.PHYSICAL, 75, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, SecondaryEffect(10, Status.FREEZE, False), None, None),
    Move.THUNDER_PUNCH: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 75, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, SecondaryEffect(10, Status.PARALYSIS, False), None, None),
    Move.SCRATCH: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 40, 100, 35, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.VISE_GRIP: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 55, 100, 30, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.GUILLOTINE: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 0, 30, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.RAZOR_WIND: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.SWORDS_DANCE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.CUT: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 50, 100, 30, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.GUST: MoveData(Type.FLYING, MoveCategory.SPECIAL, 40, 100, 35, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    Move.WING_ATTACK: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 60, 100, 35, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    Move.WHIRLWIND: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, -6, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.FLY: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 90, 100, 15, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    Move.BIND: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 15, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SLAM: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 80, 90, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.VINE_WHIP: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 45, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.STOMP: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 65, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.DOUBLE_KICK: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 30, 100, 30, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 2),
    Move.MEGA_KICK: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 120, 85, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.JUMP_KICK: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 100, 95, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ROLLING_KICK: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.SAND_ATTACK: MoveData(Type.GROUND, MoveCategory.STATUS, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.HEADBUTT: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 70, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.HORN_ATTACK: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 65, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FURY_ATTACK: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 15, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 5),
    Move.HORN_DRILL: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 0, 30, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.TACKLE: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 40, 100, 35, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BODY_SLAM: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 85, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.PARALYSIS, False), None, None),
    Move.WRAP: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 15, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.TAKE_DOWN: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 90, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, (1, 4)),
    Move.THRASH: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 120, 100, 10, 0, MoveTarget.RANDOM_NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.DOUBLE_EDGE: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 120, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, (33, 100)),
    Move.TAIL_WHIP: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 30, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.NONE, None, None, None),
    Move.POISON_STING: MoveData(Type.POISON, MoveCategory.PHYSICAL, 15, 100, 35, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.POISON, False), None, None),
    Move.TWINEEDLE: MoveData(Type.BUG, MoveCategory.PHYSICAL, 25, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, Status.POISON, False), None, None),
    Move.PIN_MISSILE: MoveData(Type.BUG, MoveCategory.PHYSICAL, 25, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 5),
    Move.LEER: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.NONE, None, None, None),
    Move.BITE: MoveData(Type.DARK, MoveCategory.PHYSICAL, 60, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.GROWL: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.NONE, None, None, None),
    Move.ROAR: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, -6, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SING: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 70, 15, 0, MoveTarget.NORMAL, MoveTag.STATUS, None, None, None),
    Move.SUPERSONIC: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 70, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SONIC_BOOM: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 0, 100, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.DISABLE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ACID: MoveData(Type.POISON, MoveCategory.SPECIAL, 40, 100, 30, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((3, -1, False),)), None, None),
    Move.EMBER: MoveData(Type.FIRE, MoveCategory.SPECIAL, 40, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.BURN, False), None, None),
    Move.FLAMETHROWER: MoveData(Type.FIRE, MoveCategory.SPECIAL, 90, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.BURN, False), None, None),
    # REMOVED(unimplemented status move) Move.MIST: MoveData(Type.ICE, MoveCategory.STATUS, 0, None, 30, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.WATER_GUN: MoveData(Type.WATER, MoveCategory.SPECIAL, 40, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HYDRO_PUMP: MoveData(Type.WATER, MoveCategory.SPECIAL, 110, 85, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SURF: MoveData(Type.WATER, MoveCategory.SPECIAL, 90, 100, 15, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, None, None, None),
    Move.ICE_BEAM: MoveData(Type.ICE, MoveCategory.SPECIAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.FREEZE, False), None, None),
    Move.BLIZZARD: MoveData(Type.ICE, MoveCategory.SPECIAL, 110, 80, 5, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(10, Status.FREEZE, False), None, None),
    Move.PSYBEAM: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 65, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, volatile="confused"), None, None),
    Move.BUBBLE_BEAM: MoveData(Type.WATER, MoveCategory.SPECIAL, 65, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((4, -1, False),)), None, None),
    Move.AURORA_BEAM: MoveData(Type.ICE, MoveCategory.SPECIAL, 65, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((0, -1, False),)), None, None),
    Move.HYPER_BEAM: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 150, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.PECK: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 35, 100, 35, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    Move.DRILL_PECK: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 80, 100, 20, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    Move.SUBMISSION: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 80, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, (1, 4)),
    Move.LOW_KICK: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 0, 100, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.COUNTER: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 0, 100, 20, -5, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SEISMIC_TOSS: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 0, 100, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.STRENGTH: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ABSORB: MoveData(Type.GRASS, MoveCategory.SPECIAL, 40, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, (1, 2), None),
    Move.MEGA_DRAIN: MoveData(Type.GRASS, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, (1, 2), None),
    Move.LEECH_SEED: MoveData(Type.GRASS, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.GROWTH: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.RAZOR_LEAF: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 55, 100, 25, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.SOLAR_BEAM: MoveData(Type.GRASS, MoveCategory.SPECIAL, 120, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.POISON_POWDER: MoveData(Type.POISON, MoveCategory.STATUS, 0, 90, 35, 0, MoveTarget.NORMAL, MoveTag.STATUS | MoveTag.POWDER, None, None, None),
    Move.STUN_SPORE: MoveData(Type.GRASS, MoveCategory.STATUS, 0, 90, 30, 0, MoveTarget.NORMAL, MoveTag.STATUS | MoveTag.POWDER, None, None, None),
    Move.SLEEP_POWDER: MoveData(Type.GRASS, MoveCategory.STATUS, 0, 80, 15, 0, MoveTarget.NORMAL, MoveTag.STATUS | MoveTag.POWDER, None, None, None),
    Move.PETAL_DANCE: MoveData(Type.GRASS, MoveCategory.SPECIAL, 120, 100, 10, 0, MoveTarget.RANDOM_NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.STRING_SHOT: MoveData(Type.BUG, MoveCategory.STATUS, 0, 95, 40, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.NONE, None, None, None),
    Move.DRAGON_RAGE: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.FIRE_SPIN: MoveData(Type.FIRE, MoveCategory.SPECIAL, 35, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.THUNDER_SHOCK: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 40, 100, 30, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.PARALYSIS, False), None, None),
    Move.THUNDERBOLT: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 90, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.PARALYSIS, False), None, None),
    Move.THUNDER_WAVE: MoveData(Type.ELECTRIC, MoveCategory.STATUS, 0, 90, 20, 0, MoveTarget.NORMAL, MoveTag.STATUS, None, None, None),
    Move.THUNDER: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 110, 80, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.PARALYSIS, False), None, None),
    Move.ROCK_THROW: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 50, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.EARTHQUAKE: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 100, 100, 10, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, None, None, None),
    Move.FISSURE: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 0, 30, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.DIG: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.TOXIC: MoveData(Type.POISON, MoveCategory.STATUS, 0, 90, 10, 0, MoveTarget.NORMAL, MoveTag.STATUS, None, None, None),
    Move.CONFUSION: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 50, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, volatile="confused"), None, None),
    Move.PSYCHIC: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((3, -1, False),)), None, None),
    Move.HYPNOSIS: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, 70, 20, 0, MoveTarget.NORMAL, MoveTag.STATUS, None, None, None),
    Move.MEDITATE: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 40, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.AGILITY: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 30, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.QUICK_ATTACK: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 40, 100, 30, 1, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.RAGE: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 20, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.TELEPORT: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 20, -6, MoveTarget.SELF, MoveTag.PIVOT, None, None, None),
    Move.NIGHT_SHADE: MoveData(Type.GHOST, MoveCategory.SPECIAL, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.MIMIC: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SCREECH: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.DOUBLE_TEAM: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.RECOVER: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.HARDEN: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.MINIMIZE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.SMOKESCREEN: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.CONFUSE_RAY: MoveData(Type.GHOST, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.WITHDRAW: MoveData(Type.WATER, MoveCategory.STATUS, 0, None, 40, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.DEFENSE_CURL: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 40, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.BARRIER: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.LIGHT_SCREEN: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 30, 0, MoveTarget.NORMAL, MoveTag.SCREEN, None, None, None),
    Move.HAZE: MoveData(Type.ICE, MoveCategory.STATUS, 0, None, 30, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.REFLECT: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.NORMAL, MoveTag.SCREEN, None, None, None),
    Move.FOCUS_ENERGY: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 30, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.METRONOME: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.MIRROR_MOVE: MoveData(Type.FLYING, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SELF_DESTRUCT: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 200, 100, 5, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, None, None, None),
    Move.EGG_BOMB: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 100, 75, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.LICK: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 40, 100, 30, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.PARALYSIS, False), None, None),
    Move.SMOG: MoveData(Type.POISON, MoveCategory.SPECIAL, 30, 90, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, Status.POISON, False), None, None),
    Move.SLUDGE: MoveData(Type.POISON, MoveCategory.SPECIAL, 65, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.POISON, False), None, None),
    Move.BONE_CLUB: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 65, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, True), None, None),
    Move.FIRE_BLAST: MoveData(Type.FIRE, MoveCategory.SPECIAL, 110, 85, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.BURN, False), None, None),
    Move.WATERFALL: MoveData(Type.WATER, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, None, True), None, None),
    Move.CLAMP: MoveData(Type.WATER, MoveCategory.PHYSICAL, 35, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SWIFT: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 60, None, 20, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.SKULL_BASH: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 130, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SPIKE_CANNON: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 20, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.CONSTRICT: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 10, 100, 35, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False), None, None),
    Move.AMNESIA: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.KINESIS: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SOFT_BOILED: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.HIGH_JUMP_KICK: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 130, 90, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.GLARE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 30, 0, MoveTarget.NORMAL, MoveTag.STATUS, None, None, None),
    Move.DREAM_EATER: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 100, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, (1, 2), None),
    Move.POISON_GAS: MoveData(Type.POISON, MoveCategory.STATUS, 0, 90, 40, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.STATUS, None, None, None),
    Move.BARRAGE: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 15, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.LEECH_LIFE: MoveData(Type.BUG, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, (1, 2), None),
    Move.LOVELY_KISS: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 80, 10, 0, MoveTarget.NORMAL, MoveTag.STATUS, None, None, None),
    Move.SKY_ATTACK: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 140, 100, 5, 0, MoveTarget.ANY, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None, crit_boost=1),
    Move.TRANSFORM: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.BUBBLE: MoveData(Type.WATER, MoveCategory.SPECIAL, 40, 100, 30, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(10, None, False), None, None),
    Move.DIZZY_PUNCH: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 70, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, None, False, volatile="confused"), None, None),
    Move.SPORE: MoveData(Type.GRASS, MoveCategory.STATUS, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.STATUS | MoveTag.POWDER, None, None, None),
    Move.FLASH: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 70, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.PSYWAVE: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SPLASH: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 40, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.ACID_ARMOR: MoveData(Type.POISON, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.CRABHAMMER: MoveData(Type.WATER, MoveCategory.PHYSICAL, 100, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.EXPLOSION: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 250, 100, 5, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, None, None, None),
    Move.FURY_SWIPES: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 18, 90, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 5),
    Move.BONEMERANG: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 50, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 2),
    Move.REST: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.ROCK_SLIDE: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 75, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.HYPER_FANG: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, True), None, None),
    Move.SHARPEN: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 30, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    # REMOVED(unimplemented status move) Move.CONVERSION: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 30, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.TRI_ATTACK: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, None, False), None, None),
    Move.SUPER_FANG: MoveData(Type.DARK, MoveCategory.PHYSICAL, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SLASH: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 70, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.SUBSTITUTE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.STRUGGLE: MoveData(Type.TYPELESS, MoveCategory.PHYSICAL, 50, None, 1, 0, MoveTarget.RANDOM_NORMAL, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.SKETCH: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 1, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.TRIPLE_KICK: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 10, 90, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.THIEF: MoveData(Type.DARK, MoveCategory.PHYSICAL, 60, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.SPIDER_WEB: MoveData(Type.BUG, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.NIGHTMARE: MoveData(Type.GHOST, MoveCategory.STATUS, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.FLAME_WHEEL: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 60, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.BURN, False), None, None),
    Move.SNORE: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 50, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.CURSE: MoveData(Type.GHOST, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.SETUP, None, None, None),
    Move.FLAIL: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.CONVERSION_2: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 30, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.AEROBLAST: MoveData(Type.FLYING, MoveCategory.SPECIAL, 100, 100, 5, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    Move.COTTON_SPORE: MoveData(Type.GRASS, MoveCategory.STATUS, 0, 100, 40, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.POWDER, None, None, None),
    Move.REVERSAL: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.SPITE: MoveData(Type.GHOST, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.POWDER_SNOW: MoveData(Type.ICE, MoveCategory.SPECIAL, 40, 100, 25, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(10, Status.FREEZE, False), None, None),
    Move.PROTECT: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 4, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.MACH_PUNCH: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 40, 100, 30, 1, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, None, None, None),
    Move.SCARY_FACE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.FEINT_ATTACK: MoveData(Type.DARK, MoveCategory.PHYSICAL, 60, None, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SWEET_KISS: MoveData(Type.FAIRY, MoveCategory.STATUS, 0, 80, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.BELLY_DRUM: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.SLUDGE_BOMB: MoveData(Type.POISON, MoveCategory.SPECIAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.POISON, False), None, None),
    Move.MUD_SLAP: MoveData(Type.GROUND, MoveCategory.SPECIAL, 20, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((5, -1, False),)), None, None),
    Move.OCTAZOOKA: MoveData(Type.WATER, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, False, ((5, -1, False),)), None, None),
    Move.SPIKES: MoveData(Type.GROUND, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.FOE_SIDE, MoveTag.HAZARD, None, None, None),
    Move.ZAP_CANNON: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 120, 50, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, Status.PARALYSIS, False), None, None),
    Move.FORESIGHT: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 40, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.DESTINY_BOND: MoveData(Type.GHOST, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.PERISH_SONG: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.ICY_WIND: MoveData(Type.ICE, MoveCategory.SPECIAL, 55, 100, 15, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((4, -1, False),)), None, None),
    Move.DETECT: MoveData(Type.FIGHTING, MoveCategory.STATUS, 0, None, 5, 4, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.BONE_RUSH: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 25, 90, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 5),
    Move.OUTRAGE: MoveData(Type.DRAGON, MoveCategory.PHYSICAL, 120, 100, 10, 0, MoveTarget.RANDOM_NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SANDSTORM: MoveData(Type.ROCK, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.GIGA_DRAIN: MoveData(Type.GRASS, MoveCategory.SPECIAL, 75, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, (1, 2), None),
    Move.ENDURE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 4, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.CHARM: MoveData(Type.FAIRY, MoveCategory.STATUS, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ROLLOUT: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 30, 90, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FALSE_SWIPE: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 40, 100, 40, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SWAGGER: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 90, 15, 0, MoveTarget.NORMAL, MoveTag.SETUP, None, None, None),
    Move.MILK_DRINK: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.SPARK: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 65, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.PARALYSIS, False), None, None),
    Move.FURY_CUTTER: MoveData(Type.BUG, MoveCategory.PHYSICAL, 40, 95, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.STEEL_WING: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 70, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((1, 1, True),)), None, None),
    Move.MEAN_LOOK: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ATTRACT: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SLEEP_TALK: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.HEAL_BELL: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.ALLY_SIDE, MoveTag.NONE, None, None, None),
    Move.RETURN: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 102, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.PRESENT: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 0, 90, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.FRUSTRATION: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 102, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SAFEGUARD: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 25, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.PAIN_SPLIT: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SACRED_FIRE: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(50, Status.BURN, False), None, None),
    Move.MAGNITUDE: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 0, 100, 30, 0, MoveTarget.ALL_ADJACENT, MoveTag.NONE, None, None, None),
    Move.DYNAMIC_PUNCH: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 100, 50, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, SecondaryEffect(100, None, False, volatile="confused"), None, None),
    Move.MEGAHORN: MoveData(Type.BUG, MoveCategory.PHYSICAL, 120, 90, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.DRAGON_BREATH: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 60, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.PARALYSIS, False), None, None),
    Move.BATON_PASS: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 40, 0, MoveTarget.SELF, MoveTag.PIVOT, None, None, None),
    Move.ENCORE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.PURSUIT: MoveData(Type.DARK, MoveCategory.PHYSICAL, 40, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.RAPID_SPIN: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 50, 100, 40, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, self_stat_changes=((4, 1),)),
    Move.SWEET_SCENT: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 20, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.NONE, None, None, None),
    Move.IRON_TAIL: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 100, 85, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, False, ((1, -1, False),)), None, None),
    Move.METAL_CLAW: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 50, 100, 35, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((0, 1, True),)), None, None),
    Move.VITAL_THROW: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 70, None, 10, -1, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MORNING_SUN: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.SYNTHESIS: MoveData(Type.GRASS, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.MOONLIGHT: MoveData(Type.FAIRY, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.HIDDEN_POWER: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_BUG: MoveData(Type.BUG, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_DARK: MoveData(Type.DARK, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_DRAGON: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_ELECTRIC: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_FIGHTING: MoveData(Type.FIGHTING, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_FIRE: MoveData(Type.FIRE, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_FLYING: MoveData(Type.FLYING, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_GHOST: MoveData(Type.GHOST, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_GRASS: MoveData(Type.GRASS, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_GROUND: MoveData(Type.GROUND, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_ICE: MoveData(Type.ICE, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_POISON: MoveData(Type.POISON, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_PSYCHIC: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_ROCK: MoveData(Type.ROCK, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_STEEL: MoveData(Type.STEEL, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HIDDEN_POWER_WATER: MoveData(Type.WATER, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.CROSS_CHOP: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 100, 90, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.TWISTER: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 40, 100, 20, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(20, None, True), None, None),
    Move.RAIN_DANCE: MoveData(Type.WATER, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.SUNNY_DAY: MoveData(Type.FIRE, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.CRUNCH: MoveData(Type.DARK, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, None, False, ((1, -1, False),)), None, None),
    Move.MIRROR_COAT: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 0, 100, 20, -5, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.PSYCH_UP: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.EXTREME_SPEED: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 80, 100, 5, 2, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ANCIENT_POWER: MoveData(Type.ROCK, MoveCategory.SPECIAL, 60, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((0, 1, True), (1, 1, True), (2, 1, True), (3, 1, True), (4, 1, True),)), None, None),
    Move.SHADOW_BALL: MoveData(Type.GHOST, MoveCategory.SPECIAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, None, False, ((3, -1, False),)), None, None),
    Move.FUTURE_SIGHT: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 120, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ROCK_SMASH: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 40, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((1, -1, False),)), None, None),
    Move.WHIRLPOOL: MoveData(Type.WATER, MoveCategory.SPECIAL, 35, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BEAT_UP: MoveData(Type.DARK, MoveCategory.PHYSICAL, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.FAKE_OUT: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 40, 100, 5, 3, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, True), None, None),
    Move.UPROAR: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 90, 100, 10, 0, MoveTarget.RANDOM_NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.STOCKPILE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.SPIT_UP: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SWALLOW: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.HEAT_WAVE: MoveData(Type.FIRE, MoveCategory.SPECIAL, 95, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(10, Status.BURN, False), None, None),
    Move.HAIL: MoveData(Type.ICE, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.TORMENT: MoveData(Type.DARK, MoveCategory.STATUS, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.FLATTER: MoveData(Type.DARK, MoveCategory.STATUS, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.SETUP, None, None, None),
    Move.WILL_O_WISP: MoveData(Type.FIRE, MoveCategory.STATUS, 0, 85, 15, 0, MoveTarget.NORMAL, MoveTag.STATUS, None, None, None),
    Move.MEMENTO: MoveData(Type.DARK, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.FACADE: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 70, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FOCUS_PUNCH: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 150, 100, 20, -3, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, None, None, None),
    Move.SMELLING_SALTS: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 70, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FOLLOW_ME: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, 2, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.NATURE_POWER: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.CHARGE: MoveData(Type.ELECTRIC, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.TAUNT: MoveData(Type.DARK, MoveCategory.STATUS, 0, 100, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.HELPING_HAND: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, 5, MoveTarget.ALLY, MoveTag.NONE, None, None, None),
    Move.TRICK: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ROLE_PLAY: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.WISH: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.ASSIST: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.INGRAIN: MoveData(Type.GRASS, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.SUPERPOWER: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 120, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, self_stat_changes=((0, -1), (1, -1))),
    Move.MAGIC_COAT: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 15, 4, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.RECYCLE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.REVENGE: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 60, 100, 10, -4, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BRICK_BREAK: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 75, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.YAWN: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.STATUS, None, None, None),
    Move.KNOCK_OFF: MoveData(Type.DARK, MoveCategory.PHYSICAL, 65, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ENDEAVOR: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ERUPTION: MoveData(Type.FIRE, MoveCategory.SPECIAL, 150, 100, 5, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.SKILL_SWAP: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.IMPRISON: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.REFRESH: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.GRUDGE: MoveData(Type.GHOST, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.SNATCH: MoveData(Type.DARK, MoveCategory.STATUS, 0, None, 10, 4, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.SECRET_POWER: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 70, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.PARALYSIS, False), None, None),
    Move.DIVE: MoveData(Type.WATER, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ARM_THRUST: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 15, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 5),
    # REMOVED(unimplemented status move) Move.CAMOUFLAGE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.TAIL_GLOW: MoveData(Type.BUG, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.LUSTER_PURGE: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 95, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(50, None, False, ((3, -1, False),)), None, None),
    Move.MIST_BALL: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 95, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(50, None, False, ((2, -1, False),)), None, None),
    Move.FEATHER_DANCE: MoveData(Type.FLYING, MoveCategory.STATUS, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.TEETER_DANCE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 20, 0, MoveTarget.ALL_ADJACENT, MoveTag.NONE, None, None, None),
    Move.BLAZE_KICK: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 85, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.BURN, False), None, None, crit_boost=1),
    # REMOVED(unimplemented status move) Move.MUD_SPORT: MoveData(Type.GROUND, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.ICE_BALL: MoveData(Type.ICE, MoveCategory.PHYSICAL, 30, 90, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.NEEDLE_ARM: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.SLACK_OFF: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.HYPER_VOICE: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 90, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.POISON_FANG: MoveData(Type.POISON, MoveCategory.PHYSICAL, 50, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(50, Status.TOXIC, False), None, None),
    Move.CRUSH_CLAW: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 75, 95, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(50, None, False, ((1, -1, False),)), None, None),
    Move.BLAST_BURN: MoveData(Type.FIRE, MoveCategory.SPECIAL, 150, 90, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HYDRO_CANNON: MoveData(Type.WATER, MoveCategory.SPECIAL, 150, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.METEOR_MASH: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, None, False, ((0, 1, True),)), None, None),
    Move.ASTONISH: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 40, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.WEATHER_BALL: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 50, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.AROMATHERAPY: MoveData(Type.GRASS, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.ALLY_SIDE, MoveTag.NONE, None, None, None),
    Move.FAKE_TEARS: MoveData(Type.DARK, MoveCategory.STATUS, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.AIR_CUTTER: MoveData(Type.FLYING, MoveCategory.SPECIAL, 60, 100, 25, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.OVERHEAT: MoveData(Type.FIRE, MoveCategory.SPECIAL, 130, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, self_stat_changes=((2, -2),)),
    Move.ODOR_SLEUTH: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 40, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ROCK_TOMB: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 60, 95, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((4, -1, False),)), None, None),
    Move.SILVER_WIND: MoveData(Type.BUG, MoveCategory.SPECIAL, 60, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((0, 1, True), (1, 1, True), (2, 1, True), (3, 1, True), (4, 1, True),)), None, None),
    Move.METAL_SOUND: MoveData(Type.STEEL, MoveCategory.STATUS, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.GRASS_WHISTLE: MoveData(Type.GRASS, MoveCategory.STATUS, 0, 70, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.TICKLE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.COSMIC_POWER: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.WATER_SPOUT: MoveData(Type.WATER, MoveCategory.SPECIAL, 150, 100, 5, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.SIGNAL_BEAM: MoveData(Type.BUG, MoveCategory.SPECIAL, 75, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, volatile="confused"), None, None),
    Move.SHADOW_PUNCH: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 60, None, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, None, None, None),
    Move.EXTRASENSORY: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 80, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, True), None, None),
    Move.SKY_UPPERCUT: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 85, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, None, None, None),
    Move.SAND_TOMB: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 35, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SHEER_COLD: MoveData(Type.ICE, MoveCategory.SPECIAL, 0, 30, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.MUDDY_WATER: MoveData(Type.WATER, MoveCategory.SPECIAL, 90, 95, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(30, None, False, ((5, -1, False),)), None, None),
    Move.BULLET_SEED: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 25, 100, 30, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 5),
    Move.AERIAL_ACE: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 60, None, 20, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    Move.ICICLE_SPEAR: MoveData(Type.ICE, MoveCategory.PHYSICAL, 25, 100, 30, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 5),
    Move.IRON_DEFENSE: MoveData(Type.STEEL, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.BLOCK: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.HOWL: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 40, 0, MoveTarget.ALLY_SIDE, MoveTag.SETUP, None, None, None),
    Move.DRAGON_CLAW: MoveData(Type.DRAGON, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FRENZY_PLANT: MoveData(Type.GRASS, MoveCategory.SPECIAL, 150, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BULK_UP: MoveData(Type.FIGHTING, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.BOUNCE: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 85, 95, 5, 0, MoveTarget.ANY, MoveTag.DAMAGE, SecondaryEffect(30, Status.PARALYSIS, False), None, None),
    Move.MUD_SHOT: MoveData(Type.GROUND, MoveCategory.SPECIAL, 55, 95, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((4, -1, False),)), None, None),
    Move.POISON_TAIL: MoveData(Type.POISON, MoveCategory.PHYSICAL, 50, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.POISON, False), None, None, crit_boost=1),
    Move.COVET: MoveData(Type.FAIRY, MoveCategory.PHYSICAL, 60, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.VOLT_TACKLE: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 120, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.PARALYSIS, False), None, (33, 100)),
    Move.MAGICAL_LEAF: MoveData(Type.GRASS, MoveCategory.SPECIAL, 60, None, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.WATER_SPORT: MoveData(Type.WATER, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.CALM_MIND: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.LEAF_BLADE: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 90, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.DRAGON_DANCE: MoveData(Type.DRAGON, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.ROCK_BLAST: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 25, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 5),
    Move.SHOCK_WAVE: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 60, None, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.WATER_PULSE: MoveData(Type.WATER, MoveCategory.SPECIAL, 60, 100, 20, 0, MoveTarget.ANY, MoveTag.DAMAGE, SecondaryEffect(20, None, False, volatile="confused"), None, None),
    Move.DOOM_DESIRE: MoveData(Type.STEEL, MoveCategory.SPECIAL, 140, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.PSYCHO_BOOST: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 140, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, self_stat_changes=((2, -2),)),
    Move.ROOST: MoveData(Type.FLYING, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.GRAVITY: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.MIRACLE_EYE: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 40, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.WAKE_UP_SLAP: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 70, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HAMMER_ARM: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 100, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, None, None, None, self_stat_changes=((4, -1),)),
    Move.GYRO_BALL: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.HEALING_WISH: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.BRINE: MoveData(Type.WATER, MoveCategory.SPECIAL, 65, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.NATURAL_GIFT: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.FEINT: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 30, 100, 10, 2, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.PLUCK: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 60, 100, 20, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    Move.TAILWIND: MoveData(Type.FLYING, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ACUPRESSURE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 30, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.METAL_BURST: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.U_TURN: MoveData(Type.BUG, MoveCategory.PHYSICAL, 70, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PIVOT, None, None, None),
    Move.CLOSE_COMBAT: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 120, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, self_stat_changes=((1, -1), (3, -1))),
    Move.PAYBACK: MoveData(Type.DARK, MoveCategory.PHYSICAL, 50, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ASSURANCE: MoveData(Type.DARK, MoveCategory.PHYSICAL, 60, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.EMBARGO: MoveData(Type.DARK, MoveCategory.STATUS, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.FLING: MoveData(Type.DARK, MoveCategory.PHYSICAL, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.PSYCHO_SHIFT: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.TRUMP_CARD: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 0, None, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.WRING_OUT: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.POWER_TRICK: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.GASTRO_ACID: MoveData(Type.POISON, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.LUCKY_CHANT: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 30, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ME_FIRST: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.COPYCAT: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.POWER_SWAP: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.GUARD_SWAP: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.PUNISHMENT: MoveData(Type.DARK, MoveCategory.PHYSICAL, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.LAST_RESORT: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 140, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.WORRY_SEED: MoveData(Type.GRASS, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SUCKER_PUNCH: MoveData(Type.DARK, MoveCategory.PHYSICAL, 70, 100, 5, 1, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, None, None, None),
    Move.TOXIC_SPIKES: MoveData(Type.POISON, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.FOE_SIDE, MoveTag.HAZARD, None, None, None),
    # REMOVED(unimplemented status move) Move.HEART_SWAP: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.AQUA_RING: MoveData(Type.WATER, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.MAGNET_RISE: MoveData(Type.ELECTRIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.FLARE_BLITZ: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 120, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.BURN, False), None, (33, 100)),
    Move.FORCE_PALM: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 60, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.PARALYSIS, False), None, None),
    Move.AURA_SPHERE: MoveData(Type.FIGHTING, MoveCategory.SPECIAL, 80, None, 20, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    Move.ROCK_POLISH: MoveData(Type.ROCK, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.POISON_JAB: MoveData(Type.POISON, MoveCategory.PHYSICAL, 80, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.POISON, False), None, None),
    Move.DARK_PULSE: MoveData(Type.DARK, MoveCategory.SPECIAL, 80, 100, 15, 0, MoveTarget.ANY, MoveTag.DAMAGE, SecondaryEffect(20, None, True), None, None),
    Move.NIGHT_SLASH: MoveData(Type.DARK, MoveCategory.PHYSICAL, 70, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.AQUA_TAIL: MoveData(Type.WATER, MoveCategory.PHYSICAL, 90, 95, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SEED_BOMB: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.AIR_SLASH: MoveData(Type.FLYING, MoveCategory.SPECIAL, 75, 100, 15, 0, MoveTarget.ANY, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.X_SCISSOR: MoveData(Type.BUG, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BUG_BUZZ: MoveData(Type.BUG, MoveCategory.SPECIAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((3, -1, False),)), None, None),
    Move.DRAGON_PULSE: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 85, 100, 10, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    Move.DRAGON_RUSH: MoveData(Type.DRAGON, MoveCategory.PHYSICAL, 100, 85, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, None, True), None, None),
    Move.POWER_GEM: MoveData(Type.ROCK, MoveCategory.SPECIAL, 80, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.DRAIN_PUNCH: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 75, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, None, (1, 2), None),
    Move.VACUUM_WAVE: MoveData(Type.FIGHTING, MoveCategory.SPECIAL, 40, 100, 30, 1, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FOCUS_BLAST: MoveData(Type.FIGHTING, MoveCategory.SPECIAL, 120, 80, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((3, -1, False),)), None, None),
    Move.ENERGY_BALL: MoveData(Type.GRASS, MoveCategory.SPECIAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((3, -1, False),)), None, None),
    Move.BRAVE_BIRD: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 120, 100, 15, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, (33, 100)),
    Move.EARTH_POWER: MoveData(Type.GROUND, MoveCategory.SPECIAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((3, -1, False),)), None, None),
    Move.SWITCHEROO: MoveData(Type.DARK, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.GIGA_IMPACT: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 150, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.NASTY_PLOT: MoveData(Type.DARK, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.BULLET_PUNCH: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 40, 100, 30, 1, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, None, None, None),
    Move.AVALANCHE: MoveData(Type.ICE, MoveCategory.PHYSICAL, 60, 100, 10, -4, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ICE_SHARD: MoveData(Type.ICE, MoveCategory.PHYSICAL, 40, 100, 30, 1, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SHADOW_CLAW: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 70, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.THUNDER_FANG: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 65, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.PARALYSIS, False), None, None, secondary2=SecondaryEffect(10, None, True)),
    Move.ICE_FANG: MoveData(Type.ICE, MoveCategory.PHYSICAL, 65, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.FREEZE, False), None, None, secondary2=SecondaryEffect(10, None, True)),
    Move.FIRE_FANG: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 65, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.BURN, False), None, None, secondary2=SecondaryEffect(10, None, True)),
    Move.SHADOW_SNEAK: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 40, 100, 30, 1, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MUD_BOMB: MoveData(Type.GROUND, MoveCategory.SPECIAL, 65, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, None, False), None, None),
    Move.PSYCHO_CUT: MoveData(Type.PSYCHIC, MoveCategory.PHYSICAL, 70, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.ZEN_HEADBUTT: MoveData(Type.PSYCHIC, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, None, True), None, None),
    Move.MIRROR_SHOT: MoveData(Type.STEEL, MoveCategory.SPECIAL, 65, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, False, ((5, -1, False),)), None, None),
    Move.FLASH_CANNON: MoveData(Type.STEEL, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((3, -1, False),)), None, None),
    Move.ROCK_CLIMB: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 90, 95, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, None, False), None, None),
    Move.DEFOG: MoveData(Type.FLYING, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.TRICK_ROOM: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 5, -7, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.DRACO_METEOR: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 130, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, self_stat_changes=((2, -2),)),
    Move.DISCHARGE: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 80, 100, 15, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, SecondaryEffect(30, Status.PARALYSIS, False), None, None),
    Move.LAVA_PLUME: MoveData(Type.FIRE, MoveCategory.SPECIAL, 80, 100, 15, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, SecondaryEffect(30, Status.BURN, False), None, None),
    Move.LEAF_STORM: MoveData(Type.GRASS, MoveCategory.SPECIAL, 130, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, self_stat_changes=((2, -2),)),
    Move.POWER_WHIP: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 120, 90, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ROCK_WRECKER: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 150, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.CROSS_POISON: MoveData(Type.POISON, MoveCategory.PHYSICAL, 70, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.POISON, False), None, None, crit_boost=1),
    Move.GUNK_SHOT: MoveData(Type.POISON, MoveCategory.PHYSICAL, 120, 85, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.POISON, False), None, None),
    Move.IRON_HEAD: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.MAGNET_BOMB: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 60, None, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.STONE_EDGE: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 100, 85, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.CAPTIVATE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 5, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.NONE, None, None, None),
    Move.STEALTH_ROCK: MoveData(Type.ROCK, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.FOE_SIDE, MoveTag.HAZARD, None, None, None),
    Move.GRASS_KNOT: MoveData(Type.GRASS, MoveCategory.SPECIAL, 0, 100, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.CHATTER: MoveData(Type.FLYING, MoveCategory.SPECIAL, 65, 100, 20, 0, MoveTarget.ANY, MoveTag.DAMAGE, SecondaryEffect(100, None, False, volatile="confused"), None, None),
    Move.JUDGMENT: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 100, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BUG_BITE: MoveData(Type.BUG, MoveCategory.PHYSICAL, 60, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.CHARGE_BEAM: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 40, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((2, 1, True),)), None, None),
    Move.WOOD_HAMMER: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 120, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, (33, 100)),
    Move.AQUA_JET: MoveData(Type.WATER, MoveCategory.PHYSICAL, 40, 100, 20, 1, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ATTACK_ORDER: MoveData(Type.BUG, MoveCategory.PHYSICAL, 90, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.DEFEND_ORDER: MoveData(Type.BUG, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.HEAL_ORDER: MoveData(Type.BUG, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.HEAD_SMASH: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 150, 85, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, (1, 2)),
    Move.DOUBLE_HIT: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 35, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 2),
    Move.ROAR_OF_TIME: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 150, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SPACIAL_REND: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 100, 95, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.LUNAR_DANCE: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.CRUSH_GRIP: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.MAGMA_STORM: MoveData(Type.FIRE, MoveCategory.SPECIAL, 100, 90, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.DARK_VOID: MoveData(Type.DARK, MoveCategory.STATUS, 0, 80, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.STATUS, None, None, None),
    Move.SEED_FLARE: MoveData(Type.GRASS, MoveCategory.SPECIAL, 120, 90, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(40, None, False, ((3, -2, False),)), None, None),
    Move.OMINOUS_WIND: MoveData(Type.GHOST, MoveCategory.SPECIAL, 60, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False), None, None),
    Move.HONE_CLAWS: MoveData(Type.DARK, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.WIDE_GUARD: MoveData(Type.ROCK, MoveCategory.STATUS, 0, None, 10, 3, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.GUARD_SPLIT: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.POWER_SPLIT: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.WONDER_ROOM: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.PSYSHOCK: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.VENOSHOCK: MoveData(Type.POISON, MoveCategory.SPECIAL, 65, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.AUTOTOMIZE: MoveData(Type.STEEL, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.RAGE_POWDER: MoveData(Type.BUG, MoveCategory.STATUS, 0, None, 20, 2, MoveTarget.SELF, MoveTag.POWDER, None, None, None),
    Move.TELEKINESIS: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.MAGIC_ROOM: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.SMACK_DOWN: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 50, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.STORM_THROW: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 60, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=3),
    Move.FLAME_BURST: MoveData(Type.FIRE, MoveCategory.SPECIAL, 70, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SLUDGE_WAVE: MoveData(Type.POISON, MoveCategory.SPECIAL, 95, 100, 10, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, SecondaryEffect(10, Status.POISON, False), None, None),
    Move.QUIVER_DANCE: MoveData(Type.BUG, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.HEAVY_SLAM: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SYNCHRONOISE: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 120, 100, 10, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, None, None, None),
    Move.ELECTRO_BALL: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SOAK: MoveData(Type.WATER, MoveCategory.STATUS, 0, 100, 20, 0, MoveTarget.NORMAL, MoveTag.STATUS, None, None, None),
    Move.FLAME_CHARGE: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 50, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((4, 1, True),)), None, None),
    Move.COIL: MoveData(Type.POISON, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.LOW_SWEEP: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 65, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((4, -1, False),)), None, None),
    Move.ACID_SPRAY: MoveData(Type.POISON, MoveCategory.SPECIAL, 40, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((3, -2, False),)), None, None),
    Move.FOUL_PLAY: MoveData(Type.DARK, MoveCategory.PHYSICAL, 95, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.SIMPLE_BEAM: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.ENTRAINMENT: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.AFTER_YOU: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ROUND: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ECHOED_VOICE: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 40, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.CHIP_AWAY: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 70, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.CLEAR_SMOG: MoveData(Type.POISON, MoveCategory.SPECIAL, 50, None, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.STORED_POWER: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 20, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.QUICK_GUARD: MoveData(Type.FIGHTING, MoveCategory.STATUS, 0, None, 15, 3, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ALLY_SWITCH: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 15, 2, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.SCALD: MoveData(Type.WATER, MoveCategory.SPECIAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.BURN, False), None, None),
    Move.SHELL_SMASH: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.HEAL_PULSE: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ANY, MoveTag.RECOVERY, None, None, None),
    Move.HEX: MoveData(Type.GHOST, MoveCategory.SPECIAL, 65, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SKY_DROP: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 60, 100, 10, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    Move.SHIFT_GEAR: MoveData(Type.STEEL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.CIRCLE_THROW: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 60, 95, 10, -6, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.INCINERATE: MoveData(Type.FIRE, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.QUASH: MoveData(Type.DARK, MoveCategory.STATUS, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ACROBATICS: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 55, 100, 15, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.REFLECT_TYPE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.RETALIATE: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 70, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FINAL_GAMBIT: MoveData(Type.FIGHTING, MoveCategory.SPECIAL, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.BESTOW: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.INFERNO: MoveData(Type.FIRE, MoveCategory.SPECIAL, 100, 50, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, Status.BURN, False), None, None),
    Move.WATER_PLEDGE: MoveData(Type.WATER, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FIRE_PLEDGE: MoveData(Type.FIRE, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.GRASS_PLEDGE: MoveData(Type.GRASS, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.VOLT_SWITCH: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 70, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PIVOT, None, None, None),
    Move.STRUGGLE_BUG: MoveData(Type.BUG, MoveCategory.SPECIAL, 50, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((2, -1, False),)), None, None),
    Move.BULLDOZE: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 60, 100, 20, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((4, -1, False),)), None, None),
    Move.FROST_BREATH: MoveData(Type.ICE, MoveCategory.SPECIAL, 60, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=3),
    Move.DRAGON_TAIL: MoveData(Type.DRAGON, MoveCategory.PHYSICAL, 60, 95, 10, -6, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.WORK_UP: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 30, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.ELECTROWEB: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 55, 100, 15, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((4, -1, False),)), None, None),
    Move.WILD_CHARGE: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 90, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, (1, 4)),
    Move.DRILL_RUN: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.DUAL_CHOP: MoveData(Type.DRAGON, MoveCategory.PHYSICAL, 40, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 2),
    Move.HEART_STAMP: MoveData(Type.PSYCHIC, MoveCategory.PHYSICAL, 60, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.HORN_LEECH: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 75, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, (1, 2), None),
    Move.SACRED_SWORD: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 90, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.RAZOR_SHELL: MoveData(Type.WATER, MoveCategory.PHYSICAL, 75, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(50, None, False, ((1, -1, False),)), None, None),
    Move.HEAT_CRASH: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.LEAF_TORNADO: MoveData(Type.GRASS, MoveCategory.SPECIAL, 65, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, False), None, None),
    Move.STEAMROLLER: MoveData(Type.BUG, MoveCategory.PHYSICAL, 65, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.COTTON_GUARD: MoveData(Type.GRASS, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.NIGHT_DAZE: MoveData(Type.DARK, MoveCategory.SPECIAL, 85, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, False, ((5, -1, False),)), None, None),
    Move.PSYSTRIKE: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 100, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.TAIL_SLAP: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 25, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 5),
    Move.HURRICANE: MoveData(Type.FLYING, MoveCategory.SPECIAL, 110, 80, 10, 0, MoveTarget.ANY, MoveTag.DAMAGE, SecondaryEffect(30, None, False, volatile="confused"), None, None),
    Move.HEAD_CHARGE: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 120, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, (1, 4)),
    Move.GEAR_GRIND: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 50, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 2),
    Move.SEARING_SHOT: MoveData(Type.FIRE, MoveCategory.SPECIAL, 100, 100, 5, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, SecondaryEffect(30, Status.BURN, False), None, None),
    Move.TECHNO_BLAST: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 120, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.RELIC_SONG: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 75, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(10, Status.SLEEP, False), None, None),
    Move.SECRET_SWORD: MoveData(Type.FIGHTING, MoveCategory.SPECIAL, 85, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.GLACIATE: MoveData(Type.ICE, MoveCategory.SPECIAL, 65, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((4, -1, False),)), None, None),
    Move.BOLT_STRIKE: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 130, 90, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.CONTACT, SecondaryEffect(20, Status.PARALYSIS, False), None, None),
    Move.BLUE_FLARE: MoveData(Type.FIRE, MoveCategory.SPECIAL, 130, 90, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, Status.BURN, False), None, None),
    Move.FIERY_DANCE: MoveData(Type.FIRE, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(50, None, False, ((2, 1, True),)), None, None),
    Move.FREEZE_SHOCK: MoveData(Type.ICE, MoveCategory.PHYSICAL, 140, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.PARALYSIS, False), None, None),
    Move.ICE_BURN: MoveData(Type.ICE, MoveCategory.SPECIAL, 140, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.BURN, False), None, None),
    Move.SNARL: MoveData(Type.DARK, MoveCategory.SPECIAL, 55, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((2, -1, False),)), None, None),
    Move.ICICLE_CRASH: MoveData(Type.ICE, MoveCategory.PHYSICAL, 85, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.V_CREATE: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 180, 95, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, self_stat_changes=((4, -1), (1, -1), (3, -1))),
    Move.FUSION_FLARE: MoveData(Type.FIRE, MoveCategory.SPECIAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FUSION_BOLT: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FLYING_PRESS: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 100, 100, 10, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    Move.MAT_BLOCK: MoveData(Type.FIGHTING, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.BELCH: MoveData(Type.POISON, MoveCategory.SPECIAL, 120, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.ROTOTILLER: MoveData(Type.GROUND, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.STICKY_WEB: MoveData(Type.BUG, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.FOE_SIDE, MoveTag.HAZARD, None, None, None),
    Move.FELL_STINGER: MoveData(Type.BUG, MoveCategory.PHYSICAL, 50, 100, 25, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.PHANTOM_FORCE: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.TRICK_OR_TREAT: MoveData(Type.GHOST, MoveCategory.STATUS, 0, 100, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.NOBLE_ROAR: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ION_DELUGE: MoveData(Type.ELECTRIC, MoveCategory.STATUS, 0, None, 25, 1, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.PARABOLIC_CHARGE: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 65, 100, 20, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, None, (1, 2), None),
    # REMOVED(unimplemented status move) Move.FOREST_S_CURSE: MoveData(Type.GRASS, MoveCategory.STATUS, 0, 100, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.PETAL_BLIZZARD: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 90, 100, 15, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, None, None, None),
    Move.FREEZE_DRY: MoveData(Type.ICE, MoveCategory.SPECIAL, 70, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.STATUS, SecondaryEffect(10, Status.FREEZE, False), None, None),
    Move.DISARMING_VOICE: MoveData(Type.FAIRY, MoveCategory.SPECIAL, 40, None, 15, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.PARTING_SHOT: MoveData(Type.DARK, MoveCategory.STATUS, 0, 100, 20, 0, MoveTarget.NORMAL, MoveTag.PIVOT, None, None, None),
    # REMOVED(unimplemented status move) Move.TOPSY_TURVY: MoveData(Type.DARK, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.DRAINING_KISS: MoveData(Type.FAIRY, MoveCategory.SPECIAL, 50, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, (3, 4), None),
    Move.CRAFTY_SHIELD: MoveData(Type.FAIRY, MoveCategory.STATUS, 0, None, 10, 3, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.FLOWER_SHIELD: MoveData(Type.FAIRY, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.GRASSY_TERRAIN: MoveData(Type.GRASS, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.MISTY_TERRAIN: MoveData(Type.FAIRY, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.ELECTRIFY: MoveData(Type.ELECTRIC, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.PLAY_ROUGH: MoveData(Type.FAIRY, MoveCategory.PHYSICAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, None, False, ((0, -1, False),)), None, None),
    Move.FAIRY_WIND: MoveData(Type.FAIRY, MoveCategory.SPECIAL, 40, 100, 30, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MOONBLAST: MoveData(Type.FAIRY, MoveCategory.SPECIAL, 95, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, False, ((2, -1, False),)), None, None),
    Move.BOOMBURST: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 140, 100, 10, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.FAIRY_LOCK: MoveData(Type.FAIRY, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.KING_S_SHIELD: MoveData(Type.STEEL, MoveCategory.STATUS, 0, None, 10, 4, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.PLAY_NICE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.CONFIDE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.DIAMOND_STORM: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 100, 100, 5, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.STEAM_ERUPTION: MoveData(Type.WATER, MoveCategory.SPECIAL, 110, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.BURN, False), None, None),
    Move.HYPERSPACE_HOLE: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 80, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.WATER_SHURIKEN: MoveData(Type.WATER, MoveCategory.SPECIAL, 15, 100, 20, 1, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 5),
    Move.MYSTICAL_FIRE: MoveData(Type.FIRE, MoveCategory.SPECIAL, 75, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((2, -1, False),)), None, None),
    Move.SPIKY_SHIELD: MoveData(Type.GRASS, MoveCategory.STATUS, 0, None, 10, 4, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.AROMATIC_MIST: MoveData(Type.FAIRY, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.ALLY, MoveTag.SETUP, None, None, None),
    Move.EERIE_IMPULSE: MoveData(Type.ELECTRIC, MoveCategory.STATUS, 0, 100, 5, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.VENOM_DRENCH: MoveData(Type.POISON, MoveCategory.STATUS, 0, 100, 20, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.NONE, None, None, None),
    Move.POWDER: MoveData(Type.BUG, MoveCategory.STATUS, 0, 100, 20, 1, MoveTarget.NORMAL, MoveTag.POWDER, None, None, None),
    # REMOVED(unimplemented status move) Move.GEOMANCY: MoveData(Type.FAIRY, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    # REMOVED(unimplemented status move) Move.MAGNETIC_FLUX: MoveData(Type.ELECTRIC, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.HAPPY_HOUR: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 30, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ELECTRIC_TERRAIN: MoveData(Type.ELECTRIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.DAZZLING_GLEAM: MoveData(Type.FAIRY, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.CELEBRATE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 40, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.HOLD_HANDS: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 40, 0, MoveTarget.ALLY, MoveTag.NONE, None, None, None),
    Move.BABY_DOLL_EYES: MoveData(Type.FAIRY, MoveCategory.STATUS, 0, 100, 10, 1, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.NUZZLE: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 20, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.STATUS, SecondaryEffect(100, Status.PARALYSIS, False), None, None),
    Move.HOLD_BACK: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 40, 100, 40, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.INFESTATION: MoveData(Type.BUG, MoveCategory.SPECIAL, 20, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.POWER_UP_PUNCH: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 40, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING, SecondaryEffect(100, None, False, ((0, 1, True),)), None, None),
    Move.OBLIVION_WING: MoveData(Type.FLYING, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, (3, 4), None),
    Move.THOUSAND_ARROWS: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 90, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.THOUSAND_WAVES: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 90, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.LAND_S_WRATH: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 90, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.LIGHT_OF_RUIN: MoveData(Type.FAIRY, MoveCategory.SPECIAL, 140, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, (1, 2)),
    Move.ORIGIN_PULSE: MoveData(Type.WATER, MoveCategory.SPECIAL, 110, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.PRECIPICE_BLADES: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 120, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.DRAGON_ASCENT: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 120, 100, 5, 0, MoveTarget.ANY, MoveTag.DAMAGE, None, None, None),
    Move.HYPERSPACE_FURY: MoveData(Type.DARK, MoveCategory.PHYSICAL, 100, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SHORE_UP: MoveData(Type.GROUND, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.RECOVERY, None, None, None),
    Move.FIRST_IMPRESSION: MoveData(Type.BUG, MoveCategory.PHYSICAL, 90, 100, 10, 2, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BANEFUL_BUNKER: MoveData(Type.POISON, MoveCategory.STATUS, 0, None, 10, 4, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.SPIRIT_SHACKLE: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.DARKEST_LARIAT: MoveData(Type.DARK, MoveCategory.PHYSICAL, 85, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SPARKLING_ARIA: MoveData(Type.WATER, MoveCategory.SPECIAL, 90, 100, 10, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.ICE_HAMMER: MoveData(Type.ICE, MoveCategory.PHYSICAL, 100, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, self_stat_changes=((4, -1),)),
    Move.FLORAL_HEALING: MoveData(Type.FAIRY, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.RECOVERY, None, None, None),
    Move.HIGH_HORSEPOWER: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 95, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.STRENGTH_SAP: MoveData(Type.GRASS, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.RECOVERY, None, None, None),
    Move.SOLAR_BLADE: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 125, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.LEAFAGE: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 40, 100, 40, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SPOTLIGHT: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 15, 3, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.TOXIC_THREAD: MoveData(Type.POISON, MoveCategory.STATUS, 0, 100, 20, 0, MoveTarget.NORMAL, MoveTag.STATUS, None, None, None),
    Move.LASER_FOCUS: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 30, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.GEAR_UP: MoveData(Type.STEEL, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.THROAT_CHOP: MoveData(Type.DARK, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.POLLEN_PUFF: MoveData(Type.BUG, MoveCategory.SPECIAL, 90, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ANCHOR_SHOT: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 80, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.PSYCHIC_TERRAIN: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.LUNGE: MoveData(Type.BUG, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((0, -1, False),)), None, None),
    Move.FIRE_LASH: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((1, -1, False),)), None, None),
    Move.POWER_TRIP: MoveData(Type.DARK, MoveCategory.PHYSICAL, 20, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BURN_UP: MoveData(Type.FIRE, MoveCategory.SPECIAL, 130, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.SPEED_SWAP: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SMART_STRIKE: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 70, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.PURIFY: MoveData(Type.POISON, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.REVELATION_DANCE: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 90, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.CORE_ENFORCER: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 100, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.TROP_KICK: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 70, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((0, -1, False),)), None, None),
    # REMOVED(unimplemented status move) Move.INSTRUCT: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.BEAK_BLAST: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 100, 100, 15, -3, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.CLANGING_SCALES: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 110, 100, 5, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None, self_stat_changes=((1, -1),)),
    Move.DRAGON_HAMMER: MoveData(Type.DRAGON, MoveCategory.PHYSICAL, 90, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BRUTAL_SWING: MoveData(Type.DARK, MoveCategory.PHYSICAL, 60, 100, 20, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, None, None, None),
    Move.AURORA_VEIL: MoveData(Type.ICE, MoveCategory.STATUS, 0, None, 20, 0, MoveTarget.NORMAL, MoveTag.SCREEN, None, None, None),
    Move.SHELL_TRAP: MoveData(Type.FIRE, MoveCategory.SPECIAL, 150, 100, 5, -3, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.FLEUR_CANNON: MoveData(Type.FAIRY, MoveCategory.SPECIAL, 130, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.PSYCHIC_FANGS: MoveData(Type.PSYCHIC, MoveCategory.PHYSICAL, 85, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.STOMPING_TANTRUM: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 75, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SHADOW_BONE: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 85, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, None, False, ((1, -1, False),)), None, None),
    Move.ACCELEROCK: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 40, 100, 20, 1, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.LIQUIDATION: MoveData(Type.WATER, MoveCategory.PHYSICAL, 85, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, None, False, ((1, -1, False),)), None, None),
    Move.PRISMATIC_LASER: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 160, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SPECTRAL_THIEF: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SUNSTEEL_STRIKE: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MOONGEIST_BEAM: MoveData(Type.GHOST, MoveCategory.SPECIAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.TEARFUL_LOOK: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.ZING_ZAP: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.NATURE_S_MADNESS: MoveData(Type.FAIRY, MoveCategory.SPECIAL, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.MULTI_ATTACK: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 120, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MIND_BLOWN: MoveData(Type.FIRE, MoveCategory.SPECIAL, 150, 100, 5, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, None, None, None),
    Move.PLASMA_FISTS: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 100, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PUNCHING | MoveTag.CONTACT, None, None, None),
    Move.PHOTON_GEYSER: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ZIPPY_ZAP: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 80, 100, 10, 2, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.SPLISHY_SPLASH: MoveData(Type.WATER, MoveCategory.SPECIAL, 90, 100, 15, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(30, Status.PARALYSIS, False), None, None),
    Move.FLOATY_FALL: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 90, 95, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    Move.PIKA_PAPOW: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 0, None, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.BOUNCY_BUBBLE: MoveData(Type.WATER, MoveCategory.SPECIAL, 60, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, (1, 2), None),
    Move.BUZZY_BUZZ: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 60, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, Status.PARALYSIS, False), None, None),
    Move.SIZZLY_SLIDE: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 60, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, Status.BURN, False), None, None),
    Move.GLITZY_GLOW: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 80, 95, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BADDY_BAD: MoveData(Type.DARK, MoveCategory.SPECIAL, 80, 95, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SAPPY_SEED: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 100, 90, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FREEZY_FROST: MoveData(Type.ICE, MoveCategory.SPECIAL, 100, 90, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SPARKLY_SWIRL: MoveData(Type.FAIRY, MoveCategory.SPECIAL, 120, 85, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.VEEVEE_VOLLEY: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 0, None, 20, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.DOUBLE_IRON_BASH: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 60, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None, 0, 2, 2),
    Move.MAX_GUARD: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 4, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.DYNAMAX_CANNON: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SNIPE_SHOT: MoveData(Type.WATER, MoveCategory.SPECIAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.JAW_LOCK: MoveData(Type.DARK, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.STUFF_CHEEKS: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.NO_RETREAT: MoveData(Type.FIGHTING, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    # REMOVED(unimplemented status move) Move.TAR_SHOT: MoveData(Type.ROCK, MoveCategory.STATUS, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.MAGIC_POWDER: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, 100, 20, 0, MoveTarget.NORMAL, MoveTag.POWDER, None, None, None),
    Move.DRAGON_DARTS: MoveData(Type.DRAGON, MoveCategory.PHYSICAL, 50, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 2),
    # REMOVED(unimplemented status move) Move.TEATIME: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.OCTOLOCK: MoveData(Type.FIGHTING, MoveCategory.STATUS, 0, 100, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.BOLT_BEAK: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 85, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FISHIOUS_REND: MoveData(Type.WATER, MoveCategory.PHYSICAL, 85, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.COURT_CHANGE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.MAX_FLARE: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 100, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_FLUTTERBY: MoveData(Type.BUG, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_LIGHTNING: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_STRIKE: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_KNUCKLE: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_PHANTASM: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_HAILSTORM: MoveData(Type.ICE, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_OOZE: MoveData(Type.POISON, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_GEYSER: MoveData(Type.WATER, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_AIRSTREAM: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_STARFALL: MoveData(Type.FAIRY, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_WYRMWIND: MoveData(Type.DRAGON, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_MINDSTORM: MoveData(Type.PSYCHIC, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_ROCKFALL: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_QUAKE: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_DARKNESS: MoveData(Type.DARK, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_OVERGROWTH: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAX_STEELSPIKE: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.CLANGOROUS_SOUL: MoveData(Type.DRAGON, MoveCategory.STATUS, 0, 100, 5, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.BODY_PRESS: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.DECORATE: MoveData(Type.FAIRY, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.NORMAL, MoveTag.SETUP, None, None, None),
    Move.DRUM_BEATING: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((4, -1, False),)), None, None),
    Move.SNAP_TRAP: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 35, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.PYRO_BALL: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 120, 90, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.BURN, False), None, None),
    Move.BEHEMOTH_BLADE: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BEHEMOTH_BASH: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.AURA_WHEEL: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 110, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((4, 1, True),)), None, None),
    Move.BREAKING_SWIPE: MoveData(Type.DRAGON, MoveCategory.PHYSICAL, 60, 100, 15, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((0, -1, False),)), None, None),
    Move.BRANCH_POKE: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 40, 100, 40, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.OVERDRIVE: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.APPLE_ACID: MoveData(Type.GRASS, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((3, -1, False),)), None, None),
    Move.GRAV_APPLE: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((1, -1, False),)), None, None),
    Move.SPIRIT_BREAK: MoveData(Type.FAIRY, MoveCategory.PHYSICAL, 75, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((2, -1, False),)), None, None),
    Move.STRANGE_STEAM: MoveData(Type.FAIRY, MoveCategory.SPECIAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, None, False, volatile="confused"), None, None),
    Move.LIFE_DEW: MoveData(Type.WATER, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALLY_SIDE, MoveTag.RECOVERY, None, None, None),
    Move.OBSTRUCT: MoveData(Type.DARK, MoveCategory.STATUS, 0, 100, 10, 4, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.FALSE_SURRENDER: MoveData(Type.DARK, MoveCategory.PHYSICAL, 80, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.METEOR_ASSAULT: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 150, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ETERNABEAM: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 160, 90, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.STEEL_BEAM: MoveData(Type.STEEL, MoveCategory.SPECIAL, 140, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.EXPANDING_FORCE: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.STEEL_ROLLER: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 130, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SCALE_SHOT: MoveData(Type.DRAGON, MoveCategory.PHYSICAL, 25, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 5, self_stat_changes=((1, -1), (4, 1))),
    Move.METEOR_BEAM: MoveData(Type.ROCK, MoveCategory.SPECIAL, 120, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SHELL_SIDE_ARM: MoveData(Type.POISON, MoveCategory.SPECIAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(20, Status.POISON, False), None, None),
    Move.MISTY_EXPLOSION: MoveData(Type.FAIRY, MoveCategory.SPECIAL, 200, 100, 5, 0, MoveTarget.ALL_ADJACENT, MoveTag.DAMAGE, None, None, None),
    Move.GRASSY_GLIDE: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 55, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.RISING_VOLTAGE: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 70, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.TERRAIN_PULSE: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 50, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SKITTER_SMACK: MoveData(Type.BUG, MoveCategory.PHYSICAL, 70, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False, ((2, -1, False),)), None, None),
    Move.BURNING_JEALOUSY: MoveData(Type.FIRE, MoveCategory.SPECIAL, 70, 100, 5, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.LASH_OUT: MoveData(Type.DARK, MoveCategory.PHYSICAL, 75, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.POLTERGEIST: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 110, 90, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.CORROSIVE_GAS: MoveData(Type.POISON, MoveCategory.STATUS, 0, 100, 40, 0, MoveTarget.ALL_ADJACENT, MoveTag.NONE, None, None, None),
    Move.COACHING: MoveData(Type.FIGHTING, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALLY, MoveTag.SETUP, None, None, None),
    Move.FLIP_TURN: MoveData(Type.WATER, MoveCategory.PHYSICAL, 60, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.PIVOT, None, None, None),
    Move.TRIPLE_AXEL: MoveData(Type.ICE, MoveCategory.PHYSICAL, 20, 90, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 3, 3),
    Move.DUAL_WINGBEAT: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 40, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 2, 2),
    Move.SCORCHING_SANDS: MoveData(Type.GROUND, MoveCategory.SPECIAL, 70, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.BURN, False), None, None),
    Move.JUNGLE_HEALING: MoveData(Type.GRASS, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALLY_SIDE, MoveTag.RECOVERY, None, None, None),
    Move.WICKED_BLOW: MoveData(Type.DARK, MoveCategory.PHYSICAL, 75, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=3),
    Move.SURGING_STRIKES: MoveData(Type.WATER, MoveCategory.PHYSICAL, 25, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 3, 3, crit_boost=3),
    Move.THUNDER_CAGE: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.DRAGON_ENERGY: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 150, 100, 5, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.FREEZING_GLARE: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.FREEZE, False), None, None),
    Move.FIERY_WRATH: MoveData(Type.DARK, MoveCategory.SPECIAL, 90, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(20, None, True), None, None),
    Move.THUNDEROUS_KICK: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE | MoveTag.CONTACT, SecondaryEffect(100, None, False, ((1, -1, False),)), None, None),
    Move.GLACIAL_LANCE: MoveData(Type.ICE, MoveCategory.PHYSICAL, 120, 100, 5, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.ASTRAL_BARRAGE: MoveData(Type.GHOST, MoveCategory.SPECIAL, 120, 100, 5, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.EERIE_SPELL: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 80, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.DIRE_CLAW: MoveData(Type.POISON, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(50, None, False), None, None),
    Move.PSYSHIELD_BASH: MoveData(Type.PSYCHIC, MoveCategory.PHYSICAL, 70, 90, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    # REMOVED(unimplemented status move) Move.POWER_SHIFT: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.STONE_AXE: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 65, 90, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SPRINGTIDE_STORM: MoveData(Type.FAIRY, MoveCategory.SPECIAL, 100, 80, 5, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(30, None, False), None, None),
    Move.MYSTICAL_POWER: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 70, 90, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.RAGING_FURY: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 120, 100, 10, 0, MoveTarget.RANDOM_NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.WAVE_CRASH: MoveData(Type.WATER, MoveCategory.PHYSICAL, 120, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, (33, 100)),
    Move.CHLOROBLAST: MoveData(Type.GRASS, MoveCategory.SPECIAL, 150, 95, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MOUNTAIN_GALE: MoveData(Type.ICE, MoveCategory.PHYSICAL, 100, 85, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, True), None, None),
    # REMOVED(unimplemented status move) Move.VICTORY_DANCE: MoveData(Type.FIGHTING, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.HEADLONG_RUSH: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 120, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BARB_BARRAGE: MoveData(Type.POISON, MoveCategory.PHYSICAL, 60, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(50, Status.POISON, False), None, None),
    Move.ESPER_WING: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.BITTER_MALICE: MoveData(Type.GHOST, MoveCategory.SPECIAL, 75, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    # REMOVED(unimplemented status move) Move.SHELTER: MoveData(Type.STEEL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.TRIPLE_ARROWS: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(50, None, False), None, None),
    Move.INFERNAL_PARADE: MoveData(Type.GHOST, MoveCategory.SPECIAL, 60, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.BURN, False), None, None),
    Move.CEASELESS_EDGE: MoveData(Type.DARK, MoveCategory.PHYSICAL, 65, 90, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BLEAKWIND_STORM: MoveData(Type.FLYING, MoveCategory.SPECIAL, 100, 80, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(30, None, False), None, None),
    Move.WILDBOLT_STORM: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 100, 80, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(20, Status.PARALYSIS, False), None, None),
    Move.SANDSEAR_STORM: MoveData(Type.GROUND, MoveCategory.SPECIAL, 100, 80, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(20, Status.BURN, False), None, None),
    Move.LUNAR_BLESSING: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 5, 0, MoveTarget.ALLY_SIDE, MoveTag.RECOVERY, None, None, None),
    # REMOVED(unimplemented status move) Move.TAKE_HEART: MoveData(Type.PSYCHIC, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.TERA_BLAST: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SILK_TRAP: MoveData(Type.BUG, MoveCategory.STATUS, 0, None, 10, 4, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.AXE_KICK: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 120, 90, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, False), None, None),
    Move.LAST_RESPECTS: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 50, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.LUMINA_CRASH: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.ORDER_UP: MoveData(Type.DRAGON, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.JET_PUNCH: MoveData(Type.WATER, MoveCategory.PHYSICAL, 60, 100, 15, 1, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.SPICY_EXTRACT: MoveData(Type.GRASS, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.SPIN_OUT: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.POPULATION_BOMB: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 20, 90, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 1, 10),
    Move.ICE_SPINNER: MoveData(Type.ICE, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.GLAIVE_RUSH: MoveData(Type.DRAGON, MoveCategory.PHYSICAL, 120, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    # REMOVED(unimplemented status move) Move.REVIVAL_BLESSING: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 1, 0, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.SALT_CURE: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 40, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.TRIPLE_DIVE: MoveData(Type.WATER, MoveCategory.PHYSICAL, 30, 95, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, 0, 3, 3),
    Move.MORTAL_SPIN: MoveData(Type.POISON, MoveCategory.PHYSICAL, 30, 100, 15, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(100, Status.POISON, False), None, None),
    # REMOVED(unimplemented status move) Move.DOODLE: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.FILLET_AWAY: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    Move.KOWTOW_CLEAVE: MoveData(Type.DARK, MoveCategory.PHYSICAL, 85, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FLOWER_TRICK: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 70, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.TORCH_SONG: MoveData(Type.FIRE, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.AQUA_STEP: MoveData(Type.WATER, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.RAGING_BULL: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MAKE_IT_RAIN: MoveData(Type.STEEL, MoveCategory.SPECIAL, 120, 100, 5, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.PSYBLADE: MoveData(Type.PSYCHIC, MoveCategory.PHYSICAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HYDRO_STEAM: MoveData(Type.WATER, MoveCategory.SPECIAL, 80, 100, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.RUINATION: MoveData(Type.DARK, MoveCategory.SPECIAL, 0, 90, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.COLLISION_COURSE: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ELECTRO_DRIFT: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SHED_TAIL: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.PIVOT, None, None, None),
    # REMOVED(unimplemented status move) Move.CHILLY_RECEPTION: MoveData(Type.ICE, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.TIDY_UP: MoveData(Type.NORMAL, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.SELF, MoveTag.SETUP, None, None, None),
    # REMOVED(unimplemented status move) Move.SNOWSCAPE: MoveData(Type.ICE, MoveCategory.STATUS, 0, None, 10, 0, MoveTarget.ALL, MoveTag.NONE, None, None, None),
    Move.POUNCE: MoveData(Type.BUG, MoveCategory.PHYSICAL, 50, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.TRAILBLAZE: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 50, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.CHILLING_WATER: MoveData(Type.WATER, MoveCategory.SPECIAL, 50, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.HYPER_DRILL: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.TWIN_BEAM: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 40, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.RAGE_FIST: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 50, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ARMOR_CANNON: MoveData(Type.FIRE, MoveCategory.SPECIAL, 120, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BITTER_BLADE: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 90, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, (1, 2), None),
    Move.DOUBLE_SHOCK: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 120, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.GIGATON_HAMMER: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 160, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.COMEUPPANCE: MoveData(Type.DARK, MoveCategory.PHYSICAL, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    Move.AQUA_CUTTER: MoveData(Type.WATER, MoveCategory.PHYSICAL, 70, 100, 20, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None, crit_boost=1),
    Move.BLAZING_TORQUE: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.BURN, False), None, None),
    Move.WICKED_TORQUE: MoveData(Type.DARK, MoveCategory.PHYSICAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(10, Status.SLEEP, False), None, None),
    Move.NOXIOUS_TORQUE: MoveData(Type.POISON, MoveCategory.PHYSICAL, 100, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.POISON, False), None, None),
    Move.COMBAT_TORQUE: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 100, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, Status.PARALYSIS, False), None, None),
    Move.MAGICAL_TORQUE: MoveData(Type.FAIRY, MoveCategory.PHYSICAL, 100, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(30, None, False), None, None),
    Move.BLOOD_MOON: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 140, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MATCHA_GOTCHA: MoveData(Type.GRASS, MoveCategory.SPECIAL, 80, 90, 15, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, SecondaryEffect(20, Status.BURN, False), (1, 2), None),
    Move.SYRUP_BOMB: MoveData(Type.GRASS, MoveCategory.SPECIAL, 60, 85, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.IVY_CUDGEL: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 100, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.ELECTRO_SHOT: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 130, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.TERA_STARSTORM: MoveData(Type.NORMAL, MoveCategory.SPECIAL, 120, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.FICKLE_BEAM: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 80, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.BURNING_BULWARK: MoveData(Type.FIRE, MoveCategory.STATUS, 0, None, 10, 4, MoveTarget.SELF, MoveTag.NONE, None, None, None),
    Move.THUNDERCLAP: MoveData(Type.ELECTRIC, MoveCategory.SPECIAL, 70, 100, 5, 1, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.MIGHTY_CLEAVE: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 95, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.TACHYON_CUTTER: MoveData(Type.STEEL, MoveCategory.SPECIAL, 50, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.HARD_PRESS: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 0, 100, 10, 0, MoveTarget.NORMAL, MoveTag.NONE, None, None, None),
    # REMOVED(unimplemented status move) Move.DRAGON_CHEER: MoveData(Type.DRAGON, MoveCategory.STATUS, 0, None, 15, 0, MoveTarget.ALLY, MoveTag.NONE, None, None, None),
    Move.ALLURING_VOICE: MoveData(Type.FAIRY, MoveCategory.SPECIAL, 80, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.TEMPER_FLARE: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 75, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.SUPERCELL_SLAM: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 100, 95, 15, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.PSYCHIC_NOISE: MoveData(Type.PSYCHIC, MoveCategory.SPECIAL, 75, 100, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, False), None, None),
    Move.UPPER_HAND: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 65, 100, 15, 3, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(100, None, True), None, None),
    Move.MALIGNANT_CHAIN: MoveData(Type.POISON, MoveCategory.SPECIAL, 100, 100, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, SecondaryEffect(50, Status.TOXIC, False), None, None),
    Move.NIHIL_LIGHT: MoveData(Type.DRAGON, MoveCategory.SPECIAL, 100, 100, 10, 0, MoveTarget.ALL_ADJACENT_FOES, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_BEFUDDLE: MoveData(Type.BUG, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_CANNONADE: MoveData(Type.WATER, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_CENTIFERNO: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_CHI_STRIKE: MoveData(Type.FIGHTING, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_CUDDLE: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_DEPLETION: MoveData(Type.DRAGON, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_DRUM_SOLO: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 160, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_FINALE: MoveData(Type.FAIRY, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_FIREBALL: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 160, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_FOAM_BURST: MoveData(Type.WATER, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_GOLD_RUSH: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_GRAVITAS: MoveData(Type.PSYCHIC, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_HYDROSNIPE: MoveData(Type.WATER, MoveCategory.PHYSICAL, 160, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_MALODOR: MoveData(Type.POISON, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_MELTDOWN: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_ONE_BLOW: MoveData(Type.DARK, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_RAPID_FLOW: MoveData(Type.WATER, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_REPLENISH: MoveData(Type.NORMAL, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_RESONANCE: MoveData(Type.ICE, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_SANDBLAST: MoveData(Type.GROUND, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_SMITE: MoveData(Type.FAIRY, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_SNOOZE: MoveData(Type.DARK, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_STEELSURGE: MoveData(Type.STEEL, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_STONESURGE: MoveData(Type.WATER, MoveCategory.PHYSICAL, 10, None, 5, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_STUN_SHOCK: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_SWEETNESS: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_TARTNESS: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_TERROR: MoveData(Type.GHOST, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_VINE_LASH: MoveData(Type.GRASS, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_VOLCALITH: MoveData(Type.ROCK, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_VOLT_CRASH: MoveData(Type.ELECTRIC, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_WILDFIRE: MoveData(Type.FIRE, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
    Move.G_MAX_WIND_RAGE: MoveData(Type.FLYING, MoveCategory.PHYSICAL, 10, None, 10, 0, MoveTarget.NORMAL, MoveTag.DAMAGE, None, None, None),
}

# Contact moves sourced from Showdown flags: {contact: 1}. Applied as a post-processing step
# to avoid touching hundreds of individual entries.
_CONTACT_MOVES: frozenset[Move] = frozenset({
    Move.ACCELEROCK, Move.ACROBATICS, Move.AERIAL_ACE, Move.ANCHOR_SHOT, Move.AQUA_JET,
    Move.AQUA_STEP, Move.AQUA_TAIL, Move.ARM_THRUST, Move.ASSURANCE, Move.ASTONISH,
    Move.AVALANCHE, Move.AXE_KICK, Move.BIND, Move.BITE, Move.BITTER_BLADE,
    Move.BLAZE_KICK, Move.BODY_PRESS, Move.BODY_SLAM, Move.BOLT_BEAK, Move.BOUNCE,
    Move.BRAVE_BIRD, Move.BREAKING_SWIPE, Move.BRICK_BREAK, Move.BRUTAL_SWING,
    Move.BUG_BITE, Move.BULLET_PUNCH, Move.CEASELESS_EDGE, Move.CHIP_AWAY,
    Move.CIRCLE_THROW, Move.CLAMP, Move.CLOSE_COMBAT, Move.COLLISION_COURSE,
    Move.COMET_PUNCH, Move.COMEUPPANCE, Move.CONSTRICT, Move.COUNTER, Move.COVET,
    Move.CRABHAMMER, Move.CROSS_CHOP, Move.CROSS_POISON, Move.CRUNCH, Move.CRUSH_CLAW,
    Move.CRUSH_GRIP, Move.CUT, Move.DARKEST_LARIAT, Move.DIG, Move.DIRE_CLAW,
    Move.DIVE, Move.DIZZY_PUNCH, Move.DOUBLE_HIT, Move.DOUBLE_IRON_BASH,
    Move.DOUBLE_KICK, Move.DOUBLE_SHOCK, Move.DOUBLE_SLAP, Move.DOUBLE_EDGE,
    Move.DRAGON_ASCENT, Move.DRAGON_CLAW, Move.DRAGON_HAMMER, Move.DRAGON_RUSH,
    Move.DRAGON_TAIL, Move.DRAIN_PUNCH, Move.DRAINING_KISS, Move.DRILL_PECK,
    Move.DRILL_RUN, Move.DUAL_CHOP, Move.DUAL_WINGBEAT, Move.DYNAMIC_PUNCH,
    Move.ELECTRO_DRIFT, Move.ENDEAVOR, Move.EXTREME_SPEED, Move.FACADE, Move.FAKE_OUT,
    Move.FALSE_SWIPE, Move.FEINT_ATTACK, Move.FELL_STINGER, Move.FIRE_FANG,
    Move.FIRE_LASH, Move.FIRE_PUNCH, Move.FIRST_IMPRESSION, Move.FISHIOUS_REND,
    Move.FLAIL, Move.FLAME_CHARGE, Move.FLAME_WHEEL, Move.FLARE_BLITZ, Move.FLIP_TURN,
    Move.FLY, Move.FLYING_PRESS, Move.FOCUS_PUNCH, Move.FORCE_PALM, Move.FOUL_PLAY,
    Move.FRUSTRATION, Move.FURY_ATTACK, Move.FURY_CUTTER, Move.FURY_SWIPES,
    Move.GEAR_GRIND, Move.GIGA_IMPACT, Move.GLAIVE_RUSH, Move.GRASS_KNOT,
    Move.GRASSY_GLIDE, Move.GUILLOTINE, Move.GYRO_BALL, Move.HAMMER_ARM,
    Move.HARD_PRESS, Move.HEAD_CHARGE, Move.HEAD_SMASH, Move.HEADBUTT,
    Move.HEADLONG_RUSH, Move.HEART_STAMP, Move.HEAT_CRASH, Move.HEAVY_SLAM,
    Move.HIGH_HORSEPOWER, Move.HIGH_JUMP_KICK, Move.HOLD_BACK, Move.HORN_ATTACK,
    Move.HORN_DRILL, Move.HORN_LEECH, Move.HYPER_DRILL, Move.HYPER_FANG,
    Move.ICE_BALL, Move.ICE_FANG, Move.ICE_HAMMER, Move.ICE_PUNCH, Move.ICE_SPINNER,
    Move.INFESTATION, Move.IRON_HEAD, Move.IRON_TAIL, Move.JAW_LOCK, Move.JET_PUNCH,
    Move.JUMP_KICK, Move.KARATE_CHOP, Move.KNOCK_OFF, Move.KOWTOW_CLEAVE,
    Move.LASH_OUT, Move.LAST_RESORT, Move.LEAF_BLADE, Move.LEECH_LIFE, Move.LICK,
    Move.LIQUIDATION, Move.LOW_KICK, Move.LOW_SWEEP, Move.LUNGE, Move.MACH_PUNCH,
    Move.MEGA_KICK, Move.MEGA_PUNCH, Move.MEGAHORN, Move.METAL_CLAW, Move.METEOR_MASH,
    Move.MIGHTY_CLEAVE, Move.MORTAL_SPIN, Move.MULTI_ATTACK, Move.NEEDLE_ARM,
    Move.NIGHT_SLASH, Move.NUZZLE, Move.OUTRAGE, Move.PAYBACK, Move.PECK,
    Move.PETAL_DANCE, Move.PHANTOM_FORCE, Move.PLAY_ROUGH, Move.PLUCK,
    Move.POISON_FANG, Move.POISON_JAB, Move.POISON_TAIL, Move.POPULATION_BOMB,
    Move.POUNCE, Move.POUND, Move.POWER_TRIP, Move.POWER_WHIP, Move.POWER_UP_PUNCH,
    Move.PSYBLADE, Move.PSYCHIC_FANGS, Move.PSYSHIELD_BASH, Move.PUNISHMENT,
    Move.PURSUIT, Move.QUICK_ATTACK, Move.RAGE, Move.RAGE_FIST, Move.RAGING_BULL,
    Move.RAPID_SPIN, Move.RAZOR_SHELL, Move.RETALIATE, Move.RETURN, Move.REVENGE,
    Move.REVERSAL, Move.ROCK_CLIMB, Move.ROCK_SMASH, Move.ROLLING_KICK, Move.ROLLOUT,
    Move.SACRED_SWORD, Move.SCRATCH, Move.SEISMIC_TOSS, Move.SHADOW_CLAW,
    Move.SHADOW_PUNCH, Move.SHADOW_SNEAK, Move.SKITTER_SMACK,
    Move.SKULL_BASH, Move.SKY_DROP, Move.SKY_UPPERCUT, Move.SLAM, Move.SLASH,
    Move.SMART_STRIKE, Move.SMELLING_SALTS, Move.SNAP_TRAP, Move.SOLAR_BLADE,
    Move.SPARK, Move.SPECTRAL_THIEF, Move.SPIN_OUT, Move.SPIRIT_BREAK,
    Move.STEAMROLLER, Move.STEEL_ROLLER, Move.STEEL_WING, Move.STOMP,
    Move.STOMPING_TANTRUM, Move.STONE_AXE, Move.STORM_THROW, Move.STRENGTH,
    Move.STRUGGLE, Move.SUBMISSION, Move.SUCKER_PUNCH, Move.SUNSTEEL_STRIKE,
    Move.SUPER_FANG, Move.SUPERCELL_SLAM, Move.SUPERPOWER, Move.SURGING_STRIKES,
    Move.TACKLE, Move.TAIL_SLAP, Move.TAKE_DOWN, Move.TEMPER_FLARE, Move.THIEF,
    Move.THRASH, Move.THROAT_CHOP, Move.THUNDER_FANG, Move.THUNDER_PUNCH,
    Move.TRAILBLAZE, Move.TRIPLE_AXEL, Move.TRIPLE_DIVE, Move.TRIPLE_KICK,
    Move.TROP_KICK, Move.TRUMP_CARD, Move.U_TURN, Move.UPPER_HAND, Move.V_CREATE,
    Move.VINE_WHIP, Move.VISE_GRIP, Move.VITAL_THROW, Move.VOLT_TACKLE,
    Move.WAKE_UP_SLAP, Move.WATERFALL, Move.WAVE_CRASH, Move.WICKED_BLOW,
    Move.WILD_CHARGE, Move.WING_ATTACK, Move.WOOD_HAMMER, Move.WRAP, Move.WRING_OUT,
    Move.X_SCISSOR, Move.ZEN_HEADBUTT, Move.ZING_ZAP,
})

for _move in _CONTACT_MOVES:
    if _move in MOVE_DATA:
        _data = MOVE_DATA[_move]
        MOVE_DATA[_move] = MoveData(
            _data.move_type, _data.category, _data.base_power, _data.accuracy,
            _data.pp, _data.priority, _data.target, _data.tags | MoveTag.CONTACT,
            _data.secondary, _data.drain, _data.recoil, _data.flags,
            _data.min_hits, _data.max_hits, _data.crit_boost, _data.secondary2,
            _data.self_stat_changes,
        )


# Sound moves: blocked by Soundproof, boosted by Punk Rock, converted by Liquid Voice.
# Sourced from Showdown {sound: 1} flag.
_SOUND_MOVES: frozenset[str] = frozenset({
    "HYPER_VOICE", "BUG_BUZZ", "BOOMBURST", "CHATTER", "DISARMING_VOICE",
    "ECHOED_VOICE", "GRASS_WHISTLE", "GROWL", "HEAL_BELL", "NOBLE_ROAR",
    "OVERDRIVE", "PERISH_SONG", "RELIC_SONG", "ROAR", "ROUND", "SCREECH",
    "SING", "SNARL", "SNORE", "SUPERSONIC", "UPROAR", "SPARKLING_ARIA",
    "EERIE_IMPULSE", "CLANGING_SCALES", "CLANGOROUS_SOUL", "PARTING_SHOT",
    "METAL_SOUND",
})

# Bullet/ball moves: blocked by Bulletproof.
_BULLET_MOVES: frozenset[str] = frozenset({
    "BULLET_SEED", "EGG_BOMB", "ELECTRO_BALL", "ENERGY_BALL", "FOCUS_BLAST",
    "GYRO_BALL", "MAGNET_BOMB", "MUD_BOMB", "OCTAZOOKA", "POLLEN_PUFF",
    "ROCK_BLAST", "ROCK_WRECKER", "SEED_BOMB", "SHADOW_BALL", "SLUDGE_BOMB",
    "WEATHER_BALL", "AURA_SPHERE", "PYRO_BALL",
})

# Pulse moves: boosted by Mega Launcher.
_PULSE_MOVES: frozenset[str] = frozenset({
    "AURA_SPHERE", "DARK_PULSE", "DRAGON_PULSE", "HEAL_PULSE",
    "ORIGIN_PULSE", "WATER_PULSE",
})

# Biting moves: boosted by Strong Jaw.
_BITING_MOVES: frozenset[str] = frozenset({
    "BITE", "CRUNCH", "FIRE_FANG", "ICE_FANG", "THUNDER_FANG",
    "POISON_FANG", "PSYCHIC_FANGS", "HYPER_FANG", "JAW_LOCK", "FISHIOUS_REND",
})

for _name in _SOUND_MOVES:
    if hasattr(Move, _name) and Move[_name] in MOVE_DATA:
        _data = MOVE_DATA[Move[_name]]
        MOVE_DATA[Move[_name]] = MoveData(
            _data.move_type, _data.category, _data.base_power, _data.accuracy,
            _data.pp, _data.priority, _data.target, _data.tags | MoveTag.SOUND,
            _data.secondary, _data.drain, _data.recoil, _data.flags,
            _data.min_hits, _data.max_hits, _data.crit_boost, _data.secondary2,
            _data.self_stat_changes,
        )

for _name in _BULLET_MOVES:
    if hasattr(Move, _name) and Move[_name] in MOVE_DATA:
        _data = MOVE_DATA[Move[_name]]
        MOVE_DATA[Move[_name]] = MoveData(
            _data.move_type, _data.category, _data.base_power, _data.accuracy,
            _data.pp, _data.priority, _data.target, _data.tags | MoveTag.BULLET,
            _data.secondary, _data.drain, _data.recoil, _data.flags,
            _data.min_hits, _data.max_hits, _data.crit_boost, _data.secondary2,
            _data.self_stat_changes,
        )

for _name in _PULSE_MOVES:
    if hasattr(Move, _name) and Move[_name] in MOVE_DATA:
        _data = MOVE_DATA[Move[_name]]
        MOVE_DATA[Move[_name]] = MoveData(
            _data.move_type, _data.category, _data.base_power, _data.accuracy,
            _data.pp, _data.priority, _data.target, _data.tags | MoveTag.PULSE,
            _data.secondary, _data.drain, _data.recoil, _data.flags,
            _data.min_hits, _data.max_hits, _data.crit_boost, _data.secondary2,
            _data.self_stat_changes,
        )

for _name in _BITING_MOVES:
    if hasattr(Move, _name) and Move[_name] in MOVE_DATA:
        _data = MOVE_DATA[Move[_name]]
        MOVE_DATA[Move[_name]] = MoveData(
            _data.move_type, _data.category, _data.base_power, _data.accuracy,
            _data.pp, _data.priority, _data.target, _data.tags | MoveTag.BITING,
            _data.secondary, _data.drain, _data.recoil, _data.flags,
            _data.min_hits, _data.max_hits, _data.crit_boost, _data.secondary2,
            _data.self_stat_changes,
        )

# Extra punching moves not covered by initial inline tags.
_PUNCHING_EXTRA: frozenset[str] = frozenset({
    "FORCE_PALM", "WAKE_UP_SLAP", "DIZZY_PUNCH", "WICKED_BLOW",
})

for _name in _PUNCHING_EXTRA:
    if hasattr(Move, _name) and Move[_name] in MOVE_DATA:
        _data = MOVE_DATA[Move[_name]]
        MOVE_DATA[Move[_name]] = MoveData(
            _data.move_type, _data.category, _data.base_power, _data.accuracy,
            _data.pp, _data.priority, _data.target, _data.tags | MoveTag.PUNCHING,
            _data.secondary, _data.drain, _data.recoil, _data.flags,
            _data.min_hits, _data.max_hits, _data.crit_boost, _data.secondary2,
            _data.self_stat_changes,
        )

# Slicing moves: boosted by Sharpness.
_SLICING_MOVES: frozenset[str] = frozenset({
    "AIR_SLASH", "NIGHT_SLASH", "LEAF_BLADE", "SLASH", "PSYCHO_CUT",
    "RAZOR_SHELL", "SACRED_SWORD", "SMART_STRIKE", "X_SCISSOR",
    "CROSS_POISON", "CEASELESS_EDGE", "AQUA_CUTTER",
})

for _name in _SLICING_MOVES:
    if hasattr(Move, _name) and Move[_name] in MOVE_DATA:
        _data = MOVE_DATA[Move[_name]]
        MOVE_DATA[Move[_name]] = MoveData(
            _data.move_type, _data.category, _data.base_power, _data.accuracy,
            _data.pp, _data.priority, _data.target, _data.tags | MoveTag.SLICING,
            _data.secondary, _data.drain, _data.recoil, _data.flags,
            _data.min_hits, _data.max_hits, _data.crit_boost, _data.secondary2,
            _data.self_stat_changes,
        )

# ---------------------------------------------------------------------------
# Canonical move-group frozensets
# These group moves for engine dispatch logic (e.g. "is this a protect move?").
# MoveTag bits serve a different purpose: per-move property flags checked at
# damage/effect lookup time (e.g. SOUND, BULLET). Frozensets are used where the
# grouping drives branching logic rather than a per-move attribute.
# ---------------------------------------------------------------------------

PROTECT_MOVES: frozenset[Move] = frozenset({
    Move.PROTECT, Move.DETECT,
    Move.KING_S_SHIELD, Move.SPIKY_SHIELD, Move.BANEFUL_BUNKER,
    Move.DEFEND_ORDER, Move.OBSTRUCT,
    Move.WIDE_GUARD, Move.QUICK_GUARD,
})

# Status moves that target the opponent but are NOT reflected by Magic Bounce
# (Showdown: these lack the 'reflectable' flag)
NON_REFLECTABLE_MOVES: frozenset[Move] = frozenset({
    Move.MEMENTO,
    Move.DECORATE,
})

PIVOT_MOVES: frozenset[Move] = frozenset({Move.U_TURN, Move.VOLT_SWITCH, Move.FLIP_TURN})

PHASING_STATUS_MOVES: frozenset[Move] = frozenset({Move.ROAR, Move.WHIRLWIND})
PHASING_DAMAGE_MOVES: frozenset[Move] = frozenset({Move.DRAGON_TAIL, Move.CIRCLE_THROW})

# Weather-recovery healing scales with weather (Moonlight/Synthesis/etc.); Shore Up is boosted in Sand.
WEATHER_RECOVERY_MOVES: frozenset[Move] = frozenset({
    Move.MOONLIGHT, Move.MORNING_SUN, Move.SYNTHESIS, Move.SHORE_UP,
})

RECOVERY_MOVE_SET: frozenset[Move] = frozenset({
    Move.RECOVER, Move.SLACK_OFF, Move.HEAL_ORDER, Move.SOFT_BOILED,
    Move.ROOST, Move.STRENGTH_SAP, Move.SHORE_UP,
})

PARALYSIS_MOVES: frozenset[Move] = frozenset({
    Move.THUNDER_WAVE, Move.STUN_SPORE, Move.GLARE, Move.NUZZLE, Move.ZAP_CANNON,
})

POISON_INFLICT_MOVES: frozenset[Move] = frozenset({Move.TOXIC, Move.POISON_POWDER, Move.POISON_GAS})

SPEED_SETUP_MOVES: frozenset[Move] = frozenset({Move.AGILITY, Move.ROCK_POLISH, Move.AUTOTOMIZE})

OFFENSIVE_SETUP_MOVES: frozenset[Move] = frozenset({
    Move.SWORDS_DANCE, Move.DRAGON_DANCE, Move.SHIFT_GEAR, Move.HOWL,
    Move.SHARPEN, Move.MEDITATE, Move.HONE_CLAWS, Move.NASTY_PLOT,
    Move.TAIL_GLOW, Move.WORK_UP,
})

DEFENSIVE_SETUP_MOVES: frozenset[Move] = frozenset({
    Move.ACID_ARMOR, Move.BARRIER, Move.IRON_DEFENSE, Move.COTTON_GUARD,
    Move.HARDEN, Move.STOCKPILE, Move.COSMIC_POWER,
})

TERRAIN_MOVES: frozenset[Move] = frozenset({
    Move.ELECTRIC_TERRAIN, Move.PSYCHIC_TERRAIN,
    Move.GRASSY_TERRAIN, Move.MISTY_TERRAIN,
})

# Move classification sets (used by engine)
OHKO_MOVES = frozenset({Move.GUILLOTINE, Move.HORN_DRILL, Move.FISSURE, Move.SHEER_COLD})
RAMPAGE_MOVES = frozenset({Move.THRASH, Move.OUTRAGE, Move.PETAL_DANCE})
BINDING_MOVES = frozenset({Move.WRAP, Move.FIRE_SPIN, Move.CLAMP, Move.WHIRLPOOL, Move.SAND_TOMB, Move.INFESTATION, Move.MAGMA_STORM, Move.BIND})
PROTECT_BYPASS_MOVES = frozenset({Move.FEINT, Move.HYPERSPACE_FURY, Move.HYPERSPACE_HOLE, Move.PHANTOM_FORCE, Move.PLAY_NICE})
DANCE_MOVES = frozenset({
    Move.SWORDS_DANCE, Move.DRAGON_DANCE, Move.QUIVER_DANCE, Move.FEATHER_DANCE,
    Move.PETAL_DANCE, Move.TEETER_DANCE, Move.FIERY_DANCE,
    Move.LUNAR_DANCE, Move.REVELATION_DANCE,
})
GRAVITY_BLOCKED_MOVES = frozenset({
    Move.FLY, Move.BOUNCE, Move.HIGH_JUMP_KICK, Move.JUMP_KICK,
    Move.MAGNET_RISE, Move.SPLASH, Move.TELEKINESIS, Move.SKY_DROP,
})
TWO_TURN_MOVES = frozenset({
    Move.SOLAR_BEAM, Move.SOLAR_BLADE, Move.BOUNCE, Move.DIVE,
    Move.FLY, Move.PHANTOM_FORCE, Move.METEOR_BEAM, Move.SKULL_BASH,
    Move.DIG, Move.SKY_ATTACK, Move.RAZOR_WIND,
})
WEATHER_SKIP_CHARGE = frozenset({Move.SOLAR_BEAM, Move.SOLAR_BLADE})
SEMI_INVULNERABLE_MOVES = frozenset({Move.BOUNCE, Move.FLY, Move.DIVE, Move.DIG, Move.PHANTOM_FORCE})

# Semi-invulnerable charge states grouped by where the target hides. A handful of attacking
# moves can still hit a target in each state (and a subset deal double damage). Phantom Force
# (and Shadow Force) leave no opening — nothing hits through them.
_SEMI_INVULN_AIRBORNE = frozenset({Move.FLY, Move.BOUNCE, Move.SKY_DROP})
_SEMI_INVULN_UNDERGROUND = frozenset({Move.DIG})
_SEMI_INVULN_UNDERWATER = frozenset({Move.DIVE})

# (hits-through set, double-damage subset) for each invuln state.
_AIRBORNE_HIT_MOVES = frozenset({
    Move.GUST, Move.TWISTER, Move.THUNDER, Move.HURRICANE,
    Move.SKY_UPPERCUT, Move.SMACK_DOWN, Move.THOUSAND_ARROWS,
})
_AIRBORNE_DOUBLE_MOVES = frozenset({Move.GUST, Move.TWISTER})
_UNDERGROUND_HIT_MOVES = frozenset({Move.EARTHQUAKE, Move.MAGNITUDE, Move.FISSURE})
_UNDERGROUND_DOUBLE_MOVES = frozenset({Move.EARTHQUAKE, Move.MAGNITUDE})
_UNDERWATER_HIT_MOVES = frozenset({Move.SURF, Move.WHIRLPOOL})
_UNDERWATER_DOUBLE_MOVES = frozenset({Move.SURF, Move.WHIRLPOOL})


def semi_invuln_interaction(charging_move: "Move", attacking_move: "Move") -> tuple[bool, bool]:
    """Return (hits_through, double_damage) for an attack on a semi-invulnerable target.

    charging_move is the two-turn move the target is mid-charge on (Fly/Bounce/Dig/Dive/...).
    Returns (False, False) when the attack misses the invulnerable target (the default), or
    (True, ...) when the attack reaches it — with double_damage True for the moves whose power
    doubles against that state (e.g. Gust/Twister vs airborne, Earthquake vs underground).
    """
    if charging_move in _SEMI_INVULN_AIRBORNE:
        return (attacking_move in _AIRBORNE_HIT_MOVES, attacking_move in _AIRBORNE_DOUBLE_MOVES)
    if charging_move in _SEMI_INVULN_UNDERGROUND:
        return (attacking_move in _UNDERGROUND_HIT_MOVES, attacking_move in _UNDERGROUND_DOUBLE_MOVES)
    if charging_move in _SEMI_INVULN_UNDERWATER:
        return (attacking_move in _UNDERWATER_HIT_MOVES, attacking_move in _UNDERWATER_DOUBLE_MOVES)
    return (False, False)
TRAP_DEFENDER_MOVES = frozenset({Move.ANCHOR_SHOT, Move.SPIRIT_SHACKLE})
HJK_MOVES = frozenset({Move.HIGH_JUMP_KICK, Move.JUMP_KICK, Move.SUPERCELL_SLAM})
RECHARGE_MOVES = frozenset({
    Move.HYPER_BEAM, Move.GIGA_IMPACT, Move.BLAST_BURN,
    Move.HYDRO_CANNON, Move.FRENZY_PLANT, Move.METEOR_ASSAULT,
    Move.ROCK_WRECKER,
})
DEFROST_TARGET_MOVES = frozenset({Move.SCALD, Move.SACRED_FIRE, Move.BURN_UP, Move.SCORCHING_SANDS})
GULP_TRIGGER_MOVES = frozenset({Move.SURF, Move.DIVE})


def safe_move(name: str):
    """Return Move[name] or None if the move doesn't exist in this codebase's Move enum."""
    try:
        return Move[name]
    except KeyError:
        return None


def _levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (ca != cb)))
        prev = curr
    return prev[-1]


def move_name_to_enum(move_name: str) -> Optional[Move]:
    """Resolve a human-readable move name to its Move enum, or None if not found.

    Normalises input (strip/uppercase/spaces+hyphens→underscores), tries exact lookup
    first, then falls back to Levenshtein distance ≤ 2 linear scan.
    """
    normalised = move_name.strip().upper().replace(" ", "_").replace("-", "_")
    try:
        return Move[normalised]
    except KeyError:
        pass
    best: Optional[Move] = None
    best_dist = 3  # threshold: accept only ≤ 2
    for member in Move:
        dist = _levenshtein(normalised, member.name)
        if dist < best_dist:
            best_dist = dist
            best = member
    return best


# safe_move returns None for moves absent from the current Move enum; filter(None, ...) drops them intentionally for forward-compatibility.
METRONOME_EXCLUDED = frozenset(filter(None, [
    safe_move('AFTER_YOU'), safe_move('APPLE_ACID'), safe_move('ARMOR_CANNON'),
    safe_move('ASSIST'), safe_move('AURA_WHEEL'), safe_move('BANEFUL_BUNKER'),
    safe_move('BEAK_BLAST'), safe_move('BELCH'), safe_move('BESTOW'),
    safe_move('BODY_PRESS'), safe_move('BOUNCE'), safe_move('CELEBRATE'),
    safe_move('CHATTER'), safe_move('CLANGOROUS_SOUL'), safe_move('COPYCAT'),
    safe_move('COUNTER'), safe_move('COVET'), safe_move('DESTINY_BOND'),
    safe_move('DETECT'), safe_move('DIG'), safe_move('DIVE'),
    safe_move('DYNAMAX_CANNON'), safe_move('ENDURE'), safe_move('FEINT'),
    safe_move('FISSURE'), safe_move('FLY'), safe_move('FOCUS_PUNCH'),
    safe_move('FOLLOW_ME'), safe_move('FREEZE_SHOCK'), safe_move('GEOMANCY'),
    safe_move('GRAV_APPLE'), safe_move('GUILLOTINE'), safe_move('HEAL_PULSE'),
    safe_move('HELPING_HAND'), safe_move('HORN_DRILL'), safe_move('ICE_BURN'),
    safe_move('INSTRUCT'), safe_move('KINGS_SHIELD'), safe_move('KING_S_SHIELD'),
    safe_move('LIGHT_OF_RUIN'), safe_move('LOVE_SONG'), safe_move('MAKE_IT_RAIN'),
    safe_move('MAT_BLOCK'), safe_move('ME_FIRST'), safe_move('METRONOME'),
    safe_move('MIMIC'), safe_move('MIRROR_COAT'), safe_move('MIRROR_MOVE'),
    safe_move('MOONGEIST_BEAM'), safe_move('NATURE_POWER'), safe_move('PHOTON_GEYSER'),
    safe_move('PLASMA_FISTS'), safe_move('PROTECT'), safe_move('RAGE_FIST'),
    safe_move('RAGE_POWDER'), safe_move('RECYCLE'), safe_move('REVIVAL_BLESSING'),
    safe_move('SHELL_TRAP'), safe_move('SKETCH'),
    safe_move('SKULL_BASH'), safe_move('SKY_ATTACK'), safe_move('SKY_DROP'),
    safe_move('SLEEP_TALK'), safe_move('SNATCH'), safe_move('SNAP_TRAP'),
    safe_move('SPIT_UP'), safe_move('SPLISHY_SPLASH'), safe_move('STEAL_FIRE'),
    safe_move('STRUGGLE'), safe_move('SUNSTEEL_STRIKE'), safe_move('TRANSFORM'),
    safe_move('TRICK_OR_TREAT'), safe_move('UPROAR'), safe_move('WHIRLPOOL'),
]))

# Same forward-compatibility pattern as METRONOME_EXCLUDED.
SLEEP_TALK_EXCLUDED = frozenset(filter(None, [
    safe_move('BELCH'), safe_move('BOUNCE'), safe_move('COPYCAT'),
    safe_move('DIG'), safe_move('DIVE'), safe_move('FOCUS_PUNCH'),
    safe_move('FLY'), safe_move('INSTRUCT'), safe_move('ME_FIRST'),
    safe_move('MIMIC'), safe_move('MIRROR_MOVE'), safe_move('SHELL_TRAP'),
    safe_move('SKETCH'), safe_move('SKY_DROP'), safe_move('SLEEP_TALK'),
    safe_move('SNATCH'), safe_move('UPROAR'), safe_move('BEAK_BLAST'),
    safe_move('GEOMANCY'), safe_move('SKULL_BASH'), safe_move('SKY_ATTACK'),
    safe_move('SOLAR_BEAM'), safe_move('SOLAR_BLADE'),
    safe_move('PHANTOM_FORCE'), safe_move('RAZOR_WIND'),
    safe_move('ASSIST'), safe_move('ELECTRO_SHOT'), safe_move('METEOR_BEAM'),
]))


# Same forward-compatibility pattern as METRONOME_EXCLUDED.
COPYCAT_EXCLUDED = frozenset(filter(None, [
    safe_move('AFTER_YOU'), safe_move('ASSIST'), safe_move('BEAK_BLAST'),
    safe_move('BELCH'), safe_move('BESTOW'), safe_move('CELEBRATE'),
    safe_move('CHATTER'), safe_move('CIRCLE_THROW'), safe_move('COPYCAT'),
    safe_move('COUNTER'), safe_move('COVET'), safe_move('DESTINY_BOND'),
    safe_move('DETECT'), safe_move('DIG'), safe_move('DIVE'),
    safe_move('DRAGON_TAIL'), safe_move('ENDURE'), safe_move('FEINT'),
    safe_move('FLY'), safe_move('FOCUS_PUNCH'), safe_move('FOLLOW_ME'),
    safe_move('HELPING_HAND'), safe_move('INSTRUCT'), safe_move('ME_FIRST'),
    safe_move('METRONOME'), safe_move('MIMIC'), safe_move('MIRROR_COAT'),
    safe_move('MIRROR_MOVE'), safe_move('PROTECT'), safe_move('RAGE_POWDER'),
    safe_move('SHELL_TRAP'), safe_move('SKETCH'), safe_move('SLEEP_TALK'),
    safe_move('SNATCH'), safe_move('SPIKY_SHIELD'), safe_move('STRUGGLE'),
    safe_move('THIEF'), safe_move('TRANSFORM'),
]))

# Same forward-compatibility pattern as METRONOME_EXCLUDED.
MIRROR_MOVE_EXCLUDED = frozenset(filter(None, [
    safe_move('MIRROR_MOVE'), safe_move('COPYCAT'), safe_move('ASSIST'),
    safe_move('METRONOME'), safe_move('SLEEP_TALK'), safe_move('BEAK_BLAST'),
    safe_move('FOCUS_PUNCH'), safe_move('SHELL_TRAP'), safe_move('STRUGGLE'),
]))


def copycat_valid(move: 'Move') -> bool:
    """Return True if the move can be called by Copycat."""
    return move not in COPYCAT_EXCLUDED


def mirror_move_valid(move: 'Move') -> bool:
    """Return True if the move can be called by Mirror Move."""
    return move not in MIRROR_MOVE_EXCLUDED


def metronome_options() -> list:
    """Return all Move values usable by Metronome (excludes banned list and NONE/STRUGGLE)."""
    result = []
    for m in Move:
        if m == Move.NONE:
            continue
        if m == Move.STRUGGLE:
            continue
        if m in METRONOME_EXCLUDED:
            continue
        if m not in MOVE_DATA:
            continue
        result.append(m)
    return result


def sleep_talk_options(pokemon) -> list:
    """Return moves in pokemon's moveset usable by Sleep Talk."""
    result = []
    for move, pp in zip(pokemon.move_ids, pokemon.move_pp):
        if move == Move.NONE:
            continue
        if move in SLEEP_TALK_EXCLUDED:
            continue
        result.append(move)
    return result
