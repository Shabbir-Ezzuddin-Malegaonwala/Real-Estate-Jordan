export type VerdictTag = "good" | "watch";

const TAG_CLASSES: Record<VerdictTag, string> = {
  good: "bg-[#e3f4ee] text-[#0a7a5b]",
  watch: "bg-[#fdece0] text-[#a5490a]",
};

// One amenity/factor row with a good/watch tag — Demo-G's `.li` pattern used
// in the Location-Intelligence view (education, healthcare, transport…).
export function VerdictRow({
  tag,
  title,
  subtitle,
  className = "",
}: {
  tag: VerdictTag;
  title: string;
  subtitle?: string;
  className?: string;
}) {
  return (
    <div className={`flex items-start gap-2.5 py-2.5 border-b border-stitch-soft last:border-b-0 ${className}`}>
      <span
        className={`mt-0.5 flex-none rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${TAG_CLASSES[tag]}`}
      >
        {tag === "good" ? "Good" : "Watch-out"}
      </span>
      <div className="text-sm">
        <span className="font-semibold text-stitch-ink">{title}</span>
        {subtitle && <span className="block text-xs text-stitch-muted mt-0.5">{subtitle}</span>}
      </div>
    </div>
  );
}
