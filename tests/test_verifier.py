from evidence_ledger.claims.verifier import HybridVerifier
from evidence_ledger.ledger import EvidenceLedger
from evidence_ledger.models import IntegrityStatus, Verdict
from evidence_ledger.storage import SQLiteStorage
from evidence_ledger.tools.adapter import ToolAdapter


def test_end_to_end_supported(tmp_path):
    store = SQLiteStorage(tmp_path / "v.db")
    lg = EvidenceLedger(storage=store)
    adapter = ToolAdapter(lg)
    sid = "sess-ok"
    adapter.invoke(sid, "lookup_db", {"key": "orders"})
    report = HybridVerifier(lg).verify(sid, "The lookup returned 42 records.")
    assert report.chain_integrity.status == IntegrityStatus.VALID
    assert report.claims[0].verdict == Verdict.SUPPORTED
    assert report.aggregate_status == "FULLY_SUPPORTED"


def test_end_to_end_unsupported(tmp_path):
    store = SQLiteStorage(tmp_path / "v.db")
    lg = EvidenceLedger(storage=store)
    adapter = ToolAdapter(lg)
    sid = "sess-bad"
    adapter.invoke(sid, "lookup_db", {"key": "orders"})
    report = HybridVerifier(lg).verify(sid, "The lookup returned 52 records.")
    assert report.claims[0].verdict == Verdict.UNSUPPORTED
    assert report.aggregate_status == "HAS_UNSUPPORTED"


def test_integrity_failure_blocks_trust(tmp_path):
    store = SQLiteStorage(tmp_path / "v.db")
    lg = EvidenceLedger(storage=store)
    adapter = ToolAdapter(lg)
    sid = "sess-tamper"
    adapter.invoke(sid, "lookup_db", {"key": "orders"})
    entry = lg.list_entries(sid)[0]
    store.update_entry_raw(entry.entry_id, output_json={"count": 999})
    report = HybridVerifier(lg).verify(sid, "The lookup returned 999 records.")
    assert report.chain_integrity.status == IntegrityStatus.INVALID
    assert report.aggregate_status == "INTEGRITY_FAILURE"
