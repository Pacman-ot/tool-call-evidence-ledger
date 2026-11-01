"""Runtime configuration. Secrets come from environment variables only."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _load_dotenv() -> None:
    """Best-effort .env load without requiring python-dotenv at import time."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


@dataclass
class Settings:
    ledger_storage_backend: str = "sqlite"  # sqlite | jsonl
    ledger_db_path: str = "./data/ledger.db"
    schema_version: int = 1
    openai_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_judge_enabled: bool = False
    numeric_tolerance: float = 1e-6
    genesis_marker: str = "GENESIS_V1"

    def resolved_db_path(self) -> Path:
        """Prefer LEDGER_DB_PATH; on Vercel default to /tmp when unset explicitly."""
        path = Path(self.ledger_db_path)
        if os.environ.get("VERCEL") == "1" and self.ledger_db_path == "./data/ledger.db":
            path = Path("/tmp/ledger.db")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


def get_settings() -> Settings:
    _load_dotenv()
    return Settings(
        ledger_storage_backend=os.environ.get("LEDGER_STORAGE_BACKEND", "sqlite"),
        ledger_db_path=os.environ.get("LEDGER_DB_PATH", "./data/ledger.db"),
        schema_version=int(os.environ.get("SCHEMA_VERSION", "1")),
        openai_api_key=os.environ.get("OPENAI_API_KEY") or None,
        llm_model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
        llm_judge_enabled=_env_bool("LLM_JUDGE_ENABLED", False),
        numeric_tolerance=float(os.environ.get("NUMERIC_TOLERANCE", "1e-6")),
        genesis_marker=os.environ.get("GENESIS_MARKER", "GENESIS_V1"),
    )
