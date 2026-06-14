"""
Human task inbox.

GET  /workflow/tasks/inbox   — tasks assigned to me or matching my roles
GET  /workflow/tasks/{id}    — task detail with form schema
POST /workflow/tasks/{id}/claim    — claim (assign to self)
POST /workflow/tasks/{id}/complete — submit form data and advance workflow

Claiming is optional: supervisors can complete unclaimed tasks directly.
Completing a task enqueues a Celery task (complete_task) which calls the
SpiffWorkflow engine, then advances to the next step.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.workflow import TaskInstance
from gxp_shared.auth.dependencies import UserContext, require_roles
from worker.tasks import complete_task as celery_complete_task

router = APIRouter()

RequiresUser = Annotated[UserContext, Depends(require_roles(
    "gxp-user", "gxp-developer", "gxp-admin",
    "gxp-approver", "gxp-case-worker", "gxp-case-manager",
))]


class TaskOut(BaseModel):
    id: uuid.UUID
    instance_id: uuid.UUID
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


class CompleteRequest(BaseModel):
    completion_data: dict[str, Any] = {}


@router.get("/inbox", response_model=list[TaskOut])
async def get_inbox(
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Return tasks that:
      - are assigned directly to this user, OR
      - are unassigned and have at least one candidate role the user holds
    Only returns 'ready' or 'claimed' tasks.
    """
    user_roles = user.roles

    stmt = (
        select(TaskInstance)
        .where(
            TaskInstance.status.in_(["ready", "claimed"]),
            or_(
                TaskInstance.assigned_to == user.user_id,
                # PostgreSQL: candidate_roles ?| array[...] checks for overlap
                TaskInstance.candidate_roles.op("?|")(user_roles),
            ),
        )
        .order_by(TaskInstance.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: uuid.UUID,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(TaskInstance, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    _assert_task_access(task, user)
    return task


@router.post("/{task_id}/claim", response_model=TaskOut)
async def claim_task(
    task_id: uuid.UUID,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(TaskInstance, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "ready":
        raise HTTPException(status_code=409, detail=f"Task is not in ready state (status={task.status})")
    _assert_task_access(task, user)

    task.assigned_to = user.user_id
    task.status = "claimed"
    task.claimed_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/{task_id}/complete", status_code=202)
async def complete_task(
    task_id: uuid.UUID,
    body: CompleteRequest,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(TaskInstance, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in ("ready", "claimed"):
        raise HTTPException(status_code=409, detail=f"Task cannot be completed (status={task.status})")
    _assert_task_access(task, user)

    tenant_slug = user.tenant_slug or "platform"
    celery_complete_task.apply_async(
        args=[
            str(task.id),
            str(task.instance_id),
            task.spiff_task_id,
            tenant_slug,
            body.completion_data,
            user.user_id,
        ],
        queue="workflow",
    )
    return {"task_id": str(task_id), "status": "processing"}


def _assert_task_access(task: TaskInstance, user: UserContext) -> None:
    """Raise 403 if the user is neither assigned to this task nor holds a candidate role."""
    is_assigned = task.assigned_to == user.user_id
    role_match = bool(set(task.candidate_roles or []).intersection(user.roles))
    if not is_assigned and not role_match:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
