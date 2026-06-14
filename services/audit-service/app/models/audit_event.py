"""
AuditEvent — append-only table partitioned by month (RANGE on event_time).

The table is owned by a dedicated DB role with INSERT-only grants so that
even a compromised application service cannot UPDATE or DELETE audit records.
Satisfies NIST 800-53 AU-9 (protection of audit information).

Partitions are created automatically by the migration or by a monthly Celery
beat job:  audit_events_YYYY_MM
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, JSON, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuditEvent(Base):
    """
    Mirrors the fields emitted by gxp_shared.audit.emitter.emit_audit_event().
    The table is PARTITIONED BY RANGE (event_time); SQLAlchemy maps to the
    parent table — PostgreSQL routes rows to child partitions transparently.
    """
    __tablename__ = "audit_events"
    # No schema prefix — each service DB uses search_path to scope to the tenant.
    # The audit service DB uses the "public" schema for its single-tenant table.

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, primary_key=True)

    service: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)

    actor_id: Mapped[str] = mapped_column(Text, nullable=False, default="")
    actor_email: Mapped[str] = mapped_column(Text, nullable=False, default="")
    actor_roles: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)

    resource_type: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    resource_id: Mapped[str] = mapped_column(Text, nullable=False, default="")

    action: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)  # success | client_error | server_error

    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, default="")
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    tenant_slug: Mapped[str | None] = mapped_column(String(64), nullable=True)

    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_audit_events_actor_id", "actor_id"),
        Index("ix_audit_events_event_time", "event_time"),
        Index("ix_audit_events_tenant_slug", "tenant_slug"),
        Index("ix_audit_events_event_type", "event_type"),
        {
            # Tell PostgreSQL this is a partitioned parent table
            "postgresql_partition_by": "RANGE (event_time)",
        },
    )
