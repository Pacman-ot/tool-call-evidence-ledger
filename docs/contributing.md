# Contributing / developer setup

## Setup

```bash
git clone https://github.com/NoteAditya/tool-call-evidence-ledger.git
cd tool-call-evidence-ledger
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
ledger ledger init
pytest -q
```

## Layout

```text
src/evidence_ledger/   # library
api/index.py           # Vercel/Mangum entry
tests/                 # pytest
examples/              # integration samples
data/                  # scenarios + ground truth
docs/                  # guides + normative specs
scripts/deploy_vercel.sh
```

## Conventions

- Python ≥ 3.11; keep core importable with only `pydantic` unless using extras.
- Do not invent features ahead of the SRS / architecture specs without updating those docs.
- Prefer extending ABCs (`StorageBackend`, `ClaimDecomposer`, `LLMJudge`) over breaking the hash payload field set (`schema_version` exists for evolution).
- No frontend in this repository.

## Specs to read first

1. [developer_guide.md](developer_guide.md)  
2. [architecture.md](architecture.md)  
3. [SRS.md](SRS.md)  
