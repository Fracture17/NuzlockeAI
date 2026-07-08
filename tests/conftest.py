# conftest.py — project-wide pytest configuration.
#
# Problem: test_constraints.py and test_play_helpers.py stub out liveplay.vision.ocr
# (and related modules) with MagicMock at import time so they can import
# SCRIPTS/play.py without hardware deps.  They use sys.modules.setdefault(),
# which is a no-op when the key is already present.  If those files are
# collected before test_vision_ocr.py, the mock lands in sys.modules first and
# test_vision_ocr.py ends up importing a MagicMock instead of the real module.
#
# Fix: import the real vision modules here, at conftest load time, which runs
# before any test module is imported.  The real objects are now in sys.modules,
# so every subsequent setdefault() call is a no-op and the real module is
# preserved for test_vision_ocr.py.

import liveplay.vision.ocr          # noqa: F401  — must stay before test collection
import liveplay.vision.hp_bar       # noqa: F401
