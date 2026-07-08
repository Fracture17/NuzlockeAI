# Tests for the shared to_python_name normalization function in scripts/_naming.py.
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "SCRIPTS"))
from _naming import to_python_name


@pytest.mark.parametrize("display_name, expected", [
    # Hyphens become underscores
    ("Will-O-Wisp", "WILL_O_WISP"),
    ("Ho-Oh", "HO_OH"),
    ("Porygon-Z", "PORYGON_Z"),
    # Space and period runs collapse to single underscore
    ("Mr. Mime", "MR_MIME"),
    # Apostrophe
    ("Farfetch'd", "FARFETCH_D"),
    # No special characters — pass through uppercased
    ("Thunderbolt", "THUNDERBOLT"),
    ("Swift", "SWIFT"),
    # Mixed: parens, spaces, hyphens
    ("Toxic (Poison-type user)", "TOXIC_POISON_TYPE_USER"),
    # Leading/trailing non-alphanum are stripped
    ("---test---", "TEST"),
    # Already uppercase, no specials
    ("NORMAL", "NORMAL"),
    # Digits are preserved
    ("Porygon2", "PORYGON2"),
    ("Type: Null", "TYPE_NULL"),
])
def test_to_python_name(display_name, expected):
    assert to_python_name(display_name) == expected
