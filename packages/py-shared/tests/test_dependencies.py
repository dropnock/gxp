"""Tests for FastAPI auth dependency factories."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from gxp_shared.auth.dependencies import (
    UserContext,
    get_current_user,
    require_platform_admin,
    require_roles,
)


def _make_request(**state_attrs):
    req = MagicMock()
    state = MagicMock()
    for k, v in state_attrs.items():
        setattr(state, k, v)
    req.state = state
    return req


# ── get_current_user ──────────────────────────────────────────────────────────

def test_get_current_user_authenticated():
    req = _make_request(user_id="u-123", user_email="a@b.com", user_roles=["gxp-user"], tenant_slug="dot")
    user = get_current_user(req)
    assert user.user_id == "u-123"
    assert user.email == "a@b.com"
    assert user.roles == ["gxp-user"]
    assert user.tenant_slug == "dot"


def test_get_current_user_unauthenticated():
    req = _make_request(user_id=None)
    with pytest.raises(HTTPException) as exc:
        get_current_user(req)
    assert exc.value.status_code == 401


def test_get_current_user_missing_state():
    req = MagicMock()
    # getattr with default returns None for missing attributes
    del req.state.user_id
    req.state = MagicMock(spec=[])   # empty spec → getattr returns None
    with pytest.raises(HTTPException) as exc:
        get_current_user(req)
    assert exc.value.status_code == 401


# ── require_roles ─────────────────────────────────────────────────────────────

def test_require_roles_passes_when_role_present():
    user = UserContext(user_id="u1", email="x@y.com", roles=["gxp-developer"], tenant_slug="dot")
    checker = require_roles("gxp-developer", "gxp-admin")
    # Call the inner _check function directly
    result = checker.__closure__  # ensure factory created closure
    # Use the returned callable as FastAPI would (injecting user via Depends)
    inner = checker(user=user)
    assert inner == user


def test_require_roles_denied_when_no_matching_role():
    user = UserContext(user_id="u1", email="x@y.com", roles=["gxp-user"], tenant_slug="dot")
    checker = require_roles("gxp-developer", "gxp-admin")
    with pytest.raises(HTTPException) as exc:
        checker(user=user)
    assert exc.value.status_code == 403


def test_require_roles_accepts_any_of_listed():
    user = UserContext(user_id="u1", email="x@y.com", roles=["gxp-admin"], tenant_slug="dot")
    checker = require_roles("gxp-developer", "gxp-admin")
    assert checker(user=user) == user


# ── require_platform_admin ────────────────────────────────────────────────────

def test_require_platform_admin_passes():
    user = UserContext(user_id="p1", email="admin@gxp.internal", roles=["gxp-platform-admin"], tenant_slug=None)
    assert require_platform_admin(user) == user


def test_require_platform_admin_denied_for_tenant_user():
    user = UserContext(user_id="u1", email="u@dot.gov", roles=["gxp-platform-admin"], tenant_slug="dot")
    with pytest.raises(HTTPException) as exc:
        require_platform_admin(user)
    assert exc.value.status_code == 403


def test_require_platform_admin_denied_for_wrong_role():
    user = UserContext(user_id="u1", email="u@dot.gov", roles=["gxp-admin"], tenant_slug=None)
    with pytest.raises(HTTPException) as exc:
        require_platform_admin(user)
    assert exc.value.status_code == 403
