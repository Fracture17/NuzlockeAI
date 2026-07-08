"""
Tests for BattleMessageMatcher — the fuzzy OCR-to-message matcher.

Test IDs map to real in-game scenarios:
  - Exact literal matches
  - Possessive fusion ("PIKACHU's" as one OCR word)
  - Fuzzy literal matching (1-3 edit tolerance)
  - Multi-word VAR slots (e.g. THUNDER WAVE)
  - Prefix-based finalization (typewriter effect)
  - Screen signal detection
  - Attacker vs. target disambiguation via "Foe" prefix
  - UnknownMessageError on finalized-but-unmatched text
"""

import pytest
from liveplay.battle_message_matcher import (
    BattleMessageMatcher,
    MatchResult,
    UnknownMessageError,
    ScreenKind,
    ScreenSignal,
    _preprocess_ocr,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fresh() -> BattleMessageMatcher:
    """Return a new matcher with empty pending state."""
    return BattleMessageMatcher()


def match(m: BattleMessageMatcher, words: list[str], constraints=None):
    """Feed one complete frame then flush. Returns the MatchResult or None."""
    m.process(words, constraints=constraints)
    return m.flush()


def feed(m: BattleMessageMatcher, *frames):
    """Feed multiple frames; return list of non-None process() return values."""
    results = []
    for words in frames:
        r = m.process(words)
        if r is not None:
            results.append(r)
    return results


# ---------------------------------------------------------------------------
# Exact literal matches
# ---------------------------------------------------------------------------

def test_critical_hit():
    r = match(fresh(), ["A", "critical", "hit!"])
    assert r is not None
    assert r.string_id == "STRINGID_CRITICALHIT"


def test_super_effective():
    r = match(fresh(), ["It's", "super", "effective!"])
    assert r is not None
    assert r.string_id == "STRINGID_SUPEREFFECTIVE"


def test_not_very_effective():
    # OCR produces ASCII dots; template has Unicode ellipsis (normalised to ...)
    r = match(fresh(), ["It's", "not", "very", "effective..."])
    assert r is not None
    assert r.string_id == "STRINGID_NOTVERYEFFECTIVE"


def test_no_effect_single_capture():
    # Full capture includes Pokémon name and trailing ellipsis
    r = match(fresh(), ["It", "doesn't", "affect", "Foe", "PIKACHU", "..."])
    assert r is not None
    assert r.string_id == "STRINGID_ITDOESNTAFFECT"


def test_not_very_effective_no_ellipsis():
    # OCR commonly drops the ellipsis glyph entirely; template must still match.
    r = match(fresh(), ["It's", "not", "very", "effective"])
    assert r is not None
    assert r.string_id == "STRINGID_NOTVERYEFFECTIVE"


def test_no_effect_no_ellipsis():
    # Real stress failure: OCR read no trailing ellipsis at all.
    r = match(fresh(), ["It", "doesn't", "affect", "Foe", "Poochyena"])
    assert r is not None
    assert r.string_id == "STRINGID_ITDOESNTAFFECT"


def test_no_effect_apostrophe_split_no_ellipsis():
    # Exact stress capture: apostrophe dropped to a space ("doesn't" -> "doesn t")
    # AND no trailing ellipsis. Must still match.
    r = match(fresh(), ["It", "doesn", "t", "affect", "Foe", "Poochyena"])
    assert r is not None
    assert r.string_id == "STRINGID_ITDOESNTAFFECT"


# ---------------------------------------------------------------------------
# R&B custom ability-survival message (Sturdy)
# ---------------------------------------------------------------------------

def test_sturdy_endured_hit_using():
    # Run & Bun reworded the Sturdy OHKO-survival proc to include the ability
    # name: "{target} Endured the hit using {ability}!". This is NOT in vanilla
    # battle_message.c, so the matcher must carry it as a manual addition or it
    # raises UnknownMessageError and crashes the battle (real stress failure,
    # run_0003_Rick2: 'Foe Pineco Endured the hit using Sturdy !').
    r = match(fresh(), ["Foe", "Pineco", "Endured", "the", "hit", "using", "Sturdy", "!"])
    assert r is not None
    assert r.string_id == "STRINGID_PKMNENDUREDHITUSING"


# ---------------------------------------------------------------------------
# R&B / Gen-5 Autotomize stat-rise message ("became nimble!")
# ---------------------------------------------------------------------------

def test_autotomize_became_nimble():
    # Run & Bun's Autotomize (Speed +2) prints "{user} became nimble!" for the
    # stat rise instead of the generic "{user}'s Speed sharply rose!". This is
    # NOT in vanilla battle_message.c, so the matcher must carry it as a manual
    # addition or it raises UnknownMessageError and crashes the battle (real
    # stress failure, run_0001_Tiana1: 'Foe Spinda became nimble !'). The engine
    # applies the Speed boost during Autotomize execution, so the message itself
    # is matched-and-ignored by the sweep.
    r = match(fresh(), ["Foe", "Spinda", "became", "nimble", "!"])
    assert r is not None
    assert r.string_id == "STRINGID_PKMNBECAMENIMBLE"


# ---------------------------------------------------------------------------
# Possessive-suffix fusion ("PIKACHU's" as one OCR token)
# ---------------------------------------------------------------------------

def test_attack_missed_fused():
    # Template: {VAR}'s attack missed!
    # OCR fuses "PIKACHU" + "'s" into a single bounding box
    r = match(fresh(), ["PIKACHU's", "attack", "missed!"])
    assert r is not None
    assert r.string_id == "STRINGID_ATTACKMISSED"


def test_stat_rose_attacker_fused():
    # Template: {VAR}'s {VAR} {VAR}  (stat-rose; attacker side = no "Foe")
    r = match(fresh(), ["PIKACHU's", "ATTACK", "rose!"])
    assert r is not None
    assert r.string_id == "STRINGID_ATTACKERSSTATROSE"


def test_stat_rose_defender_fused():
    # Template: {VAR}'s {VAR} {VAR}  (stat-rose; defender side = has "Foe")
    r = match(fresh(), ["Foe", "PIKACHU's", "ATTACK", "rose!"])
    assert r is not None
    assert r.string_id == "STRINGID_DEFENDERSSTATROSE"


# ---------------------------------------------------------------------------
# Attacker vs. target disambiguation
# ---------------------------------------------------------------------------

def test_target_fainted_foe_prefix():
    # "Foe PIKACHU" → defender slot → TARGETFAINTED beats ATTACKERFAINTED
    r = match(fresh(), ["Foe", "PIKACHU", "fainted!"])
    assert r is not None
    assert r.string_id == "STRINGID_TARGETFAINTED"


def test_attacker_fainted_no_foe():
    # "PIKACHU" (no Foe) → attacker slot → ATTACKERFAINTED beats TARGETFAINTED
    r = match(fresh(), ["PIKACHU", "fainted!"])
    assert r is not None
    assert r.string_id == "STRINGID_ATTACKERFAINTED"


# ---------------------------------------------------------------------------
# Fuzzy literal matching
# ---------------------------------------------------------------------------

def test_fuzzy_critical():
    # "crtical" is 2 edits from "critical" (7-char word → threshold 3)
    r = match(fresh(), ["A", "crtical", "hit!"])
    assert r is not None
    assert r.string_id == "STRINGID_CRITICALHIT"


def test_fuzzy_super_effective():
    # "supr" is 2 edits from "super" (5-char word → threshold 2)
    r = match(fresh(), ["It's", "supr", "effective!"])
    assert r is not None
    assert r.string_id == "STRINGID_SUPEREFFECTIVE"


def test_fuzzy_fainted():
    # "faintd!" is 2 edits from "fainted!" (8-char word → threshold 3)
    r = match(fresh(), ["Foe", "PIKACHU", "faintd!"])
    assert r is not None
    assert r.string_id == "STRINGID_TARGETFAINTED"


def test_truncated_faint_bare_attacker():
    # The faint message flashes briefly; OCR drops the trailing "ed!" leaving
    # "faint" (edit distance 4 from "fainted !"). With no "Foe" prefix this is
    # the bare ATTACKERFAINTED template — must still match (Bug 16 regression).
    r = match(fresh(), ["PIKACHU", "faint"])
    assert r is not None
    assert r.string_id == "STRINGID_ATTACKERFAINTED"


def test_truncated_faint_foe_target():
    # Same truncation on the opponent side.
    r = match(fresh(), ["Foe", "PIKACHU", "faint"])
    assert r is not None
    assert r.string_id == "STRINGID_TARGETFAINTED"


def test_truncated_faint_gen4_name_via_constraints():
    # The exact crash: a Gen-4 species (not in the static name list) supplied via
    # constraints.valid_pokemon, with the truncated "faint".
    c = Constraints(valid_pokemon=["ROOKIDEE"])
    r = match(fresh(), ["Rookidee", "faint"], constraints=c)
    assert r is not None
    assert r.string_id == "STRINGID_ATTACKERFAINTED"


# ---------------------------------------------------------------------------
# Multi-word VAR slots
# ---------------------------------------------------------------------------

def test_used_move_single_word():
    # Template: {VAR} used {VAR}   — move_name VAR gets "TACKLE!"
    r = match(fresh(), ["PIKACHU", "used", "TACKLE!"])
    assert r is not None
    assert r.string_id == "STRINGID_USEDMOVE"


def test_used_move_two_word():
    # Move name spans two OCR words: "THUNDER" "WAVE!"
    r = match(fresh(), ["PIKACHU", "used", "THUNDER", "WAVE!"])
    assert r is not None
    assert r.string_id == "STRINGID_USEDMOVE"


def test_used_move_metronome_excluded_in_enum_move():
    # Heal Pulse is in the Move enum but METRONOME_EXCLUDED, so it was missing from
    # MOVE_NAMES and "Foe Swirlix used Heal Pulse !" failed to match (live crash:
    # UnknownMessageError no_template_match). Per rule "implemented = in the Move
    # enum", every in-enum move name must be parseable.
    r = match(fresh(), ["Foe", "Swirlix", "used", "Heal", "Pulse", "!"])
    assert r is not None
    assert r.string_id == "STRINGID_USEDMOVE"
    assert any("HEAL PULSE" in v.upper() for v in r.var_values)


def test_used_move_struggle_unconstrained():
    # Struggle is a real move; "Foe Magikarp used Struggle !" must parse to USEDMOVE.
    r = match(fresh(), ["Foe", "Magikarp", "used", "Struggle", "!"])
    assert r is not None
    assert r.string_id == "STRINGID_USEDMOVE"
    assert any(v.upper() == "STRUGGLE" for v in r.var_values)


def test_used_move_struggle_bypasses_valid_moves_constraint():
    # Regression (live crash: UnknownMessageError no_template_match on
    # 'Foe Magikarp used Struggle !'). Struggle is forced when a mon is out of usable
    # moves and is NEVER in any moveset, so it must bypass the valid_moves constraint.
    from liveplay.battle_types import Constraints
    c = Constraints(valid_moves=["TACKLE", "FLAIL"])  # Struggle intentionally absent
    r = match(fresh(), ["Foe", "Magikarp", "used", "Struggle", "!"], constraints=c)
    assert r is not None
    assert r.string_id == "STRINGID_USEDMOVE"
    assert any(v.upper() == "STRUGGLE" for v in r.var_values)


def test_all_enum_moves_in_move_names():
    # MOVE_NAMES must cover the display name of every in-enum move (not just the
    # Metronome-callable subset) so the matcher can parse any move that appears.
    from liveplay.data.moves import Move
    from liveplay.known_values import MOVE_NAMES
    missing = [
        m.name for m in Move
        if m.name != "NONE" and m.name.replace("_", " ") not in MOVE_NAMES
    ]
    assert not missing, f"in-enum moves absent from MOVE_NAMES: {missing}"


# ---------------------------------------------------------------------------
# Two-name "X was poisoned by Y's <ability>!" (R&B reworded PKMNPOISONEDBY)
# ---------------------------------------------------------------------------

def test_poisoned_by_ability_foe_subject():
    # Live stress-test crash: "Foe Carvanha was poisoned by Budew's Poison Point!"
    # Three root causes: (1) battle_messages.py carried the vanilla wording
    # ("{holder}'s {ability} poisoned {target}!") — R&B reordered it;
    # (2) _foe_split only generated Foe-variants for single-name templates, so the
    # two-name *BY family never matched a "Foe X" subject; (3) Budew (Gen 4) was
    # absent from the unconstrained POKEMON_NAMES list. OCR drops the apostrophe in
    # "Budew's" -> "Budew s".
    r = match(fresh(), "Foe Carvanha was poisoned by Budew s Poison Point !".split())
    assert r is not None
    assert r.string_id == "STRINGID_PKMNPOISONEDBY"
    # Subject is the poisoned mon ("Foe Carvanha") -> opponent side.
    assert r.side_hint == 1


def test_all_species_display_names_in_pokemon_names():
    # The unconstrained validation path must recognize the full R&B roster, not
    # just vanilla Gen 1-3. Every Species' emulator display name must be present.
    from liveplay.data.species import Species
    from liveplay.data.name_aliases import emulator_species_name
    from liveplay.known_values import POKEMON_NAMES
    missing = [
        s.name for s in Species
        if emulator_species_name(s).upper() not in POKEMON_NAMES
    ]
    assert not missing, f"species absent from POKEMON_NAMES: {missing[:10]}"


class TestNumberSlotOcrDigits:
    """NUMBER-category slots tolerate OCR digit↔letter confusions.

    OCR routinely swaps 0/O, 1/I/l, 5/S, 8/B, etc. A NUMBER VAR only appears inside an
    already-matched template (surrounding literals prove it is numeric), so normalizing
    the glyphs is safe; the canonical value stores the corrected digits.
    """

    def test_exp_gain_with_letter_o_for_zero(self):
        # Live crash: OCR read the EXP amount "60" as "6O" (letter O).
        r = match(fresh(), ["Skitty", "gained", "6O", "Exp.", "Points", "!"])
        assert r is not None
        assert r.string_id == "STRINGID_PKMNGAINEDEXP"
        assert r.var_values[1] == "60"

    def test_pure_digit_number_still_matches(self):
        r = match(fresh(), ["Skitty", "gained", "60", "Exp.", "Points", "!"])
        assert r is not None
        assert r.string_id == "STRINGID_PKMNGAINEDEXP"
        assert r.var_values[1] == "60"

    def test_normalize_ocr_digits_helper(self):
        from liveplay.battle_message_matcher import _normalize_ocr_digits
        assert _normalize_ocr_digits("6O") == "60"
        assert _normalize_ocr_digits("lOO") == "100"
        assert _normalize_ocr_digits("S8") == "58"
        assert _normalize_ocr_digits("1,234") == "1,234"
        assert _normalize_ocr_digits("60") == "60"


# ---------------------------------------------------------------------------
# Trainer intro / multi-word trainer class
# ---------------------------------------------------------------------------
# Live play sets Constraints(trainer_class, trainer_name) from the opponent's
# full name via rsplit(" ", 1): "Lass Haley" -> ("Lass", "Haley"),
# "Team Aqua Grunt" -> ("Team Aqua", "Grunt"). The DP split between the two
# adjacent VARs is arbitrary, so a multi-word class must be validated by
# joining both spans, not per-VAR.

from liveplay.battle_types import Constraints


def test_intro_single_word_class_constrained():
    c = Constraints(trainer_class="Lass", trainer_name="Haley")
    r = match(fresh(), ["Lass", "Haley", "would", "like", "to", "battle!"], constraints=c)
    assert r is not None
    assert r.string_id == "STRINGID_INTROMSG"


def test_intro_multi_word_class_constrained():
    # "Team Aqua" is a two-word class; the third word "Grunt" is the name.
    c = Constraints(trainer_class="Team Aqua", trainer_name="Grunt")
    r = match(fresh(), ["Team", "Aqua", "Grunt", "would", "like", "to", "battle!"], constraints=c)
    assert r is not None
    assert r.string_id == "STRINGID_INTROMSG"


def test_battleend_multi_word_class_constrained():
    # Same multi-word-class handling must work for other trainer templates.
    c = Constraints(trainer_class="Team Aqua", trainer_name="Grunt")
    r = match(fresh(), ["Player", "defeated", "Team", "Aqua", "Grunt!"], constraints=c)
    assert r is not None
    assert r.string_id in ("STRINGID_BATTLEEND", "STRINGID_PLAYERDEFEATEDTRAINER1")


def test_intro_wrong_trainer_constraint_rejected():
    # Matching phrase but the constrained trainer is a different one -> fail loud.
    c = Constraints(trainer_class="Lass", trainer_name="Haley")
    with pytest.raises(UnknownMessageError):
        match(fresh(), ["Team", "Aqua", "Grunt", "would", "like", "to", "battle!"], constraints=c)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_empty_input_returns_none():
    assert fresh().process([]) is None


def test_process_returns_match_result_type():
    r = match(fresh(), ["A", "critical", "hit!"])
    assert isinstance(r, MatchResult)
    assert isinstance(r.string_id, str)
    assert isinstance(r.id_value, int)
    assert isinstance(r.var_values, list)
    assert isinstance(r.score, int)


# ---------------------------------------------------------------------------
# New tests for Changes 1-9
# ---------------------------------------------------------------------------

def test_rookidee_stat_fell():
    # "8" is an OCR misread of "'s" (distance 2 > per-word threshold of 1);
    # the message-level budget absorbs the error and allows the match.
    # Input simulates: "PIKACHU's ATTACK fell!" with "'s" read as "8".
    r = match(fresh(), ["PIKACHU", "8", "ATTACK", "fell!"])
    assert r is not None
    assert r.string_id == "STRINGID_ATTACKERSSTATFELL"


def test_partial_never_matched():
    # Partial frame alone never raises — only finalization triggers a match attempt.
    # A partial that never gets a breaking frame just stays pending.
    m = fresh()
    words = ["Foe", "Poochyena", "used", "Sard"]
    # All process() calls return None (still just pending, no finalization)
    r1 = m.process(words)
    assert r1 is None
    r2 = m.process(words)
    assert r2 is None  # same prefix (identical), still pending


def test_used_move_exclamation():
    # USEDMOVE gets a "!" terminal token appended at build time.
    r = match(fresh(), ["PIKACHU", "used", "TACKLE!"])
    assert r is not None
    assert r.string_id == "STRINGID_USEDMOVE"


def test_do_what_with_mon_prompt_matched_not_raised():
    # Party-menu submenu prompt "Do what with this PKMN?". The literal "PKMN"
    # glyph uses a non-standard font that never OCRs, so the captured text is
    # 'Do what with this ?'. It must match a benign template, not raise.
    from liveplay.battle_constants import PRIMARY_STRING_IDS
    r = match(fresh(), ["Do", "what", "with", "this", "?"])
    assert r is not None
    assert r.string_id == "STRINGID_DOWHATWITHMON"
    # Benign: not a turn-boundary / action-starting message.
    assert r.string_id not in PRIMARY_STRING_IDS


# ---------------------------------------------------------------------------
# Screen detection tests
# ---------------------------------------------------------------------------

def test_option_select_returns_signal():
    result = fresh().process(["Fight", "Bag", "Pokemon", "Run", "do?"])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.OPTION_SELECT


def test_action_prompt_returns_option_select():
    # "What will <mon> do?" prompt arrives alone (menu words are a separate region).
    result = fresh().process(["What", "will", "Rookidee", "do?"])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.OPTION_SELECT


def test_action_prompt_fuzzy_and_other_mon():
    # Tolerate minor OCR error and any species in the middle.
    result = fresh().process(["Wha", "will", "Poochyena", "do?"])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.OPTION_SELECT


def test_move_select_returns_signal():
    result = fresh().process(["35/35", "Peck", "Leer", "PP", "Fury", "Attack"])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.MOVE_SELECT


def test_option_select_clears_pending():
    # Under prefix logic, OPTION_SELECT does NOT clear pending (play.py calls flush).
    # The pending frame is preserved; a subsequent flush() still yields the match.
    m = fresh()
    m.process(["A", "critical", "hit!"])
    result = m.process(["Fight", "Bag", "Pokemon", "Run"])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.OPTION_SELECT
    # pending preserved — flush yields the match
    r2 = m.flush()
    assert r2 is not None
    assert r2.string_id == "STRINGID_CRITICALHIT"


def test_move_select_does_not_error():
    # Move select must not raise UnknownMessageError even with pending partials
    m = fresh()
    result = m.process(["35/35", "Peck", "PP", "Leer"])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.MOVE_SELECT


def test_party_menu_spaced_words():
    # OCR produces separate words: "Choose Pokemon Cance] a"
    result = fresh().process(["Choose", "Pokemon", "Cance]", "a"])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.PARTY_MENU


def test_party_menu_merged_words():
    # OCR merges words: "ChooseaPokemon: Cance]"
    result = fresh().process(["ChooseaPokemon:", "Cance]"])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.PARTY_MENU


def test_choose_pokemon_message_box_prompt():
    # The forced-replacement message-box prompt "Choose a POKéMON." (normal
    # palette) reaches the matcher as a battle message; it must be recognized
    # as a PARTY_MENU signal, not raise UnknownMessageError.
    result = fresh().process(["Choose", "a", "POKéMON."])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.PARTY_MENU


def test_choose_pokemon_prompt_e_dropped():
    # Robust to OCR that still drops the 'é' ("POKéMON" -> "Pok" "mon").
    result = fresh().process(["Choose", "a", "Pok", "mon."])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.PARTY_MENU


def test_party_menu_clears_pending():
    # PARTY_MENU does NOT clear pending; play.py calls flush explicitly.
    m = fresh()
    m.process(["A", "critical", "hit!"])
    result = m.process(["Choose", "Pokemon", "Cance]"])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.PARTY_MENU
    # pending preserved — flush yields the match
    r2 = m.flush()
    assert r2 is not None
    assert r2.string_id == "STRINGID_CRITICALHIT"


def test_empty_frame_preserves_pending():
    # Empty frame must NOT clear pending (box blanks between messages).
    m = fresh()
    m.process(["A", "critical", "hit!"])
    m.process([])
    r = m.flush()
    assert r is not None
    assert r.string_id == "STRINGID_CRITICALHIT"


# ---------------------------------------------------------------------------
# Prefix-finalization tests (THE KEY NEW BEHAVIOR)
# ---------------------------------------------------------------------------

def test_dropped_faint_regression():
    # Typewriter effect: "Exeggcu" -> "Exeggcute fainte" -> "Exeggcute fainted!"
    # All three are growing prefixes; none should finalize mid-typewriter.
    # flush() at the end yields the complete faint message.
    m = fresh()
    r1 = m.process(["Exeggcu"])
    assert r1 is None
    r2 = m.process(["Exeggcute", "fainte"])
    assert r2 is None
    r3 = m.process(["Exeggcute", "fainted!"])
    assert r3 is None
    result = m.flush()
    assert result is not None
    assert result.string_id == "STRINGID_ATTACKERFAINTED"
    assert "EXEGGCUTE" in result.var_values


def test_prefix_collapse_identical_finals():
    # Same complete frame fed 3x — all three process() calls return None,
    # flush() yields exactly one match.
    m = fresh()
    words = ["A", "critical", "hit!"]
    assert m.process(words) is None
    assert m.process(words) is None
    assert m.process(words) is None
    result = m.flush()
    assert result is not None
    assert result.string_id == "STRINGID_CRITICALHIT"


def test_repeat_message_split_by_shorter_partial():
    # Complete msg A, then shorter partial restart of A, then complete A again, then flush.
    # The shorter partial breaks the prefix -> first A finalizes on seeing partial.
    # Second A finalizes on flush.
    m = fresh()
    complete_a = ["A", "critical", "hit!"]
    partial_restart = ["A"]          # shorter than complete_a raw string — breaks prefix
    results = []

    r = m.process(complete_a)
    assert r is None  # first complete: now pending

    r = m.process(partial_restart)
    # "A critical hit!" does NOT start with "A" ... wait, "A" IS a prefix of "A critical hit!"
    # So this stays pending (partial_restart raw "A" is a prefix of complete_a raw "A critical hit!")
    # Actually per the rule: pending_raw="A critical hit!", current_raw="A"
    # is "A critical hit!".startswith("A") -> True? No! The rule is:
    # _is_prefix(pending_raw, current_raw) = current_raw.startswith(pending_raw)
    # = "A".startswith("A critical hit!") -> False. So it DOES break.
    if r is not None:
        results.append(r)

    r = m.process(complete_a)
    if r is not None:
        results.append(r)

    flushed = m.flush()
    if flushed is not None:
        results.append(flushed)

    assert len(results) == 2, f"Expected 2 matches, got {len(results)}: {[r.string_id for r in results]}"
    assert all(r.string_id == "STRINGID_CRITICALHIT" for r in results)


def test_repeat_across_flush_boundary_records_both():
    # Regression for the cross-turn dedup drop: a message that ENDS turn N (drained by
    # flush() at the boundary) and also BEGINS turn N+1 must be emitted BOTH times. The
    # matcher must not suppress the second occurrence just because it equals the last
    # flushed message — flush() clears pending, so a fresh identical chain finalizes anew.
    m = fresh()

    # Turn N ends with this message; the boundary flush drains it.
    assert m.process(["A", "critical", "hit!"]) is None
    first = m.flush()
    assert first is not None and first.string_id == "STRINGID_CRITICALHIT"

    # Turn N+1 opens with the SAME message (fresh growing chain), then its own flush.
    assert m.process(["A", "critical", "hit!"]) is None
    second = m.flush()
    assert second is not None and second.string_id == "STRINGID_CRITICALHIT"


def test_multi_message_turn_ordering():
    # Two distinct complete messages back-to-back; assert they arrive in feed order.
    m = fresh()
    results = []

    # Feed msg A (critical hit)
    r = m.process(["A", "critical", "hit!"])
    if r is not None:
        results.append(r)

    # Feed msg B (super effective) — breaks prefix of A, finalizes A
    r = m.process(["It's", "super", "effective!"])
    if r is not None:
        results.append(r)

    # flush finalizes B
    flushed = m.flush()
    if flushed is not None:
        results.append(flushed)

    assert len(results) == 2
    assert results[0].string_id == "STRINGID_CRITICALHIT"
    assert results[1].string_id == "STRINGID_SUPEREFFECTIVE"


def test_flush_returns_pending():
    # One complete frame (process returns None), flush() gives match.
    # Second flush() gives None.
    m = fresh()
    assert m.process(["A", "critical", "hit!"]) is None
    r1 = m.flush()
    assert r1 is not None
    assert r1.string_id == "STRINGID_CRITICALHIT"
    r2 = m.flush()
    assert r2 is None


def test_flush_empty_returns_none():
    assert fresh().flush() is None


def test_unknown_finalized_frame_raises():
    # Garbage frame finalized by a breaking frame raises UnknownMessageError.
    m = fresh()
    garbage = ["xqzwj", "klmnop", "vvvvv!"]
    m.process(garbage)
    # A completely different non-extending frame breaks the prefix and triggers finalization
    with pytest.raises(UnknownMessageError):
        m.process(["It's", "super", "effective!"])

    # Also: garbage pending finalized by flush() raises
    m2 = fresh()
    m2.process(["xqzwj", "klmnop", "vvvvv!"])
    with pytest.raises(UnknownMessageError):
        m2.flush()


def test_screen_signal_does_not_match_pending():
    # Feed a complete frame, then an OPTION_SELECT signal.
    # Signal returns ScreenSignal, pending is preserved, flush() yields the match.
    m = fresh()
    assert m.process(["A", "critical", "hit!"]) is None
    result = m.process(["Fight", "Bag", "Pokemon", "Run", "do?"])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.OPTION_SELECT
    r = m.flush()
    assert r is not None
    assert r.string_id == "STRINGID_CRITICALHIT"


def test_move_select_preserves_pending():
    # MOVE_SELECT must not disturb pending state.
    m = fresh()
    assert m.process(["A", "critical", "hit!"]) is None
    result = m.process(["35/35", "Peck", "Leer", "PP", "Fury", "Attack"])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.MOVE_SELECT
    r = m.flush()
    assert r is not None
    assert r.string_id == "STRINGID_CRITICALHIT"


def test_action_prompt_does_not_error_with_pending():
    # Must not raise UnknownMessageError even if a complete frame was pending.
    m = fresh()
    m.process(["A", "critical", "hit!"])
    result = m.process(["What", "will", "Rookidee", "do?"])
    assert isinstance(result, ScreenSignal)
    assert result.kind == ScreenKind.OPTION_SELECT


# ---------------------------------------------------------------------------
# Phrase-level literal matching and slot_labels
# ---------------------------------------------------------------------------

def test_merged_critical_hit():
    # OCR merges "A critical" → "Acritical"; should still match CRITICALHIT.
    # After preprocessing: ["Acritical", "hit", "!"] — 3 words vs 4 literal tokens.
    r = match(fresh(), ["Acritical", "hit!"])
    assert r is not None
    assert r.string_id == "STRINGID_CRITICALHIT"


def test_slot_labels_populated_usedmove():
    # USEDMOVE has 2 extracting slots: attacker VAR and move VAR.
    r = match(fresh(), ["PIKACHU", "used", "TACKLE!"])
    assert r is not None
    assert len(r.slot_labels) == 2
    assert all(isinstance(s, str) and s for s in r.slot_labels)


def test_slot_labels_populated_stat_rose():
    # ATTACKERSSTATROSE has 2 extracting slots: pokemon VAR and stat Enum.
    # Direction is now a literal, not an extracted slot.
    r = match(fresh(), ["PIKACHU's", "ATTACK", "rose!"])
    assert r is not None
    assert len(r.slot_labels) == 2


def test_slot_labels_populated_fainted():
    # TARGETFAINTED has 1 extracting slot: the pokemon VAR.
    r = match(fresh(), ["Foe", "PIKACHU", "fainted!"])
    assert r is not None
    assert len(r.slot_labels) == 1


# ---------------------------------------------------------------------------
# battle_types integration and Constraints parameter
# ---------------------------------------------------------------------------

def test_match_result_importable_from_battle_types():
    from liveplay.battle_types import MatchResult as MR
    assert MR is not None

def test_constraints_param_accepted():
    from liveplay.battle_message_matcher import Constraints
    r = match(fresh(), ["A", "critical", "hit!"], constraints=None)
    assert r is not None
    assert r.string_id == "STRINGID_CRITICALHIT"

def test_constraints_import_from_matcher():
    # Constraints must be importable from the matcher module for backward compat
    from liveplay.battle_message_matcher import Constraints
    c = Constraints()
    assert c.valid_pokemon is None


# ---------------------------------------------------------------------------
# _validate_pokemon_name — no nickname fallback
# ---------------------------------------------------------------------------

class TestValidatePokemonNameNoFallback:
    """_validate_pokemon_name must only accept known species names, not arbitrary nicknames."""

    def setup_method(self):
        from liveplay.battle_message_matcher import _validate_pokemon_name
        self.validate = _validate_pokemon_name

    def test_known_species_accepted(self):
        assert self.validate("Pikachu") is True

    def test_foe_prefix_known_species_accepted(self):
        assert self.validate("Foe Pikachu") is True

    def test_unknown_nickname_rejected(self):
        # "Fluffins" looks like a plausible nickname but is not a known species.
        assert self.validate("Fluffins") is False

    def test_empty_string_rejected(self):
        assert self.validate("") is False


# ---------------------------------------------------------------------------
# Foe/no-Foe split for ATK-side placeholders (STRINGID_USEDMOVE)
# ---------------------------------------------------------------------------

class TestFoePrefixAtkSide:
    """Opponent moves should match with 'Foe' as a literal token, not absorbed into the name var."""

    def test_opponent_move_foe_stripped(self):
        # OCR: ["Foe", "Poochyena", "used", "BITE", "!"]
        # "Foe" must be matched as a literal prefix token, not part of var_values[0].
        # Canonicalization maps "Poochyena" → "POOCHYENA" (the form in POKEMON_NAMES).
        r = match(fresh(), ["Foe", "Poochyena", "used", "BITE!"])
        assert r is not None
        assert r.string_id == "STRINGID_USEDMOVE"
        assert r.var_values[0] == "POOCHYENA"

    def test_player_move_no_foe(self):
        # Player's own move — no "Foe" in the input.
        # Canonicalization maps "Pikachu" → "PIKACHU" (the form in POKEMON_NAMES).
        r = match(fresh(), ["Pikachu", "used", "THUNDERSHOCK!"])
        assert r is not None
        assert r.string_id == "STRINGID_USEDMOVE"
        assert r.var_values[0] == "PIKACHU"

    def test_foe_not_absorbed_into_name(self):
        # var_values[0] must not contain the string "Foe" for opponent moves.
        r = match(fresh(), ["Foe", "Poochyena", "used", "BITE!"])
        assert r is not None
        assert "Foe" not in r.var_values[0]


class TestSubjectSideHint:
    """MatchResult.side_hint exposes the in-game side of var_values[0] from the Foe prefix.

    A "Foe " prefix on the subject name means the opponent (side 1); its absence means
    the player (side 0). This is the only reliable side signal when both sides field the
    same species (mirror match) — the prefix is otherwise consumed as a literal token.
    """

    def test_opponent_move_side_hint_is_1(self):
        r = match(fresh(), ["Foe", "Poochyena", "used", "BITE!"])
        assert r is not None
        assert r.side_hint == 1

    def test_player_move_side_hint_is_0(self):
        r = match(fresh(), ["Pikachu", "used", "THUNDERSHOCK!"])
        assert r is not None
        assert r.side_hint == 0

    def test_non_name_first_slot_side_hint_none(self):
        # CRITICALHIT has no extracting Pokémon-name slot → no side hint.
        r = match(fresh(), ["A", "critical", "hit!"])
        assert r is not None
        assert r.side_hint is None


class TestNameSideSlots:
    """MatchResult.name_side_slots maps every POKEMON_NAME extracting-slot index to its side.

    Unlike side_hint (which only covers slot 0), name_side_slots covers every
    pokémon-name VAR regardless of its position. side_of_name_slot() is the
    public accessor; it returns None for non-name or unresolvable indices.
    """

    def test_foe_subject_usedmove_name_side_slots(self):
        # "Foe Poochyena used BITE!" — mon at extracting idx 0 → opponent side.
        r = match(fresh(), ["Foe", "Poochyena", "used", "BITE!"])
        assert r is not None
        assert r.name_side_slots == {0: 1}
        assert r.side_of_name_slot(0) == 1
        # Consistency: side_hint must agree with name_side_slots[0].
        assert r.side_hint == r.name_side_slots.get(0)

    def test_player_subject_usedmove_name_side_slots(self):
        # "Pikachu used THUNDERSHOCK!" — mon at idx 0 → player side.
        r = match(fresh(), ["Pikachu", "used", "THUNDERSHOCK!"])
        assert r is not None
        assert r.name_side_slots == {0: 0}
        assert r.side_of_name_slot(0) == 0
        assert r.side_hint == r.name_side_slots.get(0)

    def test_usingitem_foe_mon_at_correct_extracting_idx(self):
        # "Using {item}, the {stat} of Foe {mon} rose!" (id 325).
        # B_BUFF2 is expanded into literal direction tokens so it is NOT an extracting slot.
        # Extracting slots: idx 0 = B_LAST_ITEM (item), idx 1 = B_BUFF1 (stat text),
        # idx 2 = B_SCR_ACTIVE_NAME_WITH_PREFIX (mon name).
        # We verify which index holds the mon by inspecting slot_labels at runtime.
        r = match(fresh(), ["Using", "POTION", "the", "HP", "of", "Foe", "POOCHYENA", "rose!"])
        assert r is not None
        assert r.string_id == "STRINGID_USINGITEMSTATOFPKMNROSE"
        # Locate the mon's extracting index dynamically — do NOT assume it is 2.
        mon_idx = next(
            (i for i, lbl in enumerate(r.slot_labels) if lbl == "B_SCR_ACTIVE_NAME_WITH_PREFIX"),
            None,
        )
        assert mon_idx is not None, f"B_SCR_ACTIVE_NAME_WITH_PREFIX not found in slot_labels: {r.slot_labels}"
        # Captured value must be bare (no "Foe " prefix in the name itself).
        assert "Foe" not in r.var_values[mon_idx]
        assert r.var_values[mon_idx] == "POOCHYENA"
        # The mon slot must map to side 1 (foe).
        assert r.name_side_slots.get(mon_idx) == 1
        assert r.side_of_name_slot(mon_idx) == 1
        # slot 0 is the item — side_hint must be None (not a POKEMON_NAME slot).
        assert r.side_hint is None

    def test_usingitem_player_mon_at_correct_extracting_idx(self):
        # Same message, no "Foe" prefix → player side.
        r = match(fresh(), ["Using", "POTION", "the", "HP", "of", "POOCHYENA", "rose!"])
        assert r is not None
        assert r.string_id == "STRINGID_USINGITEMSTATOFPKMNROSE"
        mon_idx = next(
            (i for i, lbl in enumerate(r.slot_labels) if lbl == "B_SCR_ACTIVE_NAME_WITH_PREFIX"),
            None,
        )
        assert mon_idx is not None
        assert r.name_side_slots.get(mon_idx) == 0
        assert r.side_of_name_slot(mon_idx) == 0
        assert r.side_hint is None

    def test_two_name_message_foe_first_player_second(self):
        # PKMNPOISONEDBY: "{target} was poisoned by {holder}'s {ability}!"
        # Extracting slots: 0 = target (B_EFF_NAME_WITH_PREFIX), 1 = holder (B_SCR_ACTIVE_NAME_WITH_PREFIX), 2 = ability.
        # "Foe Carvanha" at idx 0 → side 1; "Budew" at idx 1 → side 0.
        r = match(fresh(), "Foe Carvanha was poisoned by Budew s Poison Point !".split())
        assert r is not None
        assert r.string_id == "STRINGID_PKMNPOISONEDBY"
        target_idx = next(
            (i for i, lbl in enumerate(r.slot_labels) if lbl == "B_EFF_NAME_WITH_PREFIX"), None
        )
        holder_idx = next(
            (i for i, lbl in enumerate(r.slot_labels) if lbl == "B_SCR_ACTIVE_NAME_WITH_PREFIX"), None
        )
        assert target_idx is not None and holder_idx is not None
        assert r.name_side_slots.get(target_idx) == 1   # Foe Carvanha → opponent
        assert r.name_side_slots.get(holder_idx) == 0   # Budew → player
        assert r.side_of_name_slot(target_idx) == 1
        assert r.side_of_name_slot(holder_idx) == 0

    def test_two_name_message_player_first_foe_second(self):
        # PKMNPOISONEDBY: "Pikachu was poisoned by Foe Carvanha's Poison Point!"
        # Player Pikachu at idx 0 → side 0; Foe Carvanha at idx 1 → side 1.
        r = match(fresh(), "Pikachu was poisoned by Foe Carvanha s Poison Point !".split())
        assert r is not None
        assert r.string_id == "STRINGID_PKMNPOISONEDBY"
        target_idx = next(
            (i for i, lbl in enumerate(r.slot_labels) if lbl == "B_EFF_NAME_WITH_PREFIX"), None
        )
        holder_idx = next(
            (i for i, lbl in enumerate(r.slot_labels) if lbl == "B_SCR_ACTIVE_NAME_WITH_PREFIX"), None
        )
        assert target_idx is not None and holder_idx is not None
        assert r.name_side_slots.get(target_idx) == 0   # Pikachu → player
        assert r.name_side_slots.get(holder_idx) == 1   # Foe Carvanha → opponent
        assert r.side_of_name_slot(target_idx) == 0
        assert r.side_of_name_slot(holder_idx) == 1

    def test_no_name_message_empty_name_side_slots(self):
        # CRITICALHIT has no POKEMON_NAME slots → name_side_slots is empty.
        r = match(fresh(), ["A", "critical", "hit!"])
        assert r is not None
        assert r.name_side_slots == {}
        assert r.side_of_name_slot(0) is None


# ---------------------------------------------------------------------------
# Constraint-based validation
# ---------------------------------------------------------------------------

class TestConstraintValidation:
    """Constraints.valid_pokemon/valid_abilities narrow name matching.

    Trainer item-use messages are intentionally unsupported in Run & Bun (trainers
    cannot use battle items), so the item templates were removed; there is no
    valid_items matching path to test.
    """

    def test_pokemon_name_accepts_when_in_constraints(self):
        # Live failure: "Rookidee used FuryAttack!" was not matching STRINGID_USEDMOVE
        # because "Rookidee" failed the global POKEMON_NAMES check (Gen 1-3 list only).
        # With valid_pokemon constraint containing "ROOKIDEE", it must match.
        from liveplay.battle_types import Constraints
        c = Constraints(valid_pokemon=["ROOKIDEE", "POOCHYENA"])
        r = match(fresh(), ["Rookidee", "used", "FuryAttack!"], constraints=c)
        assert r is not None
        assert r.string_id == "STRINGID_USEDMOVE"

    def test_pokemon_name_rejects_when_not_in_constraints(self):
        # When valid_pokemon is set, names outside that list must fail validation.
        # Rejection of an otherwise structurally-plausible USEDMOVE message manifests
        # as the matcher's "no template matched" contract — UnknownMessageError on a
        # finalized capture — not as a None return.
        from liveplay.battle_types import Constraints
        c = Constraints(valid_pokemon=["PIKACHU"])
        # "Rookidee" is not in constraints — no template can claim it, so the finalized
        # capture raises rather than matching STRINGID_USEDMOVE.
        with pytest.raises(UnknownMessageError):
            match(fresh(), ["Rookidee", "used", "TACKLE!"], constraints=c)


# ---------------------------------------------------------------------------
# Canonical var_values
# ---------------------------------------------------------------------------

class TestCanonicalVarValues:
    """var_values must always contain canonical names, never raw OCR noise."""

    def test_pokemon_name_canonicalized(self):
        # "Pookidee" is OCR noise for "ROOKIDEE"; with valid_pokemon constraint
        # the matched result must contain the canonical name, not the OCR string.
        from liveplay.battle_types import Constraints
        c = Constraints(valid_pokemon=["ROOKIDEE"])
        r = match(fresh(), ["Pookidee", "used", "FuryAttack!"], constraints=c)
        assert r is not None
        assert r.var_values[0] == "ROOKIDEE"

    def test_move_name_canonicalized(self):
        # "FuryAttack" (merged OCR) must be canonicalized to "FURY ATTACK" (the canonical
        # form in MOVE_NAMES), not left as the raw OCR string "FuryAttack".
        r = match(fresh(), ["Pikachu", "used", "FuryAttack!"])
        assert r is not None
        assert r.var_values[1] == "FURY ATTACK"

    def test_unnerve_matches_opposing_team(self):
        # "The opposing team is too nervous to eat Berries!" — B_EFF_TEAM is an
        # enum with exactly {"The opposing team", "Your team"}.
        r = match(fresh(), ["The", "opposing", "team", "is", "too", "nervous", "to", "eat", "Berries!"])
        assert r is not None
        assert r.string_id == "STRINGID_UNNERVESTART"
        assert r.var_values[0] == "The opposing team"

    def test_unnerve_matches_with_merged_ocr_words(self):
        # OCR sometimes merges adjacent words: 'teamis', 'toonervous', 'toeatBerries'.
        # True string edit distance is ~5 (missing spaces), but the segmented DP pays ~9
        # because the ENUM absorbs 'teamis' as 'team', leaving the phrase to re-derive 'is '.
        r = match(fresh(), ["The", "opposing", "teamis", "toonervous", "toeatBerries", "!"])
        assert r is not None
        assert r.string_id == "STRINGID_UNNERVESTART"


# ---------------------------------------------------------------------------
# Literal-coverage fallback: a var-greedy template must not win over a
# literal-heavy template when it absorbs most of the (garbled) OCR into VARs.
# ---------------------------------------------------------------------------

class TestLiteralCoverageFallback:
    # Garbled "Foe Poochyena is paralyzed! It can't move!" — OCR misread "Foe"->"For",
    # "!"->",", dropped the apostrophe. The greedy "For {VAR}, {VAR} {VAR}" template
    # (STRINGID_FORXCOMMAYZ) scores 0 by dumping everything into VARs, but only covers
    # 2/10 words with literals. The correct STRINGID_PKMNISPARALYZED must win.
    def test_garbled_paralysis_picks_correct_template(self):
        words = ["For", "Poochyena", "is", "paralyzed", ",", "It", "can", "t", "move", "!"]
        r = match(fresh(), words)
        assert r is not None
        assert r.string_id == "STRINGID_PKMNISPARALYZED", (
            f"got {r.string_id} (coverage={getattr(r, 'literal_coverage', None)})"
        )

    def test_literal_coverage_computed_low_for_var_greedy(self):
        # Even after the fallback re-selects the right template, the *winning* match's
        # coverage should be high (most words explained by literals), confirming the metric.
        words = ["For", "Poochyena", "is", "paralyzed", ",", "It", "can", "t", "move", "!"]
        r = match(fresh(), words)
        assert r is not None
        # PKMNISPARALYZED is "{VAR} is paralyzed! It can't move!" — one VAR ("Poochyena"),
        # the rest literals → coverage well above the 0.30 gate.
        assert r.literal_coverage >= 0.5

    def test_usedmove_unaffected_regression(self):
        # USEDMOVE is only ~33% literal coverage but is the correct, most-literal aligner;
        # the fallback (if it fires) must not change the result.
        r = match(fresh(), ["Foe", "POOCHYENA", "used", "QUICK", "ATTACK", "!"])
        assert r is not None
        assert r.string_id == "STRINGID_USEDMOVE"
        assert r.var_values[0] == "POOCHYENA"
        assert r.var_values[1] == "QUICK ATTACK"

    def test_clean_paralysis_still_matches(self):
        # The non-garbled form must of course still match PKMNISPARALYZED.
        r = match(fresh(), ["Foe", "POOCHYENA", "is", "paralyzed!", "It", "can't", "move!"])
        assert r is not None
        assert r.string_id == "STRINGID_PKMNISPARALYZED"


# ---------------------------------------------------------------------------
# Stat-change direction as literal (±2 crash fix)
# ---------------------------------------------------------------------------
# OCR splits trailing "!" into its own token, so "sharply rose!" arrives as
# ["sharply", "rose", "!"]. The direction phrase must be handled as literal
# template text rather than an enum slot (whose max_words cap would block it).


def _full_match(text: str, constraints=None):
    """Run the pure match path on a space-split OCR string."""
    m = BattleMessageMatcher()
    words = _preprocess_ocr(text.split())
    return m._try_full_match(words, constraints)


def test_stat_sharply_rose_matches():
    # Real crash string: OCR splits "sharply rose!" into 3 tokens.
    r = _full_match("Exeggcute s Attack sharply rose !")
    assert r is not None
    assert r.constant_name == "sText_AttackersStatRose"
    assert r.var_values == ["EXEGGCUTE", "ATTACK"]
    assert r.slot_labels == ["B_ATK_NAME_WITH_PREFIX", "B_BUFF1"]


def test_stat_harshly_fell_matches():
    # ±2 fall direction must also match via literal path.
    r = _full_match("Pikachu s Attack harshly fell !")
    assert r is not None
    assert r.constant_name == "sText_AttackersStatFell"
    assert r.var_values == ["PIKACHU", "ATTACK"]


def test_stat_rose_single_still_matches():
    # Regression: ±1 "rose!" must still match after direction becomes literal.
    r = _full_match("Pikachu s Speed rose !")
    assert r is not None
    assert r.constant_name == "sText_AttackersStatRose"
    assert r.var_values == ["PIKACHU", "SPEED"]


def test_stat_fell_single_still_matches():
    # Regression: ±1 "fell!" must still match after direction becomes literal.
    r = _full_match("Geodude s Defense fell !")
    assert r is not None
    assert r.constant_name == "sText_AttackersStatFell"
    assert r.var_values == ["GEODUDE", "DEFENSE"]


def test_stat_direction_not_extracted():
    # Direction must not appear in var_values; only name + stat name are extracted.
    r = _full_match("Pikachu s Attack sharply rose !")
    assert r is not None
    assert len(r.var_values) == 2
    assert not any("rose" in v.lower() or "fell" in v.lower() for v in r.var_values)


def test_multiword_statname_sharply():
    # Stat-name enum (SP. ATK) must still work alongside the literal direction.
    r = _full_match("Pikachu s SP. ATK sharply rose !")
    assert r is not None
    assert r.constant_name == "sText_AttackersStatRose"
    assert r.var_values == ["PIKACHU", "SP. ATK"]


def test_defender_stat_fell_template_count():
    # STRINGID_DEFENDERSSTATFELL must produce 4 templates: 2 directions × 2 Foe variants.
    from liveplay.battle_message_matcher import _build_templates
    from liveplay.battle_messages import BATTLE_MESSAGES
    msg = next(m for m in BATTLE_MESSAGES if m["string_id"] == "STRINGID_DEFENDERSSTATFELL")
    templates = _build_templates(msg)
    assert len(templates) == 4
    # B_BUFF2 must not be an enum or var token in any template.
    for t in templates:
        for tok in t.tokens:
            assert tok.placeholder != "B_BUFF2", f"B_BUFF2 still extracting in {t}"


def test_defender_stat_fell_foe_match():
    # Defender-side ±2 fall with "Foe" prefix must match and strip "Foe" from var_values[0].
    r = _full_match("Foe Pikachu s Defense harshly fell !")
    assert r is not None
    assert r.constant_name == "sText_DefendersStatFell"
    assert r.var_values[0] == "PIKACHU"
    assert r.var_values == ["PIKACHU", "DEFENSE"]


# ---------------------------------------------------------------------------
# Generic item-triggered stat boost (STRINGID_USINGITEMSTATOFPKMNROSE)
# Live ROM phrasing: "Using {item}, the {stat} of {mon} rose!" — covers pinch
# berries (Salac etc.) and on-hit stat items (Cell Battery etc.).
# ---------------------------------------------------------------------------

def test_using_item_stat_rose_matches():
    # Reproduces the live crash: Salac Berry on Foe Croagunk. Croagunk is a Gen-4
    # species absent from the static list, so live play supplies it via constraints.
    c = Constraints(valid_pokemon=["CROAGUNK"])
    r = _full_match("Using Salac Berry, the Speed of Foe Croagunk rose !", constraints=c)
    assert r is not None
    assert r.string_id == "STRINGID_USINGITEMSTATOFPKMNROSE"


def test_using_item_stat_sharply_rose_matches():
    c = Constraints(valid_pokemon=["CROAGUNK"])
    r = _full_match("Using Starf Berry, the Attack of Foe Croagunk sharply rose !", constraints=c)
    assert r is not None
    assert r.string_id == "STRINGID_USINGITEMSTATOFPKMNROSE"


def test_using_item_direction_not_extracted():
    # B_BUFF2 verb buffer must not leak into var_values.
    c = Constraints(valid_pokemon=["CROAGUNK"])
    r = _full_match("Using Salac Berry, the Speed of Foe Croagunk rose !", constraints=c)
    assert r is not None
    assert not any("rose" in v.lower() for v in r.var_values)
