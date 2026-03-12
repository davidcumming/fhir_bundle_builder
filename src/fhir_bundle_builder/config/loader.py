from __future__ import annotations

from pathlib import Path

import yaml

from .agent_config import AgentConfig


def load_agent_config(path: str | Path) -> AgentConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    return AgentConfig(**data)
