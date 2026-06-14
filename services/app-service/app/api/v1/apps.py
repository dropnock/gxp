"""
App CRUD.

status machine: draft → under_review → published | rejected
Only gxp-developer or gxp-admin can create apps.
All roles with view permission on a specific app can read it.
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
from app.models.app import GxpApp, AppPermission
from gxp_shared.auth.dependencies import UserContext, require_roles

router = APIRouter()

RequiresDev = Annotated[UserContext, Depends(require_roles("gxp-developer", "gxp-admin"))]
RequiresAdmin = Annotated[UserContext, Depends(require_roles("gxp-admin"))]
RequiresAny = Annotated[UserContext, Depends(require_roles(
    "gxp-user", "gxp-developer", "gxp-admin", "gxp-case-worker",
))]

_VALID_STATUSES = {"draft", "under_review", "published", "rejected"}


class AppCreate(BaseModel):
    name: str
    description: str | None = None


class AppUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class AppOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    status: str
    current_version_id: uuid.UUID | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class PermissionOut(BaseModel):
    id: uuid.UUID; app_id: uuid.UUID; role: str; permission: str
    model_config = {"from_attributes": True}


class PermissionGrant(BaseModel):
    role: str
    permission: str = "view"


@router.post("", response_model=AppOut, status_code=201)
async def create_app(
    body: AppCreate,
    user: RequiresDev,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(tz=timezone.utc)
    app = GxpApp(
        id=uuid.uuid4(),
        name=body.name,
        description=body.description,
        status="draft",
        created_by=user.user_id,
        created_at=now,
        updated_at=now,
        is_active=True,
    )
    db.add(app)
    # Creator gets edit permission automatically
    db.add(AppPermission(
        id=uuid.uuid4(), app_id=app.id, role="gxp-developer",
        permission="edit", granted_by=user.user_id, granted_at=now,
    ))
    await db.commit()
    await db.refresh(app)
    return app


@router.get("", response_model=list[AppOut])
async def list_apps(
    user: RequiresAny,
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    stmt = select(GxpApp).where(GxpApp.is_active == True)  # noqa: E712
    if status:
        if status not in _VALID_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid status")
        stmt = stmt.where(GxpApp.status == status)

    # Non-admins only see apps where they have a permission entry
    if "gxp-admin" not in user.roles:
        from sqlalchemy import exists
        user_roles = user.roles
        stmt = stmt.where(
            exists(
                select(AppPermission.id).where(
                    AppPermission.app_id == GxpApp.id,
                    AppPermission.role.in_(user_roles),
                )
            )
        )

    stmt = stmt.order_by(GxpApp.updated_at.desc()).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.get("/{app_id}", response_model=AppOut)
async def get_app(
    app_id: uuid.UUID,
    user: RequiresAny,
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(GxpApp, app_id)
    if not app or not app.is_active:
        raise HTTPException(status_code=404, detail="App not found")
    return app


@router.patch("/{app_id}", response_model=AppOut)
async def update_app(
    app_id: uuid.UUID,
    body: AppUpdate,
    user: RequiresDev,
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(GxpApp, app_id)
    if not app or not app.is_active:
        raise HTTPException(status_code=404, detail="App not found")
    if app.status not in ("draft", "rejected"):
        raise HTTPException(status_code=409, detail="Only draft or rejected apps can be edited")
    if body.name is not None:
        app.name = body.name
    if body.description is not None:
        app.description = body.description
    app.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(app)
    return app


@router.delete("/{app_id}", status_code=204)
async def delete_app(
    app_id: uuid.UUID,
    user: RequiresAdmin,
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(GxpApp, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    app.is_active = False
    app.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()


@router.get("/{app_id}/permissions", response_model=list[PermissionOut])
async def list_permissions(
    app_id: uuid.UUID,
    user: RequiresDev,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AppPermission).where(AppPermission.app_id == app_id)
    )
    return result.scalars().all()


@router.post("/{app_id}/permissions", response_model=PermissionOut, status_code=201)
async def grant_permission(
    app_id: uuid.UUID,
    body: PermissionGrant,
    user: RequiresAdmin,
    db: AsyncSession = Depends(get_db),
):
    if body.permission not in ("view", "edit"):
        raise HTTPException(status_code=422, detail="permission must be 'view' or 'edit'")
    app = await db.get(GxpApp, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    perm = AppPermission(
        id=uuid.uuid4(), app_id=app_id, role=body.role,
        permission=body.permission, granted_by=user.user_id,
        granted_at=datetime.now(tz=timezone.utc),
    )
    db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return perm
