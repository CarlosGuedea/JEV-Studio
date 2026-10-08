"""Execution service: queue workflows, run them in background, and persist every step."""
from datetime import datetime, timezone
from threading import Thread
from typing import Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..engine import run_workflow
from ..models import Execution, ExecutionStep, Workflow
from ..schemas import ExecuteRequest, WorkflowDefinition
from .workflow_service import _to_definition, get_workflow

SessionFactory = Callable[[], Session]


def queue_execution(db: Session, workflow_id: int, req: ExecuteRequest, *, trigger: str = "manual") -> Execution:
    """Persist a queued run and return immediately; the caller starts the worker afterwards."""
    wf = get_workflow(db, workflow_id)
    execution = Execution(
        workflow_id=wf.id,
        status="QUEUED",
        trigger=trigger,
        input={"input": req.input, "variables": req.variables},
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def enqueue_workflow(db: Session, workflow_id: int, req: ExecuteRequest, *, trigger: str = "manual") -> Execution:
    execution = queue_execution(db, workflow_id, req, trigger=trigger)
    start_execution(execution.id)
    return execution


def start_execution(execution_id: int, *, session_factory: SessionFactory = SessionLocal) -> None:
    """Run independently of the request lifecycle, with a dedicated database session."""
    Thread(target=run_execution, args=(execution_id,), kwargs={"session_factory": session_factory}, daemon=True).start()


def run_execution(execution_id: int, *, session_factory: SessionFactory = SessionLocal) -> None:
    with session_factory() as db:
        execution = get_execution(db, execution_id)
        if execution.status != "QUEUED":
            return
        execution.status = "RUNNING"
        db.commit()

        wf = get_workflow(db, execution.workflow_id)
        definition: WorkflowDefinition = _to_definition(wf)
        payload = execution.input or {}
        user_input = payload.get("input")
        variables = payload.get("variables") or {}

        try:
            result = run_workflow(definition, user_input=user_input, variables=variables)
        except Exception as exc:  # engine-level guard (e.g. step limit)
            execution.status = "ERROR"
            execution.error = str(exc)
            execution.ended_at = datetime.now(timezone.utc)
            db.commit()
            return

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


def _parse(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts) if ts else None


def get_execution(db: Session, execution_id: int) -> Execution:
    ex = db.get(Execution, execution_id)
    if ex is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return ex


def list_executions(db: Session, workflow_id: int, *, limit: int = 20) -> list[Execution]:
    get_workflow(db, workflow_id)
    return (
        db.query(Execution)
        .filter(Execution.workflow_id == workflow_id)
        .order_by(Execution.id.desc())
        .limit(limit)
        .all()
    )


def get_workflow_by_webhook(db: Session, token: str) -> Workflow:
    wf = db.query(Workflow).filter(Workflow.webhook_token == token).first()
    if wf is None or not wf.active:
        raise HTTPException(status_code=404, detail="Webhook not found or workflow inactive")
    return wf


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
        "trigger": ex.trigger,
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
