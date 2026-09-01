"""Application configuration."""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    llm_model: str = "groq/openai/gpt-oss-20b"
    groq_api_key: str = ""
    openai_api_key: str = ""

    # Database
    database_url: str = f"sqlite+aiosqlite:///{ROOT_DIR / 'data' / 'crm_enquiries.db'}"

    # SuiteCRM
    suitecrm_base_url: str = "https://crm.example.com"
    suitecrm_client_id: str = ""
    suitecrm_client_secret: str = ""
    suitecrm_username: str = ""
    suitecrm_password: str = ""
    suitecrm_mock: bool = True

    # Email
    m365_tenant_id: str = ""
    m365_client_id: str = ""
    m365_client_secret: str = ""
    outbound_from_email: str = "sales@glancyfawcett.com"
    email_mock: bool = True

    # Calendar
    calendar_user_email: str = ""
    default_meeting_duration_minutes: int = 60
    availability_lookahead_days: int = 14
    calendar_mock: bool = True

    # Fathom
    fathom_api_key: str = ""
    fathom_webhook_secret: str = ""
    fathom_mock: bool = True

    # Knowledge Base
    chroma_persist_dir: str = str(ROOT_DIR / "data" / "chroma")
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    knowledge_dir: str = str(ROOT_DIR / "knowledge" / "glancy_faq")

    # App
    api_key: str = "dev-api-key-change-me"
    jwt_secret: str = "dev-jwt-secret-change-me"
    approval_notify_email: str = ""
    app_env: str = "development"
    log_level: str = "INFO"

    crm_field_map_path: str = str(ROOT_DIR / "config" / "crm_field_map.yaml")

    @property
    def async_database_url(self) -> str:
        """Return a SQLAlchemy async driver URL (e.g. postgresql+asyncpg)."""
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_crm_field_map() -> dict:
    path = Path(get_settings().crm_field_map_path)
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
