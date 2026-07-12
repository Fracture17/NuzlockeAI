# Tests for AI scorer fixes: sleep-move generalization and Truant loafing incapacitation.
# Covers Fix 1 (Hypnosis/Sing/Grass Whistle/Dark Void + Sweet Veil) and Fix 2 (Truant loafing).
import pytest
from liveplay.data.abilities import Ability
from liveplay.data.moves import Move
from liveplay.data.species import Species
from liveplay.data.status import Status
from liveplay.state.pokemon import Volatile
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
# Fix 1 — sleep-move block: player already has a status condition
# ---------------------------------------------------------------------------

def test_hypnosis_blocked_player_has_status():
    """Hypnosis vs burned player: probability ≈ 0 (score -20 vs +7 for Tackle)."""
    ai_mon = make_mon(Species.GENGAR, moves=(Move.HYPNOSIS, Move.TACKLE))
    player_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,), status=Status.BURN)
    state = make_battle(player_mon, ai_mon)
    assert _prob_for_move(state, Move.HYPNOSIS) < 0.01


# ---------------------------------------------------------------------------
# Fix 1 — sleep-move block: player ability blocks sleep
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("blocking_ability", [
    Ability.INSOMNIA,
    Ability.VITAL_SPIRIT,
    Ability.SWEET_VEIL,
])
def test_hypnosis_blocked_by_ability(blocking_ability):
    """Hypnosis vs player with sleep-blocking ability: probability ≈ 0."""
    ai_mon = make_mon(Species.GENGAR, moves=(Move.HYPNOSIS, Move.TACKLE))
    player_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,), ability=blocking_ability)
    state = make_battle(player_mon, ai_mon)
    assert _prob_for_move(state, Move.HYPNOSIS) < 0.01


def test_hypnosis_not_blocked_clean_player():
    """Hypnosis vs clean player: should score +6, so probability > 0."""
    ai_mon = make_mon(Species.GENGAR, moves=(Move.HYPNOSIS, Move.TACKLE))
    player_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,))
    state = make_battle(player_mon, ai_mon)
    assert _prob_for_move(state, Move.HYPNOSIS) > 0.1


# ---------------------------------------------------------------------------
# Fix 1 — same block applies to all five sleep moves
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sleep_move", [
    Move.SING,
    Move.GRASS_WHISTLE,
    Move.DARK_VOID,
    Move.HYPNOSIS,
])
def test_sleep_move_blocked_player_has_status(sleep_move):
    """All sleep moves blocked when player already has a status."""
    ai_mon = make_mon(Species.GENGAR, moves=(sleep_move, Move.TACKLE))
    player_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,), status=Status.BURN)
    state = make_battle(player_mon, ai_mon)
    assert _prob_for_move(state, sleep_move) < 0.01


@pytest.mark.parametrize("sleep_move", [
    Move.SING,
    Move.GRASS_WHISTLE,
    Move.DARK_VOID,
    Move.HYPNOSIS,
])
def test_sleep_move_blocked_by_insomnia(sleep_move):
    """All sleep moves blocked when player has Insomnia."""
    ai_mon = make_mon(Species.GENGAR, moves=(sleep_move, Move.TACKLE))
    player_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,), ability=Ability.INSOMNIA)
    state = make_battle(player_mon, ai_mon)
    assert _prob_for_move(state, sleep_move) < 0.01


# ---------------------------------------------------------------------------
# Fix 1 — Yawn regression: original blocking still works + Sweet Veil added
# ---------------------------------------------------------------------------

def test_yawn_still_blocked_player_has_status():
    """Yawn regression: blocked when player has a status (unchanged behavior)."""
    ai_mon = make_mon(Species.SNORLAX, moves=(Move.YAWN, Move.TACKLE))
    player_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,), status=Status.PARALYSIS)
    state = make_battle(player_mon, ai_mon)
    assert _prob_for_move(state, Move.YAWN) < 0.01


def test_yawn_still_blocked_insomnia():
    """Yawn regression: blocked by Insomnia (unchanged behavior)."""
    ai_mon = make_mon(Species.SNORLAX, moves=(Move.YAWN, Move.TACKLE))
    player_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,), ability=Ability.INSOMNIA)
    state = make_battle(player_mon, ai_mon)
    assert _prob_for_move(state, Move.YAWN) < 0.01


def test_yawn_blocked_sweet_veil():
    """Yawn NEW: Sweet Veil now blocks Yawn (was missing before the fix)."""
    ai_mon = make_mon(Species.SNORLAX, moves=(Move.YAWN, Move.TACKLE))
    player_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,), ability=Ability.SWEET_VEIL)
    state = make_battle(player_mon, ai_mon)
    assert _prob_for_move(state, Move.YAWN) < 0.01


# ---------------------------------------------------------------------------
# Fix 2 — Truant loafing: is_incapacitated returns True when loafing bit set
# ---------------------------------------------------------------------------
# Observable: dist_damage Contrary-Overheat branch returns 9 vs incapacitated (6 otherwise).
# An AI Contrary mon using Overheat against a player that is incapacitated scores higher,
# which shifts probability toward Overheat vs the alternative.

def _make_contrary_overheat_state(player_volatiles: int = 0, player_ability: Ability = Ability.NONE):
    """AI: Malamar (Contrary) with Overheat + Tackle. Player: Chansey."""
    ai_mon = make_mon(Species.GENGAR, moves=(Move.OVERHEAT, Move.TACKLE), ability=Ability.CONTRARY)
    player_mon = make_mon(Species.CHANSEY, moves=(Move.SPLASH,), ability=player_ability)
    state = make_battle(player_mon, ai_mon)
    # Set player volatiles directly on the mutable PokemonState
    if player_volatiles:
        state.sides[0].team[0].volatiles = player_volatiles
    return state


def test_truant_loafing_raises_overheat_score():
    """Contrary Overheat probability is higher when player has Truant + loafing bit set (incapacitated)."""
    TRUANT_LOAFING = Volatile.TRUANT_LOAFING

    state_loafing = _make_contrary_overheat_state(
        player_ability=Ability.TRUANT,
        player_volatiles=int(TRUANT_LOAFING),
    )
    state_not_loafing = _make_contrary_overheat_state(
        player_ability=Ability.TRUANT,
        player_volatiles=0,
    )

    prob_loafing = _prob_for_move(state_loafing, Move.OVERHEAT)
    prob_not_loafing = _prob_for_move(state_not_loafing, Move.OVERHEAT)

    # When incapacitated, dist_damage Contrary branch returns 9 instead of 6 — higher score means higher probability
    assert prob_loafing > prob_not_loafing, (
        f"Expected Overheat prob to be higher when Truant loafing: "
        f"loafing={prob_loafing:.3f}, not_loafing={prob_not_loafing:.3f}"
    )


def test_truant_without_loafing_bit_not_incapacitated():
    """Truant ability alone (loafing bit cleared) does NOT incapacitate — score stays at 6."""
    state_no_loaf = _make_contrary_overheat_state(player_ability=Ability.TRUANT, player_volatiles=0)
    state_clean = _make_contrary_overheat_state()

    prob_no_loaf = _prob_for_move(state_no_loaf, Move.OVERHEAT)
    prob_clean = _prob_for_move(state_clean, Move.OVERHEAT)

    # Both should score identically (6) — probabilities should match
    assert abs(prob_no_loaf - prob_clean) < 0.01, (
        f"Truant without loafing bit changed Overheat probability unexpectedly: "
        f"no_loaf={prob_no_loaf:.3f}, clean={prob_clean:.3f}"
    )
