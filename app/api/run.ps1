# Run the Jordan Real Estate Intelligence API.
# Run from the repo root so `app` is importable.
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

# Serve the CANONICAL database — the one the auto-update pipeline keeps fresh
# (pipeline/run_all.py writes here). Without this the API would fall back to a
# stale local copy and the UI would show week-old prices. Override by setting
# JORDAN_RE_DB before running. See docs/LIVE-DATA.md.
if (-not $env:JORDAN_RE_DB) {
  $env:JORDAN_RE_DB = "C:/Rubicon/Real-Estate-Jordan/db/jordan_re.sqlite"
}
if (-not $env:ALLOWED_ORIGINS) {
  $env:ALLOWED_ORIGINS = "http://localhost:5055,http://127.0.0.1:5055,http://localhost:5173,http://127.0.0.1:5173"
}
Write-Host "Serving DB: $($env:JORDAN_RE_DB)"

python -m pip install -r app\api\requirements.txt
uvicorn app.api.main:app --port 8000 --reload
