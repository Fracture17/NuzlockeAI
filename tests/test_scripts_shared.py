# Tests for SCRIPTS/_shared.py — covers _Tee (pure, unit-testable) and import smoke tests
# for OS-side-effecting helpers (_kill_existing_mgba).
import io
import sys
from pathlib import Path

# Ensure SCRIPTS/ is importable as a package sibling of the project root.
sys.path.insert(0, str(Path(__file__).parent.parent / "SCRIPTS"))

from _shared import _Tee, _kill_existing_mgba  # noqa: E402


class TestTee:
    def test_write_fans_out_to_both_streams(self):
        a, b = io.StringIO(), io.StringIO()
        tee = _Tee(a, b)
        tee.write("hello")
        assert a.getvalue() == "hello"
        assert b.getvalue() == "hello"

    def test_write_returns_length(self):
        a, b = io.StringIO(), io.StringIO()
        tee = _Tee(a, b)
        result = tee.write("abc")
        assert result == 3

    def test_write_multiple_calls_accumulate(self):
        a, b = io.StringIO(), io.StringIO()
        tee = _Tee(a, b)
        tee.write("foo")
        tee.write("bar")
        assert a.getvalue() == "foobar"
        assert b.getvalue() == "foobar"

    def test_flush_propagates_to_both_streams(self):
        flushed = []

        class TrackingStream:
            def write(self, data):
                pass
            def flush(self):
                flushed.append(id(self))

        s1, s2 = TrackingStream(), TrackingStream()
        tee = _Tee(s1, s2)
        tee.flush()
        assert id(s1) in flushed
        assert id(s2) in flushed

    def test_isatty_returns_false(self):
        tee = _Tee(io.StringIO(), io.StringIO())
        assert tee.isatty() is False

    def test_three_streams(self):
        a, b, c = io.StringIO(), io.StringIO(), io.StringIO()
        tee = _Tee(a, b, c)
        tee.write("xyz")
        assert a.getvalue() == b.getvalue() == c.getvalue() == "xyz"


class TestSmokeImports:
    def test_kill_existing_mgba_is_callable(self):
        assert callable(_kill_existing_mgba)
