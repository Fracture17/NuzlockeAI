"""
Absolute pixel coordinates for Pokemon Emerald (Gen 3) battle screen regions.

GBA native resolution: 240 × 160 px.
Each entry is (x, y, width, height).

Workflow to calibrate:
  1. Run `python SCRIPTS/play.py`, press L to save frame + crops to /tmp/vision/.
  2. Open /tmp/vision/frame.png as the reference.
  3. Adjust the numbers below, re-press L, compare crops.
"""

# ┌─────────────────────────────── 240 ───────────────────────────────────┐
# │  [OPPONENT STATUS ≈ 0,2,120,36]                                       │
# │                         [opponent sprite]                             │
# │         [player sprite]                                               │
# │                                   [PLAYER STATUS ≈ 112,88,128,42]    │
# │══════════════════════════════════════════════════════════════════════│
# │  [BATTLE MESSAGE ≈ 4,112,232,46]                                      │
# └───────────────────────────────────────────────────────────────────────┘

# Battle message / move selection box (bottom strip)
BATTLE_MESSAGE: tuple[int, int, int, int] = (4, 112, 232, 46)

# Player HP box — name, HP bar, and numeric HP (bottom-right)
PLAYER_HP: tuple[int, int, int, int] = (140, 75, 85, 30)

# Opponent HP box — name and HP bar (top-left)
OPPONENT_HP_BAR: tuple[int, int, int, int] = (15, 18, 90, 20)

# Single-pixel row within the opponent HP bar for pixel-counting HP estimation.
# Coordinates are relative to the OPPONENT_HP_BAR crop.
# Includes 1 edge pixel at the beginning and end to ensure it's a valid bar row.
OPPONENT_HP_BAR_PIXELS: tuple[int, int, int, int] = (52 - 16, 35 - 19, 50, 1)  # placeholder

# Party screen — full frame (overlay replaces the whole screen)
PARTY_MENU: tuple[int, int, int, int] = (0, 0, 240, 130)

# Individual party slot regions — (x, y, width, height).
# Slot 1 is the larger left-panel summary; slots 2–6 are right-side rows spaced 25 px apart.
SLOT_DISTANCE = 24
PARTY_SLOTS: tuple[tuple[int, int, int, int], ...] = (
    ( 19, 36,  65, 38),   # slot 1
    (110, 13 + SLOT_DISTANCE * 0, 126, 20),   # slot 2
    (110, 13 + SLOT_DISTANCE * 1, 126, 20),   # slot 3
    (110, 13 + SLOT_DISTANCE * 2, 126, 20),   # slot 4
    (110, 13 + SLOT_DISTANCE * 3, 126, 20),   # slot 5
    (110, 13 + SLOT_DISTANCE * 4, 126, 20),   # slot 6
)

# Sub-regions within slot 1 (large left panel) — (x, y, width, height), relative to slot top-left.
PARTY_SLOT_NAME:       tuple[int, int, int, int] = ( 9,  3, 50, 7)
PARTY_SLOT_STATUS:     tuple[int, int, int, int] = (14, 12, 36, 9)
PARTY_SLOT_HP_CURRENT: tuple[int, int, int, int] = (28, 29, 14, 7)
PARTY_SLOT_HP_MAX:     tuple[int, int, int, int] = (47, 29, 17, 7)

# Sub-regions within slots 2–6 (right-side rows) — (x, y, width, height), relative to slot top-left.
PARTY_SLOT_ROW_NAME:       tuple[int, int, int, int] = (  2,  2, 48, 7)
PARTY_SLOT_ROW_STATUS:     tuple[int, int, int, int] = (  5, 11, 34, 7)
PARTY_SLOT_ROW_HP_CURRENT: tuple[int, int, int, int] = ( 85, 11, 17, 7)
PARTY_SLOT_ROW_HP_MAX:     tuple[int, int, int, int] = (108, 11, 15, 7)
