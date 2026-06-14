from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings
from gxp_shared.auth.tenant_context import make_tenant_db_dependency

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    pass  # Alembic handles schema + table creation


# Tenant-aware DB dependency: sets search_path = t_{tenant_slug} per request
get_db = make_tenant_db_dependency(AsyncSessionLocal)
