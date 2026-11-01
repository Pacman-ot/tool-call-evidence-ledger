# Architecture (guide)

This page summarizes the **implemented** architecture. The normative design write-up is [architecture.md](architecture.md).

## Component map

```mermaid
flowchart TB
  subgraph capture [Capture]
    T[Tool callables]
    W["wrap_tool / @session.tool"]
    A[ToolAdapter]
    T --> W
    T --> A
  end
  subgraph ledger [Ledger]
    EL[EvidenceLedger]
    ST[(StorageBackend<br/>SQLite / JSONL)]
    H[canonicalize + SHA-256]
    EL --> H
    EL --> ST
  end
  subgraph verify [Verification]
    HV[HybridVerifier]
    D[HeuristicDecomposer]
    M[StructuredMatcher]
    J[LLMJudge<br/>Deterministic or OpenAI]
    HV --> D --> M
    M -->|UNRESOLVED| J
  end
  W --> EL
  A --> EL
  EL --> HV
  HV --> R[AnswerVerificationReport]
```

## Runtime data flow

### Recording a tool call

```mermaid
sequenceDiagram
  participant Agent
  participant Adapter as ToolAdapter / wrap_tool
  participant Ledger as EvidenceLedger
  participant Store as StorageBackend
  Agent->>Adapter: invoke(name, args) or call wrapped fn
  Adapter->>Adapter: run tool / catch errors
  Adapter->>Ledger: append(session, tool, input, output, status)
  Ledger->>Ledger: previous_hash, sequence_no, hash_payload
  Ledger->>Store: append_entry(LedgerEntry)
  Store-->>Ledger: persisted entry
  Ledger-->>Adapter: LedgerEntry / ToolInvokeResult
```

### Verifying an answer

```mermaid
sequenceDiagram
  participant Caller
  participant HV as HybridVerifier
  participant Ledger as EvidenceLedger
  participant Dec as HeuristicDecomposer
  participant Mat as StructuredMatcher
  participant Judge as LLMJudge
  Caller->>HV: verify(session_id, answer)
  HV->>Ledger: verify(session_id) + list_entries
  HV->>Dec: decompose(answer)
  loop each AtomicClaim
    HV->>Mat: match(claim, entries)
    alt MATCH_SUPPORTED / MATCH_CONTRADICTED
      Mat-->>HV: decision + evidence
    else UNRESOLVED
      HV->>Judge: assess(claim, entries)
      Judge-->>HV: verdict + rationale
    end
  end
  HV-->>Caller: AnswerVerificationReport
```

## Layers (code)

| Layer | Modules |
|-------|---------|
| Public API | `__init__.py`, `integration.py`, `verify.py` |
| Ledger | `ledger.py`, `hashing.py`, `canonicalize.py`, `models.py` |
| Storage | `storage.py` |
| Tools | `tools/adapter.py`, `tools/calculator.py`, `lookup_db.py`, `fake_weather.py` |
| Claims | `claims/decomposer.py`, `structured_matcher.py`, `derivations.py`, `llm_judge.py`, `verifier.py`, `taxonomy.py` |
| Evaluation | `evaluation/*` |
| Surfaces | `api.py`, `cli.py`, `api/index.py` |

## Design freezes reflected in code

- Hash algorithm: **SHA-256 only** (`hashing.py`).
- Genesis: literal string **`GENESIS_V1`**.
- Canonical JSON: sorted keys, no NaN/Inf (`canonicalize.py`).
- Matcher before judge; judge only on unresolved claims.
- No frontend; optional HTTP for deploy.
