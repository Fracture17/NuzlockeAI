"""
Reads /tmp/vision/frame.png, crops the 4 battle regions defined in
src/vision/regions.py, and saves them alongside the frame in /tmp/vision/.

Workflow:
  1. python SCRIPTS/play.py  — press L in-game to capture a frame
  2. python SCRIPTS/crop_check.py  — inspect the crops, tweak regions.py, repeat

    python SCRIPTS/crop_check.py [--frame PATH]
"""

import argparse
import importlib
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))
import liveplay.vision.regions as regions

OUT_DIR = Path("/tmp/vision")

CROPS = [
    ("opponent_hp_bar", "OPPONENT_HP_BAR"),
    ("player_hp",       "PLAYER_HP"),
    ("battle_message",  "BATTLE_MESSAGE"),
    ("party_menu",      "PARTY_MENU"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame", default=str(OUT_DIR / "frame.png"),
                        help="Source frame PNG (default: /tmp/vision/frame.png)")
    args = parser.parse_args()

    frame_path = Path(args.frame)
    if not frame_path.exists():
        print(f"Frame not found: {frame_path}")
        print("Run `python SCRIPTS/play.py` and press L in-game first.")
        sys.exit(1)

    importlib.reload(regions)   # pick up any edits without restarting
    frame = Image.open(frame_path)
    frame.load()
    print(f"Frame: {frame_path}  ({frame.width}×{frame.height})\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, attr in CROPS:
        x, y, w, h = getattr(regions, attr)
        crop = frame.crop((x, y, x + w, y + h))
        dest = OUT_DIR / f"{name}.png"
        crop.save(dest)
        print(f"  {name:<20} ({x:3},{y:3}) {w:3}×{h:<3}  →  {dest}")


if __name__ == "__main__":
    main()
