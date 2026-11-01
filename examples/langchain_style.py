"""LangChain-style tools without importing LangChain.

Illustrates wrapping callables the same way you would wrap ``@tool`` functions
before handing them to an agent executor.
"""

from __future__ import annotations

from evidence_ledger import EvidenceLedger, SQLiteStorage, wrap_tool, verify_chain


def main() -> None:
    ledger = EvidenceLedger(storage=SQLiteStorage("/tmp/evidence-ledger-lc-style.db"))
    ledger.init()
    sid = ledger.create_session("demo-lc-style")

    def multiply(a: int, b: int) -> int:
        """Multiply two integers."""
        return a * b

    def city_info(name: str) -> dict:
        """Return a tiny fact table for a city."""
        return {"name": name, "country": "FR" if name.lower() == "paris" else "??"}

    # Equivalent to decorating LangChain @tool functions before the agent runs
    multiply_logged = wrap_tool(ledger, sid, name="multiply")(multiply)
    city_logged = wrap_tool(ledger, sid, name="city_info")(city_info)

    tools = [multiply_logged, city_logged]
    # Agent would pick tools by name; here we call them directly
    product = tools[0](6, 7)
    info = tools[1]("Paris")
    print({"product": product, "info": info, "chain": verify_chain(sid, ledger).status})


if __name__ == "__main__":
    main()
