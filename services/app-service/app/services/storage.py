"""MinIO client for app schema snapshots."""
from __future__ import annotations

import io
import json

from minio import Minio
from minio.error import S3Error

from app.config import settings

_client: Minio | None = None


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def _bucket(tenant_slug: str) -> str:
    return f"gxp-app-schemas-{tenant_slug}"


def ensure_bucket(tenant_slug: str) -> None:
    client = get_client()
    bucket = _bucket(tenant_slug)
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def put_schema(tenant_slug: str, app_id: str, version: int, schema: dict) -> str:
    """Write frozen schema JSON to MinIO. Returns the object key."""
    ensure_bucket(tenant_slug)
    client = get_client()
    key = f"{app_id}/v{version}.json"
    data = json.dumps(schema).encode()
    client.put_object(
        _bucket(tenant_slug), key,
        io.BytesIO(data), length=len(data),
        content_type="application/json",
    )
    return key


def get_schema(tenant_slug: str, minio_key: str) -> dict:
    client = get_client()
    try:
        resp = client.get_object(_bucket(tenant_slug), minio_key)
        return json.loads(resp.read())
    except S3Error as e:
        raise FileNotFoundError(f"Schema not found in MinIO: {e}") from e
