from __future__ import annotations

import shutil
import subprocess
import zipfile
from ipaddress import ip_address, ip_network
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import UploadFile
from repomind.core.config import PROJECT_ROOT, get_settings
from repomind.core.store import store
from repomind.utils.ignore import IGNORED_DIRS

BLOCKED_NETWORKS = tuple(
    ip_network(value)
    for value in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    )
)


def _safe_repo_name(value: str) -> str:
    stem = Path(urlparse(value).path).stem or Path(value).stem or "repository"
    return "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in stem).strip("-") or "repository"


def _workspace(name: str) -> Path:
    settings = get_settings()
    path = settings.repositories_dir / f"{_safe_repo_name(name)}-{uuid4().hex[:10]}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def _safe_extract(zip_path: Path, destination: Path) -> None:
    settings = get_settings()
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        if len(members) > settings.max_zip_members:
            raise ValueError(f"ZIP contains too many files: {len(members)}")
        compressed = sum(max(member.compress_size, 0) for member in members)
        extracted = sum(max(member.file_size, 0) for member in members)
        if extracted > settings.max_zip_extracted_bytes:
            raise ValueError("ZIP extracted size exceeds configured limit.")
        if compressed and extracted / compressed > settings.max_zip_compression_ratio:
            raise ValueError("ZIP compression ratio exceeds configured limit.")
        for member in members:
            target = destination / member.filename
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError(f"Unsafe zip path: {member.filename}")
            if _is_zip_symlink(member):
                raise ValueError(f"Refusing to extract symlink from ZIP: {member.filename}")
        archive.extractall(destination)


async def ingest_zip(file: UploadFile) -> dict:
    settings = get_settings()
    upload_path = settings.uploads_dir / f"{uuid4().hex}-{file.filename or 'repository.zip'}"
    total = 0
    with upload_path.open("wb") as handle:
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > settings.max_upload_bytes:
                upload_path.unlink(missing_ok=True)
                raise ValueError("Upload exceeds configured size limit.")
            handle.write(chunk)
    workspace = _workspace(file.filename or "upload")
    _safe_extract(upload_path, workspace)
    children = [p for p in workspace.iterdir() if p.is_dir()]
    repo_path = children[0] if len(children) == 1 and not any(workspace.glob("*.*")) else workspace
    return store.create_repository(_safe_repo_name(file.filename or "upload"), "zip", repo_path, file.filename or "")


def ingest_github(url: str) -> dict:
    _validate_git_url(url)
    workspace = _workspace(url)
    try:
        subprocess.run(["git", "clone", "--depth", "1", url, str(workspace)], check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(workspace, ignore_errors=True)
        stderr = exc.stderr.decode(errors="ignore")
        raise ValueError(f"git clone failed: {stderr}") from exc
    return store.create_repository(_safe_repo_name(url), "github", workspace, url)


def ingest_local_path(path: str) -> dict:
    settings = get_settings()
    if not settings.enable_local_path_import:
        raise ValueError("Local path import is disabled. Set REPOMIND_ENABLE_LOCAL_PATH_IMPORT=true for trusted local use.")
    source = Path(path).expanduser()
    if not source.is_absolute():
        source = PROJECT_ROOT / source
    source = source.resolve()
    if not source.exists() or not source.is_dir():
        raise ValueError(f"Local repository path does not exist or is not a directory: {source}")
    if not _is_allowed_local_source(source):
        raise ValueError(f"Local repository path is outside configured allowed roots: {source}")
    workspace = _workspace(source.name)
    shutil.copytree(source, workspace, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*IGNORED_DIRS))
    return store.create_repository(source.name, "local", workspace, str(source))


def _validate_git_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS GitHub clone URLs are allowed.")
    host = (parsed.hostname or "").lower()
    settings = get_settings()
    allowed = settings.parsed_allowed_git_hosts
    if host not in allowed:
        raise ValueError(f"Git host is not allowed: {host}")
    try:
        address = ip_address(host)
    except ValueError:
        return
    if any(address in network for network in BLOCKED_NETWORKS):
        raise ValueError("Git URL resolves to a blocked network address.")


def _is_allowed_local_source(source: Path) -> bool:
    roots = get_settings().parsed_local_import_roots
    return any(_is_relative_to(source, root) for root in roots)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _is_zip_symlink(member: zipfile.ZipInfo) -> bool:
    return (member.external_attr >> 16) & 0o170000 == 0o120000
