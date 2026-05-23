import os
from pathlib import Path

import pytest
from repomind.analysis.analyzer import analyze_repository
from repomind.core.store import store
from repomind.ingestion.ingestor import ingest_local_path
from repomind.rag.qa import answer_question

pytestmark = pytest.mark.skipif(
    os.environ.get("REPOMIND_RUN_MODEL_TESTS") != "1",
    reason="Full analysis pipeline requires local embedding and qwen-judge model runtime.",
)


def test_local_folder_analysis_end_to_end(tmp_path: Path) -> None:
    source = tmp_path / "python_fastapi_example"
    source.mkdir()
    (source / "main.py").write_text(
        "from fastapi import FastAPI\n\n"
        "app = FastAPI()\n\n"
        "@app.get('/health')\n"
        "def health():\n"
        "    return {'ok': True}\n\n"
        "@app.post('/items')\n"
        "def create_item():\n"
        "    password = 'example-secret'\n"
        "    return {'created': bool(password)}\n"
    )
    (source / "requirements.txt").write_text("fastapi\n")

    repo = ingest_local_path(str(source))
    summary = analyze_repository(repo)
    store.update(repo["id"], status="complete", summary=summary, reports=summary["reports"])

    assert summary["languages"]["primary"] == "Python"
    assert "FastAPI" in summary["stack"]["frameworks"]
    assert summary["statistics"]["routes"] >= 2
    assert summary["security"]["findings"]
    assert Path(summary["reports"]["ARCHITECTURE.md"]).exists()

    answer = answer_question(repo["id"], "Where are API routes implemented?")
    assert answer["citations"]
