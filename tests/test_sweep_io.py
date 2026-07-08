# Tests for liveplay/sweep_io.py — lossless JSON round-trip codec for sweep inputs/outputs.
# TRIM: test_round_tripped_inputs_produce_identical_engine_output and
# test_output_candidates_round_trip dropped (call run_candidate_sweep stub).
# Also dropped: the diff_harness import (not carried to new repo).
import json
import dataclasses

import pytest

from liveplay.candidate import Candidate
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status
from liveplay.state.pokemon import Volatile, VolatileEffect
from liveplay.state.battle import WeatherEnum
from liveplay.state.side import SideCondition
from tests.state_builders import make_battle, make_mon, odelta


def _make_sweep_input():
    """Charizard Tackle vs Bulbasaur — reuses engine_select test construction."""
    from liveplay.battle_types import ActionGroup, MatchResult
    charizard = make_mon(Species.CHARIZARD, moves=(Move.TACKLE,))
    bulbasaur = make_mon(Species.BULBASAUR, moves=(Move.SPLASH,))
    state = make_battle(charizard, bulbasaur)
    initial_candidate = Candidate(state=state)

    primary = MatchResult(
        string_id="STRINGID_USEDMOVE",
        id_value=0,
        constant_name="sText_AttackerUsedMove",
        var_values=["Charizard", "Tackle"],
        score=0,
        matched_text="",
        slot_labels=[],
        side_hint=0,
    )
    messages = [primary]
    hp_deltas = [odelta(bulbasaur.species, (48, 38), max_hp=bulbasaur.max_hp)]
    return messages, hp_deltas, [initial_candidate], None


# ---------------------------------------------------------------------------
# Round-trip equality: input components only (no engine call)
# ---------------------------------------------------------------------------

class TestRoundTripEquality:
    def test_input_components_equal_after_round_trip(self, tmp_path):
        from liveplay.sweep_io import dump_sweep_input, load_sweep_input
        messages, hp_deltas, initial_candidates, action_groups = _make_sweep_input()

        path = tmp_path / "sweep.json"
        dump_sweep_input(messages, hp_deltas, initial_candidates, action_groups, path)

        m2, h2, c2, ag2 = load_sweep_input(path)

        assert messages == m2
        assert hp_deltas == h2
        assert initial_candidates == c2
        assert action_groups == ag2


# ---------------------------------------------------------------------------
# Tuple and enum fidelity
# ---------------------------------------------------------------------------

class TestTupleEnumFidelity:
    def test_tuple_field_stays_tuple(self, tmp_path):
        """ivs (tuple[int, ...]) must remain a tuple, not become a list, after round-trip."""
        from liveplay.sweep_io import dump_sweep_input, load_sweep_input
        messages, hp_deltas, initial_candidates, action_groups = _make_sweep_input()

        path = tmp_path / "sweep.json"
        dump_sweep_input(messages, hp_deltas, initial_candidates, action_groups, path)
        _, _, c2, _ = load_sweep_input(path)

        poke = c2[0].state.sides[0].team[0]
        assert isinstance(poke.ivs, tuple), f"ivs should be tuple, got {type(poke.ivs)}"
        assert isinstance(poke.move_ids, tuple), f"move_ids should be tuple, got {type(poke.move_ids)}"
        assert isinstance(poke.stat_stages, tuple), f"stat_stages should be tuple, got {type(poke.stat_stages)}"

    def test_intflag_volatile_roundtrip(self, tmp_path):
        """Volatile IntFlag values must reconstruct to the exact members."""
        from liveplay.sweep_io import to_jsonable, from_jsonable
        v = Volatile.CONFUSED | Volatile.FLINCHED
        encoded = to_jsonable(v)
        decoded = from_jsonable(encoded)
        # IntFlag: decoded must be == and same type
        assert decoded == v
        assert type(decoded) is type(v)

    def test_intenum_species_roundtrip(self):
        """Species IntEnum must reconstruct to the exact member."""
        from liveplay.sweep_io import to_jsonable, from_jsonable
        s = Species.CHARIZARD
        encoded = to_jsonable(s)
        decoded = from_jsonable(encoded)
        assert decoded is s or decoded == s
        assert type(decoded) is Species

    def test_weather_enum_roundtrip(self):
        """WeatherEnum must survive codec without becoming a plain int."""
        from liveplay.sweep_io import to_jsonable, from_jsonable
        w = WeatherEnum.RAINY
        decoded = from_jsonable(to_jsonable(w))
        assert decoded == w
        assert type(decoded) is WeatherEnum

    def test_prev_turn_order_tuple_of_ints(self, tmp_path):
        """BattleState.prev_turn_order (tuple[int, ...]) must remain a tuple."""
        from liveplay.sweep_io import dump_sweep_input, load_sweep_input
        messages, hp_deltas, initial_candidates, action_groups = _make_sweep_input()
        # Patch in a non-empty prev_turn_order
        state = initial_candidates[0].state
        new_state = dataclasses.replace(state, prev_turn_order=(0, 1))
        initial_candidates = [Candidate(state=new_state)]

        path = tmp_path / "sweep.json"
        dump_sweep_input(messages, hp_deltas, initial_candidates, action_groups, path)
        _, _, c2, _ = load_sweep_input(path)

        assert isinstance(c2[0].state.prev_turn_order, tuple)
        assert c2[0].state.prev_turn_order == (0, 1)

    def test_exp_participants_frozenset(self, tmp_path):
        """exp_participants (tuple[frozenset, ...]) must reconstruct frozensets."""
        from liveplay.sweep_io import dump_sweep_input, load_sweep_input
        messages, hp_deltas, initial_candidates, action_groups = _make_sweep_input()
        state = initial_candidates[0].state
        new_state = dataclasses.replace(state, exp_participants=(frozenset({0, 1}), frozenset({2})))
        initial_candidates = [Candidate(state=new_state)]

        path = tmp_path / "sweep.json"
        dump_sweep_input(messages, hp_deltas, initial_candidates, action_groups, path)
        _, _, c2, _ = load_sweep_input(path)

        ep = c2[0].state.exp_participants
        assert isinstance(ep, tuple)
        assert all(isinstance(s, frozenset) for s in ep)
        assert ep == (frozenset({0, 1}), frozenset({2}))


# ---------------------------------------------------------------------------
# Unknown-type fail-loud
# ---------------------------------------------------------------------------

class TestFailLoud:
    def test_unhandled_type_raises(self):
        """to_jsonable must raise (not silently mangle) for an unknown object type."""
        from liveplay.sweep_io import to_jsonable

        class _Uncodeable:
            pass

        with pytest.raises((TypeError, ValueError)):
            to_jsonable(_Uncodeable())

    def test_json_file_is_human_readable(self, tmp_path):
        """The emitted file must be valid JSON (parseable by stdlib json)."""
        from liveplay.sweep_io import dump_sweep_input
        messages, hp_deltas, initial_candidates, action_groups = _make_sweep_input()

        path = tmp_path / "sweep.json"
        dump_sweep_input(messages, hp_deltas, initial_candidates, action_groups, path)

        raw = path.read_text()
        parsed = json.loads(raw)  # must not raise
        assert isinstance(parsed, dict)
