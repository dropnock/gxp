"""
Orchestrates full tenant provisioning:
  1. Keycloak realm creation (from parameterized template)
  2. PostgreSQL schema creation in each service database
  3. MinIO bucket creation (documents + app-schemas)
  4. OpenSearch index alias setup
  5. Valkey tenant cache warm-up
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import UUID

import redis.asyncio as aioredis
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from minio import Minio
from opensearchpy import AsyncOpenSearch
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)

REALM_TEMPLATE_PATH = Path(__file__).parent.parent.parent.parent.parent / "services" / "identity" / "realm-template.json"

# All service databases that need a per-tenant schema
SERVICE_DB_URLS = {
    "app_service": settings.app_service_db_url,
    "workflow_service": settings.workflow_service_db_url,
    "case_service": settings.case_service_db_url,
    "document_service": settings.document_service_db_url,
    "audit_service": settings.audit_service_db_url,
}


async def provision_tenant(slug: str, name: str, created_by: UUID) -> None:
    """Full tenant provisioning sequence. Raises on any step failure."""
    logger.info("Provisioning tenant: %s (%s)", slug, name)

    realm_name = f"gxp-{slug}"

    await _create_keycloak_realm(slug, name, realm_name)
    await _create_postgres_schemas(slug)
    await _create_minio_buckets(slug)
    await _create_opensearch_indices(slug)
    await _warm_valkey_cache(slug, realm_name)

    logger.info("Tenant provisioning complete: %s", slug)


async def deprovision_tenant(slug: str) -> None:
    """Marks tenant suspended in cache. Physical teardown is a separate job."""
    r = aioredis.from_url(settings.valkey_url, decode_responses=True)
    await r.hset(f"gxp:tenant:{slug}", "status", "suspended")
    await r.delete(f"gxp:tenant:realm:gxp-{slug}")
    logger.info("Tenant suspended in cache: %s", slug)


# ── Steps ──────────────────────────────────────────────────────────────────────

async def _create_keycloak_realm(slug: str, name: str, realm_name: str) -> None:
    template = json.loads(REALM_TEMPLATE_PATH.read_text())
    template["realm"] = realm_name
    template["displayName"] = name

    # Substitute {tenant_slug} and {tenant_name} in all string values
    template_str = json.dumps(template)
    template_str = template_str.replace("{tenant_slug}", slug).replace("{tenant_name}", name)
    realm_payload = json.loads(template_str)

    conn = KeycloakOpenIDConnection(
        server_url=settings.keycloak_url,
        username=settings.keycloak_admin_username,
        password=settings.keycloak_admin_password,
        realm_name="master",
        verify=True,
    )
    admin = KeycloakAdmin(connection=conn)

    existing = [r["realm"] for r in admin.get_realms()]
    if realm_name in existing:
        logger.warning("Realm %s already exists, skipping creation", realm_name)
        return

    admin.create_realm(payload=realm_payload, skip_exists=True)
    logger.info("Created Keycloak realm: %s", realm_name)


async def _create_postgres_schemas(slug: str) -> None:
    schema = f"t_{slug}"
    for svc_name, db_url in SERVICE_DB_URLS.items():
        engine = create_async_engine(db_url, echo=False)
        try:
            async with engine.connect() as conn:
                await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
                await conn.commit()
            logger.info("Created schema %s in %s", schema, svc_name)
        finally:
            await engine.dispose()


async def _create_minio_buckets(slug: str) -> None:
    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    buckets = [
        f"gxp-docs-{slug}",           # clean documents (WORM)
        f"gxp-stage-{slug}",          # upload staging (pre-AV scan)
        f"gxp-quarantine-{slug}",     # infected files
        f"gxp-app-schemas-{slug}",    # published app schemas
    ]
    for bucket in buckets:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info("Created MinIO bucket: %s", bucket)
        else:
            logger.warning("MinIO bucket already exists: %s", bucket)


async def _create_opensearch_indices(slug: str) -> None:
    client = AsyncOpenSearch(hosts=[settings.opensearch_url])
    indices = {
        f"{slug}-documents": {
            "mappings": {
                "properties": {
                    "document_id": {"type": "keyword"},
                    "tenant_slug": {"type": "keyword"},
                    "name": {"type": "text"},
                    "tags": {"type": "keyword"},
                    "content": {"type": "text"},
                    "created_at": {"type": "date"},
                }
            }
        },
        f"{slug}-cases": {
            "mappings": {
                "properties": {
                    "case_id": {"type": "keyword"},
                    "tenant_slug": {"type": "keyword"},
                    "title": {"type": "text"},
                    "case_number": {"type": "keyword"},
                    "status": {"type": "keyword"},
                    "created_at": {"type": "date"},
                }
            }
        },
    }
    for index_name, body in indices.items():
        exists = await client.indices.exists(index=index_name)
        if not exists:
            await client.indices.create(index=index_name, body=body)
            logger.info("Created OpenSearch index: %s", index_name)
    await client.close()


async def _warm_valkey_cache(slug: str, realm_name: str) -> None:
    r = aioredis.from_url(settings.valkey_url, decode_responses=True)
    # Map slug → metadata
    await r.hset(f"gxp:tenant:{slug}", mapping={"realm": realm_name, "status": "active"})
    # Map realm name → slug (for fast JWT iss lookup)
    await r.set(f"gxp:tenant:realm:{realm_name}", slug)
    # Add to the active tenants set
    await r.sadd("gxp:tenants:active", slug)
    logger.info("Warmed Valkey cache for tenant: %s", slug)
