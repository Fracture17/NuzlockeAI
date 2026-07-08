# One-shot Stage C seeding of the requirements.md record store from the old repo.
# Full carry (no records dropped): scopes are remapped mechanically to the new layout;
# records for code still living in the old repo (sweep, Python engine, ai, nn, search)
# keep their original src/ paths until the Stage E re-point re-scopes them.
import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

OLD_ROOT = Path("/home/Fracture/PycharmProjects/NuzlockeAI")
NEW_ROOT = Path("/home/Fracture/CLionProjects/NuzlockeAI")
FIELDS = ("name", "file", "confidence", "rationale", "updated")


def _esc(v: str) -> str:
    return v.replace("\\", "\\\\").replace('"', '\\"')


def serialize(records: list[dict]) -> str:
    out = []
    for r in records:
        lines = ["[[record]]"]
        for f in FIELDS:
            lines.append(f'{f} = "{_esc(str(r.get(f, "")))}"')
        out.append("\n".join(lines))
    return "\n\n".join(out) + "\n"


def remap(fileval: str) -> str:
    if fileval == "" or fileval.startswith(("tests/", "SCRIPTS/")):
        return fileval
    if fileval.startswith("cpp/") or fileval == "cpp/":
        return "engine/" + fileval[len("cpp/"):]
    if fileval == "src/engine/actions.py":
        return "liveplay/actions.py"
    if fileval.startswith("src/"):
        candidate = "liveplay/" + fileval[len("src/"):]
        target = NEW_ROOT / candidate.rstrip("/")
        if target.exists():
            return candidate
    return fileval  # old-repo resident until Stage E


def main() -> None:
    with open(OLD_ROOT / "requirements.md", "rb") as f:
        records = tomllib.load(f)["record"]
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    stats = {"moved": 0, "kept_old_path": 0, "unchanged": 0}
    for r in records:
        old = r["file"]
        new = remap(old)
        if new != old:
            stats["moved"] += 1
        elif old.startswith(("src/", "cpp/")):
            stats["kept_old_path"] += 1
        else:
            stats["unchanged"] += 1
        r["file"] = new

        if r["name"] == "capture_interval_10fps":
            r["name"] = "capture_interval_25hz"
            r["rationale"] = (
                "Capture runs at 25Hz (0.04s interval); user ruled 2026-07 the code is "
                "correct and the old 10fps record was stale. Stability filter deduplicates "
                "repeated frames so template matching only runs on newly stable text."
            )
            r["updated"] = now
        elif r["name"] == "run_one_turn_state_only":
            r["rationale"] = (
                "SUPERSEDED by C++ GameDriver orchestration (C1.7h): cpp_run_one_turn "
                "returned only the mutated BattleState with winner/done/phase computed in "
                "Python; orchestrate.cpp/game_driver.cpp now own the game loop and outcome."
            )
            r["updated"] = now

    dest = NEW_ROOT / "requirements.md"
    if dest.exists():
        sys.exit(f"refusing to overwrite existing {dest}")
    dest.write_text(serialize(records), encoding="utf-8")
    print(f"wrote {len(records)} records to {dest}")
    print(stats)
    dangling = sorted({r["file"] for r in records if not (NEW_ROOT / r["file"].rstrip("/")).exists() and r["file"]})
    print(f"{len(dangling)} scopes not present in new repo (Stage E residents):")
    for d in dangling:
        print(f"  {d}")


if __name__ == "__main__":
    main()
