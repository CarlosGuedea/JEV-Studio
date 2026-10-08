import { LogIn, Brain, Sparkles, Code2, Globe, GitFork, LogOut } from "lucide-react";
import type { NodeType } from "@/types/workflow";
import { NODE_LABELS } from "@/types/workflow";
import { cn } from "@/lib/utils";
import { toFlowNode, useEditorStore } from "@/stores/editorStore";

const PALETTE: { type: NodeType; icon: React.ReactNode; description: string; tone: string }[] = [
  { type: "input", icon: <LogIn className="h-4 w-4 text-sky-500" />, description: "Entrada inicial del usuario", tone: "hover:border-sky-400" },
  { type: "jev_decision", icon: <Brain className="h-4 w-4 text-violet-500" />, description: "Decisión con Jev", tone: "hover:border-violet-400" },
  { type: "llm", icon: <Sparkles className="h-4 w-4 text-amber-500" />, description: "Llamada a modelo de lenguaje", tone: "hover:border-amber-400" },
  { type: "python", icon: <Code2 className="h-4 w-4 text-emerald-500" />, description: "Operación Python segura", tone: "hover:border-emerald-400" },
  { type: "http_request", icon: <Globe className="h-4 w-4 text-sky-500" />, description: "Llamada a API REST", tone: "hover:border-sky-400" },
  { type: "condition", icon: <GitFork className="h-4 w-4 text-rose-500" />, description: "Condición sobre resultados", tone: "hover:border-rose-400" },
  { type: "output", icon: <LogOut className="h-4 w-4 text-emerald-500" />, description: "Salida final del workflow", tone: "hover:border-emerald-400" },
];

export function NodeSidebar() {
  const addWithKeyboard = (type: NodeType, index: number) => {
    useEditorStore.getState().addNode(toFlowNode(type, { x: 80 + index * 28, y: 80 + index * 28 }));
  };

  return (
    <aside className="flex w-full shrink-0 flex-col border-b border-border bg-background lg:w-60 lg:border-r lg:border-b-0">
      <div className="border-b border-border px-4 py-2.5 lg:py-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Nodos</h2>
        <p className="mt-0.5 text-[11px] text-muted-foreground">Arrastra al canvas o usa Intro</p>
      </div>
      <div className="flex gap-2 overflow-x-auto p-3 lg:flex-1 lg:flex-col lg:overflow-y-auto">
        {PALETTE.map((item, index) => (
          <div
            key={item.type}
            draggable
            role="button"
            tabIndex={0}
            aria-label={`${NODE_LABELS[item.type]}. Arrastra al canvas o pulsa Intro para añadirlo.`}
            onDragStart={(e) => {
              e.dataTransfer.setData("application/jev-node", item.type);
              e.dataTransfer.effectAllowed = "move";
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                addWithKeyboard(item.type, index);
              }
            }}
            className={cn(
              "min-w-48 cursor-grab rounded-lg border border-border bg-card p-2.5 shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:cursor-grabbing lg:min-w-0",
              item.tone
            )}
          >
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-muted">{item.icon}</span>
              <span className="text-xs font-medium">{NODE_LABELS[item.type]}</span>
            </div>
            <p className="mt-1.5 text-[11px] leading-snug text-muted-foreground">{item.description}</p>
          </div>
        ))}
      </div>
    </aside>
  );
}
