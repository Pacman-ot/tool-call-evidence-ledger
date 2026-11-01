# Integration guides

Runnable samples live under [`examples/`](../examples/).

## Plain Python agent

Use a bound session and decorate ordinary functions:

```python
from evidence_ledger import EvidenceLedger, verify_chain, verify_answer

ledger = EvidenceLedger()
session = ledger.session("demo")

@session.tool
def calculator(op: str, a: float, b: float) -> dict:
    ...

@session.tool(name="lookup_db")
def lookup(key: str) -> dict:
    ...

calculator(op="add", a=20, b=22)
lookup("orders")
verify_chain(session.session_id, ledger)
verify_answer(session.session_id, "Orders=42; 20+22=42", ledger)
```

See `examples/plain_agent.py`.

## OpenAI function-calling style

Keep handlers as `dict -> dict` (or any JSON-serializable return). When the model returns `tool_calls`, parse `arguments` JSON and call `ToolAdapter.invoke`:

```python
adapter = ToolAdapter(ledger, tools={"get_weather": get_weather, "search_docs": search_docs})
for call in tool_calls:
    name = call["function"]["name"]
    args = json.loads(call["function"]["arguments"])
    result = adapter.invoke(session_id, name, args)
    # send result.output back to the model as the tool message
```

This repository does **not** bundle the OpenAI Chat Completions client for the agent loop; `examples/openai_tools_style.py` shows the wiring with fake `tool_calls`. The optional `[openai]` extra is for the **claim judge**, not for driving the agent.

## LangChain-style tools

Without importing LangChain, wrap callables the same way you would wrap `@tool` functions before an executor:

```python
from evidence_ledger import wrap_tool

multiply_logged = wrap_tool(ledger, sid, name="multiply")(multiply)
city_logged = wrap_tool(ledger, sid, name="city_info")(city_info)
```

See `examples/langchain_style.py`. There is no first-party LangChain dependency or callback handler in this package.
