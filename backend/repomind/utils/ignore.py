from pathlib import Path

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    "vendor",
    "coverage",
    ".next",
    "target",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "data",
    "reports",
    "sample_repos",
}

IGNORED_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".woff",
    ".woff2",
    ".ttf",
    ".mp4",
    ".mov",
    ".sqlite",
    ".sqlite3",
}

IGNORED_PATH_PARTS = {
    "compiled",
    "fixtures",
    "snapshots",
}

IGNORED_FILENAMES = {
    "BENCHMARK_RESULTS.md",
    "FINAL_VERIFICATION_REPORT.md",
    "PRODUCT_REVIEW.md",
    "RELEASE_CANDIDATE_REPORT.md",
}


def should_ignore(path: Path, root: Path | None = None) -> bool:
    parts = path.relative_to(root).parts if root else path.parts
    if any(part in IGNORED_DIRS for part in parts):
        return True
    if any(part in IGNORED_PATH_PARTS for part in parts):
        return True
    if path.name in IGNORED_FILENAMES:
        return True
    if path.name.endswith(".min.js") or path.name.endswith(".bundle.js"):
        return True
    return path.suffix.lower() in IGNORED_SUFFIXES
