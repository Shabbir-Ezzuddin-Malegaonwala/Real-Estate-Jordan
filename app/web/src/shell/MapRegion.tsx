import { useMemo, useState } from "react";
import { dataSource as mockSource } from "../lib/dataSource";
import { useApp } from "../lib/store";
import { Card, Tooltip } from "../ui";

const AMENITY_ROWS: { key: string; label: string; icon: string; defaultOn: boolean }[] = [
  { key: "schools", label: "Schools", icon: "🎓", defaultOn: true },
  { key: "universities", label: "Universities", icon: "🏛️", defaultOn: false },
  { key: "hospitals", label: "Hospitals", icon: "🏥", defaultOn: false },
  { key: "busStops", label: "Bus stops", icon: "🚌", defaultOn: true },
  { key: "shopping", label: "Shopping", icon: "🛒", defaultOn: false },
];
const OVERLAY_ROWS: { key: string; label: string; icon: string }[] = [
  { key: "opportunity", label: "Opportunity heat", icon: "🔥" },
  { key: "roads", label: "Major roads", icon: "🛣️" },
];

// Normalise a coordinate into the 10%-90% band of the container so pins never
// sit flush against the map edge.
function pct(v: number, min: number, max: number): number {
  if (max === min) return 50;
  return ((v - min) / (max - min)) * 80 + 10;
}

export function MapRegion() {
  const { state, setArea } = useApp();
  const areas = useMemo(() => mockSource.listAreas(), []);

  const bounds = useMemo(() => {
    const lngs = areas.map((a) => a.centroid[0]);
    const lats = areas.map((a) => a.centroid[1]);
    return {
      minLng: Math.min(...lngs),
      maxLng: Math.max(...lngs),
      minLat: Math.min(...lats),
      maxLat: Math.max(...lats),
    };
  }, [areas]);

  const positioned = useMemo(
    () =>
      areas.map((a) => ({
        ...a,
        x: pct(a.centroid[0], bounds.minLng, bounds.maxLng),
        // Higher latitude = further north = higher on screen = smaller y%.
        y: 100 - pct(a.centroid[1], bounds.minLat, bounds.maxLat),
      })),
    [areas, bounds],
  );

  const selected = state.selectedArea;
  const selectedPin = positioned.find((p) => p.name === selected) ?? null;
  const bundle = selected ? mockSource.getBundle(selected) : null;

  const [controlsOpen, setControlsOpen] = useState(true);
  const [amenityOn, setAmenityOn] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(AMENITY_ROWS.map((r) => [r.key, r.defaultOn])),
  );
  const [overlayOn, setOverlayOn] = useState<Record<string, boolean>>({ opportunity: false, roads: false });

  return (
    <div className="relative min-w-0 flex-1 overflow-hidden bg-[#e9ede2]">
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,0,0,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(0,0,0,0.04) 1px, transparent 1px)",
          backgroundSize: "42px 42px",
        }}
        aria-hidden
      />

      {selectedPin && (
        <div
          className="pointer-events-none absolute h-[190px] w-[190px] -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-stitch-warn bg-stitch-warn/10 transition-all duration-300"
          style={{ left: `${selectedPin.x}%`, top: `${selectedPin.y}%` }}
          aria-hidden
        />
      )}

      {positioned.map((p) => {
        const isSel = p.name === selected;
        return (
          <button
            key={p.name}
            type="button"
            onClick={() => setArea(p.name)}
            title={p.name}
            className={`absolute z-[1] -translate-x-1/2 -translate-y-1/2 text-center transition-opacity ${
              selected && !isSel ? "opacity-40 hover:opacity-70" : ""
            }`}
            style={{ left: `${p.x}%`, top: `${p.y}%` }}
          >
            <span
              className={`inline-flex h-[26px] min-w-[34px] items-center justify-center rounded-full border-2 border-white px-1.5 text-xs font-bold text-white shadow-md transition-transform ${
                isSel ? "scale-110 bg-stitch-warn" : "bg-stitch-brand"
              }`}
            >
              {p.price.toLocaleString()}
            </span>
            <span className="mt-0.5 block rounded bg-white/80 px-1 text-[11px] font-bold text-stitch-ink">
              {p.name}
            </span>
          </button>
        );
      })}

      {bundle && (
        <Card className="absolute bottom-4 left-4 z-[2] w-[min(280px,80vw)] shadow-lg">
          <div className="text-base font-extrabold text-stitch-ink">{bundle.summary.name}</div>
          <div className="mt-0.5 text-2xl font-extrabold text-stitch-brand-dark">
            {bundle.summary.price.toLocaleString()}{" "}
            <span className="text-sm font-semibold text-stitch-muted">JD/m²</span>
          </div>
          <div className="text-[13px] text-stitch-muted">
            Safe {bundle.summary.minSafe.toLocaleString()} – Premium {bundle.summary.premium.toLocaleString()} ·{" "}
            {bundle.summary.confidence} confidence
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Tooltip label="Schools within 1 km">
              <span className="flex items-center gap-1.5 rounded-lg bg-stitch-soft px-2.5 py-1.5 text-sm font-bold text-stitch-ink">
                🎓 {bundle.summary.amenities.schools}
              </span>
            </Tooltip>
            <Tooltip label="Universities within 1 km">
              <span className="flex items-center gap-1.5 rounded-lg bg-stitch-soft px-2.5 py-1.5 text-sm font-bold text-stitch-ink">
                🏛️ {bundle.summary.amenities.universities}
              </span>
            </Tooltip>
            <Tooltip label="Hospitals within 1 km">
              <span className="flex items-center gap-1.5 rounded-lg bg-stitch-soft px-2.5 py-1.5 text-sm font-bold text-stitch-ink">
                🏥 {bundle.summary.amenities.hospitals}
              </span>
            </Tooltip>
            <Tooltip label="Bus stops within 1 km">
              <span className="flex items-center gap-1.5 rounded-lg bg-stitch-soft px-2.5 py-1.5 text-sm font-bold text-stitch-ink">
                🚌 {bundle.summary.amenities.busStops}
              </span>
            </Tooltip>
          </div>
        </Card>
      )}

      <button
        type="button"
        onClick={() => setControlsOpen((v) => !v)}
        title="Map controls"
        className={`absolute top-3 z-[6] rounded-l-lg border border-r-0 border-stitch-line bg-stitch-card px-2.5 py-2 shadow-sm transition-all duration-200 ${
          controlsOpen ? "right-[min(230px,72vw)]" : "right-0 rounded-lg border-r"
        }`}
      >
        ⚙
      </button>
      <div
        className={`absolute inset-y-0 right-0 z-[5] w-[min(230px,72vw)] overflow-y-auto border-l border-stitch-line bg-stitch-card p-3.5 transition-transform duration-200 ${
          controlsOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <h4 className="mt-3 text-[11px] font-bold uppercase tracking-wide text-stitch-muted first:mt-0">
          Amenities on map
        </h4>
        {AMENITY_ROWS.map((r) => (
          <label key={r.key} className="flex cursor-pointer items-center gap-2 py-1.5 text-[13.5px] text-stitch-ink">
            <input
              type="checkbox"
              checked={amenityOn[r.key]}
              onChange={() => setAmenityOn((s) => ({ ...s, [r.key]: !s[r.key] }))}
            />
            {r.icon} {r.label}
          </label>
        ))}
        <h4 className="mt-3 text-[11px] font-bold uppercase tracking-wide text-stitch-muted">Overlays</h4>
        {OVERLAY_ROWS.map((r) => (
          <label key={r.key} className="flex cursor-pointer items-center gap-2 py-1.5 text-[13.5px] text-stitch-ink">
            <input
              type="checkbox"
              checked={overlayOn[r.key]}
              onChange={() => setOverlayOn((s) => ({ ...s, [r.key]: !s[r.key] }))}
            />
            {r.icon} {r.label}
          </label>
        ))}
        <button
          type="button"
          onClick={() => {
            setAmenityOn(Object.fromEntries(AMENITY_ROWS.map((r) => [r.key, false])));
            setOverlayOn({ opportunity: false, roads: false });
          }}
          className="mt-3 w-full rounded-lg border border-stitch-line bg-stitch-soft px-2 py-2 text-[13px] text-stitch-muted"
        >
          Clear all
        </button>
      </div>
    </div>
  );
}
