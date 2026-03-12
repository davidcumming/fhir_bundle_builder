from __future__ import annotations

import os
from pathlib import Path

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

from fhir_bundle_builder.agents.base import AgentDefinition

PLACEHOLDER_OPENAI_API_KEY = "placeholder"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_openai_api_key() -> str:
    env_api_key = os.getenv("OPENAI_API_KEY")
    if env_api_key:
        return env_api_key
    return PLACEHOLDER_OPENAI_API_KEY


def _resolve_env_file_path() -> str | None:
    env_path = _repo_root() / ".env"
    if env_path.exists():
        return str(env_path)
    return None


def build_framework_agent(agent_definition: AgentDefinition) -> Agent:
    if agent_definition.model_provider != "openai":
        raise NotImplementedError(f"Unsupported model provider: {agent_definition.model_provider}")

    client = OpenAIChatClient(
        model_id=agent_definition.model_name,
        api_key=_resolve_openai_api_key(),
        env_file_path=_resolve_env_file_path(),
    )

    return Agent(
        client=client,
        instructions=agent_definition.instructions,
        name=agent_definition.name,
        description=agent_definition.primary_artifact,
        default_options={
            "temperature": agent_definition.temperature,
        },
    )
