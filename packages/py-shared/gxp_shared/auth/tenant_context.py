"""
TenantContextMiddleware — resolves a tenant from the JWT on every request.

Resolution order:
  1. Full JWKS signature verification (per-realm client cached in jwt_validator)
  2. Extract tenant slug from iss: ".../realms/gxp-{slug}"
  3. Validate slug is active via Valkey cache (avoids DB hit per request)
  4. Store context on request.state

Services call get_db(request) which reads request.state.tenant_slug and sets
PostgreSQL search_path to t_{slug} before yielding the session.
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

import jwt as pyjwt
import redis.asyncio as aioredis
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .jwt_validator import decode_token, extract_roles, extract_tenant_slug

logger = logging.getLogger(__name__)

_EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Validates the JWT signature via per-realm JWKS, extracts tenant context,
    and confirms the tenant is active in the Valkey cache.
    Sets request.state.{tenant_slug, user_id, user_email, user_roles}.
    """

    def __init__(self, app, valkey_url: str, jwt_audience: str = "account") -> None:
        super().__init__(app)
        self._valkey_url = valkey_url
        self._jwt_audience = jwt_audience
        self._redis: aioredis.Redis | None = None

    def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(self._valkey_url, decode_responses=True)
        return self._redis

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return await call_next(request)

        token = auth[7:]
        try:
            payload = decode_token(token, expected_audience=self._jwt_audience)
        except pyjwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except pyjwt.InvalidAudienceError:
            raise HTTPException(status_code=401, detail="Invalid token audience")
        except pyjwt.PyJWKClientConnectionError as exc:
            # JWKS endpoint unreachable — log and fail closed
            logger.error("JWKS fetch failed for token: %s", exc)
            raise HTTPException(status_code=503, detail="Identity provider temporarily unavailable")
        except (pyjwt.DecodeError, pyjwt.InvalidTokenError) as exc:
            raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

        tenant_slug = extract_tenant_slug(payload)

        if tenant_slug:
            status = await self._get_redis().hget(f"gxp:tenant:{tenant_slug}", "status")
            if status != "active":
                raise HTTPException(status_code=403, detail=f"Tenant '{tenant_slug}' is not active")
            request.state.tenant_slug = tenant_slug
        else:
            # Platform admin realm (gxp-platform) — no per-tenant context
            request.state.tenant_slug = None

        request.state.user_id = payload.get("sub")
        request.state.user_email = payload.get("email", "")
        request.state.user_roles = extract_roles(payload)

        return await call_next(request)


def _slug_from_issuer(issuer: str) -> str | None:
    """
    Extract tenant slug from a Keycloak issuer URL.
    ".../realms/gxp-dot"     → "dot"
    ".../realms/gxp-platform" → None
    """
    if not issuer:
        return None
    realm = issuer.rstrip("/").split("/")[-1]
    if realm.startswith("gxp-") and realm != "gxp-platform":
        return realm[len("gxp-"):]
    return None


def make_tenant_db_dependency(async_session_local):
    """
    Returns a FastAPI dependency that creates an AsyncSession and sets the
    PostgreSQL search_path to the calling tenant's schema.

    Usage in each service:
        get_db = make_tenant_db_dependency(AsyncSessionLocal)
    """
    from sqlalchemy import text

    async def get_db(request: Request):
        tenant_slug = getattr(request.state, "tenant_slug", None)
        async with async_session_local() as session:
            if tenant_slug:
                await session.execute(text(f'SET search_path TO "t_{tenant_slug}", public'))
            yield session

    return get_db
