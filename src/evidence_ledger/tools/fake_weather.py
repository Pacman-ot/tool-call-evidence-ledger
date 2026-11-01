"""Fake weather toy tool with deterministic outputs."""

from __future__ import annotations

from typing import Any

_WEATHER = {
    "nyc": {"temp_c": 18.5, "condition": "cloudy", "humidity": 62},
    "sf": {"temp_c": 16.0, "condition": "foggy", "humidity": 80},
    "blr": {"temp_c": 27.0, "condition": "sunny", "humidity": 55},
}


def fake_weather(args: dict[str, Any]) -> dict[str, Any]:
    city = str(args.get("city", "")).lower()
    if city not in _WEATHER:
        raise KeyError(f"unknown city: {city}")
    return {"city": city, **_WEATHER[city]}
