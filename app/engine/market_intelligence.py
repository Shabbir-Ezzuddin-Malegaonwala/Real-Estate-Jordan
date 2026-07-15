"""Market Intelligence (Milestone 2) — reads the change events the auto-update pipeline writes
into `market_changes`, plus competitor projects, and produces the manager's overview + weekly brief.

All math is server-side and sourced. Nothing is invented: every number comes from a real change
event or a sourced table. A disappeared listing is 'delisted', never 'sold' (Jordan withholds sale
prices). The narration here is deterministic (templated from real counts) — an LLM may later re-phrase
it but may never change a number.
"""
from __future__ import annotations
import sqlite3, datetime as dt


def _conn(db_path):
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c


def _has_table(cur, name: str) -> bool:
    return cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _series_signal(cur, indicator: str, label: str) -> dict | None:
    """Latest value of a macro time-series + its % change vs ~a year earlier."""
    rows = cur.execute(
        "SELECT period, value FROM macro_series WHERE indicator=? AND value IS NOT NULL "
        "AND value != 'NULL' ORDER BY period", (indicator,)).fetchall()
    vals = []
    for p, v in rows:
        try:
            vals.append((p, float(v)))
        except (TypeError, ValueError):
            continue
    if len(vals) < 2:
        return None
    latest = vals[-1]
    prior = vals[-5] if len(vals) >= 5 else vals[0]  # ~4 quarters back
    change = round(100 * (latest[1] - prior[1]) / prior[1], 1) if prior[1] else None
    return {"label": label, "value": round(latest[1], 1), "period": latest[0],
            "change_pct": change, "note": "vs a year ago"}


def key_signals(db_path: str) -> list[dict]:
    """A few glanceable market gauges (real, sourced) with up/down — the 'ticker'."""
    c = _conn(db_path); cur = c.cursor()
    if not _has_table(cur, "macro_series"):
        c.close()
        return []
    out = []
    for ind, lbl in [
        ("Real estate price index - General", "Property prices"),
        ("Real estate price index - Buildings - Apartment", "Apartment prices"),
        ("Real estate price index - Lands - Land", "Land prices"),
    ]:
        s = _series_signal(cur, ind, lbl)
        if s:
            out.append(s)
    c.close()
    return out


def market_overview(db_path: str, days: int = 30) -> dict:
    """What changed in the market over the last `days`: new listings, price moves, active areas,
    competitor activity — all from real change events + sourced competitor data."""
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    c = _conn(db_path); cur = c.cursor()
    if not _has_table(cur, "market_changes"):
        # Pipeline change-log absent (e.g. a core-only DB) — honest empty overview,
        # never a 500 that the browser would surface as a CORS/console error.
        c.close()
        return {"totals": {"window_days": days, "new_listings": 0, "price_increases": 0,
                           "price_drops": 0, "delisted": 0, "total_events": 0,
                           "avg_increase_pct": None, "avg_drop_pct": None},
                "active_areas": [], "recent_events": [], "competitors": [], "news": [],
                "last_update": None, "key_signals": key_signals(db_path)}

    def n(where, args=()):
        return cur.execute(f"SELECT COUNT(*) FROM market_changes WHERE detected_at>=? {where}", (since, *args)).fetchone()[0]

    totals = {
        "window_days": days,
        "new_listings": n("AND change_type='new'"),
        "price_increases": n("AND change_type='price_up'"),
        "price_drops": n("AND change_type='price_down'"),
        "delisted": n("AND change_type='delisted'"),
        "total_events": n(""),
    }
    avg_up = cur.execute("SELECT ROUND(AVG(delta_pct),1) FROM market_changes WHERE change_type='price_up' AND detected_at>=?", (since,)).fetchone()[0]
    avg_down = cur.execute("SELECT ROUND(AVG(delta_pct),1) FROM market_changes WHERE change_type='price_down' AND detected_at>=?", (since,)).fetchone()[0]
    totals["avg_increase_pct"] = avg_up
    totals["avg_drop_pct"] = avg_down

    # most-active areas (by change count) — the "which areas are moving" signal
    active_areas = [dict(r) for r in cur.execute(
        "SELECT neighborhood AS area, COUNT(*) AS changes, "
        "SUM(change_type='new') AS new, SUM(change_type='price_up') AS up, SUM(change_type='price_down') AS down "
        "FROM market_changes WHERE detected_at>=? AND neighborhood IS NOT NULL "
        "GROUP BY neighborhood ORDER BY changes DESC LIMIT 10", (since,))]

    # recent notable events (price moves first, then new)
    recent = [dict(r) for r in cur.execute(
        "SELECT detected_at, change_type, neighborhood AS area, property_type, old_value, new_value, delta_pct, source_url "
        "FROM market_changes WHERE detected_at>=? ORDER BY "
        "CASE change_type WHEN 'price_up' THEN 0 WHEN 'price_down' THEN 0 ELSE 1 END, change_id DESC LIMIT 25", (since,))]

    # competitor activity (sourced table)
    competitors = []
    try:
        competitors = [dict(r) for r in cur.execute(
            "SELECT project_name_en AS project, developer, area_en AS area, status, "
            "price_jd_per_m2, payment_plan, source_url FROM re_competitor_projects "
            "WHERE project_name_en IS NOT NULL LIMIT 20")]
    except sqlite3.OperationalError:
        pass

    # market news & announcements (gov / regulatory / infrastructure / launches / news)
    news = []
    try:
        news = [dict(r) for r in cur.execute(
            "SELECT event_date, category, title_en, summary_en, area_en, impact, source_name, source_url, confidence "
            "FROM re_market_news WHERE event_date>=? OR event_date IS NULL "
            "ORDER BY event_date DESC LIMIT 30", (since,))]
    except sqlite3.OperationalError:
        pass

    # last pipeline run (freshness)
    freshness = None
    try:
        r = cur.execute("SELECT source_key, finished_at, status, rows_in, changes FROM pipeline_runs ORDER BY run_id DESC LIMIT 1").fetchone()
        if r: freshness = dict(r)
    except sqlite3.OperationalError:
        pass

    c.close()
    return {"totals": totals, "active_areas": active_areas, "recent_events": recent,
            "competitors": competitors, "news": news, "last_update": freshness,
            "key_signals": key_signals(db_path)}


def weekly_brief(db_path: str) -> dict:
    """The manager's 'weekly management market intelligence brief' — a plain-language summary
    built from real change counts. Every sentence is backed by a number from market_changes."""
    ov = market_overview(db_path, days=7)
    t = ov["totals"]
    lines = []
    if t["total_events"] == 0:
        lines.append("No material market changes were detected this week from the monitored sources.")
    else:
        lines.append(
            f"This week the market monitor recorded {t['total_events']} changes across the tracked areas: "
            f"{t['new_listings']} newly-advertised property listings, {t['price_increases']} price increases"
            + (f" (avg +{t['avg_increase_pct']}%)" if t['avg_increase_pct'] else "")
            + f", and {t['price_drops']} price drops"
            + (f" (avg {t['avg_drop_pct']}%)" if t['avg_drop_pct'] else "")
            + ".")
        if ov["active_areas"]:
            top = ov["active_areas"][0]
            lines.append(f"The most active area was {top['area']} ({top['changes']} changes: "
                         f"{top['new']} new, {top['up']} up, {top['down']} down).")
        if t["price_drops"] > t["price_increases"]:
            lines.append("Competitor asking prices softened more than they rose this week — worth watching before the next launch-price review.")
        elif t["price_increases"] > t["price_drops"]:
            lines.append("Competitor asking prices firmed this week, which supports holding or raising launch prices.")
    if ov["competitors"]:
        lines.append(f"{len(ov['competitors'])} competitor projects are under active monitoring for new phases, price or payment-plan changes.")
    lines.append("Note: figures reflect advertised (asking) data; Jordan does not publish sold prices. A disappeared listing is treated as delisted, never as sold.")

    return {"week_ending": dt.date.today().isoformat(),
            "headline": lines[0],
            "brief": " ".join(lines),
            "metrics": t,
            "top_areas": ov["active_areas"][:5]}
