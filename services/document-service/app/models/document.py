"""
Document service data model.

Hierarchy: Folder (self-referential tree) → Document → DocumentVersion
Permissions apply to folders or documents; inheritance walks up the tree
via a recursive CTE in app/services/permissions.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY, BigInteger, Boolean, DateTime, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("folders.id"), nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. /contracts/2024 (denormalized for display)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    children: Mapped[list[Folder]] = relationship("Folder", back_populates="parent")
    parent: Mapped[Folder | None] = relationship("Folder", back_populates="children", remote_side=[id])
    documents: Mapped[list[Document]] = relationship("Document", back_populates="folder")
    permissions: Mapped[list[DocumentPermission]] = relationship(
        "DocumentPermission",
        primaryjoin="and_(DocumentPermission.resource_type=='folder', foreign(DocumentPermission.resource_id)==Folder.id)",
        viewonly=True,
    )

    __table_args__ = (
        Index("ix_folders_parent_id", "parent_id"),
        Index("ix_folders_path", "path"),
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folder_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("folders.id"), nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    # Set to the latest clean version; NULL while first upload is still scanning
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    folder: Mapped[Folder | None] = relationship("Folder", back_populates="documents")
    versions: Mapped[list[DocumentVersion]] = relationship("DocumentVersion", back_populates="document", order_by="DocumentVersion.version_number")

    __table_args__ = (
        Index("ix_documents_folder_id", "folder_id"),
        Index("ix_documents_created_by", "created_by"),
    )


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    minio_bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    minio_key: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # pending → scanning → clean | infected | error
    av_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    av_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_by: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    document: Mapped[Document] = relationship("Document", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_doc_version"),
        Index("ix_document_versions_document_id", "document_id"),
        Index("ix_document_versions_av_status", "av_status"),
    )


class DocumentPermission(Base):
    """
    Grants a principal (user or role) specific permissions on a folder or document.
    Document-level grants override inherited folder-level grants.
    """
    __tablename__ = "document_permissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # 'folder' or 'document'
    resource_type: Mapped[str] = mapped_column(String(16), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # 'user' or 'role'
    principal_type: Mapped[str] = mapped_column(String(8), nullable=False)
    principal_id: Mapped[str] = mapped_column(Text, nullable=False)  # user sub or role name
    # e.g. ['read'], ['read','write'], ['read','write','delete']
    permissions: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_doc_perms_resource", "resource_type", "resource_id"),
        Index("ix_doc_perms_principal", "principal_type", "principal_id"),
    )
