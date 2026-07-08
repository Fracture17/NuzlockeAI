"""
Loads the 4 battle region crops from /tmp/vision/ and prints OCR results.
Run crop_check.py first to generate the crops from a captured frame.

    python SCRIPTS/ocr_check.py [--dir PATH]
"""

import argparse
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from liveplay.vision.ocr import (
    read_battle_message,
    read_player_info,
    read_opponent_info,
    read_party_menu,
)
from liveplay.vision.regions import PARTY_SLOTS

CROPS = [
    ("opponent_hp_bar", read_opponent_info),
    ("player_hp",       read_player_info),
    ("battle_message",  read_battle_message),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="/tmp/vision",
                        help="Directory containing crop PNGs (default: /tmp/vision)")
    args = parser.parse_args()

    crop_dir = Path(args.dir)

    for name, fn in CROPS:
        path = crop_dir / f"{name}.png"
        if not path.exists():
            print(f"  {name:<20}  [missing: {path}]")
            continue
        img = Image.open(path)
        result = fn(img)
        print(f"  {name:<20}  {result}")

    party_path = crop_dir / "party_menu.png"
    if party_path.exists():
        party_img = Image.open(party_path)
        slot_images = [
            party_img.crop((x, y, x + w, y + h)) for x, y, w, h in PARTY_SLOTS
        ]
        results = read_party_menu(slot_images)
        print(f"  {'party_menu':<20}  {results}")
    else:
        print(f"  {'party_menu':<20}  [missing: {party_path}]")


if __name__ == "__main__":
    main()
