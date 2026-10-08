from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.services import scheduler, workflow_service
from app.services.cron import matches_cron, validate_cron_expression
from tests.test_async_executions import definition


def test_cron_matches_weekday_calendar_expression():
    monday = datetime(2026, 10, 5, 9, 0, tzinfo=timezone.utc)
    saturday = datetime(2026, 10, 3, 9, 0, tzinfo=timezone.utc)
    assert matches_cron("0 9 * * 1-5", monday)
    assert not matches_cron("0 9 * * 1-5", saturday)
    assert not matches_cron("0 9 * * 1-5", monday.replace(minute=1))


def test_invalid_cron_is_rejected():
    with pytest.raises(ValueError):
        validate_cron_expression("invalid cron")
    with pytest.raises(ValueError):
        validate_cron_expression("0 99 * * *")


def test_scheduler_runs_cron_once_per_matching_minute(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        workflow = workflow_service.create_workflow(db, definition())
        workflow.schedule_cron = "* * * * *"
        db.commit()

    monkeypatch.setattr(scheduler, "SessionLocal", Session)
    started: list[int] = []
    monkeypatch.setattr(scheduler, "start_execution", started.append)
    now = datetime(2026, 10, 5, 9, 0, 10, tzinfo=timezone.utc)

    assert len(scheduler.dispatch_due_schedules(now)) == 1
    assert scheduler.dispatch_due_schedules(now + timedelta(seconds=30)) == []
    assert len(scheduler.dispatch_due_schedules(now + timedelta(minutes=1))) == 1
    assert len(started) == 2
