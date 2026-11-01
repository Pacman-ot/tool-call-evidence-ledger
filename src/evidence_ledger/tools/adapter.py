"""Central tool adapter: invoke + capture into the ledger."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from evidence_ledger.ledger import EvidenceLedger
from evidence_ledger.models import EntryStatus, ToolInvokeResult
from evidence_ledger.tools.calculator import calculator
from evidence_ledger.tools.fake_weather import fake_weather
from evidence_ledger.tools.lookup_db import lookup_db

DEFAULT_TOOLS = {
    "calculator": calculator,
    "lookup_db": lookup_db,
    "fake_weather": fake_weather,
}


class ToolAdapter:
    def __init__(
        self,
        ledger: EvidenceLedger,
        tools: dict[str, Callable[[dict[str, Any]], Any]] | None = None,
        timeout_s: float | None = None,
    ) -> None:
        self.ledger = ledger
        self.tools = tools or dict(DEFAULT_TOOLS)
        self.timeout_s = timeout_s

    def register(self, name: str, fn: Callable[[dict[str, Any]], Any]) -> None:
        self.tools[name] = fn

    def invoke(self, session_id: str, tool_name: str, args: dict[str, Any]) -> ToolInvokeResult:
        fn = self.tools.get(tool_name)
        if fn is None:
            entry = self.ledger.append(
                session_id=session_id,
                tool_name=tool_name,
                input_json=args,
                output_json=None,
                status=EntryStatus.ERROR,
                error_info={"type": "UnknownTool", "message": f"unknown tool: {tool_name}"},
            )
            return ToolInvokeResult(
                tool_name=tool_name,
                output=None,
                status=EntryStatus.ERROR,
                error_info=entry.error_info,
                entry_id=entry.entry_id,
                entry_hash=entry.entry_hash,
            )

        started = time.monotonic()
        try:
            output = fn(args)
            elapsed = time.monotonic() - started
            if self.timeout_s is not None and elapsed > self.timeout_s:
                entry = self.ledger.append(
                    session_id=session_id,
                    tool_name=tool_name,
                    input_json=args,
                    output_json=None,
                    status=EntryStatus.TIMEOUT,
                    error_info={"type": "Timeout", "message": f"exceeded {self.timeout_s}s"},
                )
                return ToolInvokeResult(
                    tool_name=tool_name,
                    output=None,
                    status=EntryStatus.TIMEOUT,
                    error_info=entry.error_info,
                    entry_id=entry.entry_id,
                    entry_hash=entry.entry_hash,
                )
            entry = self.ledger.append(
                session_id=session_id,
                tool_name=tool_name,
                input_json=args,
                output_json=output,
                status=EntryStatus.SUCCESS,
            )
            return ToolInvokeResult(
                tool_name=tool_name,
                output=output,
                status=EntryStatus.SUCCESS,
                entry_id=entry.entry_id,
                entry_hash=entry.entry_hash,
            )
        except Exception as exc:  # noqa: BLE001 — capture into ledger
            entry = self.ledger.append(
                session_id=session_id,
                tool_name=tool_name,
                input_json=args,
                output_json=None,
                status=EntryStatus.ERROR,
                error_info={"type": type(exc).__name__, "message": str(exc)},
            )
            return ToolInvokeResult(
                tool_name=tool_name,
                output=None,
                status=EntryStatus.ERROR,
                error_info=entry.error_info,
                entry_id=entry.entry_id,
                entry_hash=entry.entry_hash,
            )
