# Security, threat model, and limitations

Aligned with [architecture.md](architecture.md) § failure modes / threat model and [SRS.md](SRS.md) constraints.

## In scope (prototype)

- Detect **post-write mutation** of stored ledger fields (output, input, timestamp, tool name, hashes, sequence/order) when the attacker does **not** rewrite the entire chain consistently.
- Keep tool outputs out of the LLM judge’s instruction channel (quoted as untrusted data).
- Fail closed on integrity failure when verifying answers (`INTEGRITY_FAILURE`).

## Out of scope / limitations

- **Full chain rewrite:** recomputing every `entry_hash` after editing payloads can still look `VALID` internally. Mitigation (future): external **chain-head checkpoint** / anchoring.
- Compromised host, Python runtime, or DB admin with full rewrite capability.
- Dishonest or compromised **tools** (wrong world facts still hash-chain cleanly).
- Cryptographic **non-repudiation**, multi-party signatures, or consensus.
- Guaranteeing absence of model hallucination beyond the hybrid checker’s coverage.
- Durable multi-tenant cloud storage hardening (Vercel `/tmp` is ephemeral).

## Operational notes

- Secrets only via environment (`OPENAI_API_KEY`, etc.); never commit `.env`.
- `update_entry_raw` / `delete_entry` exist for tests — do not expose them on public HTTP APIs (they are not HTTP routes today).
- Treat this as a **research prototype**, not a compliance certification artifact.
