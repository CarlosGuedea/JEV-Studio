"""Workflow REST endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import ExecuteRequest, WorkflowCreate, WorkflowUpdate
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


@api_router.post("/workflows/{workflow_id}/execute", status_code=201)
def execute_workflow(workflow_id: int, body: ExecuteRequest, db: Session = Depends(get_db)):
    ex = execution_service.execute_workflow(db, workflow_id, body)
    return execution_service.serialize_execution(ex)
