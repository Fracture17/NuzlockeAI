"""Exception hierarchy for the vision capture/read pipeline: CaptureError is the base; RegionEmptyError covers invalid crops; ScreenMismatchError covers unexpected screen layout."""


class CaptureError(Exception):
    pass

class RegionEmptyError(CaptureError):
    pass

class ScreenMismatchError(CaptureError):
    """Raised when the captured region doesn't match the expected screen layout."""
    pass
