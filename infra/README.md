# infra

Infrastructure configuration and operational scripts for GXP. Covers the local Docker Compose dev stack, Kubernetes base manifests for production, multi-tenant migration tooling, and air-gap bundle creation/loading.

---

## Key Design Decisions

- **Docker Compose for dev, Kubernetes for production** — Docker Compose runs all services on a single machine for rapid local iteration. The `k8s/base/` manifests are Kustomize-compatible and intended as the production deployment target, with overlay directories per environment.
- **One PostgreSQL instance per service** — each service has its own named PostgreSQL container (`postgres-app`, `postgres-workflow`, etc.) and database. This provides blast-radius isolation: a schema migration error in one service cannot affect another service's data. It is the correct trade-off for a multi-service government platform.
- **Valkey (Redis fork) over Redis** — See [ADR-005](../docs/adr/ADR-005-valkey-(redis-fork)-for-messaging-and-caching.md). Valkey is BSD-3-Clause; Redis re-licensed to SSPL in 2024.
- **Air-gap bundle is a signed tar** — `airgap-bundle.sh` builds all custom images and pulls all third-party images, saves them to a `.tar.gz`, and generates a SHA-256 manifest. If `GPG_KEY_ID` is set, the manifest is GPG-signed. `load-images.sh` verifies and loads the bundle on the target node.
- **Multi-tenant Alembic runner** — `migrate_tenants.py` reads active tenant slugs from `platform.tenants`, then runs `alembic upgrade head` for each `(service, tenant_schema)` combination. It accepts `--service` and `--tenant` flags for targeted runs, and `--dry-run` for review.

---

## Structure

```
infra/
├── docker/
│   ├── docker-compose.yml    # Full dev stack (all services + infrastructure)
│   └── .env.example          # Template for required environment variables
├── k8s/
│   └── base/
│       ├── namespace.yaml    # gxp Namespace
│       └── {service}/
│           ├── deployment.yaml
│           └── service.yaml
├── scripts/
│   ├── airgap-bundle.sh      # Build + package all Docker images for offline deployment
│   ├── load-images.sh        # Load an air-gap bundle on a target node
│   └── migrate_tenants.py    # Run Alembic migrations for all tenant schemas
└── security/
    └── zap-rules.tsv         # OWASP ZAP rule overrides for the security CI scan
```

---

## Docker Compose Dev Stack

Services started by `docker compose up -d` in `infra/docker/`:

| Container | Image | Purpose |
|---|---|---|
| `traefik` | traefik:v3.3 | Reverse proxy + dashboard (:8080) |
| `postgres-{svc}` ×6 | postgres:16-alpine | One DB per service |
| `postgres-keycloak` | postgres:16-alpine | Keycloak DB |
| `valkey` | valkey/valkey:8-alpine | Cache + message broker |
| `minio` | minio/minio:… | Object storage (S3 API :9000 direct; console via Traefik at `minio.<GXP_DOMAIN>`) |
| `keycloak` | quay.io/keycloak/keycloak:26.0 | Identity provider |
| `opensearch` | opensearchproject/opensearch:2.18.0 | Full-text search |
| `clamav` | clamav/clamav:1.4 | Virus scanning |
| `tika` | apache/tika:2.9.2.1-full | Document text extraction |
| `{svc}-service` | built from `services/{svc}/Dockerfile` | Application services |
| `{svc}-worker` | same image, `celery worker` command | Celery workers |
| `{svc}-beat` | same image, `celery beat` command | Celery scheduled tasks |

All containers share the `gxp-net` bridge network.

---

## Local Quick Start

```bash
cp infra/docker/.env.example infra/docker/.env
# Edit .env — change all changeme_dev values

# Generate TLS certificates (first time only)
infra/scripts/gen-certs.sh

cd infra/docker
docker compose up -d

# Wait for healthy state (~60 s on first run)
docker compose ps

# First-time Keycloak bootstrap
KEYCLOAK_URL=https://keycloak.gxp.localhost services/identity/scripts/bootstrap-realm.sh
```

---

## Database Migrations

Run all migrations for all active tenants across all services:

```bash
uv run python infra/scripts/migrate_tenants.py
```

Options:

| Flag | Example | Description |
|---|---|---|
| `--service` | `--service app-service` | Migrate one service only |
| `--tenant` | `--tenant dot` | Migrate one tenant schema only |
| `--dry-run` | | Print commands, do not execute |

The script reads active tenant slugs from the `platform.tenants` table in the tenant-service DB. Set `TENANT_DB_URL` (and the per-service `*_DB_URL` env vars) for non-default environments.

---

## Air-Gap Deployment

**Build the bundle (internet-connected machine):**

```bash
GXP_VERSION=1.0.0 infra/scripts/airgap-bundle.sh
# Produces: gxp-airgap-bundle-1.0.0.tar.gz + .sha256 manifest
# Optional: set GPG_KEY_ID to sign the manifest
```

Third-party images bundled: Keycloak 26.0, MinIO 2025-01-20, Valkey 8-alpine, PostgreSQL 16-alpine, OpenSearch 2.18.0, ClamAV 1.4, Traefik v3.3, nginx 1.27-alpine.

**Load on the target node:**

```bash
infra/scripts/load-images.sh gxp-airgap-bundle-1.0.0.tar.gz
# Runs docker load; images are then available for docker compose up
```

---

## Kubernetes Base Manifests

`infra/k8s/base/` contains a `Deployment` and `Service` per application service, plus a `Namespace` manifest. Use Kustomize overlays to inject secrets and environment-specific config:

```bash
kubectl apply -k infra/k8s/base/
```

Production overlays (not yet committed) should:
- Replace `image:` tags with pinned versions.
- Add `Ingress` or Traefik `IngressRoute` resources.
- Mount secrets from a secret store (Vault, Sealed Secrets, etc.) rather than plain `Secret` objects.

---

## Security Notes (`zap-rules.tsv`)

The OWASP ZAP baseline scan runs against a live dev stack in CI (on schedule and `main` branch). `infra/security/zap-rules.tsv` contains rule overrides (e.g., `IGNORE` for rules that are false positives in dev-mode). Review and tighten these overrides before production launch.
