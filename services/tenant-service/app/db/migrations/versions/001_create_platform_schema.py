"""Create platform schema with tenants, cross_tenant_grants, catalog_templates

Revision ID: 001
Revises:
Create Date: 2026-06-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # platform schema is created in env.py before migrations run

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(63), nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("keycloak_realm", sa.Text, nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
        sa.UniqueConstraint("keycloak_realm", name="uq_tenants_keycloak_realm"),
        sa.CheckConstraint("status IN ('active','suspended','deprovisioning')", name="ck_tenants_status"),
        schema="platform",
    )

    op.create_table(
        "cross_tenant_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("requesting_tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform.tenants.id"), nullable=False),
        sa.Column("granting_tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform.tenants.id"), nullable=False),
        sa.Column("resource_type", sa.Text, nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permissions", postgresql.ARRAY(sa.Text), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending','approved','revoked','expired')", name="ck_grants_status"),
        schema="platform",
    )
    op.create_index("ix_cross_tenant_grants_resource", "cross_tenant_grants", ["resource_type", "resource_id"], schema="platform")
    op.create_index("ix_cross_tenant_grants_status", "cross_tenant_grants", ["status"], schema="platform")

    op.create_table(
        "catalog_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("version", sa.String(20), nullable=False, server_default="1"),
        sa.Column("schema_json", postgresql.JSONB, nullable=False),
        sa.Column("published_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("tags", postgresql.ARRAY(sa.Text), nullable=True),
        schema="platform",
    )
    op.create_index("ix_catalog_templates_category", "catalog_templates", ["category"], schema="platform")
    op.create_index("ix_catalog_templates_active", "catalog_templates", ["is_active"], schema="platform")


def downgrade() -> None:
    op.drop_table("catalog_templates", schema="platform")
    op.drop_table("cross_tenant_grants", schema="platform")
    op.drop_table("tenants", schema="platform")
