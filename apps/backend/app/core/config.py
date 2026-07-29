from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_database_urls(
    database_url: str,
    database_url_sync: str,
) -> tuple[str, str]:
    """Render/Heroku often provide postgresql:// — async SQLAlchemy needs +asyncpg."""
    async_url = database_url.strip()
    sync_url = database_url_sync.strip()

    if async_url.startswith("postgres://"):
        async_url = "postgresql://" + async_url[len("postgres://") :]
    if sync_url.startswith("postgres://"):
        sync_url = "postgresql://" + sync_url[len("postgres://") :]

    # If only DATABASE_URL is set (common on Render), derive sync URL.
    if not sync_url or sync_url == "postgresql://bmwai:bmwai_secret@localhost:5432/bmwai_db":
        if async_url.startswith("postgresql+asyncpg://"):
            sync_url = "postgresql://" + async_url[len("postgresql+asyncpg://") :]
        elif async_url.startswith("postgresql://"):
            sync_url = async_url

    if async_url.startswith("postgresql://") and "+asyncpg" not in async_url:
        async_url = "postgresql+asyncpg://" + async_url[len("postgresql://") :]

    return async_url, sync_url


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
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    # When true, write/ack endpoints require a valid JWT (production default via ENVIRONMENT)
    require_auth_writes: bool = False
    # Comma-separated extra CORS origins (e.g. https://bmw-demo.vercel.app)
    cors_origins: str = ""

    # App
    environment: str = "development"
    public_api_url: str = "http://127.0.0.1:8000"
    frontend_url: str = "http://localhost:3000"
    upload_dir: str = ""

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
    # Public/CDN base for clip URLs (e.g. https://cdn.example.com or http://localhost:9000)
    cdn_base_url: str = ""
    minio_public_base: str = "http://localhost:9000"
    kafka_bootstrap: str = "localhost:19092"
    kafka_enabled: bool = True
    stripe_secret_key: str = ""
    stripe_success_url: str = "http://localhost:3000/admin/dashboard?billing=success"
    stripe_cancel_url: str = "http://localhost:3000/admin/dashboard?billing=cancel"
    # Optional analytics read replica (falls back to primary)
    database_url_read: str = ""

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # Optional LLM cloud keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Spec Phase 8F — Google OAuth (optional)
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:3000/auth/google/callback"

    # Spec Phase 10 — observability / security
    sentry_dsn: str = ""
    log_json: bool = True
    login_rate_limit: int = 5
    login_rate_window_sec: int = 60
    max_upload_bytes: int = 5 * 1024 * 1024

    # Spec Phase 12A — notifications
    resend_api_key: str = ""
    resend_from_email: str = "alerts@bmwai.dev"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    notify_critical_email_fallback: str = ""  # used when user has no prefs

    # Spec Phase 13 — performance
    db_pool_size: int = 10
    db_max_overflow: int = 20
    ws_max_hz: float = 4.0  # fleet WebSocket fan-out throttle
    telemetry_batch_flush_sec: float = 2.0
    telemetry_batch_enabled: bool = True
    analytics_cache_max_age_sec: int = 30
    assistant_semantic_cache_ttl_sec: int = 300
    assistant_semantic_cache_threshold: float = 0.92
    cv_frame_sample_every: int = 3  # full inference every N frames
    cv_face_gate_enabled: bool = True
    road_seg_full_every_n: int = 5

    weight_signing_secret: str = ""
    tenant_rate_limit: int = 120
    tenant_rate_window_sec: int = 60
    require_model_signatures: bool = False

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

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        async_url, sync_url = _normalize_database_urls(
            self.database_url,
            self.database_url_sync,
        )
        object.__setattr__(self, "database_url", async_url)
        object.__setattr__(self, "database_url_sync", sync_url)


settings = Settings()
