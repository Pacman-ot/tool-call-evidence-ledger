"""Toy tools and the central tool adapter."""

from evidence_ledger.tools.adapter import DEFAULT_TOOLS, ToolAdapter
from evidence_ledger.tools.calculator import calculator
from evidence_ledger.tools.fake_weather import fake_weather
from evidence_ledger.tools.lookup_db import lookup_db

__all__ = [
    "ToolAdapter",
    "calculator",
    "lookup_db",
    "fake_weather",
    "DEFAULT_TOOLS",
]
