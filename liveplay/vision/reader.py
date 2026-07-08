"""High-level battle screen reader. Returns PIL Images (stubs) or raises CaptureError."""

from PIL import Image
from .capture import ScreenCapture
from .regions import BATTLE_MESSAGE, PLAYER_HP, OPPONENT_HP_BAR, PARTY_MENU
from .errors import ScreenMismatchError
from liveplay.emulator.socket_client import MGBASocketClient


class BattleReader:
    """
    Captures sub-regions of the Pokemon Emerald battle screen via the mGBA socket client.

    Each method returns a PIL.Image of the relevant region, or raises a
    CaptureError subclass if the region looks wrong.

    Call invalidate() to force a fresh screenshot on the next capture.
    """

    def __init__(self, client: MGBASocketClient):
        self._screen = ScreenCapture(client)

    def invalidate(self) -> None:
        """Force the next capture to take a fresh screenshot."""
        self._screen.invalidate()

    # ------------------------------------------------------------------
    # Public capture methods
    # ------------------------------------------------------------------

    def battle_message(self) -> Image.Image:
        """Capture the battle message / move selection box."""
        return self._capture("battle_message", BATTLE_MESSAGE)

    def player_hp(self) -> Image.Image:
        """Capture the player HP display (numeric HP text)."""
        return self._capture("player_hp", PLAYER_HP)

    def opponent_hp_bar(self) -> Image.Image:
        """Capture the opponent HP bar."""
        return self._capture("opponent_hp_bar", OPPONENT_HP_BAR)

    def party_menu(self) -> Image.Image:
        """Capture the party menu overlay."""
        return self._capture("party_menu", PARTY_MENU)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _capture(self, name: str, region: tuple[int, int, int, int]) -> Image.Image:
        x, y, w, h = region
        image = self._screen.capture(x, y, w, h)
        _check_region(image, name)
        return image


def _check_region(image: Image.Image, name: str) -> None:
    """Sanity check: ensure the image is non-empty and not a solid colour."""
    if image.width == 0 or image.height == 0:
        raise ScreenMismatchError(f"[{name}] Captured region is empty")
    extrema = image.convert("L").getextrema()
    if extrema[0] == extrema[1]:
        raise ScreenMismatchError(
            f"[{name}] Captured region is solid colour (value={extrema[0]}); "
            "screen may be off or coordinates are wrong"
        )
