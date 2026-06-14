# services/app-service

Manages the lifecycle of low-code GXP applications: creation, page editing, review workflow, publish, and runtime schema delivery. It is the backend for the portal's visual app builder and the source of published schemas for the runtime app.

---

## Key Design Decisions

- **Explicit publish state machine** — apps move through `draft → under_review → published | rejected`. Developers submit for review; admins publish or reject. This gate ensures no unreviewed app is served to end users. The state is enforced in both the `apps.py` router (edit blocked unless `draft` or `rejected`) and `publish.py` (publish blocked unless `under_review` or `draft`).
- **Published schemas stored in MinIO** — when an app is published, `publisher.py` assembles the `AppSchema` JSON and writes it to `gxp-app-schemas-{tenant_slug}` in MinIO. The `AppVersion` row records the MinIO key. This decouples schema storage from the database and enables large schemas without DB bloat.
- **Role-based app visibility** — non-admins see only apps for which an `AppPermission` row exists with one of their roles. Admins see all. Creator gets `gxp-developer / edit` automatically on create.
- **Schema validation at publish** — `builder.py` validates the `AppSchema` JSON: required fields, valid component types (must match the runtime registry), valid permission roles. `SchemaValidationError` maps to HTTP 422.
- **Per-tenant schema isolation** — `TenantContextMiddleware` sets `search_path` to `t_{slug}` before every DB query, so all `GxpApp` rows in `apps` and `AppVersion` rows in `app_versions` are naturally scoped to the calling tenant.

---

## Structure

```
services/app-service/
├── app/
│   ├── api/v1/
│   │   ├── apps.py          # App CRUD + permissions endpoints
│   │   ├── pages.py         # Page CRUD within an app
│   │   ├── publish.py       # Submit-review, reject, publish, get-published, list-versions
│   │   └── cross_tenant.py  # Cross-tenant app access enforcement
│   ├── config.py
│   ├── db/
│   │   ├── session.py
│   │   └── migrations/versions/001_create_app_tables.py
│   ├── models/app.py        # GxpApp, AppVersion, AppPage, AppPermission ORM models
│   └── services/
│       ├── builder.py       # AppSchema validation + VALID_COMPONENT_TYPES
│       ├── publisher.py     # Assemble + write published schema to MinIO
│       └── storage.py       # MinIO client helpers
└── tests/
```

---

## Dependencies / Licenses

| Package | License | Purpose |
|---|---|---|
| fastapi 0.115 | MIT | API framework |
| uvicorn 0.32 | BSD-3 | ASGI server |
| sqlalchemy 2 async | MIT | ORM |
| asyncpg 0.30 | Apache 2.0 | PostgreSQL async driver |
| alembic 1.14 | MIT | Migrations |
| minio 7.2 | Apache 2.0 | Schema storage |
| redis 5.2 | MIT | Valkey (tenant cache) |
| gxp-shared | internal | Auth, audit middleware |

---

## Local Development

```bash
uv sync
cd services/app-service
uvicorn app.main:app --reload --port 8001
```

Run tests:
```bash
uv run pytest services/app-service/tests/ -q
```

---

## REST API

Base path: `/api/v1/apps`

### Apps

| Method | Path | Required Role | Description |
|---|---|---|---|
| `POST` | `/apps` | `gxp-developer`, `gxp-admin` | Create a new app (status: `draft`) |
| `GET` | `/apps` | any | List apps visible to caller |
| `GET` | `/apps/{id}` | any | Get app metadata |
| `PATCH` | `/apps/{id}` | `gxp-developer`, `gxp-admin` | Update name/description (draft only) |
| `DELETE` | `/apps/{id}` | `gxp-admin` | Soft-delete app |
| `GET` | `/apps/{id}/permissions` | `gxp-developer`, `gxp-admin` | List permissions |
| `POST` | `/apps/{id}/permissions` | `gxp-admin` | Grant a role view/edit permission |

### Publish workflow

| Method | Path | Required Role | Description |
|---|---|---|---|
| `POST` | `/apps/{id}/submit-review` | `gxp-developer`, `gxp-admin` | Transition draft → under_review |
| `POST` | `/apps/{id}/reject` | `gxp-admin` | Transition under_review → rejected |
| `POST` | `/apps/{id}/publish` | `gxp-admin` | Publish app; creates an `AppVersion` |
| `GET` | `/apps/{id}/published` | any | Get current published schema (used by runtime) |
| `GET` | `/apps/{id}/versions` | `gxp-developer`, `gxp-admin` | List version history |

---

## Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | App-service database (`gxp_apps`) |
| `VALKEY_URL` | Valkey (tenant cache, DB 0) |
| `MINIO_ENDPOINT` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | MinIO |
| `MINIO_SECURE` | TLS toggle (default `false` in dev) |
| `KEYCLOAK_URL` | Keycloak (JWKS fetch) |
| `CLIENT_ID` / `CLIENT_SECRET` | Service OAuth2 credentials |
| `TENANT_SERVICE_DB_URL` | Tenant DB (cross-tenant grant checks) |

---

## Security Notes

- `VALID_COMPONENT_TYPES` in `builder.py` must stay in sync with the component registry in `apps/runtime/src/engine/component-registry.ts`. Unknown types are stripped at publish time.
- `AppPermission` rows are scoped to the tenant schema via `search_path`. Cross-tenant app access requires a grant checked by `assert_cross_tenant_grant` in `cross_tenant.py`.
