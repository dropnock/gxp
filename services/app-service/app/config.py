from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/gxp_apps"
    valkey_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "changeme"
    minio_secure: bool = False
    keycloak_url: str = "http://localhost:8080"
    client_id: str = "gxp-app-service"
    client_secret: str = "changeme"
    tenant_service_db_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/gxp_tenant"


settings = Settings()
