from __future__ import annotations

from collections import Counter
from pathlib import Path

LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".sql": "SQL",
    ".md": "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".sh": "Shell",
    ".dockerfile": "Dockerfile",
}


def classify_file(path: Path) -> str:
    if path.name == "Dockerfile" or path.name.endswith(".Dockerfile"):
        return "Dockerfile"
    return LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "Text")


def language_summary(files: list[dict]) -> dict:
    counts = Counter(item["language"] for item in files)
    primary = counts.most_common(1)[0][0] if counts else "Unknown"
    return {"primary": primary, "all": dict(counts)}


def detect_stack(root: Path, files: list[dict]) -> dict:
    names = {Path(item["relative_path"]).name for item in files}
    suffixes = {Path(item["relative_path"]).suffix for item in files}
    frameworks: set[str] = set()
    package_managers: set[str] = set()
    build_tools: set[str] = set()
    ci: set[str] = set()

    if "package.json" in names:
        package_managers.add("npm")
        package = root / "package.json"
        text = package.read_text(errors="ignore") if package.exists() else ""
        if "next" in text:
            frameworks.add("Next.js")
        if "react" in text:
            frameworks.add("React")
        if "vue" in text:
            frameworks.add("Vue")
        if "express" in text:
            frameworks.add("Express")
    if "pnpm-lock.yaml" in names:
        package_managers.add("pnpm")
    if "yarn.lock" in names:
        package_managers.add("yarn")
    if "requirements.txt" in names or "pyproject.toml" in names:
        package_managers.add("pip/uv")
        pytext = "\n".join(
            (root / n).read_text(errors="ignore")
            for n in ["requirements.txt", "pyproject.toml"]
            if (root / n).exists()
        )
        if "fastapi" in pytext.lower():
            frameworks.add("FastAPI")
        if "django" in pytext.lower():
            frameworks.add("Django")
        if "flask" in pytext.lower():
            frameworks.add("Flask")
    if "pom.xml" in names:
        build_tools.add("Maven")
        pom = root / "pom.xml"
        text = pom.read_text(errors="ignore").lower() if pom.exists() else ""
        if "spring-boot" in text or "springframework" in text:
            frameworks.add("Spring")
    if "build.gradle" in names or "build.gradle.kts" in names:
        build_tools.add("Gradle")
        for gradle_name in ("build.gradle", "build.gradle.kts"):
            gradle = root / gradle_name
            text = gradle.read_text(errors="ignore").lower() if gradle.exists() else ""
            if "spring-boot" in text or "springframework" in text:
                frameworks.add("Spring")
    if "go.mod" in names:
        package_managers.add("Go modules")
        go_mod = root / "go.mod"
        text = go_mod.read_text(errors="ignore").lower() if go_mod.exists() else ""
        if "github.com/gin-gonic/gin" in text:
            frameworks.add("Gin")
        if "github.com/go-chi/chi" in text:
            frameworks.add("Chi")
        if "github.com/gofiber/fiber" in text:
            frameworks.add("Fiber")
        if "github.com/labstack/echo" in text:
            frameworks.add("Echo")
    if "Cargo.toml" in names:
        package_managers.add("Cargo")
        cargo = root / "Cargo.toml"
        text = cargo.read_text(errors="ignore").lower() if cargo.exists() else ""
        if "actix-web" in text:
            frameworks.add("Actix Web")
        if "axum" in text:
            frameworks.add("Axum")
        if "rocket" in text:
            frameworks.add("Rocket")
    if "Dockerfile" in names or "docker-compose.yml" in names or "docker-compose.yaml" in names:
        build_tools.add("Docker")
    if any(".github/workflows/" in item["relative_path"] for item in files):
        ci.add("GitHub Actions")
    if ".sql" in suffixes:
        frameworks.add("SQL/database")

    return {
        "frameworks": sorted(frameworks),
        "package_managers": sorted(package_managers),
        "build_tools": sorted(build_tools),
        "ci_cd": sorted(ci),
        "docker": "Docker" in build_tools,
    }
