import type { EvidenceObject } from "../types";
import { SourceChip } from "./SourceChip";

// Two distinct sections (MASTER-PLAN §2e): CURRENT STATE evidence feeds the
// valuation grid; FUTURE SIGNALS feed the appreciation narrative. Never mixed.
export function EvidenceSection({
  title,
  eyebrow,
  tone,
  items,
}: {
  title: string;
  eyebrow: string;
  tone: "current" | "future";
  items: EvidenceObject[];
}) {
  if (items.length === 0) return null;
  const accent = tone === "future" ? "text-cyan border-cyan/40" : "text-accent border-accent/40";

  return (
    <section className="px-4 pt-5" aria-label={title}>
      <div className="mb-2 flex items-center gap-2">
        <span className={`inline-block h-3 w-[3px] rounded-full ${tone === "future" ? "bg-cyan" : "bg-accent"}`} />
        <h3 className="text-[13px] font-semibold text-ink">{title}</h3>
        <span className="label-eyebrow ml-auto">{eyebrow}</span>
      </div>

      <div className="space-y-1.5">
        {items.map((e) => (
          <article key={e.factor} className="card p-2.5">
            <div className="flex items-start justify-between gap-2">
              <span className="text-[12px] font-medium text-ink">{e.factor}</span>
              <span className={`shrink-0 rounded-[2px] border px-1.5 py-[1px] text-2xs ${accent}`}>
                {tone === "future" ? (e.expected_year ? `~${e.expected_year}` : "signal") : e.adjustment}
              </span>
            </div>
            <p className="mt-1 text-2xs leading-relaxed text-ink-dim">{e.explanation}</p>
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-2xs text-ink-mute">
              <span className="text-ink-faint">{e.method}</span>
              {e.impact_area && (
                <>
                  <span className="text-ink-faint">·</span>
                  <span>{e.impact_area}</span>
                </>
              )}
              <span className="text-ink-faint">·</span>
              <span className="uppercase tracking-wide">{e.confidence}</span>
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1">
              {e.sources.map((s, i) => (
                <SourceChip key={i} source={s} variable={e.factor} />
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
