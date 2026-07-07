# API Report — Jordan Real Estate Intelligence (Live Engine API)

**Status:** serving · **Base URL (dev):** `http://localhost:8000` · **Stack:** FastAPI + Uvicorn, Python 3.13
**Source:** `app/api/main.py` · **Engine:** `app/engine` (unchanged) · **DB:** `db/jordan_re.sqlite`

This API wraps the Decision Engine so the frontend can compute a recommendation **on demand** for any
user-specified property, instead of showing five pre-computed static results. It is a thin transport
layer: it validates input, builds an engine `Subject`, calls `engine.recommend(subject, bundle)`, and
returns the `RecommendationResult` verbatim per `db-contract.md` §4.

---

## Business logic delegation (governance)

**100% of pricing logic lives in `app/engine`. The API contains no pricing math.** Verified by parity:
a bare `POST /recommend {"neighborhood":"Abdoun"}` (area defaults to 175 m²) returns exactly what the
engine produces for `Subject(neighborhood="Abdoun", area_m2=175)`:

| | min_safe | recommended | premium | confidence |
|---|---|---|---|---|
| Engine (`pipeline.recommend`, 175 m²) | 713.3 | 978.2 | 1540.1 | 0.68 (M) |
| API `POST /recommend {"neighborhood":"Abdoun"}` | 713.3 | 978.2 | 1540.1 | 0.68 (M) |

The API builds the `Subject` only from fields the caller actually supplies (letting the engine's own
dataclass defaults fill the rest), so it can never diverge from the engine's own default subject.

**Full bundle, not a per-neighborhood slice:** the engine filters comparables by `subject.neighborhood`
internally and deliberately falls back to a **citywide** pool when a submarket is too thin to derive an
attribute premium (`pipeline._citywide_pool`). The API therefore loads the whole bundle once at startup
and passes it to every call. Slicing per neighborhood would silently break that fallback — so we don't.

---

## How to run

From the repo root (`C:\Rubicon\Real-Estate-Jordan`), so that `app` is importable:

```powershell
# option A — script (installs deps then serves)
app\api\run.ps1

# option B — manual
python -m pip install -r app\api\requirements.txt
uvicorn app.api.main:app --port 8000 --reload
```

Dependencies: `app/api/requirements.txt` (fastapi 0.115.12, uvicorn[standard] 0.34.3, pydantic 2.11.4).
The DB path defaults to `db/jordan_re.sqlite`; override with the `JORDAN_RE_DB` env var.
Interactive docs at `http://localhost:8000/docs`.

---

## Endpoints

### `GET /health`
Liveness + what's loaded.
```json
{"status":"ok","listings":854,
 "neighborhoods":["Abdoun","Dabouq","Khalda","Shmeisani","Sweifieh"],
 "db_path":"C:\\Rubicon\\Real-Estate-Jordan\\db\\jordan_re.sqlite"}
```

### `GET /neighborhoods`
The covered submarkets, for map + picker. `median_price_per_m2` is the median of plausible sale
listings (≥ 250 JD/m², the engine's placeholder floor). Real response:
```json
[
 {"name":"Abdoun","centroid_lat":31.948833,"centroid_lng":35.89266,"listing_count":170,"sale_listing_count":93,"median_price_per_m2":1055.6},
 {"name":"Dabouq","centroid_lat":31.988059,"centroid_lng":35.811302,"listing_count":177,"sale_listing_count":100,"median_price_per_m2":1000.0},
 {"name":"Khalda","centroid_lat":31.990057,"centroid_lng":35.844849,"listing_count":166,"sale_listing_count":93,"median_price_per_m2":766.7},
 {"name":"Shmeisani","centroid_lat":31.97348,"centroid_lng":35.896883,"listing_count":172,"sale_listing_count":81,"median_price_per_m2":790.0},
 {"name":"Sweifieh","centroid_lat":31.958369,"centroid_lng":35.863877,"listing_count":169,"sale_listing_count":95,"median_price_per_m2":1000.0}
]
```

### `POST /recommend`
The core endpoint. Body (only `neighborhood` is required):

| field | type | default | notes |
|---|---|---|---|
| `neighborhood` | string | — | must be one of the 5 covered (case-insensitive) |
| `property_type` | enum | `apartment` | `apartment\|villa\|land\|commercial` |
| `area_m2` | number > 0 | `175` | |
| `bedrooms` | int ≥ 0 | — | |
| `bathrooms` | int ≥ 0 | — | accepted; not modelled by the engine Subject → ignored in pricing |
| `floor_level` | int ≥ 0 | — | |
| `total_floors` | int ≥ 1 | — | accepted; not modelled by the engine Subject → ignored in pricing |
| `building_age_years` | int ≥ 0 | — | omitted → engine default (new build) |
| `view` | enum | — | `none\|sea\|city\|garden\|mountain\|panoramic\|unknown` |
| `parking` | enum | — | `none\|open\|covered\|unknown` |
| `furnishing` | enum | — | `no\|semi\|full\|unknown` |
| `finish_quality` | enum | — | `basic\|standard\|high\|luxury\|unknown` |
| `elevator` | enum | — | `y\|n\|u\|unknown` |

Missing optional attributes are left to the engine, which treats them as unknown and surfaces the gap
in `risk_factors` (it already does this for view/parking, which the portals rarely expose).

**Request** (`Abdoun`, 170 m², floor 12, city view, high finish):
```json
{"neighborhood":"Abdoun","area_m2":170,"floor_level":12,"view":"city","finish_quality":"high"}
```
**Response** (abridged — arrays trimmed to one element; full shape per `db-contract.md` §4):
```json
{
  "location_id": null,
  "neighborhood": "Abdoun",
  "property_type": "apartment",
  "min_safe_price_jd_m2": 735.6,
  "recommended_price_jd_m2": 1005.0,
  "premium_price_jd_m2": 1540.1,
  "confidence": { "label": "M", "numeric": 0.687, "interval_jd_m2": [735.6, 1274.5] },
  "evidence_objects": [
    {
      "factor": "Finish quality (high)",
      "adjustment": "+0.9%",
      "confidence": "Medium",
      "method": "paired median differential (n_high=7, n_luxury=40)",
      "datasets": ["listings"],
      "sources": [{ "name": "OpenSooq", "url": "https://jo.opensooq.com/en/search/282282874", "capture_date": "2026-07-07" }],
      "category": "current_state",
      "explanation": "..."
    }
  ],
  "comparables": [
    { "listing_id": "opensooq-282283228", "neighborhood": "Abdoun", "price_per_m2": 913.3,
      "similarity": 0.832, "adjustments_applied": ["Size"] }
  ],
  "risk_factors": [
    { "factor": "View premium unavailable", "severity": "low", "detail": "..." }
  ],
  "alternative_scenarios": [
    { "name": "Recommended launch", "recommended_price_jd_m2": 1005.0, "rationale": "..." }
  ],
  "narrative": "For a high apartment in Abdoun (~170 m²), the recommended launch price is 1005 JD/m² ...",
  "computed_date": "2026-07-07",
  "method_values": { "comparison_asking": ..., "comparison": ..., "cost_floor": null, "income_ceiling": ..., "development_score": ... }
}
```

**Input sensitivity (real, same server):** identical body but neighborhood `Khalda`, 120 m², floor 3 →
`min/rec/premium = 423.5 / 598.2 / 773.0`, confidence 0.76 (H). Khalda's cheaper submarket (median
767 vs Abdoun 1056 JD/m²) flows straight through — numbers move sensibly with input and are traceable
to the underlying listings.

**Errors** — always `{"detail": "..."}`:
- Uncovered neighborhood → `422 {"detail":"No data for Marka; covered: ['Abdoun','Dabouq','Khalda','Shmeisani','Sweifieh']"}` (never fabricated).
- Bad enum (`view":"ocean"`) or non-positive `area_m2` → `422` (pydantic validation).

### `GET /comparables?neighborhood=&limit=20`
Raw plausible sale listings for a submarket, newest first — for a comps table alongside the
recommendation. `limit` 1–100 (default 20). Real response (`Khalda`, limit 3):
```json
{"neighborhood":"Khalda","count":93,"comparables":[
  {"listing_id":"opensooq-283704650","price_per_m2":808.8,"area_m2":204.0,"listing_date":"2026-07-06","source":{"name":"OpenSooq","url":"..."}, "...":"..."}
]}
```

---

## How the frontend should call it

1. On load: `GET /neighborhoods` to render the map/picker (centroids + medians already included).
2. When the user submits the property form: `POST /recommend` with the form fields. Send only what the
   user filled in — omit blanks entirely (do **not** send `""`); the engine treats absent attributes as
   unknown. Render `recommended_price_jd_m2` as the headline, `min_safe`/`premium` as the band,
   `confidence`, then the `evidence_objects` waterfall (each row already carries `sources[]` chips),
   `comparables`, `risk_factors`, and `alternative_scenarios`.
3. All prices are JD/m² canonical numbers — do display formatting client-side (per `api-design`
   client-vs-server rule). The API never returns pre-formatted strings.
4. CORS is enabled for `http://localhost:5173` and `http://localhost:4173` (Vite dev + preview),
   including 127.0.0.1. Verified: preflight returns `access-control-allow-origin: http://localhost:5173`.

---

## Verification performed

- `GET /health`, `GET /neighborhoods` — return real counts (854 listings, 5 submarkets).
- `POST /recommend` for **Abdoun** (170 m², floor 12, city, high) and **Khalda** (120 m², floor 3) —
  distinct, sensible numbers traceable to listings.
- **Parity**: `POST /recommend {"neighborhood":"Abdoun"}` == engine's own 175 m² output (713.3 / 978.2 / 1540.1).
- Error paths: uncovered neighborhood, bad enum, negative area all return `422 {detail}`.
- CORS preflight + actual request for both allowed origins.
- `GET /comparables` returns real OpenSooq listings, newest first.
