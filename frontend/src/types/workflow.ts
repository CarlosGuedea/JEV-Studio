// Workflow JSON model — mirrors backend/app/schemas/workflow.py

export type NodeType =
  | "automation"
  | "input"
  | "jev_decision"
  | "llm"
  | "python"
  | "http_request"
  | "condition"
  | "output";

export type StepStatus =
  | "IDLE"
  | "QUEUED"
  | "RUNNING"
  | "SUCCESS"
  | "ERROR"
  | "SKIPPED";

export interface Position {
  x: number;
  y: number;
}

export interface WorkflowNode {
  id: string;
  type: NodeType;
  label: string;
  position: Position;
  config: Record<string, unknown>;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  label?: string | null;
}

export interface WorkflowDefinition {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  config: { name: string; description?: string };
  variables: Record<string, unknown>;
}

export interface WorkflowSummary {
  id: number;
  name: string;
  description: string;
  node_count: number;
  updated_at: string;
  active: boolean;
  webhook_token: string;
  schedule_interval_seconds: number | null;
  schedule_cron: string | null;
}

export interface WorkflowResponse {
  id: number;
  name: string;
  description: string;
  definition: WorkflowDefinition;
  created_at: string;
  updated_at: string;
  active: boolean;
  webhook_token: string;
  schedule_interval_seconds: number | null;
  schedule_cron: string | null;
  last_scheduled_at: string | null;
}

export interface ExecutionStepResult {
  node_id: string;
  node_type: string;
  label: string;
  status: StepStatus;
  input: unknown;
  output: unknown;
  error: string | null;
  started_at: string | null;
  ended_at: string | null;
  duration_ms: number | null;
}

export interface ExecutionResponse {
  id: number;
  workflow_id: number;
  status: StepStatus;
  error: string | null;
  input: unknown;
  output: unknown;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  trigger: "manual" | "webhook" | "schedule";
  steps: ExecutionStepResult[];
}

export interface ProvidersInfo {
  jev: string;
  jev_mock: boolean;
  llm_providers: string[];
}

// ── Default configs per node type ─────────────────────────────────────

export const DEFAULT_CONFIGS: Record<NodeType, Record<string, unknown>> = {
  automation: { active: true, interval_seconds: null, cron: "" },
  input: { message: "Escribe tu solicitud…" },
  jev_decision: {
    name: "Jev Decision",
    instructions: "",
    question: "¿Qué ruta debe seguir esta solicitud?",
    options: ["SQL", "PYTHON", "LLM", "RAG", "REJECT"],
    model: null,
    provider: "auto",
  },
  llm: {
    provider: "openai",
    endpoint: "",
    model: "gpt-4o-mini",
    api_key_env: "OPENAI_API_KEY",
    system_prompt: "",
    prompt: "{{input}}",
    temperature: 0.7,
    max_tokens: 1024,
  },
  python: { expression: "data", description: "" },
  http_request: {
    url: "https://jsonplaceholder.typicode.com/posts/1",
    method: "GET",
    headers: {},
    body: null,
    timeout_seconds: 30,
  },
  condition: { expression: "confidence > 0.8" },
  output: { label: "Output" },
};

export const NODE_LABELS: Record<NodeType, string> = {
  automation: "Automatización",
  input: "Input",
  jev_decision: "Jev Decision",
  llm: "LLM",
  python: "Python",
  http_request: "HTTP Request",
  condition: "Condition",
  output: "Output",
};
