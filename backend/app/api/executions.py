"""Execution REST endpoints."""
from fastapi import Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import execution_service
from .routes import api_router


@api_router.get("/executions/{execution_id}")
def get_execution(execution_id: int, db: Session = Depends(get_db)):
    ex = execution_service.get_execution(db, execution_id)
    return execution_service.serialize_execution(ex)


@api_router.get("/executions/{execution_id}/steps")
def get_execution_steps(execution_id: int, db: Session = Depends(get_db)):
    ex = execution_service.get_execution(db, execution_id)
    return execution_service.serialize_execution(ex)["steps"]
