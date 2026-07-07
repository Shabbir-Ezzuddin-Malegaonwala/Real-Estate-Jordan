import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RecommendationBundle, RecommendationResult } from "./types";
import { loadGeo, loadRecommendations, poiCategoryCounts, type GeoLayers } from "./lib/loadData";
import {
  checkHealth,
  fetchNeighborhoods,
  requestRecommendation,
  type NeighborhoodMeta,
  type SubjectInput,
} from "./lib/api";
import { adaptApiRecommendation } from "./lib/adaptEngine";
import { MapView } from "./components/MapView";
import { LayerControl, type LayerState } from "./components/LayerControl";
import { MarketCharts } from "./components/MarketCharts";
import { SubjectForm } from "./components/SubjectForm";
import { SearchBox } from "./components/SearchBox";
import { Toast } from "./components/Toast";
import { PriceBands } from "./components/PriceBands";
import { AdjustmentWaterfall } from "./components/AdjustmentWaterfall";
import { EvidenceSection } from "./components/EvidenceSection";
import { Comparables } from "./components/Comparables";
import { RiskAndNarrative } from "./components/RiskAndNarrative";
import { shortDate } from "./lib/format";

type ApiStatus = "checking" | "online" | "offline";

const DEFAULT_LAYERS: LayerState = {
  zoning: false,
  pois: true,
  comparables: true,
  future: true,
  roads: true,
};

const COVERED = "Abdoun, Dabouq, Sweifieh, Khalda, Shmeisani";

function metaFromBundle(b: RecommendationBundle): Record<string, NeighborhoodMeta> {
  const out: Record<string, NeighborhoodMeta> = {};
  for (const [nb, r] of Object.entries(b.results)) {
    out[nb] = {
      name: nb,
      centroid_lat: r.centroid?.[1] ?? 0,
      centroid_lng: r.centroid?.[0] ?? 0,
      listing_count: r.comps_considered ?? 0,
      median_price_per_m2: r.base_value_jd_m2 ?? 0,
    };
  }
  return out;
}

export default function App() {
  const [geo, setGeo] = useState<GeoLayers | null>(null);
  const [bundle, setBundle] = useState<RecommendationBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [layers, setLayers] = useState<LayerState>(DEFAULT_LAYERS);

  const [apiStatus, setApiStatusState] = useState<ApiStatus>("checking");
  const [meta, setMeta] = useState<Record<string, NeighborhoodMeta>>({});
  const [subject, setSubject] = useState<SubjectInput | null>(null);
  const [result, setResult] = useState<RecommendationResult | null>(null);
  const [computing, setComputing] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const apiStatusRef = useRef<ApiStatus>("checking");
  const bundleRef = useRef<RecommendationBundle | null>(null);
  const timer = useRef<number>();

  const setApiStatus = (s: ApiStatus) => {
    apiStatusRef.current = s;
    setApiStatusState(s);
  };

  // The single compute path. Online → POST /recommend; offline → the precomputed
  // engine result for the neighbourhood. Reads status/bundle from refs so it stays
  // stable and callable from event handlers.
  const recompute = useCallback(async (subj: SubjectInput) => {
    const b = bundleRef.current;
    const centroid = b?.results[subj.neighborhood]?.centroid ?? null;
    setComputing(true);
    try {
      if (apiStatusRef.current === "online") {
        const raw = await requestRecommendation(subj);
        const res = adaptApiRecommendation(raw, "Live API · computed on demand");
        res.centroid = centroid;
        setResult(res);
      } else {
        const pre = b?.results[subj.neighborhood];
        setResult(
          pre
            ? { ...pre, source_note: "Offline — showing precomputed defaults (API unreachable)." }
            : null,
        );
      }
    } catch (e) {
      setApiStatus("offline");
      const pre = bundleRef.current?.results[subj.neighborhood];
      setResult(
        pre
          ? {
              ...pre,
              source_note: `Offline — ${e instanceof Error ? e.message : "API error"}; showing precomputed defaults.`,
            }
          : null,
      );
    } finally {
      setComputing(false);
    }
  }, []);

  const schedule = useCallback(
    (subj: SubjectInput) => {
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => recompute(subj), 400);
    },
    [recompute],
  );

  // Field edits: update subject + debounced recompute.
  const patch = useCallback(
    (p: Partial<SubjectInput>) =>
      setSubject((prev) => {
        if (!prev) return prev;
        const next = { ...prev, ...p };
        schedule(next);
        return next;
      }),
    [schedule],
  );

  // Neighbourhood change (form select, search, map click, market bar): immediate.
  const selectNeighborhood = useCallback(
    (nb: string) =>
      setSubject((prev) => {
        const next: SubjectInput = { ...(prev ?? { area_m2: 175 }), neighborhood: nb };
        window.clearTimeout(timer.current);
        recompute(next);
        return next;
      }),
    [recompute],
  );

  const analyze = useCallback(() => {
    if (subject) {
      window.clearTimeout(timer.current);
      recompute(subject);
    }
  }, [recompute, subject]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [g, b] = await Promise.all([loadGeo(), loadRecommendations()]);
        if (!alive) return;
        setGeo(g);
        setBundle(b);
        bundleRef.current = b;
        setMeta(metaFromBundle(b));

        const def =
          Object.values(b.results).find((r) => r.is_live)?.neighborhood ??
          Object.keys(b.results)[0];
        const initSubject: SubjectInput = {
          neighborhood: def,
          area_m2: 175,
          view: "unknown",
          parking: "unknown",
          finish_quality: "unknown",
        };
        setSubject(initSubject);

        const ok = await checkHealth();
        if (!alive) return;
        setApiStatus(ok ? "online" : "offline");
        if (ok) {
          try {
            const list = await fetchNeighborhoods();
            if (alive) {
              setMeta((m) => {
                const next = { ...m };
                for (const n of list) next[n.name] = n;
                return next;
              });
            }
          } catch {
            // /neighborhoods optional — coverage falls back to bundle-derived meta
          }
        }
        if (alive) recompute(initSubject);
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      alive = false;
      window.clearTimeout(timer.current);
    };
  }, [recompute]);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 6000);
    return () => window.clearTimeout(t);
  }, [toast]);

  const poiCounts = useMemo(() => (geo ? poiCategoryCounts(geo.pois) : {}), [geo]);

  if (error) return <Splash title="Failed to load" detail={error} tone="error" />;
  if (!geo || !bundle || !subject)
    return <Splash title="Loading Amman intelligence…" detail="Reading map layers and engine output." />;

  const neighborhoods = Object.keys(bundle.results);
  const selected = subject.neighborhood;

  return (
    <div className="relative h-full w-full overflow-hidden bg-base text-ink">
      <MapView
        geo={geo}
        bundle={bundle}
        selected={selected}
        onSelect={selectNeighborhood}
        onOutside={() =>
          setToast(`No data for this location — select a covered submarket (${COVERED}).`)
        }
        layers={layers}
      />

      <div className="pointer-events-none absolute inset-0 z-10">
        <LayerControl state={layers} onToggle={(k) => setLayers((s) => ({ ...s, [k]: !s[k] }))} />
        <MarketCharts
          bundle={bundle}
          poiCounts={poiCounts}
          selected={selected}
          onSelect={selectNeighborhood}
        />
        {toast && <Toast message={toast} onClose={() => setToast(null)} />}
      </div>

      <aside
        className="scroll-thin absolute inset-y-0 left-0 z-20 flex w-[440px] max-w-[92vw] flex-col overflow-y-auto border-r border-line bg-surface/95 backdrop-blur-sm"
        aria-label="Analysis panel"
      >
        <header className="sticky top-0 z-30 border-b border-line bg-surface/95 px-4 py-3 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <div>
              <div className="label-eyebrow">Amman Real Estate</div>
              <div className="text-[15px] font-semibold tracking-tight text-ink">Analyst Terminal</div>
            </div>
            <ApiBadge status={apiStatus} />
          </div>
        </header>

        <SearchBox neighborhoods={neighborhoods} meta={meta} onPick={selectNeighborhood} />
        <SubjectForm
          subject={subject}
          neighborhoods={neighborhoods}
          onPatch={patch}
          onNeighborhood={selectNeighborhood}
          onAnalyze={analyze}
          computing={computing}
        />

        {result ? (
          <Analysis r={result} computing={computing} />
        ) : (
          <EmptyState />
        )}

        <footer className="mt-auto border-t border-line px-4 py-3 text-2xs leading-relaxed text-ink-mute">
          {bundle.disclaimer}
        </footer>
      </aside>
    </div>
  );
}

function Analysis({ r, computing }: { r: RecommendationResult; computing: boolean }) {
  const future = r.evidence_objects.filter((e) => e.category === "future_signal");
  return (
    <div className={`pb-2 transition-opacity ${computing ? "opacity-50" : "opacity-100"}`}>
      <div className="border-b border-line-soft px-4 py-3">
        <div className="flex items-center gap-2">
          <h2 className="truncate text-[18px] font-semibold text-ink">{r.neighborhood}</h2>
          {r.name_ar && <span className="text-[15px] text-ink-mute">{r.name_ar}</span>}
        </div>
        <div className="mt-0.5 text-2xs text-ink-mute">
          {r.tier ? `${r.tier} · ` : ""}
          {r.property_type}
          {r.as_of ? ` · as of ${shortDate(r.as_of)}` : ""}
        </div>
        {r.source_note && (
          <p className="mt-1.5 text-2xs italic leading-relaxed text-ink-faint">{r.source_note}</p>
        )}
      </div>

      <SectionDivider label="Current state — today's justified range" />
      <PriceBands r={r} />
      <AdjustmentWaterfall r={r} />

      <SectionDivider label="Future signals — appreciation narrative" tone="future" />
      {future.length > 0 ? (
        <EvidenceSection
          title="Future Signals"
          eyebrow="positioning, not applied to today's band"
          tone="future"
          items={future}
        />
      ) : (
        <AwaitingData note="No infrastructure, policy, or news signals collected for this submarket yet — the Future Signals pipeline is pending (v1). The premium tier rests on the current-state comparison band." />
      )}

      <Comparables items={r.comparables} />
      <RiskAndNarrative risks={r.risk_factors} narrative={r.narrative} />
    </div>
  );
}

function ApiBadge({ status }: { status: ApiStatus }) {
  if (status === "online")
    return (
      <span className="shrink-0 rounded-[2px] border border-pos/40 bg-pos/10 px-2 py-[2px] text-2xs font-medium uppercase tracking-wide text-pos">
        Live API
      </span>
    );
  if (status === "offline")
    return (
      <span className="shrink-0 rounded-[2px] border border-warn/40 bg-warn/10 px-2 py-[2px] text-2xs font-medium uppercase tracking-wide text-warn">
        Offline · precomputed
      </span>
    );
  return (
    <span className="shrink-0 rounded-[2px] border border-line bg-panel px-2 py-[2px] text-2xs font-medium uppercase tracking-wide text-ink-mute">
      Checking API…
    </span>
  );
}

function SectionDivider({ label, tone }: { label: string; tone?: "current" | "future" }) {
  return (
    <div className="flex items-center gap-2 px-4 pt-5">
      <span
        className={`inline-block h-3 w-[3px] rounded-full ${tone === "future" ? "bg-cyan" : "bg-accent"}`}
      />
      <span className="label-eyebrow">{label}</span>
    </div>
  );
}

function AwaitingData({ note }: { note: string }) {
  return (
    <div className="px-4 pt-2">
      <div className="card border-dashed p-3">
        <div className="text-2xs font-medium uppercase tracking-wide text-ink-mute">Awaiting data</div>
        <p className="mt-1 text-2xs leading-relaxed text-ink-dim">{note}</p>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 text-center">
      <div className="text-[13px] font-medium text-ink-dim">Enter a subject property</div>
      <p className="mt-1 max-w-[240px] text-2xs leading-relaxed text-ink-mute">
        Pick a submarket and size above, or click a neighbourhood on the map, to compute an
        evidence-backed launch price.
      </p>
    </div>
  );
}

function Splash({ title, detail, tone }: { title: string; detail: string; tone?: "error" }) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center bg-base px-6 text-center">
      <div className={`text-[14px] font-semibold ${tone === "error" ? "text-neg" : "text-ink"}`}>
        {title}
      </div>
      <p className="mt-1.5 max-w-[380px] text-2xs leading-relaxed text-ink-mute">{detail}</p>
    </div>
  );
}
