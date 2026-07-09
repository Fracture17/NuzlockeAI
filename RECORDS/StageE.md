# Stage E — Sweep Re-Point & Old-Repo Retirement (plan)

Consolidated checklist of everything deferred to Stage E during the Stage C migration
(2026-07-08/09, user-reviewed). Stage E wires the live-play layer to the C++ engine and
retires the old repo (`/home/Fracture/PycharmProjects/NuzlockeAI`). Until Stage E lands,
the old repo stays frozen as the parity referee — do not modify it.

**Exit gate:** frozen 1028-trace + 100k-corpus replays stay green through the re-point;
carried pytest green with the Stage E skips removed; a full live battle runs end-to-end
on the emulator from this repo (play.py and stress_test.py).

## 1. Sweep re-point (the core seam)
- Swap the `NotImplementedError` bodies in `liveplay/engine_select.py`
  (`run_candidate_sweep`, `enumerate_legal_actions`) for C++-backed implementations.
  Signatures are locked (record `stage_e_seam_signatures`) — this is a body swap.
- Extract/port `check_log_events` + sweep orchestration from the old repo's
  `src/simulation_runner.py` (63 records currently scoped there). The ~20 LogEvents it
  consumes define the rich-logger spec (see §2).

## 2. C++ rich logger (two-logger design)
- Implement `engine/src/logger.h` per the forward-looking records
  `cpp_logger_runtime_toggle` and `cpp_analytical_rng_logger`: runtime-toggleable event
  logger mirroring the Python `LogEvent` stream, plus the lighter analytical RNG log.
- **Missing log events (user ruling 2026-07-09: fix here, not in the frozen Python
  engine).** These `LogEvent` members exist (`liveplay/logger.py`) but have no emit call
  sites anywhere; the C++ logger must emit them where the mechanics execute:
  - `CHARGE_TURN` (38), `SEMI_INVULNERABLE_ENTER` (39), `SEMI_INVULNERABLE_EXIT` (40) —
    two-turn moves are implemented (old `src/engine/core.py` `_TWO_TURN_MOVES`) but silent.
  - `BATON_PASS_TRANSFER` (92) — Baton Pass implemented (old `core.py:1906`) but silent.
  - `STAT_COPY` (55) — Psych Up implemented (old `effects.py:1348`) but silent.
  - `PURSUIT_INTERCEPT` (44) — the intercept **mechanic itself is unimplemented in both
    engines** (R&B keeps vanilla gen-8 Pursuit: 80 BP pre-switch interception, per
    RECORDS/Moves.md; only the AI scorer references it). Implementing it changes battle
    behavior → breaks trace parity, so it is post-retirement work with an
    INTENTIONAL_DIVERGENCES entry. Tracked in TODO.md; the event lands with the mechanic.
- Update `RECORDS/LOGGER_GUIDE.md` §2 when the events start firing.

## 3. Simulator-harness re-point
- Provide `make_sim` / `run_turn` / `capture_turn` / `capture_battle` equivalents driving
  the C++ `GameDriver` (the pure half already lives in `tests/state_builders.py`).
- Remove the three `@pytest.mark.skip(reason="Stage E: ...")` classes in
  `tests/test_battle_policy.py` (14 skipped tests) once `enumerate_legal_actions` works.
- Remove the "old-repo until Stage E" notes from `RECORDS/Simulator.md`,
  `RECORDS/LOGGER_GUIDE.md`, and `RECORDS/DebugScript.md`.

## 4. Live play operational in this repo
- `RandomPolicy`'s battle-action path calls `enumerate_legal_actions` — once §1 lands,
  verify `SCRIPTS/play.py` and `SCRIPTS/stress_test.py` run full battles from this repo.

## 5. gen_cpp_data.py old-repo dependency
- `SCRIPTS/gen_cpp_data.py`'s AI move-set header (`_emit_ai_move_sets_h`) lazy-imports
  `src.ai` via a hardcoded sys.path entry pointing at the old repo. Port the move-set
  source into this repo (with the C++ AI as authority) and delete the path hack.

## 6. Records store re-scoping
- ~156 records still carry old-repo `src/` scopes (`src/simulation_runner.py`,
  `src/engine/*`, `src/ai.py`, `src/simulator.py`, `src/nn/*`, `src/search/*`, ...).
  Re-scope each to its new home as the code arrives (record `records_store_seeding`).
- Ask the user how to dispose of records for dropped subsystems (greedy, nn, search) —
  records are never deleted without instruction.
- `tests/test_cpp_c17g_gate.py` record scope is dangling (test not carried); decide the
  gate's replacement or retire the record.

## 7. Docs debt
- `StaticIssues.md` (old repo): living sweep/state-transition audit — mine still-open
  entries and carry/close when the sweep moves.
- `RECORDS/AI.md`: audit §5.1 asked to "mark resolved inline discrepancies" — was carried
  as-is at Stage C; do the marking pass when the C++ AI is the sole authority.

## 8. Old-repo retirement
- Final sweep of the old repo for anything still referenced (States/ savestates,
  mGBA configs, reference material), archive it, and update
  `RECORDS/C++Transition.md` + memory to record retirement.
