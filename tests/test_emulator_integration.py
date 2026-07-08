# Integration tests for MGBASocketClient against a live mGBA Lua socket server.
# Skipped in the normal fast suite (requires mGBA running on localhost:8888).
import pytest
from pathlib import Path

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def mgba_client():
    """Connect to a live mGBA Lua socket server on localhost:8888. Skip if unavailable."""
    from liveplay.emulator.socket_client import MGBASocketClient, MGBAConnectionError
    client = MGBASocketClient()
    try:
        client.connect()
    except MGBAConnectionError:
        pytest.skip("mGBA socket server not reachable on localhost:8888")
    yield client
    client.close()


def test_connect(mgba_client):
    assert mgba_client is not None


def test_tap(mgba_client):
    import time
    t0 = time.perf_counter()
    mgba_client.tap("A")
    assert time.perf_counter() - t0 < 1.0


def test_screenshot(mgba_client, tmp_path):
    from PIL import Image
    path = str(tmp_path / "frame.png")
    mgba_client.screenshot(path)
    p = Path(path)
    assert p.exists()
    assert p.stat().st_size > 0
    img = Image.open(path)
    assert img.size == (240, 160)


def test_run_frames(mgba_client):
    import time
    t0 = time.perf_counter()
    mgba_client.run_frames(10)
    assert time.perf_counter() - t0 < 5.0


def test_post_close_raises(mgba_client):
    """Closing and then using the client must raise MGBAConnectionError."""
    from liveplay.emulator.socket_client import MGBAConnectionError
    mgba_client.close()
    with pytest.raises(MGBAConnectionError):
        mgba_client.screenshot("/tmp/x.png")
