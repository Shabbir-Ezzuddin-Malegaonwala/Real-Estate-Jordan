# Deployment guide (Vercel frontend + backend host)

The platform is two parts. The **frontend** (React/Vite) is a static site → **Vercel**.
The **backend** (FastAPI + a 129 MB SQLite database + the pricing engine) needs a
real server → **Railway / Render / Fly** (NOT Vercel — the DB is too big for Vercel's
serverless limit and cold-starts would reload the engine every call).

The code is already deploy-ready: the frontend reads `VITE_API_BASE`, the backend
reads `ALLOWED_ORIGINS`, `JORDAN_RE_DB`, and the LLM keys from the environment.

---

## 1. Backend → Railway (or Render)
1. New project from the repo, **root = the JRE-v3 folder**.
2. It auto-detects Python (`requirements.txt` at root → `-r app/api/requirements.txt`).
   Start command (already in `Procfile`):
   `uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
3. **Upload the database** and point at it. `db/jordan_re.sqlite` (129 MB) is
   gitignored, so add it via a Railway **volume** (mount e.g. `/data`, upload the
   file) or bundle it in the deploy. Then set the env var below.
4. **Environment variables:**
   - `JORDAN_RE_DB` = path to the uploaded DB (e.g. `/data/jordan_re.sqlite`)
   - `ALLOWED_ORIGINS` = your Vercel URL (e.g. `https://jre.vercel.app`) — comma-sep
     for multiple
   - `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, `TAVILY_API_KEY` (from `.env`)
5. Deploy → note the public URL (e.g. `https://jre-api.up.railway.app`). Check
   `GET /health` returns `{"status":"ok", ...}`.

## 2. Frontend → Vercel
1. New project from the repo, **Root Directory = `app/web`**.
2. Framework auto-detected (Vite); build `npm run build`, output `dist`
   (already in `app/web/vercel.json`).
3. **Environment variable:**
   - `VITE_API_BASE` = the backend URL from step 1 (e.g.
     `https://jre-api.up.railway.app`) — this is baked in at build time.
4. Deploy → note the Vercel URL, and make sure it's in the backend's
   `ALLOWED_ORIGINS`. Redeploy the backend if you added it after.

## 3. Wiring recap
```
Vercel frontend  --VITE_API_BASE-->  Railway backend  --JORDAN_RE_DB-->  jordan_re.sqlite
       ^-------------------- ALLOWED_ORIGINS (Vercel URL) ----------------------^
```

## Notes
- **Graceful fallback:** if the backend is unreachable, the frontend still loads and
  shows the bundled map + a mock dataset (offline mode) — it won't crash during a demo.
- **Data files:** the map geojson (`app/web/public/data/*`) are bundled into the
  static build and served by Vercel — no backend needed for the map itself.
- **Keys:** never commit `.env`. Set the keys in the Railway dashboard only.
- **Quick alternative for a live demo without a backend host:** run the backend
  locally and expose it with a tunnel (`cloudflared tunnel --url http://localhost:8000`
  or `ngrok http 8000`), then set `VITE_API_BASE` to the tunnel URL and
  `ALLOWED_ORIGINS` to the Vercel URL.
