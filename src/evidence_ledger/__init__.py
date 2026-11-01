"""Tool Call Evidence Ledger — tamper-evident tool traces for agentic AI.

Quickstart::

    from evidence_ledger import EvidenceLedger

    ledger = EvidenceLedger()
    session = ledger.session()

    @session.tool
    def lookup(key: str) -> dict:
        return {"orders": 42}.get(key) or {"error": "missing"}

    lookup("orders")
    print(session.ledger.verify(session.session_id))
"""

from __future__ import annotations

from evidence_ledger.integration import BoundSession, wrap_tool
from evidence_ledger.ledger import EvidenceLedger
from evidence_ledger.models import (
    AnswerVerificationReport,
    ChainVerifyResult,
    EntryStatus,
    IntegrityStatus,
    LedgerEntry,
    ToolInvokeResult,
    Verdict,
)
from evidence_ledger.storage import (
    JSONLStorage,
    SQLiteStorage,
    StorageBackend,
    create_storage,
)
from evidence_ledger.tools.adapter import ToolAdapter
from evidence_ledger.verify import verify_answer, verify_chain

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # Core
    "EvidenceLedger",
    "BoundSession",
    "wrap_tool",
    "ToolAdapter",
    # Verification
    "verify_chain",
    "verify_answer",
    # Storage
    "StorageBackend",
    "SQLiteStorage",
    "JSONLStorage",
    "create_storage",
    # Models (common)
    "LedgerEntry",
    "EntryStatus",
    "IntegrityStatus",
    "ChainVerifyResult",
    "AnswerVerificationReport",
    "ToolInvokeResult",
    "Verdict",
]
