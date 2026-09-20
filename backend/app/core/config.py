"""ChainSentinel core configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, configurable via environment variables."""

    # Application
    APP_NAME: str = "ChainSentinel"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Authentication
    API_KEY: str = ""

    # Upload limits
    MAX_UPLOAD_BYTES: int = 524_288_000  # 500 MB

    # Paths
    DATA_DIR: Path = Path("data")
    DB_PATH: Path = Path("data/chainsentinel.duckdb")
    SQLITE_PATH: Path = Path("data/chainsentinel.sqlite")
    MODELS_DIR: Path = Path("data/models")
    FRONTEND_DIR: Path = Path("../frontend/out")

    # ML
    SEED: int = 42
    MODEL_VERSION: str = "0.1.0"

    # GeoIP
    GEOIP_DB_PATH: Path = Path("data/reference/geoip")

    model_config = {"env_prefix": "CS_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
