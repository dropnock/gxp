"""
DMN decision table CRUD + ad-hoc evaluation endpoint.

DMN definitions share the workflow_definitions table with BPMN definitions,
distinguished by definition_type='dmn'.  The dmn_id column stores the
<decision id="..."> attribute value used by BPMN Business Rule Tasks to
reference this table.

POST /{id}/evaluate allows developers to test decision tables against
sample input before embedding them in a BPMN process.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.engine import evaluate_dmn, extract_dmn_id, sha256_xml, validate_dmn
from app.models.workflow import WorkflowDefinition
from gxp_shared.auth.dependencies import UserContext, require_roles

router = APIRouter()

RequiresDeveloper = Annotated[UserContext, Depends(require_roles("gxp-developer", "gxp-admin"))]


class DmnCreate(BaseModel):
    name: str
    description: str | None = None
    xml_content: str


class DmnUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    xml_content: str | None = None


class DmnOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    definition_type: str
    dmn_id: str | None
    version: int
    xml_hash: str
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DmnDetailOut(DmnOut):
    xml_content: str


class EvaluateRequest(BaseModel):
    input_data: dict[str, Any]


class EvaluateResponse(BaseModel):
    output: dict[str, Any]


@router.post("", response_model=DmnDetailOut, status_code=201)
async def create_dmn_definition(
    body: DmnCreate,
    user: RequiresDeveloper,
    db: AsyncSession = Depends(get_db),
):
    valid, err = validate_dmn(body.xml_content)
    if not valid:
        raise HTTPException(status_code=422, detail=f"Invalid DMN: {err}")

    dmn_id = extract_dmn_id(body.xml_content)
    defn = WorkflowDefinition(
        id=uuid.uuid4(),
        definition_type="dmn",
        name=body.name,
        description=body.description,
        xml_content=body.xml_content,
        xml_hash=sha256_xml(body.xml_content),
        dmn_id=dmn_id,
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


@router.get("", response_model=list[DmnOut])
async def list_dmn_definitions(
    user: RequiresDeveloper,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    active_only: bool = Query(True),
):
    stmt = select(WorkflowDefinition).where(WorkflowDefinition.definition_type == "dmn")
    if active_only:
        stmt = stmt.where(WorkflowDefinition.is_active == True)  # noqa: E712
    stmt = stmt.order_by(WorkflowDefinition.name).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.get("/{definition_id}", response_model=DmnDetailOut)
async def get_dmn_definition(
    definition_id: uuid.UUID,
    user: RequiresDeveloper,
    db: AsyncSession = Depends(get_db),
):
    defn = await db.get(WorkflowDefinition, definition_id)
    if not defn or defn.definition_type != "dmn":
        raise HTTPException(status_code=404, detail="DMN definition not found")
    return defn


@router.put("/{definition_id}", response_model=DmnDetailOut)
async def update_dmn_definition(
    definition_id: uuid.UUID,
    body: DmnUpdate,
    user: RequiresDeveloper,
    db: AsyncSession = Depends(get_db),
):
    defn = await db.get(WorkflowDefinition, definition_id)
    if not defn or defn.definition_type != "dmn":
        raise HTTPException(status_code=404, detail="DMN definition not found")
    if not defn.is_active:
        raise HTTPException(status_code=409, detail="Cannot update inactive definition")

    if body.name is not None:
        defn.name = body.name
    if body.description is not None:
        defn.description = body.description
    if body.xml_content is not None:
        valid, err = validate_dmn(body.xml_content)
        if not valid:
            raise HTTPException(status_code=422, detail=f"Invalid DMN: {err}")
        defn.xml_content = body.xml_content
        defn.xml_hash = sha256_xml(body.xml_content)
        defn.dmn_id = extract_dmn_id(body.xml_content)
        defn.version += 1

    defn.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(defn)
    return defn


@router.delete("/{definition_id}", status_code=204)
async def delete_dmn_definition(
    definition_id: uuid.UUID,
    user: Annotated[UserContext, Depends(require_roles("gxp-admin"))],
    db: AsyncSession = Depends(get_db),
):
    defn = await db.get(WorkflowDefinition, definition_id)
    if not defn or defn.definition_type != "dmn":
        raise HTTPException(status_code=404, detail="DMN definition not found")
    defn.is_active = False
    defn.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()


@router.post("/{definition_id}/evaluate", response_model=EvaluateResponse)
async def evaluate_dmn_definition(
    definition_id: uuid.UUID,
    body: EvaluateRequest,
    user: RequiresDeveloper,
    db: AsyncSession = Depends(get_db),
):
    """Ad-hoc evaluate a DMN table against sample inputs — for developer testing."""
    defn = await db.get(WorkflowDefinition, definition_id)
    if not defn or defn.definition_type != "dmn":
        raise HTTPException(status_code=404, detail="DMN definition not found")

    try:
        output = evaluate_dmn(defn.xml_content, body.input_data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return EvaluateResponse(output=output)
