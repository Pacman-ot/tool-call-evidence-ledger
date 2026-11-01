from fastapi.testclient import TestClient

from evidence_ledger.api import app


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_invoke_and_verify_flow(monkeypatch, tmp_path):
    monkeypatch.setenv("LEDGER_DB_PATH", str(tmp_path / "api.db"))
    # Recreate settings pick up env — EvidenceLedger reads Settings() fresh each call.
    from evidence_ledger import config

    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: config.Settings(ledger_db_path=str(tmp_path / "api.db")),
    )

    s = client.post("/sessions")
    assert s.status_code == 200
    sid = s.json()["session_id"]

    inv = client.post(
        "/tools/invoke",
        json={"session_id": sid, "tool_name": "lookup_db", "args": {"key": "orders"}},
    )
    assert inv.status_code == 200
    assert inv.json()["status"] == "success"

    chain = client.get(f"/ledger/{sid}/verify")
    assert chain.status_code == 200
    assert chain.json()["status"] == "VALID"

    ans = client.post(
        "/verify/answer",
        json={"session_id": sid, "answer": "The lookup returned 42 records."},
    )
    assert ans.status_code == 200
    body = ans.json()
    assert body["claims"][0]["verdict"] == "SUPPORTED"
