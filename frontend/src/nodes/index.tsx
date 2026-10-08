import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";
import { memo, type ReactNode } from "react";
import type { StepStatus } from "@/types/workflow";
import { useEditorStore } from "@/stores/editorStore";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<StepStatus, string> = {
  IDLE: "",
  QUEUED: "ring-2 ring-blue-400",
  RUNNING: "ring-2 ring-amber-400 animate-pulse",
  SUCCESS: "ring-2 ring-emerald-500",
  ERROR: "ring-2 ring-red-500",
  SKIPPED: "opacity-45 border-dashed",
};

interface ShellProps {
  id: string;
  icon: ReactNode;
  title: string;
  subtitle?: string;
  badge?: string;
  badgeTone?: "amber" | "violet" | "sky" | "rose" | "emerald" | "slate";
  connectable?: boolean;
  children?: ReactNode;
}

export function NodeShell({ id, icon, title, subtitle, badge, badgeTone = "slate", connectable = true, children }: ShellProps) {
  const status = useEditorStore((s) => s.nodeStatuses[id]) ?? "IDLE";

  return (
    <div
      className={cn(
        "w-64 rounded-xl border bg-card text-card-foreground shadow-md transition-shadow dark:bg-zinc-900",
        status === "IDLE" && "border-border",
        STATUS_STYLES[status]
      )}
    >
      {connectable && <Handle
        id="in"
        type="target"
        position={Position.Left}
        className="!h-2.5 !w-2.5 !border-2 !border-background !bg-muted-foreground"
      />}

      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-muted">{icon}</span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold leading-tight">{title}</div>
          {subtitle && <div className="truncate text-[11px] text-muted-foreground">{subtitle}</div>}
        </div>
        {badge && (
          <span
            className={cn(
              "rounded-full px-1.5 py-0.5 text-[10px] font-medium",
              badgeTone === "amber" && "bg-amber-500/15 text-amber-600 dark:text-amber-400",
              badgeTone === "violet" && "bg-violet-500/15 text-violet-600 dark:text-violet-400",
              badgeTone === "sky" && "bg-sky-500/15 text-sky-600 dark:text-sky-400",
              badgeTone === "rose" && "bg-rose-500/15 text-rose-600 dark:text-rose-400",
              badgeTone === "emerald" && "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
              badgeTone === "slate" && "bg-muted text-muted-foreground"
            )}
          >
            {badge}
          </span>
        )}
      </div>

      {children && <div className="px-3 py-2 text-xs text-muted-foreground">{children}</div>}

      {connectable && <Handle
        id="out"
        type="source"
        position={Position.Right}
        className="!h-2.5 !w-2.5 !border-2 !border-background !bg-muted-foreground"
      />}
    </div>
  );
}

type FlowNode = Node<{ label: string; config: Record<string, unknown> }>;

function cfg(props: NodeProps<FlowNode>) {
  return props.data.config;
}

// ── Individual node types ─────────────────────────────────────────────

import { LogIn, Brain, Sparkles, Code2, Globe, GitFork, LogOut, CalendarClock } from "lucide-react";

export const AutomationNode = memo(function AutomationNode(props: NodeProps<FlowNode>) {
  const c = cfg(props);
  const active = c.active !== false;
  const cron = String(c.cron ?? "").trim();
  const interval = Number(c.interval_seconds ?? 0);
  const schedule = cron ? `Cron UTC · ${cron}` : interval ? `Cada ${interval} s` : "Webhook";
  return (
    <NodeShell
      id={props.id}
      icon={<CalendarClock className="h-4 w-4 text-violet-500" />}
      title={props.data.label}
      subtitle={schedule}
      badge={active ? "Activa" : "Pausada"}
      badgeTone={active ? "violet" : "slate"}
      connectable={false}
    >
      <div>{active ? "Webhook habilitado" : "Los disparadores están pausados"}</div>
    </NodeShell>
  );
});

export const InputNode = memo(function InputNode(props: NodeProps<FlowNode>) {
  const c = cfg(props);
  return (
    <NodeShell id={props.id} icon={<LogIn className="h-4 w-4 text-sky-500" />} title={props.data.label} subtitle="Entrada del usuario">
      <div className="line-clamp-2">{String(c.message ?? "")}</div>
    </NodeShell>
  );
});

export const JevNode = memo(function JevNode(props: NodeProps<FlowNode>) {
  const c = cfg(props);
  const options = (c.options as string[]) ?? [];
  return (
    <NodeShell
      id={props.id}
      icon={<Brain className="h-4 w-4 text-violet-500" />}
      title={props.data.label}
      subtitle={String(c.question ?? "")}
      badge="Jev"
      badgeTone="violet"
    >
      <div className="flex flex-wrap gap-1">
        {options.map((o) => (
          <span key={o} className="rounded bg-violet-500/10 px-1.5 py-0.5 text-[10px] font-medium text-violet-600 dark:text-violet-400">
            {o}
          </span>
        ))}
      </div>
    </NodeShell>
  );
});

export const LLMNode = memo(function LLMNode(props: NodeProps<FlowNode>) {
  const c = cfg(props);
  return (
    <NodeShell id={props.id} icon={<Sparkles className="h-4 w-4 text-amber-500" />} title={props.data.label} subtitle={String(c.model ?? "")} badge="LLM" badgeTone="amber">
      <div className="line-clamp-2">{String(c.prompt ?? "")}</div>
    </NodeShell>
  );
});

export const PythonNode = memo(function PythonNode(props: NodeProps<FlowNode>) {
  const c = cfg(props);
  return (
    <NodeShell id={props.id} icon={<Code2 className="h-4 w-4 text-emerald-500" />} title={props.data.label} badge="Py" badgeTone="emerald">
      <code className="block truncate rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">{String(c.expression ?? "")}</code>
    </NodeShell>
  );
});

export const HttpNode = memo(function HttpNode(props: NodeProps<FlowNode>) {
  const c = cfg(props);
  return (
    <NodeShell id={props.id} icon={<Globe className="h-4 w-4 text-sky-500" />} title={props.data.label} badge={String(c.method ?? "GET")} badgeTone="sky">
      <div className="truncate">{String(c.url ?? "")}</div>
    </NodeShell>
  );
});

export const ConditionNode = memo(function ConditionNode(props: NodeProps<FlowNode>) {
  const c = cfg(props);
  return (
    <NodeShell
      id={props.id}
      icon={<GitFork className="h-4 w-4 text-rose-500" />}
      title={props.data.label}
    >
      <code className="block truncate rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">{String(c.expression ?? "")}</code>
      <div className="mt-1 flex gap-2 text-[10px] font-medium">
        <span className="text-emerald-600 dark:text-emerald-400">true</span>
        <span className="text-rose-500">false</span>
      </div>
    </NodeShell>
  );
});

export const OutputNode = memo(function OutputNode(props: NodeProps<FlowNode>) {
  return (
    <NodeShell id={props.id} icon={<LogOut className="h-4 w-4 text-emerald-500" />} title={props.data.label} subtitle="Salida final">
      <div />
    </NodeShell>
  );
});

// React Flow consumes this component map; it is intentionally exported beside its nodes.
// eslint-disable-next-line react-refresh/only-export-components
export const NODE_COMPONENTS = {
  automation: AutomationNode,
  input: InputNode,
  jev_decision: JevNode,
  llm: LLMNode,
  python: PythonNode,
  http_request: HttpNode,
  condition: ConditionNode,
  output: OutputNode,
};
