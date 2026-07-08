# Shared name-normalization utilities for data-generation scripts.
import re


def to_python_name(name: str) -> str:
    """Converts display name to uppercase Python identifier: 'Will-O-Wisp' -> 'WILL_O_WISP'."""
    name = re.sub(r"[^a-zA-Z0-9]+", "_", name)
    return name.strip("_").upper()
