"""
Workflow instance lifecycle.

POST /workflow/instances        — start instance (enqueues execute_workflow_step)
GET  /workflow/instances        — list with status/definition filter
GET  /workflow/instances/{id}   — single instance + task list
POST /workflow/instances/{id}/cancel — cancel running/waiting instance

After creation the initial engine steps are run asynchronously via Celery.
The client polls GET /{id} to watch status change from 'running' → 'waiting'
(waiting on human task) or 'completed'.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.engine import create_workflow, serialize_workflow, validate_bpmn
from app.models.workflow import TaskInstance, WorkflowDefinition, WorkflowInstance
from gxp_shared.auth.dependencies import UserContext, require_roles
from worker.tasks import execute_workflow_step

router = APIRouter()

RequiresUser = Annotated[UserContext, Depends(require_roles("gxp-user", "gxp-developer", "gxp-admin", "gxp-case-worker", "gxp-case-manager"))]
RequiresAdmin = Annotated[UserContext, Depends(require_roles("gxp-admin"))]


class InstanceCreate(BaseModel):
    definition_id: uuid.UUID
    initial_variables: dict = {}
    case_id: uuid.UUID | None = None


class TaskInstanceOut(BaseModel):
    id: uuid.UUID
    spiff_task_id: str
    task_name: str
    task_title: str | None
    form_schema: dict
    status: str
    assigned_to: str | None
    candidate_roles: list
    created_at: datetime
    claimed_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class InstanceOut(BaseModel):
    id: uuid.UUID
    definition_id: uuid.UUID
    definition_version: int
    status: str
    variables: dict
    case_id: uuid.UUID | None
    started_by: str
    started_at: datetime
    completed_at: datetime | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class InstanceDetailOut(InstanceOut):
    task_instances: list[TaskInstanceOut]


@router.post("", response_model=InstanceOut, status_code=202)
async def start_instance(
    body: InstanceCreate,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    defn = await db.get(WorkflowDefinition, body.definition_id)
    if not defn or defn.definition_type != "bpmn" or not defn.is_active:
        raise HTTPException(status_code=404, detail="Active BPMN definition not found")

    # Eagerly build and serialize initial workflow state so Celery worker
    # can start from a valid checkpoint rather than re-parsing XML.
    workflow = create_workflow(
        bpmn_xml=defn.xml_content,
        process_id=defn.process_id,
        initial_variables=body.initial_variables,
    )
    state = serialize_workflow(workflow)

    instance = WorkflowInstance(
        id=uuid.uuid4(),
        definition_id=defn.id,
        definition_version=defn.version,
        status="running",
        state_json=state,
        variables=body.initial_variables,
        case_id=body.case_id,
        started_by=user.user_id,
        started_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )
    db.add(instance)
    await db.commit()
    await db.refresh(instance)

    # Kick off the first engine step asynchronously
    tenant_slug = user.tenant_slug or "platform"
    execute_workflow_step.apply_async(
        args=[str(instance.id), tenant_slug, user.user_id],
        queue="workflow",
    )

    return instance


@router.get("", response_model=list[InstanceOut])
async def list_instances(
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None, description="Filter by status: running|waiting|completed|cancelled"),
    definition_id: uuid.UUID | None = Query(None),
):
    stmt = select(WorkflowInstance)
    if status:
        stmt = stmt.where(WorkflowInstance.status == status)
    if definition_id:
        stmt = stmt.where(WorkflowInstance.definition_id == definition_id)
    stmt = stmt.order_by(WorkflowInstance.started_at.desc()).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.get("/{instance_id}", response_model=InstanceDetailOut)
async def get_instance(
    instance_id: uuid.UUID,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkflowInstance)
        .options(selectinload(WorkflowInstance.task_instances))
        .where(WorkflowInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    return instance


@router.post("/{instance_id}/cancel", status_code=200)
async def cancel_instance(
    instance_id: uuid.UUID,
    user: RequiresAdmin,
    db: AsyncSession = Depends(get_db),
):
    instance = await db.get(WorkflowInstance, instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")
    if instance.status in ("completed", "cancelled"):
        raise HTTPException(status_code=409, detail=f"Instance already {instance.status}")

    instance.status = "cancelled"
    instance.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
    return {"id": str(instance_id), "status": "cancelled"}
