# Tests for the nuzlocke_engine_cpp pybind11 stub extension (C0.2).
# Skips entire module if the extension is not yet built/installed.
import pytest

nuzlocke_engine_cpp = pytest.importorskip("nuzlocke_engine_cpp")


def test_is_stub():
    assert nuzlocke_engine_cpp.is_stub() is False


def test_version():
    v = nuzlocke_engine_cpp.version()
    assert isinstance(v, str)
    assert len(v) > 0


def test_run_candidate_sweep_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        nuzlocke_engine_cpp.run_candidate_sweep_cpp()
