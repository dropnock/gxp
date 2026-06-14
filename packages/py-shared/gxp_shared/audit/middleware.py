"""
AuditMiddleware — captures every HTTP request/response as an audit event
and emits it to Redis Streams via the shared emitter.

Covers NIST 800-53 AU-3 (record content) and AU-12 (audit generation).
Audit failures never block the application request — errors are logged only.

Each service registers this middleware after TenantContextMiddleware so that
request.state.{user_id, user_email, user_roles, tenant_slug} are already set.

Usage in each service's main.py:

    from gxp_shared.audit.middleware import AuditMiddleware
    app.add_middleware(
        AuditMiddleware,
        valkey_url=settings.valkey_url,
        service_name="document-service",
    )
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .emitter import emit_audit_event

logger = logging.getLogger(__name__)

# Paths that produce high-volume noise without compliance value
_SKIP_PATHS = {"/health", "/metrics", "/docs", "/openapi.json", "/redoc"}


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Emits one audit event per request: actor, resource, action, outcome, IP,
    request ID, and response status.  Missing identity fields default to empty
    strings so the event always records something useful.
    """

    def __init__(self, app, valkey_url: str, service_name: str) -> None:
        super().__init__(app)
        self._valkey_url = valkey_url
        self._service_name = service_name

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        # Make the request ID available downstream (e.g. for service-to-service calls)
        request.state.request_id = request_id

        start = time.monotonic()
        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            outcome = "success" if status_code < 400 else ("client_error" if status_code < 500 else "server_error")
            duration_ms = int((time.monotonic() - start) * 1000)

            try:
                await emit_audit_event(
                    redis_url=self._valkey_url,
                    service=self._service_name,
                    event_type="http.request",
                    actor_id=getattr(request.state, "user_id", "") or "",
                    actor_email=getattr(request.state, "user_email", "") or "",
                    actor_roles=getattr(request.state, "user_roles", []) or [],
                    resource_type=_resource_type_from_path(request.url.path),
                    resource_id=_resource_id_from_path(request.url.path),
                    action=f"{request.method} {request.url.path}",
                    outcome=outcome,
                    ip_address=_client_ip(request),
                    request_id=request_id,
                    metadata={
                        "http_status": status_code,
                        "duration_ms": duration_ms,
                        "tenant_slug": getattr(request.state, "tenant_slug", None),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                # Audit failure must never crash the application
                logger.error("Audit emit failed for %s %s: %s", request.method, request.url.path, exc)


def _client_ip(request: Request) -> str:
    """Extract real client IP, respecting Traefik's X-Forwarded-For header."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


def _resource_type_from_path(path: str) -> str:
    """
    Infer a resource type label from the API path.
    /api/v1/documents/... → "document"
    /api/v1/cases/...     → "case"
    etc.
    """
    parts = [p for p in path.split("/") if p]
    # Skip 'api' and version segment
    for i, part in enumerate(parts):
        if part.startswith("v") and part[1:].isdigit():
            if i + 1 < len(parts):
                return parts[i + 1].rstrip("s")  # strip plural 's'
    return ""


def _resource_id_from_path(path: str) -> str:
    """
    Extract a UUID-shaped path segment as the resource ID.
    /api/v1/documents/3fa85f64-... → "3fa85f64-..."
    """
    for part in path.split("/"):
        if len(part) == 36 and part.count("-") == 4:
            return part
    return ""
