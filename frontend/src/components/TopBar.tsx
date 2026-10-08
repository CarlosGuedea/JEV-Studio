import { useState } from "react";
import { useEditorStore } from "@/stores/editorStore";
import { api } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Play, Save, Moon, Sun, Brain } from "lucide-react";
import type { ProvidersInfo } from "@/types/workflow";

export function RunDialog({ providers }: { providers: ProvidersInfo | null }) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const workflowName = useEditorStore((s) => s.workflowName);

  const run = async () => {
    setOpen(false);
    const s = useEditorStore.getState();
    s.setRunning(true);
    s.setRunError(null);
    s.clearExecution();
    try {
      let id = s.workflowId;
      if (id == null || s.dirty) {
        // auto-save before running
        const def = s.toDefinition();
        if (id == null) {
          const created = await api.createWorkflow(def);
          id = created.id;
        } else {
          await api.updateWorkflow(id, def);
        }
        s.markSaved(id);
      }
      const ex = await api.execute(id, input || null, {});
      useEditorStore.getState().applyExecution(ex);
    } catch (err) {
      useEditorStore.getState().setRunning(false);
      useEditorStore.getState().setRunError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1.5">
          <Play className="h-3.5 w-3.5" /> Ejecutar
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-sm">Ejecutar “{workflowName}”</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label className="text-xs">Entrada del usuario</Label>
            <Textarea value={input} onChange={(e) => setInput(e.target.value)} rows={4} className="text-xs" placeholder="Escribe la solicitud que entrará por el nodo Input…" autoFocus />
          </div>
          {providers?.jev_mock && (
            <p className="rounded-md bg-amber-500/10 p-2 text-[11px] text-amber-600 dark:text-amber-400">
              Proveedor Jev en modo simulación (mock). Configura TYPESAFE_API_KEY para decisiones reales.
            </p>
          )}
          <Button className="w-full" onClick={run}>Ejecutar workflow</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function TopBar({ providers, dark, onToggleDark }: { providers: ProvidersInfo | null; dark: boolean; onToggleDark: () => void }) {
  const workflowName = useEditorStore((s) => s.workflowName);
  const workflowDescription = useEditorStore((s) => s.workflowDescription);
  const dirty = useEditorStore((s) => s.dirty);
  const workflowId = useEditorStore((s) => s.workflowId);
  const running = useEditorStore((s) => s.running);
  const setMeta = useEditorStore((s) => s.setMeta);

  const save = async () => {
    const s = useEditorStore.getState();
    const def = s.toDefinition();
    try {
      if (s.workflowId == null) {
        const created = await api.createWorkflow(def);
        s.markSaved(created.id);
      } else {
        await api.updateWorkflow(s.workflowId, def);
        s.markSaved(s.workflowId);
      }
    } catch (err) {
      useEditorStore.getState().setRunError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <header className="flex min-h-14 flex-wrap items-center gap-x-2 gap-y-2 border-b border-border bg-background px-3 py-2 sm:h-14 sm:flex-nowrap sm:px-4 sm:py-0">
      <div className="flex shrink-0 items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/15">
          <Brain className="h-4.5 w-4.5 text-violet-500" />
        </span>
        <span className="text-sm font-bold tracking-tight">Jev Studio</span>
      </div>

      <div className="order-3 flex w-full min-w-0 items-center gap-2 sm:order-none sm:w-auto sm:flex-1">
        <Input
          value={workflowName}
          onChange={(e) => setMeta(e.target.value, workflowDescription)}
          className="h-8 min-w-0 flex-1 text-xs font-medium sm:max-w-xs"
          placeholder="Nombre del workflow"
        />
        <Input
          value={workflowDescription}
          onChange={(e) => setMeta(workflowName, e.target.value)}
          className="hidden h-8 flex-1 text-xs text-muted-foreground sm:block"
          placeholder="Descripción"
        />
        <span className="shrink-0 text-[11px] text-muted-foreground">
          {workflowId != null ? `#${workflowId}` : "sin guardar"}
          {dirty && " ·"}
        </span>
        {dirty && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400" title="Cambios sin guardar" />}
      </div>

      {providers && (
        <span
          className={
            providers.jev_mock
              ? "hidden shrink-0 rounded-full bg-amber-500/15 px-2 py-0.5 text-[11px] font-medium text-amber-600 lg:inline dark:text-amber-400"
              : "hidden shrink-0 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] font-medium text-emerald-600 lg:inline dark:text-emerald-400"
          }
          title={providers.jev_mock ? "Jev simulado (mock)" : "Jev conectado a TypeSafe API"}
        >
          Jev: {providers.jev === "typesafe" ? "TypeSafe" : "MOCK"}
        </span>
      )}

      <div className="flex shrink-0 items-center gap-1.5">
        <Button variant="outline" size="sm" onClick={save} disabled={running} className="gap-1.5" aria-label="Guardar workflow">
          <Save className="h-3.5 w-3.5" /> <span className="hidden sm:inline">Guardar</span>
        </Button>
        <RunDialog providers={providers} />
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onToggleDark} title={dark ? "Modo claro" : "Modo oscuro"}>
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>
    </header>
  );
}
