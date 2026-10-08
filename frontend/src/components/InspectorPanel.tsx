import { useEditorStore } from "@/stores/editorStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import type { NodeType, StepStatus } from "@/types/workflow";
import { NODE_LABELS } from "@/types/workflow";
import { Copy, Trash2 } from "lucide-react";

const STATUS_LABELS: Record<StepStatus, string> = {
  IDLE: "Sin ejecutar",
  QUEUED: "En cola",
  RUNNING: "Ejecutando",
  SUCCESS: "Correcto",
  ERROR: "Error",
  SKIPPED: "Omitido",
};

function JsonView({ value }: { value: unknown }) {
  if (value === undefined || value === null) return <span className="text-muted-foreground">—</span>;
  return (
    <pre className="max-h-48 overflow-auto rounded-md bg-muted p-2 font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-all">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function ExecutionSummary() {
  const nodes = useEditorStore((s) => s.nodes);
  const statuses = useEditorStore((s) => s.nodeStatuses);
  const results = useEditorStore((s) => s.nodeResults);
  const executed = nodes.filter((node) => statuses[node.id] && statuses[node.id] !== "IDLE");
  const successful = executed.filter((node) => statuses[node.id] === "SUCCESS");
  const failed = executed.filter((node) => statuses[node.id] === "ERROR");
  const finalOutput = nodes.find((node) => node.type === "output" && statuses[node.id] === "SUCCESS");

  if (executed.length === 0) return null;

  return (
    <section className="space-y-2 border-b border-border px-4 py-3" aria-label="Última ejecución">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs font-semibold">Última ejecución</h3>
        <span className={failed.length ? "text-[11px] font-medium text-red-500" : "text-[11px] font-medium text-emerald-600 dark:text-emerald-400"}>
          {failed.length ? "Con errores" : "Correcta"}
        </span>
      </div>
      <p className="text-[11px] text-muted-foreground">
        {successful.length} correcto{successful.length === 1 ? "" : "s"} · {executed.filter((node) => statuses[node.id] === "SKIPPED").length} omitido{executed.filter((node) => statuses[node.id] === "SKIPPED").length === 1 ? "" : "s"}
      </p>
      <div className="flex flex-wrap gap-1" aria-label="Estado de los nodos">
        {executed.map((node) => (
          <span
            key={node.id}
            className={
              statuses[node.id] === "SUCCESS"
                ? "rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-400"
                : statuses[node.id] === "ERROR"
                  ? "rounded bg-red-500/10 px-1.5 py-0.5 text-[10px] font-medium text-red-700 dark:text-red-400"
                  : "rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground"
            }
          >
            {String(node.data.label)} · {STATUS_LABELS[statuses[node.id]]}
          </span>
        ))}
      </div>
      {finalOutput && results[finalOutput.id] && (
        <div className="space-y-1">
          <span className="text-[11px] font-medium text-muted-foreground">Resultado final</span>
          <JsonView value={results[finalOutput.id].output} />
        </div>
      )}
    </section>
  );
}

export function InspectorPanel({ selected }: { selected: { id: string; type: string; label: string; config: Record<string, unknown> } | null }) {
  const updateNodeConfig = useEditorStore((s) => s.updateNodeConfig);
  const updateNodeLabel = useEditorStore((s) => s.updateNodeLabel);
  const duplicateNode = useEditorStore((s) => s.duplicateNode);
  const setNodes = useEditorStore((s) => s.setNodes);
  const result = useEditorStore((s) => (selected ? s.nodeResults[selected.id] : undefined));
  const status = useEditorStore((s) => (selected ? s.nodeStatuses[selected.id] ?? "IDLE" : "IDLE"));

  const set = (key: string, value: unknown) => {
    if (!selected) return;
    updateNodeConfig(selected.id, { ...selected.config, [key]: value });
  };

  return (
    <aside className="flex min-h-[360px] w-full shrink-0 flex-col border-t border-border bg-background lg:min-h-0 lg:w-80 lg:border-t-0 lg:border-l">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Inspector</h2>
      </div>
      <ExecutionSummary />
      <div className="flex-1 overflow-y-auto p-4">
        {!selected ? (
          <p className="text-xs text-muted-foreground">
            Selecciona un nodo del canvas para configurarlo. Las flechas que salen de un Jev Decision o Condition llevan un selector para elegir la rama.
          </p>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="rounded bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                {NODE_LABELS[selected.type as NodeType] ?? selected.type}
              </span>
              <div className="flex gap-1">
                <Button variant="ghost" size="icon" className="h-7 w-7" title="Duplicar nodo" onClick={() => duplicateNode(selected.id)}>
                  <Copy className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-destructive"
                  title="Eliminar nodo"
                  onClick={() =>
                    setNodes((ns) => {
                      useEditorStore.setState((s) => ({ edges: s.edges.filter((e) => e.source !== selected.id && e.target !== selected.id) }));
                      return ns.filter((n) => n.id !== selected.id);
                    })
                  }
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs">Nombre</Label>
              <Input value={selected.label} onChange={(e) => updateNodeLabel(selected.id, e.target.value)} className="h-8 text-xs" />
            </div>

            <NodeFields type={selected.type as NodeType} config={selected.config} onChange={set} />

            {result && (
              <>
                <Separator />
                <details className="space-y-2" open={status === "ERROR"}>
                  <div className="flex items-center justify-between">
                    <summary className="cursor-pointer text-xs font-semibold">Detalles del nodo</summary>
                    <span
                      className={
                        status === "SUCCESS"
                          ? "text-[11px] font-medium text-emerald-600"
                          : status === "ERROR"
                            ? "text-[11px] font-medium text-red-500"
                            : "text-[11px] text-muted-foreground"
                      }
                    >
                      {STATUS_LABELS[status]}
                      {result.durationMs != null && ` · ${result.durationMs} ms`}
                    </span>
                  </div>
                  {result.error && <div className="rounded-md bg-red-500/10 p-2 text-[11px] text-red-600 dark:text-red-400">{result.error}</div>}
                  <div className="space-y-1">
                    <span className="text-[11px] font-medium text-muted-foreground">Input</span>
                    <JsonView value={result.input} />
                  </div>
                  <div className="space-y-1">
                    <span className="text-[11px] font-medium text-muted-foreground">Output</span>
                    <JsonView value={result.output} />
                  </div>
                </details>
              </>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}

function NodeFields({ type, config, onChange }: { type: NodeType; config: Record<string, unknown>; onChange: (k: string, v: unknown) => void }) {
  const str = (k: string) => String(config[k] ?? "");
  const num = (k: string) => Number(config[k] ?? 0);

  switch (type) {
    case "automation":
      return (
        <>
          <Field label="Estado">
            <select value={config.active === false ? "paused" : "active"} onChange={(e) => onChange("active", e.target.value === "active")} className="h-8 w-full rounded-md border bg-background px-2 text-xs">
              <option value="active">Activa: acepta webhook y horarios</option>
              <option value="paused">Pausada: detiene todos los disparadores</option>
            </select>
          </Field>
          <Field label="Intervalo (segundos)">
            <Input
              type="number"
              min="60"
              max="604800"
              value={config.interval_seconds == null ? "" : String(config.interval_seconds)}
              onChange={(e) => onChange("interval_seconds", e.target.value === "" ? null : Number(e.target.value))}
              placeholder="Sin intervalo"
              className="h-8 text-xs"
            />
          </Field>
          <Field label="Calendario cron (UTC)">
            <Input value={str("cron")} onChange={(e) => onChange("cron", e.target.value)} placeholder="0 9 * * 1-5" className="h-8 font-mono text-xs" />
          </Field>
          <p className="text-[11px] leading-snug text-muted-foreground">
            El webhook queda disponible al guardar el workflow. Cron tiene prioridad sobre el intervalo; deja ambos vacíos para usar solo webhook.
          </p>
        </>
      );
    case "input":
      return (
        <div className="space-y-1.5">
          <Label className="text-xs">Mensaje</Label>
          <Textarea value={str("message")} onChange={(e) => onChange("message", e.target.value)} className="text-xs" rows={2} />
        </div>
      );
    case "jev_decision":
      return (
        <>
          <Field label="Instrucciones / contexto">
            <Textarea value={str("instructions")} onChange={(e) => onChange("instructions", e.target.value)} className="text-xs" rows={3}
              placeholder="Contexto que Jev usa para decidir" />
          </Field>
          <Field label="Pregunta">
            <Input value={str("question")} onChange={(e) => onChange("question", e.target.value)} className="h-8 text-xs" />
          </Field>
          <Field label="Opciones (una por línea)">
            <Textarea
              value={((config.options as string[]) ?? []).join("\n")}
              onChange={(e) => onChange("options", e.target.value.split("\n").map((s) => s.trim()).filter(Boolean))}
              className="text-xs font-mono"
              rows={5}
            />
          </Field>
          <Field label="Proveedor">
            <select value={str("provider") || "auto"} onChange={(e) => onChange("provider", e.target.value)} className="h-8 w-full rounded-md border bg-background px-2 text-xs">
              <option value="auto">auto (real si hay API key, si no mock)</option>
              <option value="typesafe">typesafe (API real)</option>
              <option value="mock">mock (simulación)</option>
            </select>
          </Field>
        </>
      );
    case "llm":
      return (
        <>
          <Field label="Proveedor">
            <Input value={str("provider")} onChange={(e) => onChange("provider", e.target.value)} className="h-8 text-xs" placeholder="openai / local / llamacpp" />
          </Field>
          <Field label="Endpoint (vacío = por defecto)">
            <Input value={str("endpoint")} onChange={(e) => onChange("endpoint", e.target.value)} className="h-8 text-xs" placeholder="http://localhost:8080/v1" />
          </Field>
          <Field label="Modelo">
            <Input value={str("model")} onChange={(e) => onChange("model", e.target.value)} className="h-8 text-xs" />
          </Field>
          <Field label="Variable de entorno de la API key">
            <Input value={str("api_key_env")} onChange={(e) => onChange("api_key_env", e.target.value)} className="h-8 text-xs font-mono" />
          </Field>
          <Field label="System prompt">
            <Textarea value={str("system_prompt")} onChange={(e) => onChange("system_prompt", e.target.value)} className="text-xs" rows={2} />
          </Field>
          <Field label="Prompt (admite {{input}}, {{nodes.id}})">
            <Textarea value={str("prompt")} onChange={(e) => onChange("prompt", e.target.value)} className="text-xs" rows={3} />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Temperature">
              <Input type="number" step="0.1" min="0" max="2" value={num("temperature")} onChange={(e) => onChange("temperature", Number(e.target.value))} className="h-8 text-xs" />
            </Field>
            <Field label="Max tokens">
              <Input type="number" value={num("max_tokens")} onChange={(e) => onChange("max_tokens", Number(e.target.value))} className="h-8 text-xs" />
            </Field>
          </div>
        </>
      );
    case "python":
      return (
        <>
          <Field label="Expresión (lista blanca, sin imports)">
            <Textarea value={str("expression")} onChange={(e) => onChange("expression", e.target.value)} className="font-mono text-xs" rows={3} />
          </Field>
          <p className="text-[11px] leading-snug text-muted-foreground">
            Disponibles: <code>data</code> (entrada), <code>input</code>, funciones como <code>len</code>, <code>split</code>, <code>get</code>, <code>sum</code>…
          </p>
        </>
      );
    case "http_request":
      return (
        <>
          <Field label="URL">
            <Input value={str("url")} onChange={(e) => onChange("url", e.target.value)} className="h-8 text-xs" />
          </Field>
          <Field label="Método">
            <select value={str("method") || "GET"} onChange={(e) => onChange("method", e.target.value)} className="h-8 w-full rounded-md border bg-background px-2 text-xs">
              {["GET", "POST", "PUT", "PATCH", "DELETE"].map((m) => (<option key={m}>{m}</option>))}
            </select>
          </Field>
          <Field label="Headers (JSON)">
            <Textarea
              value={JSON.stringify(config.headers ?? {}, null, 2)}
              onChange={(e) => { try { onChange("headers", JSON.parse(e.target.value || "{}")); } catch { /* keep editing */ } }}
              className="font-mono text-xs"
              rows={3}
            />
          </Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Timeout (s)">
              <Input type="number" value={num("timeout_seconds")} onChange={(e) => onChange("timeout_seconds", Number(e.target.value))} className="h-8 text-xs" />
            </Field>
          </div>
        </>
      );
    case "condition":
      return (
        <Field label="Expresión (p. ej. confidence > 0.8)">
          <Input value={str("expression")} onChange={(e) => onChange("expression", e.target.value)} className="h-8 font-mono text-xs" />
        </Field>
      );
    case "output":
      return (
        <Field label="Etiqueta">
          <Input value={str("label")} onChange={(e) => onChange("label", e.target.value)} className="h-8 text-xs" />
        </Field>
      );
  }
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{label}</Label>
      {children}
    </div>
  );
}
