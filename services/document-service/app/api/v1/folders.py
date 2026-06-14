"""Folder CRUD with permission management."""
from __future__ import annotations

import uuid
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.document import DocumentPermission, Folder
from app.services.permissions import check_permission
from gxp_shared.auth.dependencies import UserContext, get_current_user

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[UUID] = None


class FolderRead(BaseModel):
    id: UUID
    parent_id: Optional[UUID]
    name: str
    path: str
    created_by: str
    created_at: str

    model_config = {"from_attributes": True}


class PermissionGrant(BaseModel):
    principal_type: str  # 'user' | 'role'
    principal_id: str
    permissions: list[str]  # ['read'] | ['read','write'] | ['read','write','delete']


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[FolderRead])
async def list_folders(
    parent_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """List folders. If parent_id is omitted, lists root folders."""
    stmt = select(Folder).where(Folder.parent_id == parent_id).order_by(Folder.name)
    result = await db.execute(stmt)
    folders = result.scalars().all()
    return [_serialize_folder(f) for f in folders]


@router.post("", response_model=FolderRead, status_code=status.HTTP_201_CREATED)
async def create_folder(
    body: FolderCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    # If creating inside a parent, check write access to parent
    if body.parent_id:
        parent = await _get_folder_or_404(db, body.parent_id)
        await check_permission(
            db=db, user=user, resource_type="folder",
            resource_id=body.parent_id, required_permission="write",
        )
        path = f"{parent.path}/{body.name}"
    else:
        path = f"/{body.name}"

    folder = Folder(
        id=uuid.uuid4(),
        parent_id=body.parent_id,
        name=body.name,
        path=path,
        created_by=user.user_id,
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return _serialize_folder(folder)


@router.get("/{folder_id}", response_model=FolderRead)
async def get_folder(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    folder = await _get_folder_or_404(db, folder_id)
    await check_permission(db=db, user=user, resource_type="folder",
                           resource_id=folder_id, required_permission="read")
    return _serialize_folder(folder)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    folder = await _get_folder_or_404(db, folder_id)
    await check_permission(db=db, user=user, resource_type="folder",
                           resource_id=folder_id, required_permission="delete")

    # Prevent deleting non-empty folders
    child_result = await db.execute(select(Folder).where(Folder.parent_id == folder_id).limit(1))
    if child_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Folder is not empty")

    await db.delete(folder)
    await db.commit()


@router.post("/{folder_id}/permissions", status_code=status.HTTP_201_CREATED)
async def grant_folder_permission(
    folder_id: UUID,
    body: PermissionGrant,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Grant a user or role access to a folder (inherits to contained documents)."""
    await _get_folder_or_404(db, folder_id)
    await check_permission(db=db, user=user, resource_type="folder",
                           resource_id=folder_id, required_permission="write")

    perm = DocumentPermission(
        resource_type="folder",
        resource_id=folder_id,
        principal_type=body.principal_type,
        principal_id=body.principal_id,
        permissions=body.permissions,
        created_by=user.user_id,
    )
    db.add(perm)
    await db.commit()
    return {"granted": True}


@router.get("/{folder_id}/permissions")
async def list_folder_permissions(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    await _get_folder_or_404(db, folder_id)
    await check_permission(db=db, user=user, resource_type="folder",
                           resource_id=folder_id, required_permission="read")

    result = await db.execute(
        select(DocumentPermission).where(
            DocumentPermission.resource_type == "folder",
            DocumentPermission.resource_id == folder_id,
        )
    )
    perms = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "principal_type": p.principal_type,
            "principal_id": p.principal_id,
            "permissions": p.permissions,
        }
        for p in perms
    ]


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_folder_or_404(db: AsyncSession, folder_id: UUID) -> Folder:
    result = await db.execute(select(Folder).where(Folder.id == folder_id))
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder


def _serialize_folder(f: Folder) -> dict:
    return {
        "id": str(f.id),
        "parent_id": str(f.parent_id) if f.parent_id else None,
        "name": f.name,
        "path": f.path,
        "created_by": f.created_by,
        "created_at": f.created_at.isoformat() if f.created_at else "",
    }
