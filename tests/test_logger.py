# Tests for src/logger.py: noop behavior, BattleLogger formatting, and format_state.
import pytest
import liveplay.logger as logger_module
from liveplay.logger import log, LogEvent, BattleLogger, format_state
from liveplay.data.species import Species
from liveplay.data.moves import Move
from liveplay.data.natures import Nature
from liveplay.data.status import Status
from liveplay.state.pokemon import PokemonState, GenderEnum
from liveplay.state.side import SideState
from liveplay.state.battle import BattleState, WeatherEnum


def _make_pokemon(species, hp=None, status=Status.NONE):
    p = PokemonState(
        species=species,
        nature=Nature.HARDY,
        ivs=(31,) * 6,
        gender=GenderEnum.MALE,
        move_ids=(Move.TACKLE, Move.NONE, Move.NONE, Move.NONE),
        move_pp=(35, 0, 0, 0),
        status=status,
    )
    if hp is not None:
        p = p._replace(hp=hp)
    return p


def _make_battle(weather=WeatherEnum.NONE, turn_number=1):
    p0 = _make_pokemon(Species.PIKACHU)
    p1 = _make_pokemon(Species.CLEFAIRY)
    side0 = SideState(team=[p0], active_indices=[0])
    side1 = SideState(team=[p1], active_indices=[0])
    return BattleState(sides=(side0, side1), weather=weather, turn_number=turn_number)


class TestLogNoop:

    def test_log_noop_when_none(self):
        logger_module.logger = None
        # Must not raise and must produce no output
        log(LogEvent.TURN_START, turn=1)

    def test_log_calls_handle_when_set(self):
        calls = []

        class RecordingLogger(BattleLogger):
            def handle(self, event, **kwargs):
                calls.append((event, kwargs))

        logger_module.logger = RecordingLogger()
        try:
            p = _make_pokemon(Species.PIKACHU)
            log(LogEvent.FAINT, pokemon=p.species)
            assert len(calls) == 1
            assert calls[0][0] == LogEvent.FAINT
        finally:
            logger_module.logger = None


class TestBattleLoggerFormat:

    def test_format_state_contains_species_names(self):
        state = _make_battle()
        output = format_state(state)
        assert "pikachu" in output.lower()
        assert "clefairy" in output.lower()

    def test_format_state_shows_hp(self):
        state = _make_battle()
        output = format_state(state)
        # Pikachu's max HP at level 50, 31 IVs, Hardy: floor((2*35+31)*50/100)+50+10 = 95
        p0 = state.sides[0].team[0]
        assert str(p0.max_hp) in output

    def test_format_state_turn_number(self):
        state = _make_battle(turn_number=7)
        output = format_state(state)
        assert "7" in output

    def test_format_state_shows_weather(self):
        state = _make_battle(weather=WeatherEnum.RAINY)
        output = format_state(state)
        assert "rain" in output.lower() or "rainy" in output.lower()

    def test_format_state_no_weather_blank(self):
        state = _make_battle(weather=WeatherEnum.NONE)
        output = format_state(state)
        # Must not display "None" as a weather label
        assert "weather: none" not in output.lower()
