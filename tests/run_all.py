"""Single entrypoint for the whole QA suite.

Runs, in order:
  1. engine edge cases     tests/test_engine_edge_cases.py
  2. existing engine tests  app/engine/test_pipeline.py   (21 baseline tests)
  3. API edge cases         tests/test_api_edge_cases.py   (skips if API is down)
  4. E2E frontend           tests/e2e_frontend.py          (skips if web/playwright absent)

Exit code is non-zero if any suite hard-fails. Suites that SKIP (API/web/playwright not
available) do not fail the run — they are reported as skipped.

Run from the repo root:  python tests/run_all.py
Pre-reqs for the full run:
  * API up:   python -m uvicorn app.api.main:app --port 8000
  * Web up:   cd app/web && npm run dev         (serves http://localhost:5173)
  * Browser:  pip install playwright && python -m playwright install chromium
"""

from __future__ import annotations

import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)


def _run(label: str, argv: list[str]) -> int:
    print("\n" + "=" * 70)
    print(f">>> {label}")
    print("=" * 70)
    return subprocess.run(argv, cwd=_ROOT).returncode


def main() -> int:
    py = sys.executable
    results: dict[str, int] = {}

    results["engine edge + baseline"] = _run(
        "Engine suites (pytest)",
        [py, "-m", "pytest", "-q",
         os.path.join("tests", "test_engine_edge_cases.py"),
         os.path.join("app", "engine", "test_pipeline.py")])

    results["api edge"] = _run(
        "API suite (pytest — skips if API down)",
        [py, "-m", "pytest", "-q", os.path.join("tests", "test_api_edge_cases.py")])

    results["e2e frontend"] = _run(
        "E2E frontend (playwright — skips if web/browser absent)",
        [py, os.path.join("tests", "e2e_frontend.py")])

    print("\n" + "=" * 70)
    print("OVERALL")
    print("=" * 70)
    hard_fail = False
    for label, code in results.items():
        # pytest exit 5 = "no tests collected" (all skipped) — treat as non-fatal.
        ok = code in (0, 5)
        status = "OK" if ok else f"FAIL (exit {code})"
        hard_fail = hard_fail or not ok
        print(f"  {label:28} {status}")
    print("=" * 70)
    return 1 if hard_fail else 0


if __name__ == "__main__":
    sys.exit(main())
