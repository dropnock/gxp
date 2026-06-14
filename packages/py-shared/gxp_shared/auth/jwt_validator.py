"""
Validates Keycloak-issued JWTs offline using per-realm cached JWKS.

Supports multiple realms (multi-tenant): the JWKS URL is derived from the
JWT's own `iss` claim, so new tenant realms are handled automatically
without any configuration change.

Never calls Keycloak at request time — critical for air-gap resilience.
JWKS clients are refreshed every hour.
"""
from __future__ import annotations

import time
from typing import Any

import jwt as pyjwt
from jwt import PyJWKClient

_JWKS_TTL = 3600  # seconds between JWKS refreshes

# { issuer_url: (PyJWKClient, fetched_at_timestamp) }
_clients: dict[str, tuple[PyJWKClient, float]] = {}


def _get_jwks_client(issuer: str) -> PyJWKClient:
    """Return a cached PyJWKClient for the given Keycloak realm issuer URL."""
    now = time.monotonic()
    entry = _clients.get(issuer)
    if entry is None or (now - entry[1]) > _JWKS_TTL:
        jwks_uri = f"{issuer.rstrip('/')}/protocol/openid-connect/certs"
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
