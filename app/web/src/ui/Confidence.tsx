// Word + 3-dot confidence indicator — Demo-G's `.word`/`.dots` pattern
// (e.g. "Strong" ●●● / "Good" ●●○ / "Fair" ●○○).
export function Confidence({
  word,
  filled,
  caption,
  className = "",
}: {
  word: string;
  filled: 1 | 2 | 3;
  caption?: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <span className="text-xl font-bold text-stitch-brand-dark">{word}</span>
      <span className="ml-2 inline-flex gap-1 align-middle" role="img" aria-label={`${filled} of 3 confidence dots`}>
        {[1, 2, 3].map((i) => (
          <i key={i} className={`h-2 w-[18px] rounded-sm ${i <= filled ? "bg-stitch-brand" : "bg-stitch-soft"}`} />
        ))}
      </span>
      {caption && <div className="mt-1.5 text-[13px] text-stitch-muted">{caption}</div>}
    </div>
  );
}
