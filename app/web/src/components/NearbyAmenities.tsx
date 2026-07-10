import type { AreaAmenities } from "../lib/poi";
import { AMENITY_GROUPS } from "../lib/poi";
import { jd } from "../lib/format";

// "What's nearby" — grouped amenity counts for the selected area, from
// area_amenities.json. Honest: a 0 shows as "none" muted, never hidden. Serves
// builder/agent/buyer transparency (anyone should see everything).
export function NearbyAmenities({ amenities }: { amenities: AreaAmenities | null }) {
  if (!amenities) {
    return (
      <section className="px-4 pt-4" aria-label="Nearby amenities">
        <div className="mb-2 label-eyebrow">What's nearby</div>
        <div className="card border-dashed p-3 text-2xs leading-relaxed text-ink-dim">
          No amenity counts for this area yet.
        </div>
      </section>
    );
  }

  const airportKm = amenities.km_to_airport;
  const highwayKm = amenities.km_to_highway;

  return (
    <section className="px-4 pt-4" aria-label="Nearby amenities">
      <div className="mb-2 flex items-center justify-between">
        <span className="label-eyebrow">What's nearby</span>
        <span className="text-2xs text-ink-mute tnum">{jd(amenities.total_poi_n)} POIs mapped</span>
      </div>

      <div className="space-y-2">
        {AMENITY_GROUPS.map((g) => {
          const items = g.items.map((it) => ({ label: it.label, n: Number(amenities[it.field] ?? 0) }));
          const groupTotal = items.reduce((a, it) => a + it.n, 0);
          return (
            <div key={g.key} className="card p-2.5">
              <div className="mb-1.5 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full" style={{ background: g.color }} aria-hidden />
                <span className="text-[11px]" aria-hidden>{g.icon}</span>
                <span className="text-[12px] font-medium text-ink">{g.label}</span>
                <span className="ml-auto tnum text-2xs text-ink-mute">{jd(groupTotal)}</span>
              </div>
              <div className="flex flex-wrap gap-x-3 gap-y-1">
                {items.map((it) => (
                  <span
                    key={it.label}
                    className={`inline-flex items-center gap-1 text-2xs ${it.n === 0 ? "text-ink-faint" : "text-ink-dim"}`}
                  >
                    <span className={`tnum font-medium ${it.n === 0 ? "text-ink-faint" : "text-ink"}`}>
                      {it.n === 0 ? "none" : jd(it.n)}
                    </span>
                    {it.label}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div className="card mt-2 divide-y divide-line-soft">
        <Row label="Nearest airport" value={`${amenities.nearest_airport || "—"}${Number.isFinite(airportKm) ? ` · ${airportKm.toFixed(1)} km` : ""}`} />
        <Row label="Main highway" value={Number.isFinite(highwayKm) ? `${highwayKm.toFixed(2)} km` : "—"} />
      </div>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between px-2.5 py-1.5 text-[12px]">
      <span className="text-ink-dim">{label}</span>
      <span className="tnum text-ink">{value}</span>
    </div>
  );
}
