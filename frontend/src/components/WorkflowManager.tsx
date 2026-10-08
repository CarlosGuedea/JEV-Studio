import { useCallback, useEffect, useState } from "react";
import { useEditorStore } from "@/stores/editorStore";
import { api } from "@/services/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { FolderOpen, FilePlus2, Copy, Trash2, History, Plus } from "lucide-react";
import type { ExecutionResponse, WorkflowSummary } from "@/types/workflow";

export function WorkflowManager() {
  // The library is the product's entry point; the editor is opened only after
  // selecting a workflow or starting a new one.
  const [open, setOpen] = useState(true);
  const [items, setItems] = useState<WorkflowSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [historyId, setHistoryId] = useState<number | null>(null);
  const [history, setHistory] = useState<ExecutionResponse[]>([]);

  const refresh = useCallback(async () => {
    try {
      setItems(await api.listWorkflows());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    api.listWorkflows()
      .then((workflows) => {
        setItems(workflows);
        setError(null);
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)));
  }, [open]);

  const openWorkflow = async (id: number) => {
    try {
      const wf = await api.getWorkflow(id);
      useEditorStore.getState().loadDefinition(wf.definition, wf.id);
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const createNew = () => {
    useEditorStore.getState().newWorkflow();
    setHistoryId(null);
    setOpen(false);
  };

  const duplicate = async (id: number) => {
    await api.duplicateWorkflow(id);
    refresh();
  };

  const remove = async (id: number) => {
    await api.deleteWorkflow(id);
    if (useEditorStore.getState().workflowId === id) useEditorStore.getState().newWorkflow();
    refresh();
  };

  const showHistory = async (id: number) => {
    if (historyId === id) {
      setHistoryId(null);
      return;
    }
    setHistoryId(id);
    try {
      setHistory(await api.listExecutions(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
      }}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm" className="gap-1.5">
            <FolderOpen className="h-3.5 w-3.5" /> Abrir
          </Button>
        </DialogTrigger>
        <DialogContent className="max-h-[calc(100vh-2rem)] overflow-hidden p-5 sm:max-w-4xl sm:p-8">
          <DialogHeader className="pr-10">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <DialogTitle className="text-2xl font-bold tracking-tight">Workflows guardados</DialogTitle>
              <Button size="sm" className="gap-1.5" onClick={createNew}>
                <Plus className="h-4 w-4" /> Nuevo workflow
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">Abre, consulta o administra tus flujos de automatización.</p>
          </DialogHeader>
          {error && <p className="rounded-md bg-red-500/10 p-2 text-xs text-red-600 dark:text-red-400">{error}</p>}
          <div className="max-h-[65vh] space-y-3 overflow-y-auto pr-1">
            {items.length === 0 && !error && (
              <div className="rounded-xl border border-dashed p-10 text-center">
                <p className="text-sm font-medium">Aún no hay workflows guardados.</p>
                <p className="mt-1 text-xs text-muted-foreground">Crea un workflow para empezar a automatizar.</p>
                <Button size="sm" className="mt-4 gap-1.5" onClick={createNew}><Plus className="h-3.5 w-3.5" /> Crear workflow</Button>
              </div>
            )}
            {items.map((w) => (
              <div key={w.id} className="rounded-2xl border border-border bg-card p-4 shadow-sm transition-colors hover:border-foreground/25">
                <div className="flex items-center gap-2 sm:gap-4">
                  <button className="min-w-0 flex-1 text-left" onClick={() => openWorkflow(w.id)} aria-label={`Abrir ${w.name}`}>
                    <div className="flex items-center gap-1.5">
                      <span className={w.active ? "h-2.5 w-2.5 shrink-0 rounded-full bg-emerald-500" : "h-2.5 w-2.5 shrink-0 rounded-full bg-muted-foreground"} />
                      <span className="truncate text-base font-semibold">{w.name}</span>
                    </div>
                    <div className="mt-1 truncate text-sm text-muted-foreground">
                      {w.node_count} nodos · {w.active ? "activo" : "pausado"} · {new Date(w.updated_at).toLocaleString()}
                    </div>
                  </button>
                  <Button variant="ghost" size="icon" className="h-10 w-10 shrink-0" title="Historial de ejecuciones" aria-label={`Historial de ${w.name}`} onClick={() => showHistory(w.id)}>
                    <History className="h-5 w-5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-10 w-10 shrink-0" title="Duplicar" aria-label={`Duplicar ${w.name}`} onClick={() => duplicate(w.id)}>
                    <Copy className="h-5 w-5" />
                  </Button>
                  <Button variant="ghost" size="icon" className="h-10 w-10 shrink-0 text-destructive" title="Eliminar" aria-label={`Eliminar ${w.name}`} onClick={() => remove(w.id)}>
                    <Trash2 className="h-5 w-5" />
                  </Button>
                </div>
                {historyId === w.id && (
                  <div className="mt-3 space-y-3 border-t border-border pt-3">
                    <div className="space-y-1">
                      <p className="flex items-center gap-1 text-[11px] font-medium text-muted-foreground"><History className="h-3.5 w-3.5" /> Ejecuciones recientes</p>
                      {history.length === 0 ? (
                        <p className="text-[11px] text-muted-foreground">Todavía no hay ejecuciones.</p>
                      ) : history.slice(0, 5).map((execution) => (
                        <div key={execution.id} className="flex items-center justify-between rounded bg-muted px-2 py-1 text-[11px]">
                          <span>{execution.trigger} · #{execution.id}</span>
                          <span className={execution.status === "SUCCESS" ? "text-emerald-600 dark:text-emerald-400" : execution.status === "ERROR" ? "text-red-500" : "text-amber-600 dark:text-amber-400"}>{execution.status}</span>
                        </div>
                      ))}
                    </div>
                    <p className="text-[11px] text-muted-foreground">La automatización se configura desde el nodo Automatización dentro del canvas.</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      <Button
        variant="outline"
        size="sm"
        className="gap-1.5"
        onClick={createNew}
      >
        <FilePlus2 className="h-3.5 w-3.5" /> Nuevo
      </Button>
    </>
  );
}
