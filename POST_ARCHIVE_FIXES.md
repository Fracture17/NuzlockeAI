# Post-Archive Fixes — deliberate divergences from Python to apply AFTER Python is archived

Python (`src/`) is the authoritative parity reference DURING the C++ port and must be matched
EXACTLY, including its bugs. This file tracks known-incorrect Python behaviors that C++ replicates
for now (to keep the parity gates GREEN) and must be corrected in C++ once Python is archived and
C++ becomes authoritative. Do NOT apply any of these while Python parity gates are still active.

## TODO

### 1. Moody stat pool asymmetry (`src/engine/residuals.py:347-360`)
- **Current Python behavior:** oracle path does `boost_idx % 7` (0–6, includes accuracy & evasion)
  but `drop_idx % 5` (0–4, main stats only). Result: Moody can BOOST accuracy/evasion but never
  DROP them. Comment claims "Gen 8: indices 0-4 only" but only the drop was restricted — the boost
  still uses the old all-7 pool. Internally inconsistent (a half-applied Gen-8 change).
- **Why it's kept:** C++ must replicate the `%7`/`%5` asymmetry (no dedup on the oracle path) so
  parity holds during the port.
- **Intended fix (DECIDED):** both boost and drop span all 7 stats — `boost_idx % 7` and
  `drop_idx % 7` (Gen 5–7 Moody). The Python `% 5` on the drop is a mistake (implementer confusion,
  per user). Apply `%7`/`%7` to BOTH the oracle path and the native fallback. Keep the boost≠drop
  guarantee on the native fallback (extend its dedup to the 7-stat pool).
- **Files to change (C++):** `cpp/src/residuals.cpp` (Moody oracle + native draw).
