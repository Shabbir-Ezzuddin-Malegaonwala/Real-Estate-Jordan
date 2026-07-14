import { useState } from "react";
import { POI_CATEGORIES, GEO_OVERLAYS } from "../lib/poi";

export interface LayerState {
  zoning: boolean;
  pois: boolean;
  comparables: boolean;
  future: boolean;
  roads: boolean;
  areaPrices: boolean;
  listings: boolean;
}

// Grouped map-layer control: amenity categories (9), geographic overlays, and the
// analytical layers. Toggling an amenity/overlay lazy-loads its data on first
// enable; the heavy Water layer (8.4 MB) shows a loading state.
export function MapLayers({
  state,
  onToggle,
  poiState,
  onTogglePoi,
  loading,
}: {
  state: LayerState;
  onToggle: (key: keyof LayerState) => void;
  poiState: Record<string, boolean>;
  onTogglePoi: (key: string) => void;
  loading: Record<string, boolean>;
}) {
  const [open, setOpen] = useState(true);

  return (
    <div className="pointer-events-auto absolute right-3 top-3 z-10 w-56 card shadow-2xl">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between border-b border-line px-3 py-2"
      >
        <span className="label-eyebrow">Map layers</span>
        <span className="text-2xs text-ink-mute">{open ? "Hide ▾" : "Show ▸"}</span>
      </button>

      {open && (
        <div className="scroll-thin max-h-[calc(100vh-120px)] overflow-y-auto">
          <Group title="Amenities">
            {POI_CATEGORIES.map((c) => (
              <Toggle
                key={c.key}
                checked={!!poiState[c.key]}
                onChange={() => onTogglePoi(c.key)}
                label={c.label}
                color={c.color}
                icon={c.icon}
                loading={loading[c.key]}
              />
            ))}
          </Group>

          <Group title="Geography">
            {GEO_OVERLAYS.map((o) => (
              <Toggle
                key={o.key}
                checked={!!poiState[o.key]}
                onChange={() => onTogglePoi(o.key)}
                label={o.label}
                color={o.color}
                icon={o.icon}
                loading={loading[o.key]}
                note={o.heavy ? "8 MB" : undefined}
              />
            ))}
          </Group>

          <Group title="Prices">
            <Toggle checked={state.areaPrices} onChange={() => onToggle("areaPrices")} label="Asking price by area" color="#1d4ed8" />
            <Toggle checked={state.listings} onChange={() => onToggle("listings")} label="All listings" color="#3b82f6" note="19k" />
          </Group>

          <Group title="Analytical">
            <Toggle checked={state.comparables} onChange={() => onToggle("comparables")} label="Comparables" color="#e6a94b" />
            <Toggle checked={state.future} onChange={() => onToggle("future")} label="Future signals" color="#5fb2c9" />
            <Toggle checked={state.roads} onChange={() => onToggle("roads")} label="Road network" color="#8794a5" />
            <Toggle checked={state.zoning} onChange={() => onToggle("zoning")} label="Land use" color="#9aa6b6" note="OSM" />
          </Group>

          <div className="border-t border-line px-3 py-1.5 text-2xs leading-relaxed text-ink-faint">
            Asking prices are portal medians (not appraised). Points appear as you zoom in.
          </div>
        </div>
      )}
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-line first:border-t-0">
      <div className="px-3 pt-2 pb-0.5">
        <span className="label-eyebrow">{title}</span>
      </div>
      <div className="px-2 pb-1.5">{children}</div>
    </div>
  );
}

function Toggle({
  checked,
  onChange,
  label,
  color,
  icon,
  loading,
  note,
}: {
  checked: boolean;
  onChange: () => void;
  label: string;
  color: string;
  icon?: string;
  loading?: boolean;
  note?: string;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 rounded-[2px] px-1.5 py-1 text-[12px] hover:bg-raised">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="h-3 w-3 accent-accent"
        aria-label={`Toggle ${label}`}
      />
      <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: color }} aria-hidden />
      {icon && <span className="text-[11px]" aria-hidden>{icon}</span>}
      <span className="truncate text-ink-dim">{label}</span>
      {loading ? (
        <span className="ml-auto text-2xs text-cyan">loading…</span>
      ) : note ? (
        <span className="ml-auto text-2xs text-ink-faint">{note}</span>
      ) : null}
    </label>
  );
}
