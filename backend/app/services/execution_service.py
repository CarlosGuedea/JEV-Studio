"""Execution service: runs the engine and persists executions + steps."""
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..engine import run_workflow
from ..models import Execution, ExecutionStep
from ..schemas import ExecuteRequest, WorkflowDefinition
from .workflow_service import get_workflow


def execute_workflow(db: Session, workflow_id: int, req: ExecuteRequest) -> Execution:
    wf = get_workflow(db, workflow_id)
    from .workflow_service import _to_definition
    definition: WorkflowDefinition = _to_definition(wf)

    execution = Execution(workflow_id=wf.id, status="RUNNING", input={"input": req.input, "variables": req.variables})
    db.add(execution)
    db.commit()
    db.refresh(execution)

    try:
        result = run_workflow(definition, user_input=req.input, variables=req.variables)
    except Exception as exc:  # engine-level guard (e.g. step limit)
        execution.status = "ERROR"
        execution.error = str(exc)
        execution.ended_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(execution)
        return execution

    for step in result.steps:
        db.add(ExecutionStep(
            execution_id=execution.id,
            node_id=step.node_id,
            node_type=step.node_type,
            label=step.label,
            status=step.status.value,
            input=step.input,
            output=step.output,
            error=step.error,
            started_at=_parse(step.started_at),
            ended_at=_parse(step.ended_at),
            duration_ms=step.duration_ms,
        ))
    execution.status = result.status.value
    execution.error = result.error
    execution.output = {"output": result.output}
    execution.ended_at = _parse(result.ended_at)
    execution.duration_ms = result.duration_ms
    db.commit()
    db.refresh(execution)
    return execution


def _parse(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts) if ts else None


def get_execution(db: Session, execution_id: int) -> Execution:
    ex = db.get(Execution, execution_id)
    if ex is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ex


def serialize_execution(ex: Execution) -> dict:
    return {
        "id": ex.id,
        "workflow_id": ex.workflow_id,
        "status": ex.status,
        "error": ex.error,
        "input": ex.input,
        "output": ex.output,
        "started_at": ex.started_at.isoformat() if ex.started_at else None,
        "ended_at": ex.ended_at.isoformat() if ex.ended_at else None,
        "duration_ms": ex.duration_ms,
        "steps": [
            {
                "node_id": s.node_id,
                "node_type": s.node_type,
                "label": s.label,
                "status": s.status,
                "input": s.input,
                "output": s.output,
                "error": s.error,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "duration_ms": s.duration_ms,
            }
            for s in ex.steps
        ],
    }
