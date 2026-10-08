"""Database setup (SQLite via SQLAlchemy)."""
import secrets

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from . import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema()


def _migrate_sqlite_schema() -> None:
    """Apply the small additive migration needed by installations without Alembic."""
    if engine.dialect.name != "sqlite" or "workflows" not in inspect(engine).get_table_names():
        return

    columns = {column["name"] for column in inspect(engine).get_columns("workflows")}
    execution_columns = {column["name"] for column in inspect(engine).get_columns("executions")}
    with engine.begin() as connection:
        if "active" not in columns:
            connection.execute(text("ALTER TABLE workflows ADD COLUMN active BOOLEAN NOT NULL DEFAULT 1"))
        if "webhook_token" not in columns:
            connection.execute(text("ALTER TABLE workflows ADD COLUMN webhook_token VARCHAR(64)"))
        if "schedule_interval_seconds" not in columns:
            connection.execute(text("ALTER TABLE workflows ADD COLUMN schedule_interval_seconds INTEGER"))
        if "schedule_cron" not in columns:
            connection.execute(text("ALTER TABLE workflows ADD COLUMN schedule_cron VARCHAR(128)"))
        if "last_scheduled_at" not in columns:
            connection.execute(text("ALTER TABLE workflows ADD COLUMN last_scheduled_at DATETIME"))
        if "trigger" not in execution_columns:
            connection.execute(text("ALTER TABLE executions ADD COLUMN trigger VARCHAR(16) NOT NULL DEFAULT 'manual'"))

        missing_tokens = connection.execute(text("SELECT id FROM workflows WHERE webhook_token IS NULL OR webhook_token = ''")).scalars()
        for workflow_id in missing_tokens:
            connection.execute(
                text("UPDATE workflows SET webhook_token = :token WHERE id = :id"),
                {"token": secrets.token_urlsafe(18), "id": workflow_id},
            )
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_workflows_webhook_token ON workflows (webhook_token)"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
