from pathlib import Path
from typing import Any
import yaml
import sys
from pydantic_settings import BaseSettings
from loguru import logger


def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    BASE_DIR: Path = get_base_dir()
    CONFIG_PATH: Path = BASE_DIR / "config" / "config.yaml"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:050811@127.0.0.1:5432/furnace"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # External Services
    REALTIME_SERVICE_URL: str = "http://localhost:8000"
    REALTIME_SERVICE_TIMEOUT: float = 30.0
    HISTORY_SERVICE_URL: str = "http://localhost:8001"
    HISTORY_SERVICE_TIMEOUT: float = 30.0

    # Model paths
    HEATING_MODEL_PATH: str = "heating_bilstm.pth"
    HEATING_FEAT_SCALER_PATH: str = "heating_feat_scaler.pkl"
    HEATING_TARGET_SCALER_PATH: str = "heating_target_scaler.pkl"
    COOLING_MODEL_PATH: str = "cooling_bilstm.pth"
    COOLING_FEAT_SCALER_PATH: str = "cooling_feat_scaler.pkl"
    COOLING_TARGET_SCALER_PATH: str = "cooling_target_scaler.pkl"
    HOLDING_MODEL_PATH: str = "holding_bilstm.pth"
    HOLDING_FEAT_SCALER_PATH: str = "holding_feat_scaler.pkl"
    HOLDING_TARGET_SCALER_PATH: str = "holding_target_scaler.pkl"

    # Alarm settings
    CORE_TEMP_THRESHOLD: float = 810.0

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "logs/app.log"
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "7 days"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_from_yaml()

    def _load_from_yaml(self):
        if self.CONFIG_PATH.exists():
            try:
                with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)
                self._apply_config(config_data)
                logger.info(f"Loaded configuration from {self.CONFIG_PATH}")
            except Exception as e:
                logger.warning(f"Failed to load config from {self.CONFIG_PATH}: {e}")

    def _apply_config(self, config_data: dict[str, Any]):
        if "server" in config_data:
            server = config_data["server"]
            self.HOST = server.get("host", self.HOST)
            self.PORT = server.get("port", self.PORT)
            self.DEBUG = server.get("debug", self.DEBUG)

        if "database" in config_data:
            db = config_data["database"]
            self.DATABASE_URL = db.get("url", self.DATABASE_URL)
            self.DATABASE_ECHO = db.get("echo", self.DATABASE_ECHO)
            self.DATABASE_POOL_SIZE = db.get("pool_size", self.DATABASE_POOL_SIZE)
            self.DATABASE_MAX_OVERFLOW = db.get("max_overflow", self.DATABASE_MAX_OVERFLOW)

        if "external_services" in config_data:
            ext = config_data["external_services"]
            if "realtime" in ext:
                self.REALTIME_SERVICE_URL = ext["realtime"].get("base_url", self.REALTIME_SERVICE_URL)
                self.REALTIME_SERVICE_TIMEOUT = ext["realtime"].get("timeout", self.REALTIME_SERVICE_TIMEOUT)
            if "history" in ext:
                self.HISTORY_SERVICE_URL = ext["history"].get("base_url", self.HISTORY_SERVICE_URL)
                self.HISTORY_SERVICE_TIMEOUT = ext["history"].get("timeout", self.HISTORY_SERVICE_TIMEOUT)

        if "model" in config_data:
            model = config_data["model"]
            self.HEATING_MODEL_PATH = model.get("heating_model_path", self.HEATING_MODEL_PATH)
            self.HEATING_FEAT_SCALER_PATH = model.get("heating_feat_scaler_path", self.HEATING_FEAT_SCALER_PATH)
            self.HEATING_TARGET_SCALER_PATH = model.get("heating_target_scaler_path", self.HEATING_TARGET_SCALER_PATH)
            self.COOLING_MODEL_PATH = model.get("cooling_model_path", self.COOLING_MODEL_PATH)
            self.COOLING_FEAT_SCALER_PATH = model.get("cooling_feat_scaler_path", self.COOLING_FEAT_SCALER_PATH)
            self.COOLING_TARGET_SCALER_PATH = model.get("cooling_target_scaler_path", self.COOLING_TARGET_SCALER_PATH)
            self.HOLDING_MODEL_PATH = model.get("holding_model_path", self.HOLDING_MODEL_PATH)
            self.HOLDING_FEAT_SCALER_PATH = model.get("holding_feat_scaler_path", self.HOLDING_FEAT_SCALER_PATH)
            self.HOLDING_TARGET_SCALER_PATH = model.get("holding_target_scaler_path", self.HOLDING_TARGET_SCALER_PATH)

        if "alarm" in config_data:
            self.CORE_TEMP_THRESHOLD = config_data["alarm"].get("core_temp_threshold", self.CORE_TEMP_THRESHOLD)

        if "logging" in config_data:
            log = config_data["logging"]
            self.LOG_LEVEL = log.get("level", self.LOG_LEVEL)
            self.LOG_FILE_PATH = log.get("file_path", self.LOG_FILE_PATH)
            self.LOG_ROTATION = log.get("rotation", self.LOG_ROTATION)
            self.LOG_RETENTION = log.get("retention", self.LOG_RETENTION)


settings = Settings()
