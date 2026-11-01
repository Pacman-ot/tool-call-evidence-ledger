# Deployment

## Local HTTP

```bash
pip install -e ".[api]"
uvicorn evidence_ledger.api:app --reload --port 8000
```

## Vercel

- Project entry: `api/index.py` (adds `src/` to `sys.path`, `handler = Mangum(app, lifespan="off")`).
- `vercel.json` uses legacy `@vercel/python` **builds** + catch-all **routes** to `api/index.py`.
- Vercel’s Python/uv installer installs **main** `pyproject.toml` dependencies (not extras). The helper script stages a copy with `[api]` packages folded into main deps, and deploys via `--archive=tgz` (avoids Git commit-author deployment blocks observed on this project).

```bash
./scripts/deploy_vercel.sh
```

Production URL: https://tool-call-evidence-ledger.vercel.app

### Ephemeral `/tmp` caveat

When `VERCEL=1` and `LEDGER_DB_PATH` is left at the default `./data/ledger.db`, the effective path becomes **`/tmp/ledger.db`**.

- Writable in the serverless runtime.
- **Not durable** across cold starts / instances.
- Suitable for demos and smoke tests only.

For durable storage, set an external backend later (not shipped). Do not assume multi-request sessions survive without sticky state.

`requirements.txt` mirrors the API runtime stack for installers that read it.
