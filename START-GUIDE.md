# How to Run the Platform (VS Code) — Step by Step

Everything runs **locally** on your machine. Three pieces: the **database** (already built), the **API** (Python), and the **web app** (Node). You start the API, then the web app, then open the browser.

Prerequisites (already installed on your machine): **Python 3.13**, **Node 22**, **VS Code**.

---

## 1. Open the project in VS Code

1. Open VS Code → **File → Open Folder** → select `C:\Rubicon\Real-Estate-Jordan`.
2. Open a terminal: **Terminal → New Terminal** (it opens at the project root).

You'll use **two terminals** — one for the API, one for the web app. Split with the `+` or the split icon in the terminal panel.

---

## 2. (One-time) Install dependencies

**Terminal 1 — Python/API deps:**
```powershell
pip install -r app/api/requirements.txt
pip install fastapi uvicorn scipy openpyxl pandas
```

**Terminal 2 — Web app deps:**
```powershell
cd app/web
npm install
cd ../..
```

---

## 3. (Only if you ever need to rebuild the database)

The database `db/jordan_re.sqlite` is **already built and populated** (24k+ listings, 11 tables). You normally skip this. To rebuild from scratch:
```powershell
python db/init_db.py
python db/load_csv.py data/processed/poi.csv
python db/load_csv.py data/raw/listings_bayut_20260707.csv
python db/load_csv.py data/raw/listings_opensooq_20260707.csv
python db/load_csv.py data/raw/friend/listings_friend_geocoded.csv
python db/load_csv.py data/raw/research/projects_research.csv
python db/load_csv.py data/raw/research/cost_benchmarks_research.csv
python db/load_csv.py data/raw/research/evidence_items_research.csv
python db/load_csv.py data/raw/research/neighborhood_profiles_research.csv
python db/load_geojson.py
python -m app.engine.emit_sample
```

---

## 4. Start the API  (Terminal 1)

From the project root (`C:\Rubicon\Real-Estate-Jordan`):
```powershell
python -m uvicorn app.api.main:app --port 8000
```
Leave this running. Check it works: open **http://localhost:8000/health** in a browser — you should see `{"status":"ok","listings":24471,...}`.
(Interactive API docs: **http://localhost:8000/docs**)

---

## 5. Start the web app  (Terminal 2)

```powershell
cd app/web
npm run dev
```
Leave this running. It prints `Local: http://localhost:5173/`.

---

## 6. Open the platform

Open **http://localhost:5173/** in your browser (Chrome/Edge).
- The header has a **theme toggle** (sun/moon) and a **? Help** button.
- Pick a submarket (dropdown / search / click the map) → enter a unit's size/floor → **Analyze**.

> Both the API (5173 needs it) and the web app must be running at the same time. If the app shows an "Offline" badge, the API (step 4) isn't running.

---

## 7. Run the tests (optional, to verify everything)
```powershell
python tests/run_all.py
```
All suites should print **OK**.

---

## 8. View the documents
- Manager HTML dashboard: open `docs/dashboard/index.html` in a browser (double-click it).
- Master Excel: `deliverables/Jordan_Real_Estate_Master_Dataset.xlsx`
- Text2SQL training doc: `deliverables/text2sql_training_document.md`

---

## Stopping
In each terminal press **Ctrl + C**. To force-kill stray servers:
```powershell
Get-Process -Name python,node -ErrorAction SilentlyContinue | Stop-Process -Force
```

## Troubleshooting
- **Port already in use:** kill stray servers (command above), or change `--port`.
- **`ModuleNotFoundError`:** re-run step 2 (pip install).
- **Map tiles blank:** needs internet (CARTO/OSM tiles); the rest of the app still works offline from precomputed data.
- **`npm run dev` fails:** delete `app/web/node_modules` and re-run `npm install`.
