#!/usr/bin/env python3
"""Compute measured wave-unlock counts from audit_analytic mask-combo output.

A candidate wave clearing scope-bit-set W fully unlocks exactly the matchups
whose scope mask is a subset of W (mask & ~W == 0). Per-bit histograms cannot
give this (reasons co-occur), so this consumes the exact combination histogram.

Usage:
    ./engine/build/audit_analytic --klass sash --n 20000 --mode fast \
        --combo-top 10000 | python3 SCRIPTS/wave_unlock.py [--waves w1,w2 ...]

Waves are comma-separated bit names (see BITS). Default: a ladder of the
plan's candidate lemma waves. Reads stdin; prints unlock count per wave.
"""
import re
import sys

BITS = {
    "MULTI_HIT": 0, "ACCURACY_LT100": 1, "SECONDARY": 2, "RECOIL": 3,
    "DRAIN": 4, "BINDING": 5, "CHARGE_TURN": 6, "PRIORITY": 7,
    "HP_DEP_BP": 8, "WEATHER_SCREEN": 9, "ENTRY_DIRTY": 10,
    "ITEM_NOT_ALLOWED": 11, "OPP_NO_DAMAGE": 12, "NONDEFAULT_QUESTION": 13,
    "RESIDUAL_UNKNOWN": 14,
}

DEFAULT_WAVES = [
    "SECONDARY",
    "ACCURACY_LT100",
    "SECONDARY,ACCURACY_LT100",
    "SECONDARY,HP_DEP_BP",
    "SECONDARY,ACCURACY_LT100,HP_DEP_BP",
    "SECONDARY,ACCURACY_LT100,PRIORITY",
    "SECONDARY,ACCURACY_LT100,HP_DEP_BP,PRIORITY",
    "SECONDARY,ACCURACY_LT100,HP_DEP_BP,PRIORITY,RESIDUAL_UNKNOWN",
]

LINE_RE = re.compile(r"^\s*0x([0-9a-fA-F]+)\s*:\s*(\d+)\b")


def wave_mask(spec: str) -> int:
    mask = 0
    for name in spec.split(","):
        name = name.strip().upper()
        if name not in BITS:
            raise SystemExit(f"unknown scope bit name: {name!r}")
        mask |= 1 << BITS[name]
    return mask


def main() -> None:
    waves = DEFAULT_WAVES
    if "--waves" in sys.argv:
        waves = sys.argv[sys.argv.index("--waves") + 1:]
        if not waves:
            raise SystemExit("--waves requires at least one wave spec")

    combos: dict[int, int] = {}
    scanned = None
    total_listed = None
    for line in sys.stdin:
        m = LINE_RE.match(line)
        if m:
            combos[int(m.group(1), 16)] = int(m.group(2))
            continue
        sm = re.match(r"^scanned\s*:\s*(\d+)", line.strip())
        if sm:
            scanned = int(sm.group(1))
        tm = re.search(r"top (\d+) of (\d+) combos", line)
        if tm and int(tm.group(1)) < int(tm.group(2)):
            total_listed = (int(tm.group(1)), int(tm.group(2)))

    if not combos:
        raise SystemExit("no mask-combo lines found on stdin "
                         "(pipe full audit_analytic output, use --combo-top 10000)")
    if total_listed:
        raise SystemExit(f"combo list truncated ({total_listed[0]} of "
                         f"{total_listed[1]}); rerun with a larger --combo-top")

    blocked = sum(combos.values())
    print(f"combos={len(combos)} blocked_matchups={blocked}"
          + (f" scanned={scanned}" if scanned else ""))
    print(f"{'wave (bits cleared)':60s} {'unlocked':>8s}  {'% blocked':>9s}")
    for spec in waves:
        w = wave_mask(spec)
        unlocked = sum(c for m, c in combos.items() if (m & ~w) == 0)
        pct = 100.0 * unlocked / blocked if blocked else 0.0
        print(f"{spec:60s} {unlocked:8d}  {pct:8.2f}%")


if __name__ == "__main__":
    main()
