"""Persistence tests for queued, webhook, and scheduled workflow execution."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.schemas import ExecuteRequest, WorkflowDefinition
from app.services import execution_service, scheduler, workflow_service


def definition() -> WorkflowDefinition:
    return WorkflowDefinition.model_validate({
        "config": {"name": "Background test"},
        "nodes": [
            {"id": "in", "type": "input", "position": {"x": 0, "y": 0}, "config": {}},
            {"id": "py", "type": "python", "position": {"x": 1, "y": 0}, "config": {"expression": "len(split(input))"}},
            {"id": "out", "type": "output", "position": {"x": 2, "y": 0}, "config": {}},
        ],
        "edges": [
            {"id": "e1", "source": "in", "target": "py"},
            {"id": "e2", "source": "py", "target": "out"},
        ],
    })


def session_factory():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_queued_execution_completes_in_a_separate_session():
    Session = session_factory()
    with Session() as db:
        workflow = workflow_service.create_workflow(db, definition())
        execution = execution_service.queue_execution(db, workflow.id, ExecuteRequest(input="uno dos tres"))
        assert execution.status == "QUEUED"

    execution_service.run_execution(execution.id, session_factory=Session)

    with Session() as db:
        stored = execution_service.get_execution(db, execution.id)
        assert stored.status == "SUCCESS"
        assert stored.trigger == "manual"
        assert len(stored.steps) == 3


def test_scheduler_queues_active_interval_workflows(monkeypatch):
    Session = session_factory()
    with Session() as db:
        workflow = workflow_service.create_workflow(db, definition())
        workflow.schedule_interval_seconds = 60
        workflow.active = True
        db.commit()

    monkeypatch.setattr(scheduler, "SessionLocal", Session)
    started: list[int] = []
    monkeypatch.setattr(scheduler, "start_execution", started.append)
    now = datetime.now(timezone.utc)
    execution_ids = scheduler.dispatch_due_schedules(now)

    assert len(execution_ids) == 1
    assert started == execution_ids
    with Session() as db:
        stored = execution_service.get_execution(db, execution_ids[0])
        assert stored.status == "QUEUED"
        assert stored.trigger == "schedule"

    # A second scheduler pass reads SQLite's naïve timestamp and must neither
    # crash nor enqueue again before the configured interval has elapsed.
    assert scheduler.dispatch_due_schedules(now + timedelta(seconds=30)) == []
    assert scheduler.dispatch_due_schedules(now + timedelta(seconds=61))


def test_inactive_workflow_rejects_webhook():
    Session = session_factory()
    with Session() as db:
        workflow = workflow_service.create_workflow(db, definition())
        workflow.active = False
        db.commit()

        try:
            execution_service.get_workflow_by_webhook(db, workflow.webhook_token)
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 404
        else:
            raise AssertionError("Inactive webhook should not be reachable")
