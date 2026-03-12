from __future__ import annotations

from pathlib import Path

from fhir_bundle_builder.config.loader import load_agent_config


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def main() -> None:
    config_dir = _repo_root() / "config" / "agents"

    for config_path in sorted(config_dir.glob("*.yaml")):
        config = load_agent_config(config_path)
        print(f"{config.role_id}: {config.model.provider} / {config.model.model_name}")


if __name__ == "__main__":
    main()
