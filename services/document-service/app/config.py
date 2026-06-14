from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/gxp_document_service"
    valkey_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "changeme"
    minio_secure: bool = False

    # ClamAV
    clamav_host: str = "localhost"
    clamav_port: int = 3310

    # OpenSearch
    opensearch_url: str = "http://localhost:9200"

    # Apache Tika (text extraction for OpenSearch indexing)
    tika_url: str = "http://tika:9998"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/3"

    # Service identity
    client_id: str = "gxp-document-service"
    client_secret: str = "changeme"

    # Presigned URL expiry (seconds)
    presign_expiry_seconds: int = 300

    tenant_service_db_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/gxp_tenant"


settings = Settings()
