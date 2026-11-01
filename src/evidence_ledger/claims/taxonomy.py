"""Claim type helpers."""

from __future__ import annotations

import re

from evidence_ledger.models import ClaimType


_NUMERIC = re.compile(
    r"(?i)(?:increased|decreased|changed)\s+by\s+(-?\d+(?:\.\d+)?)\s*%|"
    r"(-?\d+(?:\.\d+)?)\s*%|"
    r"(?<![A-Za-z])(-?\d+(?:\.\d+)?)(?![A-Za-z%])"
)


def infer_claim_type(text: str) -> ClaimType:
    lower = text.lower()
    if any(k in lower for k in ("increased by", "decreased by", "ratio", "sum of", "days between", "difference")):
        return ClaimType.DERIVED
    if _NUMERIC.search(text):
        return ClaimType.DIRECT_NUMERIC
    return ClaimType.PARAPHRASED
