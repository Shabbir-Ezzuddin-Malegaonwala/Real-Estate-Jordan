import type { AreaEntry } from "../../types";
import { jd } from "../../lib/format";

export function WorkspaceHeader({
  title,
  nameAr,
  sub,
  note,
}: {
  title: string;
  nameAr?: string;
  sub?: string;
  note?: string;
}) {
  return (
    <div className="border-b border-line-soft px-4 py-3">
      <div className="flex items-center gap-2">
        <h2 className="truncate text-[18px] font-semibold text-ink">{title}</h2>
        {nameAr && <span className="text-[15px] text-ink-mute">{nameAr}</span>}
      </div>
      {sub && <div className="mt-0.5 text-2xs text-ink-mute">{sub}</div>}
      {note && <p className="mt-1.5 text-2xs italic leading-relaxed text-ink-faint">{note}</p>}
    </div>
  );
}

// Honest empty state for a context-only area — never a fabricated price. Shows
// what we DO know (portal counts) and what is pending.
export function NoStructuredData({ area }: { area: AreaEntry }) {
  return (
    <section className="px-4 pt-4" aria-label="No structured data">
      <div className="card border-dashed p-3">
        <div className="text-2xs font-medium uppercase tracking-wide text-ink-mute">
          No structured pricing yet
        </div>
        <p className="mt-1 text-2xs leading-relaxed text-ink-dim">
          {area.name} is shown for context. The decision engine has not been run here — so we show
          no launch price rather than a fabricated one. Coverage expands as enough comparable
          listings are collected.
        </p>
        {(area.listing_count || area.median_price_per_m2) && (
          <div className="mt-2 flex flex-wrap gap-2 text-2xs">
            {area.listing_count != null && (
              <span className="rounded-[2px] border border-line bg-raised px-1.5 py-[1px] tnum text-ink-mute">
                {jd(area.listing_count)} listings seen
              </span>
            )}
            {area.median_price_per_m2 != null && area.median_price_per_m2 > 0 && (
              <span className="rounded-[2px] border border-line bg-raised px-1.5 py-[1px] tnum text-ink-mute">
                ~{jd(area.median_price_per_m2)} JD/m² asking median (uncalibrated)
              </span>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
