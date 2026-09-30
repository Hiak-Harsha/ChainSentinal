import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, configurable via environment variables."""

    # Application
    APP_NAME: str = "ChainSentinel"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server (bind to 0.0.0.0 in container/production, supports Render $PORT)
    HOST: str = os.environ.get("CS_HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", os.environ.get("CS_PORT", 8000)))

    # Authentication & Session Security
    API_KEY: str = ""
    SESSION_SECRET: str = ""
    SESSION_COOKIE_NAME: str = "cs_session"
    SESSION_MAX_AGE_SECONDS: int = 86400  # 24 hours
    OPERATOR_PASSWORD: str = ""

    # CORS Configuration (comma-separated list of allowed origins, e.g. "https://app.example.com")
    CORS_ORIGINS: str = ""

    # Upload limits
    MAX_UPLOAD_BYTES: int = 524_288_000  # 500 MB

    # Paths (auto-detect serverless environment like Vercel or AWS Lambda where only /tmp is writable)
    _is_serverless: bool = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    DATA_DIR: Path = Path(os.environ.get("CS_DATA_DIR", "/tmp/chainsentinel/data" if _is_serverless else "data"))
    DB_PATH: Path = Path(os.environ.get("CS_DB_PATH", "/tmp/chainsentinel/data/chainsentinel.duckdb" if _is_serverless else "data/chainsentinel.duckdb"))
    SQLITE_PATH: Path = Path(os.environ.get("CS_SQLITE_PATH", "/tmp/chainsentinel/data/chainsentinel.sqlite" if _is_serverless else "data/chainsentinel.sqlite"))
    MODELS_DIR: Path = Path(os.environ.get("CS_MODELS_DIR", "/tmp/chainsentinel/data/models" if _is_serverless else "data/models"))
    EXPORTS_DIR: Path = Path(os.environ.get("CS_EXPORTS_DIR", "/tmp/chainsentinel/data/exports" if _is_serverless else "data/exports"))
    FRONTEND_DIR: Path = Path(os.environ.get("CS_FRONTEND_DIR", "../frontend/out"))

    # ML
    SEED: int = 42
    MODEL_VERSION: str = "0.1.0"

    # GeoIP
    GEOIP_DB_PATH: Path = Path(os.environ.get(
        "CS_GEOIP_DB_PATH",
        "data/geoip/dbip-country-asn-lite.mmdb" if Path("data/geoip/dbip-country-asn-lite.mmdb").exists() else "data/reference/geoip"
    ))

    model_config = {"env_prefix": "CS_", "env_file": ".env", "extra": "ignore"}


settings = Settings()

