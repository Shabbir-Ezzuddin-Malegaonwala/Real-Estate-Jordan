// Legend for the builder opportunity choropleth — sits top-right of the map so
// the colour ramp is never ambiguous. Higher = better place to build.
const STOPS = [
  { c: "#b06a5f", label: "Low" },
  { c: "#e6a94b", label: "" },
  { c: "#c9a75f", label: "Mid" },
  { c: "#5fa47f", label: "" },
  { c: "#3f8f63", label: "High" },
];

export function OpportunityLegend() {
  return (
    <div className="pointer-events-auto absolute left-[456px] top-4 z-10 hidden rounded-[3px] border border-line bg-panel/95 px-3 py-2 shadow-xl backdrop-blur-sm lg:block">
      <div className="label-eyebrow mb-1.5">Opportunity to build</div>
      <div className="flex items-center gap-0.5">
        {STOPS.map((s, i) => (
          <span key={i} className="h-2.5 w-6 first:rounded-l-sm last:rounded-r-sm" style={{ background: s.c }} aria-hidden />
        ))}
      </div>
      <div className="mt-1 flex justify-between text-2xs text-ink-mute">
        <span>Lower</span>
        <span>Higher</span>
      </div>
    </div>
  );
}
