from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    provider: str
    model_name: str
    temperature: float = 0.2


class MemoryConfig(BaseModel):
    type: str
    namespace: str


class ContextConfig(BaseModel):
    roots: List[str] = Field(default_factory=list)


class ToolsConfig(BaseModel):
    allowed: List[str] = Field(default_factory=list)


class OutputConfig(BaseModel):
    primary_artifact: str


class BehaviorConfig(BaseModel):
    narrate_progress: bool = False
    expose_delegation_trace: bool = False


class AgentConfig(BaseModel):
    role_id: str
    name: str
    profile_markdown: str
    model: ModelConfig
    memory: MemoryConfig
    context: ContextConfig
    tools: ToolsConfig
    output: OutputConfig
    behavior: BehaviorConfig