"""HTTP API (FastAPI) for the research prototype.

Docs prioritize CLI; this API exists so the backend can be deployed on Vercel
as Python serverless functions without building a frontend.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from evidence_ledger import __version__
from evidence_ledger.claims.verifier import HybridVerifier
from evidence_ledger.ledger import EvidenceLedger
from evidence_ledger.tools.adapter import ToolAdapter

app = FastAPI(
    title="Tool Call Evidence Ledger",
    version=__version__,
    description="Backend API for the tamper-evident tool-call evidence ledger research prototype.",
)


def get_ledger() -> EvidenceLedger:
    lg = EvidenceLedger()
    lg.init()
    return lg


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


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "version": __version__, "service": "tool-call-evidence-ledger"}


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "tool-call-evidence-ledger",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }


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
    from evidence_ledger.tools.adapter import DEFAULT_TOOLS

    return {"tools": sorted(DEFAULT_TOOLS.keys())}
