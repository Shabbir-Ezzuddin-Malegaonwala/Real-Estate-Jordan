# Run the Jordan Real Estate Intelligence API.
# Run from the repo root (C:\Rubicon\Real-Estate-Jordan) so `app` is importable.
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root
python -m pip install -r app\api\requirements.txt
uvicorn app.api.main:app --port 8000 --reload
