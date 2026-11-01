import pytest

from evidence_ledger import EvidenceLedger, SQLiteStorage, wrap_tool, verify_chain
from evidence_ledger.models import EntryStatus, IntegrityStatus


def test_wrap_tool_records_success(tmp_path):
    lg = EvidenceLedger(storage=SQLiteStorage(tmp_path / "t.db"))
    sid = lg.create_session("s-wrap")

    @wrap_tool(lg, sid)
    def add(a: int, b: int) -> dict:
        return {"result": a + b}

    assert add(2, 3) == {"result": 5}
    entries = lg.list_entries(sid)
    assert len(entries) == 1
    assert entries[0].tool_name == "add"
    assert entries[0].input_json == {"a": 2, "b": 3}
    assert entries[0].output_json == {"result": 5}
    assert entries[0].status == EntryStatus.SUCCESS
    assert verify_chain(sid, lg).status == IntegrityStatus.VALID


def test_ledger_tool_decorator_and_session(tmp_path):
    lg = EvidenceLedger(storage=SQLiteStorage(tmp_path / "t.db"))
    session = lg.session("s-session")

    @session.tool(name="lookup")
    def lookup(key: str) -> dict:
        return {key: 1}

    @session.tool
    def ping() -> str:
        return "pong"

    assert lookup("x") == {"x": 1}
    assert ping() == "pong"
    assert len(lg.list_entries(session.session_id)) == 2


def test_wrap_tool_error_reraise(tmp_path):
    lg = EvidenceLedger(storage=SQLiteStorage(tmp_path / "t.db"))
    sid = "s-err"

    @wrap_tool(lg, sid)
    def boom() -> None:
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError):
        boom()
    e = lg.list_entries(sid)[0]
    assert e.status == EntryStatus.ERROR
    assert e.error_info["type"] == "RuntimeError"
