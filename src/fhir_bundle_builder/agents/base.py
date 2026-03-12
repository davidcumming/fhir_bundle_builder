from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class AgentDefinition:
    role_id: str
    name: str
    instructions: str
    model_provider: str
    model_name: str
    temperature: float
    memory_namespace: str
    context_roots: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    primary_artifact: str = ""
    narrate_progress: bool = False
    expose_delegation_trace: bool = False
