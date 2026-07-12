# Procedural battle generator for curriculum training. Builds random-but-legal BattleState
# instances from the generated learnset/ability tables. Move weighting: player gets level-up
# (weight 1.0), TM/tutor (0.5), NO eggs; opponent gets every learnset entry (weight 1.0).
# Items: curated GENERAL_ITEMS pool (validated at import); opponent always holds an item;
# player has 20% chance of NONE, else picks from pool (+ species' mega stone if applicable).
# Natures: opponent gets optimal — physical mon picks ADAMANT or JOLLY, special picks MODEST
# or TIMID (chosen via rng so opponents vary between max-power and max-speed spreads).
# Abilities: player draws only from normal abilities; opponent draws from normal + hidden.
import json
import random
from functools import lru_cache
from pathlib import Path

from liveplay.data.abilities import Ability
from liveplay.data.items import Item
from liveplay.data.mega import MEGA_PRE_SPECIES
from liveplay.data.moves import Move, MOVE_DATA, MoveCategory
from liveplay.data.natures import Nature, NATURE_DATA, Stat
from liveplay.data.species import Species, SPECIES_DATA
from liveplay.state.battle import BattleState
from liveplay.state.pokemon import PokemonState, GenderEnum
from liveplay.state.side import SideState

_DATA_DIR = Path(__file__).parent / "data"
_LEARNSETS_PATH = _DATA_DIR / "generated_learnsets.json"
_ABILITIES_PATH = _DATA_DIR / "generated_abilities.json"

# ---------------------------------------------------------------------------
# Curated item pool — validated against Item enum at import time.
# Only items with a real in-battle effect. Excludes: NONE, mega stones (handled
# separately per species), and species-specific items (Thick Club, Light Ball, etc.).
# ---------------------------------------------------------------------------

def _build_general_items() -> tuple[Item, ...]:
    """Build and validate the curated general item pool. Fails loud if any name is not a real Item member."""
    _CURATED_NAMES: list[str] = [
        # --- Status-curing / HP berries ---
        "SITRUS_BERRY", "LUM_BERRY", "ORAN_BERRY",
        "CHERI_BERRY", "CHESTO_BERRY", "PECHA_BERRY", "RAWST_BERRY", "ASPEAR_BERRY",
        "LEPPA_BERRY", "PERSIM_BERRY",
        # --- Confusion/pinch berries (flavour/stat boost at low HP) ---
        "FIGY_BERRY", "WIKI_BERRY", "MAGO_BERRY", "AGUAV_BERRY", "IAPAPA_BERRY",
        # --- Stat-pinch berries ---
        "LIECHI_BERRY", "GANLON_BERRY", "SALAC_BERRY", "PETAYA_BERRY", "APICOT_BERRY",
        "LANSAT_BERRY", "STARF_BERRY", "CUSTAP_BERRY",
        # --- Counter berries ---
        "KEE_BERRY", "MARANGA_BERRY",
        # --- Type-resist berries ---
        "OCCA_BERRY", "PASSHO_BERRY", "WACAN_BERRY", "RINDO_BERRY", "YACHE_BERRY",
        "CHOPLE_BERRY", "KEBIA_BERRY", "SHUCA_BERRY", "COBA_BERRY", "PAYAPA_BERRY",
        "TANGA_BERRY", "CHARTI_BERRY", "KASIB_BERRY", "HABAN_BERRY", "COLBUR_BERRY",
        "BABIRI_BERRY", "CHILAN_BERRY", "ROSELI_BERRY",
        # --- Gems ---
        "NORMAL_GEM", "FIRE_GEM", "WATER_GEM", "GRASS_GEM", "ELECTRIC_GEM", "ICE_GEM",
        "FIGHTING_GEM", "POISON_GEM", "GROUND_GEM", "FLYING_GEM", "PSYCHIC_GEM",
        "BUG_GEM", "ROCK_GEM", "GHOST_GEM", "DRAGON_GEM", "DARK_GEM", "STEEL_GEM",
        "FAIRY_GEM",
        # --- Core competitive items ---
        "LEFTOVERS", "LIFE_ORB", "FOCUS_SASH", "FOCUS_BAND",
        "CHOICE_BAND", "CHOICE_SPECS", "CHOICE_SCARF",
        "ASSAULT_VEST", "EVIOLITE", "BLACK_SLUDGE", "ROCKY_HELMET",
        "QUICK_CLAW", "WIDE_LENS", "SCOPE_LENS",
        "EXPERT_BELT", "MUSCLE_BAND", "WISE_GLASSES",
        "KING_S_ROCK", "RAZOR_CLAW", "RAZOR_FANG",
        "BRIGHT_POWDER", "LAGGING_TAIL", "IRON_BALL", "AIR_BALLOON",
        "WHITE_HERB", "POWER_HERB",
        "BIG_ROOT",
        "LIGHT_CLAY", "DAMP_ROCK", "HEAT_ROCK", "SMOOTH_ROCK", "ICY_ROCK",
        "METRONOME", "TOXIC_ORB", "FLAME_ORB", "STICKY_BARB",
        "RED_CARD", "EJECT_BUTTON",
        "SAFETY_GOGGLES", "PROTECTIVE_PADS",
        "THROAT_SPRAY", "ADRENALINE_ORB", "BLUNDER_POLICY", "WEAKNESS_POLICY",
        # --- Type-boost items ---
        "CHARCOAL", "MYSTIC_WATER", "MIRACLE_SEED", "MAGNET", "TWISTED_SPOON",
        "NEVER_MELT_ICE", "BLACK_BELT", "BLACK_GLASSES", "SHARP_BEAK", "POISON_BARB",
        "SOFT_SAND", "HARD_STONE", "SILK_SCARF", "SILVER_POWDER", "SPELL_TAG",
        "DRAGON_FANG", "METAL_COAT",
    ]

    bad = [n for n in _CURATED_NAMES if not hasattr(Item, n)]
    if bad:
        raise ValueError(f"Curated item names not found in Item enum: {bad}")

    return tuple(Item[n] for n in _CURATED_NAMES)


GENERAL_ITEMS: tuple[Item, ...] = _build_general_items()

# Reverse map: Species → frozenset of its mega stones (built once from MEGA_PRE_SPECIES).
_SPECIES_MEGA_STONES: dict[Species, frozenset[Item]] = {}
for _stone, _species in MEGA_PRE_SPECIES.items():
    _SPECIES_MEGA_STONES.setdefault(_species, set()).add(_stone)
_SPECIES_MEGA_STONES = {k: frozenset(v) for k, v in _SPECIES_MEGA_STONES.items()}

# Emergency Exit / Wimp Out mid-turn switch is deliberately unported in the C++ engine
# (see engine/src/turn.cpp ~line 839), so these species are pruned from all generated corpora.
CORPUS_BANNED_SPECIES = ("GOLISOPOD", "WIMPOD")


@lru_cache(maxsize=1)
def _load_tables() -> tuple[dict, dict]:
    """Load and cache learnset and ability JSON tables."""
    learnsets = json.loads(_LEARNSETS_PATH.read_text())
    abilities = json.loads(_ABILITIES_PATH.read_text())
    return learnsets, abilities


@lru_cache(maxsize=1)
def generatable_species() -> list[str]:
    """Return sorted list of species names usable by the generator (learnsets ∩ abilities ∩ SPECIES_DATA)."""
    learnsets, abilities = _load_tables()
    pool = []
    for name in learnsets:
        # Require at least one normal ability: the player must always have a legal non-hidden
        # ability. The RnB source omits ability lines for some species, leaving them with empty
        # normal lists — excluded here rather than crashing mid-generation. (CELEBI has only a
        # hidden-less Natural Cure; STARYU/STARMIE/DURALUDON were backfilled manually.)
        entry = abilities.get(name)
        if not entry or not entry.get("normal"):
            continue
        try:
            s = Species[name]
        except KeyError:
            continue
        if s not in SPECIES_DATA:
            continue
        pool.append(name)
    return sorted(pool)


def corpus_species_pool() -> list[str]:
    """Return generatable_species() minus CORPUS_BANNED_SPECIES."""
    return [s for s in generatable_species() if s not in CORPUS_BANNED_SPECIES]


def move_candidate_weights(species_name: str, level: int, is_player: bool) -> dict[Move, float]:
    """Return {Move: weight} candidate dict for the given species/level/side.

    Player: level-up moves at or below level (1.0), TM/tutor (0.5), max weight wins, no eggs.
    Opponent: every learnset entry at 1.0.
    Raises KeyError for unknown species names.
    """
    learnsets, _ = _load_tables()
    if species_name not in learnsets:
        raise KeyError(f"Unknown species: {species_name}")
    learnset = learnsets[species_name]
    result: dict[Move, float] = {}
    for move_name, info in learnset.items():
        try:
            move = Move[move_name]
        except KeyError:
            continue  # move not in engine enum; skip
        if is_player:
            w = _player_move_weight(info, level)
            if w > 0.0:
                result[move] = w
        else:
            result[move] = 1.0
    return result


def _player_move_weight(info: dict, level: int) -> float:
    """Compute weight for a single move entry for the player side. Returns 0.0 if not eligible."""
    best = 0.0
    if info["levelup"] is not None and info["levelup"] <= level:
        best = 1.0
    if info["tm"] or info["tutor"]:
        best = max(best, 0.5)
    return best


def optimized_nature(species_name: str, move_ids, rng: random.Random) -> Nature:
    """Return an optimal nature for the species using rng to vary between power and speed.

    Physical-leaning mon: ADAMANT (+Atk) or JOLLY (+Spe), both lower SpA.
    Special-leaning mon: MODEST (+SpA) or TIMID (+Spe), both lower Atk.
    Heuristic: compare base_atk vs base_spa; if equal, tiebreak via move majority.
    """
    learnsets, _ = _load_tables()
    if species_name not in learnsets:
        raise KeyError(f"Unknown species: {species_name}")
    species = Species[species_name]
    sdata = SPECIES_DATA[species]
    base_atk = sdata.base_atk
    base_spa = sdata.base_spa

    if base_atk != base_spa:
        boost_physical = base_atk > base_spa
    else:
        # Tiebreak via move majority
        phys = sum(
            1 for m in move_ids
            if m != Move.NONE and MOVE_DATA[m].category == MoveCategory.PHYSICAL
        )
        spec = sum(
            1 for m in move_ids
            if m != Move.NONE and MOVE_DATA[m].category == MoveCategory.SPECIAL
        )
        boost_physical = phys >= spec  # default to physical on tie

    if boost_physical:
        return rng.choice([Nature.ADAMANT, Nature.JOLLY])
    else:
        return rng.choice([Nature.MODEST, Nature.TIMID])


def _sample_item(species: Species, is_player: bool, rng: random.Random) -> Item:
    """Sample an item for the mon. Opponent always holds one; player has 20% chance of NONE."""
    if is_player and rng.random() < 0.20:
        return Item.NONE
    species_stones = _SPECIES_MEGA_STONES.get(species, frozenset())
    pool = GENERAL_ITEMS + tuple(species_stones)
    return rng.choice(pool)


def _sample_gender(species_name: str, rng: random.Random) -> GenderEnum:
    """Sample a gender for the species based on its male_ratio field."""
    species = Species[species_name]
    sdata = SPECIES_DATA[species]
    if sdata.male_ratio is None:
        return GenderEnum.GENDERLESS
    return GenderEnum.MALE if rng.random() < sdata.male_ratio else GenderEnum.FEMALE


def _sample_moves(
    species_name: str,
    level: int,
    is_player: bool,
    rng: random.Random,
) -> tuple[tuple[Move, ...], tuple[int, ...]]:
    """Sample up to 4 distinct moves for a mon, guaranteeing at least one damaging move if possible."""
    weights = move_candidate_weights(species_name, level, is_player)
    if not weights:
        raise ValueError(f"No candidate moves for {species_name} (level={level}, is_player={is_player})")

    moves_list = list(weights.keys())
    move_weights = [weights[m] for m in moves_list]

    # Identify damaging moves in the pool
    damaging = [m for m in moves_list if MOVE_DATA[m].category in (MoveCategory.PHYSICAL, MoveCategory.SPECIAL)]

    chosen: list[Move] = []

    # If damaging moves exist, guarantee one is included
    if damaging:
        first = rng.choices(damaging, k=1)[0]
        chosen.append(first)
        # Remove from pool for subsequent draws
        remaining_moves = [m for m in moves_list if m != first]
        remaining_weights = [weights[m] for m in remaining_moves]
    else:
        remaining_moves = moves_list
        remaining_weights = move_weights

    # Draw up to 3 more distinct moves
    while len(chosen) < 4 and remaining_moves:
        pick = rng.choices(remaining_moves, weights=remaining_weights, k=1)[0]
        chosen.append(pick)
        idx = remaining_moves.index(pick)
        remaining_moves.pop(idx)
        remaining_weights.pop(idx)

    # Pad to 4 slots
    while len(chosen) < 4:
        chosen.append(Move.NONE)

    move_ids = tuple(chosen)
    move_pp = tuple(MOVE_DATA[m].pp if m != Move.NONE else 0 for m in move_ids)
    return move_ids, move_pp


def generate_mon(
    species_name: str,
    level: int,
    is_player: bool,
    rng: random.Random,
) -> PokemonState:
    """Generate a single random-but-legal PokemonState. Raises KeyError for unknown species."""
    _, abilities_table = _load_tables()
    if species_name not in abilities_table:
        raise KeyError(f"Unknown species: {species_name}")

    species = Species[species_name]
    ivs = (31, 31, 31, 31, 31, 31)

    move_ids, move_pp = _sample_moves(species_name, level, is_player, rng)

    if is_player:
        nature = rng.choice(list(Nature))
    else:
        nature = optimized_nature(species_name, move_ids, rng)

    # Ability: player draws from normal only; opponent draws from normal + hidden.
    entry = abilities_table[species_name]
    if is_player:
        legal_abilities = entry["normal"]
    else:
        legal_abilities = entry["normal"] + entry["hidden"]
    if not legal_abilities:
        raise ValueError(f"No legal abilities for {species_name} (is_player={is_player})")
    ability_name = rng.choice(legal_abilities)
    ability = Ability[ability_name]

    item = _sample_item(species, is_player, rng)

    gender = _sample_gender(species_name, rng)

    return PokemonState(
        species=species,
        nature=nature,
        ivs=ivs,
        gender=gender,
        level=level,
        ability=ability,
        item=item,
        move_ids=move_ids,
        move_pp=move_pp,
    )


def generate_team(
    rng: random.Random,
    *,
    size: int,
    level: int,
    is_player: bool,
    species_pool: list[str] | None = None,
) -> list[PokemonState]:
    """Generate a team of `size` mons with distinct species sampled from species_pool."""
    if species_pool is None:
        species_pool = generatable_species()
    if size > len(species_pool):
        raise ValueError(f"Requested team size {size} exceeds pool size {len(species_pool)}")
    chosen_species = rng.sample(species_pool, size)
    return [generate_mon(name, level, is_player, rng) for name in chosen_species]


def generate_battle(
    rng: random.Random,
    *,
    player_level: int,
    opp_level: int,
    player_size: int,
    opp_size: int,
    species_pool: list[str] | None = None,
) -> BattleState:
    """Generate a full BattleState. Player is side 0, opponent is side 1.

    species_pool restricts BOTH sides (parity corpora use it to prune species whose
    only ability is Emergency Exit / Wimp Out — the C++ mid-turn switch path is unported).
    """
    player_team = generate_team(rng, size=player_size, level=player_level, is_player=True,
                                species_pool=species_pool)
    opp_team = generate_team(rng, size=opp_size, level=opp_level, is_player=False,
                             species_pool=species_pool)
    player_side = SideState(team=player_team)
    opp_side = SideState(team=opp_team)
    return BattleState(sides=(player_side, opp_side))


def make_random_battle(rng: random.Random) -> tuple[BattleState, dict]:
    """Generate a random singles battle using corpus_species_pool(). Levels 5-100, team sizes 1-6 per side."""
    params = dict(
        player_level=rng.randint(5, 100),
        opp_level=rng.randint(5, 100),
        player_size=rng.randint(1, 6),
        opp_size=rng.randint(1, 6),
    )
    state = generate_battle(rng, species_pool=corpus_species_pool(), **params)
    return state, params
