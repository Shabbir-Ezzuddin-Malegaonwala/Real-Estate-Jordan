"""Read-only text-to-SQL analytics over the canonical DB.

Safety model (defence in depth):
  1. The DB is opened in read-only mode (`file:...?mode=ro`).
  2. Generated SQL must be a SINGLE statement starting with SELECT or WITH.
  3. A denylist rejects any DDL/DML/PRAGMA/ATTACH keyword.
  4. Only allow-listed tables may be referenced.
  5. A LIMIT is injected if absent; rows are hard-capped.
The natural-language -> SQL step uses the cheap Groq model; the SQL it produces
is returned to the caller for full transparency (the UI shows the query).
"""

from __future__ import annotations

import re
import sqlite3
from functools import lru_cache

from langchain_groq import ChatGroq

from .config import DB_PATH, GROQ_API_KEY, GROQ_FAST_MODEL, GROQ_TEMPERATURE

# Tables the analyst may query. Everything else is invisible to text-to-SQL.
ALLOWED_TABLES = {
    "listings", "poi", "poi_extended", "area_yields", "dos_building_cost",
    "macro_series", "neighborhood_geocontext", "listing_geofeatures", "districts",
}

MAX_ROWS = 25

_SCHEMA_HINT = """\
Tables you may query (SQLite, read-only). Only these exist:

listings(listing_id, portal, listing_type['sale'|'rent'], property_type['apartment'|'villa'|'land'|'commercial'],
         neighborhood, district, lat, lng, price_jd, area_m2, bedrooms, bathrooms, floor_level, total_floors,
         view, parking, building_age_years, furnishing, finish_quality, seller_type, listing_date, source_name, source_url)
  -- 52k rows across all of Jordan. price per m2 = price_jd/area_m2. Filter listing_type='sale' for sale prices.
  -- Guard against nulls/outliers: price_jd>0 AND area_m2>0 AND price_jd/area_m2 BETWEEN 100 AND 6000.

area_yields(neighborhood, property_type, median_rent_jd_m2, annual_rent_jd_m2, median_sale_jd_m2,
            gross_yield_pct, n_rent, n_sale)  -- derived rental yields per area.

macro_series(indicator, geography, period, value, unit, source_name, source_url, capture_date)
  -- time series. Key indicators (exact strings): 'CBJ policy rate', 'CPI inflation (YoY)',
  -- 'USD/JOD exchange rate', 'Real estate price index - General', 'Real estate sale transactions (count)',
  -- 'Real estate trading volume', 'Gold price 24K'. Use period for time ordering (e.g. '2025-Q4' or a date).

dos_building_cost(year, quarter, authority, building_type, license_type, cost_jd_per_m2)  -- official DoS build cost.

poi_extended(category, subcategory, name, lat, lng, governorate, neighborhood)  -- 9k POIs (schools, malls, hospitals...).
poi(name, category, neighborhood, lat, lng)  -- curated subset.

neighborhood_geocontext(neighborhood, median_elevation_m, elevation_rank, median_population_density,
                        median_nightlight, dominant_aspect, context)

listing_geofeatures(listing_id, elevation_m, slope_deg, aspect_cardinal, population_density, nightlight_intensity)

districts(name, centroid_lat, centroid_lng)  -- the 5 core priced districts.
"""

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|"
    r"reindex|analyze|truncate|grant|revoke)\b",
    re.IGNORECASE,
)
_TABLE_REF = re.compile(r"\b(?:from|join)\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
# Names introduced by a WITH clause (CTEs) are query-local, not real tables.
_CTE_DEF = re.compile(r"(?:\bwith\s+|,\s*)([A-Za-z_][A-Za-z0-9_]*)\s+as\s*\(", re.IGNORECASE)


@lru_cache(maxsize=1)
def _sql_llm() -> ChatGroq:
    return ChatGroq(model=GROQ_FAST_MODEL, temperature=0, api_key=GROQ_API_KEY, max_retries=0)


def _generate_sql(question: str) -> str:
    prompt = (
        "You translate a question into ONE read-only SQLite SELECT query.\n"
        f"{_SCHEMA_HINT}\n"
        "Rules: output ONLY the SQL, no prose, no markdown fences. Single SELECT (or WITH...SELECT). "
        "Always add a LIMIT (<= 50). Never modify data. Use only the tables above.\n\n"
        f"Question: {question}\nSQL:"
    )
    resp = _sql_llm().invoke(prompt)
    sql = (resp.content or "").strip()
    sql = re.sub(r"^```(?:sql)?|```$", "", sql, flags=re.IGNORECASE | re.MULTILINE).strip()
    # Keep only the first statement.
    sql = sql.split(";")[0].strip()
    return sql


def _validate(sql: str) -> tuple[bool, str]:
    low = sql.lower().lstrip()
    if not (low.startswith("select") or low.startswith("with")):
        return False, "Only SELECT/WITH queries are allowed."
    if _FORBIDDEN.search(sql):
        return False, "Query contains a forbidden (write/DDL) keyword."
    refs = {t.lower() for t in _TABLE_REF.findall(sql)}
    ctes = {c.lower() for c in _CTE_DEF.findall(sql)}  # query-local names, allowed
    illegal = refs - ALLOWED_TABLES - ctes
    if illegal:
        return False, f"Query references non-allow-listed table(s): {sorted(illegal)}"
    return True, ""


def _ensure_limit(sql: str) -> str:
    if re.search(r"\blimit\b", sql, re.IGNORECASE):
        return sql
    return f"{sql.rstrip()} LIMIT {MAX_ROWS}"


def query_data(question: str) -> dict:
    q = (question or "").strip()
    if not q:
        return {"error": "empty_question"}
    if not GROQ_API_KEY:
        return {"error": "no_groq_key", "message": "GROQ_API_KEY is required for text-to-SQL."}

    try:
        sql = _generate_sql(q)
    except Exception as e:
        return {"error": "sql_generation_failed", "question": q, "detail": str(e)}

    ok, reason = _validate(sql)
    if not ok:
        return {"error": "unsafe_or_invalid_sql", "question": q, "sql": sql, "reason": reason}
    sql = _ensure_limit(sql)

    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql)
        rows = [dict(r) for r in cur.fetchmany(MAX_ROWS)]
        cols = [d[0] for d in cur.description] if cur.description else []
        conn.close()
    except Exception as e:
        return {"error": "query_execution_failed", "question": q, "sql": sql, "detail": str(e)}

    return {
        "question": q,
        "sql": sql,
        "columns": cols,
        "row_count": len(rows),
        "rows": rows,
        "source": {
            "name": "Canonical DB (jordan_re.sqlite) — read-only SQL",
            "sql": sql,
            "kind": "database",
        },
    }
