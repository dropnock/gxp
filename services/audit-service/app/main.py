from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as v1_router
from app.config import settings
from app.consumers.audit_consumer import start_consumer_background_task
from gxp_shared.audit.middleware import AuditMiddleware
from gxp_shared.auth.tenant_context import TenantContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = await start_consumer_background_task(settings.valkey_url)
    yield
    task.cancel()


app = FastAPI(title="GXP Audit Service", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AuditMiddleware must be added AFTER TenantContextMiddleware so that
# request.state.{user_id, tenant_slug} are already populated when audit runs.
# Starlette middleware executes in reverse-registration order.
app.add_middleware(
    AuditMiddleware,
    valkey_url=settings.valkey_url,
    service_name="audit-service",
)
app.add_middleware(TenantContextMiddleware, valkey_url=settings.valkey_url)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "audit-service"}
