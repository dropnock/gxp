# services/document-service

Provides permission-gated document storage for government agencies. Documents are organised in hierarchical folders, stored in MinIO, virus-scanned by ClamAV, text-extracted by Apache Tika, and indexed in OpenSearch for full-text search. Every upload is async — the caller receives a 202 immediately and polls for AV scan completion before the document becomes downloadable.

See [ADR-004](../../docs/adr/ADR-004-minio-for-object-storage.md) for the MinIO selection rationale.

---

## Key Design Decisions

- **Staging → clean bucket separation** — uploads go to `gxp-stage-{tenant}`. ClamAV scans the staged file via a Celery task. On success the file moves to `gxp-docs-{tenant}` (WORM-eligible). Infected files move to `gxp-quarantine-{tenant}`. Only `clean` versions are downloadable.
- **AV scan is async via Celery** — `POST /documents` returns 202 with `av_status: pending`. The `scan_document` Celery task (running in the `document` queue) performs the scan, runs Tika extraction, writes the OpenSearch index entry, and updates `av_status` to `clean` or `infected`.
- **Presigned URL download** — `GET /documents/{id}/download` generates a 5-minute MinIO presigned URL and returns a 302 redirect. The file bytes never pass through the Python service, keeping the service stateless and traffic low.
- **Folder-and-document permission model** — `DocumentPermission` rows reference either a folder or a document, a principal type (`user` or `role`), and a set of permissions (`read`, `write`, `delete`). `check_permission` in `services/permissions.py` checks document-level first, then falls back to the folder.
- **Versioning** — each upload to an existing document creates a new `DocumentVersion`. `document.current_version_id` tracks the latest clean version. Old versions remain accessible for audit and rollback.

---

## Structure

```
services/document-service/
├── app/
│   ├── api/v1/
│   │   ├── documents.py         # Upload, list, get, versions, download, delete, permissions
│   │   ├── folders.py           # Folder CRUD and tree navigation
│   │   ├── search.py            # Full-text search via OpenSearch
│   │   └── cross_tenant.py      # Cross-tenant document access
│   ├── config.py
│   ├── db/
│   │   ├── session.py
│   │   └── migrations/versions/001_create_document_tables.py
│   ├── models/document.py       # Document, DocumentVersion, Folder, DocumentPermission ORM
│   ├── search/
│   │   └── opensearch_client.py # OpenSearch index helpers
│   ├── services/
│   │   └── permissions.py       # check_permission (doc-level then folder-level)
│   ├── storage/
│   │   └── minio_client.py      # stage_bucket, docs_bucket, upload_to_staging, generate_presigned_url
│   └── worker/
│       ├── celery_app.py
│       └── tasks.py             # scan_document: ClamAV scan → Tika extract → OpenSearch index
└── tests/
    ├── test_permissions.py
    └── conftest.py
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
| minio 7.2 | Apache 2.0 | Object storage client |
| opensearch-py 2.7 | Apache 2.0 | Full-text search |
| celery 5.4 | BSD-3 | Async AV scan + indexing tasks |
| redis 5.2 | MIT | Celery broker (Valkey DB 3) |
| gxp-shared | internal | Auth, audit middleware |

ClamAV and Apache Tika are called as external services (via TCP socket and HTTP respectively), not as Python libraries.

---

## Local Development

```bash
uv sync
cd services/document-service
uvicorn app.main:app --reload --port 8004

# Celery worker (separate terminal)
celery -A app.worker.celery_app worker --loglevel=info -Q document
```

Run tests:
```bash
uv run pytest services/document-service/tests/ -q
```

---

## REST API

Base path: `/api/v1/documents`

### Documents

| Method | Path | Description |
|---|---|---|
| `POST` | `/documents` | Upload new document (202, AV scan async) |
| `GET` | `/documents` | List documents in a folder (`?folder_id=`) |
| `GET` | `/documents/{id}` | Get document metadata |
| `GET` | `/documents/{id}/versions` | List version history |
| `POST` | `/documents/{id}/versions` | Upload new version (202, AV scan async) |
| `GET` | `/documents/{id}/download` | 302 redirect to 5-min presigned URL (clean only) |
| `DELETE` | `/documents/{id}` | Soft-delete document |
| `POST` | `/documents/{id}/permissions` | Grant permissions on a document |

### Folders

| Method | Path | Description |
|---|---|---|
| `POST` | `/documents/folders` | Create folder |
| `GET` | `/documents/folders` | List root folders |
| `GET` | `/documents/folders/{id}` | Get folder + children |
| `PATCH` | `/documents/folders/{id}` | Rename folder |
| `DELETE` | `/documents/folders/{id}` | Delete empty folder |

### Search

| Method | Path | Description |
|---|---|---|
| `GET` | `/documents/search` | Full-text search (`?q=`, tenant-scoped to OpenSearch index) |

---

## Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Document-service database (`gxp_documents`) |
| `VALKEY_URL` | Valkey (tenant cache, DB 3) |
| `CELERY_BROKER_URL` | Valkey (Celery broker, DB 3) |
| `MINIO_ENDPOINT` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | MinIO |
| `MINIO_SECURE` | TLS for MinIO (default `false` in dev) |
| `CLAMAV_HOST` / `CLAMAV_PORT` | ClamAV clamd socket (default `localhost:3310`) |
| `OPENSEARCH_URL` | OpenSearch |
| `TIKA_URL` | Apache Tika REST server |
| `PRESIGN_EXPIRY_SECONDS` | Presigned URL TTL (default `300`) |
| `CLIENT_ID` / `CLIENT_SECRET` | Service OAuth2 credentials |
| `TENANT_SERVICE_DB_URL` | Tenant DB (cross-tenant grant checks) |

---

## MinIO Buckets (per tenant)

| Bucket | Purpose |
|---|---|
| `gxp-stage-{slug}` | Uploaded files awaiting AV scan |
| `gxp-docs-{slug}` | Clean, downloadable files (WORM-eligible) |
| `gxp-quarantine-{slug}` | Infected files (isolated, not downloadable) |
| `gxp-app-schemas-{slug}` | Published app JSON schemas (written by app-service) |

---

## Security / Compliance Notes

- Only `av_status = 'clean'` versions can be downloaded. Any attempt to download a `pending` or `infected` version returns HTTP 409.
- Files in `gxp-quarantine-{slug}` are retained for forensic review and never served.
- The Python service never streams file bytes to the client — downloads redirect to MinIO presigned URLs, limiting the attack surface for content injection.
- Enable MinIO object locking on `gxp-docs-{slug}` in production to satisfy document retention requirements (NIST 800-53 AU-11 analog for documents).
