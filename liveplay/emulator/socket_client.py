# TCP client for the mGBA Lua socket server. Sends UTF-8 commands and reads <|END|>-delimited responses.
import socket
from liveplay.emulator.pokemon_snapshot import PokemonSnapshot

_END = "<|END|>"
_END_BYTES = b"<|END|>"
_SUCCESS_PREFIX = "<|SUCCESS|>"
_ERROR_PREFIX = "<|ERROR|>"
_EVENT_PREFIX = "<|EVENT|>"
_RECV_SIZE = 4096


class MGBAConnectionError(Exception):
    """Raised when the mGBA socket connection fails or returns an error response."""


class MGBASocketClient:
    """Synchronous TCP client for the mGBA Lua socket server."""

    def __init__(self, host: str = "localhost", port: int = 8888) -> None:
        self._host = host
        self._port = port
        self._sock: socket.socket | None = None

    def connect(self, event_timeout: float | None = None) -> None:
        """Open the TCP connection. Raises MGBAConnectionError on failure.

        event_timeout sets the socket timeout for recv_event() calls (applied once at connect time).
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self._host, self._port))
            self._sock = sock
        except OSError as exc:
            raise MGBAConnectionError(f"connect failed: {exc}") from exc
        if event_timeout is not None:
            self._sock.settimeout(event_timeout)

    def close(self) -> None:
        """Close the TCP connection if open."""
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def __enter__(self) -> "MGBASocketClient":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public commands
    # ------------------------------------------------------------------

    def screenshot(self, path: str) -> None:
        self._send(f"screenshot {path}")

    def add_key(self, key: str) -> None:
        self._send(f"addKey {key}")

    def clear_key(self, key: str) -> None:
        self._send(f"clearKey {key}")

    def tap(self, key: str) -> None:
        self._send(f"tap {key}")

    def run_frames(self, n: int) -> None:
        self._send(f"runFrames {n}")

    def load_state(self, path: str) -> None:
        """Load a save state from a file path (e.g. /path/to/game.ss2)."""
        self._send(f"loadstate {path}")

    def save_state(self, path: str) -> None:
        self._send(f"savestate {path}")

    def recv_event(self) -> str | None:
        """Block until Lua pushes an unsolicited event, or until the timeout set at connect() expires.

        Returns the payload string (after the <|EVENT|> prefix) on success,
        or None if the timeout elapsed with no data.
        Raises MGBAConnectionError on connection errors or unexpected messages.
        """
        if self._sock is None:
            raise MGBAConnectionError("not connected")
        try:
            raw = self._recv_until_end()
        except socket.timeout:
            return None
        if raw.startswith(_EVENT_PREFIX):
            return raw[len(_EVENT_PREFIX):]
        raise MGBAConnectionError(f"unexpected message (expected event): {raw!r}")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _raw_send(self, cmd: str) -> str:
        """Guard connection, build wire bytes, sendall, recv until end, return raw response."""
        if self._sock is None:
            raise MGBAConnectionError("not connected")
        wire = (cmd + _END).encode()
        try:
            self._sock.sendall(wire)
        except OSError as exc:
            raise MGBAConnectionError(f"send failed: {exc}") from exc
        return self._recv_until_end()

    def _send(self, cmd: str) -> None:
        """Send command and read response. Raises MGBAConnectionError on error or bad response."""
        response = self._raw_send(cmd)
        self._check_response(response)

    def _recv_until_end(self) -> str:
        """Accumulate bytes until <|END|> is found, then return the decoded message.

        Re-raises socket.timeout as-is so callers can distinguish "no data yet"
        from a genuine connection failure.
        """
        buf = bytearray()
        while True:
            try:
                chunk = self._sock.recv(_RECV_SIZE)
            except socket.timeout:
                raise
            except OSError as exc:
                raise MGBAConnectionError(f"recv failed: {exc}") from exc
            if not chunk:
                raise MGBAConnectionError("connection closed")
            buf += chunk
            if _END_BYTES in buf:
                end_pos = buf.index(_END_BYTES)
                return buf[:end_pos].decode()

    def _send_data(self, cmd: str) -> str:
        """Send command and return payload after <|SUCCESS|>. Raises MGBAConnectionError on failure."""
        response = self._raw_send(cmd)
        if response.startswith(_ERROR_PREFIX):
            raise MGBAConnectionError(response[len(_ERROR_PREFIX):])
        if not response.startswith(_SUCCESS_PREFIX):
            raise MGBAConnectionError(f"unexpected response: {response!r}")
        return response[len(_SUCCESS_PREFIX):]

    def _parse_mons(self, data: str) -> list[PokemonSnapshot]:
        if not data:
            return []
        return [PokemonSnapshot.from_wire(line) for line in data.split("\n") if line]

    # ------------------------------------------------------------------
    # Party / box reads
    # ------------------------------------------------------------------

    def read_party(self) -> list[PokemonSnapshot]:
        data = self._send_data("readparty")
        return self._parse_mons(data)

    def read_box_mon(self, box: int, slot: int) -> PokemonSnapshot | None:
        data = self._send_data(f"readbox {box} {slot}")
        if not data:
            return None
        return PokemonSnapshot.from_wire(data)

    def read_all_boxes(self) -> list[PokemonSnapshot]:
        data = self._send_data("readallboxes")
        return self._parse_mons(data)

    def _check_response(self, response: str) -> None:
        """Parse response; raise MGBAConnectionError if it signals an error."""
        if response.startswith(_ERROR_PREFIX):
            message = response[len(_ERROR_PREFIX):]
            raise MGBAConnectionError(message)
        # SUCCESS prefix is stripped; return value (if any) is ignored for now
