import { useState } from "react";
import type { EvidenceSource } from "../types";
import { shortDate } from "../lib/format";

// Inline provenance chip: source name + capture date, hover/click reveals URL.
// Every evidenced fact carries one (MASTER-PLAN §6).
export function SourceChip({ source }: { source: EvidenceSource }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-flex">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onBlur={() => setOpen(false)}
        aria-label={`Source: ${source.name}, captured ${shortDate(source.capture_date)}`}
        className="group inline-flex items-center gap-1 rounded-[2px] border border-line bg-raised px-1.5 py-[1px] text-2xs text-ink-dim transition-colors hover:border-cyan-dim hover:text-ink"
      >
        <span className="h-1 w-1 rounded-full bg-cyan-dim" aria-hidden />
        <span className="max-w-[120px] truncate">{source.name}</span>
        <span className="tnum text-ink-mute">{shortDate(source.capture_date)}</span>
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute bottom-full left-0 z-30 mb-1 w-64 rounded-[3px] border border-line bg-surface p-2 text-2xs leading-relaxed shadow-xl"
        >
          <span className="block font-medium text-ink">{source.name}</span>
          <a
            href={source.url}
            target="_blank"
            rel="noreferrer noopener"
            className="block truncate text-cyan hover:underline"
          >
            {source.url}
          </a>
          <span className="mt-0.5 block text-ink-mute">
            Captured {shortDate(source.capture_date)}
          </span>
        </span>
      )}
    </span>
  );
}
