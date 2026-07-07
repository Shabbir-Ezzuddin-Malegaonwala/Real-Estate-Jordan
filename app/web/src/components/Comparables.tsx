import type { Comparable } from "../types";
import { jd, money, shortDate, titleCase } from "../lib/format";

export function Comparables({ items }: { items: Comparable[] }) {
  if (items.length === 0) return null;
  return (
    <section className="px-4 pt-5" aria-label="Comparable listings">
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-[13px] font-semibold text-ink">Comparables</h3>
        <span className="text-2xs text-ink-mute">{items.length} weighted comps</span>
      </div>

      <div className="space-y-1.5">
        {items.map((c) => (
          <a
            key={c.id}
            href={c.url}
            target="_blank"
            rel="noreferrer noopener"
            className="card block p-2.5 transition-colors hover:border-cyan-dim"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="tnum font-mono text-[14px] text-ink">{jd(c.price_per_m2)}</span>
                <span className="text-2xs text-ink-mute">JD/m² adj.</span>
              </div>
              <SimilarityMeter value={c.similarity} />
            </div>

            {c.adjustments && c.adjustments.length > 0 ? (
              <ReconciliationBody c={c} />
            ) : (
              <AttributeBody c={c} />
            )}
          </a>
        ))}
      </div>
    </section>
  );
}

// Real-engine comp: show how the listing was normalised to the subject.
function ReconciliationBody({ c }: { c: Comparable }) {
  return (
    <>
      <div className="mt-1.5 flex items-center gap-1.5 text-2xs text-ink-mute">
        <span className="tnum text-ink-dim">{jd(c.original_ppm2 ?? c.price_per_m2)}</span>
        <span className="text-ink-faint">→</span>
        <span className="tnum text-ink">{jd(c.adjusted_ppm2 ?? c.price_per_m2)}</span>
        {c.gross_adjustment != null && (
          <span className="text-ink-faint">· net adj {(c.gross_adjustment * 100).toFixed(1)}%</span>
        )}
        <span className="ml-auto tnum">{jd(c.area_m2)} m²</span>
      </div>

      <div className="mt-1.5 flex flex-wrap gap-1">
        {c.adjustments!.map((a, i) => (
          <span
            key={i}
            title={a.detail ?? a.method}
            className="inline-flex items-center gap-1 rounded-[2px] border border-line bg-raised px-1.5 py-[1px] text-2xs text-ink-dim"
          >
            <span>{a.factor}</span>
            <span
              className={`tnum ${
                a.adjustment.trim().startsWith("-") || a.adjustment.trim().startsWith("−")
                  ? "text-neg"
                  : "text-pos"
              }`}
            >
              {a.adjustment}
            </span>
          </span>
        ))}
      </div>

      <div className="mt-1.5 flex items-center justify-between text-2xs text-ink-mute">
        <span className="max-w-[190px] truncate">{c.portal}</span>
        {c.listing_date && <span className="tnum">{shortDate(c.listing_date)}</span>}
      </div>
    </>
  );
}

// Illustrative mock comp: attribute snapshot.
function AttributeBody({ c }: { c: Comparable }) {
  return (
    <>
      <div className="mt-1.5 grid grid-cols-4 gap-1 text-2xs text-ink-dim">
        <Cell label="Area" value={`${jd(c.area_m2)} m²`} />
        <Cell label="Beds" value={c.bedrooms != null ? String(c.bedrooms) : "—"} />
        <Cell label="Floor" value={c.floor_level != null ? String(c.floor_level) : "—"} />
        <Cell label="Age" value={c.building_age_years != null ? `${c.building_age_years}y` : "—"} />
      </div>

      <div className="mt-1.5 flex items-center justify-between text-2xs text-ink-mute">
        <span>
          {c.portal}
          {c.view ? ` · ${titleCase(c.view)} view` : ""}
          {c.seller_type ? ` · ${titleCase(c.seller_type)}` : ""}
        </span>
        <span className="tnum">{money(c.price_jd)}</span>
      </div>
    </>
  );
}

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-ink-faint">{label}</div>
      <div className="tnum text-ink">{value}</div>
    </div>
  );
}

function SimilarityMeter({ value }: { value: number }) {
  return (
    <span className="inline-flex items-center gap-1.5" title={`Similarity ${(value * 100).toFixed(0)}%`}>
      <span className="h-1 w-12 overflow-hidden rounded-full bg-raised">
        <span className="block h-full bg-cyan-dim" style={{ width: `${value * 100}%` }} />
      </span>
      <span className="tnum text-2xs text-ink-mute">{(value * 100).toFixed(0)}%</span>
    </span>
  );
}
