"""Override maps that reconcile external names with our engine enums.

Two problems are solved here:

1. Trainer-pkl names use Showdown-style spellings (``Weezing_Galarian``,
   ``Vice Grip``, ``As One (Glastrier)``) that do not normalize onto our
   GBA-derived enum members. ``*_ALIASES`` map a raw external name to the
   correct member. ``_lookup_enum`` consults these BEFORE its normalized
   direct lookup and raises if neither resolves (no silent NONE fallback).

2. Form species (Galarian/Alolan/Hisuian/etc.) are displayed by the emulator
   under their BASE name. ``SPECIES_TO_EMULATOR_NAME`` overrides a form's match
   string with its base species name so OCR'd opponent names resolve.

All maps are override-only: anything not listed falls back to the existing
direct lookup. Keys are the raw external strings exactly as they appear.
"""

from liveplay.data.species import Species
from liveplay.data.moves import Move
from liveplay.data.items import Item
from liveplay.data.abilities import Ability

# --- Trainer-pkl name -> engine enum member (override only) ---------------

SPECIES_ALIASES: dict[str, Species] = {
    "Farfetchd": Species.FARFETCH_U2019D,
    "Farfetchd_Galarian": Species.FARFETCH_U2019D_GALAR,
    "Sirfetchd": Species.SIRFETCH_U2019D,
    "Linoone_Galarian": Species.LINOONE_GALAR,
    "Zigzagoon_Galarian": Species.ZIGZAGOON_GALAR,
    "Dugtrio_Alolan": Species.DUGTRIO_ALOLA,
    "Graveler_Alolan": Species.GRAVELER_ALOLA,
    "Golem_Alolan": Species.GOLEM_ALOLA,
    "Persian_Alolan": Species.PERSIAN_ALOLA,
    "Raichu_Alolan": Species.RAICHU_ALOLA,
    "Slowbro_Galarian": Species.SLOWBRO_GALAR,
    "Slowking_Galarian": Species.SLOWKING_GALAR,
    "Rapidash_Galarian": Species.RAPIDASH_GALAR,
    "Exeggutor_Alolan": Species.EXEGGUTOR_ALOLA,
    "Muk_Alolan": Species.MUK_ALOLA,
    "Weezing_Galarian": Species.WEEZING_GALAR,
    "Marowak_Alolan": Species.MAROWAK_ALOLA,
    "Ninetales_Alolan": Species.NINETALES_ALOLA,
    "Sandslash_Alolan": Species.SANDSLASH_ALOLA,
    "Raticate_Alolan": Species.RATICATE_ALOLA,
    "Mr_Mime_Galarian": Species.MR_MIME_GALAR,
    "Articuno_Galarian": Species.ARTICUNO_GALAR,
    "Zapdos_Galarian": Species.ZAPDOS_GALAR,
    "Moltres_Galarian": Species.MOLTRES_GALAR,
    "Corsola_Galarian": Species.CORSOLA_GALAR,
    "Meowstic_Female": Species.MEOWSTIC_F,
    "Indeedee_Female": Species.INDEEDEE_F,
    "Floette_Eternal_Flower": Species.FLOETTE_ETERNAL,
    "Wormadam_Trash_Cloak": Species.WORMADAM_TRASH,
    "Wormadam_Sandy_Cloak": Species.WORMADAM_SANDY,
    "Greninja_Battle_Bond": Species.GRENINJA_BOND,
    "Oricorio_Pau": Species.ORICORIO_PA_U,
    "Urshifu_Rapid_Strike_Style": Species.URSHIFU_RAPID_STRIKE,
    "Avalugg_Hisuian": Species.AVALUGG_HISUI,
    "Arcanine_Hisuian": Species.ARCANINE_HISUI,
    "Samurott_Hisuian": Species.SAMUROTT_HISUI,
    "Decidueye_Hisuian": Species.DECIDUEYE_HISUI,
    "Typhlosion_Hisuian": Species.TYPHLOSION_HISUI,
    "Zoroark_Hisuian": Species.ZOROARK_HISUI,
    "Electrode_Hisuian": Species.ELECTRODE_HISUI,
    "Goodra_Hisuian": Species.GOODRA_HISUI,
    "Braviary_Hisuian": Species.BRAVIARY_HISUI,
    "Lilligant_Hisuian": Species.LILLIGANT_HISUI,
    "Darmanitan_Galarian": Species.DARMANITAN_GALAR,
    "Calyrex_Ice_Rider": Species.CALYREX_ICE,
    "Pikachu_World_Cap": Species.PIKACHU_WORLD,
    "Zygarde_50_Power_Construct": Species.ZYGARDE,
}

MOVE_ALIASES: dict[str, Move] = {
    "Vice Grip": Move.VISE_GRIP,
    "Natures Madness": Move.NATURE_S_MADNESS,
    "Kings Shield": Move.KING_S_SHIELD,
}

ITEM_ALIASES: dict[str, Item] = {
    "Kings Rock": Item.KING_S_ROCK,
}

ABILITY_ALIASES: dict[str, Ability] = {
    "As One (Glastrier)": Ability.AS_ONE_GLASTRIER,
}

# Dispatch table consulted by _lookup_enum, keyed by enum class.
ENUM_ALIASES = {
    Species: SPECIES_ALIASES,
    Move: MOVE_ALIASES,
    Item: ITEM_ALIASES,
    Ability: ABILITY_ALIASES,
}

# --- Engine species member -> emulator display name (override only) -------
# Forms render under their base species name in the emulator; map each form to
# the base member's name so OCR'd opponent names match. Values are the base
# member names (via ``.name``) to stay in lock-step with how base species match.

SPECIES_TO_EMULATOR_NAME: dict[Species, str] = {
    Species.FARFETCH_U2019D_GALAR: Species.FARFETCH_U2019D.name,
    Species.LINOONE_GALAR: Species.LINOONE.name,
    Species.ZIGZAGOON_GALAR: Species.ZIGZAGOON.name,
    Species.DUGTRIO_ALOLA: Species.DUGTRIO.name,
    Species.GRAVELER_ALOLA: Species.GRAVELER.name,
    Species.GOLEM_ALOLA: Species.GOLEM.name,
    Species.PERSIAN_ALOLA: Species.PERSIAN.name,
    Species.RAICHU_ALOLA: Species.RAICHU.name,
    Species.SLOWBRO_GALAR: Species.SLOWBRO.name,
    Species.SLOWKING_GALAR: Species.SLOWKING.name,
    Species.RAPIDASH_GALAR: Species.RAPIDASH.name,
    Species.EXEGGUTOR_ALOLA: Species.EXEGGUTOR.name,
    Species.MUK_ALOLA: Species.MUK.name,
    Species.WEEZING_GALAR: Species.WEEZING.name,
    Species.MAROWAK_ALOLA: Species.MAROWAK.name,
    Species.NINETALES_ALOLA: Species.NINETALES.name,
    Species.SANDSLASH_ALOLA: Species.SANDSLASH.name,
    Species.RATICATE_ALOLA: Species.RATICATE.name,
    Species.MR_MIME_GALAR: Species.MR_MIME.name,
    Species.ARTICUNO_GALAR: Species.ARTICUNO.name,
    Species.ZAPDOS_GALAR: Species.ZAPDOS.name,
    Species.MOLTRES_GALAR: Species.MOLTRES.name,
    Species.CORSOLA_GALAR: Species.CORSOLA.name,
    Species.MEOWSTIC_F: Species.MEOWSTIC.name,
    Species.INDEEDEE_F: Species.INDEEDEE.name,
    Species.FLOETTE_ETERNAL: Species.FLOETTE.name,
    Species.WORMADAM_TRASH: Species.WORMADAM.name,
    Species.WORMADAM_SANDY: Species.WORMADAM.name,
    Species.GRENINJA_BOND: Species.GRENINJA.name,
    Species.ORICORIO_PA_U: Species.ORICORIO.name,
    Species.URSHIFU_RAPID_STRIKE: Species.URSHIFU.name,
    Species.AVALUGG_HISUI: Species.AVALUGG.name,
    Species.ARCANINE_HISUI: Species.ARCANINE.name,
    Species.SAMUROTT_HISUI: Species.SAMUROTT.name,
    Species.DECIDUEYE_HISUI: Species.DECIDUEYE.name,
    Species.TYPHLOSION_HISUI: Species.TYPHLOSION.name,
    Species.ZOROARK_HISUI: Species.ZOROARK.name,
    Species.ELECTRODE_HISUI: Species.ELECTRODE.name,
    Species.GOODRA_HISUI: Species.GOODRA.name,
    Species.BRAVIARY_HISUI: Species.BRAVIARY.name,
    Species.LILLIGANT_HISUI: Species.LILLIGANT.name,
    Species.DARMANITAN_GALAR: Species.DARMANITAN.name,
    Species.CALYREX_ICE: Species.CALYREX.name,
    Species.PIKACHU_WORLD: Species.PIKACHU.name,
}


def emulator_species_name(species: Species) -> str:
    """Return the match string the emulator displays for a species.

    Form species fall back to their base name; everything else uses the
    member name directly (current behavior).
    """
    return SPECIES_TO_EMULATOR_NAME.get(species, species.name)
