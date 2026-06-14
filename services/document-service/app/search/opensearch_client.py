"""
OpenSearch indexing for documents.

Text is extracted from the file bytes using Apache Tika (REST API).
Falls back gracefully if Tika is unavailable — document is still indexed
with metadata only, and a re-index can be triggered later.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from opensearchpy import OpenSearch

from app.config import settings

logger = logging.getLogger(__name__)

_client: OpenSearch | None = None


def get_client() -> OpenSearch:
    global _client
    if _client is None:
        _client = OpenSearch(hosts=[settings.opensearch_url])
    return _client


def extract_text(data: bytes, content_type: str) -> str:
    """Call Apache Tika to extract plain text from a document's bytes."""
    try:
        response = httpx.put(
            f"{settings.tika_url}/tika",
            content=data,
            headers={"Content-Type": content_type, "Accept": "text/plain"},
            timeout=30.0,
        )
        if response.status_code == 200:
            return response.text
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tika extraction failed (%s): %s — indexing metadata only", content_type, exc)
    return ""


def index_document(
    tenant_slug: str,
    document_id: str,
    version_id: str,
    name: str,
    description: str,
    tags: list[str],
    mime_type: str,
    uploaded_by: str,
    created_at: str,
    content_text: str = "",
) -> None:
    """Index or re-index a document version in OpenSearch."""
    client = get_client()
    index = f"{tenant_slug}-documents"
    doc: dict[str, Any] = {
        "document_id": document_id,
        "version_id": version_id,
        "tenant_slug": tenant_slug,
        "name": name,
        "description": description or "",
        "tags": tags,
        "mime_type": mime_type or "",
        "uploaded_by": uploaded_by,
        "created_at": created_at,
        "content": content_text,
    }
    client.index(index=index, id=document_id, body=doc)


def delete_document(tenant_slug: str, document_id: str) -> None:
    try:
        get_client().delete(index=f"{tenant_slug}-documents", id=document_id)
    except Exception:  # noqa: BLE001
        pass  # already gone or never indexed


def search_documents(
    tenant_slug: str,
    query: str,
    tags: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Full-text search across document name, description, tags, and extracted content."""
    must: list[dict] = [
        {
            "multi_match": {
                "query": query,
                "fields": ["name^3", "description^2", "tags^2", "content"],
                "type": "best_fields",
                "fuzziness": "AUTO",
            }
        }
    ]
    if tags:
        must.append({"terms": {"tags": tags}})

    body = {
        "query": {"bool": {"must": must}},
        "from": offset,
        "size": limit,
        "_source": ["document_id", "name", "description", "tags", "mime_type", "created_at"],
    }

    result = get_client().search(index=f"{tenant_slug}-documents", body=body)
    hits = result.get("hits", {}).get("hits", [])
    return [{"score": h["_score"], **h["_source"]} for h in hits]
