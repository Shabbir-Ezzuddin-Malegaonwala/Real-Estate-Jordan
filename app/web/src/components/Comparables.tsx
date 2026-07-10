import type { Comparable } from "../types";
import { jd, money, shortDate, titleCase } from "../lib/format";

export function Comparables({ items }: { items: Comparable[] }) {
  if (items.length === 0) return null;
  return (
    <section className="px-4 pt-5" aria-label="Comparable listings">
      <div className="mb-2">
        <div className="flex items-baseline justify-between">
          <h3 className="text-[13px] font-semibold text-ink">The listings this price is based on</h3>
          <span className="text-2xs text-ink-mute">{items.length} nearby</span>
        </div>
        <p className="mt-0.5 text-2xs leading-relaxed text-ink-mute">
          Real apartments listed nearby. Each one is a piece of evidence — click any to open the
          actual listing.
        </p>
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

// Real-engine comp: what the listing is, then how it was compared to the subject.
function ReconciliationBody({ c }: { c: Comparable }) {
  const specs = listingSpecs(c);
  return (
    <>
      {/* what the listing actually consists of */}
      {specs.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-x-2.5 gap-y-0.5 text-2xs text-ink-dim">
          {specs.map((s) => (
            <span key={s.k}>
              <span className="text-ink-faint">{s.k} </span>
              <span className="tnum text-ink">{s.v}</span>
            </span>
          ))}
        </div>
      )}

      <div className="mt-1.5 flex items-center gap-1.5 text-2xs text-ink-mute">
        <span title="its own listed price">
          <span className="tnum text-ink-dim">{jd(c.original_ppm2 ?? c.price_per_m2)}</span>
        </span>
        <span className="text-ink-faint">→</span>
        <span title="adjusted to match your unit">
          <span className="tnum text-ink">{jd(c.adjusted_ppm2 ?? c.price_per_m2)}</span>
        </span>
        {c.gross_adjustment != null && (
          <span className="text-ink-faint">· adjusted {(c.gross_adjustment * 100).toFixed(0)}%</span>
        )}
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

// Build the "what this listing consists of" spec list from whatever the comp carries.
function listingSpecs(c: Comparable): { k: string; v: string }[] {
  const out: { k: string; v: string }[] = [];
  if (c.area_m2) out.push({ k: "Size", v: `${jd(c.area_m2)} m²` });
  if (c.bedrooms != null) out.push({ k: "Beds", v: String(c.bedrooms) });
  if (c.bathrooms != null) out.push({ k: "Baths", v: String(c.bathrooms) });
  if (c.floor_level != null) out.push({ k: "Floor", v: String(c.floor_level) });
  if (c.building_age_years != null) out.push({ k: "Age", v: `${c.building_age_years}y` });
  if (c.view) out.push({ k: "View", v: titleCase(c.view) });
  if (c.parking) out.push({ k: "Parking", v: titleCase(c.parking) });
  if (c.price_jd) out.push({ k: "Asking", v: money(c.price_jd) });
  return out;
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
