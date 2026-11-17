"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_FILE = BASE_DIR / "app" / "data" / "properties.json"
DEFAULT_FRONTEND_DIR = BASE_DIR / "frontend"


@dataclass(frozen=True)
class Settings:
    """Runtime settings decoupled from application logic."""

    app_name: str
    environment: str
    host: str
    port: int
    data_file_path: Path
    frontend_dir: Path
    model_path: str | None
    model_version: str | None


def load_settings() -> Settings:
    """Load and validate application configuration from environment variables."""
    environment = os.getenv("APP_ENV", "development").strip() or "development"
    host = os.getenv("APP_HOST", "0.0.0.0").strip() or "0.0.0.0"

    raw_port = os.getenv("APP_PORT", "8000").strip()
    try:
        port = int(raw_port)
        if not (1 <= port <= 65535):
            raise ValueError("Port must be between 1 and 65535.")
    except ValueError as exc:
        raise RuntimeError(f"Invalid APP_PORT configuration '{raw_port}': {exc}") from exc

    raw_data_path = os.getenv("DATA_FILE_PATH", "").strip()
    data_file_path = Path(raw_data_path) if raw_data_path else DEFAULT_DATA_FILE

    raw_frontend_dir = os.getenv("FRONTEND_DIR", "").strip()
    frontend_dir = Path(raw_frontend_dir) if raw_frontend_dir else DEFAULT_FRONTEND_DIR

    raw_model_path = os.getenv("MODEL_PATH", "").strip()
    model_path = raw_model_path or None

    raw_model_version = os.getenv("MODEL_VERSION", "").strip()
    model_version = raw_model_version or None

    return Settings(
        app_name="House Price Predictor",
        environment=environment,
        host=host,
        port=port,
        data_file_path=data_file_path,
        frontend_dir=frontend_dir,
        model_path=model_path,
        model_version=model_version,
    )
