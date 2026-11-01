"""Pluggable ledger storage backends.

SQLite is the default for local research runs. On Vercel the filesystem is
ephemeral: use LEDGER_DB_PATH=/tmp/ledger.db (auto-selected when VERCEL=1).
JSONL is available for simple file dumps / debugging.
Do not provision paid remote storage without explicit user approval.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from evidence_ledger.models import EntryStatus, LedgerEntry


class StorageBackend(ABC):
    @abstractmethod
    def init_schema(self) -> None: ...

    @abstractmethod
    def append_entry(self, entry: LedgerEntry) -> LedgerEntry: ...

    @abstractmethod
    def get_latest(self, session_id: str) -> LedgerEntry | None: ...

    @abstractmethod
    def list_entries(self, session_id: str) -> list[LedgerEntry]: ...

    @abstractmethod
    def get_entry(self, entry_id: str) -> LedgerEntry | None: ...

    @abstractmethod
    def update_entry_raw(self, entry_id: str, **fields: Any) -> None:
        """Test/tamper helper: mutate stored fields without rehashing."""

    @abstractmethod
    def delete_entry(self, entry_id: str) -> None: ...


class SQLiteStorage(StorageBackend):
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS ledger_entries (
                  session_id TEXT NOT NULL,
                  sequence_no INTEGER NOT NULL,
                  entry_id TEXT NOT NULL UNIQUE,
                  timestamp_utc TEXT NOT NULL,
                  tool_name TEXT NOT NULL,
                  input_json TEXT NOT NULL,
                  output_json TEXT,
                  status TEXT NOT NULL,
                  error_info TEXT,
                  schema_version INTEGER NOT NULL,
                  previous_hash TEXT NOT NULL,
                  entry_hash TEXT NOT NULL,
                  PRIMARY KEY (session_id, sequence_no)
                );
                CREATE INDEX IF NOT EXISTS idx_ledger_session
                  ON ledger_entries(session_id, sequence_no);

                CREATE TABLE IF NOT EXISTS sessions (
                  session_id TEXT PRIMARY KEY,
                  created_at TEXT NOT NULL,
                  metadata_json TEXT,
                  chain_head TEXT
                );
                """
            )
            self._conn.commit()

    def _row_to_entry(self, row: sqlite3.Row) -> LedgerEntry:
        return LedgerEntry(
            session_id=row["session_id"],
            sequence_no=row["sequence_no"],
            entry_id=row["entry_id"],
            timestamp_utc=row["timestamp_utc"],
            tool_name=row["tool_name"],
            input_json=json.loads(row["input_json"]),
            output_json=json.loads(row["output_json"]) if row["output_json"] is not None else None,
            status=EntryStatus(row["status"]),
            error_info=json.loads(row["error_info"]) if row["error_info"] else None,
            schema_version=row["schema_version"],
            previous_hash=row["previous_hash"],
            entry_hash=row["entry_hash"],
        )

    def append_entry(self, entry: LedgerEntry) -> LedgerEntry:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO ledger_entries (
                  session_id, sequence_no, entry_id, timestamp_utc, tool_name,
                  input_json, output_json, status, error_info, schema_version,
                  previous_hash, entry_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.session_id,
                    entry.sequence_no,
                    entry.entry_id,
                    entry.timestamp_utc,
                    entry.tool_name,
                    json.dumps(entry.input_json, separators=(",", ":"), ensure_ascii=False),
                    None
                    if entry.output_json is None
                    else json.dumps(entry.output_json, separators=(",", ":"), ensure_ascii=False),
                    entry.status.value,
                    None
                    if entry.error_info is None
                    else json.dumps(entry.error_info, separators=(",", ":"), ensure_ascii=False),
                    entry.schema_version,
                    entry.previous_hash,
                    entry.entry_hash,
                ),
            )
            self._conn.execute(
                """
                INSERT INTO sessions (session_id, created_at, metadata_json, chain_head)
                VALUES (?, ?, NULL, ?)
                ON CONFLICT(session_id) DO UPDATE SET chain_head=excluded.chain_head
                """,
                (entry.session_id, entry.timestamp_utc, entry.entry_hash),
            )
            self._conn.commit()
            return entry

    def get_latest(self, session_id: str) -> LedgerEntry | None:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT * FROM ledger_entries
                WHERE session_id = ?
                ORDER BY sequence_no DESC LIMIT 1
                """,
                (session_id,),
            )
            row = cur.fetchone()
            return self._row_to_entry(row) if row else None

    def list_entries(self, session_id: str) -> list[LedgerEntry]:
        with self._lock:
            cur = self._conn.execute(
                """
                SELECT * FROM ledger_entries
                WHERE session_id = ?
                ORDER BY sequence_no ASC
                """,
                (session_id,),
            )
            return [self._row_to_entry(r) for r in cur.fetchall()]

    def get_entry(self, entry_id: str) -> LedgerEntry | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM ledger_entries WHERE entry_id = ?",
                (entry_id,),
            )
            row = cur.fetchone()
            return self._row_to_entry(row) if row else None

    def update_entry_raw(self, entry_id: str, **fields: Any) -> None:
        allowed = {
            "output_json",
            "input_json",
            "previous_hash",
            "entry_hash",
            "sequence_no",
            "tool_name",
            "timestamp_utc",
            "status",
            "error_info",
        }
        sets = []
        values: list[Any] = []
        for k, v in fields.items():
            if k not in allowed:
                raise ValueError(f"cannot update field {k}")
            if k in {"output_json", "input_json", "error_info"} and v is not None and not isinstance(v, str):
                v = json.dumps(v, separators=(",", ":"), ensure_ascii=False)
            sets.append(f"{k} = ?")
            values.append(v)
        if not sets:
            return
        values.append(entry_id)
        with self._lock:
            self._conn.execute(
                f"UPDATE ledger_entries SET {', '.join(sets)} WHERE entry_id = ?",
                values,
            )
            self._conn.commit()

    def delete_entry(self, entry_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM ledger_entries WHERE entry_id = ?", (entry_id,))
            self._conn.commit()


class JSONLStorage(StorageBackend):
    """Simple append-only JSONL store (local / debugging). Not concurrent-safe."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def init_schema(self) -> None:
        return None

    def _read_all(self) -> list[LedgerEntry]:
        entries: list[LedgerEntry] = []
        if not self.path.exists():
            return entries
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entries.append(LedgerEntry.model_validate_json(line))
        return entries

    def _write_all(self, entries: list[LedgerEntry]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            for e in entries:
                f.write(e.model_dump_json() + "\n")

    def append_entry(self, entry: LedgerEntry) -> LedgerEntry:
        with self._lock:
            entries = self._read_all()
            entries.append(entry)
            self._write_all(entries)
            return entry

    def get_latest(self, session_id: str) -> LedgerEntry | None:
        entries = [e for e in self._read_all() if e.session_id == session_id]
        return max(entries, key=lambda e: e.sequence_no) if entries else None

    def list_entries(self, session_id: str) -> list[LedgerEntry]:
        entries = [e for e in self._read_all() if e.session_id == session_id]
        return sorted(entries, key=lambda e: e.sequence_no)

    def get_entry(self, entry_id: str) -> LedgerEntry | None:
        for e in self._read_all():
            if e.entry_id == entry_id:
                return e
        return None

    def update_entry_raw(self, entry_id: str, **fields: Any) -> None:
        with self._lock:
            entries = self._read_all()
            for i, e in enumerate(entries):
                if e.entry_id == entry_id:
                    data = e.model_dump()
                    data.update(fields)
                    entries[i] = LedgerEntry.model_validate(data)
                    self._write_all(entries)
                    return
            raise KeyError(entry_id)

    def delete_entry(self, entry_id: str) -> None:
        with self._lock:
            entries = [e for e in self._read_all() if e.entry_id != entry_id]
            self._write_all(entries)


def create_storage(backend: str, path: Path | str) -> StorageBackend:
    backend = backend.lower().strip()
    if backend == "sqlite":
        return SQLiteStorage(path)
    if backend == "jsonl":
        return JSONLStorage(path)
    raise ValueError(f"unknown storage backend: {backend}")
