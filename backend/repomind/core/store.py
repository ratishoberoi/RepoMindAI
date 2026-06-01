from __future__ import annotations

import json
import time
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from repomind.core.config import get_settings
from repomind.db.models import ArtifactRecord, Base, JobRecord, RepositoryRecord
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker


class RepositoryStore:
    """SQL-backed metadata store for repository, job, and artifact state."""

    def __init__(self, database_url: str | None = None, legacy_path: Path | None = None) -> None:
        settings = get_settings()
        self.database_url = database_url or str(settings.database_url)
        self.legacy_path = legacy_path or settings.data_dir / "metadata.json"
        self._lock = RLock()
        connect_args = (
            {"check_same_thread": False} if self.database_url.startswith("sqlite") else {}
        )
        self.engine = create_engine(self.database_url, future=True, connect_args=connect_args)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False, future=True)
        Base.metadata.create_all(self.engine)
        self._migrate_legacy_json()

    def create_repository(
        self, name: str, source_type: str, path: Path, source: str
    ) -> dict[str, Any]:
        now = time.time()
        repo_id = uuid4().hex
        record = RepositoryRecord(
            id=repo_id,
            name=name,
            source_type=source_type,
            source=source,
            path=str(path),
            status="ingested",
            created_at=now,
            updated_at=now,
            summary={},
            reports={},
            error=None,
            repository_deleted=False,
            repository_deleted_at=None,
            repository_retention_minutes=get_settings().retention_minutes,
        )
        with self._session() as session:
            session.add(record)
            session.commit()
            return _repo_dict(record)

    def update(self, repo_id: str, **fields: Any) -> dict[str, Any]:
        with self._lock, self._session() as session:
            record = session.get(RepositoryRecord, repo_id)
            if record is None:
                raise KeyError(repo_id)
            for key, value in fields.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            record.updated_at = time.time()
            if "analysis_job" in fields and fields["analysis_job"]:
                _upsert_job(session, repo_id, fields["analysis_job"])
            if "reports" in fields and fields["reports"]:
                _sync_artifacts(session, repo_id, fields["reports"])
            session.commit()
            session.refresh(record)
            return _repo_dict(record)

    def get(self, repo_id: str) -> dict[str, Any]:
        with self._session() as session:
            record = session.get(RepositoryRecord, repo_id)
            if record is None:
                raise KeyError(repo_id)
            return _repo_dict(record)

    def list(self) -> list[dict[str, Any]]:
        with self._session() as session:
            records = session.scalars(
                select(RepositoryRecord).order_by(RepositoryRecord.created_at.desc())
            ).all()
            return [_repo_dict(record) for record in records]

    def delete(self, repo_id: str) -> dict[str, Any]:
        with self._lock, self._session() as session:
            record = session.get(RepositoryRecord, repo_id)
            if record is None:
                raise KeyError(repo_id)
            item = _repo_dict(record)
            session.execute(delete(ArtifactRecord).where(ArtifactRecord.repo_id == repo_id))
            session.execute(delete(JobRecord).where(JobRecord.repo_id == repo_id))
            session.delete(record)
            session.commit()
            return item

    def _session(self) -> Session:
        return self.SessionLocal()

    def _migrate_legacy_json(self) -> None:
        if not self.legacy_path.exists():
            return
        with self._lock, self._session() as session:
            has_rows = session.scalar(select(RepositoryRecord.id).limit(1))
            if has_rows:
                return
            payload = json.loads(self.legacy_path.read_text() or '{"repositories": {}}')
            for item in payload.get("repositories", {}).values():
                record = RepositoryRecord(
                    id=item["id"],
                    name=item["name"],
                    source_type=item["source_type"],
                    source=item["source"],
                    path=item["path"],
                    status=item["status"],
                    created_at=item.get("created_at", time.time()),
                    updated_at=item.get("updated_at", time.time()),
                    summary=item.get("summary") or {},
                    reports=item.get("reports") or {},
                    analysis_job=item.get("analysis_job"),
                    error=item.get("error"),
                    repository_deleted=bool(item.get("repository_deleted", False)),
                    repository_deleted_at=item.get("repository_deleted_at"),
                    repository_retention_minutes=item.get(
                        "repository_retention_minutes", get_settings().retention_minutes
                    ),
                )
                session.merge(record)
                if record.analysis_job:
                    _upsert_job(session, record.id, record.analysis_job)
                if record.reports:
                    _sync_artifacts(session, record.id, record.reports)
            session.commit()


def _repo_dict(record: RepositoryRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "source_type": record.source_type,
        "source": record.source,
        "path": record.path,
        "status": record.status,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "summary": record.summary or {},
        "reports": record.reports or {},
        "analysis_job": record.analysis_job,
        "error": record.error,
        "repository_deleted": record.repository_deleted,
        "repository_deleted_at": record.repository_deleted_at,
        "repository_retention_minutes": record.repository_retention_minutes,
    }


def _upsert_job(session: Session, repo_id: str, job: dict[str, Any]) -> None:
    job_id = job["id"]
    record = session.get(JobRecord, job_id)
    if record is None:
        record = JobRecord(
            id=job_id,
            repo_id=repo_id,
            status=job.get("status", "unknown"),
            progress=int(job.get("progress", 0)),
            message=job.get("message", ""),
            created_at=job.get("created_at", time.time()),
            updated_at=job.get("updated_at", time.time()),
        )
        session.add(record)
    else:
        record.status = job.get("status", record.status)
        record.progress = int(job.get("progress", record.progress))
        record.message = job.get("message", record.message)
        record.updated_at = job.get("updated_at", time.time())


def _sync_artifacts(session: Session, repo_id: str, reports: dict[str, str]) -> None:
    session.execute(delete(ArtifactRecord).where(ArtifactRecord.repo_id == repo_id))
    now = time.time()
    for name, path in reports.items():
        artifact_type = "summary" if name.endswith(".json") else "report"
        session.add(
            ArtifactRecord(
                id=f"{repo_id}:{name}",
                repo_id=repo_id,
                name=name,
                artifact_type=artifact_type,
                path=path,
                created_at=now,
            )
        )


store = RepositoryStore()
