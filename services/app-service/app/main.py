from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as v1_router
from app.config import settings
from app.db.session import init_db
from gxp_shared.audit.middleware import AuditMiddleware
from gxp_shared.auth.tenant_context import TenantContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="GXP App Service",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/v1/apps/docs",
    openapi_url="/api/v1/apps/openapi.json",
    redoc_url="/api/v1/apps/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware, valkey_url=settings.valkey_url, service_name="app-service")
app.add_middleware(TenantContextMiddleware, valkey_url=settings.valkey_url)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
@app.get("/api/v1/apps/health")
async def health():
    return {"status": "ok", "service": "app-service"}
