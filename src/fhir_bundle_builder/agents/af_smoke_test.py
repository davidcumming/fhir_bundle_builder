from __future__ import annotations

from pathlib import Path

from fhir_bundle_builder.agents import build_agent_definition, build_framework_agent


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> None:
    config_path = _repo_root() / "config" / "agents" / "coordinator.yaml"
    agent_definition = build_agent_definition(config_path)
    framework_agent = build_framework_agent(agent_definition)
    framework_type = f"{type(framework_agent).__module__}.{type(framework_agent).__name__}"

    print(f"role_id={agent_definition.role_id}")
    print(f"framework_type={framework_type}")
    print("adapter=ok")


if __name__ == "__main__":
    main()
