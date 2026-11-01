"""Typed schemas and enums for the evidence ledger."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EntryStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class ClaimType(str, Enum):
    DIRECT_NUMERIC = "direct_numeric"
    DERIVED = "derived"
    PARAPHRASED = "paraphrased"
    OTHER = "other"


class Verdict(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"


class MatchDecision(str, Enum):
    MATCH_SUPPORTED = "MATCH_SUPPORTED"
    MATCH_CONTRADICTED = "MATCH_CONTRADICTED"
    UNRESOLVED = "UNRESOLVED"


class VerificationMethod(str, Enum):
    STRUCTURED_DIRECT = "structured_direct"
    STRUCTURED_DERIVED = "structured_derived"
    LLM_JUDGE = "llm_judge"
    PROCESSING_ERROR = "processing_error"


class IntegrityStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"


class EvidencePointer(BaseModel):
    entry_id: str
    field_path: str


class LedgerEntry(BaseModel):
    session_id: str
    sequence_no: int
    entry_id: str
    timestamp_utc: str
    tool_name: str
    input_json: Any
    output_json: Any | None = None
    status: EntryStatus
    error_info: dict[str, Any] | None = None
    schema_version: int
    previous_hash: str
    entry_hash: str


class ChainVerifyResult(BaseModel):
    status: IntegrityStatus
    entries_checked: int = 0
    first_failing_sequence: int | None = None
    reason: str | None = None
    chain_head: str | None = None


class AtomicClaim(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: ClaimType = ClaimType.OTHER


class ClaimVerdict(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: ClaimType
    verdict: Verdict
    method: VerificationMethod
    evidence: list[EvidencePointer] = Field(default_factory=list)
    rationale: str = ""
    confidence: float | None = None
    processing_error: str | None = None


class AnswerVerificationReport(BaseModel):
    session_id: str
    chain_integrity: ChainVerifyResult
    claims: list[ClaimVerdict]
    aggregate_status: str

    @staticmethod
    def aggregate(chain: ChainVerifyResult, claims: list[ClaimVerdict]) -> str:
        if chain.status != IntegrityStatus.VALID:
            return "INTEGRITY_FAILURE"
        if not claims:
            return "NO_CLAIMS"
        if any(c.verdict == Verdict.UNSUPPORTED for c in claims):
            return "HAS_UNSUPPORTED"
        if any(c.verdict == Verdict.PARTIALLY_SUPPORTED for c in claims):
            return "PARTIALLY_SUPPORTED"
        return "FULLY_SUPPORTED"


class ToolInvokeResult(BaseModel):
    tool_name: str
    output: Any | None = None
    status: EntryStatus
    error_info: dict[str, Any] | None = None
    entry_id: str | None = None
    entry_hash: str | None = None
