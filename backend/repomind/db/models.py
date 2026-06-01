from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RepositoryRecord(Base):
    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    reports: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    analysis_job: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    repository_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    repository_deleted_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    repository_retention_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)


class JobRecord(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    updated_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)


class ArtifactRecord(Base):
    __tablename__ = "repository_artifacts"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)
