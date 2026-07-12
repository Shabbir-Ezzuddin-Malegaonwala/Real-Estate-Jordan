import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  AreaEntry,
  OpportunityScore,
  RecommendationBundle,
  RecommendationResult,
} from "./types";
import { loadGeo, loadRecommendations, poiCategoryCounts, loadAmenities, type GeoLayers } from "./lib/loadData";
import {
  checkHealth,
  fetchNeighborhoods,
  requestRecommendation,
  type NeighborhoodMeta,
  type SubjectInput,
} from "./lib/api";
import { fetchAreas, fetchOpportunity } from "./lib/intel";
import { adaptApiRecommendation } from "./lib/adaptEngine";
import { useEntered, type EntryMode, type StepKey } from "./lib/journey";
import { MapView } from "./components/MapView";
import { MapLayers, type LayerState } from "./components/MapLayers";
import { DEFAULT_POI_ON, type AreaAmenities } from "./lib/poi";
import { MarketCharts } from "./components/MarketCharts";
import { AreaSearch } from "./components/AreaSearch";
import { Toast } from "./components/Toast";
import { ThemeToggle } from "./components/ThemeToggle";
import { HelpPanel } from "./components/HelpPanel";
import { Landing } from "./components/Landing";
import { Stepper } from "./components/Stepper";
import { SubjectForm } from "./components/SubjectForm";
import { StepContent } from "./components/steps/StepContent";
import { OpportunityLegend } from "./components/OpportunityLegend";
import { useTheme } from "./lib/theme";

type ApiStatus = "checking" | "online" | "offline";

const DEFAULT_LAYERS: LayerState = {
  zoning: false,
  pois: false, // superseded by the 9 amenity category layers (MapLayers)
  comparables: true,
  future: true,
  roads: true,
};

// The representative unit the engine prices when the user hasn't customised it — kept in
// sync with scrapers/emit_national.py so the precomputed brief and the form agree.
const DEFAULT_SUBJECT: SubjectInput = {
  neighborhood: "",
  area_m2: 175,
  bedrooms: 3,
  floor_level: 4,
  building_age_years: 0,
  view: "unknown",
  parking: "unknown",
  finish_quality: "high",
};

function areasFromBundle(
  bundle: RecommendationBundle,
  meta: Record<string, NeighborhoodMeta>,
): AreaEntry[] {
  return Object.values(bundle.results).map((r) => {
    const m = meta[r.neighborhood];
    return {
      name: r.neighborhood,
      name_ar: r.name_ar,
      covered: true,
      context: false,
      listing_count: m?.listing_count ?? r.comps_considered,
      sale_listing_count: (m as { sale_listing_count?: number })?.sale_listing_count,
      median_price_per_m2: m?.median_price_per_m2 ?? r.base_value_jd_m2,
      centroid_lat: r.centroid?.[1],
      centroid_lng: r.centroid?.[0],
    };
  });
}

export default function App() {
  const { entered, enter, exit } = useEntered();
  const { theme, toggle: toggleTheme } = useTheme();

  const [geo, setGeo] = useState<GeoLayers | null>(null);
  const [bundle, setBundle] = useState<RecommendationBundle | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [layers, setLayers] = useState<LayerState>(DEFAULT_LAYERS);

  const [apiStatus, setApiStatusState] = useState<ApiStatus>("checking");
  const [areas, setAreas] = useState<AreaEntry[]>([]);
  const [opportunity, setOpportunity] = useState<OpportunityScore[]>([]);
  const [amenities, setAmenities] = useState<Record<string, AreaAmenities>>({});
  const [poiState, setPoiState] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(DEFAULT_POI_ON.map((k) => [k, true])),
  );
  const [layerLoading, setLayerLoading] = useState<Record<string, boolean>>({});
  const [selectedArea, setSelectedArea] = useState<AreaEntry | null>(null);
  const [subject, setSubject] = useState<SubjectInput>(DEFAULT_SUBJECT);
  const [result, setResult] = useState<RecommendationResult | null>(null);
  const [computing, setComputing] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const [step, setStep] = useState<StepKey>("pricing");

  const apiStatusRef = useRef<ApiStatus>("checking");
  const bundleRef = useRef<RecommendationBundle | null>(null);
  const subjectRef = useRef<SubjectInput>(subject);
  subjectRef.current = subject;

  const setApiStatus = (s: ApiStatus) => {
    apiStatusRef.current = s;
    setApiStatusState(s);
  };

  // Unchanged engine wiring: online → POST /recommend; offline → precomputed.
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
        setResult(pre ? { ...pre, source_note: "Offline — showing precomputed defaults (API unreachable)." } : null);
      }
    } catch (e) {
      setApiStatus("offline");
      const pre = bundleRef.current?.results[subj.neighborhood];
      setResult(
        pre
          ? { ...pre, source_note: `Offline — ${e instanceof Error ? e.message : "API error"}; showing precomputed defaults.` }
          : null,
      );
    } finally {
      setComputing(false);
    }
  }, []);

  const selectArea = useCallback(
    (area: AreaEntry) => {
      setSelectedArea(area);
      if (area.covered) {
        // price the area with the user's current subject params, not a bare default
        const subj = { ...subjectRef.current, neighborhood: area.name };
        setSubject(subj);
        recompute(subj);
      } else setResult(null);
    },
    [recompute],
  );

  // Subject form wiring: edit a field → patch state; "Analyze" → recompute on demand.
  const onPatchSubject = useCallback(
    (patch: Partial<SubjectInput>) => setSubject((s) => ({ ...s, ...patch })),
    [],
  );
  const onAnalyze = useCallback(() => {
    const subj = subjectRef.current;
    if (subj.neighborhood && subj.area_m2) recompute(subj);
  }, [recompute]);

  const selectByName = useCallback(
    (name: string) => {
      const a = areas.find((x) => x.name === name) ?? {
        name,
        covered: !!bundleRef.current?.results[name],
        context: !bundleRef.current?.results[name],
      };
      selectArea(a);
    },
    [areas, selectArea],
  );

  const onEnter = useCallback(
    (_mode: EntryMode) => {
      enter();
      setStep("pricing"); // recommendation-first: land on the launch-price view
    },
    [enter],
  );

  const onTogglePoi = useCallback((k: string) => setPoiState((s) => ({ ...s, [k]: !s[k] })), []);
  const onLayerLoading = useCallback(
    (k: string, loading: boolean) => setLayerLoading((s) => ({ ...s, [k]: loading })),
    [],
  );

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [g, b, am] = await Promise.all([loadGeo(), loadRecommendations(), loadAmenities()]);
        if (!alive) return;
        setGeo(g);
        setBundle(b);
        setAmenities(am);
        bundleRef.current = b;

        let meta: Record<string, NeighborhoodMeta> = {};
        const ok = await checkHealth();
        if (!alive) return;
        setApiStatus(ok ? "online" : "offline");
        if (ok) {
          try {
            const list = await fetchNeighborhoods();
            for (const n of list) meta[n.name] = n;
          } catch {
            meta = {};
          }
        }

        const liveAreas = await fetchAreas(areasFromBundle(b, meta));
        if (!alive) return;
        setAreas(liveAreas);
        const opp = await fetchOpportunity(liveAreas, g.opportunityHeatmap);
        if (alive) setOpportunity(opp);
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 6000);
    return () => window.clearTimeout(t);
  }, [toast]);

  const poiCounts = useMemo(() => (geo ? poiCategoryCounts(geo.pois) : {}), [geo]);
  const selectedOpp = useMemo(
    () => opportunity.find((o) => o.area === selectedArea?.name) ?? null,
    [opportunity, selectedArea],
  );
  const selectedAmenities = useMemo(
    () => (selectedArea ? amenities[selectedArea.name] ?? null : null),
    [amenities, selectedArea],
  );
  // The priceable set is exactly the engine's result keys — reliable and always populated
  // once the bundle loads (the `areas` list routes through the /areas API and can be empty).
  const neighborhoodNames = useMemo(
    () => (bundle ? Object.keys(bundle.results).sort((x, y) => x.localeCompare(y)) : []),
    [bundle],
  );

  // Recommendation-first: once data is ready, open on the first neighbourhood so the price
  // bands are populated and Analyze is enabled immediately (user can change area/params).
  useEffect(() => {
    if (!selectedArea && neighborhoodNames.length) selectByName(neighborhoodNames[0]);
  }, [neighborhoodNames, selectedArea, selectByName]);

  if (!entered) return <Landing onEnter={onEnter} theme={theme} onToggleTheme={toggleTheme} />;
  if (error) return <Splash title="Failed to load" detail={error} tone="error" />;
  if (!geo || !bundle) return <Splash title="Loading Amman intelligence…" detail="Reading map layers and engine output." />;

  const selected = selectedArea?.name ?? null;

  return (
    <div className="relative h-full w-full overflow-hidden bg-base text-ink">
      <MapView
        geo={geo}
        bundle={bundle}
        selected={selected}
        onSelect={selectByName}
        onOutside={() => setToast("No structured data for this location yet — pick a covered area or search.")}
        layers={layers}
        theme={theme}
        opportunity={opportunity}
        showOpportunity
        poiState={poiState}
        onLayerLoading={onLayerLoading}
      />

      <div className="pointer-events-none absolute inset-0 z-10">
        <MapLayers
          state={layers}
          onToggle={(k) => setLayers((s) => ({ ...s, [k]: !s[k] }))}
          poiState={poiState}
          onTogglePoi={onTogglePoi}
          loading={layerLoading}
        />
        <OpportunityLegend />
        <MarketCharts bundle={bundle} poiCounts={poiCounts} selected={selected} onSelect={selectByName} />
        {toast && <Toast message={toast} onClose={() => setToast(null)} />}
      </div>

      <aside
        className="scroll-thin absolute inset-y-0 left-0 z-20 flex w-[440px] max-w-[92vw] flex-col overflow-y-auto border-r border-line bg-surface/95 backdrop-blur-sm"
        aria-label="Builder workspace"
      >
        <header className="sticky top-0 z-30 border-b border-line bg-surface/95 px-4 py-3 backdrop-blur-sm">
          <div className="flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={exit}
              className="min-w-0 text-left"
              aria-label="Back to start"
              title="Back to start"
            >
              <div className="label-eyebrow">Jordan Real Estate Intelligence</div>
              <div className="text-[15px] font-semibold tracking-tight text-ink">Builder workspace</div>
            </button>
            <div className="flex shrink-0 items-center gap-2">
              <ApiBadge status={apiStatus} />
              <button
                type="button"
                onClick={() => setHelpOpen(true)}
                aria-label="How to use this tool"
                className="grid h-7 w-7 place-items-center rounded-[3px] border border-line bg-panel text-[13px] font-semibold text-ink-dim transition-colors hover:border-cyan-dim hover:text-ink"
              >
                ?
              </button>
              <ThemeToggle theme={theme} onToggle={toggleTheme} />
            </div>
          </div>
        </header>

        <AreaSearch areas={areas} onPick={selectArea} />
        <SubjectForm
          subject={subject}
          neighborhoods={neighborhoodNames}
          onPatch={onPatchSubject}
          onNeighborhood={selectByName}
          onAnalyze={onAnalyze}
          computing={computing}
        />
        <Stepper active={step} onSelect={setStep} />

        <StepContent
          step={step}
          area={selectedArea}
          result={result}
          opportunity={selectedOpp}
          amenities={selectedAmenities}
          computing={computing}
          generatedAt={bundle.generated_at}
        />

        <footer className="mt-auto border-t border-line px-4 py-3 text-2xs leading-relaxed text-ink-mute">
          {bundle.disclaimer}
        </footer>
      </aside>

      {helpOpen && <HelpPanel onClose={() => setHelpOpen(false)} />}
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

function Splash({ title, detail, tone }: { title: string; detail: string; tone?: "error" }) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center bg-base px-6 text-center">
      <div className={`text-[14px] font-semibold ${tone === "error" ? "text-neg" : "text-ink"}`}>{title}</div>
      <p className="mt-1.5 max-w-[380px] text-2xs leading-relaxed text-ink-mute">{detail}</p>
    </div>
  );
}
