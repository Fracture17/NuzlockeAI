"""
Captures all 4 battle screen regions and saves them as PNGs via the mGBA Lua socket server.

Save a raw GBA frame (240x160) for calibrating region coordinates in src/vision/regions.py:
    python SCRIPTS/vision_check.py --screenshot [--out /tmp/vision]

Run region capture test (requires mGBA running with Lua socket server on localhost:8888):
    python SCRIPTS/vision_check.py [--out /tmp/vision]
"""

import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from liveplay.emulator import MGBAProcess
from liveplay.vision import BattleReader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", action="store_true",
                        help="Save a raw GBA frame (240x160) as frame.png and exit")
    parser.add_argument("--out", default="/tmp/vision", help="Output directory for PNGs")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("Launching mGBA...")
    with MGBAProcess() as mgba:
        print("  mGBA is running")
        print()

        if args.screenshot:
            path = str(out / "frame.png")
            mgba.socket.screenshot(path)
            print(f"Saved to {path}")
            return

        reader = BattleReader(mgba.socket)
        captures = {
            "battle_message":  reader.battle_message,
            "player_hp":       reader.player_hp,
            "opponent_hp_bar": reader.opponent_hp_bar,
            "party_menu":      reader.party_menu,
        }

        total_start = time.perf_counter()
        for name, fn in captures.items():
            t0 = time.perf_counter()
            img = fn()
            elapsed_ms = (time.perf_counter() - t0) * 1000
            path = out / f"{name}.png"
            img.save(path)
            size_kb = path.stat().st_size / 1024
            print(f"  [ok]    {name:<20} {img.width}x{img.height}  {size_kb:6.1f} KB  {elapsed_ms:6.1f} ms  -> {path}")

        total_ms = (time.perf_counter() - total_start) * 1000
        print(f"\n  total: {total_ms:.1f} ms")
        print("\nPress Enter to close mGBA...")
        input()


if __name__ == "__main__":
    main()
