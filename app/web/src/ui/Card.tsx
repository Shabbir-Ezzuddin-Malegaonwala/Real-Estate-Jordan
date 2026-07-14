import type { ReactNode } from "react";

// Base surface for the Stitch design system — white card, hairline border,
// 12px radius (Demo-G reference). Every panel/tile composes this.
export function Card({
  children,
  className = "",
  padded = true,
}: {
  children: ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <div
      className={`bg-stitch-card border border-stitch-line rounded-xl ${padded ? "p-4" : ""} ${className}`}
    >
      {children}
    </div>
  );
}
