import type { ReactNode } from "react";

// Hover-reveal label, no JS positioning library — pure CSS group-hover.
// Used for the amenity chips ("Schools within 1 km") and chart legend hints.
export function Tooltip({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span className="group relative inline-flex" tabIndex={0}>
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-0 z-20 mb-1.5 whitespace-nowrap rounded-md bg-stitch-ink px-2 py-1 text-[11px] font-normal text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
      >
        {label}
      </span>
    </span>
  );
}
