# Python API reference

Public surface is defined by `evidence_ledger.__all__` plus commonly used submodule exports documented here. Version: `evidence_ledger.__version__` (`0.1.0`). Package is typed (`py.typed`).

## `evidence_ledger` (package)

### `EvidenceLedger`

```python
EvidenceLedger(storage: StorageBackend | None = None, settings: Settings | None = None)
```

| Method | Description |
|--------|-------------|
| `init()` | Ensure storage schema |
| `create_session(session_id=None) -> str` | UUID4 if omitted |
| `append(session_id, tool_name, input_json, output_json=None, status=SUCCESS, error_info=None, timestamp_utc=None, entry_id=None) -> LedgerEntry` | Append chained entry |
| `list_entries(session_id) -> list[LedgerEntry]` | Ordered by sequence |
| `get_entry(entry_id) -> LedgerEntry \| None` | |
| `verify(session_id) -> ChainVerifyResult` | Hash-chain check |
| `session(session_id=None) -> BoundSession` | Init + bind |
| `tool(session_id, *, name=None, reraise=True)` | Decorator factory |

Attributes: `settings`, `storage`, `genesis`.

### `BoundSession`

| Attr / method | Description |
|---------------|-------------|
| `ledger`, `session_id` | Bound handles |
| `tool` | Decorator (`@session.tool` or `@session.tool(name=...)`) |
| `invoke(tool_name, args, fn) -> ToolInvokeResult` | One-shot dict-style invoke via temporary `ToolAdapter` |

### `wrap_tool(ledger, session_id, *, name=None, reraise=True)`

Decorator factory recording every call.

### `ToolAdapter`

```python
ToolAdapter(ledger, tools=None, timeout_s=None)
```

Default `tools=DEFAULT_TOOLS`. Methods: `register`, `invoke(session_id, tool_name, args) -> ToolInvokeResult`.

### `verify_chain(session_id, ledger=None) -> ChainVerifyResult`

### `verify_answer(session_id, answer, ledger=None) -> AnswerVerificationReport`

Uses `HybridVerifier`.

### Storage

| Symbol | Description |
|--------|-------------|
| `StorageBackend` | ABC |
| `SQLiteStorage(db_path)` | SQLite backend |
| `JSONLStorage(path)` | JSONL backend |
| `create_storage(backend, path)` | `"sqlite"` \| `"jsonl"` |

### Models (re-exported)

`LedgerEntry`, `EntryStatus`, `IntegrityStatus`, `ChainVerifyResult`, `AnswerVerificationReport`, `ToolInvokeResult`, `Verdict`.

---

## `evidence_ledger.claims`

| Symbol | Module | Role |
|--------|--------|------|
| `HybridVerifier` | `verifier.py` | Full pipeline (`__init__` exports this) |
| `HeuristicDecomposer` / `ClaimDecomposer` | `decomposer.py` | Claim split |
| `StructuredMatcher` / `MatchResult` | `structured_matcher.py` | Structured match |
| `LLMJudge`, `DeterministicJudge`, `OpenAIJudge`, `build_judge`, `JudgeResult` | `llm_judge.py` | Judge interface |
| `infer_claim_type` | `taxonomy.py` | Claim typing |
| `derive_*` | `derivations.py` | Percentage, ratio, sum, date delta |

`HybridVerifier(ledger, decomposer=None, matcher=None, judge=None, settings=None)` → `.verify(session_id, answer)`.

---

## `evidence_ledger.models` (additional)

Enums: `ClaimType`, `MatchDecision`, `VerificationMethod`.  
Models: `EvidencePointer`, `AtomicClaim`, `ClaimVerdict`.

---

## `evidence_ledger.config`

`Settings` dataclass; `get_settings()` reads environment (see [storage.md](storage.md)).

---

## `evidence_ledger.hashing` / `canonicalize`

`GENESIS_V1`, `hash_payload`, `sha256_hex`; `canonicalize`, `canonicalize_bytes`, `CanonicalizationError`.

---

## `evidence_ledger.tools`

`calculator`, `lookup_db`, `fake_weather`, `DEFAULT_TOOLS`, `ToolAdapter`.

---

## `evidence_ledger.evaluation`

`run_evaluation`, `load_jsonl`, `BaselineAJudge`, `BaselineBJudge`, metrics helpers — see [evaluation.md](evaluation.md).

---

## `evidence_ledger.api` / `cli`

Require extras `[api]` / `[cli]`. See [http-api.md](http-api.md) and [cli.md](cli.md).
