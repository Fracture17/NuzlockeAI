# Intentional C++-diverges-from-Python decisions

This file tracks places where the C++ engine **deliberately** behaves differently
from the authoritative Python engine (`src/`). These are NOT bugs and NOT parity
failures — they are approved design choices. If a sweep ever surfaces one of these
divergences, cross-check here first before treating it as a regression.

Distinct from `CPP_CORRECT_DIVERGENCES.md`, which tracks cases where Python has a
latent bug and C++ happens to be correct (Python frozen, leave alone).

---

## #1 — Quick Draw fires 30% in random_mode

- **Site:** `cpp/src/core_leaf.cpp` `resolve_quick_draw` (per-Entry, in `cpp_build_queue`).
- **Decision (user, 2026-07-02):** In `random_mode`, C++ fires Quick Draw with a
  30% native-RNG draw (`rng->random() < 0.3`).
- **Why it diverges:** Python's `_action_sort_key` (core.py) computes
  `quick_draw_fires = luck.secondary_threshold <= 30.0` with **no** random_mode branch.
  Under `LuckGroup.RANDOM` the profile's `secondary_threshold` stays 50.0, so Python
  **never** fires Quick Draw in random_mode. C++ intentionally does.
- **Controlled (non-random) mode:** UNCHANGED. C++ keeps `secondary_threshold <= 30.0`
  (GOOD-only, "real-game"), which matches Python exactly — zero parity risk. The c17h
  parity gate runs under `_PINNED` (secondary_threshold=101, not random_mode), so Quick
  Draw never fires there and the gate is unaffected.
- **Corpus hygiene:** the random battle creator prunes the Quick Draw ability so the
  parity/deterministic corpora never generate it (the divergence only lives in the
  native random_mode path, exercised by the random_mode sweep).

---

## #2 — Residual-triggered forced switch (Emergency Exit / Wimp Out) left unported

- **Sites:** Python `src/simulator.py` `_finish_turn:791`; C++ `cpp/src/turn.cpp:448`
  (`throw "unported: residual_switch"`).
- **Decision (user, 2026-07-02):** Leave BOTH engines as-is. Do not fix Python, do not
  implement the C++ residual-switch path. This whole mechanic stays out of the parity corpus.
- **The Python bug being frozen:** when an end-of-turn residual (burn/poison/toxic/weather/
  Leech Seed/etc.) drops an Emergency Exit or Wimp Out holder to ≤50%, the forced switch makes
  `_finish_turn` re-run in full on resume, so **every residual effect for that turn is applied
  twice** (verified: burn tick 20 → 40 HP lost, `UPKEEP_START` logged twice, one `SWITCH_OUT`).
  N party-triggering residual switches ⇒ N+1 applications.
- **C++ status:** the residual-switch path is an ACCEPTED unported boundary — C++ fails loud
  (`unported: residual_switch`) rather than replicate the buggy double-application. It is NOT
  a Category-A oracle gap; it is a deliberately deferred control-flow branch.
- **Corpus hygiene:** `EMERGENCY_EXIT` and `WIMP_OUT` are pruned from every parity/deterministic
  corpus (`SCRIPTS/c17h_clean_battle_gen.py` `EXCLUDED_ABILITIES`, and the random_mode smoke
  gate's `_EXCLUDED_ABILITIES`), so the divergence never appears in a C++-vs-Python comparison.
- **If you ever revisit:** fixing Python (apply residuals once) is the right long-term move but
  changes real battle outcomes on this path and requires new Python tests FIRST; only then port
  a single-pass C++ resolve and un-exclude the two abilities.
