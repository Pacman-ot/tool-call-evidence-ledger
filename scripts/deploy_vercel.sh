#!/usr/bin/env bash
# Deploy production API to Vercel.
# Vercel's Python builder installs only main pyproject deps (ignores extras and,
# with legacy `builds`, installCommand). We stage a gitless copy with API deps
# folded into main so the serverless function gets FastAPI/Mangum, without
# bloating the published library's default dependency set.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$(mktemp -d /tmp/tcel-vercel-XXXXXX)"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

tar -C "$ROOT" -cf - \
  --exclude '.git' --exclude '.venv' --exclude '.vercel' \
  --exclude '__pycache__' --exclude '.pytest_cache' --exclude '*.db' \
  . | tar -C "$STAGE" -xf -
mkdir -p "$STAGE/.vercel"
cp "$ROOT/.vercel/project.json" "$STAGE/.vercel/project.json"

python3 - "$STAGE/pyproject.toml" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
text = p.read_text()
needle = 'dependencies = [\n  "pydantic>=2.7.0",\n]'
repl = '''dependencies = [
  "pydantic>=2.7.0",
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "mangum>=0.19.0",
  "python-dotenv>=1.0.0",
]'''
if needle not in text:
    raise SystemExit("expected slim core dependencies block missing; refuse to patch")
p.write_text(text.replace(needle, repl, 1))
print("patched", p)
PY

cd "$STAGE"
vercel --prod --yes --archive=tgz --force
