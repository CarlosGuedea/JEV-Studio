import { BaseEdge, EdgeLabelRenderer, getBezierPath, type Edge, type EdgeProps } from "@xyflow/react";
import { cn } from "@/lib/utils";

export interface BranchEdgeData extends Record<string, unknown> {
  options: string[];
  value: string;
  onChange: (edgeId: string, label: string) => void;
}

export type BranchEdgeType = Edge<BranchEdgeData>;

/**
 * Edge with an inline branch selector (Node-RED style): one output handle per
 * node; the routing label is picked from the dropdown rendered on the edge.
 */
export function BranchEdge({
  id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
  markerEnd, data, selected,
}: EdgeProps<BranchEdgeType>) {
  const [path, labelX, labelY] = getBezierPath({
    sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition,
  });
  const { options, value, onChange } = (data ?? { options: [], value: "", onChange: () => {} }) as BranchEdgeData;

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        style={selected ? { strokeWidth: 2.5 } : undefined}
      />
      <EdgeLabelRenderer>
        <select
          value={value}
          onChange={(e) => onChange(id, e.target.value)}
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
          title="Rama que activa esta conexión"
          className={cn(
            "nodrag nopan nowheel absolute z-10 -translate-x-1/2 -translate-y-1/2",
            "h-5 cursor-pointer rounded-full border px-1 text-[10px] font-semibold outline-none",
            "border-violet-400/40 bg-background text-violet-600 shadow-sm dark:text-violet-400"
          )}
          style={{ left: labelX, top: labelY }}
        >
          {options.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      </EdgeLabelRenderer>
    </>
  );
}
