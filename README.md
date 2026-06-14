# GXP — Government Low-Code Platform

A secure, air-gap–compatible, multi-tenant low-code platform built for government agencies. GXP lets non-technical staff build internal tools, automate approvals with BPMN workflows, manage complex cases, and store classified documents — all behind a hardened, FedRAMP-aligned security perimeter.

---

## Features

### Drag-and-Drop App Builder
Build fully functional internal applications in a visual editor powered by [GrapesJS](https://grapesjs.com/). Publish apps as live web pages served by the runtime engine — no code required.

### BPMN 2.0 / DMN 1.3 Workflow Engine
Design and execute approval workflows visually with [bpmn-js](https://github.com/bpmn-io/bpmn-js) and [dmn-js](https://github.com/bpmn-io/dmn-js). Decision tables are evaluated by [SpiffWorkflow](https://github.com/sartography/SpiffWorkflow) (pure-Python, LGPL-2.1). Task inboxes surface work items to the right people at the right time.

### Adaptive Case Management
Track complex, long-running government cases with case types, participant roles, timeline events, and automatic case number generation. Cases integrate directly with the workflow engine for structured process steps.

### Permission-Gated Document Storage
Upload, version, organise into folders, and full-text search documents backed by MinIO object storage and OpenSearch. Every upload is virus-scanned by ClamAV and content-extracted by Apache Tika before indexing.

### Immutable Audit Trail
Every API action across every service emits a structured audit event consumed by the audit service. Events are stored immutably with actor, tenant, resource, and timestamp. Reports surface failed actions and per-actor activity for compliance reviews.

### Hard Multi-Tenancy
Each government agency (tenant) gets an isolated Keycloak realm (`gxp-{slug}`) and a dedicated PostgreSQL schema (`t_{slug}`) in every service database. Tenants cannot see each other's data; cross-tenant access requires bilateral approval recorded in the platform database.

### Air-Gap Deployment
A single script bundles all container images into a tarball for transfer to air-gapped nodes. No internet access is required at runtime.

### FedRAMP / NIST 800-53 Alignment
Security controls are mapped to NIST 800-53 families. Automated compliance tests run in CI. Trivy, Bandit, Semgrep, pip-audit, pnpm audit, and OWASP ZAP run on every push and on a daily schedule.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend framework | React 18 + TypeScript + Vite |
| Frontend routing | React Router v6 |
| Data fetching | TanStack Query v5 |
| Visual app builder | GrapesJS 0.21 |
| BPMN editor | bpmn-js 17 |
| DMN editor | dmn-js 16 |
| Identity (OIDC) | keycloak-js 26 |
| Monorepo (JS) | pnpm workspaces + Turborepo |
| API framework | FastAPI 0.115 + uvicorn |
| ORM / migrations | SQLAlchemy 2 async + Alembic |
| Task queue | Celery 5 + Celery Beat |
| BPMN/DMN engine | SpiffWorkflow (LGPL-2.1) |
| Auth validation | PyJWT + cryptography |
| Observability | OpenTelemetry (API + SDK) |
| Package manager (Python) | uv workspace |
| Identity provider | Keycloak 26 (Apache 2.0) |
| Reverse proxy | Traefik v3 |
| Databases | PostgreSQL 16 (one per service) |
| Cache / message broker | Valkey 8 (Redis fork, BSD) |
| Object storage | MinIO (AGPL, internal use) |
| Full-text search | OpenSearch 2.18 |
| Virus scanning | ClamAV 1.4 |
| Content extraction | Apache Tika 2.9 |
| Container runtime | Docker / Docker Compose |
| Kubernetes manifests | K8s base + Kustomize overlays |

All dependencies are open source with commercial-compatible licenses (MIT, Apache 2.0, BSD, LGPL, AGPL for internal use).

---

## Repository Structure

```
gxp/
├── apps/
│   ├── portal/                  # Staff-facing React SPA (app builder, workflows, cases, docs, audit)
│   │   └── src/
│   │       ├── features/
│   │       │   ├── app-builder/     # GrapesJS visual editor + app CRUD
│   │       │   ├── workflow-editor/ # BPMN editor, DMN editor, task inbox, instance viewer
│   │       │   ├── case-manager/    # Case list, detail, create
│   │       │   ├── document-manager/# Folder tree, upload, search
│   │       │   ├── audit/           # Event log, reports, actor activity
│   │       │   └── platform-admin/  # Tenant provisioning, cross-tenant grants, catalog
│   │       └── shared/
│   │           ├── auth/            # Keycloak adapter, OIDC provider, route guards
│   │           ├── api/             # Axios/fetch base client
│   │           └── components/      # NavBar and shared UI
│   └── runtime/                 # Lightweight React app that renders published GXP apps
│       └── src/
│           ├── components/          # GxpButton, GxpCard, GxpForm, GxpTable, GxpText, GxpContainer
│           └── engine/              # Component registry + JSON-schema renderer
│
├── packages/
│   ├── py-shared/               # Python library shared by all services
│   │   └── gxp_shared/
│   │       ├── auth/            # JWT validator, tenant context middleware, service tokens, cross-tenant
│   │       ├── audit/           # Audit event emitter + FastAPI middleware
│   │       ├── messaging/       # Valkey Streams helpers
│   │       └── telemetry/       # OpenTelemetry setup
│   └── ts-shared/               # TypeScript types and OIDC client shared by frontend apps
│       └── src/
│           ├── auth/            # OIDC client wrapper
│           └── gxp-schema/      # App schema types (component definitions)
│
├── services/
│   ├── tenant-service/          # Platform super-admin: provision tenants, cross-tenant grants, catalog
│   ├── app-service/             # App definitions, pages, publishing to runtime
│   ├── workflow-service/        # BPMN/DMN definitions, process instances, user tasks
│   ├── case-service/            # Case types, cases, participants, timeline
│   ├── document-service/        # Folders, documents, MinIO storage, OpenSearch indexing
│   ├── audit-service/           # Audit event ingestion, reports, archiving to MinIO
│   ├── notification-service/    # Email/in-app notification delivery
│   ├── gateway/                 # Traefik static + dynamic config
│   └── identity/                # Keycloak realm export, realm template, bootstrap script
│       └── scripts/
│           └── bootstrap-realm.sh
│
├── infra/
│   ├── docker/
│   │   ├── docker-compose.yml   # Full dev stack (all services + infrastructure)
│   │   └── .env.example         # Required environment variables
│   ├── k8s/
│   │   └── base/                # Kubernetes Deployment + Service manifests per service
│   ├── scripts/
│   │   ├── airgap-bundle.sh     # Build offline tar bundle of all images
│   │   ├── load-images.sh       # Load bundle on air-gapped node
│   │   └── migrate_tenants.py   # Run Alembic migrations for all tenant schemas
│   └── security/
│       └── zap-rules.tsv        # OWASP ZAP rule overrides
│
├── tests/
│   └── compliance/              # NIST 800-53 AU-control automated tests
│
├── docs/
│   ├── adr/                     # Architectural Decision Records
│   └── compliance/              # FedRAMP / NIST 800-53 control mapping
│
├── .github/
│   └── workflows/
│       ├── ci.yml               # Lint, type-check, test, Docker build (all services + frontend)
│       └── security.yml         # Trivy, Bandit, Semgrep, pip-audit, pnpm audit, OWASP ZAP
│
├── pyproject.toml               # uv workspace root (all Python services + packages)
├── package.json                 # pnpm workspace root
├── pnpm-workspace.yaml
├── turbo.json                   # Turborepo task pipeline
├── bandit.toml                  # Bandit SAST config
├── conftest.py                  # Root pytest conftest
└── pytest.ini                   # Pytest config
```

Each Python service follows the same internal layout:

```
services/<name>/
├── app/
│   ├── api/v1/          # FastAPI routers
│   ├── db/
│   │   ├── session.py   # Async SQLAlchemy engine
│   │   └── migrations/  # Alembic env + versioned migrations
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic request/response schemas
│   └── services/        # Business logic
├── worker/              # Celery app + task definitions (where applicable)
├── tests/
├── Dockerfile
├── alembic.ini
└── pyproject.toml
```

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Docker + Docker Compose | 24 / 2.24 |
| Python | 3.12 |
| uv | latest |
| Node.js | 20 |
| pnpm | 9.15 |

---

## Getting Started

### 1. Clone and configure

```bash
git clone <repo-url> gxp && cd gxp
cp infra/docker/.env.example infra/docker/.env
# Edit infra/docker/.env — change all `changeme_dev` values before deploying anywhere non-local
```

### 2. Start the full dev stack

```bash
cd infra/docker
docker compose up -d
```

This starts: Traefik, PostgreSQL ×6, Keycloak, MinIO, Valkey, OpenSearch, ClamAV, Apache Tika, and all application services + Celery workers.

Wait for services to become healthy (≈60 s on first run while images pull):

```bash
docker compose ps   # all should show "healthy" or "running"
```

### 3. Bootstrap Keycloak (first time only)

```bash
KEYCLOAK_URL=http://localhost:8080 services/identity/scripts/bootstrap-realm.sh
```

Creates the `gxp-platform` realm and service account clients.

### 4. Install frontend dependencies

```bash
pnpm install
```

### 5. Start the portal

```bash
pnpm --filter @gxp/portal dev
# Portal available at http://localhost:5173
```

### Running a service outside Docker (for fast iteration)

```bash
uv sync
cd services/app-service
uvicorn app.main:app --reload --port 8001
```

---

## Service Endpoints (dev)

All services are exposed through Traefik at `http://api.gxp.localhost`. Add `127.0.0.1 api.gxp.localhost keycloak.gxp.localhost` to `/etc/hosts` (or use the domain as-is if your system resolves `.localhost`).

| Service | Route prefix | Internal port |
|---|---|---|
| tenant-service | `/api/v1/tenants` | 8000 |
| app-service | `/api/v1/apps` | 8000 |
| workflow-service | `/api/v1/workflow` | 8000 |
| case-service | `/api/v1/cases` | 8000 |
| document-service | `/api/v1/documents` | 8000 |
| audit-service | `/api/v1/audit` | 8000 |
| Keycloak | `keycloak.gxp.localhost` | 8080 |
| MinIO console | `localhost:9001` | — |
| Traefik dashboard | `localhost:8080` | — |

---

## Multi-Tenancy

Tenants map to government agencies. Each tenant gets:

- A dedicated Keycloak realm: `gxp-{slug}`
- A dedicated PostgreSQL schema in every service DB: `t_{slug}`
- Isolated MinIO bucket prefixes and OpenSearch indices

**Provision a new tenant:**

```bash
curl -X POST http://api.gxp.localhost/api/v1/tenants \
  -H "Authorization: Bearer $PLATFORM_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"slug": "dot", "name": "Dept of Transportation"}'
```

**Run schema migrations for all tenants:**

```bash
uv run python infra/scripts/migrate_tenants.py
```

**Cross-tenant access** requires a bilateral grant approved in the platform admin UI (or via `POST /api/v1/tenants/{id}/grants`). The `TenantContextMiddleware` in `py-shared` resolves the active tenant from the JWT `iss` claim and sets `search_path` for every database request.

---

## Common Commands

```bash
# Run all Python tests
uv run pytest

# Run tests for a specific service
uv run pytest services/app-service/tests/ -q

# Run compliance tests only
uv run pytest tests/compliance/ -v

# Lint + format check (Python)
uv run ruff check services/ packages/
uv run ruff format --check services/ packages/

# Build all TS apps
pnpm build

# TypeScript type-check only
pnpm -r tsc --noEmit

# Build a single service Docker image
docker build -t gxp/app-service:local services/app-service/

# Rebuild and restart a single service
cd infra/docker && docker compose up -d --build app-service
```

---

## Air-Gap Deployment

```bash
# On a machine with internet access + Docker:
GXP_VERSION=1.0.0 infra/scripts/airgap-bundle.sh
# → produces gxp-airgap-bundle-1.0.0.tar.gz

# Transfer the tarball to the air-gapped node, then:
infra/scripts/load-images.sh gxp-airgap-bundle-1.0.0.tar.gz
# Images are loaded into the local Docker daemon; start normally with docker compose
```

---

## CI / CD

Two GitHub Actions pipelines run on every push and pull request to `main`:

**`ci.yml`** — Correctness
- Ruff lint + format check, Pyright type checking, and pytest for every Python service (parallel matrix)
- `py-shared` unit tests
- NIST 800-53 compliance tests
- TypeScript type-check, ESLint, and Turborepo build for all frontend packages
- Docker build smoke-test for every service image

**`security.yml`** — Security (also runs daily at 03:00 UTC)
- **Trivy** — container image vulnerability scan (CRITICAL/HIGH, SARIF uploaded to GitHub Security)
- **Bandit** — Python SAST
- **Semgrep** — OWASP Top 10 + JWT + secrets rules
- **pip-audit** — Python dependency CVE check
- **pnpm audit** — JS dependency CVE check
- **OWASP ZAP** — baseline DAST against a running dev stack (main branch + schedule only)

---

## Environment Variables

Copy `infra/docker/.env.example` and fill in every value. Key variables:

| Variable | Purpose |
|---|---|
| `POSTGRES_PASSWORD` | Shared PostgreSQL password across all DBs |
| `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD` | Keycloak bootstrap credentials |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | MinIO root credentials |
| `VALKEY_PASSWORD` | Valkey/Redis auth password |
| `*_SERVICE_CLIENT_SECRET` | OAuth2 client secret per service (one each) |
| `GXP_DOMAIN` | Base domain for Traefik routing (default: `gxp.localhost`) |

Never commit `.env`. The `.gitignore` blocks it; `.env.example` is the safe reference.

---

## Architectural Decision Records

| ADR | Decision |
|---|---|
| [ADR-001](docs/adr/ADR-001-monorepo-architecture.md) | Single monorepo (uv + pnpm workspaces) |
| [ADR-002](docs/adr/ADR-002-spiffworkflow-for-bpmn-and-dmn-execution.md) | SpiffWorkflow for BPMN/DMN execution |
| [ADR-003](docs/adr/ADR-003-keycloak-for-identity-and-access-management.md) | Keycloak for IAM |
| [ADR-004](docs/adr/ADR-004-minio-for-object-storage.md) | MinIO for object storage |
| [ADR-005](docs/adr/ADR-005-valkey-(redis-fork)-for-messaging-and-caching.md) | Valkey for caching and message brokering |

---

## Implementation Phases

| Phase | Scope | Status |
|---|---|---|
| 0 | Foundation (monorepo, CI, shared libs, Docker Compose) | Complete |
| 0b | Multi-tenancy infrastructure | In progress |
| 1 | Auth backbone + audit trail | In progress |
| 2 | Document service MVP | Upcoming |
| 3 | Workflow + DMN MVP | Upcoming |
| 3b | Case service MVP | Upcoming |
| 4 | App builder MVP | Upcoming |
| 5 | Hardening + compliance | Upcoming |
| 6 | Production readiness | Upcoming |

---

## Compliance

GXP targets **FedRAMP Moderate** and **FISMA/NIST 800-53**. Control mappings live in `docs/compliance/`. Automated AU-family (audit and accountability) control tests run in `tests/compliance/` on every CI run.

All third-party software uses open source licenses compatible with internal government deployment (MIT, Apache 2.0, BSD, LGPL dynamic linking, AGPL for services not distributed externally).
