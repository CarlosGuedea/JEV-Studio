import { create } from "zustand";
import type { Edge, Node } from "@xyflow/react";
import {
  DEFAULT_CONFIGS,
  NODE_LABELS,
  type ExecutionResponse,
  type NodeType,
  type StepStatus,
  type WorkflowDefinition,
} from "@/types/workflow";

let idCounter = 1;
export function nextId(prefix: string): string {
  return `${prefix}_${Date.now().toString(36)}_${idCounter++}`;
}

export function toFlowNode(type: NodeType, position: { x: number; y: number }, id?: string): Node {
  return {
    id: id ?? nextId(type),
    type,
    position,
    data: { label: NODE_LABELS[type], config: structuredClone(DEFAULT_CONFIGS[type]) },
  };
}

function definitionFrom(nodes: Node[], edges: Edge[], name: string, description: string): WorkflowDefinition {
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      type: n.type as NodeType,
      label: (n.data.label as string) ?? "",
      position: { x: n.position.x, y: n.position.y },
      config: (n.data.config as Record<string, unknown>) ?? {},
    })),
    edges: edges.map((e) => ({ id: e.id, source: e.source, target: e.target, label: (e.label as string | null) ?? null })),
    config: { name, description },
    variables: {},
  };
}

interface EditorState {
  nodes: Node[];
  edges: Edge[];
  workflowId: number | null;
  workflowName: string;
  workflowDescription: string;
  dirty: boolean;
  running: boolean;
  runError: string | null;
  nodeStatuses: Record<string, StepStatus>;
  nodeResults: Record<string, { input: unknown; output: unknown; error: string | null; durationMs: number | null; status: StepStatus }>;
  activeEdgeIds: string[];

  setNodes: (nodes: Node[] | ((ns: Node[]) => Node[])) => void;
  setEdges: (edges: Edge[] | ((es: Edge[]) => Edge[])) => void;
  addNode: (node: Node) => void;
  duplicateNode: (id: string) => void;
  updateNodeConfig: (id: string, config: Record<string, unknown>) => void;
  updateNodeLabel: (id: string, label: string) => void;

  loadDefinition: (def: WorkflowDefinition, id: number | null) => void;
  setMeta: (name: string, description: string) => void;
  markSaved: (id: number) => void;
  newWorkflow: () => void;

  setRunning: (v: boolean) => void;
  setRunError: (v: string | null) => void;
  applyExecution: (ex: ExecutionResponse) => void;
  clearExecution: () => void;
  toDefinition: () => WorkflowDefinition;
}

export const useEditorStore = create<EditorState>((set, get) => ({
  nodes: [],
  edges: [],
  workflowId: null,
  workflowName: "Untitled workflow",
  workflowDescription: "",
  dirty: false,
  running: false,
  runError: null,
  nodeStatuses: {},
  nodeResults: {},
  activeEdgeIds: [],

  setNodes: (nodes) =>
    set((s) => ({
      nodes: typeof nodes === "function" ? nodes(s.nodes) : nodes,
      dirty: true,
    })),
  setEdges: (edges) =>
    set((s) => ({
      edges: typeof edges === "function" ? edges(s.edges) : edges,
      dirty: true,
    })),
  addNode: (node) => set((s) => ({ nodes: [...s.nodes, node], dirty: true })),

  duplicateNode: (id) =>
    set((s) => {
      const src = s.nodes.find((n) => n.id === id);
      if (!src) return s;
      const copy: Node = {
        ...structuredClone(src),
        id: nextId(src.type as string),
        position: { x: src.position.x + 40, y: src.position.y + 40 },
        selected: false,
        data: { ...src.data, label: `${src.data.label} (copia)` },
      };
      return { nodes: [...s.nodes, copy], dirty: true };
    }),

  updateNodeConfig: (id, config) =>
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, config } } : n)),
      dirty: true,
    })),
  updateNodeLabel: (id, label) =>
    set((s) => ({
      nodes: s.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, label } } : n)),
      dirty: true,
    })),

  loadDefinition: (def, id) =>
    set({
      workflowId: id,
      workflowName: def.config.name,
      workflowDescription: def.config.description ?? "",
      nodes: def.nodes.map((n) => ({
        id: n.id,
        type: n.type,
        position: n.position,
        data: { label: n.label, config: n.config },
      })),
      edges: def.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label ?? undefined,
      })),
      dirty: false,
      nodeStatuses: {},
      nodeResults: {},
      activeEdgeIds: [],
      runError: null,
    }),

  setMeta: (name, description) => set({ workflowName: name, workflowDescription: description, dirty: true }),
  markSaved: (id) => set({ workflowId: id, dirty: false }),

  newWorkflow: () =>
    set({
      workflowId: null,
      workflowName: "Untitled workflow",
      workflowDescription: "",
      nodes: [],
      edges: [],
      dirty: false,
      nodeStatuses: {},
      nodeResults: {},
      activeEdgeIds: [],
      runError: null,
    }),

  setRunning: (v) => set({ running: v }),
  setRunError: (v) => set({ runError: v }),

  applyExecution: (ex) =>
    set((s) => {
      const nodeStatuses: Record<string, StepStatus> = {};
      const nodeResults: EditorState["nodeResults"] = {};
      const activeEdgeIds: string[] = [];
      for (const step of ex.steps) {
        nodeStatuses[step.node_id] = step.status;
        nodeResults[step.node_id] = {
          input: step.input,
          output: step.output,
          error: step.error,
          durationMs: step.duration_ms,
          status: step.status,
        };
      }
      // an edge was "active" if its source succeeded and its target was not skipped
      for (const e of s.edges) {
        const src = nodeStatuses[e.source];
        const tgt = nodeStatuses[e.target];
        if (src === "SUCCESS" && tgt && tgt !== "SKIPPED") activeEdgeIds.push(e.id);
      }
      return { nodeStatuses, nodeResults, activeEdgeIds, running: false, runError: ex.error };
    }),

  clearExecution: () =>
    set({ nodeStatuses: {}, nodeResults: {}, activeEdgeIds: [], runError: null }),

  toDefinition: () => {
    const s = get();
    return definitionFrom(s.nodes, s.edges, s.workflowName, s.workflowDescription);
  },
}));
