from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/gxp_audit_service"
    valkey_url: str = "redis://localhost:6379/0"
    service_name: str = "audit-service"
    client_id: str = "gxp-audit-service"
    client_secret: str = "changeme"
    celery_broker_url: str = "redis://localhost:6379/4"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "changeme"
    minio_secure: bool = False
    audit_retention_years: int = 3
    audit_archive_bucket: str = "gxp-audit-archive"


settings = Settings()
