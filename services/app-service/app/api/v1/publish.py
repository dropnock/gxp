"""
App publish flow.

draft → submit-review → under_review → publish (admin) → published
                                      → reject  (admin) → rejected → (edit) → draft

The published schema is served from MinIO via a pre-signed URL redirect,
or directly from the AppVersion.schema_json column (for sandbox preview).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.config import settings
from app.db.session import get_db
from app.models.app import AppVersion, GxpApp
from app.services.builder import SchemaValidationError
from app.services.publisher import publish_app
from gxp_shared.auth.dependencies import UserContext, require_roles

router = APIRouter()

RequiresDev = Annotated[UserContext, Depends(require_roles("gxp-developer", "gxp-admin"))]
RequiresAdmin = Annotated[UserContext, Depends(require_roles("gxp-admin"))]
RequiresAny = Annotated[UserContext, Depends(require_roles(
    "gxp-user", "gxp-developer", "gxp-admin", "gxp-case-worker",
))]


class ReviewNote(BaseModel):
    note: str | None = None


class VersionOut(BaseModel):
    id: uuid.UUID
    app_id: uuid.UUID
    version_number: int
    schema_json: dict
    minio_key: str
    published_by: str
    published_at: datetime

    model_config = {"from_attributes": True}


@router.post("/{app_id}/submit-review", status_code=200)
async def submit_review(
    app_id: uuid.UUID,
    user: RequiresDev,
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(GxpApp, app_id)
    if not app or not app.is_active:
        raise HTTPException(status_code=404, detail="App not found")
    if app.status != "draft":
        raise HTTPException(status_code=409, detail=f"App status is '{app.status}', must be 'draft'")
    app.status = "under_review"
    app.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
    return {"app_id": str(app_id), "status": "under_review"}


@router.post("/{app_id}/reject", status_code=200)
async def reject_app(
    app_id: uuid.UUID,
    body: ReviewNote,
    user: RequiresAdmin,
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(GxpApp, app_id)
    if not app or not app.is_active:
        raise HTTPException(status_code=404, detail="App not found")
    if app.status != "under_review":
        raise HTTPException(status_code=409, detail="App is not under review")
    app.status = "rejected"
    app.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
    return {"app_id": str(app_id), "status": "rejected", "note": body.note}


@router.post("/{app_id}/publish", response_model=VersionOut, status_code=201)
async def publish(
    app_id: uuid.UUID,
    user: RequiresAdmin,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(GxpApp)
        .options(
            selectinload(GxpApp.pages),
            selectinload(GxpApp.versions),
            selectinload(GxpApp.permissions),
        )
        .where(GxpApp.id == app_id)
    )
    app = result.scalar_one_or_none()
    if not app or not app.is_active:
        raise HTTPException(status_code=404, detail="App not found")
    if app.status not in ("under_review", "draft"):
        raise HTTPException(status_code=409, detail=f"App status is '{app.status}', must be 'under_review' or 'draft'")

    tenant_slug = user.tenant_slug or "platform"
    try:
        version = await publish_app(app, tenant_slug, user.user_id, db)
    except SchemaValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    await db.commit()
    await db.refresh(version)
    return version


@router.get("/{app_id}/published", response_model=VersionOut | None)
async def get_published(
    app_id: uuid.UUID,
    user: RequiresAny,
    db: AsyncSession = Depends(get_db),
):
    """Return the current published schema. Used by the runtime app."""
    app = await db.get(GxpApp, app_id)
    if not app or not app.is_active:
        raise HTTPException(status_code=404, detail="App not found")
    if not app.current_version_id:
        return None
    version = await db.get(AppVersion, app.current_version_id)
    return version


@router.get("/{app_id}/versions", response_model=list[VersionOut])
async def list_versions(
    app_id: uuid.UUID,
    user: RequiresDev,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AppVersion)
        .where(AppVersion.app_id == app_id)
        .order_by(AppVersion.version_number.desc())
    )
    return result.scalars().all()
