import type { Source } from "./types";

// Citation chips under a sourced answer. A chip with a URL is clickable (opens
// the source); a DB/SQL/computation chip shows provenance on hover.
export function Citations({ sources, onPick }: { sources: Source[]; onPick?: (s: Source) => void }) {
  if (!sources || sources.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {sources.map((s, i) => {
        const label = chipLabel(s);
        const title = s.sql ? `SQL: ${s.sql}` : s.url ?? s.name ?? "";
        if (s.url) {
          return (
            <a
              key={i}
              href={s.url}
              target="_blank"
              rel="noreferrer noopener"
              title={title}
              className="inline-flex max-w-[240px] items-center gap-1 truncate rounded-full border border-line bg-raised px-2 py-[2px] text-2xs text-cyan hover:border-cyan-dim"
            >
              <span className="opacity-70">↗</span>
              <span className="truncate">{label}</span>
              {s.date ? <span className="text-ink-faint">· {s.date}</span> : null}
            </a>
          );
        }
        return (
          <button
            key={i}
            title={title}
            onClick={() => onPick?.(s)}
            className="inline-flex max-w-[240px] items-center gap-1 truncate rounded-full border border-line bg-raised px-2 py-[2px] text-2xs text-ink-dim hover:border-cyan-dim"
          >
            <span className="opacity-70">
              {s.sql ? (
                <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <ellipse cx="12" cy="5" rx="8" ry="3" />
                  <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
                  <path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" />
                </svg>
              ) : (
                "◆"
              )}
            </span>
            <span className="truncate">{label}</span>
          </button>
        );
      })}
    </div>
  );
}

function chipLabel(s: Source): string {
  if (s.name) return s.name;
  if (s.url) {
    try {
      return new URL(s.url).hostname.replace(/^www\./, "");
    } catch {
      return s.url;
    }
  }
  if (s.sql) return "SQL query";
  return "source";
}
