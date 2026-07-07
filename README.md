# Jordan Real Estate Intelligence Platform

An evidence-backed **launch-price decision-support tool** for residential real estate in Amman, Jordan. You pick a location and describe a property, and the platform recommends a defensible launch price — **and shows why**: every number is backed by real market evidence with a traceable source.

> **This is not a price-prediction black box.** The client (a builder/developer) doesn't just need a price — they need to *justify* a launch price to buyers, investors, and their board. So the product's core is the **reasoning and its evidence**, not the number alone. Explainability is the product.

---

## 1. What it does (in one screen)

- **Map of Amman** with the covered submarkets, points of interest (schools, hospitals, malls…), roads, and a land-use layer.
- **Pick a submarket + describe a unit** (size, floor, view, finish, age…) → the engine computes a **launch price band**: Minimum-Safe / Recommended / Premium (JD per m²) with a **confidence level**.
- **Adjustment waterfall** — the recommended price is built up from a comparable base through evidenced adjustments (size, floor, building age, finish…), each row carrying **source chips** (the actual listings + dates behind it).
- **Comparables, risk factors, and a plain-English analyst narrative** — including honest statements of what data is missing.

Coverage today: **5 Amman submarkets** — Abdoun, Dabouq, Sweifieh, Khalda, Shmeisani.

---

## 2. Why it's built this way

Jordan does **not** publish unit-level transaction prices (confidential by law). Official sources give only macro/governorate-level signals. So market intelligence has to be **reconstructed** by fusing many sources — portal asking prices, GIS/POIs, official indices — and every conclusion has to be **traceable**. That constraint drives the whole architecture: collect evidence → store with provenance → reason over it → explain with sources.

The pricing methodology follows the client's own framework: **Sales Comparison** (evidenced adjustment grid) as the spine, with a **Cost-approach floor** and an **Income-approach ceiling** as cross-checks. (Hedonic/AVM/ML need 300–500 clean transactions and are Phase-2.)

---

## 3. Repository structure — *what* each part is and *why* it exists

| Path | What it is | Why it exists |
|---|---|---|
| `MASTER-PLAN.md` | The single source of truth: business goal, dataset inventory, schema, engine design, governance | Read this first — it explains every design decision |
| `DEEP-RESEARCH-PROMPTS.md` | Ready-to-run research prompts (R1–R7) for ChatGPT/Gemini/Perplexity | Fills the evidence tables that scraping can't (competitor projects, costs, infra news, qualitative area character) |
| `JUNIOR-PACKET.md` / `K-PACKET.md` | Self-contained data-collection briefing + exact CSV schemas | Hand to a second collector so data lands in one consistent format |
| **`db/`** | SQLite schema, DB init, and CSV/GeoJSON loaders | The structured database — the foundation everything sits on |
| `db/schema.sql` | All tables (listings, poi, districts, macro_series, zoning_plots, evidence_items, projects, neighborhood_profiles, cost_benchmarks, derived_premiums, recommendations) | Every table carries **provenance columns** (source_url, capture_date, confidence…) |
| `db/jordan_re.sqlite` | The populated database (854 listings + POIs + macro + zoning) | Run the app immediately without re-scraping |
| **`scrapers/`** | Data collectors | Turn raw sources into schema-clean CSVs |
| `scrapers/bayut_scraper.py`, `opensooq_scraper.py` | Portal listing scrapers (plain HTTP — JSON is embedded in the page) | The pricing backbone: real asking-price listings |
| `scrapers/osm_overpass.py` | OpenStreetMap POIs / boundaries / roads via Overpass API | The map + distance-to-amenity features |
| `scrapers/official_data.py` | CBJ price index, DoS permits, DLS context | Macro trend + supply-pipeline context |
| `scrapers/enrich_*.py` | Detail-page attribute enrichment (floor, age, finish, parking…) | Enriches listings beyond the search-results fields |
| **`app/engine/`** | The Decision Engine (pure Python, no hardcoded weights) | The "brain" — all pricing logic lives here and nowhere else |
| `app/engine/{comparable_analysis,adjustment,evidence,confidence,recommendation}.py` | The five sub-engines | Select comps → derive adjustments from data → build evidence objects → score confidence → produce the band + narrative |
| **`app/api/`** | FastAPI service wrapping the engine | Serves on-demand recommendations to the frontend (`POST /recommend`) |
| **`app/web/`** | React + TypeScript + MapLibre frontend | The interactive dashboard (map, form, waterfall, evidence panel) |
| **`data/processed/`** | Clean, schema-matching CSV/GeoJSON | What actually gets loaded into the DB |
| **`data/raw/`** | Original downloads (portal CSVs, CBJ/DoS files, OSM cache) | Auditable source of the processed data |
| **`docs/`** | Per-workstream reports + verification screenshots | How each piece was built and verified |
| Client PDFs | `Jordan Real Estate Data Sources.pdf`, `Real Estate Pricing Strategies.pdf` | The two authoritative client documents |

> **Not in git:** `data/research-data/` (multi-GB incoming research downloads), `node_modules/`, build caches, and personal media — see `.gitignore`. These are regenerable or ingested separately.

---

## 4. Data sources — where every number comes from

Every row in the database stores its own `source_url` + `capture_date`. Summary:

| Data | Source | Link | Status |
|---|---|---|---|
| Property listings (854, asking prices) | Bayut Jordan, OpenSooq Jordan | bayut.jo · jo.opensooq.com/en/real-estate | ✅ Real (each row links its listing) |
| POIs (984), districts (5), roads (2,558) | OpenStreetMap (Overpass) | overpass-api.de | ✅ Real |
| Real-estate price index (2005→2021-Q3) | Central Bank of Jordan | cbj.gov.jo/En/List/Jordan_Real_Estate_Price_Index | ✅ Real (ends 2021-Q3) |
| Building permits (supply, to 2024) | Dept. of Statistics | dosweb.dos.gov.jo | ✅ Real |
| Land-use polygons (zoning backdrop) | OpenStreetMap land-use | overpass-api.de | ⚠️ Unofficial proxy (labelled) |
| DLS transaction totals (national) | News citing DLS (Zawya, Jordan News) | per-row article URLs | ⚠️ Fallback, low-confidence (labelled) |
| Map basemap | OpenStreetMap + CARTO tiles | — | ✅ |

**Geo-blocked from outside Jordan** (fallbacks used, labelled): official DLS transactions (dls.gov.jo), GAM official zoning (ammancitygis.gov.jo), CBJ post-2021 index (statisticaldb.cbj.gov.jo). These require a Jordan-side connection to pull.

**Honesty note:** listings are *asking* prices; the engine calibrates asking→transaction with a documented 5–15% discount from the client's pricing PDF. This is stated on the dashboard itself.

---

## 5. How to run it

Prereqs: **Python 3.12+**, **Node 18+**.

```bash
# 1) Database (already populated as db/jordan_re.sqlite; to rebuild:)
python db/init_db.py                        # creates the schema
python db/load_csv.py data/processed/*.csv  # loads processed CSVs
python db/load_geojson.py                   # loads districts/zoning

# 2) Decision Engine (sanity check — runs on the real DB)
python -m app.engine.test_pipeline          # tests
python -m app.engine.emit_sample            # regenerate app/engine/sample_output.json

# 3) Live API (serves recommendations on demand)
pip install -r app/api/requirements.txt
uvicorn app.api.main:app --port 8000
#   GET  http://localhost:8000/health
#   GET  http://localhost:8000/neighborhoods
#   POST http://localhost:8000/recommend  { "neighborhood":"Abdoun", "area_m2":170, "floor_level":12, "finish_quality":"high" }

# 4) Frontend (interactive dashboard)
cd app/web
npm install
npm run dev            # → http://localhost:5173  (needs the API on :8000)
```

Offline fallback: if the API isn't running, the frontend renders precomputed results from `app/engine/sample_output.json` and shows an "Offline" badge — so a demo never hard-breaks.

---

## 6. What's included vs. not (v1 status)

**Included & real:** listings pipeline, POIs/map, macro indices, zoning backdrop, the 5-sub-engine Decision Engine (comparison + cost/income cross-checks, confidence scoring, evidence objects), the live API, and the interactive frontend.

**Not yet populated (empty tables, awaiting research):** `projects` (competitor launches), `cost_benchmarks` (construction costs), `evidence_items` (future infrastructure/news), `neighborhood_profiles` (qualitative area character). These come from the R1–R7 deep-research relay in `DEEP-RESEARCH-PROMPTS.md`. Until then the dashboard shows honest "awaiting data" states.

**Known limitations (all surfaced in the UI):** view/parking not available per-listing (portals don't publish them → view moves to neighborhood-level research); CBJ price index ends 2021-Q3; official zoning + DLS transactions are geo-blocked (unofficial fallbacks used).

---

## 7. Roadmap

- Ingest the deep-research CSVs → cost floor, competitor cross-check, future-signal appreciation story, qualitative "why" reasons.
- Pull the geo-blocked official sources (CBJ recent quarters, DLS transactions, GAM zoning) from a Jordan connection.
- Phase-2: hedonic/ML pricing once ≥300–500 clean records exist; AI-vision view/finish from listing photos; expand beyond the 5 submarkets.

---

## 8. Governance / who does what

- **Engineering & architecture:** Claude Code (technical lead) with a team of specialized agents.
- **Solution/business review:** ChatGPT (design reviewer).
- **Research & data collection:** Gemini/Perplexity deep-research + a second collector, into the frozen schema.
- **Project lead / final decisions:** the repo owner.

See `MASTER-PLAN.md` §Governance for the full model.
