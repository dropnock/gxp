# services/tenant-service

The platform super-admin service. It is the only service authenticated against the `gxp-platform` Keycloak realm. Everything else authenticates against tenant-specific realms. Tenant-service owns the full lifecycle of a tenant: creating and suspending Keycloak realms, provisioning PostgreSQL schemas in every other service's database, creating MinIO buckets, creating OpenSearch indices, and warming the Valkey tenant cache.

Platform super-admins also use it to manage the cross-tenant access grant system and the shared template catalog.

---

## Key Design Decisions

- **Sole provisioner** — no other service creates Keycloak realms, PostgreSQL schemas, MinIO buckets, or OpenSearch indices. Centralising this here keeps provisioning logic in one place and ensures every resource is created consistently.
- **Platform-realm only** — `TenantContextMiddleware` still runs, but for valid platform admin requests it sets `tenant_slug = None`. `require_platform_admin` checks both that `tenant_slug is None` and that the caller holds `gxp-platform-admin`.
- **Async provisioning** — `POST /api/v1/tenants` returns 202 immediately after writing the DB record; the five-step provisioning sequence (Keycloak → Postgres schemas × 5 → MinIO buckets × 4 → OpenSearch indices × 2 → Valkey cache) runs as a FastAPI `BackgroundTask`. This avoids HTTP timeouts during provisioning.
- **Valkey cache warm-up** — on successful provisioning, `gxp:tenant:{slug}` (status=`active`) and `gxp:tenant:realm:gxp-{slug}` (slug lookup) are written to Valkey. All other services check this cache to validate tenant context without a DB round-trip.
- **Celery for scheduled work** — a `tenant-beat` + `tenant-worker` pair handles periodic tasks (e.g., tenant health checks, scheduled de-provisioning). The web process itself does not run Celery.

---

## Structure

```
services/tenant-service/
├── app/
│   ├── api/v1/
│   │   ├── tenants.py       # Tenant CRUD + cross-tenant grant endpoints
│   │   └── catalog.py       # Template catalog endpoints
│   ├── config.py            # Settings (DB URLs for all service DBs, Keycloak, MinIO, etc.)
│   ├── db/
│   │   ├── session.py
│   │   └── migrations/versions/001_create_platform_schema.py
│   ├── models/platform.py   # Tenant, CrossTenantGrant, CatalogTemplate ORM models
│   ├── schemas/tenant.py    # Pydantic request/response models
│   └── services/
│       ├── provisioner.py   # Full tenant provisioning orchestration
│       └── catalog.py       # Template fork logic
├── worker/
│   ├── celery_app.py
│   └── tasks.py             # Scheduled tenant-lifecycle tasks
└── tests/
```

---

## Dependencies / Licenses

| Package | License | Purpose |
|---|---|---|
| fastapi 0.115 | MIT | API framework |
| uvicorn 0.32 | BSD-3 | ASGI server |
| sqlalchemy 2 async | MIT | ORM + async DB |
| asyncpg 0.30 | Apache 2.0 | PostgreSQL async driver |
| alembic 1.14 | MIT | DB migrations |
| python-keycloak 4.7 | MIT | Keycloak Admin API client |
| minio 7.2 | Apache 2.0 | MinIO bucket management |
| opensearch-py 2.7 | Apache 2.0 | OpenSearch index management |
| redis 5.2 | MIT | Valkey cache warm-up |
| celery 5.4 | BSD-3 | Scheduled tasks |
| gxp-shared | internal | Auth, audit, messaging |

---

## Local Development

```bash
uv sync
cd services/tenant-service
uvicorn app.main:app --reload --port 8010
```

Run tests:
```bash
uv run pytest services/tenant-service/tests/ -q
```

---

## REST API

Base path: `/api/v1`

### Tenants (`/tenants`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/tenants` | platform-admin | Provision a new tenant (202 Accepted, async) |
| `GET` | `/tenants` | platform-admin | List all tenants |
| `GET` | `/tenants/{slug}` | platform-admin | Get tenant by slug |
| `PATCH` | `/tenants/{slug}` | platform-admin | Update tenant name / status |
| `POST` | `/tenants/{slug}/cross-tenant-grants` | `gxp-admin` | Request cross-tenant access |
| `POST` | `/tenants/{slug}/cross-tenant-grants/{id}/approve` | `gxp-admin` | Approve a pending grant |
| `DELETE` | `/tenants/{slug}/cross-tenant-grants/{id}` | `gxp-admin` | Revoke a grant |
| `GET` | `/tenants/{slug}/cross-tenant-grants` | `gxp-admin` | List grants for a tenant |

### Catalog (`/catalog`)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/catalog` | any authenticated | List active templates (optional `?category=`) |
| `POST` | `/catalog` | platform-admin | Publish a new template |
| `POST` | `/catalog/{id}/fork` | any authenticated | Copy template into calling tenant's namespace |
| `DELETE` | `/catalog/{id}` | platform-admin | Deactivate (soft-delete) a template |

---

## Configuration

All settings are in `app/config.py` and loaded from environment variables.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Tenant-service's own database (`gxp_tenant`) |
| `APP_SERVICE_DB_URL` | App-service DB (schema creation on provisioning) |
| `WORKFLOW_SERVICE_DB_URL` | Workflow-service DB (schema creation on provisioning) |
| `CASE_SERVICE_DB_URL` | Case-service DB |
| `DOCUMENT_SERVICE_DB_URL` | Document-service DB |
| `AUDIT_SERVICE_DB_URL` | Audit-service DB |
| `KEYCLOAK_URL` | Keycloak base URL |
| `KEYCLOAK_ADMIN_USERNAME` / `KEYCLOAK_ADMIN_PASSWORD` | Keycloak Admin API credentials |
| `MINIO_ENDPOINT` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | MinIO |
| `OPENSEARCH_URL` | OpenSearch |
| `VALKEY_URL` | Valkey (cache warm-up) |
| `CELERY_BROKER_URL` | Valkey (Celery broker, DB 6) |
| `CLIENT_ID` / `CLIENT_SECRET` | OAuth2 service account credentials |

---

## Security / Compliance Notes

- Only this service interacts with the Keycloak Admin API. No other service creates or deletes realms.
- Cross-tenant grants are stored in `platform.cross_tenant_grants` and have an optional `expires_at`. Revocation sets `status='revoked'`; the Valkey cache TTL (60 s in `py-shared`) bounds propagation delay.
- Tenant suspension (`deprovision_tenant`) writes `status='suspended'` to Valkey immediately, blocking all tenant requests within the cache TTL.
