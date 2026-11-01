"""In-memory lookup DB toy tool."""

from __future__ import annotations

from typing import Any

_DB: dict[str, Any] = {
    "orders": {"count": 42, "status": "ok", "region": "west"},
    "users": {"count": 17, "status": "ok", "region": "east"},
    "incidents": {
        "count": 3,
        "status": "degraded",
        "old_value": 100,
        "new_value": 120,
        "start_date": "2026-01-01",
        "end_date": "2026-01-11",
    },
}


def lookup_db(args: dict[str, Any]) -> dict[str, Any]:
    key = args.get("key")
    if not isinstance(key, str):
        raise ValueError("key must be a string")
    if key not in _DB:
        raise KeyError(f"unknown key: {key}")
    record = dict(_DB[key])
    field = args.get("field")
    if field is not None:
        if field not in record:
            raise KeyError(f"unknown field: {field}")
        return {"key": key, "field": field, "value": record[field], **{field: record[field]}}
    return {"key": key, **record}
