import { useMemo, useState } from "react";
import { POI_CATEGORIES, GEO_OVERLAYS, type PoiType, type AreaPoiCounts } from "../lib/poi";

export interface LayerState {
  zoning: boolean;
  pois: boolean;
  comparables: boolean;
  future: boolean;
  roads: boolean;
  areaPrices: boolean;
  listings: boolean;
}

interface Props {
  state: LayerState;
  onToggle: (key: keyof LayerState) => void;
  poiState: Record<string, boolean>;
  onTogglePoi: (key: string) => void;
  loading: Record<string, boolean>;
  poiTypes: PoiType[];
  areaCounts: AreaPoiCounts;
  hiddenTypes: Record<string, string[]>;
  onToggleType: (group: string, type: string) => void;
  selectedArea: string | null;
}

// Grouped map-layer control. The 9 amenity GROUPS toggle their data layer; each
// expands to its curated place-types (unique emoji each). When an area is
// selected, a live count per type/group for THAT area is shown alongside.
export function MapLayers(props: Props) {
  const { state, onToggle, poiState, onTogglePoi, loading, poiTypes, areaCounts, hiddenTypes, onToggleType, selectedArea } = props;
  const [open, setOpen] = useState(true);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const typesByGroup = useMemo(() => {
    const m: Record<string, PoiType[]> = {};
    for (const t of poiTypes) (m[t.group] ??= []).push(t);
    return m;
  }, [poiTypes]);

  const counts = selectedArea ? areaCounts[selectedArea] ?? {} : null;
  const groupTotal = (g: string) =>
    counts ? (typesByGroup[g] ?? []).reduce((s, t) => s + (counts[t.key] ?? 0), 0) : null;

  return (
    <div className="pointer-events-auto absolute right-3 top-3 z-10 w-60 card shadow-2xl">
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
          <Group title={selectedArea ? `Amenities — ${selectedArea}` : "Amenities (click a type to expand)"}>
            {POI_CATEGORIES.map((g) => {
              const types = (typesByGroup[g.key] ?? []).slice().sort((a, b) =>
                counts ? (counts[b.key] ?? 0) - (counts[a.key] ?? 0) : a.label.localeCompare(b.label),
              );
              const isOpen = !!expanded[g.key];
              const total = groupTotal(g.key);
              const hidden = hiddenTypes[g.key] ?? [];
              return (
                <div key={g.key}>
                  <div className="flex items-center gap-2 rounded-[2px] px-1.5 py-1 text-[12px] hover:bg-raised">
                    <input
                      type="checkbox"
                      checked={!!poiState[g.key]}
                      onChange={() => onTogglePoi(g.key)}
                      className="h-3 w-3 accent-accent"
                      aria-label={`Toggle ${g.label}`}
                    />
                    <span className="text-[12px]" aria-hidden>{g.icon}</span>
                    <button
                      type="button"
                      onClick={() => setExpanded((s) => ({ ...s, [g.key]: !s[g.key] }))}
                      className="flex flex-1 items-center justify-between text-left text-ink-dim"
                    >
                      <span className="truncate">{g.label}</span>
                      <span className="ml-1 flex items-center gap-1.5 text-2xs text-ink-faint">
                        {loading[g.key] && <span className="text-cyan">…</span>}
                        {total != null && total > 0 && <span className="font-semibold text-ink-dim">{total}</span>}
                        <span>{isOpen ? "▾" : "▸"}</span>
                      </span>
                    </button>
                  </div>
                  {isOpen && (
                    <div className="mb-1 ml-5 border-l border-line pl-1.5">
                      {types.map((t) => (
                        <label key={t.key} className="flex cursor-pointer items-center gap-1.5 rounded-[2px] px-1 py-0.5 text-[11.5px] hover:bg-raised">
                          <input
                            type="checkbox"
                            checked={!hidden.includes(t.key)}
                            onChange={() => onToggleType(g.key, t.key)}
                            className="h-2.5 w-2.5 accent-accent"
                            aria-label={`Toggle ${t.label}`}
                          />
                          <span aria-hidden>{t.emoji}</span>
                          <span className="flex-1 truncate text-ink-dim">{t.label}</span>
                          {counts && <span className="text-2xs text-ink-faint">{counts[t.key] ?? 0}</span>}
                        </label>
                      ))}
                      {types.length === 0 && <div className="px-1 py-0.5 text-2xs text-ink-faint">no subtypes</div>}
                    </div>
                  )}
                </div>
              );
            })}
          </Group>

          <Group title="Geography">
            {GEO_OVERLAYS.map((o) => (
              <Toggle key={o.key} checked={!!poiState[o.key]} onChange={() => onTogglePoi(o.key)} label={o.label} color={o.color} icon={o.icon} loading={loading[o.key]} note={o.heavy ? "8 MB" : undefined} />
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
            {selectedArea ? `Counts are for ${selectedArea}.` : "Select an area to see counts."} Icons appear as you zoom in.
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
  checked, onChange, label, color, icon, loading, note,
}: {
  checked: boolean; onChange: () => void; label: string; color: string; icon?: string; loading?: boolean; note?: string;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 rounded-[2px] px-1.5 py-1 text-[12px] hover:bg-raised">
      <input type="checkbox" checked={checked} onChange={onChange} className="h-3 w-3 accent-accent" aria-label={`Toggle ${label}`} />
      <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: color }} aria-hidden />
      {icon && <span className="text-[11px]" aria-hidden>{icon}</span>}
      <span className="truncate text-ink-dim">{label}</span>
      {loading ? <span className="ml-auto text-2xs text-cyan">loading…</span> : note ? <span className="ml-auto text-2xs text-ink-faint">{note}</span> : null}
    </label>
  );
}
