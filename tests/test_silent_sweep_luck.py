# Port of OLD tests/test_silent_sweep_luck.py — Cindy1 regression only.
#
# Sections 1-3 (SWEEP_LUCK resolve_* internals tests) test OLD Python RNG plumbing with no
# NEW analog (the NEW plain-mode C++ path replaces it) — DROPPED BY DECISION.
# SWEEP_LUCK silent-defaults are covered by test_sweep_driver.py::TestSweepLuck.
#
# Ported: test_paralyzed_love_immobilized_emits_infatuation_not_paralysis (Cindy1 regression).
#
# Scenario: Budew is paralyzed AND infatuated. The sweep observed "immobilized by love"
# and injects ATTRACT_IMMOBILIZE=False, but does NOT inject FULL_PARALYSIS.
# Engine checks paralysis BEFORE attract; the silent default (can act, threshold=0.0)
# lets the paralysis roll pass, so the engine reaches the attract check and emits
# CANT_INFATUATION, NOT CANT_PARALYSIS.
from __future__ import annotations

from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status
from liveplay.logger import LogEvent
from liveplay.rng import RNGEvent
from liveplay.state.pokemon import Volatile
from liveplay.sweep_driver import SideOverrides, SweepConfig, run_with_capture
from tests.state_builders import (
    make_mon, make_battle, slot,
    assert_event, assert_no_event,
)


def test_paralyzed_love_immobilized_emits_infatuation_not_paralysis():
    """Cindy1 regression: paralyzed+infatuated mon with observed 'immobilized by love' must emit
    CANT_INFATUATION, not CANT_PARALYSIS.

    ATTRACT_IMMOBILIZE=False is injected (observed immobilization by love).
    FULL_PARALYSIS is NOT injected (silent default = can act, threshold=0.0 → passes).
    Engine: paralysis check → passes → attract check → CANT_INFATUATION.
    """
    budew = make_mon(Species.BUDEW, moves=(Move.ABSORB,), status=Status.PARALYSIS)
    budew = budew._replace(volatiles=budew.volatiles | Volatile.ATTRACTED)
    foe = make_mon(Species.JIGGLYPUFF, moves=(Move.SPLASH,))
    state = make_battle(budew, foe)

    # ATTRACT_IMMOBILIZE=False → attract_threshold=101.0 (immobilized by love).
    # FULL_PARALYSIS not set → SWEEP_LUCK default paralysis_threshold=0.0 (can act, silent).
    config = SweepConfig(
        side0=SideOverrides(extra_overrides={RNGEvent.ATTRACT_IMMOBILIZE: False}),
    )

    final, log = run_with_capture(state, slot(0), slot(0), config)
    assert final is not None, "run_with_capture returned None — NeedsRNG or unexpected error"

    assert_event(log, LogEvent.CANT_INFATUATION)
    assert_no_event(log, LogEvent.CANT_PARALYSIS)
