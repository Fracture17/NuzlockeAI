# Action dataclass and related constants for a single side in a battle turn. Engine-free.
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

# Sentinel move_slot for the forced Struggle action. Distinct from recharge (-1) so
# every `move_slot == -1` / `< 0` site that means "recharge" stays unambiguous and any
# unhandled Struggle site fails loudly rather than being mis-read as a recharge. The
# move itself is carried by move_override=Move.STRUGGLE.
STRUGGLE_SLOT = -2


class ActionKind(IntEnum):
    MOVE = 0
    SWITCH = 1


@dataclass
class Action:
    kind: ActionKind     # MOVE or SWITCH
    move_slot: int = -1  # -1 = recharge (no real move chosen)
    target_slot: int = 0 # for doubles: which opponent slot to target
    switch_to_slot: int = -1
    mega: bool = False
    move_override: Optional[object] = None  # sub-move override (Metronome, Sleep Talk, Assist); Move enum in practice
    source_slot: int = 0    # which active slot within the side this action comes from (0 or 1)
    target_side: int = -1   # for ANY-targeting: 0=own side, 1=foe side, -1=default foe side
