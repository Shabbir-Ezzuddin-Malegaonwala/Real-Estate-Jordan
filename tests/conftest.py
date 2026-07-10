"""Put the repo root on sys.path so `import app.engine...` works regardless of how
pytest is invoked (python -m pytest, pytest, or from any CWD)."""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
