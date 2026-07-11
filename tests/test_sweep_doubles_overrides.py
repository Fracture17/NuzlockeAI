"""Assessment of OLD tests/test_sweep_doubles_overrides.py — slot-keyed override dicts.

LEDGER
======
PORTED: none
ALREADY-COVERED: none
DROPPED (all 5 tests):
  test_singles_emits_scalar_not_dict      — tests OLD _make_sweep_sim_from_partial building a
    scalar DAMAGE_ROLL for singles; that internal doesn't exist in NEW (C++ sweep uses
    SweepConfig/LuckProfile directly). Equivalent coverage exists in
    test_sweep_driver.py::TestBuildSweepLuckExtraOverrides::test_damage_roll_float.
  test_singles_multihit_emits_tuple_not_dict — same: OLD partial DAMAGE_ROLL tuple shape;
    no NEW _make_sweep_sim_from_partial analog. Covered by
    test_sweep_driver.py::test_damage_roll_tuple.
  test_doubles_two_single_hit_per_side_dict — OLD slot-keyed dict shape on overrides_0;
    no NEW analog. Slot-keyed rolls covered by
    test_sweep_driver.py::TestBuildSweepLuckExtraOverrides::test_slot_keyed_rolls_per_hit.
  test_doubles_multihit_plus_single_dict  — OLD multihit+single dict shape; no NEW analog.
  test_doubles_no_valueerror_end_to_end   — uses OLD _run_with_capture (private internal);
    no NEW analog. End-to-end doubles multihit coverage provided by
    test_sweep_doubles_multihit.py::TestDoublesOneMultiHitMover and TestDoublesDoubleMultiHit.

FAILED-NEEDS-REVIEW: none

All tests in this OLD file test _make_sweep_sim_from_partial / _run_with_capture which are
OLD Python Simulator internals with no direct NEW equivalent. The NEW C++ sweep path
handles equivalent concerns via SweepConfig → _build_side_profile → LuckProfile, fully
tested in test_sweep_driver.py.
"""
