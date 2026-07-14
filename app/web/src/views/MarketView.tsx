import type { ReactNode } from "react";
import type { AreaBundle } from "../lib/contract";
import { Card } from "../ui";
import { HBarList, Sparkline } from "../ui/charts";

type Focus = "competitors" | "news";

function LiveBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-bold text-stitch-green">
      <span className="h-2 w-2 rounded-full bg-stitch-green animate-pulse" aria-hidden />
      LIVE
    </span>
  );
}

export function MarketView({ bundle, focus }: { bundle: AreaBundle; focus: Focus }) {
  const { market } = bundle;

  const newsCard: ReactNode = (
    <Card key="news">
      <div className="flex items-center justify-between">
        <div className="text-xs font-semibold uppercase tracking-wide text-stitch-muted">Market news</div>
        <LiveBadge />
      </div>
      <div className="mt-1 flex flex-col">
        {market.news.map((n) => (
          <div key={`${n.date}-${n.text}`} className="flex gap-2.5 border-b border-stitch-soft py-2.5 text-sm last:border-b-0">
            <span className="w-11 flex-none text-[11px] text-stitch-muted">{n.date}</span>
            <div>
              <span className="text-stitch-ink">{n.text}</span>
              {n.action && <span className="mt-0.5 block font-semibold text-stitch-brand-dark">{n.action}</span>}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );

  const competitorsCard: ReactNode = (
    <Card key="competitors">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-stitch-muted">Competitors</div>
      <HBarList
        items={market.competitors.map((c) => ({ label: c.name, value: c.price }))}
        title="Competitor launch prices"
        caption="JD/m² launch price"
      />
    </Card>
  );

  const trendCard: ReactNode = (
    <Card key="trend">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-stitch-muted">Price trend</div>
      <Sparkline data={market.trend} width={260} height={60} title="Market price trend" />
    </Card>
  );

  const ordered = focus === "news" ? [newsCard, competitorsCard, trendCard] : [competitorsCard, newsCard, trendCard];

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-xl bg-gradient-to-br from-stitch-brand-dark to-stitch-brand px-4 py-3.5 text-white">
        <div className="text-base font-bold leading-snug">{market.status}</div>
        <div className="mt-0.5 text-[13px] text-white/90">{market.changesThisWeek} changes this week</div>
      </div>
      {ordered}
    </div>
  );
}
