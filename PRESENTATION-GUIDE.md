# Presentation Guide — Jordan Real Estate Analyst Terminal (National build)

**Branch:** `feature/national-data-rebuild`
**What it is:** an evidence-backed launch-pricing tool. Pick a submarket, describe a unit → it returns a defensible price band (Minimum-Safe / Recommended / Premium in JD/m²) with a confidence level and an adjustment waterfall where **every number traces to real listings**. Now running on the full **56,854-listing, nationwide** dataset (was 854, Amman-only).

---

## 1. Run it (2 terminals)

Prereqs: Python 3.11+, Node 18+ (already installed here).

**Terminal 1 — the pricing API (live engine):**
```bash
cd "D:/Rubikon Labs/Real-Estate-Jordan"
# Windows PowerShell:  $env:JORDAN_RE_DB="db/jordan_national.sqlite"
JORDAN_RE_DB=db/jordan_national.sqlite python -m uvicorn app.api.main:app --port 8000
```
Wait ~5s for "Application startup complete". (Health check: http://localhost:8000/health → 56,854 listings, 714 neighborhoods.)

**Terminal 2 — the dashboard:**
```bash
cd "D:/Rubikon Labs/Real-Estate-Jordan/app/web"
npm run dev
```
Open the printed URL (**http://localhost:5173**).

> **Fail-safe:** the map + prices work even if the API is down — the app falls back to precomputed results and shows an "Offline" badge. So the visual demo never breaks. The API only adds *live* recompute when you change the unit form.

---

## 2. What you'll see (and how it changed)

- The map is **nationwide** — **42 clickable regions** (was 5): **36 Amman submarkets** (Abdoun, Dabouq, Khalda, Sweifieh, Dair Ghbar, Umm Uthaina, 4th–7th Circle, …) at street granularity, **plus 6 governorate-city circles** (Irbid, Zarqa, Aqaba, Al Salt, Madaba, Jordan Valley). Zoom out to see the whole country; zoom into Amman for submarket detail.
- **2,595 amenity dots** countrywide (schools, hospitals, malls, mosques, parks, universities, transport).
- The bottom dock shows the **top-10 regions by price** and POI counts.

> **Why two granularities?** Amman has ~22k geocoded listings, so we price it by submarket. Other governorates are sparser, so we pool each city and price it at **city level** (e.g. Irbid = 391 comps). Honest granularity: fine where the evidence is dense, city-level where it's thinner — the engine prices all 714 neighborhoods on demand regardless.

## 3. The 3-minute demo flow

1. **Open on the map (zoomed to Jordan)** — "This is a nationwide reconstruction of the Jordanian market from ~57,000 live portal listings across all 12 governorates. Each circle is a market we have enough evidence to price — Amman by submarket, other cities at city level." Zoom into Amman to show the submarket density.
2. **Click Abdoun** (or Dabouq) — the left panel fills: **price band + confidence + adjustment waterfall**.
   - Point at the waterfall: *"The recommended price isn't a guess — it starts from a base of comparable listings, then each adjustment (floor, building age, size) is a number we **measured from the market** (a regression slope with a sample size), not a hardcoded weight. Then we discount asking→transaction, and cross-check against a construction-cost floor and a rental-income ceiling."*
   - Point at the **source chips** on each row: *"Every figure is traceable to the actual listings and the date we captured them."*
3. **Change the unit** in the form (e.g. area 250 m², floor 10, finish "luxury") → **live recompute** via the engine.
4. **Show confidence honesty** — click a dense area (e.g. **Al Jubaiha = High**) vs a thinner one → the band widens and confidence drops. *"It tells you where the evidence is strong and where it isn't."*
5. **National reach** — mention the bottom chart includes **Irbid / Zarqa / Aqaba** (secondary cities, correctly Low confidence) — the engine prices all 714 neighborhoods on demand, not just the map circles.

## 4. Talking points / the numbers

- **56,854 listings**, 6 portals, **all 12 governorates** (66× the previous demo).
- Prices are plausible & ordered: Dabouq ~1,190 > Abdoun ~935 > Sweifieh ~690 > Khalda ~620 > … > Irbid ~320 (JD/m²).
- **No hardcoded weights** — every adjustment is an OLS slope / paired-median from live data.
- **Cost floor now fires** for the first time (DOS construction cost ~155 JD/m²) — previously the table was empty.
- **Confidence is automatic and honest** — H (dense) / M / L (thin), band widens as evidence thins.

## 5. If asked about limitations (be upfront — it builds trust)

- Listings are **asking** prices; we apply a documented 5–15% asking→transaction discount (shown on the dashboard).
- **Granularity varies by data density** — Amman is priced by submarket (dense geocoded data); other governorates are priced at **city level** (sparser data). Both are on the map; the engine prices any of 714 neighborhoods on demand.
- **Terrain-view / affluence / density** features (from satellite data) are **built and available but not yet wired into the score** — a Phase-2 upgrade.
- The **DLS price index** we hold ends 2018-Q4 (needs a fresh pull); time-adjustment self-disables as stale until then.

---

## 6. If you need to rebuild the data (rarely)

```bash
cd "D:/Rubikon Labs/Real-Estate-Jordan"
python scrapers/ingest_national.py            # 6 portals -> canonical listings CSV
python scrapers/dos_costs.py                   # DOS -> construction cost floor
python db/init_db.py  --db db/jordan_national.sqlite
python db/load_csv.py data/processed/listings_national_20260708.csv   --db db/jordan_national.sqlite --table listings
python db/load_csv.py data/processed/cost_benchmarks_dos_20260708.csv --db db/jordan_national.sqlite --table cost_benchmarks
python db/load_csv.py data/processed/macro_construction_cost_dos.csv  --db db/jordan_national.sqlite --table macro_series
python scrapers/gen_map_layers.py              # 36 submarket circles + POIs -> data/processed
python -m scrapers.emit_national               # precomputed prices -> app/engine/sample_output.json
# then npm run dev (prepare-data.mjs copies everything into the app automatically)
```

Full technical detail: `docs/national-rebuild-report.md`.
