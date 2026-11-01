"""Export helpers for evaluation results."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def export_json(path: Path | str, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def export_records_csv(path: Path | str, records: list[dict[str, Any]]) -> None:
    if not records:
        Path(path).write_text("", encoding="utf-8")
        return
    keys = list(records[0].keys())
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(records)
