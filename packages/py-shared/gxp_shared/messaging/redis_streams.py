"""Base helpers for Redis Streams producers and consumers."""
from __future__ import annotations

import redis.asyncio as aioredis


async def xadd(redis_url: str, stream: str, fields: dict) -> str:
    r = aioredis.from_url(redis_url, decode_responses=True)
    return await r.xadd(stream, fields)


async def create_consumer_group(redis_url: str, stream: str, group: str) -> None:
    r = aioredis.from_url(redis_url, decode_responses=True)
    try:
        await r.xgroup_create(stream, group, id="0", mkstream=True)
    except Exception:
        pass  # group already exists
