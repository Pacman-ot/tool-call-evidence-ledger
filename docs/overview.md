# Overview & concepts

## The problem

Agentic systems call external **tools** (APIs, DBs, calculators) and then produce natural-language answers. Two failure modes are easy to confuse:

1. **Trace tampering** — someone (or buggy storage) changes what was recorded about a tool call.
2. **Unfaithful answers** — the model’s text is not supported by the tool outputs that *were* recorded (hallucinated numbers, wrong entities, invented derivations).

A single “trust the agent” score mixes these. This prototype **separates** them.

## Two guarantees

### 1. Integrity (hash-chain ledger)

Each successful or failed tool invocation can be appended as a `LedgerEntry`. Entries in a session form a **linear SHA-256 hash chain** starting from the literal genesis marker `GENESIS_V1`.

- Re-hashing the protected payload must match `entry_hash`.
- `previous_hash` must equal the prior entry’s hash (or genesis for the first).
- Sequence numbers must be contiguous from 1.

See [Hash-chain ledger](hash-chain.md).

### 2. Claim support / faithfulness

Given a session’s ledger and a final **answer** string, `HybridVerifier`:

1. Checks chain integrity.
2. Decomposes the answer into atomic claims (`HeuristicDecomposer`).
3. Tries a **structured matcher** (direct numeric / fixed derivations).
4. Falls back to an **LLM judge** interface only when the matcher returns unresolved (default implementation is a deterministic stub; OpenAI is optional).

See [Claim verification](claim-verification.md).

Integrity failure yields aggregate status `INTEGRITY_FAILURE` and claim verdicts are not treated as trustworthy evidence.

## Who it’s for

- Researchers evaluating tool-using agents against labelled claim support.
- Engineers who want a small, importable Python library (`evidence_ledger`) to wrap tool functions and verify answers.
- Deployments that need a thin HTTP API (FastAPI + Mangum on Vercel) **without a frontend**.

## What this is not

- Not a full agent framework (no planner, memory, or UI).
- Not a proof that tools returned ground truth about the world.
- Not non-repudiation without external anchoring (see [Security](security.md)).

## Package shape

| Piece | Location |
|-------|----------|
| Library | `src/evidence_ledger/` |
| HTTP entry (Vercel) | `api/index.py` → Mangum(`evidence_ledger.api:app`) |
| CLI | `evidence_ledger.cli:app` (extra `[cli]`) |
| Examples | `examples/` |
| Specs | `docs/SRS.md`, `architecture.md`, `developer_guide.md` |
