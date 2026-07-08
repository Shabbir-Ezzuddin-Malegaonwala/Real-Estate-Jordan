"""Build a gap-free neighbourhood map layer for Jordan real estate.

Layer hierarchy (frontend should prefer top-down, fall back on absence):
  1. official GAM polygons        (not available now: geo-blocked)
  2. Voronoi tessellation         -> neighborhoods_voronoi.geojson  (THIS FILE)
  3. approximate circles fallback -> neighborhoods.geojson          (kept as-is)

Centroids come from the geocoded listing corpus (median lat/lng per
neighbourhood). Voronoi over those centroids, clipped to the buffered convex
hull of all centroids, guarantees every point on the map belongs to its
nearest neighbourhood with zero gaps.

Also emits opportunity_heatmap.geojson: the same polygons carrying a
transparent, tunable v1 opportunity score built only from data we hold.
"""
import csv
import json
import statistics as st
from collections import Counter, defaultdict

import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import MultiPoint, Polygon
from shapely.ops import unary_union

ROOT = r"C:\Rubicon\Real-Estate-Jordan"
LISTINGS = rf"{ROOT}\data\raw\friend\listings_friend_geocoded.csv"
GEOFEATURES = rf"{ROOT}\data\raw\friend\listing_geofeatures_clean.csv"
OUT_VORONOI = rf"{ROOT}\data\processed\neighborhoods_voronoi.geojson"
OUT_HEATMAP = rf"{ROOT}\data\processed\opportunity_heatmap.geojson"

# Neighbourhoods the pricing engine actually serves.
ENGINE_COVERED = {"Abdoun", "Dabouq", "Sweifieh", "Khalda", "Shmeisani"}

# Collapse spelling variants of the same governorate.
GOV_ALIAS = {"Maan": "Ma`An", "Ajlun": "Ajloun", "Tafielah": "Tafilah"}

# Opportunity score weights (v1 heuristic; sum of active weights = 1.0).
# growth / future_signals are reserved slots at weight 0 until data exists.
W_DEMAND = 0.40
W_PRICE = 0.35
W_SUPPLY = 0.25  # applied to (100 - supply_pressure): scarce supply = opening
W_GROWTH = 0.0
W_FUTURE = 0.0

CLIP_BUFFER_DEG = 0.05  # ~5 km so edge centroids get a real cell


def load_centroids():
    pts = defaultdict(list)
    prices = defaultdict(list)
    districts = defaultdict(Counter)
    for r in csv.DictReader(open(LISTINGS, encoding="utf-8")):
        try:
            lat, lng = float(r["lat"]), float(r["lng"])
        except (ValueError, KeyError):
            continue
        n = r["neighborhood"]
        pts[n].append((lat, lng))
        districts[n][r["district"]] += 1
        try:
            price, area = float(r["price_jd"]), float(r["area_m2"])
            if price > 0 and area > 0:
                prices[n].append(price / area)
        except (ValueError, KeyError):
            pass
    centroids = {}
    for n, coords in pts.items():
        centroids[n] = {
            "neighborhood": n,
            "governorate": GOV_ALIAS.get(
                districts[n].most_common(1)[0][0], districts[n].most_common(1)[0][0]
            ),
            "centroid_lat": round(st.median(la for la, _ in coords), 6),
            "centroid_lng": round(st.median(lo for _, lo in coords), 6),
            "listing_count": len(coords),
            "price_per_m2": round(st.median(prices[n]), 1) if prices[n] else None,
            "is_covered": n in ENGINE_COVERED,
        }
    return centroids


def load_geofeatures(listing_ids_by_neigh):
    pop = {}
    ntl = {}
    for r in csv.DictReader(open(GEOFEATURES, encoding="utf-8")):
        try:
            pop[r["listing_id"]] = float(r["population_density"])
            ntl[r["listing_id"]] = float(r["nightlight_intensity"])
        except (ValueError, KeyError):
            continue
    demand = {}
    for n, ids in listing_ids_by_neigh.items():
        pv = [pop[i] for i in ids if i in pop]
        nv = [ntl[i] for i in ids if i in ntl]
        demand[n] = {
            "population_density": round(st.median(pv), 1) if pv else None,
            "nightlight_intensity": round(st.median(nv), 2) if nv else None,
        }
    return demand


def listing_ids_by_neighborhood():
    ids = defaultdict(list)
    for r in csv.DictReader(open(LISTINGS, encoding="utf-8")):
        ids[r["neighborhood"]].append(r["listing_id"])
    return ids


def finite_voronoi_polygons(points):
    """scipy Voronoi -> list of finite polygon vertex arrays aligned to points.

    Rebuilds unbounded regions by projecting each open ridge outward far
    enough to be clipped later, so every input point gets a closed polygon.
    """
    vor = Voronoi(points)
    center = points.mean(axis=0)
    radius = np.ptp(points, axis=0).max() * 10

    ridges = defaultdict(list)
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        ridges[p1].append((p2, v1, v2))
        ridges[p2].append((p1, v1, v2))

    polygons = []
    for p_idx, region_idx in enumerate(vor.point_region):
        vertices = vor.regions[region_idx]
        if all(v >= 0 for v in vertices) and vertices:
            polygons.append(vor.vertices[vertices])
            continue
        finite = {v: vor.vertices[v] for v in vertices if v >= 0}
        new_pts = list(finite.values())
        for p2, v1, v2 in ridges[p_idx]:
            if v2 < 0:
                v1, v2 = v2, v1
            if v1 >= 0:
                continue
            t = vor.points[p2] - vor.points[p_idx]
            t /= np.linalg.norm(t)
            normal = np.array([-t[1], t[0]])
            midpoint = vor.points[[p_idx, p2]].mean(axis=0)
            direction = np.sign(np.dot(midpoint - center, normal)) * normal
            new_pts.append(vor.vertices[v2] + direction * radius)
        new_pts = np.array(new_pts)
        # Voronoi cells are convex: order vertices around the cell's own centroid.
        local = new_pts.mean(axis=0)
        angles = np.arctan2(new_pts[:, 1] - local[1], new_pts[:, 0] - local[0])
        polygons.append(new_pts[np.argsort(angles)])
    return polygons


def build_polygons(centroids):
    names = list(centroids)
    # Voronoi works in (x=lng, y=lat).
    coords = np.array(
        [[centroids[n]["centroid_lng"], centroids[n]["centroid_lat"]] for n in names]
    )
    # Jitter exact duplicate centroids so Voronoi stays non-degenerate.
    seen = {}
    for i, (x, y) in enumerate(coords):
        key = (round(x, 6), round(y, 6))
        if key in seen:
            coords[i] += np.array([1e-5, 1e-5]) * (seen[key])
        seen[key] = seen.get(key, 0) + 1

    clip = MultiPoint(coords).convex_hull.buffer(CLIP_BUFFER_DEG)
    raw = finite_voronoi_polygons(coords)

    result = {}
    for name, poly_pts in zip(names, raw):
        cell = Polygon(poly_pts).buffer(0).intersection(clip)
        if cell.is_empty:
            continue
        if cell.geom_type == "MultiPolygon":
            cell = max(cell.geoms, key=lambda g: g.area)
        result[name] = cell
    return result


def polygon_ring(geom):
    ring = [[round(x, 6), round(y, 6)] for x, y in geom.exterior.coords]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return [ring]


def minmax(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return lambda v: 0.0
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return lambda v: 50.0 if v is not None else 0.0
    return lambda v: round((v - lo) / (hi - lo) * 100, 1) if v is not None else 0.0


def opportunity_scores(centroids, demand):
    # demand raw = mean of normalized population and nightlight (listing-density fallback).
    pop_norm = minmax([demand[n]["population_density"] for n in centroids])
    ntl_norm = minmax([demand[n]["nightlight_intensity"] for n in centroids])
    dens_norm = minmax([centroids[n]["listing_count"] for n in centroids])
    price_norm = minmax([centroids[n]["price_per_m2"] for n in centroids])
    supply_norm = minmax([centroids[n]["listing_count"] for n in centroids])

    scores = {}
    for n, c in centroids.items():
        d = demand[n]
        parts = [x for x in (pop_norm(d["population_density"]),
                             ntl_norm(d["nightlight_intensity"])) if x]
        demand_density = round(sum(parts) / len(parts), 1) if parts \
            else dens_norm(c["listing_count"])
        price_level = price_norm(c["price_per_m2"])
        supply_pressure = supply_norm(c["listing_count"])
        growth = 0.0
        future_signals = 0.0
        score = round(
            W_DEMAND * demand_density
            + W_PRICE * price_level
            + W_SUPPLY * (100 - supply_pressure)
            + W_GROWTH * growth
            + W_FUTURE * future_signals,
            1,
        )
        scores[n] = {
            "score": score,
            "price_level": price_level,
            "demand_density": demand_density,
            "supply_pressure": supply_pressure,
            "growth": growth,
            "future_signals": future_signals,
        }
    return scores


def write_geojson(path, features):
    fc = {"type": "FeatureCollection", "features": features}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False, indent=1)


def main():
    centroids = load_centroids()
    ids = listing_ids_by_neighborhood()
    demand = load_geofeatures(ids)
    polygons = build_polygons(centroids)
    scores = opportunity_scores(centroids, demand)

    voronoi_features = []
    heatmap_features = []
    for name, geom in polygons.items():
        c = centroids[name]
        base_props = {
            "neighborhood": name,
            "governorate": c["governorate"],
            "centroid_lat": c["centroid_lat"],
            "centroid_lng": c["centroid_lng"],
            "listing_count": c["listing_count"],
            "source": "voronoi",
            "is_covered": c["is_covered"],
        }
        ring = polygon_ring(geom)
        voronoi_features.append({
            "type": "Feature",
            "properties": base_props,
            "geometry": {"type": "Polygon", "coordinates": ring},
        })
        heat_props = dict(base_props)
        heat_props.update(scores[name])
        heat_props["price_per_m2"] = c["price_per_m2"]
        heat_props["population_density"] = demand[name]["population_density"]
        heat_props["nightlight_intensity"] = demand[name]["nightlight_intensity"]
        heatmap_features.append({
            "type": "Feature",
            "properties": heat_props,
            "geometry": {"type": "Polygon", "coordinates": ring},
        })

    write_geojson(OUT_VORONOI, voronoi_features)
    write_geojson(OUT_HEATMAP, heatmap_features)

    verify(centroids, polygons, voronoi_features)


def verify(centroids, polygons, features):
    print("=" * 60)
    print("BUILD SUMMARY")
    print("=" * 60)
    print(f"neighbourhoods with a centroid : {len(centroids)}")
    print(f"tessellated (on the map)       : {len(polygons)}")
    covered = sum(1 for n in polygons if centroids[n]["is_covered"])
    print(f"  engine-covered (is_covered)  : {covered}")
    print(f"  context                      : {len(polygons) - covered}")
    govs = Counter(centroids[n]["governorate"] for n in polygons)
    print(f"governorates represented       : {len(govs)}")
    for g, k in govs.most_common():
        print(f"    {g:20s} {k}")

    # closure + validity
    open_rings = sum(
        1 for f in features
        if f["geometry"]["coordinates"][0][0] != f["geometry"]["coordinates"][0][-1]
    )
    print(f"open (unclosed) rings          : {open_rings}")

    # gap check: union area vs clip area
    geoms = list(polygons.values())
    union = unary_union(geoms)
    clip = MultiPoint(
        [[centroids[n]["centroid_lng"], centroids[n]["centroid_lat"]] for n in centroids]
    ).convex_hull.buffer(CLIP_BUFFER_DEG)
    coverage = union.area / clip.area * 100
    print(f"coverage of clip extent        : {coverage:.2f}%  (100% = zero gaps)")
    # overlap check
    overlap = sum(g.area for g in geoms) - union.area
    print(f"total inter-cell overlap area  : {overlap:.6f} deg^2 (≈0 expected)")


if __name__ == "__main__":
    main()
