# Tests for PokemonSnapshot.from_wire and MGBASocketClient party/box methods.
# Written before implementation; all tests are expected to fail until code is in place.
import pytest
from unittest.mock import patch

from liveplay.emulator.pokemon_snapshot import PokemonSnapshot


# ---------------------------------------------------------------------------
# Wire-format test fixtures
# ---------------------------------------------------------------------------

# Full 50-field party line (box=-1, all optional fields populated).
_PARTY_LINE = (
    "-1|2|25|Pikachu|RED|12345|98765|0|0|1|"  # box,slot,species,nickname,otName,otId,personality,isEgg,isBadEgg,hasSpecies
    "0|5000|128|0|"                             # heldItem,experience,friendship,ppBonuses
    "85|72|0|0|"                                # move0,move1,move2,move3
    "35|35|5|0|"                                # pp0,pp1,pp2,pp3
    "0|0|0|0|0|0|"                              # hpEV,atkEV,defEV,speEV,spaEV,spdEV
    "31|31|31|31|31|31|"                        # hpIV,atkIV,defIV,speIV,spaIV,spdIV
    "4|0|0|4|12|5|3|"                           # nature,altAbility,pokerus,pokeball,metLocation,metLevel,metGame
    "50|45|60|0|55|40|45|50|50"                 # level,currentHP,maxHP,status,attack,defense,speed,spAttack,spDefense
)

# Full 50-field box line (box=0, slot=7, optional fields 41-49 are empty strings).
_BOX_LINE = (
    "0|7|25|Pikachu|RED|12345|98765|0|0|1|"
    "0|5000|128|0|"
    "85|72|0|0|"
    "35|35|5|0|"
    "0|0|0|0|0|0|"
    "31|31|31|31|31|31|"
    "4|0|0|4|12|5|3|"
    "||||||||"  # 9 empty fields (level through spDefense)
)

# Second line for multi-mon tests.
_PARTY_LINE_2 = (
    "-1|1|1|Bulbasaur|RED|12345|11111|0|0|1|"
    "0|1000|50|0|"
    "33|0|0|0|"
    "35|0|0|0|"
    "252|4|0|0|0|0|"
    "31|31|31|31|31|31|"
    "2|1|0|4|5|5|3|"
    "10|28|30|0|30|25|20|15|20"
)

_BOX_LINE_2 = (
    "1|0|4|Charmander|BLUE|99999|22222|0|0|1|"
    "0|800|100|0|"
    "10|0|0|0|"
    "35|0|0|0|"
    "0|252|0|0|0|0|"
    "31|31|31|31|31|31|"
    "1|0|0|4|3|5|3|"
    "||||||||"
)

_BOX_LINE_3 = (
    "2|5|6|Charizard|ASH|11111|33333|0|0|1|"
    "50|50000|200|3|"
    "13|17|0|0|"
    "15|15|0|0|"
    "0|0|252|0|0|4|"
    "31|31|31|31|31|31|"
    "0|0|0|4|10|36|3|"
    "||||||||"
)


# ---------------------------------------------------------------------------
# PokemonSnapshot.from_wire
# ---------------------------------------------------------------------------

class TestFromWireParty:
    def test_all_fields_parsed(self):
        snap = PokemonSnapshot.from_wire(_PARTY_LINE)
        assert snap.box == -1
        assert snap.slot == 2
        assert snap.species == 25
        assert snap.nickname == "Pikachu"
        assert snap.ot_name == "RED"
        assert snap.ot_id == 12345
        assert snap.personality == 98765
        assert snap.is_egg is False
        assert snap.is_bad_egg is False
        assert snap.has_species is True
        assert snap.held_item == 0
        assert snap.experience == 5000
        assert snap.friendship == 128
        assert snap.pp_bonuses == 0

    def test_moves_as_tuple(self):
        snap = PokemonSnapshot.from_wire(_PARTY_LINE)
        assert snap.moves == (85, 72, 0, 0)
        assert isinstance(snap.moves, tuple)

    def test_pp_as_tuple(self):
        snap = PokemonSnapshot.from_wire(_PARTY_LINE)
        assert snap.pp == (35, 35, 5, 0)
        assert isinstance(snap.pp, tuple)

    def test_evs(self):
        snap = PokemonSnapshot.from_wire(_PARTY_LINE)
        assert snap.hp_ev == 0
        assert snap.atk_ev == 0
        assert snap.def_ev == 0
        assert snap.spe_ev == 0
        assert snap.spa_ev == 0
        assert snap.spd_ev == 0

    def test_ivs(self):
        snap = PokemonSnapshot.from_wire(_PARTY_LINE)
        assert snap.hp_iv == 31
        assert snap.atk_iv == 31
        assert snap.def_iv == 31
        assert snap.spe_iv == 31
        assert snap.spa_iv == 31
        assert snap.spd_iv == 31

    def test_misc_fields(self):
        snap = PokemonSnapshot.from_wire(_PARTY_LINE)
        assert snap.nature == 4
        assert snap.alt_ability == 0
        assert snap.pokerus == 0
        assert snap.pokeball == 4
        assert snap.met_location == 12
        assert snap.met_level == 5
        assert snap.met_game == 3

    def test_party_optional_fields_set(self):
        snap = PokemonSnapshot.from_wire(_PARTY_LINE)
        assert snap.level == 50
        assert snap.current_hp == 45
        assert snap.max_hp == 60
        assert snap.status == 0
        assert snap.attack == 55
        assert snap.defense == 40
        assert snap.speed == 45
        assert snap.sp_attack == 50
        assert snap.sp_defense == 50

    def test_in_party_true(self):
        snap = PokemonSnapshot.from_wire(_PARTY_LINE)
        assert snap.in_party is True


class TestFromWireBox:
    def test_box_optional_fields_none(self):
        snap = PokemonSnapshot.from_wire(_BOX_LINE)
        assert snap.level is None
        assert snap.current_hp is None
        assert snap.max_hp is None
        assert snap.status is None
        assert snap.attack is None
        assert snap.defense is None
        assert snap.speed is None
        assert snap.sp_attack is None
        assert snap.sp_defense is None

    def test_in_party_false(self):
        snap = PokemonSnapshot.from_wire(_BOX_LINE)
        assert snap.in_party is False

    def test_box_and_slot(self):
        snap = PokemonSnapshot.from_wire(_BOX_LINE)
        assert snap.box == 0
        assert snap.slot == 7

    def test_non_party_fields_still_parsed(self):
        snap = PokemonSnapshot.from_wire(_BOX_LINE)
        assert snap.species == 25
        assert snap.nickname == "Pikachu"
        assert snap.moves == (85, 72, 0, 0)


class TestFromWireErrors:
    def test_wrong_field_count_raises_value_error(self):
        bad_line = "1|2|3"
        with pytest.raises(ValueError, match="expected 50 fields"):
            PokemonSnapshot.from_wire(bad_line)

    def test_49_fields_raises(self):
        # One field short of a valid box line.
        parts = _BOX_LINE.split("|")
        assert len(parts) == 50
        short = "|".join(parts[:49])
        with pytest.raises(ValueError):
            PokemonSnapshot.from_wire(short)

    def test_51_fields_raises(self):
        with pytest.raises(ValueError):
            PokemonSnapshot.from_wire(_BOX_LINE + "|extra")


# ---------------------------------------------------------------------------
# MGBASocketClient party/box methods (mocked _send_data)
# ---------------------------------------------------------------------------

from liveplay.emulator.socket_client import MGBASocketClient


def _make_client() -> MGBASocketClient:
    """Return an MGBASocketClient with no real socket."""
    return MGBASocketClient()


class TestReadParty:
    def test_two_mons_returned(self):
        client = _make_client()
        payload = _PARTY_LINE + "\n" + _PARTY_LINE_2
        with patch.object(client, "_send_data", return_value=payload):
            result = client.read_party()
        assert len(result) == 2
        assert isinstance(result[0], PokemonSnapshot)
        assert isinstance(result[1], PokemonSnapshot)
        assert result[0].species == 25
        assert result[1].species == 1

    def test_empty_string_returns_empty_list(self):
        client = _make_client()
        with patch.object(client, "_send_data", return_value=""):
            result = client.read_party()
        assert result == []

    def test_sends_readparty_command(self):
        client = _make_client()
        with patch.object(client, "_send_data", return_value="") as mock_send:
            client.read_party()
        mock_send.assert_called_once_with("readparty")


class TestReadBoxMon:
    def test_returns_snapshot(self):
        client = _make_client()
        with patch.object(client, "_send_data", return_value=_BOX_LINE):
            result = client.read_box_mon(0, 7)
        assert result is not None
        assert isinstance(result, PokemonSnapshot)
        assert result.box == 0
        assert result.slot == 7

    def test_empty_string_returns_none(self):
        client = _make_client()
        with patch.object(client, "_send_data", return_value=""):
            result = client.read_box_mon(3, 15)
        assert result is None

    def test_sends_correct_command(self):
        client = _make_client()
        with patch.object(client, "_send_data", return_value="") as mock_send:
            client.read_box_mon(5, 12)
        mock_send.assert_called_once_with("readbox 5 12")


class TestReadAllBoxes:
    def test_three_mons_returned(self):
        client = _make_client()
        payload = "\n".join([_BOX_LINE, _BOX_LINE_2, _BOX_LINE_3])
        with patch.object(client, "_send_data", return_value=payload):
            result = client.read_all_boxes()
        assert len(result) == 3
        assert result[0].box == 0
        assert result[1].box == 1
        assert result[2].box == 2

    def test_sends_readallboxes_command(self):
        client = _make_client()
        with patch.object(client, "_send_data", return_value="") as mock_send:
            client.read_all_boxes()
        mock_send.assert_called_once_with("readallboxes")
