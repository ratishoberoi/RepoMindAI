from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REPOMIND_", env_file=".env", extra="ignore")

    env: str = "development"
    data_dir: Path = Path("/home/ratish/RepoMindAI/data")
    report_dir: Path = Path("/home/ratish/RepoMindAI/reports")
    chroma_path: Path = Path("/home/ratish/RepoMindAI/data/chroma")
    frontend_origin: str = "http://localhost:3000"

    model_path: Path = Field(default=Path("/home/ratish/Forge/models/qwen-judge"))
    enable_model_inference: bool = True
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    auto_delete_after_analysis: bool = True
    retention_minutes: int = 60
    cleanup_interval_seconds: int = 300

    max_file_bytes: int = 1_000_000
    chunk_size: int = 1800
    chunk_overlap: int = 220
    embedding_batch_size: int = 64
    chroma_upsert_batch_size: int = 1000

    @model_validator(mode="after")
    def enforce_single_model(self) -> "Settings":
        required = Path("/home/ratish/Forge/models/qwen-judge")
        if self.model_path != required:
            raise ValueError(f"RepoMindAI only supports local inference from {required}")
        return self

    @property
    def repositories_dir(self) -> Path:
        return self.data_dir / "repositories"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def indexes_dir(self) -> Path:
        return self.data_dir / "indexes"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    def ensure_dirs(self) -> None:
        for path in [
            self.data_dir,
            self.report_dir,
            self.repositories_dir,
            self.uploads_dir,
            self.indexes_dir,
            self.exports_dir,
            self.chroma_path,
        ]:
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
