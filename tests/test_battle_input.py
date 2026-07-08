# Tests for src/emulator/battle_input.py: find_member_by_name and handle_battle_screen.
import pytest

from liveplay.data.species import Species
from liveplay.data.moves import Move
from liveplay.data.natures import Nature
from liveplay.state.pokemon import PokemonState, GenderEnum
from liveplay.state.side import SideState
from liveplay.state.battle import BattleState
from liveplay.vision.ocr import PartyMemberResult
from liveplay.battle_message_matcher import ScreenKind
from liveplay.battle_policy import BattlePolicy


def _make_member(name, slot_index, hp_current=50, status=None):
    return PartyMemberResult(
        name=name,
        level=50,
        hp_current=hp_current,
        hp_max=100,
        status=status,
        slot_index=slot_index,
    )


def _make_mon(species=Species.RATTATA, move_ids=None, move_pp=None, hp=50, fainted=False):
    move_ids = move_ids or (Move.TACKLE, Move.SCRATCH, Move.NONE, Move.NONE)
    move_pp = move_pp or (35, 20, 0, 0)
    mon = PokemonState(
        species=species,
        nature=Nature.HARDY,
        ivs=(31,) * 6,
        gender=GenderEnum.MALE,
        move_ids=move_ids,
        move_pp=move_pp,
    )
    return mon._replace(hp=hp, fainted=fainted)


def _make_battle_state(active_species=Species.BULBASAUR, bench_species=Species.CHARMANDER,
                       active_moves=None, active_pp=None):
    if active_moves is None:
        active_moves = (Move.TACKLE, Move.SCRATCH, Move.NONE, Move.NONE)
    if active_pp is None:
        active_pp = (35, 20, 0, 0)
    active = _make_mon(active_species, move_ids=active_moves, move_pp=active_pp)
    bench = _make_mon(bench_species)
    side0 = SideState(team=[active, bench], active_indices=[0])
    side1 = SideState(team=[_make_mon(Species.PIDGEY)], active_indices=[0])
    return BattleState(sides=(side0, side1))


class FakeSocket:
    """Records add_key/clear_key calls."""
    def __init__(self):
        self.log = []

    def add_key(self, key):
        self.log.append(("add", key))

    def clear_key(self, key):
        self.log.append(("clear", key))


class FakeScreenCapture:
    """Minimal ScreenCapture fake: invalidate() and capture() are no-ops."""
    def invalidate(self):
        pass

    def capture(self, *args):
        return None


class StubPolicy(BattlePolicy):
    """Policy that returns a preset action for choose_battle_action and preset species for forced switch."""
    def __init__(self, battle_action=None, forced_switch=None, raise_on_forced=False):
        self._battle_action = battle_action
        self._forced_switch = forced_switch
        self._raise_on_forced = raise_on_forced

    def choose_battle_action(self, state):
        return self._battle_action

    def choose_forced_switch(self, state):
        if self._raise_on_forced:
            raise AssertionError("choose_forced_switch should not have been called")
        return self._forced_switch


# ---------------------------------------------------------------------------
# find_member_by_name
# ---------------------------------------------------------------------------

class TestFindMemberByName:

    def setup_method(self):
        from liveplay.emulator.battle_input import find_member_by_name
        self.find = find_member_by_name

    def test_exact_normalized_match(self):
        members = [_make_member("BULBASAUR", 0), _make_member("CHARMANDER", 1)]
        result = self.find(members, "BULBASAUR")
        assert result.slot_index == 0

    def test_case_insensitive(self):
        members = [_make_member("Bulbasaur", 0), _make_member("Charmander", 1)]
        result = self.find(members, "BULBASAUR")
        assert result.slot_index == 0

    def test_special_chars_nidoran_m(self):
        # OCR might return "Nidoran" without the male symbol; species name is "NIDORAN_M"
        # Normalized: "NIDORANM" vs "NIDORAN" -> distance 1, threshold=max(2,7//4)=2, accept
        members = [_make_member("Nidoran", 2)]
        result = self.find(members, "NIDORAN_M")
        assert result.slot_index == 2

    def test_mr_mime_normalization(self):
        # "MR_MIME" normalizes to "MRMIME"; OCR "MrMime" normalizes to "MRMIME" -> exact
        members = [_make_member("MrMime", 3)]
        result = self.find(members, "MR_MIME")
        assert result.slot_index == 3

    def test_regional_form_suffix_matches_base_name(self):
        # Party menu shows the base species name ("Zigzagoon"), OCR-truncated to
        # "Zigzagoo". Species name carries a regional-form suffix "ZIGZAGOON_GALAR".
        # Without stripping the suffix, distance("ZIGZAGOONGALAR","ZIGZAGOO")=6 > thr.
        members = [_make_member("Zigzagoo", 4), _make_member("BUDEW", 1)]
        result = self.find(members, "ZIGZAGOON_GALAR")
        assert result.slot_index == 4

    def test_alolan_form_suffix_matches_base_name(self):
        members = [_make_member("Raichu", 0)]
        result = self.find(members, "RAICHU_ALOLA")
        assert result.slot_index == 0

    def test_raises_on_absent_name(self):
        members = [_make_member("BULBASAUR", 0), _make_member("CHARMANDER", 1)]
        with pytest.raises(RuntimeError):
            self.find(members, "MEWTWO")

    def test_none_name_member_does_not_crash(self):
        # A member with name=None should be skipped gracefully (normalized as empty string)
        members = [_make_member(None, 0), _make_member("BULBASAUR", 1)]
        result = self.find(members, "BULBASAUR")
        assert result.slot_index == 1

    def test_picks_closest_when_multiple_fuzzy(self):
        members = [_make_member("BULBASUR", 0), _make_member("BSAUR", 1)]
        # "BULBASAUR" vs "BULBASUR" -> distance 1; vs "BSAUR" -> distance 4
        result = self.find(members, "BULBASAUR")
        assert result.slot_index == 0


# ---------------------------------------------------------------------------
# handle_battle_screen
# ---------------------------------------------------------------------------

class TestHandleBattleScreen:

    def _call(self, monkeypatch, socket, screen_kind, battle_state, policy, pending_ref,
              move_input_calls=None, members_override=None, sleep_calls=None):
        """Call handle_battle_screen with mocked time.sleep, _send_move_input, _read_party_members."""
        import liveplay.emulator.battle_input as bi

        recorded_slots = [] if move_input_calls is None else move_input_calls
        monkeypatch.setattr("liveplay.emulator.battle_input._send_move_input",
                            lambda sock, slot: recorded_slots.append(slot))
        monkeypatch.setattr("time.sleep", lambda _: None)

        if members_override is not None:
            monkeypatch.setattr("liveplay.emulator.battle_input._read_party_members",
                                lambda sc: members_override)

        from liveplay.emulator.battle_input import handle_battle_screen
        handle_battle_screen(socket, FakeScreenCapture(), screen_kind, battle_state, policy, pending_ref)
        return recorded_slots

    def test_option_select_move_calls_send_move_input(self, monkeypatch):
        state = _make_battle_state(
            active_moves=(Move.TACKLE, Move.SCRATCH, Move.NONE, Move.NONE),
            active_pp=(35, 20, 0, 0),
        )
        # TACKLE is at slot 0
        policy = StubPolicy(battle_action=Move.TACKLE)
        pending = [None]
        slots = []
        self._call(monkeypatch, FakeSocket(), ScreenKind.OPTION_SELECT, state, policy, pending,
                   move_input_calls=slots)
        assert slots == [0]
        assert pending[0] is None

    def test_option_select_move_correct_slot_index(self, monkeypatch):
        state = _make_battle_state(
            active_moves=(Move.TACKLE, Move.SCRATCH, Move.NONE, Move.NONE),
            active_pp=(35, 20, 0, 0),
        )
        # SCRATCH is at slot 1
        policy = StubPolicy(battle_action=Move.SCRATCH)
        pending = [None]
        slots = []
        self._call(monkeypatch, FakeSocket(), ScreenKind.OPTION_SELECT, state, policy, pending,
                   move_input_calls=slots)
        assert slots == [1]

    def test_option_select_switch_sets_pending_and_navigates(self, monkeypatch):
        state = _make_battle_state()
        policy = StubPolicy(battle_action="CHARMANDER")
        pending = [None]
        socket = FakeSocket()
        self._call(monkeypatch, socket, ScreenKind.OPTION_SELECT, state, policy, pending)
        assert pending[0] == "CHARMANDER"
        # Navigation: down pressed (Fight->Pokémon) then A pressed
        keys_added = [key for event, key in socket.log if event == "add"]
        assert "down" in keys_added
        assert "a" in keys_added

    def test_option_select_switch_does_not_call_send_party_selection(self, monkeypatch):
        state = _make_battle_state()
        policy = StubPolicy(battle_action="CHARMANDER")
        pending = [None]

        send_party_calls = []
        monkeypatch.setattr("liveplay.emulator.battle_input.send_party_selection",
                            lambda sock, members, target: send_party_calls.append(target))
        monkeypatch.setattr("time.sleep", lambda _: None)
        monkeypatch.setattr("liveplay.emulator.battle_input._send_move_input",
                            lambda sock, slot: None)

        from liveplay.emulator.battle_input import handle_battle_screen
        handle_battle_screen(FakeSocket(), FakeScreenCapture(), ScreenKind.OPTION_SELECT,
                             state, policy, pending)
        assert send_party_calls == []

    def test_party_menu_with_pending_calls_send_party_selection(self, monkeypatch):
        state = _make_battle_state()
        policy = StubPolicy(raise_on_forced=True)
        pending = ["CHARMANDER"]
        members = [_make_member("BULBASAUR", 0), _make_member("CHARMANDER", 1)]

        send_party_calls = []
        monkeypatch.setattr("liveplay.emulator.battle_input.send_party_selection",
                            lambda sock, mems, target: send_party_calls.append(target))
        monkeypatch.setattr("time.sleep", lambda _: None)
        monkeypatch.setattr("liveplay.emulator.battle_input._read_party_members",
                            lambda sc: members)

        from liveplay.emulator.battle_input import handle_battle_screen
        handle_battle_screen(FakeSocket(), FakeScreenCapture(), ScreenKind.PARTY_MENU,
                             state, policy, pending)
        assert send_party_calls == ["CHARMANDER"]
        assert pending[0] is None

    def test_party_menu_without_pending_calls_choose_forced_switch(self, monkeypatch):
        state = _make_battle_state()
        policy = StubPolicy(forced_switch="SQUIRTLE")
        pending = [None]
        members = [_make_member("BULBASAUR", 0), _make_member("SQUIRTLE", 1)]

        send_party_calls = []
        monkeypatch.setattr("liveplay.emulator.battle_input.send_party_selection",
                            lambda sock, mems, target: send_party_calls.append(target))
        monkeypatch.setattr("time.sleep", lambda _: None)
        monkeypatch.setattr("liveplay.emulator.battle_input._read_party_members",
                            lambda sc: members)

        from liveplay.emulator.battle_input import handle_battle_screen
        handle_battle_screen(FakeSocket(), FakeScreenCapture(), ScreenKind.PARTY_MENU,
                             state, policy, pending)
        assert send_party_calls == ["SQUIRTLE"]

    def test_option_select_move_not_in_moveset_raises(self, monkeypatch):
        state = _make_battle_state(
            active_moves=(Move.TACKLE, Move.NONE, Move.NONE, Move.NONE),
            active_pp=(35, 0, 0, 0),
        )
        # FLAMETHROWER is not in the moveset
        policy = StubPolicy(battle_action=Move.FLAMETHROWER)
        pending = [None]
        monkeypatch.setattr("time.sleep", lambda _: None)
        monkeypatch.setattr("liveplay.emulator.battle_input._send_move_input",
                            lambda sock, slot: None)

        from liveplay.emulator.battle_input import handle_battle_screen
        with pytest.raises(RuntimeError):
            handle_battle_screen(FakeSocket(), FakeScreenCapture(), ScreenKind.OPTION_SELECT,
                                 state, policy, pending)
