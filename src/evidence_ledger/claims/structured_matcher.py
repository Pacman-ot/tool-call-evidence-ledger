"""Structured matching: direct numeric/entity + fixed derivations."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from evidence_ledger.claims.derivations import (
    DerivationError,
    derive_date_delta_days,
    derive_percentage_change,
    derive_ratio,
    derive_sum,
)
from evidence_ledger.models import EvidencePointer, LedgerEntry, MatchDecision


@dataclass
class MatchResult:
    decision: MatchDecision
    evidence: list[EvidencePointer] = field(default_factory=list)
    method: str = "structured_direct"
    rationale: str = ""
    computed_value: Any = None


_NUM = re.compile(r"(?<![A-Za-z])(-?\d+(?:\.\d+)?)(%?)(?![A-Za-z])")
_PCT_CHANGE = re.compile(
    r"(?i)(?:increased|decreased|changed|grew|rose|fell)\s+by\s+(-?\d+(?:\.\d+)?)\s*%"
)
_RATIO = re.compile(r"(?i)ratio\s+(?:of\s+)?(-?\d+(?:\.\d+)?)\s*(?:to|:|/)")
_SUM = re.compile(r"(?i)sum(?:\s+of)?\s+(?:is\s+)?(-?\d+(?:\.\d+)?)")
_DAYS = re.compile(r"(?i)(-?\d+)\s+days?\s+(?:between|apart|difference)")


def _flatten(obj: Any, prefix: str) -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            out.extend(_flatten(v, path))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(_flatten(v, f"{prefix}[{i}]"))
    else:
        out.append((prefix, obj))
    return out


def _collect_fields(entries: list[LedgerEntry]) -> list[tuple[str, str, Any]]:
    """Return (entry_id, json_path, value) for output and input leaves."""
    fields: list[tuple[str, str, Any]] = []
    for e in entries:
        for path, val in _flatten(e.output_json, "$.output"):
            fields.append((e.entry_id, path, val))
        for path, val in _flatten(e.input_json, "$.input"):
            fields.append((e.entry_id, path, val))
    return fields


def _nums_close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol or (b != 0 and abs(a - b) / abs(b) <= tol)


class StructuredMatcher:
    def __init__(self, numeric_tolerance: float = 1e-6) -> None:
        self.tol = numeric_tolerance

    def match(self, claim_text: str, entries: list[LedgerEntry]) -> MatchResult:
        fields = _collect_fields(entries)

        # Derived: percentage change
        m = _PCT_CHANGE.search(claim_text)
        if m:
            claimed = float(m.group(1))
            if "decreased" in claim_text.lower() or "fell" in claim_text.lower():
                claimed = -abs(claimed)
            olds = [(eid, p, v) for eid, p, v in fields if str(p).endswith("old_value") and isinstance(v, (int, float))]
            news = [(eid, p, v) for eid, p, v in fields if str(p).endswith("new_value") and isinstance(v, (int, float))]
            if olds and news:
                try:
                    computed = derive_percentage_change(olds[0][2], news[0][2])
                    evidence = [
                        EvidencePointer(entry_id=olds[0][0], field_path=olds[0][1]),
                        EvidencePointer(entry_id=news[0][0], field_path=news[0][1]),
                    ]
                    if _nums_close(computed, claimed, self.tol):
                        return MatchResult(
                            MatchDecision.MATCH_SUPPORTED,
                            evidence=evidence,
                            method="structured_derived",
                            rationale=f"percentage_change matched: computed={computed}",
                            computed_value=computed,
                        )
                    return MatchResult(
                        MatchDecision.MATCH_CONTRADICTED,
                        evidence=evidence,
                        method="structured_derived",
                        rationale=f"percentage_change contradicted: computed={computed}, claimed={claimed}",
                        computed_value=computed,
                    )
                except DerivationError as exc:
                    return MatchResult(
                        MatchDecision.UNRESOLVED,
                        rationale=f"derivation error: {exc}",
                        method="structured_derived",
                    )

        # Derived: date delta
        m = _DAYS.search(claim_text)
        if m:
            claimed_days = int(m.group(1))
            starts = [(eid, p, v) for eid, p, v in fields if "start" in p.lower()]
            ends = [(eid, p, v) for eid, p, v in fields if "end" in p.lower()]
            if starts and ends:
                try:
                    computed = derive_date_delta_days(starts[0][2], ends[0][2])
                    evidence = [
                        EvidencePointer(entry_id=starts[0][0], field_path=starts[0][1]),
                        EvidencePointer(entry_id=ends[0][0], field_path=ends[0][1]),
                    ]
                    if computed == claimed_days:
                        return MatchResult(
                            MatchDecision.MATCH_SUPPORTED,
                            evidence=evidence,
                            method="structured_derived",
                            rationale=f"date_delta_days matched: {computed}",
                            computed_value=computed,
                        )
                    return MatchResult(
                        MatchDecision.MATCH_CONTRADICTED,
                        evidence=evidence,
                        method="structured_derived",
                        rationale=f"date_delta_days contradicted: {computed} vs {claimed_days}",
                        computed_value=computed,
                    )
                except DerivationError as exc:
                    return MatchResult(MatchDecision.UNRESOLVED, rationale=str(exc), method="structured_derived")

        # Derived: sum of numeric fields when claim says "sum"
        m = _SUM.search(claim_text)
        if m:
            claimed = float(m.group(1))
            nums = [(eid, p, v) for eid, p, v in fields if isinstance(v, (int, float)) and not isinstance(v, bool)]
            if len(nums) >= 2:
                try:
                    # Prefer explicit a/b/result style: sum of a and b vs claimed
                    values = [v for _, _, v in nums if True]
                    # Heuristic: if claim sum equals sum of two numbers present, use those
                    for i in range(len(nums)):
                        for j in range(i + 1, len(nums)):
                            computed = derive_sum([nums[i][2], nums[j][2]])
                            if _nums_close(computed, claimed, self.tol):
                                evidence = [
                                    EvidencePointer(entry_id=nums[i][0], field_path=nums[i][1]),
                                    EvidencePointer(entry_id=nums[j][0], field_path=nums[j][1]),
                                ]
                                return MatchResult(
                                    MatchDecision.MATCH_SUPPORTED,
                                    evidence=evidence,
                                    method="structured_derived",
                                    rationale=f"sum matched: {computed}",
                                    computed_value=computed,
                                )
                    # No pair matched — contradict if any pair is close-ish? leave unresolved unless single total field.
                except DerivationError:
                    pass

        # Derived: ratio
        m = _RATIO.search(claim_text)
        if m:
            claimed = float(m.group(1))
            nums = [(eid, p, v) for eid, p, v in fields if isinstance(v, (int, float)) and not isinstance(v, bool)]
            for i in range(len(nums)):
                for j in range(len(nums)):
                    if i == j:
                        continue
                    try:
                        computed = derive_ratio(nums[i][2], nums[j][2])
                    except DerivationError:
                        continue
                    if _nums_close(computed, claimed, self.tol):
                        return MatchResult(
                            MatchDecision.MATCH_SUPPORTED,
                            evidence=[
                                EvidencePointer(entry_id=nums[i][0], field_path=nums[i][1]),
                                EvidencePointer(entry_id=nums[j][0], field_path=nums[j][1]),
                            ],
                            method="structured_derived",
                            rationale=f"ratio matched: {computed}",
                            computed_value=computed,
                        )

        # Direct numeric / entity
        claimed_nums: list[tuple[float, bool]] = []
        for m in _NUM.finditer(claim_text):
            # skip if part of percentage-change phrase already handled
            val = float(m.group(1))
            is_pct = m.group(2) == "%"
            claimed_nums.append((val, is_pct))

        numeric_fields = [
            (eid, p, float(v))
            for eid, p, v in fields
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        ]
        string_fields = [(eid, p, str(v)) for eid, p, v in fields if isinstance(v, str)]

        if claimed_nums:
            # Prefer non-percent claim numbers against numeric fields
            for claimed, is_pct in claimed_nums:
                if is_pct:
                    continue
                for eid, path, val in numeric_fields:
                    if _nums_close(val, claimed, self.tol):
                        return MatchResult(
                            MatchDecision.MATCH_SUPPORTED,
                            evidence=[EvidencePointer(entry_id=eid, field_path=path)],
                            method="structured_direct",
                            rationale=f"numeric field {path}={val} matches claim",
                            computed_value=val,
                        )
            # Contradiction: claim contains a number and a similarly named count field differs
            count_fields = [(eid, p, v) for eid, p, v in numeric_fields if p.rstrip("]").endswith("count") or p.endswith("result")]
            if count_fields and claimed_nums:
                claimed, _ = next((c for c in claimed_nums if not c[1]), claimed_nums[0])
                eid, path, val = count_fields[0]
                if not _nums_close(val, claimed, self.tol):
                    return MatchResult(
                        MatchDecision.MATCH_CONTRADICTED,
                        evidence=[EvidencePointer(entry_id=eid, field_path=path)],
                        method="structured_direct",
                        rationale=f"numeric contradiction: {path}={val} vs claimed={claimed}",
                        computed_value=val,
                    )

        # Entity / string containment (conservative)
        lower_claim = claim_text.lower()
        for eid, path, val in string_fields:
            if val and val.lower() in lower_claim:
                return MatchResult(
                    MatchDecision.MATCH_SUPPORTED,
                    evidence=[EvidencePointer(entry_id=eid, field_path=path)],
                    method="structured_direct",
                    rationale=f"entity/value string match on {path}",
                    computed_value=val,
                )

        return MatchResult(
            MatchDecision.UNRESOLVED,
            rationale="no structured match or contradiction found",
            method="structured_direct",
        )
