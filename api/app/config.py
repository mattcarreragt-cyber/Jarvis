from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    database_url: str = "postgresql+asyncpg://jarvis:changeme@postgres:5432/jarvis"
    redis_url: str = "redis://redis:6379/0"
    qdrant_url: str = "http://qdrant:6333"

    # Compute node (Kubuntu)
    kubuntu_url: str = "http://localhost:11434"
    kubuntu_mac: str = ""
    kubuntu_wol_enabled: bool = False
    kubuntu_wol_timeout: int = 60

    # Backends
    ollama_base_url: str = "http://localhost:11434"
    comfyui_base_url: str = "http://localhost:8188"
    whisper_base_url: str = "http://localhost:9000"
    piper_base_url: str = "http://localhost:5000"

    # API
    secret_key: str = "changeme"
    api_key: str = ""            # vide = auth désactivée (dev). Obligatoire en prod.
    log_level: str = "info"

    # Home Assistant
    ha_url: str = "http://homeassistant.local:8123"
    ha_token: str = ""


settings = Settings()
