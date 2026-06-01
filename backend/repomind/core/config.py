from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").is_file() and (candidate / "backend" / "repomind").is_dir():
            return candidate
    return Path(__file__).resolve().parents[3]


PROJECT_ROOT = find_project_root()


def _project_path(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)


def _resolve_path(path: Path) -> Path:
    expanded = Path(path).expanduser()
    if expanded.is_absolute():
        return expanded
    return (PROJECT_ROOT / expanded).resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REPOMIND_",
        env_file=str(PROJECT_ROOT / ".env"),
        extra="ignore",
        populate_by_name=True,
    )

    env: str = "development"
    data_dir: Path = Field(
        default_factory=lambda: _project_path("data"),
        validation_alias=AliasChoices("REPOMIND_DATA_DIR", "DATA_DIR"),
    )
    reports_dir: Path = Field(
        default_factory=lambda: _project_path("reports"),
        validation_alias=AliasChoices("REPOMIND_REPORTS_DIR", "REPOMIND_REPORT_DIR", "REPORTS_DIR", "REPORT_DIR"),
    )
    index_dir: Path = Field(
        default_factory=lambda: _project_path("data", "indexes"),
        validation_alias=AliasChoices("REPOMIND_INDEX_DIR", "REPOMIND_INDEXES_DIR", "INDEX_DIR", "INDEXES_DIR"),
    )
    chroma_dir: Path = Field(
        default_factory=lambda: _project_path("data", "chroma"),
        validation_alias=AliasChoices("REPOMIND_CHROMA_DIR", "REPOMIND_CHROMA_PATH", "CHROMA_DIR", "CHROMA_PATH"),
    )
    upload_dir: Path = Field(
        default_factory=lambda: _project_path("data", "uploads"),
        validation_alias=AliasChoices("REPOMIND_UPLOAD_DIR", "REPOMIND_UPLOADS_DIR", "UPLOAD_DIR", "UPLOADS_DIR"),
    )
    frontend_origin: str = "http://localhost:3000"
    api_key: str | None = None
    require_api_key: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    model_path: Path = Field(
        default_factory=lambda: _project_path("models", "qwen-judge"),
        validation_alias=AliasChoices("REPOMIND_MODEL_PATH", "MODEL_PATH"),
    )
    enable_model_inference: bool = True
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    auto_delete_after_analysis: bool = True
    retention_minutes: int = 60
    cleanup_interval_seconds: int = 300

    max_file_bytes: int = 1_000_000
    max_repository_files: int = 50_000
    max_indexed_chunks: int = 100_000
    chunk_size: int = 1800
    chunk_overlap: int = 220
    embedding_batch_size: int = 64
    chroma_upsert_batch_size: int = 1000
    analysis_workers: int = 2
    enable_local_path_import: bool = False
    local_import_allowed_roots: str = Field(default_factory=lambda: str(PROJECT_ROOT))
    allowed_git_hosts: str = "github.com"
    max_upload_bytes: int = 50_000_000
    max_zip_members: int = 20_000
    max_zip_extracted_bytes: int = 250_000_000
    max_zip_compression_ratio: int = 100
    redact_secrets: bool = True
    trust_remote_model_code: bool = False

    @model_validator(mode="after")
    def normalize_and_validate_paths(self) -> "Settings":
        self.data_dir = _resolve_path(self.data_dir)
        self.reports_dir = _resolve_path(self.reports_dir)
        self.index_dir = _resolve_path(self.index_dir)
        self.chroma_dir = _resolve_path(self.chroma_dir)
        self.upload_dir = _resolve_path(self.upload_dir)
        self.model_path = _resolve_path(self.model_path)
        if self.model_path.name != "qwen-judge":
            raise ValueError("RepoMindAI only supports qwen-judge local inference. Set REPOMIND_MODEL_PATH to that checkpoint.")
        return self

    @property
    def parsed_local_import_roots(self) -> list[Path]:
        roots = [item.strip() for item in self.local_import_allowed_roots.split(",") if item.strip()]
        return [_resolve_path(Path(root)) for root in roots]

    @property
    def parsed_allowed_git_hosts(self) -> set[str]:
        return {item.strip().lower() for item in self.allowed_git_hosts.split(",") if item.strip()}

    @property
    def report_dir(self) -> Path:
        return self.reports_dir

    @property
    def chroma_path(self) -> Path:
        return self.chroma_dir

    @property
    def repositories_dir(self) -> Path:
        return self.data_dir / "repositories"

    @property
    def uploads_dir(self) -> Path:
        return self.upload_dir

    @property
    def indexes_dir(self) -> Path:
        return self.index_dir

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    def ensure_dirs(self) -> None:
        for path in [
            self.data_dir,
            self.reports_dir,
            self.repositories_dir,
            self.upload_dir,
            self.index_dir,
            self.exports_dir,
            self.chroma_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
