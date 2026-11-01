# Hash-chain ledger design

## Protected payload

For each entry, `EvidenceLedger` builds a dict (see `build_protected_payload` in `ledger.py`) and hashes it:

| Field | Role |
|-------|------|
| `session_id` | Session scope |
| `sequence_no` | 1-based position in session |
| `entry_id` | Default `{session_id}:{sequence_no}` |
| `timestamp_utc` | ISO-8601 UTC with milliseconds + `Z` |
| `tool_name` | Tool identifier |
| `input_json` | Arguments / call record |
| `output_json` | Result or `null` on failure |
| `status` | `success` \| `error` \| `timeout` |
| `error_info` | Optional `{type, message}` |
| `schema_version` | Integer (default `1`) |
| `previous_hash` | Prior `entry_hash` or genesis |

```
H_0 = "GENESIS_V1"
H_i = SHA256( canonical_json_utf8( protected_payload_i ) )
```

`entry_hash` is the hex digest. It is **not** included inside the hashed payload (only `previous_hash` links the chain).

## Canonicalization

`canonicalize()` (`canonicalize.py`) is an RFC 8785–inspired deterministic serializer:

- UTF-8 JSON text, no insignificant whitespace  
- Object keys sorted lexicographically  
- Arrays keep order  
- `NaN` / `±Infinity` rejected (`CanonicalizationError`)  
- Booleans / null / strings / ints / floats supported  

`hash_payload` = `SHA-256(canonicalize_bytes(payload))`.

## Append algorithm

1. Read latest entry for `session_id` (or none).
2. `sequence_no = 1` or `last + 1`; `previous_hash = GENESIS_V1` or `last.entry_hash`.
3. Build payload → `entry_hash`.
4. Persist via `StorageBackend.append_entry`.

SQLite storage uses a lock around read-latest + insert for basic concurrency safety on one process.

## Verify algorithm (`EvidenceLedger.verify`)

For empty sessions: `VALID` with `entries_checked=0` and `chain_head=genesis`.

Otherwise, walk entries in sequence order:

1. Expect `sequence_no == 1, 2, 3, …`  
2. Expect `previous_hash` equals expected previous  
3. Recompute hash of protected payload; compare to `entry_hash`  
4. On failure: `INVALID` with `first_failing_sequence` and `reason`  
5. On success: `VALID`, `chain_head` = last hash  

Helpers: `verify_chain(session_id, ledger=None)` in `verify.py`.

## Status values

`EntryStatus`: `success`, `error`, `timeout`. Failed tool calls are still chained (output may be `null`, `error_info` set) so the trace remains complete.
