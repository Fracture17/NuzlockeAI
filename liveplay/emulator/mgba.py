"""Manages a locally-built mGBA process and its Lua socket server script."""

import os
import subprocess
import time
from pathlib import Path

from .socket_client import MGBAConnectionError, MGBASocketClient

MGBA_BIN  = str(Path.home() / ".local/bin/mgba-qt")
ROM_PATH  = os.environ.get("NUZLOCKE_ROM_PATH", "/home/Fracture/Downloads/RunNBun.gba")

_CONNECT_ATTEMPTS = 60
_CONNECT_INTERVAL = 0.5  # seconds between retries (60 × 0.5s = 30s max)


class MGBAProcess:
    """
    Launches the locally-built mgba-qt with the Lua socket server script
    (--script), then connects via TCP on localhost:8888.

    Usage:
        with MGBAProcess() as mgba:
            mgba.socket.tap("A")
    """

    def __init__(self, rom_path: str = ROM_PATH, event_timeout: float | None = None):
        self._rom_path = rom_path
        self._event_timeout = event_timeout
        self._process: subprocess.Popen | None = None
        self.socket: MGBASocketClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Launch mgba-qt with --script, then wait for the Lua server to bind."""
        script_path = str(Path(__file__).resolve().parents[2] / "SCRIPTS" / "mGBASocketServer.lua")
        env = {**os.environ, "QT_QPA_PLATFORM": "xcb"}
        self._process = subprocess.Popen(
            [MGBA_BIN, "--script", script_path, self._rom_path],
            env=env,
        )
        self._connect_socket()

    def close(self) -> None:
        """Close the socket and terminate mGBA if still running."""
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
        self._process = None

    def __enter__(self) -> "MGBAProcess":
        self.start()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _connect_socket(self) -> None:
        """Retry socket connection up to _CONNECT_ATTEMPTS times. Raises MGBAConnectionError if all fail."""
        client = MGBASocketClient()
        last_exc: MGBAConnectionError | None = None
        for _ in range(_CONNECT_ATTEMPTS):
            try:
                client.connect(event_timeout=self._event_timeout)
                self.socket = client
                return
            except MGBAConnectionError as exc:
                last_exc = exc
                time.sleep(_CONNECT_INTERVAL)
        raise MGBAConnectionError(
            f"Could not connect to mGBA Lua socket server on localhost:8888 "
            f"after {_CONNECT_ATTEMPTS} attempts."
        ) from last_exc
