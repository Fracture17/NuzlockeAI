# Scripts

Documented scripts in the new NuzlockeAI repo.

- [build_cpp.py](build_cpp.py) — Configures and builds the nuzlocke_engine_cpp pybind11 extension via CMake (engine/build/) then installs the .so into the venv site-packages. Re-runnable/idempotent; exits non-zero on any failure.
- [replay_golden_traces.py](replay_golden_traces.py) — Replays golden-trace .jsonl.gz files through C++ GameDriver forced replay, asserting winner/turn/fingerprint identity. `--dir` selects corpus, `--jobs 0` = all cores; exit 1 on any divergence.
- [gen_cpp_data.py](gen_cpp_data.py) — Regenerates deterministic C++ data-table headers in engine/generated/ from liveplay/data/*. `--check` verifies committed headers are not stale (exit non-zero on drift). AI move-set header still imports src.ai from the old repo until Stage E.
- [_naming.py](_naming.py) — Shared name-normalization helpers (display name → Python identifier) for data-generation scripts.
- [migrate_records.py](migrate_records.py) — One-shot Stage C seeding of requirements.md from the old repo: full 296-record carry with mechanical scope remap (cpp/→engine/, src/→liveplay/ where moved) plus the capture_interval and run_one_turn_state_only fixes.
- [play.py](play.py) — Launch mGBA with `--config States/<folder>/config.json`; L toggles capture, O inits battle, M saves current state to a new States/ subfolder (prompts for name), K pickles the live BattleState to CurrentBattle.pkl. Battle decisions come from RandomPolicy.
- [stress_test.py](stress_test.py) — Runs battles in a loop, picking a random state subfolder from States/ (config.json holds opponent_index and level_cap). Each battle is driven by 100% RandomPolicy. Logs to /tmp/vision/stress/.
- [replay_sweep.py](replay_sweep.py) — Replays recorded sweep boundary sessions from /tmp/vision/recordings/ through the live engine; reports per-boundary PASS/FAIL with state diffs. Supports single-boundary selection, failing-only filter, and verbose diff output.
- [debug_sweep.py](debug_sweep.py) — Auto-plays a battle with a specified per-turn move sequence (--moves SLOT ...) and logs all sweep diagnostics to /tmp/vision/debug_sweep.log for post-run analysis.
- [_shared.py](_shared.py) — Shared helpers for operational SCRIPTS/: `_Tee` (multi-stream stdout/file tee) and `_kill_existing_mgba` (pkill mGBA-qt). Imported by play.py, debug_sweep.py, and stress_test.py.
- [mGBASocketServer.lua](mGBASocketServer.lua) — Lua TCP socket server loaded by mGBA at launch; accepts commands from Python over localhost:8888. L=toggle_capture, O=init_battle, M=save_state events; savestate/loadstate commands.
- [vision_check.py](vision_check.py) — Captures all 4 battle screen regions from a live mGBA window and saves PNGs to /tmp/vision for visual calibration of region coords.
- [ocr_check.py](ocr_check.py) — Loads the 4 crop PNGs from /tmp/vision/ and prints OCR results for each region. Run after crop_check.py.
- [crop_check.py](crop_check.py) — Opens /tmp/vision/frame.png and saves the 4 cropped regions to /tmp/vision/ for calibrating regions.py.
- [gen_seam_payload.py](gen_seam_payload.py) — Extracts a golden-trace initial_state into /tmp/d5_seam_payload.json for the native D5 seam benchmark (engine/build/nuzlocke_bench_seam). `--trace`/`--out` override the fixed default trace/path.
- [parse_trainers.py](parse_trainers.py) — Rebuilds liveplay/data/trainers.pkl from the R&B text roster + syl-rnb-calc sets. --force gated: current sources produce output incompatible with the canonical 2026-06-07 pickle (see docstring).
- [record_cpp_manifest.py](record_cpp_manifest.py) — Generates a C++ self-regression manifest: plays N deterministic games via make_random_battle + cpp.run_game, storing winner/fingerprint/final_state per entry as gzipped JSONL shards. Supersedes Python-era golden traces; exposes run_one/verify_entry for gate-test reuse.
- [dbg_oracle_mc_hole.cpp](dbg_oracle_mc_hole.cpp) — Standalone C++ repro template for diagnosing audit-mc completeness holes: re-runs one (matchup, sample_seed) with the analytical RNG log attached and diffs the sampled child against oracle support. Edit the hardcoded matchup/seed, compile against engine/build/lib*.a (see file header).
