from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://bmwai:bmwai_secret@localhost:5432/bmwai_db"
    database_url_sync: str = "postgresql://bmwai:bmwai_secret@localhost:5432/bmwai_db"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Security
    secret_key: str = "change-this-to-a-real-random-string-in-production"
    access_token_expire_minutes: int = 60

    # App
    environment: str = "development"

    # Kuksa VSS
    kuksa_host: str = "localhost"
    kuksa_port: int = 55555

    # Ollama LLM
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"

    # Storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket_events: str = "safety-events"
    minio_bucket_heatmaps: str = "xai-heatmaps"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # Optional LLM cloud keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Phase 1 — driver monitoring model assets (paths relative to repo / absolute)
    dlib_landmark_path: str = ""
    yolo_driver_model_path: str = ""
    ml_models_dir: str = ""

    # Phase 2 — road understanding
    seg_road_model_path: str = ""
    yolo_road_model_path: str = ""  # optional box detector for later modules
    pedestrian_temporal_model_path: str = ""
    midas_model_type: str = ""  # default MiDaS_small via ml.road_understanding.config
    depth_meters_scale: float | None = None
    depth_meters_offset: float | None = None
    ml_device: str = ""


settings = Settings()
