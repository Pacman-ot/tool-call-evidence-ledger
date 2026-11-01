from evidence_ledger.ledger import EvidenceLedger
from evidence_ledger.models import IntegrityStatus
from evidence_ledger.storage import SQLiteStorage


def _seed(tmp_path):
    store = SQLiteStorage(tmp_path / "tamper.db")
    lg = EvidenceLedger(storage=store)
    sid = "tamper-session"
    lg.append(sid, "lookup_db", {"key": "orders"}, {"count": 42})
    lg.append(sid, "calculator", {"op": "add", "a": 1, "b": 1}, {"result": 2})
    return lg, store, sid


def test_edit_output_detected(tmp_path):
    lg, store, sid = _seed(tmp_path)
    entry = lg.list_entries(sid)[0]
    store.update_entry_raw(entry.entry_id, output_json={"count": 99})
    result = lg.verify(sid)
    assert result.status == IntegrityStatus.INVALID
    assert result.reason == "entry hash mismatch"
    assert result.first_failing_sequence == 1


def test_modify_previous_hash_detected(tmp_path):
    lg, store, sid = _seed(tmp_path)
    entry = lg.list_entries(sid)[1]
    store.update_entry_raw(entry.entry_id, previous_hash="0" * 64)
    result = lg.verify(sid)
    assert result.status == IntegrityStatus.INVALID
    assert result.reason in {"previous hash mismatch", "entry hash mismatch"}


def test_delete_entry_detected(tmp_path):
    lg, store, sid = _seed(tmp_path)
    entry = lg.list_entries(sid)[0]
    store.delete_entry(entry.entry_id)
    result = lg.verify(sid)
    assert result.status == IntegrityStatus.INVALID
    assert result.reason == "sequence gap/order"


def test_reorder_via_sequence_change_detected(tmp_path):
    lg, store, sid = _seed(tmp_path)
    e2 = lg.list_entries(sid)[1]
    store.update_entry_raw(e2.entry_id, sequence_no=9)
    result = lg.verify(sid)
    assert result.status == IntegrityStatus.INVALID
