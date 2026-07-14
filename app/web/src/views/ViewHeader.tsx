import type { ReactNode } from "react";

// Shared breadcrumb + title block every view leads with (Demo-G's
// `.crumb`/`.title`/`.titlesub`). `crumbExtra` lets chatopen append a
// "· history" link without a separate header component.
export function ViewHeader({
  category,
  title,
  subtitle,
  crumbExtra,
}: {
  category: string;
  title?: string;
  subtitle?: string;
  crumbExtra?: ReactNode;
}) {
  return (
    <div>
      <div className="text-xs font-semibold text-stitch-muted">
        {category}
        {crumbExtra}
      </div>
      {title && <div className="mt-0.5 text-lg font-bold text-stitch-ink">{title}</div>}
      {subtitle && <div className="mt-0.5 text-[13px] text-stitch-muted">{subtitle}</div>}
    </div>
  );
}
