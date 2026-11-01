# HTTP API reference

FastAPI app: `evidence_ledger.api:app` (extra `[api]`).  
Vercel entry: `api/index.py` wraps the same app with Mangum.

Local:

```bash
pip install -e ".[api]"
uvicorn evidence_ledger.api:app --reload --port 8000
```

OpenAPI UI: `http://127.0.0.1:8000/docs`  
Production: `https://tool-call-evidence-ledger.vercel.app`

Each request constructs a fresh `EvidenceLedger()` (settings from env). On Vercel, storage defaults to ephemeral `/tmp/ledger.db`.

---

## `GET /health`

Liveness.

**Response**

```json
{"status":"ok","version":"0.1.0","service":"tool-call-evidence-ledger"}
```

## `GET /`

Service stub with links.

```json
{"service":"tool-call-evidence-ledger","version":"0.1.0","docs":"/docs","health":"/health"}
```

## `POST /sessions`

Create a new session id (UUID4). Does not require a body.

**Response**

```json
{"session_id":"0be9ef16-35d2-4eb4-b356-8f5672ba6a84"}
```

## `GET /tools`

List default toy tool names.

```json
{"tools":["calculator","fake_weather","lookup_db"]}
```

## `POST /tools/invoke`

Run a registered toy tool through `ToolAdapter` and append a ledger entry.

**Request**

```json
{
  "session_id": "<uuid>",
  "tool_name": "lookup_db",
  "args": {"key": "orders"}
}
```

**Response** (`ToolInvokeResult`)

```json
{
  "tool_name": "lookup_db",
  "output": {"key": "orders", "count": 42, "status": "ok", "region": "west"},
  "status": "success",
  "error_info": null,
  "entry_id": "<session>:1",
  "entry_hash": "<hex>"
}
```

## `POST /ledger/append`

Append an entry without executing a local tool (external capture).

**Request**

```json
{
  "session_id": "<uuid>",
  "tool_name": "external",
  "input_json": {"q": "x"},
  "output_json": {"ok": true},
  "status": "success",
  "error_info": null
}
```

**Response:** full `LedgerEntry` JSON.

## `GET /ledger/{session_id}`

List entries for a session.

```json
{"session_id":"<uuid>","entries":[ /* LedgerEntry objects */ ]}
```

## `GET /ledger/{session_id}/verify`

Hash-chain verification → `ChainVerifyResult`.

```json
{
  "status": "VALID",
  "entries_checked": 1,
  "first_failing_sequence": null,
  "reason": null,
  "chain_head": "<hex>"
}
```

## `POST /verify/answer`

Hybrid claim verification.

**Request**

```json
{"session_id":"<uuid>","answer":"There are 42 orders."}
```

Empty answer → **400** `{"detail":"answer must be non-empty"}`.

**Response:** `AnswerVerificationReport` (includes `chain_integrity`, `claims[]`, `aggregate_status`).

---

### curl smoke sequence

```bash
BASE=https://tool-call-evidence-ledger.vercel.app
SID=$(curl -sS -X POST "$BASE/sessions" | python3 -c 'import sys,json;print(json.load(sys.stdin)["session_id"])')
curl -sS -X POST "$BASE/tools/invoke" -H 'content-type: application/json' \
  -d "{\"session_id\":\"$SID\",\"tool_name\":\"lookup_db\",\"args\":{\"key\":\"orders\"}}"
curl -sS "$BASE/ledger/$SID/verify"
curl -sS -X POST "$BASE/verify/answer" -H 'content-type: application/json' \
  -d "{\"session_id\":\"$SID\",\"answer\":\"There are 42 orders.\"}"
```
