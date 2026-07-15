"""Central configuration for the Jordan Real-Estate Assistant backend.

Everything tunable is an env var with a sensible free-tier default, so the app
runs with nothing but a GROQ_API_KEY. See README.md for the full list.

This is a STANDALONE app, separate from the recommendation app. It reuses two
things from that app (per the "reuse, don't rebuild" mandate): the pricing
ENGINE (imported in-process) and the ONE canonical DATABASE. Both live in the
recommendation repo, located as a sibling by default and overridable via the
RECO_REPO env var — so the two apps stay physically decoupled.
"""

from __future__ import annotations

import os
from pathlib import Path

# app/assistant/config.py -> parents[2] == the repo root, where the SINGLE .env
# lives. All secrets (DATABASE_URL for the recommendation API + GROQ_API_KEY for
# the assistant) are kept in that one root .env — one place for every key.
APP_ROOT = Path(__file__).resolve().parents[2]

# Load the root .env so GROQ_API_KEY (and any optional keys) are available.
# Real env vars always win over .env values.
try:
    from dotenv import load_dotenv

    _env = APP_ROOT / ".env"
    if _env.exists():
        load_dotenv(_env, override=False)
except Exception:  # dotenv is optional; env vars still work without it
    pass

# The recommendation repo (source of the engine + canonical DB). Now that the
# assistant lives INSIDE this repo, RECO_REPO is the repo root itself
# (app/assistant/config.py -> parents[2]). Override with RECO_REPO if needed.
RECO_REPO = Path(os.environ.get("RECO_REPO", str(Path(__file__).resolve().parents[2])))

# The ONE canonical database (team no-duplicate-data rule). 52k listings with
# lat/lng spanning all of Jordan, plus POIs, yields, macro series and building
# cost. Read-only. Defaults to the canonical enriched DB; override via JORDAN_RE_DB.
DB_PATH = os.environ.get("JORDAN_RE_DB", str(RECO_REPO / "db" / "jordan_re_new.sqlite"))

# --- Groq (free tier) -------------------------------------------------------
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
# Primary model: best tool-calling on Groq's free tier, 128k context.
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# Model FALLBACK CHAIN. Rate limits on Groq are PER-MODEL (each model has its own
# TPM/RPM bucket), so when the primary is throttled we rotate to the next model —
# which multiplies effective throughput and keeps the assistant answering. All of
# these are tool-calling capable production models with large contexts. Order =
# quality-first, then fast/cheap. Override with GROQ_MODELS (comma-separated).
_DEFAULT_CHAIN = (
    "llama-3.3-70b-versatile,"   # 70B, best quality (300K TPM)
    "openai/gpt-oss-120b,"       # 120B, high quality, separate bucket (250K TPM)
    "openai/gpt-oss-20b,"        # 20B, very fast (250K TPM)
    "llama-3.1-8b-instant"       # 8B, fastest, last-resort (250K TPM)
)
GROQ_MODELS = [m.strip() for m in os.environ.get("GROQ_MODELS", _DEFAULT_CHAIN).split(",") if m.strip()]
# Guarantee the primary is first and unique.
GROQ_MODELS = [GROQ_MODEL] + [m for m in GROQ_MODELS if m != GROQ_MODEL]

# Cheap/fast auxiliary model for the text-to-SQL step.
GROQ_FAST_MODEL = os.environ.get("GROQ_FAST_MODEL", "llama-3.1-8b-instant")
GROQ_TEMPERATURE = float(os.environ.get("GROQ_TEMPERATURE", "0.2"))

# Free-tier rate-limit handling: retry 429s with exponential backoff.
GROQ_MAX_RETRIES = int(os.environ.get("GROQ_MAX_RETRIES", "5"))
GROQ_BACKOFF_BASE_S = float(os.environ.get("GROQ_BACKOFF_BASE_S", "2.0"))
GROQ_BACKOFF_CAP_S = float(os.environ.get("GROQ_BACKOFF_CAP_S", "30.0"))

# --- Optional higher-quality providers (all off by default) -----------------
# If TAVILY_API_KEY is present, web_search upgrades from DuckDuckGo to Tavily.
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

# Nominatim (OpenStreetMap) geocoding — no key, but etiquette requires a
# descriptive UA and <=1 req/s. Override the UA to identify your deployment.
NOMINATIM_USER_AGENT = os.environ.get(
    "NOMINATIM_USER_AGENT", "jordan-re-assistant/1.0 (contact: dev@localhost)"
)

# --- CORS -------------------------------------------------------------------
ALLOWED_ORIGINS = os.environ.get(
    "ASSISTANT_ALLOWED_ORIGINS",
    "http://localhost:5174,http://127.0.0.1:5174,http://localhost:5173,http://127.0.0.1:5173",
).split(",")
