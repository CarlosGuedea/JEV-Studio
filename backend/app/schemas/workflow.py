"""Pydantic schemas: the workflow JSON model shared with the frontend.

The frontend sends WorkflowDefinition {nodes, edges, config, variables};
every entry point is validated here before it reaches the engine.
"""
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class NodeType(str, Enum):
    AUTOMATION = "automation"
    INPUT = "input"
    JEV_DECISION = "jev_decision"
    LLM = "llm"
    PYTHON = "python"
    HTTP_REQUEST = "http_request"
    CONDITION = "condition"
    OUTPUT = "output"


class StepStatus(str, Enum):
    IDLE = "IDLE"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class Position(BaseModel):
    x: float = 0
    y: float = 0


# ── Per-node configuration ────────────────────────────────────────────


class InputConfig(BaseModel):
    message: str = "Escribe tu solicitud…"


class AutomationConfig(BaseModel):
    """Metadata-only node that configures workflow-level triggers."""
    active: bool = True
    interval_seconds: int | None = Field(default=None, ge=60, le=604_800)
    cron: str = ""

    @field_validator("cron")
    @classmethod
    def validate_cron(cls, value: str) -> str:
        if not value.strip():
            return ""
        from ..services.cron import validate_cron_expression

        return validate_cron_expression(value)


class JevDecisionConfig(BaseModel):
    name: str = "Jev Decision"
    instructions: str = ""
    question: str = "¿Qué ruta debe seguir esta solicitud?"
    options: list[str] = Field(default_factory=lambda: ["SQL", "PYTHON", "LLM", "RAG", "REJECT"])
    model: str | None = None  # None → server default (jev-latest)
    # provider: "auto" (real if API key configured, else mock), "mock", "typesafe"
    provider: Literal["auto", "mock", "typesafe"] = "auto"


class LLMConfig(BaseModel):
    provider: str = "openai"  # provider key; see providers/llm
    endpoint: str = ""  # empty → provider default endpoint
    model: str = "gpt-4o-mini"
    api_key_env: str = "OPENAI_API_KEY"  # NAME of env var; the secret never lives here
    system_prompt: str = ""
    prompt: str = "{{input}}"
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1024, ge=1, le=128_000)


class PythonConfig(BaseModel):
    # NOT arbitrary code: a restricted expression evaluated by a whitelisted AST
    # interpreter. `data` holds the incoming value.
    expression: str = "data"
    description: str = ""


class HttpRequestConfig(BaseModel):
    url: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    headers: dict[str, str] = Field(default_factory=dict)
    body: Any = None
    timeout_seconds: float = Field(default=30.0, gt=0, le=120)


class ConditionConfig(BaseModel):
    expression: str = "confidence > 0.8"


class OutputConfig(BaseModel):
    label: str = "Output"


NodeConfig = (
    AutomationConfig | InputConfig | JevDecisionConfig | LLMConfig | PythonConfig
    | HttpRequestConfig | ConditionConfig | OutputConfig
)


# ── Graph model ───────────────────────────────────────────────────────


class WorkflowNode(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    type: NodeType
    label: str = ""
    position: Position = Field(default_factory=Position)
    config: dict[str, Any] = Field(default_factory=dict)

    def parsed_config(self) -> NodeConfig:
        cls = {
            NodeType.AUTOMATION: AutomationConfig,
            NodeType.INPUT: InputConfig,
            NodeType.JEV_DECISION: JevDecisionConfig,
            NodeType.LLM: LLMConfig,
            NodeType.PYTHON: PythonConfig,
            NodeType.HTTP_REQUEST: HttpRequestConfig,
            NodeType.CONDITION: ConditionConfig,
            NodeType.OUTPUT: OutputConfig,
        }[self.type]
        return cls.model_validate(self.config)


class WorkflowEdge(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    source: str
    target: str
    # For branch nodes (jev_decision / condition) the label selects the branch:
    # an option name ("SQL", "PYTHON", …) or "true"/"false".
    label: str | None = None


class WorkflowConfig(BaseModel):
    name: str = "Untitled workflow"
    description: str = ""


class WorkflowDefinition(BaseModel):
    """The JSON the frontend sends to run/save a workflow."""
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    config: WorkflowConfig = Field(default_factory=WorkflowConfig)
    variables: dict[str, Any] = Field(default_factory=dict)


# ── API payloads ──────────────────────────────────────────────────────


class WorkflowCreate(BaseModel):
    definition: WorkflowDefinition


class WorkflowUpdate(BaseModel):
    definition: WorkflowDefinition


class WorkflowSummary(BaseModel):
    id: int
    name: str
    description: str
    node_count: int
    updated_at: str
    active: bool = True
    webhook_token: str = ""
    schedule_interval_seconds: int | None = None
    schedule_cron: str | None = None

    model_config = {"from_attributes": True}


class WorkflowResponse(BaseModel):
    id: int
    name: str
    description: str
    definition: WorkflowDefinition
    created_at: str
    updated_at: str
    active: bool = True
    webhook_token: str = ""
    schedule_interval_seconds: int | None = None
    schedule_cron: str | None = None
    last_scheduled_at: str | None = None


class WorkflowRuntimeUpdate(BaseModel):
    active: bool | None = None
    schedule_interval_seconds: int | None = Field(default=None, ge=60, le=604_800)
    schedule_cron: str | None = Field(default=None, max_length=128)

    @field_validator("schedule_cron")
    @classmethod
    def validate_cron(cls, value: str | None) -> str | None:
        if value is None:
            return value
        from ..services.cron import validate_cron_expression

        return validate_cron_expression(value)


class ExecuteRequest(BaseModel):
    input: Any = None
    variables: dict[str, Any] = Field(default_factory=dict)

    @field_validator("input")
    @classmethod
    def limit_input_size(cls, v: Any) -> Any:
        import json
        if len(json.dumps(v, default=str)) > 256_000:
            raise ValueError("input exceeds 256 KB")
        return v


class ExecutionStepResult(BaseModel):
    node_id: str
    node_type: str
    label: str
    status: StepStatus
    input: Any = None
    output: Any = None
    error: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    duration_ms: float | None = None


class ExecutionResponse(BaseModel):
    id: int
    workflow_id: int
    status: StepStatus
    error: str | None = None
    input: Any = None
    output: Any = None
    started_at: str
    ended_at: str | None = None
    duration_ms: float | None = None
    trigger: str = "manual"
    steps: list[ExecutionStepResult]


class ProvidersInfo(BaseModel):
    jev: str  # "typesafe" | "mock"
    jev_mock: bool
    llm_providers: list[str]
