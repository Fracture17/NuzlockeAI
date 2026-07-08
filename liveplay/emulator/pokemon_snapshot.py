# Immutable snapshot of a single Pokemon as read from the emulator memory.
# Parsed from the 50-field pipe-delimited wire format produced by mGBASocketServer.lua.
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from liveplay.data.species import Species

_NFIELDS = 50


@dataclass
class PokemonSnapshot:
    """One Pokemon's data from emulator memory (box or party)."""

    box: int          # -1 for party, 0–13 for box
    slot: int         # party index 0–5, or box slot 0–29
    species: int
    nickname: str
    ot_name: str
    ot_id: int
    personality: int
    is_egg: bool
    is_bad_egg: bool
    has_species: bool
    held_item: int
    experience: int
    friendship: int
    pp_bonuses: int
    moves: tuple[int, int, int, int]
    pp: tuple[int, int, int, int]
    hp_ev: int
    atk_ev: int
    def_ev: int
    spe_ev: int
    spa_ev: int
    spd_ev: int
    hp_iv: int
    atk_iv: int
    def_iv: int
    spe_iv: int
    spa_iv: int
    spd_iv: int
    nature: int
    alt_ability: int
    pokerus: int
    pokeball: int
    met_location: int
    met_level: int
    met_game: int
    level: Optional[int] = None
    current_hp: Optional[int] = None
    max_hp: Optional[int] = None
    status: Optional[int] = None
    attack: Optional[int] = None
    defense: Optional[int] = None
    speed: Optional[int] = None
    sp_attack: Optional[int] = None
    sp_defense: Optional[int] = None

    @property
    def in_party(self) -> bool:
        return self.box == -1

    def leftover_exp(self, species: "Species") -> int:
        """Return EXP accumulated beyond the current level threshold."""
        if self.level is None:
            raise ValueError("level is None; cannot compute leftover_exp")
        from liveplay.data.species import SPECIES_DATA
        from liveplay.data.growth_rate import exp_for_level
        growth_rate = SPECIES_DATA[species].growth_rate
        return self.experience - exp_for_level(growth_rate, self.level)

    @classmethod
    def from_wire(cls, line: str) -> "PokemonSnapshot":
        """Parse a 50-field pipe-delimited wire line into a PokemonSnapshot."""
        parts = line.split("|")
        if len(parts) != _NFIELDS:
            raise ValueError(f"expected {_NFIELDS} fields, got {len(parts)}")

        def opt(s: str) -> Optional[int]:
            return int(s) if s else None

        return cls(
            box=int(parts[0]),
            slot=int(parts[1]),
            species=int(parts[2]),
            nickname=parts[3],
            ot_name=parts[4],
            ot_id=int(parts[5]),
            personality=int(parts[6]),
            is_egg=bool(int(parts[7])),
            is_bad_egg=bool(int(parts[8])),
            has_species=bool(int(parts[9])),
            held_item=int(parts[10]),
            experience=int(parts[11]),
            friendship=int(parts[12]),
            pp_bonuses=int(parts[13]),
            moves=(int(parts[14]), int(parts[15]), int(parts[16]), int(parts[17])),
            pp=(int(parts[18]), int(parts[19]), int(parts[20]), int(parts[21])),
            hp_ev=int(parts[22]),
            atk_ev=int(parts[23]),
            def_ev=int(parts[24]),
            spe_ev=int(parts[25]),
            spa_ev=int(parts[26]),
            spd_ev=int(parts[27]),
            hp_iv=int(parts[28]),
            atk_iv=int(parts[29]),
            def_iv=int(parts[30]),
            spe_iv=int(parts[31]),
            spa_iv=int(parts[32]),
            spd_iv=int(parts[33]),
            nature=int(parts[34]),
            alt_ability=int(parts[35]),
            pokerus=int(parts[36]),
            pokeball=int(parts[37]),
            met_location=int(parts[38]),
            met_level=int(parts[39]),
            met_game=int(parts[40]),
            level=opt(parts[41]),
            current_hp=opt(parts[42]),
            max_hp=opt(parts[43]),
            status=opt(parts[44]),
            attack=opt(parts[45]),
            defense=opt(parts[46]),
            speed=opt(parts[47]),
            sp_attack=opt(parts[48]),
            sp_defense=opt(parts[49]),
        )
