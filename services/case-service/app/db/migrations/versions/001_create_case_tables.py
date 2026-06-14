"""create case tables

Revision ID: 001
Revises:
Create Date: 2026-06-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "case_types",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("default_workflow_id", UUID(as_uuid=True), nullable=True),
        sa.Column("schema", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "cases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_type_id", UUID(as_uuid=True), sa.ForeignKey("case_types.id"), nullable=False),
        sa.Column("case_number", sa.Text, nullable=False, unique=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(8), nullable=False, server_default="normal"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("assigned_to", sa.Text, nullable=True),
        sa.Column("org_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cases_case_type_id", "cases", ["case_type_id"])
    op.create_index("ix_cases_status", "cases", ["status"])
    op.create_index("ix_cases_assigned_to", "cases", ["assigned_to"])
    op.create_index("ix_cases_org_id", "cases", ["org_id"])

    op.create_table(
        "case_participants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="collaborator"),
        sa.Column("added_by", sa.Text, nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("case_id", "user_id", name="uq_case_participant"),
    )
    op.create_index("ix_case_participants_user_id", "case_participants", ["user_id"])

    op.create_table(
        "case_workflow_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("workflow_instance_id", UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.Text, nullable=True),
        sa.Column("linked_by", sa.Text, nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("case_id", "workflow_instance_id", name="uq_case_workflow_link"),
    )

    op.create_table(
        "case_document_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), nullable=False),
        sa.Column("linked_by", sa.Text, nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("case_id", "document_id", name="uq_case_document_link"),
    )

    op.create_table(
        "case_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("is_internal", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_case_notes_case_id", "case_notes", ["case_id"])

    op.create_table(
        "case_timeline_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.Text, nullable=False),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_case_timeline_case_id_time", "case_timeline_events", ["case_id", "occurred_at"])

    op.create_table(
        "case_counters",
        sa.Column("org_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("year", sa.Integer, primary_key=True),
        sa.Column("last_seq", sa.BigInteger, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("case_counters")
    op.drop_table("case_timeline_events")
    op.drop_table("case_notes")
    op.drop_table("case_document_links")
    op.drop_table("case_workflow_links")
    op.drop_table("case_participants")
    op.drop_table("cases")
    op.drop_table("case_types")
