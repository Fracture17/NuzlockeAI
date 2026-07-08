# Tests for helper functions in SCRIPTS/play.py.
# play.py has heavy vision/OCR imports; we stub them before importing.
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Stub out unavailable optional deps before importing play
_STUB_MODULES = ("liveplay.vision.ocr", "liveplay.vision.capture", "liveplay.vision.hp_bar")
for mod in _STUB_MODULES:
    sys.modules.setdefault(mod, MagicMock())


@pytest.fixture(autouse=True, scope="module")
def _restore_stubbed_modules():
    """Remove vision stubs after this module's tests so later modules get the real imports."""
    yield
    for mod in _STUB_MODULES:
        sys.modules.pop(mod, None)


sys.path.insert(0, str(Path(__file__).parent.parent / "SCRIPTS"))
import play as play_module

_lookup_enum = play_module._lookup_enum
_trainer_pokemon_to_state = play_module._trainer_pokemon_to_state

import json
import pickle
from types import SimpleNamespace
from liveplay.data.moves import Move
from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.species import Species
from liveplay.emulator.pokemon_snapshot import PokemonSnapshot
from liveplay.state.battle import BattleState
from liveplay.state.side import SideState

_snapshot_to_pokemon_state = play_module._snapshot_to_pokemon_state
_select_active_opp_klog = play_module._select_active_opp_klog
_resolve_team_mon = play_module._resolve_team_mon
_split_trainer_name = play_module._split_trainer_name
_snapshots_to_states = play_module._snapshots_to_states
_save_training_snapshot = play_module._save_training_snapshot
_move_from_gba_id = play_module._move_from_gba_id


class TestSplitTrainerName:
    """Trainer pkl names carry Run & Bun bracket annotations ([Boss], [Double], etc.)
    that are NOT shown in-game. The intro message ('<class> <name> would like to
    battle!') matches the in-game display, so the constraint must strip annotations
    before splitting class/name — otherwise the trailing '[Boss]' poisons the match.

    The split point itself is cosmetic: the matcher rejoins class+name, so the
    contract is that the rejoined string equals the annotation-stripped display name."""

    @staticmethod
    def _rejoin(name: str) -> str:
        cls, nm = _split_trainer_name(name)
        return f"{cls} {nm}".strip()

    def test_strips_boss_annotation(self):
        assert self._rejoin("Team Aqua Grunt [Boss]") == "Team Aqua Grunt"

    def test_strips_double_annotation_preserves_name(self):
        assert self._rejoin("Pokemon Trainer May [Double]") == "Pokemon Trainer May"

    def test_strips_double_battle_with_annotation(self):
        assert self._rejoin("Aroma Lady Rose [Double Battle With Tate]") == "Aroma Lady Rose"

    def test_no_annotation_two_word(self):
        assert _split_trainer_name("Lass Haley") == ("Lass", "Haley")

    def test_no_annotation_single_word(self):
        assert _split_trainer_name("Wally") == ("Wally", "")


class TestSelectActiveOppKlog:
    """The sweep must read the CURRENTLY-ACTIVE opponent's k-pixel HP log, not an
    arbitrary dict entry. opp_k_logs accumulates stale entries for opponents that
    fainted/switched out; next(iter(...)) returned the wrong (stale) mon's log and
    silently zeroed out HP deltas (regression: 4-hit Double Slap rejected because a
    fainted lead's single-value log produced empty deltas)."""

    def test_exact_match_ignores_stale_first_entry(self):
        # poochyena (fainted lead) inserted first; lillipup is active.
        logs = {"poochyena": [7], "lillipup": [48, 10]}
        assert _select_active_opp_klog(logs, "LILLIPUP") == [48, 10]

    def test_exact_match_lowercased(self):
        logs = {"skitty": [48, 25]}
        assert _select_active_opp_klog(logs, "Skitty") == [48, 25]

    def test_empty_dict_returns_empty(self):
        assert _select_active_opp_klog({}, "LILLIPUP") == []

    def test_fuzzy_fallback_close_key(self):
        # OCR misread the active opponent's name by one char.
        logs = {"poochyena": [7], "lilipup": [48, 10]}
        assert _select_active_opp_klog(logs, "LILLIPUP") == [48, 10]

    def test_no_plausible_match_raises(self):
        logs = {"poochyena": [7], "rookidee": [48]}
        with pytest.raises(Exception):
            _select_active_opp_klog(logs, "EXEGGCUTE")

class TestResolveTeamMon:
    """The sweep resolves a lowercased OCR HP-log name to a player team mon by species
    name. Regional forms (e.g. ZIGZAGOON_GALAR) OCR as their base display name
    ('zigzagoon'); the raw enum name carries a '_GALAR' suffix that pushes Levenshtein
    distance past the fuzzy threshold, so matching must go through emulator_species_name
    (regression: 'zigzagoon' refused to match team species ['ZIGZAGOON_GALAR', ...])."""

    @staticmethod
    def _team(*species):
        return [SimpleNamespace(species=s) for s in species]

    def test_exact_match_returns_mon_and_index(self):
        team = self._team(Species.LILLIPUP, Species.BUDEW)
        mon, idx = _resolve_team_mon("budew", team)
        assert idx == 1 and mon.species == Species.BUDEW

    def test_regional_form_matches_base_display_name(self):
        # 'zigzagoon' (in-game display) must match ZIGZAGOON_GALAR via the base name.
        team = self._team(Species.BUDEW, Species.ZIGZAGOON_GALAR, Species.NATU)
        mon, idx = _resolve_team_mon("zigzagoon", team)
        assert idx == 1 and mon.species == Species.ZIGZAGOON_GALAR

    def test_fuzzy_fallback_one_glyph_off(self):
        team = self._team(Species.LILLIPUP, Species.BUDEW)
        mon, idx = _resolve_team_mon("lilipup", team)
        assert idx == 0 and mon.species == Species.LILLIPUP

    def test_no_plausible_match_raises(self):
        team = self._team(Species.LILLIPUP, Species.BUDEW)
        with pytest.raises(Exception):
            _resolve_team_mon("charizard", team)


# Minimal valid party wire line: Bulbasaur, level 5, all moves empty (id 0).
# Fields: box|slot|species|nick|ot|ot_id|pers|egg|badegg|hasspecies|
#         item|experience|friendship|ppbonus| moves(4)| pp(4)| evs(6)| ivs(6)|
#         nature|altability|pokerus|ball|metloc|metlvl|metgame|
#         level|curhp|maxhp|status|atk|def|spe|spa|spd
_PARTY_LINE = (
    "-1|0|1|Bulbasaur|RED|12345|98765|0|0|1|"
    "0|999|128|0|"
    "0|0|0|0|"
    "35|0|0|0|"
    "0|0|0|0|0|0|"
    "31|31|31|31|31|31|"
    "2|0|0|4|5|5|3|"
    "5|18|21|0|11|11|11|11|11"
)


class TestLookupEnum:
    def test_known_member_no_default(self):
        result = _lookup_enum(Move, "Tackle")
        assert result == Move.TACKLE

    def test_known_member_with_default(self):
        # default is ignored when member exists
        result = _lookup_enum(Move, "Tackle", default=Move.NONE)
        assert result == Move.TACKLE

    def test_unknown_member_with_default(self):
        result = _lookup_enum(Move, "TOTALLY_FAKE_MOVE_XYZ", default=Move.NONE)
        assert result == Move.NONE

    def test_unknown_member_no_default_raises(self):
        with pytest.raises(ValueError) as exc_info:
            _lookup_enum(Move, "TOTALLY_FAKE_MOVE_XYZ")
        msg = str(exc_info.value)
        assert "Move" in msg
        assert "TOTALLY_FAKE_MOVE_XYZ" in msg

    def test_unknown_member_error_message_contains_normalized_key(self):
        with pytest.raises(ValueError) as exc_info:
            _lookup_enum(Move, "fake move name")
        msg = str(exc_info.value)
        # Normalized key should appear in message
        assert "FAKE_MOVE_NAME" in msg

    def test_name_normalization_spaces(self):
        # "Ice Beam" should normalize to ICE_BEAM
        result = _lookup_enum(Move, "Ice Beam")
        assert result == Move.ICE_BEAM

    def test_name_normalization_hyphens(self):
        # "Pin-Missile" should normalize to PIN_MISSILE
        result = _lookup_enum(Move, "Pin-Missile")
        assert result == Move.PIN_MISSILE

    def test_name_normalization_mixed_case(self):
        result = _lookup_enum(Move, "tackle")
        assert result == Move.TACKLE

    def test_ability_none_default(self):
        result = _lookup_enum(Ability, "NotRealAbility", default=Ability.NONE)
        assert result == Ability.NONE

    def test_item_none_default(self):
        result = _lookup_enum(Item, "NotRealItem", default=Item.NONE)
        assert result == Item.NONE

    def test_explicit_none_default_returns_none(self):
        # Passing default=None explicitly should return None, not raise.
        result = _lookup_enum(Move, "TOTALLY_FAKE_MOVE_XYZ", default=None)
        assert result is None

    # --- override aliases: external names that don't normalize onto a member ---

    def test_move_alias_vice_grip(self):
        # "Vice Grip" would normalize to VICE_GRIP, but the member is VISE_GRIP.
        assert _lookup_enum(Move, "Vice Grip") == Move.VISE_GRIP

    def test_move_alias_natures_madness(self):
        assert _lookup_enum(Move, "Natures Madness") == Move.NATURE_S_MADNESS

    def test_move_alias_kings_shield(self):
        assert _lookup_enum(Move, "Kings Shield") == Move.KING_S_SHIELD

    def test_item_alias_kings_rock(self):
        assert _lookup_enum(Item, "Kings Rock") == Item.KING_S_ROCK

    def test_ability_alias_as_one_glastrier(self):
        # Parentheses defeat normalization; the alias resolves it.
        assert _lookup_enum(Ability, "As One (Glastrier)") == Ability.AS_ONE_GLASTRIER

    def test_species_alias_form(self):
        assert _lookup_enum(Species, "Weezing_Galarian") == Species.WEEZING_GALAR

    def test_species_alias_apostrophe_form(self):
        assert _lookup_enum(Species, "Farfetchd_Galarian") == Species.FARFETCH_U2019D_GALAR

    def test_alias_wins_over_direct_lookup(self):
        # An aliased name resolves to its override even though a normalized
        # direct lookup would miss; precedence is alias first.
        assert _lookup_enum(Item, "Kings Rock") == Item.KING_S_ROCK

    def test_non_aliased_name_still_uses_direct_lookup(self):
        # Names absent from the alias map fall through to normalized lookup.
        assert _lookup_enum(Move, "Ice Beam") == Move.ICE_BEAM

    def test_aliased_class_unknown_name_still_raises(self):
        # An enum with aliases still raises (no silent NONE) for a truly unknown
        # name that is neither aliased nor a normalized member.
        with pytest.raises(ValueError):
            _lookup_enum(Item, "TotallyFakeItemXYZ")


class TestTrainerPokemonToState:
    """No-silent-NONE: unmatched trainer data must raise, not default to NONE."""

    def _tp(self, **overrides):
        base = dict(
            name="Pikachu",
            level=5,
            item="",
            moves=["Tackle"],
            nature="Hardy",
            ability="Static",
        )
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_unmatched_item_raises(self):
        with pytest.raises(ValueError):
            _trainer_pokemon_to_state(self._tp(item="TotallyFakeItemXYZ"))

    def test_unmatched_move_raises(self):
        with pytest.raises(ValueError):
            _trainer_pokemon_to_state(self._tp(moves=["TotallyFakeMoveXYZ"]))

    def test_unmatched_ability_raises(self):
        with pytest.raises(ValueError):
            _trainer_pokemon_to_state(self._tp(ability="TotallyFakeAbilityXYZ"))

    def test_empty_item_is_none(self):
        state = _trainer_pokemon_to_state(self._tp(item=""))
        assert state.item == Item.NONE

    def test_aliased_item_resolves(self):
        state = _trainer_pokemon_to_state(self._tp(item="Kings Rock"))
        assert state.item == Item.KING_S_ROCK

    def test_aliased_species_resolves(self):
        state = _trainer_pokemon_to_state(self._tp(name="Weezing_Galarian"))
        assert state.species == Species.WEEZING_GALAR

    def test_move_pp_slot0_maxed_others_base(self):
        # Run & Bun trainer mons get one PP Up bundle on their FIRST slot only
        # (max PP); remaining slots stay at base PP (Issue 10). Under-estimating
        # slot 0 wrongly drops an observed move and crashes the sweep.
        from liveplay.data.moves import MOVE_DATA
        state = _trainer_pokemon_to_state(
            self._tp(moves=["Bounce", "Tackle", "Growl", "Splash"])
        )
        bounce_base = MOVE_DATA[Move.BOUNCE].pp
        assert state.move_pp[0] == bounce_base + (bounce_base // 5) * 3
        assert state.move_pp[0] == 8
        assert state.move_pp[1] == MOVE_DATA[Move.TACKLE].pp
        assert state.move_pp[2] == MOVE_DATA[Move.GROWL].pp
        assert state.move_pp[3] == MOVE_DATA[Move.SPLASH].pp

    def test_move_pp_none_slots_are_zero(self):
        state = _trainer_pokemon_to_state(self._tp(moves=["Tackle"]))
        assert state.move_pp[1:] == (0, 0, 0)


class TestSnapshotToPokemonState:
    def _snap(self, experience: int):
        snap = PokemonSnapshot.from_wire(_PARTY_LINE)
        object.__setattr__(snap, "experience", experience)
        return snap

    def test_exp_carried_through(self):
        # The live game's accumulated EXP must reach PokemonState so the sim can level up.
        snap = self._snap(experience=12345)
        state = _snapshot_to_pokemon_state(snap)
        assert state.exp == 12345

    def test_level_carried_through(self):
        snap = self._snap(experience=999)
        state = _snapshot_to_pokemon_state(snap)
        assert state.level == 5

    def test_species_mapped(self):
        snap = self._snap(experience=999)
        state = _snapshot_to_pokemon_state(snap)
        assert state.species == Species.BULBASAUR

    def test_ability_slot_zero(self):
        # alt_ability=0 selects slot 0 directly.
        snap = self._snap(experience=999)
        object.__setattr__(snap, "species", Species.SKITTY.value)
        object.__setattr__(snap, "alt_ability", 0)
        state = _snapshot_to_pokemon_state(snap)
        assert state.ability == Ability.NORMALIZE

    def test_box_mon_level_derived_from_exp(self):
        # Box mons carry no stored level (field empty -> None); level must be
        # reconstructed from EXP. Bulbasaur is MEDIUM_SLOW; exp_for_level(5)=135.
        from liveplay.data.growth_rate import GrowthRate, exp_for_level
        snap = PokemonSnapshot.from_wire(_PARTY_LINE)
        object.__setattr__(snap, "level", None)
        object.__setattr__(snap, "experience", exp_for_level(GrowthRate.MEDIUM_SLOW, 5))
        state = _snapshot_to_pokemon_state(snap)
        assert state.level == 5

    def test_party_mon_uses_stored_level(self):
        # Party mons keep their explicit stored level even if EXP would round down.
        snap = self._snap(experience=999999)
        assert _snapshot_to_pokemon_state(snap).level == 5

    def test_gen7_move_id_translated(self):
        # A raw ROM move id (Leafage = 633) is translated through GBA_MOVE_MAP.
        snap = self._snap(experience=999)
        object.__setattr__(snap, "moves", (633, 0, 0, 0))
        state = _snapshot_to_pokemon_state(snap)
        assert state.move_ids[0] == Move.LEAFAGE

    def test_ability_slot_one_falls_back_to_slot_zero(self):
        # Skitty's table is (NORMALIZE, NONE, NONE). A live mon whose ability bit
        # reads slot 1 must still resolve to NORMALIZE — the game falls back to
        # slot 0 rather than yielding Ability.NONE (regression test for Bug 18).
        snap = self._snap(experience=999)
        object.__setattr__(snap, "species", Species.SKITTY.value)
        object.__setattr__(snap, "alt_ability", 1)
        state = _snapshot_to_pokemon_state(snap)
        assert state.ability == Ability.NORMALIZE


class TestSnapshotsToStates:
    """Party/box snapshots become PokemonStates, with eggs and empty slots dropped."""

    def _snap(self, *, is_egg=False, has_species=True):
        snap = PokemonSnapshot.from_wire(_PARTY_LINE)
        object.__setattr__(snap, "is_egg", is_egg)
        object.__setattr__(snap, "has_species", has_species)
        return snap

    def test_keeps_normal_mon(self):
        states = _snapshots_to_states([self._snap()])
        assert len(states) == 1
        assert states[0].species == Species.BULBASAUR

    def test_skips_eggs(self):
        assert _snapshots_to_states([self._snap(is_egg=True)]) == []

    def test_skips_empty_slots(self):
        assert _snapshots_to_states([self._snap(has_species=False)]) == []

    def test_mixed_filters_correctly(self):
        snaps = [
            self._snap(),
            self._snap(is_egg=True),
            self._snap(has_species=False),
            self._snap(),
        ]
        assert len(_snapshots_to_states(snaps)) == 2

    def test_empty_input(self):
        assert _snapshots_to_states([]) == []


class TestMoveFromGbaId:
    """ROM move IDs use R&B's internal numbering; vanilla IDs match the Showdown
    Move enum but Gen 7/8 moves diverge (Leafage = ROM 633, enum 670)."""

    def test_zero_is_none(self):
        assert _move_from_gba_id(0) == Move.NONE

    def test_vanilla_move_self_maps(self):
        # Pound is ROM id 1 and enum value 1.
        assert _move_from_gba_id(1) == Move.POUND

    def test_gen7_move_translated(self):
        # Leafage: ROM id 633 -> Move.LEAFAGE (enum value 670). The regression.
        assert _move_from_gba_id(633) == Move.LEAFAGE

    def test_apostrophe_move_resolves(self):
        # "King's Shield" at ROM id 588.
        assert _move_from_gba_id(588) == Move.KING_S_SHIELD

    def test_unmapped_id_raises(self):
        # An ID with no engine equivalent fails loud rather than silently dropping.
        with pytest.raises(ValueError):
            _move_from_gba_id(999999)


class TestSaveTrainingSnapshot:
    """The 'p'-key save writes party+opponent+level_cap (BattleState pickle),
    box pokemon, a config.json, and a verbatim copy of the resources file."""

    def _battle_state(self):
        mon = _snapshot_to_pokemon_state(PokemonSnapshot.from_wire(_PARTY_LINE))
        player = SideState(team=[mon], active_indices=[0])
        opp = SideState(team=[mon, mon], active_indices=[0])
        return BattleState(sides=(player, opp), level_cap=42)

    def _resources(self, tmp_path, body="{}"):
        path = tmp_path / "CurrentResources.json"
        path.write_text(body)
        return path

    def test_writes_all_files(self, tmp_path):
        folder = tmp_path / "snap"
        box = [_snapshot_to_pokemon_state(PokemonSnapshot.from_wire(_PARTY_LINE))]
        _save_training_snapshot(
            folder, self._battle_state(), box,
            opponent_index=7, level_cap=42,
            resources_path=self._resources(tmp_path),
        )
        assert (folder / "battle_state.pkl").exists()
        assert (folder / "box.pkl").exists()
        assert (folder / "config.json").exists()
        assert (folder / "CurrentResources.json").exists()

    def test_config_contents(self, tmp_path):
        folder = tmp_path / "snap"
        _save_training_snapshot(
            folder, self._battle_state(), [],
            opponent_index=7, level_cap=42,
            resources_path=self._resources(tmp_path),
        )
        cfg = json.loads((folder / "config.json").read_text())
        assert cfg == {"opponent_index": 7, "level_cap": 42}

    def test_resources_copied_verbatim(self, tmp_path):
        original = '{"items": {"Oran Berry": 3}}'
        folder = tmp_path / "snap"
        _save_training_snapshot(
            folder, self._battle_state(), [],
            opponent_index=0, level_cap=10,
            resources_path=self._resources(tmp_path, original),
        )
        assert (folder / "CurrentResources.json").read_text() == original

    def test_battle_state_roundtrips(self, tmp_path):
        folder = tmp_path / "snap"
        _save_training_snapshot(
            folder, self._battle_state(), [],
            opponent_index=0, level_cap=42,
            resources_path=self._resources(tmp_path),
        )
        with (folder / "battle_state.pkl").open("rb") as f:
            loaded = pickle.load(f)
        assert loaded.level_cap == 42
        assert len(loaded.sides[0].team) == 1  # player party
        assert len(loaded.sides[1].team) == 2  # opponent team

    def test_box_roundtrips(self, tmp_path):
        folder = tmp_path / "snap"
        box = [_snapshot_to_pokemon_state(PokemonSnapshot.from_wire(_PARTY_LINE))]
        _save_training_snapshot(
            folder, self._battle_state(), box,
            opponent_index=0, level_cap=42,
            resources_path=self._resources(tmp_path),
        )
        with (folder / "box.pkl").open("rb") as f:
            loaded = pickle.load(f)
        assert len(loaded) == 1
        assert loaded[0].species == Species.BULBASAUR

    def test_missing_resources_raises(self, tmp_path):
        # Fail loud: a missing resources file is an error, not a silent skip.
        folder = tmp_path / "snap"
        with pytest.raises(FileNotFoundError):
            _save_training_snapshot(
                folder, self._battle_state(), [],
                opponent_index=0, level_cap=42,
                resources_path=tmp_path / "does_not_exist.json",
            )


_active_opp_name = play_module._active_opp_name


def _make_opp_side(active_indices, team_names):
    """Build a SimpleNamespace opp_side from active_indices and a list of species names."""
    team = [SimpleNamespace(species=SimpleNamespace(name=n)) for n in team_names]
    return SimpleNamespace(active_indices=active_indices, team=team)


class TestActiveOppName:
    """_active_opp_name resolves the active opponent's species name or raises on desync.

    Desync = active_indices is non-empty but the slot index exceeds team length.
    Empty active_indices is a legitimate pre-battle state; default slot 0 is used."""

    def test_valid_slot_returns_name(self):
        opp_side = _make_opp_side([0], ["Pidgey"])
        assert _active_opp_name(opp_side) == "Pidgey"

    def test_valid_slot_nonzero_returns_correct_name(self):
        opp_side = _make_opp_side([1], ["Pidgey", "Rattata"])
        assert _active_opp_name(opp_side) == "Rattata"

    def test_desync_raises_with_index_and_length(self):
        # active_indices=[3] but team only has 1 mon — genuine desync.
        opp_side = _make_opp_side([3], ["Pidgey"])
        with pytest.raises(RuntimeError) as exc_info:
            _active_opp_name(opp_side)
        msg = str(exc_info.value)
        assert "3" in msg
        assert "1" in msg  # team length

    def test_empty_active_indices_uses_slot_zero(self):
        # Pre-battle / battle-not-started: active_indices is empty, default to slot 0.
        opp_side = _make_opp_side([], ["Pidgey"])
        assert _active_opp_name(opp_side) == "Pidgey"

    def test_empty_active_indices_empty_team_returns_empty_string(self):
        # No active slot and no team: legitimate "not yet in battle" state.
        opp_side = _make_opp_side([], [])
        assert _active_opp_name(opp_side) == ""
