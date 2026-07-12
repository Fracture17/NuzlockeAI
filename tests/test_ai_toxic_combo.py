# Tests for Stage 2 AI scorer ports: Toxic/poison combo bonus (Task A) and sleep synergy (Task B).
# Uses compute_action_probabilities (analytic, deterministic) with make_mon/make_battle (1v1, AI=side 1).
# All probability comparisons are strict equality or inequality — no tolerance needed for analytic scorer.
import dataclasses
import pytest
from liveplay.data.abilities import Ability
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status
from tests.state_builders import make_mon, make_battle


def _prob_for_move(state, move: Move, ai_idx: int = 1) -> float:
    """Return the probability assigned to the given move by the AI scorer."""
    from liveplay.engine_select import compute_action_probabilities
    from liveplay.actions import ActionKind
    probs = compute_action_probabilities(state, ai_idx=ai_idx)
    ai_side = state.sides[ai_idx]
    ai_mon = ai_side.team[ai_side.active_indices[0]]
    slot = ai_mon.move_ids.index(move)
    for action, p in probs:
        if action.kind == ActionKind.MOVE and action.move_slot == slot:
            return p
    return 0.0


# ---------------------------------------------------------------------------
# Test 1 — Player burned; AI = Toxic + Rest at full HP.
# Distinguishes new -40 from old -20: Rest at full HP scores -20, so Toxic at
# -40 (new) must lose to Rest's -20, making P(Toxic) ≈ 0 and P(Rest) ≈ 1.
# ---------------------------------------------------------------------------

def test_toxic_blocked_player_has_status_beats_rest():
    """Player burned → Toxic -40 (old was -20). Rest at full HP is -20, so P(Toxic)≈0, P(Rest)≈1."""
    ai_mon = make_mon(Species.GENGAR, moves=(Move.TOXIC, Move.REST))
    pl_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,), status=Status.BURN)
    state = make_battle(pl_mon, ai_mon)
    assert _prob_for_move(state, Move.TOXIC) < 0.01
    assert _prob_for_move(state, Move.REST) > 0.99


# ---------------------------------------------------------------------------
# Test 2 — Steel/Poison type gate (also Poison Gas via POISON_INFLICT_MOVES routing)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("poison_move", [Move.POISON_POWDER, Move.POISON_GAS])
def test_poison_move_blocked_steel_player(poison_move):
    """Poison move vs Steel player without Corrosion AI: P ≈ 0."""
    ai_mon = make_mon(Species.GENGAR, moves=(poison_move, Move.SPLASH))
    pl_mon = make_mon(Species.SKARMORY, moves=(Move.SPLASH,))  # Steel/Flying
    state = make_battle(pl_mon, ai_mon)
    assert _prob_for_move(state, poison_move) < 0.01


@pytest.mark.parametrize("poison_move", [Move.POISON_POWDER, Move.POISON_GAS])
def test_poison_move_corrosion_allows_vs_steel(poison_move):
    """AI with Corrosion can poison Steel player: P ≈ 0.5 (ties Splash at score 6)."""
    ai_mon = make_mon(Species.GENGAR, moves=(poison_move, Move.SPLASH), ability=Ability.CORROSION)
    pl_mon = make_mon(Species.SKARMORY, moves=(Move.SPLASH,))  # Steel/Flying
    state = make_battle(pl_mon, ai_mon)
    # Both score 6 → equal probability
    assert abs(_prob_for_move(state, poison_move) - 0.5) < 0.05


# ---------------------------------------------------------------------------
# Test 3 — Combo bonus: Toxic + Tackle vs Chansey (Splash only = 0 damage)
# Merciless ability triggers toxScore +2; AI with Hex also triggers +2.
# ---------------------------------------------------------------------------

def test_toxic_combo_merciless_increases_probability():
    """Merciless ability gives the Toxic combo bonus: P(Toxic|Merciless) > P(Toxic|no ability)."""
    pl_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,))

    ai_merciless = make_mon(Species.GENGAR, moves=(Move.TOXIC, Move.TACKLE), ability=Ability.MERCILESS)
    state_merciless = make_battle(pl_mon, ai_merciless)

    ai_plain = make_mon(Species.GENGAR, moves=(Move.TOXIC, Move.TACKLE))
    state_plain = make_battle(pl_mon, ai_plain)

    p_merciless = _prob_for_move(state_merciless, Move.TOXIC)
    p_plain = _prob_for_move(state_plain, Move.TOXIC)
    assert p_merciless > p_plain, (
        f"Merciless should increase Toxic probability: merciless={p_merciless:.4f}, plain={p_plain:.4f}"
    )


def test_toxic_combo_hex_increases_probability():
    """AI moveset with Hex triggers the Toxic combo bonus: P(Toxic|Hex) > P(Toxic|Splash-filler)."""
    pl_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,))

    ai_hex = make_mon(Species.GENGAR, moves=(Move.TOXIC, Move.TACKLE, Move.HEX))
    state_hex = make_battle(pl_mon, ai_hex)

    ai_no_hex = make_mon(Species.GENGAR, moves=(Move.TOXIC, Move.TACKLE, Move.SPLASH))
    state_no_hex = make_battle(pl_mon, ai_no_hex)

    p_hex = _prob_for_move(state_hex, Move.TOXIC)
    p_no_hex = _prob_for_move(state_no_hex, Move.TOXIC)
    assert p_hex > p_no_hex, (
        f"Hex should increase Toxic probability: hex={p_hex:.4f}, no_hex={p_no_hex:.4f}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negations: each equals the no-bonus baseline exactly
# ---------------------------------------------------------------------------

def test_toxic_combo_negation_player_has_damaging_move():
    """Player with Pound (damaging move) prevents combo bonus: equals no-Merciless baseline.

    Uses Slowbro (Water/Psychic) as the AI so Pound is not type-immune (Gengar is Ghost,
    which is immune to Normal-type Pound, making it appear to deal 0 damage).
    """
    pl_splash = make_mon(Species.CHANSEY, moves=(Move.SPLASH,))
    pl_pound = make_mon(Species.CHANSEY, moves=(Move.POUND,))

    # Slowbro: Water/Psychic — not immune to Normal-type Pound
    ai_merciless = make_mon(Species.SLOWBRO, moves=(Move.TOXIC, Move.TACKLE), ability=Ability.MERCILESS)

    state_splash = make_battle(pl_splash, ai_merciless)
    state_pound = make_battle(pl_pound, ai_merciless)

    p_splash = _prob_for_move(state_splash, Move.TOXIC)
    p_pound = _prob_for_move(state_pound, Move.TOXIC)
    # Player with Pound can deal damage, so combo bonus is suppressed — equals no-bonus case
    ai_plain = make_mon(Species.SLOWBRO, moves=(Move.TOXIC, Move.TACKLE))
    state_plain = make_battle(pl_pound, ai_plain)
    p_plain_pound = _prob_for_move(state_plain, Move.TOXIC)
    assert abs(p_pound - p_plain_pound) < 1e-9, (
        f"Merciless combo bonus should be suppressed when player has damaging move: "
        f"with_pound={p_pound:.6f}, plain={p_plain_pound:.6f}"
    )
    # Confirm bonus IS active vs Splash-only player
    assert p_splash > p_plain_pound


def test_toxic_combo_negation_player_low_hp():
    """Player at ≤20% HP prevents combo bonus: P equals no-bonus baseline."""
    pl_low = make_mon(Species.CHANSEY, moves=(Move.SPLASH,))
    pl_low = dataclasses.replace(pl_low, hp=pl_low.max_hp * 20 // 100)  # exactly 20%

    ai_merciless = make_mon(Species.GENGAR, moves=(Move.TOXIC, Move.TACKLE), ability=Ability.MERCILESS)
    state_low = make_battle(pl_low, ai_merciless)

    ai_plain = make_mon(Species.GENGAR, moves=(Move.TOXIC, Move.TACKLE))
    state_plain_low = make_battle(pl_low, ai_plain)

    p_low_merciless = _prob_for_move(state_low, Move.TOXIC)
    p_low_plain = _prob_for_move(state_plain_low, Move.TOXIC)
    assert abs(p_low_merciless - p_low_plain) < 1e-9, (
        f"Combo bonus suppressed at ≤20% HP: merciless={p_low_merciless:.6f}, plain={p_low_plain:.6f}"
    )


def test_toxic_combo_negation_sees_kill():
    """Player at 1 HP (Tackle = guaranteed KO): sees_kill suppresses combo bonus.

    P(Toxic|Merciless) == P(Toxic|no Merciless) when AI Tackle kills.
    """
    pl_1hp = make_mon(Species.CHANSEY, moves=(Move.SPLASH,))
    pl_1hp = dataclasses.replace(pl_1hp, hp=1)

    ai_merciless = make_mon(Species.GENGAR, moves=(Move.TOXIC, Move.TACKLE), ability=Ability.MERCILESS)
    ai_plain = make_mon(Species.GENGAR, moves=(Move.TOXIC, Move.TACKLE))

    state_merciless = make_battle(pl_1hp, ai_merciless)
    state_plain = make_battle(pl_1hp, ai_plain)

    p_merciless = _prob_for_move(state_merciless, Move.TOXIC)
    p_plain = _prob_for_move(state_plain, Move.TOXIC)
    assert abs(p_merciless - p_plain) < 1e-9, (
        f"sees_kill must suppress combo bonus: merciless={p_merciless:.6f}, plain={p_plain:.6f}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Sleep synergy visible: Nightmare raises Hypnosis probability
# ---------------------------------------------------------------------------

def test_sleep_synergy_nightmare_increases_hypnosis():
    """AI with Nightmare scores higher sleep synergy: P(Hypnosis|Nightmare) > P(Hypnosis|Splash)."""
    pl_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,))

    ai_nightmare = make_mon(Species.GENGAR, moves=(Move.HYPNOSIS, Move.TACKLE, Move.NIGHTMARE))
    state_nightmare = make_battle(pl_mon, ai_nightmare)

    ai_splash = make_mon(Species.GENGAR, moves=(Move.HYPNOSIS, Move.TACKLE, Move.SPLASH))
    state_splash = make_battle(pl_mon, ai_splash)

    p_nightmare = _prob_for_move(state_nightmare, Move.HYPNOSIS)
    p_splash = _prob_for_move(state_splash, Move.HYPNOSIS)
    assert p_nightmare > p_splash, (
        f"Nightmare synergy should raise Hypnosis probability: "
        f"nightmare={p_nightmare:.4f}, splash={p_splash:.4f}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Snore/Sleep Talk negation: player has Sleep Talk
# ---------------------------------------------------------------------------

def test_sleep_synergy_negated_by_player_sleep_talk():
    """Player moveset with Sleep Talk negates Dream Eater/Nightmare synergy bonus."""
    pl_sleep_talk = make_mon(Species.CHANSEY, moves=(Move.SLEEP_TALK,))
    pl_splash = make_mon(Species.CHANSEY, moves=(Move.SPLASH,))

    ai_nightmare = make_mon(Species.GENGAR, moves=(Move.HYPNOSIS, Move.TACKLE, Move.NIGHTMARE))

    state_sleep_talk = make_battle(pl_sleep_talk, ai_nightmare)
    state_splash_control = make_battle(pl_splash,
                                       make_mon(Species.GENGAR, moves=(Move.HYPNOSIS, Move.TACKLE, Move.SPLASH)))

    p_sleep_talk = _prob_for_move(state_sleep_talk, Move.HYPNOSIS)
    p_control = _prob_for_move(state_splash_control, Move.HYPNOSIS)
    assert abs(p_sleep_talk - p_control) < 1e-9, (
        f"Sleep Talk should negate synergy bonus, matching no-synergy baseline: "
        f"sleep_talk={p_sleep_talk:.6f}, control={p_control:.6f}"
    )


# ---------------------------------------------------------------------------
# Test 7 — sees_kill suppression: player at 1 HP (Tackle KO)
# ---------------------------------------------------------------------------

def test_sleep_synergy_sees_kill_suppression():
    """Player at 1 HP (Tackle kills): P(Hypnosis|Hex) == P(Hypnosis|no Hex)."""
    pl_1hp = make_mon(Species.CHANSEY, moves=(Move.SPLASH,))
    pl_1hp = dataclasses.replace(pl_1hp, hp=1)

    ai_hex = make_mon(Species.GENGAR, moves=(Move.HYPNOSIS, Move.TACKLE, Move.HEX))
    ai_no_hex = make_mon(Species.GENGAR, moves=(Move.HYPNOSIS, Move.TACKLE, Move.SPLASH))

    state_hex = make_battle(pl_1hp, ai_hex)
    state_no_hex = make_battle(pl_1hp, ai_no_hex)

    p_hex = _prob_for_move(state_hex, Move.HYPNOSIS)
    p_no_hex = _prob_for_move(state_no_hex, Move.HYPNOSIS)
    assert abs(p_hex - p_no_hex) < 1e-9, (
        f"sees_kill must suppress sleep synergy bonus: hex={p_hex:.6f}, no_hex={p_no_hex:.6f}"
    )


# ---------------------------------------------------------------------------
# Test 8 — Exception-move sees_kill (Whirlpool trapping kill vs 1-HP player)
# ---------------------------------------------------------------------------

def _hypnosis_score_dist(state, ai_idx: int = 1):
    """Raw score distribution for the AI's Hypnosis move (slot 0), read from the
    ai_action_dists binding. Asserting on the raw Hypnosis score isolates the
    sleep-synergy bonus from move-selection competition: Hex is itself a damaging
    move whose own score differs from Splash, which would confound a P(select)
    comparison even when the Hypnosis bonus is identical."""
    import json
    import nuzlocke_engine_cpp as cpp
    import liveplay.sweep_io as sweep_io
    res = cpp.ai_action_dists(json.dumps(sweep_io.to_jsonable(state)), ai_idx)
    for a, d in zip(res["actions"], res["dists"]):
        if a["move_slot"] == 0:  # Hypnosis
            return {int(s): round(float(p), 6) for s, p in d}
    raise AssertionError("No Hypnosis action found")


def test_sleep_synergy_exception_move_sees_kill():
    """Whirlpool trapping kill on 1-HP player triggers exception_move_sees_kill, which
    suppresses the Hex sleep-synergy bonus → Hypnosis raw score is identical with/without
    Hex. At full HP Whirlpool does not kill → sees_kill=false → the bonus applies → the
    scores differ. Asserting on the raw Hypnosis score (not P(select)) avoids the Hex-as-
    competitor confound that pre-fix was masked by Whirlpool's inflated 12/14 kill score.
    """
    pl_1hp = make_mon(Species.CHANSEY, moves=(Move.SPLASH,))
    pl_1hp = dataclasses.replace(pl_1hp, hp=1)
    pl_full = make_mon(Species.CHANSEY, moves=(Move.SPLASH,))

    # AI with Whirlpool (trapping) + Hypnosis; Hex provides the sleep-synergy bonus.
    ai_hex = make_mon(Species.GENGAR, moves=(Move.HYPNOSIS, Move.WHIRLPOOL, Move.HEX))
    ai_no_hex = make_mon(Species.GENGAR, moves=(Move.HYPNOSIS, Move.WHIRLPOOL, Move.SPLASH))

    # At 1 HP: Whirlpool kills → exception_move_sees_kill → sees_kill=true → bonus suppressed.
    d_1hp_hex = _hypnosis_score_dist(make_battle(pl_1hp, ai_hex))
    d_1hp_no_hex = _hypnosis_score_dist(make_battle(pl_1hp, ai_no_hex))
    assert d_1hp_hex == d_1hp_no_hex, (
        f"exception_move_sees_kill should suppress sleep synergy: "
        f"hex={d_1hp_hex}, no_hex={d_1hp_no_hex}"
    )

    # At full HP: Whirlpool doesn't kill → sees_kill=false → bonus active → scores differ.
    d_full_hex = _hypnosis_score_dist(make_battle(pl_full, ai_hex))
    d_full_no_hex = _hypnosis_score_dist(make_battle(pl_full, ai_no_hex))
    assert d_full_hex != d_full_no_hex, (
        f"At full HP Hex synergy should change the Hypnosis score: "
        f"hex={d_full_hex}, no_hex={d_full_no_hex}"
    )


# ---------------------------------------------------------------------------
# Test 9 — Exact-value assertion with derivation
#
# Setup: AI = Hypnosis (slot 0) + Tackle (slot 1) vs Chansey (Splash only, full HP).
# No Dream Eater/Nightmare, no Hex → ss = 1 (base sees_kill=false adds 1).
#
# After implementation:
#   Hypnosis dist: {7, 0.25}, {6, 0.75}
#   Tackle dist:   {6, 0.8},  {8, 0.2}
#     (p_highest=1.0 because player Splash deals 0; no kill vs full 325-HP Chansey)
#
# P(Hypnosis) via product over (hypnosis_score, tackle_score):
#   (7, 6): prob=0.25*0.8=0.20 → Hypnosis wins  → adds 0.20 to P(Hypnosis)
#   (7, 8): prob=0.25*0.2=0.05 → Tackle wins    → adds 0.00 to P(Hypnosis)
#   (6, 6): prob=0.75*0.8=0.60 → tie (share=0.5)→ adds 0.30 to P(Hypnosis)
#   (6, 8): prob=0.75*0.2=0.15 → Tackle wins    → adds 0.00 to P(Hypnosis)
# Total P(Hypnosis) = 0.20 + 0.30 = 0.50
# ---------------------------------------------------------------------------

def test_sleep_synergy_exact_value_hypnosis_tackle():
    """Exact P(Hypnosis) = 0.50 for AI=Hypnosis+Tackle vs full-HP Splash-only Chansey (ss=1)."""
    ai_mon = make_mon(Species.GENGAR, moves=(Move.HYPNOSIS, Move.TACKLE))
    pl_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,))
    state = make_battle(pl_mon, ai_mon)

    p_hyp = _prob_for_move(state, Move.HYPNOSIS)
    assert abs(p_hyp - 0.50) < 1e-9, (
        f"P(Hypnosis) should be exactly 0.50, got {p_hyp:.10f}"
    )
