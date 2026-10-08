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
import { FolderOpen, FilePlus2, Copy, Trash2 } from "lucide-react";
import type { WorkflowSummary } from "@/types/workflow";

export function WorkflowManager() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<WorkflowSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setItems(await api.listWorkflows());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  const openWorkflow = async (id: number) => {
    try {
      const wf = await api.getWorkflow(id);
      useEditorStore.getState().loadDefinition(wf.definition, wf.id);
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
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

  return (
    <>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm" className="gap-1.5">
            <FolderOpen className="h-3.5 w-3.5" /> Abrir
          </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-sm">Workflows guardados</DialogTitle>
          </DialogHeader>
          {error && <p className="rounded-md bg-red-500/10 p-2 text-xs text-red-600 dark:text-red-400">{error}</p>}
          <div className="max-h-80 space-y-1.5 overflow-y-auto">
            {items.length === 0 && !error && (
              <p className="py-6 text-center text-xs text-muted-foreground">
                No hay workflows guardados todavía. Guarda el actual para verlo aquí.
              </p>
            )}
            {items.map((w) => (
              <div key={w.id} className="flex items-center gap-2 rounded-lg border border-border p-2.5">
                <button className="min-w-0 flex-1 text-left" onClick={() => openWorkflow(w.id)}>
                  <div className="truncate text-xs font-medium">{w.name}</div>
                  <div className="truncate text-[11px] text-muted-foreground">
                    {w.node_count} nodos · {new Date(w.updated_at).toLocaleString()}
                  </div>
                </button>
                <Button variant="ghost" size="icon" className="h-7 w-7" title="Duplicar" onClick={() => duplicate(w.id)}>
                  <Copy className="h-3.5 w-3.5" />
                </Button>
                <Button variant="ghost" size="icon" className="h-7 w-7 text-destructive" title="Eliminar" onClick={() => remove(w.id)}>
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      <Button
        variant="outline"
        size="sm"
        className="gap-1.5"
        onClick={() => {
          useEditorStore.getState().newWorkflow();
        }}
      >
        <FilePlus2 className="h-3.5 w-3.5" /> Nuevo
      </Button>
    </>
  );
}
