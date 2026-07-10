# QA / Edge-Case Test Suite

Adversarial, re-runnable edge-case coverage for the Jordan Real Estate Intelligence
Platform — engine, HTTP API, and frontend. Findings and repros live in
[`../docs/qa-report.md`](../docs/qa-report.md).

## Layout

| File | Target | Needs |
|------|--------|-------|
| `test_engine_edge_cases.py` | `app.engine` (pure Python) | nothing (imports the engine) |
| `test_api_edge_cases.py` | `http://localhost:8000` | API running (else skips) |
| `e2e_frontend.py` | `http://localhost:5173` | frontend + Playwright (else skips) |
| `run_all.py` | all of the above | as available |
| `conftest.py` | puts repo root on `sys.path` | — |

## One command

```bash
# from the repo root  (C:\Rubicon\Real-Estate-Jordan)
python tests/run_all.py
```

## Run a suite on its own

```bash
# Engine — no server needed
python -m pytest tests/test_engine_edge_cases.py -v

# API — start the server first
python -m uvicorn app.api.main:app --port 8000      # (in another shell)
python -m pytest tests/test_api_edge_cases.py -v

# E2E — start the frontend + install the browser once
cd app/web && npm run dev                            # serves http://localhost:5173
pip install playwright && python -m playwright install chromium
python tests/e2e_frontend.py                         # standalone, prints a summary
python -m pytest tests/e2e_frontend.py -v            # or via pytest (skips if web down)
```

## Overrides

| Env var | Default | Used by |
|---------|---------|---------|
| `JORDAN_API_URL` | `http://127.0.0.1:8000` | API suite |
| `JORDAN_WEB_URL` | `http://localhost:5173` | E2E suite |
| `JORDAN_RE_DB` | `db/jordan_re.sqlite` | the API process itself |

## Notes

- The engine suite is fully self-contained and always runs.
- The API and E2E suites **skip cleanly** (never error) when their server is down, so
  `run_all.py` stays green in a partial environment.
- One engine test is an `xfail` — it documents a real crash (`area_m2=0` →
  `ZeroDivisionError`, see qa-report BUG-1). It will flip to an "unexpected pass" the
  moment the engine is hardened, which is the signal to remove the marker.
- E2E screenshots are written to `tests/screenshots/`.
