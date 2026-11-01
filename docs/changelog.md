# Changelog

## 0.1.0

Initial research prototype and library packaging.

- SHA-256 linear evidence ledger (`GENESIS_V1`) with deterministic JSON canonicalization.
- Storage: SQLite (default) and JSONL; pluggable `StorageBackend`.
- Capture: `EvidenceLedger`, `ToolAdapter`, `wrap_tool` / `@session.tool`.
- Toy tools: `calculator`, `lookup_db`, `fake_weather`.
- Hybrid verification: heuristic decomposer, structured matcher (+ fixed derivations), LLM judge interface with deterministic stub and optional OpenAI backend.
- Surfaces: Typer CLI (`[cli]`), FastAPI + Mangum (`[api]`), Vercel deployment helper.
- Evaluation harness with scenarios/ground truth and baselines A/B.
- Packaging: `src/` layout, optional extras, `py.typed`, public `__init__` exports.
- Documentation set under `docs/` (guides + retained SRS/architecture/developer specs).
