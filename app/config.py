from pathlib import Path
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "F1 Season Calculator"
    debug: bool = False

    database_path: Path = PROJECT_ROOT / "instance" / "championships.db"
    data_folder: Path = PROJECT_ROOT / "data"
    seasons_folder: Path = PROJECT_ROOT / "data" / "seasons"
    templates_folder: Path = PROJECT_ROOT / "app" / "templates"
    static_folder: Path = PROJECT_ROOT / "app" / "static"
    static_dist_folder: Path = PROJECT_ROOT / "app" / "static" / "dist"

    cache_ttl_seconds: int = 3600
    cache_maxsize: int = 1024

    request_timeout_seconds: float = 30.0

    default_season: int | None = Field(
        default=None,
        description="If unset, the highest year with a seasons/{year}.json is used.",
    )

    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def instance_folder(self) -> Path:
        return self.database_path.parent


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
