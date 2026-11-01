"""Baseline A (no trace) and Baseline B (full trace) stubs.

Both reuse the LLMJudge interface. Without an API key they fall back to the
deterministic judge so evaluation wiring can be tested offline.
"""

from __future__ import annotations

from evidence_ledger.claims.llm_judge import DeterministicJudge, LLMJudge, JudgeResult
from evidence_ledger.models import LedgerEntry, Verdict


class BaselineAJudge(LLMJudge):
    """Answer-only judge: deliberately ignores the trace."""

    def __init__(self, inner: LLMJudge | None = None) -> None:
        self.inner = inner or DeterministicJudge()

    def assess(self, claim_text: str, entries: list[LedgerEntry]) -> JudgeResult:
        _ = entries
        # Without trace, mark as PARTIALLY_SUPPORTED unless the claim is empty.
        if not claim_text.strip():
            return JudgeResult(Verdict.UNSUPPORTED, "empty claim", model_id="baseline-a")
        return JudgeResult(
            Verdict.PARTIALLY_SUPPORTED,
            "Baseline A has no tool trace; cannot confirm support",
            model_id="baseline-a",
        )


class BaselineBJudge(LLMJudge):
    """Full-trace judge: delegates to the configured judge with all entries."""

    def __init__(self, inner: LLMJudge | None = None) -> None:
        self.inner = inner or DeterministicJudge()

    def assess(self, claim_text: str, entries: list[LedgerEntry]) -> JudgeResult:
        return self.inner.assess(claim_text, entries)
