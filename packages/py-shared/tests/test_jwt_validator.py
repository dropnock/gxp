"""Tests for JWT utility functions (extraction helpers, not JWKS verification)."""
from __future__ import annotations

import pytest

from gxp_shared.auth.jwt_validator import extract_roles, extract_tenant_slug


@pytest.mark.parametrize("issuer,expected", [
    ("https://keycloak.gxp.internal/realms/gxp-dot", "dot"),
    ("https://keycloak.gxp.internal/realms/gxp-doh", "doh"),
    ("https://keycloak.gxp.internal/realms/gxp-my-agency", "my-agency"),
    ("https://keycloak.gxp.internal/realms/gxp-platform", None),   # platform realm → None
    ("https://keycloak.gxp.internal/realms/other-realm", None),    # no gxp- prefix → None
    ("", None),                                                      # missing iss → None
])
def test_extract_tenant_slug(issuer, expected):
    payload = {"iss": issuer} if issuer else {}
    assert extract_tenant_slug(payload) == expected


def test_extract_tenant_slug_trailing_slash():
    payload = {"iss": "https://keycloak.gxp.internal/realms/gxp-dot/"}
    assert extract_tenant_slug(payload) == "dot"


@pytest.mark.parametrize("payload,expected", [
    ({"realm_access": {"roles": ["gxp-admin", "gxp-developer"]}}, ["gxp-admin", "gxp-developer"]),
    ({"realm_access": {"roles": []}}, []),
    ({"realm_access": {}}, []),
    ({}, []),
])
def test_extract_roles(payload, expected):
    assert extract_roles(payload) == expected
