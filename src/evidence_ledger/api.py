"""HTTP API (FastAPI) for the research prototype + demo UI.

On Vercel, /tmp SQLite is per-instance and ephemeral, so multi-request
session flows are unreliable. Prefer the /demo/* endpoints which keep the
ledger in the request body (or run a full scenario in one request).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from evidence_ledger import __version__
from evidence_ledger.claims.verifier import HybridVerifier
from evidence_ledger.ledger import EvidenceLedger
from evidence_ledger.models import EntryStatus, LedgerEntry
from evidence_ledger.storage import MemoryStorage
from evidence_ledger.tools.adapter import DEFAULT_TOOLS, ToolAdapter

app = FastAPI(
    title="Tool Call Evidence Ledger",
    version=__version__,
    description=(
        "Tamper-evident tool-call evidence ledger. "
        "Use /demo/* for reliable serverless demos (ledger travels with the request)."
    ),
)


def _static_dir() -> Path:
    """Demo assets ship inside the package so Vercel file-tracing includes them."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "static",
        here.parents[1] / "static",  # fallback
        Path.cwd() / "src" / "evidence_ledger" / "static",
        Path.cwd() / "public",
    ]
    for c in candidates:
        if (c / "index.html").exists():
            return c
    return candidates[0]


PUBLIC_DIR = _static_dir()


def get_ledger() -> EvidenceLedger:
    lg = EvidenceLedger()
    lg.init()
    return lg


def ephemeral_ledger(
    entries: list[LedgerEntry] | list[dict[str, Any]] | None = None,
) -> EvidenceLedger:
    """In-memory ledger seeded from client-carried entries (stateless across instances)."""
    parsed: list[LedgerEntry] = []
    for item in entries or []:
        if isinstance(item, LedgerEntry):
            parsed.append(item)
        else:
            parsed.append(LedgerEntry.model_validate(item))
    store = MemoryStorage(parsed)
    lg = EvidenceLedger(storage=store)
    lg.init()
    return lg


def _dump_entries(lg: EvidenceLedger, session_id: str) -> list[dict[str, Any]]:
    return [e.model_dump(mode="json") for e in lg.list_entries(session_id)]


class SessionCreateResponse(BaseModel):
    session_id: str


class InvokeRequest(BaseModel):
    session_id: str
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)


class AppendRequest(BaseModel):
    session_id: str
    tool_name: str
    input_json: dict[str, Any] = Field(default_factory=dict)
    output_json: Any | None = None
    status: str = "success"
    error_info: dict[str, Any] | None = None


class VerifyAnswerRequest(BaseModel):
    session_id: str
    answer: str


class DemoCall(BaseModel):
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)


class DemoInvokeRequest(BaseModel):
    """Stateless invoke: optional prior entries travel with the request."""

    session_id: str | None = None
    entries: list[dict[str, Any]] = Field(default_factory=list)
    tool_name: str
    args: dict[str, Any] = Field(default_factory=dict)


class DemoEntriesRequest(BaseModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)
    session_id: str | None = None


class DemoTamperRequest(BaseModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)
    sequence_no: int = 1
    output_patch: dict[str, Any] = Field(default_factory=lambda: {"count": 999})


class DemoVerifyAnswerRequest(BaseModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)
    answer: str
    session_id: str | None = None


class DemoRunRequest(BaseModel):
    """One-shot full walkthrough — safe on serverless."""

    question: str = "How many orders are in the west region, and what is 40 + 2?"
    calls: list[DemoCall] | None = None
    answer: str | None = None
    include_tamper: bool = True
    tamper_sequence: int = 1
    tamper_output_patch: dict[str, Any] | None = None


DEFAULT_DEMO_CALLS: list[DemoCall] = [
    DemoCall(tool_name="lookup_db", args={"key": "orders"}),
    DemoCall(tool_name="calculator", args={"op": "add", "a": 40, "b": 2}),
]

DEFAULT_DEMO_ANSWER = (
    "There are 42 orders in the west region. 40 + 2 equals 42."
)


# ---------------------------------------------------------------------------
# Static demo UI
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def demo_home() -> FileResponse:
    index = PUBLIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="demo UI missing")
    return FileResponse(index, media_type="text/html")


@app.get("/api")
def api_root() -> dict[str, Any]:
    return {
        "service": "tool-call-evidence-ledger",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
        "demo": "/",
        "demo_run": "POST /demo/run",
        "note": (
            "Session endpoints that rely on /tmp are unreliable across Vercel "
            "instances. Prefer /demo/* which carry the ledger in the request."
        ),
    }


if PUBLIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(PUBLIC_DIR)), name="static")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "version": __version__, "service": "tool-call-evidence-ledger"}


# ---------------------------------------------------------------------------
# Legacy session API (local / same-instance only)
# ---------------------------------------------------------------------------


@app.post("/sessions", response_model=SessionCreateResponse)
def create_session() -> SessionCreateResponse:
    lg = get_ledger()
    return SessionCreateResponse(session_id=lg.create_session())


@app.post("/tools/invoke")
def invoke_tool(body: InvokeRequest) -> dict[str, Any]:
    lg = get_ledger()
    adapter = ToolAdapter(lg)
    result = adapter.invoke(body.session_id, body.tool_name, body.args)
    return result.model_dump(mode="json")


@app.post("/ledger/append")
def append_entry(body: AppendRequest) -> dict[str, Any]:
    lg = get_ledger()
    entry = lg.append(
        session_id=body.session_id,
        tool_name=body.tool_name,
        input_json=body.input_json,
        output_json=body.output_json,
        status=body.status,
        error_info=body.error_info,
    )
    return entry.model_dump(mode="json")


@app.get("/ledger/{session_id}")
def list_session(session_id: str) -> dict[str, Any]:
    lg = get_ledger()
    entries = lg.list_entries(session_id)
    return {"session_id": session_id, "entries": [e.model_dump(mode="json") for e in entries]}


@app.get("/ledger/{session_id}/verify")
def verify_chain(session_id: str) -> dict[str, Any]:
    lg = get_ledger()
    return lg.verify(session_id).model_dump(mode="json")


@app.post("/verify/answer")
def verify_answer(body: VerifyAnswerRequest) -> dict[str, Any]:
    lg = get_ledger()
    if not body.answer.strip():
        raise HTTPException(status_code=400, detail="answer must be non-empty")
    report = HybridVerifier(lg).verify(body.session_id, body.answer)
    return report.model_dump(mode="json")


@app.get("/tools")
def list_tools() -> dict[str, Any]:
    return {
        "tools": sorted(DEFAULT_TOOLS.keys()),
        "schemas": {
            "lookup_db": {"key": "orders|users|incidents", "field": "optional"},
            "calculator": {"op": "add|sub|mul|div", "a": "number", "b": "number"},
            "fake_weather": {"city": "string"},
        },
    }


# ---------------------------------------------------------------------------
# Stateless demo API — reliable on Vercel
# ---------------------------------------------------------------------------


@app.post("/demo/invoke")
def demo_invoke(body: DemoInvokeRequest) -> dict[str, Any]:
    lg = ephemeral_ledger(body.entries)
    sid = body.session_id or (body.entries[0]["session_id"] if body.entries else lg.create_session())
    if body.tool_name not in DEFAULT_TOOLS:
        raise HTTPException(status_code=400, detail=f"unknown tool: {body.tool_name}")
    adapter = ToolAdapter(lg)
    result = adapter.invoke(sid, body.tool_name, body.args)
    entries = _dump_entries(lg, sid)
    return {
        "session_id": sid,
        "result": result.model_dump(mode="json"),
        "entries": entries,
        "verify": lg.verify(sid).model_dump(mode="json"),
    }


@app.post("/demo/verify")
def demo_verify(body: DemoEntriesRequest) -> dict[str, Any]:
    if not body.entries:
        raise HTTPException(status_code=400, detail="entries required")
    sid = body.session_id or body.entries[0]["session_id"]
    lg = ephemeral_ledger(body.entries)
    return {
        "session_id": sid,
        "entries": _dump_entries(lg, sid),
        "verify": lg.verify(sid).model_dump(mode="json"),
    }


@app.post("/demo/tamper")
def demo_tamper(body: DemoTamperRequest) -> dict[str, Any]:
    if not body.entries:
        raise HTTPException(status_code=400, detail="entries required")
    sid = body.entries[0]["session_id"]
    lg = ephemeral_ledger(body.entries)
    target = next((e for e in lg.list_entries(sid) if e.sequence_no == body.sequence_no), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"no entry at sequence {body.sequence_no}")

    before = lg.verify(sid).model_dump(mode="json")
    patched = copy.deepcopy(target.output_json) if isinstance(target.output_json, dict) else {}
    if not isinstance(patched, dict):
        patched = {"value": patched}
    patched.update(body.output_patch)
    # Mutate stored payload without rehashing — classic tamper.
    lg.storage.update_entry_raw(target.entry_id, output_json=patched)
    after = lg.verify(sid).model_dump(mode="json")
    return {
        "session_id": sid,
        "tampered_sequence": body.sequence_no,
        "output_patch": body.output_patch,
        "entries": _dump_entries(lg, sid),
        "verify_before": before,
        "verify_after": after,
        "explanation": (
            "The output was changed in storage but entry_hash was left alone. "
            "Rehashing the protected payload no longer matches, so the chain is INVALID "
            f"at sequence {after.get('first_failing_sequence')}."
        ),
    }


@app.post("/demo/verify-answer")
def demo_verify_answer(body: DemoVerifyAnswerRequest) -> dict[str, Any]:
    if not body.answer.strip():
        raise HTTPException(status_code=400, detail="answer must be non-empty")
    if not body.entries:
        raise HTTPException(status_code=400, detail="entries required")
    sid = body.session_id or body.entries[0]["session_id"]
    lg = ephemeral_ledger(body.entries)
    report = HybridVerifier(lg).verify(sid, body.answer)
    return report.model_dump(mode="json")


@app.post("/demo/run")
def demo_run(body: DemoRunRequest | None = None) -> dict[str, Any]:
    """Record tool calls → verify VALID → optional tamper → INVALID → claim check.

    Entire scenario runs inside one serverless invocation with MemoryStorage.
    """
    req = body or DemoRunRequest()
    calls = req.calls or DEFAULT_DEMO_CALLS
    answer = req.answer if req.answer is not None else DEFAULT_DEMO_ANSWER
    patch = req.tamper_output_patch or {"count": 999}

    lg = ephemeral_ledger()
    sid = lg.create_session()
    adapter = ToolAdapter(lg)

    steps: list[dict[str, Any]] = []
    for call in calls:
        result = adapter.invoke(sid, call.tool_name, call.args)
        steps.append(
            {
                "tool_name": call.tool_name,
                "args": call.args,
                "result": result.model_dump(mode="json"),
            }
        )

    entries_valid = _dump_entries(lg, sid)
    verify_valid = lg.verify(sid).model_dump(mode="json")

    answer_report = HybridVerifier(lg).verify(sid, answer).model_dump(mode="json")

    tamper_block: dict[str, Any] | None = None
    if req.include_tamper and entries_valid:
        # Work on a fresh copy so the valid chain remains in the response.
        tampered = ephemeral_ledger(entries_valid)
        target = next(
            (e for e in tampered.list_entries(sid) if e.sequence_no == req.tamper_sequence),
            None,
        )
        if target is not None:
            patched = copy.deepcopy(target.output_json) if isinstance(target.output_json, dict) else {}
            if not isinstance(patched, dict):
                patched = {"value": patched}
            patched.update(patch)
            tampered.storage.update_entry_raw(target.entry_id, output_json=patched)
            tamper_block = {
                "tampered_sequence": req.tamper_sequence,
                "output_patch": patch,
                "entries": _dump_entries(tampered, sid),
                "verify": tampered.verify(sid).model_dump(mode="json"),
                "explanation": (
                    "Mutating a stored tool output without recomputing entry_hash "
                    "breaks the SHA-256 chain at that sequence."
                ),
            }

    return {
        "mode": "stateless",
        "question": req.question,
        "session_id": sid,
        "steps": steps,
        "entries": entries_valid,
        "verify": verify_valid,
        "answer": answer,
        "answer_report": answer_report,
        "tamper": tamper_block,
        "presenter_notes": [
            "Each tool call is canonicalized and hashed with the previous entry hash.",
            "GENESIS_V1 seeds the first previous_hash.",
            "verify() recomputes every hash; any byte change → INVALID at that sequence.",
            "Claim verification matches answer fragments against ledger evidence.",
            "This endpoint is one request so Vercel /tmp isolation cannot break the demo.",
        ],
    }


@app.get("/demo/presets")
def demo_presets() -> dict[str, Any]:
    return {
        "presets": [
            {
                "id": "orders",
                "question": "How many orders are in the west region, and what is 40 + 2?",
                "calls": [c.model_dump() for c in DEFAULT_DEMO_CALLS],
                "answer": DEFAULT_DEMO_ANSWER,
                "unsupported_answer": "There are 9000 orders in the north region.",
            },
            {
                "id": "weather",
                "question": "What is the weather in NYC?",
                "calls": [{"tool_name": "fake_weather", "args": {"city": "nyc"}}],
                "answer": "NYC is cloudy at 18.5 C with humidity 62.",
                "unsupported_answer": "NYC is 40 C and sunny.",
            },
            {
                "id": "users",
                "question": "How many users are in the east region?",
                "calls": [{"tool_name": "lookup_db", "args": {"key": "users"}}],
                "answer": "There are 17 users in the east region.",
                "unsupported_answer": "There are 500 users in the west region.",
            },
        ]
    }
