# services/audit-service

Consumes structured audit events emitted by every other service and provides a queryable, immutable log for auditors. It is the automated implementation of NIST 800-53 AU controls. Events arrive via a Valkey Stream (`audit:events`) and are bulk-inserted into a partitioned PostgreSQL table. A separate Celery beat job archives old partitions to MinIO and creates future partitions.

---

## Key Design Decisions

- **Redis Streams consumer group** — `AuditMiddleware` in every service writes to `audit:events` fire-and-forget. The audit-service runs an asyncio consumer group (`audit-service`) that reads in batches of 100, bulk-inserts via `ON CONFLICT DO NOTHING`, and ACKs. Multiple audit-service replicas share the load. If the service is down, events persist in Valkey (satisfying NIST 800-53 AU-5).
- **Append-only table** — the Alembic migration for `audit_events` includes `REVOKE UPDATE, DELETE, TRUNCATE ON audit_events FROM PUBLIC` and grants a read-only role for the service's query user. No endpoint in the audit API has a DELETE or PUT method (enforced by the AU-9 compliance test in `tests/compliance/`).
- **Timezone-aware timestamps** — `event_time` is `TIMESTAMP WITH TIME ZONE`. The consumer always parses timestamps as UTC. This satisfies NIST 800-53 AU-8.
- **Tenant scoping** — auditors can only query their own tenant's events. Platform admins (`tenant_slug=None`) can query across all tenants. Scoping is applied at the SQL level, not as a post-filter.
- **Configurable retention** — `audit_retention_years` (default: 3) controls when the archival task moves old partitions to MinIO. The CI compliance test (`test_au11_retention_config_exists`) verifies the default is ≥ 3 years.

---

## Structure

```
services/audit-service/
├── app/
│   ├── api/v1/
│   │   ├── events.py            # GET /audit/events (query log)
│   │   └── reports.py           # GET /audit/reports/summary, actor-activity, failed-actions
│   ├── config.py
│   ├── consumers/
│   │   └── audit_consumer.py    # Asyncio Redis Streams consumer (started on app startup)
│   ├── db/
│   │   ├── session.py
│   │   └── migrations/versions/001_create_audit_events.py  # includes REVOKE statements
│   └── models/
│       └── audit_event.py       # AuditEvent ORM model (no update/delete methods)
├── worker/
│   ├── celery_app.py
│   └── tasks.py                 # archive_old_partitions, create_next_partition (Celery Beat)
└── tests/
    ├── test_consumer.py
    └── test_reports.py
```

---

## Dependencies / Licenses

| Package | License | Purpose |
|---|---|---|
| fastapi 0.115 | MIT | API framework |
| uvicorn 0.32 | BSD-3 | ASGI server |
| sqlalchemy 2 async | MIT | ORM |
| asyncpg 0.30 | Apache 2.0 | PostgreSQL driver |
| alembic 1.14 | MIT | Migrations |
| redis 5.2 | MIT | Valkey Streams consumer |
| celery 5.4 | BSD-3 | Archival scheduled tasks |
| minio 7.2 | Apache 2.0 | Archive storage |
| gxp-shared | internal | Auth, audit middleware |

---

## Local Development

```bash
uv sync
cd services/audit-service
uvicorn app.main:app --reload --port 8005

# Celery worker + beat (separate terminal)
celery -A worker.celery_app worker --loglevel=info -Q audit
celery -A worker.celery_app beat  --loglevel=info --schedule=/tmp/celerybeat-schedule
```

Run tests:
```bash
uv run pytest services/audit-service/tests/ -q
```

---

## REST API

Base path: `/api/v1/audit`

Required role for all endpoints: `gxp-auditor`, `gxp-admin`, or `gxp-platform-admin`.

### Events

| Method | Path | Description |
|---|---|---|
| `GET` | `/audit/events` | Query audit log (filter by actor, event type, resource, outcome, time range) |
| `GET` | `/audit/events/{id}` | Get single event by ID |

Query params for `GET /audit/events`:

| Param | Type | Description |
|---|---|---|
| `actor_id` | string | Filter by actor (user sub) |
| `event_type` | string | e.g. `http.request` |
| `resource_type` | string | e.g. `document`, `case` |
| `resource_id` | string | UUID |
| `outcome` | string | `success`, `client_error`, `server_error` |
| `since` / `until` | ISO-8601 datetime | Time window |
| `limit` | int (max 1000) | Default 100 |
| `offset` | int | Pagination |

### Reports

| Method | Path | Description |
|---|---|---|
| `GET` | `/audit/reports/summary` | Event counts by (service, event_type, outcome) for a time window |
| `GET` | `/audit/reports/actor-activity` | Per-actor event history (`?actor_id=`) |
| `GET` | `/audit/reports/failed-actions` | Events with `outcome` in (`client_error`, `server_error`) |

---

## Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Audit-service database (`gxp_audit`) |
| `VALKEY_URL` | Valkey (consumer + tenant cache, DB 4) |
| `CELERY_BROKER_URL` | Valkey (Celery broker, DB 4) |
| `MINIO_ENDPOINT` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | Archive destination |
| `AUDIT_RETENTION_YEARS` | Minimum 3 (default `3`). Controls archival job cutoff. |
| `AUDIT_ARCHIVE_BUCKET` | MinIO bucket for archived partitions (default `gxp-audit-archive`) |
| `CLIENT_ID` / `CLIENT_SECRET` | Service OAuth2 credentials |

---

## Compliance Notes (NIST 800-53 AU Controls)

| Control | Implementation |
|---|---|
| AU-2 Event types | `AuditMiddleware` emits one event per API call; resource_type derived from URL path |
| AU-3 Record content | `actor_id`, `actor_email`, `actor_roles`, `event_time`, `service`, `action`, `outcome`, `ip_address`, `request_id`, `tenant_slug` |
| AU-4 Storage capacity | Monthly table partitions; old partitions archived to MinIO by Celery Beat |
| AU-5 Processing failures | Events persist in Valkey Streams while consumer is down; malformed events are ACKed to prevent infinite retry |
| AU-6 Review and reporting | `/summary`, `/actor-activity`, `/failed-actions` endpoints; `gxp-auditor` role required |
| AU-8 Timestamps | `event_time TIMESTAMP WITH TIME ZONE`; UTC enforced in consumer |
| AU-9 Protection | `REVOKE UPDATE, DELETE, TRUNCATE` in migration; no DELETE endpoints in audit API |
| AU-11 Retention | `audit_retention_years >= 3` enforced by config default and CI test |
| AU-12 Generation | `AuditMiddleware` in every service's `main.py` verified by CI compliance test |
