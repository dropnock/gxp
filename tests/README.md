# tests

Root-level test suite. Currently contains NIST 800-53 AU (Audit and Accountability) compliance tests. These are static analysis tests — they inspect source code, migration SQL, and configuration files without requiring a running database or network. They run in CI on every pull request as part of the `compliance` job.

Service-level tests live in `services/{name}/tests/`. Shared library tests live in `packages/py-shared/tests/`. This directory is for cross-cutting compliance and integration tests that span multiple services.

---

## Key Design Decisions

- **Static compliance tests over integration tests** — the AU control tests inspect the presence of required fields, middleware, SQL statements, and configuration values directly in the source tree. This makes them fast (no Docker required), deterministic (no network flakiness), and executable on every PR in a standard GitHub Actions runner without a test database.
- **Tests encode control requirements, not just assertions** — each test function has a docstring quoting the NIST control number and what it verifies. This creates a living link between the code and the compliance checklist, making audit evidence easier to produce.
- **Malformed events are ACKed** — AU-5 test (`test_au5_consumer_handles_errors`) verifies that the audit consumer ACKs malformed stream entries after logging rather than leaving them in a pending state, which would cause an infinite retry loop.

---

## Structure

```
tests/
├── compliance/
│   ├── conftest.py            # pytest fixtures for compliance tests (e.g., REPO path)
│   └── test_au_controls.py   # NIST 800-53 AU control tests (AU-2 through AU-12)
```

---

## Running the Tests

```bash
# All compliance tests
uv run pytest tests/compliance/ -v

# All tests (service + shared + compliance)
uv run pytest
```

No environment variables or external services are required for compliance tests.

---

## Controls Covered in `test_au_controls.py`

| Test | Control | What is verified |
|---|---|---|
| `test_au2_required_event_categories` | AU-2 | AuditMiddleware derives `resource_type` from URL path; all required resource categories (`document`, `workflow`, `case`, `tenant`, `audit`) have API routes |
| `test_au3_audit_record_fields` | AU-3 | `AuditEvent` model contains all required fields |
| `test_au4_archival_task_exists` | AU-4 | `archive_old_partitions` Celery task exists and references MinIO |
| `test_au4_partition_creation_task_exists` | AU-4 | `create_next_partition` Celery task exists |
| `test_au5_consumer_handles_errors` | AU-5 | Consumer handles `CancelledError`, has retry logic, ACKs malformed events |
| `test_au6_report_endpoints_exist` | AU-6 | `/summary`, `actor-activity`, `failed-actions` endpoints present |
| `test_au6_auditor_role_required` | AU-6 | `gxp-auditor` role enforced on report endpoints |
| `test_au8_timestamps_are_timezone_aware` | AU-8 | `event_time` column uses `timezone=True` |
| `test_au8_consumer_uses_utc` | AU-8 | Consumer uses `timezone.utc` for timestamp conversion |
| `test_au9_append_only_grant_in_migration` | AU-9 | Alembic migration contains `REVOKE UPDATE, DELETE, TRUNCATE` on `audit_events` |
| `test_au9_no_update_delete_in_audit_models` | AU-9 | No DELETE router methods in audit API |
| `test_au11_retention_config_exists` | AU-11 | `audit_retention_years` config exists with default ≥ 3 |
| `test_au11_archival_respects_retention` | AU-11 | Archival task references `audit_retention_years` |
| `test_au12_audit_middleware_in_all_services` | AU-12 | `AuditMiddleware` present in every service's `main.py` |
| `test_au12_audit_emitter_in_shared` | AU-12 | `emit_audit_event` defined in `gxp_shared/audit/emitter.py` |

---

## Adding New Compliance Tests

1. Add a new test function to `test_au_controls.py` (or a new file for a different control family).
2. Include the NIST control number in the docstring.
3. Use `REPO = Path(__file__).parents[2]` to navigate the source tree.
4. Keep tests static — read files, parse text, check patterns. Do not import application code that has external dependencies.

Future additions: SC (System and Communications Protection) controls for TLS enforcement, AC (Access Control) controls for role definitions, and IA (Identification and Authentication) controls for MFA policy.
