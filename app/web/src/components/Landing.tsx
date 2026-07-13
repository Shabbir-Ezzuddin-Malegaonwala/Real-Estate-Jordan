import type { EntryMode } from "../lib/journey";
import { ThemeToggle } from "./ThemeToggle";
import type { Theme } from "../lib/theme";

// Builder-first landing. Two equally-prominent doors into the SAME 7-step
// journey: discover where to build, or evaluate land you already hold.
export function Landing({
  onEnter,
  theme,
  onToggleTheme,
}: {
  onEnter: (mode: EntryMode) => void;
  theme: Theme;
  onToggleTheme: () => void;
}) {
  return (
    <div className="relative flex h-full w-full flex-col items-center justify-center overflow-y-auto bg-base px-6 py-10 text-center">
      <div className="absolute right-4 top-4">
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>

      <div className="label-eyebrow">Jordan Real Estate Intelligence · Builder</div>
      <h1 className="mt-2 max-w-[620px] text-[27px] font-semibold leading-tight tracking-tight text-ink">
        Decide where to build, and what to launch at.
      </h1>
      <p className="mt-2 max-w-[500px] text-[13px] leading-relaxed text-ink-mute">
        One evidence base, one builder journey — opportunity, economics, pricing, monitoring.
        Every number is traceable to a source; where a signal is missing, we say so.
      </p>

      <div className="mt-8 grid w-full max-w-[720px] gap-3 sm:grid-cols-2">
        <EntryCard
          icon="◎"
          title="Explore Opportunities"
          sub="I want to discover where to build"
          blurb="Open the 290-area opportunity map — ranked, evidence-backed, honest about thin data."
          cta="Open the map"
          onClick={() => onEnter("explore")}
        />
        <EntryCard
          icon="▣"
          title="Evaluate My Land"
          sub="I already own land"
          blurb="Search your area and jump straight to economics and launch pricing."
          cta="Find my area"
          onClick={() => onEnter("evaluate")}
        />
      </div>

      <p className="mt-8 max-w-[520px] text-2xs leading-relaxed text-ink-faint">
        Decision-support, not a formal valuation. Prices are computed from calibrated portal listings
        + official indices; missing signals show an honest awaiting state, never a fabricated number.
      </p>
    </div>
  );
}

function EntryCard({
  icon,
  title,
  sub,
  blurb,
  cta,
  onClick,
}: {
  icon: string;
  title: string;
  sub: string;
  blurb: string;
  cta: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex flex-col rounded-[4px] border border-line bg-surface p-5 text-left transition-colors hover:border-accent/60 hover:bg-accent/[0.05] focus-visible:border-accent"
    >
      <span className="text-[20px] text-accent" aria-hidden>{icon}</span>
      <span className="mt-2 text-[16px] font-semibold text-ink">{title}</span>
      <span className="mt-1 text-[12px] font-medium text-ink-dim">{sub}</span>
      <span className="mt-2 text-2xs leading-relaxed text-ink-mute">{blurb}</span>
      <span className="mt-3 text-2xs font-medium text-accent opacity-70 transition-opacity group-hover:opacity-100">
        {cta} →
      </span>
    </button>
  );
}
