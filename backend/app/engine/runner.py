"""Workflow execution engine.

Runs a WorkflowDefinition:
  1. validate the graph                    (validation.validate_graph)
  2. find the Input node
  3. walk the graph propagating activation (branches select outgoing edges)
  4. execute each reachable node in dependency order
  5. pass predecessor outputs to each node; record every step
  6. stop infinite loops (max step guard) and report errors

The engine is node-type agnostic: executors come from nodes/registry().
"""
import time
from datetime import datetime, timezone
from typing import Any

from ..config import get_settings
from ..nodes import ExecutionContext, registry
from ..schemas import NodeType, StepStatus, WorkflowDefinition, WorkflowNode


class StepRecord:
    def __init__(self, node: WorkflowNode) -> None:
        self.node_id = node.id
        self.node_type = node.type.value
        self.label = node.label or node.id
        self.status = StepStatus.IDLE
        self.input: Any = None
        self.output: Any = None
        self.error: str | None = None
        self.started_at: str | None = None
        self.ended_at: str | None = None
        self.duration_ms: float | None = None

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "status": self.status.value,
            "input": self.input,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
        }


class RunResult:
    def __init__(self) -> None:
        self.status = StepStatus.QUEUED
        self.error: str | None = None
        self.input: Any = None
        self.output: Any = None
        self.started_at = _now()
        self.ended_at: str | None = None
        self.duration_ms: float | None = None
        self.steps: list[StepRecord] = []

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "error": self.error,
            "input": self.input,
            "output": self.output,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": self.duration_ms,
            "steps": [s.to_dict() for s in self.steps],
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_workflow(defn: WorkflowDefinition, *, user_input: Any = None,
                 variables: dict[str, Any] | None = None) -> RunResult:
    from .validation import validate_graph

    result = RunResult()
    result.input = user_input
    result.status = StepStatus.RUNNING

    t0 = time.perf_counter()
    try:
        order = validate_graph(defn)
    except Exception as exc:
        result.status = StepStatus.ERROR
        result.error = f"Validation failed: {exc}"
        result.ended_at = _now()
        result.duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        return result

    settings = get_settings()
    node_by_id = {n.id: n for n in defn.nodes}
    edges_by_source: dict[str, list] = {}
    for e in defn.edges:
        edges_by_source.setdefault(e.source, []).append(e)
    incoming: dict[str, list] = {n.id: [] for n in defn.nodes}
    for e in defn.edges:
        incoming[e.target].append(e)

    run_vars = dict(defn.variables)
    run_vars.update(variables or {})
    if user_input is not None:
        run_vars["input"] = user_input

    records = {n.id: StepRecord(n) for n in defn.nodes}
    outputs: dict[str, Any] = {}
    active_edges: set[str] = set()   # edge ids that carried activation
    completed: set[str] = set()

    input_node = next(n for n in defn.nodes if n.type == NodeType.INPUT)
    ready = [input_node.id]

    steps_run = 0
    while ready:
        if steps_run >= settings.engine_max_steps:
            raise RuntimeError(f"Execution stopped: exceeded {settings.engine_max_steps} steps (possible infinite loop)")
        node = node_by_id[ready.pop(0)]
        rec = records[node.id]

        active_incoming = [e for e in incoming[node.id] if e.id in active_edges]
        if node.type != NodeType.INPUT and not active_incoming:
            rec.status = StepStatus.SKIPPED
            continue
        if node.type != NodeType.INPUT and any(
            e.source not in completed for e in active_incoming
        ):
            # predecessor failed → this branch dies
            rec.status = StepStatus.SKIPPED
            continue

        inputs = [outputs[e.source] for e in active_incoming if e.source in outputs]
        rec.input = inputs[0] if len(inputs) == 1 else inputs
        rec.status = StepStatus.RUNNING
        rec.started_at = _now()

        executor = registry().get(node.type.value)
        try:
            ctx = ExecutionContext(
                node_id=node.id,
                config=node.parsed_config(),
                inputs=inputs,
                variables=run_vars,
                outputs=outputs,
            )
            out = executor.execute(ctx)
            rec.output = out
            outputs[node.id] = out
            rec.status = StepStatus.SUCCESS
        except Exception as exc:
            rec.status = StepStatus.ERROR
            rec.error = f"{type(exc).__name__}: {exc}"
        finally:
            rec.ended_at = _now()
            rec.duration_ms = round(
                (datetime.fromisoformat(rec.ended_at) - datetime.fromisoformat(rec.started_at))
                .total_seconds() * 1000, 2
            )
        steps_run += 1
        completed.add(node.id)

        if rec.status != StepStatus.SUCCESS:
            # downstream nodes of this branch are skipped; loop continues and
            # marks them SKIPPED as they surface without active inputs
            continue

        # ── branch selection ────────────────────────────────────────
        # Labeled edges act as guards: they carry activation only when their
        # label is chosen. Unlabeled edges always pass activation through.
        chosen: set[str] | None = None
        if hasattr(executor, "branch"):
            chosen = executor.branch(ctx, rec.output)  # type: ignore[attr-defined]
        for edge in edges_by_source.get(node.id, []):
            label = (edge.label or "").strip().upper()
            if chosen is None or not label or label in chosen:
                active_edges.add(edge.id)
                if edge.target not in ready and edge.target not in completed:
                    ready.append(edge.target)

    # anything never activated is SKIPPED
    for nid, rec in records.items():
        if rec.status == StepStatus.IDLE:
            rec.status = StepStatus.SKIPPED

    outs = [r.output for r in records.values()
            if r.node_type == NodeType.OUTPUT.value and r.status == StepStatus.SUCCESS]
    result.output = outs[0] if len(outs) == 1 else outs
    result.steps = [records[nid] for nid in order]
    result.status = StepStatus.SUCCESS if not any(
        s.status == StepStatus.ERROR for s in result.steps
    ) else StepStatus.ERROR
    if result.status == StepStatus.ERROR:
        failed = next(s for s in result.steps if s.status == StepStatus.ERROR)
        result.error = f"Node '{failed.label}' failed: {failed.error}"
    result.ended_at = _now()
    result.duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    return result
