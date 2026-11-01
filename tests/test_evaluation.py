from pathlib import Path

from evidence_ledger.evaluation.metrics import false_positive_rate, precision_recall_f1
from evidence_ledger.evaluation.runner import run_evaluation
from evidence_ledger.ledger import EvidenceLedger
from evidence_ledger.storage import SQLiteStorage


def test_metrics_helpers():
    yt = ["SUPPORTED", "UNSUPPORTED", "SUPPORTED"]
    yp = ["SUPPORTED", "SUPPORTED", "SUPPORTED"]
    m = precision_recall_f1(yt, yp)
    assert m["tp"] == 2
    assert m["fp"] == 1
    assert false_positive_rate(yt, yp) == 1.0


def test_runner_smoke(tmp_path):
    root = Path(__file__).resolve().parents[1]
    scenarios = root / "data" / "scenarios.jsonl"
    gold = root / "data" / "ground_truth.jsonl"
    if not scenarios.exists():
        return
    store = SQLiteStorage(tmp_path / "eval.db")
    lg = EvidenceLedger(storage=store)
    out = run_evaluation(lg, scenarios, gold, results_dir=tmp_path / "results")
    assert out["metrics"]["n_claims"] >= 1
