"""Top-level verification helpers."""

from __future__ import annotations

from evidence_ledger.claims.verifier import HybridVerifier
from evidence_ledger.ledger import EvidenceLedger
from evidence_ledger.models import AnswerVerificationReport, ChainVerifyResult


def verify_chain(
    session_id: str,
    ledger: EvidenceLedger | None = None,
) -> ChainVerifyResult:
    """Verify the SHA-256 hash chain for a session."""
    lg = ledger or EvidenceLedger()
    lg.init()
    return lg.verify(session_id)


def verify_answer(
    session_id: str,
    answer: str,
    ledger: EvidenceLedger | None = None,
) -> AnswerVerificationReport:
    """Run hybrid claim verification of ``answer`` against the session ledger."""
    lg = ledger or EvidenceLedger()
    lg.init()
    return HybridVerifier(lg).verify(session_id, answer)
