# Platform feature exchange — Shabbir ⇄ Kartikeya (agreed via Issue #2)

Both platforms will be demoed; the manager picks one to deploy. To keep both
feature-equal (and to enrich whichever wins), we agreed a two-way port. **Porting
happens AFTER the manager selects a UI** — for the demo, each side ships as-is.

## What WE PULL FROM Kartikeya's platform (into ours)
- **Engine internals** (`app/engine/`): `adjustment.py` (plausibility gate + `suppressed[]`
  honesty), `confidence.py`, `stats.py` (robust stats), `opportunity.py`
  (percentile-ranked 4-component score), `monitoring.py` (`area_monitoring` +
  **`peer_comparison`** cross-region).
- **MarketCharts.tsx + MonitoringStep** — backend-computed graphs (price histogram,
  yearly-median trend, by-portal split, price-rank percentile, cross-region peer,
  fullscreen). Our Market view is lighter here → real gain.
- **C1–C4 methodology remediation** + the `attribute_coverage` gate
  (`ok / thin / not_derivable`) + the honest in-UI `not_derivable` disclosure.
- **Spatial enrichment** — `scrapers/enrich_spatial.py` (Copernicus DEM / VIIRS
  night-lights / GHS-POP → `listing_geofeatures`, 23.6k rows).
- **Provenance stamping** (source file, row count, snapshot hash, git SHA).
- **Plain-language de-jargon pass** + docs `pricing-math-explained.html`,
  `how-to-use-it.html`, `the-data-explained.html`.
- **Landing two-door entry** (`Landing.tsx`: "find a good area" vs "I have land") +
  `EvidenceSection` hover-chip → the exact source variable.

## What THEY PULL FROM ours (into theirs)
- **Grounded AI Assistant** — `app/api/llm.py` (OpenAI→Groq→Gemini, explain-only) +
  `/ask` (grounded + **Tavily web-fallback**, flagged w/ sources) + voice input.
  (They removed their Copilot; this seeds their standalone assistant app.) ← their top ask.
- **POI taxonomy + map export** — `scrapers/poi_taxonomy.py`, `export_map_full.py`
  (69k POIs → 53 place-types + emoji).
- **Market-intelligence engine** — `app/engine/market_intelligence.py` +
  `/market-intelligence[/brief]`.
- **Seller pin-valuation** — `app/api/valuation.py` + `/value-property`.
- **Auto-update pipeline** — `pipeline/run_all.py` + scheduler + `market_changes`.
- **Deploy scaffolding** — `vercel.json`, `Procfile`, `docs/DEPLOY.md`.

## DB / deploy decision (both Claudes agree)
- **POC/demo today:** ONE SQLite on a persistent **volume** (Railway/Render/Fly) +
  FastAPI backend + Vercel static frontend → backend URL. **No Postgres today.**
- **Limit that was hit:** GitHub's 100 MB file-push cap (DB is 129–135 MB, gitignored,
  distributed out-of-band). Vercel serverless also can't host it.
- **Postgres = post-selection production step**, owned by the data/science lane, one
  managed instance both UIs point at (keeps the one-canonical-DB rule).

## ⚠️ Open blocker — reconcile to ONE canonical DB
We're on **different files**: theirs `jordan_re_new.sqlite` (~135 MB) vs ours
`jordan_re.sqlite` (~129 MB). Same area could show different numbers across the two
platforms in front of the client. Action: Kartikeya confirms the canonical filename +
Drive link → repoint our backend `JORDAN_RE_DB` → verify a few areas match.

## Open confirmations (awaiting Kartikeya's Claude on Issue #2)
- [ ] Canonical DB filename + Drive link.
- [ ] Meeting split confirmation (Shabbir=dashboard, Kartikeya=sources+methodology).
