"""OpenAI-style function calling: wrap handlers the model would call.

No OpenAI SDK required — this shows the wiring pattern agents use when the
model returns ``tool_calls`` with JSON arguments.
"""

from __future__ import annotations

import json
from typing import Any

from evidence_ledger import EvidenceLedger, SQLiteStorage, ToolAdapter, verify_chain


def get_weather(args: dict[str, Any]) -> dict[str, Any]:
    city = args.get("city", "Unknown")
    return {"city": city, "temp_c": 22, "condition": "clear"}


def search_docs(args: dict[str, Any]) -> dict[str, Any]:
    return {"query": args.get("q"), "hits": ["doc-1", "doc-2"]}


# Schemas you'd send to the Chat Completions ``tools`` parameter
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Search internal docs",
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string"}},
                "required": ["q"],
            },
        },
    },
]


def main() -> None:
    ledger = EvidenceLedger(storage=SQLiteStorage("/tmp/evidence-ledger-openai-style.db"))
    ledger.init()
    sid = ledger.create_session("demo-openai-style")
    adapter = ToolAdapter(
        ledger,
        tools={"get_weather": get_weather, "search_docs": search_docs},
    )

    # Pretend the model emitted these tool_calls
    fake_tool_calls = [
        {"id": "call_1", "function": {"name": "get_weather", "arguments": '{"city": "Paris"}'}},
        {"id": "call_2", "function": {"name": "search_docs", "arguments": '{"q": "ledger"}'}},
    ]

    results = []
    for call in fake_tool_calls:
        name = call["function"]["name"]
        args = json.loads(call["function"]["arguments"])
        result = adapter.invoke(sid, name, args)
        results.append({"tool_call_id": call["id"], "output": result.output, "hash": result.entry_hash})

    print("tool schemas for the model:", len(TOOL_SCHEMAS))
    print("results:", results)
    print("chain:", verify_chain(sid, ledger).model_dump())


if __name__ == "__main__":
    main()
