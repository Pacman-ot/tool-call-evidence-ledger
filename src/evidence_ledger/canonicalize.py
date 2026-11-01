"""Deterministic JSON canonicalization for hash inputs.

Implements a narrowly specified, RFC 8785-inspired serializer:
- UTF-8
- object keys sorted lexicographically by Unicode code point
- no insignificant whitespace
- arrays preserve order
- reject float NaN / Infinity
- integers and non-integer floats distinguished only by JSON number form
"""

from __future__ import annotations

import math
from typing import Any


class CanonicalizationError(ValueError):
    """Raised when a value cannot be deterministically serialized."""


def _encode_string(s: str) -> str:
    out: list[str] = ['"']
    for ch in s:
        code = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\b":
            out.append("\\b")
        elif ch == "\f":
            out.append("\\f")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif code < 0x20:
            out.append(f"\\u{code:04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _encode_number(n: int | float) -> str:
    if isinstance(n, bool):
        # bool is a subclass of int; callers should avoid reaching here.
        raise CanonicalizationError("boolean must be handled before number")
    if isinstance(n, int):
        return str(n)
    if not math.isfinite(n):
        raise CanonicalizationError("NaN/Infinity are not allowed in canonical JSON")
    # Use shortest round-trip representation without scientific notation where possible.
    text = format(n, ".15g")
    if text == "-0":
        text = "0"
    if "." not in text and "e" not in text and "E" not in text:
        # Ensure floats that are whole numbers keep a decimal marker? RFC 8785
        # allows integers without decimal. Keep as-is for ints-as-float.
        pass
    return text


def canonicalize(value: Any) -> str:
    """Return a deterministic JSON string for *value*."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return _encode_string(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return _encode_number(value)
    if isinstance(value, float):
        return _encode_number(value)
    if isinstance(value, list):
        return "[" + ",".join(canonicalize(v) for v in value) + "]"
    if isinstance(value, tuple):
        return "[" + ",".join(canonicalize(v) for v in value) + "]"
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda kv: kv[0])
        parts = []
        for k, v in items:
            if not isinstance(k, str):
                raise CanonicalizationError(f"object keys must be strings, got {type(k)}")
            parts.append(_encode_string(k) + ":" + canonicalize(v))
        return "{" + ",".join(parts) + "}"
    raise CanonicalizationError(f"unsupported type for canonicalization: {type(value)}")


def canonicalize_bytes(value: Any) -> bytes:
    return canonicalize(value).encode("utf-8")
