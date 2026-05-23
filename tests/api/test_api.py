from pathlib import Path

from repomind.core.config import get_settings
from repomind.core.store import store
from repomind.main import health, import_local_repository
from repomind.schemas import LocalPathRequest


def test_health_endpoint() -> None:
    assert health()["status"] == "ok"


def test_local_import_uses_configured_workspace(tmp_path: Path) -> None:
    source = tmp_path / "sample_repo"
    source.mkdir()
    (source / "README.md").write_text("# Sample\n")

    response = import_local_repository(LocalPathRequest(path=str(source)))
    repo = store.get(response["id"])
    workspace = Path(repo["path"])

    assert response["source_type"] == "local"
    assert workspace.exists()
    assert workspace.is_relative_to(get_settings().repositories_dir)
