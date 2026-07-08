# Tests for MGBASocketClient using an in-process mock TCP server (no real mGBA needed).
import socket
import threading

import pytest

from liveplay.emulator import MGBASocketClient, MGBAConnectionError

END = b"<|END|>"
SUCCESS = b"<|SUCCESS|><|END|>"


def _make_server(responses: list[bytes]) -> tuple[str, int, threading.Thread]:
    """Start a one-shot TCP server that replies with `responses` in order, then closes."""

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    host, port = server.getsockname()

    def serve():
        conn, _ = server.accept()
        server.close()
        with conn:
            # Read all incoming data (we don't validate it in most tests)
            buf = bytearray()
            while END not in buf:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk
            for resp in responses:
                conn.sendall(resp)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return host, port, thread


def _make_capturing_server(received: list[bytes], responses: list[bytes]) -> tuple[str, int, threading.Thread]:
    """Like _make_server but records what the client sent into `received`."""

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    host, port = server.getsockname()

    def serve():
        conn, _ = server.accept()
        server.close()
        with conn:
            buf = bytearray()
            while END not in buf:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk
            received.append(bytes(buf))
            for resp in responses:
                conn.sendall(resp)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return host, port, thread


def _client(host: str, port: int) -> MGBASocketClient:
    client = MGBASocketClient(host=host, port=port)
    client.connect()
    return client


# ---------------------------------------------------------------------------
# Happy-path command tests
# ---------------------------------------------------------------------------

def test_screenshot_sends_correct_command():
    received: list[bytes] = []
    host, port, _ = _make_capturing_server(received, [SUCCESS])
    client = _client(host, port)
    client.screenshot("/tmp/foo.png")
    client.close()
    assert received[0] == b"screenshot /tmp/foo.png<|END|>"


def test_add_key_sends_correct_command():
    received: list[bytes] = []
    host, port, _ = _make_capturing_server(received, [SUCCESS])
    client = _client(host, port)
    client.add_key("A")
    client.close()
    assert received[0] == b"addKey A<|END|>"


def test_clear_key_sends_correct_command():
    received: list[bytes] = []
    host, port, _ = _make_capturing_server(received, [SUCCESS])
    client = _client(host, port)
    client.clear_key("A")
    client.close()
    assert received[0] == b"clearKey A<|END|>"


def test_tap_sends_correct_command():
    received: list[bytes] = []
    host, port, _ = _make_capturing_server(received, [SUCCESS])
    client = _client(host, port)
    client.tap("B")
    client.close()
    assert received[0] == b"tap B<|END|>"


def test_run_frames_sends_correct_command():
    received: list[bytes] = []
    host, port, _ = _make_capturing_server(received, [SUCCESS])
    client = _client(host, port)
    client.run_frames(5)
    client.close()
    assert received[0] == b"runFrames 5<|END|>"


# ---------------------------------------------------------------------------
# Error-handling tests
# ---------------------------------------------------------------------------

def test_error_response_raises_with_message():
    host, port, _ = _make_server([b"<|ERROR|>bad arg<|END|>"])
    client = _client(host, port)
    with pytest.raises(MGBAConnectionError, match="bad arg"):
        client.screenshot("/tmp/x.png")
    client.close()


def test_server_closes_socket_raises_connection_error():
    """Server closes without sending <|END|>."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    host, port = server.getsockname()

    def serve():
        conn, _ = server.accept()
        server.close()
        conn.close()  # close immediately, no response

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    client = _client(host, port)
    with pytest.raises(MGBAConnectionError):
        client.screenshot("/tmp/x.png")
    client.close()


def test_send_on_closed_socket_raises_connection_error():
    host, port, _ = _make_server([SUCCESS])
    client = _client(host, port)
    client.close()
    with pytest.raises(MGBAConnectionError):
        client.screenshot("/tmp/x.png")


def test_not_connected_raises_for_send_data():
    """_send_data raises MGBAConnectionError when not connected (no-op client)."""
    client = MGBASocketClient()
    with pytest.raises(MGBAConnectionError, match="not connected"):
        client.read_party()


class _RaisingSendallSocket:
    """Minimal socket stand-in whose sendall always raises OSError."""

    def sendall(self, data):
        raise OSError("injected error")


def test_oserror_during_send_maps_to_connection_error_for_send():
    """OSError during sendall in _send path raises MGBAConnectionError with 'send failed'."""
    client = MGBASocketClient()
    client._sock = _RaisingSendallSocket()
    with pytest.raises(MGBAConnectionError, match="send failed"):
        client.screenshot("/tmp/x.png")


def test_oserror_during_send_maps_to_connection_error_for_send_data():
    """OSError during sendall in _send_data path raises MGBAConnectionError with 'send failed'."""
    client = MGBASocketClient()
    client._sock = _RaisingSendallSocket()
    with pytest.raises(MGBAConnectionError, match="send failed"):
        client.read_party()


def test_send_data_returns_payload_on_success():
    """_send_data strips <|SUCCESS|> and returns the payload string."""
    payload = b"<|SUCCESS|>some data<|END|>"
    host, port, _ = _make_server([payload])
    client = _client(host, port)
    result = client._send_data("readparty")
    client.close()
    assert result == "some data"


def test_send_data_raises_on_error_prefix():
    """_send_data raises MGBAConnectionError with the error message from <|ERROR|> response."""
    host, port, _ = _make_server([b"<|ERROR|>bad slot<|END|>"])
    client = _client(host, port)
    with pytest.raises(MGBAConnectionError, match="bad slot"):
        client._send_data("readbox 0 0")
    client.close()


def test_send_data_raises_on_unexpected_prefix():
    """_send_data raises MGBAConnectionError on a response that is neither SUCCESS nor ERROR."""
    host, port, _ = _make_server([b"<|EVENT|>something<|END|>"])
    client = _client(host, port)
    with pytest.raises(MGBAConnectionError, match="unexpected response"):
        client._send_data("readparty")
    client.close()


def test_multi_chunk_response_reassembled():
    """Mock server sends response in two writes split inside <|END|>."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    host, port = server.getsockname()

    def serve():
        conn, _ = server.accept()
        server.close()
        with conn:
            buf = bytearray()
            while END not in buf:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk
            # Split "<|SUCCESS|><|END|>" between "<|" and "END|>"
            full = b"<|SUCCESS|><|END|>"
            conn.sendall(full[:10])   # "<|SUCCESS|"
            conn.sendall(full[10:])   # "><|END|>"

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    client = _client(host, port)
    client.screenshot("/tmp/x.png")  # must not raise
    client.close()


# ---------------------------------------------------------------------------
# recv_event with event_timeout set at connect time
# ---------------------------------------------------------------------------

def _make_event_server(event_payload: bytes | None, delay: float = 0.0) -> tuple[str, int, threading.Thread]:
    """Server that waits `delay` seconds then sends an event (or closes without sending if None)."""
    import time
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    host, port = server.getsockname()

    def serve():
        conn, _ = server.accept()
        server.close()
        with conn:
            time.sleep(delay)
            if event_payload is not None:
                conn.sendall(event_payload)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    return host, port, thread


def test_recv_event_timeout_returns_none():
    """connect(event_timeout=0.05) with no event: recv_event() returns None."""
    host, port, _ = _make_event_server(event_payload=None, delay=5.0)
    client = MGBASocketClient(host=host, port=port)
    client.connect(event_timeout=0.05)
    result = client.recv_event()
    client.close()
    assert result is None


def test_recv_event_with_event_timeout_returns_payload():
    """connect(event_timeout=0.05) and server sends event immediately: recv_event() returns payload."""
    payload = b"<|EVENT|>toggle_capture<|END|>"
    host, port, _ = _make_event_server(event_payload=payload)
    client = MGBASocketClient(host=host, port=port)
    client.connect(event_timeout=0.05)
    result = client.recv_event()
    client.close()
    assert result == "toggle_capture"


def test_recv_event_no_timeout_with_event():
    """connect() with no timeout and server sends event: recv_event() still returns payload."""
    payload = b"<|EVENT|>init_battle<|END|>"
    host, port, _ = _make_event_server(event_payload=payload)
    client = MGBASocketClient(host=host, port=port)
    client.connect()
    result = client.recv_event()
    client.close()
    assert result == "init_battle"
