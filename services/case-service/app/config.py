from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/gxp_case"
    valkey_url: str = "redis://localhost:6379/0"
    client_id: str = "gxp-case-service"
    client_secret: str = "changeme"
    opensearch_url: str = "http://localhost:9200"
    # Base URL of the workflow-service for service-to-service calls
    workflow_service_url: str = "http://workflow-service:8000"
    # Base URL of the document-service (used for display purposes only — not called by case-service)
    document_service_url: str = "http://document-service:8000"
    tenant_service_db_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/gxp_tenant"


settings = Settings()
