from __future__ import annotations

from pathlib import Path

from fhir_bundle_builder.agents import build_agent_definition


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> None:
    config_dir = _repo_root() / "config" / "agents"

    for config_path in sorted(config_dir.glob("*.yaml")):
        agent_definition = build_agent_definition(config_path)
        print(
            f"{agent_definition.role_id}: "
            f"{agent_definition.model_provider} / "
            f"{agent_definition.model_name} / "
            f"{agent_definition.primary_artifact} "
            f"instructions={len(agent_definition.instructions)} chars"
        )


if __name__ == "__main__":
    main()
