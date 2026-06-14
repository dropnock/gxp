# services/case-service

Manages adaptive case management: case types, cases, participants, notes, timeline events, and links to workflow instances and documents. Cases are long-running government work items that may span multiple workflow steps, involve multiple staff members, and accumulate documents over time.

---

## Key Design Decisions

- **Participant-based access control** — non-admin users see and edit only cases they participate in (`CaseParticipant` rows). The four participant roles are `owner`, `collaborator`, `observer`, `subject`. Admins and case managers bypass participant checks.
- **Immutable timeline** — every case state change (status change, note added, participant added/removed, workflow started, document linked) appends a `CaseTimelineEvent`. Timeline events are never updated or deleted; they provide an auditable chronology.
- **Case number format** — `CASE-{YEAR}-{SEQ:05d}`, generated atomically per `(org_id, year)` using a counter table. `next_case_number` in `services/case_numbers.py` uses a database-level sequence/lock to prevent gaps or duplicates.
- **Service-to-service workflow start** — `POST /cases/{id}/start-workflow` calls workflow-service directly using an OAuth2 client credentials token (via `ServiceTokenManager` from `py-shared`). The response instance ID is linked back as a `CaseWorkflowLink`.
- **Asyncio timeline consumer** — the case-service runs a background asyncio task (`run_timeline_consumer`) that listens for workflow completion events on a Valkey stream and appends corresponding timeline entries. This avoids polling and keeps timeline updates near-real-time.

---

## Structure

```
services/case-service/
├── app/
│   ├── api/v1/
│   │   ├── cases.py             # Case CRUD, participants, notes, workflow links, document links, timeline
│   │   ├── case_types.py        # Case type definitions CRUD
│   │   └── cross_tenant.py      # Cross-tenant case access
│   ├── config.py
│   ├── db/
│   │   ├── session.py
│   │   └── migrations/versions/001_create_case_tables.py
│   ├── models/case.py           # Case, CaseParticipant, CaseNote, CaseWorkflowLink,
│   │                            #   CaseDocumentLink, CaseTimelineEvent, CaseType ORM models
│   └── services/
│       ├── case_numbers.py      # Atomic case number generation
│       ├── permissions.py       # assert_can_read / assert_can_write helpers
│       └── timeline.py          # Background Valkey stream consumer for timeline events
└── tests/
    ├── test_case_numbers.py
    └── test_permissions.py
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
| httpx 0.27 | BSD-3 | Service-to-service calls (workflow-service) |
| opensearch-py 2.7 | Apache 2.0 | Case full-text search index |
| redis 5.2 | MIT | Valkey (timeline consumer) |
| gxp-shared | internal | Auth, audit, cross-tenant, service tokens |

---

## Local Development

```bash
uv sync
cd services/case-service
uvicorn app.main:app --reload --port 8003
```

Run tests:
```bash
uv run pytest services/case-service/tests/ -q
```

---

## REST API

Base path: `/api/v1/cases`

### Cases

| Method | Path | Required Role | Description |
|---|---|---|---|
| `POST` | `/cases` | any user role | Create case (auto-assigns case number, adds creator as owner) |
| `GET` | `/cases` | any user role | List cases (participants only unless admin) |
| `GET` | `/cases/{id}` | participant or admin | Get case with participants, workflow links, document links |
| `PUT` | `/cases/{id}` | participant (write) or admin | Update case fields / status |

### Participants

| Method | Path | Description |
|---|---|---|
| `GET` | `/cases/{id}/participants` | List participants |
| `POST` | `/cases/{id}/participants` | Add participant (roles: owner/collaborator/observer/subject) |
| `DELETE` | `/cases/{id}/participants/{user_id}` | Remove participant |

### Notes

| Method | Path | Description |
|---|---|---|
| `GET` | `/cases/{id}/notes` | List notes (internal notes hidden from non-case-workers by default) |
| `POST` | `/cases/{id}/notes` | Add note |
| `PUT` | `/cases/{id}/notes/{note_id}` | Update own note (admin can edit any) |

### Workflow & Document Links

| Method | Path | Description |
|---|---|---|
| `POST` | `/cases/{id}/workflow-links` | Link an existing workflow instance to a case |
| `POST` | `/cases/{id}/start-workflow` | Create a new workflow instance in workflow-service and link it |
| `POST` | `/cases/{id}/document-links` | Link a document from document-service to this case |

### Timeline

| Method | Path | Description |
|---|---|---|
| `GET` | `/cases/{id}/timeline` | Get chronological timeline events for a case |

---

## Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Case-service database (`gxp_case`) |
| `VALKEY_URL` | Valkey (timeline consumer, DB 2) |
| `OPENSEARCH_URL` | OpenSearch (case search index) |
| `WORKFLOW_SERVICE_URL` | workflow-service base URL for S2S calls |
| `CLIENT_ID` / `CLIENT_SECRET` | OAuth2 service credentials |
| `TENANT_SERVICE_DB_URL` | Tenant DB (cross-tenant grant checks) |

---

## Case Status Values

`open` → `pending` → `on_hold` → `closed` → `archived`

Every status transition is recorded in the timeline with `event_type: "status_change"` and `{ from, to }` metadata.
