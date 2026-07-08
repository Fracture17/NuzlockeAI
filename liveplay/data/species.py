# Species enum and base-stat data for all Gen 1-9 Pokemon including regional forms.
# Generated from Showdown pokedex.ts. Form variants use 10000*num+idx as enum value.
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional
from liveplay.data.types import Type
from liveplay.data.growth_rate import GrowthRate


class Species(IntEnum):
    BULBASAUR = 1
    IVYSAUR = 2
    VENUSAUR = 3
    VENUSAUR_MEGA = 906
    CHARMANDER = 4
    CHARMELEON = 5
    CHARIZARD = 6
    CHARIZARD_MEGA_X = 907
    CHARIZARD_MEGA_Y = 908
    SQUIRTLE = 7
    WARTORTLE = 8
    BLASTOISE = 9
    BLASTOISE_MEGA = 909
    CATERPIE = 10
    METAPOD = 11
    BUTTERFREE = 12
    WEEDLE = 13
    KAKUNA = 14
    BEEDRILL = 15
    BEEDRILL_MEGA = 910
    PIDGEY = 16
    PIDGEOTTO = 17
    PIDGEOT = 18
    PIDGEOT_MEGA = 911
    RATTATA = 19
    RATTATA_ALOLA = 956
    RATICATE = 20
    RATICATE_ALOLA = 957
    SPEAROW = 21
    FEAROW = 22
    EKANS = 23
    ARBOK = 24
    PIKACHU = 25
    PIKACHU_COSPLAY = 1009
    PIKACHU_ROCK_STAR = 1010
    PIKACHU_BELLE = 1011
    PIKACHU_POP_STAR = 1012
    PIKACHU_PHD = 1013
    PIKACHU_LIBRE = 1014
    PIKACHU_ORIGINAL = 1015
    PIKACHU_HOENN = 1016
    PIKACHU_SINNOH = 1017
    PIKACHU_UNOVA = 1018
    PIKACHU_KALOS = 1019
    PIKACHU_ALOLA = 1020
    PIKACHU_PARTNER = 1021
    PIKACHU_WORLD = 1022
    RAICHU = 26
    RAICHU_ALOLA = 958
    SANDSHREW = 27
    SANDSHREW_ALOLA = 959
    SANDSLASH = 28
    SANDSLASH_ALOLA = 960
    NIDORAN_F = 29
    NIDORINA = 30
    NIDOQUEEN = 31
    NIDORAN_M = 32
    NIDORINO = 33
    NIDOKING = 34
    CLEFAIRY = 35
    CLEFABLE = 36
    VULPIX = 37
    VULPIX_ALOLA = 961
    NINETALES = 38
    NINETALES_ALOLA = 962
    JIGGLYPUFF = 39
    WIGGLYTUFF = 40
    ZUBAT = 41
    GOLBAT = 42
    ODDISH = 43
    GLOOM = 44
    VILEPLUME = 45
    PARAS = 46
    PARASECT = 47
    VENONAT = 48
    VENOMOTH = 49
    DIGLETT = 50
    DIGLETT_ALOLA = 963
    DUGTRIO = 51
    DUGTRIO_ALOLA = 964
    MEOWTH = 52
    MEOWTH_ALOLA = 965
    MEOWTH_GALAR = 974
    PERSIAN = 53
    PERSIAN_ALOLA = 966
    PSYDUCK = 54
    GOLDUCK = 55
    MANKEY = 56
    PRIMEAPE = 57
    GROWLITHE = 58
    GROWLITHE_HISUI = 993
    ARCANINE = 59
    ARCANINE_HISUI = 994
    POLIWAG = 60
    POLIWHIRL = 61
    POLIWRATH = 62
    ABRA = 63
    KADABRA = 64
    ALAKAZAM = 65
    ALAKAZAM_MEGA = 912
    MACHOP = 66
    MACHOKE = 67
    MACHAMP = 68
    BELLSPROUT = 69
    WEEPINBELL = 70
    VICTREEBEL = 71
    TENTACOOL = 72
    TENTACRUEL = 73
    GEODUDE = 74
    GEODUDE_ALOLA = 967
    GRAVELER = 75
    GRAVELER_ALOLA = 968
    GOLEM = 76
    GOLEM_ALOLA = 969
    PONYTA = 77
    PONYTA_GALAR = 975
    RAPIDASH = 78
    RAPIDASH_GALAR = 976
    SLOWPOKE = 79
    SLOWPOKE_GALAR = 977
    SLOWBRO = 80
    SLOWBRO_MEGA = 913
    SLOWBRO_GALAR = 978
    MAGNEMITE = 81
    MAGNETON = 82
    FARFETCH_U2019D = 83
    FARFETCH_U2019D_GALAR = 979
    DODUO = 84
    DODRIO = 85
    SEEL = 86
    DEWGONG = 87
    GRIMER = 88
    GRIMER_ALOLA = 970
    MUK = 89
    MUK_ALOLA = 971
    SHELLDER = 90
    CLOYSTER = 91
    GASTLY = 92
    HAUNTER = 93
    GENGAR = 94
    GENGAR_MEGA = 914
    ONIX = 95
    DROWZEE = 96
    HYPNO = 97
    KRABBY = 98
    KINGLER = 99
    VOLTORB = 100
    VOLTORB_HISUI = 995
    ELECTRODE = 101
    ELECTRODE_HISUI = 996
    EXEGGCUTE = 102
    EXEGGUTOR = 103
    EXEGGUTOR_ALOLA = 972
    CUBONE = 104
    MAROWAK = 105
    MAROWAK_ALOLA = 973
    HITMONLEE = 106
    HITMONCHAN = 107
    LICKITUNG = 108
    KOFFING = 109
    WEEZING = 110
    WEEZING_GALAR = 980
    RHYHORN = 111
    RHYDON = 112
    CHANSEY = 113
    TANGELA = 114
    KANGASKHAN = 115
    KANGASKHAN_MEGA = 915
    HORSEA = 116
    SEADRA = 117
    GOLDEEN = 118
    SEAKING = 119
    STARYU = 120
    STARMIE = 121
    MR_MIME = 122
    MR_MIME_GALAR = 981
    SCYTHER = 123
    JYNX = 124
    ELECTABUZZ = 125
    MAGMAR = 126
    PINSIR = 127
    PINSIR_MEGA = 916
    TAUROS = 128
    MAGIKARP = 129
    GYARADOS = 130
    GYARADOS_MEGA = 917
    LAPRAS = 131
    DITTO = 132
    EEVEE = 133
    VAPOREON = 134
    JOLTEON = 135
    FLAREON = 136
    PORYGON = 137
    OMANYTE = 138
    OMASTAR = 139
    KABUTO = 140
    KABUTOPS = 141
    AERODACTYL = 142
    AERODACTYL_MEGA = 918
    SNORLAX = 143
    ARTICUNO = 144
    ARTICUNO_GALAR = 982
    ZAPDOS = 145
    ZAPDOS_GALAR = 983
    MOLTRES = 146
    MOLTRES_GALAR = 984
    DRATINI = 147
    DRAGONAIR = 148
    DRAGONITE = 149
    MEWTWO = 150
    MEWTWO_MEGA_X = 919
    MEWTWO_MEGA_Y = 920
    MEW = 151
    CHIKORITA = 152
    BAYLEEF = 153
    MEGANIUM = 154
    CYNDAQUIL = 155
    QUILAVA = 156
    TYPHLOSION = 157
    TYPHLOSION_HISUI = 997
    TOTODILE = 158
    CROCONAW = 159
    FERALIGATR = 160
    SENTRET = 161
    FURRET = 162
    HOOTHOOT = 163
    NOCTOWL = 164
    LEDYBA = 165
    LEDIAN = 166
    SPINARAK = 167
    ARIADOS = 168
    CROBAT = 169
    CHINCHOU = 170
    LANTURN = 171
    PICHU = 172
    PICHU_SPIKY_EARED = 1023
    CLEFFA = 173
    IGGLYBUFF = 174
    TOGEPI = 175
    TOGETIC = 176
    NATU = 177
    XATU = 178
    MAREEP = 179
    FLAAFFY = 180
    AMPHAROS = 181
    AMPHAROS_MEGA = 921
    BELLOSSOM = 182
    MARILL = 183
    AZUMARILL = 184
    SUDOWOODO = 185
    POLITOED = 186
    HOPPIP = 187
    SKIPLOOM = 188
    JUMPLUFF = 189
    AIPOM = 190
    SUNKERN = 191
    SUNFLORA = 192
    YANMA = 193
    WOOPER = 194
    QUAGSIRE = 195
    ESPEON = 196
    UMBREON = 197
    MURKROW = 198
    SLOWKING = 199
    SLOWKING_GALAR = 985
    MISDREAVUS = 200
    UNOWN_A = 201
    UNOWN_B = 1024
    UNOWN_C = 1025
    UNOWN_D = 1026
    UNOWN_E = 1027
    UNOWN_F = 1028
    UNOWN_G = 1029
    UNOWN_H = 1030
    UNOWN_I = 1031
    UNOWN_J = 1032
    UNOWN_K = 1033
    UNOWN_L = 1034
    UNOWN_M = 1035
    UNOWN_N = 1036
    UNOWN_O = 1037
    UNOWN_P = 1038
    UNOWN_Q = 1039
    UNOWN_R = 1040
    UNOWN_S = 1041
    UNOWN_T = 1042
    UNOWN_U = 1043
    UNOWN_V = 1044
    UNOWN_W = 1045
    UNOWN_X = 1046
    UNOWN_Y = 1047
    UNOWN_Z = 1048
    UNOWN_EX = 1049
    UNOWN_QUESTION = 1050
    WOBBUFFET = 202
    GIRAFARIG = 203
    PINECO = 204
    FORRETRESS = 205
    DUNSPARCE = 206
    GLIGAR = 207
    STEELIX = 208
    STEELIX_MEGA = 922
    SNUBBULL = 209
    GRANBULL = 210
    QWILFISH = 211
    QWILFISH_HISUI = 998
    SCIZOR = 212
    SCIZOR_MEGA = 923
    SHUCKLE = 213
    HERACROSS = 214
    HERACROSS_MEGA = 924
    SNEASEL = 215
    SNEASEL_HISUI = 999
    TEDDIURSA = 216
    URSARING = 217
    SLUGMA = 218
    MAGCARGO = 219
    SWINUB = 220
    PILOSWINE = 221
    CORSOLA = 222
    CORSOLA_GALAR = 986
    REMORAID = 223
    OCTILLERY = 224
    DELIBIRD = 225
    MANTINE = 226
    SKARMORY = 227
    HOUNDOUR = 228
    HOUNDOOM = 229
    HOUNDOOM_MEGA = 925
    KINGDRA = 230
    PHANPY = 231
    DONPHAN = 232
    PORYGON2 = 233
    STANTLER = 234
    SMEARGLE = 235
    TYROGUE = 236
    HITMONTOP = 237
    SMOOCHUM = 238
    ELEKID = 239
    MAGBY = 240
    MILTANK = 241
    BLISSEY = 242
    RAIKOU = 243
    ENTEI = 244
    SUICUNE = 245
    LARVITAR = 246
    PUPITAR = 247
    TYRANITAR = 248
    TYRANITAR_MEGA = 926
    LUGIA = 249
    HO_OH = 250
    CELEBI = 251
    TREECKO = 252
    GROVYLE = 253
    SCEPTILE = 254
    SCEPTILE_MEGA = 927
    TORCHIC = 255
    COMBUSKEN = 256
    BLAZIKEN = 257
    BLAZIKEN_MEGA = 928
    MUDKIP = 258
    MARSHTOMP = 259
    SWAMPERT = 260
    SWAMPERT_MEGA = 929
    POOCHYENA = 261
    MIGHTYENA = 262
    ZIGZAGOON = 263
    ZIGZAGOON_GALAR = 987
    LINOONE = 264
    LINOONE_GALAR = 988
    WURMPLE = 265
    SILCOON = 266
    BEAUTIFLY = 267
    CASCOON = 268
    DUSTOX = 269
    LOTAD = 270
    LOMBRE = 271
    LUDICOLO = 272
    SEEDOT = 273
    NUZLEAF = 274
    SHIFTRY = 275
    TAILLOW = 276
    SWELLOW = 277
    WINGULL = 278
    PELIPPER = 279
    RALTS = 280
    KIRLIA = 281
    GARDEVOIR = 282
    GARDEVOIR_MEGA = 930
    SURSKIT = 283
    MASQUERAIN = 284
    SHROOMISH = 285
    BRELOOM = 286
    SLAKOTH = 287
    VIGOROTH = 288
    SLAKING = 289
    NINCADA = 290
    NINJASK = 291
    SHEDINJA = 292
    WHISMUR = 293
    LOUDRED = 294
    EXPLOUD = 295
    MAKUHITA = 296
    HARIYAMA = 297
    AZURILL = 298
    NOSEPASS = 299
    SKITTY = 300
    DELCATTY = 301
    SABLEYE = 302
    SABLEYE_MEGA = 931
    MAWILE = 303
    MAWILE_MEGA = 932
    ARON = 304
    LAIRON = 305
    AGGRON = 306
    AGGRON_MEGA = 933
    MEDITITE = 307
    MEDICHAM = 308
    MEDICHAM_MEGA = 934
    ELECTRIKE = 309
    MANECTRIC = 310
    MANECTRIC_MEGA = 935
    PLUSLE = 311
    MINUN = 312
    VOLBEAT = 313
    ILLUMISE = 314
    ROSELIA = 315
    GULPIN = 316
    SWALOT = 317
    CARVANHA = 318
    SHARPEDO = 319
    SHARPEDO_MEGA = 936
    WAILMER = 320
    WAILORD = 321
    NUMEL = 322
    CAMERUPT = 323
    CAMERUPT_MEGA = 937
    TORKOAL = 324
    SPOINK = 325
    GRUMPIG = 326
    SPINDA = 327
    TRAPINCH = 328
    VIBRAVA = 329
    FLYGON = 330
    CACNEA = 331
    CACTURNE = 332
    SWABLU = 333
    ALTARIA = 334
    ALTARIA_MEGA = 938
    ZANGOOSE = 335
    SEVIPER = 336
    LUNATONE = 337
    SOLROCK = 338
    BARBOACH = 339
    WHISCASH = 340
    CORPHISH = 341
    CRAWDAUNT = 342
    BALTOY = 343
    CLAYDOL = 344
    LILEEP = 345
    CRADILY = 346
    ANORITH = 347
    ARMALDO = 348
    FEEBAS = 349
    MILOTIC = 350
    CASTFORM = 351
    CASTFORM_SUNNY = 1051
    CASTFORM_RAINY = 1052
    CASTFORM_SNOWY = 1053
    KECLEON = 352
    SHUPPET = 353
    BANETTE = 354
    BANETTE_MEGA = 939
    DUSKULL = 355
    DUSCLOPS = 356
    TROPIUS = 357
    CHIMECHO = 358
    ABSOL = 359
    ABSOL_MEGA = 940
    WYNAUT = 360
    SNORUNT = 361
    GLALIE = 362
    GLALIE_MEGA = 941
    SPHEAL = 363
    SEALEO = 364
    WALREIN = 365
    CLAMPERL = 366
    HUNTAIL = 367
    GOREBYSS = 368
    RELICANTH = 369
    LUVDISC = 370
    BAGON = 371
    SHELGON = 372
    SALAMENCE = 373
    SALAMENCE_MEGA = 942
    BELDUM = 374
    METANG = 375
    METAGROSS = 376
    METAGROSS_MEGA = 943
    REGIROCK = 377
    REGICE = 378
    REGISTEEL = 379
    LATIAS = 380
    LATIAS_MEGA = 944
    LATIOS = 381
    LATIOS_MEGA = 945
    KYOGRE = 382
    KYOGRE_PRIMAL = 954
    GROUDON = 383
    GROUDON_PRIMAL = 955
    RAYQUAZA = 384
    RAYQUAZA_MEGA = 953
    JIRACHI = 385
    DEOXYS = 386
    DEOXYS_ATTACK = 1054
    DEOXYS_DEFENSE = 1055
    DEOXYS_SPEED = 1056
    TURTWIG = 387
    GROTLE = 388
    TORTERRA = 389
    CHIMCHAR = 390
    MONFERNO = 391
    INFERNAPE = 392
    PIPLUP = 393
    PRINPLUP = 394
    EMPOLEON = 395
    STARLY = 396
    STARAVIA = 397
    STARAPTOR = 398
    BIDOOF = 399
    BIBAREL = 400
    KRICKETOT = 401
    KRICKETUNE = 402
    SHINX = 403
    LUXIO = 404
    LUXRAY = 405
    BUDEW = 406
    ROSERADE = 407
    CRANIDOS = 408
    RAMPARDOS = 409
    SHIELDON = 410
    BASTIODON = 411
    BURMY = 412
    BURMY_SANDY = 1057
    BURMY_TRASH = 1058
    WORMADAM = 413
    WORMADAM_SANDY = 1059
    WORMADAM_TRASH = 1060
    MOTHIM = 414
    COMBEE = 415
    VESPIQUEN = 416
    PACHIRISU = 417
    BUIZEL = 418
    FLOATZEL = 419
    CHERUBI = 420
    CHERRIM = 421
    CHERRIM_SUNSHINE = 1061
    SHELLOS = 422
    SHELLOS_WEST = 1062
    GASTRODON = 423
    GASTRODON_WEST = 1063
    AMBIPOM = 424
    DRIFLOON = 425
    DRIFBLIM = 426
    BUNEARY = 427
    LOPUNNY = 428
    LOPUNNY_MEGA = 946
    MISMAGIUS = 429
    HONCHKROW = 430
    GLAMEOW = 431
    PURUGLY = 432
    CHINGLING = 433
    STUNKY = 434
    SKUNTANK = 435
    BRONZOR = 436
    BRONZONG = 437
    BONSLY = 438
    MIME_JR = 439
    HAPPINY = 440
    CHATOT = 441
    SPIRITOMB = 442
    GIBLE = 443
    GABITE = 444
    GARCHOMP = 445
    GARCHOMP_MEGA = 947
    MUNCHLAX = 446
    RIOLU = 447
    LUCARIO = 448
    LUCARIO_MEGA = 948
    HIPPOPOTAS = 449
    HIPPOWDON = 450
    SKORUPI = 451
    DRAPION = 452
    CROAGUNK = 453
    TOXICROAK = 454
    CARNIVINE = 455
    FINNEON = 456
    LUMINEON = 457
    MANTYKE = 458
    SNOVER = 459
    ABOMASNOW = 460
    ABOMASNOW_MEGA = 949
    WEAVILE = 461
    MAGNEZONE = 462
    LICKILICKY = 463
    RHYPERIOR = 464
    TANGROWTH = 465
    ELECTIVIRE = 466
    MAGMORTAR = 467
    TOGEKISS = 468
    YANMEGA = 469
    LEAFEON = 470
    GLACEON = 471
    GLISCOR = 472
    MAMOSWINE = 473
    PORYGON_Z = 474
    GALLADE = 475
    GALLADE_MEGA = 950
    PROBOPASS = 476
    DUSKNOIR = 477
    FROSLASS = 478
    ROTOM = 479
    ROTOM_HEAT = 1064
    ROTOM_WASH = 1065
    ROTOM_FROST = 1066
    ROTOM_FAN = 1067
    ROTOM_MOW = 1068
    UXIE = 480
    MESPRIT = 481
    AZELF = 482
    DIALGA = 483
    DIALGA_ORIGIN = 1069
    PALKIA = 484
    PALKIA_ORIGIN = 1070
    HEATRAN = 485
    REGIGIGAS = 486
    GIRATINA = 487
    GIRATINA_ORIGIN = 1071
    CRESSELIA = 488
    PHIONE = 489
    MANAPHY = 490
    DARKRAI = 491
    SHAYMIN = 492
    SHAYMIN_SKY = 1072
    ARCEUS = 493
    ARCEUS_BUG = 1078
    ARCEUS_DARK = 1088
    ARCEUS_DRAGON = 1087
    ARCEUS_ELECTRIC = 1085
    ARCEUS_FIGHTING = 1073
    ARCEUS_FIRE = 1081
    ARCEUS_FLYING = 1074
    ARCEUS_GHOST = 1079
    ARCEUS_GRASS = 1083
    ARCEUS_GROUND = 1076
    ARCEUS_ICE = 1086
    ARCEUS_POISON = 1075
    ARCEUS_PSYCHIC = 1085
    ARCEUS_ROCK = 1077
    ARCEUS_STEEL = 1080
    ARCEUS_WATER = 1082
    ARCEUS_FAIRY = 1089
    VICTINI = 494
    SNIVY = 495
    SERVINE = 496
    SERPERIOR = 497
    TEPIG = 498
    PIGNITE = 499
    EMBOAR = 500
    OSHAWOTT = 501
    DEWOTT = 502
    SAMUROTT = 503
    SAMUROTT_HISUI = 1000
    PATRAT = 504
    WATCHOG = 505
    LILLIPUP = 506
    HERDIER = 507
    STOUTLAND = 508
    PURRLOIN = 509
    LIEPARD = 510
    PANSAGE = 511
    SIMISAGE = 512
    PANSEAR = 513
    SIMISEAR = 514
    PANPOUR = 515
    SIMIPOUR = 516
    MUNNA = 517
    MUSHARNA = 518
    PIDOVE = 519
    TRANQUILL = 520
    UNFEZANT = 521
    BLITZLE = 522
    ZEBSTRIKA = 523
    ROGGENROLA = 524
    BOLDORE = 525
    GIGALITH = 526
    WOOBAT = 527
    SWOOBAT = 528
    DRILBUR = 529
    EXCADRILL = 530
    AUDINO = 531
    AUDINO_MEGA = 951
    TIMBURR = 532
    GURDURR = 533
    CONKELDURR = 534
    TYMPOLE = 535
    PALPITOAD = 536
    SEISMITOAD = 537
    THROH = 538
    SAWK = 539
    SEWADDLE = 540
    SWADLOON = 541
    LEAVANNY = 542
    VENIPEDE = 543
    WHIRLIPEDE = 544
    SCOLIPEDE = 545
    COTTONEE = 546
    WHIMSICOTT = 547
    PETILIL = 548
    LILLIGANT = 549
    LILLIGANT_HISUI = 1001
    BASCULIN = 550
    BASCULIN_BLUE_STRIPED = 1090
    BASCULIN_WHITE_STRIPED = 1091
    SANDILE = 551
    KROKOROK = 552
    KROOKODILE = 553
    DARUMAKA = 554
    DARUMAKA_GALAR = 989
    DARMANITAN = 555
    DARMANITAN_ZEN = 1092
    DARMANITAN_GALAR = 990
    DARMANITAN_GALAR_ZEN = 1093
    MARACTUS = 556
    DWEBBLE = 557
    CRUSTLE = 558
    SCRAGGY = 559
    SCRAFTY = 560
    SIGILYPH = 561
    YAMASK = 562
    YAMASK_GALAR = 991
    COFAGRIGUS = 563
    TIRTOUGA = 564
    CARRACOSTA = 565
    ARCHEN = 566
    ARCHEOPS = 567
    TRUBBISH = 568
    GARBODOR = 569
    ZORUA = 570
    ZORUA_HISUI = 1002
    ZOROARK = 571
    ZOROARK_HISUI = 1003
    MINCCINO = 572
    CINCCINO = 573
    GOTHITA = 574
    GOTHORITA = 575
    GOTHITELLE = 576
    SOLOSIS = 577
    DUOSION = 578
    REUNICLUS = 579
    DUCKLETT = 580
    SWANNA = 581
    VANILLITE = 582
    VANILLISH = 583
    VANILLUXE = 584
    DEERLING = 585
    DEERLING_SUMMER = 1094
    DEERLING_AUTUMN = 1095
    DEERLING_WINTER = 1096
    SAWSBUCK = 586
    SAWSBUCK_SUMMER = 1097
    SAWSBUCK_AUTUMN = 1098
    SAWSBUCK_WINTER = 1099
    EMOLGA = 587
    KARRABLAST = 588
    ESCAVALIER = 589
    FOONGUS = 590
    AMOONGUSS = 591
    FRILLISH = 592
    JELLICENT = 593
    ALOMOMOLA = 594
    JOLTIK = 595
    GALVANTULA = 596
    FERROSEED = 597
    FERROTHORN = 598
    KLINK = 599
    KLANG = 600
    KLINKLANG = 601
    TYNAMO = 602
    EELEKTRIK = 603
    EELEKTROSS = 604
    ELGYEM = 605
    BEHEEYEM = 606
    LITWICK = 607
    LAMPENT = 608
    CHANDELURE = 609
    AXEW = 610
    FRAXURE = 611
    HAXORUS = 612
    CUBCHOO = 613
    BEARTIC = 614
    CRYOGONAL = 615
    SHELMET = 616
    ACCELGOR = 617
    STUNFISK = 618
    STUNFISK_GALAR = 992
    MIENFOO = 619
    MIENSHAO = 620
    DRUDDIGON = 621
    GOLETT = 622
    GOLURK = 623
    PAWNIARD = 624
    BISHARP = 625
    BOUFFALANT = 626
    RUFFLET = 627
    BRAVIARY = 628
    BRAVIARY_HISUI = 1004
    VULLABY = 629
    MANDIBUZZ = 630
    HEATMOR = 631
    DURANT = 632
    DEINO = 633
    ZWEILOUS = 634
    HYDREIGON = 635
    LARVESTA = 636
    VOLCARONA = 637
    COBALION = 638
    TERRAKION = 639
    VIRIZION = 640
    TORNADUS = 641
    TORNADUS_THERIAN = 1100
    THUNDURUS = 642
    THUNDURUS_THERIAN = 1101
    RESHIRAM = 643
    ZEKROM = 644
    LANDORUS = 645
    LANDORUS_THERIAN = 1102
    KYUREM = 646
    KYUREM_WHITE = 1104
    KYUREM_BLACK = 1105
    KELDEO = 647
    KELDEO_RESOLUTE = 1106
    MELOETTA = 648
    MELOETTA_PIROUETTE = 1107
    GENESECT = 649
    GENESECT_DOUSE = 1108
    GENESECT_SHOCK = 1109
    GENESECT_BURN = 1110
    GENESECT_CHILL = 1111
    CHESPIN = 650
    QUILLADIN = 651
    CHESNAUGHT = 652
    FENNEKIN = 653
    BRAIXEN = 654
    DELPHOX = 655
    FROAKIE = 656
    FROGADIER = 657
    GRENINJA = 658
    GRENINJA_BOND = 1112
    GRENINJA_ASH = 1113
    BUNNELBY = 659
    DIGGERSBY = 660
    FLETCHLING = 661
    FLETCHINDER = 662
    TALONFLAME = 663
    SCATTERBUG = 664
    SPEWPA = 665
    VIVILLON = 666
    VIVILLON_1 = 1114
    VIVILLON_2 = 1115
    VIVILLON_3 = 1116
    VIVILLON_4 = 1117
    VIVILLON_5 = 1118
    VIVILLON_6 = 1119
    VIVILLON_7 = 1120
    VIVILLON_8 = 1121
    VIVILLON_9 = 1122
    VIVILLON_10 = 1123
    VIVILLON_11 = 1124
    VIVILLON_12 = 1125
    VIVILLON_13 = 1126
    VIVILLON_14 = 1127
    VIVILLON_15 = 1128
    VIVILLON_16 = 1129
    VIVILLON_17 = 1130
    VIVILLON_18 = 1131
    VIVILLON_19 = 1132
    LITLEO = 667
    PYROAR = 668
    FLABE_U0301BE_U0301 = 669
    FLABE_U0301BE_U0301_1 = 1133
    FLABE_U0301BE_U0301_2 = 1134
    FLABE_U0301BE_U0301_3 = 1135
    FLABE_U0301BE_U0301_4 = 1136
    FLOETTE = 670
    FLOETTE_1 = 1137
    FLOETTE_2 = 1138
    FLOETTE_3 = 1139
    FLOETTE_4 = 1140
    FLOETTE_ETERNAL = 1141
    FLORGES = 671
    FLORGES_1 = 1142
    FLORGES_2 = 1143
    FLORGES_3 = 1144
    FLORGES_4 = 1145
    SKIDDO = 672
    GOGOAT = 673
    PANCHAM = 674
    PANGORO = 675
    FURFROU = 676
    FURFROU_1 = 1146
    FURFROU_2 = 1147
    FURFROU_3 = 1148
    FURFROU_4 = 1149
    FURFROU_5 = 1150
    FURFROU_6 = 1151
    FURFROU_7 = 1152
    FURFROU_8 = 1153
    FURFROU_9 = 1154
    ESPURR = 677
    MEOWSTIC = 678
    MEOWSTIC_F = 1155
    HONEDGE = 679
    DOUBLADE = 680
    AEGISLASH = 681
    AEGISLASH_BLADE = 1156
    SPRITZEE = 682
    AROMATISSE = 683
    SWIRLIX = 684
    SLURPUFF = 685
    INKAY = 686
    MALAMAR = 687
    BINACLE = 688
    BARBARACLE = 689
    SKRELP = 690
    DRAGALGE = 691
    CLAUNCHER = 692
    CLAWITZER = 693
    HELIOPTILE = 694
    HELIOLISK = 695
    TYRUNT = 696
    TYRANTRUM = 697
    AMAURA = 698
    AURORUS = 699
    SYLVEON = 700
    HAWLUCHA = 701
    DEDENNE = 702
    CARBINK = 703
    GOOMY = 704
    SLIGGOO = 705
    SLIGGOO_HISUI = 1005
    GOODRA = 706
    GOODRA_HISUI = 1006
    KLEFKI = 707
    PHANTUMP = 708
    TREVENANT = 709
    PUMPKABOO = 710
    PUMPKABOO_SMALL = 1157
    PUMPKABOO_LARGE = 1158
    PUMPKABOO_SUPER = 1159
    GOURGEIST = 711
    GOURGEIST_SMALL = 1160
    GOURGEIST_LARGE = 1161
    GOURGEIST_SUPER = 1162
    BERGMITE = 712
    AVALUGG = 713
    AVALUGG_HISUI = 1007
    NOIBAT = 714
    NOIVERN = 715
    XERNEAS = 716
    XERNEAS_NEUTRAL = 1163
    YVELTAL = 717
    ZYGARDE_AURA_BREAK = 718
    ZYGARDE_10_AURA_BREAK = 1164
    ZYGARDE_10 = 1165
    ZYGARDE = 1166
    ZYGARDE_COMPLETE = 1167
    DIANCIE = 719
    DIANCIE_MEGA = 952
    HOOPA = 720
    HOOPA_UNBOUND = 1168
    VOLCANION = 721
    ROWLET = 722
    DARTRIX = 723
    DECIDUEYE = 724
    DECIDUEYE_HISUI = 1008
    LITTEN = 725
    TORRACAT = 726
    INCINEROAR = 727
    POPPLIO = 728
    BRIONNE = 729
    PRIMARINA = 730
    PIKIPEK = 731
    TRUMBEAK = 732
    TOUCANNON = 733
    YUNGOOS = 734
    GUMSHOOS = 735
    GRUBBIN = 736
    CHARJABUG = 737
    VIKAVOLT = 738
    CRABRAWLER = 739
    CRABOMINABLE = 740
    ORICORIO = 741
    ORICORIO_POM_POM = 1169
    ORICORIO_PA_U = 1170
    ORICORIO_SENSU = 1171
    CUTIEFLY = 742
    RIBOMBEE = 743
    ROCKRUFF = 744
    ROCKRUFF_DUSK = 1172
    LYCANROC = 745
    LYCANROC_MIDNIGHT = 1173
    LYCANROC_DUSK = 1174
    WISHIWASHI = 746
    WISHIWASHI_SCHOOL = 1175
    MAREANIE = 747
    TOXAPEX = 748
    MUDBRAY = 749
    MUDSDALE = 750
    DEWPIDER = 751
    ARAQUANID = 752
    FOMANTIS = 753
    LURANTIS = 754
    MORELULL = 755
    SHIINOTIC = 756
    SALANDIT = 757
    SALAZZLE = 758
    STUFFUL = 759
    BEWEAR = 760
    BOUNSWEET = 761
    STEENEE = 762
    TSAREENA = 763
    COMFEY = 764
    ORANGURU = 765
    PASSIMIAN = 766
    WIMPOD = 767
    GOLISOPOD = 768
    SANDYGAST = 769
    PALOSSAND = 770
    PYUKUMUKU = 771
    TYPE_NULL = 772
    SILVALLY = 773
    SILVALLY_BUG = 1176
    SILVALLY_DARK = 1177
    SILVALLY_DRAGON = 1178
    SILVALLY_ELECTRIC = 1179
    SILVALLY_FAIRY = 1180
    SILVALLY_FIGHTING = 1181
    SILVALLY_FIRE = 1182
    SILVALLY_FLYING = 1183
    SILVALLY_GHOST = 1184
    SILVALLY_GRASS = 1185
    SILVALLY_GROUND = 1186
    SILVALLY_ICE = 1187
    SILVALLY_POISON = 1188
    SILVALLY_PSYCHIC = 1189
    SILVALLY_ROCK = 1190
    SILVALLY_STEEL = 1191
    SILVALLY_WATER = 1192
    #TODO: MINIOR has 7 colors that don't change gameplay, each with 2 battle forms that affect gameplay (14 total, 13 have IDs in range [1193, 1205]). It's not known which form each ID corresponds to, so this will need to be fixed when a MINIOR is encountered.
    MINIOR = 774
    MINIOR_METEOR = 7740001
    KOMALA = 775
    TURTONATOR = 776
    TOGEDEMARU = 777
    MIMIKYU = 778
    MIMIKYU_BUSTED = 1206
    BRUXISH = 779
    DRAMPA = 780
    DHELMISE = 781
    JANGMO_O = 782
    HAKAMO_O = 783
    KOMMO_O = 784
    TAPU_KOKO = 785
    TAPU_LELE = 786
    TAPU_BULU = 787
    TAPU_FINI = 788
    COSMOG = 789
    COSMOEM = 790
    SOLGALEO = 791
    LUNALA = 792
    NIHILEGO = 793
    BUZZWOLE = 794
    PHEROMOSA = 795
    XURKITREE = 796
    CELESTEELA = 797
    KARTANA = 798
    GUZZLORD = 799
    NECROZMA = 800
    NECROZMA_DUSK_MANE = 1207
    NECROZMA_DAWN_WINGS = 1208
    NECROZMA_ULTRA = 1209
    MAGEARNA = 801
    MAGEARNA_ORIGINAL = 1210
    MARSHADOW = 802
    POIPOLE = 803
    NAGANADEL = 804
    STAKATAKA = 805
    BLACEPHALON = 806
    ZERAORA = 807
    MELTAN = 808
    MELMETAL = 809
    GROOKEY = 810
    THWACKEY = 811
    RILLABOOM = 812
    SCORBUNNY = 813
    RABOOT = 814
    CINDERACE = 815
    SOBBLE = 816
    DRIZZILE = 817
    INTELEON = 818
    SKWOVET = 819
    GREEDENT = 820
    ROOKIDEE = 821
    CORVISQUIRE = 822
    CORVIKNIGHT = 823
    BLIPBUG = 824
    DOTTLER = 825
    ORBEETLE = 826
    NICKIT = 827
    THIEVUL = 828
    GOSSIFLEUR = 829
    ELDEGOSS = 830
    WOOLOO = 831
    DUBWOOL = 832
    CHEWTLE = 833
    DREDNAW = 834
    YAMPER = 835
    BOLTUND = 836
    ROLYCOLY = 837
    CARKOL = 838
    COALOSSAL = 839
    APPLIN = 840
    FLAPPLE = 841
    APPLETUN = 842
    SILICOBRA = 843
    SANDACONDA = 844
    CRAMORANT = 845
    CRAMORANT_GULPING = 1211
    CRAMORANT_GORGING = 1212
    ARROKUDA = 846
    BARRASKEWDA = 847
    TOXEL = 848
    TOXTRICITY = 849
    TOXTRICITY_LOW_KEY = 1213
    SIZZLIPEDE = 850
    CENTISKORCH = 851
    CLOBBOPUS = 852
    GRAPPLOCT = 853
    SINISTEA = 854
    SINISTEA_ANTIQUE = 1214
    POLTEAGEIST = 855
    POLTEAGEIST_ANTIQUE = 1215
    HATENNA = 856
    HATTREM = 857
    HATTERENE = 858
    IMPIDIMP = 859
    MORGREM = 860
    GRIMMSNARL = 861
    OBSTAGOON = 862
    PERRSERKER = 863
    CURSOLA = 864
    SIRFETCH_U2019D = 865
    MR_RIME = 866
    RUNERIGUS = 867
    MILCERY = 868
    ALCREMIE = 869
    ALCREMIE_1 = 1216
    ALCREMIE_2 = 1217
    ALCREMIE_3 = 1218
    ALCREMIE_4 = 1219
    ALCREMIE_5 = 1220
    ALCREMIE_6 = 1221
    ALCREMIE_7 = 1222
    ALCREMIE_8 = 1223
    FALINKS = 870
    PINCURCHIN = 871
    SNOM = 872
    FROSMOTH = 873
    STONJOURNER = 874
    EISCUE = 875
    EISCUE_NOICE = 1224
    INDEEDEE = 876
    INDEEDEE_F = 1225
    MORPEKO = 877
    MORPEKO_HANGRY = 1226
    CUFANT = 878
    COPPERAJAH = 879
    DRACOZOLT = 880
    ARCTOZOLT = 881
    DRACOVISH = 882
    ARCTOVISH = 883
    DURALUDON = 884
    DREEPY = 885
    DRAKLOAK = 886
    DRAGAPULT = 887
    ZACIAN = 888
    ZACIAN_CROWNED = 1227
    ZAMAZENTA = 889
    ZAMAZENTA_CROWNED = 1228
    ETERNATUS = 890
    ETERNATUS_ETERNAMAX = 1229
    KUBFU = 891
    URSHIFU = 892
    URSHIFU_RAPID_STRIKE = 1230
    ZARUDE = 893
    ZARUDE_DADA = 1231
    REGIELEKI = 894
    REGIDRAGO = 895
    GLASTRIER = 896
    SPECTRIER = 897
    CALYREX = 898
    CALYREX_ICE = 1232
    CALYREX_SHADOW = 1233
    WYRDEER = 899
    KLEAVOR = 900
    URSALUNA = 901
    BASCULEGION = 902
    SNEASLER = 903
    OVERQWIL = 904
    ENAMORUS = 905
    ENAMORUS_THERIAN = 1103


@dataclass(frozen=True)
class SpeciesData:
    types: tuple  # tuple of Type values, length 1 or 2
    base_hp: int
    base_atk: int
    base_def: int
    base_spa: int
    base_spd: int
    base_spe: int
    male_ratio: Optional[float]  # None = genderless; 0.0-1.0 otherwise
    weight_kg: float = 0.0       # body weight in kg; used by Low Kick, Grass Knot, Heavy Slam, Heat Crash
    growth_rate: GrowthRate = GrowthRate.MEDIUM_FAST  # EXP growth curve
    exp_yield: int = 0                               # base EXP awarded when defeated


SPECIES_DATA: dict[Species, SpeciesData] = {
    Species.BULBASAUR: SpeciesData((Type.GRASS, Type.POISON), 45, 49, 49, 65, 65, 45, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=64),
    Species.IVYSAUR: SpeciesData((Type.GRASS, Type.POISON), 60, 62, 63, 80, 80, 60, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.VENUSAUR: SpeciesData((Type.GRASS, Type.POISON), 80, 82, 83, 100, 100, 80, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=263),
    Species.VENUSAUR_MEGA: SpeciesData((Type.GRASS, Type.POISON), 80, 100, 123, 122, 120, 80, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=313),
    Species.CHARMANDER: SpeciesData((Type.FIRE,), 39, 52, 43, 60, 50, 65, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.CHARMELEON: SpeciesData((Type.FIRE,), 58, 64, 58, 80, 65, 80, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.CHARIZARD: SpeciesData((Type.FIRE, Type.FLYING), 78, 84, 78, 109, 85, 100, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=267),
    Species.CHARIZARD_MEGA_X: SpeciesData((Type.FIRE, Type.DRAGON), 78, 130, 111, 130, 85, 100, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=317),
    Species.CHARIZARD_MEGA_Y: SpeciesData((Type.FIRE, Type.FLYING), 78, 104, 78, 159, 115, 100, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=317),
    Species.SQUIRTLE: SpeciesData((Type.WATER,), 44, 48, 65, 50, 64, 43, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=63),
    Species.WARTORTLE: SpeciesData((Type.WATER,), 59, 63, 80, 65, 80, 58, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.BLASTOISE: SpeciesData((Type.WATER,), 79, 83, 100, 85, 105, 78, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.BLASTOISE_MEGA: SpeciesData((Type.WATER,), 79, 103, 120, 135, 115, 78, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=315),
    Species.CATERPIE: SpeciesData((Type.BUG,), 45, 30, 35, 20, 20, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=39),
    Species.METAPOD: SpeciesData((Type.BUG,), 50, 20, 55, 25, 25, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=72),
    Species.BUTTERFREE: SpeciesData((Type.BUG, Type.FLYING), 60, 45, 50, 90, 80, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=198),
    Species.WEEDLE: SpeciesData((Type.BUG, Type.POISON), 40, 35, 30, 20, 20, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=39),
    Species.KAKUNA: SpeciesData((Type.BUG, Type.POISON), 45, 25, 50, 25, 25, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=72),
    Species.BEEDRILL: SpeciesData((Type.BUG, Type.POISON), 65, 90, 40, 45, 80, 75, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=198),
    Species.BEEDRILL_MEGA: SpeciesData((Type.BUG, Type.POISON), 65, 150, 40, 15, 80, 145, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=248),
    Species.PIDGEY: SpeciesData((Type.NORMAL, Type.FLYING), 40, 45, 40, 35, 35, 56, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=50),
    Species.PIDGEOTTO: SpeciesData((Type.NORMAL, Type.FLYING), 63, 60, 55, 50, 50, 71, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=122),
    Species.PIDGEOT: SpeciesData((Type.NORMAL, Type.FLYING), 83, 80, 75, 70, 70, 101, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=240),
    Species.PIDGEOT_MEGA: SpeciesData((Type.NORMAL, Type.FLYING), 83, 80, 80, 135, 80, 121, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=290),
    Species.RATTATA: SpeciesData((Type.NORMAL,), 30, 56, 35, 25, 35, 72, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=51),
    Species.RATTATA_ALOLA: SpeciesData((Type.DARK, Type.NORMAL), 30, 56, 35, 25, 35, 72, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=51),
    Species.RATICATE: SpeciesData((Type.NORMAL,), 55, 81, 60, 50, 70, 97, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=145),
    Species.RATICATE_ALOLA: SpeciesData((Type.DARK, Type.NORMAL), 75, 71, 70, 40, 80, 77, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=145),
    Species.SPEAROW: SpeciesData((Type.NORMAL, Type.FLYING), 40, 60, 30, 31, 31, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=52),
    Species.FEAROW: SpeciesData((Type.NORMAL, Type.FLYING), 65, 90, 65, 61, 61, 100, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=155),
    Species.EKANS: SpeciesData((Type.POISON,), 35, 60, 44, 40, 54, 55, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=58),
    Species.ARBOK: SpeciesData((Type.POISON,), 60, 95, 69, 65, 79, 80, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=157),
    Species.PIKACHU: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.PIKACHU_COSPLAY: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.PIKACHU_ROCK_STAR: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.PIKACHU_BELLE: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.PIKACHU_POP_STAR: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.PIKACHU_PHD: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.PIKACHU_LIBRE: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.PIKACHU_ORIGINAL: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.PIKACHU_HOENN: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.PIKACHU_SINNOH: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.PIKACHU_UNOVA: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.PIKACHU_KALOS: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.PIKACHU_ALOLA: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.PIKACHU_PARTNER: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=151),
    Species.PIKACHU_WORLD: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 50, 50, 90, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=112),
    Species.RAICHU: SpeciesData((Type.ELECTRIC,), 60, 90, 55, 90, 80, 110, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=243),
    Species.RAICHU_ALOLA: SpeciesData((Type.ELECTRIC, Type.PSYCHIC), 60, 85, 50, 95, 85, 110, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=243),
    Species.SANDSHREW: SpeciesData((Type.GROUND,), 50, 75, 85, 20, 30, 40, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=60),
    Species.SANDSHREW_ALOLA: SpeciesData((Type.ICE, Type.STEEL), 50, 75, 90, 10, 35, 40, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=60),
    Species.SANDSLASH: SpeciesData((Type.GROUND,), 75, 100, 110, 45, 55, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=158),
    Species.SANDSLASH_ALOLA: SpeciesData((Type.ICE, Type.STEEL), 75, 100, 120, 25, 65, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=158),
    Species.NIDORAN_F: SpeciesData((Type.POISON,), 55, 47, 52, 40, 40, 41, 0.0, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=55),
    Species.NIDORINA: SpeciesData((Type.POISON,), 70, 62, 67, 55, 55, 56, 0.0, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=128),
    Species.NIDOQUEEN: SpeciesData((Type.POISON, Type.GROUND), 90, 92, 87, 75, 85, 76, 0.0, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=253),
    Species.NIDORAN_M: SpeciesData((Type.POISON,), 46, 57, 40, 40, 40, 50, 1.0, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=55),
    Species.NIDORINO: SpeciesData((Type.POISON,), 61, 72, 57, 55, 55, 65, 1.0, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=128),
    Species.NIDOKING: SpeciesData((Type.POISON, Type.GROUND), 81, 102, 77, 85, 75, 85, 1.0, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=253),
    Species.CLEFAIRY: SpeciesData((Type.FAIRY,), 70, 45, 48, 60, 65, 35, 0.25, growth_rate=GrowthRate.FAST, exp_yield=113),
    Species.CLEFABLE: SpeciesData((Type.FAIRY,), 95, 70, 73, 95, 90, 60, 0.25, growth_rate=GrowthRate.FAST, exp_yield=242),
    Species.VULPIX: SpeciesData((Type.FIRE,), 38, 41, 40, 50, 65, 65, 0.25, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=60),
    Species.VULPIX_ALOLA: SpeciesData((Type.ICE,), 38, 41, 40, 50, 65, 65, 0.25, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=60),
    Species.NINETALES: SpeciesData((Type.FIRE,), 73, 76, 75, 81, 100, 100, 0.25, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=177),
    Species.NINETALES_ALOLA: SpeciesData((Type.ICE, Type.FAIRY), 73, 67, 75, 81, 100, 109, 0.25, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=177),
    Species.JIGGLYPUFF: SpeciesData((Type.NORMAL, Type.FAIRY), 115, 45, 20, 45, 25, 20, 0.25, growth_rate=GrowthRate.FAST, exp_yield=95),
    Species.WIGGLYTUFF: SpeciesData((Type.NORMAL, Type.FAIRY), 140, 70, 45, 85, 50, 45, 0.25, growth_rate=GrowthRate.FAST, exp_yield=218),
    Species.ZUBAT: SpeciesData((Type.POISON, Type.FLYING), 40, 45, 35, 30, 40, 55, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=49),
    Species.GOLBAT: SpeciesData((Type.POISON, Type.FLYING), 75, 80, 70, 65, 75, 90, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=159),
    Species.ODDISH: SpeciesData((Type.GRASS, Type.POISON), 45, 50, 55, 75, 65, 30, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=64),
    Species.GLOOM: SpeciesData((Type.GRASS, Type.POISON), 60, 65, 70, 85, 75, 40, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=138),
    Species.VILEPLUME: SpeciesData((Type.GRASS, Type.POISON), 75, 80, 85, 110, 90, 50, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=245),
    Species.PARAS: SpeciesData((Type.BUG, Type.GRASS), 35, 70, 55, 45, 55, 25, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=57),
    Species.PARASECT: SpeciesData((Type.BUG, Type.GRASS), 60, 95, 80, 60, 80, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=142),
    Species.VENONAT: SpeciesData((Type.BUG, Type.POISON), 60, 55, 50, 40, 55, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.VENOMOTH: SpeciesData((Type.BUG, Type.POISON), 70, 65, 60, 90, 75, 90, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=158),
    Species.DIGLETT: SpeciesData((Type.GROUND,), 10, 55, 25, 35, 45, 95, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=53),
    Species.DIGLETT_ALOLA: SpeciesData((Type.GROUND, Type.STEEL), 10, 55, 30, 35, 45, 90, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=53),
    Species.DUGTRIO: SpeciesData((Type.GROUND,), 35, 100, 50, 50, 70, 120, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=149),
    Species.DUGTRIO_ALOLA: SpeciesData((Type.GROUND, Type.STEEL), 35, 100, 60, 50, 70, 110, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=149),
    Species.MEOWTH: SpeciesData((Type.NORMAL,), 40, 45, 35, 40, 40, 90, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=58),
    Species.MEOWTH_ALOLA: SpeciesData((Type.DARK,), 40, 35, 35, 50, 40, 90, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=58),
    Species.MEOWTH_GALAR: SpeciesData((Type.STEEL,), 50, 65, 55, 40, 40, 40, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=58),
    Species.PERSIAN: SpeciesData((Type.NORMAL,), 65, 70, 60, 65, 65, 115, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=154),
    Species.PERSIAN_ALOLA: SpeciesData((Type.DARK,), 65, 60, 60, 75, 65, 115, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=154),
    Species.PSYDUCK: SpeciesData((Type.WATER,), 50, 52, 48, 65, 50, 55, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=64),
    Species.GOLDUCK: SpeciesData((Type.WATER,), 80, 82, 78, 95, 80, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.MANKEY: SpeciesData((Type.FIGHTING,), 40, 80, 35, 35, 45, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.PRIMEAPE: SpeciesData((Type.FIGHTING,), 65, 105, 60, 60, 70, 95, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=159),
    Species.GROWLITHE: SpeciesData((Type.FIRE,), 55, 70, 45, 70, 50, 60, 0.75, growth_rate=GrowthRate.SLOW, exp_yield=70),
    Species.GROWLITHE_HISUI: SpeciesData((Type.FIRE, Type.ROCK), 60, 75, 45, 65, 50, 55, 0.75, growth_rate=GrowthRate.SLOW, exp_yield=70),
    Species.ARCANINE: SpeciesData((Type.FIRE,), 90, 110, 80, 100, 80, 95, 0.75, growth_rate=GrowthRate.SLOW, exp_yield=194),
    Species.ARCANINE_HISUI: SpeciesData((Type.FIRE, Type.ROCK), 95, 115, 80, 95, 80, 90, 0.75, growth_rate=GrowthRate.SLOW, exp_yield=194),
    Species.POLIWAG: SpeciesData((Type.WATER,), 40, 50, 40, 40, 40, 90, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=60),
    Species.POLIWHIRL: SpeciesData((Type.WATER,), 65, 65, 65, 50, 50, 90, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=135),
    Species.POLIWRATH: SpeciesData((Type.WATER, Type.FIGHTING), 90, 95, 95, 70, 90, 70, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=255),
    Species.ABRA: SpeciesData((Type.PSYCHIC,), 25, 20, 15, 105, 55, 90, 0.75, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.KADABRA: SpeciesData((Type.PSYCHIC,), 40, 35, 30, 120, 70, 105, 0.75, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=140),
    Species.ALAKAZAM: SpeciesData((Type.PSYCHIC,), 55, 50, 45, 135, 95, 120, 0.75, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=250),
    Species.ALAKAZAM_MEGA: SpeciesData((Type.PSYCHIC,), 55, 50, 65, 175, 105, 150, 0.75, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=300),
    Species.MACHOP: SpeciesData((Type.FIGHTING,), 70, 80, 50, 35, 35, 35, 0.75, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=61),
    Species.MACHOKE: SpeciesData((Type.FIGHTING,), 80, 100, 70, 50, 60, 45, 0.75, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.MACHAMP: SpeciesData((Type.FIGHTING,), 90, 130, 80, 65, 85, 55, 0.75, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=253),
    Species.BELLSPROUT: SpeciesData((Type.GRASS, Type.POISON), 50, 75, 35, 70, 30, 40, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=60),
    Species.WEEPINBELL: SpeciesData((Type.GRASS, Type.POISON), 65, 90, 50, 85, 45, 55, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=137),
    Species.VICTREEBEL: SpeciesData((Type.GRASS, Type.POISON), 80, 105, 65, 100, 70, 70, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=245),
    Species.TENTACOOL: SpeciesData((Type.WATER, Type.POISON), 40, 40, 35, 50, 100, 70, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=67),
    Species.TENTACRUEL: SpeciesData((Type.WATER, Type.POISON), 80, 70, 65, 80, 120, 100, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=180),
    Species.GEODUDE: SpeciesData((Type.ROCK, Type.GROUND), 40, 80, 100, 30, 30, 20, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=60),
    Species.GEODUDE_ALOLA: SpeciesData((Type.ROCK, Type.ELECTRIC), 40, 80, 100, 30, 30, 20, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=60),
    Species.GRAVELER: SpeciesData((Type.ROCK, Type.GROUND), 55, 95, 115, 45, 45, 35, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=137),
    Species.GRAVELER_ALOLA: SpeciesData((Type.ROCK, Type.ELECTRIC), 55, 95, 115, 45, 45, 35, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=137),
    Species.GOLEM: SpeciesData((Type.ROCK, Type.GROUND), 80, 120, 130, 55, 65, 45, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=248),
    Species.GOLEM_ALOLA: SpeciesData((Type.ROCK, Type.ELECTRIC), 80, 120, 130, 55, 65, 45, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=248),
    Species.PONYTA: SpeciesData((Type.FIRE,), 50, 85, 55, 65, 65, 90, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=82),
    Species.PONYTA_GALAR: SpeciesData((Type.PSYCHIC,), 50, 85, 55, 65, 65, 90, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=82),
    Species.RAPIDASH: SpeciesData((Type.FIRE,), 65, 100, 70, 80, 80, 105, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.RAPIDASH_GALAR: SpeciesData((Type.PSYCHIC, Type.FAIRY), 65, 100, 70, 80, 80, 105, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.SLOWPOKE: SpeciesData((Type.WATER, Type.PSYCHIC), 90, 65, 65, 40, 40, 15, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=63),
    Species.SLOWPOKE_GALAR: SpeciesData((Type.PSYCHIC,), 90, 65, 65, 40, 40, 15, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=63),
    Species.SLOWBRO: SpeciesData((Type.WATER, Type.PSYCHIC), 95, 75, 110, 100, 80, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.SLOWBRO_MEGA: SpeciesData((Type.WATER, Type.PSYCHIC), 95, 75, 180, 130, 80, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=207),
    Species.SLOWBRO_GALAR: SpeciesData((Type.POISON, Type.PSYCHIC), 95, 100, 95, 100, 70, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.MAGNEMITE: SpeciesData((Type.ELECTRIC, Type.STEEL), 25, 35, 70, 95, 55, 45, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=65),
    Species.MAGNETON: SpeciesData((Type.ELECTRIC, Type.STEEL), 50, 60, 95, 120, 70, 70, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=163),
    Species.FARFETCH_U2019D: SpeciesData((Type.NORMAL, Type.FLYING), 52, 90, 55, 58, 62, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=132),
    Species.FARFETCH_U2019D_GALAR: SpeciesData((Type.FIGHTING,), 52, 95, 55, 58, 62, 55, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=132),
    Species.DODUO: SpeciesData((Type.NORMAL, Type.FLYING), 35, 85, 45, 35, 35, 75, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=62),
    Species.DODRIO: SpeciesData((Type.NORMAL, Type.FLYING), 60, 110, 70, 60, 60, 110, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.SEEL: SpeciesData((Type.WATER,), 65, 45, 55, 45, 70, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=65),
    Species.DEWGONG: SpeciesData((Type.WATER, Type.ICE), 90, 70, 80, 70, 95, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.GRIMER: SpeciesData((Type.POISON,), 80, 80, 50, 40, 50, 25, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=65),
    Species.GRIMER_ALOLA: SpeciesData((Type.POISON, Type.DARK), 80, 80, 50, 40, 50, 25, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=65),
    Species.MUK: SpeciesData((Type.POISON,), 105, 105, 75, 65, 100, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.MUK_ALOLA: SpeciesData((Type.POISON, Type.DARK), 105, 105, 75, 65, 100, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.SHELLDER: SpeciesData((Type.WATER,), 30, 65, 100, 45, 25, 40, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=61),
    Species.CLOYSTER: SpeciesData((Type.WATER, Type.ICE), 50, 95, 180, 85, 45, 70, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=184),
    Species.GASTLY: SpeciesData((Type.GHOST, Type.POISON), 30, 35, 30, 100, 35, 80, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.HAUNTER: SpeciesData((Type.GHOST, Type.POISON), 45, 50, 45, 115, 55, 95, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.GENGAR: SpeciesData((Type.GHOST, Type.POISON), 60, 65, 60, 130, 75, 110, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=250),
    Species.GENGAR_MEGA: SpeciesData((Type.GHOST, Type.POISON), 60, 65, 80, 170, 95, 130, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=300),
    Species.ONIX: SpeciesData((Type.ROCK, Type.GROUND), 35, 45, 160, 30, 45, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=77),
    Species.DROWZEE: SpeciesData((Type.PSYCHIC,), 60, 48, 45, 43, 90, 42, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=66),
    Species.HYPNO: SpeciesData((Type.PSYCHIC,), 85, 73, 70, 73, 115, 67, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=169),
    Species.KRABBY: SpeciesData((Type.WATER,), 30, 105, 90, 25, 25, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=65),
    Species.KINGLER: SpeciesData((Type.WATER,), 55, 130, 115, 50, 50, 75, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.VOLTORB: SpeciesData((Type.ELECTRIC,), 40, 30, 50, 55, 55, 100, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=66),
    Species.VOLTORB_HISUI: SpeciesData((Type.ELECTRIC, Type.GRASS), 40, 30, 50, 55, 55, 100, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=66),
    Species.ELECTRODE: SpeciesData((Type.ELECTRIC,), 60, 50, 70, 80, 80, 150, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.ELECTRODE_HISUI: SpeciesData((Type.ELECTRIC, Type.GRASS), 60, 50, 70, 80, 80, 150, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.EXEGGCUTE: SpeciesData((Type.GRASS, Type.PSYCHIC), 60, 40, 80, 60, 45, 40, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=65),
    Species.EXEGGUTOR: SpeciesData((Type.GRASS, Type.PSYCHIC), 95, 95, 85, 125, 75, 55, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=186),
    Species.EXEGGUTOR_ALOLA: SpeciesData((Type.GRASS, Type.DRAGON), 95, 105, 85, 125, 75, 45, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=186),
    Species.CUBONE: SpeciesData((Type.GROUND,), 50, 50, 95, 40, 50, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=64),
    Species.MAROWAK: SpeciesData((Type.GROUND,), 60, 80, 110, 50, 80, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=149),
    Species.MAROWAK_ALOLA: SpeciesData((Type.FIRE, Type.GHOST), 60, 80, 110, 50, 80, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=149),
    Species.HITMONLEE: SpeciesData((Type.FIGHTING,), 50, 120, 53, 35, 110, 87, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=159),
    Species.HITMONCHAN: SpeciesData((Type.FIGHTING,), 50, 105, 79, 35, 110, 76, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=159),
    Species.LICKITUNG: SpeciesData((Type.NORMAL,), 90, 55, 75, 60, 75, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=77),
    Species.KOFFING: SpeciesData((Type.POISON,), 40, 65, 95, 60, 45, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=68),
    Species.WEEZING: SpeciesData((Type.POISON,), 65, 90, 120, 85, 70, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.WEEZING_GALAR: SpeciesData((Type.POISON, Type.FAIRY), 65, 90, 120, 85, 70, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.RHYHORN: SpeciesData((Type.GROUND, Type.ROCK), 80, 85, 95, 30, 30, 25, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=69),
    Species.RHYDON: SpeciesData((Type.GROUND, Type.ROCK), 105, 130, 120, 45, 45, 40, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=170),
    Species.CHANSEY: SpeciesData((Type.NORMAL,), 250, 5, 5, 35, 105, 50, 0.0, growth_rate=GrowthRate.FAST, exp_yield=395),
    Species.TANGELA: SpeciesData((Type.GRASS,), 65, 55, 115, 100, 40, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=87),
    Species.KANGASKHAN: SpeciesData((Type.NORMAL,), 105, 95, 80, 40, 80, 90, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.KANGASKHAN_MEGA: SpeciesData((Type.NORMAL,), 105, 125, 100, 60, 100, 100, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=207),
    Species.HORSEA: SpeciesData((Type.WATER,), 30, 40, 70, 70, 25, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=59),
    Species.SEADRA: SpeciesData((Type.WATER,), 55, 65, 95, 95, 45, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=154),
    Species.GOLDEEN: SpeciesData((Type.WATER,), 45, 67, 60, 35, 50, 63, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=64),
    Species.SEAKING: SpeciesData((Type.WATER,), 80, 92, 65, 65, 80, 68, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=158),
    Species.STARYU: SpeciesData((Type.WATER,), 30, 45, 55, 70, 55, 85, None, growth_rate=GrowthRate.SLOW, exp_yield=68),
    Species.STARMIE: SpeciesData((Type.WATER, Type.PSYCHIC), 60, 75, 85, 100, 85, 115, None, growth_rate=GrowthRate.SLOW, exp_yield=182),
    Species.MR_MIME: SpeciesData((Type.PSYCHIC, Type.FAIRY), 40, 45, 65, 100, 120, 90, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=161),
    Species.MR_MIME_GALAR: SpeciesData((Type.ICE, Type.PSYCHIC), 50, 65, 65, 90, 90, 100, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=161),
    Species.SCYTHER: SpeciesData((Type.BUG, Type.FLYING), 70, 110, 80, 55, 80, 105, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=100),
    Species.JYNX: SpeciesData((Type.ICE, Type.PSYCHIC), 65, 50, 35, 115, 95, 95, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=159),
    Species.ELECTABUZZ: SpeciesData((Type.ELECTRIC,), 65, 83, 57, 95, 85, 105, 0.75, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.MAGMAR: SpeciesData((Type.FIRE,), 65, 95, 57, 100, 85, 93, 0.75, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.PINSIR: SpeciesData((Type.BUG,), 65, 125, 100, 55, 70, 85, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=175),
    Species.PINSIR_MEGA: SpeciesData((Type.BUG, Type.FLYING), 65, 155, 120, 65, 90, 105, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=210),
    Species.TAUROS: SpeciesData((Type.NORMAL,), 75, 100, 95, 40, 70, 110, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=172),
    Species.MAGIKARP: SpeciesData((Type.WATER,), 20, 10, 55, 15, 20, 80, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=40),
    Species.GYARADOS: SpeciesData((Type.WATER, Type.FLYING), 95, 125, 79, 60, 100, 81, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=189),
    Species.GYARADOS_MEGA: SpeciesData((Type.WATER, Type.DARK), 95, 155, 109, 70, 130, 81, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=224),
    Species.LAPRAS: SpeciesData((Type.WATER, Type.ICE), 130, 85, 80, 85, 95, 60, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=187),
    Species.DITTO: SpeciesData((Type.NORMAL,), 48, 48, 48, 48, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=101),
    Species.EEVEE: SpeciesData((Type.NORMAL,), 55, 55, 50, 45, 65, 55, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=87),
    Species.VAPOREON: SpeciesData((Type.WATER,), 130, 65, 60, 110, 95, 65, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=184),
    Species.JOLTEON: SpeciesData((Type.ELECTRIC,), 65, 65, 60, 110, 95, 130, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=184),
    Species.FLAREON: SpeciesData((Type.FIRE,), 65, 130, 60, 95, 110, 65, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=184),
    Species.PORYGON: SpeciesData((Type.NORMAL,), 65, 60, 70, 85, 75, 40, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=79),
    Species.OMANYTE: SpeciesData((Type.ROCK, Type.WATER), 35, 40, 100, 90, 55, 35, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=71),
    Species.OMASTAR: SpeciesData((Type.ROCK, Type.WATER), 70, 60, 125, 115, 70, 55, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.KABUTO: SpeciesData((Type.ROCK, Type.WATER), 30, 80, 90, 55, 45, 55, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=71),
    Species.KABUTOPS: SpeciesData((Type.ROCK, Type.WATER), 60, 115, 105, 65, 70, 80, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.AERODACTYL: SpeciesData((Type.ROCK, Type.FLYING), 80, 105, 65, 60, 75, 130, 0.875, growth_rate=GrowthRate.SLOW, exp_yield=180),
    Species.AERODACTYL_MEGA: SpeciesData((Type.ROCK, Type.FLYING), 80, 135, 85, 70, 95, 150, 0.875, growth_rate=GrowthRate.SLOW, exp_yield=215),
    Species.SNORLAX: SpeciesData((Type.NORMAL,), 160, 110, 65, 65, 110, 30, 0.875, growth_rate=GrowthRate.SLOW, exp_yield=189),
    Species.ARTICUNO: SpeciesData((Type.ICE, Type.FLYING), 90, 85, 100, 95, 125, 85, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.ARTICUNO_GALAR: SpeciesData((Type.PSYCHIC, Type.FLYING), 90, 85, 85, 125, 100, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.ZAPDOS: SpeciesData((Type.ELECTRIC, Type.FLYING), 90, 90, 85, 125, 90, 100, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.ZAPDOS_GALAR: SpeciesData((Type.FIGHTING, Type.FLYING), 90, 125, 90, 85, 90, 100, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.MOLTRES: SpeciesData((Type.FIRE, Type.FLYING), 90, 100, 90, 125, 85, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.MOLTRES_GALAR: SpeciesData((Type.DARK, Type.FLYING), 90, 85, 90, 100, 125, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.DRATINI: SpeciesData((Type.DRAGON,), 41, 64, 45, 50, 50, 50, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=60),
    Species.DRAGONAIR: SpeciesData((Type.DRAGON,), 61, 84, 65, 70, 70, 70, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=147),
    Species.DRAGONITE: SpeciesData((Type.DRAGON, Type.FLYING), 91, 134, 95, 100, 100, 80, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.MEWTWO: SpeciesData((Type.PSYCHIC,), 106, 110, 90, 154, 90, 130, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.MEWTWO_MEGA_X: SpeciesData((Type.PSYCHIC, Type.FIGHTING), 106, 190, 100, 154, 100, 130, None, growth_rate=GrowthRate.SLOW, exp_yield=390),
    Species.MEWTWO_MEGA_Y: SpeciesData((Type.PSYCHIC,), 106, 150, 70, 194, 120, 140, None, growth_rate=GrowthRate.SLOW, exp_yield=390),
    Species.MEW: SpeciesData((Type.PSYCHIC,), 100, 100, 100, 100, 100, 100, None, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=300),
    Species.CHIKORITA: SpeciesData((Type.GRASS,), 45, 49, 65, 49, 65, 45, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=64),
    Species.BAYLEEF: SpeciesData((Type.GRASS,), 60, 62, 80, 63, 80, 60, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.MEGANIUM: SpeciesData((Type.GRASS,), 80, 82, 100, 83, 100, 80, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=263),
    Species.CYNDAQUIL: SpeciesData((Type.FIRE,), 39, 52, 43, 60, 50, 65, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.QUILAVA: SpeciesData((Type.FIRE,), 58, 64, 58, 80, 65, 80, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.TYPHLOSION: SpeciesData((Type.FIRE,), 78, 84, 78, 109, 85, 100, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=267),
    Species.TYPHLOSION_HISUI: SpeciesData((Type.FIRE, Type.GHOST), 73, 84, 78, 119, 85, 95, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=267),
    Species.TOTODILE: SpeciesData((Type.WATER,), 50, 65, 64, 44, 48, 43, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=63),
    Species.CROCONAW: SpeciesData((Type.WATER,), 65, 80, 80, 59, 63, 58, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.FERALIGATR: SpeciesData((Type.WATER,), 85, 105, 100, 79, 83, 78, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.SENTRET: SpeciesData((Type.NORMAL,), 35, 46, 34, 35, 45, 20, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=43),
    Species.FURRET: SpeciesData((Type.NORMAL,), 85, 76, 64, 45, 55, 90, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=145),
    Species.HOOTHOOT: SpeciesData((Type.NORMAL, Type.FLYING), 60, 30, 30, 36, 56, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=52),
    Species.NOCTOWL: SpeciesData((Type.NORMAL, Type.FLYING), 100, 50, 50, 86, 96, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=158),
    Species.LEDYBA: SpeciesData((Type.BUG, Type.FLYING), 40, 20, 30, 40, 80, 55, 0.5, growth_rate=GrowthRate.FAST, exp_yield=53),
    Species.LEDIAN: SpeciesData((Type.BUG, Type.FLYING), 55, 35, 50, 55, 110, 85, 0.5, growth_rate=GrowthRate.FAST, exp_yield=137),
    Species.SPINARAK: SpeciesData((Type.BUG, Type.POISON), 40, 60, 40, 40, 40, 30, 0.5, growth_rate=GrowthRate.FAST, exp_yield=50),
    Species.ARIADOS: SpeciesData((Type.BUG, Type.POISON), 70, 90, 70, 60, 70, 40, 0.5, growth_rate=GrowthRate.FAST, exp_yield=140),
    Species.CROBAT: SpeciesData((Type.POISON, Type.FLYING), 85, 90, 80, 70, 80, 130, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=268),
    Species.CHINCHOU: SpeciesData((Type.WATER, Type.ELECTRIC), 75, 38, 38, 56, 56, 67, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=66),
    Species.LANTURN: SpeciesData((Type.WATER, Type.ELECTRIC), 125, 58, 58, 76, 76, 67, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=161),
    Species.PICHU: SpeciesData((Type.ELECTRIC,), 20, 40, 15, 35, 35, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=41),
    Species.PICHU_SPIKY_EARED: SpeciesData((Type.ELECTRIC,), 20, 40, 15, 35, 35, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=41),
    Species.CLEFFA: SpeciesData((Type.FAIRY,), 50, 25, 28, 45, 55, 15, 0.25, growth_rate=GrowthRate.FAST, exp_yield=44),
    Species.IGGLYBUFF: SpeciesData((Type.NORMAL, Type.FAIRY), 90, 30, 15, 40, 20, 15, 0.25, growth_rate=GrowthRate.FAST, exp_yield=42),
    Species.TOGEPI: SpeciesData((Type.FAIRY,), 35, 20, 65, 40, 65, 20, 0.875, growth_rate=GrowthRate.FAST, exp_yield=49),
    Species.TOGETIC: SpeciesData((Type.FAIRY, Type.FLYING), 55, 40, 85, 80, 105, 40, 0.875, growth_rate=GrowthRate.FAST, exp_yield=142),
    Species.NATU: SpeciesData((Type.PSYCHIC, Type.FLYING), 40, 50, 45, 70, 45, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=64),
    Species.XATU: SpeciesData((Type.PSYCHIC, Type.FLYING), 65, 75, 70, 95, 70, 95, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.MAREEP: SpeciesData((Type.ELECTRIC,), 55, 40, 40, 65, 45, 35, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=56),
    Species.FLAAFFY: SpeciesData((Type.ELECTRIC,), 70, 55, 55, 80, 60, 45, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=128),
    Species.AMPHAROS: SpeciesData((Type.ELECTRIC,), 90, 75, 85, 115, 90, 55, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=255),
    Species.AMPHAROS_MEGA: SpeciesData((Type.ELECTRIC, Type.DRAGON), 90, 95, 105, 165, 110, 45, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=305),
    Species.BELLOSSOM: SpeciesData((Type.GRASS,), 75, 80, 95, 90, 100, 50, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=245),
    Species.MARILL: SpeciesData((Type.WATER, Type.FAIRY), 70, 20, 50, 20, 50, 40, 0.5, growth_rate=GrowthRate.FAST, exp_yield=88),
    Species.AZUMARILL: SpeciesData((Type.WATER, Type.FAIRY), 100, 50, 80, 60, 80, 50, 0.5, growth_rate=GrowthRate.FAST, exp_yield=210),
    Species.SUDOWOODO: SpeciesData((Type.ROCK,), 70, 100, 115, 30, 65, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=144),
    Species.POLITOED: SpeciesData((Type.WATER,), 90, 75, 75, 90, 100, 70, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=250),
    Species.HOPPIP: SpeciesData((Type.GRASS, Type.FLYING), 35, 35, 40, 35, 55, 50, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=50),
    Species.SKIPLOOM: SpeciesData((Type.GRASS, Type.FLYING), 55, 45, 50, 45, 65, 80, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=119),
    Species.JUMPLUFF: SpeciesData((Type.GRASS, Type.FLYING), 75, 55, 70, 55, 95, 110, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=230),
    Species.AIPOM: SpeciesData((Type.NORMAL,), 55, 70, 55, 40, 55, 85, 0.5, growth_rate=GrowthRate.FAST, exp_yield=72),
    Species.SUNKERN: SpeciesData((Type.GRASS,), 30, 30, 30, 30, 30, 30, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=36),
    Species.SUNFLORA: SpeciesData((Type.GRASS,), 75, 75, 55, 105, 85, 30, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=149),
    Species.YANMA: SpeciesData((Type.BUG, Type.FLYING), 65, 65, 45, 75, 45, 95, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=78),
    Species.WOOPER: SpeciesData((Type.WATER, Type.GROUND), 55, 45, 45, 25, 25, 15, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=42),
    Species.QUAGSIRE: SpeciesData((Type.WATER, Type.GROUND), 95, 85, 85, 65, 65, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=151),
    Species.ESPEON: SpeciesData((Type.PSYCHIC,), 65, 65, 60, 130, 95, 110, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=184),
    Species.UMBREON: SpeciesData((Type.DARK,), 95, 65, 110, 60, 130, 65, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=184),
    Species.MURKROW: SpeciesData((Type.DARK, Type.FLYING), 60, 85, 42, 85, 42, 91, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=81),
    Species.SLOWKING: SpeciesData((Type.WATER, Type.PSYCHIC), 95, 75, 80, 100, 110, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.SLOWKING_GALAR: SpeciesData((Type.POISON, Type.PSYCHIC), 95, 65, 80, 110, 110, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.MISDREAVUS: SpeciesData((Type.GHOST,), 60, 60, 60, 85, 85, 85, 0.5, growth_rate=GrowthRate.FAST, exp_yield=87),
    Species.UNOWN_A: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_B: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_C: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_D: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_E: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_F: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_G: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_H: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_I: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_J: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_K: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_L: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_M: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_N: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_O: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_P: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_Q: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_R: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_S: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_T: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_U: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_V: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_W: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_X: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_Y: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_Z: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_EX: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.UNOWN_QUESTION: SpeciesData((Type.PSYCHIC,), 48, 72, 48, 72, 48, 48, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=118),
    Species.WOBBUFFET: SpeciesData((Type.PSYCHIC,), 190, 33, 58, 33, 58, 33, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=142),
    Species.GIRAFARIG: SpeciesData((Type.NORMAL, Type.PSYCHIC), 70, 80, 65, 90, 65, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=159),
    Species.PINECO: SpeciesData((Type.BUG,), 50, 65, 90, 35, 35, 15, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=58),
    Species.FORRETRESS: SpeciesData((Type.BUG, Type.STEEL), 75, 90, 140, 60, 60, 40, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=163),
    Species.DUNSPARCE: SpeciesData((Type.NORMAL,), 100, 70, 70, 65, 65, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=145),
    Species.GLIGAR: SpeciesData((Type.GROUND, Type.FLYING), 65, 75, 105, 35, 65, 85, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=86),
    Species.STEELIX: SpeciesData((Type.STEEL, Type.GROUND), 75, 85, 200, 55, 65, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=179),
    Species.STEELIX_MEGA: SpeciesData((Type.STEEL, Type.GROUND), 75, 125, 230, 55, 95, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=214),
    Species.SNUBBULL: SpeciesData((Type.FAIRY,), 60, 80, 50, 40, 40, 30, 0.25, growth_rate=GrowthRate.FAST, exp_yield=60),
    Species.GRANBULL: SpeciesData((Type.FAIRY,), 90, 120, 75, 60, 60, 45, 0.25, growth_rate=GrowthRate.FAST, exp_yield=158),
    Species.QWILFISH: SpeciesData((Type.WATER, Type.POISON), 65, 95, 85, 55, 55, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=88),
    Species.QWILFISH_HISUI: SpeciesData((Type.DARK, Type.POISON), 65, 95, 85, 55, 55, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=88),
    Species.SCIZOR: SpeciesData((Type.BUG, Type.STEEL), 70, 130, 100, 55, 80, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.SCIZOR_MEGA: SpeciesData((Type.BUG, Type.STEEL), 70, 150, 140, 65, 100, 75, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=210),
    Species.SHUCKLE: SpeciesData((Type.BUG, Type.ROCK), 20, 10, 230, 10, 230, 5, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=177),
    Species.HERACROSS: SpeciesData((Type.BUG, Type.FIGHTING), 80, 125, 75, 40, 95, 85, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=175),
    Species.HERACROSS_MEGA: SpeciesData((Type.BUG, Type.FIGHTING), 80, 185, 115, 40, 105, 75, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=210),
    Species.SNEASEL: SpeciesData((Type.DARK, Type.ICE), 55, 95, 55, 35, 75, 115, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=86),
    Species.SNEASEL_HISUI: SpeciesData((Type.FIGHTING, Type.POISON), 55, 95, 55, 35, 75, 115, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=86),
    Species.TEDDIURSA: SpeciesData((Type.NORMAL,), 60, 80, 50, 50, 50, 40, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=66),
    Species.URSARING: SpeciesData((Type.NORMAL,), 90, 130, 75, 75, 75, 55, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.SLUGMA: SpeciesData((Type.FIRE,), 40, 40, 40, 70, 40, 20, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=50),
    Species.MAGCARGO: SpeciesData((Type.FIRE, Type.ROCK), 60, 50, 120, 90, 80, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=151),
    Species.SWINUB: SpeciesData((Type.ICE, Type.GROUND), 50, 50, 40, 30, 30, 50, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=50),
    Species.PILOSWINE: SpeciesData((Type.ICE, Type.GROUND), 100, 100, 80, 60, 60, 50, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=158),
    Species.CORSOLA: SpeciesData((Type.WATER, Type.ROCK), 65, 55, 95, 65, 95, 35, 0.25, growth_rate=GrowthRate.FAST, exp_yield=144),
    Species.CORSOLA_GALAR: SpeciesData((Type.GHOST,), 60, 55, 100, 65, 100, 30, 0.25, growth_rate=GrowthRate.FAST, exp_yield=144),
    Species.REMORAID: SpeciesData((Type.WATER,), 35, 65, 35, 65, 35, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=60),
    Species.OCTILLERY: SpeciesData((Type.WATER,), 75, 105, 75, 105, 75, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.DELIBIRD: SpeciesData((Type.ICE, Type.FLYING), 45, 55, 45, 65, 45, 75, 0.5, growth_rate=GrowthRate.FAST, exp_yield=116),
    Species.MANTINE: SpeciesData((Type.WATER, Type.FLYING), 85, 40, 70, 80, 140, 70, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=170),
    Species.SKARMORY: SpeciesData((Type.STEEL, Type.FLYING), 65, 80, 140, 40, 70, 70, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=163),
    Species.HOUNDOUR: SpeciesData((Type.DARK, Type.FIRE), 45, 60, 30, 80, 50, 65, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=66),
    Species.HOUNDOOM: SpeciesData((Type.DARK, Type.FIRE), 75, 90, 50, 110, 80, 95, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=175),
    Species.HOUNDOOM_MEGA: SpeciesData((Type.DARK, Type.FIRE), 75, 90, 90, 140, 90, 115, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=210),
    Species.KINGDRA: SpeciesData((Type.WATER, Type.DRAGON), 75, 95, 95, 95, 95, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=270),
    Species.PHANPY: SpeciesData((Type.GROUND,), 90, 60, 60, 40, 40, 40, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=66),
    Species.DONPHAN: SpeciesData((Type.GROUND,), 90, 120, 120, 60, 60, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.PORYGON2: SpeciesData((Type.NORMAL,), 85, 80, 90, 105, 95, 60, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=180),
    Species.STANTLER: SpeciesData((Type.NORMAL,), 73, 95, 62, 85, 65, 85, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=163),
    Species.SMEARGLE: SpeciesData((Type.NORMAL,), 55, 20, 35, 20, 45, 75, 0.5, growth_rate=GrowthRate.FAST, exp_yield=88),
    Species.TYROGUE: SpeciesData((Type.FIGHTING,), 35, 35, 35, 35, 35, 35, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=42),
    Species.HITMONTOP: SpeciesData((Type.FIGHTING,), 50, 95, 95, 35, 110, 70, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=159),
    Species.SMOOCHUM: SpeciesData((Type.ICE, Type.PSYCHIC), 45, 30, 15, 85, 65, 65, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.ELEKID: SpeciesData((Type.ELECTRIC,), 45, 63, 37, 65, 55, 95, 0.75, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=72),
    Species.MAGBY: SpeciesData((Type.FIRE,), 45, 75, 37, 70, 55, 83, 0.75, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=73),
    Species.MILTANK: SpeciesData((Type.NORMAL,), 95, 80, 105, 40, 70, 100, 0.0, growth_rate=GrowthRate.SLOW, exp_yield=172),
    Species.BLISSEY: SpeciesData((Type.NORMAL,), 255, 10, 10, 75, 135, 55, 0.0, growth_rate=GrowthRate.FAST, exp_yield=635),
    Species.RAIKOU: SpeciesData((Type.ELECTRIC,), 90, 85, 75, 115, 100, 115, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.ENTEI: SpeciesData((Type.FIRE,), 115, 115, 85, 90, 75, 100, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.SUICUNE: SpeciesData((Type.WATER,), 100, 75, 115, 90, 115, 85, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.LARVITAR: SpeciesData((Type.ROCK, Type.GROUND), 50, 64, 50, 45, 50, 41, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=60),
    Species.PUPITAR: SpeciesData((Type.ROCK, Type.GROUND), 70, 84, 70, 65, 70, 51, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=144),
    Species.TYRANITAR: SpeciesData((Type.ROCK, Type.DARK), 100, 134, 110, 95, 100, 61, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.TYRANITAR_MEGA: SpeciesData((Type.ROCK, Type.DARK), 100, 164, 150, 95, 120, 71, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=350),
    Species.LUGIA: SpeciesData((Type.PSYCHIC, Type.FLYING), 106, 90, 130, 90, 154, 110, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.HO_OH: SpeciesData((Type.FIRE, Type.FLYING), 106, 130, 90, 110, 154, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.CELEBI: SpeciesData((Type.PSYCHIC, Type.GRASS), 100, 100, 100, 100, 100, 100, None, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=300),
    Species.TREECKO: SpeciesData((Type.GRASS,), 40, 45, 35, 65, 55, 70, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.GROVYLE: SpeciesData((Type.GRASS,), 50, 65, 45, 85, 65, 95, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.SCEPTILE: SpeciesData((Type.GRASS,), 70, 85, 65, 105, 85, 120, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.SCEPTILE_MEGA: SpeciesData((Type.GRASS, Type.DRAGON), 70, 110, 75, 145, 85, 145, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=315),
    Species.TORCHIC: SpeciesData((Type.FIRE,), 45, 60, 40, 70, 50, 45, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.COMBUSKEN: SpeciesData((Type.FIRE, Type.FIGHTING), 60, 85, 60, 85, 60, 55, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.BLAZIKEN: SpeciesData((Type.FIRE, Type.FIGHTING), 80, 120, 70, 110, 70, 80, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.BLAZIKEN_MEGA: SpeciesData((Type.FIRE, Type.FIGHTING), 80, 160, 80, 130, 80, 100, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=315),
    Species.MUDKIP: SpeciesData((Type.WATER,), 50, 70, 50, 50, 50, 40, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.MARSHTOMP: SpeciesData((Type.WATER, Type.GROUND), 70, 85, 70, 60, 70, 50, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.SWAMPERT: SpeciesData((Type.WATER, Type.GROUND), 100, 110, 90, 85, 90, 60, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=268),
    Species.SWAMPERT_MEGA: SpeciesData((Type.WATER, Type.GROUND), 100, 150, 110, 95, 110, 70, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=318),
    Species.POOCHYENA: SpeciesData((Type.DARK,), 35, 55, 35, 30, 30, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=56),
    Species.MIGHTYENA: SpeciesData((Type.DARK,), 70, 90, 70, 60, 60, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=147),
    Species.ZIGZAGOON: SpeciesData((Type.NORMAL,), 38, 30, 41, 30, 41, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=56),
    Species.ZIGZAGOON_GALAR: SpeciesData((Type.DARK, Type.NORMAL), 38, 30, 41, 30, 41, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=56),
    Species.LINOONE: SpeciesData((Type.NORMAL,), 78, 70, 61, 50, 61, 100, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=147),
    Species.LINOONE_GALAR: SpeciesData((Type.DARK, Type.NORMAL), 78, 70, 61, 50, 61, 100, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=147),
    Species.WURMPLE: SpeciesData((Type.BUG,), 45, 45, 35, 20, 30, 20, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=56),
    Species.SILCOON: SpeciesData((Type.BUG,), 50, 35, 55, 25, 25, 15, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=72),
    Species.BEAUTIFLY: SpeciesData((Type.BUG, Type.FLYING), 60, 70, 50, 100, 50, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=198),
    Species.CASCOON: SpeciesData((Type.BUG,), 50, 35, 55, 25, 25, 15, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=72),
    Species.DUSTOX: SpeciesData((Type.BUG, Type.POISON), 60, 50, 70, 50, 90, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=193),
    Species.LOTAD: SpeciesData((Type.WATER, Type.GRASS), 40, 30, 30, 40, 50, 30, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=44),
    Species.LOMBRE: SpeciesData((Type.WATER, Type.GRASS), 60, 50, 50, 60, 70, 50, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=119),
    Species.LUDICOLO: SpeciesData((Type.WATER, Type.GRASS), 80, 70, 70, 90, 100, 70, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=240),
    Species.SEEDOT: SpeciesData((Type.GRASS,), 40, 40, 50, 30, 30, 30, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=44),
    Species.NUZLEAF: SpeciesData((Type.GRASS, Type.DARK), 70, 70, 40, 60, 40, 60, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=119),
    Species.SHIFTRY: SpeciesData((Type.GRASS, Type.DARK), 90, 100, 60, 90, 60, 80, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=240),
    Species.TAILLOW: SpeciesData((Type.NORMAL, Type.FLYING), 40, 55, 30, 30, 30, 85, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=54),
    Species.SWELLOW: SpeciesData((Type.NORMAL, Type.FLYING), 60, 85, 60, 75, 50, 125, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=159),
    Species.WINGULL: SpeciesData((Type.WATER, Type.FLYING), 40, 30, 30, 55, 30, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=54),
    Species.PELIPPER: SpeciesData((Type.WATER, Type.FLYING), 60, 50, 100, 95, 70, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=154),
    Species.RALTS: SpeciesData((Type.PSYCHIC, Type.FAIRY), 28, 25, 25, 45, 35, 40, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=40),
    Species.KIRLIA: SpeciesData((Type.PSYCHIC, Type.FAIRY), 38, 35, 35, 65, 55, 50, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=97),
    Species.GARDEVOIR: SpeciesData((Type.PSYCHIC, Type.FAIRY), 68, 65, 65, 125, 115, 80, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=259),
    Species.GARDEVOIR_MEGA: SpeciesData((Type.PSYCHIC, Type.FAIRY), 68, 85, 65, 165, 135, 100, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=309),
    Species.SURSKIT: SpeciesData((Type.BUG, Type.WATER), 40, 30, 32, 50, 52, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=54),
    Species.MASQUERAIN: SpeciesData((Type.BUG, Type.FLYING), 70, 60, 62, 100, 82, 80, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=159),
    Species.SHROOMISH: SpeciesData((Type.GRASS,), 60, 40, 60, 40, 60, 35, 0.5, growth_rate=GrowthRate.FLUCTUATING, exp_yield=59),
    Species.BRELOOM: SpeciesData((Type.GRASS, Type.FIGHTING), 60, 130, 80, 60, 60, 70, 0.5, growth_rate=GrowthRate.FLUCTUATING, exp_yield=161),
    Species.SLAKOTH: SpeciesData((Type.NORMAL,), 60, 60, 60, 35, 35, 30, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=56),
    Species.VIGOROTH: SpeciesData((Type.NORMAL,), 80, 80, 80, 55, 55, 90, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=154),
    Species.SLAKING: SpeciesData((Type.NORMAL,), 150, 160, 100, 95, 65, 100, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.NINCADA: SpeciesData((Type.BUG, Type.GROUND), 31, 45, 90, 30, 30, 40, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=53),
    Species.NINJASK: SpeciesData((Type.BUG, Type.FLYING), 61, 90, 45, 50, 50, 160, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=160),
    Species.SHEDINJA: SpeciesData((Type.BUG, Type.GHOST), 1, 90, 45, 30, 30, 40, None, growth_rate=GrowthRate.ERRATIC, exp_yield=83),
    Species.WHISMUR: SpeciesData((Type.NORMAL,), 64, 51, 23, 51, 23, 28, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=48),
    Species.LOUDRED: SpeciesData((Type.NORMAL,), 84, 71, 43, 71, 43, 48, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=126),
    Species.EXPLOUD: SpeciesData((Type.NORMAL,), 104, 91, 63, 91, 73, 68, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=245),
    Species.MAKUHITA: SpeciesData((Type.FIGHTING,), 72, 60, 30, 20, 30, 25, 0.75, growth_rate=GrowthRate.FLUCTUATING, exp_yield=47),
    Species.HARIYAMA: SpeciesData((Type.FIGHTING,), 144, 120, 60, 40, 60, 50, 0.75, growth_rate=GrowthRate.FLUCTUATING, exp_yield=166),
    Species.AZURILL: SpeciesData((Type.NORMAL, Type.FAIRY), 50, 20, 40, 20, 40, 20, 0.25, growth_rate=GrowthRate.FAST, exp_yield=38),
    Species.NOSEPASS: SpeciesData((Type.ROCK,), 30, 45, 135, 45, 90, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=75),
    Species.SKITTY: SpeciesData((Type.NORMAL,), 50, 45, 45, 35, 35, 50, 0.25, growth_rate=GrowthRate.FAST, exp_yield=52),
    Species.DELCATTY: SpeciesData((Type.NORMAL,), 70, 65, 65, 55, 55, 90, 0.25, growth_rate=GrowthRate.FAST, exp_yield=140),
    Species.SABLEYE: SpeciesData((Type.DARK, Type.GHOST), 50, 75, 75, 65, 65, 50, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=133),
    Species.SABLEYE_MEGA: SpeciesData((Type.DARK, Type.GHOST), 50, 85, 125, 85, 115, 20, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=168),
    Species.MAWILE: SpeciesData((Type.STEEL, Type.FAIRY), 50, 85, 85, 55, 55, 50, 0.5, growth_rate=GrowthRate.FAST, exp_yield=133),
    Species.MAWILE_MEGA: SpeciesData((Type.STEEL, Type.FAIRY), 50, 105, 125, 55, 95, 50, 0.5, growth_rate=GrowthRate.FAST, exp_yield=168),
    Species.ARON: SpeciesData((Type.STEEL, Type.ROCK), 50, 70, 100, 40, 40, 30, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=66),
    Species.LAIRON: SpeciesData((Type.STEEL, Type.ROCK), 60, 90, 140, 50, 50, 40, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=151),
    Species.AGGRON: SpeciesData((Type.STEEL, Type.ROCK), 70, 110, 180, 60, 60, 50, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=265),
    Species.AGGRON_MEGA: SpeciesData((Type.STEEL,), 70, 140, 230, 60, 80, 50, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=315),
    Species.MEDITITE: SpeciesData((Type.FIGHTING, Type.PSYCHIC), 30, 40, 55, 40, 55, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=56),
    Species.MEDICHAM: SpeciesData((Type.FIGHTING, Type.PSYCHIC), 60, 60, 75, 60, 75, 80, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=144),
    Species.MEDICHAM_MEGA: SpeciesData((Type.FIGHTING, Type.PSYCHIC), 60, 100, 85, 80, 85, 100, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=179),
    Species.ELECTRIKE: SpeciesData((Type.ELECTRIC,), 40, 45, 40, 65, 40, 65, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=59),
    Species.MANECTRIC: SpeciesData((Type.ELECTRIC,), 70, 75, 60, 105, 60, 105, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=166),
    Species.MANECTRIC_MEGA: SpeciesData((Type.ELECTRIC,), 70, 75, 80, 135, 80, 135, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=201),
    Species.PLUSLE: SpeciesData((Type.ELECTRIC,), 60, 50, 40, 85, 75, 95, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=142),
    Species.MINUN: SpeciesData((Type.ELECTRIC,), 60, 40, 50, 75, 85, 95, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=142),
    Species.VOLBEAT: SpeciesData((Type.BUG,), 65, 73, 75, 47, 85, 85, 1.0, growth_rate=GrowthRate.ERRATIC, exp_yield=151),
    Species.ILLUMISE: SpeciesData((Type.BUG,), 65, 47, 75, 73, 85, 85, 0.0, growth_rate=GrowthRate.FLUCTUATING, exp_yield=151),
    Species.ROSELIA: SpeciesData((Type.GRASS, Type.POISON), 50, 60, 45, 100, 80, 65, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=140),
    Species.GULPIN: SpeciesData((Type.POISON,), 70, 43, 53, 43, 53, 40, 0.5, growth_rate=GrowthRate.FLUCTUATING, exp_yield=60),
    Species.SWALOT: SpeciesData((Type.POISON,), 100, 73, 83, 73, 83, 55, 0.5, growth_rate=GrowthRate.FLUCTUATING, exp_yield=163),
    Species.CARVANHA: SpeciesData((Type.WATER, Type.DARK), 45, 90, 20, 65, 20, 65, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=61),
    Species.SHARPEDO: SpeciesData((Type.WATER, Type.DARK), 70, 120, 40, 95, 40, 95, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=161),
    Species.SHARPEDO_MEGA: SpeciesData((Type.WATER, Type.DARK), 70, 140, 70, 110, 65, 105, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=196),
    Species.WAILMER: SpeciesData((Type.WATER,), 130, 70, 35, 70, 35, 60, 0.5, growth_rate=GrowthRate.FLUCTUATING, exp_yield=80),
    Species.WAILORD: SpeciesData((Type.WATER,), 170, 90, 45, 90, 45, 60, 0.5, growth_rate=GrowthRate.FLUCTUATING, exp_yield=175),
    Species.NUMEL: SpeciesData((Type.FIRE, Type.GROUND), 60, 60, 40, 65, 45, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.CAMERUPT: SpeciesData((Type.FIRE, Type.GROUND), 70, 100, 70, 105, 75, 40, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=161),
    Species.CAMERUPT_MEGA: SpeciesData((Type.FIRE, Type.GROUND), 70, 120, 100, 145, 105, 20, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=196),
    Species.TORKOAL: SpeciesData((Type.FIRE,), 70, 85, 140, 85, 70, 20, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.SPOINK: SpeciesData((Type.PSYCHIC,), 60, 25, 35, 70, 80, 60, 0.5, growth_rate=GrowthRate.FAST, exp_yield=66),
    Species.GRUMPIG: SpeciesData((Type.PSYCHIC,), 80, 45, 65, 90, 110, 80, 0.5, growth_rate=GrowthRate.FAST, exp_yield=165),
    Species.SPINDA: SpeciesData((Type.NORMAL,), 60, 60, 60, 60, 60, 60, 0.5, growth_rate=GrowthRate.FAST, exp_yield=126),
    Species.TRAPINCH: SpeciesData((Type.GROUND,), 45, 100, 45, 45, 45, 10, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=58),
    Species.VIBRAVA: SpeciesData((Type.GROUND, Type.DRAGON), 50, 70, 50, 50, 50, 70, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=119),
    Species.FLYGON: SpeciesData((Type.GROUND, Type.DRAGON), 80, 100, 80, 80, 80, 100, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=260),
    Species.CACNEA: SpeciesData((Type.GRASS,), 50, 85, 40, 85, 40, 35, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=67),
    Species.CACTURNE: SpeciesData((Type.GRASS, Type.DARK), 70, 115, 60, 115, 60, 55, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=166),
    Species.SWABLU: SpeciesData((Type.NORMAL, Type.FLYING), 45, 40, 60, 40, 75, 50, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=62),
    Species.ALTARIA: SpeciesData((Type.DRAGON, Type.FLYING), 75, 70, 90, 70, 105, 80, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=172),
    Species.ALTARIA_MEGA: SpeciesData((Type.DRAGON, Type.FAIRY), 75, 110, 110, 110, 105, 80, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=207),
    Species.ZANGOOSE: SpeciesData((Type.NORMAL,), 73, 115, 60, 60, 60, 90, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=160),
    Species.SEVIPER: SpeciesData((Type.POISON,), 73, 100, 60, 100, 60, 65, 0.5, growth_rate=GrowthRate.FLUCTUATING, exp_yield=160),
    Species.LUNATONE: SpeciesData((Type.ROCK, Type.PSYCHIC), 90, 55, 65, 95, 85, 70, None, growth_rate=GrowthRate.FAST, exp_yield=161),
    Species.SOLROCK: SpeciesData((Type.ROCK, Type.PSYCHIC), 90, 95, 85, 55, 65, 70, None, growth_rate=GrowthRate.FAST, exp_yield=161),
    Species.BARBOACH: SpeciesData((Type.WATER, Type.GROUND), 50, 48, 43, 46, 41, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=58),
    Species.WHISCASH: SpeciesData((Type.WATER, Type.GROUND), 110, 78, 73, 76, 71, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=164),
    Species.CORPHISH: SpeciesData((Type.WATER,), 43, 80, 65, 50, 35, 35, 0.5, growth_rate=GrowthRate.FLUCTUATING, exp_yield=62),
    Species.CRAWDAUNT: SpeciesData((Type.WATER, Type.DARK), 63, 120, 85, 90, 55, 55, 0.5, growth_rate=GrowthRate.FLUCTUATING, exp_yield=164),
    Species.BALTOY: SpeciesData((Type.GROUND, Type.PSYCHIC), 40, 40, 55, 40, 70, 55, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=60),
    Species.CLAYDOL: SpeciesData((Type.GROUND, Type.PSYCHIC), 60, 70, 105, 70, 120, 75, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.LILEEP: SpeciesData((Type.ROCK, Type.GRASS), 66, 41, 77, 61, 87, 23, 0.875, growth_rate=GrowthRate.ERRATIC, exp_yield=71),
    Species.CRADILY: SpeciesData((Type.ROCK, Type.GRASS), 86, 81, 97, 81, 107, 43, 0.875, growth_rate=GrowthRate.ERRATIC, exp_yield=173),
    Species.ANORITH: SpeciesData((Type.ROCK, Type.BUG), 45, 95, 50, 40, 50, 75, 0.875, growth_rate=GrowthRate.ERRATIC, exp_yield=71),
    Species.ARMALDO: SpeciesData((Type.ROCK, Type.BUG), 75, 125, 100, 70, 80, 45, 0.875, growth_rate=GrowthRate.ERRATIC, exp_yield=173),
    Species.FEEBAS: SpeciesData((Type.WATER,), 20, 15, 20, 10, 55, 80, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=40),
    Species.MILOTIC: SpeciesData((Type.WATER,), 95, 60, 79, 100, 125, 81, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=189),
    Species.CASTFORM: SpeciesData((Type.NORMAL,), 70, 70, 70, 70, 70, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=147),
    Species.CASTFORM_SUNNY: SpeciesData((Type.FIRE,), 70, 70, 70, 70, 70, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=147),
    Species.CASTFORM_RAINY: SpeciesData((Type.WATER,), 70, 70, 70, 70, 70, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=147),
    Species.CASTFORM_SNOWY: SpeciesData((Type.ICE,), 70, 70, 70, 70, 70, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=147),
    Species.KECLEON: SpeciesData((Type.NORMAL,), 60, 90, 70, 60, 120, 40, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=154),
    Species.SHUPPET: SpeciesData((Type.GHOST,), 44, 75, 35, 63, 33, 45, 0.5, growth_rate=GrowthRate.FAST, exp_yield=59),
    Species.BANETTE: SpeciesData((Type.GHOST,), 64, 115, 65, 83, 63, 65, 0.5, growth_rate=GrowthRate.FAST, exp_yield=159),
    Species.BANETTE_MEGA: SpeciesData((Type.GHOST,), 64, 165, 75, 93, 83, 75, 0.5, growth_rate=GrowthRate.FAST, exp_yield=194),
    Species.DUSKULL: SpeciesData((Type.GHOST,), 20, 40, 90, 30, 90, 25, 0.5, growth_rate=GrowthRate.FAST, exp_yield=59),
    Species.DUSCLOPS: SpeciesData((Type.GHOST,), 40, 70, 130, 60, 130, 25, 0.5, growth_rate=GrowthRate.FAST, exp_yield=159),
    Species.TROPIUS: SpeciesData((Type.GRASS, Type.FLYING), 99, 68, 83, 72, 87, 51, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=161),
    Species.CHIMECHO: SpeciesData((Type.PSYCHIC,), 75, 50, 80, 95, 90, 65, 0.5, growth_rate=GrowthRate.FAST, exp_yield=159),
    Species.ABSOL: SpeciesData((Type.DARK,), 65, 130, 60, 75, 60, 75, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=163),
    Species.ABSOL_MEGA: SpeciesData((Type.DARK,), 65, 150, 60, 115, 60, 115, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=198),
    Species.WYNAUT: SpeciesData((Type.PSYCHIC,), 95, 23, 48, 23, 48, 23, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=52),
    Species.SNORUNT: SpeciesData((Type.ICE,), 50, 50, 50, 50, 50, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=60),
    Species.GLALIE: SpeciesData((Type.ICE,), 80, 80, 80, 80, 80, 80, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.GLALIE_MEGA: SpeciesData((Type.ICE,), 80, 120, 80, 120, 80, 100, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=203),
    Species.SPHEAL: SpeciesData((Type.ICE, Type.WATER), 70, 40, 50, 55, 50, 25, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=58),
    Species.SEALEO: SpeciesData((Type.ICE, Type.WATER), 90, 60, 70, 75, 70, 45, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=144),
    Species.WALREIN: SpeciesData((Type.ICE, Type.WATER), 110, 80, 90, 95, 90, 65, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.CLAMPERL: SpeciesData((Type.WATER,), 35, 64, 85, 74, 55, 32, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=69),
    Species.HUNTAIL: SpeciesData((Type.WATER,), 55, 104, 105, 94, 75, 52, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=170),
    Species.GOREBYSS: SpeciesData((Type.WATER,), 55, 84, 105, 114, 75, 52, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=170),
    Species.RELICANTH: SpeciesData((Type.WATER, Type.ROCK), 100, 90, 130, 45, 65, 55, 0.875, growth_rate=GrowthRate.SLOW, exp_yield=170),
    Species.LUVDISC: SpeciesData((Type.WATER,), 43, 30, 55, 40, 65, 97, 0.25, growth_rate=GrowthRate.FAST, exp_yield=116),
    Species.BAGON: SpeciesData((Type.DRAGON,), 45, 75, 60, 40, 30, 50, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=60),
    Species.SHELGON: SpeciesData((Type.DRAGON,), 65, 95, 100, 60, 50, 50, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=147),
    Species.SALAMENCE: SpeciesData((Type.DRAGON, Type.FLYING), 95, 135, 80, 110, 80, 100, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.SALAMENCE_MEGA: SpeciesData((Type.DRAGON, Type.FLYING), 95, 145, 130, 120, 90, 120, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=350),
    Species.BELDUM: SpeciesData((Type.STEEL, Type.PSYCHIC), 40, 55, 80, 35, 60, 30, None, growth_rate=GrowthRate.SLOW, exp_yield=60),
    Species.METANG: SpeciesData((Type.STEEL, Type.PSYCHIC), 60, 75, 100, 55, 80, 50, None, growth_rate=GrowthRate.SLOW, exp_yield=147),
    Species.METAGROSS: SpeciesData((Type.STEEL, Type.PSYCHIC), 80, 135, 130, 95, 90, 70, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.METAGROSS_MEGA: SpeciesData((Type.STEEL, Type.PSYCHIC), 80, 145, 150, 105, 110, 110, None, growth_rate=GrowthRate.SLOW, exp_yield=350),
    Species.REGIROCK: SpeciesData((Type.ROCK,), 80, 100, 200, 50, 100, 50, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.REGICE: SpeciesData((Type.ICE,), 80, 50, 100, 100, 200, 50, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.REGISTEEL: SpeciesData((Type.STEEL,), 80, 75, 150, 75, 150, 50, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.LATIAS: SpeciesData((Type.DRAGON, Type.PSYCHIC), 80, 80, 90, 110, 130, 110, 0.0, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.LATIAS_MEGA: SpeciesData((Type.DRAGON, Type.PSYCHIC), 80, 100, 120, 140, 150, 110, 0.0, growth_rate=GrowthRate.SLOW, exp_yield=350),
    Species.LATIOS: SpeciesData((Type.DRAGON, Type.PSYCHIC), 80, 90, 80, 130, 110, 110, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.LATIOS_MEGA: SpeciesData((Type.DRAGON, Type.PSYCHIC), 80, 130, 100, 160, 120, 110, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=350),
    Species.KYOGRE: SpeciesData((Type.WATER,), 100, 100, 90, 150, 140, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=335),
    Species.KYOGRE_PRIMAL: SpeciesData((Type.WATER,), 100, 150, 90, 180, 160, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=385),
    Species.GROUDON: SpeciesData((Type.GROUND,), 100, 150, 140, 100, 90, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=335),
    Species.GROUDON_PRIMAL: SpeciesData((Type.GROUND, Type.FIRE), 100, 180, 160, 150, 90, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=385),
    Species.RAYQUAZA: SpeciesData((Type.DRAGON, Type.FLYING), 105, 150, 90, 150, 90, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.RAYQUAZA_MEGA: SpeciesData((Type.DRAGON, Type.FLYING), 105, 180, 100, 180, 100, 115, None, growth_rate=GrowthRate.SLOW, exp_yield=390),
    Species.JIRACHI: SpeciesData((Type.STEEL, Type.PSYCHIC), 100, 100, 100, 100, 100, 100, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.DEOXYS: SpeciesData((Type.PSYCHIC,), 50, 150, 50, 150, 50, 150, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.DEOXYS_ATTACK: SpeciesData((Type.PSYCHIC,), 50, 180, 20, 180, 20, 150, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.DEOXYS_DEFENSE: SpeciesData((Type.PSYCHIC,), 50, 70, 160, 70, 160, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.DEOXYS_SPEED: SpeciesData((Type.PSYCHIC,), 50, 95, 90, 95, 90, 180, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.TURTWIG: SpeciesData((Type.GRASS,), 55, 68, 64, 45, 55, 31, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=64),
    Species.GROTLE: SpeciesData((Type.GRASS,), 75, 89, 85, 55, 65, 36, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.TORTERRA: SpeciesData((Type.GRASS, Type.GROUND), 95, 109, 105, 75, 85, 56, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=263),
    Species.CHIMCHAR: SpeciesData((Type.FIRE,), 44, 58, 44, 58, 44, 61, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.MONFERNO: SpeciesData((Type.FIRE, Type.FIGHTING), 64, 78, 52, 78, 52, 81, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.INFERNAPE: SpeciesData((Type.FIRE, Type.FIGHTING), 76, 104, 71, 104, 71, 108, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=267),
    Species.PIPLUP: SpeciesData((Type.WATER,), 53, 51, 53, 61, 56, 40, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=63),
    Species.PRINPLUP: SpeciesData((Type.WATER,), 64, 66, 68, 81, 76, 50, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.EMPOLEON: SpeciesData((Type.WATER, Type.STEEL), 84, 86, 88, 111, 101, 60, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.STARLY: SpeciesData((Type.NORMAL, Type.FLYING), 40, 55, 30, 30, 30, 60, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=49),
    Species.STARAVIA: SpeciesData((Type.NORMAL, Type.FLYING), 55, 75, 50, 40, 40, 80, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=119),
    Species.STARAPTOR: SpeciesData((Type.NORMAL, Type.FLYING), 85, 120, 70, 50, 60, 100, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=243),
    Species.BIDOOF: SpeciesData((Type.NORMAL,), 59, 45, 40, 35, 40, 31, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=50),
    Species.BIBAREL: SpeciesData((Type.NORMAL, Type.WATER), 79, 85, 60, 55, 60, 71, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=144),
    Species.KRICKETOT: SpeciesData((Type.BUG,), 37, 25, 41, 25, 41, 25, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=39),
    Species.KRICKETUNE: SpeciesData((Type.BUG,), 77, 85, 51, 55, 51, 65, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=134),
    Species.SHINX: SpeciesData((Type.ELECTRIC,), 45, 65, 34, 40, 34, 45, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=53),
    Species.LUXIO: SpeciesData((Type.ELECTRIC,), 60, 85, 49, 60, 49, 60, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=127),
    Species.LUXRAY: SpeciesData((Type.ELECTRIC,), 80, 120, 79, 95, 79, 70, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=262),
    Species.BUDEW: SpeciesData((Type.GRASS, Type.POISON), 40, 30, 35, 50, 70, 55, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=56),
    Species.ROSERADE: SpeciesData((Type.GRASS, Type.POISON), 60, 70, 65, 125, 105, 90, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=258),
    Species.CRANIDOS: SpeciesData((Type.ROCK,), 67, 125, 40, 30, 30, 58, 0.875, growth_rate=GrowthRate.ERRATIC, exp_yield=70),
    Species.RAMPARDOS: SpeciesData((Type.ROCK,), 97, 165, 60, 65, 50, 58, 0.875, growth_rate=GrowthRate.ERRATIC, exp_yield=173),
    Species.SHIELDON: SpeciesData((Type.ROCK, Type.STEEL), 30, 42, 118, 42, 88, 30, 0.875, growth_rate=GrowthRate.ERRATIC, exp_yield=70),
    Species.BASTIODON: SpeciesData((Type.ROCK, Type.STEEL), 60, 52, 168, 47, 138, 30, 0.875, growth_rate=GrowthRate.ERRATIC, exp_yield=173),
    Species.BURMY: SpeciesData((Type.BUG,), 40, 29, 45, 29, 45, 36, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=45),
    Species.BURMY_SANDY: SpeciesData((Type.BUG,), 40, 29, 45, 29, 45, 36, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=45),
    Species.BURMY_TRASH: SpeciesData((Type.BUG,), 40, 29, 45, 29, 45, 36, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=45),
    Species.WORMADAM: SpeciesData((Type.BUG, Type.GRASS), 60, 59, 85, 79, 105, 36, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=148),
    Species.WORMADAM_SANDY: SpeciesData((Type.BUG, Type.GROUND), 60, 79, 105, 59, 85, 36, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=148),
    Species.WORMADAM_TRASH: SpeciesData((Type.BUG, Type.STEEL), 60, 69, 95, 69, 95, 36, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=148),
    Species.MOTHIM: SpeciesData((Type.BUG, Type.FLYING), 70, 94, 50, 94, 50, 66, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=148),
    Species.COMBEE: SpeciesData((Type.BUG, Type.FLYING), 30, 30, 42, 30, 42, 70, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=49),
    Species.VESPIQUEN: SpeciesData((Type.BUG, Type.FLYING), 70, 80, 102, 80, 102, 40, 0.0, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=166),
    Species.PACHIRISU: SpeciesData((Type.ELECTRIC,), 60, 45, 70, 45, 90, 95, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=142),
    Species.BUIZEL: SpeciesData((Type.WATER,), 55, 65, 35, 60, 30, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=66),
    Species.FLOATZEL: SpeciesData((Type.WATER,), 85, 105, 55, 85, 50, 115, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.CHERUBI: SpeciesData((Type.GRASS,), 45, 35, 45, 62, 53, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=55),
    Species.CHERRIM: SpeciesData((Type.GRASS,), 70, 60, 70, 87, 78, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=158),
    Species.CHERRIM_SUNSHINE: SpeciesData((Type.GRASS,), 70, 60, 70, 87, 78, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=158),
    Species.SHELLOS: SpeciesData((Type.WATER,), 76, 48, 48, 57, 62, 34, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=65),
    Species.SHELLOS_WEST: SpeciesData((Type.WATER,), 76, 48, 48, 57, 62, 34, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=65),
    Species.GASTRODON: SpeciesData((Type.WATER, Type.GROUND), 111, 83, 68, 92, 82, 39, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.GASTRODON_WEST: SpeciesData((Type.WATER, Type.GROUND), 111, 83, 68, 92, 82, 39, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.AMBIPOM: SpeciesData((Type.NORMAL,), 75, 100, 66, 60, 66, 115, 0.5, growth_rate=GrowthRate.FAST, exp_yield=169),
    Species.DRIFLOON: SpeciesData((Type.GHOST, Type.FLYING), 90, 50, 34, 60, 44, 70, 0.5, growth_rate=GrowthRate.FLUCTUATING, exp_yield=70),
    Species.DRIFBLIM: SpeciesData((Type.GHOST, Type.FLYING), 150, 80, 44, 90, 54, 80, 0.5, growth_rate=GrowthRate.FLUCTUATING, exp_yield=174),
    Species.BUNEARY: SpeciesData((Type.NORMAL,), 55, 66, 44, 44, 56, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=70),
    Species.LOPUNNY: SpeciesData((Type.NORMAL,), 65, 76, 84, 54, 96, 105, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.LOPUNNY_MEGA: SpeciesData((Type.NORMAL, Type.FIGHTING), 65, 136, 94, 54, 96, 135, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=203),
    Species.MISMAGIUS: SpeciesData((Type.GHOST,), 60, 60, 60, 105, 105, 105, 0.5, growth_rate=GrowthRate.FAST, exp_yield=173),
    Species.HONCHKROW: SpeciesData((Type.DARK, Type.FLYING), 100, 125, 52, 105, 52, 71, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=177),
    Species.GLAMEOW: SpeciesData((Type.NORMAL,), 49, 55, 42, 42, 37, 85, 0.25, growth_rate=GrowthRate.FAST, exp_yield=62),
    Species.PURUGLY: SpeciesData((Type.NORMAL,), 71, 82, 64, 64, 59, 112, 0.25, growth_rate=GrowthRate.FAST, exp_yield=158),
    Species.CHINGLING: SpeciesData((Type.PSYCHIC,), 45, 30, 50, 65, 50, 45, 0.5, growth_rate=GrowthRate.FAST, exp_yield=57),
    Species.STUNKY: SpeciesData((Type.POISON, Type.DARK), 63, 63, 47, 41, 41, 74, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=66),
    Species.SKUNTANK: SpeciesData((Type.POISON, Type.DARK), 103, 93, 67, 71, 61, 84, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.BRONZOR: SpeciesData((Type.STEEL, Type.PSYCHIC), 57, 24, 86, 24, 86, 23, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=60),
    Species.BRONZONG: SpeciesData((Type.STEEL, Type.PSYCHIC), 67, 89, 116, 79, 116, 33, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.BONSLY: SpeciesData((Type.ROCK,), 50, 80, 95, 10, 45, 10, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=58),
    Species.MIME_JR: SpeciesData((Type.PSYCHIC, Type.FAIRY), 20, 25, 45, 70, 90, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=62),
    Species.HAPPINY: SpeciesData((Type.NORMAL,), 100, 5, 5, 15, 65, 30, 0.0, growth_rate=GrowthRate.FAST, exp_yield=110),
    Species.CHATOT: SpeciesData((Type.NORMAL, Type.FLYING), 76, 65, 45, 92, 42, 91, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=144),
    Species.SPIRITOMB: SpeciesData((Type.GHOST, Type.DARK), 50, 92, 108, 92, 108, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=170),
    Species.GIBLE: SpeciesData((Type.DRAGON, Type.GROUND), 58, 70, 45, 40, 45, 42, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=60),
    Species.GABITE: SpeciesData((Type.DRAGON, Type.GROUND), 68, 90, 65, 50, 55, 82, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=144),
    Species.GARCHOMP: SpeciesData((Type.DRAGON, Type.GROUND), 108, 130, 95, 80, 85, 102, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.GARCHOMP_MEGA: SpeciesData((Type.DRAGON, Type.GROUND), 108, 170, 115, 120, 95, 92, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=350),
    Species.MUNCHLAX: SpeciesData((Type.NORMAL,), 135, 85, 40, 40, 85, 5, 0.875, growth_rate=GrowthRate.SLOW, exp_yield=78),
    Species.RIOLU: SpeciesData((Type.FIGHTING,), 40, 70, 40, 35, 40, 60, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=57),
    Species.LUCARIO: SpeciesData((Type.FIGHTING, Type.STEEL), 70, 110, 70, 115, 70, 90, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=184),
    Species.LUCARIO_MEGA: SpeciesData((Type.FIGHTING, Type.STEEL), 70, 145, 88, 140, 70, 112, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=219),
    Species.HIPPOPOTAS: SpeciesData((Type.GROUND,), 68, 72, 78, 38, 42, 32, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=66),
    Species.HIPPOWDON: SpeciesData((Type.GROUND,), 108, 112, 118, 68, 72, 47, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=184),
    Species.SKORUPI: SpeciesData((Type.POISON, Type.BUG), 40, 50, 90, 30, 55, 65, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=66),
    Species.DRAPION: SpeciesData((Type.POISON, Type.DARK), 70, 90, 110, 60, 75, 95, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=175),
    Species.CROAGUNK: SpeciesData((Type.POISON, Type.FIGHTING), 48, 61, 40, 61, 40, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=60),
    Species.TOXICROAK: SpeciesData((Type.POISON, Type.FIGHTING), 83, 106, 65, 86, 65, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.CARNIVINE: SpeciesData((Type.GRASS,), 74, 100, 72, 90, 72, 46, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=159),
    Species.FINNEON: SpeciesData((Type.WATER,), 49, 49, 56, 49, 61, 66, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=66),
    Species.LUMINEON: SpeciesData((Type.WATER,), 69, 69, 76, 69, 86, 91, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=161),
    Species.MANTYKE: SpeciesData((Type.WATER, Type.FLYING), 45, 20, 50, 60, 120, 50, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=69),
    Species.SNOVER: SpeciesData((Type.GRASS, Type.ICE), 60, 62, 50, 62, 60, 40, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=67),
    Species.ABOMASNOW: SpeciesData((Type.GRASS, Type.ICE), 90, 92, 75, 92, 85, 60, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=173),
    Species.ABOMASNOW_MEGA: SpeciesData((Type.GRASS, Type.ICE), 90, 132, 105, 132, 105, 30, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=208),
    Species.WEAVILE: SpeciesData((Type.DARK, Type.ICE), 70, 120, 65, 45, 85, 125, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=179),
    Species.MAGNEZONE: SpeciesData((Type.ELECTRIC, Type.STEEL), 70, 70, 115, 130, 90, 60, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=268),
    Species.LICKILICKY: SpeciesData((Type.NORMAL,), 110, 85, 95, 80, 95, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=180),
    Species.RHYPERIOR: SpeciesData((Type.GROUND, Type.ROCK), 115, 140, 130, 55, 55, 40, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=268),
    Species.TANGROWTH: SpeciesData((Type.GRASS,), 100, 100, 125, 110, 50, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=187),
    Species.ELECTIVIRE: SpeciesData((Type.ELECTRIC,), 75, 123, 67, 95, 85, 95, 0.75, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=270),
    Species.MAGMORTAR: SpeciesData((Type.FIRE,), 75, 95, 67, 125, 95, 83, 0.75, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=270),
    Species.TOGEKISS: SpeciesData((Type.FAIRY, Type.FLYING), 85, 50, 95, 120, 115, 80, 0.875, growth_rate=GrowthRate.FAST, exp_yield=273),
    Species.YANMEGA: SpeciesData((Type.BUG, Type.FLYING), 86, 76, 86, 116, 56, 95, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=180),
    Species.LEAFEON: SpeciesData((Type.GRASS,), 65, 110, 130, 60, 65, 95, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=184),
    Species.GLACEON: SpeciesData((Type.ICE,), 65, 60, 110, 130, 95, 65, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=184),
    Species.GLISCOR: SpeciesData((Type.GROUND, Type.FLYING), 75, 95, 125, 45, 75, 95, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=179),
    Species.MAMOSWINE: SpeciesData((Type.ICE, Type.GROUND), 110, 130, 80, 70, 60, 80, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=265),
    Species.PORYGON_Z: SpeciesData((Type.NORMAL,), 85, 80, 70, 135, 75, 90, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=268),
    Species.GALLADE: SpeciesData((Type.PSYCHIC, Type.FIGHTING), 68, 125, 65, 65, 115, 80, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=259),
    Species.GALLADE_MEGA: SpeciesData((Type.PSYCHIC, Type.FIGHTING), 68, 165, 95, 65, 115, 110, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=309),
    Species.PROBOPASS: SpeciesData((Type.ROCK, Type.STEEL), 60, 55, 145, 75, 150, 40, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=184),
    Species.DUSKNOIR: SpeciesData((Type.GHOST,), 45, 100, 135, 65, 135, 45, 0.5, growth_rate=GrowthRate.FAST, exp_yield=263),
    Species.FROSLASS: SpeciesData((Type.ICE, Type.GHOST), 70, 80, 70, 80, 70, 110, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.ROTOM: SpeciesData((Type.ELECTRIC, Type.GHOST), 50, 50, 77, 95, 77, 91, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=154),
    Species.ROTOM_HEAT: SpeciesData((Type.ELECTRIC, Type.FIRE), 50, 65, 107, 105, 107, 86, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=182),
    Species.ROTOM_WASH: SpeciesData((Type.ELECTRIC, Type.WATER), 50, 65, 107, 105, 107, 86, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=182),
    Species.ROTOM_FROST: SpeciesData((Type.ELECTRIC, Type.ICE), 50, 65, 107, 105, 107, 86, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=182),
    Species.ROTOM_FAN: SpeciesData((Type.ELECTRIC, Type.FLYING), 50, 65, 107, 105, 107, 86, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=182),
    Species.ROTOM_MOW: SpeciesData((Type.ELECTRIC, Type.GRASS), 50, 65, 107, 105, 107, 86, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=182),
    Species.UXIE: SpeciesData((Type.PSYCHIC,), 75, 75, 130, 75, 130, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.MESPRIT: SpeciesData((Type.PSYCHIC,), 80, 105, 105, 105, 105, 80, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.AZELF: SpeciesData((Type.PSYCHIC,), 75, 125, 70, 125, 70, 115, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.DIALGA: SpeciesData((Type.STEEL, Type.DRAGON), 100, 120, 120, 150, 100, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.DIALGA_ORIGIN: SpeciesData((Type.STEEL, Type.DRAGON), 100, 100, 120, 150, 120, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.PALKIA: SpeciesData((Type.WATER, Type.DRAGON), 90, 120, 100, 150, 120, 100, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.PALKIA_ORIGIN: SpeciesData((Type.WATER, Type.DRAGON), 90, 100, 100, 150, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.HEATRAN: SpeciesData((Type.FIRE, Type.STEEL), 91, 90, 106, 130, 106, 77, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.REGIGIGAS: SpeciesData((Type.NORMAL,), 110, 160, 110, 80, 110, 100, None, growth_rate=GrowthRate.SLOW, exp_yield=335),
    Species.GIRATINA: SpeciesData((Type.GHOST, Type.DRAGON), 150, 100, 120, 100, 120, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.GIRATINA_ORIGIN: SpeciesData((Type.GHOST, Type.DRAGON), 150, 120, 100, 120, 100, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.CRESSELIA: SpeciesData((Type.PSYCHIC,), 120, 70, 110, 75, 120, 85, 0.0, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.PHIONE: SpeciesData((Type.WATER,), 80, 80, 80, 80, 80, 80, None, growth_rate=GrowthRate.SLOW, exp_yield=240),
    Species.MANAPHY: SpeciesData((Type.WATER,), 100, 100, 100, 100, 100, 100, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.DARKRAI: SpeciesData((Type.DARK,), 70, 90, 90, 135, 90, 125, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.SHAYMIN: SpeciesData((Type.GRASS,), 100, 100, 100, 100, 100, 100, None, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=300),
    Species.SHAYMIN_SKY: SpeciesData((Type.GRASS, Type.FLYING), 100, 103, 75, 120, 75, 127, None, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=300),
    Species.ARCEUS: SpeciesData((Type.NORMAL,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_BUG: SpeciesData((Type.BUG,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_DARK: SpeciesData((Type.DARK,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_DRAGON: SpeciesData((Type.DRAGON,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_ELECTRIC: SpeciesData((Type.ELECTRIC,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_FAIRY: SpeciesData((Type.FAIRY,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_FIGHTING: SpeciesData((Type.FIGHTING,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_FIRE: SpeciesData((Type.FIRE,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_FLYING: SpeciesData((Type.FLYING,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_GHOST: SpeciesData((Type.GHOST,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_GRASS: SpeciesData((Type.GRASS,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_GROUND: SpeciesData((Type.GROUND,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_ICE: SpeciesData((Type.ICE,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_POISON: SpeciesData((Type.POISON,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_PSYCHIC: SpeciesData((Type.PSYCHIC,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_ROCK: SpeciesData((Type.ROCK,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_STEEL: SpeciesData((Type.STEEL,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ARCEUS_WATER: SpeciesData((Type.WATER,), 120, 120, 120, 120, 120, 120, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.VICTINI: SpeciesData((Type.PSYCHIC, Type.FIRE), 100, 100, 100, 100, 100, 100, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.SNIVY: SpeciesData((Type.GRASS,), 45, 45, 55, 45, 55, 63, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.SERVINE: SpeciesData((Type.GRASS,), 60, 60, 75, 60, 75, 83, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=145),
    Species.SERPERIOR: SpeciesData((Type.GRASS,), 75, 75, 95, 75, 95, 113, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=264),
    Species.TEPIG: SpeciesData((Type.FIRE,), 65, 63, 45, 45, 45, 45, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.PIGNITE: SpeciesData((Type.FIRE, Type.FIGHTING), 90, 93, 55, 70, 55, 55, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=146),
    Species.EMBOAR: SpeciesData((Type.FIRE, Type.FIGHTING), 110, 123, 65, 100, 65, 65, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=264),
    Species.OSHAWOTT: SpeciesData((Type.WATER,), 55, 55, 45, 63, 45, 45, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.DEWOTT: SpeciesData((Type.WATER,), 75, 75, 60, 83, 60, 60, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=145),
    Species.SAMUROTT: SpeciesData((Type.WATER,), 95, 100, 85, 108, 70, 70, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=264),
    Species.SAMUROTT_HISUI: SpeciesData((Type.WATER, Type.DARK), 90, 108, 80, 100, 65, 85, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=264),
    Species.PATRAT: SpeciesData((Type.NORMAL,), 45, 55, 39, 35, 39, 42, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=51),
    Species.WATCHOG: SpeciesData((Type.NORMAL,), 60, 85, 69, 60, 69, 77, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=147),
    Species.LILLIPUP: SpeciesData((Type.NORMAL,), 45, 60, 45, 25, 45, 55, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=55),
    Species.HERDIER: SpeciesData((Type.NORMAL,), 65, 80, 65, 35, 65, 60, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=130),
    Species.STOUTLAND: SpeciesData((Type.NORMAL,), 85, 110, 90, 45, 90, 80, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=250),
    Species.PURRLOIN: SpeciesData((Type.DARK,), 41, 50, 37, 50, 37, 66, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=56),
    Species.LIEPARD: SpeciesData((Type.DARK,), 64, 88, 50, 88, 50, 106, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=156),
    Species.PANSAGE: SpeciesData((Type.GRASS,), 50, 53, 48, 53, 48, 64, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=63),
    Species.SIMISAGE: SpeciesData((Type.GRASS,), 75, 98, 63, 98, 63, 101, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=174),
    Species.PANSEAR: SpeciesData((Type.FIRE,), 50, 53, 48, 53, 48, 64, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=63),
    Species.SIMISEAR: SpeciesData((Type.FIRE,), 75, 98, 63, 98, 63, 101, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=174),
    Species.PANPOUR: SpeciesData((Type.WATER,), 50, 53, 48, 53, 48, 64, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=63),
    Species.SIMIPOUR: SpeciesData((Type.WATER,), 75, 98, 63, 98, 63, 101, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=174),
    Species.MUNNA: SpeciesData((Type.PSYCHIC,), 76, 25, 45, 67, 55, 24, 0.5, growth_rate=GrowthRate.FAST, exp_yield=58),
    Species.MUSHARNA: SpeciesData((Type.PSYCHIC,), 116, 55, 85, 107, 95, 29, 0.5, growth_rate=GrowthRate.FAST, exp_yield=170),
    Species.PIDOVE: SpeciesData((Type.NORMAL, Type.FLYING), 50, 55, 50, 36, 30, 43, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=53),
    Species.TRANQUILL: SpeciesData((Type.NORMAL, Type.FLYING), 62, 77, 62, 50, 42, 65, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=125),
    Species.UNFEZANT: SpeciesData((Type.NORMAL, Type.FLYING), 80, 115, 80, 65, 55, 93, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=244),
    Species.BLITZLE: SpeciesData((Type.ELECTRIC,), 45, 60, 32, 50, 32, 76, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=59),
    Species.ZEBSTRIKA: SpeciesData((Type.ELECTRIC,), 75, 100, 63, 80, 63, 116, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=174),
    Species.ROGGENROLA: SpeciesData((Type.ROCK,), 55, 75, 85, 25, 25, 15, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=56),
    Species.BOLDORE: SpeciesData((Type.ROCK,), 70, 105, 105, 50, 40, 20, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=137),
    Species.GIGALITH: SpeciesData((Type.ROCK,), 85, 135, 130, 60, 80, 25, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=258),
    Species.WOOBAT: SpeciesData((Type.PSYCHIC, Type.FLYING), 65, 45, 43, 55, 43, 72, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=65),
    Species.SWOOBAT: SpeciesData((Type.PSYCHIC, Type.FLYING), 67, 57, 55, 77, 55, 114, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=149),
    Species.DRILBUR: SpeciesData((Type.GROUND,), 60, 85, 40, 30, 45, 68, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=66),
    Species.EXCADRILL: SpeciesData((Type.GROUND, Type.STEEL), 110, 135, 60, 50, 65, 88, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=178),
    Species.AUDINO: SpeciesData((Type.NORMAL,), 103, 60, 86, 60, 86, 50, 0.5, growth_rate=GrowthRate.FAST, exp_yield=390),
    Species.AUDINO_MEGA: SpeciesData((Type.NORMAL, Type.FAIRY), 103, 60, 126, 80, 126, 50, 0.5, growth_rate=GrowthRate.FAST, exp_yield=425),
    Species.TIMBURR: SpeciesData((Type.FIGHTING,), 75, 80, 55, 25, 35, 35, 0.75, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=61),
    Species.GURDURR: SpeciesData((Type.FIGHTING,), 85, 105, 85, 40, 50, 40, 0.75, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.CONKELDURR: SpeciesData((Type.FIGHTING,), 105, 140, 95, 55, 65, 45, 0.75, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=253),
    Species.TYMPOLE: SpeciesData((Type.WATER,), 50, 50, 40, 50, 40, 64, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=59),
    Species.PALPITOAD: SpeciesData((Type.WATER, Type.GROUND), 75, 65, 55, 65, 55, 69, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=134),
    Species.SEISMITOAD: SpeciesData((Type.WATER, Type.GROUND), 105, 95, 75, 85, 75, 74, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=255),
    Species.THROH: SpeciesData((Type.FIGHTING,), 120, 100, 85, 30, 85, 45, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=163),
    Species.SAWK: SpeciesData((Type.FIGHTING,), 75, 125, 75, 30, 75, 85, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=163),
    Species.SEWADDLE: SpeciesData((Type.BUG, Type.GRASS), 45, 53, 70, 40, 60, 42, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.SWADLOON: SpeciesData((Type.BUG, Type.GRASS), 55, 63, 90, 50, 80, 42, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=133),
    Species.LEAVANNY: SpeciesData((Type.BUG, Type.GRASS), 75, 103, 80, 70, 80, 92, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=250),
    Species.VENIPEDE: SpeciesData((Type.BUG, Type.POISON), 30, 45, 59, 30, 39, 57, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=52),
    Species.WHIRLIPEDE: SpeciesData((Type.BUG, Type.POISON), 40, 55, 99, 40, 79, 47, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=126),
    Species.SCOLIPEDE: SpeciesData((Type.BUG, Type.POISON), 60, 100, 89, 55, 69, 112, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=243),
    Species.COTTONEE: SpeciesData((Type.GRASS, Type.FAIRY), 40, 27, 60, 37, 50, 66, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=56),
    Species.WHIMSICOTT: SpeciesData((Type.GRASS, Type.FAIRY), 60, 67, 85, 77, 75, 116, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.PETILIL: SpeciesData((Type.GRASS,), 45, 35, 50, 70, 50, 30, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=56),
    Species.LILLIGANT: SpeciesData((Type.GRASS,), 70, 60, 75, 110, 75, 90, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.LILLIGANT_HISUI: SpeciesData((Type.GRASS, Type.FIGHTING), 70, 105, 75, 50, 75, 105, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.BASCULIN: SpeciesData((Type.WATER,), 70, 92, 65, 80, 55, 98, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=161),
    Species.BASCULIN_BLUE_STRIPED: SpeciesData((Type.WATER,), 70, 92, 65, 80, 55, 98, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=161),
    Species.BASCULIN_WHITE_STRIPED: SpeciesData((Type.WATER,), 70, 92, 65, 80, 55, 98, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=161),
    Species.SANDILE: SpeciesData((Type.GROUND, Type.DARK), 50, 72, 35, 35, 35, 65, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=58),
    Species.KROKOROK: SpeciesData((Type.GROUND, Type.DARK), 60, 82, 45, 45, 45, 74, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=123),
    Species.KROOKODILE: SpeciesData((Type.GROUND, Type.DARK), 95, 117, 80, 65, 70, 92, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=260),
    Species.DARUMAKA: SpeciesData((Type.FIRE,), 70, 90, 45, 15, 45, 50, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=63),
    Species.DARUMAKA_GALAR: SpeciesData((Type.ICE,), 70, 90, 45, 15, 45, 50, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=63),
    Species.DARMANITAN: SpeciesData((Type.FIRE,), 105, 140, 55, 30, 55, 95, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=168),
    Species.DARMANITAN_ZEN: SpeciesData((Type.FIRE, Type.PSYCHIC), 105, 30, 105, 140, 105, 55, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=189),
    Species.DARMANITAN_GALAR: SpeciesData((Type.ICE,), 105, 140, 55, 30, 55, 95, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=168),
    Species.DARMANITAN_GALAR_ZEN: SpeciesData((Type.ICE, Type.FIRE), 105, 160, 55, 30, 55, 135, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=189),
    Species.MARACTUS: SpeciesData((Type.GRASS,), 75, 86, 67, 106, 67, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=161),
    Species.DWEBBLE: SpeciesData((Type.BUG, Type.ROCK), 50, 65, 85, 35, 35, 55, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=65),
    Species.CRUSTLE: SpeciesData((Type.BUG, Type.ROCK), 70, 105, 125, 65, 75, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=170),
    Species.SCRAGGY: SpeciesData((Type.DARK, Type.FIGHTING), 50, 75, 70, 35, 70, 48, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=70),
    Species.SCRAFTY: SpeciesData((Type.DARK, Type.FIGHTING), 65, 90, 115, 45, 115, 58, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=171),
    Species.SIGILYPH: SpeciesData((Type.PSYCHIC, Type.FLYING), 72, 58, 80, 103, 80, 97, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.YAMASK: SpeciesData((Type.GHOST,), 38, 30, 85, 55, 65, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.YAMASK_GALAR: SpeciesData((Type.GROUND, Type.GHOST), 38, 55, 85, 30, 65, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.COFAGRIGUS: SpeciesData((Type.GHOST,), 58, 50, 145, 95, 105, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=169),
    Species.TIRTOUGA: SpeciesData((Type.WATER, Type.ROCK), 54, 78, 103, 53, 45, 22, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=71),
    Species.CARRACOSTA: SpeciesData((Type.WATER, Type.ROCK), 74, 108, 133, 83, 65, 32, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.ARCHEN: SpeciesData((Type.ROCK, Type.FLYING), 55, 112, 45, 74, 45, 70, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=71),
    Species.ARCHEOPS: SpeciesData((Type.ROCK, Type.FLYING), 75, 140, 65, 112, 65, 110, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=177),
    Species.TRUBBISH: SpeciesData((Type.POISON,), 50, 50, 62, 40, 62, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=66),
    Species.GARBODOR: SpeciesData((Type.POISON,), 80, 95, 82, 60, 82, 75, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.ZORUA: SpeciesData((Type.DARK,), 40, 65, 40, 80, 40, 65, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=66),
    Species.ZORUA_HISUI: SpeciesData((Type.NORMAL, Type.GHOST), 35, 60, 40, 85, 40, 70, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=66),
    Species.ZOROARK: SpeciesData((Type.DARK,), 60, 105, 60, 120, 60, 105, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=179),
    Species.ZOROARK_HISUI: SpeciesData((Type.NORMAL, Type.GHOST), 55, 100, 60, 125, 60, 110, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=179),
    Species.MINCCINO: SpeciesData((Type.NORMAL,), 55, 50, 40, 40, 40, 75, 0.25, growth_rate=GrowthRate.FAST, exp_yield=60),
    Species.CINCCINO: SpeciesData((Type.NORMAL,), 75, 95, 60, 65, 60, 115, 0.25, growth_rate=GrowthRate.FAST, exp_yield=165),
    Species.GOTHITA: SpeciesData((Type.PSYCHIC,), 45, 30, 50, 55, 65, 45, 0.25, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=58),
    Species.GOTHORITA: SpeciesData((Type.PSYCHIC,), 60, 45, 70, 75, 85, 55, 0.25, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=137),
    Species.GOTHITELLE: SpeciesData((Type.PSYCHIC,), 70, 55, 95, 95, 110, 65, 0.25, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=245),
    Species.SOLOSIS: SpeciesData((Type.PSYCHIC,), 45, 30, 40, 105, 50, 20, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=58),
    Species.DUOSION: SpeciesData((Type.PSYCHIC,), 65, 40, 50, 125, 60, 30, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=130),
    Species.REUNICLUS: SpeciesData((Type.PSYCHIC,), 110, 65, 75, 125, 85, 30, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=245),
    Species.DUCKLETT: SpeciesData((Type.WATER, Type.FLYING), 62, 44, 50, 44, 50, 55, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.SWANNA: SpeciesData((Type.WATER, Type.FLYING), 75, 87, 63, 87, 63, 98, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.VANILLITE: SpeciesData((Type.ICE,), 36, 50, 50, 65, 60, 44, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=61),
    Species.VANILLISH: SpeciesData((Type.ICE,), 51, 65, 65, 80, 75, 59, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=138),
    Species.VANILLUXE: SpeciesData((Type.ICE,), 71, 95, 85, 110, 95, 79, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=268),
    Species.DEERLING: SpeciesData((Type.NORMAL, Type.GRASS), 60, 60, 50, 40, 50, 75, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=67),
    Species.DEERLING_SUMMER: SpeciesData((Type.NORMAL, Type.GRASS), 60, 60, 50, 40, 50, 75, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=67),
    Species.DEERLING_AUTUMN: SpeciesData((Type.NORMAL, Type.GRASS), 60, 60, 50, 40, 50, 75, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=67),
    Species.DEERLING_WINTER: SpeciesData((Type.NORMAL, Type.GRASS), 60, 60, 50, 40, 50, 75, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=67),
    Species.SAWSBUCK: SpeciesData((Type.NORMAL, Type.GRASS), 80, 100, 70, 60, 70, 95, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.SAWSBUCK_SUMMER: SpeciesData((Type.NORMAL, Type.GRASS), 80, 100, 70, 60, 70, 95, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.SAWSBUCK_AUTUMN: SpeciesData((Type.NORMAL, Type.GRASS), 80, 100, 70, 60, 70, 95, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.SAWSBUCK_WINTER: SpeciesData((Type.NORMAL, Type.GRASS), 80, 100, 70, 60, 70, 95, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.EMOLGA: SpeciesData((Type.ELECTRIC, Type.FLYING), 55, 75, 60, 75, 60, 103, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=150),
    Species.KARRABLAST: SpeciesData((Type.BUG,), 50, 75, 45, 40, 45, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=63),
    Species.ESCAVALIER: SpeciesData((Type.BUG, Type.STEEL), 70, 135, 105, 60, 105, 20, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.FOONGUS: SpeciesData((Type.GRASS, Type.POISON), 69, 55, 45, 55, 55, 15, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=59),
    Species.AMOONGUSS: SpeciesData((Type.GRASS, Type.POISON), 114, 85, 70, 85, 80, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=162),
    Species.FRILLISH: SpeciesData((Type.WATER, Type.GHOST), 55, 40, 50, 65, 85, 40, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=67),
    Species.JELLICENT: SpeciesData((Type.WATER, Type.GHOST), 100, 60, 70, 85, 105, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.ALOMOMOLA: SpeciesData((Type.WATER,), 165, 75, 80, 40, 45, 65, 0.5, growth_rate=GrowthRate.FAST, exp_yield=165),
    Species.JOLTIK: SpeciesData((Type.BUG, Type.ELECTRIC), 50, 47, 50, 57, 50, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=64),
    Species.GALVANTULA: SpeciesData((Type.BUG, Type.ELECTRIC), 70, 77, 60, 97, 60, 108, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.FERROSEED: SpeciesData((Type.GRASS, Type.STEEL), 44, 50, 91, 24, 86, 10, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.FERROTHORN: SpeciesData((Type.GRASS, Type.STEEL), 74, 94, 131, 54, 116, 20, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=171),
    Species.KLINK: SpeciesData((Type.STEEL,), 40, 55, 70, 45, 60, 30, None, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=60),
    Species.KLANG: SpeciesData((Type.STEEL,), 60, 80, 95, 70, 85, 50, None, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=154),
    Species.KLINKLANG: SpeciesData((Type.STEEL,), 60, 100, 115, 70, 85, 90, None, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=260),
    Species.TYNAMO: SpeciesData((Type.ELECTRIC,), 35, 55, 40, 45, 40, 60, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=55),
    Species.EELEKTRIK: SpeciesData((Type.ELECTRIC,), 65, 85, 70, 75, 70, 40, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=142),
    Species.EELEKTROSS: SpeciesData((Type.ELECTRIC,), 85, 115, 80, 105, 80, 50, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=258),
    Species.ELGYEM: SpeciesData((Type.PSYCHIC,), 55, 55, 55, 85, 55, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=67),
    Species.BEHEEYEM: SpeciesData((Type.PSYCHIC,), 75, 75, 75, 125, 95, 40, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=170),
    Species.LITWICK: SpeciesData((Type.GHOST, Type.FIRE), 50, 30, 55, 65, 55, 20, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=55),
    Species.LAMPENT: SpeciesData((Type.GHOST, Type.FIRE), 60, 40, 60, 95, 60, 55, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=130),
    Species.CHANDELURE: SpeciesData((Type.GHOST, Type.FIRE), 60, 55, 90, 145, 90, 80, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=260),
    Species.AXEW: SpeciesData((Type.DRAGON,), 46, 87, 60, 30, 40, 57, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=64),
    Species.FRAXURE: SpeciesData((Type.DRAGON,), 66, 117, 70, 40, 50, 67, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=144),
    Species.HAXORUS: SpeciesData((Type.DRAGON,), 76, 147, 90, 60, 70, 97, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=270),
    Species.CUBCHOO: SpeciesData((Type.ICE,), 55, 70, 40, 60, 40, 40, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.BEARTIC: SpeciesData((Type.ICE,), 95, 130, 80, 70, 80, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=177),
    Species.CRYOGONAL: SpeciesData((Type.ICE,), 80, 50, 50, 95, 135, 105, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=180),
    Species.SHELMET: SpeciesData((Type.BUG,), 50, 40, 85, 40, 65, 25, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.ACCELGOR: SpeciesData((Type.BUG,), 80, 70, 40, 100, 60, 145, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.STUNFISK: SpeciesData((Type.GROUND, Type.ELECTRIC), 109, 66, 84, 81, 99, 32, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.STUNFISK_GALAR: SpeciesData((Type.GROUND, Type.STEEL), 109, 81, 99, 66, 84, 32, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.MIENFOO: SpeciesData((Type.FIGHTING,), 45, 85, 50, 55, 50, 65, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=70),
    Species.MIENSHAO: SpeciesData((Type.FIGHTING,), 65, 125, 60, 95, 60, 105, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=179),
    Species.DRUDDIGON: SpeciesData((Type.DRAGON,), 77, 120, 90, 60, 90, 48, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=170),
    Species.GOLETT: SpeciesData((Type.GROUND, Type.GHOST), 59, 74, 50, 35, 50, 35, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.GOLURK: SpeciesData((Type.GROUND, Type.GHOST), 89, 124, 80, 55, 80, 55, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=169),
    Species.PAWNIARD: SpeciesData((Type.DARK, Type.STEEL), 45, 85, 70, 40, 40, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=68),
    Species.BISHARP: SpeciesData((Type.DARK, Type.STEEL), 65, 125, 100, 60, 70, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.BOUFFALANT: SpeciesData((Type.NORMAL,), 95, 110, 95, 40, 95, 55, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.RUFFLET: SpeciesData((Type.NORMAL, Type.FLYING), 70, 83, 50, 37, 50, 60, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=70),
    Species.BRAVIARY: SpeciesData((Type.NORMAL, Type.FLYING), 100, 123, 75, 57, 75, 80, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=179),
    Species.BRAVIARY_HISUI: SpeciesData((Type.PSYCHIC, Type.FLYING), 110, 83, 70, 112, 70, 65, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=179),
    Species.VULLABY: SpeciesData((Type.DARK, Type.FLYING), 70, 55, 75, 45, 65, 60, 0.0, growth_rate=GrowthRate.SLOW, exp_yield=74),
    Species.MANDIBUZZ: SpeciesData((Type.DARK, Type.FLYING), 110, 65, 105, 55, 95, 80, 0.0, growth_rate=GrowthRate.SLOW, exp_yield=179),
    Species.HEATMOR: SpeciesData((Type.FIRE,), 85, 97, 66, 105, 66, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=169),
    Species.DURANT: SpeciesData((Type.BUG, Type.STEEL), 58, 109, 112, 48, 48, 109, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=169),
    Species.DEINO: SpeciesData((Type.DARK, Type.DRAGON), 52, 65, 50, 45, 50, 38, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=60),
    Species.ZWEILOUS: SpeciesData((Type.DARK, Type.DRAGON), 72, 85, 70, 65, 70, 58, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=147),
    Species.HYDREIGON: SpeciesData((Type.DARK, Type.DRAGON), 92, 105, 90, 125, 90, 98, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.LARVESTA: SpeciesData((Type.BUG, Type.FIRE), 55, 85, 55, 50, 55, 60, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=72),
    Species.VOLCARONA: SpeciesData((Type.BUG, Type.FIRE), 85, 60, 65, 135, 105, 100, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=275),
    Species.COBALION: SpeciesData((Type.STEEL, Type.FIGHTING), 91, 90, 129, 90, 72, 108, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.TERRAKION: SpeciesData((Type.ROCK, Type.FIGHTING), 91, 129, 90, 72, 90, 108, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.VIRIZION: SpeciesData((Type.GRASS, Type.FIGHTING), 91, 90, 72, 90, 129, 108, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.TORNADUS: SpeciesData((Type.FLYING,), 79, 115, 70, 125, 80, 111, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.TORNADUS_THERIAN: SpeciesData((Type.FLYING,), 79, 100, 80, 110, 90, 121, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.THUNDURUS: SpeciesData((Type.ELECTRIC, Type.FLYING), 79, 115, 70, 125, 80, 111, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.THUNDURUS_THERIAN: SpeciesData((Type.ELECTRIC, Type.FLYING), 79, 105, 70, 145, 80, 101, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.RESHIRAM: SpeciesData((Type.DRAGON, Type.FIRE), 100, 120, 100, 150, 120, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.ZEKROM: SpeciesData((Type.DRAGON, Type.ELECTRIC), 100, 150, 120, 120, 100, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.LANDORUS: SpeciesData((Type.GROUND, Type.FLYING), 89, 125, 90, 115, 80, 101, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.LANDORUS_THERIAN: SpeciesData((Type.GROUND, Type.FLYING), 89, 145, 90, 105, 80, 91, 1.0, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.KYUREM: SpeciesData((Type.DRAGON, Type.ICE), 125, 130, 90, 130, 90, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=330),
    Species.KYUREM_BLACK: SpeciesData((Type.DRAGON, Type.ICE), 125, 170, 100, 120, 90, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=350),
    Species.KYUREM_WHITE: SpeciesData((Type.DRAGON, Type.ICE), 125, 120, 90, 170, 100, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=350),
    Species.KELDEO: SpeciesData((Type.WATER, Type.FIGHTING), 91, 72, 90, 129, 90, 108, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.KELDEO_RESOLUTE: SpeciesData((Type.WATER, Type.FIGHTING), 91, 72, 90, 129, 90, 108, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.MELOETTA: SpeciesData((Type.NORMAL, Type.PSYCHIC), 100, 77, 77, 128, 128, 90, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.MELOETTA_PIROUETTE: SpeciesData((Type.NORMAL, Type.FIGHTING), 100, 128, 90, 77, 77, 128, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.GENESECT: SpeciesData((Type.BUG, Type.STEEL), 71, 120, 95, 120, 95, 99, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.GENESECT_DOUSE: SpeciesData((Type.BUG, Type.STEEL), 71, 120, 95, 120, 95, 99, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.GENESECT_SHOCK: SpeciesData((Type.BUG, Type.STEEL), 71, 120, 95, 120, 95, 99, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.GENESECT_BURN: SpeciesData((Type.BUG, Type.STEEL), 71, 120, 95, 120, 95, 99, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.GENESECT_CHILL: SpeciesData((Type.BUG, Type.STEEL), 71, 120, 95, 120, 95, 99, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.CHESPIN: SpeciesData((Type.GRASS,), 56, 61, 65, 48, 45, 38, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=63),
    Species.QUILLADIN: SpeciesData((Type.GRASS,), 61, 78, 95, 56, 58, 57, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.CHESNAUGHT: SpeciesData((Type.GRASS, Type.FIGHTING), 88, 107, 122, 74, 75, 64, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.FENNEKIN: SpeciesData((Type.FIRE,), 40, 45, 40, 62, 60, 60, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=61),
    Species.BRAIXEN: SpeciesData((Type.FIRE,), 59, 59, 58, 90, 70, 73, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=143),
    Species.DELPHOX: SpeciesData((Type.FIRE, Type.PSYCHIC), 75, 69, 72, 114, 100, 104, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=267),
    Species.FROAKIE: SpeciesData((Type.WATER,), 41, 56, 40, 62, 44, 71, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=63),
    Species.FROGADIER: SpeciesData((Type.WATER,), 54, 63, 52, 83, 56, 97, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=142),
    Species.GRENINJA: SpeciesData((Type.WATER, Type.DARK), 72, 95, 67, 103, 71, 122, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.GRENINJA_BOND: SpeciesData((Type.WATER, Type.DARK), 72, 95, 67, 103, 71, 122, 1.0, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.GRENINJA_ASH: SpeciesData((Type.WATER, Type.DARK), 72, 145, 67, 153, 71, 132, 1.0, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=320),
    Species.BUNNELBY: SpeciesData((Type.NORMAL,), 38, 36, 38, 32, 36, 57, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=47),
    Species.DIGGERSBY: SpeciesData((Type.NORMAL, Type.GROUND), 85, 56, 77, 50, 77, 78, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=148),
    Species.FLETCHLING: SpeciesData((Type.NORMAL, Type.FLYING), 45, 50, 43, 40, 38, 62, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=56),
    Species.FLETCHINDER: SpeciesData((Type.FIRE, Type.FLYING), 62, 73, 55, 56, 52, 84, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=134),
    Species.TALONFLAME: SpeciesData((Type.FIRE, Type.FLYING), 78, 81, 71, 74, 69, 126, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=175),
    Species.SCATTERBUG: SpeciesData((Type.BUG,), 38, 35, 40, 27, 25, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=40),
    Species.SPEWPA: SpeciesData((Type.BUG,), 45, 22, 60, 27, 30, 29, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=75),
    Species.VIVILLON: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_1: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_2: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_3: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_4: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_5: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_6: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_7: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_8: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_9: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_10: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_11: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_12: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_13: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_14: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_15: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_16: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_17: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_18: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.VIVILLON_19: SpeciesData((Type.BUG, Type.FLYING), 80, 52, 50, 90, 50, 89, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=206),
    Species.LITLEO: SpeciesData((Type.FIRE, Type.NORMAL), 62, 50, 58, 73, 54, 72, 0.125, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=74),
    Species.PYROAR: SpeciesData((Type.FIRE, Type.NORMAL), 86, 68, 72, 109, 66, 106, 0.125, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=177),
    Species.FLABE_U0301BE_U0301: SpeciesData((Type.FAIRY,), 44, 38, 39, 61, 79, 42, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.FLABE_U0301BE_U0301_1: SpeciesData((Type.FAIRY,), 44, 38, 39, 61, 79, 42, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.FLABE_U0301BE_U0301_2: SpeciesData((Type.FAIRY,), 44, 38, 39, 61, 79, 42, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.FLABE_U0301BE_U0301_3: SpeciesData((Type.FAIRY,), 44, 38, 39, 61, 79, 42, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.FLABE_U0301BE_U0301_4: SpeciesData((Type.FAIRY,), 44, 38, 39, 61, 79, 42, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.FLOETTE: SpeciesData((Type.FAIRY,), 54, 45, 47, 75, 98, 52, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=130),
    Species.FLOETTE_1: SpeciesData((Type.FAIRY,), 54, 45, 47, 75, 98, 52, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=130),
    Species.FLOETTE_2: SpeciesData((Type.FAIRY,), 54, 45, 47, 75, 98, 52, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=130),
    Species.FLOETTE_3: SpeciesData((Type.FAIRY,), 54, 45, 47, 75, 98, 52, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=130),
    Species.FLOETTE_4: SpeciesData((Type.FAIRY,), 54, 45, 47, 75, 98, 52, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=130),
    Species.FLOETTE_ETERNAL: SpeciesData((Type.FAIRY,), 74, 65, 67, 125, 128, 92, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=243),
    Species.FLORGES: SpeciesData((Type.FAIRY,), 78, 65, 68, 112, 154, 75, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=276),
    Species.FLORGES_1: SpeciesData((Type.FAIRY,), 78, 65, 68, 112, 154, 75, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=276),
    Species.FLORGES_2: SpeciesData((Type.FAIRY,), 78, 65, 68, 112, 154, 75, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=276),
    Species.FLORGES_3: SpeciesData((Type.FAIRY,), 78, 65, 68, 112, 154, 75, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=276),
    Species.FLORGES_4: SpeciesData((Type.FAIRY,), 78, 65, 68, 112, 154, 75, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=276),
    Species.SKIDDO: SpeciesData((Type.GRASS,), 66, 65, 48, 62, 57, 52, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=70),
    Species.GOGOAT: SpeciesData((Type.GRASS,), 123, 100, 62, 97, 81, 68, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=186),
    Species.PANCHAM: SpeciesData((Type.FIGHTING,), 67, 82, 62, 46, 48, 43, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=70),
    Species.PANGORO: SpeciesData((Type.FIGHTING, Type.DARK), 95, 124, 78, 69, 71, 58, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.FURFROU: SpeciesData((Type.NORMAL,), 75, 80, 60, 65, 90, 102, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.FURFROU_1: SpeciesData((Type.NORMAL,), 75, 80, 60, 65, 90, 102, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.FURFROU_2: SpeciesData((Type.NORMAL,), 75, 80, 60, 65, 90, 102, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.FURFROU_3: SpeciesData((Type.NORMAL,), 75, 80, 60, 65, 90, 102, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.FURFROU_4: SpeciesData((Type.NORMAL,), 75, 80, 60, 65, 90, 102, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.FURFROU_5: SpeciesData((Type.NORMAL,), 75, 80, 60, 65, 90, 102, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.FURFROU_6: SpeciesData((Type.NORMAL,), 75, 80, 60, 65, 90, 102, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.FURFROU_7: SpeciesData((Type.NORMAL,), 75, 80, 60, 65, 90, 102, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.FURFROU_8: SpeciesData((Type.NORMAL,), 75, 80, 60, 65, 90, 102, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.FURFROU_9: SpeciesData((Type.NORMAL,), 75, 80, 60, 65, 90, 102, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.ESPURR: SpeciesData((Type.PSYCHIC,), 62, 48, 54, 63, 60, 68, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=71),
    Species.MEOWSTIC: SpeciesData((Type.PSYCHIC,), 74, 48, 76, 83, 81, 104, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=163),
    Species.MEOWSTIC_F: SpeciesData((Type.PSYCHIC,), 74, 48, 76, 83, 81, 104, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=163),
    Species.HONEDGE: SpeciesData((Type.STEEL, Type.GHOST), 45, 80, 100, 35, 37, 28, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=65),
    Species.DOUBLADE: SpeciesData((Type.STEEL, Type.GHOST), 59, 110, 150, 45, 49, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=157),
    Species.AEGISLASH: SpeciesData((Type.STEEL, Type.GHOST), 60, 50, 140, 50, 140, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=250),
    Species.AEGISLASH_BLADE: SpeciesData((Type.STEEL, Type.GHOST), 60, 140, 50, 140, 50, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=250),
    Species.SPRITZEE: SpeciesData((Type.FAIRY,), 78, 52, 60, 63, 65, 23, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=68),
    Species.AROMATISSE: SpeciesData((Type.FAIRY,), 101, 72, 72, 99, 89, 29, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=162),
    Species.SWIRLIX: SpeciesData((Type.FAIRY,), 62, 48, 66, 59, 57, 49, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=68),
    Species.SLURPUFF: SpeciesData((Type.FAIRY,), 82, 80, 86, 85, 75, 72, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.INKAY: SpeciesData((Type.DARK, Type.PSYCHIC), 53, 54, 53, 37, 46, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=58),
    Species.MALAMAR: SpeciesData((Type.DARK, Type.PSYCHIC), 86, 92, 88, 68, 75, 73, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=169),
    Species.BINACLE: SpeciesData((Type.ROCK, Type.WATER), 42, 52, 67, 39, 56, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.BARBARACLE: SpeciesData((Type.ROCK, Type.WATER), 72, 105, 115, 54, 86, 68, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.SKRELP: SpeciesData((Type.POISON, Type.WATER), 50, 60, 60, 60, 60, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=64),
    Species.DRAGALGE: SpeciesData((Type.POISON, Type.DRAGON), 65, 75, 90, 97, 123, 44, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.CLAUNCHER: SpeciesData((Type.WATER,), 50, 53, 62, 58, 63, 44, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=66),
    Species.CLAWITZER: SpeciesData((Type.WATER,), 71, 73, 88, 120, 89, 59, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=100),
    Species.HELIOPTILE: SpeciesData((Type.ELECTRIC, Type.NORMAL), 44, 38, 33, 61, 43, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=58),
    Species.HELIOLISK: SpeciesData((Type.ELECTRIC, Type.NORMAL), 62, 55, 52, 109, 94, 109, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.TYRUNT: SpeciesData((Type.ROCK, Type.DRAGON), 58, 89, 77, 45, 45, 48, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=72),
    Species.TYRANTRUM: SpeciesData((Type.ROCK, Type.DRAGON), 82, 121, 119, 69, 59, 71, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=182),
    Species.AMAURA: SpeciesData((Type.ROCK, Type.ICE), 77, 59, 50, 67, 63, 46, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=72),
    Species.AURORUS: SpeciesData((Type.ROCK, Type.ICE), 123, 77, 72, 99, 92, 58, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=104),
    Species.SYLVEON: SpeciesData((Type.FAIRY,), 95, 65, 65, 110, 130, 60, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=184),
    Species.HAWLUCHA: SpeciesData((Type.FIGHTING, Type.FLYING), 78, 92, 75, 74, 63, 118, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.DEDENNE: SpeciesData((Type.ELECTRIC, Type.FAIRY), 67, 58, 57, 81, 67, 101, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=151),
    Species.CARBINK: SpeciesData((Type.ROCK, Type.FAIRY), 50, 50, 150, 50, 150, 50, None, growth_rate=GrowthRate.SLOW, exp_yield=100),
    Species.GOOMY: SpeciesData((Type.DRAGON,), 45, 50, 35, 55, 75, 40, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=60),
    Species.SLIGGOO: SpeciesData((Type.DRAGON,), 68, 75, 53, 83, 113, 60, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=158),
    Species.SLIGGOO_HISUI: SpeciesData((Type.STEEL, Type.DRAGON), 58, 75, 83, 83, 113, 40, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=158),
    Species.GOODRA: SpeciesData((Type.DRAGON,), 90, 100, 70, 110, 150, 80, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.GOODRA_HISUI: SpeciesData((Type.STEEL, Type.DRAGON), 80, 100, 100, 110, 150, 60, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.KLEFKI: SpeciesData((Type.STEEL, Type.FAIRY), 57, 80, 91, 80, 87, 75, 0.5, growth_rate=GrowthRate.FAST, exp_yield=165),
    Species.PHANTUMP: SpeciesData((Type.GHOST, Type.GRASS), 43, 70, 48, 50, 60, 38, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=62),
    Species.TREVENANT: SpeciesData((Type.GHOST, Type.GRASS), 85, 110, 76, 65, 82, 56, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.PUMPKABOO: SpeciesData((Type.GHOST, Type.GRASS), 49, 66, 70, 44, 55, 51, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=67),
    Species.PUMPKABOO_SMALL: SpeciesData((Type.GHOST, Type.GRASS), 44, 66, 70, 44, 55, 56, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=67),
    Species.PUMPKABOO_LARGE: SpeciesData((Type.GHOST, Type.GRASS), 54, 66, 70, 44, 55, 46, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=67),
    Species.PUMPKABOO_SUPER: SpeciesData((Type.GHOST, Type.GRASS), 59, 66, 70, 44, 55, 41, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=67),
    Species.GOURGEIST: SpeciesData((Type.GHOST, Type.GRASS), 65, 90, 122, 58, 75, 84, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.GOURGEIST_SMALL: SpeciesData((Type.GHOST, Type.GRASS), 55, 85, 122, 58, 75, 99, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.GOURGEIST_LARGE: SpeciesData((Type.GHOST, Type.GRASS), 75, 95, 122, 58, 75, 69, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.GOURGEIST_SUPER: SpeciesData((Type.GHOST, Type.GRASS), 85, 100, 122, 58, 75, 54, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.BERGMITE: SpeciesData((Type.ICE,), 55, 69, 85, 32, 35, 28, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.AVALUGG: SpeciesData((Type.ICE,), 95, 117, 184, 44, 46, 28, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=180),
    Species.AVALUGG_HISUI: SpeciesData((Type.ICE, Type.ROCK), 95, 127, 184, 34, 36, 38, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=180),
    Species.NOIBAT: SpeciesData((Type.FLYING, Type.DRAGON), 40, 30, 35, 45, 40, 55, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=49),
    Species.NOIVERN: SpeciesData((Type.FLYING, Type.DRAGON), 85, 70, 80, 97, 80, 123, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=187),
    Species.XERNEAS: SpeciesData((Type.FAIRY,), 126, 131, 95, 131, 98, 99, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.XERNEAS_NEUTRAL: SpeciesData((Type.FAIRY,), 126, 131, 95, 131, 98, 99, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.YVELTAL: SpeciesData((Type.DARK, Type.FLYING), 126, 131, 95, 131, 98, 99, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.ZYGARDE: SpeciesData((Type.DRAGON, Type.GROUND), 108, 100, 121, 81, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.ZYGARDE_AURA_BREAK: SpeciesData((Type.DRAGON, Type.GROUND), 108, 100, 121, 81, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.ZYGARDE_10: SpeciesData((Type.DRAGON, Type.GROUND), 54, 100, 71, 61, 85, 115, None, growth_rate=GrowthRate.SLOW, exp_yield=243),
    Species.ZYGARDE_10_AURA_BREAK: SpeciesData((Type.DRAGON, Type.GROUND), 54, 100, 71, 61, 85, 115, None, growth_rate=GrowthRate.SLOW, exp_yield=243),
    Species.ZYGARDE_COMPLETE: SpeciesData((Type.DRAGON, Type.GROUND), 216, 100, 121, 91, 95, 85, None, growth_rate=GrowthRate.SLOW, exp_yield=354),
    Species.DIANCIE: SpeciesData((Type.ROCK, Type.FAIRY), 50, 100, 150, 100, 150, 50, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.DIANCIE_MEGA: SpeciesData((Type.ROCK, Type.FAIRY), 50, 160, 110, 160, 110, 110, None, growth_rate=GrowthRate.SLOW, exp_yield=350),
    Species.HOOPA: SpeciesData((Type.PSYCHIC, Type.GHOST), 80, 110, 60, 150, 130, 70, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.HOOPA_UNBOUND: SpeciesData((Type.PSYCHIC, Type.DARK), 80, 160, 60, 170, 130, 80, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.VOLCANION: SpeciesData((Type.FIRE, Type.WATER), 80, 110, 120, 130, 90, 70, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.ROWLET: SpeciesData((Type.GRASS, Type.FLYING), 68, 55, 55, 50, 50, 42, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=64),
    Species.DARTRIX: SpeciesData((Type.GRASS, Type.FLYING), 78, 75, 75, 70, 70, 52, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=147),
    Species.DECIDUEYE: SpeciesData((Type.GRASS, Type.GHOST), 78, 107, 75, 100, 100, 70, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.DECIDUEYE_HISUI: SpeciesData((Type.GRASS, Type.FIGHTING), 88, 112, 80, 95, 95, 60, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.LITTEN: SpeciesData((Type.FIRE,), 45, 65, 40, 60, 40, 70, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=64),
    Species.TORRACAT: SpeciesData((Type.FIRE,), 65, 85, 50, 80, 50, 90, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=147),
    Species.INCINEROAR: SpeciesData((Type.FIRE, Type.DARK), 95, 115, 90, 80, 90, 60, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.POPPLIO: SpeciesData((Type.WATER,), 50, 54, 54, 66, 56, 40, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=64),
    Species.BRIONNE: SpeciesData((Type.WATER,), 60, 69, 69, 91, 81, 50, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=147),
    Species.PRIMARINA: SpeciesData((Type.WATER, Type.FAIRY), 80, 74, 74, 126, 116, 60, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.PIKIPEK: SpeciesData((Type.NORMAL, Type.FLYING), 35, 75, 30, 30, 30, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=53),
    Species.TRUMBEAK: SpeciesData((Type.NORMAL, Type.FLYING), 55, 85, 50, 40, 50, 75, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=124),
    Species.TOUCANNON: SpeciesData((Type.NORMAL, Type.FLYING), 80, 120, 75, 75, 75, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=243),
    Species.YUNGOOS: SpeciesData((Type.NORMAL,), 48, 70, 30, 30, 30, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=51),
    Species.GUMSHOOS: SpeciesData((Type.NORMAL,), 88, 110, 60, 55, 60, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=146),
    Species.GRUBBIN: SpeciesData((Type.BUG,), 47, 62, 45, 55, 45, 46, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=60),
    Species.CHARJABUG: SpeciesData((Type.BUG, Type.ELECTRIC), 57, 82, 95, 55, 75, 36, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=140),
    Species.VIKAVOLT: SpeciesData((Type.BUG, Type.ELECTRIC), 77, 70, 90, 145, 75, 43, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=250),
    Species.CRABRAWLER: SpeciesData((Type.FIGHTING,), 47, 82, 57, 42, 47, 63, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=68),
    Species.CRABOMINABLE: SpeciesData((Type.FIGHTING, Type.ICE), 97, 132, 77, 62, 67, 43, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=167),
    Species.ORICORIO: SpeciesData((Type.FIRE, Type.FLYING), 75, 70, 70, 98, 70, 93, 0.25, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=167),
    Species.ORICORIO_POM_POM: SpeciesData((Type.ELECTRIC, Type.FLYING), 75, 70, 70, 98, 70, 93, 0.25, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=167),
    Species.ORICORIO_PA_U: SpeciesData((Type.PSYCHIC, Type.FLYING), 75, 70, 70, 98, 70, 93, 0.25, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=167),
    Species.ORICORIO_SENSU: SpeciesData((Type.GHOST, Type.FLYING), 75, 70, 70, 98, 70, 93, 0.25, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=167),
    Species.CUTIEFLY: SpeciesData((Type.BUG, Type.FAIRY), 40, 45, 40, 55, 40, 84, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.RIBOMBEE: SpeciesData((Type.BUG, Type.FAIRY), 60, 55, 60, 95, 70, 124, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=162),
    Species.ROCKRUFF: SpeciesData((Type.ROCK,), 45, 65, 40, 30, 40, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=56),
    Species.ROCKRUFF_DUSK: SpeciesData((Type.ROCK,), 45, 65, 40, 30, 40, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=56),
    Species.LYCANROC: SpeciesData((Type.ROCK,), 75, 115, 65, 55, 65, 112, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=170),
    Species.LYCANROC_MIDNIGHT: SpeciesData((Type.ROCK,), 85, 115, 75, 55, 75, 82, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=170),
    Species.LYCANROC_DUSK: SpeciesData((Type.ROCK,), 75, 117, 65, 55, 65, 110, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=170),
    Species.WISHIWASHI: SpeciesData((Type.WATER,), 45, 20, 20, 25, 25, 40, 0.5, growth_rate=GrowthRate.FAST, exp_yield=61),
    Species.WISHIWASHI_SCHOOL: SpeciesData((Type.WATER,), 45, 140, 130, 140, 135, 30, 0.5, growth_rate=GrowthRate.FAST, exp_yield=217),
    Species.MAREANIE: SpeciesData((Type.POISON, Type.WATER), 50, 53, 62, 43, 52, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.TOXAPEX: SpeciesData((Type.POISON, Type.WATER), 50, 63, 152, 53, 142, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.MUDBRAY: SpeciesData((Type.GROUND,), 70, 100, 70, 45, 55, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=77),
    Species.MUDSDALE: SpeciesData((Type.GROUND,), 100, 125, 100, 55, 85, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.DEWPIDER: SpeciesData((Type.WATER, Type.BUG), 38, 40, 52, 40, 72, 27, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=54),
    Species.ARAQUANID: SpeciesData((Type.WATER, Type.BUG), 68, 70, 92, 50, 132, 42, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=159),
    Species.FOMANTIS: SpeciesData((Type.GRASS,), 40, 55, 35, 50, 35, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=50),
    Species.LURANTIS: SpeciesData((Type.GRASS,), 70, 105, 90, 80, 90, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.MORELULL: SpeciesData((Type.GRASS, Type.FAIRY), 40, 35, 55, 65, 75, 15, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=57),
    Species.SHIINOTIC: SpeciesData((Type.GRASS, Type.FAIRY), 60, 45, 80, 90, 100, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=142),
    Species.SALANDIT: SpeciesData((Type.POISON, Type.FIRE), 48, 44, 40, 71, 40, 77, 0.875, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=64),
    Species.SALAZZLE: SpeciesData((Type.POISON, Type.FIRE), 68, 64, 60, 111, 60, 117, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.STUFFUL: SpeciesData((Type.NORMAL, Type.FIGHTING), 70, 75, 50, 45, 50, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=68),
    Species.BEWEAR: SpeciesData((Type.NORMAL, Type.FIGHTING), 120, 125, 80, 55, 60, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.BOUNSWEET: SpeciesData((Type.GRASS,), 42, 30, 38, 30, 38, 32, 0.0, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=42),
    Species.STEENEE: SpeciesData((Type.GRASS,), 52, 40, 48, 40, 48, 62, 0.0, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=102),
    Species.TSAREENA: SpeciesData((Type.GRASS,), 72, 120, 98, 50, 98, 72, 0.0, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=255),
    Species.COMFEY: SpeciesData((Type.FAIRY,), 51, 52, 90, 82, 110, 100, 0.25, growth_rate=GrowthRate.FAST, exp_yield=170),
    Species.ORANGURU: SpeciesData((Type.NORMAL, Type.PSYCHIC), 90, 60, 80, 90, 110, 60, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=172),
    Species.PASSIMIAN: SpeciesData((Type.FIGHTING,), 100, 120, 90, 40, 60, 80, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=172),
    Species.WIMPOD: SpeciesData((Type.BUG, Type.WATER), 25, 35, 40, 20, 30, 80, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=46),
    Species.GOLISOPOD: SpeciesData((Type.BUG, Type.WATER), 75, 125, 140, 60, 90, 40, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=186),
    Species.SANDYGAST: SpeciesData((Type.GHOST, Type.GROUND), 55, 55, 80, 70, 45, 15, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=64),
    Species.PALOSSAND: SpeciesData((Type.GHOST, Type.GROUND), 85, 75, 110, 100, 75, 35, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=168),
    Species.PYUKUMUKU: SpeciesData((Type.WATER,), 55, 60, 130, 30, 130, 5, 0.5, growth_rate=GrowthRate.FAST, exp_yield=144),
    Species.TYPE_NULL: SpeciesData((Type.NORMAL,), 95, 95, 95, 95, 95, 59, None, growth_rate=GrowthRate.SLOW, exp_yield=107),
    Species.SILVALLY: SpeciesData((Type.NORMAL,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_BUG: SpeciesData((Type.BUG,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_DARK: SpeciesData((Type.DARK,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_DRAGON: SpeciesData((Type.DRAGON,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_ELECTRIC: SpeciesData((Type.ELECTRIC,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_FAIRY: SpeciesData((Type.FAIRY,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_FIGHTING: SpeciesData((Type.FIGHTING,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_FIRE: SpeciesData((Type.FIRE,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_FLYING: SpeciesData((Type.FLYING,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_GHOST: SpeciesData((Type.GHOST,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_GRASS: SpeciesData((Type.GRASS,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_GROUND: SpeciesData((Type.GROUND,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_ICE: SpeciesData((Type.ICE,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_POISON: SpeciesData((Type.POISON,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_PSYCHIC: SpeciesData((Type.PSYCHIC,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_ROCK: SpeciesData((Type.ROCK,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_STEEL: SpeciesData((Type.STEEL,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.SILVALLY_WATER: SpeciesData((Type.WATER,), 95, 95, 95, 95, 95, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.MINIOR: SpeciesData((Type.ROCK, Type.FLYING), 60, 100, 60, 100, 60, 120, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.MINIOR_METEOR: SpeciesData((Type.ROCK, Type.FLYING), 60, 60, 100, 60, 100, 60, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=154),
    Species.KOMALA: SpeciesData((Type.NORMAL,), 65, 115, 65, 75, 95, 65, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=168),
    Species.TURTONATOR: SpeciesData((Type.FIRE, Type.DRAGON), 60, 78, 135, 91, 85, 36, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=170),
    Species.TOGEDEMARU: SpeciesData((Type.ELECTRIC, Type.STEEL), 65, 98, 63, 40, 73, 96, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=152),
    Species.MIMIKYU: SpeciesData((Type.GHOST, Type.FAIRY), 55, 90, 80, 50, 105, 96, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=167),
    Species.MIMIKYU_BUSTED: SpeciesData((Type.GHOST, Type.FAIRY), 55, 90, 80, 50, 105, 96, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=167),
    Species.BRUXISH: SpeciesData((Type.WATER, Type.PSYCHIC), 68, 105, 70, 70, 70, 92, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.DRAMPA: SpeciesData((Type.NORMAL, Type.DRAGON), 78, 60, 85, 135, 91, 36, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=170),
    Species.DHELMISE: SpeciesData((Type.GHOST, Type.GRASS), 70, 131, 100, 86, 90, 40, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=181),
    Species.JANGMO_O: SpeciesData((Type.DRAGON,), 45, 55, 65, 45, 45, 45, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=60),
    Species.HAKAMO_O: SpeciesData((Type.DRAGON, Type.FIGHTING), 55, 75, 90, 65, 70, 65, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=147),
    Species.KOMMO_O: SpeciesData((Type.DRAGON, Type.FIGHTING), 75, 110, 125, 100, 105, 85, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.TAPU_KOKO: SpeciesData((Type.ELECTRIC, Type.FAIRY), 70, 115, 85, 95, 75, 130, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.TAPU_LELE: SpeciesData((Type.PSYCHIC, Type.FAIRY), 70, 85, 75, 130, 115, 95, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.TAPU_BULU: SpeciesData((Type.GRASS, Type.FAIRY), 70, 130, 115, 85, 95, 75, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.TAPU_FINI: SpeciesData((Type.WATER, Type.FAIRY), 70, 75, 115, 95, 130, 85, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.COSMOG: SpeciesData((Type.PSYCHIC,), 43, 29, 31, 29, 31, 37, None, growth_rate=GrowthRate.SLOW, exp_yield=40),
    Species.COSMOEM: SpeciesData((Type.PSYCHIC,), 43, 29, 131, 29, 131, 37, None, growth_rate=GrowthRate.SLOW, exp_yield=140),
    Species.SOLGALEO: SpeciesData((Type.PSYCHIC, Type.STEEL), 137, 137, 107, 113, 89, 97, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.LUNALA: SpeciesData((Type.PSYCHIC, Type.GHOST), 137, 113, 89, 137, 107, 97, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.NIHILEGO: SpeciesData((Type.ROCK, Type.POISON), 109, 53, 47, 127, 131, 103, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.BUZZWOLE: SpeciesData((Type.BUG, Type.FIGHTING), 107, 139, 139, 53, 53, 79, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.PHEROMOSA: SpeciesData((Type.BUG, Type.FIGHTING), 71, 137, 37, 137, 37, 151, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.XURKITREE: SpeciesData((Type.ELECTRIC,), 83, 89, 71, 173, 71, 83, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.CELESTEELA: SpeciesData((Type.STEEL, Type.FLYING), 97, 101, 103, 107, 101, 61, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.KARTANA: SpeciesData((Type.GRASS, Type.STEEL), 59, 181, 131, 59, 31, 109, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.GUZZLORD: SpeciesData((Type.DARK, Type.DRAGON), 223, 101, 53, 97, 53, 43, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.NECROZMA: SpeciesData((Type.PSYCHIC,), 97, 107, 101, 127, 89, 79, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.NECROZMA_DUSK_MANE: SpeciesData((Type.PSYCHIC, Type.STEEL), 97, 157, 127, 113, 109, 77, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.NECROZMA_DAWN_WINGS: SpeciesData((Type.PSYCHIC, Type.GHOST), 97, 113, 109, 157, 127, 77, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.NECROZMA_ULTRA: SpeciesData((Type.PSYCHIC, Type.DRAGON), 97, 167, 97, 167, 97, 129, None, growth_rate=GrowthRate.SLOW, exp_yield=377),
    Species.MAGEARNA: SpeciesData((Type.STEEL, Type.FAIRY), 80, 95, 115, 130, 115, 65, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.MAGEARNA_ORIGINAL: SpeciesData((Type.STEEL, Type.FAIRY), 80, 95, 115, 130, 115, 65, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.MARSHADOW: SpeciesData((Type.FIGHTING, Type.GHOST), 90, 125, 80, 90, 90, 125, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.POIPOLE: SpeciesData((Type.POISON,), 67, 73, 67, 73, 67, 73, None, growth_rate=GrowthRate.SLOW, exp_yield=210),
    Species.NAGANADEL: SpeciesData((Type.POISON, Type.DRAGON), 73, 73, 73, 127, 73, 121, None, growth_rate=GrowthRate.SLOW, exp_yield=270),
    Species.STAKATAKA: SpeciesData((Type.ROCK, Type.STEEL), 61, 131, 211, 53, 101, 13, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.BLACEPHALON: SpeciesData((Type.FIRE, Type.GHOST), 53, 127, 53, 151, 79, 107, None, growth_rate=GrowthRate.SLOW, exp_yield=285),
    Species.ZERAORA: SpeciesData((Type.ELECTRIC,), 88, 112, 75, 102, 80, 143, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.MELTAN: SpeciesData((Type.STEEL,), 46, 65, 65, 55, 35, 34, None, growth_rate=GrowthRate.SLOW, exp_yield=150),
    Species.MELMETAL: SpeciesData((Type.STEEL,), 135, 143, 143, 80, 65, 34, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.GROOKEY: SpeciesData((Type.GRASS,), 50, 65, 50, 40, 40, 65, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.THWACKEY: SpeciesData((Type.GRASS,), 70, 85, 70, 55, 60, 80, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=147),
    Species.RILLABOOM: SpeciesData((Type.GRASS,), 100, 125, 90, 60, 70, 85, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.SCORBUNNY: SpeciesData((Type.FIRE,), 50, 71, 40, 40, 40, 69, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.RABOOT: SpeciesData((Type.FIRE,), 65, 86, 60, 55, 60, 94, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=147),
    Species.CINDERACE: SpeciesData((Type.FIRE,), 80, 116, 75, 65, 75, 119, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.SOBBLE: SpeciesData((Type.WATER,), 50, 40, 40, 70, 40, 70, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.DRIZZILE: SpeciesData((Type.WATER,), 65, 60, 55, 95, 55, 90, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=147),
    Species.INTELEON: SpeciesData((Type.WATER,), 70, 85, 65, 125, 65, 120, 0.875, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=265),
    Species.SKWOVET: SpeciesData((Type.NORMAL,), 70, 55, 55, 35, 35, 25, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=55),
    Species.GREEDENT: SpeciesData((Type.NORMAL,), 120, 95, 95, 55, 75, 20, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=161),
    Species.ROOKIDEE: SpeciesData((Type.FLYING,), 38, 47, 35, 33, 35, 57, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=49),
    Species.CORVISQUIRE: SpeciesData((Type.FLYING,), 68, 67, 55, 43, 55, 77, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=128),
    Species.CORVIKNIGHT: SpeciesData((Type.FLYING, Type.STEEL), 98, 87, 105, 53, 85, 67, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=248),
    Species.BLIPBUG: SpeciesData((Type.BUG,), 25, 20, 20, 25, 45, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=36),
    Species.DOTTLER: SpeciesData((Type.BUG, Type.PSYCHIC), 50, 35, 80, 50, 90, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=117),
    Species.ORBEETLE: SpeciesData((Type.BUG, Type.PSYCHIC), 60, 45, 110, 80, 120, 90, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=253),
    Species.NICKIT: SpeciesData((Type.DARK,), 40, 28, 28, 47, 52, 50, 0.5, growth_rate=GrowthRate.FAST, exp_yield=49),
    Species.THIEVUL: SpeciesData((Type.DARK,), 70, 58, 58, 87, 92, 90, 0.5, growth_rate=GrowthRate.FAST, exp_yield=159),
    Species.GOSSIFLEUR: SpeciesData((Type.GRASS,), 40, 40, 60, 40, 60, 10, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=50),
    Species.ELDEGOSS: SpeciesData((Type.GRASS,), 60, 50, 90, 80, 120, 60, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=161),
    Species.WOOLOO: SpeciesData((Type.NORMAL,), 42, 40, 55, 40, 45, 48, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=122),
    Species.DUBWOOL: SpeciesData((Type.NORMAL,), 72, 80, 100, 60, 90, 88, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=172),
    Species.CHEWTLE: SpeciesData((Type.WATER,), 50, 64, 50, 38, 38, 44, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=57),
    Species.DREDNAW: SpeciesData((Type.WATER, Type.ROCK), 90, 115, 90, 48, 68, 74, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=170),
    Species.YAMPER: SpeciesData((Type.ELECTRIC,), 59, 45, 50, 40, 50, 26, 0.5, growth_rate=GrowthRate.FAST, exp_yield=54),
    Species.BOLTUND: SpeciesData((Type.ELECTRIC,), 69, 90, 60, 90, 60, 121, 0.5, growth_rate=GrowthRate.FAST, exp_yield=172),
    Species.ROLYCOLY: SpeciesData((Type.ROCK,), 30, 40, 50, 40, 50, 30, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=48),
    Species.CARKOL: SpeciesData((Type.ROCK, Type.FIRE), 80, 60, 90, 60, 70, 50, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=144),
    Species.COALOSSAL: SpeciesData((Type.ROCK, Type.FIRE), 110, 80, 120, 80, 90, 30, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=255),
    Species.APPLIN: SpeciesData((Type.GRASS, Type.DRAGON), 40, 40, 80, 40, 40, 20, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=52),
    Species.FLAPPLE: SpeciesData((Type.GRASS, Type.DRAGON), 70, 110, 80, 95, 60, 70, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=170),
    Species.APPLETUN: SpeciesData((Type.GRASS, Type.DRAGON), 110, 85, 80, 100, 80, 30, 0.5, growth_rate=GrowthRate.ERRATIC, exp_yield=170),
    Species.SILICOBRA: SpeciesData((Type.GROUND,), 52, 57, 75, 35, 50, 46, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=63),
    Species.SANDACONDA: SpeciesData((Type.GROUND,), 72, 107, 125, 65, 70, 71, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=179),
    Species.CRAMORANT: SpeciesData((Type.FLYING, Type.WATER), 70, 85, 55, 85, 95, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.CRAMORANT_GULPING: SpeciesData((Type.FLYING, Type.WATER), 70, 85, 55, 85, 95, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.CRAMORANT_GORGING: SpeciesData((Type.FLYING, Type.WATER), 70, 85, 55, 85, 95, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.ARROKUDA: SpeciesData((Type.WATER,), 41, 63, 40, 40, 30, 66, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=56),
    Species.BARRASKEWDA: SpeciesData((Type.WATER,), 61, 123, 60, 60, 50, 136, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=172),
    Species.TOXEL: SpeciesData((Type.ELECTRIC, Type.POISON), 40, 38, 35, 54, 35, 40, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=48),
    Species.TOXTRICITY: SpeciesData((Type.ELECTRIC, Type.POISON), 75, 98, 70, 114, 70, 75, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=176),
    Species.TOXTRICITY_LOW_KEY: SpeciesData((Type.ELECTRIC, Type.POISON), 75, 98, 70, 114, 70, 75, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=176),
    Species.SIZZLIPEDE: SpeciesData((Type.FIRE, Type.BUG), 50, 65, 45, 50, 50, 45, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=61),
    Species.CENTISKORCH: SpeciesData((Type.FIRE, Type.BUG), 100, 115, 65, 90, 90, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=184),
    Species.CLOBBOPUS: SpeciesData((Type.FIGHTING,), 50, 68, 60, 50, 50, 32, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=62),
    Species.GRAPPLOCT: SpeciesData((Type.FIGHTING,), 80, 118, 90, 70, 80, 42, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=168),
    Species.SINISTEA: SpeciesData((Type.GHOST,), 40, 45, 45, 74, 54, 50, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=62),
    Species.SINISTEA_ANTIQUE: SpeciesData((Type.GHOST,), 40, 45, 45, 74, 54, 50, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=62),
    Species.POLTEAGEIST: SpeciesData((Type.GHOST,), 60, 65, 65, 134, 114, 70, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=178),
    Species.POLTEAGEIST_ANTIQUE: SpeciesData((Type.GHOST,), 60, 65, 65, 134, 114, 70, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=178),
    Species.HATENNA: SpeciesData((Type.PSYCHIC,), 42, 30, 45, 56, 53, 39, 0.0, growth_rate=GrowthRate.SLOW, exp_yield=53),
    Species.HATTREM: SpeciesData((Type.PSYCHIC,), 57, 40, 65, 86, 73, 49, 0.0, growth_rate=GrowthRate.SLOW, exp_yield=130),
    Species.HATTERENE: SpeciesData((Type.PSYCHIC, Type.FAIRY), 57, 90, 95, 136, 103, 29, 0.0, growth_rate=GrowthRate.SLOW, exp_yield=255),
    Species.IMPIDIMP: SpeciesData((Type.DARK, Type.FAIRY), 45, 45, 30, 55, 40, 50, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=53),
    Species.MORGREM: SpeciesData((Type.DARK, Type.FAIRY), 65, 60, 45, 75, 55, 70, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=130),
    Species.GRIMMSNARL: SpeciesData((Type.DARK, Type.FAIRY), 95, 120, 65, 95, 75, 60, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=255),
    Species.OBSTAGOON: SpeciesData((Type.DARK, Type.NORMAL), 93, 90, 101, 60, 81, 95, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=260),
    Species.PERRSERKER: SpeciesData((Type.STEEL,), 70, 110, 100, 50, 60, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=154),
    Species.CURSOLA: SpeciesData((Type.GHOST,), 60, 95, 50, 145, 130, 30, 0.25, growth_rate=GrowthRate.FAST, exp_yield=179),
    Species.SIRFETCH_U2019D: SpeciesData((Type.FIGHTING,), 62, 135, 95, 68, 82, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=177),
    Species.MR_RIME: SpeciesData((Type.ICE, Type.PSYCHIC), 80, 85, 75, 110, 100, 70, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=182),
    Species.RUNERIGUS: SpeciesData((Type.GROUND, Type.GHOST), 58, 95, 145, 50, 105, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=169),
    Species.MILCERY: SpeciesData((Type.FAIRY,), 45, 40, 40, 50, 61, 34, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=54),
    Species.ALCREMIE: SpeciesData((Type.FAIRY,), 65, 60, 75, 110, 121, 64, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.ALCREMIE_1: SpeciesData((Type.FAIRY,), 65, 60, 75, 110, 121, 64, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.ALCREMIE_2: SpeciesData((Type.FAIRY,), 65, 60, 75, 110, 121, 64, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.ALCREMIE_3: SpeciesData((Type.FAIRY,), 65, 60, 75, 110, 121, 64, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.ALCREMIE_4: SpeciesData((Type.FAIRY,), 65, 60, 75, 110, 121, 64, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.ALCREMIE_5: SpeciesData((Type.FAIRY,), 65, 60, 75, 110, 121, 64, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.ALCREMIE_6: SpeciesData((Type.FAIRY,), 65, 60, 75, 110, 121, 64, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.ALCREMIE_7: SpeciesData((Type.FAIRY,), 65, 60, 75, 110, 121, 64, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.ALCREMIE_8: SpeciesData((Type.FAIRY,), 65, 60, 75, 110, 121, 64, 0.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=173),
    Species.FALINKS: SpeciesData((Type.FIGHTING,), 65, 100, 100, 70, 60, 75, None, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=165),
    Species.PINCURCHIN: SpeciesData((Type.ELECTRIC,), 48, 101, 95, 91, 85, 15, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=152),
    Species.SNOM: SpeciesData((Type.ICE, Type.BUG), 30, 25, 35, 45, 30, 20, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=37),
    Species.FROSMOTH: SpeciesData((Type.ICE, Type.BUG), 70, 65, 60, 125, 90, 65, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=166),
    Species.STONJOURNER: SpeciesData((Type.ROCK,), 100, 125, 135, 20, 20, 70, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=165),
    Species.EISCUE: SpeciesData((Type.ICE,), 75, 80, 110, 65, 90, 50, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=165),
    Species.EISCUE_NOICE: SpeciesData((Type.ICE,), 75, 80, 70, 65, 50, 130, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=165),
    Species.INDEEDEE: SpeciesData((Type.PSYCHIC, Type.NORMAL), 60, 65, 55, 105, 95, 95, 1.0, growth_rate=GrowthRate.FAST, exp_yield=166),
    Species.INDEEDEE_F: SpeciesData((Type.PSYCHIC, Type.NORMAL), 70, 55, 65, 95, 105, 85, 0.0, growth_rate=GrowthRate.FAST, exp_yield=166),
    Species.MORPEKO: SpeciesData((Type.ELECTRIC, Type.DARK), 58, 95, 58, 70, 58, 97, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=153),
    Species.MORPEKO_HANGRY: SpeciesData((Type.ELECTRIC, Type.DARK), 58, 95, 58, 70, 58, 97, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=153),
    Species.CUFANT: SpeciesData((Type.STEEL,), 72, 80, 49, 40, 49, 40, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=66),
    Species.COPPERAJAH: SpeciesData((Type.STEEL,), 122, 130, 69, 80, 69, 30, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.DRACOZOLT: SpeciesData((Type.ELECTRIC, Type.DRAGON), 90, 100, 90, 80, 70, 75, None, growth_rate=GrowthRate.SLOW, exp_yield=177),
    Species.ARCTOZOLT: SpeciesData((Type.ELECTRIC, Type.ICE), 90, 100, 90, 90, 80, 55, None, growth_rate=GrowthRate.SLOW, exp_yield=177),
    Species.DRACOVISH: SpeciesData((Type.WATER, Type.DRAGON), 90, 90, 100, 70, 80, 75, None, growth_rate=GrowthRate.SLOW, exp_yield=177),
    Species.ARCTOVISH: SpeciesData((Type.WATER, Type.ICE), 90, 90, 100, 80, 90, 55, None, growth_rate=GrowthRate.SLOW, exp_yield=177),
    Species.DURALUDON: SpeciesData((Type.STEEL, Type.DRAGON), 70, 95, 115, 120, 50, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=187),
    Species.DREEPY: SpeciesData((Type.DRAGON, Type.GHOST), 28, 60, 30, 40, 30, 82, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=54),
    Species.DRAKLOAK: SpeciesData((Type.DRAGON, Type.GHOST), 68, 80, 50, 60, 50, 102, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=144),
    Species.DRAGAPULT: SpeciesData((Type.DRAGON, Type.GHOST), 88, 120, 75, 100, 75, 142, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.ZACIAN: SpeciesData((Type.FAIRY,), 92, 120, 115, 80, 115, 138, None, growth_rate=GrowthRate.SLOW, exp_yield=335),
    Species.ZACIAN_CROWNED: SpeciesData((Type.FAIRY, Type.STEEL), 92, 150, 115, 80, 115, 148, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ZAMAZENTA: SpeciesData((Type.FIGHTING,), 92, 120, 115, 80, 115, 138, None, growth_rate=GrowthRate.SLOW, exp_yield=335),
    Species.ZAMAZENTA_CROWNED: SpeciesData((Type.FIGHTING, Type.STEEL), 92, 120, 140, 80, 140, 128, None, growth_rate=GrowthRate.SLOW, exp_yield=360),
    Species.ETERNATUS: SpeciesData((Type.POISON, Type.DRAGON), 140, 85, 95, 145, 95, 130, None, growth_rate=GrowthRate.SLOW, exp_yield=345),
    Species.ETERNATUS_ETERNAMAX: SpeciesData((Type.POISON, Type.DRAGON), 255, 115, 250, 125, 250, 130, None, growth_rate=GrowthRate.SLOW, exp_yield=563),
    Species.KUBFU: SpeciesData((Type.FIGHTING,), 60, 90, 60, 53, 50, 72, 0.875, growth_rate=GrowthRate.SLOW, exp_yield=77),
    Species.URSHIFU: SpeciesData((Type.FIGHTING, Type.DARK), 100, 130, 100, 63, 60, 97, 0.875, growth_rate=GrowthRate.SLOW, exp_yield=275),
    Species.URSHIFU_RAPID_STRIKE: SpeciesData((Type.FIGHTING, Type.WATER), 100, 130, 100, 63, 60, 97, 0.875, growth_rate=GrowthRate.SLOW, exp_yield=275),
    Species.ZARUDE: SpeciesData((Type.DARK, Type.GRASS), 105, 120, 105, 70, 95, 105, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.ZARUDE_DADA: SpeciesData((Type.DARK, Type.GRASS), 105, 120, 105, 70, 95, 105, None, growth_rate=GrowthRate.SLOW, exp_yield=300),
    Species.REGIELEKI: SpeciesData((Type.ELECTRIC,), 80, 100, 50, 100, 50, 200, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.REGIDRAGO: SpeciesData((Type.DRAGON,), 200, 100, 50, 100, 50, 80, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.GLASTRIER: SpeciesData((Type.ICE,), 100, 145, 130, 65, 110, 30, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.SPECTRIER: SpeciesData((Type.GHOST,), 100, 65, 60, 145, 80, 130, None, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.CALYREX: SpeciesData((Type.PSYCHIC, Type.GRASS), 100, 80, 80, 80, 80, 80, None, growth_rate=GrowthRate.SLOW, exp_yield=250),
    Species.CALYREX_ICE: SpeciesData((Type.PSYCHIC, Type.ICE), 100, 165, 150, 85, 130, 50, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.CALYREX_SHADOW: SpeciesData((Type.PSYCHIC, Type.GHOST), 100, 85, 80, 165, 100, 150, None, growth_rate=GrowthRate.SLOW, exp_yield=340),
    Species.WYRDEER: SpeciesData((Type.NORMAL, Type.PSYCHIC), 103, 105, 72, 105, 75, 65, 0.5, growth_rate=GrowthRate.SLOW, exp_yield=184),
    Species.KLEAVOR: SpeciesData((Type.BUG, Type.ROCK), 70, 135, 95, 45, 70, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=175),
    Species.URSALUNA: SpeciesData((Type.GROUND, Type.NORMAL), 130, 140, 105, 45, 80, 50, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=193),
    Species.BASCULEGION: SpeciesData((Type.WATER, Type.GHOST), 120, 112, 65, 80, 75, 78, 1.0, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=186),
    Species.SNEASLER: SpeciesData((Type.FIGHTING, Type.POISON), 80, 130, 60, 40, 80, 120, 0.5, growth_rate=GrowthRate.MEDIUM_SLOW, exp_yield=179),
    Species.OVERQWIL: SpeciesData((Type.DARK, Type.POISON), 85, 115, 95, 65, 65, 85, 0.5, growth_rate=GrowthRate.MEDIUM_FAST, exp_yield=102),
    Species.ENAMORUS: SpeciesData((Type.FAIRY, Type.FLYING), 74, 115, 70, 135, 80, 106, 0.0, growth_rate=GrowthRate.SLOW, exp_yield=290),
    Species.ENAMORUS_THERIAN: SpeciesData((Type.FAIRY, Type.FLYING), 74, 115, 110, 135, 100, 46, 0.0, growth_rate=GrowthRate.SLOW, exp_yield=290),
}

# Import-time invariant: every species must have at least one valid Type.
for _species, _data in SPECIES_DATA.items():
    if not _data.types or not isinstance(_data.types, tuple) or not all(isinstance(_t, Type) for _t in _data.types):
        raise ValueError(f"Species {_species.name} has invalid types: {_data.types!r}")

# Species eligible for item bonuses or special mechanics, grouped by the item or mechanic.
LEEK_SPECIES: frozenset[Species] = frozenset({
    Species.FARFETCH_U2019D, Species.FARFETCH_U2019D_GALAR, Species.SIRFETCH_U2019D,
})

THICK_CLUB_SPECIES: frozenset[Species] = frozenset({
    Species.CUBONE, Species.MAROWAK, Species.MAROWAK_ALOLA,
})

PIKACHU_SPECIES: frozenset[Species] = frozenset({
    Species.PIKACHU, Species.PIKACHU_COSPLAY, Species.PIKACHU_ROCK_STAR, Species.PIKACHU_BELLE,
    Species.PIKACHU_POP_STAR, Species.PIKACHU_PHD, Species.PIKACHU_LIBRE, Species.PIKACHU_ORIGINAL,
    Species.PIKACHU_HOENN, Species.PIKACHU_SINNOH, Species.PIKACHU_UNOVA, Species.PIKACHU_KALOS,
    Species.PIKACHU_ALOLA, Species.PIKACHU_PARTNER,
    Species.PIKACHU_WORLD,
})

# Species that still have a further evolution (Eviolite holders get 1.5x Def and SpD)
UNEVOLVED_SPECIES: frozenset[Species] = frozenset({
    # Gen 1
    Species.BULBASAUR, Species.IVYSAUR, Species.CHARMANDER, Species.CHARMELEON,
    Species.SQUIRTLE, Species.WARTORTLE, Species.CATERPIE, Species.METAPOD,
    Species.WEEDLE, Species.KAKUNA, Species.PIDGEY, Species.PIDGEOTTO,
    Species.RATTATA, Species.RATTATA_ALOLA, Species.SPEAROW, Species.EKANS,
    Species.PIKACHU, Species.PIKACHU_COSPLAY, Species.PIKACHU_ROCK_STAR, Species.PIKACHU_BELLE,
    Species.PIKACHU_POP_STAR, Species.PIKACHU_PHD, Species.PIKACHU_LIBRE, Species.PIKACHU_ORIGINAL,
    Species.PIKACHU_HOENN, Species.PIKACHU_SINNOH, Species.PIKACHU_UNOVA, Species.PIKACHU_KALOS,
    Species.PIKACHU_ALOLA, Species.PIKACHU_PARTNER,
    Species.PIKACHU_WORLD, Species.SANDSHREW, Species.SANDSHREW_ALOLA,
    Species.NIDORAN_F, Species.NIDORINA, Species.NIDORAN_M, Species.NIDORINO,
    Species.CLEFAIRY, Species.VULPIX, Species.VULPIX_ALOLA, Species.JIGGLYPUFF,
    Species.ZUBAT, Species.GOLBAT, Species.ODDISH, Species.GLOOM,
    Species.PARAS, Species.VENONAT, Species.DIGLETT, Species.DIGLETT_ALOLA,
    Species.MEOWTH, Species.MEOWTH_ALOLA, Species.MEOWTH_GALAR,
    Species.PSYDUCK, Species.MANKEY, Species.GROWLITHE, Species.GROWLITHE_HISUI,
    Species.POLIWAG, Species.POLIWHIRL, Species.ABRA, Species.KADABRA,
    Species.MACHOP, Species.MACHOKE, Species.BELLSPROUT, Species.WEEPINBELL,
    Species.TENTACOOL, Species.GEODUDE, Species.GEODUDE_ALOLA, Species.GRAVELER, Species.GRAVELER_ALOLA,
    Species.PONYTA, Species.PONYTA_GALAR, Species.SLOWPOKE, Species.SLOWPOKE_GALAR,
    Species.MAGNEMITE, Species.MAGNETON, Species.FARFETCH_U2019D, Species.FARFETCH_U2019D_GALAR,
    Species.DODUO, Species.SEEL, Species.GRIMER, Species.GRIMER_ALOLA,
    Species.SHELLDER, Species.GASTLY, Species.HAUNTER, Species.ONIX,
    Species.DROWZEE, Species.KRABBY, Species.VOLTORB, Species.VOLTORB_HISUI,
    Species.EXEGGCUTE, Species.CUBONE, Species.LICKITUNG, Species.KOFFING,
    Species.RHYHORN, Species.RHYDON, Species.CHANSEY, Species.TANGELA,
    Species.HORSEA, Species.SEADRA, Species.GOLDEEN, Species.STARYU,
    Species.SCYTHER, Species.PINSIR, Species.MAGIKARP, Species.LAPRAS,
    Species.EEVEE, Species.PORYGON, Species.OMANYTE,
    Species.KABUTO, Species.AERODACTYL, Species.DRATINI, Species.DRAGONAIR,
    # Gen 2
    Species.CHIKORITA, Species.BAYLEEF, Species.CYNDAQUIL, Species.QUILAVA,
    Species.TOTODILE, Species.CROCONAW, Species.SENTRET, Species.HOOTHOOT,
    Species.LEDYBA, Species.SPINARAK, Species.CHINCHOU, Species.PICHU, Species.PICHU_SPIKY_EARED,
    Species.CLEFFA, Species.IGGLYBUFF, Species.TOGEPI, Species.TOGETIC,
    Species.NATU, Species.MAREEP, Species.FLAAFFY, Species.MARILL,
    Species.HOPPIP, Species.SKIPLOOM, Species.AIPOM, Species.SUNKERN,
    Species.YANMA, Species.WOOPER, Species.MISDREAVUS,
    Species.GIRAFARIG, Species.PINECO, Species.DUNSPARCE,
    Species.GLIGAR, Species.SNUBBULL, Species.QWILFISH, Species.QWILFISH_HISUI,
    Species.SHUCKLE, Species.HERACROSS, Species.SNEASEL, Species.SNEASEL_HISUI,
    Species.TEDDIURSA, Species.SLUGMA, Species.SWINUB, Species.PILOSWINE,
    Species.CORSOLA, Species.CORSOLA_GALAR, Species.REMORAID, Species.DELIBIRD,
    Species.HOUNDOUR, Species.PHANPY, Species.PORYGON2, Species.STANTLER,
    Species.TYROGUE, Species.SMOOCHUM, Species.ELEKID, Species.MAGBY,
    Species.MILTANK, Species.LARVITAR, Species.PUPITAR,
    # Gen 3 partial (pre-evolutions only)
    Species.TREECKO, Species.GROVYLE, Species.TORCHIC, Species.COMBUSKEN,
    Species.MUDKIP, Species.MARSHTOMP, Species.POOCHYENA, Species.ZIGZAGOON,
    Species.ZIGZAGOON_GALAR, Species.WURMPLE, Species.SILCOON, Species.CASCOON,
    Species.LOTAD, Species.LOMBRE, Species.SEEDOT, Species.NUZLEAF,
    Species.TAILLOW, Species.WINGULL, Species.RALTS, Species.KIRLIA,
    Species.SURSKIT, Species.SHROOMISH, Species.SLAKOTH, Species.VIGOROTH,
    Species.NINCADA, Species.WHISMUR, Species.LOUDRED, Species.MAKUHITA,
    Species.AZURILL, Species.NOSEPASS, Species.SKITTY, Species.SABLEYE,
    Species.MAWILE, Species.ARON, Species.LAIRON, Species.MEDITITE,
    Species.ELECTRIKE, Species.PLUSLE, Species.MINUN, Species.VOLBEAT,
    Species.ILLUMISE, Species.ROSELIA, Species.GULPIN, Species.CARVANHA,
    Species.WAILMER, Species.NUMEL, Species.SPOINK, Species.SPINDA,
    Species.TRAPINCH, Species.VIBRAVA, Species.CACNEA, Species.SWABLU,
    Species.ZANGOOSE, Species.SEVIPER, Species.SOLROCK, Species.LUNATONE,
    Species.BARBOACH, Species.CORPHISH, Species.BALTOY, Species.LILEEP,
    Species.ANORITH, Species.FEEBAS, Species.CASTFORM, Species.KECLEON,
    Species.SHUPPET, Species.DUSKULL, Species.DUSCLOPS, Species.TROPIUS,
    Species.CHIMECHO, Species.ABSOL, Species.SNORUNT, Species.SPHEAL,
    Species.SEALEO, Species.CLAMPERL, Species.RELICANTH, Species.LUVDISC,
    Species.BAGON, Species.SHELGON, Species.BELDUM, Species.METANG,
    # Gen 4 partial
    Species.TURTWIG, Species.GROTLE, Species.CHIMCHAR, Species.MONFERNO,
    Species.PIPLUP, Species.PRINPLUP, Species.STARLY, Species.STARAVIA,
    Species.BIDOOF, Species.KRICKETOT, Species.SHINX, Species.LUXIO,
    Species.BUDEW, Species.CRANIDOS, Species.SHIELDON, Species.BURMY,
    Species.COMBEE, Species.PACHIRISU, Species.BUIZEL, Species.CHERUBI,
    Species.SHELLOS, Species.DRIFLOON, Species.BUNEARY, Species.GLAMEOW,
    Species.CHINGLING, Species.STUNKY, Species.BRONZOR, Species.BONSLY,
    Species.MIME_JR, Species.HAPPINY, Species.CHATOT, Species.SPIRITOMB,
    Species.GIBLE, Species.GABITE, Species.MUNCHLAX, Species.RIOLU,
    Species.HIPPOPOTAS, Species.SKORUPI, Species.CROAGUNK, Species.CARNIVINE,
    Species.FINNEON, Species.MANTYKE, Species.SNOVER, Species.ROTOM,
    # Gen 5 partial
    Species.SNIVY, Species.SERVINE, Species.TEPIG, Species.PIGNITE,
    Species.OSHAWOTT, Species.DEWOTT, Species.PATRAT, Species.LILLIPUP,
    Species.HERDIER, Species.PURRLOIN, Species.PIDOVE, Species.TRANQUILL,
    Species.BLITZLE, Species.ROGGENROLA, Species.BOLDORE, Species.WOOBAT,
    Species.DRILBUR, Species.TIMBURR, Species.GURDURR, Species.TYMPOLE,
    Species.PALPITOAD, Species.THROH, Species.SAWK, Species.SEWADDLE,
    Species.SWADLOON, Species.VENIPEDE, Species.WHIRLIPEDE, Species.COTTONEE,
    Species.PETILIL, Species.BASCULIN, Species.SANDILE, Species.KROKOROK,
    Species.DARUMAKA, Species.DARUMAKA_GALAR, Species.MARACTUS, Species.DWEBBLE,
    Species.CRUSTLE, Species.SCRAGGY, Species.SIGILYPH, Species.YAMASK,
    Species.YAMASK_GALAR, Species.TIRTOUGA, Species.ARCHEN, Species.TRUBBISH,
    Species.ZORUA, Species.ZORUA_HISUI, Species.MINCCINO, Species.GOTHITA,
    Species.GOTHORITA, Species.SOLOSIS, Species.DUOSION, Species.DUCKLETT,
    Species.VANILLITE, Species.VANILLISH, Species.DEERLING, Species.EMOLGA,
    Species.KARRABLAST, Species.FOONGUS, Species.FRILLISH, Species.ALOMOMOLA,
    Species.JOLTIK, Species.GALVANTULA, Species.FERROSEED, Species.KLINK,
    Species.KLANG, Species.TYNAMO, Species.EELEKTRIK, Species.ELGYEM,
    Species.LITWICK, Species.LAMPENT, Species.AXEW, Species.FRAXURE,
    Species.CUBCHOO, Species.CRYOGONAL, Species.SHELMET, Species.STUNFISK,
    Species.STUNFISK_GALAR, Species.MIENFOO, Species.DRUDDIGON, Species.GOLETT,
    Species.PAWNIARD, Species.BISHARP, Species.BOUFFALANT, Species.RUFFLET,
    Species.VULLABY, Species.HEATMOR, Species.DURANT, Species.DEINO,
    Species.ZWEILOUS, Species.LARVESTA, Species.VOLCARONA,
    # Gen 6 partial
    Species.CHESPIN, Species.QUILLADIN, Species.FENNEKIN, Species.BRAIXEN,
    Species.FROAKIE, Species.FROGADIER, Species.FLETCHLING, Species.FLETCHINDER,
    Species.SCATTERBUG, Species.SPEWPA, Species.LITLEO,
    Species.FLOETTE, Species.SKIDDO, Species.PANCHAM, Species.ESPURR,
    Species.HONEDGE, Species.DOUBLADE, Species.INKAY, Species.BINACLE,
    Species.BARBARACLE, Species.SKRELP, Species.CLAUNCHER, Species.HELIOPTILE,
    Species.TYRUNT, Species.AMAURA, Species.HAWLUCHA, Species.DEDENNE,
    Species.CARBINK, Species.GOOMY, Species.SLIGGOO, Species.SLIGGOO_HISUI,
    Species.KLEFKI, Species.PHANTUMP, Species.PUMPKABOO, Species.BERGMITE,
    Species.NOIBAT,
    # Gen 7 partial
    Species.ROWLET, Species.DARTRIX, Species.LITTEN, Species.TORRACAT,
    Species.POPPLIO, Species.BRIONNE, Species.PIKIPEK, Species.TRUMBEAK,
    Species.YUNGOOS, Species.GRUBBIN, Species.CHARJABUG, Species.CUTIEFLY,
    Species.ROCKRUFF, Species.WISHIWASHI, Species.MAREANIE, Species.MUDBRAY,
    Species.DEWPIDER, Species.FOMANTIS, Species.MORELULL, Species.SALANDIT,
    Species.STUFFUL, Species.BOUNSWEET, Species.STEENEE, Species.WIMPOD,
    Species.SANDYGAST, Species.KOMALA, Species.TURTONATOR, Species.TOGEDEMARU,
    Species.MIMIKYU, Species.BRUXISH, Species.DRAMPA, Species.DHELMISE,
    Species.JANGMO_O, Species.HAKAMO_O,
    # Gen 8 partial
    Species.GROOKEY, Species.THWACKEY, Species.SCORBUNNY, Species.RABOOT,
    Species.SOBBLE, Species.DRIZZILE, Species.SKWOVET, Species.ROOKIDEE,
    Species.CORVISQUIRE, Species.BLIPBUG, Species.DOTTLER, Species.APPLIN,
    Species.SILICOBRA, Species.CRAMORANT, Species.ARROKUDA, Species.TOXEL,
    Species.SIZZLIPEDE, Species.CENTISKORCH, Species.CLOBBOPUS, Species.SINISTEA,
    Species.HATENNA, Species.HATTREM, Species.IMPIDIMP, Species.MORGREM,
    Species.MILCERY, Species.FALINKS, Species.PINCURCHIN, Species.SNOM,
    Species.EISCUE, Species.INDEEDEE, Species.MORPEKO, Species.CUFANT,
    Species.DRACOZOLT, Species.ARCTOZOLT, Species.DRACOVISH, Species.ARCTOVISH,
    Species.DREEPY, Species.DRAKLOAK,
})

SOUL_DEW_SPECIES: frozenset[Species] = frozenset({Species.LATIAS, Species.LATIOS})

# Body weights in kg for Low Kick / Grass Knot / Heavy Slam / Heat Crash calculations.
# Authoritative source: Pokemon Showdown data/pokedex.ts (Gen 8; weightkg field). Complete
# for every species in SPECIES_DATA - regenerate via SCRIPTS/build_species_weights.py.
# MINIOR is pinned to the in-battle Meteor form (40.0 kg), not Core. Cosmetic/sub-forms
# inherit their base-form weight.
SPECIES_WEIGHTS: dict['Species', float] = {
    Species.BULBASAUR: 6.9, Species.IVYSAUR: 13.0, Species.VENUSAUR: 100.0, Species.CHARMANDER: 8.5, Species.CHARMELEON: 19.0,
    Species.CHARIZARD: 90.5, Species.SQUIRTLE: 9.0, Species.WARTORTLE: 22.5, Species.BLASTOISE: 85.5, Species.CATERPIE: 2.9,
    Species.METAPOD: 9.9, Species.BUTTERFREE: 32.0, Species.WEEDLE: 3.2, Species.KAKUNA: 10.0, Species.BEEDRILL: 29.5,
    Species.PIDGEY: 1.8, Species.PIDGEOTTO: 30.0, Species.PIDGEOT: 39.5, Species.RATTATA: 3.5, Species.RATICATE: 18.5,
    Species.SPEAROW: 2.0, Species.FEAROW: 38.0, Species.EKANS: 6.9, Species.ARBOK: 65.0, Species.PIKACHU: 6.0,
    Species.RAICHU: 30.0, Species.SANDSHREW: 12.0, Species.SANDSLASH: 29.5, Species.NIDORAN_F: 7.0, Species.NIDORINA: 20.0,
    Species.NIDOQUEEN: 60.0, Species.NIDORAN_M: 9.0, Species.NIDORINO: 19.5, Species.NIDOKING: 62.0, Species.CLEFAIRY: 7.5,
    Species.CLEFABLE: 40.0, Species.VULPIX: 9.9, Species.NINETALES: 19.9, Species.JIGGLYPUFF: 5.5, Species.WIGGLYTUFF: 12.0,
    Species.ZUBAT: 7.5, Species.GOLBAT: 55.0, Species.ODDISH: 5.4, Species.GLOOM: 8.6, Species.VILEPLUME: 18.6,
    Species.PARAS: 5.4, Species.PARASECT: 29.5, Species.VENONAT: 30.0, Species.VENOMOTH: 12.5, Species.DIGLETT: 0.8,
    Species.DUGTRIO: 33.3, Species.MEOWTH: 4.2, Species.PERSIAN: 32.0, Species.PSYDUCK: 19.6, Species.GOLDUCK: 76.6,
    Species.MANKEY: 28.0, Species.PRIMEAPE: 32.0, Species.GROWLITHE: 19.0, Species.ARCANINE: 155.0, Species.POLIWAG: 12.4,
    Species.POLIWHIRL: 20.0, Species.POLIWRATH: 54.0, Species.ABRA: 19.5, Species.KADABRA: 56.5, Species.ALAKAZAM: 48.0,
    Species.MACHOP: 19.5, Species.MACHOKE: 70.5, Species.MACHAMP: 130.0, Species.BELLSPROUT: 4.0, Species.WEEPINBELL: 6.4,
    Species.VICTREEBEL: 15.5, Species.TENTACOOL: 45.5, Species.TENTACRUEL: 55.0, Species.GEODUDE: 20.0, Species.GRAVELER: 105.0,
    Species.GOLEM: 300.0, Species.PONYTA: 30.0, Species.RAPIDASH: 95.0, Species.SLOWPOKE: 36.0, Species.SLOWBRO: 78.5,
    Species.MAGNEMITE: 6.0, Species.MAGNETON: 60.0, Species.FARFETCH_U2019D: 15.0, Species.DODUO: 39.2, Species.DODRIO: 85.2,
    Species.SEEL: 90.0, Species.DEWGONG: 120.0, Species.GRIMER: 30.0, Species.MUK: 30.0, Species.SHELLDER: 4.0,
    Species.CLOYSTER: 132.5, Species.GASTLY: 0.1, Species.HAUNTER: 0.1, Species.GENGAR: 40.5, Species.ONIX: 210.0,
    Species.DROWZEE: 32.4, Species.HYPNO: 75.6, Species.KRABBY: 6.5, Species.KINGLER: 60.0, Species.VOLTORB: 10.4,
    Species.ELECTRODE: 66.6, Species.EXEGGCUTE: 2.5, Species.EXEGGUTOR: 120.0, Species.CUBONE: 6.5, Species.MAROWAK: 45.0,
    Species.HITMONLEE: 49.8, Species.HITMONCHAN: 50.2, Species.LICKITUNG: 65.5, Species.KOFFING: 1.0, Species.WEEZING: 9.5,
    Species.RHYHORN: 115.0, Species.RHYDON: 120.0, Species.CHANSEY: 34.6, Species.TANGELA: 35.0, Species.KANGASKHAN: 80.0,
    Species.HORSEA: 8.0, Species.SEADRA: 25.0, Species.GOLDEEN: 15.0, Species.SEAKING: 39.0, Species.STARYU: 34.5,
    Species.STARMIE: 80.0, Species.MR_MIME: 54.5, Species.SCYTHER: 56.0, Species.JYNX: 40.6, Species.ELECTABUZZ: 30.0,
    Species.MAGMAR: 44.5, Species.PINSIR: 55.0, Species.TAUROS: 88.4, Species.MAGIKARP: 10.0, Species.GYARADOS: 235.0,
    Species.LAPRAS: 220.0, Species.DITTO: 4.0, Species.EEVEE: 6.5, Species.VAPOREON: 29.0, Species.JOLTEON: 24.5,
    Species.FLAREON: 25.0, Species.PORYGON: 36.5, Species.OMANYTE: 7.5, Species.OMASTAR: 35.0, Species.KABUTO: 11.5,
    Species.KABUTOPS: 40.5, Species.AERODACTYL: 59.0, Species.SNORLAX: 460.0, Species.ARTICUNO: 55.4, Species.ZAPDOS: 52.6,
    Species.MOLTRES: 60.0, Species.DRATINI: 3.3, Species.DRAGONAIR: 16.5, Species.DRAGONITE: 210.0, Species.MEWTWO: 122.0,
    Species.MEW: 4.0, Species.CHIKORITA: 6.4, Species.BAYLEEF: 15.8, Species.MEGANIUM: 100.5, Species.CYNDAQUIL: 7.9,
    Species.QUILAVA: 19.0, Species.TYPHLOSION: 79.5, Species.TOTODILE: 9.5, Species.CROCONAW: 25.0, Species.FERALIGATR: 88.8,
    Species.SENTRET: 6.0, Species.FURRET: 32.5, Species.HOOTHOOT: 21.2, Species.NOCTOWL: 40.8, Species.LEDYBA: 10.8,
    Species.LEDIAN: 35.6, Species.SPINARAK: 8.5, Species.ARIADOS: 33.5, Species.CROBAT: 75.0, Species.CHINCHOU: 12.0,
    Species.LANTURN: 22.5, Species.PICHU: 2.0, Species.CLEFFA: 3.0, Species.IGGLYBUFF: 1.0, Species.TOGEPI: 1.5,
    Species.TOGETIC: 3.2, Species.NATU: 2.0, Species.XATU: 15.0, Species.MAREEP: 7.8, Species.FLAAFFY: 13.3,
    Species.AMPHAROS: 61.5, Species.BELLOSSOM: 5.8, Species.MARILL: 8.5, Species.AZUMARILL: 28.5, Species.SUDOWOODO: 38.0,
    Species.POLITOED: 33.9, Species.HOPPIP: 0.5, Species.SKIPLOOM: 1.0, Species.JUMPLUFF: 3.0, Species.AIPOM: 11.5,
    Species.SUNKERN: 1.8, Species.SUNFLORA: 8.5, Species.YANMA: 38.0, Species.WOOPER: 8.5, Species.QUAGSIRE: 75.0,
    Species.ESPEON: 26.5, Species.UMBREON: 27.0, Species.MURKROW: 2.1, Species.SLOWKING: 79.5, Species.MISDREAVUS: 1.0,
    Species.UNOWN_A: 5.0, Species.WOBBUFFET: 28.5, Species.GIRAFARIG: 41.5, Species.PINECO: 7.2, Species.FORRETRESS: 125.8,
    Species.DUNSPARCE: 14.0, Species.GLIGAR: 64.8, Species.STEELIX: 400.0, Species.SNUBBULL: 7.8, Species.GRANBULL: 48.7,
    Species.QWILFISH: 3.9, Species.SCIZOR: 118.0, Species.SHUCKLE: 20.5, Species.HERACROSS: 54.0, Species.SNEASEL: 28.0,
    Species.TEDDIURSA: 8.8, Species.URSARING: 125.8, Species.SLUGMA: 35.0, Species.MAGCARGO: 55.0, Species.SWINUB: 6.5,
    Species.PILOSWINE: 55.8, Species.CORSOLA: 5.0, Species.REMORAID: 12.0, Species.OCTILLERY: 28.5, Species.DELIBIRD: 16.0,
    Species.MANTINE: 220.0, Species.SKARMORY: 50.5, Species.HOUNDOUR: 10.8, Species.HOUNDOOM: 35.0, Species.KINGDRA: 152.0,
    Species.PHANPY: 33.5, Species.DONPHAN: 120.0, Species.PORYGON2: 32.5, Species.STANTLER: 71.2, Species.SMEARGLE: 58.0,
    Species.TYROGUE: 21.0, Species.HITMONTOP: 48.0, Species.SMOOCHUM: 6.0, Species.ELEKID: 23.5, Species.MAGBY: 21.4,
    Species.MILTANK: 75.5, Species.BLISSEY: 46.8, Species.RAIKOU: 178.0, Species.ENTEI: 198.0, Species.SUICUNE: 187.0,
    Species.LARVITAR: 72.0, Species.PUPITAR: 152.0, Species.TYRANITAR: 202.0, Species.LUGIA: 216.0, Species.HO_OH: 199.0,
    Species.CELEBI: 5.0, Species.TREECKO: 5.0, Species.GROVYLE: 21.6, Species.SCEPTILE: 52.2, Species.TORCHIC: 2.5,
    Species.COMBUSKEN: 19.5, Species.BLAZIKEN: 52.0, Species.MUDKIP: 7.6, Species.MARSHTOMP: 28.0, Species.SWAMPERT: 81.9,
    Species.POOCHYENA: 13.6, Species.MIGHTYENA: 37.0, Species.ZIGZAGOON: 17.5, Species.LINOONE: 32.5, Species.WURMPLE: 3.6,
    Species.SILCOON: 10.0, Species.BEAUTIFLY: 28.4, Species.CASCOON: 11.5, Species.DUSTOX: 31.6, Species.LOTAD: 2.6,
    Species.LOMBRE: 32.5, Species.LUDICOLO: 55.0, Species.SEEDOT: 4.0, Species.NUZLEAF: 28.0, Species.SHIFTRY: 59.6,
    Species.TAILLOW: 2.3, Species.SWELLOW: 19.8, Species.WINGULL: 9.5, Species.PELIPPER: 28.0, Species.RALTS: 6.6,
    Species.KIRLIA: 20.2, Species.GARDEVOIR: 48.4, Species.SURSKIT: 1.7, Species.MASQUERAIN: 3.6, Species.SHROOMISH: 4.5,
    Species.BRELOOM: 39.2, Species.SLAKOTH: 24.0, Species.VIGOROTH: 46.5, Species.SLAKING: 130.5, Species.NINCADA: 5.5,
    Species.NINJASK: 12.0, Species.SHEDINJA: 1.2, Species.WHISMUR: 16.3, Species.LOUDRED: 40.5, Species.EXPLOUD: 84.0,
    Species.MAKUHITA: 86.4, Species.HARIYAMA: 253.8, Species.AZURILL: 2.0, Species.NOSEPASS: 97.0, Species.SKITTY: 11.0,
    Species.DELCATTY: 32.6, Species.SABLEYE: 11.0, Species.MAWILE: 11.5, Species.ARON: 60.0, Species.LAIRON: 120.0,
    Species.AGGRON: 360.0, Species.MEDITITE: 11.2, Species.MEDICHAM: 31.5, Species.ELECTRIKE: 15.2, Species.MANECTRIC: 40.2,
    Species.PLUSLE: 4.2, Species.MINUN: 4.2, Species.VOLBEAT: 17.7, Species.ILLUMISE: 17.7, Species.ROSELIA: 2.0,
    Species.GULPIN: 10.3, Species.SWALOT: 80.0, Species.CARVANHA: 20.8, Species.SHARPEDO: 88.8, Species.WAILMER: 130.0,
    Species.WAILORD: 398.0, Species.NUMEL: 24.0, Species.CAMERUPT: 220.0, Species.TORKOAL: 80.4, Species.SPOINK: 30.6,
    Species.GRUMPIG: 71.5, Species.SPINDA: 5.0, Species.TRAPINCH: 15.0, Species.VIBRAVA: 15.3, Species.FLYGON: 82.0,
    Species.CACNEA: 51.3, Species.CACTURNE: 77.4, Species.SWABLU: 1.2, Species.ALTARIA: 20.6, Species.ZANGOOSE: 40.3,
    Species.SEVIPER: 52.5, Species.LUNATONE: 168.0, Species.SOLROCK: 154.0, Species.BARBOACH: 1.9, Species.WHISCASH: 23.6,
    Species.CORPHISH: 11.5, Species.CRAWDAUNT: 32.8, Species.BALTOY: 21.5, Species.CLAYDOL: 108.0, Species.LILEEP: 23.8,
    Species.CRADILY: 60.4, Species.ANORITH: 12.5, Species.ARMALDO: 68.2, Species.FEEBAS: 7.4, Species.MILOTIC: 162.0,
    Species.CASTFORM: 0.8, Species.KECLEON: 22.0, Species.SHUPPET: 2.3, Species.BANETTE: 12.5, Species.DUSKULL: 15.0,
    Species.DUSCLOPS: 30.6, Species.TROPIUS: 100.0, Species.CHIMECHO: 1.0, Species.ABSOL: 47.0, Species.WYNAUT: 14.0,
    Species.SNORUNT: 16.8, Species.GLALIE: 256.5, Species.SPHEAL: 39.5, Species.SEALEO: 87.6, Species.WALREIN: 150.6,
    Species.CLAMPERL: 52.5, Species.HUNTAIL: 27.0, Species.GOREBYSS: 22.6, Species.RELICANTH: 23.4, Species.LUVDISC: 8.7,
    Species.BAGON: 42.1, Species.SHELGON: 110.5, Species.SALAMENCE: 102.6, Species.BELDUM: 95.2, Species.METANG: 202.5,
    Species.METAGROSS: 550.0, Species.REGIROCK: 230.0, Species.REGICE: 175.0, Species.REGISTEEL: 205.0, Species.LATIAS: 40.0,
    Species.LATIOS: 60.0, Species.KYOGRE: 352.0, Species.GROUDON: 950.0, Species.RAYQUAZA: 206.5, Species.JIRACHI: 1.1,
    Species.DEOXYS: 60.8, Species.TURTWIG: 10.2, Species.GROTLE: 97.0, Species.TORTERRA: 310.0, Species.CHIMCHAR: 6.2,
    Species.MONFERNO: 22.0, Species.INFERNAPE: 55.0, Species.PIPLUP: 5.2, Species.PRINPLUP: 23.0, Species.EMPOLEON: 84.5,
    Species.STARLY: 2.0, Species.STARAVIA: 15.5, Species.STARAPTOR: 24.9, Species.BIDOOF: 20.0, Species.BIBAREL: 31.5,
    Species.KRICKETOT: 2.2, Species.KRICKETUNE: 25.5, Species.SHINX: 9.5, Species.LUXIO: 30.5, Species.LUXRAY: 42.0,
    Species.BUDEW: 1.2, Species.ROSERADE: 14.5, Species.CRANIDOS: 31.5, Species.RAMPARDOS: 102.5, Species.SHIELDON: 57.0,
    Species.BASTIODON: 149.5, Species.BURMY: 3.4, Species.WORMADAM: 6.5, Species.MOTHIM: 23.3, Species.COMBEE: 5.5,
    Species.VESPIQUEN: 38.5, Species.PACHIRISU: 3.9, Species.BUIZEL: 29.5, Species.FLOATZEL: 33.5, Species.CHERUBI: 3.3,
    Species.CHERRIM: 9.3, Species.SHELLOS: 6.3, Species.GASTRODON: 29.9, Species.AMBIPOM: 20.3, Species.DRIFLOON: 1.2,
    Species.DRIFBLIM: 15.0, Species.BUNEARY: 5.5, Species.LOPUNNY: 33.3, Species.MISMAGIUS: 4.4, Species.HONCHKROW: 27.3,
    Species.GLAMEOW: 3.9, Species.PURUGLY: 43.8, Species.CHINGLING: 0.6, Species.STUNKY: 19.2, Species.SKUNTANK: 38.0,
    Species.BRONZOR: 60.5, Species.BRONZONG: 187.0, Species.BONSLY: 15.0, Species.MIME_JR: 13.0, Species.HAPPINY: 24.4,
    Species.CHATOT: 1.9, Species.SPIRITOMB: 108.0, Species.GIBLE: 20.5, Species.GABITE: 56.0, Species.GARCHOMP: 95.0,
    Species.MUNCHLAX: 105.0, Species.RIOLU: 20.2, Species.LUCARIO: 54.0, Species.HIPPOPOTAS: 49.5, Species.HIPPOWDON: 300.0,
    Species.SKORUPI: 12.0, Species.DRAPION: 61.5, Species.CROAGUNK: 23.0, Species.TOXICROAK: 44.4, Species.CARNIVINE: 27.0,
    Species.FINNEON: 7.0, Species.LUMINEON: 24.0, Species.MANTYKE: 65.0, Species.SNOVER: 50.5, Species.ABOMASNOW: 135.5,
    Species.WEAVILE: 34.0, Species.MAGNEZONE: 180.0, Species.LICKILICKY: 140.0, Species.RHYPERIOR: 282.8, Species.TANGROWTH: 128.6,
    Species.ELECTIVIRE: 138.6, Species.MAGMORTAR: 68.0, Species.TOGEKISS: 38.0, Species.YANMEGA: 51.5, Species.LEAFEON: 25.5,
    Species.GLACEON: 25.9, Species.GLISCOR: 42.5, Species.MAMOSWINE: 291.0, Species.PORYGON_Z: 34.0, Species.GALLADE: 52.0,
    Species.PROBOPASS: 340.0, Species.DUSKNOIR: 106.6, Species.FROSLASS: 26.6, Species.ROTOM: 0.3, Species.UXIE: 0.3,
    Species.MESPRIT: 0.3, Species.AZELF: 0.3, Species.DIALGA: 683.0, Species.PALKIA: 336.0, Species.HEATRAN: 430.0,
    Species.REGIGIGAS: 420.0, Species.GIRATINA: 750.0, Species.CRESSELIA: 85.6, Species.PHIONE: 3.1, Species.MANAPHY: 1.4,
    Species.DARKRAI: 50.5, Species.SHAYMIN: 2.1, Species.ARCEUS: 320.0, Species.VICTINI: 4.0, Species.SNIVY: 8.1,
    Species.SERVINE: 16.0, Species.SERPERIOR: 63.0, Species.TEPIG: 9.9, Species.PIGNITE: 55.5, Species.EMBOAR: 150.0,
    Species.OSHAWOTT: 5.9, Species.DEWOTT: 24.5, Species.SAMUROTT: 94.6, Species.PATRAT: 11.6, Species.WATCHOG: 27.0,
    Species.LILLIPUP: 4.1, Species.HERDIER: 14.7, Species.STOUTLAND: 61.0, Species.PURRLOIN: 10.1, Species.LIEPARD: 37.5,
    Species.PANSAGE: 10.5, Species.SIMISAGE: 30.5, Species.PANSEAR: 11.0, Species.SIMISEAR: 28.0, Species.PANPOUR: 13.5,
    Species.SIMIPOUR: 29.0, Species.MUNNA: 23.3, Species.MUSHARNA: 60.5, Species.PIDOVE: 2.1, Species.TRANQUILL: 15.0,
    Species.UNFEZANT: 29.0, Species.BLITZLE: 29.8, Species.ZEBSTRIKA: 79.5, Species.ROGGENROLA: 18.0, Species.BOLDORE: 102.0,
    Species.GIGALITH: 260.0, Species.WOOBAT: 2.1, Species.SWOOBAT: 10.5, Species.DRILBUR: 8.5, Species.EXCADRILL: 40.4,
    Species.AUDINO: 31.0, Species.TIMBURR: 12.5, Species.GURDURR: 40.0, Species.CONKELDURR: 87.0, Species.TYMPOLE: 4.5,
    Species.PALPITOAD: 17.0, Species.SEISMITOAD: 62.0, Species.THROH: 55.5, Species.SAWK: 51.0, Species.SEWADDLE: 2.5,
    Species.SWADLOON: 7.3, Species.LEAVANNY: 20.5, Species.VENIPEDE: 5.3, Species.WHIRLIPEDE: 58.5, Species.SCOLIPEDE: 200.5,
    Species.COTTONEE: 0.6, Species.WHIMSICOTT: 6.6, Species.PETILIL: 6.6, Species.LILLIGANT: 16.3, Species.BASCULIN: 18.0,
    Species.SANDILE: 15.2, Species.KROKOROK: 33.4, Species.KROOKODILE: 96.3, Species.DARUMAKA: 37.5, Species.DARMANITAN: 92.9,
    Species.MARACTUS: 28.0, Species.DWEBBLE: 14.5, Species.CRUSTLE: 200.0, Species.SCRAGGY: 11.8, Species.SCRAFTY: 30.0,
    Species.SIGILYPH: 14.0, Species.YAMASK: 1.5, Species.COFAGRIGUS: 76.5, Species.TIRTOUGA: 16.5, Species.CARRACOSTA: 81.0,
    Species.ARCHEN: 9.5, Species.ARCHEOPS: 32.0, Species.TRUBBISH: 31.0, Species.GARBODOR: 107.3, Species.ZORUA: 12.5,
    Species.ZOROARK: 81.1, Species.MINCCINO: 5.8, Species.CINCCINO: 7.5, Species.GOTHITA: 5.8, Species.GOTHORITA: 18.0,
    Species.GOTHITELLE: 44.0, Species.SOLOSIS: 1.0, Species.DUOSION: 8.0, Species.REUNICLUS: 20.1, Species.DUCKLETT: 5.5,
    Species.SWANNA: 24.2, Species.VANILLITE: 5.7, Species.VANILLISH: 41.0, Species.VANILLUXE: 57.5, Species.DEERLING: 19.5,
    Species.SAWSBUCK: 92.5, Species.EMOLGA: 5.0, Species.KARRABLAST: 5.9, Species.ESCAVALIER: 33.0, Species.FOONGUS: 1.0,
    Species.AMOONGUSS: 10.5, Species.FRILLISH: 33.0, Species.JELLICENT: 135.0, Species.ALOMOMOLA: 31.6, Species.JOLTIK: 0.6,
    Species.GALVANTULA: 14.3, Species.FERROSEED: 18.8, Species.FERROTHORN: 110.0, Species.KLINK: 21.0, Species.KLANG: 51.0,
    Species.KLINKLANG: 81.0, Species.TYNAMO: 0.3, Species.EELEKTRIK: 22.0, Species.EELEKTROSS: 80.5, Species.ELGYEM: 9.0,
    Species.BEHEEYEM: 34.5, Species.LITWICK: 3.1, Species.LAMPENT: 13.0, Species.CHANDELURE: 34.3, Species.AXEW: 18.0,
    Species.FRAXURE: 36.0, Species.HAXORUS: 105.5, Species.CUBCHOO: 8.5, Species.BEARTIC: 260.0, Species.CRYOGONAL: 148.0,
    Species.SHELMET: 7.7, Species.ACCELGOR: 25.3, Species.STUNFISK: 11.0, Species.MIENFOO: 20.0, Species.MIENSHAO: 35.5,
    Species.DRUDDIGON: 139.0, Species.GOLETT: 92.0, Species.GOLURK: 330.0, Species.PAWNIARD: 10.2, Species.BISHARP: 70.0,
    Species.BOUFFALANT: 94.6, Species.RUFFLET: 10.5, Species.BRAVIARY: 41.0, Species.VULLABY: 9.0, Species.MANDIBUZZ: 39.5,
    Species.HEATMOR: 58.0, Species.DURANT: 33.0, Species.DEINO: 17.3, Species.ZWEILOUS: 50.0, Species.HYDREIGON: 160.0,
    Species.LARVESTA: 28.8, Species.VOLCARONA: 46.0, Species.COBALION: 250.0, Species.TERRAKION: 260.0, Species.VIRIZION: 200.0,
    Species.TORNADUS: 63.0, Species.THUNDURUS: 61.0, Species.RESHIRAM: 330.0, Species.ZEKROM: 345.0, Species.LANDORUS: 68.0,
    Species.KYUREM: 325.0, Species.KELDEO: 48.5, Species.MELOETTA: 6.5, Species.GENESECT: 82.5, Species.CHESPIN: 9.0,
    Species.QUILLADIN: 29.0, Species.CHESNAUGHT: 90.0, Species.FENNEKIN: 9.4, Species.BRAIXEN: 14.5, Species.DELPHOX: 39.0,
    Species.FROAKIE: 7.0, Species.FROGADIER: 10.9, Species.GRENINJA: 40.0, Species.BUNNELBY: 5.0, Species.DIGGERSBY: 42.4,
    Species.FLETCHLING: 1.7, Species.FLETCHINDER: 16.0, Species.TALONFLAME: 24.5, Species.SCATTERBUG: 2.5, Species.SPEWPA: 8.4,
    Species.VIVILLON: 17.0, Species.LITLEO: 13.5, Species.PYROAR: 81.5, Species.FLABE_U0301BE_U0301: 0.1, Species.FLOETTE: 0.9,
    Species.FLORGES: 10.0, Species.SKIDDO: 31.0, Species.GOGOAT: 91.0, Species.PANCHAM: 8.0, Species.PANGORO: 136.0,
    Species.FURFROU: 28.0, Species.ESPURR: 3.5, Species.MEOWSTIC: 8.5, Species.HONEDGE: 2.0, Species.DOUBLADE: 4.5,
    Species.AEGISLASH: 53.0, Species.SPRITZEE: 0.5, Species.AROMATISSE: 15.5, Species.SWIRLIX: 3.5, Species.SLURPUFF: 5.0,
    Species.INKAY: 3.5, Species.MALAMAR: 47.0, Species.BINACLE: 31.0, Species.BARBARACLE: 96.0, Species.SKRELP: 7.3,
    Species.DRAGALGE: 81.5, Species.CLAUNCHER: 8.3, Species.CLAWITZER: 35.3, Species.HELIOPTILE: 6.0, Species.HELIOLISK: 21.0,
    Species.TYRUNT: 26.0, Species.TYRANTRUM: 270.0, Species.AMAURA: 25.2, Species.AURORUS: 225.0, Species.SYLVEON: 23.5,
    Species.HAWLUCHA: 21.5, Species.DEDENNE: 2.2, Species.CARBINK: 5.7, Species.GOOMY: 2.8, Species.SLIGGOO: 17.5,
    Species.GOODRA: 150.5, Species.KLEFKI: 3.0, Species.PHANTUMP: 7.0, Species.TREVENANT: 71.0, Species.PUMPKABOO: 5.0,
    Species.GOURGEIST: 12.5, Species.BERGMITE: 99.5, Species.AVALUGG: 505.0, Species.NOIBAT: 8.0, Species.NOIVERN: 85.0,
    Species.XERNEAS: 215.0, Species.YVELTAL: 203.0, Species.ZYGARDE_AURA_BREAK: 305.0, Species.DIANCIE: 8.8, Species.HOOPA: 9.0,
    Species.VOLCANION: 195.0, Species.ROWLET: 1.5, Species.DARTRIX: 16.0, Species.DECIDUEYE: 36.6, Species.LITTEN: 4.3,
    Species.TORRACAT: 25.0, Species.INCINEROAR: 83.0, Species.POPPLIO: 7.5, Species.BRIONNE: 17.5, Species.PRIMARINA: 44.0,
    Species.PIKIPEK: 1.2, Species.TRUMBEAK: 14.8, Species.TOUCANNON: 26.0, Species.YUNGOOS: 6.0, Species.GUMSHOOS: 14.2,
    Species.GRUBBIN: 4.4, Species.CHARJABUG: 10.5, Species.VIKAVOLT: 45.0, Species.CRABRAWLER: 7.0, Species.CRABOMINABLE: 180.0,
    Species.ORICORIO: 3.4, Species.CUTIEFLY: 0.2, Species.RIBOMBEE: 0.5, Species.ROCKRUFF: 9.2, Species.LYCANROC: 25.0,
    Species.WISHIWASHI: 0.3, Species.MAREANIE: 8.0, Species.TOXAPEX: 14.5, Species.MUDBRAY: 110.0, Species.MUDSDALE: 920.0,
    Species.DEWPIDER: 4.0, Species.ARAQUANID: 82.0, Species.FOMANTIS: 1.5, Species.LURANTIS: 18.5, Species.MORELULL: 1.5,
    Species.SHIINOTIC: 11.5, Species.SALANDIT: 4.8, Species.SALAZZLE: 22.2, Species.STUFFUL: 6.8, Species.BEWEAR: 135.0,
    Species.BOUNSWEET: 3.2, Species.STEENEE: 8.2, Species.TSAREENA: 21.4, Species.COMFEY: 0.3, Species.ORANGURU: 76.0,
    Species.PASSIMIAN: 82.8, Species.WIMPOD: 12.0, Species.GOLISOPOD: 108.0, Species.SANDYGAST: 70.0, Species.PALOSSAND: 250.0,
    Species.PYUKUMUKU: 1.2, Species.TYPE_NULL: 120.5, Species.SILVALLY: 100.5, Species.MINIOR: 40.0, Species.KOMALA: 19.9,
    Species.TURTONATOR: 212.0, Species.TOGEDEMARU: 3.3, Species.MIMIKYU: 0.7, Species.BRUXISH: 19.0, Species.DRAMPA: 185.0,
    Species.DHELMISE: 210.0, Species.JANGMO_O: 29.7, Species.HAKAMO_O: 47.0, Species.KOMMO_O: 78.2, Species.TAPU_KOKO: 20.5,
    Species.TAPU_LELE: 18.6, Species.TAPU_BULU: 45.5, Species.TAPU_FINI: 21.2, Species.COSMOG: 0.1, Species.COSMOEM: 999.9,
    Species.SOLGALEO: 230.0, Species.LUNALA: 120.0, Species.NIHILEGO: 55.5, Species.BUZZWOLE: 333.6, Species.PHEROMOSA: 25.0,
    Species.XURKITREE: 100.0, Species.CELESTEELA: 999.9, Species.KARTANA: 0.1, Species.GUZZLORD: 888.0, Species.NECROZMA: 230.0,
    Species.MAGEARNA: 80.5, Species.MARSHADOW: 22.2, Species.POIPOLE: 1.8, Species.NAGANADEL: 150.0, Species.STAKATAKA: 820.0,
    Species.BLACEPHALON: 13.0, Species.ZERAORA: 44.5, Species.MELTAN: 8.0, Species.MELMETAL: 800.0, Species.GROOKEY: 5.0,
    Species.THWACKEY: 14.0, Species.RILLABOOM: 90.0, Species.SCORBUNNY: 4.5, Species.RABOOT: 9.0, Species.CINDERACE: 33.0,
    Species.SOBBLE: 4.0, Species.DRIZZILE: 11.5, Species.INTELEON: 45.2, Species.SKWOVET: 2.5, Species.GREEDENT: 6.0,
    Species.ROOKIDEE: 1.8, Species.CORVISQUIRE: 16.0, Species.CORVIKNIGHT: 75.0, Species.BLIPBUG: 8.0, Species.DOTTLER: 19.5,
    Species.ORBEETLE: 40.8, Species.NICKIT: 8.9, Species.THIEVUL: 19.9, Species.GOSSIFLEUR: 2.2, Species.ELDEGOSS: 2.5,
    Species.WOOLOO: 6.0, Species.DUBWOOL: 43.0, Species.CHEWTLE: 8.5, Species.DREDNAW: 115.5, Species.YAMPER: 13.5,
    Species.BOLTUND: 34.0, Species.ROLYCOLY: 12.0, Species.CARKOL: 78.0, Species.COALOSSAL: 310.5, Species.APPLIN: 0.5,
    Species.FLAPPLE: 1.0, Species.APPLETUN: 13.0, Species.SILICOBRA: 7.6, Species.SANDACONDA: 65.5, Species.CRAMORANT: 18.0,
    Species.ARROKUDA: 1.0, Species.BARRASKEWDA: 30.0, Species.TOXEL: 11.0, Species.TOXTRICITY: 40.0, Species.SIZZLIPEDE: 1.0,
    Species.CENTISKORCH: 120.0, Species.CLOBBOPUS: 4.0, Species.GRAPPLOCT: 39.0, Species.SINISTEA: 0.2, Species.POLTEAGEIST: 0.4,
    Species.HATENNA: 3.4, Species.HATTREM: 4.8, Species.HATTERENE: 5.1, Species.IMPIDIMP: 5.5, Species.MORGREM: 12.5,
    Species.GRIMMSNARL: 61.0, Species.OBSTAGOON: 46.0, Species.PERRSERKER: 28.0, Species.CURSOLA: 0.4, Species.SIRFETCH_U2019D: 117.0,
    Species.MR_RIME: 58.2, Species.RUNERIGUS: 66.6, Species.MILCERY: 0.3, Species.ALCREMIE: 0.5, Species.FALINKS: 62.0,
    Species.PINCURCHIN: 1.0, Species.SNOM: 3.8, Species.FROSMOTH: 42.0, Species.STONJOURNER: 520.0, Species.EISCUE: 89.0,
    Species.INDEEDEE: 28.0, Species.MORPEKO: 3.0, Species.CUFANT: 100.0, Species.COPPERAJAH: 650.0, Species.DRACOZOLT: 190.0,
    Species.ARCTOZOLT: 150.0, Species.DRACOVISH: 215.0, Species.ARCTOVISH: 175.0, Species.DURALUDON: 40.0, Species.DREEPY: 2.0,
    Species.DRAKLOAK: 11.0, Species.DRAGAPULT: 50.0, Species.ZACIAN: 110.0, Species.ZAMAZENTA: 210.0, Species.ETERNATUS: 950.0,
    Species.KUBFU: 12.0, Species.URSHIFU: 105.0, Species.ZARUDE: 70.0, Species.REGIELEKI: 145.0, Species.REGIDRAGO: 200.0,
    Species.GLASTRIER: 800.0, Species.SPECTRIER: 44.5, Species.CALYREX: 7.7, Species.WYRDEER: 95.1, Species.KLEAVOR: 89.0,
    Species.URSALUNA: 290.0, Species.BASCULEGION: 110.0, Species.SNEASLER: 43.0, Species.OVERQWIL: 60.5, Species.ENAMORUS: 48.0,
    Species.VENUSAUR_MEGA: 155.5, Species.CHARIZARD_MEGA_X: 110.5, Species.CHARIZARD_MEGA_Y: 100.5, Species.BLASTOISE_MEGA: 101.1, Species.BEEDRILL_MEGA: 40.5,
    Species.PIDGEOT_MEGA: 50.5, Species.ALAKAZAM_MEGA: 48.0, Species.SLOWBRO_MEGA: 120.0, Species.GENGAR_MEGA: 40.5, Species.KANGASKHAN_MEGA: 100.0,
    Species.PINSIR_MEGA: 59.0, Species.GYARADOS_MEGA: 305.0, Species.AERODACTYL_MEGA: 79.0, Species.MEWTWO_MEGA_X: 127.0, Species.MEWTWO_MEGA_Y: 33.0,
    Species.AMPHAROS_MEGA: 61.5, Species.STEELIX_MEGA: 740.0, Species.SCIZOR_MEGA: 125.0, Species.HERACROSS_MEGA: 62.5, Species.HOUNDOOM_MEGA: 49.5,
    Species.TYRANITAR_MEGA: 255.0, Species.SCEPTILE_MEGA: 55.2, Species.BLAZIKEN_MEGA: 52.0, Species.SWAMPERT_MEGA: 102.0, Species.GARDEVOIR_MEGA: 48.4,
    Species.SABLEYE_MEGA: 161.0, Species.MAWILE_MEGA: 23.5, Species.AGGRON_MEGA: 395.0, Species.MEDICHAM_MEGA: 31.5, Species.MANECTRIC_MEGA: 44.0,
    Species.SHARPEDO_MEGA: 130.3, Species.CAMERUPT_MEGA: 320.5, Species.ALTARIA_MEGA: 20.6, Species.BANETTE_MEGA: 13.0, Species.ABSOL_MEGA: 49.0,
    Species.GLALIE_MEGA: 350.2, Species.SALAMENCE_MEGA: 112.6, Species.METAGROSS_MEGA: 942.9, Species.LATIAS_MEGA: 52.0, Species.LATIOS_MEGA: 70.0,
    Species.LOPUNNY_MEGA: 28.3, Species.GARCHOMP_MEGA: 95.0, Species.LUCARIO_MEGA: 57.5, Species.ABOMASNOW_MEGA: 185.0, Species.GALLADE_MEGA: 56.4,
    Species.AUDINO_MEGA: 32.0, Species.DIANCIE_MEGA: 27.8, Species.RAYQUAZA_MEGA: 392.0, Species.KYOGRE_PRIMAL: 430.0, Species.GROUDON_PRIMAL: 999.7,
    Species.RATTATA_ALOLA: 3.8, Species.RATICATE_ALOLA: 25.5, Species.RAICHU_ALOLA: 21.0, Species.SANDSHREW_ALOLA: 40.0, Species.SANDSLASH_ALOLA: 55.0,
    Species.VULPIX_ALOLA: 9.9, Species.NINETALES_ALOLA: 19.9, Species.DIGLETT_ALOLA: 1.0, Species.DUGTRIO_ALOLA: 66.6, Species.MEOWTH_ALOLA: 4.2,
    Species.PERSIAN_ALOLA: 33.0, Species.GEODUDE_ALOLA: 20.3, Species.GRAVELER_ALOLA: 110.0, Species.GOLEM_ALOLA: 316.0, Species.GRIMER_ALOLA: 42.0,
    Species.MUK_ALOLA: 52.0, Species.EXEGGUTOR_ALOLA: 415.6, Species.MAROWAK_ALOLA: 34.0, Species.MEOWTH_GALAR: 7.5, Species.PONYTA_GALAR: 24.0,
    Species.RAPIDASH_GALAR: 80.0, Species.SLOWPOKE_GALAR: 36.0, Species.SLOWBRO_GALAR: 70.5, Species.FARFETCH_U2019D_GALAR: 42.0, Species.WEEZING_GALAR: 16.0,
    Species.MR_MIME_GALAR: 56.8, Species.ARTICUNO_GALAR: 50.9, Species.ZAPDOS_GALAR: 58.2, Species.MOLTRES_GALAR: 66.0, Species.SLOWKING_GALAR: 79.5,
    Species.CORSOLA_GALAR: 0.5, Species.ZIGZAGOON_GALAR: 17.5, Species.LINOONE_GALAR: 32.5, Species.DARUMAKA_GALAR: 40.0, Species.DARMANITAN_GALAR: 120.0,
    Species.YAMASK_GALAR: 1.5, Species.STUNFISK_GALAR: 20.5, Species.GROWLITHE_HISUI: 22.7, Species.ARCANINE_HISUI: 168.0, Species.VOLTORB_HISUI: 13.0,
    Species.ELECTRODE_HISUI: 71.0, Species.TYPHLOSION_HISUI: 69.8, Species.QWILFISH_HISUI: 3.9, Species.SNEASEL_HISUI: 27.0, Species.SAMUROTT_HISUI: 58.2,
    Species.LILLIGANT_HISUI: 19.2, Species.ZORUA_HISUI: 12.5, Species.ZOROARK_HISUI: 73.0, Species.BRAVIARY_HISUI: 43.4, Species.SLIGGOO_HISUI: 68.5,
    Species.GOODRA_HISUI: 334.1, Species.AVALUGG_HISUI: 262.4, Species.DECIDUEYE_HISUI: 37.0, Species.PIKACHU_COSPLAY: 6.0, Species.PIKACHU_ROCK_STAR: 6.0,
    Species.PIKACHU_BELLE: 6.0, Species.PIKACHU_POP_STAR: 6.0, Species.PIKACHU_PHD: 6.0, Species.PIKACHU_LIBRE: 6.0, Species.PIKACHU_ORIGINAL: 6.0,
    Species.PIKACHU_HOENN: 6.0, Species.PIKACHU_SINNOH: 6.0, Species.PIKACHU_UNOVA: 6.0, Species.PIKACHU_KALOS: 6.0, Species.PIKACHU_ALOLA: 6.0,
    Species.PIKACHU_PARTNER: 6.0, Species.PIKACHU_WORLD: 6.0, Species.PICHU_SPIKY_EARED: 2.0, Species.UNOWN_B: 5.0, Species.UNOWN_C: 5.0,
    Species.UNOWN_D: 5.0, Species.UNOWN_E: 5.0, Species.UNOWN_F: 5.0, Species.UNOWN_G: 5.0, Species.UNOWN_H: 5.0,
    Species.UNOWN_I: 5.0, Species.UNOWN_J: 5.0, Species.UNOWN_K: 5.0, Species.UNOWN_L: 5.0, Species.UNOWN_M: 5.0,
    Species.UNOWN_N: 5.0, Species.UNOWN_O: 5.0, Species.UNOWN_P: 5.0, Species.UNOWN_Q: 5.0, Species.UNOWN_R: 5.0,
    Species.UNOWN_S: 5.0, Species.UNOWN_T: 5.0, Species.UNOWN_U: 5.0, Species.UNOWN_V: 5.0, Species.UNOWN_W: 5.0,
    Species.UNOWN_X: 5.0, Species.UNOWN_Y: 5.0, Species.UNOWN_Z: 5.0, Species.UNOWN_EX: 5.0, Species.UNOWN_QUESTION: 5.0,
    Species.CASTFORM_SUNNY: 0.8, Species.CASTFORM_RAINY: 0.8, Species.CASTFORM_SNOWY: 0.8, Species.DEOXYS_ATTACK: 60.8, Species.DEOXYS_DEFENSE: 60.8,
    Species.DEOXYS_SPEED: 60.8, Species.BURMY_SANDY: 3.4, Species.BURMY_TRASH: 3.4, Species.WORMADAM_SANDY: 6.5, Species.WORMADAM_TRASH: 6.5,
    Species.CHERRIM_SUNSHINE: 9.3, Species.SHELLOS_WEST: 6.3, Species.GASTRODON_WEST: 29.9, Species.ROTOM_HEAT: 0.3, Species.ROTOM_WASH: 0.3,
    Species.ROTOM_FROST: 0.3, Species.ROTOM_FAN: 0.3, Species.ROTOM_MOW: 0.3, Species.DIALGA_ORIGIN: 850.0, Species.PALKIA_ORIGIN: 660.0,
    Species.GIRATINA_ORIGIN: 650.0, Species.SHAYMIN_SKY: 5.2, Species.ARCEUS_FIGHTING: 320.0, Species.ARCEUS_FLYING: 320.0, Species.ARCEUS_POISON: 320.0,
    Species.ARCEUS_GROUND: 320.0, Species.ARCEUS_ROCK: 320.0, Species.ARCEUS_BUG: 320.0, Species.ARCEUS_GHOST: 320.0, Species.ARCEUS_STEEL: 320.0,
    Species.ARCEUS_FIRE: 320.0, Species.ARCEUS_WATER: 320.0, Species.ARCEUS_GRASS: 320.0, Species.ARCEUS_ELECTRIC: 320.0, Species.ARCEUS_ICE: 320.0,
    Species.ARCEUS_DRAGON: 320.0, Species.ARCEUS_DARK: 320.0, Species.ARCEUS_FAIRY: 320.0, Species.BASCULIN_BLUE_STRIPED: 18.0, Species.BASCULIN_WHITE_STRIPED: 18.0,
    Species.DARMANITAN_ZEN: 92.9, Species.DARMANITAN_GALAR_ZEN: 120.0, Species.DEERLING_SUMMER: 19.5, Species.DEERLING_AUTUMN: 19.5, Species.DEERLING_WINTER: 19.5,
    Species.SAWSBUCK_SUMMER: 92.5, Species.SAWSBUCK_AUTUMN: 92.5, Species.SAWSBUCK_WINTER: 92.5, Species.TORNADUS_THERIAN: 63.0, Species.THUNDURUS_THERIAN: 61.0,
    Species.LANDORUS_THERIAN: 68.0, Species.ENAMORUS_THERIAN: 48.0, Species.KYUREM_WHITE: 325.0, Species.KYUREM_BLACK: 325.0, Species.KELDEO_RESOLUTE: 48.5,
    Species.MELOETTA_PIROUETTE: 6.5, Species.GENESECT_DOUSE: 82.5, Species.GENESECT_SHOCK: 82.5, Species.GENESECT_BURN: 82.5, Species.GENESECT_CHILL: 82.5,
    Species.GRENINJA_BOND: 40.0, Species.GRENINJA_ASH: 40.0, Species.VIVILLON_1: 17.0, Species.VIVILLON_2: 17.0, Species.VIVILLON_3: 17.0,
    Species.VIVILLON_4: 17.0, Species.VIVILLON_5: 17.0, Species.VIVILLON_6: 17.0, Species.VIVILLON_7: 17.0, Species.VIVILLON_8: 17.0,
    Species.VIVILLON_9: 17.0, Species.VIVILLON_10: 17.0, Species.VIVILLON_11: 17.0, Species.VIVILLON_12: 17.0, Species.VIVILLON_13: 17.0,
    Species.VIVILLON_14: 17.0, Species.VIVILLON_15: 17.0, Species.VIVILLON_16: 17.0, Species.VIVILLON_17: 17.0, Species.VIVILLON_18: 17.0,
    Species.VIVILLON_19: 17.0, Species.FLABE_U0301BE_U0301_1: 0.1, Species.FLABE_U0301BE_U0301_2: 0.1, Species.FLABE_U0301BE_U0301_3: 0.1, Species.FLABE_U0301BE_U0301_4: 0.1,
    Species.FLOETTE_1: 0.9, Species.FLOETTE_2: 0.9, Species.FLOETTE_3: 0.9, Species.FLOETTE_4: 0.9, Species.FLOETTE_ETERNAL: 0.9,
    Species.FLORGES_1: 10.0, Species.FLORGES_2: 10.0, Species.FLORGES_3: 10.0, Species.FLORGES_4: 10.0, Species.FURFROU_1: 28.0,
    Species.FURFROU_2: 28.0, Species.FURFROU_3: 28.0, Species.FURFROU_4: 28.0, Species.FURFROU_5: 28.0, Species.FURFROU_6: 28.0,
    Species.FURFROU_7: 28.0, Species.FURFROU_8: 28.0, Species.FURFROU_9: 28.0, Species.MEOWSTIC_F: 8.5, Species.AEGISLASH_BLADE: 53.0,
    Species.PUMPKABOO_SMALL: 3.5, Species.PUMPKABOO_LARGE: 7.5, Species.PUMPKABOO_SUPER: 15.0, Species.GOURGEIST_SMALL: 9.5, Species.GOURGEIST_LARGE: 14.0,
    Species.GOURGEIST_SUPER: 39.0, Species.XERNEAS_NEUTRAL: 215.0, Species.ZYGARDE_10_AURA_BREAK: 33.5, Species.ZYGARDE_10: 33.5, Species.ZYGARDE: 305.0,
    Species.ZYGARDE_COMPLETE: 610.0, Species.HOOPA_UNBOUND: 490.0, Species.ORICORIO_POM_POM: 3.4, Species.ORICORIO_PA_U: 3.4, Species.ORICORIO_SENSU: 3.4,
    Species.ROCKRUFF_DUSK: 9.2, Species.LYCANROC_MIDNIGHT: 25.0, Species.LYCANROC_DUSK: 25.0, Species.WISHIWASHI_SCHOOL: 78.6, Species.SILVALLY_BUG: 100.5,
    Species.SILVALLY_DARK: 100.5, Species.SILVALLY_DRAGON: 100.5, Species.SILVALLY_ELECTRIC: 100.5, Species.SILVALLY_FAIRY: 100.5, Species.SILVALLY_FIGHTING: 100.5,
    Species.SILVALLY_FIRE: 100.5, Species.SILVALLY_FLYING: 100.5, Species.SILVALLY_GHOST: 100.5, Species.SILVALLY_GRASS: 100.5, Species.SILVALLY_GROUND: 100.5,
    Species.SILVALLY_ICE: 100.5, Species.SILVALLY_POISON: 100.5, Species.SILVALLY_PSYCHIC: 100.5, Species.SILVALLY_ROCK: 100.5, Species.SILVALLY_STEEL: 100.5,
    Species.SILVALLY_WATER: 100.5, Species.MIMIKYU_BUSTED: 0.7, Species.NECROZMA_DUSK_MANE: 460.0, Species.NECROZMA_DAWN_WINGS: 350.0, Species.NECROZMA_ULTRA: 230.0,
    Species.MAGEARNA_ORIGINAL: 80.5, Species.CRAMORANT_GULPING: 18.0, Species.CRAMORANT_GORGING: 18.0, Species.TOXTRICITY_LOW_KEY: 40.0, Species.SINISTEA_ANTIQUE: 0.2,
    Species.POLTEAGEIST_ANTIQUE: 0.4, Species.ALCREMIE_1: 0.5, Species.ALCREMIE_2: 0.5, Species.ALCREMIE_3: 0.5, Species.ALCREMIE_4: 0.5,
    Species.ALCREMIE_5: 0.5, Species.ALCREMIE_6: 0.5, Species.ALCREMIE_7: 0.5, Species.ALCREMIE_8: 0.5, Species.EISCUE_NOICE: 89.0,
    Species.INDEEDEE_F: 28.0, Species.MORPEKO_HANGRY: 3.0, Species.ZACIAN_CROWNED: 355.0, Species.ZAMAZENTA_CROWNED: 785.0, Species.ETERNATUS_ETERNAMAX: 0.0,
    Species.URSHIFU_RAPID_STRIKE: 105.0, Species.ZARUDE_DADA: 70.0, Species.CALYREX_ICE: 809.1, Species.CALYREX_SHADOW: 53.6, Species.MINIOR_METEOR: 40.0,
}
