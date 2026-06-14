import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DATABASE_URL env var overrides alembic.ini (used by migrate_tenants.py)
db_url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")

# GXP_TENANT_SCHEMA selects which schema to migrate (e.g. "t_dot")
# Defaults to "public" for backwards-compat during initial dev
tenant_schema = os.environ.get("GXP_TENANT_SCHEMA", "public")

try:
    from app.db.session import Base
    import app.models  # noqa: F401 — registers all models
    target_metadata = Base.metadata
except Exception:
    target_metadata = None


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=False,
        version_table=f"alembic_version",
        version_table_schema=tenant_schema,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(db_url, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        # Ensure the tenant schema exists
        await connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{tenant_schema}"'))
        await connection.execute(text(f'SET search_path TO "{tenant_schema}", public'))
        await connection.commit()
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
