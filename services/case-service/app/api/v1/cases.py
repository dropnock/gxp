"""
Case CRUD and all sub-resources:
  participants, notes, workflow links, document links, timeline, start-workflow.

Access control:
  - List/Get: participant only (admin bypasses)
  - Create/Update: participant with owner/collaborator role (admin bypasses)
  - Admin (gxp-admin) role bypasses all participant checks

Case number: CASE-{YEAR}-{SEQ:05d}, generated atomically per (org_id, year).
org_id is taken from the requesting user's tenant (user_id's first org assignment).
For simplicity in the MVP, org_id == a deterministic UUID derived from the tenant slug.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.session import get_db
from app.models.case import (
    Case, CaseDocumentLink, CaseNote, CaseParticipant,
    CaseTimelineEvent, CaseWorkflowLink,
)
from app.services.case_numbers import next_case_number
from app.services.permissions import assert_can_read, assert_can_write, get_case_or_404
from gxp_shared.auth.dependencies import UserContext, require_roles

router = APIRouter()

RequiresUser = Annotated[UserContext, Depends(require_roles(
    "gxp-user", "gxp-developer", "gxp-admin",
    "gxp-case-worker", "gxp-case-manager", "gxp-approver",
))]
RequiresAdmin = Annotated[UserContext, Depends(require_roles("gxp-admin", "gxp-case-manager"))]


def _org_id_from_tenant(tenant_slug: str | None) -> uuid.UUID:
    """Deterministic org UUID from tenant slug. Replace with a real lookup in production."""
    if not tenant_slug:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"gxp.{tenant_slug}.org")


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class CaseCreate(BaseModel):
    case_type_id: uuid.UUID
    title: str
    priority: str = "normal"
    metadata: dict[str, Any] = {}
    assigned_to: str | None = None


class CaseUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    priority: str | None = None
    metadata: dict[str, Any] | None = None
    assigned_to: str | None = None


class ParticipantAdd(BaseModel):
    user_id: str
    role: str = "collaborator"


class NoteCreate(BaseModel):
    body: str
    is_internal: bool = True


class NoteUpdate(BaseModel):
    body: str | None = None
    is_internal: bool | None = None


class WorkflowLinkCreate(BaseModel):
    workflow_instance_id: uuid.UUID
    label: str | None = None


class DocumentLinkCreate(BaseModel):
    document_id: uuid.UUID


class StartWorkflowRequest(BaseModel):
    definition_id: uuid.UUID
    initial_variables: dict[str, Any] = {}
    label: str | None = None


class ParticipantOut(BaseModel):
    id: uuid.UUID; case_id: uuid.UUID; user_id: str; role: str; added_by: str; added_at: datetime
    model_config = {"from_attributes": True}


class NoteOut(BaseModel):
    id: uuid.UUID; case_id: uuid.UUID; body: str; is_internal: bool
    created_by: str; created_at: datetime; updated_at: datetime
    model_config = {"from_attributes": True}


class WorkflowLinkOut(BaseModel):
    id: uuid.UUID; case_id: uuid.UUID; workflow_instance_id: uuid.UUID
    label: str | None; linked_by: str; linked_at: datetime
    model_config = {"from_attributes": True}


class DocumentLinkOut(BaseModel):
    id: uuid.UUID; case_id: uuid.UUID; document_id: uuid.UUID
    linked_by: str; linked_at: datetime
    model_config = {"from_attributes": True}


class TimelineEventOut(BaseModel):
    id: uuid.UUID; case_id: uuid.UUID; event_type: str; actor_id: str
    metadata: dict; occurred_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_event(cls, e: CaseTimelineEvent) -> "TimelineEventOut":
        return cls(
            id=e.id, case_id=e.case_id, event_type=e.event_type,
            actor_id=e.actor_id, metadata=e.metadata_, occurred_at=e.occurred_at,
        )


class CaseOut(BaseModel):
    id: uuid.UUID; case_type_id: uuid.UUID; case_number: str; title: str
    status: str; priority: str; metadata: dict; assigned_to: str | None
    org_id: uuid.UUID; created_by: str; created_at: datetime
    updated_at: datetime; closed_at: datetime | None
    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, c: Case) -> "CaseOut":
        return cls(
            id=c.id, case_type_id=c.case_type_id, case_number=c.case_number,
            title=c.title, status=c.status, priority=c.priority,
            metadata=c.metadata_, assigned_to=c.assigned_to, org_id=c.org_id,
            created_by=c.created_by, created_at=c.created_at,
            updated_at=c.updated_at, closed_at=c.closed_at,
        )


class CaseDetailOut(CaseOut):
    participants: list[ParticipantOut]
    workflow_links: list[WorkflowLinkOut]
    document_links: list[DocumentLinkOut]


# ── Helper ────────────────────────────────────────────────────────────────────

async def _append_timeline(
    db: AsyncSession,
    case_id: uuid.UUID,
    event_type: str,
    actor_id: str,
    metadata: dict,
) -> None:
    db.add(CaseTimelineEvent(
        id=uuid.uuid4(),
        case_id=case_id,
        event_type=event_type,
        actor_id=actor_id,
        metadata_=metadata,
        occurred_at=datetime.now(tz=timezone.utc),
    ))


# ── Cases ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=CaseOut, status_code=201)
async def create_case(
    body: CaseCreate,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    if body.priority not in ("low", "normal", "high", "urgent"):
        raise HTTPException(status_code=422, detail="Invalid priority")

    org_id = _org_id_from_tenant(user.tenant_slug)
    case_number = await next_case_number(org_id, db)
    now = datetime.now(tz=timezone.utc)

    case = Case(
        id=uuid.uuid4(),
        case_type_id=body.case_type_id,
        case_number=case_number,
        title=body.title,
        status="open",
        priority=body.priority,
        metadata_=body.metadata,
        assigned_to=body.assigned_to or user.user_id,
        org_id=org_id,
        created_by=user.user_id,
        created_at=now,
        updated_at=now,
    )
    db.add(case)
    await db.flush()

    # Creator is the initial owner-participant
    db.add(CaseParticipant(
        id=uuid.uuid4(), case_id=case.id, user_id=user.user_id,
        role="owner", added_by=user.user_id, added_at=now,
    ))

    await _append_timeline(db, case.id, "case_created", user.user_id, {"title": body.title})
    await db.commit()
    await db.refresh(case)
    return CaseOut.from_model(case)


@router.get("", response_model=list[CaseOut])
async def list_cases(
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    assigned_to: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    stmt = select(Case)
    if status:
        stmt = stmt.where(Case.status == status)
    if priority:
        stmt = stmt.where(Case.priority == priority)
    if assigned_to:
        stmt = stmt.where(Case.assigned_to == assigned_to)

    # Non-admins only see cases they participate in
    if "gxp-admin" not in user.roles:
        from sqlalchemy import exists
        stmt = stmt.where(
            exists(
                select(CaseParticipant.id).where(
                    CaseParticipant.case_id == Case.id,
                    CaseParticipant.user_id == user.user_id,
                )
            )
        )

    stmt = stmt.order_by(Case.created_at.desc()).offset(skip).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [CaseOut.from_model(c) for c in rows]


@router.get("/{case_id}", response_model=CaseDetailOut)
async def get_case(
    case_id: uuid.UUID,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Case)
        .options(
            selectinload(Case.participants),
            selectinload(Case.workflow_links),
            selectinload(Case.document_links),
        )
        .where(Case.id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    await assert_can_read(case, user, db)
    base = CaseOut.from_model(case)
    return CaseDetailOut(
        **base.model_dump(),
        participants=case.participants,
        workflow_links=case.workflow_links,
        document_links=case.document_links,
    )


@router.put("/{case_id}", response_model=CaseOut)
async def update_case(
    case_id: uuid.UUID,
    body: CaseUpdate,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    case = await get_case_or_404(case_id, db)
    await assert_can_write(case, user, db)

    prev_status = case.status
    if body.title is not None: case.title = body.title
    if body.priority is not None: case.priority = body.priority
    if body.metadata is not None: case.metadata_ = body.metadata
    if body.assigned_to is not None: case.assigned_to = body.assigned_to
    if body.status is not None:
        valid = {"open", "pending", "on_hold", "closed", "archived"}
        if body.status not in valid:
            raise HTTPException(status_code=422, detail=f"Invalid status. Must be one of: {valid}")
        case.status = body.status
        if body.status == "closed" and not case.closed_at:
            case.closed_at = datetime.now(tz=timezone.utc)

    case.updated_at = datetime.now(tz=timezone.utc)

    if body.status and body.status != prev_status:
        await _append_timeline(db, case.id, "status_change", user.user_id,
                               {"from": prev_status, "to": body.status})

    await db.commit()
    await db.refresh(case)
    return CaseOut.from_model(case)


# ── Participants ──────────────────────────────────────────────────────────────

@router.get("/{case_id}/participants", response_model=list[ParticipantOut])
async def list_participants(
    case_id: uuid.UUID,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    case = await get_case_or_404(case_id, db)
    await assert_can_read(case, user, db)
    result = await db.execute(
        select(CaseParticipant).where(CaseParticipant.case_id == case_id)
    )
    return result.scalars().all()


@router.post("/{case_id}/participants", response_model=ParticipantOut, status_code=201)
async def add_participant(
    case_id: uuid.UUID,
    body: ParticipantAdd,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    if body.role not in ("owner", "collaborator", "observer", "subject"):
        raise HTTPException(status_code=422, detail="Invalid role")
    case = await get_case_or_404(case_id, db)
    await assert_can_write(case, user, db)
    now = datetime.now(tz=timezone.utc)
    p = CaseParticipant(
        id=uuid.uuid4(), case_id=case_id, user_id=body.user_id,
        role=body.role, added_by=user.user_id, added_at=now,
    )
    db.add(p)
    await _append_timeline(db, case_id, "participant_added", user.user_id,
                           {"user_id": body.user_id, "role": body.role})
    await db.commit()
    await db.refresh(p)
    return p


@router.delete("/{case_id}/participants/{user_id}", status_code=204)
async def remove_participant(
    case_id: uuid.UUID,
    user_id: str,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    case = await get_case_or_404(case_id, db)
    await assert_can_write(case, user, db)
    result = await db.execute(
        select(CaseParticipant).where(
            CaseParticipant.case_id == case_id,
            CaseParticipant.user_id == user_id,
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    await db.delete(p)
    await _append_timeline(db, case_id, "participant_removed", user.user_id, {"user_id": user_id})
    await db.commit()


# ── Notes ─────────────────────────────────────────────────────────────────────

@router.get("/{case_id}/notes", response_model=list[NoteOut])
async def list_notes(
    case_id: uuid.UUID,
    user: RequiresUser,
    include_internal: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    case = await get_case_or_404(case_id, db)
    await assert_can_read(case, user, db)

    stmt = select(CaseNote).where(CaseNote.case_id == case_id)
    is_editor = "gxp-admin" in user.roles or "gxp-case-worker" in user.roles or "gxp-case-manager" in user.roles
    if not include_internal or not is_editor:
        stmt = stmt.where(CaseNote.is_internal == False)  # noqa: E712
    stmt = stmt.order_by(CaseNote.created_at.asc())
    return (await db.execute(stmt)).scalars().all()


@router.post("/{case_id}/notes", response_model=NoteOut, status_code=201)
async def add_note(
    case_id: uuid.UUID,
    body: NoteCreate,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    case = await get_case_or_404(case_id, db)
    await assert_can_write(case, user, db)
    now = datetime.now(tz=timezone.utc)
    note = CaseNote(
        id=uuid.uuid4(), case_id=case_id, body=body.body,
        is_internal=body.is_internal, created_by=user.user_id,
        created_at=now, updated_at=now,
    )
    db.add(note)
    await _append_timeline(db, case_id, "note_added", user.user_id,
                           {"is_internal": body.is_internal})
    await db.commit()
    await db.refresh(note)
    return note


@router.put("/{case_id}/notes/{note_id}", response_model=NoteOut)
async def update_note(
    case_id: uuid.UUID,
    note_id: uuid.UUID,
    body: NoteUpdate,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    case = await get_case_or_404(case_id, db)
    await assert_can_write(case, user, db)
    note = await db.get(CaseNote, note_id)
    if not note or note.case_id != case_id:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.created_by != user.user_id and "gxp-admin" not in user.roles:
        raise HTTPException(status_code=403, detail="Can only edit your own notes")
    if body.body is not None: note.body = body.body
    if body.is_internal is not None: note.is_internal = body.is_internal
    note.updated_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(note)
    return note


# ── Workflow Links ────────────────────────────────────────────────────────────

@router.post("/{case_id}/workflow-links", response_model=WorkflowLinkOut, status_code=201)
async def link_workflow(
    case_id: uuid.UUID,
    body: WorkflowLinkCreate,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    case = await get_case_or_404(case_id, db)
    await assert_can_write(case, user, db)
    now = datetime.now(tz=timezone.utc)
    link = CaseWorkflowLink(
        id=uuid.uuid4(), case_id=case_id,
        workflow_instance_id=body.workflow_instance_id,
        label=body.label, linked_by=user.user_id, linked_at=now,
    )
    db.add(link)
    await _append_timeline(db, case_id, "workflow_linked", user.user_id,
                           {"workflow_instance_id": str(body.workflow_instance_id), "label": body.label})
    await db.commit()
    await db.refresh(link)
    return link


@router.post("/{case_id}/start-workflow", response_model=WorkflowLinkOut, status_code=202)
async def start_workflow(
    case_id: uuid.UUID,
    body: StartWorkflowRequest,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new workflow instance in workflow-service (service-to-service call),
    then link it to this case.
    """
    case = await get_case_or_404(case_id, db)
    await assert_can_write(case, user, db)

    from gxp_shared.auth.service_token import ServiceTokenManager
    token_mgr = ServiceTokenManager()
    token = await token_mgr.get_token(
        keycloak_url=settings.workflow_service_url,
        realm=user.tenant_slug or "gxp-platform",
        client_id=settings.client_id,
        client_secret=settings.client_secret,
    )

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.workflow_service_url}/api/v1/workflow/instances",
            json={
                "definition_id": str(body.definition_id),
                "initial_variables": body.initial_variables,
                "case_id": str(case_id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code not in (200, 201, 202):
            raise HTTPException(status_code=502, detail=f"Workflow service error: {resp.text}")
        instance_data = resp.json()

    now = datetime.now(tz=timezone.utc)
    link = CaseWorkflowLink(
        id=uuid.uuid4(), case_id=case_id,
        workflow_instance_id=uuid.UUID(instance_data["id"]),
        label=body.label, linked_by=user.user_id, linked_at=now,
    )
    db.add(link)
    await _append_timeline(db, case_id, "workflow_started", user.user_id,
                           {"workflow_instance_id": instance_data["id"], "definition_id": str(body.definition_id)})
    await db.commit()
    await db.refresh(link)
    return link


# ── Document Links ────────────────────────────────────────────────────────────

@router.post("/{case_id}/document-links", response_model=DocumentLinkOut, status_code=201)
async def link_document(
    case_id: uuid.UUID,
    body: DocumentLinkCreate,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
):
    case = await get_case_or_404(case_id, db)
    await assert_can_write(case, user, db)
    now = datetime.now(tz=timezone.utc)
    link = CaseDocumentLink(
        id=uuid.uuid4(), case_id=case_id,
        document_id=body.document_id,
        linked_by=user.user_id, linked_at=now,
    )
    db.add(link)
    await _append_timeline(db, case_id, "document_linked", user.user_id,
                           {"document_id": str(body.document_id)})
    await db.commit()
    await db.refresh(link)
    return link


# ── Timeline ──────────────────────────────────────────────────────────────────

@router.get("/{case_id}/timeline", response_model=list[TimelineEventOut])
async def get_timeline(
    case_id: uuid.UUID,
    user: RequiresUser,
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    case = await get_case_or_404(case_id, db)
    await assert_can_read(case, user, db)
    result = await db.execute(
        select(CaseTimelineEvent)
        .where(CaseTimelineEvent.case_id == case_id)
        .order_by(CaseTimelineEvent.occurred_at.asc())
        .offset(skip).limit(limit)
    )
    return [TimelineEventOut.from_orm_event(e) for e in result.scalars().all()]
