"""create workflow tables

Revision ID: 001
Revises:
Create Date: 2026-06-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("definition_type", sa.String(8), nullable=False, server_default="bpmn"),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("xml_content", sa.Text, nullable=False),
        sa.Column("xml_hash", sa.String(64), nullable=False),
        sa.Column("process_id", sa.String(256), nullable=True),
        sa.Column("dmn_id", sa.String(256), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_wf_definitions_type", "workflow_definitions", ["definition_type"])
    op.create_index("ix_wf_definitions_name", "workflow_definitions", ["name"])

    op.create_table(
        "workflow_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("definition_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workflow_definitions.id"), nullable=False),
        sa.Column("definition_version", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("state_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("variables", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_by", sa.Text, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_wf_instances_definition_id", "workflow_instances", ["definition_id"])
    op.create_index("ix_wf_instances_status", "workflow_instances", ["status"])
    op.create_index("ix_wf_instances_case_id", "workflow_instances", ["case_id"])

    op.create_table(
        "task_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("instance_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("workflow_instances.id"), nullable=False),
        sa.Column("spiff_task_id", sa.String(64), nullable=False),
        sa.Column("task_name", sa.Text, nullable=False),
        sa.Column("task_title", sa.Text, nullable=True),
        sa.Column("form_schema", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(16), nullable=False, server_default="ready"),
        sa.Column("assigned_to", sa.Text, nullable=True),
        sa.Column("candidate_roles", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.UniqueConstraint("instance_id", "spiff_task_id", name="uq_task_spiff_id"),
    )
    op.create_index("ix_task_instances_instance_id", "task_instances", ["instance_id"])
    op.create_index("ix_task_instances_assigned_to", "task_instances", ["assigned_to"])
    op.create_index("ix_task_instances_status", "task_instances", ["status"])


def downgrade() -> None:
    op.drop_table("task_instances")
    op.drop_table("workflow_instances")
    op.drop_table("workflow_definitions")
