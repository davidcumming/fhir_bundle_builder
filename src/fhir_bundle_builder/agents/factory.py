from __future__ import annotations

from pathlib import Path
from typing import Union

from fhir_bundle_builder.agents.base import AgentDefinition
from fhir_bundle_builder.config import load_agent_config


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def read_profile_markdown(config_path: Union[str, Path], profile_markdown: str) -> str:
    config_file = Path(config_path).resolve()
    candidate_paths = [
        config_file.parent / profile_markdown,
        _repo_root() / profile_markdown,
    ]

    for candidate_path in candidate_paths:
        if candidate_path.exists():
            return candidate_path.read_text(encoding="utf-8")

    raise FileNotFoundError(f"Profile markdown not found for {config_file}: {profile_markdown}")


def build_agent_definition(config_path: Union[str, Path]) -> AgentDefinition:
    config_file = Path(config_path).resolve()
    config = load_agent_config(config_file)
    instructions = read_profile_markdown(config_file, config.profile_markdown)

    return AgentDefinition(
        role_id=config.role_id,
        name=config.name,
        instructions=instructions,
        model_provider=config.model.provider,
        model_name=config.model.model_name,
        temperature=config.model.temperature,
        memory_namespace=config.memory.namespace,
        context_roots=list(config.context.roots),
        allowed_tools=list(config.tools.allowed),
        primary_artifact=config.output.primary_artifact,
        narrate_progress=config.behavior.narrate_progress,
        expose_delegation_trace=config.behavior.expose_delegation_trace,
    )
