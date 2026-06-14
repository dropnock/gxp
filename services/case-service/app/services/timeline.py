"""
Redis Streams consumer that auto-appends case timeline events.

Subscribes to the 'audit:events' stream (published by all GXP services via
gxp_shared.audit.emitter).  Filters for workflow and document events on
resources that are linked to cases, then creates CaseTimelineEvent rows.

Runs as a background asyncio task started in the FastAPI lifespan.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.case import CaseTimelineEvent, CaseWorkflowLink, CaseDocumentLink

logger = logging.getLogger(__name__)

_STREAM_KEY = "audit:events"
_GROUP = "case-service"
_CONSUMER = "case-timeline-0"

# Event types we care about and the timeline event type they map to
_WORKFLOW_EVENTS = {
    "workflow.step_executed": "workflow_advanced",
    "workflow.task_completed": "task_completed",
}
_DOCUMENT_EVENTS = {
    "document.uploaded": "document_uploaded",
    "document.scan_passed": "document_scan_passed",
    "document.quarantined": "document_quarantined",
}


async def _get_session_factory():
    engine = create_async_engine(settings.database_url, echo=False)
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def run_timeline_consumer(shutdown_event: asyncio.Event) -> None:
    """
    Long-running coroutine.  Reads from audit:events stream and creates
    CaseTimelineEvent rows for workflow/document events on linked resources.
    """
    session_factory = await _get_session_factory()
    r = aioredis.from_url(settings.valkey_url, decode_responses=True)

    # Ensure consumer group exists
    try:
        await r.xgroup_create(_STREAM_KEY, _GROUP, id="$", mkstream=True)
    except Exception:
        pass  # group already exists

    logger.info("Case timeline consumer started")

    while not shutdown_event.is_set():
        try:
            messages = await r.xreadgroup(
                _GROUP, _CONSUMER, {_STREAM_KEY: ">"}, count=50, block=2000,
            )
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Stream read error: %s", exc)
            await asyncio.sleep(2)
            continue

        if not messages:
            continue

        stream_name, entries = messages[0]
        ack_ids = []

        async with session_factory() as db:
            for entry_id, fields in entries:
                try:
                    await _process_event(fields, db)
                    ack_ids.append(entry_id)
                except Exception as exc:
                    logger.error("Timeline event processing error: %s", exc)
                    # Don't ACK — will be retried

            if ack_ids:
                try:
                    await db.commit()
                    await r.xack(_STREAM_KEY, _GROUP, *ack_ids)
                except Exception as exc:
                    logger.error("Timeline commit/ack error: %s", exc)
                    await db.rollback()

    await r.aclose()
    logger.info("Case timeline consumer stopped")


async def _process_event(fields: dict, db: AsyncSession) -> None:
    service = fields.get("service", "")
    event_type = fields.get("event_type", "")
    resource_type = fields.get("resource_type", "")
    resource_id = fields.get("resource_id", "")
    actor_id = fields.get("actor_id", "system")
    metadata = {}
    if fields.get("metadata"):
        try:
            metadata = json.loads(fields["metadata"])
        except Exception:
            pass

    case_id: uuid.UUID | None = None
    timeline_event_type: str | None = None

    # Workflow events
    if service == "workflow-service" and event_type in _WORKFLOW_EVENTS:
        try:
            instance_id = uuid.UUID(resource_id)
        except ValueError:
            return
        result = await db.execute(
            select(CaseWorkflowLink.case_id).where(
                CaseWorkflowLink.workflow_instance_id == instance_id
            )
        )
        row = result.first()
        if row:
            case_id = row.case_id
            timeline_event_type = _WORKFLOW_EVENTS[event_type]
            metadata["workflow_instance_id"] = resource_id

    # Document events
    elif service == "document-service" and event_type in _DOCUMENT_EVENTS:
        try:
            doc_id = uuid.UUID(resource_id)
        except ValueError:
            return
        result = await db.execute(
            select(CaseDocumentLink.case_id).where(
                CaseDocumentLink.document_id == doc_id
            )
        )
        row = result.first()
        if row:
            case_id = row.case_id
            timeline_event_type = _DOCUMENT_EVENTS[event_type]
            metadata["document_id"] = resource_id

    if case_id and timeline_event_type:
        # We need to set search_path so the INSERT targets the right tenant schema.
        # The tenant slug is in the audit metadata.
        tenant_slug = metadata.get("tenant_slug")
        if tenant_slug:
            await db.execute(
                # pylint: disable=consider-using-f-string
                __import__("sqlalchemy").text(f'SET search_path TO "t_{tenant_slug}", public')
            )

        event = CaseTimelineEvent(
            id=uuid.uuid4(),
            case_id=case_id,
            event_type=timeline_event_type,
            actor_id=actor_id,
            metadata_=metadata,
            occurred_at=datetime.now(tz=timezone.utc),
        )
        db.add(event)
