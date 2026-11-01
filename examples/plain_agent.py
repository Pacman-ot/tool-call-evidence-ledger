"""Minimal agent integration: decorate any tool function.

Run from repo root after ``pip install -e .``::

    python examples/plain_agent.py
"""

from __future__ import annotations

from evidence_ledger import EvidenceLedger, SQLiteStorage, verify_answer, verify_chain


def main() -> None:
    store = SQLiteStorage("/tmp/evidence-ledger-demo.db")
    ledger = EvidenceLedger(storage=store)
    session = ledger.session("demo-plain")

    @session.tool
    def calculator(op: str, a: float, b: float) -> dict:
        ops = {
            "add": a + b,
            "mul": a * b,
            "div": a / b if b else None,
        }
        if op not in ops or ops[op] is None:
            raise ValueError(f"bad op: {op}")
        return {"result": ops[op]}

    @session.tool(name="lookup_db")
    def lookup(key: str) -> dict:
        db = {"orders": 42, "revenue": 1250.5}
        if key not in db:
            raise KeyError(key)
        return {key: db[key]}

    # Agent "uses tools"
    calc = calculator(op="add", a=20, b=22)
    orders = lookup("orders")
    answer = f"Orders={orders['orders']}; 20+22={calc['result']}"

    chain = verify_chain(session.session_id, ledger)
    report = verify_answer(session.session_id, answer, ledger)
    print("chain:", chain.status, "entries:", chain.entries_checked)
    print("answer aggregate:", report.aggregate_status)
    for c in report.claims:
        print(f"  - {c.claim_text!r} -> {c.verdict}")


if __name__ == "__main__":
    main()
