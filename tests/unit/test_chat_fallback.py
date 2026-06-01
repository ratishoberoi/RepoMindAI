from repomind.rag import qa


def test_chat_uses_deterministic_fallback_when_model_missing(monkeypatch):
    monkeypatch.setattr(
        qa.store,
        "get",
        lambda repo_id: {
            "id": repo_id,
            "name": "demo",
            "summary": {
                "repository": {"name": "demo"},
                "statistics": {"routes": 2},
                "stack": {"frameworks": ["FastAPI"]},
                "security": {"findings": [{"severity": "high", "file": "app/security.py"}]},
                "files": [{"relative_path": "app/main.py"}],
            },
        },
    )
    monkeypatch.setattr(
        qa,
        "retrieve",
        lambda repo_id, question: [
            {
                "id": "chunk-1",
                "path": "app/main.py",
                "line_start": 1,
                "line_end": 20,
                "text": "from fastapi import FastAPI",
                "score": 0.9,
                "vector_score": 0.8,
                "rerank_score": 0.7,
            }
        ],
    )

    class MissingModel:
        def generate(self, prompt: str, max_tokens: int = 110) -> str:
            raise RuntimeError("Model path does not exist.")

        def status(self) -> dict:
            return {"loadable": False}

    monkeypatch.setattr(qa, "local_model", lambda: MissingModel())

    answer = qa.answer_question("repo-1", "What are the highest risks?")

    assert answer["answer"]
    assert answer["citations"]
    assert answer["related_files"]
    assert answer["follow_ups"]
    assert answer["model_status"]["mode"] == "deterministic_fallback"
