# Tool Call Evidence Ledger

A Python library and research prototype for **verifiable, tamper-evident tool use** in agentic AI systems.

When an LLM agent calls tools (calculators, databases, APIs) and then answers a question, two separate problems appear:

1. **Did anyone alter the recorded tool trace after the fact?**  
2. **Do the claims in the final answer actually follow from that trace?**

This project addresses both — and keeps them separate on purpose.

| Guarantee | What it means | What it does *not* mean |
|-----------|---------------|-------------------------|
| **Integrity** | Tool-call records form a SHA-256 linear hash chain (`GENESIS_V1` → entry₁ → …). Tampering with fields, order, or links is detectable via `verify` / `verify_chain`. | Cryptographic non-repudiation, or protection against a full rewrite of every entry *with recomputed hashes* unless an external chain-head checkpoint exists. |
| **Claim support (faithfulness)** | Atomic claims in an answer are checked against the ledger (structured matcher first; optional LLM judge on unresolved claims). | That the tools themselves told the truth, or that hallucination is impossible in general. |

**Who it’s for:** researchers and engineers building or evaluating agent tool-calling pipelines who need a concrete evidence trail and a hybrid verifier — not a frontend product. Backend / library only (**no UI**).

**Specs (normative):** [`docs/SRS.md`](docs/SRS.md) · [`docs/architecture.md`](docs/architecture.md) · [`docs/developer_guide.md`](docs/developer_guide.md)  
**Guides & reference:** [`docs/index.md`](docs/index.md)

Live HTTP demo (ephemeral storage): https://tool-call-evidence-ledger.vercel.app

---

## Install

Requires **Python ≥ 3.11**.

```bash
# Core library (minimal dependency: pydantic)
pip install "git+https://github.com/NoteAditya/tool-call-evidence-ledger.git"

# With FastAPI / Mangum (HTTP API + Vercel handler)
pip install "tool-call-evidence-ledger[api] @ git+https://github.com/NoteAditya/tool-call-evidence-ledger.git"
```

| Extra | Adds |
|-------|------|
| `[api]` | FastAPI, uvicorn, mangum, python-dotenv |
| `[cli]` | Typer CLI (`ledger` entry point) |
| `[openai]` | OpenAI client for the optional LLM judge |
| `[dev]` | pytest, httpx, plus api/cli/openai |
| `[all]` | api + cli + openai |

From a clone:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # optional
```

---

## Quickstart

```python
from evidence_ledger import EvidenceLedger, verify_chain, verify_answer

ledger = EvidenceLedger()       # SQLite at ./data/ledger.db by default
session = ledger.session()      # new session_id + schema init

@session.tool
def lookup(key: str) -> dict:
    return {"orders": 42}[key]

lookup("orders")

print(verify_chain(session.session_id, ledger))
print(verify_answer(session.session_id, "There are 42 orders.", ledger))
```

More patterns: [`examples/`](examples/) · [Integration guides](docs/integration.md).

---

## Documentation

Start at **[`docs/index.md`](docs/index.md)** for the full table of contents (overview, architecture, hash chain, claim pipeline, tools, API/CLI/HTTP references, evaluation, deployment, security, contributing).

---

## License

MIT (see `pyproject.toml`). Research prototype — see [limitations & threat model](docs/security.md).
