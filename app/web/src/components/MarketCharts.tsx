import { useMemo, useState } from "react";
import type { RecommendationBundle } from "../types";
import { POI_COLORS } from "../lib/mapStyle";
import { jd, titleCase } from "../lib/format";
import { BarRow } from "./BarRow";

// Bottom market-context dock: recommended price/m² by neighbourhood, and POI
// mix by category. Collapsible to keep the map dominant.
export function MarketCharts({
  bundle,
  poiCounts,
  selected,
  onSelect,
}: {
  bundle: RecommendationBundle;
  poiCounts: Record<string, number>;
  selected: string | null;
  onSelect: (nb: string) => void;
}) {
  const [open, setOpen] = useState(true);

  const priceRows = useMemo(
    () =>
      Object.values(bundle.results)
        .map((r) => ({ nb: r.neighborhood, value: r.recommended_jd_m2 }))
        .sort((a, b) => b.value - a.value),
    [bundle],
  );
  const priceMax = Math.max(...priceRows.map((r) => r.value), 1);

  const poiRows = useMemo(
    () =>
      Object.entries(poiCounts)
        .map(([cat, n]) => ({ cat, n }))
        .sort((a, b) => b.n - a.n),
    [poiCounts],
  );
  const poiMax = Math.max(...poiRows.map((r) => r.n), 1);
  const poiTotal = poiRows.reduce((a, r) => a + r.n, 0);

  return (
    <div className="pointer-events-auto absolute bottom-6 left-1/2 z-10 w-[560px] max-w-[calc(100vw-460px)] -translate-x-1/2">
      <div className="card shadow-2xl">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex w-full items-center justify-between px-3 py-2"
        >
          <span className="label-eyebrow">Market Overview</span>
          <span className="text-2xs text-ink-mute">{open ? "Hide ▾" : "Show ▸"}</span>
        </button>

        {open && (
          <div className="grid grid-cols-2 gap-4 border-t border-line px-3 py-3">
            <div>
              <div className="mb-1.5 text-2xs text-ink-mute">
                Recommended price · <span className="text-ink-dim">JD/m²</span>
              </div>
              {priceRows.map((r) => (
                <button
                  key={r.nb}
                  type="button"
                  onClick={() => onSelect(r.nb)}
                  className="block w-full text-left"
                >
                  <BarRow
                    label={r.nb}
                    value={r.value}
                    display={jd(r.value)}
                    max={priceMax}
                    color="#e6a94b"
                    highlight={selected === r.nb}
                  />
                </button>
              ))}
            </div>

            <div>
              <div className="mb-1.5 text-2xs text-ink-mute">
                POIs by category · <span className="text-ink-dim tnum">{jd(poiTotal)} total</span>
              </div>
              {poiRows.map((r) => (
                <BarRow
                  key={r.cat}
                  label={titleCase(r.cat)}
                  value={r.n}
                  display={jd(r.n)}
                  max={poiMax}
                  color={POI_COLORS[r.cat] ?? "#5fb2c9"}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
