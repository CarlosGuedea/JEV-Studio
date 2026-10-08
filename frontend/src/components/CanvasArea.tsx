import { useCallback, useEffect, useRef } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Panel,
  addEdge,
  useReactFlow,
  ReactFlowProvider,
  type Connection,
  type Edge,
  type EdgeTypes,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEditorStore, toFlowNode, nextId } from "@/stores/editorStore";
import { NODE_COMPONENTS } from "@/nodes";
import { BranchEdge } from "@/nodes/BranchEdge";
import type { NodeType } from "@/types/workflow";

const nodeTypes: NodeTypes = NODE_COMPONENTS;
const edgeTypes: EdgeTypes = { branch: BranchEdge };

function FitViewOnLoad() {
  const { fitView } = useReactFlow();
  const count = useEditorStore((s) => s.nodes.length);
  const prev = useRef(0);
  useEffect(() => {
    if (count > 0 && prev.current === 0) {
      setTimeout(() => fitView({ padding: 0.25, duration: 300 }), 60);
    }
    prev.current = count;
  }, [count, fitView]);
  return null;
}

function CanvasInner() {
  const nodes = useEditorStore((s) => s.nodes);
  const edges = useEditorStore((s) => s.edges);
  const setNodes = useEditorStore((s) => s.setNodes);
  const setEdges = useEditorStore((s) => s.setEdges);
  const activeEdgeIds = useEditorStore((s) => s.activeEdgeIds);
  const running = useEditorStore((s) => s.running);
  const { screenToFlowPosition } = useReactFlow();
  const wrapper = useRef<HTMLDivElement>(null);

  const nodeById = useCallback((id: string) => nodes.find((n) => n.id === id), [nodes]);

  /** Branch options for edges leaving a jev_decision / condition node. */
  const branchOptionsOf = useCallback(
    (sourceId: string): string[] | null => {
      const src = nodeById(sourceId);
      if (!src) return null;
      if (src.type === "jev_decision") return ((src.data.config as Record<string, unknown>).options as string[]) ?? [];
      if (src.type === "condition") return ["true", "false"];
      return null;
    },
    [nodeById]
  );

  const onConnect = useCallback(
    (conn: Connection) => {
      const options = branchOptionsOf(conn.source);
      const label = options?.[0];
      setEdges((eds) => addEdge({ ...conn, id: nextId("e"), label }, eds));
    },
    [branchOptionsOf, setEdges]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const type = e.dataTransfer.getData("application/jev-node") as NodeType;
      if (!type) return;
      const position = screenToFlowPosition({ x: e.clientX, y: e.clientY });
      useEditorStore.getState().addNode(toFlowNode(type, position));
    },
    [screenToFlowPosition]
  );

  const setEdgeLabel = useCallback(
    (edgeId: string, label: string) => {
      setEdges((es) => es.map((e) => (e.id === edgeId ? { ...e, label } : e)));
    },
    [setEdges]
  );

  const styledEdges: Edge[] = edges.map((e) => {
    const active = activeEdgeIds.includes(e.id);
    const options = branchOptionsOf(e.source);
    const base: Edge = {
      ...e,
      animated: running || active,
      style: active ? { stroke: "#10b981", strokeWidth: 2 } : e.style,
    };
    if (options) {
      // branch edge: label chosen from the inline selector on the edge
      const value = String(e.label ?? options[0] ?? "");
      return {
        ...base,
        type: "branch",
        label: undefined,
        data: { options, value, onChange: setEdgeLabel },
      };
    }
    return {
      ...base,
      labelStyle: { fontSize: 10, fontWeight: 600 },
      labelBgStyle: { fill: "var(--muted, #71717a)", fillOpacity: 0.08 },
    };
  });

  return (
    <div ref={wrapper} className="min-w-[540px] flex-1" onDrop={onDrop} onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; }}>
      <ReactFlow
        nodes={nodes}
        edges={styledEdges}
        nodeTypes={nodeTypes}
        onNodesChange={(changes) => {
          setNodes((ns) => {
            let out = [...ns];
            for (const c of changes) {
              if (c.type === "position" && c.position) {
                out = out.map((n) => (n.id === c.id ? { ...n, position: c.position! } : n));
              } else if (c.type === "select") {
                out = out.map((n) => (n.id === c.id ? { ...n, selected: c.selected } : n));
              } else if (c.type === "remove") {
                out = out.filter((n) => n.id !== c.id);
              }
            }
            return out;
          });
          const removedNodes = changes.filter((c) => c.type === "remove").map((c) => (c as { id: string }).id);
          if (removedNodes.length) {
            setEdges((es) => es.filter((e) => !removedNodes.includes(e.source) && !removedNodes.includes(e.target)));
          }
        }}
        onEdgesChange={(changes) => {
          setEdges((es) => {
            let out = [...es];
            for (const c of changes) {
              if (c.type === "remove") out = out.filter((e) => e.id !== c.id);
              else if (c.type === "select") out = out.map((e) => (e.id === c.id ? { ...e, selected: c.selected } : e));
            }
            return out;
          });
        }}
        onConnect={onConnect}
        edgeTypes={edgeTypes}
        deleteKeyCode={["Backspace", "Delete"]}
        fitView
        minZoom={0.2}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <FitViewOnLoad />
        <Background variant={BackgroundVariant.Dots} gap={20} size={1.5} />
        <Controls position="bottom-left" />
        <MiniMap position="bottom-right" pannable zoomable className="!h-32 !w-44" />
        <Panel position="top-left">
          <div className="rounded-md border border-border bg-background/80 px-2 py-1 text-[11px] text-muted-foreground backdrop-blur">
            {running ? "Ejecutando workflow…" : "Arrastra desde el punto derecho de un nodo para conectar · elige la rama en el selector de la flecha"}
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}

export function CanvasArea() {
  return (
    <ReactFlowProvider>
      <CanvasInner />
    </ReactFlowProvider>
  );
}
