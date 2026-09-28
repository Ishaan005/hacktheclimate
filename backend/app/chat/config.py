from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPO_ROOT / ".env"


def _load_env_file(path: Path = ENV_FILE) -> None:
    """Load KEY=VALUE lines from the git-ignored .env without overriding real env vars."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class ChatSettings:
    endpoint: str | None
    api_key: str | None
    deployment: str
    api_version: str

    @property
    def configured(self) -> bool:
        return bool(self.endpoint and self.api_key)

    @property
    def is_reasoning_model(self) -> bool:
        # gpt-5.x deployments reject temperature and need a newer API version.
        return self.deployment.startswith(("gpt-5", "o1", "o3", "o4"))


def get_settings() -> ChatSettings:
    _load_env_file()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
    default_version = "2025-04-01-preview" if deployment.startswith("gpt-5") else "2024-10-21"
    return ChatSettings(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        deployment=deployment,
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", default_version),
    )
