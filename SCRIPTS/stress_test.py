"""
Stress-test the battle capture pipeline by running many battles in sequence.

Randomly picks a save state from --states-dir each run, launches a fresh mGBA
instance, loads the state, auto-initialises the battle, then plays it out with
a random move slot each turn.  Loops until Ctrl+C.

Outcomes per run: OK | STUCK | ERRORS | TIMEOUT | CRASHED
Per-run logs: /tmp/vision/stress/run_NNNN_<state>_<timestamp>.log
Summary line printed to stdout after every run.

Usage:
    python SCRIPTS/stress_test.py [--states-dir PATH] [--timeout SECS]

    --states-dir: Directory containing state subfolders, each with a config.json
                  and one *.ss* save state file.
                  Default: States/ (project root).
    --timeout:    Per-battle hard timeout in seconds. Default: 600.
"""
import argparse
import json
import random
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from _shared import _Tee, _kill_existing_mgba  # noqa: E402

import play as _play_module  # noqa: E402
from play import (  # noqa: E402
    _do_capture,
    _build_battle_state,
    _make_stub_battle_state,
    _CAPTURE_INTERVAL,
    _B_PRESS_INTERVAL,
)

from liveplay.emulator import MGBAProcess, MGBAConnectionError  # noqa: E402
from liveplay.emulator.battle_input import _press, handle_battle_screen  # noqa: E402
from liveplay.battle_policy import RandomPolicy  # noqa: E402
from liveplay.battle_message_matcher import BattleMessageMatcher, ScreenKind  # noqa: E402
from liveplay.battle_types import Constraints  # noqa: E402
from liveplay.candidate import Candidate  # noqa: E402
from liveplay.candidate_tracker import CandidateTracker  # noqa: E402
from liveplay.sweep_recorder import SweepRecorder  # noqa: E402

_STRESS_DIR = Path("/tmp/vision/stress")
_ERROR_DIR = Path("/tmp/vision/sweep_errors")

_STUCK_THRESHOLD = 10.0   # seconds of identical OCR text → stuck


def _make_policy(rng: random.Random):
    """Return a RandomPolicy for this battle.

    Returns (policy, mode_label). The label is printed once per battle.
    """
    return RandomPolicy(rng), "RANDOM"


class _StuckTracker:
    """Detects a hung screen: identical OCR text persisting past `threshold`
    seconds. Policy/search compute time must be excluded — the capture loop is
    single-threaded, so a slow policy decision (e.g. a future search-based
    policy) blocks captures and would otherwise look like a frozen screen.
    Call `note_decision` right after a decision so the decision duration
    doesn't count toward the stuck threshold.
    """
    def __init__(self, threshold: float, now: float):
        self.threshold = threshold
        self.last_text = ""
        self.last_change_time = now

    def observe(self, now: float, text: str) -> bool:
        """Record an OCR sample; return True once the screen has been stuck."""
        if text != self.last_text:
            self.last_text = text
            self.last_change_time = now
            return False
        return now - self.last_change_time > self.threshold

    def note_decision(self, now: float) -> None:
        """Reset the stuck clock after a (possibly slow) policy decision."""
        self.last_change_time = now


_TOP_RIGHT_X = 2561
_TOP_RIGHT_Y = 0


def _start_minimize_watcher() -> None:
    import subprocess as _sp
    import threading

    def _wids_by_class() -> set[str]:
        try:
            r = _sp.run(["xdotool", "search", "--class", "mGBA"],
                        capture_output=True, text=True, timeout=3)
            return {w.strip() for w in r.stdout.strip().splitlines() if w.strip()}
        except Exception:
            return set()

    def _window_name(wid: str) -> str:
        try:
            r = _sp.run(["xdotool", "getwindowname", wid],
                        capture_output=True, text=True, timeout=3)
            return r.stdout.strip()
        except Exception:
            return ""

    def _watch() -> None:
        arranged: set[str] = set()
        scripting_done = False
        game_done = False
        deadline = time.time() + 15.0
        while time.time() < deadline and not (scripting_done and game_done):
            for wid in _wids_by_class() - arranged:
                name = _window_name(wid)
                if not name:
                    continue
                if name == "Scripting":
                    try:
                        _sp.run(["xdotool", "windowminimize", wid],
                                capture_output=True, timeout=3)
                        arranged.add(wid)
                        scripting_done = True
                        print(f"[stress] Minimized Scripting console {wid}.", flush=True)
                    except Exception as exc:
                        print(f"[stress] windowminimize {wid} failed: {exc}", flush=True)
                elif "mGBA" in name:
                    try:
                        _sp.run(["xdotool", "windowmove", wid,
                                 str(_TOP_RIGHT_X), str(_TOP_RIGHT_Y)],
                                capture_output=True, timeout=3)
                        arranged.add(wid)
                        game_done = True
                        print(f"[stress] Moved game window {wid} to top-right.", flush=True)
                    except Exception as exc:
                        print(f"[stress] windowmove {wid} failed: {exc}", flush=True)
            time.sleep(0.05)

    threading.Thread(target=_watch, daemon=True).start()


def _run_one_battle(state_path: Path, opponent_idx: int, level_cap: int, timeout: float,
                    log_path: Path) -> str:
    """
    Run a single battle from *state_path*.  Returns outcome string:
    'OK' | 'STUCK' | 'ERRORS' | 'TIMEOUT' | 'CRASHED'
    Output is tee'd to *log_path*.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("w", buffering=1)
    orig_stdout = sys.stdout
    sys.stdout = _Tee(orig_stdout, log_file)
    _play_module._verbose_log = sys.stdout  # route _vlog() calls into the Tee

    outcome = "CRASHED"
    try:
        print(f"[stress] state={state_path}", flush=True)
        print(f"[stress] opponent_idx={opponent_idx}", flush=True)
        print(f"[stress] level_cap={level_cap}", flush=True)
        print(f"[stress] timeout={timeout}s", flush=True)
        print(f"[stress] log → {log_path}", flush=True)

        _kill_existing_mgba()
        _start_minimize_watcher()

        err_count_start = len(list(_ERROR_DIR.glob("*.json"))) if _ERROR_DIR.exists() else 0

        with MGBAProcess(event_timeout=0.1) as mgba:
            from liveplay.vision.capture import ScreenCapture  # noqa

            print(f"[stress] Loading save state…", flush=True)
            mgba.socket.load_state(str(state_path))
            time.sleep(0.3)
            print(f"[stress] Save state loaded.", flush=True)

            screen_capture = ScreenCapture(mgba.socket)
            matcher = BattleMessageMatcher()
            captures: list[dict] = []
            current_turn: list[dict] = []
            last_capture_time_ref = [0.0]
            opponent_hp_bufs: dict = {}
            player_hp_bufs: dict = {}
            battle_state_ref = [_make_stub_battle_state()]
            constraints_ref = [Constraints()]
            candidate_tracker_ref = [None]
            opp_k_log_ref: list = [{}]
            player_hp_log_ref: list = [{}]
            foe_faint_deltas_ref: list = [[]]
            last_screen_kind_ref: list = [None]
            last_b_press_time_ref = [0.0]
            pending_switch_ref: list = [None]
            policy, policy_mode = _make_policy(random.Random())
            print(f"[stress] Policy: {policy_mode}", flush=True)
            turn_count = 0
            run_start = time.time()
            stuck = _StuckTracker(_STUCK_THRESHOLD, time.time())

            print(f"[stress] Auto-initialising battle (opponent_idx={opponent_idx})…", flush=True)
            battle_state_ref[0], constraints_ref[0] = _build_battle_state(
                opponent_idx, mgba.socket, level_cap
            )
            initial_candidate = Candidate(state=battle_state_ref[0])
            candidate_tracker_ref[0] = CandidateTracker([initial_candidate])
            recorder_ref = [SweepRecorder.create()]
            print(f"[recorder] Session: {recorder_ref[0].session_dir}", flush=True)
            last_capture_time_ref[0] = 0.0
            last_screen_kind_ref[0] = None
            last_b_press_time_ref[0] = 0.0
            p_mons = len(battle_state_ref[0].sides[0].team)
            o_mons = len(battle_state_ref[0].sides[1].team)
            print(f"[state] {p_mons} player mons  {o_mons} opponent mons", flush=True)

            while True:
                event = mgba.socket.recv_event()

                if event is None:
                    now = time.time()

                    if now - run_start > timeout:
                        print(f"\n[stress] Timeout ({timeout}s) reached.", flush=True)
                        outcome = "TIMEOUT"
                        break

                    if now - last_capture_time_ref[0] >= _CAPTURE_INTERVAL:
                        battle_ended, screen_kind, ocr_text = _do_capture(
                            screen_capture, matcher, captures, current_turn,
                            last_capture_time_ref, True,
                            opponent_hp_bufs=opponent_hp_bufs,
                            player_hp_bufs=player_hp_bufs,
                            candidate_tracker_ref=candidate_tracker_ref,
                            opp_k_log_ref=opp_k_log_ref,
                            player_hp_log_ref=player_hp_log_ref,
                            battle_state_ref=battle_state_ref,
                            constraints_ref=constraints_ref,
                            recorder_ref=recorder_ref,
                            foe_faint_deltas_ref=foe_faint_deltas_ref,
                        )

                        if stuck.observe(now, ocr_text):
                            print(
                                f"\n[stress] Stuck: same text for >{_STUCK_THRESHOLD}s:"
                                f" {ocr_text!r}",
                                flush=True,
                            )
                            outcome = "STUCK"
                            break

                        if battle_ended:
                            print(f"\n[stress] Battle ended — {turn_count} turns played.", flush=True)
                            err_count_now = len(list(_ERROR_DIR.glob("*.json"))) if _ERROR_DIR.exists() else 0
                            outcome = "ERRORS" if err_count_now > err_count_start else "OK"
                            break
                        elif (
                            screen_kind in (ScreenKind.OPTION_SELECT, ScreenKind.PARTY_MENU)
                            and last_screen_kind_ref[0] != screen_kind
                        ):
                            if screen_kind == ScreenKind.OPTION_SELECT:
                                turn_count += 1
                                print(f"[stress] Turn {turn_count}: deciding action", flush=True)
                            handle_battle_screen(
                                mgba.socket, screen_capture, screen_kind,
                                battle_state_ref[0], policy, pending_switch_ref,
                            )
                            # A slow policy decision (e.g. a future search-based
                            # policy) can run many seconds; exclude that compute
                            # time from the stuck clock so a slow decision isn't
                            # mistaken for a frozen screen.
                            stuck.note_decision(time.time())
                            last_screen_kind_ref[0] = screen_kind
                        else:
                            last_screen_kind_ref[0] = screen_kind

                    if last_screen_kind_ref[0] is None:
                        if time.time() - last_b_press_time_ref[0] >= _B_PRESS_INTERVAL:
                            _press(mgba.socket, "b")
                            last_b_press_time_ref[0] = time.time()

    except MGBAConnectionError as exc:
        print(f"\n[stress] mGBA closed: {exc}", flush=True)
        outcome = "CRASHED"
    except Exception:
        print(f"\n[stress] Unexpected crash:", flush=True)
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        outcome = "CRASHED"
    finally:
        sys.stdout = orig_stdout
        _play_module._verbose_log = None
        log_file.close()

    return outcome


def main() -> None:
    project_root = Path(__file__).parent.parent
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--states-dir", default=str(project_root / "States"), metavar="PATH",
        help="Directory containing state subfolders with config.json. Default: States/ (project root).",
    )
    parser.add_argument(
        "--timeout", type=int, default=1200, metavar="SECS",
        help="Per-battle hard timeout in seconds. Default: 1200.",
    )
    args = parser.parse_args()

    states_dir = Path(args.states_dir)
    state_entries: list[tuple[Path, int, int]] = []
    for subdir in sorted(states_dir.iterdir()):
        if not subdir.is_dir():
            continue
        cfg_path = subdir / "config.json"
        if not cfg_path.exists():
            raise FileNotFoundError(f"[stress] Missing config.json in {subdir}")
        with cfg_path.open() as f:
            cfg = json.load(f)
        if not isinstance(cfg.get("opponent_index"), int):
            raise ValueError(f"[stress] 'opponent_index' missing or not int in {cfg_path}")
        if not isinstance(cfg.get("level_cap"), int):
            raise ValueError(f"[stress] 'level_cap' missing or not int in {cfg_path}")
        ss_files = list(subdir.glob("*.ss*"))
        if len(ss_files) == 0:
            raise FileNotFoundError(f"[stress] No .ss* file found in {subdir}")
        if len(ss_files) > 1:
            raise ValueError(f"[stress] Multiple .ss* files in {subdir}: {ss_files}")
        state_entries.append((ss_files[0], cfg["opponent_index"], cfg["level_cap"]))

    if not state_entries:
        print(f"[stress] No state subfolders found in {states_dir}. Exiting.", flush=True)
        sys.exit(1)

    print(f"[stress] Found {len(state_entries)} state(s) in {states_dir}:", flush=True)
    for ss_path, opp_idx, lv_cap in state_entries:
        print(f"  {ss_path.parent.name}  (opponent_index={opp_idx}, level_cap={lv_cap})", flush=True)
    print(f"[stress] Timeout: {args.timeout}s per battle. Ctrl+C to stop.\n", flush=True)

    _STRESS_DIR.mkdir(parents=True, exist_ok=True)

    run_number = 0
    totals: dict[str, int] = {}

    try:
        outcome = "OK"
        while outcome == "OK":
            run_number += 1
            ss_path, opp_idx, lv_cap = random.choice(state_entries)
            ts = time.strftime("%Y%m%d_%H%M%S")
            log_name = f"run_{run_number:04d}_{ss_path.parent.name}_{ts}.log"
            log_path = _STRESS_DIR / log_name

            print(f"{'─' * 60}", flush=True)
            print(f"[stress] Run {run_number}  state={ss_path.parent.name}", flush=True)
            t0 = time.time()
            outcome = _run_one_battle(ss_path, opp_idx, lv_cap, float(args.timeout), log_path)
            elapsed = time.time() - t0
            totals[outcome] = totals.get(outcome, 0) + 1

            # Purge logs for clean battles: only failing runs are worth keeping, and a
            # successful run's log can span several encounters, which is just noise.
            if outcome == "OK":
                log_path.unlink(missing_ok=True)
                log_display = "(purged — OK)"
            else:
                log_display = log_name

            counts = "  ".join(f"{k}={v}" for k, v in sorted(totals.items()))
            print(
                f"[stress] Run {run_number} → {outcome}  ({elapsed:.1f}s)"
                f"  log={log_display}",
                flush=True,
            )
            print(f"[stress] Totals: {counts}", flush=True)

    except KeyboardInterrupt:
        print(f"\n[stress] Stopped after {run_number} run(s).", flush=True)
        counts = "  ".join(f"{k}={v}" for k, v in sorted(totals.items()))
        print(f"[stress] Final totals: {counts}", flush=True)


if __name__ == "__main__":
    main()
