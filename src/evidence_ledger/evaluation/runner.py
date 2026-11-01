"""Minimal evaluation runner for labelled scenarios."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from evidence_ledger.claims.verifier import HybridVerifier
from evidence_ledger.evaluation.baselines import BaselineAJudge, BaselineBJudge
from evidence_ledger.evaluation.dataset import load_jsonl
from evidence_ledger.evaluation.metrics import false_positive_rate, precision_recall_f1
from evidence_ledger.ledger import EvidenceLedger
from evidence_ledger.models import Verdict
from evidence_ledger.tools.adapter import ToolAdapter


def _run_scenario_tools(adapter: ToolAdapter, session_id: str, tool_calls: list[dict[str, Any]]) -> None:
    for call in tool_calls:
        adapter.invoke(session_id, call["tool"], call.get("args") or {})


def run_evaluation(
    ledger: EvidenceLedger,
    scenarios_path: Path | str,
    ground_truth_path: Path | str,
    results_dir: Path | str = "results",
) -> dict[str, Any]:
    scenarios = {s["scenario_id"]: s for s in load_jsonl(scenarios_path)}
    gold = load_jsonl(ground_truth_path)
    adapter = ToolAdapter(ledger)
    hybrid = HybridVerifier(ledger)
    baseline_a = BaselineAJudge()
    baseline_b = BaselineBJudge()

    run_id = str(uuid.uuid4())
    records: list[dict[str, Any]] = []

    by_scenario: dict[str, list[dict[str, Any]]] = {}
    for g in gold:
        by_scenario.setdefault(g["scenario_id"], []).append(g)

    for scenario_id, claims_gold in by_scenario.items():
        scenario = scenarios.get(scenario_id)
        if not scenario:
            continue
        session_id = f"eval-{scenario_id}-{run_id[:8]}"
        _run_scenario_tools(adapter, session_id, scenario.get("tool_calls") or [])
        answer = scenario.get("answer") or ""

        t0 = time.monotonic()
        report = hybrid.verify(session_id, answer)
        hybrid_ms = (time.monotonic() - t0) * 1000

        entries = ledger.list_entries(session_id)
        for g in claims_gold:
            text = g["claim_text"]
            # Hybrid: find matching claim by text or id
            hv = next((c for c in report.claims if c.claim_text == text or c.claim_id == g.get("claim_id")), None)
            hybrid_verdict = hv.verdict.value if hv else Verdict.UNSUPPORTED.value

            a = baseline_a.assess(text, entries)
            b = baseline_b.assess(text, entries)
            records.append(
                {
                    "run_id": run_id,
                    "scenario_id": scenario_id,
                    "claim_id": g.get("claim_id"),
                    "claim_text": text,
                    "gold_verdict": g.get("gold_verdict"),
                    "hybrid_verdict": hybrid_verdict,
                    "baseline_a_verdict": a.verdict.value,
                    "baseline_b_verdict": b.verdict.value,
                    "hybrid_latency_ms": hybrid_ms,
                }
            )

    gold_v = [r["gold_verdict"] for r in records]
    metrics = {
        "hybrid": precision_recall_f1(gold_v, [r["hybrid_verdict"] for r in records]),
        "baseline_a": precision_recall_f1(gold_v, [r["baseline_a_verdict"] for r in records]),
        "baseline_b": precision_recall_f1(gold_v, [r["baseline_b_verdict"] for r in records]),
        "hybrid_fpr": false_positive_rate(gold_v, [r["hybrid_verdict"] for r in records]),
        "n_claims": len(records),
        "run_id": run_id,
    }

    out = Path(results_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{run_id}.json").write_text(
        json.dumps({"metrics": metrics, "records": records}, indent=2),
        encoding="utf-8",
    )
    return {"metrics": metrics, "records": records}
