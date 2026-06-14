# services/notification-service

Delivers email and in-app notifications triggered by events across the platform (workflow task assignments, case updates, document approvals, etc.). It is an event-driven consumer service — it subscribes to Valkey Streams published by other services and dispatches notifications via SMTP or a future WebSocket channel.

This service is the least-built service in the current implementation phase and serves primarily as a placeholder/scaffold for Phase 1.

---

## Key Design Decisions

- **Event-driven consumption** — notifications are triggered by events from other services (workflow task ready, case status changed, etc.) via Valkey Streams rather than direct HTTP calls. This decouples notification delivery from the source service's request path and makes it resilient to notification-service downtime (events buffer in Valkey).
- **No database schema** — unlike other services, the notification-service does not use a tenant-scoped PostgreSQL schema. Notification delivery state (queued, sent, failed) is tracked transiently via Celery task state. Persistent notification preferences or history would be a future addition.
- **Standard FastAPI skeleton** — the service follows the same middleware stack as all others (`TenantContextMiddleware`, `AuditMiddleware`) so it participates in the audit trail and can be monitored uniformly.
- **SMTP for delivery** — the initial implementation targets SMTP (configurable host/port). No commercial SaaS email service is used, preserving air-gap compatibility.

---

## Structure

```
services/notification-service/
├── app/
│   ├── api/
│   │   └── __init__.py          # API router (endpoints TBD in Phase 1)
│   ├── config.py
│   ├── consumers/
│   │   └── __init__.py          # Valkey stream consumers (scaffold)
│   ├── db/
│   │   └── session.py           # DB session (currently unused — no schema)
│   ├── models/
│   │   └── __init__.py          # ORM models (TBD)
│   └── main.py
└── pyproject.toml
```

---

## Dependencies / Licenses

| Package | License | Purpose |
|---|---|---|
| fastapi 0.115 | MIT | API framework |
| uvicorn 0.32 | BSD-3 | ASGI server |
| redis 5.2 | MIT | Valkey stream consumer |
| gxp-shared | internal | Auth, audit middleware |

---

## Local Development

```bash
uv sync
cd services/notification-service
uvicorn app.main:app --reload --port 8006
```

---

## Configuration

| Variable | Purpose |
|---|---|
| `VALKEY_URL` | Valkey (stream subscription, DB 5) |
| `KEYCLOAK_URL` | Keycloak base URL |
| `KEYCLOAK_REALM` | Default tenant realm (used when resolving notification targets) |
| `CLIENT_ID` / `CLIENT_SECRET` | Service OAuth2 credentials |
| `SMTP_HOST` / `SMTP_PORT` | SMTP server for email delivery |

---

## Planned Streams

The following Valkey streams will be consumed once Phase 1 implementation is complete:

| Stream | Source | Trigger |
|---|---|---|
| `workflow:task_ready` | workflow-service | Human task becomes available |
| `case:status_changed` | case-service | Case status transition |
| `document:scan_complete` | document-service | AV scan result available |
| `tenant:provisioned` | tenant-service | New tenant provisioned |
