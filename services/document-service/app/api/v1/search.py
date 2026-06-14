"""Full-text document search via OpenSearch."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.search.opensearch_client import search_documents
from gxp_shared.auth.dependencies import UserContext, get_current_user

router = APIRouter()


@router.get("")
async def search(
    q: str = Query(..., min_length=1, description="Search query"),
    tags: Optional[str] = Query(None, description="Comma-separated tag filter"),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    user: UserContext = Depends(get_current_user),
):
    """
    Full-text search across document name, description, tags, and extracted content.
    Results are scoped to the calling tenant's OpenSearch index.
    """
    tenant_slug = user.tenant_slug
    if not tenant_slug:
        return []

    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]

    hits = search_documents(
        tenant_slug=tenant_slug,
        query=q,
        tags=tag_list or None,
        limit=limit,
        offset=offset,
    )
    return hits
