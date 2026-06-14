"""
Case service data models.

CaseType        — configurable case category (permit, investigation, benefits claim, etc.)
Case            — the core case entity; status machine; metadata validated against type schema
CaseParticipant — user roles on a specific case (owner/collaborator/observer/subject)
CaseWorkflowLink — soft link to a workflow instance in workflow-service
CaseDocumentLink — soft link to a document in document-service
CaseNote        — internal or external notes on a case
CaseTimelineEvent — append-only audit trail of all case activity
CaseCounter     — per-(org, year) counter for human-readable case numbers
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class CaseType(Base):
    __tablename__ = "case_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Optional default BPMN definition to auto-start on case creation
    default_workflow_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # JSON Schema for metadata fields (validated on case create/update)
    schema: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    cases: Mapped[list[Case]] = relationship("Case", back_populates="case_type")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("case_types.id"), nullable=False)
    # Human-readable: CASE-2026-00001
    case_number: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    # open | pending | on_hold | closed | archived
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    # low | normal | high | urgent
    priority: Mapped[str] = mapped_column(String(8), nullable=False, default="normal")
    # Type-specific fields (validated against case_types.schema)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    assigned_to: Mapped[str | None] = mapped_column(Text, nullable=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    case_type: Mapped[CaseType] = relationship("CaseType", back_populates="cases")
    participants: Mapped[list[CaseParticipant]] = relationship("CaseParticipant", back_populates="case", cascade="all, delete-orphan")
    workflow_links: Mapped[list[CaseWorkflowLink]] = relationship("CaseWorkflowLink", back_populates="case", cascade="all, delete-orphan")
    document_links: Mapped[list[CaseDocumentLink]] = relationship("CaseDocumentLink", back_populates="case", cascade="all, delete-orphan")
    notes: Mapped[list[CaseNote]] = relationship("CaseNote", back_populates="case", cascade="all, delete-orphan")
    timeline: Mapped[list[CaseTimelineEvent]] = relationship("CaseTimelineEvent", back_populates="case", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_cases_case_type_id", "case_type_id"),
        Index("ix_cases_status", "status"),
        Index("ix_cases_assigned_to", "assigned_to"),
        Index("ix_cases_org_id", "org_id"),
    )


class CaseParticipant(Base):
    __tablename__ = "case_participants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    # owner | collaborator | observer | subject
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="collaborator")
    added_by: Mapped[str] = mapped_column(Text, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    case: Mapped[Case] = relationship("Case", back_populates="participants")

    __table_args__ = (
        UniqueConstraint("case_id", "user_id", name="uq_case_participant"),
        Index("ix_case_participants_user_id", "user_id"),
    )


class CaseWorkflowLink(Base):
    __tablename__ = "case_workflow_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    # FK into workflow-service's workflow_instances table (cross-service reference by ID only)
    workflow_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_by: Mapped[str] = mapped_column(Text, nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    case: Mapped[Case] = relationship("Case", back_populates="workflow_links")

    __table_args__ = (
        UniqueConstraint("case_id", "workflow_instance_id", name="uq_case_workflow_link"),
    )


class CaseDocumentLink(Base):
    __tablename__ = "case_document_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    # FK into document-service's documents table (cross-service reference by ID only)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    linked_by: Mapped[str] = mapped_column(Text, nullable=False)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    case: Mapped[Case] = relationship("Case", back_populates="document_links")

    __table_args__ = (
        UniqueConstraint("case_id", "document_id", name="uq_case_document_link"),
    )


class CaseNote(Base):
    __tablename__ = "case_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    case: Mapped[Case] = relationship("Case", back_populates="notes")

    __table_args__ = (
        Index("ix_case_notes_case_id", "case_id"),
    )


class CaseTimelineEvent(Base):
    """Append-only audit trail. Never updated or deleted after creation."""
    __tablename__ = "case_timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    # status_change | note_added | document_linked | workflow_started | workflow_completed
    # task_assigned | participant_added | participant_removed
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str] = mapped_column(Text, nullable=False)
    # Event-specific payload
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    case: Mapped[Case] = relationship("Case", back_populates="timeline")

    __table_args__ = (
        Index("ix_case_timeline_case_id_time", "case_id", "occurred_at"),
    )


class CaseCounter(Base):
    """Per-(org_id, year) counter for generating human-readable case numbers."""
    __tablename__ = "case_counters"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_seq: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
