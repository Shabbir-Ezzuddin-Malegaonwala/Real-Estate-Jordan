import type { Role } from "../types";
import { ROLE_META } from "../lib/role";
import { ThemeToggle } from "./ThemeToggle";
import type { Theme } from "../lib/theme";

const ORDER: Role[] = ["builder", "agent", "buyer"];

const ICON: Record<Role, string> = { builder: "▲", agent: "◆", buyer: "●" };

// First screen: choose the lens. The choice reshapes the workspace over the same
// map + evidence base; it persists and can be changed from the header any time.
export function RoleSelector({
  onPick,
  theme,
  onToggleTheme,
}: {
  onPick: (r: Role) => void;
  theme: Theme;
  onToggleTheme: () => void;
}) {
  return (
    <div className="relative flex h-full w-full flex-col items-center justify-center overflow-y-auto bg-base px-6 py-10 text-center">
      <div className="absolute right-4 top-4">
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>

      <div className="label-eyebrow">Jordan Real Estate Intelligence</div>
      <h1 className="mt-2 max-w-[560px] text-[26px] font-semibold leading-tight tracking-tight text-ink">
        One evidence base. Three ways to decide.
      </h1>
      <p className="mt-2 max-w-[460px] text-[13px] leading-relaxed text-ink-mute">
        Every number is traceable to a source. Choose your lens — the workspace adapts to your
        question over the same map and evidence.
      </p>

      <div className="mt-8 grid w-full max-w-[860px] gap-3 sm:grid-cols-3">
        {ORDER.map((role) => {
          const m = ROLE_META[role];
          return (
            <button
              key={role}
              type="button"
              onClick={() => onPick(role)}
              className="group flex flex-col rounded-[4px] border border-line bg-surface p-5 text-left transition-colors hover:border-accent/60 hover:bg-accent/[0.05] focus-visible:border-accent"
            >
              <span className="text-[18px] text-accent" aria-hidden>{ICON[role]}</span>
              <span className="mt-2 text-[15px] font-semibold text-ink">I'm a {m.label}</span>
              <span className="mt-1.5 text-[12px] font-medium leading-snug text-ink-dim">{m.question}</span>
              <span className="mt-2 text-2xs leading-relaxed text-ink-mute">{m.blurb}</span>
              <span className="mt-auto pt-3 text-2xs font-medium text-accent opacity-0 transition-opacity group-hover:opacity-100">
                Enter workspace →
              </span>
            </button>
          );
        })}
      </div>

      <p className="mt-8 max-w-[520px] text-2xs leading-relaxed text-ink-faint">
        Decision-support, not a formal valuation. Prices are computed from calibrated portal
        listings + official indices; where a signal is missing we show an honest awaiting state,
        never a fabricated number.
      </p>
    </div>
  );
}
