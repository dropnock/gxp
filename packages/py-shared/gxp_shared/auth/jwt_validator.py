"""
Validates Keycloak-issued JWTs offline using per-realm cached JWKS.

Supports multiple realms (multi-tenant): the JWKS URL is derived from the
JWT's own `iss` claim, so new tenant realms are handled automatically
without any configuration change.

Never calls Keycloak at request time — critical for air-gap resilience.
JWKS clients are refreshed every hour.

KEYCLOAK_INTERNAL_URL (optional env var): when set, the scheme+host of the
JWKS fetch URL is rewritten to this base (e.g. http://keycloak:8080). The
realm path from the iss claim is preserved. Use this when services run
behind a reverse proxy with a self-signed cert — the public iss URL is kept
for JWT validation while the JWKS fetch uses the trusted internal endpoint.
"""
from __future__ import annotations

import os
import time
from urllib.parse import urlparse, urlunparse
from typing import Any

import jwt as pyjwt
from jwt import PyJWKClient

_JWKS_TTL = 3600  # seconds between JWKS refreshes

# { issuer_url: (PyJWKClient, fetched_at_timestamp) }
_clients: dict[str, tuple[PyJWKClient, float]] = {}

# When set, JWKS fetches use this base URL instead of the public iss hostname.
# Allows services to reach Keycloak internally without trusting the TLS cert.
_KEYCLOAK_INTERNAL_URL: str | None = os.environ.get("KEYCLOAK_INTERNAL_URL") or os.environ.get("KEYCLOAK_URL")


def _jwks_uri_for_issuer(issuer: str) -> str:
    """
    Build the JWKS endpoint URL for a given issuer.
    If KEYCLOAK_INTERNAL_URL / KEYCLOAK_URL is set, the scheme and host are
    replaced with the internal base so that self-signed certs are bypassed
    while the realm path (and the iss claim used for validation) are unchanged.
    """
    certs_path = f"{issuer.rstrip('/')}/protocol/openid-connect/certs"
    if _KEYCLOAK_INTERNAL_URL:
        internal = urlparse(_KEYCLOAK_INTERNAL_URL)
        public = urlparse(certs_path)
        certs_path = urlunparse(public._replace(scheme=internal.scheme, netloc=internal.netloc))
    return certs_path


def _get_jwks_client(issuer: str) -> PyJWKClient:
    """Return a cached PyJWKClient for the given Keycloak realm issuer URL."""
    now = time.monotonic()
    entry = _clients.get(issuer)
    if entry is None or (now - entry[1]) > _JWKS_TTL:
        jwks_uri = _jwks_uri_for_issuer(issuer)
        client = PyJWKClient(jwks_uri, cache_keys=True)
        _clients[issuer] = (client, now)
    return _clients[issuer][0]


def decode_token(token: str, expected_audience: str = "account") -> dict[str, Any]:
    """
    Fully verify a Keycloak JWT: signature, expiry, issuer, audience.
    Derives the JWKS endpoint from the token's own iss claim.
    Raises jwt.exceptions.* on any validation failure.
    """
    # Unverified decode to extract issuer only — the full decode below re-validates
    unverified = pyjwt.decode(token, options={"verify_signature": False})
    issuer: str = unverified.get("iss", "")
    if not issuer:
        raise pyjwt.InvalidTokenError("JWT missing iss claim")

    client = _get_jwks_client(issuer)
    signing_key = client.get_signing_key_from_jwt(token)

    return pyjwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=expected_audience,
        issuer=issuer,
        options={"verify_exp": True},
    )


def decode_token_unverified(token: str) -> dict[str, Any]:
    """Decode without signature check — for use when Traefik has already verified."""
    return pyjwt.decode(token, options={"verify_signature": False})


def extract_roles(payload: dict[str, Any]) -> list[str]:
    return payload.get("realm_access", {}).get("roles", [])


def extract_tenant_slug(payload: dict[str, Any]) -> str | None:
    """Extract tenant slug from the realm name embedded in the iss claim."""
    issuer: str = payload.get("iss", "")
    realm = issuer.rstrip("/").split("/")[-1]
    if realm.startswith("gxp-") and realm != "gxp-platform":
        return realm[len("gxp-"):]
    return None
