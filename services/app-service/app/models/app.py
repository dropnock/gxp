"""
App service data models.

GxpApp      — the application entity; goes through draft → under_review → published / rejected
AppPage     — one page within an app; stores GrapesJS project JSON for round-trip editing
              and the compiled GXP component tree for the runtime
AppVersion  — immutable snapshot created on each publish; MinIO key points to frozen schema
AppPermission — per-role access grants (view / edit)
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class GxpApp(Base):
    __tablename__ = "apps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # draft | under_review | published | rejected
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    # ID of the current live AppVersion (NULL until first publish)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    pages: Mapped[list[AppPage]] = relationship("AppPage", back_populates="app", cascade="all, delete-orphan")
    versions: Mapped[list[AppVersion]] = relationship("AppVersion", back_populates="app", cascade="all, delete-orphan")
    permissions: Mapped[list[AppPermission]] = relationship("AppPermission", back_populates="app", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_apps_status", "status"),
        Index("ix_apps_created_by", "created_by"),
    )


class AppPage(Base):
    __tablename__ = "app_pages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("apps.id"), nullable=False)
    page_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    route: Mapped[str] = mapped_column(Text, nullable=False)
    # GrapesJS project JSON (component tree + styles) — used by the portal builder
    gjs_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Compiled GXP ComponentNode tree — used by the runtime renderer
    components: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # CSS rules keyed by selector
    styles: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    app: Mapped[GxpApp] = relationship("GxpApp", back_populates="pages")

    __table_args__ = (
        UniqueConstraint("app_id", "page_id", name="uq_app_page_id"),
        UniqueConstraint("app_id", "route", name="uq_app_page_route"),
        Index("ix_app_pages_app_id", "app_id"),
    )


class AppVersion(Base):
    __tablename__ = "app_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("apps.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Full GXP AppSchema JSON (immutable after creation)
    schema_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # MinIO key: gxp-app-schemas-{slug}/{app_id}/{version}.json
    minio_key: Mapped[str] = mapped_column(Text, nullable=False)
    published_by: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    app: Mapped[GxpApp] = relationship("GxpApp", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("app_id", "version_number", name="uq_app_version"),
        Index("ix_app_versions_app_id", "app_id"),
    )


class AppPermission(Base):
    __tablename__ = "app_permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("apps.id"), nullable=False)
    # Keycloak role name (e.g. 'gxp-user', 'gxp-developer')
    role: Mapped[str] = mapped_column(Text, nullable=False)
    # view | edit
    permission: Mapped[str] = mapped_column(String(8), nullable=False, default="view")
    granted_by: Mapped[str] = mapped_column(Text, nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    app: Mapped[GxpApp] = relationship("GxpApp", back_populates="permissions")

    __table_args__ = (
        UniqueConstraint("app_id", "role", name="uq_app_permission_role"),
    )
