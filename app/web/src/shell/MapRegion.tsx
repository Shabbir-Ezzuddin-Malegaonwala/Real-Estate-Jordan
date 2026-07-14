import { useCallback, useState } from "react";
import { dataSource } from "../lib/dataSource";
import { useApp } from "../lib/store";
import { Card, Tooltip } from "../ui";
import { MapView } from "../components/MapView";
import { MapLayers } from "../components/MapLayers";
import { Toast } from "../components/Toast";
import { useMapData } from "./mapData";

// Real MapLibre map (whole-Jordan neighbourhood/voronoi coverage, opportunity
// choropleth, POI categories) — reuses the friend's MapView/MapLayers/
// OpportunityLegend verbatim; only the data wiring and the linked detail card
// are owned here. See shell/mapData.ts for the load.
export function MapRegion() {
  const { state, setArea, setSellPin } = useApp();
  const selected = state.selectedArea;
  const {
    geo,
    bundle,
    opportunity,
    error,
    layers,
    setLayers,
    poiState,
    togglePoi,
    layerLoading,
    onLayerLoading,
    poiTypes,
    areaCounts,
    hiddenTypes,
    toggleType,
  } = useMapData();

  const [toast, setToast] = useState<string | null>(null);
  const handleOutside = useCallback(() => {
    setToast("No structured data for this location yet — pick a covered area or search.");
    window.setTimeout(() => setToast(null), 5000);
  }, []);

  // The sidebar's own (simpler) per-area bundle drives the linked detail card —
  // same source the rest of the dashboard's views read from.
  const card = selected ? dataSource.getBundle(selected) : null;

  if (error) {
    return (
      <div className="relative flex min-w-0 flex-1 items-center justify-center bg-[#e9ede2] px-6 text-center">
        <div>
          <div className="text-[14px] font-semibold text-stitch-ink">Map failed to load</div>
          <p className="mt-1.5 max-w-[380px] text-[13px] leading-relaxed text-stitch-muted">{error}</p>
        </div>
      </div>
    );
  }

  if (!geo || !bundle) {
    return (
      <div className="relative flex min-w-0 flex-1 items-center justify-center bg-[#e9ede2]">
        <div className="text-[13px] text-stitch-muted">Loading Jordan map intelligence…</div>
      </div>
    );
  }

  return (
    <div className="relative min-w-0 flex-1 overflow-hidden bg-[#e9ede2]">
      <MapView
        geo={geo}
        bundle={bundle}
        selected={selected}
        onSelect={setArea}
        onOutside={handleOutside}
        layers={layers}
        theme="light"
        opportunity={opportunity}
        showOpportunity
        poiState={poiState}
        poiTypes={poiTypes}
        hiddenTypes={hiddenTypes}
        onLayerLoading={onLayerLoading}
        sellMode={state.view === "sell"}
        sellPin={state.sellPin}
        onSellPin={setSellPin}
      />

      <div className="pointer-events-none absolute inset-0 z-10">
        <MapLayers
          state={layers}
          onToggle={(k) => setLayers((s) => ({ ...s, [k]: !s[k] }))}
          poiState={poiState}
          onTogglePoi={togglePoi}
          loading={layerLoading}
          poiTypes={poiTypes}
          areaCounts={areaCounts}
          hiddenTypes={hiddenTypes}
          onToggleType={toggleType}
          selectedArea={selected}
        />
        {toast && <Toast message={toast} onClose={() => setToast(null)} />}
      </div>

      {card && (
        <Card className="absolute bottom-4 left-4 z-[2] w-[min(280px,80vw)] shadow-lg">
          <div className="text-base font-extrabold text-stitch-ink">{card.summary.name}</div>
          <div className="mt-0.5 text-2xl font-extrabold text-stitch-brand-dark">
            {card.summary.price.toLocaleString()}{" "}
            <span className="text-sm font-semibold text-stitch-muted">JD/m²</span>
          </div>
          <div className="text-[13px] text-stitch-muted">
            Safe {card.summary.minSafe.toLocaleString()} – Premium {card.summary.premium.toLocaleString()} ·{" "}
            {card.summary.confidence} confidence
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Tooltip label="Schools within 1 km">
              <span className="flex items-center gap-1.5 rounded-lg bg-stitch-soft px-2.5 py-1.5 text-sm font-bold text-stitch-ink">
                🎓 {card.summary.amenities.schools}
              </span>
            </Tooltip>
            <Tooltip label="Universities within 1 km">
              <span className="flex items-center gap-1.5 rounded-lg bg-stitch-soft px-2.5 py-1.5 text-sm font-bold text-stitch-ink">
                🏛️ {card.summary.amenities.universities}
              </span>
            </Tooltip>
            <Tooltip label="Hospitals within 1 km">
              <span className="flex items-center gap-1.5 rounded-lg bg-stitch-soft px-2.5 py-1.5 text-sm font-bold text-stitch-ink">
                🏥 {card.summary.amenities.hospitals}
              </span>
            </Tooltip>
            <Tooltip label="Bus stops within 1 km">
              <span className="flex items-center gap-1.5 rounded-lg bg-stitch-soft px-2.5 py-1.5 text-sm font-bold text-stitch-ink">
                🚌 {card.summary.amenities.busStops}
              </span>
            </Tooltip>
          </div>
        </Card>
      )}
    </div>
  );
}
