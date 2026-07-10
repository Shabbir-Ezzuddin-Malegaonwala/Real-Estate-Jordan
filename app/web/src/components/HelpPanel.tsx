import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

// In-app "How to use / About" drawer. Honest and skimmable — mirrors what the
// panels actually show, and what is still awaiting research data.
export function HelpPanel({ onClose }: { onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="absolute inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="Close help"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-black/45"
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="help-title"
        className="scroll-thin relative flex h-full w-[480px] max-w-[94vw] flex-col overflow-y-auto border-l border-line bg-surface shadow-2xl"
      >
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-surface/95 px-5 py-4 backdrop-blur-sm">
          <div>
            <div className="label-eyebrow">About this tool</div>
            <h2 id="help-title" className="text-[16px] font-semibold tracking-tight text-ink">
              How to use this tool
            </h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close help"
            className="grid h-7 w-7 shrink-0 place-items-center rounded-[3px] border border-line bg-panel text-ink-mute transition-colors hover:text-ink"
          >
            ✕
          </button>
        </header>

        <div className="px-5 py-4">
          <p className="text-[13px] leading-relaxed text-ink-dim">
            An evidence-backed launch-price decision-support tool for five premium Amman submarkets —{" "}
            <span className="text-ink">Abdoun, Dabouq, Sweifieh, Khalda, and Shmeisani</span>. It turns
            real listings and market indicators into a defensible launch price, and shows the reasoning
            behind every number.
          </p>

          <Section title="How to use it">
            <ol className="space-y-2 text-[12px] leading-relaxed text-ink-dim">
              <Step n={1}>
                <b className="text-ink">Pick a submarket</b> — use the dropdown, the search box, or click
                its area on the map.
              </Step>
              <Step n={2}>
                <b className="text-ink">Describe your unit</b> — enter size, floor, finish, and age in the
                subject-property form.
              </Step>
              <Step n={3}>
                <b className="text-ink">Read the result</b> — the Launch Price Band and the evidenced
                reasons behind it update as you type.
              </Step>
            </ol>
          </Section>

          <Section title="What each panel means">
            <dl className="space-y-2.5">
              <Term name="Launch Price Band">
                Minimum-Safe, Recommended, and Premium in JD per m², with a confidence level. Never a
                single naked number — a defensible range.
              </Term>
              <Term name="Adjustment Waterfall">
                A reconciled comparable base, then each evidenced +/− adjustment (size, floor, finish,
                view…). Every row carries its method and a source chip.
              </Term>
              <Term name="Comparables">
                The real listings behind the price, each normalised to your unit — original → adjusted
                JD/m², with a similarity score.
              </Term>
              <Term name="Risk Factors">
                An honest read of the gaps and cautions behind the estimate — thin samples, wide
                dispersion, missing attributes.
              </Term>
              <Term name="Future Signals">
                The appreciation narrative (infrastructure, policy, development). Positioning only — never
                applied to today's band. Currently awaiting research data.
              </Term>
            </dl>
          </Section>

          <Section title="Included vs. pending">
            <ul className="space-y-1.5 text-[12px] leading-relaxed text-ink-dim">
              <Bullet tone="pending">
                <b className="text-ink">View and parking</b> are not available per listing — the portals
                don't publish them reliably.
              </Bullet>
              <Bullet tone="pending">
                <b className="text-ink">Competitor projects, construction costs, future infrastructure,
                and neighbourhood profiles</b> are awaiting research and show an "awaiting data" state.
              </Bullet>
              <Bullet tone="included">
                <b className="text-ink">Live listings, the price band, the adjustment waterfall, and
                comparables</b> are fully wired to real data today.
              </Bullet>
            </ul>
          </Section>

          <Section title="Data sources">
            <ul className="space-y-1.5 text-[12px] leading-relaxed text-ink-dim">
              <Src name="Bayut · OpenSooq">asking-price listings for the five submarkets</Src>
              <Src name="OpenStreetMap">basemap, POIs, roads, and land use</Src>
              <Src name="Central Bank of Jordan">real-estate price index</Src>
              <Src name="Dept. of Statistics">building-permit activity</Src>
            </ul>
            <p className="mt-3 rounded-[3px] border border-line bg-panel px-3 py-2 text-2xs italic leading-relaxed text-ink-mute">
              Asking prices are calibrated to the transaction level. This is decision-support, not a
              formal valuation.
            </p>
          </Section>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-5 border-t border-line-soft pt-4">
      <h3 className="mb-2 label-eyebrow">{title}</h3>
      {children}
    </section>
  );
}

function Step({ n, children }: { n: number; children: ReactNode }) {
  return (
    <li className="flex gap-2.5">
      <span className="mt-[1px] grid h-4 w-4 shrink-0 place-items-center rounded-full border border-accent/50 bg-accent/10 text-[10px] font-semibold text-accent">
        {n}
      </span>
      <span>{children}</span>
    </li>
  );
}

function Term({ name, children }: { name: string; children: ReactNode }) {
  return (
    <div className="rounded-[3px] border border-line bg-panel p-2.5">
      <dt className="text-[12px] font-semibold text-ink">{name}</dt>
      <dd className="mt-0.5 text-2xs leading-relaxed text-ink-dim">{children}</dd>
    </div>
  );
}

function Bullet({ tone, children }: { tone: "included" | "pending"; children: ReactNode }) {
  return (
    <li className="flex gap-2">
      <span
        className={`mt-[5px] h-2 w-2 shrink-0 rounded-full ${tone === "included" ? "bg-pos" : "bg-warn"}`}
        aria-hidden
      />
      <span>{children}</span>
    </li>
  );
}

function Src({ name, children }: { name: string; children: ReactNode }) {
  return (
    <li className="flex flex-wrap items-baseline gap-x-1.5">
      <span className="text-[12px] font-medium text-ink">{name}</span>
      <span className="text-2xs text-ink-mute">— {children}</span>
    </li>
  );
}
