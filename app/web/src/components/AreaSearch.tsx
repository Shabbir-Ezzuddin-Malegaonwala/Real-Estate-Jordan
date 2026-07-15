import { useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import type { AreaEntry } from "../types";
import { jd } from "../lib/format";

// Autocomplete over the full area list. Covered areas fly the map + update the
// panel; context-only areas still fly there but surface an honest "no structured
// data yet" state (handled by the caller) rather than a fabricated price.
export function AreaSearch({
  areas,
  onPick,
  placeholder = "Search any area — e.g. Abdoun, Jabal Amman…",
}: {
  areas: AreaEntry[];
  onPick: (a: AreaEntry) => void;
  placeholder?: string;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const matches = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const list = needle
      ? areas.filter(
          (a) => a.name.toLowerCase().includes(needle) || a.name_ar?.includes(q.trim()),
        )
      : areas;
    // Covered areas first — they answer the question fully.
    return [...list].sort((a, b) => Number(b.covered) - Number(a.covered)).slice(0, 40);
  }, [q, areas]);

  const pick = (a: AreaEntry) => {
    onPick(a);
    setQ("");
    setOpen(false);
    inputRef.current?.blur();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, matches.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (matches[active]) pick(matches[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  const coveredCount = areas.filter((a) => a.covered).length;

  return (
    <div className="relative border-b border-line px-4 py-3">
      <label htmlFor="area-search" className="mb-1 block label-eyebrow">
        Search areas
      </label>
      <input
        id="area-search"
        ref={inputRef}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls="area-listbox"
        aria-autocomplete="list"
        placeholder={placeholder}
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={onKeyDown}
        className="input"
      />
      <p className="mt-1 text-2xs text-ink-faint">
        {jd(areas.length)} areas · {jd(coveredCount)} we can price
      </p>

      {open && matches.length > 0 && (
        <ul
          id="area-listbox"
          role="listbox"
          className="scroll-thin absolute left-4 right-4 z-30 mt-1 max-h-72 overflow-y-auto rounded-[3px] border border-line bg-surface shadow-2xl"
        >
          {matches.map((a, i) => (
            <li
              key={a.name}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault();
                pick(a);
              }}
              onMouseEnter={() => setActive(i)}
              className={`flex cursor-pointer items-center justify-between gap-2 px-2.5 py-1.5 text-[12px] ${
                i === active ? "bg-raised text-ink" : "text-ink-dim"
              }`}
            >
              <span className="flex items-center gap-2 truncate">
                <span
                  className={`h-1.5 w-1.5 shrink-0 rounded-full ${a.covered ? "bg-pos" : "bg-ink-faint"}`}
                  aria-hidden
                />
                <span className="truncate">{a.name}</span>
                {a.name_ar && <span className="shrink-0 text-2xs text-ink-mute">{a.name_ar}</span>}
              </span>
              <span className="shrink-0 tnum text-2xs text-ink-mute">
                {a.covered
                  ? a.median_price_per_m2
                    ? `${jd(a.median_price_per_m2)} JD/m²`
                    : `${jd(a.listing_count ?? 0)} homes`
                  : "no price yet"}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
