"""Workflow CRUD service: maps WorkflowDefinition <-> ORM rows."""
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Edge, Node, Workflow
from ..schemas import AutomationConfig, NodeType, WorkflowDefinition


def _to_orm(db: Session, definition: WorkflowDefinition, wf: Workflow | None = None) -> Workflow:
    wf = wf or Workflow(webhook_token=secrets.token_urlsafe(18))
    wf.name = definition.config.name
    wf.description = definition.config.description
    wf.config = {"variables": definition.variables}
    automation = next((node for node in definition.nodes if node.type == NodeType.AUTOMATION), None)
    if automation is not None:
        trigger = AutomationConfig.model_validate(automation.config)
        wf.active = trigger.active
        if trigger.cron:
            wf.schedule_cron = trigger.cron
            wf.schedule_interval_seconds = None
        else:
            wf.schedule_cron = None
            wf.schedule_interval_seconds = trigger.interval_seconds
    wf.updated_at = datetime.now(timezone.utc)
    if wf.id is None:
        db.add(wf)
        db.flush()

    wf.nodes.clear()
    wf.edges.clear()
    db.flush()
    for n in definition.nodes:
        db.add(Node(workflow_id=wf.id, node_id=n.id, type=n.type.value,
                    label=n.label, position=n.position.model_dump(), config=n.config))
    for e in definition.edges:
        db.add(Edge(workflow_id=wf.id, edge_id=e.id, source=e.source,
                    target=e.target, label=e.label))
    db.commit()
    db.refresh(wf)
    return wf


def _to_definition(wf: Workflow) -> WorkflowDefinition:
    nodes = [
        {"id": n.node_id, "type": n.type, "label": n.label,
         "position": n.position, "config": n.config}
        for n in sorted(wf.nodes, key=lambda x: x.id)
    ]
    edges = [
        {"id": e.edge_id, "source": e.source, "target": e.target, "label": e.label}
        for e in sorted(wf.edges, key=lambda x: x.id)
    ]
    for node in nodes:
        if node["type"] == NodeType.AUTOMATION.value:
            node["config"] = {
                "active": wf.active,
                "interval_seconds": wf.schedule_interval_seconds,
                "cron": wf.schedule_cron or "",
            }
    return WorkflowDefinition.model_validate({
        "nodes": nodes,
        "edges": edges,
        "config": {"name": wf.name, "description": wf.description},
        "variables": (wf.config or {}).get("variables", {}),
    })


def list_workflows(db: Session) -> list[dict]:
    out = []
    for wf in db.query(Workflow).order_by(Workflow.updated_at.desc()).all():
        out.append({
            "id": wf.id,
            "name": wf.name,
            "description": wf.description,
            "node_count": len(wf.nodes),
            "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
            "active": wf.active,
            "webhook_token": wf.webhook_token,
            "schedule_interval_seconds": wf.schedule_interval_seconds,
            "schedule_cron": wf.schedule_cron,
        })
    return out


def get_workflow(db: Session, workflow_id: int) -> Workflow:
    wf = db.get(Workflow, workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


def create_workflow(db: Session, definition: WorkflowDefinition) -> Workflow:
    return _to_orm(db, definition)


def update_workflow(db: Session, workflow_id: int, definition: WorkflowDefinition) -> Workflow:
    wf = get_workflow(db, workflow_id)
    return _to_orm(db, definition, wf)


def delete_workflow(db: Session, workflow_id: int) -> None:
    wf = get_workflow(db, workflow_id)
    db.delete(wf)
    db.commit()


def duplicate_workflow(db: Session, workflow_id: int) -> Workflow:
    wf = get_workflow(db, workflow_id)
    definition = _to_definition(wf)
    definition.config.name = f"{wf.name} (copia)"
    for n in definition.nodes:
        n.id = f"{n.id}_c"
    id_map = {e.id: f"{e.id}_c" for e in definition.edges}
    for e in definition.edges:
        e.id = id_map[e.id]
        if e.source.endswith("_c") is False:
            e.source = f"{e.source}_c"
        if e.target.endswith("_c") is False:
            e.target = f"{e.target}_c"
    copy = _to_orm(db, definition)
    copy.active = False
    copy.schedule_interval_seconds = None
    copy.schedule_cron = None
    db.commit()
    db.refresh(copy)
    return copy


def update_runtime(
    db: Session,
    workflow_id: int,
    *,
    active: bool | None = None,
    schedule_interval_seconds: int | None | object = ...,  # ... means unchanged
    schedule_cron: str | None | object = ...,  # ... means unchanged
) -> Workflow:
    wf = get_workflow(db, workflow_id)
    if active is not None:
        wf.active = active
    if schedule_interval_seconds is not ...:
        wf.schedule_interval_seconds = schedule_interval_seconds  # type: ignore[assignment]
        if schedule_interval_seconds is not None:
            wf.schedule_cron = None
        wf.last_scheduled_at = None
    if schedule_cron is not ...:
        wf.schedule_cron = schedule_cron  # type: ignore[assignment]
        if schedule_cron is not None:
            wf.schedule_interval_seconds = None
        wf.last_scheduled_at = None
    wf.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(wf)
    return wf
