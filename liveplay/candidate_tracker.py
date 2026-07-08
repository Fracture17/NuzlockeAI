# CandidateTracker: manages the active candidate pool across turn generations.
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from liveplay.candidate import Candidate


class CandidateTracker:
    """Tracks the live candidate pool, supporting deduplication and pruning of dead branches."""

    def __init__(self, initial_candidates: list[Candidate]):
        self._candidates: list[Candidate] = list(initial_candidates)

    @property
    def candidates(self) -> list[Candidate]:
        return list(self._candidates)

    def __len__(self) -> int:
        return len(self._candidates)

    @property
    def is_resolved(self) -> bool:
        return len(self._candidates) == 1

    def update(self, new_candidates: list[Candidate]) -> None:
        self._candidates = list(new_candidates)

    def deduplicate(self) -> None:
        """Remove duplicate candidates by state equality (hash + __eq__), keeping first occurrence."""
        seen: set = set()
        unique: list[Candidate] = []
        for candidate in self._candidates:
            if candidate.state not in seen:
                seen.add(candidate.state)
                unique.append(candidate)
        self._candidates = unique

    def prune_empty(self, new_candidates: list[Candidate]) -> list[Candidate]:
        """Remove candidates with no children in new_candidates; returns the pruned list.

        Uses id() matching to identify parent-child relationships, so distinct objects
        that compare equal are treated as separate parents.
        """
        parent_ids = {id(nc.parent_candidate) for nc in new_candidates}
        kept: list[Candidate] = []
        pruned: list[Candidate] = []
        for candidate in self._candidates:
            if id(candidate) in parent_ids:
                kept.append(candidate)
            else:
                pruned.append(candidate)
        self._candidates = kept
        return pruned
