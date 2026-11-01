# Tools

## Built-in toy tools

Registered in `DEFAULT_TOOLS` and used by `ToolAdapter` / HTTP `/tools/invoke`.

### `calculator`

**Args:** `{ "op": "add"|"sub"|"mul"|"div", "a": number, "b": number }`  
**Returns:** `{ "op", "a", "b", "result" }`  
**Errors:** non-numbers, unsupported op, division by zero.

### `lookup_db`

In-memory demo DB keys: `orders`, `users`, `incidents`.

**Args:** `{ "key": str, "field"?: str }`  
**Returns:** record fields plus `key`, or a single field projection.  
**Errors:** unknown key/field.

Example `orders` → `count=42`, `status=ok`, `region=west`.  
`incidents` includes `old_value` / `new_value` and dates for derivation demos.

### `fake_weather`

**Args:** `{ "city": str }` — known: `nyc`, `sf`, `blr` (case-insensitive).  
**Returns:** `{ "city", "temp_c", "condition", "humidity" }`.

List via HTTP `GET /tools` → `{"tools": ["calculator", "fake_weather", "lookup_db"]}`.

---

## Calling styles

### 1. Decorator / wrap (kwargs-style functions)

```python
from evidence_ledger import EvidenceLedger

ledger = EvidenceLedger()
session = ledger.session()

@session.tool
def my_search(q: str, limit: int = 5) -> dict:
    return {"q": q, "limit": limit, "hits": []}

my_search("ledger", limit=3)  # recorded as tool_name="my_search"
```

Or `@wrap_tool(ledger, session_id, name="search")`, or `@ledger.tool(session_id)`.

On exception: entry with `status=error` is appended, then the exception is re-raised (`reraise=True` by default).

### 2. ToolAdapter (dict-args, OpenAI function-calling style)

```python
from evidence_ledger import EvidenceLedger, ToolAdapter
from evidence_ledger.tools.calculator import calculator

ledger = EvidenceLedger()
ledger.init()
sid = ledger.create_session()
adapter = ToolAdapter(ledger, tools={"calculator": calculator})
adapter.invoke(sid, "calculator", {"op": "add", "a": 1, "b": 2})
```

`ToolAdapter.register(name, fn)` adds tools. Unknown names → `error` entry with `UnknownTool`.

Optional `timeout_s`: if the call returns after the threshold, status `timeout` (cooperative check after return; not a hard preemption).

### 3. Manual append

```python
ledger.append(session_id, "external_api", {"url": "..."}, {"ok": True})
```

Use when the tool already ran outside the process.
