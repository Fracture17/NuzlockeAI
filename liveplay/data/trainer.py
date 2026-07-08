"""Trainer/Pokemon dataclasses and the parser that builds them from the R&B calc's
SETDEX_SS blob (src/js/data/sets/gen8.js in syl-rnb-calc).

The calc stores per-mon IVs that the old text-file source lacked. Data is keyed
species -> trainer -> set; we invert it into per-trainer Pokemon lists ordered by
the set's global `index`. Trainer names are reconciled against a reference list of
OCR-correct names (the previous pickle) since on-screen names must match exactly.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json
import pickle
import re
from typing import Optional

TRAINERS_PICKLE = Path(__file__).parent / "trainers.pkl"

# Calc IV keys in PokemonState.ivs tuple order: (hp, atk, def, spa, spd, spe).
IV_KEY_ORDER = ("hp", "at", "df", "sa", "sd", "sp")
DEFAULT_IV = 31


@dataclass
class Pokemon:
    name: str
    level: int
    item: Optional[str]
    moves: list[str]
    nature: str
    ability: str
    ivs: dict[str, int] = field(default_factory=dict)  # only non-31 stats; missing => 31

    def __str__(self) -> str:
        item_str = f" @{self.item}" if self.item else ""
        moves_str = f": {', '.join(self.moves)}" if self.moves else ""
        iv_str = f" IVs{self.ivs}" if self.ivs else ""
        return f"  {self.name} Lv.{self.level}{item_str}{moves_str} [{self.nature}|{self.ability}]{iv_str}"


@dataclass
class Trainer:
    name: str            # clean OCR name: "<class> <name>" (or "<class> Grunt"); no [..] tags
    route: str
    pokemon: list[Pokemon] = field(default_factory=list)
    boss: bool = False
    double: bool = False
    partner: Optional[int] = None  # index of the opposing partner trainer in a multi-trainer double
    tag: Optional[int] = None      # index of your ally trainer (tag battles, e.g. Steven)

    def __str__(self) -> str:
        flags = "".join(f" [{f}]" for f, on in (("Boss", self.boss), ("Double", self.double)) if on)
        ptn = f" partner={self.partner}" if self.partner is not None else ""
        tag = f" tag={self.tag}" if self.tag is not None else ""
        lines = [f"{self.name} ({self.route}){flags}{ptn}{tag}"]
        for p in self.pokemon:
            lines.append(str(p))
        return "\n".join(lines)


def iv_tuple(ivs: dict[str, int]) -> tuple[int, int, int, int, int, int]:
    """Expand a sparse calc IV dict into a full 6-tuple, defaulting missing stats to 31."""
    return tuple(ivs.get(k, DEFAULT_IV) for k in IV_KEY_ORDER)  # type: ignore[return-value]


def extract_setdex(js_text: str) -> dict:
    """Parse `var SETDEX_SS = { ... };` into a Python dict.

    The blob is almost-JSON: it has trailing commas (`{...,}`) and stray whitespace
    after numbers (`"level":12 `). We strip the JS wrapper and trailing commas, then
    json.loads the remainder.
    """
    # Non-greedy up to the first `};` that ends a line: the top-level statement
    # terminator. Inner objects end with `,`/`}`, never `;`, so this stops at the
    # real end of SETDEX_SS even when later `var ...` statements follow in the file.
    m = re.search(r"=\s*(\{.*?\})\s*;\s*$", js_text, re.DOTALL | re.MULTILINE)
    if m is None:
        raise ValueError("could not locate SETDEX object assignment")
    body = m.group(1)
    body = re.sub(r",(\s*[}\]])", r"\1", body)  # drop trailing commas
    # JS tolerates unknown escapes (e.g. "King\s Shield" -> "Kings Shield"); JSON does
    # not. Drop any backslash not introducing a valid JSON escape, matching JS behavior.
    body = re.sub(r'\\(?!["\\/bfnrtu])', "", body)
    return json.loads(body)


def build_calc_trainers(setdex: dict) -> list[tuple[str, list[Pokemon]]]:
    """Invert species->trainer->set into [(calc_name, [Pokemon ordered by index])].

    Same-species duplicates on one trainer are disambiguated in the calc by leading
    spaces in the trainer key; we strip them so all of a trainer's mons group together.
    """
    grouped: dict[str, list[tuple[int, Pokemon]]] = {}
    for species, trainers in setdex.items():
        for raw_name, s in trainers.items():
            name = raw_name.strip()
            mon = Pokemon(
                name=species,
                level=int(s["level"]),
                item=s.get("item") or None,
                moves=list(s.get("moves", [])),
                nature=s["nature"],
                ability=s["ability"],
                ivs={k: int(v) for k, v in s.get("ivs", {}).items()},
            )
            grouped.setdefault(name, []).append((int(s["index"]), mon))

    result: list[tuple[str, list[Pokemon]]] = []
    for name, entries in grouped.items():
        entries.sort(key=lambda e: e[0])
        result.append((name, [mon for _idx, mon in entries]))
    return result


_TAG_RE = re.compile(r"\[([^\]]*)\]")


def parse_old_name(name: str) -> tuple[str, bool, bool, Optional[str]]:
    """Split an old pickle name into (clean_name, boss, double, partner).

    Old names embed R&B annotations: `[Boss]`, `[Double]`, `[Double Battle With <X>]`.
    The clean name (tags stripped) is the OCR-correct '<class> <name>' the game shows.
    """
    tags = _TAG_RE.findall(name)
    clean = re.sub(r"\s+", " ", _TAG_RE.sub("", name)).strip()
    boss = any(t == "Boss" for t in tags)
    double = any(t.startswith("Double") for t in tags)
    partner = None
    for t in tags:
        m = re.match(r"Double Battle With (.+)", t)
        if m:
            partner = m.group(1).strip()
    return clean, boss, double, partner


def _norm_loc(s: str) -> str:
    """Normalize a route/location string for fuzzy comparison: lowercase, strip
    punctuation and parentheticals, expand calc abbreviations, drop weather suffixes."""
    s = s.lower()
    s = re.sub(r"\(.*?\)", " ", s)               # drop parentheticals like "(South)"
    s = re.split(r",|permanent", s)[0]            # drop ", permanent Rain" etc.
    s = re.sub(r"[^a-z0-9 ]", " ", s)             # strip punctuation (Mt. -> mt)
    s = re.sub(r"\s+", " ", s).strip()
    repl = {"vr": "victory road", "inst": "institute"}
    return " ".join(repl.get(tok, tok) for tok in s.split())


def _loc_match(location: str, route: str) -> bool:
    """True if a calc name's trailing location agrees with an old route (lenient)."""
    a, b = _norm_loc(location), _norm_loc(route)
    if not a:
        return True                               # calc name had no location suffix
    if a in b or b in a:
        return True
    return bool(set(a.split()) & set(b.split()))   # any shared word


def _trailing_ordinal(text: str) -> int:
    """Extract a calc grunt's '#N' ordinal (e.g. 'Aqua Hideout #3' -> 3); 0 if none."""
    m = re.search(r"#\s*(\d+)", text)
    return int(m.group(1)) if m else 0


def _canon_tokens(s: str) -> list[str]:
    """Lowercase token list with `&`/`and` joiners unified (handles unspaced `A&B`)."""
    s = re.sub(r"\s*(?:&|\band\b)\s*", " & ", s, flags=re.IGNORECASE)
    return s.lower().split()


def _split_calc_name(
    calc_name: str, clean_index: list[tuple[str, list[str]]]
) -> tuple[Optional[str], str]:
    """Identify which clean trainer name heads a calc key, returning (clean, remainder).

    Longest token-prefix match against old clean names, after peeling a trailing
    'Double' and trying the prefixes the calc drops ('Pokemon ' for Trainer/Breeder/
    Ranger, 'Team ' for grunts). `&`/`And` joiners are unified. remainder = location tail.
    """
    base = calc_name
    if base.endswith("Double"):
        base = base[: -len("Double")].rstrip()
    candidates = [base, "Pokemon " + base, "Team " + base]

    best: tuple[Optional[str], str] = (None, "")
    best_len = 0
    for cand in candidates:
        ctoks = _canon_tokens(cand)
        raw = cand.split()
        for clean, ntoks in clean_index:
            n = len(ntoks)
            if n > len(ctoks) or n <= best_len:
                continue
            if ctoks[:n] == ntoks:
                best_len = n
                best = (clean, " ".join(raw[n:]))
    return best


def enrich_trainers(
    old: list[Trainer],
    calc_trainers: list[tuple[str, list[Pokemon]]],
) -> tuple[list[Trainer], list[str], list[int]]:
    """Overlay calc Pokemon/IVs onto the ordered old roster, preserving indices.

    Each old entry's name is cleaned and its boss/double/partner flags set from the old
    tags. Calc teams are matched onto a distinct old entry by longest-name-prefix, then
    route-disambiguated, then claimed in '#N' order so numbered duplicates align with the
    old list order. Returns (enriched_roster, unmatched_calc_names, unenriched_old_indices).
    """
    enriched = [
        Trainer(name=(p := parse_old_name(t.name))[0], route=t.route,
                pokemon=list(t.pokemon), boss=p[1], double=p[2], partner=p[3])
        for t in old
    ]

    # Group old positions by clean name, preserving list order.
    by_clean: dict[str, list[int]] = {}
    for i, t in enumerate(enriched):
        by_clean.setdefault(t.name, []).append(i)
    clean_index = [(c, _canon_tokens(c)) for c in by_clean]
    claimed: set[int] = set()

    # Resolve each calc trainer to (clean, location, ordinal), then assign #N in order.
    resolved = []
    unmatched: list[str] = []
    for calc_name, mons in calc_trainers:
        clean, remainder = _split_calc_name(calc_name, clean_index)
        if clean is None:
            unmatched.append(calc_name)
            continue
        resolved.append((clean, remainder, _trailing_ordinal(remainder), calc_name, mons))
    resolved.sort(key=lambda r: (r[0], r[2]))  # group by trainer, ascending ordinal

    for clean, remainder, _ord, calc_name, mons in resolved:
        pool = [i for i in by_clean.get(clean, []) if i not in claimed]
        if not pool:
            unmatched.append(calc_name)
            continue
        # Drop any partner tail ("& <partner>") so it isn't mistaken for a location.
        loc_part = re.split(r"\s*(?:&|\band\b)\s*", remainder, maxsplit=1, flags=re.IGNORECASE)[0]
        located = [i for i in pool if _loc_match(loc_part, enriched[i].route)]
        # If the calc name carries a real location word, only claim a route-matching old
        # slot — never steal another location's slot (which would mis-assign teams).
        has_location = any(not tok.isdigit() for tok in _norm_loc(loc_part).split())
        if has_location and not located:
            unmatched.append(calc_name)
            continue
        idx = (located or pool)[0]
        claimed.add(idx)
        enriched[idx].pokemon = mons

    unenriched = [i for i in range(len(enriched)) if i not in claimed]
    return enriched, unmatched, unenriched


def _parse_text_pokemon_line(line: str) -> Pokemon:
    bracket_match = re.search(r'\[([^|]+)\|([^\]]+)\]$', line.strip())
    if bracket_match is None:
        raise ValueError(f"malformed pokemon line: {line!r}")
    nature = bracket_match.group(1).strip()
    ability = bracket_match.group(2).strip()
    without_bracket = line[:bracket_match.start()].strip()
    lv_match = re.match(r'^(.+?)\s+Lv\.(\d+)', without_bracket)
    if lv_match is None:
        raise ValueError(f"malformed pokemon line: {line!r}")
    name = lv_match.group(1).strip()
    level = int(lv_match.group(2))
    rest = without_bracket[lv_match.end():].strip()
    item: Optional[str] = None
    if rest.startswith('@'):
        colon_idx = rest.index(':')
        item = rest[1:colon_idx].strip()
        rest = rest[colon_idx + 1:].strip()
    moves = [m.strip() for m in rest.split(',') if m.strip()] if rest else []
    return Pokemon(name=name, level=level, item=item, moves=moves, nature=nature, ability=ability)


def parse_trainers_from_text(path: str) -> list[Trainer]:
    """Parse the original 'Trainer Battles.txt' into ordered Trainer objects.

    This is the authoritative source for canonical ordering (play.py walks trainers by
    position, incrementing as the run progresses), OCR names, and double/boss structure.
    The calc supplies per-mon IVs on top via enrich_trainers.

    Doubles come in two text shapes, with different in-game mechanics:
    - "<lead> [Double Battle With <ally>]" then the lead's mons, a "~" line, then the
      partner's mons. These become TWO trainers, listed in game order, cross-referencing
      via `partner` (an index) with `double=True`.
    - "<name> [Double]" with a single mon list (e.g. a couple). One trainer, `double=True`,
      `partner=None`.
    """
    trainers: list[Trainer] = []
    current_route = "Unknown"
    current_trainer: Optional[Trainer] = None
    pending_route: Optional[str] = None
    in_separator = False
    pending_partner_name: Optional[str] = None  # ally name awaiting its "~" mon block
    lead_idx: Optional[int] = None              # list index of the lead in a "~" double
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if stripped == "------":
            if not in_separator:
                in_separator = True
                pending_route = None
            else:
                in_separator = False
                if pending_route is not None:
                    current_route = pending_route
                    pending_route = None
            current_trainer = None
            continue
        if in_separator:
            pending_route = stripped
            continue
        if not stripped or stripped.startswith("- "):
            continue
        if stripped == "~":
            # Switch from the lead's mon block to the ally's; the ally becomes its own
            # trainer, cross-linked to the lead via `partner`.
            if pending_partner_name is None or lead_idx is None:
                raise ValueError(f"'~' separator with no pending [Double Battle With ...] lead")
            ally_idx = len(trainers)
            trainers[lead_idx].partner = ally_idx
            ally = Trainer(name=pending_partner_name, route=current_route,
                           double=True, partner=lead_idx)
            trainers.append(ally)
            current_trainer = ally
            pending_partner_name = None
            lead_idx = None
            continue
        if "Lv." in line:
            if current_trainer is not None:
                current_trainer.pokemon.append(_parse_text_pokemon_line(line))
        else:
            clean, boss, double, partner_name = parse_old_name(stripped)
            current_trainer = Trainer(name=clean, route=current_route, boss=boss, double=double)
            lead_idx = len(trainers)
            trainers.append(current_trainer)
            pending_partner_name = partner_name  # set only for "[Double Battle With X]"
    return trainers


def parse_trainers_from_calc(
    js_path: str, old: list[Trainer]
) -> tuple[list[Trainer], list[str], list[int]]:
    """Full pipeline: read the calc sets file and enrich the old roster in place."""
    js_text = Path(js_path).read_text(encoding="utf-8")
    setdex = extract_setdex(js_text)
    calc_trainers = build_calc_trainers(setdex)
    return enrich_trainers(old, calc_trainers)


def load_trainers() -> list[Trainer]:
    """Load trainers from the pre-built pickle. Run scripts/parse_trainers.py to regenerate."""
    with open(TRAINERS_PICKLE, "rb") as f:
        return pickle.load(f)
