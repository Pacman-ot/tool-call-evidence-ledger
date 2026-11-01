# Tool Call Evidence Ledger

Research prototype for **verifiable, tamper-evident tool use** in agentic systems.

Primary guarantees (kept separate):

1. **Integrity** — recorded tool traces form a SHA-256 linear hash chain (`GENESIS_V1` → …).
2. **Faithfulness** — atomic claims in a final answer are checked against that trace (structured matcher first, LLM judge fallback).

This repository implements the **backend / architecture** from the project SRS, Architecture, and Developer Guide. **No frontend.**

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env

ledger init
pytest -q
```

### CLI

```bash
ledger init
ledger run --scenario S-001
ledger inspect --session scenario-S-001   # session id printed by run
ledger verify --session <SESSION_ID>
verify answer --session <SESSION_ID> --input answer.txt
evaluate --dataset data/scenarios.jsonl
```

### HTTP API (local)

```bash
uvicorn evidence_ledger.api:app --reload --port 8000
curl http://127.0.0.1:8000/health
```

Key routes:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| POST | `/sessions` | Create session id |
| POST | `/tools/invoke` | Run toy tool + append ledger entry |
| GET | `/ledger/{session_id}` | Inspect entries |
| GET | `/ledger/{session_id}/verify` | Hash-chain verification |
| POST | `/verify/answer` | Hybrid claim verification |

## Storage note (Vercel)

Vercel’s filesystem is **ephemeral**. Storage is pluggable:

- **Local default:** SQLite at `./data/ledger.db` (`LEDGER_STORAGE_BACKEND=sqlite`).
- **Vercel:** when `VERCEL=1`, the default path becomes `/tmp/ledger.db` (lost between cold starts).
- **JSONL:** set `LEDGER_STORAGE_BACKEND=jsonl` and point `LEDGER_DB_PATH` at a file.

Paid durable storage (Vercel Blob, Neon, etc.) is **not** provisioned unless you ask.

## Architecture (backend)

```
ToolAdapter → EvidenceLedger (SQLite + SHA-256 chain)
Agent answer → HeuristicDecomposer → StructuredMatcher → (optional) LLMJudge
             ↳ HybridVerifier report (verdict + evidence pointers)
```

Toy tools: `calculator`, `lookup_db`, `fake_weather`.

## Spec decisions frozen here

| Decision | Choice |
|----------|--------|
| Language | Python ≥ 3.11 |
| Hash | Hard-coded SHA-256 |
| Genesis marker | literal `GENESIS_V1` |
| Canonicalization | Deterministic sorted-key JSON (RFC 8785-inspired), NaN/Inf rejected |
| Matcher first | Yes; judge only on `UNRESOLVED` |
| LLM judge | Interface + deterministic stub; OpenAI optional via `LLM_JUDGE_ENABLED` |
| Interface | CLI + FastAPI API for deploy; no UI |

## Docs

- `docs/SRS.md`
- `docs/architecture.md`
- `docs/developer_guide.md`

## Threat model (short)

A full rewrite of every entry + recomputed hashes can look internally valid unless a trusted chain-head checkpoint is stored elsewhere. That anchoring is documented as future work.
