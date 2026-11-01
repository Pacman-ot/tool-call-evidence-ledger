"""Hybrid verifier: integrity → decompose → structured match → LLM judge."""

from __future__ import annotations

from evidence_ledger.claims.decomposer import ClaimDecomposer, HeuristicDecomposer
from evidence_ledger.claims.llm_judge import LLMJudge, build_judge
from evidence_ledger.claims.structured_matcher import StructuredMatcher
from evidence_ledger.config import Settings, get_settings
from evidence_ledger.ledger import EvidenceLedger
from evidence_ledger.models import (
    AnswerVerificationReport,
    ClaimType,
    ClaimVerdict,
    IntegrityStatus,
    MatchDecision,
    Verdict,
    VerificationMethod,
)


class HybridVerifier:
    def __init__(
        self,
        ledger: EvidenceLedger,
        decomposer: ClaimDecomposer | None = None,
        matcher: StructuredMatcher | None = None,
        judge: LLMJudge | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.ledger = ledger
        self.settings = settings or get_settings()
        self.decomposer = decomposer or HeuristicDecomposer()
        self.matcher = matcher or StructuredMatcher(self.settings.numeric_tolerance)
        self.judge = judge or build_judge(
            enabled=self.settings.llm_judge_enabled,
            api_key=self.settings.openai_api_key,
            model=self.settings.llm_model,
        )

    def verify(self, session_id: str, answer: str) -> AnswerVerificationReport:
        chain = self.ledger.verify(session_id)
        entries = self.ledger.list_entries(session_id)

        claims_out: list[ClaimVerdict] = []
        try:
            atomic = self.decomposer.decompose(answer)
        except Exception as exc:  # noqa: BLE001
            report_claims = [
                ClaimVerdict(
                    claim_id="C0",
                    claim_text=answer,
                    claim_type=ClaimType.OTHER,
                    verdict=Verdict.UNSUPPORTED,
                    method=VerificationMethod.PROCESSING_ERROR,
                    rationale="decomposition failed",
                    processing_error=str(exc),
                )
            ]
            return AnswerVerificationReport(
                session_id=session_id,
                chain_integrity=chain,
                claims=report_claims,
                aggregate_status=AnswerVerificationReport.aggregate(chain, report_claims),
            )

        # If chain is invalid, still produce claim reports but mark integrity failure.
        for claim in atomic:
            if chain.status != IntegrityStatus.VALID:
                claims_out.append(
                    ClaimVerdict(
                        claim_id=claim.claim_id,
                        claim_text=claim.claim_text,
                        claim_type=claim.claim_type,
                        verdict=Verdict.UNSUPPORTED,
                        method=VerificationMethod.PROCESSING_ERROR,
                        rationale="ledger chain integrity failure; evidence not trusted",
                        processing_error=chain.reason,
                    )
                )
                continue

            match = self.matcher.match(claim.claim_text, entries)
            if match.decision == MatchDecision.MATCH_SUPPORTED:
                claims_out.append(
                    ClaimVerdict(
                        claim_id=claim.claim_id,
                        claim_text=claim.claim_text,
                        claim_type=claim.claim_type,
                        verdict=Verdict.SUPPORTED,
                        method=(
                            VerificationMethod.STRUCTURED_DERIVED
                            if match.method == "structured_derived"
                            else VerificationMethod.STRUCTURED_DIRECT
                        ),
                        evidence=match.evidence,
                        rationale=match.rationale,
                    )
                )
                continue
            if match.decision == MatchDecision.MATCH_CONTRADICTED:
                claims_out.append(
                    ClaimVerdict(
                        claim_id=claim.claim_id,
                        claim_text=claim.claim_text,
                        claim_type=claim.claim_type,
                        verdict=Verdict.UNSUPPORTED,
                        method=(
                            VerificationMethod.STRUCTURED_DERIVED
                            if match.method == "structured_derived"
                            else VerificationMethod.STRUCTURED_DIRECT
                        ),
                        evidence=match.evidence,
                        rationale=match.rationale,
                    )
                )
                continue

            # Unresolved → LLM judge fallback
            judged = self.judge.assess(claim.claim_text, entries)
            claims_out.append(
                ClaimVerdict(
                    claim_id=claim.claim_id,
                    claim_text=claim.claim_text,
                    claim_type=claim.claim_type,
                    verdict=judged.verdict,
                    method=VerificationMethod.LLM_JUDGE,
                    evidence=judged.evidence,
                    rationale=judged.rationale,
                )
            )

        return AnswerVerificationReport(
            session_id=session_id,
            chain_integrity=chain,
            claims=claims_out,
            aggregate_status=AnswerVerificationReport.aggregate(chain, claims_out),
        )
