"""Tests for AuditMiddleware path helpers and outcome mapping."""
from __future__ import annotations

import pytest

from gxp_shared.audit.middleware import _client_ip, _resource_id_from_path, _resource_type_from_path


@pytest.mark.parametrize("path,expected", [
    ("/api/v1/documents/abc-123", "document"),
    ("/api/v1/documents", "document"),
    ("/api/v1/cases/uuid-here", "case"),
    ("/api/v1/apps/uuid-here", "app"),
    ("/api/v1/workflows/uuid-here", "workflow"),
    ("/api/v1/tenants/uuid-here", "tenant"),
    ("/api/v1/folders/uuid-here", "folder"),
    ("/health", ""),
    ("/api/v1", ""),
])
def test_resource_type_from_path(path, expected):
    assert _resource_type_from_path(path) == expected


@pytest.mark.parametrize("path,expected", [
    ("/api/v1/documents/3fa85f64-5717-4562-b3fc-2c963f66afa6", "3fa85f64-5717-4562-b3fc-2c963f66afa6"),
    ("/api/v1/documents/not-a-uuid", ""),
    ("/api/v1/documents", ""),
    ("/api/v1/apps/00000000-0000-0000-0000-000000000001/pages", "00000000-0000-0000-0000-000000000001"),
])
def test_resource_id_from_path(path, expected):
    assert _resource_id_from_path(path) == expected


def test_client_ip_from_x_forwarded_for():
    from unittest.mock import MagicMock
    req = MagicMock()
    req.headers = {"x-forwarded-for": "1.2.3.4, 10.0.0.1"}
    req.client = None
    assert _client_ip(req) == "1.2.3.4"


def test_client_ip_from_client():
    from unittest.mock import MagicMock
    req = MagicMock()
    req.headers = {}
    req.client.host = "192.168.1.10"
    assert _client_ip(req) == "192.168.1.10"


def test_client_ip_fallback():
    from unittest.mock import MagicMock
    req = MagicMock()
    req.headers = {}
    req.client = None
    assert _client_ip(req) == ""
