"""Small in-process interval scheduler for active workflows.

It intentionally uses persisted timestamps rather than in-memory timers, so a
restart only delays a schedule by at most one polling cycle.
"""
import asyncio
import logging
from datetime import datetime, timezone

from ..config import get_settings
from ..db import SessionLocal
from ..models import Workflow
from ..schemas import ExecuteRequest
from .cron import matches_cron
from .execution_service import queue_execution, start_execution

logger = logging.getLogger(__name__)


def dispatch_due_schedules(now: datetime | None = None) -> list[int]:
    now = now or datetime.now(timezone.utc)
    execution_ids: list[int] = []
    with SessionLocal() as db:
        workflows = (
            db.query(Workflow)
            .filter(
                Workflow.active.is_(True),
                (Workflow.schedule_interval_seconds.is_not(None) | Workflow.schedule_cron.is_not(None)),
            )
            .all()
        )
        for workflow in workflows:
            interval = workflow.schedule_interval_seconds
            cron = workflow.schedule_cron
            last = workflow.last_scheduled_at
            # SQLite does not round-trip timezone information for DATETIME.
            if last is not None and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if cron:
                if last and last.replace(second=0, microsecond=0) == now.replace(second=0, microsecond=0):
                    continue
                if not matches_cron(cron, now):
                    continue
            elif interval is None or (last and (now - last).total_seconds() < interval):
                continue
            execution = queue_execution(db, workflow.id, ExecuteRequest(), trigger="schedule")
            workflow.last_scheduled_at = now
            db.commit()
            execution_ids.append(execution.id)

    for execution_id in execution_ids:
        start_execution(execution_id)
    return execution_ids


async def run_scheduler() -> None:
    poll_seconds = max(1, get_settings().scheduler_poll_seconds)
    while True:
        try:
            dispatch_due_schedules()
        except Exception:  # Scheduler must not take down the API.
            logger.exception("Unable to dispatch scheduled workflows")
        await asyncio.sleep(poll_seconds)
