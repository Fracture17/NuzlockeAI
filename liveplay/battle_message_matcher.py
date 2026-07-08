"""
Fuzzy matcher for Pokémon Emerald battle messages captured by OCR.

Architecture:
  - Template: parses a normalized message string into TemplateTokens (Literal, Var, or Enum)
  - DP alignment: finds min-cost match between OCR words and template tokens
  - BattleMessageMatcher: stateful wrapper that uses character-level prefix finalization
    to handle the typewriter rendering effect; a pending frame is finalized only when the
    next frame's raw string is NOT a continuation of it (or flush() is called explicitly)
"""
from __future__ import annotations

import re
import os
import json
import datetime
import itertools
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from rapidfuzz.distance import Levenshtein as _Lev

from .battle_messages import BATTLE_MESSAGES
from .known_values import (
    POKEMON_NAMES, MOVE_NAMES, ITEM_NAMES, ABILITY_NAMES,
    STAT_NAMES, TYPE_NAMES, TRAINER_CLASS_NAMES, TRAINER_NAMES,
)
from .battle_types import MatchResult, Constraints

__all__ = [
    "BattleMessageMatcher",
    "MatchResult",
    "Constraints",
    "VarCategory",
    "ScreenKind",
    "ScreenSignal",
    "UnknownMessageError",
    "BattleMessageError",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_INF = 10 ** 9
_FOE_PREFIX = "Foe"   # The "Foe " prefix for opponent Pokémon in Emerald trainer battles

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class BattleMessageError(Exception):
    """Base class for all matcher errors."""

class UnknownMessageError(BattleMessageError):
    """
    Raised when a finalized frame (broken prefix or flush) matches no template.
    Always fatal — save context and escalate to user.
    """
    def __init__(self, ocr_words: list[str], reason: str):
        self.ocr_words = ocr_words
        self.reason = reason
        super().__init__(
            f"Unaccountable battle message ({reason}): {' '.join(ocr_words)!r}"
        )


@dataclass
class ScreenSignal:
    kind: ScreenKind

# ---------------------------------------------------------------------------
# VarCategory
# ---------------------------------------------------------------------------

class VarCategory(Enum):
    POKEMON_NAME  = "pokemon_name"
    MOVE_NAME     = "move_name"
    ITEM_NAME     = "item_name"
    ABILITY_NAME  = "ability_name"
    STAT_NAME     = "stat_name"
    TYPE_NAME     = "type_name"
    TRAINER_CLASS = "trainer_class"
    TRAINER_NAME  = "trainer_name"
    NUMBER        = "number"
    TEXT          = "text"   # unchecked / free text

_CAT_FROM_STR: dict[str, VarCategory] = {c.value: c for c in VarCategory}


# ---------------------------------------------------------------------------
# ScreenKind / ScreenSignal
# ---------------------------------------------------------------------------

class ScreenKind(Enum):
    OPTION_SELECT = "option_select"   # Fight/Bag/Pokemon/Run menu — turn boundary
    MOVE_SELECT   = "move_select"     # move chooser screen — silently dropped
    PARTY_MENU    = "party_menu"      # Choose-a-Pokemon/Cancel menu — turn boundary

# Minimum fraction of OCR words a winning template must explain with literal/enum
# segments. Below this, the score-winner likely absorbed garbled text into free VARs,
# so _try_full_match re-selects the highest-coverage aligner instead.
_MIN_LITERAL_COVERAGE = 0.30

# ---------------------------------------------------------------------------
# Fuzzy word matching helpers
# ---------------------------------------------------------------------------

def _max_edits(word_len: int) -> int:
    """Allowed Levenshtein edits for a segment or choice of the given character length.

    Scales at ~20% of length for longer strings so that OCR word-merging (e.g. 'teamis'
    for 'team is') stays within budget on messages with many words.
    """
    if word_len <= 3:
        return 1
    elif word_len <= 6:
        return 2
    return max(3, word_len // 5)


def _word_cost(ocr: str, template: str) -> int:
    """Raw case-insensitive Levenshtein distance (no INF gating)."""
    return _Lev.distance(ocr.lower(), template.lower())


def _best_match(candidate: str, known: frozenset | list[str]) -> Optional[str]:
    """Return closest fuzzy match in *known* within threshold, or None."""
    threshold = _max_edits(len(candidate))
    best_dist = threshold + 1
    best_val: Optional[str] = None
    cand_l = candidate.lower()
    for v in known:
        d = _Lev.distance(cand_l, v.lower())
        if d < best_dist:
            best_dist = d
            best_val = v
    return best_val


def _matches_any_constraint(value: str, candidates) -> bool:
    """True if value is within edit-distance tolerance of any candidate name."""
    return any(_Lev.distance(value.lower(), c.lower()) <= _max_edits(len(c)) for c in candidates)


# Struggle is a universal fallback move: any Pokemon is forced to use it when it has no
# usable move (all PP gone, every move Disabled/Taunted, etc.). It is never part of a
# moveset, so it must bypass the valid_moves constraint in both canonicalization and
# validation — otherwise "Foe X used Struggle!" fails to match during constrained live play.
_STRUGGLE_CANON = "STRUGGLE"


def _is_struggle_span(span: str) -> bool:
    """True if an OCR span fuzzy-matches the move Struggle within edit tolerance."""
    return _Lev.distance(span.lower(), _STRUGGLE_CANON.lower()) <= _max_edits(len(_STRUGGLE_CANON))


def _value_has_foe_prefix(value: str) -> bool:
    """True if the captured value's first word is the 'Foe ' opponent prefix."""
    words = value.split()
    return bool(words) and words[0].lower() == _FOE_PREFIX.lower()


# ---------------------------------------------------------------------------
# TemplateToken
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TemplateToken:
    is_var: bool
    word: str = ""                          # non-empty for Literal tokens
    category: VarCategory = VarCategory.TEXT  # for Var tokens
    placeholder: str = ""                   # original placeholder name
    choices: frozenset = field(default_factory=frozenset)  # non-empty for Enum tokens

    @property
    def is_enum(self) -> bool:
        return not self.is_var and bool(self.choices)

    @property
    def max_words(self) -> int:
        """Max OCR words this token may consume."""
        if self.is_enum:
            return max(len(c.split()) for c in self.choices)
        return 1


# ---------------------------------------------------------------------------
# _Segment — phrase-level grouping of template tokens for DP alignment
# ---------------------------------------------------------------------------

@dataclass
class _Segment:
    """A contiguous group of template tokens for phrase-level DP alignment.

    A phrase segment groups consecutive Lit tokens so OCR merges (e.g. "Acritical"
    from "A critical") count as a single edit rather than a filter failure.
    VAR and Enum tokens each get their own single-token segment.
    """
    tokens: list  # list[TemplateToken]

    @property
    def is_phrase(self) -> bool:
        return not self.tokens[0].is_var and not self.tokens[0].is_enum

    @property
    def is_var(self) -> bool:
        return len(self.tokens) == 1 and self.tokens[0].is_var

    @property
    def is_enum(self) -> bool:
        return len(self.tokens) == 1 and self.tokens[0].is_enum

    @property
    def phrase_text(self) -> str:
        """Space-joined literal words (phrase segments only)."""
        return " ".join(tok.word for tok in self.tokens)

    @property
    def max_words(self) -> int:
        """Max OCR words this segment may consume."""
        if self.is_phrase:
            return len(self.tokens)
        elif self.is_enum:
            return self.tokens[0].max_words
        return _INF  # VAR

    @property
    def single_token(self):
        """For VAR/Enum segments only."""
        return self.tokens[0]


# ---------------------------------------------------------------------------
# Enum sets and per-template overrides
# ---------------------------------------------------------------------------

_STAT_NAMES_ENUM = frozenset([
    "HP", "ATTACK", "DEFENSE", "SPEED", "SP. ATK", "SP. DEF", "accuracy", "evasiveness"
])
_RISE_DIRS = frozenset(["rose!", "sharply rose!"])
_FALL_DIRS = frozenset(["fell!", "harshly fell!"])
_TYPE_NAMES_ENUM = frozenset(TYPE_NAMES)

# Per-template placeholder → EnumToken choices overrides
_ENUM_OVERRIDES: dict[str, dict[str, frozenset]] = {
    # B_BUFF2 (direction) intentionally absent for stat templates — direction phrases
    # like "sharply rose!" are multi-word with a detached "!" token after OCR
    # preprocessing, so they must go through the literal path (_LITERAL_DIRECTION_OVERRIDES)
    # rather than the enum path whose max_words limit would block the 3-token span.
    "STRINGID_ATTACKERSSTATROSE": {"B_BUFF1": _STAT_NAMES_ENUM},
    "STRINGID_DEFENDERSSTATROSE": {"B_BUFF1": _STAT_NAMES_ENUM},
    "STRINGID_ATTACKERSSTATFELL": {"B_BUFF1": _STAT_NAMES_ENUM},
    "STRINGID_DEFENDERSSTATFELL": {"B_BUFF1": _STAT_NAMES_ENUM},
    "STRINGID_STATSWONTINCREASE": {"B_BUFF1": _STAT_NAMES_ENUM},
    "STRINGID_STATSWONTDECREASE": {"B_BUFF1": _STAT_NAMES_ENUM},
    "STRINGID_PKMNCHANGEDTYPE":   {"B_BUFF1": _TYPE_NAMES_ENUM},
    "STRINGID_UNNERVESTART":      {"B_EFF_TEAM": frozenset(["The opposing team", "Your team"])},
}

# Per-template placeholder → set of literal direction phrases to expand into separate templates.
# Each phrase is tokenized via _literal_word_tokens and replaces the named VAR token,
# producing one template variant per phrase (cross-producted with the Foe split).
_LITERAL_DIRECTION_OVERRIDES: dict[str, dict[str, frozenset]] = {
    "STRINGID_ATTACKERSSTATROSE": {"B_BUFF2": _RISE_DIRS},
    "STRINGID_DEFENDERSSTATROSE": {"B_BUFF2": _RISE_DIRS},
    "STRINGID_ATTACKERSSTATFELL": {"B_BUFF2": _FALL_DIRS},
    "STRINGID_DEFENDERSSTATFELL": {"B_BUFF2": _FALL_DIRS},
    "STRINGID_USINGITEMSTATOFPKMNROSE": {"B_BUFF2": _RISE_DIRS},
}

# Extra edit-distance budget for specific templates. The faint message flashes
# briefly, so OCR routinely catches a truncated "faint" for "fainted !"
# (edit distance 4), which the default budget (3) rejects. The VAR is a
# constraints-validated Pokémon name, so loosening the literal budget here is
# safe against false matches.
_BUDGET_BONUS: dict[str, int] = {
    "STRINGID_ATTACKERFAINTED": 2,
    "STRINGID_TARGETFAINTED": 2,
}

# Placeholders that may carry a "Foe " prefix at runtime in trainer battles
_ANY_PREFIX_PH = frozenset({
    "B_DEF_NAME_WITH_PREFIX", "B_ATK_NAME_WITH_PREFIX", "B_EFF_NAME_WITH_PREFIX",
    "B_SCR_ACTIVE_NAME_WITH_PREFIX", "B_OPPONENT_MON1_NAME", "B_OPPONENT_MON2_NAME",
    "B_LINK_OPPONENT_MON1_NAME", "B_LINK_OPPONENT_MON2_NAME",
    "B_PLAYER_MON1_NAME", "B_PLAYER_MON2_NAME",
})

# DEF-side placeholders: these carry "Foe " in trainer battles (opponent Pokémon)
_DEF_PREFIX_PH = frozenset({
    "B_DEF_NAME_WITH_PREFIX", "B_EFF_NAME_WITH_PREFIX",
    "B_OPPONENT_MON1_NAME", "B_OPPONENT_MON2_NAME",
    "B_LINK_OPPONENT_MON1_NAME", "B_LINK_OPPONENT_MON2_NAME",
})

# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

class Template:
    """
    Represents a single battle message template.
    Parses the normalized string into a sequence of TemplateTokens and
    exposes DP-based alignment.
    """

    def __init__(self, msg: dict, _tokens_override: list[TemplateToken] | None = None):
        self.string_id     = msg["string_id"]
        self.id_value      = msg["id_value"]
        self.constant_name = msg["constant_name"]
        self.normalized    = msg["normalized"]

        raw_cats = msg.get("slot_categories", [])
        self._categories: list[VarCategory] = [
            _CAT_FROM_STR.get(c, VarCategory.TEXT) for c in raw_cats
        ]
        self._placeholders: list[str] = msg.get("placeholders", [])

        if _tokens_override is not None:
            self.tokens = _tokens_override
        else:
            self.tokens = self._parse()

        self.literal_count = sum(1 for t in self.tokens if not t.is_var and not t.is_enum)
        self.enum_count    = sum(1 for t in self.tokens if t.is_enum)
        self.var_count     = sum(1 for t in self.tokens if t.is_var)
        self._segments = self._build_segments()
        self._phrase_segment_count = sum(1 for s in self._segments if s.is_phrase)
        self.min_words = self._phrase_segment_count + self.enum_count + self.var_count
        self._budget       = self._compute_budget()  # must come after _segments

    # ------------------------------------------------------------------

    def _parse(self) -> list[TemplateToken]:
        tokens: list[TemplateToken] = []
        cat_idx = 0
        parts = re.split(r'(\{VAR\})', self.normalized)
        for part in parts:
            if part == "{VAR}":
                cat = self._categories[cat_idx] if cat_idx < len(self._categories) else VarCategory.TEXT
                ph = self._placeholders[cat_idx] if cat_idx < len(self._placeholders) else ""
                tokens.append(TemplateToken(is_var=True, category=cat, placeholder=ph))
                cat_idx += 1
            else:
                tokens.extend(_literal_word_tokens(part))
        return tokens

    # ------------------------------------------------------------------
    # Segment construction
    # ------------------------------------------------------------------

    def _build_segments(self) -> list:
        """Group consecutive Lit tokens into phrase segments; VAR/Enum get their own segment."""
        segments = []
        i = 0
        while i < len(self.tokens):
            tok = self.tokens[i]
            if tok.is_var or tok.is_enum:
                segments.append(_Segment([tok]))
                i += 1
            else:
                j = i
                while j < len(self.tokens) and not self.tokens[j].is_var and not self.tokens[j].is_enum:
                    j += 1
                segments.append(_Segment(self.tokens[i:j]))
                i = j
        return segments

    # ------------------------------------------------------------------
    # Budget computation
    # ------------------------------------------------------------------

    def _compute_budget(self) -> int:
        """Total allowed edit distance across all constrained (literal + enum) segments."""
        total = 0
        for seg in self._segments:
            if seg.is_phrase:
                total += _max_edits(len(seg.phrase_text))
            elif seg.is_enum:
                total += _max_edits(max(len(c) for c in seg.single_token.choices))
            # VAR segments don't contribute
        return total + _BUDGET_BONUS.get(self.string_id, 0)

    # ------------------------------------------------------------------
    # DP alignment
    # ------------------------------------------------------------------

    def try_align(self, ocr_words: list[str], partial: bool = False, constraints: "Constraints | None" = None) -> Optional[MatchResult]:
        """
        Align *ocr_words* against this template using segment-based DP.

        partial=False  → all words AND all segments must be consumed (full match)
        partial=True   → all words consumed, any non-zero number of segments consumed

        Returns MatchResult on success, None on failure.
        """
        n = len(ocr_words)
        S = len(self._segments)

        # dp[i][s] = min cost having consumed i words and s segments
        dp     = [[_INF] * (S + 1) for _ in range(n + 1)]
        parent = [[None] * (S + 1) for _ in range(n + 1)]
        dp[0][0] = 0

        for i in range(n + 1):
            for s in range(S + 1):
                cost = dp[i][s]
                if cost == _INF or s == S:
                    continue
                seg = self._segments[s]

                if seg.is_var:
                    for end in range(i + 1, n + 1):
                        if cost < dp[end][s + 1]:
                            dp[end][s + 1] = cost
                            parent[end][s + 1] = (i, s)

                elif seg.is_enum:
                    tok = seg.single_token
                    max_w = tok.max_words
                    for end in range(i + 1, min(i + max_w + 1, n + 1)):
                        span = " ".join(ocr_words[i:end])
                        best_dist = min(
                            _Lev.distance(span.lower(), c.lower()) for c in tok.choices
                        )
                        new_cost = cost + best_dist
                        if new_cost < dp[end][s + 1]:
                            dp[end][s + 1] = new_cost
                            parent[end][s + 1] = (i, s)

                else:  # phrase segment
                    phrase_text = seg.phrase_text
                    max_w = seg.max_words  # = len(seg.tokens)

                    # Try 1..max_words+1 OCR words for the whole phrase. The +1
                    # absorbs a single intra-phrase OCR token split (e.g. an
                    # apostrophe dropped so "doesn't" -> "doesn" "t"). The char
                    # edit budget still gates match quality, so widening the word
                    # window stays safe against false matches.
                    for k in range(1, max_w + 2):
                        end = i + k
                        if end > n:
                            break
                        span = " ".join(ocr_words[i:end])
                        dist = _Lev.distance(span.lower(), phrase_text.lower())
                        new_cost = cost + dist
                        if new_cost < dp[end][s + 1]:
                            dp[end][s + 1] = new_cost
                            parent[end][s + 1] = (i, s)

                    # Fused-suffix: phrase starts with a "'" token (e.g. "'s") and the
                    # preceding OCR word already contains that suffix (VAR consumed it).
                    first_tok = seg.tokens[0]
                    if first_tok.word.startswith("'") and i > 0:
                        prev_word = ocr_words[i - 1]
                        suffix = first_tok.word
                        if prev_word.lower().endswith(suffix.lower()):
                            base = prev_word[: -len(suffix)]
                            if len(base) >= 3 and _validate_pokemon_name(base):
                                rest_tokens = seg.tokens[1:]
                                if rest_tokens:
                                    rest_text = " ".join(tok.word for tok in rest_tokens)
                                    for k in range(1, len(rest_tokens) + 1):
                                        end = i + k
                                        if end > n:
                                            break
                                        span = " ".join(ocr_words[i:end])
                                        dist = _Lev.distance(span.lower(), rest_text.lower())
                                        new_cost = cost + dist
                                        if new_cost < dp[end][s + 1]:
                                            dp[end][s + 1] = new_cost
                                            parent[end][s + 1] = (i, s)
                                else:
                                    # Phrase is just the "'" token — zero-word transition
                                    if cost < dp[i][s + 1]:
                                        dp[i][s + 1] = cost
                                        parent[i][s + 1] = (i, s)

        # Find terminal state
        if partial:
            final_s = min(
                (s for s in range(1, S + 1) if dp[n][s] < _INF),
                key=lambda s: dp[n][s],
                default=None,
            )
            if final_s is None:
                return None
            final_cost = dp[n][final_s]
        else:
            if dp[n][S] >= _INF:
                return None
            final_s = S
            final_cost = dp[n][S]

        if final_cost > self._budget:
            return None

        var_values = self._traceback(parent, ocr_words, n, final_s, constraints)

        if not partial and not self._validate_vars(var_values, constraints):
            return None

        # Literal coverage: fraction of OCR words consumed by literal/enum segments
        # (i.e. NOT absorbed into free VARs). A var-greedy template that dumps most of
        # the input into VARs scores low here even if its few literals match cheaply.
        var_words = 0
        ti, ts = n, final_s
        while parent[ti][ts] is not None:
            pi, ps = parent[ti][ts]
            if self._segments[ps].is_var:
                var_words += (ti - pi)
            ti, ts = pi, ps
        literal_coverage = (n - var_words) / n if n else 1.0

        slot_labels = [
            seg.single_token.placeholder
            for seg in self._segments
            if not seg.is_phrase
        ]

        return MatchResult(
            string_id     = self.string_id,
            id_value      = self.id_value,
            constant_name = self.constant_name,
            var_values    = var_values,
            score         = final_cost,
            context_score = self._context_score(var_values),
            matched_text  = self._reconstruct(var_values),
            slot_labels   = slot_labels,
            literal_coverage = literal_coverage,
            side_hint     = self._subject_side_hint(var_values),
            name_side_slots = self._name_side_slots(var_values),
        )

    def _name_side_slots(self, var_values: list[str]) -> dict[int, int]:
        """Map each POKEMON_NAME extracting-slot index to its side (0=player, 1=opponent).

        Detects 'Foe' via both signals: a literal token immediately preceding the VAR
        in self.tokens (the _foe_split path) and a 'Foe ' prefix in the captured value
        (legacy no-split OCR path). Enum slots are skipped (they are never POKEMON_NAME).
        """
        result: dict[int, int] = {}
        # Build a mapping from segment index (in self._segments) → token start index (in self.tokens).
        # Walk self.tokens in parallel to find where each segment begins.
        seg_token_start: list[int] = []
        tok_pos = 0
        for seg in self._segments:
            seg_token_start.append(tok_pos)
            tok_pos += len(seg.tokens)

        extracting_idx = 0
        for seg_idx, seg in enumerate(self._segments):
            if seg.is_phrase:
                continue
            tok = seg.single_token
            if tok.is_var and tok.category == VarCategory.POKEMON_NAME:
                val = var_values[extracting_idx] if extracting_idx < len(var_values) else ""
                tok_idx = seg_token_start[seg_idx]  # index of this VAR token in self.tokens
                foe_as_literal = (
                    tok_idx > 0
                    and not self.tokens[tok_idx - 1].is_var
                    and not self.tokens[tok_idx - 1].is_enum
                    and self.tokens[tok_idx - 1].word.lower() == _FOE_PREFIX.lower()
                )
                has_foe = foe_as_literal or _value_has_foe_prefix(val)
                result[extracting_idx] = 1 if has_foe else 0
            extracting_idx += 1
        return result

    def _subject_side_hint(self, var_values: list[str]) -> int | None:
        """Side of var_values[0] inferred from the Foe prefix, or None.

        The first extracting slot is the message subject (the USEDMOVE attacker, the
        status-affected mon, etc.). In trainer battles the opponent's name is shown with
        a "Foe " prefix and the player's without one, so a Foe prefix → side 1, its
        absence → side 0. Returns None when slot 0 is not a Pokémon-name VAR (no side
        signal). The prefix appears either as a literal token preceding the VAR (the
        _build_templates Foe-split path) or as the first word of the captured value.
        """
        extracting = [s for s in self._segments if not s.is_phrase]
        if not extracting or not var_values:
            return None
        first = extracting[0].single_token
        if first.is_var is False or first.category != VarCategory.POKEMON_NAME:
            return None
        # Index of slot 0's token within self.tokens (first var/enum token).
        tok_idx = next(
            (i for i, t in enumerate(self.tokens) if t.is_var or t.is_enum),
            None,
        )
        foe_literal = (
            tok_idx is not None and tok_idx > 0
            and not self.tokens[tok_idx - 1].is_var
            and not self.tokens[tok_idx - 1].is_enum
            and self.tokens[tok_idx - 1].word.lower() == _FOE_PREFIX.lower()
        )
        val0 = var_values[0]
        foe_value = _value_has_foe_prefix(val0)
        return 1 if (foe_literal or foe_value) else 0

    # ------------------------------------------------------------------
    # Context scoring (kept for backward compat; not used in ranking)
    # ------------------------------------------------------------------

    _ATK_PLACEHOLDERS = frozenset({
        "B_ATK_NAME_WITH_PREFIX", "B_PLAYER_MON1_NAME", "B_PLAYER_MON2_NAME",
    })
    _DEF_PLACEHOLDERS = frozenset({
        "B_DEF_NAME_WITH_PREFIX", "B_OPPONENT_MON1_NAME", "B_OPPONENT_MON2_NAME",
        "B_LINK_OPPONENT_MON1_NAME", "B_LINK_OPPONENT_MON2_NAME",
    })

    def _context_score(self, var_values: list[str]) -> int:
        """Penalty for Foe-prefixed names in attacker slots or vice versa.

        "Foe" may appear either as a literal template token immediately preceding the VAR
        (inserted by _build_templates) or as part of var_values (legacy no-split path).
        Both forms are detected so disambiguation works correctly.
        """
        var_token_indices = [i for i, t in enumerate(self.tokens) if t.is_var]
        var_tokens = [self.tokens[i] for i in var_token_indices]
        penalty = 0
        for slot_idx, (tok, val) in enumerate(zip(var_tokens, var_values)):
            if tok.category != VarCategory.POKEMON_NAME:
                continue
            # Check if "Foe" appears as a literal token just before this VAR token,
            # or as the first word of the captured value (legacy path without Foe-split).
            tok_idx = var_token_indices[slot_idx]
            foe_as_literal = (
                tok_idx > 0
                and not self.tokens[tok_idx - 1].is_var
                and self.tokens[tok_idx - 1].word.lower() == _FOE_PREFIX.lower()
            )
            foe_in_value = _value_has_foe_prefix(val)
            has_foe = foe_as_literal or foe_in_value
            if has_foe and tok.placeholder in self._ATK_PLACEHOLDERS:
                penalty += 1
            elif not has_foe and tok.placeholder in self._DEF_PLACEHOLDERS:
                penalty += 1
        return penalty

    # ------------------------------------------------------------------

    def _traceback(
        self, parent: list, ocr_words: list[str], end_i: int, end_s: int,
        constraints: "Constraints | None" = None,
    ) -> list[str]:
        """Walk parent pointers to extract what each VAR or Enum segment consumed."""
        steps: list[tuple[int, int, int, int]] = []
        i, s = end_i, end_s
        while parent[i][s] is not None:
            pi, ps = parent[i][s]
            steps.append((pi, ps, i, s))
            i, s = pi, ps
        steps.reverse()

        var_values: list[str] = []
        for (pi, ps, ci, cs) in steps:
            seg = self._segments[ps]
            if seg.is_enum:
                span = " ".join(ocr_words[pi:ci])
                canonical = min(seg.single_token.choices, key=lambda c: _Lev.distance(span.lower(), c.lower()))
                var_values.append(canonical)
            elif seg.is_var:
                span = " ".join(ocr_words[pi:ci])
                var_values.append(_canonical_var_value(span, seg.single_token.category, constraints))
        return var_values

    # ------------------------------------------------------------------

    def _reconstruct(self, var_values: list[str]) -> str:
        """
        Rebuild the canonical message string from template tokens + matched values.
        Literals use their template word; VAR/Enum slots use the corresponding var_values entry.
        '!' and tokens starting with "'" are joined without a preceding space.
        """
        parts: list[str] = []
        var_idx = 0
        for tok in self.tokens:
            if tok.is_var or tok.is_enum:
                if var_idx < len(var_values):
                    parts.append(var_values[var_idx])
                    var_idx += 1
            else:
                # Skip a possessive literal (e.g. "'s") when the preceding var
                # value already ends with it — OCR sometimes fuses "PIKACHU's"
                # into one token, so the VAR captures the suffix and the Lit
                # would double it without this guard.
                if tok.word.startswith("'") and parts and parts[-1].endswith(tok.word):
                    continue
                parts.append(tok.word)

        result = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if result and not part.startswith("!") and not part.startswith("'"):
                result += " "
            result += part
        return result

    # ------------------------------------------------------------------
    # VAR validation
    # ------------------------------------------------------------------

    def _extracting_tokens(self) -> list[TemplateToken]:
        """All tokens that extract a value (VAR or Enum), in document order."""
        return [t for t in self.tokens if t.is_var or t.is_enum]

    def _validate_vars(self, var_values: list[str], constraints: "Constraints | None" = None) -> bool:
        toks = self._extracting_tokens()
        # Adjacent (TRAINER_CLASS, TRAINER_NAME) VARs are validated as one joined
        # "Class Name" identifier: the DP split between them is arbitrary (both
        # VARs cost 0), so a multi-word class (e.g. "Team Aqua") lands on either
        # side and per-VAR checks would spuriously fail.
        skip: set[int] = set()
        for k in range(len(toks) - 1):
            if (toks[k].is_var and toks[k].category == VarCategory.TRAINER_CLASS
                    and toks[k + 1].is_var and toks[k + 1].category == VarCategory.TRAINER_NAME):
                if k + 1 >= len(var_values):
                    return False
                combined = f"{var_values[k]} {var_values[k + 1]}".strip()
                if not self._validate_trainer_pair(combined, constraints):
                    return False
                skip.update({k, k + 1})

        for idx, (tok, val) in enumerate(zip(toks, var_values)):
            if idx in skip or tok.is_enum:
                continue  # joined-validated pair, or enum already validated by DP
            if not self._validate_one(val, tok.category, constraints):
                return False
        return True

    @staticmethod
    def _validate_trainer_pair(combined: str, constraints: "Constraints | None") -> bool:
        """Validate a joined 'Class Name' span against the constrained trainer
        (or the full TRAINER_NAMES identifier list when unconstrained)."""
        if constraints is not None and constraints.trainer_class is not None:
            target = f"{constraints.trainer_class} {constraints.trainer_name or ''}".strip()
            return _Lev.distance(combined.lower(), target.lower()) <= _max_edits(len(target))
        return _best_match(combined, TRAINER_NAMES) is not None

    def _validate_one(self, value: str, cat: VarCategory, constraints: "Constraints | None" = None) -> bool:
        if cat == VarCategory.TEXT:
            return True
        if not value:
            return False

        if cat == VarCategory.POKEMON_NAME:
            if constraints is not None and constraints.unconstrained_names:
                return _validate_pokemon_name(value)
            elif constraints is not None and constraints.valid_pokemon is not None:
                # Strip optional "Foe " prefix before matching against constraints
                words = value.split()
                if len(words) >= 2 and _word_cost(words[0], _FOE_PREFIX) <= _max_edits(len(_FOE_PREFIX)):
                    bare = " ".join(words[1:])
                else:
                    bare = value
                return _matches_any_constraint(bare, constraints.valid_pokemon)
            return _validate_pokemon_name(value)
        elif cat == VarCategory.MOVE_NAME:
            # Struggle is a forced fallback that is never in any moveset — always accept it.
            if value == _STRUGGLE_CANON or _is_struggle_span(value):
                return True
            if constraints is not None and constraints.unconstrained_moves:
                return _best_match(value, MOVE_NAMES) is not None
            elif constraints is not None and constraints.valid_moves is not None:
                return _matches_any_constraint(value, constraints.valid_moves)
            return _best_match(value, MOVE_NAMES) is not None
        elif cat == VarCategory.ITEM_NAME:
            if constraints is not None and constraints.valid_items is not None:
                return _matches_any_constraint(value, constraints.valid_items)
            return _best_match(value, ITEM_NAMES) is not None
        elif cat == VarCategory.ABILITY_NAME:
            if constraints is not None and constraints.valid_abilities is not None:
                return _matches_any_constraint(value, constraints.valid_abilities)
            return _best_match(value, ABILITY_NAMES) is not None
        elif cat == VarCategory.STAT_NAME:
            return _best_match(value, STAT_NAMES) is not None
        elif cat == VarCategory.TYPE_NAME:
            return _best_match(value, TYPE_NAMES) is not None
        elif cat == VarCategory.TRAINER_CLASS:
            if constraints is not None and constraints.trainer_class is not None:
                return _Lev.distance(value.lower(), constraints.trainer_class.lower()) <= _max_edits(len(constraints.trainer_class))
            return _best_match(value, TRAINER_CLASS_NAMES) is not None
        elif cat == VarCategory.TRAINER_NAME:
            if constraints is not None and constraints.trainer_name is not None:
                return _Lev.distance(value.lower(), constraints.trainer_name.lower()) <= _max_edits(len(constraints.trainer_name))
            return _best_match(value, TRAINER_NAMES) is not None
        elif cat == VarCategory.NUMBER:
            return bool(re.fullmatch(r'[\d,¥]+', _normalize_ocr_digits(value)))
        return True


# High-confidence OCR letter→digit confusions for NUMBER-category slots. A NUMBER VAR
# only appears inside an already-matched template, so the surrounding literals already
# prove the span is numeric; normalizing these glyphs lets values like "6O" read as "60".
_OCR_DIGIT_MAP = str.maketrans({
    "O": "0", "o": "0", "Q": "0", "D": "0",
    "I": "1", "l": "1", "|": "1", "i": "1",
    "Z": "2",
    "S": "5",
    "G": "6",
    "T": "7",
    "B": "8",
})


def _normalize_ocr_digits(value: str) -> str:
    """Map common OCR letter↔digit confusions to their digit forms (e.g. '6O' → '60')."""
    return value.translate(_OCR_DIGIT_MAP)


def _canonical_var_value(span: str, cat: VarCategory, constraints: "Constraints | None" = None) -> str:
    """
    Return the canonical form of a VAR-slot OCR span.
    Looks up the closest known name for each named category, using constraint
    lists when available and falling back to global lists otherwise.
    """
    if cat == VarCategory.NUMBER:
        return _normalize_ocr_digits(span)

    if cat == VarCategory.MOVE_NAME:
        # Struggle is never in valid_moves; canonicalize it to the global Struggle name.
        if _is_struggle_span(span):
            return _STRUGGLE_CANON
        if constraints is not None and not constraints.unconstrained_moves and constraints.valid_moves is not None:
            return _best_match(span, constraints.valid_moves) or span
        return _best_match(span, MOVE_NAMES) or span

    if cat == VarCategory.POKEMON_NAME:
        # Strip optional "Foe " prefix, canonicalize the bare name, then reattach.
        words = span.split()
        if len(words) >= 2 and _word_cost(words[0], _FOE_PREFIX) <= _max_edits(len(_FOE_PREFIX)):
            bare = " ".join(words[1:])
            had_foe = True
        else:
            bare = span
            had_foe = False
        known = (constraints.valid_pokemon if constraints is not None and constraints.valid_pokemon is not None
                 else POKEMON_NAMES)
        canonical = _best_match(bare, known) or bare
        return (_FOE_PREFIX + " " + canonical) if had_foe else canonical

    if cat == VarCategory.ITEM_NAME:
        known = (constraints.valid_items if constraints is not None and constraints.valid_items is not None
                 else ITEM_NAMES)
        return _best_match(span, known) or span

    if cat == VarCategory.ABILITY_NAME:
        known = (constraints.valid_abilities if constraints is not None and constraints.valid_abilities is not None
                 else ABILITY_NAMES)
        return _best_match(span, known) or span

    if cat == VarCategory.TRAINER_CLASS:
        if constraints is not None and constraints.trainer_class is not None:
            val = constraints.trainer_class
            if _Lev.distance(span.lower(), val.lower()) <= _max_edits(len(val)):
                return val
            return span
        return _best_match(span, TRAINER_CLASS_NAMES) or span

    if cat == VarCategory.TRAINER_NAME:
        if constraints is not None and constraints.trainer_name is not None:
            val = constraints.trainer_name
            if _Lev.distance(span.lower(), val.lower()) <= _max_edits(len(val)):
                return val
            return span
        return _best_match(span, TRAINER_NAMES) or span

    return span


def _validate_pokemon_name(value: str) -> bool:
    """Accept a known species name, optionally preceded by a fuzzy "Foe" prefix."""
    words = value.split()
    if not words:
        return False

    # Strip optional "Foe " prefix
    if len(words) >= 2 and _word_cost(words[0], _FOE_PREFIX) <= _max_edits(len(_FOE_PREFIX)):
        name_part = " ".join(words[1:])
    elif len(words) == 1:
        name_part = value
    else:
        # 2+ words with no recognised prefix — not a valid Pokémon name
        return False

    # Validate name_part against known species
    return _best_match(name_part, POKEMON_NAMES) is not None


# ---------------------------------------------------------------------------
# OCR preprocessing
# ---------------------------------------------------------------------------

_OPTION_SELECT_WORDS = {"fight", "bag", "pokemon", "run"}


def _is_party_menu(lower_words: list[str]) -> bool:
    """Detect the 'Choose a Pokemon / Cancel' party menu from lowercased OCR words.

    OCR can merge words ('ChooseaPokemon:') or misread characters ('Cance]'),
    so we check for 'pokemon' as a substring of any word and 'cancel' within
    1 Levenshtein edit of any word.
    """
    joined = " ".join(lower_words)
    has_pokemon = "pokemon" in joined
    has_cancel = any(_Lev.distance(w, "cancel") <= 1 for w in lower_words)
    return has_pokemon and has_cancel


def _is_choose_pokemon_prompt(lower_words: list[str]) -> bool:
    """Detect the forced-replacement message-box prompt "Choose a POKéMON.".

    Unlike the party-list screen, this normal-palette prompt has no "Cancel"
    button, so it reaches the matcher as a battle message. It has no template
    (by design); recognizing it as a PARTY_MENU signal avoids a spurious
    UnknownMessageError. Keys on 'choose' + a 'pok...' token so it works whether
    OCR reads 'POKéMON' whole or drops the 'é' into 'pok' + 'mon'.
    """
    if not lower_words or _Lev.distance(lower_words[0], "choose") > 1:
        return False
    return any(w.startswith("pok") for w in lower_words)


def _is_action_prompt(lower_words: list[str]) -> bool:
    """Detect the "What will <mon> do?" action-select prompt.

    The Fight/Bag/Pokemon/Run menu words live in a separate OCR region, so the
    prompt often arrives alone. It's structurally distinctive: starts with
    "What will" and ends with "do?"/"do" (the species in the middle varies).
    Fuzzy (Lev ≤ 1) to tolerate OCR error.
    """
    if len(lower_words) < 3:
        return False
    starts = (
        _Lev.distance(lower_words[0], "what") <= 1
        and _Lev.distance(lower_words[1], "will") <= 1
    )
    last = lower_words[-1].rstrip("?")
    ends = _Lev.distance(last, "do") <= 1
    return starts and ends


def _detect_screen_type(ocr_words: list[str]) -> ScreenKind | None:
    """Identify menu screens from raw OCR words before DP matching."""
    lower = [w.lower() for w in ocr_words]
    if sum(1 for w in lower if w in _OPTION_SELECT_WORDS) >= 3:
        return ScreenKind.OPTION_SELECT
    if _is_action_prompt(lower):
        return ScreenKind.OPTION_SELECT
    has_pp = any(w == "pp" for w in lower)
    has_fraction = any(re.fullmatch(r'\d+/\d+', w) for w in ocr_words)
    if has_pp and has_fraction:
        return ScreenKind.MOVE_SELECT
    if _is_party_menu(lower):
        return ScreenKind.PARTY_MENU
    if _is_choose_pokemon_prompt(lower):
        return ScreenKind.PARTY_MENU
    return None


def _preprocess_ocr(ocr_words: list[str]) -> list[str]:
    """Split trailing '!' off any word that ends with it (OCR fuses '!' with last word).

    Also strips ellipsis (Unicode "…" and ASCII runs of 2+ dots) to stay symmetric
    with template parsing, which strips ellipsis at build time. Words that become
    empty after stripping are dropped.
    """
    result = []
    for w in ocr_words:
        w = w.replace("…", "")
        w = re.sub(r"\.{2,}", "", w)
        if not w:
            continue
        if w.endswith("!") and len(w) > 1:
            result.append(w[:-1])
            result.append("!")
        else:
            result.append(w)
    return result


# ---------------------------------------------------------------------------
# Template expansion helpers
# ---------------------------------------------------------------------------

def _literal_word_tokens(phrase: str) -> list[TemplateToken]:
    """Tokenize a literal phrase into TemplateTokens using the same rules as Template._parse."""
    tokens: list[TemplateToken] = []
    for word in phrase.split():
        if not word:
            continue
        word = word.replace("…", "")
        word = re.sub(r"\.{2,}", "", word)
        if not word:
            continue
        if word.endswith("!") and len(word) > 1:
            tokens.append(TemplateToken(is_var=False, word=word[:-1]))
            tokens.append(TemplateToken(is_var=False, word="!"))
        else:
            tokens.append(TemplateToken(is_var=False, word=word))
    return tokens


def _foe_split(msg: dict, tokens: list) -> list[Template]:
    """Generate the full Foe/no-Foe combination across every NAME_WITH_PREFIX name.

    In trainer battles each Pokémon name renders with a "Foe " prefix when it belongs
    to the opponent and bare when it belongs to the player. A message can name two (or
    more) mons on different sides — e.g. "{X} was poisoned by {Y}'s {ability}!" where X
    is the foe and Y the player, OR the reverse. We therefore emit one template variant
    per Foe/no-Foe assignment over all name placeholders so the right one aligns and the
    "Foe " literal is stripped out of each captured name.

    Previously only single-name templates got a Foe variant; two-name messages (the
    ability-proc *BY family, Bind/Wrap, infatuation, etc.) had no Foe-subject variant,
    so a "Foe X ..." message failed name validation and fell through as an
    UnknownMessageError (crashing the capture loop). Name-var tokens are identified by
    their placeholder so enum/direction overrides earlier in the list can't misalign the
    insertion points.
    """
    positions = [
        i for i, tok in enumerate(tokens)
        if tok.is_var and tok.placeholder in _ANY_PREFIX_PH
    ]
    if not positions:
        return [Template(msg, _tokens_override=tokens)]

    variants: list[Template] = []
    for combo in itertools.product((False, True), repeat=len(positions)):
        new_tokens = list(tokens)
        # Insert right-to-left so earlier insertion indices stay valid.
        for idx, use_foe in sorted(zip(positions, combo), key=lambda x: -x[0]):
            if use_foe:
                new_tokens.insert(idx, TemplateToken(is_var=False, word="Foe"))
        variants.append(Template(msg, _tokens_override=new_tokens))
    return variants


# ---------------------------------------------------------------------------
# Template expansion
# ---------------------------------------------------------------------------

def _build_templates(msg: dict) -> list[Template]:
    """
    Build one or more Template objects from a battle_messages entry.
    Applies:
      - EnumToken substitution for known small-set placeholders
      - Literal direction expansion for stat templates (one variant per phrase)
      - "Foe" literal prefix for single-NAME_WITH_PREFIX templates (generates 2 variants)
      - "!" terminal literal for STRINGID_USEDMOVE
    """
    base = Template(msg)
    tokens = list(base.tokens)

    # Apply EnumToken overrides
    overrides = _ENUM_OVERRIDES.get(msg["string_id"], {})
    if overrides:
        placeholders = msg.get("placeholders", [])
        ph_iter = iter(placeholders)
        new_tokens = []
        for tok in tokens:
            if tok.is_var:
                ph = next(ph_iter, "")
                if ph in overrides:
                    new_tokens.append(TemplateToken(
                        is_var=False,
                        choices=overrides[ph],
                        placeholder=ph,
                    ))
                else:
                    new_tokens.append(tok)
            else:
                new_tokens.append(tok)
        tokens = new_tokens

    # Add "!" terminal for USEDMOVE (game appends "!" to move name at runtime)
    if msg["string_id"] == "STRINGID_USEDMOVE":
        tokens.append(TemplateToken(is_var=False, word="!"))

    # Expand literal direction phrases into separate token-list variants.
    # Each phrase (e.g. "sharply rose!") replaces the named VAR token with literal
    # tokens produced by _literal_word_tokens, yielding one variant per phrase.
    # We find the VAR by placeholder name rather than positional counting because
    # B_BUFF1 was already converted to an Enum token above, so positional counting
    # of var tokens would land on the wrong token.
    dir_overrides = _LITERAL_DIRECTION_OVERRIDES.get(msg["string_id"], {})
    token_variants: list[list] = [tokens]
    if dir_overrides:
        for ph, phrases in dir_overrides.items():
            expanded: list[list] = []
            for toks in token_variants:
                # Find the VAR token for this placeholder.
                var_pos = next(
                    (i for i, tok in enumerate(toks) if tok.is_var and tok.placeholder == ph),
                    None,
                )
                if var_pos is None:
                    expanded.append(toks)
                    continue
                for phrase in sorted(phrases):  # sorted for deterministic order
                    expanded.append(
                        toks[:var_pos] + _literal_word_tokens(phrase) + toks[var_pos + 1:]
                    )
            token_variants = expanded

    # Foe/no-Foe split — cross-producted with direction variants so that each direction
    # phrase also gets both Foe and no-Foe forms.
    result: list[Template] = []
    for toks in token_variants:
        result.extend(_foe_split(msg, toks))
    return result


# ---------------------------------------------------------------------------
# Prefix helpers
# ---------------------------------------------------------------------------

def _is_prefix(a: str, b: str) -> bool:
    """True iff a is a character-level prefix of b (equality counts)."""
    return b.startswith(a)


# ---------------------------------------------------------------------------
# BattleMessageMatcher
# ---------------------------------------------------------------------------

class BattleMessageMatcher:
    """
    Stateful matcher for a stream of OCR captures using prefix-based finalization.

    The emulator renders battle text as a typewriter effect, so consecutive frames
    of the same message are strictly growing character prefixes. A pending frame is
    finalized (matched) only when the next frame's raw string breaks the prefix chain,
    or when flush() is called explicitly at turn boundaries.

    Raises UnknownMessageError if a finalized frame matches no template.
    """

    def __init__(self, save_dir: Optional[str] = None):
        """
        save_dir: if given, error contexts are saved as JSON files here.
        """
        self._templates: list[Template] = [t for m in BATTLE_MESSAGES for t in _build_templates(m)]
        self._save_dir = save_dir
        # Pending-frame state: the most recent text frame not yet confirmed final.
        self._pending_words: list[str] | None = None       # raw ocr_words of pending frame
        self._pending_raw: str | None = None               # raw joined string for prefix compare
        self._pending_constraints: Constraints | None = None  # constraints captured with pending

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, ocr_words: list[str], constraints: Constraints | None = None) -> Optional[MatchResult | ScreenSignal]:
        """
        Process one OCR capture (list of word strings from bounding boxes).

        Uses character-level prefix finalization: a pending frame is finalized only
        when the next frame's raw string is NOT a continuation (prefix) of it.

        Empty frames preserve pending state (the text box blanks between messages).
        Screen signals (OPTION_SELECT, MOVE_SELECT, PARTY_MENU) are returned immediately
        without disturbing pending state; play.py calls flush() at turn boundaries.

        Returns:
          MatchResult        — the NOW-FINALIZED previous message (one frame late)
          ScreenSignal       — if a menu screen is detected
          None               — if the capture is still pending or no text yet

        Raises:
          UnknownMessageError — if a finalized frame matches no template
        """
        if not ocr_words:
            # Preserve pending — box blank before a menu must not drop the last message
            return None

        screen = _detect_screen_type(ocr_words)
        if screen == ScreenKind.OPTION_SELECT:
            return ScreenSignal(ScreenKind.OPTION_SELECT)
        if screen == ScreenKind.MOVE_SELECT:
            return ScreenSignal(ScreenKind.MOVE_SELECT)
        if screen == ScreenKind.PARTY_MENU:
            return ScreenSignal(ScreenKind.PARTY_MENU)

        current_raw = " ".join(ocr_words)

        if self._pending_raw is None:
            # No pending frame yet — store this one
            self._pending_words = ocr_words
            self._pending_raw = current_raw
            self._pending_constraints = constraints
            return None

        if _is_prefix(self._pending_raw, current_raw):
            # Still growing (or identical) — replace pending with current frame
            self._pending_words = ocr_words
            self._pending_raw = current_raw
            self._pending_constraints = constraints
            return None

        # Prefix broken: finalize the OLD pending, store current as new pending
        old_words = self._pending_words
        old_constraints = self._pending_constraints
        self._pending_words = ocr_words
        self._pending_raw = current_raw
        self._pending_constraints = constraints
        return self._finalize(_preprocess_ocr(old_words), old_constraints)

    def flush(self) -> Optional[MatchResult]:
        """Finalize and return any pending frame; return None if nothing is pending."""
        if self._pending_words is None:
            return None
        words = self._pending_words
        constraints = self._pending_constraints
        self._pending_words = None
        self._pending_raw = None
        self._pending_constraints = None
        return self._finalize(_preprocess_ocr(words), constraints)

    def reset(self) -> None:
        """Clear pending state (call between battles)."""
        self._pending_words = None
        self._pending_raw = None
        self._pending_constraints = None

    # ------------------------------------------------------------------
    # Matching internals
    # ------------------------------------------------------------------

    def _finalize(self, words: list[str], constraints: "Constraints | None") -> MatchResult:
        """Match preprocessed words against all templates; raise UnknownMessageError on failure."""
        result = self._try_full_match(words, constraints)
        if result is not None:
            return result
        self._save_error_context(words, None, "no_template_match")
        raise UnknownMessageError(ocr_words=words, reason="no_template_match")

    def _try_full_match(self, words: list[str], constraints: "Constraints | None" = None) -> Optional[MatchResult]:
        """
        Run DP against all templates; return best full match or None.

        Ranking (lower is better):
          1. score (edit-distance on literals/enums)
          2. literal_count descending (more literals = more specific)
          3. context_score (Foe-prefix side mismatch penalty)

        Templates with no literal or enum tokens are excluded to prevent
        absorbing all inputs and defeating partial-capture detection.

        Low-coverage fallback: if the score-winner explains less than
        _MIN_LITERAL_COVERAGE of the OCR words with literals/enums (i.e. it won by
        dumping most of the garbled input into free VARs), re-select among all
        aligning templates the one with the highest literal coverage. This stops a
        var-greedy template (e.g. "For {VAR}, {VAR} {VAR}") from beating a specific,
        literal-heavy template on noisy OCR.
        """
        best: Optional[MatchResult] = None
        best_literals = -1
        results: list[tuple[MatchResult, int]] = []
        candidates = self._filter_candidates(words)
        for tmpl in candidates:
            if tmpl.literal_count == 0 and tmpl.enum_count == 0:
                continue  # skip unconstrained {VAR}-only templates
            r = tmpl.try_align(words, partial=False, constraints=constraints)
            if r is None:
                continue
            results.append((r, tmpl.literal_count))
            if best is None:
                best = r
                best_literals = tmpl.literal_count
            elif r.score < best.score:
                best = r
                best_literals = tmpl.literal_count
            elif r.score == best.score and tmpl.literal_count > best_literals:
                best = r
                best_literals = tmpl.literal_count
            elif r.score == best.score and tmpl.literal_count == best_literals and r.context_score < best.context_score:
                best = r
                best_literals = tmpl.literal_count

        if best is not None and best.literal_coverage < _MIN_LITERAL_COVERAGE:
            # Highest coverage wins; tie-break by the normal ranking
            # (lower score, then more literals, then lower context_score).
            best = max(
                results,
                key=lambda rl: (
                    rl[0].literal_coverage,
                    -rl[0].score,
                    rl[1],
                    -rl[0].context_score,
                ),
            )[0]
        return best

    def _filter_candidates(self, words: list[str]) -> list[Template]:
        """
        Cheap O(N) pre-filter: skip templates whose segment counts make a valid
        alignment impossible given the OCR word count.
        """
        n = len(words)
        return [
            t for t in self._templates
            if t.min_words <= n <= (t.literal_count + t.enum_count * 3 + t.var_count * 3 + 1)
        ]

    # ------------------------------------------------------------------
    # Error context saving
    # ------------------------------------------------------------------

    def _save_error_context(
        self,
        ocr_words:      list[str],
        matched_words:  Optional[list[str]],
        reason:         str,
    ) -> None:
        if not self._save_dir:
            return
        os.makedirs(self._save_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = os.path.join(self._save_dir, f"matcher_error_{ts}.json")
        payload = {
            "timestamp":     ts,
            "reason":        reason,
            "ocr_words":     ocr_words,
            "matched_words": matched_words,
        }
        with open(path, "w") as fh:
            json.dump(payload, fh, indent=2)


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    matcher = BattleMessageMatcher()

    # Test 1: stability requires two identical captures
    words = ["A", "critical", "hit!"]
    matcher.process(words)
    r1 = matcher.process(words)
    print(f"Test 1 — critical hit: string_id={r1.string_id if r1 else None!r}  "
          f"(expect STRINGID_CRITICALHIT)")

    # Test 2: stability requires two identical captures for TARGETFAINTED
    m2 = BattleMessageMatcher()
    words2 = ["Foe", "PIKACHU", "fainted!"]
    m2.process(words2)
    r2 = m2.process(words2)
    print(f"Test 2 — target fainted: string_id={r2.string_id if r2 else None!r}  "
          f"(expect STRINGID_TARGETFAINTED)")
