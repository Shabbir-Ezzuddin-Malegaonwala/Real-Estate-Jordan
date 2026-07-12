import { useEffect, useState } from "react";
import type { AreaEntry, Feasibility, FeasibilityStatus } from "../../types";
import { fetchFeasibility } from "../../lib/intel";
import { SourceChip } from "../SourceChip";

const STATUS: Record<FeasibilityStatus, { label: string; cls: string; dot: string }> = {
  ok: { label: "OK", cls: "text-pos", dot: "bg-pos" },
  partial: { label: "Partial data", cls: "text-warn", dot: "bg-warn" },
  caution: { label: "Caution", cls: "text-warn", dot: "bg-warn" },
  risk: { label: "Risk", cls: "text-neg", dot: "bg-neg" },
  unknown: { label: "Awaiting data", cls: "text-ink-faint", dot: "bg-ink-faint" },
};

// Step 2 — "can I build here?" Broad feasibility dimensions from GET /feasibility.
// Everything we don't yet hold is shown honestly as "awaiting data", never faked.
export function FeasibilityStep({ area }: { area: AreaEntry | null }) {
  const [feas, setFeas] = useState<Feasibility | null>(null);

  useEffect(() => {
    if (!area) {
      setFeas(null);
      return;
    }
    let alive = true;
    fetchFeasibility(area.name).then((f) => {
      if (alive) setFeas(f);
    });
    return () => {
      alive = false;
    };
  }, [area]);

  if (!area) return <Prompt />;

  const allUnknown = feas?.dimensions.every((d) => d.status === "unknown");

  return (
    <div className="px-4 pt-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="label-eyebrow">Feasibility · can I build here?</span>
        {feas && <span className="text-2xs text-ink-faint">{feas.source === "live" ? "engine" : "pending backend"}</span>}
      </div>

      {allUnknown && (
        <div className="card mb-2 border-dashed p-3">
          <p className="text-2xs leading-relaxed text-ink-dim">
            Structured feasibility (GAM zoning & height, flood/valley, geotechnical, access) is not
            yet collected for {area.name}. These dimensions are scaffolded honestly — no fabricated
            green lights — and populate as the feasibility pipeline lands.
          </p>
        </div>
      )}

      <div className="card divide-y divide-line-soft">
        {feas?.dimensions.map((d) => {
          const s = STATUS[d.status];
          return (
            <div key={d.key} className="p-2.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[12px] text-ink">{d.label}</span>
                <span className={`flex items-center gap-1.5 text-2xs font-medium ${s.cls}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} aria-hidden />
                  {d.value ?? s.label}
                </span>
              </div>
              <p className="mt-1 text-2xs leading-relaxed text-ink-faint">{d.reason}</p>
              {d.sources && d.sources.length > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {d.sources.map((src, i) => (
                    <SourceChip key={i} source={src} variable={d.label} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Prompt() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <div className="text-[13px] font-medium text-ink-dim">Pick an area first</div>
      <p className="mt-1 max-w-[260px] text-2xs leading-relaxed text-ink-mute">
        Search or click the map to check whether a site can be built — zoning, slope, flood, access.
      </p>
    </div>
  );
}
