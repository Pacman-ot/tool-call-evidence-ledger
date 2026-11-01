"""Atomic claim decomposition.

Default implementation is a deterministic sentence splitter suitable for the
research prototype and unit tests. An LLM-backed decomposer can be plugged in
behind the same interface when API keys are available.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from evidence_ledger.claims.taxonomy import infer_claim_type
from evidence_ledger.models import AtomicClaim


class ClaimDecomposer(ABC):
    @abstractmethod
    def decompose(self, answer: str) -> list[AtomicClaim]: ...


class HeuristicDecomposer(ClaimDecomposer):
    """Split on sentence boundaries; assign stable C1..Cn IDs."""

    _SPLIT = re.compile(r"(?<=[.!?])\s+")

    def decompose(self, answer: str) -> list[AtomicClaim]:
        text = (answer or "").strip()
        if not text:
            return []
        parts = [p.strip() for p in self._SPLIT.split(text) if p.strip()]
        claims: list[AtomicClaim] = []
        for i, part in enumerate(parts, start=1):
            # Drop trailing punctuation for claim text stability? keep original.
            claims.append(
                AtomicClaim(
                    claim_id=f"C{i}",
                    claim_text=part,
                    claim_type=infer_claim_type(part),
                )
            )
        return claims
