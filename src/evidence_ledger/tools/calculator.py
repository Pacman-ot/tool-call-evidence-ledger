"""Simple calculator toy tool."""

from __future__ import annotations

from typing import Any


def calculator(args: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a tiny arithmetic expression over numbers.

    Supported ops: add, sub, mul, div.
    args: {op: str, a: number, b: number}
    """
    op = args.get("op")
    a = args.get("a")
    b = args.get("b")
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise ValueError("a and b must be numbers")
    if op == "add":
        result = a + b
    elif op == "sub":
        result = a - b
    elif op == "mul":
        result = a * b
    elif op == "div":
        if b == 0:
            raise ZeroDivisionError("division by zero")
        result = a / b
    else:
        raise ValueError(f"unsupported op: {op}")
    return {"op": op, "a": a, "b": b, "result": result}
