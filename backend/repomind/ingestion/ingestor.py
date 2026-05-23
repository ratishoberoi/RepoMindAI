from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import UploadFile
from repomind.core.config import get_settings
from repomind.core.store import store
from repomind.utils.ignore import IGNORED_DIRS


def _safe_repo_name(value: str) -> str:
    stem = Path(urlparse(value).path).stem or Path(value).stem or "repository"
    return "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in stem).strip("-") or "repository"


def _workspace(name: str) -> Path:
    settings = get_settings()
    path = settings.repositories_dir / f"{_safe_repo_name(name)}-{uuid4().hex[:10]}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def _safe_extract(zip_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = destination / member.filename
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError(f"Unsafe zip path: {member.filename}")
        archive.extractall(destination)


async def ingest_zip(file: UploadFile) -> dict:
    settings = get_settings()
    upload_path = settings.uploads_dir / f"{uuid4().hex}-{file.filename or 'repository.zip'}"
    with upload_path.open("wb") as handle:
        while chunk := await file.read(1024 * 1024):
            handle.write(chunk)
    workspace = _workspace(file.filename or "upload")
    _safe_extract(upload_path, workspace)
    children = [p for p in workspace.iterdir() if p.is_dir()]
    repo_path = children[0] if len(children) == 1 and not any(workspace.glob("*.*")) else workspace
    return store.create_repository(_safe_repo_name(file.filename or "upload"), "zip", repo_path, file.filename or "")


def ingest_github(url: str) -> dict:
    workspace = _workspace(url)
    try:
        subprocess.run(["git", "clone", "--depth", "1", url, str(workspace)], check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(workspace, ignore_errors=True)
        stderr = exc.stderr.decode(errors="ignore")
        raise ValueError(f"git clone failed: {stderr}") from exc
    return store.create_repository(_safe_repo_name(url), "github", workspace, url)


def ingest_local_path(path: str) -> dict:
    source = Path(path).expanduser().resolve()
    if not source.exists() or not source.is_dir():
        raise ValueError(f"Local repository path does not exist or is not a directory: {source}")
    workspace = _workspace(source.name)
    shutil.copytree(source, workspace, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*IGNORED_DIRS))
    return store.create_repository(source.name, "local", workspace, str(source))
