# C++-Correct Divergences (Python bug — do NOT fix)

Running tally of parity-gate divergences where the **C++ engine produces the
correct real-game behavior and the authoritative Python engine is wrong**.

Python is being retired, so it is frozen: we neither patch Python nor replicate
its bug in C++. These entries are expected divergences — track them, leave them
alone. Do not treat them as gate failures.

| # | Master seed | Index | Mechanic | Root cause (Python bug) | Real-game / C++ behavior |
|---|-------------|-------|----------|-------------------------|--------------------------|
| 1 | 33445566 | 174620 | Binding release on binder faint | `residuals.py` `_band_late_damage:505` writes back a stale `pokemon` local, resurrecting a BOUND that `release_inflicted_traps` already stripped when the binder fainted mid-band; `_res_tick_timed_volatiles` then decrements it (3→2), leaving the victim bound (`turns=2`). The band's own `_inflictor_already_gone` guard skips the damage but not the volatile, showing release was intended. | Binder faints → victim's trap is released immediately (`bound=[]`). C++ releases correctly. |
