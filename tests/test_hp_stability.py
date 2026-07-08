# Tests for src/hp_stability.py — StabilityBuffer, OpponentHpBuffer, PlayerHpBuffer, hp_range.
import pytest
from liveplay.hp_stability import StabilityBuffer, OpponentHpBuffer, PlayerHpBuffer, hp_range


class TestStabilityBuffer:
    def test_first_reading_not_stable(self):
        buf = StabilityBuffer(required=3)
        assert buf.update(10) is False

    def test_second_identical_not_stable(self):
        buf = StabilityBuffer(required=3)
        buf.update(10)
        assert buf.update(10) is False

    def test_third_identical_is_stable(self):
        buf = StabilityBuffer(required=3)
        buf.update(10)
        buf.update(10)
        assert buf.update(10) is True
        assert buf.confirmed == 10

    def test_fourth_identical_not_newly_stable(self):
        buf = StabilityBuffer(required=3)
        buf.update(10)
        buf.update(10)
        buf.update(10)
        assert buf.update(10) is False

    def test_different_value_resets_streak(self):
        buf = StabilityBuffer(required=3)
        buf.update(10)
        buf.update(10)
        buf.update(10)  # confirmed == 10
        buf.update(20)  # streak resets
        buf.update(20)
        assert buf.update(20) is True  # re-confirmed with new value
        assert buf.confirmed == 20

    def test_none_breaks_streak(self):
        buf = StabilityBuffer(required=3)
        buf.update(10)
        buf.update(10)
        buf.update(None)  # breaks streak
        buf.update(10)
        assert buf.update(10) is False  # only 2 after the None; not yet stable

    def test_none_then_three_stable(self):
        buf = StabilityBuffer(required=3)
        buf.update(10)
        buf.update(10)
        buf.update(None)
        buf.update(10)
        buf.update(10)
        assert buf.update(10) is True

    def test_reset_clears_all_state(self):
        buf = StabilityBuffer(required=3)
        buf.update(10)
        buf.update(10)
        buf.update(10)
        buf.reset()
        assert buf.confirmed is None
        # After reset, need 3 more identicals
        buf.update(10)
        buf.update(10)
        assert buf.update(10) is True

    def test_confirmed_none_before_any_stable(self):
        buf = StabilityBuffer(required=3)
        assert buf.confirmed is None
        buf.update(5)
        assert buf.confirmed is None


class TestHpRange:
    def test_k0_returns_0_0(self):
        assert hp_range(0, 200) == (0, 0)

    def test_k24_within_bounds(self):
        hp_min, hp_max = hp_range(24, 200)
        assert 0 <= hp_min <= hp_max <= 200

    def test_k24_consistent_with_formula(self):
        import math
        hp_min, hp_max = hp_range(24, 200)
        assert hp_min == math.ceil(24 * 200 / 48)
        assert hp_max == min(math.ceil(25 * 200 / 48) - 1, 200)

    def test_k48_max_equals_max_hp(self):
        _, hp_max = hp_range(48, 200)
        assert hp_max == 200

    def test_k1_hp_min_at_least_1(self):
        hp_min, _ = hp_range(1, 100)
        assert hp_min >= 1


class TestSubclasses:
    def test_opponent_hp_buffer_is_stability_buffer(self):
        buf = OpponentHpBuffer()
        assert isinstance(buf, StabilityBuffer)

    def test_player_hp_buffer_is_stability_buffer(self):
        buf = PlayerHpBuffer()
        assert isinstance(buf, StabilityBuffer)

    def test_opponent_hp_buffer_required_2(self):
        buf = OpponentHpBuffer()
        assert buf._required == 2

    def test_player_hp_buffer_required_2(self):
        buf = PlayerHpBuffer()
        assert buf._required == 2


class TestOpponentHpTracking:
    """Tests for the name-keyed HP tracking logic used in _do_capture."""

    def _process_readings(self, sequence: list[tuple]) -> tuple[dict, dict]:
        """Simulate _do_capture's HP tracking logic for a list of (opp_name, k) pairs."""
        opponent_hp_bufs: dict = {}
        opp_k_logs: dict = {}
        for opp_name_raw, k in sequence:
            opp_name = (opp_name_raw or "").lower()
            if not opp_name:
                continue  # skip None/empty names (fix under test)
            buf = opponent_hp_bufs.setdefault(opp_name, OpponentHpBuffer())
            if buf.update(k):
                name_log = opp_k_logs.setdefault(opp_name, [])
                if not name_log or name_log[-1] != buf.confirmed:
                    name_log.append(buf.confirmed)
        return opponent_hp_bufs, opp_k_logs

    def test_null_opponent_name_does_not_create_buffer(self):
        bufs, logs = self._process_readings([(None, None), (None, None)])
        assert not bufs
        assert not logs

    def test_real_opponent_tracked_correctly(self):
        _, logs = self._process_readings([
            ("Poochyena", 33), ("Poochyena", 33),   # confirmed 33
            ("Poochyena", 24), ("Poochyena", 24),   # confirmed 24
        ])
        assert logs == {"poochyena": [33, 24]}

    def test_null_frames_before_real_do_not_shadow_real_log(self):
        """Null frames (battle intro) must not insert a key ahead of the real opponent."""
        _, logs = self._process_readings([
            (None, None), (None, None),               # intro transition — must be skipped
            ("Poochyena", 33), ("Poochyena", 33),     # confirmed 33
            (None, None), (None, None),               # mid-battle transition
            ("Poochyena", 24), ("Poochyena", 24),     # confirmed 24
        ])
        assert list(logs.keys()) == ["poochyena"], "Real opponent must be first (and only) key"
        assert logs["poochyena"] == [33, 24]

    def test_null_frames_between_damage_preserve_delta(self):
        """None readings between the initial confirmation and post-damage confirmation
        must not prevent the delta from being captured."""
        _, logs = self._process_readings([
            ("Poochyena", 33), ("Poochyena", 33),  # confirmed 33
            (None, None), (None, None), (None, None), (None, None),
            ("Poochyena", 32),                      # first post-damage reading (not confirmed)
            ("Poochyena", 24), ("Poochyena", 24),  # confirmed 24
        ])
        assert logs["poochyena"] == [33, 24]
