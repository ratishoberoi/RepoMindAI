from __future__ import annotations

import pytest

from scripts.prove_capability import (
    _high_confidence_expected_file,
    _rank_expected_files,
    validate_accuracy,
)
from scripts.scale_validate import (
    aggregate_summaries,
    completed_batches,
    enforce_regression_gates,
    interleave_corpus,
    render_batch_report,
)


def test_scale_summary_aggregation_weights_accuracy_by_passed_repositories() -> None:
    summary = aggregate_summaries(
        [
            {
                "repositories_attempted": 100,
                "repositories_passed": 100,
                "repositories_failed": 0,
                "failure_rate": 0.0,
                "mean_citation_accuracy": 0.8,
                "mean_retrieval_accuracy": 0.75,
                "mean_architecture_correctness": 0.9,
                "language_mix": {"Python": 50, "Go": 50},
                "size_mix": {"small": 80, "medium": 20},
                "top_bottlenecks": [{"stage": "indexing", "seconds": 30.0}],
            },
            {
                "repositories_attempted": 50,
                "repositories_passed": 25,
                "repositories_failed": 25,
                "failure_rate": 0.5,
                "mean_citation_accuracy": 0.6,
                "mean_retrieval_accuracy": 0.7,
                "mean_architecture_correctness": 0.8,
                "language_mix": {"Rust": 50},
                "size_mix": {"large": 50},
                "top_bottlenecks": [{"stage": "indexing", "seconds": 20.0}],
            },
        ]
    )

    assert summary["repositories_attempted"] == 150
    assert summary["repositories_passed"] == 125
    assert summary["failure_rate"] == 0.167
    assert summary["mean_citation_accuracy"] == 0.76
    assert summary["mean_retrieval_accuracy"] == 0.74
    assert summary["mean_architecture_correctness"] == 0.88
    assert summary["language_mix"] == {"Python": 50, "Go": 50, "Rust": 50}
    assert summary["top_bottlenecks"] == [{"stage": "indexing", "seconds": 50.0}]


def test_scale_corpus_interleaves_languages() -> None:
    corpus = interleave_corpus(
        [
            [{"language": "Python", "url": "python-1"}, {"language": "Python", "url": "python-2"}],
            [{"language": "Go", "url": "go-1"}, {"language": "Go", "url": "go-2"}],
        ]
    )

    assert [item["url"] for item in corpus] == ["python-1", "go-1", "python-2", "go-2"]


def test_resume_ignores_failed_complete_batches(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("scripts.scale_validate.SCALE_ROOT", tmp_path)
    batch_dir = tmp_path / "batches" / "batch_001"
    batch_dir.mkdir(parents=True)
    (batch_dir / "summary.json").write_text(
        """{
          "repositories_attempted": 100,
          "repositories_failed": 1,
          "mean_citation_accuracy": 0.9,
          "mean_retrieval_accuracy": 0.9,
          "mean_architecture_correctness": 0.9
        }"""
    )

    assert completed_batches(100) == set()


def test_scale_regression_gate_stops_on_quality_drop() -> None:
    with pytest.raises(SystemExit) as exc:
        enforce_regression_gates(
            {
                "mean_citation_accuracy": 0.74,
                "mean_retrieval_accuracy": 0.80,
                "mean_architecture_correctness": 0.82,
            }
        )

    assert "mean_citation_accuracy=0.74 < 0.75" in str(exc.value)


def test_scale_regression_gate_stops_on_any_failure() -> None:
    with pytest.raises(SystemExit) as exc:
        enforce_regression_gates(
            {
                "repositories_failed": 1,
                "mean_citation_accuracy": 0.90,
                "mean_retrieval_accuracy": 0.90,
                "mean_architecture_correctness": 0.90,
            }
        )

    assert "repositories_failed=1 != 0" in str(exc.value)


def test_accuracy_validation_does_not_penalize_repositories_without_benchmark_signals() -> None:
    result = validate_accuracy(
        {
            "stack": {"package_managers": [], "frameworks": []},
            "statistics": {"files": 4},
            "security": {"findings": []},
            "architecture": {"summary": "Small utility repository.", "route_files": []},
            "languages": {"primary": "TypeScript"},
        },
        {
            "manifest_files": [],
            "security_signals": [],
            "expected_files": {"routes": []},
            "extension_counts": [[".ts", 1]],
        },
    )

    assert result["applicability"] == "no_independent_signals"
    assert result["correctness"] == 1.0


def test_auth_expected_file_detection_does_not_match_author_substrings() -> None:
    assert not _high_confidence_expected_file(
        "authentication",
        "src/report/render/markdown.rs",
        "let author_name = frontmatter.author;",
    )
    assert _high_confidence_expected_file(
        "authentication",
        "src/AuthController.php",
        "function login() { return $this->authenticate(); }",
    )


def test_expected_file_ranking_prefers_implementation_paths() -> None:
    ranked = _rank_expected_files(
        "authentication",
        [
            "internal/server/container_server.go",
            "internal/auth/middleware.go",
            "docs/authentication.md",
            "internal/auth/middleware_test.go",
        ],
    )

    assert ranked[0] == "internal/auth/middleware.go"


def test_scale_batch_report_includes_required_metrics(tmp_path) -> None:
    path = tmp_path / "batch_001.md"
    summary = {
        "batch_number": 1,
        "repositories_attempted": 1,
        "repositories_passed": 1,
        "repositories_failed": 0,
        "failure_rate": 0.0,
        "mean_citation_accuracy": 0.8,
        "mean_retrieval_accuracy": 0.8,
        "mean_architecture_correctness": 0.85,
        "memory": {"max_rss_mb_peak": 512.0},
        "timings": {
            "indexing_seconds": 10.0,
            "embedding_seconds": 3.0,
            "graph_stack_seconds": 2.0,
            "analysis_seconds": 20.0,
        },
        "language_mix": {"Python": 1},
        "size_mix": {"small": 1},
        "top_bottlenecks": [{"stage": "indexing", "seconds": 10.0}],
        "failures": [],
    }

    render_batch_report(
        summary,
        [{"url": "https://github.com/example/repo", "timeout_seconds": 180, "total_seconds": 10}],
        path,
    )

    content = path.read_text(encoding="utf-8")
    assert "Citation accuracy: 0.800" in content
    assert "Retrieval accuracy: 0.800" in content
    assert "Architecture correctness: 0.850" in content
    assert "Fixes Retained" in content
    assert "Recovered architecture correctness" in content
