"""Evidence ledger: append + verify with SHA-256 linear hash chain."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from evidence_ledger.config import Settings, get_settings
from evidence_ledger.hashing import GENESIS_V1, hash_payload
from evidence_ledger.models import (
    ChainVerifyResult,
    EntryStatus,
    IntegrityStatus,
    LedgerEntry,
)
from evidence_ledger.storage import StorageBackend, create_storage


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def build_protected_payload(
    *,
    session_id: str,
    sequence_no: int,
    entry_id: str,
    timestamp_utc: str,
    tool_name: str,
    input_json: Any,
    output_json: Any,
    status: str,
    error_info: Any,
    schema_version: int,
    previous_hash: str,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "sequence_no": sequence_no,
        "entry_id": entry_id,
        "timestamp_utc": timestamp_utc,
        "tool_name": tool_name,
        "input_json": input_json,
        "output_json": output_json,
        "status": status,
        "error_info": error_info,
        "schema_version": schema_version,
        "previous_hash": previous_hash,
    }


class EvidenceLedger:
    def __init__(
        self,
        storage: StorageBackend | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.storage = storage or create_storage(
            self.settings.ledger_storage_backend,
            self.settings.resolved_db_path(),
        )
        self.genesis = self.settings.genesis_marker or GENESIS_V1

    def init(self) -> None:
        self.storage.init_schema()

    def create_session(self, session_id: str | None = None) -> str:
        return session_id or str(uuid.uuid4())

    def append(
        self,
        session_id: str,
        tool_name: str,
        input_json: Any,
        output_json: Any = None,
        status: EntryStatus | str = EntryStatus.SUCCESS,
        error_info: dict[str, Any] | None = None,
        timestamp_utc: str | None = None,
        entry_id: str | None = None,
    ) -> LedgerEntry:
        if isinstance(status, str):
            status = EntryStatus(status)

        # Transactional sequence/hash allocation lives in storage backends that
        # take a lock around read-latest + insert (SQLiteStorage).
        last = self.storage.get_latest(session_id)
        sequence_no = 1 if last is None else last.sequence_no + 1
        previous_hash = self.genesis if last is None else last.entry_hash
        entry_id = entry_id or f"{session_id}:{sequence_no}"
        timestamp_utc = timestamp_utc or utc_now_iso()
        schema_version = self.settings.schema_version

        payload = build_protected_payload(
            session_id=session_id,
            sequence_no=sequence_no,
            entry_id=entry_id,
            timestamp_utc=timestamp_utc,
            tool_name=tool_name,
            input_json=input_json,
            output_json=output_json,
            status=status.value,
            error_info=error_info,
            schema_version=schema_version,
            previous_hash=previous_hash,
        )
        digest = hash_payload(payload)
        entry = LedgerEntry(
            session_id=payload["session_id"],
            sequence_no=payload["sequence_no"],
            entry_id=payload["entry_id"],
            timestamp_utc=payload["timestamp_utc"],
            tool_name=payload["tool_name"],
            input_json=payload["input_json"],
            output_json=payload["output_json"],
            status=status,
            error_info=payload["error_info"],
            schema_version=payload["schema_version"],
            previous_hash=payload["previous_hash"],
            entry_hash=digest,
        )
        return self.storage.append_entry(entry)

    def list_entries(self, session_id: str) -> list[LedgerEntry]:
        return self.storage.list_entries(session_id)

    def get_entry(self, entry_id: str) -> LedgerEntry | None:
        return self.storage.get_entry(entry_id)

    def verify(self, session_id: str) -> ChainVerifyResult:
        entries = self.storage.list_entries(session_id)
        if not entries:
            return ChainVerifyResult(
                status=IntegrityStatus.VALID,
                entries_checked=0,
                reason="empty session",
                chain_head=self.genesis,
            )

        expected_previous = self.genesis
        expected_sequence = 1
        for entry in entries:
            if entry.sequence_no != expected_sequence:
                return ChainVerifyResult(
                    status=IntegrityStatus.INVALID,
                    entries_checked=expected_sequence - 1,
                    first_failing_sequence=entry.sequence_no,
                    reason="sequence gap/order",
                )
            if entry.previous_hash != expected_previous:
                return ChainVerifyResult(
                    status=IntegrityStatus.INVALID,
                    entries_checked=expected_sequence - 1,
                    first_failing_sequence=entry.sequence_no,
                    reason="previous hash mismatch",
                )
            payload = build_protected_payload(
                session_id=entry.session_id,
                sequence_no=entry.sequence_no,
                entry_id=entry.entry_id,
                timestamp_utc=entry.timestamp_utc,
                tool_name=entry.tool_name,
                input_json=entry.input_json,
                output_json=entry.output_json,
                status=entry.status.value if isinstance(entry.status, EntryStatus) else entry.status,
                error_info=entry.error_info,
                schema_version=entry.schema_version,
                previous_hash=entry.previous_hash,
            )
            recomputed = hash_payload(payload)
            if recomputed != entry.entry_hash:
                return ChainVerifyResult(
                    status=IntegrityStatus.INVALID,
                    entries_checked=expected_sequence - 1,
                    first_failing_sequence=entry.sequence_no,
                    reason="entry hash mismatch",
                )
            expected_previous = entry.entry_hash
            expected_sequence += 1

        return ChainVerifyResult(
            status=IntegrityStatus.VALID,
            entries_checked=len(entries),
            chain_head=expected_previous,
        )

    def session(self, session_id: str | None = None) -> "BoundSession":
        """Create/bind a session and return a handle with ``@session.tool``."""
        from evidence_ledger.integration import BoundSession

        sid = self.create_session(session_id)
        self.init()
        return BoundSession(self, sid)

    def tool(
        self,
        session_id: str,
        *,
        name: str | None = None,
        reraise: bool = True,
    ):
        """Decorator: ``@ledger.tool(session_id)`` records every call."""
        from evidence_ledger.integration import wrap_tool

        return wrap_tool(self, session_id, name=name, reraise=reraise)

