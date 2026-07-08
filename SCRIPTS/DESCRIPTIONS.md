# Scripts

Documented scripts in the new NuzlockeAI repo.

- [build_cpp.py](build_cpp.py) — Configures and builds the nuzlocke_engine_cpp pybind11 extension via CMake (engine/build/) then installs the .so into the venv site-packages. Re-runnable/idempotent; exits non-zero on any failure.
- [play.py](play.py) — Launch mGBA with `--config States/<folder>/config.json`; L toggles capture, O inits battle, M saves current state to a new States/ subfolder (prompts for name), K pickles the live BattleState to CurrentBattle.pkl. Battle decisions come from RandomPolicy.
- [stress_test.py](stress_test.py) — Runs battles in a loop, picking a random state subfolder from States/ (config.json holds opponent_index and level_cap). Each battle is driven by 100% RandomPolicy. Logs to /tmp/vision/stress/.
- [replay_sweep.py](replay_sweep.py) — Replays recorded sweep boundary sessions from /tmp/vision/recordings/ through the live engine; reports per-boundary PASS/FAIL with state diffs. Supports single-boundary selection, failing-only filter, and verbose diff output.
- [debug_sweep.py](debug_sweep.py) — Auto-plays a battle with a specified per-turn move sequence (--moves SLOT ...) and logs all sweep diagnostics to /tmp/vision/debug_sweep.log for post-run analysis.
- [_shared.py](_shared.py) — Shared helpers for operational SCRIPTS/: `_Tee` (multi-stream stdout/file tee) and `_kill_existing_mgba` (pkill mGBA-qt). Imported by play.py, debug_sweep.py, and stress_test.py.
- [mGBASocketServer.lua](mGBASocketServer.lua) — Lua TCP socket server loaded by mGBA at launch; accepts commands from Python over localhost:8888. L=toggle_capture, O=init_battle, M=save_state events; savestate/loadstate commands.
- [vision_check.py](vision_check.py) — Captures all 4 battle screen regions from a live mGBA window and saves PNGs to /tmp/vision for visual calibration of region coords.
- [ocr_check.py](ocr_check.py) — Loads the 4 crop PNGs from /tmp/vision/ and prints OCR results for each region. Run after crop_check.py.
- [crop_check.py](crop_check.py) — Opens /tmp/vision/frame.png and saves the 4 cropped regions to /tmp/vision/ for calibrating regions.py.
