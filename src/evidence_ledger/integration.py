"""One-liner integration: wrap any callable so invocations are ledgered."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar, overload

from evidence_ledger.ledger import EvidenceLedger
from evidence_ledger.models import EntryStatus, ToolInvokeResult

P = ParamSpec("P")
R = TypeVar("R")


def _call_args_to_json(
    fn: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Build a JSON-friendly record of the call (kwargs preferred)."""
    try:
        bound = inspect.signature(fn).bind_partial(*args, **kwargs)
        bound.apply_defaults()
        payload = dict(bound.arguments)
    except (TypeError, ValueError):
        payload = {"args": list(args), "kwargs": dict(kwargs)}
    # Drop bound methods' self/cls if present under those names when not useful
    return payload


def wrap_tool(
    ledger: EvidenceLedger,
    session_id: str,
    *,
    name: str | None = None,
    reraise: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator/factory: record every call to ``fn`` on the ledger.

    Example::

        @wrap_tool(ledger, session_id)
        def lookup(key: str) -> dict:
            return {"value": 42}

        lookup("orders")  # appended as tool_name=\"lookup\"
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        tool_name = name or getattr(fn, "__name__", "tool")

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            input_json = _call_args_to_json(fn, args, kwargs)
            try:
                output = fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                ledger.append(
                    session_id=session_id,
                    tool_name=tool_name,
                    input_json=input_json,
                    output_json=None,
                    status=EntryStatus.ERROR,
                    error_info={"type": type(exc).__name__, "message": str(exc)},
                )
                if reraise:
                    raise
                return None  # type: ignore[return-value]
            ledger.append(
                session_id=session_id,
                tool_name=tool_name,
                input_json=input_json,
                output_json=output,
                status=EntryStatus.SUCCESS,
            )
            return output

        wrapper._ledger_tool_name = tool_name  # type: ignore[attr-defined]
        wrapper._ledger_session_id = session_id  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator


class BoundSession:
    """Session-scoped helpers: ``@session.tool`` and ``session.invoke``."""

    def __init__(self, ledger: EvidenceLedger, session_id: str) -> None:
        self.ledger = ledger
        self.session_id = session_id

    @overload
    def tool(self, fn: Callable[P, R], /) -> Callable[P, R]: ...

    @overload
    def tool(
        self,
        fn: None = None,
        /,
        *,
        name: str | None = None,
        reraise: bool = True,
    ) -> Callable[[Callable[P, R]], Callable[P, R]]: ...

    def tool(
        self,
        fn: Callable[P, R] | None = None,
        /,
        *,
        name: str | None = None,
        reraise: bool = True,
    ) -> Any:
        """Use as ``@session.tool`` or ``@session.tool(name=\"search\")``."""
        if fn is not None:
            return wrap_tool(self.ledger, self.session_id, name=name, reraise=reraise)(fn)
        return wrap_tool(self.ledger, self.session_id, name=name, reraise=reraise)

    def invoke(self, tool_name: str, args: dict[str, Any], fn: Callable[..., Any]) -> ToolInvokeResult:
        """Call ``fn(args)`` (dict-style, like OpenAI function calling) and ledger it."""
        from evidence_ledger.tools.adapter import ToolAdapter

        adapter = ToolAdapter(self.ledger, tools={tool_name: fn})
        return adapter.invoke(self.session_id, tool_name, args)
