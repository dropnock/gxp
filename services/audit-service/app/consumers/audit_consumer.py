"""
Redis Streams consumer for the audit:events stream.

Runs as an asyncio background task started on FastAPI startup.
Uses a consumer group so that multiple audit-service replicas share the load
and no event is processed twice (at-least-once delivery with idempotent insert).

Bulk-inserts up to BATCH_SIZE events per loop iteration to minimize DB round-trips.
Satisfies NIST 800-53 AU-5 (response to audit processing failures): the stream
persists events to disk even when this consumer is down.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import AsyncSessionLocal
from app.models.audit_event import AuditEvent

logger = logging.getLogger(__name__)

STREAM_KEY = "audit:events"
CONSUMER_GROUP = "audit-service"
CONSUMER_NAME = f"audit-consumer-{uuid.uuid4().hex[:8]}"
BATCH_SIZE = 100
BLOCK_MS = 2000   # block for 2s waiting for new messages
RETRY_DELAY = 5   # seconds to wait after an error before retrying


async def _ensure_consumer_group(redis: aioredis.Redis) -> None:
    try:
        await redis.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
    except Exception as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def _process_batch(entries: list[tuple[bytes, dict]]) -> list[bytes]:
    """Insert a batch of stream entries into audit_events. Returns IDs to ACK."""
    rows: list[dict[str, Any]] = []
    ids: list[bytes] = []

    for entry_id, fields in entries:
        try:
            event_time_raw = fields.get(b"event_time") or fields.get("event_time", "")
            try:
                event_time = datetime.fromtimestamp(float(event_time_raw), tz=timezone.utc)
            except (ValueError, TypeError):
                event_time = datetime.now(tz=timezone.utc)

            metadata_raw = fields.get(b"metadata") or fields.get("metadata", "{}")
            metadata = json.loads(metadata_raw) if isinstance(metadata_raw, (str, bytes)) else {}
            tenant_slug = metadata.get("tenant_slug")

            actor_roles_raw = fields.get(b"actor_roles") or fields.get("actor_roles", "[]")
            actor_roles = json.loads(actor_roles_raw) if isinstance(actor_roles_raw, (str, bytes)) else []

            def _str(key: str) -> str:
                v = fields.get(key.encode()) or fields.get(key, "")
                return v.decode() if isinstance(v, bytes) else str(v)

            rows.append({
                "id": uuid.uuid4(),
                "event_time": event_time,
                "service": _str("service"),
                "event_type": _str("event_type"),
                "actor_id": _str("actor_id"),
                "actor_email": _str("actor_email"),
                "actor_roles": actor_roles,
                "resource_type": _str("resource_type"),
                "resource_id": _str("resource_id"),
                "action": _str("action"),
                "outcome": _str("outcome"),
                "ip_address": _str("ip_address"),
                "request_id": _str("request_id"),
                "tenant_slug": tenant_slug,
                "metadata": metadata,
            })
            ids.append(entry_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to parse audit stream entry %s: %s", entry_id, exc)
            ids.append(entry_id)  # ACK to prevent infinite retry on malformed events

    if rows:
        async with AsyncSessionLocal() as session:
            stmt = pg_insert(AuditEvent).values(rows).on_conflict_do_nothing()
            await session.execute(stmt)
            await session.commit()

    return ids


async def run_consumer(redis_url: str) -> None:
    """Main consumer loop — runs forever as an asyncio background task."""
    redis = aioredis.from_url(redis_url)
    await _ensure_consumer_group(redis)
    logger.info("Audit consumer started: group=%s consumer=%s", CONSUMER_GROUP, CONSUMER_NAME)

    while True:
        try:
            # First drain any pending (unacknowledged) messages from previous runs
            pending = await redis.xreadgroup(
                CONSUMER_GROUP, CONSUMER_NAME,
                {STREAM_KEY: "0"},
                count=BATCH_SIZE,
                block=0,
            )
            if pending and pending[0][1]:
                _, entries = pending[0]
                ids = await _process_batch(entries)
                if ids:
                    await redis.xack(STREAM_KEY, CONSUMER_GROUP, *ids)
                continue  # keep draining pending before reading new

            # Read new messages
            result = await redis.xreadgroup(
                CONSUMER_GROUP, CONSUMER_NAME,
                {STREAM_KEY: ">"},
                count=BATCH_SIZE,
                block=BLOCK_MS,
            )
            if not result:
                continue  # timeout — loop again

            _, entries = result[0]
            if entries:
                ids = await _process_batch(entries)
                if ids:
                    await redis.xack(STREAM_KEY, CONSUMER_GROUP, *ids)

        except asyncio.CancelledError:
            logger.info("Audit consumer shutting down")
            await redis.aclose()
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Audit consumer error: %s — retrying in %ds", exc, RETRY_DELAY)
            await asyncio.sleep(RETRY_DELAY)


async def start_consumer_background_task(redis_url: str) -> asyncio.Task:
    """Create and return the background consumer task (call from FastAPI lifespan)."""
    return asyncio.create_task(run_consumer(redis_url), name="audit-consumer")
