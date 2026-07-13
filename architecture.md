# NuzlockeAI Architecture

**Goal:** Real-time battle AI for Pokémon Run & Bun (Emerald hack) running in mGBA; OCRs the emulator screen to track battle state. This repo holds the C++ engine and the Python live-play layer; the Stage E sweep re-point is complete.

**Layout:** `engine/` = C++ engine (CMake, pybind11 module `nuzlocke_engine_cpp`, Catch2 native tests); `liveplay/` = Python live-play package; `tests/`, `SCRIPTS/`, `RECORDS/` at top level.

**Entry point:** `SCRIPTS/play.py` — event loop capturing screenshots at 25Hz (0.04s), matching OCR text to battle messages. Decisions come from an injectable `liveplay/battle_policy.py` policy; `liveplay/emulator/battle_input.py` translates them into key presses.

**OCR pipeline:** `liveplay/vision/` — captures screen regions, reads text by strict pixel-template matching against pokeemerald font bitmaps (`font_matcher.py`), and reads HP bars pixel-by-pixel.

**Message matching:** `liveplay/battle_message_matcher.py` — raw-text stability filter (≥2 identical frames) then fuzzy DP template matching against GBA string IDs; `battle_constants.py` lists primary (action-starting) IDs.

**HP stability:** `liveplay/hp_stability.py` — `StabilityBuffer` requires 3 consecutive identical readings; player HP is exact int, opponent HP is k-pixel (0–48) with `hp_range()` error bounds.

**State:** `liveplay/state/` — flat, hashable, copy-on-write dataclasses (`battle.py`, `side.py`, `pokemon.py`) supporting candidate deduplication.

**Data layer:** `liveplay/data/` — static lookup tables for species, moves, natures, abilities, items, types, status, growth rates.

**C++ engine (`engine/`):** pure-C++ port of the battle engine + Run & Bun opponent AI; `nuzlocke_core` static library + thin pybind11 module. `cpp_run_game` runs full singles games with per-side policies ("random"/"ai"); `GameDriver` (`game_driver.cpp`) is a resumable turn loop that pauses on Category-A oracle events (`oracle.h`) for search and forced trace replay.

**Regression gates:** C++ self-regression manifest — committed 2k subset `tests/fixtures/cpp_manifest/` + git-ignored 1M corpus `cpp_manifest_1m/` (mixed ai/random self-play; `SCRIPTS/record_cpp_manifest.py` records and verifies seed→final-state/fingerprint). 28 hand-authored `scenario_*` traces in `tests/fixtures/golden_traces/` still replay via `GameDriver` forced replay (`SCRIPTS/replay_golden_traces.py`).

**Stage E seam:** `liveplay/engine_select.py` — `enumerate_legal_actions`, `compute_action_probabilities`, and `run_candidate_sweep` are all live (C++-backed); sweep orchestration lives in `liveplay/sweep_*.py` over `liveplay/sweep_driver.py` (per-trial C++ turn driver via `cpp_driver.run_one_turn_cpp`/`apply_switch_cpp`). The old repo (`PycharmProjects/NuzlockeAI`) is retired (2026-07-11) — frozen in place as a read-only archive; see `RECORDS/C++Transition.md`.

**Solver (phase 1):** `engine/src/solver/` — `nuzlocke_solver` static lib (one-way dep on core): exact 1v1 transition oracle (`transition_oracle.cpp`, DFS prefix-replay over Cat-B injection + Cat-A overrides), state codec, Question classifier, action space, matchup generator. Audit/bench tools: `audit_oracle` (selfcheck/mc), `solver_trace`, `bench_oracle` (all EXCLUDE_FROM_ALL).

**Stress test:** `SCRIPTS/stress_test.py` — loops battles from `States/` savestates, 100% `RandomPolicy`, logs to `/tmp/vision/stress/`.
