from pathlib import Path

from repomind.analysis.analyzer import analyze_repository
from repomind.core.store import store
from repomind.ingestion.ingestor import ingest_local_path
from repomind.rag.qa import answer_question


def test_local_folder_analysis_end_to_end() -> None:
    repo = ingest_local_path("/home/ratish/RepoMindAI/sample_repos/python_fastapi_example")
    summary = analyze_repository(repo)
    store.update(repo["id"], status="complete", summary=summary, reports=summary["reports"])

    assert summary["languages"]["primary"] == "Python"
    assert "FastAPI" in summary["stack"]["frameworks"]
    assert summary["statistics"]["routes"] >= 2
    assert summary["security"]["findings"]
    assert Path(summary["reports"]["ARCHITECTURE.md"]).exists()

    answer = answer_question(repo["id"], "Where are API routes implemented?")
    assert answer["citations"]

