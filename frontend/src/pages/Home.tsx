import { useEffect, useState } from "react";
import { useEditorStore } from "@/stores/editorStore";
import { api } from "@/services/api";
import { TopBar } from "@/components/TopBar";
import { WorkflowManager } from "@/components/WorkflowManager";
import { NodeSidebar } from "@/components/NodeSidebar";
import { CanvasArea } from "@/components/CanvasArea";
import { InspectorPanel } from "@/components/InspectorPanel";
import type { ProvidersInfo } from "@/types/workflow";

export default function Home() {
  const [providers, setProviders] = useState<ProvidersInfo | null>(null);
  const [dark, setDark] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches);
  const selectedNode = useEditorStore((s) => s.nodes.find((n) => n.selected));
  const runError = useEditorStore((s) => s.runError);

  useEffect(() => {
    api.providers().then(setProviders).catch(() => setProviders(null));
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  // Load the demo workflow on first paint so the canvas is never empty.
  useEffect(() => {
    (async () => {
      const s = useEditorStore.getState();
      if (s.nodes.length > 0) return;
      try {
        const items = await api.listWorkflows();
        if (items.length > 0) {
          const wf = await api.getWorkflow(items[0].id);
          s.loadDefinition(wf.definition, wf.id);
        }
      } catch {
        /* backend offline — canvas stays empty */
      }
    })();
  }, []);

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      <div className="flex items-center gap-2 border-b border-border bg-background px-4 py-1.5">
        <WorkflowManager />
        <span className="text-[11px] text-muted-foreground">
          Arrastra nodos desde la izquierda · conecta desde el punto derecho de un nodo · elige la rama en el selector de la flecha
        </span>
      </div>
      <TopBar providers={providers} dark={dark} onToggleDark={() => setDark((d) => !d)} />
      {runError && (
        <div className="border-b border-red-500/30 bg-red-500/10 px-4 py-1.5 text-xs text-red-600 dark:text-red-400">
          {runError}
        </div>
      )}
      <div className="flex flex-1 overflow-x-auto overflow-y-hidden">
        <NodeSidebar />
        <CanvasArea />
        <InspectorPanel
          selected={
            selectedNode
              ? {
                  id: selectedNode.id,
                  type: selectedNode.type as string,
                  label: (selectedNode.data.label as string) ?? "",
                  config: (selectedNode.data.config as Record<string, unknown>) ?? {},
                }
              : null
          }
        />
      </div>
    </div>
  );
}
