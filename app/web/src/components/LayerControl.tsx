import { POI_CATEGORIES } from "../types";
import { POI_COLORS } from "../lib/mapStyle";
import { titleCase } from "../lib/format";

export interface LayerState {
  zoning: boolean;
  pois: boolean;
  comparables: boolean;
  future: boolean;
  roads: boolean;
}

const TOGGLES: { key: keyof LayerState; label: string; note?: string }[] = [
  { key: "zoning", label: "Land use", note: "OSM" },
  { key: "pois", label: "POIs" },
  { key: "comparables", label: "Comparables" },
  { key: "future", label: "Future Signals" },
  { key: "roads", label: "Road network" },
];

export function LayerControl({
  state,
  onToggle,
}: {
  state: LayerState;
  onToggle: (key: keyof LayerState) => void;
}) {
  return (
    <div className="pointer-events-auto absolute right-3 top-3 z-10 w-52 card shadow-2xl">
      <div className="border-b border-line px-3 py-2">
        <span className="label-eyebrow">Layers</span>
      </div>
      <div className="px-2 py-1.5">
        {TOGGLES.map((t) => (
          <label
            key={t.key}
            className="flex cursor-pointer items-center gap-2 rounded-[2px] px-1.5 py-1 text-[12px] hover:bg-raised"
          >
            <input
              type="checkbox"
              checked={state[t.key]}
              onChange={() => onToggle(t.key)}
              className="h-3 w-3 accent-accent"
              aria-label={`Toggle ${t.label} layer`}
            />
            <span className="text-ink-dim">{t.label}</span>
            {t.note && <span className="ml-auto text-2xs text-ink-faint">{t.note}</span>}
          </label>
        ))}
      </div>

      {state.zoning && (
        <div className="border-t border-line px-3 py-2 text-2xs leading-relaxed text-ink-mute">
          Unofficial OSM landuse — GAM regulatory zoning pending.
        </div>
      )}

      {state.pois && (
        <div className="border-t border-line px-3 py-2">
          <span className="label-eyebrow">POI legend</span>
          <div className="mt-1.5 grid grid-cols-2 gap-x-2 gap-y-1">
            {POI_CATEGORIES.map((c) => (
              <span key={c} className="flex items-center gap-1.5 text-2xs text-ink-dim">
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ background: POI_COLORS[c] }}
                  aria-hidden
                />
                {titleCase(c)}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="border-t border-line px-3 py-2 text-2xs leading-relaxed text-ink-mute">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full border border-accent bg-accent/30" aria-hidden />
          Neighbourhood (approx.)
        </span>
      </div>
    </div>
  );
}
