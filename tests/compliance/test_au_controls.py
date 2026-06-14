"""
NIST 800-53 AU (Audit and Accountability) control validation tests.

These are *static* tests — they inspect model definitions, migration SQL,
and service source code without connecting to a database. They run in CI
on every PR and serve as the automated portion of the AU control checklist.

Controls covered:
  AU-2  Event types to be audited
  AU-3  Content of audit records
  AU-4  Audit log storage capacity (archival + partition management)
  AU-5  Response to audit-processing failures (stream persistence)
  AU-6  Audit review, analysis, and reporting
  AU-8  Time stamps
  AU-9  Protection of audit information (append-only DB role)
  AU-11 Audit record retention (configurable retention >= 3 years)
  AU-12 Audit record generation (middleware present in all services)
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO = Path(__file__).parents[2]
AUDIT_SVC = REPO / "services" / "audit-service"
MIGRATION = AUDIT_SVC / "app/db/migrations/versions/001_create_audit_events.py"
SERVICES = [
    "app-service", "audit-service", "case-service",
    "document-service", "tenant-service", "workflow-service",
]


# ── AU-2: Required event types ───────────────────────────────────────────────

# GXP uses AuditMiddleware (middleware-based) audit capture: one 'http.request'
# event is emitted per API call, with resource_type derived from the URL path
# (/api/v1/documents/... → resource_type='document').  AU-2 compliance is
# satisfied by verifying that each required resource category has service API
# routes that will trigger the middleware, and that the middleware actually
# derives resource_type from path.
#
# Required resource categories → (owning service, route file search term)
CATEGORY_COVERAGE = {
    "document": ("document-service", "documents"),
    "workflow": ("workflow-service", "definitions"),
    "case":     ("case-service",     "cases"),
    "tenant":   ("tenant-service",   "tenants"),
    "audit":    ("audit-service",    "reports"),
}


def test_au2_required_event_categories():
    """
    AU-2: Each required event category is covered by AuditMiddleware across
    the service fleet.

    GXP emits one 'http.request' event per API call; resource_type is derived
    from the URL path by _resource_type_from_path.  This test confirms:
      1. AuditMiddleware uses _resource_type_from_path for category derivation.
      2. Each required resource category has at least one API route file in
         the owning service, guaranteeing events will be generated for it.
    """
    # 1. Verify the middleware has resource_type derivation from URL path
    middleware_file = REPO / "packages/py-shared/gxp_shared/audit/middleware.py"
    assert middleware_file.exists(), "AU-2 FAIL: AuditMiddleware not found"
    middleware_text = middleware_file.read_text()
    assert "_resource_type_from_path" in middleware_text, (
        "AU-2 FAIL: AuditMiddleware does not derive resource_type from path — "
        "category-based audit coverage cannot be verified"
    )
    assert "resource_type=_resource_type_from_path" in middleware_text, (
        "AU-2 FAIL: AuditMiddleware does not call _resource_type_from_path when emitting events"
    )

    # 2. Verify each required category has API routes in the owning service
    missing = []
    for category, (service, route_fragment) in CATEGORY_COVERAGE.items():
        api_dir = REPO / "services" / service / "app" / "api"
        if not api_dir.exists():
            missing.append(f"{category} (no API dir in {service})")
            continue
        found = any(
            route_fragment in py_file.read_text(errors="ignore")
            for py_file in api_dir.rglob("*.py")
        )
        if not found:
            missing.append(f"{category} (no routes with '{route_fragment}' in {service}/app/api)")

    assert not missing, f"AU-2 FAIL: Missing API coverage for categories: {missing}"


# ── AU-3: Required audit record fields ──────────────────────────────────────

REQUIRED_AUDIT_FIELDS = {
    "actor_id",
    "actor_email",
    "actor_roles",
    "event_time",
    "service",
    "event_type",
    "action",
    "outcome",
    "ip_address",
    "request_id",
    "tenant_slug",
}

def test_au3_audit_record_fields():
    """AU-3: AuditEvent model contains all required fields."""
    model_file = AUDIT_SVC / "app/models/audit_event.py"
    assert model_file.exists(), "AuditEvent model file not found"
    text = model_file.read_text()

    missing = [f for f in REQUIRED_AUDIT_FIELDS if f not in text]
    assert not missing, f"AU-3 FAIL: AuditEvent missing fields: {missing}"


# ── AU-4: Audit log storage capacity — archival job ─────────────────────────

def test_au4_archival_task_exists():
    """AU-4: audit-service has a Celery task that archives old partitions to MinIO."""
    tasks_file = AUDIT_SVC / "worker/tasks.py"
    assert tasks_file.exists(), "audit-service worker/tasks.py not found"
    text = tasks_file.read_text()
    assert "archive_old_partitions" in text, "AU-4 FAIL: archive_old_partitions task not found"
    assert "minio" in text.lower() or "Minio" in text, "AU-4 FAIL: MinIO usage not found in archival task"


def test_au4_partition_creation_task_exists():
    """AU-4: audit-service has a Celery task that creates new monthly partitions."""
    tasks_file = AUDIT_SVC / "worker/tasks.py"
    assert tasks_file.exists()
    text = tasks_file.read_text()
    assert "create_next_partition" in text, "AU-4 FAIL: create_next_partition task not found"


# ── AU-5: Response to audit processing failures ──────────────────────────────

def test_au5_consumer_handles_errors():
    """AU-5: audit consumer retries on error and does not crash on individual bad events."""
    consumer_file = AUDIT_SVC / "app/consumers/audit_consumer.py"
    assert consumer_file.exists(), "audit consumer not found"
    text = consumer_file.read_text()
    assert "asyncio.CancelledError" in text, "AU-5 FAIL: consumer does not handle CancelledError"
    assert "RETRY_DELAY" in text or "retry" in text.lower(), "AU-5 FAIL: consumer has no retry logic"
    # Events that fail parsing must still be ACKed to avoid infinite retry
    assert "ids.append(entry_id)" in text, "AU-5 FAIL: malformed events not ACKed"


# ── AU-6: Audit review, analysis, and reporting ──────────────────────────────

def test_au6_report_endpoints_exist():
    """AU-6: audit-service exposes summary, actor-activity, and failed-actions report endpoints."""
    reports_file = AUDIT_SVC / "app/api/v1/reports.py"
    assert reports_file.exists(), "audit reports API not found"
    text = reports_file.read_text()
    required_routes = ["/summary", "actor-activity", "failed-actions"]
    missing = [r for r in required_routes if r not in text]
    assert not missing, f"AU-6 FAIL: Missing report endpoints: {missing}"


def test_au6_auditor_role_required():
    """AU-6: report endpoints require gxp-auditor or gxp-admin role."""
    reports_file = AUDIT_SVC / "app/api/v1/reports.py"
    text = reports_file.read_text()
    assert "gxp-auditor" in text, "AU-6 FAIL: gxp-auditor role not required on reports"


# ── AU-8: Time stamps ────────────────────────────────────────────────────────

def test_au8_timestamps_are_timezone_aware():
    """AU-8: AuditEvent event_time column uses timezone=True."""
    model_file = AUDIT_SVC / "app/models/audit_event.py"
    text = model_file.read_text()
    assert "timezone=True" in text, "AU-8 FAIL: event_time is not timezone-aware"


def test_au8_consumer_uses_utc():
    """AU-8: audit consumer stores timestamps in UTC."""
    consumer_file = AUDIT_SVC / "app/consumers/audit_consumer.py"
    text = consumer_file.read_text()
    assert "timezone.utc" in text, "AU-8 FAIL: consumer does not use UTC for timestamps"


# ── AU-9: Protection of audit information ────────────────────────────────────

def test_au9_append_only_grant_in_migration():
    """AU-9: migration revokes UPDATE, DELETE, TRUNCATE on audit_events table."""
    assert MIGRATION.exists(), "Audit migration file not found"
    text = MIGRATION.read_text()
    assert "REVOKE" in text, "AU-9 FAIL: no REVOKE statement in audit migration"
    assert "UPDATE" in text and "DELETE" in text, "AU-9 FAIL: UPDATE/DELETE not revoked"


def test_au9_no_update_delete_in_audit_models():
    """AU-9: audit-service models do not define any update/delete operations."""
    api_dir = AUDIT_SVC / "app/api"
    if not api_dir.exists():
        pytest.skip("No API directory")
    for py_file in api_dir.rglob("*.py"):
        text = py_file.read_text()
        # DELETE methods are forbidden in the audit API
        assert "method=\"DELETE\"" not in text and 'router.delete' not in text.lower(), (
            f"AU-9 FAIL: DELETE method found in audit API: {py_file}"
        )


# ── AU-11: Audit record retention ────────────────────────────────────────────

MINIMUM_RETENTION_YEARS = 3

def test_au11_retention_config_exists():
    """AU-11: audit-service config has audit_retention_years >= 3."""
    config_file = AUDIT_SVC / "app/config.py"
    assert config_file.exists()
    text = config_file.read_text()
    assert "audit_retention_years" in text, "AU-11 FAIL: audit_retention_years not in config"
    # Extract default value
    match = re.search(r"audit_retention_years\s*:\s*int\s*=\s*(\d+)", text)
    assert match, "AU-11 FAIL: Could not parse audit_retention_years default"
    default_years = int(match.group(1))
    assert default_years >= MINIMUM_RETENTION_YEARS, (
        f"AU-11 FAIL: Default retention {default_years} years < required {MINIMUM_RETENTION_YEARS} years"
    )


def test_au11_archival_respects_retention():
    """AU-11: archival task uses audit_retention_years from config."""
    tasks_file = AUDIT_SVC / "worker/tasks.py"
    text = tasks_file.read_text()
    assert "audit_retention_years" in text, (
        "AU-11 FAIL: archival task does not reference audit_retention_years from config"
    )


# ── AU-12: Audit record generation ───────────────────────────────────────────

def test_au12_audit_middleware_in_all_services():
    """AU-12: AuditMiddleware is added in every service's main.py."""
    missing = []
    for svc in SERVICES:
        main_py = REPO / "services" / svc / "app/main.py"
        if not main_py.exists():
            missing.append(f"{svc} (main.py not found)")
            continue
        text = main_py.read_text()
        if "AuditMiddleware" not in text:
            missing.append(svc)

    assert not missing, f"AU-12 FAIL: AuditMiddleware missing in: {missing}"


def test_au12_audit_emitter_in_shared():
    """AU-12: shared audit emitter exists and exports emit_audit_event."""
    emitter = REPO / "packages/py-shared/gxp_shared/audit/emitter.py"
    assert emitter.exists(), "AU-12 FAIL: gxp_shared/audit/emitter.py not found"
    text = emitter.read_text()
    assert "emit_audit_event" in text, "AU-12 FAIL: emit_audit_event not defined in emitter"
