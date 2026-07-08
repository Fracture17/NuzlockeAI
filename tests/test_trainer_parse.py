"""Tests for parsing the R&B calc's SETDEX_SS and enriching the old trainer roster."""
from liveplay.data.trainer import (
    Pokemon,
    Trainer,
    extract_setdex,
    build_calc_trainers,
    parse_old_name,
    parse_trainers_from_text,
    enrich_trainers,
    iv_tuple,
)


# A trimmed Trainer Battles.txt covering: a route header, a "~" separator double
# (two trainers cross-linked), a single-list "[Double]" couple, and a "[Boss]" solo.
TEXT_SNIPPET = """\
------
Route 127 (Optionals)
------
Bird Keeper Aidan [Double Battle With Cool Trainer Athena]
Bruxish Lv.89 @Assault Vest: Liquidation, Psychic Fangs [Jolly|Dazzling]
Samurott_Hisuian Lv.89 @Life Orb: Liquidation, Crunch [Naive|Torrent]
~
Incineroar Lv.89 @Iapapa Berry: Flare Blitz, Throat Chop [Jolly|Intimidate]
Pinsir Lv.90 @Pinsirite: Close Combat, Return [Jolly|Hyper Cutter]

Young Couple Brian&Casey [Double]
Audino Lv.72 @Chople Berry: Icy Wind, Heal Pulse [Bold|Regenerator]
Gengar Lv.71 @Poison Gem: Sludge Wave, Shadow Ball [Timid|Levitate]

Leader Brawly [Boss]
Hariyama Lv.20 @Sitrus Berry: Brick Break [Adamant|Guts]
"""


def test_parse_text_separator_double_splits_into_two_linked_trainers(tmp_path):
    p = tmp_path / "tb.txt"
    p.write_text(TEXT_SNIPPET, encoding="utf-8")
    trainers = parse_trainers_from_text(str(p))

    aidan, athena = trainers[0], trainers[1]
    assert aidan.name == "Bird Keeper Aidan" and athena.name == "Cool Trainer Athena"
    assert aidan.double and athena.double
    assert aidan.partner == 1 and athena.partner == 0          # cross-linked by index
    assert [m.name for m in aidan.pokemon] == ["Bruxish", "Samurott_Hisuian"]
    assert [m.name for m in athena.pokemon] == ["Incineroar", "Pinsir"]  # post-"~" block
    assert athena.route == "Route 127 (Optionals)"             # ally inherits route


def test_parse_text_single_list_double_has_no_partner(tmp_path):
    p = tmp_path / "tb.txt"
    p.write_text(TEXT_SNIPPET, encoding="utf-8")
    trainers = parse_trainers_from_text(str(p))

    couple = trainers[2]
    assert couple.name == "Young Couple Brian&Casey"
    assert couple.double is True and couple.partner is None
    assert [m.name for m in couple.pokemon] == ["Audino", "Gengar"]


def test_parse_text_boss_flag_and_clean_name(tmp_path):
    p = tmp_path / "tb.txt"
    p.write_text(TEXT_SNIPPET, encoding="utf-8")
    trainers = parse_trainers_from_text(str(p))

    brawly = trainers[3]
    assert brawly.name == "Leader Brawly"          # [Boss] tag stripped from OCR name
    assert brawly.boss is True and brawly.double is False and brawly.partner is None


# A trimmed SETDEX_SS snippet exercising: multi-mon-same-species (leading-space key),
# explicit reduced IVs, a default (no ivs) mon, and trailing commas / spaced numbers.
SNIPPET = (
    'var SETDEX_SS = {'
    '"Magikarp":{'
    '"Fisherman Darian":{"level":12 ,"ability":"Rattled","moves":["Bounce"],'
    '"nature":"Adamant","item":"Choice Band","index":14},'
    '" Fisherman Darian":{"level":12 ,"ability":"Rattled","moves":["Hydro Pump","Tackle","Flail"],'
    '"nature":"Hasty","item":"Focus Sash","ivs":{"hp":0,"df":0,"sd":0,},"index":15},},'
    '"Sharpedo":{'
    '"Aqua Leader Archie Mt Pyre":{"level":33 ,"ability":"Rough Skin",'
    '"moves":["Crunch","Waterfall"],"nature":"Adamant","item":"Life Orb","index":900},},'
    '};'
)


def test_extract_setdex_handles_trailing_commas_and_spaces():
    dex = extract_setdex(SNIPPET)
    assert dex["Magikarp"]["Fisherman Darian"]["level"] == 12
    assert dex["Magikarp"][" Fisherman Darian"]["ivs"] == {"hp": 0, "df": 0, "sd": 0}


def test_extract_setdex_tolerates_invalid_js_escapes():
    js = 'var SETDEX_SS = {"Aegislash":{"X":{"level":50,"ability":"a",' \
         '"moves":["King\\s Shield"],"nature":"Timid","item":"i","index":1},},};'
    dex = extract_setdex(js)
    assert dex["Aegislash"]["X"]["moves"] == ["Kings Shield"]


def test_extract_setdex_stops_at_statement_terminator():
    js = SNIPPET + "\nvar MEGA_BASE_ABILITIES = {\"Foo\":\"Bar\"};\n"
    dex = extract_setdex(js)
    assert "Foo" not in dex and "Magikarp" in dex


def test_build_groups_same_species_dups_and_orders_by_index():
    dex = extract_setdex(SNIPPET)
    by_name = {name: mons for name, mons in build_calc_trainers(dex)}
    darian = by_name["Fisherman Darian"]
    assert [p.name for p in darian] == ["Magikarp", "Magikarp"]
    assert darian[0].moves == ["Bounce"] and darian[0].ivs == {}
    assert darian[1].ivs == {"hp": 0, "df": 0, "sd": 0}


def test_darian_second_magikarp_is_not_31_everywhere():
    """Regression for the specific fact the old text pickle could not represent."""
    dex = extract_setdex(SNIPPET)
    darian = next(mons for name, mons in build_calc_trainers(dex) if name == "Fisherman Darian")
    assert iv_tuple(darian[1].ivs) == (0, 31, 0, 31, 0, 31)  # hp/df/sd dropped to 0


def test_iv_tuple_defaults_missing_to_31():
    assert iv_tuple({}) == (31, 31, 31, 31, 31, 31)
    assert iv_tuple({"sp": 0}) == (31, 31, 31, 31, 31, 0)
    assert iv_tuple({"at": 30, "sa": 30}) == (31, 30, 31, 30, 31, 31)


def test_parse_old_name_extracts_flags_and_partner():
    assert parse_old_name("Leader Brawly [Boss]") == ("Leader Brawly", True, False, None)
    assert parse_old_name("Twins Amy & Liv [Double]") == ("Twins Amy & Liv", False, True, None)
    name, boss, dbl, partner = parse_old_name(
        "Beauty Tiffany [Double Battle With Beauty Olivia] [Boss]"
    )
    assert (name, boss, dbl, partner) == ("Beauty Tiffany", True, True, "Beauty Olivia")
    assert parse_old_name("Fisherman Darian") == ("Fisherman Darian", False, False, None)


def _mon(species):
    return Pokemon(species, 10, None, [], "Hardy", "Static")


def test_enrich_overlays_calc_team_and_preserves_order():
    old = [
        Trainer(name="Pokemon Trainer May", route="Route 103"),          # calc-absent, kept
        Trainer(name="Fisherman Darian", route="Route 104 (South)"),
        Trainer(name="Aqua Leader Archie [Boss]", route="Mt. Pyre"),     # prefix + loc + Trainer-prefix
    ]
    old[0].pokemon = [_mon("Treecko")]
    dex = extract_setdex(SNIPPET)
    enriched, unmatched, unenriched = enrich_trainers(old, build_calc_trainers(dex))

    assert [t.name for t in enriched] == ["Pokemon Trainer May", "Fisherman Darian", "Aqua Leader Archie"]
    assert enriched[2].boss is True
    assert [p.name for p in enriched[1].pokemon] == ["Magikarp", "Magikarp"]   # calc overlay
    assert [p.name for p in enriched[2].pokemon] == ["Sharpedo"]               # located match
    assert [p.name for p in enriched[0].pokemon] == ["Treecko"]               # untouched
    assert unmatched == []
    assert unenriched == [0]                                                   # May kept as-is


def test_enrich_assigns_numbered_duplicates_in_order():
    old = [
        Trainer(name="Team Aqua Grunt", route="Aqua Hideout"),
        Trainer(name="Team Aqua Grunt", route="Aqua Hideout"),
    ]
    calc = [
        ("Team Aqua Grunt Aqua Hideout #2", [_mon("Carvanha")]),
        ("Team Aqua Grunt Aqua Hideout #1", [_mon("Poochyena")]),
    ]
    enriched, unmatched, unenriched = enrich_trainers(old, calc)
    assert unmatched == [] and unenriched == []
    assert [p.name for p in enriched[0].pokemon] == ["Poochyena"]  # #1 -> first old
    assert [p.name for p in enriched[1].pokemon] == ["Carvanha"]   # #2 -> second old


def test_enrich_reports_unmatched_calc():
    old = [Trainer(name="Fisherman Darian", route="Route 104 (South)")]
    calc = [("Fisherman Darian", [_mon("Magikarp")]), ("Ghost Trainer Nobody", [_mon("Gastly")])]
    enriched, unmatched, unenriched = enrich_trainers(old, calc)
    assert unmatched == ["Ghost Trainer Nobody"]
    assert unenriched == []
