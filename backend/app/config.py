from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    




    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    app_name: str = "EcoPath API"
    database_url: str = "postgresql+psycopg://ecopath:ecopath@localhost:5432/ecopath"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24
    upload_dir: Path = ROOT / "data" / "uploads"
    model_path: Path = ROOT / "models" / "congestion_xgb.json"
    detector_backend: str = "auto"      # auto | yolo | opencv
    yolo_weights: str = "yolov8n.pt"
    frame_sample_every: int = 5
    max_frames: int = 120
    road_segment_km: float = 0.5
    carbon_limit_kg_per_hour: float = 2500.0   # govt/city CO2 cap used for the eco-friendly verdict
    cors_origins: str = "http://localhost:5173,http://localhost:3000"


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
