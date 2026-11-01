"""Runtime configuration. Secrets come from environment variables only."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

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
        # Vercel serverless: only /tmp is writable and ephemeral.
        if os.environ.get("VERCEL") == "1" and self.ledger_db_path == "./data/ledger.db":
            path = Path("/tmp/ledger.db")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


def get_settings() -> Settings:
    return Settings()
