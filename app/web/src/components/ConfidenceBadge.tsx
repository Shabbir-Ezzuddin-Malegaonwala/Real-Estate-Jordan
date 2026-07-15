import type { Confidence, ConfidenceLevel } from "../types";
import { jd } from "../lib/format";

const TONE: Record<ConfidenceLevel, string> = {
  High: "text-pos border-pos/40 bg-pos/10",
  Medium: "text-warn border-warn/40 bg-warn/10",
  Low: "text-neg border-neg/40 bg-neg/10",
};

export function ConfidenceBadge({ confidence, compact = false }: { confidence: Confidence; compact?: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-[2px] border px-2 py-[2px] text-2xs font-medium ${TONE[confidence.level]}`}
      title={confidence.drivers.join(" · ")}
    >
      <span className="uppercase tracking-wide">
        {confidence.level === "High" ? "Very sure" : confidence.level === "Low" ? "Not sure" : "Fairly sure"}
      </span>
      <span className="tnum opacity-80">{confidence.score}</span>
      {!compact && (
        <span className="tnum text-ink-dim">
          · {jd(confidence.range_low)}–{jd(confidence.range_high)}
        </span>
      )}
    </span>
  );
}
