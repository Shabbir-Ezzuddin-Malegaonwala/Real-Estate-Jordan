"""Phase 2 — join satellite/GIS grids onto listings (the features the ref app never had).

For every geocoded listing (lat/lng present) attach:
  * elevation_m, slope_deg     <- Copernicus GLO-30 DEM        (terrain / view signal)
  * ntl_radiance               <- VIIRS night-lights           (affluence proxy)
  * pop_density                <- GHS-POP                      (demand density)
  * dist_school_km / dist_hospital_km / dist_mall_km  <- OSM POIs (amenity proximity)

Nearest-cell / nearest-POI via scipy cKDTree in a local equirectangular km projection
(fast, accurate enough within Jordan). Only geocoded rows get values; the rest keep blank.
Rewrites the national listings CSV in place (adds the new columns if absent).

Usage:  python scrapers/enrich_spatial.py
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

CSV = Path("data/processed/listings_national_20260708.csv")
SRC = Path("D:/Rubikon Labs/Project on Jordan/Data")
DEM = SRC / "Copernicus_DEM_Jordan/output/jordan_dem_grid.csv"
GHS = SRC / "GHS_POP_Jordan/output/jordan_ghs_pop_grid.csv"
VIIRS = SRC / "VIIRS_NightLights_Jordan/output/jordan_viirs_ntl_grid.csv"
POIS = SRC / "OSM_Geofabrik_Jordan/csv/pois.csv"

NEW_COLS = ["elevation_m", "slope_deg", "ntl_radiance", "pop_density",
            "dist_school_km", "dist_hospital_km", "dist_mall_km"]

LAT0 = 31.5  # reference latitude for the km projection (Jordan center)
KX = 111.320 * math.cos(math.radians(LAT0))   # km per degree lon
KY = 110.574                                    # km per degree lat


def project(lon, lat):
    return np.column_stack([np.asarray(lon) * KX, np.asarray(lat) * KY])


def load_grid(path, val_cols):
    lon, lat, vals = [], [], {c: [] for c in val_cols}
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        try:
            lo, la = float(r["lon"]), float(r["lat"])
        except (ValueError, KeyError):
            continue
        lon.append(lo); lat.append(la)
        for c in val_cols:
            try:
                vals[c].append(float(r[c]))
            except (ValueError, KeyError):
                vals[c].append(float("nan"))
    return project(lon, lat), {c: np.array(v) for c, v in vals.items()}


def poi_cat(subtype: str) -> str | None:
    s = (subtype or "").lower()
    if "school" in s or "kindergarten" in s:
        return "school"
    if "hospital" in s or "clinic" in s or "doctors" in s:
        return "hospital"
    if "mall" in s or "supermarket" in s or "marketplace" in s or "department_store" in s:
        return "mall"
    return None


def load_poi_trees():
    cats = {"school": [], "hospital": [], "mall": []}
    for r in csv.DictReader(open(POIS, encoding="utf-8-sig")):
        c = poi_cat(r.get("subtype") or r.get("category"))
        if not c:
            continue
        try:
            lo, la = float(r["lon"]), float(r["lat"])
        except (ValueError, KeyError):
            continue
        cats[c].append((lo, la))
    trees = {}
    for c, pts in cats.items():
        if pts:
            arr = np.array(pts)
            trees[c] = cKDTree(project(arr[:, 0], arr[:, 1]))
    return trees


def main() -> None:
    print("loading grids...")
    dem_pts, dem_v = load_grid(DEM, ["elevation_m", "slope_deg"])
    ghs_pts, ghs_v = load_grid(GHS, ["pop_density_per_km2"])
    ntl_pts, ntl_v = load_grid(VIIRS, ["ntl_radiance"])
    dem_t, ghs_t, ntl_t = cKDTree(dem_pts), cKDTree(ghs_pts), cKDTree(ntl_pts)
    poi_t = load_poi_trees()
    print(f"  DEM {len(dem_pts):,} · GHS {len(ghs_pts):,} · VIIRS {len(ntl_pts):,} · "
          f"POI trees {sorted(poi_t)}")

    rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
    hdr = list(rows[0].keys())
    for c in NEW_COLS:
        if c not in hdr:
            hdr.append(c)

    geo_idx, geo_xy = [], []
    for i, r in enumerate(rows):
        for c in NEW_COLS:
            r.setdefault(c, "")
        try:
            lo, la = float(r["lng"]), float(r["lat"])
        except (ValueError, KeyError):
            continue
        geo_idx.append(i); geo_xy.append((lo, la))

    if geo_xy:
        arr = np.array(geo_xy)
        P = project(arr[:, 0], arr[:, 1])
        _, di = dem_t.query(P); _, gi = ghs_t.query(P); _, ni = ntl_t.query(P)
        dpoi = {c: poi_t[c].query(P)[0] for c in poi_t}
        for k, i in enumerate(geo_idx):
            r = rows[i]
            ev, sl = dem_v["elevation_m"][di[k]], dem_v["slope_deg"][di[k]]
            r["elevation_m"] = "" if math.isnan(ev) else f"{ev:.1f}"
            r["slope_deg"] = "" if math.isnan(sl) else f"{sl:.2f}"
            pd = ghs_v["pop_density_per_km2"][gi[k]]
            r["pop_density"] = "" if math.isnan(pd) else f"{pd:.1f}"
            nt = ntl_v["ntl_radiance"][ni[k]]
            r["ntl_radiance"] = "" if math.isnan(nt) else f"{nt:.3f}"
            for c, col in (("school", "dist_school_km"), ("hospital", "dist_hospital_km"),
                           ("mall", "dist_mall_km")):
                if c in dpoi:
                    r[col] = f"{dpoi[c][k]:.3f}"

    with CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr)
        w.writeheader(); w.writerows(rows)

    n = len(rows); g = len(geo_idx)
    print(f"enriched {g:,}/{n:,} geocoded rows with spatial features. Coverage:")
    for c in NEW_COLS:
        filled = sum(1 for r in rows if str(r.get(c) or "").strip())
        print(f"  {c:<18} {100*filled/n:5.1f}%")


if __name__ == "__main__":
    main()
