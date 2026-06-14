"""
App publish flow.

Steps:
1. Validate all pages pass the schema validator
2. Compile each page's gjs_data → GXP ComponentNode tree
3. Assemble the full GXP AppSchema JSON
4. Write to MinIO (frozen snapshot)
5. Create AppVersion row
6. Update GxpApp.current_version_id and status='published'
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app import AppVersion, GxpApp
from app.services.builder import SchemaValidationError, gjs_to_gxp_components, validate_and_sanitize
from app.services.storage import put_schema


async def publish_app(
    app: GxpApp,
    tenant_slug: str,
    publisher_id: str,
    db: AsyncSession,
) -> AppVersion:
    """
    Compile and publish a draft app. Returns the new AppVersion.
    Raises SchemaValidationError if any page fails validation.
    """
    pages = sorted(app.pages, key=lambda p: p.sort_order)
    if not pages:
        raise SchemaValidationError("App has no pages")

    gxp_pages = []
    for page in pages:
        components = gjs_to_gxp_components(page.gjs_data.get("components", []))
        gxp_pages.append({
            "id": page.page_id,
            "name": page.name,
            "route": page.route,
            "components": components,
            "styles": page.styles,
        })

    # Determine next version number
    existing_versions = [v.version_number for v in app.versions]
    next_version = max(existing_versions, default=0) + 1

    schema = {
        "schemaVersion": "1.0",
        "appId": str(app.id),
        "metadata": {
            "name": app.name,
            "description": app.description or "",
            "version": next_version,
            "theme": "default",
        },
        "datasources": [],
        "pages": gxp_pages,
        "permissions": {
            "viewRoles": [p.role for p in app.permissions if p.permission == "view"],
            "editRoles": [p.role for p in app.permissions if p.permission == "edit"],
        },
    }

    # Validate the assembled schema
    validated_schema = validate_and_sanitize(schema)

    # Write to MinIO
    minio_key = put_schema(tenant_slug, str(app.id), next_version, validated_schema)

    # Persist version record
    version = AppVersion(
        id=uuid.uuid4(),
        app_id=app.id,
        version_number=next_version,
        schema_json=validated_schema,
        minio_key=minio_key,
        published_by=publisher_id,
        published_at=datetime.now(tz=timezone.utc),
    )
    db.add(version)

    app.current_version_id = version.id
    app.status = "published"
    app.updated_at = datetime.now(tz=timezone.utc)

    return version
