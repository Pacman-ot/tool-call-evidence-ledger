# Evaluation harness

Modules under `evidence_ledger.evaluation`.

## Dataset files

| File | Role |
|------|------|
| `data/scenarios.jsonl` | `scenario_id`, `tool_calls`, `answer`, optional `domain` / `session_id` |
| `data/ground_truth.jsonl` | Per-claim gold: `scenario_id`, `claim_id`, `claim_text`, `gold_verdict` |

One JSON object per line (`load_jsonl`).

## Runner

`run_evaluation(ledger, scenarios_path, ground_truth_path, results_dir="results")`:

1. For each scenario referenced by ground truth, create session `eval-{scenario_id}-{run_prefix}`.
2. Replay `tool_calls` through `ToolAdapter`.
3. Run `HybridVerifier` on the scenario `answer`.
4. Compare hybrid verdicts to gold (match by claim text or id).
5. Also score **Baseline A** (answer-only / no trace) and **Baseline B** (full trace → inner judge, default deterministic).
6. Write `results/<run_id>.json` and return a dict including `metrics`.

Metrics helpers: `precision_recall_f1`, `false_positive_rate` (`metrics.py`).

## Baselines

| Class | Behavior |
|-------|----------|
| `BaselineAJudge` | Ignores entries; empty → `UNSUPPORTED`, else `PARTIALLY_SUPPORTED` |
| `BaselineBJudge` | Delegates to inner `LLMJudge` (default `DeterministicJudge`) |

## CLI

```bash
ledger evaluate --dataset data/scenarios.jsonl
ledger evaluate report --run <run_id>
```

Do **not** treat external benchmark percentages from the SRS literature survey as predicted scores for this prototype; report your own numbers with dataset size and limitations (see SRS § evaluation discipline).
