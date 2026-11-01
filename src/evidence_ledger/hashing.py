"""Fixed SHA-256 helper. Algorithm is intentionally not pluggable."""

from __future__ import annotations

import hashlib
from typing import Any

from evidence_ledger.canonicalize import canonicalize_bytes


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_payload(payload: dict[str, Any]) -> str:
    """SHA-256 of canonical JSON UTF-8 bytes for a protected payload."""
    return sha256_hex(canonicalize_bytes(payload))


GENESIS_V1 = "GENESIS_V1"
