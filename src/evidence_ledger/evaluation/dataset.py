"""Scenario / ground-truth loaders."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_jsonl(path: Path | str) -> list[dict[str, Any]]:
    p = Path(path)
    rows: list[dict[str, Any]] = []
    if not p.exists():
        return rows
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows
