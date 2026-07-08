"""
Auto-play a battle with a specified move sequence for sweep pipeline debugging.
Output is written to both stdout and /tmp/vision/debug_sweep.log.

Loads a save state immediately on startup so every run begins from a known
game position. Press O in-game to initialize the battle state. The script
auto-selects moves and presses B to advance text. Ctrl+C to quit.

Usage:
    python SCRIPTS/debug_sweep.py [--moves SLOT [SLOT ...]] [--opponent IDX]
                                   [--level-cap LV] [--state PATH]

    --moves:     Move slots (0-3) per turn, cycling if turns exceed list length.
                 Default: [0] (slot 0 every turn).
    --opponent:  Trainer index in trainers list. Default: 3 (RunNBun ss2).
    --level-cap: Level cap passed to build_battle_state. Default: 12 (RunNBun ss2).
    --state:     Save state file to load on startup.
                 Default: /home/Fracture/Downloads/RunNBun.ss2
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from _shared import _Tee, _kill_existing_mgba  # noqa: E402

# Import shared logic from play.py (its sys.path.insert runs on import)
from play import (  # noqa: E402
    _do_capture,
    _build_battle_state,
    _make_stub_battle_state,
    _CAPTURE_INTERVAL,
    _B_PRESS_INTERVAL,
)

from liveplay.emulator import MGBAProcess, MGBAConnectionError  # noqa: E402
from liveplay.emulator.battle_input import (  # noqa: E402
    _press,
    _send_move_input,
    _read_party_members,
    send_party_selection,
)
from liveplay.battle_policy import RandomPolicy  # noqa: E402
from liveplay.battle_message_matcher import BattleMessageMatcher, ScreenKind  # noqa: E402
from liveplay.battle_types import Constraints  # noqa: E402
from liveplay.hp_stability import PlayerHpBuffer  # noqa: E402
from liveplay.candidate import Candidate  # noqa: E402
from liveplay.candidate_tracker import CandidateTracker  # noqa: E402
from liveplay.sweep_recorder import SweepRecorder  # noqa: E402

_LOG_PATH = Path("/tmp/vision/debug_sweep.log")
_DONE_PATH = Path("/tmp/vision/debug_sweep.done")  # written at battle end; contains "OK" or "ERRORS"
_ERROR_DIR = Path("/tmp/vision/sweep_errors")

# Defaults matching the bundled RunNBun save states (States/RunNBun_ss2/config.json).
_DEFAULT_OPPONENT_INDEX = 3
_DEFAULT_LEVEL_CAP = 12


def _print_sweep_error_summary() -> None:
    """Print the most recent sweep error JSON if one exists."""
    if not _ERROR_DIR.exists():
        return
    errors = sorted(_ERROR_DIR.glob("*.json"))
    if not errors:
        print("[debug] No sweep errors found.")
        return
    latest = errors[-1]
    try:
        data = json.loads(latest.read_text())
        print(f"\n[debug] Latest sweep error: {latest.name}")
        print(f"  {data.get('error', '(no error field)')}")
        for rec in data.get("hp_deltas", []):
            side = "player" if rec.get("side") == 0 else "opp"
            sp = rec.get("species")
            print(f"  hp_delta [{side}] {sp} slot={rec.get('slot')} "
                  f"deltas={rec.get('deltas')} max_hp={rec.get('max_hp')}")
        msgs = data.get("messages", [])
        if msgs:
            print(f"  messages ({len(msgs)}):")
            for m in msgs:
                print(f"    {m.get('string_id')}  vars={m.get('var_values')}")
    except Exception as exc:
        print(f"[debug] Could not parse error file: {exc}")


_TOP_RIGHT_X = 2561  # DP-3 monitor origin
_TOP_RIGHT_Y = 0


def _start_minimize_watcher() -> None:
    """Arrange mGBA windows as soon as they appear (XWayland).

    Must be started BEFORE MGBAProcess. mGBA is launched with QT_QPA_PLATFORM=xcb
    so its windows are visible to xdotool. The 'Scripting' console is minimized;
    the main game window is moved to the top-right monitor.
    """
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
                        print(f"[debug] Minimized Scripting console {wid}.", flush=True)
                    except Exception as exc:
                        print(f"[debug] windowminimize {wid} failed: {exc}", flush=True)
                elif "mGBA" in name:
                    try:
                        _sp.run(["xdotool", "windowmove", wid,
                                 str(_TOP_RIGHT_X), str(_TOP_RIGHT_Y)],
                                capture_output=True, timeout=3)
                        arranged.add(wid)
                        game_done = True
                        print(f"[debug] Moved game window {wid} to top-right.", flush=True)
                    except Exception as exc:
                        print(f"[debug] windowmove {wid} failed: {exc}", flush=True)
            time.sleep(0.05)
        if not scripting_done:
            print("[debug] Scripting console not found within 15s.", flush=True)
        if not game_done:
            print("[debug] Game window not found within 15s.", flush=True)

    threading.Thread(target=_watch, daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--moves", type=int, nargs="+", default=[0], metavar="SLOT",
        help="Move slots (0-3) per turn, cycling. Default: [0].",
    )
    parser.add_argument(
        "--opponent", type=int, default=_DEFAULT_OPPONENT_INDEX, metavar="IDX",
        help=f"Trainer index. Default: {_DEFAULT_OPPONENT_INDEX}.",
    )
    parser.add_argument(
        "--level-cap", type=int, default=_DEFAULT_LEVEL_CAP, metavar="LV",
        help=f"Level cap for build_battle_state. Default: {_DEFAULT_LEVEL_CAP}.",
    )
    parser.add_argument(
        "--state", default="/home/Fracture/Downloads/RunNBun.ss2", metavar="PATH",
        help="Save state file to load on startup. Default: /home/Fracture/Downloads/RunNBun.ss2",
    )
    parser.add_argument(
        "--timeout", type=int, default=120, metavar="SECS",
        help="Hard exit after this many seconds regardless of battle state. Default: 120.",
    )
    args = parser.parse_args()

    moves_sequence: list[int] = args.moves
    opponent_idx: int = args.opponent
    level_cap: int = args.level_cap
    state_path: str = args.state

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DONE_PATH.unlink(missing_ok=True)  # clear sentinel from any previous run
    log_file = _LOG_PATH.open("w", buffering=1)
    orig_stdout = sys.stdout
    sys.stdout = _Tee(orig_stdout, log_file)

    print(f"[debug] moves={moves_sequence}  opponent_idx={opponent_idx}", flush=True)
    print(f"[debug] state={state_path}", flush=True)
    print(f"[debug] log → {_LOG_PATH}", flush=True)

    _kill_existing_mgba()
    _start_minimize_watcher()  # must be before MGBAProcess so window is caught immediately

    try:
        with MGBAProcess(event_timeout=0.1) as mgba:
            from liveplay.vision.capture import ScreenCapture  # noqa

            # Load save state immediately so every run starts from a known position
            print(f"[debug] Loading save state: {state_path}", flush=True)
            mgba.socket.load_state(state_path)
            time.sleep(0.3)  # let emulator settle before first capture
            print(f"[debug] Save state loaded.", flush=True)

            screen_capture = ScreenCapture(mgba.socket)
            matcher = BattleMessageMatcher()
            captures: list[dict] = []
            current_turn: list[dict] = []
            capture_active = False
            last_capture_time_ref = [0.0]
            last_match_ref = [None]
            opponent_hp_bufs: dict = {}
            player_hp_buf = PlayerHpBuffer()
            battle_state_ref = [_make_stub_battle_state()]
            constraints_ref = [Constraints()]
            candidate_tracker_ref = [None]
            opp_k_log_ref: list = [{}]
            player_hp_log_ref: list = [[]]
            last_screen_kind_ref: list = [None]
            last_b_press_time_ref = [0.0]
            policy = RandomPolicy()
            turn_count = 0
            run_start = time.time()
            last_ocr_text: str = ""
            last_text_change_time: float = time.time()

            # Auto-initialize battle state without waiting for O keypress
            print(f"[O] auto-initializing (opponent_idx={opponent_idx})...", flush=True)
            battle_state_ref[0], constraints_ref[0] = _build_battle_state(
                opponent_idx, mgba.socket, level_cap
            )
            initial_candidate = Candidate(state=battle_state_ref[0])
            candidate_tracker_ref[0] = CandidateTracker([initial_candidate])
            recorder_ref = [SweepRecorder.create()]
            print(f"[recorder] Session: {recorder_ref[0].session_dir}", flush=True)
            capture_active = True
            last_capture_time_ref[0] = 0.0
            last_screen_kind_ref[0] = None
            last_b_press_time_ref[0] = 0.0
            turn_count = 0
            p_mons = len(battle_state_ref[0].sides[0].team)
            o_mons = len(battle_state_ref[0].sides[1].team)
            print(f"[state] {p_mons} player mons  {o_mons} opponent mons", flush=True)

            while True:
                event = mgba.socket.recv_event()

                if event == "toggle_capture":
                    capture_active = not capture_active
                    if capture_active:
                        matcher = BattleMessageMatcher()
                        opponent_hp_bufs = {}
                        player_hp_buf = PlayerHpBuffer()
                        last_capture_time_ref[0] = 0.0
                        last_match_ref[0] = None
                        candidate_tracker_ref[0] = None
                        opp_k_log_ref[0] = {}
                        player_hp_log_ref[0] = []
                        last_screen_kind_ref[0] = None
                        last_b_press_time_ref[0] = 0.0
                        print("[capture] ON", flush=True)
                    else:
                        last_screen_kind_ref[0] = None
                        print("[capture] OFF", flush=True)

                elif event == "init_battle":
                    print(f"[O] initializing (opponent_idx={opponent_idx})...", flush=True)
                    battle_state_ref[0], constraints_ref[0] = _build_battle_state(
                        opponent_idx, mgba.socket, level_cap
                    )
                    initial_candidate = Candidate(state=battle_state_ref[0])
                    candidate_tracker_ref[0] = CandidateTracker([initial_candidate])
                    recorder_ref[0] = SweepRecorder.create()
                    print(f"[recorder] Session: {recorder_ref[0].session_dir}", flush=True)
                    opp_k_log_ref[0] = {}
                    player_hp_log_ref[0] = []
                    current_turn.clear()
                    matcher = BattleMessageMatcher()
                    opponent_hp_bufs = {}
                    player_hp_buf = PlayerHpBuffer()
                    last_match_ref[0] = None
                    capture_active = True
                    last_capture_time_ref[0] = 0.0
                    last_screen_kind_ref[0] = None
                    last_b_press_time_ref[0] = 0.0
                    turn_count = 0
                    last_ocr_text = ""
                    last_text_change_time = time.time()
                    p_mons = len(battle_state_ref[0].sides[0].team)
                    o_mons = len(battle_state_ref[0].sides[1].team)
                    print(f"[state] {p_mons} player mons  {o_mons} opponent mons", flush=True)
                    print("[capture] ON (battle started)", flush=True)

                elif event is None:
                    now = time.time()

                    # Global hard timeout
                    if now - run_start > args.timeout:
                        print(f"\n[debug] Global timeout ({args.timeout}s) reached.", flush=True)
                        _DONE_PATH.write_text("STUCK")
                        break

                    if capture_active and now - last_capture_time_ref[0] >= _CAPTURE_INTERVAL:
                        _err_count_before = len(list(_ERROR_DIR.glob("*.json"))) if _ERROR_DIR.exists() else 0
                        battle_ended, screen_kind, ocr_text = _do_capture(
                            screen_capture, matcher, captures, current_turn,
                            last_capture_time_ref, last_match_ref, capture_active,
                            opponent_hp_bufs=opponent_hp_bufs,
                            player_hp_buf=player_hp_buf,
                            candidate_tracker_ref=candidate_tracker_ref,
                            opp_k_log_ref=opp_k_log_ref,
                            player_hp_log_ref=player_hp_log_ref,
                            battle_state_ref=battle_state_ref,
                            constraints_ref=constraints_ref,
                            recorder_ref=recorder_ref,
                        )

                        # Stuck detection: same OCR text for 10s means no progress
                        if ocr_text != last_ocr_text:
                            last_ocr_text = ocr_text
                            last_text_change_time = time.time()
                        elif time.time() - last_text_change_time > 10.0:
                            print(
                                f"\n[debug] Stuck: same battle message for >10s: {ocr_text!r}",
                                flush=True,
                            )
                            _DONE_PATH.write_text("STUCK")
                            break

                        # Write sentinel immediately if a new sweep error was saved
                        _err_count_after = len(list(_ERROR_DIR.glob("*.json"))) if _ERROR_DIR.exists() else 0
                        if _err_count_after > _err_count_before:
                            _DONE_PATH.write_text("ERRORS")
                        if battle_ended:
                            capture_active = False
                            last_screen_kind_ref[0] = None
                            print(f"\n[debug] Battle ended — {turn_count} turns played.", flush=True)
                            _print_sweep_error_summary()
                            has_errors = bool(sorted(_ERROR_DIR.glob("*.json"))) if _ERROR_DIR.exists() else False
                            _DONE_PATH.write_text("ERRORS" if has_errors else "OK")
                            break
                        elif (
                            screen_kind == ScreenKind.OPTION_SELECT
                            and last_screen_kind_ref[0] != ScreenKind.OPTION_SELECT
                        ):
                            slot = moves_sequence[turn_count % len(moves_sequence)]
                            print(f"[debug] Turn {turn_count + 1}: slot {slot}", flush=True)
                            _send_move_input(mgba.socket, slot)
                            turn_count += 1
                            last_screen_kind_ref[0] = screen_kind
                        elif (
                            screen_kind == ScreenKind.PARTY_MENU
                            and last_screen_kind_ref[0] != ScreenKind.PARTY_MENU
                        ):
                            time.sleep(1.0)
                            screen_capture.invalidate()
                            members = _read_party_members(screen_capture)
                            print(f"[party] Detected {len(members)} member(s):", flush=True)
                            for m in members:
                                print(f"  [{m.slot_index}] raw={m.raw_text!r}", flush=True)
                                print(f"         {m.name}  Lv{m.level}  HP {m.hp_current}/{m.hp_max}  {m.status or ''}", flush=True)
                            target = policy.choose_forced_switch(battle_state_ref[0])
                            send_party_selection(mgba.socket, members, target)
                            last_screen_kind_ref[0] = screen_kind
                        else:
                            last_screen_kind_ref[0] = screen_kind

                    # Press B to advance battle text while not on a decision screen
                    if capture_active and last_screen_kind_ref[0] is None:
                        if time.time() - last_b_press_time_ref[0] >= _B_PRESS_INTERVAL:
                            _press(mgba.socket, "b")
                            last_b_press_time_ref[0] = time.time()

    except MGBAConnectionError as exc:
        print(f"\nmGBA closed: {exc}", flush=True)
        _DONE_PATH.write_text("ERRORS")
    except KeyboardInterrupt:
        print(f"\n[debug] Interrupted — log at {_LOG_PATH}", flush=True)
        _DONE_PATH.write_text("INTERRUPTED")
    except Exception:
        import traceback
        print(f"\n[debug] Unexpected crash:", flush=True)
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        _DONE_PATH.write_text("ERRORS")
    finally:
        sys.stdout = orig_stdout
        log_file.close()

    print(f"[debug] Log written to {_LOG_PATH}")


if __name__ == "__main__":
    main()
