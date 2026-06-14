import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text, ARRAY, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "platform"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(63), unique=True, nullable=False)
    name = Column(Text, nullable=False)
    keycloak_realm = Column(Text, unique=True, nullable=False)
    status = Column(
        String(20),
        nullable=False,
        default="active",
        # CHECK (status IN ('active','suspended','deprovisioning'))
    )
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    suspended_at = Column(DateTime(timezone=True), nullable=True)

    grants_as_requester = relationship(
        "CrossTenantGrant",
        foreign_keys="CrossTenantGrant.requesting_tenant_id",
        back_populates="requesting_tenant",
    )
    grants_as_granter = relationship(
        "CrossTenantGrant",
        foreign_keys="CrossTenantGrant.granting_tenant_id",
        back_populates="granting_tenant",
    )


class CrossTenantGrant(Base):
    __tablename__ = "cross_tenant_grants"
    __table_args__ = {"schema": "platform"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requesting_tenant_id = Column(UUID(as_uuid=True), ForeignKey("platform.tenants.id"), nullable=False)
    granting_tenant_id = Column(UUID(as_uuid=True), ForeignKey("platform.tenants.id"), nullable=False)
    resource_type = Column(Text, nullable=False)  # 'document' | 'app' | 'workflow_definition' | 'case'
    resource_id = Column(UUID(as_uuid=True), nullable=False)
    permissions = Column(ARRAY(Text), nullable=False)  # ['read'] | ['read','write']
    requested_by = Column(UUID(as_uuid=True), nullable=False)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        # CHECK (status IN ('pending','approved','revoked','expired'))
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    requesting_tenant = relationship(
        "Tenant",
        foreign_keys=[requesting_tenant_id],
        back_populates="grants_as_requester",
    )
    granting_tenant = relationship(
        "Tenant",
        foreign_keys=[granting_tenant_id],
        back_populates="grants_as_granter",
    )


class CatalogTemplate(Base):
    __tablename__ = "catalog_templates"
    __table_args__ = {"schema": "platform"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(Text, nullable=False)  # 'app' | 'workflow' | 'dmn' | 'case_type'
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String, nullable=False, default="1")
    schema_json = Column(JSONB, nullable=False)
    published_by = Column(UUID(as_uuid=True), nullable=False)
    published_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    tags = Column(ARRAY(Text), nullable=True)
