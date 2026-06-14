from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:changeme@localhost:5432/gxp_notification_service"
    valkey_url: str = "redis://localhost:6379/0"
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "gxp"
    client_id: str = "gxp-notification-service"
    client_secret: str = "changeme"


settings = Settings()
