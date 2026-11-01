# Testing

## Run

```bash
pip install -e ".[dev]"
pytest -q
```

`pyproject.toml` sets `testpaths = ["tests"]` and `pythonpath = ["src"]`.

## Suites (as of 0.1.0)

| File | Focus |
|------|--------|
| `test_hashing.py` | Canonicalization / SHA-256 stability |
| `test_ledger.py` | Append order, errors, empty verify |
| `test_tamper_detection.py` | Mutations detected by `verify` |
| `test_matcher.py` | Structured matcher cases |
| `test_verifier.py` | Hybrid verifier behaviors |
| `test_integration.py` | `wrap_tool` / `@session.tool` |
| `test_api.py` | FastAPI `TestClient` flows |
| `test_evaluation.py` | Evaluation runner smoke |

Tamper tests use `update_entry_raw` / delete helpers on storage — not part of the production trust path.

## Clean import check

```bash
python -m venv /tmp/tcel && source /tmp/tcel/bin/activate
pip install .
python -c "from evidence_ledger import EvidenceLedger, wrap_tool; print('ok')"
```

Core install does not require FastAPI; import `evidence_ledger.api` only with `[api]`.
