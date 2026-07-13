import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import type { AreaEntry, AreaMonitoring, RecommendationResult } from "../../types";
import { fetchAreaMonitoring } from "../../lib/intel";
import { jd, shortDate } from "../../lib/format";

// Monitoring = a small "market explorer" dashboard. EVERY number is computed by the
// backend (/area-monitoring) and only rendered here — no browser-side math. Each graph
// is deliberately simple with a one-line, plain-English caption. Expand ⛶ blows the
// dashboard up to full screen so the side panel never feels cramped.
export function MonitoringStep({
  area,
  result,
  generatedAt,
}: {
  area: AreaEntry | null;
  result: RecommendationResult | null;
  generatedAt: string;
}) {
  const [data, setData] = useState<AreaMonitoring | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!area) {
      setData(null);
      return;
    }
    let alive = true;
    setLoading(true);
    fetchAreaMonitoring(area.name)
      .then((d) => alive && setData(d))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [area]);

  if (!area) return <Prompt />;

  return (
    <div className="px-4 pt-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="label-eyebrow">Monitoring · the market at a glance</span>
        {data && (
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="rounded-[3px] border border-cyan/50 bg-cyan/10 px-2 py-[3px] text-2xs font-medium text-cyan transition-colors hover:bg-cyan/20"
          >
            ⛶ Expand
          </button>
        )}
      </div>

      {loading && !data ? (
        <Awaiting note={`Loading market graphs for ${area.name}…`} />
      ) : data ? (
        <Dashboard data={data} big={false} />
      ) : (
        <Awaiting note="Market graphs need the live engine — start/restart the backend to see them." />
      )}

      <p className="mt-3 text-2xs text-ink-faint">
        Data loaded {shortDate(generatedAt)}
        {result?.as_of ? ` · ${area.name} priced ${shortDate(result.as_of)}` : ""}. All graphs are
        computed by the engine from real listings — nothing here is estimated in the browser.
      </p>

      {expanded &&
        data &&
        // Portal to <body> so the overlay escapes the side panel's backdrop-filter
        // containing block and truly covers the whole screen — map included.
        createPortal(
          <div className="fixed inset-0 z-[100] overflow-auto bg-base p-6">
            <div className="mx-auto max-w-[1100px]">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <div className="label-eyebrow">Monitoring · {area.name}</div>
                  <h2 className="text-[18px] font-semibold text-ink">The market at a glance</h2>
                </div>
                <button
                  type="button"
                  onClick={() => setExpanded(false)}
                  className="rounded-[3px] border border-line bg-panel px-3 py-1.5 text-2xs font-medium text-ink-dim transition-colors hover:text-ink"
                >
                  ✕ Close
                </button>
              </div>
              <Dashboard data={data} big />
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
}

// --- the dashboard grid -----------------------------------------------------
function Dashboard({ data, big }: { data: AreaMonitoring; big: boolean }) {
  const grid = big ? "grid gap-4 sm:grid-cols-2" : "space-y-3";
  const h = big ? 40 : 28; // chart height in "tailwind h-" units (×0.25rem)
  return (
    <div className={grid}>
      <GraphCard title="Price spread" caption={`Where most home prices land in ${data.neighborhood} (JD/m²)`}>
        {data.price_histogram.length > 0 ? (
          <Histogram bins={data.price_histogram} heightUnits={h} />
        ) : (
          <Empty note="Too few sales to show a spread." />
        )}
      </GraphCard>

      <GraphCard title="Price by year" caption="Median price each year — only years with real dated sales">
        {data.yearly_median.length > 0 ? (
          <YearBars years={data.yearly_median} heightUnits={h} />
        ) : (
          <Empty note="No dated sales to chart a yearly trend yet." />
        )}
      </GraphCard>

      <GraphCard title="Rank vs Jordan" caption="How pricey this area is compared with everywhere else">
        {data.price_rank ? (
          <RankStrip rank={data.price_rank} />
        ) : (
          <Empty note="Not enough priced areas to rank against." />
        )}
      </GraphCard>

      <GraphCard title="Listings by source" caption="Which portals this area's data comes from">
        {data.by_portal.length > 0 ? (
          <PortalBars portals={data.by_portal} />
        ) : (
          <Empty note="No source breakdown available." />
        )}
      </GraphCard>

      {/* Cross-region analysis — only in the roomy fullscreen view. */}
      {big && data.peers.length > 1 && (
        <>
          <GraphCard title="Priciest areas" caption="Where this area's price sits among areas with real data (▮ = here)">
            <Leaderboard peers={data.peers} metric="median_price" fmt={(v) => `${jd(v)}`} />
          </GraphCard>
          <GraphCard title="Best opportunity" caption="Highest 'where to build' scores right now (▮ = here)">
            <Leaderboard peers={data.peers.filter((p) => p.opportunity != null)} metric="opportunity" fmt={(v) => `${v}`} />
          </GraphCard>
          <GraphCard title="Opportunity vs price" caption="Each dot is an area — top-left = cheaper + higher opportunity (the best bets)" wide>
            <PriceOppScatter peers={data.peers} />
          </GraphCard>
        </>
      )}
    </div>
  );
}

type Peer = AreaMonitoring["peers"][number];

function GraphCard({ title, caption, wide, children }: { title: string; caption: string; wide?: boolean; children: React.ReactNode }) {
  return (
    <section className={`card p-3 ${wide ? "sm:col-span-2" : ""}`}>
      <h3 className="text-[13px] font-semibold text-ink">{title}</h3>
      <p className="mb-2 mt-0.5 text-2xs leading-relaxed text-ink-mute">{caption}</p>
      {children}
    </section>
  );
}

// Top-10 horizontal-bar leaderboard across regions, with the selected area always shown + highlighted.
function Leaderboard({ peers, metric, fmt }: { peers: Peer[]; metric: "median_price" | "opportunity"; fmt: (v: number) => string }) {
  const val = (p: Peer) => Number(p[metric]) || 0;
  const rows = [...peers].sort((a, b) => val(b) - val(a)).slice(0, 10);
  const sel = peers.find((p) => p.is_selected);
  if (sel && !rows.some((r) => r.is_selected)) rows.push(sel);
  const max = Math.max(...rows.map(val), 1);
  return (
    <div className="space-y-1.5">
      {rows.map((p) => (
        <div key={p.name} className="flex items-center gap-2 text-2xs">
          <span className={`w-28 shrink-0 truncate ${p.is_selected ? "font-medium text-cyan" : "text-ink-dim"}`} title={p.name}>{p.name}</span>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-raised">
            <div className={`h-full rounded-full ${p.is_selected ? "bg-cyan" : "bg-accent/60"}`} style={{ width: `${(val(p) / max) * 100}%` }} />
          </div>
          <span className="tnum w-12 shrink-0 text-right text-ink-mute">{fmt(val(p))}</span>
        </div>
      ))}
    </div>
  );
}

// Each area a dot: x = price (cheaper→pricier), y = opportunity (higher is up). Selected highlighted.
function PriceOppScatter({ peers }: { peers: Peer[] }) {
  const pts = peers.filter((p) => p.opportunity != null);
  if (pts.length < 2) return <Empty note="Not enough areas to compare." />;
  const prices = pts.map((p) => p.median_price);
  const minP = Math.min(...prices);
  const maxP = Math.max(...prices);
  const x = (p: Peer) => (maxP > minP ? ((p.median_price - minP) / (maxP - minP)) * 100 : 50);
  return (
    <div className="relative h-56 overflow-hidden rounded-[3px] border border-line bg-raised/30">
      <span className="absolute left-1.5 top-1 text-[9px] text-ink-faint">↑ higher opportunity</span>
      <span className="absolute bottom-1 right-1.5 text-[9px] text-ink-faint">pricier →</span>
      <span className="absolute bottom-1 left-1.5 text-[9px] text-cyan/80">best bets ◤</span>
      {pts.map((p) => (
        <div
          key={p.name}
          title={`${p.name}: ${jd(p.median_price)} JD/m², opportunity ${p.opportunity}`}
          className={`absolute -translate-x-1/2 -translate-y-1/2 rounded-full ${
            p.is_selected ? "z-10 h-3 w-3 bg-cyan ring-2 ring-cyan/40" : "h-1.5 w-1.5 bg-ink-mute/50 hover:bg-ink-mute"
          }`}
          style={{ left: `${x(p)}%`, top: `${100 - (p.opportunity ?? 0)}%` }}
        />
      ))}
    </div>
  );
}

// --- charts (pure render of backend numbers) --------------------------------
function Histogram({ bins, heightUnits }: { bins: AreaMonitoring["price_histogram"]; heightUnits: number }) {
  const max = Math.max(...bins.map((b) => b.count), 1);
  return (
    <div>
      <div className="flex gap-1" style={{ height: `${heightUnits * 0.25}rem` }}>
        {bins.map((b, i) => (
          <div key={i} className="flex flex-1 items-end" title={`${jd(b.low)}–${jd(b.high)} JD/m²: ${b.count} listings`}>
            <div
              className="w-full rounded-t-[2px] bg-cyan/70"
              style={{ height: `${(b.count / max) * 100}%`, minHeight: b.count > 0 ? 3 : 0 }}
            />
          </div>
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[9px] text-ink-faint">
        <span>{jd(bins[0].low)}</span>
        <span>cheaper ← → pricier</span>
        <span>{jd(bins[bins.length - 1].high)}</span>
      </div>
    </div>
  );
}

function YearBars({ years, heightUnits }: { years: AreaMonitoring["yearly_median"]; heightUnits: number }) {
  const max = Math.max(...years.map((y) => y.median), 1);
  return (
    <div className="flex gap-1" style={{ height: `${heightUnits * 0.25}rem` }}>
      {years.map((y) => (
        <div key={y.year} className="flex flex-1 flex-col" title={`${y.year}: ${jd(y.median)} JD/m² (${y.n} sales)`}>
          <div className="flex flex-1 items-end">
            <div className="w-full rounded-t-[2px] bg-pos/60" style={{ height: `${(y.median / max) * 100}%`, minHeight: 3 }} />
          </div>
          <span className="mt-1 text-center text-[9px] text-ink-faint">{`'${String(y.year).slice(2)}`}</span>
        </div>
      ))}
    </div>
  );
}

function RankStrip({ rank }: { rank: NonNullable<AreaMonitoring["price_rank"]> }) {
  return (
    <div>
      <div className="relative mt-2 h-5">
        <div className="absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-gradient-to-r from-raised via-cyan/20 to-cyan/60" />
        <div className="absolute top-0 flex -translate-x-1/2 flex-col items-center" style={{ left: `${rank.percentile}%` }}>
          <span className="text-cyan text-[11px] leading-none">▲</span>
        </div>
      </div>
      <div className="mt-1 flex justify-between text-[9px] text-ink-faint">
        <span>cheapest</span>
        <span>priciest</span>
      </div>
      <p className="mt-1.5 text-2xs leading-relaxed text-ink-dim">
        Median <span className="tnum text-ink">{jd(rank.median)} JD/m²</span> — pricier than{" "}
        <span className="text-cyan">{rank.percentile}%</span> of {rank.of_n} areas.
      </p>
    </div>
  );
}

function PortalBars({ portals }: { portals: AreaMonitoring["by_portal"] }) {
  const max = Math.max(...portals.map((p) => p.count), 1);
  return (
    <div className="space-y-1.5">
      {portals.map((p) => (
        <div key={p.portal} className="flex items-center gap-2 text-2xs">
          <span className="w-20 shrink-0 truncate text-ink-dim" title={p.portal}>{p.portal}</span>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-raised">
            <div className="h-full rounded-full bg-accent/70" style={{ width: `${(p.count / max) * 100}%` }} />
          </div>
          <span className="tnum w-10 shrink-0 text-right text-ink-mute">{jd(p.count)}</span>
        </div>
      ))}
    </div>
  );
}

function Empty({ note }: { note: string }) {
  return <p className="py-4 text-center text-2xs text-ink-faint">{note}</p>;
}

function Awaiting({ note }: { note: string }) {
  return (
    <div className="card border-dashed p-3">
      <div className="text-2xs font-medium uppercase tracking-wide text-ink-mute">Market graphs</div>
      <p className="mt-1 text-2xs leading-relaxed text-ink-dim">{note}</p>
    </div>
  );
}

function Prompt() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <div className="text-[13px] font-medium text-ink-dim">Pick an area first</div>
      <p className="mt-1 max-w-[240px] text-2xs leading-relaxed text-ink-mute">
        Then this view charts the area's price spread, yearly trend, rank and data sources.
      </p>
    </div>
  );
}
