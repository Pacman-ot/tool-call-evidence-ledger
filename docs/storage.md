# Storage backends

All persistence goes through `StorageBackend` (`storage.py`).

## Interface

Abstract methods:

- `init_schema()`
- `append_entry(entry) -> LedgerEntry`
- `get_latest(session_id) -> LedgerEntry | None`
- `list_entries(session_id) -> list[LedgerEntry]`
- `get_entry(entry_id) -> LedgerEntry | None`
- `update_entry_raw(entry_id, **fields)` — **test/tamper helper** (no rehash)
- `delete_entry(entry_id)` — test helper

## SQLite (`SQLiteStorage`)

- Default backend.
- Path from settings (`LEDGER_DB_PATH`, default `./data/ledger.db`).
- Tables: `ledger_entries`, `sessions`.
- Thread lock (`RLock`) around critical sections.

## JSONL (`JSONLStorage`)

- One JSON object per line; full file rewrite on mutate helpers.
- Useful for debugging / simple dumps.

## Factory

```python
from evidence_ledger import create_storage, EvidenceLedger

store = create_storage("sqlite", "/tmp/ledger.db")  # or "jsonl"
ledger = EvidenceLedger(storage=store)
```

`EvidenceLedger()` without args uses `get_settings()` → `create_storage(backend, resolved_db_path())`.

## Environment

| Variable | Default | Meaning |
|----------|---------|---------|
| `LEDGER_STORAGE_BACKEND` | `sqlite` | `sqlite` or `jsonl` |
| `LEDGER_DB_PATH` | `./data/ledger.db` | File path |
| `VERCEL` | — | If `1` and path still default, use `/tmp/ledger.db` |
| `SCHEMA_VERSION` | `1` | Written into entries |
| `GENESIS_MARKER` | `GENESIS_V1` | Chain start string |
| `NUMERIC_TOLERANCE` | `1e-6` | Matcher tolerance |
| `LLM_JUDGE_ENABLED` | false | Enable OpenAI judge path |
| `OPENAI_API_KEY` | — | Judge key |
| `LLM_MODEL` | `gpt-4o-mini` | Judge model |

Paid remote stores (Blob, Neon, etc.) are **not** implemented unless explicitly added later.
