"""
App page CRUD.

Pages are upserted by page_id (client-generated stable ID).
GrapesJS project JSON (gjs_data) is stored alongside the compiled GXP
component tree (compiled on each save for optimistic runtime reads).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.app import AppPage, GxpApp
from app.services.builder import gjs_to_gxp_components
from gxp_shared.auth.dependencies import UserContext, require_roles

router = APIRouter()

RequiresDev = Annotated[UserContext, Depends(require_roles("gxp-developer", "gxp-admin"))]
RequiresAny = Annotated[UserContext, Depends(require_roles(
    "gxp-user", "gxp-developer", "gxp-admin", "gxp-case-worker",
))]


class PageUpsert(BaseModel):
    name: str
    route: str
    gjs_data: dict[str, Any] = {}
    styles: dict[str, Any] = {}
    sort_order: int = 0


class PageOut(BaseModel):
    id: uuid.UUID
    app_id: uuid.UUID
    page_id: str
    name: str
    route: str
    gjs_data: dict
    components: list
    styles: dict
    sort_order: int
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/{app_id}/pages", response_model=list[PageOut])
async def list_pages(
    app_id: uuid.UUID,
    user: RequiresAny,
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(GxpApp, app_id)
    if not app or not app.is_active:
        raise HTTPException(status_code=404, detail="App not found")
    result = await db.execute(
        select(AppPage)
        .where(AppPage.app_id == app_id)
        .order_by(AppPage.sort_order)
    )
    return result.scalars().all()


@router.put("/{app_id}/pages/{page_id}", response_model=PageOut)
async def upsert_page(
    app_id: uuid.UUID,
    page_id: str,
    body: PageUpsert,
    user: RequiresDev,
    db: AsyncSession = Depends(get_db),
):
    app = await db.get(GxpApp, app_id)
    if not app or not app.is_active:
        raise HTTPException(status_code=404, detail="App not found")
    if app.status not in ("draft", "rejected"):
        raise HTTPException(status_code=409, detail="Only draft or rejected apps can be edited")

    result = await db.execute(
        select(AppPage).where(AppPage.app_id == app_id, AppPage.page_id == page_id)
    )
    page = result.scalar_one_or_none()
    now = datetime.now(tz=timezone.utc)

    # Compile GrapesJS data to GXP component tree
    components = gjs_to_gxp_components(body.gjs_data.get("components", []))

    if page is None:
        page = AppPage(
            id=uuid.uuid4(),
            app_id=app_id,
            page_id=page_id,
            name=body.name,
            route=body.route,
            gjs_data=body.gjs_data,
            components=components,
            styles=body.styles,
            sort_order=body.sort_order,
            updated_at=now,
        )
        db.add(page)
    else:
        page.name = body.name
        page.route = body.route
        page.gjs_data = body.gjs_data
        page.components = components
        page.styles = body.styles
        page.sort_order = body.sort_order
        page.updated_at = now

    app.updated_at = now
    await db.commit()
    await db.refresh(page)
    return page


@router.delete("/{app_id}/pages/{page_id}", status_code=204)
async def delete_page(
    app_id: uuid.UUID,
    page_id: str,
    user: RequiresDev,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AppPage).where(AppPage.app_id == app_id, AppPage.page_id == page_id)
    )
    page = result.scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    await db.delete(page)
    await db.commit()
