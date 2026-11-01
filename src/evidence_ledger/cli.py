"""CLI contracts from the developer guide."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from evidence_ledger.claims.verifier import HybridVerifier
from evidence_ledger.evaluation.runner import run_evaluation
from evidence_ledger.ledger import EvidenceLedger
from evidence_ledger.tools.adapter import ToolAdapter

app = typer.Typer(add_completion=False, no_args_is_help=True)
ledger_app = typer.Typer(help="Ledger operations")
verify_app = typer.Typer(help="Answer verification")
evaluate_app = typer.Typer(help="Evaluation experiments")
app.add_typer(ledger_app, name="ledger")
app.add_typer(verify_app, name="verify")
app.add_typer(evaluate_app, name="evaluate")


def _ledger() -> EvidenceLedger:
    return EvidenceLedger()


@ledger_app.command("init")
def ledger_init() -> None:
    """Create or migrate the local SQLite database."""
    lg = _ledger()
    lg.init()
    typer.echo(f"Initialized storage at {lg.settings.resolved_db_path()}")


@ledger_app.command("run")
def ledger_run(
    scenario: str = typer.Option(..., "--scenario", help="Scenario ID from data/scenarios.jsonl"),
    scenarios_path: Path = typer.Option(Path("data/scenarios.jsonl"), "--scenarios"),
) -> None:
    """Execute a scenario and capture tool calls."""
    from evidence_ledger.evaluation.dataset import load_jsonl

    rows = {r["scenario_id"]: r for r in load_jsonl(scenarios_path)}
    if scenario not in rows:
        raise typer.BadParameter(f"unknown scenario: {scenario}")
    sc = rows[scenario]
    lg = _ledger()
    lg.init()
    session_id = lg.create_session(sc.get("session_id") or f"scenario-{scenario}")
    adapter = ToolAdapter(lg)
    for call in sc.get("tool_calls") or []:
        result = adapter.invoke(session_id, call["tool"], call.get("args") or {})
        typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    typer.echo(f"session_id={session_id}")


@ledger_app.command("inspect")
def ledger_inspect(session: str = typer.Option(..., "--session")) -> None:
    lg = _ledger()
    entries = lg.list_entries(session)
    if not entries:
        typer.echo("[]")
        return
    typer.echo(json.dumps([e.model_dump(mode="json") for e in entries], indent=2))


@ledger_app.command("verify")
def ledger_verify(session: str = typer.Option(..., "--session")) -> None:
    lg = _ledger()
    result = lg.verify(session)
    typer.echo(result.model_dump_json(indent=2))


@verify_app.command("answer")
def verify_answer(
    session: str = typer.Option(..., "--session"),
    input_path: Path = typer.Option(..., "--input", help="Path to answer text file"),
) -> None:
    answer = input_path.read_text(encoding="utf-8")
    lg = _ledger()
    report = HybridVerifier(lg).verify(session, answer)
    typer.echo(report.model_dump_json(indent=2))


@evaluate_app.callback(invoke_without_command=True)
def evaluate_root(
    ctx: typer.Context,
    dataset: Optional[Path] = typer.Option(None, "--dataset"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    if dataset is None:
        dataset = Path("data/scenarios.jsonl")
    lg = _ledger()
    lg.init()
    result = run_evaluation(lg, dataset, Path("data/ground_truth.jsonl"))
    typer.echo(json.dumps(result["metrics"], indent=2))


@evaluate_app.command("report")
def evaluate_report(run: str = typer.Option(..., "--run")) -> None:
    path = Path("results") / f"{run}.json"
    if not path.exists():
        raise typer.Exit(code=1)
    typer.echo(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    app()
