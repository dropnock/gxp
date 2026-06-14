"""
BPMN workflow definition CRUD.

Validation pipeline on create/update:
  1. Well-formed XML (lxml)
  2. Contains a <process> element (extract process_id)
  3. Parseable by SpiffWorkflow (catches semantic errors)

Definitions are soft-deleted (is_active=False) — instances keep a reference
to the definition they were started from, so hard delete would break history.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.engine import extract_process_id, sha256_xml, validate_bpmn
from app.models.workflow import WorkflowDefinition
from gxp_shared.auth.dependencies import UserContext, require_roles

router = APIRouter()

RequiresDeveloper = Annotated[UserContext, Depends(require_roles("gxp-developer", "gxp-admin"))]


class DefinitionCreate(BaseModel):
    name: str
    description: str | None = None
    xml_content: str


class DefinitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    xml_content: str | None = None


class DefinitionOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    definition_type: str
    process_id: str | None
    version: int
    xml_hash: str
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DefinitionDetailOut(DefinitionOut):
    xml_content: str


@router.post("", response_model=DefinitionDetailOut, status_code=201)
async def create_definition(
    body: DefinitionCreate,
    user: RequiresDeveloper,
    db: AsyncSession = Depends(get_db),
):
    valid, err = validate_bpmn(body.xml_content)
    if not valid:
        raise HTTPException(status_code=422, detail=f"Invalid BPMN: {err}")

    process_id = extract_process_id(body.xml_content)
    defn = WorkflowDefinition(
        id=uuid.uuid4(),
        definition_type="bpmn",
        name=body.name,
        description=body.description,
        xml_content=body.xml_content,
        xml_hash=sha256_xml(body.xml_content),
        process_id=process_id,
        version=1,
        is_active=True,
        created_by=user.user_id,
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )
    db.add(defn)
    await db.commit()
    await db.refresh(defn)
    return defn


@router.get("", response_model=list[DefinitionOut])
async def list_definitions(
    user: RequiresDeveloper,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    active_only: bool = Query(True),
):
    stmt = select(WorkflowDefinition).where(WorkflowDefinition.definition_type == "bpmn")
    if active_only:
        stmt = stmt.where(WorkflowDefinition.is_active == True)  # noqa: E712
    stmt = stmt.order_by(WorkflowDefinition.name).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.get("/{definition_id}", response_model=DefinitionDetailOut)
async def get_definition(
    definition_id: uuid.UUID,
    user: RequiresDeveloper,
    db: AsyncSession = Depends(get_db),
):
    defn = await db.get(WorkflowDefinition, definition_id)
    if not defn or defn.definition_type != "bpmn":
        raise HTTPException(status_code=404, detail="Definition not found")
    return defn


@router.put("/{definition_id}", response_model=DefinitionDetailOut)
async def update_definition(
    definition_id: uuid.UUID,
    body: DefinitionUpdate,
    user: RequiresDeveloper,
    db: AsyncSession = Depends(get_db),
):
    defn = await db.get(WorkflowDefinition, definition_id)
    if not defn or defn.definition_type != "bpmn":
        raise HTTPException(status_code=404, detail="Definition not found")
    if not defn.is_active:
        raise HTTPException(status_code=409, detail="Cannot update inactive definition")

    if body.name is not None:
        defn.name = body.name
    if body.description is not None:
        defn.description = body.description
    if body.xml_content is not None:
        valid, err = validate_bpmn(body.xml_content)
        if not valid:
            raise HTTPException(status_code=422, detail=f"Invalid BPMN: {err}")
        defn.xml_content = body.xml_content
        defn.xml_hash = sha256_xml(body.xml_content)
        defn.process_id = extract_process_id(body.xml_content)
        defn.version += 1

    defn.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(defn)
    return defn


@router.delete("/{definition_id}", status_code=204)
async def delete_definition(
    definition_id: uuid.UUID,
    user: Annotated[UserContext, Depends(require_roles("gxp-admin"))],
    db: AsyncSession = Depends(get_db),
):
    defn = await db.get(WorkflowDefinition, definition_id)
    if not defn or defn.definition_type != "bpmn":
        raise HTTPException(status_code=404, detail="Definition not found")
    defn.is_active = False
    defn.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
