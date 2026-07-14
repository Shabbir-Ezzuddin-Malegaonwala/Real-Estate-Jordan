# Live data — how the platform stays current

## Two layers of "live"

1. **App → Engine (on-demand):** the dashboard computes every price live from the
   database on each `/recommend` call. This has always worked.
2. **Engine DB → external sources (scheduled refresh):** the database itself is
   kept fresh by the auto-update pipeline that pulls from the live portals and
   government sources. This is what "fetch live data from live sources" means.

## The canonical database (important)

There is **one canonical DB** the whole platform must use:

    C:/Rubicon/Real-Estate-Jordan/db/jordan_re.sqlite

The auto-update pipeline (`pipeline/run_all.py`, in the version-2 tree) writes
here. The dashboard API **must** read from here too — otherwise it serves a stale
copy. This is pinned in `app/api/run.ps1` via `JORDAN_RE_DB`, and can be
overridden with that env var.

> Fixed 2026-07-15: the API had been reading a separate stale copy
> (`JRE-v3/db/jordan_re.sqlite`, last refreshed 2026-07-08) while the pipeline
> updated the canonical DB (2026-07-14/15). Repointing `JORDAN_RE_DB` at the
> canonical DB closed the gap. The canonical DB is a strict superset (all engine
> tables + the `re_*` research tables + `market_changes`/`pipeline_*`).

## Running the pipeline

    cd C:/Rubicon/Real-Estate-Jordan
    python pipeline/run_all.py --seed          # one-time: load the source config
    python pipeline/run_all.py --dry-run       # show what's due
    python pipeline/run_all.py                 # run all DUE sources
    python pipeline/run_all.py --only listings --force
    python pipeline/scheduler.py               # APScheduler: run on cadence (deploy box)

Cadence per source (manager's rule — scheduled, not streaming):
listings 1d · CBJ rates 1w · DoS permits 1w · CBJ/DLS index 1m · POIs 1m.

## Source reachability (verified 2026-07-15, from this machine)

| Source | Status | Notes |
|---|---|---|
| Bayut (listings) | ✅ live | forced fetch pulled 240 listings, 230 change events today |
| CBJ (macro) | ✅ reachable | 302 redirect, fetchable |
| OpenSooq (listings) | ⚠️ 403 | anti-bot; needs the residential proxy the config already flags |
| DoS (permits/costs) | ⚠️ unreachable direct | needs Jordan-IP proxy/VPN (`vpn` flag in the source config) |

## Open gaps (priority order)

1. **Only `listings` has ever run.** The macro/gov sources (CBJ rates, DoS
   permits, DLS/CBJ index, OSM/Overture POIs) show `(never)` in `pipeline_sources`.
   Run them once (they need no proxy except DoS/DLS) to populate fresh macro.
2. **Schedule it.** `pipeline/scheduler.py` must run on the deploy box for the
   1d/1w/1m cadence to actually happen; today it only runs when invoked by hand.
3. **Proxy for OpenSooq + DoS/DLS.** Set the residential/Jordan-IP proxy so those
   two sources stop failing.
