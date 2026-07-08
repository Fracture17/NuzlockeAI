"""Screen capture via mGBA socket client with PIL crop and a short-lived frame cache."""

import os
import tempfile
import time
from PIL import Image
from liveplay.emulator.socket_client import MGBASocketClient
from .errors import RegionEmptyError

_FRAME_CACHE_TTL = 0.1  # seconds — sub-region calls within this window share one screenshot


class ScreenCapture:
    """
    Captures absolute screen regions using the mGBA socket client + PIL crop.
    Caches the full frame for _FRAME_CACHE_TTL seconds so multiple
    sub-region calls in the same cycle share one screenshot.
    """

    def __init__(self, client: MGBASocketClient):
        self._client = client
        self._frame: Image.Image | None = None
        self._frame_time: float = 0.0

    def invalidate(self) -> None:
        """Force the next capture to take a fresh screenshot."""
        self._frame = None

    def capture(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """Capture an absolute screen region, reusing a cached frame if recent."""
        if width <= 0 or height <= 0:
            raise RegionEmptyError(f"Invalid region: {width}x{height}")
        now = time.monotonic()
        if self._frame is None or (now - self._frame_time) > _FRAME_CACHE_TTL:
            self._frame = self._take_screenshot()
            self._frame_time = now
        return self._frame.crop((x, y, x + width, y + height))

    def _take_screenshot(self) -> Image.Image:
        """Request a frame from mGBA, load it as a PIL image, and clean up the temp file."""
        fd, path = tempfile.mkstemp(suffix=".png", prefix="mgba_frame_")
        os.close(fd)
        try:
            self._client.screenshot(path)
            img = Image.open(path)
            img.load()
            return img
        finally:
            if os.path.exists(path):
                os.unlink(path)
