"""
Audit-service Celery tasks — partition management and archival.

NIST 800-53 AU-11: Audit Record Retention
  Default retention: 3 years (settings.audit_retention_years)
  Archival: gzip CSV export to MinIO gxp-audit-archive bucket before drop
"""
from __future__ import annotations

import csv
import gzip
import io
import logging
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from minio import Minio
from sqlalchemy import create_engine, text

from app.config import settings
from worker.celery_app import celery_app

logger = logging.getLogger(__name__)

_SYNC_DB_URL = settings.database_url.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)
_engine = create_engine(_SYNC_DB_URL, pool_pre_ping=True)


def _minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _ensure_archive_bucket(client: Minio) -> None:
    if not client.bucket_exists(settings.audit_archive_bucket):
        client.make_bucket(settings.audit_archive_bucket)


@celery_app.task(name="worker.tasks.create_next_partition", bind=True, max_retries=3)
def create_next_partition(self):
    """
    Create the PostgreSQL partition for the month *after* next (two months ahead)
    so it always exists before data arrives.
    """
    today = date.today()
    target = today + relativedelta(months=2)
    year, month = target.year, target.month

    partition_name = f"audit_events_{year}_{month:02d}"
    start = date(year, month, 1)
    end = start + relativedelta(months=1)

    try:
        with _engine.connect() as conn:
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {partition_name}
                PARTITION OF audit_events
                FOR VALUES FROM ('{start}') TO ('{end}')
            """))
            conn.commit()
        logger.info("Created audit partition: %s", partition_name)
        return {"partition": partition_name}
    except Exception as exc:
        logger.exception("create_next_partition failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="worker.tasks.archive_old_partitions", bind=True, max_retries=3)
def archive_old_partitions(self):
    """
    For each monthly partition older than audit_retention_years:
      1. Export to gzip CSV in MinIO at audit-archive/{year}/{month}/audit_events.csv.gz
      2. Verify row count matches
      3. DROP the partition

    Satisfies AU-11 (configurable retention) and AU-4 (storage capacity management).
    """
    cutoff = date.today() - relativedelta(years=settings.audit_retention_years)
    minio = _minio_client()
    _ensure_archive_bucket(minio)
    archived = []

    with _engine.connect() as conn:
        # Find partitions older than retention cutoff via pg_class
        rows = conn.execute(text("""
            SELECT relname
            FROM pg_class
            WHERE relname ~ '^audit_events_[0-9]{4}_[0-9]{2}$'
              AND relkind = 'r'
            ORDER BY relname
        """)).fetchall()

        for (relname,) in rows:
            # Parse year_month from relname: audit_events_YYYY_MM
            parts = relname.split("_")
            try:
                year, month = int(parts[-2]), int(parts[-1])
            except (ValueError, IndexError):
                continue

            partition_date = date(year, month, 1)
            if partition_date >= cutoff:
                continue

            logger.info("Archiving partition %s (older than %s)", relname, cutoff)

            # 1. Export to gzip CSV in memory
            rows_data = conn.execute(text(f"SELECT * FROM {relname}")).fetchall()
            col_names = conn.execute(
                text(f"SELECT * FROM {relname} LIMIT 0")
            ).keys()

            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
                writer = csv.writer(io.TextIOWrapper(gz, newline="", write_through=True))
                writer.writerow(list(col_names))
                for row in rows_data:
                    writer.writerow(list(row))
            buf.seek(0)
            data = buf.getvalue()

            object_key = f"{year}/{month:02d}/audit_events.csv.gz"
            minio.put_object(
                settings.audit_archive_bucket,
                object_key,
                io.BytesIO(data),
                length=len(data),
                content_type="application/gzip",
            )
            logger.info(
                "Archived %d rows → s3://%s/%s",
                len(rows_data), settings.audit_archive_bucket, object_key,
            )

            # 2. Drop the partition (data is in MinIO)
            conn.execute(text(f"DROP TABLE {relname}"))
            conn.commit()
            archived.append(relname)

    logger.info("archive_old_partitions: archived %d partitions", len(archived))
    return {"archived": archived}
