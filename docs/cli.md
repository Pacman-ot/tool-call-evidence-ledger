# CLI reference

Install the `[cli]` extra (or `[dev]`). Console script: **`ledger`** → `evidence_ledger.cli:app`.

```text
ledger
├── ledger      # ledger operations group
│   ├── init
│   ├── run
│   ├── inspect
│   └── verify
├── verify      # answer verification group
│   └── answer
└── evaluate    # evaluation group
    └── report
```

## Ledger operations

```bash
ledger ledger init
```

Initialize storage schema; prints resolved DB path.

```bash
ledger ledger run --scenario S-001
ledger ledger run --scenario S-001 --scenarios data/scenarios.jsonl
```

Loads the scenario from JSONL, creates session `scenario-{id}` (or scenario’s `session_id`), invokes each `tool_calls` item via `ToolAdapter` (default toy tools), prints invoke JSON and `session_id=...`.

```bash
ledger ledger inspect --session <SESSION_ID>
```

Prints all entries as JSON (or `[]`).

```bash
ledger ledger verify --session <SESSION_ID>
```

Prints `ChainVerifyResult` JSON (hash-chain integrity only).

## Answer verification

```bash
ledger verify answer --session <SESSION_ID> --input path/to/answer.txt
```

Runs `HybridVerifier` on the file contents; prints `AnswerVerificationReport` JSON.

## Evaluation

```bash
ledger evaluate --dataset data/scenarios.jsonl
```

Runs `run_evaluation(ledger, dataset, data/ground_truth.jsonl)` and prints the **metrics** object.

```bash
ledger evaluate report --run <run_id>
```

Prints `results/<run_id>.json` if that file exists; exits `1` otherwise.

## Configuration

Same environment variables as the library ([storage.md](storage.md)). Working directory should be the repo root so default `data/` paths resolve.
