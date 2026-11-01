from evidence_ledger.claims.structured_matcher import StructuredMatcher
from evidence_ledger.models import EntryStatus, LedgerEntry, MatchDecision


def _entry(eid, output, seq=1):
    return LedgerEntry(
        session_id="s",
        sequence_no=seq,
        entry_id=eid,
        timestamp_utc="2026-01-01T00:00:00.000Z",
        tool_name="lookup_db",
        input_json={"key": "x"},
        output_json=output,
        status=EntryStatus.SUCCESS,
        error_info=None,
        schema_version=1,
        previous_hash="GENESIS_V1",
        entry_hash="abc",
    )


def test_exact_numeric():
    m = StructuredMatcher()
    r = m.match("The lookup returned 42 records.", [_entry("s:1", {"count": 42})])
    assert r.decision == MatchDecision.MATCH_SUPPORTED
    assert r.evidence[0].field_path.endswith("count")


def test_wrong_value_contradicted():
    m = StructuredMatcher()
    r = m.match("The lookup returned 52 records.", [_entry("s:1", {"count": 42})])
    assert r.decision == MatchDecision.MATCH_CONTRADICTED


def test_percentage_change():
    m = StructuredMatcher()
    r = m.match(
        "The value increased by 20%.",
        [_entry("s:1", {"old_value": 100, "new_value": 120})],
    )
    assert r.decision == MatchDecision.MATCH_SUPPORTED
    assert r.method == "structured_derived"


def test_absent_unresolved():
    m = StructuredMatcher()
    r = m.match("Service performance is reduced.", [_entry("s:1", {"status": "degraded"})])
    assert r.decision in {MatchDecision.UNRESOLVED, MatchDecision.MATCH_SUPPORTED}


def test_date_delta():
    m = StructuredMatcher()
    r = m.match(
        "There were 10 days between the start and end.",
        [_entry("s:1", {"start_date": "2026-01-01", "end_date": "2026-01-11"})],
    )
    assert r.decision == MatchDecision.MATCH_SUPPORTED
