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

    # Génération d'images (ComfyUI / SDXL)
    comfyui_checkpoint: str = "sd_xl_base_1.0.safetensors"
    comfyui_steps: int = 25
    comfyui_width: int = 1024
    comfyui_height: int = 1024
    comfyui_timeout: int = 180   # secondes max pour une génération

    # ─── RunPod (3e palier : GPU cloud pour gros modèles) ───────────────────
    runpod_enabled: bool = False
    runpod_api_key: str = ""
    runpod_pod_id: str = ""             # mode Pod : id à démarrer/arrêter
    runpod_ollama_url: str = ""         # URL Ollama exposée par le pod
    runpod_comfyui_url: str = ""        # URL ComfyUI exposée par le pod
    runpod_start_timeout: int = 300     # s max d'attente au démarrage du pod
    video_hd_workflow_path: str = "config/comfyui_video_hd_workflow.json"

    # Génération de vidéo (ComfyUI / AnimateDiff) — workflow paramétrable par template
    video_workflow_path: str = "config/comfyui_video_workflow.json"
    video_fps: int = 16
    video_default_seconds: int = 10
    video_max_seconds: int = 20
    video_max_frames: int = 320   # garde-fou technique (pas de contenu) anti-OOM
    video_timeout: int = 1800     # 30 min max pour un job vidéo

    # API
    secret_key: str = "changeme"
    api_key: str = ""            # vide = auth désactivée (dev). Obligatoire en prod.
    log_level: str = "info"

    # Home Assistant
    ha_url: str = "http://homeassistant.local:8123"
    ha_token: str = ""

    # Nextcloud (RAG local)
    nextcloud_url: str = ""              # ex. http://192.168.1.50:8080 (sans /remote.php)
    nextcloud_user: str = ""
    nextcloud_password: str = ""         # app password (Paramètres → Sécurité)
    nextcloud_root: str = "/"            # "/" = tout Nextcloud ; ou "/Documents"
    nextcloud_sync_enabled: bool = False
    nextcloud_sync_interval: int = 3600  # secondes entre deux syncs périodiques
    nextcloud_max_file_mb: int = 50      # ignore les fichiers plus gros


settings = Settings()
