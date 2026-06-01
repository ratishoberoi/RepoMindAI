from scripts.platform_benchmark import bottlenecks, render_markdown


def test_benchmark_ranks_bottlenecks_and_renders_report() -> None:
    ranked = bottlenecks({"analysis": 3.0, "graph": 1.0, "retrieval": 0.5})
    markdown = render_markdown(
        [
            {
                "tier": "tiny",
                "name": "sample",
                "file_count": 12,
                "analysis_seconds": 3.0,
                "max_rss_mb": 256,
                "status": "passed",
                "bottlenecks": ranked,
            }
        ]
    )

    assert ranked[0]["stage"] == "analysis"
    assert "RepoMindAI Performance Benchmark" in markdown
    assert "| tiny | sample | 12 | 3.0s | 256 | analysis | passed |" in markdown
