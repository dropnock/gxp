"""
ServiceTokenManager — obtains and caches OAuth2 client_credentials tokens
for service-to-service calls within a Keycloak realm.

One token is maintained per (client_id, realm) pair. Tokens are refreshed
60 seconds before expiry to avoid mid-request expiry races.

Usage:
    manager = ServiceTokenManager(keycloak_base_url="https://keycloak.gxp.internal")
    token = await manager.get_token(
        realm="gxp-dot",
        client_id="gxp-document-service",
        client_secret=settings.doc_service_client_secret,
    )
    headers = {"Authorization": f"Bearer {token}"}
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import httpx

_REFRESH_BEFORE_EXPIRY = 60  # seconds


@dataclass
class _CachedToken:
    access_token: str
    expires_at: float  # monotonic timestamp


class ServiceTokenManager:
    """
    Thread-safe token cache with automatic pre-expiry refresh.
    Designed as a singleton per process — instantiate once and share.
    """

    def __init__(self, keycloak_base_url: str) -> None:
        self._base = keycloak_base_url.rstrip("/")
        self._cache: dict[str, _CachedToken] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _cache_key(self, realm: str, client_id: str) -> str:
        return f"{realm}:{client_id}"

    def _token_url(self, realm: str) -> str:
        return f"{self._base}/realms/{realm}/protocol/openid-connect/token"

    async def get_token(self, realm: str, client_id: str, client_secret: str) -> str:
        """Return a valid access token, fetching a new one if needed."""
        key = self._cache_key(realm, client_id)

        # Fast path: return cached token if still valid
        cached = self._cache.get(key)
        if cached and time.monotonic() < cached.expires_at:
            return cached.access_token

        # Slow path: acquire per-key lock to prevent thundering herd
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        async with self._locks[key]:
            # Re-check after acquiring lock
            cached = self._cache.get(key)
            if cached and time.monotonic() < cached.expires_at:
                return cached.access_token

            token_data = await self._fetch_token(realm, client_id, client_secret)
            expires_in: int = token_data.get("expires_in", 300)
            self._cache[key] = _CachedToken(
                access_token=token_data["access_token"],
                expires_at=time.monotonic() + expires_in - _REFRESH_BEFORE_EXPIRY,
            )
            return self._cache[key].access_token

    async def _fetch_token(self, realm: str, client_id: str, client_secret: str) -> dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self._token_url(realm),
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()

    def invalidate(self, realm: str, client_id: str) -> None:
        """Force a token refresh on the next get_token() call."""
        self._cache.pop(self._cache_key(realm, client_id), None)
