# Tool Call Evidence Ledger

Tamper-evident **tool-call evidence ledger** for agentic AI systems.

Primary guarantees (kept separate):

1. **Integrity** — recorded tool traces form a SHA-256 linear hash chain (`GENESIS_V1` → …).
2. **Faithfulness** — atomic claims in a final answer are checked against that trace (structured matcher first, optional LLM judge).

Backend / library only — **no frontend**.

## Install

```bash
# Core (minimal deps: pydantic only)
pip install "git+https://github.com/NoteAditya/tool-call-evidence-ledger.git"

# With FastAPI / Vercel handler
pip install "tool-call-evidence-ledger[api] @ git+https://github.com/NoteAditya/tool-call-evidence-ledger.git"

# Optional extras
#   [api]     FastAPI + uvicorn + mangum
#   [cli]     Typer CLI (`ledger` command)
#   [openai]  OpenAI-backed claim judge
#   [dev]     pytest + httpx + api/cli/openai
#   [all]     api + cli + openai
```

Editable (from a clone):

```bash
pip install -e ".[dev]"
```

## Quickstart

```python
from evidence_ledger import EvidenceLedger, verify_chain, verify_answer

ledger = EvidenceLedger()          # SQLite under ./data/ledger.db by default
session = ledger.session()         # creates session + ensures schema

@session.tool
def lookup(key: str) -> dict:
    return {"orders": 42}[key]

lookup("orders")
print(verify_chain(session.session_id, ledger))
print(verify_answer(session.session_id, "There are 42 orders.", ledger))
```

Equivalent one-liner without a bound session:

```python
from evidence_ledger import EvidenceLedger, wrap_tool

ledger = EvidenceLedger()
sid = ledger.create_session()
ledger.init()

@wrap_tool(ledger, sid)
def search(q: str) -> dict:
    return {"hits": []}
```

See `examples/plain_agent.py`, `examples/openai_tools_style.py`, and `examples/langchain_style.py`.

## Public API

| Symbol | Role |
|--------|------|
| `EvidenceLedger` | Append / list / verify hash chain; `.session()`, `.tool(session_id)` |
| `wrap_tool` / `@session.tool` | Record any Python callable |
| `ToolAdapter` | Dict-args invoke (OpenAI function-calling style) |
| `verify_chain` / `verify_answer` | Integrity + hybrid claim verification |
| `SQLiteStorage` / `JSONLStorage` / `create_storage` | Pluggable backends |
| `HybridVerifier` | `from evidence_ledger.claims import HybridVerifier` |

Package is typed (`py.typed`). Version: `evidence_ledger.__version__`.

## CLI (extra: `[cli]`)

```bash
pip install -e ".[cli]"
ledger init
ledger run --scenario S-001
ledger verify --session <SESSION_ID>
verify answer --session <SESSION_ID> --input answer.txt
```

## HTTP API (extra: `[api]`)

```bash
pip install -e ".[api]"
uvicorn evidence_ledger.api:app --reload --port 8000
curl http://127.0.0.1:8000/health
```

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| POST | `/sessions` | Create session id |
| POST | `/tools/invoke` | Run toy tool + append ledger entry |
| GET | `/ledger/{session_id}` | Inspect entries |
| GET | `/ledger/{session_id}/verify` | Hash-chain verification |
| POST | `/verify/answer` | Hybrid claim verification |

Deployed API: https://tool-call-evidence-ledger.vercel.app

## Storage

- **Local default:** SQLite at `./data/ledger.db` (`LEDGER_STORAGE_BACKEND=sqlite`).
- **Vercel:** when `VERCEL=1`, default path becomes `/tmp/ledger.db` (ephemeral).
- **JSONL:** `LEDGER_STORAGE_BACKEND=jsonl`.

Paid durable storage is not provisioned unless you ask.

## Architecture

```
@session.tool / ToolAdapter → EvidenceLedger (SQLite + SHA-256 chain)
Agent answer → HeuristicDecomposer → StructuredMatcher → (optional) LLMJudge
             ↳ HybridVerifier report (verdict + evidence pointers)
```

Toy tools shipped for demos: `calculator`, `lookup_db`, `fake_weather`.

## Spec decisions

| Decision | Choice |
|----------|--------|
| Language | Python ≥ 3.11 |
| Hash | SHA-256 |
| Genesis | literal `GENESIS_V1` |
| Canonicalization | Deterministic sorted-key JSON (RFC 8785-inspired) |
| Matcher first | Yes; judge only on unresolved claims |
| LLM judge | Stub by default; OpenAI via `[openai]` + `LLM_JUDGE_ENABLED` |
| Interface | Library + optional CLI/API; no UI |

## Docs

- `docs/SRS.md`
- `docs/architecture.md`
- `docs/developer_guide.md`

## Threat model (short)

A full rewrite of every entry with recomputed hashes can look internally valid unless a trusted chain-head checkpoint is stored elsewhere. Anchoring is future work.
