import { useState } from "react";
import type { EvidenceSource } from "../types";
import { shortDate } from "../lib/format";

// Plain-English description of what each source actually is, so a non-expert
// hovering "Bayut" knows what they're looking at.
function describe(name: string): string {
  const n = name.toLowerCase();
  if (n.includes("bayut")) return "Jordan's largest property-listing website.";
  if (n.includes("opensooq")) return "A big classifieds marketplace — lots of private sellers.";
  if (n.includes("homes")) return "An estate-agency listing portal.";
  if (n.includes("eureka")) return "A Jordanian property portal (Arabic listings).";
  if (n.includes("abujudom") || n.includes("abu judom")) return "A premium-Amman estate agency.";
  if (n.includes("4321")) return "A multi-city listing portal (has map coordinates).";
  if (n.includes("dos") || n.includes("statistics")) return "Official government construction-cost figures.";
  if (n.includes("dls") || n.includes("lands")) return "Official land-registry / price-index data.";
  if (n.includes("satellite") || n.includes("gis") || n.includes("viirs") || n.includes("dem"))
    return "Satellite & map data (terrain, night-lights, population, amenities).";
  if (n.includes("listings")) return "The pool of collected market listings.";
  if (n.includes("pdf") || n.includes("methodology")) return "The client's pricing-methodology document.";
  return "Source of this figure.";
}

// Inline provenance chip: source name + capture date, hover/click reveals what it
// is + the link. Every evidenced fact carries one (MASTER-PLAN §6).
// `variable` (optional): the factor/number this reference actually fed into the
// model — shown on hover so the user can see WHICH variable came from this source.
export function SourceChip({ source, variable }: { source: EvidenceSource; variable?: string }) {
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
          <span className="mt-0.5 block text-ink-dim">{describe(source.name)}</span>
          {variable && (
            <span className="mt-1 block rounded-[2px] border border-cyan/30 bg-cyan/5 px-1.5 py-1 text-ink">
              <span className="text-ink-mute">Variable used from this reference: </span>
              <span className="font-medium text-cyan">{variable}</span>
            </span>
          )}
          <a
            href={source.url}
            target="_blank"
            rel="noreferrer noopener"
            className="mt-1 block truncate text-cyan hover:underline"
          >
            {source.url}
          </a>
          <span className="mt-0.5 block text-ink-mute">
            Collected {shortDate(source.capture_date)}
          </span>
        </span>
      )}
    </span>
  );
}
