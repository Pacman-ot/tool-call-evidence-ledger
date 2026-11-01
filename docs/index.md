# Documentation

Human-oriented guides for the **Tool Call Evidence Ledger** research prototype.  
Normative project specs remain in place and are linked below.

## Start here

| Doc | Description |
|-----|-------------|
| [Overview & concepts](overview.md) | Problem statement, two guarantees, who it’s for |
| [Architecture](architecture-guide.md) | Components, data flow, Mermaid diagrams |
| [Hash-chain ledger](hash-chain.md) | Canonicalization, SHA-256 chain, verify algorithm |
| [Claim verification](claim-verification.md) | Decomposer → matcher → LLM judge |
| [Storage backends](storage.md) | SQLite, JSONL, env configuration |
| [Tools](tools.md) | Built-ins and writing / wrapping your own |
| [Python API reference](api-reference.md) | Public package symbols |
| [CLI reference](cli.md) | `ledger` / `verify` / `evaluate` |
| [HTTP API reference](http-api.md) | Every endpoint with examples |
| [Integration guides](integration.md) | Plain Python, OpenAI-style, LangChain-style |
| [Evaluation harness](evaluation.md) | Scenarios, baselines, metrics |
| [Deployment](deployment.md) | Vercel, `/tmp` caveat |
| [Testing](testing.md) | pytest layout and how to run |
| [Security & limitations](security.md) | Threat model, out of scope |
| [Contributing](contributing.md) | Dev setup |
| [Changelog](changelog.md) | Release notes |

## Normative specifications (kept as-is)

| Spec | Role |
|------|------|
| [SRS.md](SRS.md) | Software requirements |
| [architecture.md](architecture.md) | System architecture & design (spec) |
| [developer_guide.md](developer_guide.md) | Implementation contracts |

If a guide and a spec disagree, treat the **spec + current source code** as authoritative and open an issue.
