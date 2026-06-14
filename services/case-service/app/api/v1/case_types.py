"""
Case type CRUD.

Case types define the category of a case (e.g. Permit Application, Investigation)
and optionally specify metadata field schemas and a default workflow to auto-start.

Admin-only create/update/delete; all authenticated users can list and read.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.case import CaseType
from gxp_shared.auth.dependencies import UserContext, require_roles

router = APIRouter()

RequiresUser = Annotated[UserContext, Depends(require_roles(
    "gxp-user", "gxp-developer", "gxp-admin", "gxp-case-worker", "gxp-case-manager",
))]
RequiresAdmin = Annotated[UserContext, Depends(require_roles("gxp-admin", "gxp-case-manager"))]


class CaseTypeCreate(BaseModel):
    name: str
    description: str | None = None
    default_workflow_id: uuid.UUID | None = None
    schema: dict = {}


class CaseTypeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    default_workflow_id: uuid.UUID | None = None
    schema: dict | None = None
    is_active: bool | None = None


class CaseTypeOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    default_workflow_id: uuid.UUID | None
    schema: dict
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.post("", response_model=CaseTypeOut, status_code=201)
async def create_case_type(
    body: CaseTypeCreate,
    user: RequiresAdmin,
    db: AsyncSession = Depends(get_db),
):
    ct = CaseType(
        id=uuid.uuid4(),
        name=body.name,
        description=body.description,
        default_workflow_id=body.default_workflow_id,
        schema=body.schema,
        is_active=True,
        created_by=user.user_id,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )
    db.add(ct)
    await db.commit()
    await db.refresh(ct)
    return ct


@router.get("", response_model=list[CaseTypeOut])
async def list_case_types(
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    stmt = select(CaseType)
    if active_only:
        stmt = stmt.where(CaseType.is_active == True)  # noqa: E712
    stmt = stmt.order_by(CaseType.name).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.get("/{case_type_id}", response_model=CaseTypeOut)
async def get_case_type(
    case_type_id: uuid.UUID,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    ct = await db.get(CaseType, case_type_id)
    if not ct:
        raise HTTPException(status_code=404, detail="Case type not found")
    return ct


@router.put("/{case_type_id}", response_model=CaseTypeOut)
async def update_case_type(
    case_type_id: uuid.UUID,
    body: CaseTypeUpdate,
    user: RequiresAdmin,
    db: AsyncSession = Depends(get_db),
):
    ct = await db.get(CaseType, case_type_id)
    if not ct:
        raise HTTPException(status_code=404, detail="Case type not found")
    if body.name is not None:
        ct.name = body.name
    if body.description is not None:
        ct.description = body.description
    if body.default_workflow_id is not None:
        ct.default_workflow_id = body.default_workflow_id
    if body.schema is not None:
        ct.schema = body.schema
    if body.is_active is not None:
        ct.is_active = body.is_active
    ct.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(ct)
    return ct
