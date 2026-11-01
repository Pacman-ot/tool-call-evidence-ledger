"""Fixed derivation registry: sum, ratio, percentage change, date delta."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable


class DerivationError(ValueError):
    pass


def _as_number(v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise DerivationError(f"not a number: {v!r}")
    return float(v)


def derive_sum(values: list[Any]) -> float:
    return sum(_as_number(v) for v in values)


def derive_ratio(numerator: Any, denominator: Any) -> float:
    num = _as_number(numerator)
    den = _as_number(denominator)
    if den == 0:
        raise DerivationError("zero denominator")
    return num / den


def derive_percentage_change(old: Any, new: Any) -> float:
    old_v = _as_number(old)
    new_v = _as_number(new)
    if old_v == 0:
        raise DerivationError("old value is zero")
    return (new_v - old_v) / old_v * 100.0


def _parse_date(v: Any) -> date:
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        return date.fromisoformat(v[:10])
    raise DerivationError(f"not a date: {v!r}")


def derive_date_delta_days(start: Any, end: Any) -> int:
    """Exclusive end-start difference in whole days (end - start)."""
    return (_parse_date(end) - _parse_date(start)).days


DERIVATIONS: dict[str, Callable[..., Any]] = {
    "sum": derive_sum,
    "ratio": derive_ratio,
    "percentage_change": derive_percentage_change,
    "date_delta_days": derive_date_delta_days,
}
