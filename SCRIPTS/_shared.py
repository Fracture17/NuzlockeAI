# Shared helpers for SCRIPTS/: _Tee (multi-stream tee) and _kill_existing_mgba (process cleanup).
# Imported by play.py, debug_sweep.py, and stress_test.py.
import time


class _Tee:
    """Write to multiple streams simultaneously."""
    def __init__(self, *streams):
        self._streams = streams

    def write(self, data: str) -> int:
        for s in self._streams:
            s.write(data)
        return len(data)

    def flush(self) -> None:
        for s in self._streams:
            s.flush()

    def isatty(self) -> bool:
        return False


def _kill_existing_mgba() -> None:
    """Kill any running mGBA instances so their socket server doesn't conflict."""
    import subprocess as _sp
    _sp.run(["pkill", "mgba-qt"], capture_output=True)
    time.sleep(0.4)
