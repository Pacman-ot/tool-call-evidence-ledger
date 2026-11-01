from evidence_ledger.ledger import EvidenceLedger
from evidence_ledger.models import EntryStatus, IntegrityStatus
from evidence_ledger.storage import SQLiteStorage


def test_append_and_order(tmp_path):
    store = SQLiteStorage(tmp_path / "t.db")
    lg = EvidenceLedger(storage=store)
    sid = lg.create_session("s1")
    e1 = lg.append(sid, "calculator", {"op": "add", "a": 1, "b": 2}, {"result": 3})
    e2 = lg.append(sid, "lookup_db", {"key": "orders"}, {"count": 42})
    entries = lg.list_entries(sid)
    assert [e.sequence_no for e in entries] == [1, 2]
    assert e1.previous_hash == "GENESIS_V1"
    assert e2.previous_hash == e1.entry_hash
    assert e1.entry_id == "s1:1"


def test_failed_tool_persisted(tmp_path):
    store = SQLiteStorage(tmp_path / "t.db")
    lg = EvidenceLedger(storage=store)
    sid = "s-err"
    e = lg.append(
        sid,
        "lookup_db",
        {"key": "missing"},
        None,
        status=EntryStatus.ERROR,
        error_info={"type": "KeyError", "message": "missing"},
    )
    assert e.status == EntryStatus.ERROR
    assert lg.verify(sid).status == IntegrityStatus.VALID


def test_empty_session(tmp_path):
    store = SQLiteStorage(tmp_path / "t.db")
    lg = EvidenceLedger(storage=store)
    result = lg.verify("no-such")
    assert result.status == IntegrityStatus.VALID
    assert result.entries_checked == 0
