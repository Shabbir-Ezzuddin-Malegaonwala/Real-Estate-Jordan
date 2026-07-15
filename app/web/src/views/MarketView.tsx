import { useEffect, useState, type ReactNode } from "react";
import type { AreaBundle } from "../lib/contract";
import { fetchMarketIntelligence, fetchMarketBrief, type MarketIntel, type MarketBrief } from "../lib/intel";
import { Card } from "../ui";
import { HBarList, Sparkline } from "../ui/charts";

type Focus = "competitors" | "news";

const CAT_STYLE: Record<string, string> = {
  economic: "bg-[#e7f1fb] text-[#1d4ed8]",
  infrastructure: "bg-[#e3f4ee] text-[#0a7a5b]",
  government: "bg-[#efe9fb] text-[#6d28d9]",
  regulatory: "bg-[#fdf0dd] text-[#b06a1a]",
  launch: "bg-[#e0f2f1] text-[#0f766e]",
  news: "bg-stitch-soft text-stitch-muted",
};

function fmtDate(d: string | null): string {
  if (!d) return "";
  const dt = new Date(d);
  return isNaN(dt.getTime()) ? d : dt.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function MarketView({ bundle, focus }: { bundle: AreaBundle; focus: Focus }) {
  const { market } = bundle;
  const [intel, setIntel] = useState<MarketIntel | null>(null);
  const [brief, setBrief] = useState<MarketBrief | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      const [i, b] = await Promise.all([fetchMarketIntelligence(30), fetchMarketBrief()]);
      if (!alive) return;
      setIntel(i);
      setBrief(b);
      setLoading(false);
    })();
    return () => { alive = false; };
  }, []);

  const briefCard: ReactNode = (
    <Card key="brief">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-stitch-muted">Weekly market brief</span>
        {brief && <span className="text-[10px] font-bold text-stitch-brand">LIVE</span>}
      </div>
      {brief ? (
        <p className="text-[13px] leading-relaxed text-stitch-ink">{brief.brief}</p>
      ) : (
        <p className="text-[13px] text-stitch-muted">{loading ? "Loading the market brief…" : "Brief unavailable."}</p>
      )}
    </Card>
  );

  const newsCard: ReactNode = (
    <Card key="news">
      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-stitch-muted">
        Market news {intel && <span className="text-stitch-muted">· {intel.news.length}</span>}
      </div>
      {intel && intel.news.length > 0 ? (
        <div className="flex max-h-[42vh] flex-col overflow-y-auto pr-1">
          {intel.news.map((n, i) => (
            <div key={i} className="border-b border-stitch-soft py-2.5 last:border-b-0">
              <div className="mb-0.5 flex items-center gap-2">
                <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${CAT_STYLE[n.category] ?? CAT_STYLE.news}`}>{n.category}</span>
                {n.event_date && <span className="text-[11px] text-stitch-muted">{fmtDate(n.event_date)}</span>}
                {n.area_en && <span className="text-[11px] text-stitch-muted">· {n.area_en}</span>}
              </div>
              <div className="text-[13px] font-semibold text-stitch-ink">{n.title_en}</div>
              {n.summary_en && <div className="mt-0.5 text-[12.5px] leading-snug text-stitch-muted">{n.summary_en}</div>}
              {n.source_name && (
                <div className="mt-0.5 text-[10.5px] text-stitch-muted">
                  {n.source_url ? <a href={n.source_url} target="_blank" rel="noreferrer" className="text-stitch-brand hover:underline">{n.source_name}</a> : n.source_name}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-[13px] text-stitch-muted">{loading ? "Loading news…" : "No market news in this window."}</p>
      )}
    </Card>
  );

  const competitorsCard: ReactNode = (
    <Card key="competitors">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-stitch-muted">
        Competitor projects {intel && <span className="text-stitch-muted">· {intel.competitors.length}</span>}
      </div>
      {intel && intel.competitors.length > 0 ? (
        <div className="flex max-h-[42vh] flex-col overflow-y-auto pr-1">
          {intel.competitors.map((c, i) => (
            <div key={i} className="flex items-start justify-between gap-2 border-b border-stitch-soft py-2 text-sm last:border-b-0">
              <div className="min-w-0">
                <div className="truncate font-semibold text-stitch-ink">{c.project}</div>
                <div className="truncate text-[12px] text-stitch-muted">
                  {[c.developer, c.area, c.status].filter(Boolean).join(" · ")}
                </div>
                {c.payment_plan && <div className="truncate text-[11px] text-stitch-muted">Plan: {c.payment_plan}</div>}
              </div>
              {c.price_jd_per_m2 ? (
                <div className="flex-none text-right">
                  <div className="text-sm font-bold text-stitch-brand-dark">{Math.round(c.price_jd_per_m2).toLocaleString()}</div>
                  <div className="text-[10px] text-stitch-muted">JD/m²</div>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        // Fall back to the per-area monitoring peers if the projects table is empty.
        <HBarList items={market.competitors.map((c) => ({ label: c.name, value: c.price }))} title="Competitor launch prices" caption="JD/m² launch price" />
      )}
    </Card>
  );

  const trendCard: ReactNode = (
    <Card key="trend">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-stitch-muted">Area price trend</div>
      <Sparkline data={market.trend} width={260} height={64} title="Market price trend" />
    </Card>
  );

  const ordered = focus === "news"
    ? [briefCard, newsCard, competitorsCard, trendCard]
    : [competitorsCard, briefCard, newsCard, trendCard];

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-xl bg-gradient-to-br from-stitch-brand-dark to-stitch-brand px-4 py-3.5 text-white">
        <div className="text-base font-bold leading-snug">{brief?.headline ?? market.status}</div>
        {intel && (
          <div className="mt-0.5 text-[13px] text-white/90">
            Last {intel.totals.window_days} days: {intel.totals.new_listings} new properties advertised · {intel.totals.price_increases + intel.totals.price_drops} price changes · {intel.competitors.length} competitor projects tracked
          </div>
        )}
      </div>
      {ordered}
    </div>
  );
}
