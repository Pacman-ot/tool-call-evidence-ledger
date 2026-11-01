"""Vercel serverless entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is importable when Vercel does not install the package editable.
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mangum import Mangum

from evidence_ledger.api import app

handler = Mangum(app, lifespan="off")

__all__ = ["app", "handler"]
