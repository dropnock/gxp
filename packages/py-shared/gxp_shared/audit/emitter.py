"""
Emits structured audit events to Redis Streams asynchronously.
Events persist to disk even if the audit service is temporarily unavailable.
"""
from __future__ import annotations

import json
import time
from typing import Any

import redis.asyncio as aioredis

_redis: aioredis.Redis | None = None


def _get_redis(url: str) -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(url, decode_responses=True)
    return _redis


async def emit_audit_event(
    *,
    redis_url: str,
    service: str,
    event_type: str,
    actor_id: str,
    actor_email: str = "",
    actor_roles: list[str] | None = None,
    resource_type: str = "",
    resource_id: str = "",
    action: str,
    outcome: str,
    ip_address: str = "",
    request_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    r = _get_redis(redis_url)
    event = {
        "service": service,
        "event_type": event_type,
        "actor_id": actor_id,
        "actor_email": actor_email,
        "actor_roles": json.dumps(actor_roles or []),
        "resource_type": resource_type,
        "resource_id": resource_id,
        "action": action,
        "outcome": outcome,
        "ip_address": ip_address,
        "request_id": request_id,
        "metadata": json.dumps(metadata or {}),
        "event_time": str(time.time()),
    }
    await r.xadd("audit:events", event)
