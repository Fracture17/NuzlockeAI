"""Assessment of OLD tests/test_sweep_doubles_maxhp.py — per-slot max_hp in _check_hp_match.

LEDGER
======
PORTED: none
ALREADY-COVERED (all 3 tests):
  test_check_hp_match_perslot_max_true     — covered by
    test_sweep_integration.py::TestCheckHpMatchOpponentPerSlotKRange::test_both_opp_slots_k_match
  test_check_hp_match_perslot_max_false_when_swapped — covered by
    test_sweep_integration.py::TestCheckHpMatchOpponentPerSlotKRange::test_wrong_k_fails
  test_check_hp_match_scalar_still_works   — covered extensively by
    test_sweep_integration.py::TestIdentityBoundHpMatch (singles cases)

DROPPED: none
FAILED-NEEDS-REVIEW: none
"""
