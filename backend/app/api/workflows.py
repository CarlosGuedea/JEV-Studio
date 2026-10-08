"""Workflow REST endpoints."""
from typing import Any

from fastapi import Body, Depends, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import ExecuteRequest, WorkflowCreate, WorkflowRuntimeUpdate, WorkflowUpdate
from ..services import execution_service, workflow_service
from .routes import api_router


@api_router.get("/workflows")
def list_workflows(db: Session = Depends(get_db)):
    return workflow_service.list_workflows(db)


@api_router.post("/workflows", status_code=201)
def create_workflow(body: WorkflowCreate, db: Session = Depends(get_db)):
    wf = workflow_service.create_workflow(db, body.definition)
    return {"id": wf.id}


@api_router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    wf = workflow_service.get_workflow(db, workflow_id)
    return {
        "id": wf.id,
        "name": wf.name,
        "description": wf.description,
        "definition": workflow_service._to_definition(wf).model_dump(),
        "created_at": wf.created_at.isoformat() if wf.created_at else None,
        "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
        "active": wf.active,
        "webhook_token": wf.webhook_token,
        "schedule_interval_seconds": wf.schedule_interval_seconds,
        "schedule_cron": wf.schedule_cron,
        "last_scheduled_at": wf.last_scheduled_at.isoformat() if wf.last_scheduled_at else None,
    }


@api_router.put("/workflows/{workflow_id}")
def update_workflow(workflow_id: int, body: WorkflowUpdate, db: Session = Depends(get_db)):
    wf = workflow_service.update_workflow(db, workflow_id, body.definition)
    return {"id": wf.id}


@api_router.delete("/workflows/{workflow_id}", status_code=204)
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow_service.delete_workflow(db, workflow_id)


@api_router.post("/workflows/{workflow_id}/duplicate", status_code=201)
def duplicate_workflow(workflow_id: int, db: Session = Depends(get_db)):
    wf = workflow_service.duplicate_workflow(db, workflow_id)
    return {"id": wf.id}


@api_router.post("/workflows/{workflow_id}/execute", status_code=202)
def execute_workflow(workflow_id: int, body: ExecuteRequest, db: Session = Depends(get_db)):
    ex = execution_service.enqueue_workflow(db, workflow_id, body)
    return execution_service.serialize_execution(ex)


@api_router.patch("/workflows/{workflow_id}/runtime")
def update_workflow_runtime(workflow_id: int, body: WorkflowRuntimeUpdate, db: Session = Depends(get_db)):
    schedule = body.schedule_interval_seconds if "schedule_interval_seconds" in body.model_fields_set else ...
    cron = body.schedule_cron if "schedule_cron" in body.model_fields_set else ...
    wf = workflow_service.update_runtime(
        db,
        workflow_id,
        active=body.active,
        schedule_interval_seconds=schedule,
        schedule_cron=cron,
    )
    return {
        "id": wf.id,
        "active": wf.active,
        "webhook_token": wf.webhook_token,
        "schedule_interval_seconds": wf.schedule_interval_seconds,
        "schedule_cron": wf.schedule_cron,
        "last_scheduled_at": wf.last_scheduled_at.isoformat() if wf.last_scheduled_at else None,
    }


@api_router.get("/workflows/{workflow_id}/executions")
def list_executions(workflow_id: int, limit: int = 20, db: Session = Depends(get_db)):
    return [execution_service.serialize_execution(ex) for ex in execution_service.list_executions(db, workflow_id, limit=min(max(limit, 1), 100))]


@api_router.api_route("/webhooks/{token}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], status_code=202)
def trigger_webhook(
    token: str,
    request: Request,
    payload: Any = Body(default=None),
    db: Session = Depends(get_db),
):
    workflow = execution_service.get_workflow_by_webhook(db, token)
    execution = execution_service.enqueue_workflow(
        db,
        workflow.id,
        ExecuteRequest(input={
            "body": payload,
            "query": dict(request.query_params),
            "method": request.method,
        }),
        trigger="webhook",
    )
    return {"accepted": True, "execution": execution_service.serialize_execution(execution)}
