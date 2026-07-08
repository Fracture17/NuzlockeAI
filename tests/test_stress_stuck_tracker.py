# Tests for _StuckTracker in SCRIPTS/stress_test.py.
# stress_test imports play.py, which has heavy vision/OCR imports; stub them first.
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

_STUB_MODULES = ("liveplay.vision.ocr", "liveplay.vision.capture", "liveplay.vision.hp_bar")
for mod in _STUB_MODULES:
    sys.modules.setdefault(mod, MagicMock())


@pytest.fixture(autouse=True, scope="module")
def _restore_stubbed_modules():
    yield
    for mod in _STUB_MODULES:
        sys.modules.pop(mod, None)


sys.path.insert(0, str(Path(__file__).parent.parent / "SCRIPTS"))
import stress_test as stress_module

_StuckTracker = stress_module._StuckTracker


class TestStuckTracker:
    """The capture loop is single-threaded: a slow greedy search blocks captures,
    so its compute time must not count toward the stuck threshold. note_decision
    resets the clock after each decision (regression: a >10s search on a forced
    switch tripped a false STUCK on the next blank-screen capture)."""

    def test_changing_text_never_stuck(self):
        t = _StuckTracker(threshold=10.0, now=0.0)
        assert t.observe(1.0, "Foe used Tackle!") is False
        assert t.observe(2.0, "It's super effective!") is False

    def test_same_text_past_threshold_is_stuck(self):
        t = _StuckTracker(threshold=10.0, now=0.0)
        assert t.observe(1.0, "") is False        # first sight of this text
        assert t.observe(5.0, "") is False         # 4s < 10s
        assert t.observe(12.0, "") is True         # 11s > 10s → stuck

    def test_same_text_at_threshold_not_yet_stuck(self):
        # Use distinct text so the first observe sets a clean baseline (blank ""
        # would collide with the tracker's initial last_text).
        t = _StuckTracker(threshold=10.0, now=0.0)
        assert t.observe(1.0, "Wait...") is False   # baseline at t=1
        assert t.observe(11.0, "Wait...") is False  # exactly 10s, not strictly past

    def test_slow_decision_does_not_trip_stuck(self):
        # Blank screen seen at t=1. A greedy search then runs 12s (longer than the
        # threshold). note_decision resets the clock so the next blank capture at
        # t=13 is NOT flagged stuck — the search, not the screen, consumed the time.
        t = _StuckTracker(threshold=10.0, now=0.0)
        assert t.observe(1.0, "") is False
        t.note_decision(13.0)                       # search finished at t=13
        assert t.observe(13.1, "") is False         # would be stuck without the reset

    def test_genuine_hang_after_decision_still_trips(self):
        # After a decision reset, a screen that then stays frozen past the
        # threshold must still trip — the reset gives a fresh window, not immunity.
        t = _StuckTracker(threshold=10.0, now=0.0)
        t.note_decision(13.0)
        assert t.observe(14.0, "") is False
        assert t.observe(25.0, "") is True          # 11s of unchanged text post-reset
