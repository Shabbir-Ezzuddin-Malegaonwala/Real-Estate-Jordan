import type { ReactNode } from "react";
import { useApp } from "../lib/store";
import type { AreaBundle } from "../lib/contract";
import { Card, VerdictRow } from "../ui";

type Focus = "nearby" | "infra";

export function LocationView({ bundle, focus }: { bundle: AreaBundle; focus: Focus }) {
  const { setView } = useApp();
  const { location } = bundle;

  const verdictsCard: ReactNode = (
    <Card key="verdicts">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-stitch-muted">Amenities nearby</div>
      {location.verdicts.map((v) => (
        <VerdictRow key={v.title} tag={v.tag} title={v.title} subtitle={v.subtitle} />
      ))}
      <button
        type="button"
        onClick={() => setView("chatnew")}
        className="mt-3 text-left text-[12.5px] font-semibold text-stitch-brand hover:underline"
      >
        🤖 Ask what's missing nearby
      </button>
    </Card>
  );

  const infraCard: ReactNode = (
    <Card key="infra">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-stitch-muted">Infrastructure</div>
      <div className="flex flex-col">
        {location.infrastructure.map((f) => (
          <div key={`${f.when}-${f.text}`} className="flex gap-2.5 border-b border-stitch-soft py-2.5 text-sm last:border-b-0">
            <span className="w-11 flex-none text-[11px] text-stitch-muted">{f.when}</span>
            <span className="text-stitch-ink">{f.text}</span>
          </div>
        ))}
      </div>
    </Card>
  );

  const ordered = focus === "infra" ? [infraCard, verdictsCard] : [verdictsCard, infraCard];

  return <div className="flex flex-col gap-3">{ordered}</div>;
}
