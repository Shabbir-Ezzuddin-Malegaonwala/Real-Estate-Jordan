import { useMemo, useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import type { NeighborhoodMeta } from "../lib/api";
import { jd } from "../lib/format";

// Honest autocomplete over the five covered submarkets only — it does not
// pretend to geocode arbitrary Jordan addresses we have no data for. Picking a
// result selects it, flies the map, and recomputes.
export function SearchBox({
  neighborhoods,
  meta,
  onPick,
}: {
  neighborhoods: string[];
  meta: Record<string, NeighborhoodMeta>;
  onPick: (name: string) => void;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const matches = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const list = needle ? neighborhoods.filter((n) => n.toLowerCase().includes(needle)) : neighborhoods;
    return list;
  }, [q, neighborhoods]);

  const pick = (name: string) => {
    onPick(name);
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

  return (
    <div className="relative border-b border-line px-4 py-3">
      <label htmlFor="submarket-search" className="mb-1 block label-eyebrow">
        Search covered submarkets
      </label>
      <input
        id="submarket-search"
        ref={inputRef}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls="submarket-listbox"
        aria-autocomplete="list"
        placeholder="Abdoun, Dabouq, Sweifieh…"
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
      <p className="mt-1 text-2xs text-ink-faint">Data coverage: 5 Amman submarkets.</p>

      {open && matches.length > 0 && (
        <ul
          id="submarket-listbox"
          role="listbox"
          className="absolute left-4 right-4 z-30 mt-1 overflow-hidden rounded-[3px] border border-line bg-surface shadow-2xl"
        >
          {matches.map((n, i) => (
            <li
              key={n}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault();
                pick(n);
              }}
              onMouseEnter={() => setActive(i)}
              className={`flex cursor-pointer items-center justify-between px-2.5 py-1.5 text-[12px] ${
                i === active ? "bg-raised text-ink" : "text-ink-dim"
              }`}
            >
              <span>{n}</span>
              {meta[n] && (
                <span className="tnum text-2xs text-ink-mute">
                  {jd(meta[n].listing_count)} listings
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
