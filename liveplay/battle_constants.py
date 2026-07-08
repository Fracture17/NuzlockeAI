"""Primary message IDs — string_ids that always start a new action group."""

from typing import Iterable

# ---------------------------------------------------------------------------
# Menu-rejection messages — printed when a move SELECTION is refused in the
# battle menu, before any turn elapses. The game shows the text, then returns
# to the option-select menu. Because the capture loop sees the menu disappear
# (message) and reappear (menu), it can mistake this for a completed turn and
# fire a phantom turn sweep. None of these strings appears during move
# EXECUTION, so a turn whose only content is one of these did not really happen.
# (Base-Emerald selection refusals; later-gen-only refusals like throat chop /
# heal block are intentionally excluded as their strings are dual-use.)
# ---------------------------------------------------------------------------
MENU_REJECTION_STRING_IDS: frozenset[str] = frozenset({
    "STRINGID_NOPPLEFT",              # "There's no PP left for this move!"
    "STRINGID_PKMNMOVEISDISABLED",   # "<mon>'s <move> is disabled!"
    "STRINGID_PKMNCANTUSEMOVETORMENT",  # "...can't use the same move in a row due to the TORMENT!"
    "STRINGID_PKMNCANTUSEMOVETAUNT",    # "...can't use <move> after the TAUNT!"
    "STRINGID_PKMNCANTUSEMOVESEALED",   # "...can't use the sealed <move>!" (Imprison)
})


def turn_has_real_action(string_ids: Iterable[str]) -> bool:
    """Return True if a sequence of captured message string_ids represents a real turn.

    A turn boundary can fire spuriously: when a move selection is rejected in the
    battle menu (e.g. "There's no PP left for this move!"), the rejection text is
    captured, the menu reappears, and the loop mistakes it for a completed turn.
    Returns False when the turn contains only menu-rejection messages (or nothing),
    so callers can skip the phantom sweep and keep the battle state untouched.
    """
    return any(sid not in MENU_REJECTION_STRING_IDS for sid in string_ids)


PRIMARY_STRING_IDS: frozenset[str] = frozenset({
    # Move execution
    "STRINGID_USEDMOVE",
    # Failed to move
    "STRINGID_ITHURTCONFUSION",
    "STRINGID_PKMNFASTASLEEP",
    "STRINGID_PKMNISPARALYZED",
    "STRINGID_PKMNIMMOBILIZEDBYLOVE",
    "STRINGID_PKMNLOAFING",
    "STRINGID_PKMNWONTOBEY",
    "STRINGID_PKMNIGNOREDORDERS",
    "STRINGID_PKMNIGNORESASLEEP",
    "STRINGID_PKMNMUSTRECHARGE",
    # Two-turn move setups
    "STRINGID_PKMNFLEWHIGH",
    "STRINGID_PKMNDUGHOLE",
    "STRINGID_PKMNHIDUNDERWATER",
    "STRINGID_PKMNCHARGINGPOWER",
    "STRINGID_PKMNSPRANGUP",
    "STRINGID_PKMNISGLOWING",
    "STRINGID_PKMNTOOKSUNLIGHT",
    "STRINGID_PKMNLOWEREDHEAD",
    "STRINGID_PKMNTIGHTENINGFOCUS",
    "STRINGID_PKMNTOOKAIM",
    "STRINGID_PKMNFORESAWATTACK",
    "STRINGID_PKMNCHOSEXASDESTINY",
    "STRINGID_PKMNSTORINGENERGY",
    "STRINGID_PKMNGETTINGINTOPOSITION",
    # Switches / item use
    "STRINGID_RETURNMON",
    "STRINGID_INTROSENDOUT",
    "STRINGID_PLAYER_INTROSENDOUT",
    "STRINGID_SWITCHINMON",
    "STRINGID_PLAYER_SWITCHINMON",
    "STRINGID_PLAYERUSEDITEM",
    "STRINGID_TRAINER1USEDITEM",
    "STRINGID_WALLYUSEDITEM",
    # End-of-turn residuals (each is its own single-message action group)
    "STRINGID_PKMNHURTBYPOISON",
    "STRINGID_PKMNHURTBYBURN",
    "STRINGID_PKMNSAPPEDBYLEECHSEED",
    "STRINGID_PKMNBUFFETEDBYSANDSTORM",
    "STRINGID_PKMNPELTEDBYHAIL",
    "STRINGID_PKMNPERISHCOUNTFELL",
    # Weather / field state
    "STRINGID_SANDSTORMRAGES",
    "STRINGID_SANDSTORMISRAGING",
    "STRINGID_RAINCONTINUES",
    "STRINGID_SUNLIGHTSTRONG",
    "STRINGID_DOWNPOURCONTINUES",
    "STRINGID_HAILCONTINUES",
    "STRINGID_SANDSTORMBREWED",
    "STRINGID_STARTEDTORAIN",
    "STRINGID_STARTEDHAIL",
    "STRINGID_SUNLIGHTGOTBRIGHT",
    "STRINGID_DOWNPOURSTARTED",
    "STRINGID_SANDSTORMSUBSIDED",
    "STRINGID_RAINSTOPPED",
    "STRINGID_SUNLIGHTFADED",
    "STRINGID_HAILSTOPPED",
    # Battle boundaries
    "STRINGID_INTROMSG",
    "STRINGID_BATTLEEND",
    "STRINGID_PLAYERDEFEATEDTRAINER1",
    # Mega Evolution / Primal Reversion (trigger new action group)
    "STRINGID_MEGAEVOLUTION",
    "STRINGID_MEGAEVOLUTION_NOITEM",
    "STRINGID_MEGAEVOLUTION_GEN6",
    "STRINGID_TRANSFORMMEGA",
    "STRINGID_PRIMALREVERSION",
    # Ability activations on switch-in (each is its own action group)
    "STRINGID_AIRLOCKSUPPRESSES",
    "STRINGID_AURABREAKSTART",
    "STRINGID_COMATOSEACTIVATE",
    "STRINGID_DARKAURASTART",
    "STRINGID_FAIRYAURASTART",
    "STRINGID_FLASHFIREACTIVATE",
    "STRINGID_MOLDBREAKERSUPPRESSES",
    "STRINGID_NEUTRALIZINGGASSTART",
    "STRINGID_NEUTRALIZINGGASEND",
    "STRINGID_PRESSUREACTIVATE",
    "STRINGID_SLOWSTARTSTART",
    "STRINGID_TERAVOLTSTART",
    "STRINGID_TURBOBLAZESTART",
    "STRINGID_UNNERVESTART",
    # End-of-turn ability events
    "STRINGID_BADDREAMSDAMAGE",
    "STRINGID_DRYSKINABSORB",
    "STRINGID_HARVESTADDITEM",
    "STRINGID_SALTCUREDAMAGE",
    "STRINGID_SLOWSTARTEND",
    "STRINGID_SCHOOLINGSTART",
    "STRINGID_SCHOOLINGEND",
    "STRINGID_AQUARINGHEAL",
    "STRINGID_LEFTOVERSHEAL",
    "STRINGID_BLACKSLUDGEHEAL",
    "STRINGID_SHELLBELLHEAL",
    "STRINGID_LIFEORBDAMAGE",
    "STRINGID_STEALTHROCKDAMAGE",
    "STRINGID_STICKYWEBACTIVATE",
    "STRINGID_ROCKYHELMETDAMAGE",
    # Post-battle
    "STRINGID_PKMNGAINEDEXP",
    # Player loss
    "STRINGID_PLAYERWHITEOUT",
    "STRINGID_PLAYERWHITEOUT2",
})
