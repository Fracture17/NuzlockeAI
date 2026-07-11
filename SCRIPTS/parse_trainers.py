"""Rebuild liveplay/data/trainers.pkl by enriching the roster with R&B calc data.

Ported from the old repo's scripts/parse_trainers.py (Stage E).

WARNING (2026-07-11): running this against the CURRENT Downloads calc/text sources
produces output INCOMPATIBLE with the canonical committed pickle: calc-style names
("Vise Grip", "Farfetch'd-Galar", "Power-Up Punch") that fail play.py's enum lookups,
merged double-battle partner teams (3 mons -> 6), and changed abilities. The canonical
pickle is the 2026-06-07 roster re-dumped under liveplay module paths — an earlier
pipeline/source produced it with enum-friendly names and per-trainer teams. Do NOT
overwrite it unless the name-normalization gap is fixed; hence the --force gate below.

The calc (syl-rnb-calc) carries per-mon IVs and richer teams the text-file source
lacked, but the text file defines the canonical *ordering* (play.py selects trainers by
opponent_idx) and the OCR-correct names. So we keep every text entry in place, clean its
name + set boss/double/partner flags from the [..] tags, and overlay the calc team
(with IVs) onto the matching entry. Trainers the calc lacks (e.g. the 3 early May fights)
keep their existing teams. Unmatched calc trainers and un-enriched entries are printed
for manual review rather than silently dropped.
"""
import os
import pickle
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from liveplay.data.trainer import (
    TRAINERS_PICKLE,
    parse_trainers_from_text,
    parse_trainers_from_calc,
)

CALC_SETS_PATH = "/home/Fracture/Downloads/syl-rnb-calc-main/src/js/data/sets/gen8.js"
TEXT_REF_PATH = "/home/Fracture/Downloads/Pokémon Run & Bun/Trainer Battles.txt"

if __name__ == "__main__":
    if "--force" not in sys.argv:
        sys.exit(
            "REFUSING to overwrite the canonical trainers.pkl: current calc/text sources "
            "produce incompatible output (see module docstring). Pass --force to override."
        )
    # Reference (canonical order + OCR names + [Boss]/[Double] tags) comes from the text
    # file, NOT trainers.pkl, so re-running never clobbers its own input.
    old = parse_trainers_from_text(TEXT_REF_PATH)
    print(f"Parsed {len(old)} reference trainers from text (ordering + OCR names).")

    trainers, unmatched_calc, unenriched = parse_trainers_from_calc(CALC_SETS_PATH, old)

    if unmatched_calc:
        print(f"\n!! {len(unmatched_calc)} calc trainer(s) matched no old entry:")
        for n in sorted(unmatched_calc):
            print(f"   - {n}")
    if unenriched:
        print(f"\n!! {len(unenriched)} old entr(ies) received no calc team (kept as-is):")
        for i in unenriched:
            print(f"   - [{i}] {trainers[i].name}  ({trainers[i].route})")

    with open(TRAINERS_PICKLE, "wb") as f:
        pickle.dump(trainers, f)
    n_mons = sum(len(t.pokemon) for t in trainers)
    n_iv = sum(1 for t in trainers for p in t.pokemon if p.ivs)
    n_boss = sum(1 for t in trainers if t.boss)
    n_dbl = sum(1 for t in trainers if t.double)
    print(
        f"\nSaved {len(trainers)} trainers ({n_mons} Pokemon, {n_iv} with non-default IVs, "
        f"{n_boss} boss, {n_dbl} double) to {TRAINERS_PICKLE}"
    )
