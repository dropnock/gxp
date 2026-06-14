"""
Permission resolution for folders and documents.

Inheritance rules:
  - Permissions propagate DOWN the folder tree.
  - A document-level permission OVERRIDES any inherited folder permission for that principal.
  - If no explicit permission exists, access is denied (default-deny).
  - Admins and platform-admins bypass per-resource permission checks.

check_permission() uses a recursive CTE to walk up from a document's folder
to the root, collecting all folder-level permissions, then merges document-level
permissions on top.  Result: the effective permission set for the requesting user.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from gxp_shared.auth.dependencies import UserContext

_ADMIN_ROLES = {"gxp-admin", "gxp-platform-admin"}


async def check_permission(
    *,
    db: AsyncSession,
    user: UserContext,
    resource_type: str,  # 'folder' | 'document'
    resource_id: UUID,
    required_permission: str,  # 'read' | 'write' | 'delete'
    folder_id: UUID | None = None,  # for documents: the owning folder_id
) -> None:
    """
    Raise HTTPException(403) if the user does not have the required permission.
    Admins bypass this check entirely.
    """
    if _ADMIN_ROLES.intersection(user.roles):
        return

    effective = await get_effective_permissions(
        db=db,
        user=user,
        resource_type=resource_type,
        resource_id=resource_id,
        folder_id=folder_id,
    )

    if required_permission not in effective:
        raise HTTPException(status_code=403, detail="Insufficient permissions")


async def get_effective_permissions(
    *,
    db: AsyncSession,
    user: UserContext,
    resource_type: str,
    resource_id: UUID,
    folder_id: UUID | None = None,
) -> set[str]:
    """
    Return the set of permissions the user has on the resource.

    Algorithm:
    1. Walk up the folder ancestry via recursive CTE → collect folder permissions
    2. Collect document-level permissions (if resource_type == 'document')
    3. Document permissions override folder permissions for the same principal
    4. Merge: union of permissions from all matching principals
    """
    user_id = user.user_id
    user_roles = user.roles

    # Build principal filter:  user_id OR any of the user's roles
    principal_ids = [user_id] + list(user_roles)
    principal_placeholders = ", ".join(f":p{i}" for i in range(len(principal_ids)))
    principal_params = {f"p{i}": v for i, v in enumerate(principal_ids)}

    # Determine root folder_id for the resource
    if resource_type == "folder":
        root_folder_id = str(resource_id)
    else:
        # document: start from its folder (if any)
        root_folder_id = str(folder_id) if folder_id else None

    # Recursive CTE: ancestor folders
    folder_perms_sql = ""
    if root_folder_id:
        folder_perms_sql = f"""
        WITH RECURSIVE ancestors AS (
            SELECT id, parent_id FROM folders WHERE id = :root_folder_id
            UNION ALL
            SELECT f.id, f.parent_id FROM folders f
            JOIN ancestors a ON f.id = a.parent_id
        )
        SELECT UNNEST(permissions) AS perm
        FROM document_permissions dp
        JOIN ancestors a ON dp.resource_id = a.id
        WHERE dp.resource_type = 'folder'
          AND dp.principal_id IN ({principal_placeholders})
        """

    # Document-level permissions
    doc_perms_sql = ""
    if resource_type == "document":
        doc_perms_sql = f"""
        SELECT UNNEST(permissions) AS perm
        FROM document_permissions
        WHERE resource_type = 'document'
          AND resource_id = :resource_id
          AND principal_id IN ({principal_placeholders})
        """
        # Document-level permissions override (not additive to) folder perms
        # We check document-level first; if any exist, use only those
        result = await db.execute(
            text(doc_perms_sql),
            {"resource_id": str(resource_id), **principal_params},
        )
        doc_perms = {row.perm for row in result}
        if doc_perms:
            return doc_perms

    # Fall back to folder-inherited permissions
    if not folder_perms_sql:
        return set()

    result = await db.execute(
        text(folder_perms_sql),
        {"root_folder_id": root_folder_id, **principal_params},
    )
    return {row.perm for row in result}
