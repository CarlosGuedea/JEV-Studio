import type {
  ExecutionResponse,
  ProvidersInfo,
  WorkflowDefinition,
  WorkflowResponse,
  WorkflowSummary,
} from "@/types/workflow";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export const api = {
  providers: () => request<ProvidersInfo>("/api/providers"),

  listWorkflows: () => request<WorkflowSummary[]>("/api/workflows"),
  getWorkflow: (id: number) => request<WorkflowResponse>(`/api/workflows/${id}`),
  createWorkflow: (definition: WorkflowDefinition) =>
    request<{ id: number }>("/api/workflows", {
      method: "POST",
      body: JSON.stringify({ definition }),
    }),
  updateWorkflow: (id: number, definition: WorkflowDefinition) =>
    request<{ id: number }>(`/api/workflows/${id}`, {
      method: "PUT",
      body: JSON.stringify({ definition }),
    }),
  deleteWorkflow: (id: number) =>
    request<void>(`/api/workflows/${id}`, { method: "DELETE" }),
  duplicateWorkflow: (id: number) =>
    request<{ id: number }>(`/api/workflows/${id}/duplicate`, { method: "POST" }),

  execute: (id: number, input: unknown, variables: Record<string, unknown>) =>
    request<ExecutionResponse>(`/api/workflows/${id}/execute`, {
      method: "POST",
      body: JSON.stringify({ input, variables }),
    }),
  getExecution: (id: number) =>
    request<ExecutionResponse>(`/api/executions/${id}`),
};
