from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("REPOMIND_DATA_DIR", str(ROOT / "data"))
os.environ.setdefault("REPOMIND_REPORT_DIR", str(ROOT / "reports"))

