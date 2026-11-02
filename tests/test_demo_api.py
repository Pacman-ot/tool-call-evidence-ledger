"""Stateless demo endpoints — the path that works on multi-instance Vercel."""

from fastapi.testclient import TestClient

from evidence_ledger.api import app

client = TestClient(app)


def test_demo_home_serves_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert b"Evidence Ledger" in r.content


def test_demo_run_full_scenario():
    r = client.post("/demo/run", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["verify"]["status"] == "VALID"
    assert body["verify"]["entries_checked"] >= 1
    assert len(body["entries"]) >= 1
    assert body["tamper"]["verify"]["status"] == "INVALID"
    assert body["tamper"]["verify"]["first_failing_sequence"] == 1
    assert body["answer_report"]["claims"]
    # honest entries still VALID-shaped in primary payload
    assert body["entries"][0]["output_json"]["count"] == 42


def test_demo_invoke_carry_ledger():
    a = client.post(
        "/demo/invoke",
        json={"tool_name": "lookup_db", "args": {"key": "orders"}, "entries": []},
    )
    assert a.status_code == 200
    entries = a.json()["entries"]
    assert a.json()["verify"]["status"] == "VALID"

    b = client.post(
        "/demo/invoke",
        json={
            "session_id": a.json()["session_id"],
            "entries": entries,
            "tool_name": "calculator",
            "args": {"op": "add", "a": 40, "b": 2},
        },
    )
    assert b.status_code == 200
    assert len(b.json()["entries"]) == 2
    assert b.json()["verify"]["status"] == "VALID"
    assert b.json()["entries"][1]["previous_hash"] == b.json()["entries"][0]["entry_hash"]


def test_demo_tamper_and_answer():
    run = client.post("/demo/run", json={"include_tamper": False}).json()
    entries = run["entries"]

    v = client.post("/demo/verify", json={"entries": entries}).json()
    assert v["verify"]["status"] == "VALID"

    t = client.post(
        "/demo/tamper",
        json={"entries": entries, "sequence_no": 1, "output_patch": {"count": 999}},
    ).json()
    assert t["verify_after"]["status"] == "INVALID"
    assert t["verify_after"]["first_failing_sequence"] == 1

    ans = client.post(
        "/demo/verify-answer",
        json={"entries": entries, "answer": "There are 42 orders in the west region."},
    ).json()
    assert ans["claims"]
    assert ans["claims"][0]["verdict"] in {"SUPPORTED", "PARTIALLY_SUPPORTED"}


def test_demo_presets():
    r = client.get("/demo/presets")
    assert r.status_code == 200
    assert len(r.json()["presets"]) >= 1


def test_api_root_json():
    r = client.get("/api")
    assert r.status_code == 200
    assert r.json()["demo_run"] == "POST /demo/run"
