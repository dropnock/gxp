# GXP — Government Low-Code Platform

A secure, air-gapped government platform providing: drag-and-drop low-code app builder, BPMN/DMN workflow engine, adaptive case management, and permission-gated document storage.

## Architecture

Monorepo: React frontends + Python FastAPI microservices + PostgreSQL (per service) + Valkey + MinIO + Keycloak + Traefik.

See `/home/dropnock/.claude/plans/playful-tinkering-cupcake.md` for the full architectural plan.

## Service Map

| Service | Port | DB | Notes |
|---|---|---|---|
| tenant-service | 8000 | gxp_tenant | Platform super-admin only (gxp-platform realm) |
| app-service | 8000 | gxp_apps | Schema-per-tenant: t_{slug} |
| workflow-service | 8000 | gxp_workflow | Schema-per-tenant: t_{slug} |
| case-service | 8000 | gxp_case | Schema-per-tenant: t_{slug} |
| document-service | 8000 | gxp_documents | Schema-per-tenant: t_{slug} |
| audit-service | 8000 | gxp_audit | Schema-per-tenant: t_{slug} |
| notification-service | 8000 | — | |
| Keycloak | 8080 | keycloak |
| MinIO | 9000/9001 | — |
| Traefik dashboard | 8080 | — |

## Dev Quick Start

```bash
# 1. Copy env file
cp infra/docker/.env.example infra/docker/.env

# 2. Start the full dev stack
cd infra/docker && docker compose up -d

# 3. Bootstrap Keycloak realm (first time only)
# Requires: 127.0.0.1 keycloak.gxp.localhost in /etc/hosts (Traefik routes port 80 → keycloak:8080)
KEYCLOAK_URL=http://keycloak.gxp.localhost services/identity/scripts/bootstrap-realm.sh

# 4. Install frontend dependencies
pnpm install

# 5. Start the portal in dev mode
pnpm --filter @gxp/portal dev
```

## Python Services

All Python services use `uv` for package management within a workspace.

```bash
# Install all service deps from workspace root
uv sync

# Run a specific service locally
cd services/app-service && uvicorn app.main:app --reload --port 8001
```

## Multi-Tenancy

- Tenant = government agency. Each gets a Keycloak realm (`gxp-{slug}`) and a PostgreSQL schema (`t_{slug}`) in every service DB.
- `TenantContextMiddleware` in py-shared resolves tenant from JWT `iss` claim and sets `search_path` per request.
- `tenant-service` provisions tenants; it's the only service authenticated against `gxp-platform` realm.
- Cross-tenant access requires bilateral approval recorded in `platform.cross_tenant_grants` (tenant-service DB).
- To provision a new tenant via API: `POST /api/v1/tenants { "slug": "dot", "name": "Dept of Transportation" }`
- To run migrations for all tenants: `python infra/scripts/migrate_tenants.py`

## Key Commands

```bash
# Build all TS apps
pnpm build

# Run all Python tests
uv run pytest

# Build air-gap bundle (needs internet + Docker)
GXP_VERSION=1.0.0 infra/scripts/airgap-bundle.sh

# Load bundle on air-gapped node
infra/scripts/load-images.sh gxp-airgap-bundle-1.0.0.tar.gz
```

## Implementation Phases

- **Phase 0** (Weeks 1–3): Foundation ✓ complete
- **Phase 0b** (Weeks 4–6): Multi-tenancy infrastructure ← *current*
- **Phase 1** (Weeks 4–6): Auth + Audit backbone
- **Phase 2** (Weeks 7–10): Document service MVP
- **Phase 3** (Weeks 11–16): Workflow + DMN MVP
- **Phase 3b** (Weeks 17–20): Case service MVP
- **Phase 4** (Weeks 21–27): App builder MVP
- **Phase 5** (Weeks 28–34): Hardening + compliance
- **Phase 6** (Weeks 35–42): Production readiness

## Compliance

FedRAMP + FISMA/NIST 800-53. See `docs/compliance/` for control mapping.
All tools are open source with commercial-compatible licenses (MIT, Apache 2.0, BSD, LGPL, AGPL for internal use).

## ADRs

See `docs/adr/` for architectural decisions.
