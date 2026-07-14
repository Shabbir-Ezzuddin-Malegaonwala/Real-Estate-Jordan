import { useMemo } from "react";
import { useApp } from "../lib/store";
import { useAreas, useOpportunity } from "../lib/useEngine";
import type { OpportunityData } from "../lib/contract";
import { Card, DecisionBanner } from "../ui";
import { HBarList } from "../ui/charts";

type Focus = "opportunity" | "ranking";

const TOP_N = 10;

export function OpportunityView({ focus }: { focus: Focus }) {
  const { state } = useApp();
  const areas = useAreas();
  const opportunity = useOpportunity();

  const priceByArea = useMemo(() => {
    const m = new Map<string, number>();
    for (const a of areas.data ?? []) {
      if (typeof a.median_price_per_m2 === "number") m.set(a.name, Math.round(a.median_price_per_m2));
    }
    return m;
  }, [areas.data]);

  // Trustworthy ranking excludes low-data cells (per lib/intel.ts: scarcity in a
  // thin market is noise, not opportunity) — they're never presented as a ranked
  // build opportunity, only as map context.
  const ranked = useMemo(
    () => (opportunity.data ?? []).filter((o) => !o.low_data),
    [opportunity.data],
  );

  // Assembled client-side into the OpportunityData shape (contract.ts) — the
  // hooks above already carry live-vs-fallback provenance, this just merges score + price.
  const opportunityData: OpportunityData = useMemo(() => {
    const selIdx = state.selectedArea ? ranked.findIndex((o) => o.area === state.selectedArea) : -1;
    return {
      areas: ranked.map((o) => ({ name: o.area, score: o.score, price: priceByArea.get(o.area) ?? 0 })),
      selectedScore: selIdx >= 0 ? ranked[selIdx].score : undefined,
      selectedRank: selIdx >= 0 ? selIdx + 1 : undefined,
    };
  }, [ranked, priceByArea, state.selectedArea]);

  const loading = areas.loading || opportunity.loading;
  const failed = !loading && ranked.length === 0;

  if (loading) {
    return (
      <Card>
        <div className="text-sm text-stitch-muted">Scoring build opportunity across covered areas…</div>
      </Card>
    );
  }

  if (failed) {
    return (
      <Card>
        <div className="text-sm text-stitch-muted">
          Opportunity data unavailable right now — check the backend connection and try again.
        </div>
      </Card>
    );
  }

  const top = ranked[0];
  const topPrice = priceByArea.get(top.area);
  const selectedIndex = opportunityData.selectedRank ? opportunityData.selectedRank - 1 : -1;
  const selected = selectedIndex >= 0 ? ranked[selectedIndex] : null;
  const selectedPrice = selected ? priceByArea.get(selected.area) : undefined;

  const items = opportunityData.areas.slice(0, TOP_N).map((a) => ({
    label: a.price > 0 ? `${a.name} · ${a.price.toLocaleString()} JD/m²` : a.name,
    value: a.score,
    highlighted: a.name === state.selectedArea,
  }));

  const banner =
    focus === "opportunity" ? (
      <DecisionBanner
        verdict={`Best area to build: ${top.area}`}
        subtitle={`Opportunity score ${top.score}/100${topPrice ? ` · ${topPrice.toLocaleString()} JD/m²` : ""} · ${top.covered ? "engine-covered" : "context-only"}`}
      />
    ) : (
      <DecisionBanner
        verdict={`${ranked.length} area${ranked.length === 1 ? "" : "s"} ranked by opportunity`}
        subtitle={`Top area: ${top.area} at ${top.score}/100`}
      />
    );

  return (
    <div className="flex flex-col gap-3">
      {banner}

      {selected && (
        <Card>
          <div className="text-xs font-semibold uppercase tracking-wide text-stitch-muted">Your selected area</div>
          <div className="mt-1 text-sm text-stitch-ink">
            <span className="font-semibold">{selected.area}</span> ranks{" "}
            <span className="font-semibold text-stitch-brand-dark">#{opportunityData.selectedRank}</span> of{" "}
            {ranked.length}, with a score of <span className="font-semibold">{opportunityData.selectedScore}/100</span>
            {selectedPrice ? ` at ${selectedPrice.toLocaleString()} JD/m²` : ""}.
          </div>
          {selected.reason && <div className="mt-1 text-[12px] text-stitch-muted">{selected.reason}</div>}
        </Card>
      )}

      <Card>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-stitch-muted">
          Opportunity score, top {Math.min(TOP_N, ranked.length)} areas
        </div>
        <HBarList items={items} formatValue={(v) => `${v}/100`} title="Opportunity score by area" />
      </Card>

      <div className="text-[12px] text-stitch-muted">
        The map's 🔥 Opportunity heat overlay shows this same score across all of Jordan.
      </div>
    </div>
  );
}
