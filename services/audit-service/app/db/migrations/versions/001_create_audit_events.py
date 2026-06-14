"""create audit_events partitioned table

Revision ID: 001
Revises:
Create Date: 2026-06-13

Creates the audit_events parent table partitioned RANGE by event_time,
plus initial monthly partitions for the current and next month.

The table is intentionally owned by the application role but INSERT-only;
UPDATE and DELETE are revoked to satisfy NIST 800-53 AU-9.

New monthly partitions are created by the partition_manager Celery beat task.
"""
from __future__ import annotations

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id          UUID         NOT NULL DEFAULT gen_random_uuid(),
            event_time  TIMESTAMPTZ  NOT NULL,
            service     VARCHAR(64)  NOT NULL,
            event_type  VARCHAR(128) NOT NULL,
            actor_id    TEXT         NOT NULL DEFAULT '',
            actor_email TEXT         NOT NULL DEFAULT '',
            actor_roles TEXT[]       NOT NULL DEFAULT '{}',
            resource_type VARCHAR(128) NOT NULL DEFAULT '',
            resource_id   TEXT         NOT NULL DEFAULT '',
            action      TEXT         NOT NULL,
            outcome     VARCHAR(32)  NOT NULL,
            ip_address  VARCHAR(45)  NOT NULL DEFAULT '',
            request_id  VARCHAR(64)  NOT NULL DEFAULT '',
            tenant_slug VARCHAR(64),
            metadata    JSONB        NOT NULL DEFAULT '{}',
            PRIMARY KEY (id, event_time)
        ) PARTITION BY RANGE (event_time)
    """)

    # Indexes on the parent table propagate to all current + future partitions
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_events_actor_id   ON audit_events (actor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_events_event_time  ON audit_events (event_time)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_events_tenant_slug ON audit_events (tenant_slug)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_events_event_type  ON audit_events (event_type)")

    # Revoke destructive permissions — the app role can INSERT but never UPDATE/DELETE
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit_events FROM PUBLIC")

    # Create initial partitions for the current and next two months
    now = datetime.now(tz=timezone.utc)
    _create_partition(now.year, now.month)
    next_month = (now.month % 12) + 1
    next_year = now.year + (1 if now.month == 12 else 0)
    _create_partition(next_year, next_month)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_events CASCADE")


def _create_partition(year: int, month: int) -> None:
    start = f"{year}-{month:02d}-01"
    end_month = (month % 12) + 1
    end_year = year + (1 if month == 12 else 0)
    end = f"{end_year}-{end_month:02d}-01"
    partition_name = f"audit_events_{year}_{month:02d}"
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {partition_name}
            PARTITION OF audit_events
            FOR VALUES FROM ('{start}') TO ('{end}')
    """)
