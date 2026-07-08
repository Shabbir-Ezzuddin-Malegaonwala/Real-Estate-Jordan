# Price Factors & Edge Cases — what moves a builder's launch price in Jordan

**Owner:** Backend/Research · **Created:** 2026-07-08 · **Status:** v1 (seed for the LLM system-prompt + per-area enrichment schema)
**Authority:** `MASTER-PLAN.md` (evidence-driven, never-fabricate, derived-not-hardcoded premiums) · `docs/db-contract.md`

> **What this is.** A structured catalogue of the factors that move a new-build **launch price** in Jordan,
> each with direction, magnitude notes, interaction/edge-cases, the **data source we'd use to obtain it**
> (or the honest gap), and a crisp **LLM reasoning rule**. It ends with an **edge-case matrix** and an
> **enrichment schema seed**. Magnitudes are grounded in web research where possible and are explicitly
> tagged **[measured]**, **[literature rule-of-thumb]**, or **[directional — needs local calibration]**.
> Per `MASTER-PLAN.md §2d-2`, no premium is a hardcoded constant — the numbers below are *priors that
> tell the LLM which direction and roughly how hard to look*; the actual adjustment is **derived from our
> own paired-listing data** and written to `derived_premiums`, with sources.

## 0. Global reasoning rules for the LLM (read first)

1. **Two-signal honesty — never net blindly.** Many locations carry an *up* signal and a *down* signal at once (e.g. a hilltop view **and** an access/isolation penalty). Surface **both** as separate `evidence_objects` with their own sources; let the waterfall show them; do **not** collapse them into a single pre-netted number.
2. **Derived, not assumed.** A factor only earns a numeric adjustment if we can derive it from comparables (`paired listing comparison (n=…)`) or a cited source. Otherwise it is a **qualitative flag** at `confidence=L`, not a percentage.
3. **Asking ≠ sale.** All portal inputs are asking prices; apply the documented asking→sale gap (~5–15%) before treating any derived premium as a transaction reality.
4. **LATEST first.** 2026-to-date evidence dominates; older data is trend/context only.
5. **Context vs lever.** Elevation, population density, and night-lights are **context only** (affluence/activity proxies) — they are **never** a direct price lever (DB decision; they do not correlate with price in our data). They may *explain* a premium the comparables already show; they may not *create* one.
6. **Show the floor.** Never recommend below the cost-approach floor (land + construction). Construction floor from DoS filed licences is **~157–175 JD/m²** — a *licensing floor*, not turnkey; true turnkey is **~220–1,100 JD/m² by finish class** ([Global Property Guide / BUILD_ME]). Use the turnkey band for the real floor, the DoS figure only as an absolute ceiling-of-nonsense check.
7. **Every signal cites.** Nothing reaches the UI without ≥1 source (DB-contract).

---

## 1. Terrain & topography

| Factor | Direction | Magnitude notes | Interaction / edge-cases | Data source | LLM rule |
|---|---|---|---|---|---|
| On a hill / elevated plot | **depends** (view+prestige ↑; construction+access cost ↑) | view premium is real but **[directional]** in JD; slope raises foundation/retaining cost | Hilltop far from any hub → isolation discount can offset the view premium | `listing_geofeatures.elevation_m/slope_deg` (context), DEM grid | If elevated **and** ≤~15 min of a commercial hub → upward view/prestige signal; if elevated **and** far from market/amenities → also raise an access/isolation discount; present both, net neither. Elevation itself is context, the *view* is the priced thing. |
| Slope / gradient of plot | **down** (cost) | steep slope = excavation, retaining walls, harder access → higher build cost, lower usable yield | Mild slope with downhill view can be net-positive (terraced units, unobstructed view) | `slope_deg` | Steep slope → flag construction-cost pressure on the floor; combine with view only if view is corroborated. |
| Valley / low-lying / wadi | **down** | flood/drainage risk, damp, lower prestige, worse views | Near a green wadi that is landscaped (not a flood channel) can read as amenity | `elevation_m` (low rank), OSM waterway/landuse | Low elevation + watercourse nearby → raise a flood/drainage risk flag; do not auto-discount without corroboration. |
| Flat, well-drained plot | **up (mild)** | cheapest to build, predictable — a neutral-to-positive baseline | none major | `slope_deg` ≈ 0 | Treat as the construction-cost baseline; no view premium unless height provides it. |
| Rocky / hard substrate | **down** (cost) | excavation for foundations/basements costs more | Jordan west-Amman is largely limestone bedrock — common, partly priced-in already | Not in our data — **enrichment gap** (geotechnical) | Flag as a possible cost item; mark `L`/gap unless a soil report exists. |

## 2. Land condition & sub-surface

| Factor | Direction | Magnitude notes | Interaction / edge-cases | Data source | LLM rule |
|---|---|---|---|---|---|
| Dry vs wet/marshy ground | **down** if wet | drainage works, damp-proofing, slower build | Rare in arid Amman; more relevant Jordan Valley/Aqaba fringe | **gap** (no soil layer) | Qualitative flag only; do not quantify. |
| Plot regularity / frontage | **up** if regular & wide frontage | irregular/landlocked plots lose buildable yield & access | Corner plot = more frontage/light but more setback → depends | `zoning_plots` geometry (partial) | If plot geometry available, note yield impact qualitatively. |
| Registered land type | context | DLS land-type classification (residential/agri/…) affects what's buildable | Agricultural classification blocks residential build → hard constraint | `dls_land_type_table_2020.xlsx` | If land-type ≠ residential → this is a **regulatory blocker**, not a discount; surface prominently. |

## 3. View & orientation

| Factor | Direction | Magnitude notes | Interaction / edge-cases | Data source | LLM rule |
|---|---|---|---|---|---|
| City / skyline view | **up** | "clear expansive view is one of the most significant drivers of value" [literature]; JD size **[needs local calibration]** | View only holds if **unobstructed** — a facing tower kills it | `listings.view`, `floor_level`/`total_floors` | Derive from paired comps with/without `view`; require height or open aspect to justify; if a blocking building is known, cancel the premium. |
| Height-driven view (high floor) | **up** | ~**0.5–2% per floor** typical; ground→first can be ~9%; top floor up to ~25% over ground in a large Paris study [measured, non-Jordan] | Only where a lift exists; walk-up penalises high floors instead | `floor_level`, `total_floors`, `elevator` | Positive per-floor signal **only if `elevator=y`**; without a lift, high floor flips to a *discount*. Calibrate the per-floor step from our own comps, not the Paris number. |
| Green / landscaped outlook | **up (mild)** | parks/greenery raise desirability [literature] | Green space that is a public park = amenity; a scrubby empty lot ≠ | OSM `park`/`landuse`, `poi` | Premium only for maintained green (park POI within sight/short walk), not any open land. |
| Orientation / aspect (sun) | **depends (mild)** | in hot-arid Amman, **north/east** aspect (less harsh afternoon sun) is often preferred; strong west sun = heat load | `aspect_cardinal` is **context**, not a proven lever here | `listing_geofeatures.aspect_cardinal` | Mention aspect as qualitative comfort context; do not attach a % unless comps show it. Render `flat` literally, never as a compass point. |
| Blocked / facing another building | **down** | loss of view/light/privacy | Interacts with floor: high floor may see *over* the blocker | derivable from geometry — **partial gap** | If a taller neighbour is known, downgrade any view premium; else leave neutral. |

## 4. Location vs the wider city / market

| Factor | Direction | Magnitude notes | Interaction / edge-cases | Data source | LLM rule |
|---|---|---|---|---|---|
| Central / west-Amman prestige address | **up** | Abdoun, Dabouq, Deir Ghbar, Khalda, Sweifieh, Shmeisani = top tier; land **~1,000–1,200 JD/m²** [measured] | Prestige is submarket-level; a poor micro-plot in a prime area still lifts off the area floor | `neighborhood_profiles`, `districts`, listing medians | Anchor to the submarket median first; then adjust for the specific plot. Prestige is the strongest single lever. |
| Far from centre | **down UNLESS self-sufficient** | distance discount, but offset if the area has its own amenities/employment | A far but self-contained township (schools+mall+clinics) offsets much of the distance penalty | drive-time to CBD, `poi` density | If far **and** amenity-rich within the area → reduce the distance discount and cite the offsetting amenities; if far **and** amenity-poor → full isolation discount. Never apply distance blindly. |
| Micro-location within submarket | **depends** | main-street vs quiet cul-de-sac; near vs far from the "good" pocket | The same neighbourhood name spans very different micro-prices | lat/lng + `poi` + roads | Use coordinates, not just the neighbourhood label, when comps allow. |
| Self-sufficiency / amenity completeness | **up** | a location that meets daily needs on-site commands a convenience premium | Overlaps with "far but self-sufficient" | `poi` counts by category per area | Score amenity completeness (schools+health+retail+worship+green present) as a positive modifier to distance. |

## 5. Proximity — positive amenities

| Factor | Direction | Magnitude notes | Interaction / edge-cases | Data source | LLM rule |
|---|---|---|---|---|---|
| Good school nearby | **up (family premium)** | schools raise nearby values [literature] | *Too* close = drop-off traffic/noise → mild negative at the gate | `poi` category `school` | Premium for within short walk/drive; small penalty if directly abutting the gate. |
| Park / green space nearby | **up** | amenity + outlook | Well-kept park ↑; neglected lot ≈ 0 | `poi` `park`, OSM landuse | Positive within walking distance. |
| Mosque nearby | **up (mild, family)** | convenience/community premium in Jordan | *Immediately adjacent* = adhan volume + Friday congestion/parking → mild negative | `poi` `mosque` | Short-walk positive; directly-adjacent slight negative for noise/parking. |
| Mall / shopping / offices | **up (convenience)** | Abdoun, Taj, Mecca, City Mall etc. lift nearby residential | Directly adjacent = traffic/noise/parking spillover → partial offset | `poi` `mall`, OSM retail/commercial | Convenience premium within ~1–2 km; apply a noise/traffic offset if abutting. |
| Hospital nearby | **up (mild)** | access convenience | Directly adjacent = ambulance noise, parking → offset | `poi` `hospital` | Short-distance positive; adjacency offset. |
| Main road / highway access | **up (connectivity)** | good access raises value | **Same feature is negative for noise** if the unit fronts it — the classic two-signal case | roads layer, distance-to-arterial | Connectivity premium for *access*; **separate** noise discount if the unit directly fronts the artery (see §6). Show both. |
| Public transport (BRT corridor) | **up (mild)** | BRT is **operational** on Sweileh corridors + Zarqa + Madaba line [measured] | Only priced where a route actually runs today; Metro is *not* built | `evidence_items`, BRT route geo | Price BRT proximity as *delivered* near live corridors; do **not** price Metro proximity as imminent. |

## 6. Proximity — negative externalities

| Factor | Direction | Magnitude notes | Interaction / edge-cases | Data source | LLM rule |
|---|---|---|---|---|---|
| Highway / arterial noise (fronting) | **down** | homes fronting highways/4-lane arteries sell **~5–15% below** comps a block over; >60 dB measurably lowers price [measured] | Coexists with the *access* premium of the same road — net depends on whether the unit fronts or is set back | roads layer + orientation | Apply a fronting-noise discount **only** to units that face the artery; a set-back/rear unit keeps the access premium without the noise hit. |
| Airport proximity | **depends** | connectivity ↑ but flight-path noise ↓ | Queen Alia is ~30 km south — mostly connectivity, little noise for west Amman; near-field only matters on approach corridors | `poi` `transport`, flight-path geo (gap) | For west-Amman submarkets treat as negligible; only raise noise if under an approach corridor. |
| Industrial zone | **down** | noise, traffic, air quality, low prestige | Light/clean industry less severe than heavy | `zoning_plots`/OSM `industrial` landuse | Discount if industrial landuse within short range; scale by intensity. |
| Cemetery adjacent | **down** | cultural aversion, though quiet | Effect is proximity-decaying; a view *over* one from height less severe | OSM landuse `cemetery` | Adjacency discount, decays fast with distance. |
| Sewage / landfill / treatment | **down** | odour, prestige hit | Wind direction matters (odour plume) | OSM landuse (partial), **gap** | Strong discount if adjacent; note wind caveat. |
| Quarry | **down** | noise, dust, blasting, heavy trucks | west-Amman fringe has quarries | OSM `quarry` landuse | Discount within range. |
| High-crime / unsafe pocket | **down** | reputation penalty | Hard to source objectively in Jordan | **gap** (no crime data) | Only surface if a cited source exists; otherwise omit — do not infer. |

## 7. Regulatory & entitlement

| Factor | Direction | Magnitude notes | Interaction / edge-cases | Data source | LLM rule |
|---|---|---|---|---|---|
| Zoning class / density (Res A–D) | **up** with allowed intensity | Amman residential is classed **A–D**; Class **A** = western affluent, largest plots, lowest density [measured] | Low-density Class A = prestige but *fewer sellable m²* per plot → land value up, unit yield down | **GAP** — we hold OSM landuse only, no `zone_class`/`far`/`max_height_m` (GAM data geo-blocked) | Where FAR/class known, use it to bound buildable area; where unknown, say so and fall back to submarket comps — never invent a FAR. |
| FAR / buildable area | **up** land value with FAR | more buildable m² per land JD = higher residual land value | High FAR + small plot vs low FAR + large plot can price alike | **GAP** (same as above) | If FAR present, feed the residual-land calc; else flag entitlement uncertainty as a risk factor. |
| Height cap | **depends** | caps limit view/premium floors | A height cap on a view plot destroys the upper-floor premium | `zoning_plots.max_height_m` (mostly gap) | If a height cap is known, cap the floor-premium logic accordingly. |
| Green-zone / build-ratio cap | **down** on yield | conservation/green caps limit % of plot built | A prime plot with a heavy build cap (e.g. only a fraction buildable) loses much of its density value | `zoning_plots`, ASEZ layer | Treat a build-cap as a hard yield constraint; show it as a risk, not a vague discount. |
| Foreign-ownership rules | **depends** | ASEZ separate regime; elsewhere MOI approval + reciprocity + retention periods [measured] | Restrictions thin the buyer pool (down) but ASEZ incentives (5% flat tax) can lift Aqaba demand (up) | `evidence_items`, Aqaba rules | For Aqaba, factor buyer-pool + incentive both ways; for mainland, note approval friction for non-Jordanian demand. |
| Land-use ≠ residential | **hard blocker** | agricultural/commercial classification stops residential build | Not a discount — a gate | `dls_land_type_table`, zoning | Surface as a blocking constraint, prominently. |

## 8. Environmental

| Factor | Direction | Magnitude notes | Interaction / edge-cases | Data source | LLM rule |
|---|---|---|---|---|---|
| Air quality | **down** if poor | near industry/arterials | Overlaps industrial/road factors | **gap** (no AQ layer) | Qualitative, tied to industrial/road proximity. |
| Ambient noise | **down** | see arterial/mosque/airport rows | Cumulative across sources | derived from proximity layers | Aggregate noise from all nearby sources; don't double-count with each proximity row — net a single noise view. |
| Flood zone | **down** | wadi/low-lying drainage | Rare in Amman uplands, real in valleys | elevation + waterway (partial) | Flag where low elevation meets a watercourse. |
| Wind / exposure | **mild** | exposed ridge = wind, but also view/cooling | Mostly neutral | `aspect`/`elevation` (context) | Context only. |

## 9. Future signals (appreciation / depreciation ahead)

| Factor | Direction | Magnitude notes | Interaction / edge-cases | Data source | LLM rule |
|---|---|---|---|---|---|
| Planned road / interchange | **up** (access) | announced corridors lift adjacent land | Same road later brings noise once live — a future two-signal | `evidence_items` type `infrastructure` | Price as *future* appreciation at reduced confidence; note the eventual noise flip. |
| Planned transit (Metro) | **up (speculative)** | Metro is feasibility-stage only [measured] | Speculative until funded/under-construction | `evidence_items` | Low-confidence long-horizon signal; never price as imminent. |
| Planned development / township | **up** | new malls/schools/hospitals raise an area | Delivery risk — announced ≠ built | `evidence_items`, `projects` | Confidence scales with how firm/near the project is. |
| Planned negative (industrial/landfill) | **down** | announced disamenity depresses ahead of build | Same delivery-risk caveat | `evidence_items` | Surface as a downside future signal with source. |
| Market trend / momentum | **depends** | DLS 2025 volume **7.18bn JD (+7%)** [measured]; broadly stable-to-rising | Momentum is national; submarkets diverge | `macro_series` (DLS/CBJ), DLS monthly | Use as a gentle time-adjustment/context, not a plot-level lever. |

## 10. Building & unit attributes

| Factor | Direction | Magnitude notes | Interaction / edge-cases | Data source | LLM rule |
|---|---|---|---|---|---|
| Floor level (with lift) | **up** | ~0.5–2%/floor city-view premium [measured, non-JO] | Flips negative without a lift | `floor_level`, `elevator` | Derive per-floor step from our comps; gate on `elevator=y`. |
| Finish quality | **up** | basic→standard→high→luxury ladder; turnkey cost **~220–1,100 JD/m²** tracks it [measured] | Over-finishing above the area's tier doesn't fully recoup | `listings.finish_quality`, `cost_benchmarks` | Match finish to submarket tier; premium for high/luxury only where the area supports it. |
| Building age / new-build | **up** for new | new-build launch commands a premium over resale | Very old with no renovation discounts | `building_age_years` | New-build premium vs area resale comps. |
| Parking | **up** | covered/secure parking valued, scarce in dense areas | Essential in west Amman; less differentiating where abundant | `listings.parking` | Premium for covered/secure, larger where street parking is scarce. |
| Elevator | **up** | enables the high-floor premium | Its main value is unlocking floor premium | `listings.elevator` | Presence flips floor logic positive; absence caps it. |
| Area / size efficiency | **depends** | price/m² often falls as size rises (bigger units cheaper per m²) | Interacts with bedroom count & layout | `area_m2` | Normalise to price/m²; note the size gradient when comparing. |
| Unit type (apartment/villa/land) | **depends** | different markets & buyers | Don't compare villa /m² to apartment /m² | `property_type` | Keep comps within property type. |

---

## 11. Edge-case matrix — concrete scenarios and correct platform behaviour

| # | Scenario | Correct honest behaviour |
|---|---|---|
| 1 | Prime hill, clear city view, but green-zoned with a heavy build-cap (small buildable %) | Show **view/prestige up** AND **build-cap yield-down** as two evidence objects. Land value up per m², but buildable m² limited → residual per sellable m² may not rise. Flag the cap as a risk; never net into one number. |
| 2 | Cheap land far out, but a new road/interchange was just announced | Base = distance/isolation discount (current). Add a **future-signal appreciation** at reduced confidence with the announcement source. Note the road will later add fronting-noise. Keep current vs future in separate `category` buckets. |
| 3 | High floor, great city view, but directly fronts a busy highway | **View/height up** AND **fronting-noise down (~5–15% lit.)** both shown. Height may lift the unit *above* street noise somewhat — mention, but keep both signals; net only from comps, not by assumption. |
| 4 | Hilltop villa, panoramic view, 25 min from nearest hub, no amenities around | **View/prestige up** AND **access/isolation down**. Do not cancel one with the other; present both, and let the recommended band widen (lower confidence) to reflect the tension. |
| 5 | Far suburb, but a self-contained township (mall, schools, clinic on-site) | Reduce the distance discount and **cite the on-site amenities** as the offset. Net position can be near-neutral; explain why the usual distance penalty doesn't fully apply. |
| 6 | Prime area label (e.g. "Khalda") but the specific plot abuts a quarry/industrial edge | Area prestige lifts the floor; **micro-location industrial discount** pulls back. Use coordinates, not the label alone; show the area anchor and the plot-specific penalty separately. |
| 7 | Apartment with `view=city` in listing but a taller tower is going up directly opposite | Downgrade/cancel the view premium; add a **future view-loss risk**. Confidence low; recommend cautious pricing on the view component. |
| 8 | Aqaba plot, foreign buyer interest, inside ASEZ | Apply the **ASEZ regime** (separate rules, 5% flat tax, incentives) — potential demand up; but note reciprocity/retention friction for resale. Cite the foreign-ownership source; do not apply mainland rules. |
| 9 | Plot registered as agricultural land-type | **Hard blocker**, not a discount. Surface prominently: residential build may be disallowed/needs reclassification. Do not output a launch price as if buildable. |
| 10 | High floor but the building has **no elevator** | Flip the floor premium to a **discount** — walk-up penalises upper floors. Explain the elevator gate explicitly. |
| 11 | Mosque/school directly adjacent to the plot | Short-walk convenience is a family premium, but **immediate adjacency** adds noise/traffic/parking → small offset. Show the net as "family-amenity premium, minor adjacency noise offset". |
| 12 | Only 5 comparable sales within 800 m (thin comps) | Widen the recommended band, **lower confidence label**, and add a `risk_factors` entry "thin comparable set". Do not present a tight point price. |
| 13 | Listing dated 2022; our CBJ index ends 2021-Q3 | Time-adjust with the **documented extrapolation assumption**, and disclose it as an assumption + limitation — do not silently present a stale index as current. |
| 14 | Builder wants a luxury finish in a mid-tier submarket | Finish premium is real but **caps at what the area supports** — over-finishing doesn't fully recoup. Recommend to the area's ceiling, flag the recovery risk. |
| 15 | Plot on a steep slope with a downhill unobstructed view | **View up** AND **construction-cost up (slope)**. The floor rises (retaining/foundation) while the view lifts the ceiling — show both; the band may stay wide. |
| 16 | Near a live BRT corridor vs near the (unbuilt) Metro alignment | BRT proximity → **priced as delivered** (mild up). Metro alignment → **speculative future signal**, low confidence, not priced as imminent. Treat the two completely differently. |
| 17 | Same arterial gives great access but the unit is set back behind other buildings | Keep the **access/connectivity premium**; **drop the fronting-noise discount** (it doesn't front the road). Orientation/set-back decides which signals apply. |
| 18 | West-Amman plot near Queen Alia flight path concern raised by builder | For west Amman, airport is ~30 km and mostly **connectivity, negligible noise** — reassure with distance; only raise noise if genuinely under an approach corridor. |
| 19 | Cemetery visible from upper floors but not adjacent at ground | Adjacency discount **decays with distance**; a distant view over one from height is minor. Small/again-qualitative, low confidence. |
| 20 | Elevation is high and night-lights are bright for the area | Use elevation & night-lights as **context** ("affluent, active area") that *explains* a comp-derived premium — **never** as a standalone price lever. State explicitly they are context, not adjustments. |
| 21 | Asking-price comps only, no transaction comps in the pocket | Apply the **asking→sale gap (~5–15%)** before finalising; disclose that the band is asking-derived. |
| 22 | Prime plot but land-use polygon we hold is OSM (unofficial), no FAR | Use submarket comps for the price; **flag entitlement uncertainty** (no official GAM FAR) as a risk; do not invent a FAR or present OSM landuse as regulatory zoning. |

---

## 12. Enrichment schema seed (per-area / per-plot) — turns this catalogue into fields

Each covered area (and, where geocoded, each plot) should carry an enrichment record the engine and LLM read. Every field pairs a **value** with a **source** and **confidence**, and marks whether it is a **lever** or **context**.

```json
{
  "neighborhood": "Abdoun",
  "topography":   { "elevation_rank": "high", "slope": "gentle", "is_hill": true, "source": "listing_geofeatures", "confidence": "H", "role": "context" },
  "view":         { "typical": "city", "obstruction_risk": "low", "source": "listings", "confidence": "M", "role": "lever" },
  "location":     { "prestige_tier": "premium", "drive_min_to_cbd": 12, "self_sufficiency": "high", "source": "neighborhood_profiles+poi", "confidence": "M", "role": "lever" },
  "amenities":    { "schools": 6, "malls": 2, "parks": 3, "hospitals": 1, "mosques": 5, "source": "poi", "confidence": "M", "role": "lever" },
  "negatives":   [ { "type": "arterial_noise", "applies_to": "fronting_units", "magnitude_prior": "-5..-15% [lit]", "source": "osm_roads", "confidence": "L", "role": "lever" } ],
  "regulatory":   { "zone_class": "unknown", "far": null, "max_height_m": null, "build_cap": null, "gap": "GAM FAR geo-blocked", "source": "osm_landuse(placeholder)", "confidence": "L", "role": "lever" },
  "future":      [ { "type": "brt_corridor", "status": "operational", "distance_m": null, "source": "evidence_items", "confidence": "M", "role": "future_signal" } ],
  "cost_floor":   { "construction_turnkey_jd_m2": [220, 1100], "dos_licence_floor_jd_m2": [157, 175], "source": "GlobalPropertyGuide/BUILD_ME + dos_building_cost", "confidence": "M", "role": "floor" },
  "context_only": { "population_density": "high", "nightlight": "high", "note": "affluence/activity proxy — NOT a price lever", "source": "ghs_pop/viirs", "confidence": "H", "role": "context" }
}
```

**Field discipline (mirrors DB-contract):** every enrichment value carries `source` + `confidence` + `role` (`lever` | `context` | `future_signal` | `floor`); unknown → the literal `"unknown"`/`null` + a `gap` note, never a fabricated number. `context`-role fields may explain but never generate a price adjustment.

---

## Summary

- **~45 pricing factors** catalogued across 10 categories (terrain, land condition, view/orientation, location-vs-market, positive proximity, negative externalities, regulatory, environmental, future signals, building attributes), each with direction, grounded/tagged magnitude, interaction edge-cases, data source (or honest gap), and an LLM rule.
- **22 concrete edge-case scenarios** with the correct honest platform behaviour — the seed for the LLM system-prompt's reasoning tests.
- **Enrichment schema seed** provided (per-area/plot JSON) with `lever` vs `context` vs `future_signal` vs `floor` roles.
- **Key honest calibrations baked in:** construction floor is a *licensing* floor (~157–175 JD/m²), true turnkey ~220–1,100 JD/m² by class; elevation/density/night-lights are *context, never levers*; BRT is delivered / Metro is speculative; every two-signal case is shown as two signals, never pre-netted.

**Sources (magnitudes/Jordan specifics):**
- [Global Property Guide — Jordan m² prices](https://www.globalpropertyguide.com/middle-east/jordan/square-meter-prices) · [BUILD_ME Country Report — Jordan](https://www.buildings-mena.com/files/BUILD_MECountryReport-Jordan.pdf)
- [BusinessCloud — factors that influence property valuation](https://businesscloud.co.uk/news/top-10-factors-that-influence-property-valuation/) · [Homes.com — neighborhood factors (noise 5–15%)](https://www.homes.com/learn/how-neighborhoods-affect-home-values/)
- [Vision Constructors — floor level & price](https://vision-constructors.com/real-estate/apartment-floor-price-difference-why-floor-level-changes-property-value) · [56Paris — floor level & price (per-floor / top-floor study)](https://56paris.com/en/how-floor-level-affects-paris-apartment-prices)
- [homes-jordan — Dabouq guide / land investment](https://www.homes-jordan.com/en/blogs/detail/villas-and-mansions-for-sale-and-rent-in-dabouq-amman-homes-jordan-2026-guide) · [tajalsafa — Abdoun & Dabouq prices](https://tajalsafa.com/apartment-prices-in-abdoun-and-dabouq)
- [Amman city profile (ScienceDirect) — Res A–D classes](https://www.sciencedirect.com/science/article/pii/S0264275126001484)
- [Wikipedia — Amman BRT](https://en.wikipedia.org/wiki/Amman_Bus_Rapid_Transit) · [Transit Guide — Amman Metro](https://transitguide.org/amman-metro/)
- [Global Law Experts — foreign ownership Jordan](https://globallawexperts.com/can-foreigners-own-property-in-jordan/) · [Jordan News — 2025 trading volume JD 7.18bn](https://www.jordannews.jo/Section-33/Trade-Industry/Real-Estate-Trading-Volume-Reaches-JD-7-1-Billion-in-2025-48007)
