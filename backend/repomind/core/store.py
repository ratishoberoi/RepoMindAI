from __future__ import annotations

import json
import time
from datetime import date, datetime
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from repomind.core.config import get_settings
from repomind.db.models import (
    ArtifactRecord,
    Base,
    ExternalAccountRecord,
    JobRecord,
    MembershipRecord,
    OAuthStateRecord,
    OrganizationRecord,
    RepositoryRecord,
    TeamRecord,
    UserRecord,
)
from sqlalchemy import create_engine, delete, inspect, select, text
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
        self._ensure_schema_compatibility()
        self.ensure_default_tenant()
        self._migrate_legacy_json()

    def create_repository(
        self,
        name: str,
        source_type: str,
        path: Path,
        source: str,
        org_id: str = "default",
        created_by_user_id: str | None = "local-admin",
    ) -> dict[str, Any]:
        now = time.time()
        repo_id = uuid4().hex
        record = RepositoryRecord(
            id=repo_id,
            org_id=org_id,
            created_by_user_id=created_by_user_id,
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

    def create_user_with_org(
        self,
        email: str,
        name: str,
        password_hash: str | None,
        auth_provider: str = "password",
        provider_subject: str | None = None,
        org_name: str | None = None,
    ) -> dict[str, Any]:
        now = time.time()
        user_id = uuid4().hex
        org_id = uuid4().hex
        org_slug = _slug(org_name or email.split("@", 1)[0]) or f"org-{org_id[:8]}"
        with self._lock, self._session() as session:
            existing = session.scalar(select(UserRecord).where(UserRecord.email == email.lower()))
            if existing is not None:
                raise ValueError("A user with this email already exists.")
            suffix = 1
            base_slug = org_slug
            while session.scalar(
                select(OrganizationRecord).where(OrganizationRecord.slug == org_slug)
            ):
                suffix += 1
                org_slug = f"{base_slug}-{suffix}"
            org = OrganizationRecord(
                id=org_id,
                slug=org_slug,
                name=org_name or f"{name}'s Workspace",
                plan="team",
                created_at=now,
                updated_at=now,
            )
            user = UserRecord(
                id=user_id,
                email=email.lower(),
                name=name,
                auth_provider=auth_provider,
                provider_subject=provider_subject,
                password_hash=password_hash,
                created_at=now,
                updated_at=now,
            )
            membership = MembershipRecord(
                id=f"{org_id}:{user_id}:org",
                org_id=org_id,
                user_id=user_id,
                team_id=None,
                role="owner",
                created_at=now,
            )
            session.add_all([org, user, membership])
            session.commit()
            return {
                "user": _user_dict(user),
                "organization": _org_dict(org),
                "membership": _membership_dict(membership),
            }

    def get_user_by_email(self, email: str) -> dict[str, Any]:
        with self._session() as session:
            record = session.scalar(select(UserRecord).where(UserRecord.email == email.lower()))
            if record is None:
                raise KeyError(email)
            return _user_dict(record)

    def get_user(self, user_id: str) -> dict[str, Any]:
        with self._session() as session:
            record = session.get(UserRecord, user_id)
            if record is None:
                raise KeyError(user_id)
            return _user_dict(record)

    def memberships_for_user(self, user_id: str) -> list[dict[str, Any]]:
        with self._session() as session:
            records = session.scalars(
                select(MembershipRecord).where(MembershipRecord.user_id == user_id)
            ).all()
            return [_membership_dict(record) for record in records]

    def assert_membership(self, user_id: str, org_id: str) -> dict[str, Any]:
        with self._session() as session:
            record = session.scalar(
                select(MembershipRecord).where(
                    MembershipRecord.user_id == user_id,
                    MembershipRecord.org_id == org_id,
                )
            )
            if record is None:
                raise KeyError(org_id)
            return _membership_dict(record)

    def upsert_external_account(
        self,
        org_id: str,
        user_id: str,
        provider: str,
        provider_subject: str,
        username: str | None = None,
        access_token_encrypted: str | None = None,
        refresh_token_encrypted: str | None = None,
        installation_id: str | None = None,
        scopes: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = time.time()
        with self._lock, self._session() as session:
            record = session.scalar(
                select(ExternalAccountRecord).where(
                    ExternalAccountRecord.provider == provider,
                    ExternalAccountRecord.provider_subject == provider_subject,
                )
            )
            if record is None:
                record = ExternalAccountRecord(
                    id=uuid4().hex,
                    org_id=org_id,
                    user_id=user_id,
                    provider=provider,
                    provider_subject=provider_subject,
                    username=username,
                    access_token_encrypted=access_token_encrypted,
                    refresh_token_encrypted=refresh_token_encrypted,
                    installation_id=installation_id,
                    scopes=scopes or [],
                    metadata_json=metadata or {},
                    created_at=now,
                    updated_at=now,
                )
                session.add(record)
            else:
                record.org_id = org_id
                record.user_id = user_id
                record.username = username
                record.access_token_encrypted = access_token_encrypted
                record.refresh_token_encrypted = refresh_token_encrypted
                record.installation_id = installation_id
                record.scopes = scopes or []
                record.metadata_json = metadata or {}
                record.updated_at = now
            session.commit()
            return _external_account_dict(record)

    def get_external_account(self, org_id: str, user_id: str, provider: str) -> dict[str, Any]:
        with self._session() as session:
            record = session.scalar(
                select(ExternalAccountRecord).where(
                    ExternalAccountRecord.org_id == org_id,
                    ExternalAccountRecord.user_id == user_id,
                    ExternalAccountRecord.provider == provider,
                )
            )
            if record is None:
                raise KeyError(provider)
            return _external_account_dict(record)

    def create_oauth_state(
        self,
        provider: str,
        state: str,
        redirect_uri: str,
        org_id: str | None,
        user_id: str | None,
        expires_at: float,
    ) -> dict[str, Any]:
        now = time.time()
        with self._lock, self._session() as session:
            record = OAuthStateRecord(
                state=state,
                provider=provider,
                org_id=org_id,
                user_id=user_id,
                redirect_uri=redirect_uri,
                created_at=now,
                expires_at=expires_at,
            )
            session.add(record)
            session.commit()
            return _oauth_state_dict(record)

    def pop_oauth_state(self, provider: str, state: str) -> dict[str, Any]:
        with self._lock, self._session() as session:
            record = session.get(OAuthStateRecord, state)
            if record is None or record.provider != provider:
                raise KeyError(state)
            item = _oauth_state_dict(record)
            session.delete(record)
            session.commit()
            if item["expires_at"] < time.time():
                raise KeyError(state)
            return item

    def delete_account(self, user_id: str, org_id: str) -> dict[str, Any]:
        with self._lock, self._session() as session:
            self.assert_membership(user_id, org_id)
            repos = session.scalars(
                select(RepositoryRecord).where(RepositoryRecord.org_id == org_id)
            ).all()
            repo_items = [_repo_dict(record) for record in repos]
            for record in repos:
                session.execute(delete(ArtifactRecord).where(ArtifactRecord.repo_id == record.id))
                session.execute(delete(JobRecord).where(JobRecord.repo_id == record.id))
                session.delete(record)
            session.execute(
                delete(ExternalAccountRecord).where(
                    ExternalAccountRecord.org_id == org_id,
                    ExternalAccountRecord.user_id == user_id,
                )
            )
            session.execute(delete(MembershipRecord).where(MembershipRecord.user_id == user_id))
            user = session.get(UserRecord, user_id)
            if user:
                session.delete(user)
            if not session.scalar(
                select(MembershipRecord.id).where(MembershipRecord.org_id == org_id).limit(1)
            ):
                org = session.get(OrganizationRecord, org_id)
                if org:
                    session.delete(org)
            session.commit()
            return {"repositories": repo_items, "user_id": user_id, "org_id": org_id}

    def update(self, repo_id: str, **fields: Any) -> dict[str, Any]:
        with self._lock, self._session() as session:
            record = session.get(RepositoryRecord, repo_id)
            if record is None:
                raise KeyError(repo_id)
            normalized_fields: dict[str, Any] = {}
            for key, value in fields.items():
                if hasattr(record, key):
                    if key in {"summary", "reports", "analysis_job"}:
                        value = _json_safe(value)
                    normalized_fields[key] = value
                    setattr(record, key, value)
            record.updated_at = time.time()
            if "analysis_job" in normalized_fields and normalized_fields["analysis_job"]:
                _upsert_job(session, repo_id, normalized_fields["analysis_job"])
            if "reports" in normalized_fields and normalized_fields["reports"]:
                _sync_artifacts(session, repo_id, normalized_fields["reports"])
            session.commit()
            session.refresh(record)
            return _repo_dict(record)

    def get(self, repo_id: str) -> dict[str, Any]:
        with self._session() as session:
            record = session.get(RepositoryRecord, repo_id)
            if record is None:
                raise KeyError(repo_id)
            return _repo_dict(record)

    def get_for_org(self, repo_id: str, org_id: str) -> dict[str, Any]:
        repo = self.get(repo_id)
        if repo.get("org_id") != org_id:
            raise KeyError(repo_id)
        return repo

    def list(self, org_id: str | None = None) -> list[dict[str, Any]]:
        with self._session() as session:
            statement = select(RepositoryRecord).order_by(RepositoryRecord.created_at.desc())
            if org_id:
                statement = statement.where(RepositoryRecord.org_id == org_id)
            records = session.scalars(statement).all()
            return [_repo_dict(record) for record in records]

    def ensure_default_tenant(self) -> None:
        now = time.time()
        with self._session() as session:
            org = session.get(OrganizationRecord, "default")
            if org is None:
                session.add(
                    OrganizationRecord(
                        id="default",
                        slug="default",
                        name="Default Workspace",
                        plan="local",
                        created_at=now,
                        updated_at=now,
                    )
                )
            user = session.get(UserRecord, "local-admin")
            if user is None:
                session.add(
                    UserRecord(
                        id="local-admin",
                        email="local-admin@repomind.local",
                        name="Local Admin",
                        auth_provider="api_key",
                        provider_subject="local-admin",
                        created_at=now,
                        updated_at=now,
                    )
                )
            team = session.get(TeamRecord, "default-core")
            if team is None:
                session.add(
                    TeamRecord(
                        id="default-core",
                        org_id="default",
                        slug="core",
                        name="Core Engineering",
                        created_at=now,
                    )
                )
            membership = session.get(MembershipRecord, "default:local-admin:org")
            if membership is None:
                session.add(
                    MembershipRecord(
                        id="default:local-admin:org",
                        org_id="default",
                        user_id="local-admin",
                        team_id=None,
                        role="owner",
                        created_at=now,
                    )
                )
            session.commit()

    def tenant_summary(self) -> dict[str, Any]:
        with self._session() as session:
            return {
                "organizations": session.query(OrganizationRecord).count(),
                "users": session.query(UserRecord).count(),
                "teams": session.query(TeamRecord).count(),
                "memberships": session.query(MembershipRecord).count(),
            }

    def repository_counts(self) -> dict[str, int]:
        with self._session() as session:
            rows = session.scalars(select(RepositoryRecord.status)).all()
        counts: dict[str, int] = {}
        for status in rows:
            counts[status] = counts.get(status, 0) + 1
        counts["total"] = len(rows)
        return counts

    def job_counts(self) -> dict[str, int]:
        with self._session() as session:
            rows = session.scalars(select(JobRecord.status)).all()
        counts: dict[str, int] = {}
        for status in rows:
            counts[status] = counts.get(status, 0) + 1
        counts["total"] = len(rows)
        return counts

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

    def _ensure_schema_compatibility(self) -> None:
        """Apply minimal forward-compatible DDL for existing local databases.

        Alembic owns production migrations. This guard keeps older SQLite/local installs
        bootable when the application starts before an operator has run migrations.
        """
        inspector = inspect(self.engine)
        if "repositories" not in inspector.get_table_names():
            return
        columns = {column["name"] for column in inspector.get_columns("repositories")}
        statements = []
        if "org_id" not in columns:
            statements.append(
                "ALTER TABLE repositories ADD COLUMN org_id VARCHAR(64) NOT NULL DEFAULT 'default'"
            )
        if "created_by_user_id" not in columns:
            statements.append(
                "ALTER TABLE repositories ADD COLUMN created_by_user_id VARCHAR(64) DEFAULT 'local-admin'"
            )
        if not statements:
            pass
        with self.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))
            if statements:
                connection.execute(
                    text(
                        "UPDATE repositories SET org_id = 'default' WHERE org_id IS NULL OR org_id = ''"
                    )
                )
                connection.execute(
                    text(
                        "UPDATE repositories SET created_by_user_id = 'local-admin' "
                        "WHERE created_by_user_id IS NULL OR created_by_user_id = ''"
                    )
                )
        user_columns = (
            {column["name"] for column in inspector.get_columns("users")}
            if "users" in inspector.get_table_names()
            else set()
        )
        if user_columns and "password_hash" not in user_columns:
            with self.engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(256)"))

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
                    org_id=item.get("org_id", "default"),
                    created_by_user_id=item.get("created_by_user_id", "local-admin"),
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
        "org_id": record.org_id,
        "created_by_user_id": record.created_by_user_id,
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


def _user_dict(record: UserRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "email": record.email,
        "name": record.name,
        "auth_provider": record.auth_provider,
        "provider_subject": record.provider_subject,
        "password_hash": record.password_hash,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _org_dict(record: OrganizationRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "slug": record.slug,
        "name": record.name,
        "plan": record.plan,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _membership_dict(record: MembershipRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "org_id": record.org_id,
        "user_id": record.user_id,
        "team_id": record.team_id,
        "role": record.role,
        "created_at": record.created_at,
    }


def _external_account_dict(record: ExternalAccountRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "org_id": record.org_id,
        "user_id": record.user_id,
        "provider": record.provider,
        "provider_subject": record.provider_subject,
        "username": record.username,
        "access_token_encrypted": record.access_token_encrypted,
        "refresh_token_encrypted": record.refresh_token_encrypted,
        "installation_id": record.installation_id,
        "scopes": record.scopes or [],
        "metadata": record.metadata_json or {},
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _oauth_state_dict(record: OAuthStateRecord) -> dict[str, Any]:
    return {
        "state": record.state,
        "provider": record.provider,
        "org_id": record.org_id,
        "user_id": record.user_id,
        "redirect_uri": record.redirect_uri,
        "created_at": record.created_at,
        "expires_at": record.expires_at,
    }


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")[:80]


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=_json_default))


def _json_default(value: Any) -> str:
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value)


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
