from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

TEST_RUNTIME = Path(tempfile.mkdtemp(prefix="repomind-tests-")).resolve()
os.environ["REPOMIND_DATA_DIR"] = str(TEST_RUNTIME / "data")
os.environ["REPOMIND_REPORTS_DIR"] = str(TEST_RUNTIME / "reports")
os.environ["REPOMIND_INDEX_DIR"] = str(TEST_RUNTIME / "data" / "indexes")
os.environ["REPOMIND_CHROMA_DIR"] = str(TEST_RUNTIME / "data" / "chroma")
os.environ["REPOMIND_UPLOAD_DIR"] = str(TEST_RUNTIME / "data" / "uploads")
os.environ["REPOMIND_DATABASE_URL"] = f"sqlite:///{TEST_RUNTIME / 'data' / 'repomind-test.db'}"
os.environ["REPOMIND_MODEL_PATH"] = str(TEST_RUNTIME / "models" / "qwen-judge")
os.environ["REPOMIND_ENABLE_MODEL_INFERENCE"] = "false"
os.environ["REPOMIND_API_KEY"] = "test-api-key"
os.environ["REPOMIND_ENABLE_LOCAL_PATH_IMPORT"] = "true"
os.environ["REPOMIND_LOCAL_IMPORT_ALLOWED_ROOTS"] = tempfile.gettempdir()


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(TEST_RUNTIME, ignore_errors=True)
