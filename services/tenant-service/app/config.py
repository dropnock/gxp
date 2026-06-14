from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Tenant service's own database (hosts platform.tenants, cross_tenant_grants, catalog_templates)
    database_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/gxp_tenant"

    # URLs for each service database so provisioner can create schemas there
    app_service_db_url: str = "postgresql+asyncpg://postgres:changeme@postgres-app:5432/gxp_apps"
    workflow_service_db_url: str = "postgresql+asyncpg://postgres:changeme@postgres-workflow:5432/gxp_workflow"
    case_service_db_url: str = "postgresql+asyncpg://postgres:changeme@postgres-case:5432/gxp_case"
    document_service_db_url: str = "postgresql+asyncpg://postgres:changeme@postgres-document:5432/gxp_documents"
    audit_service_db_url: str = "postgresql+asyncpg://postgres:changeme@postgres-audit:5432/gxp_audit"

    # Keycloak
    keycloak_url: str = "http://keycloak:8080"
    keycloak_platform_realm: str = "gxp-platform"
    keycloak_admin_client_id: str = "admin-cli"
    keycloak_admin_username: str = "admin"
    keycloak_admin_password: str = "changeme_dev"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "changeme"
    minio_secure: bool = False

    # OpenSearch
    opensearch_url: str = "http://opensearch:9200"

    # Valkey / Redis
    valkey_url: str = "redis://localhost:6379/6"
    celery_broker_url: str = "redis://localhost:6379/6"

    # JWT validation for platform realm
    keycloak_realm: str = "gxp-platform"
    client_id: str = "gxp-tenant-service"
    client_secret: str = "changeme"


settings = Settings()
