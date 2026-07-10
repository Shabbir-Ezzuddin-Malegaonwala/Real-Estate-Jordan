import type { AreaEntry, RecommendationResult } from "../../types";
import { shortDate } from "../../lib/format";

// Step 7 — "what changed?" A light data-vintage panel. It does NOT invent alerts:
// continuous change monitoring (price moves, new permits, infra news) is Phase 2,
// stated plainly. What we can show honestly is when the underlying data was last
// computed and what would drive future change.
export function MonitoringStep({
  area,
  result,
  generatedAt,
}: {
  area: AreaEntry | null;
  result: RecommendationResult | null;
  generatedAt: string;
}) {
  return (
    <div className="px-4 pt-4">
      <div className="mb-2 label-eyebrow">Monitoring · what changed?</div>

      <div className="card divide-y divide-line-soft">
        <Row label="Workspace data loaded" value={shortDate(generatedAt)} />
        {area && result?.as_of && <Row label={`${area.name} priced`} value={shortDate(result.as_of)} />}
        {area && <Row label="Area" value={`${area.name}${area.covered ? " · covered" : " · context"}`} />}
      </div>

      <div className="mt-3 rounded-[3px] border border-dashed border-line bg-panel p-3">
        <div className="text-2xs font-medium uppercase tracking-wide text-ink-mute">
          Change monitoring — Phase 2
        </div>
        <p className="mt-1 text-2xs leading-relaxed text-ink-dim">
          Live "what's new since last refresh" — price movements, new competitor launches, permit
          filings, and infrastructure news per watched area — is a Phase-2 capability. We don't show
          fabricated alerts. Today the numbers reflect the data vintage above; re-running the pipeline
          refreshes them.
        </p>
      </div>

      <ul className="mt-3 space-y-1.5 text-2xs leading-relaxed text-ink-faint">
        <li>• Future drivers that would move this area: metro/BRT progress, new office/mall supply, DLS transaction trend.</li>
        <li>• The pricing rule stays "raise later, never cut" — monitoring will flag when a raise is defensible.</li>
      </ul>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between px-2.5 py-2 text-[12px]">
      <span className="text-ink-dim">{label}</span>
      <span className="tnum text-ink">{value}</span>
    </div>
  );
}
