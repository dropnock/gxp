"""
Workflow service data model.

WorkflowDefinition  — stores BPMN or DMN XML + SHA-256; versioned.
WorkflowInstance    — one running execution of a definition; SpiffWorkflow
                      serialized state stored in state_json (JSONB).
TaskInstance        — one human task within an instance; the inbox entry.
WorkflowVariable    — key/value process variables snapshot for audit/query.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 'bpmn' | 'dmn'
    definition_type: Mapped[str] = mapped_column(String(8), nullable=False, default="bpmn")
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Raw XML content
    xml_content: Mapped[str] = mapped_column(Text, nullable=False)
    # SHA-256 of xml_content for integrity checking
    xml_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # For BPMN: the process/@id attribute value (required to instantiate)
    process_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # For DMN: the decision/@id value (used to link from BPMN Business Rule Tasks)
    dmn_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(String(1), nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    instances: Mapped[list[WorkflowInstance]] = relationship("WorkflowInstance", back_populates="definition")

    __table_args__ = (
        Index("ix_wf_definitions_type", "definition_type"),
        Index("ix_wf_definitions_name", "name"),
    )


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_definitions.id"), nullable=False)
    definition_version: Mapped[int] = mapped_column(Integer, nullable=False)
    # running | waiting | completed | cancelled | error
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    # SpiffWorkflow serialized state (BpmnWorkflowSerializer.serialize_json output)
    state_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Flattened process variables for query/audit (kept in sync with state_json)
    variables: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Optional: link back to a case (populated by case-service via service-to-service)
    case_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_by: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    definition: Mapped[WorkflowDefinition] = relationship("WorkflowDefinition", back_populates="instances")
    task_instances: Mapped[list[TaskInstance]] = relationship("TaskInstance", back_populates="instance")

    __table_args__ = (
        Index("ix_wf_instances_definition_id", "definition_id"),
        Index("ix_wf_instances_status", "status"),
        Index("ix_wf_instances_case_id", "case_id"),
    )


class TaskInstance(Base):
    """A human task (UserTask in BPMN) that appears in the assignee's inbox."""
    __tablename__ = "task_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_instances.id"), nullable=False)
    # SpiffWorkflow task internal ID (UUID stored as text)
    spiff_task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    task_name: Mapped[str] = mapped_column(Text, nullable=False)
    task_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON Schema for the task form (from BPMN extension elements)
    form_schema: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # ready | claimed | completed | cancelled
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ready")
    assigned_to: Mapped[str | None] = mapped_column(Text, nullable=True)   # Keycloak user ID
    candidate_roles: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # e.g. ['gxp-approver']
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Data submitted when completing the task
    completion_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    instance: Mapped[WorkflowInstance] = relationship("WorkflowInstance", back_populates="task_instances")

    __table_args__ = (
        Index("ix_task_instances_instance_id", "instance_id"),
        Index("ix_task_instances_assigned_to", "assigned_to"),
        Index("ix_task_instances_status", "status"),
        UniqueConstraint("instance_id", "spiff_task_id", name="uq_task_spiff_id"),
    )
