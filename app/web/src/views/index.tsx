import type { ReactNode } from "react";
import { useApp } from "../lib/store";
import { dataSource as mockSource } from "../lib/dataSource";
import { Card } from "../ui";
import { ViewHeader } from "./ViewHeader";
import { getViewMeta } from "./viewMeta";
import { PricingView } from "./PricingView";
import { CostProfitView } from "./CostProfitView";
import { MarketView } from "./MarketView";
import { LocationView } from "./LocationView";
import { AssistantView } from "./AssistantView";
import { SettingsView } from "./SettingsView";
import { OpportunityView } from "./OpportunityView";
import { SubjectBar } from "./SubjectBar";
import { SellView } from "./SellView";

// Routes the shell's InfoPanel to the right view for the current nav
// selection. Assistant/Settings manage their own header (their sub-state
// varies per screen); the area-scoped views share one ViewHeader here.
export function ViewRouter() {
  const { state } = useApp();
  const { view, selectedArea } = state;

  if (view === "settings") return <SettingsView />;
  if (view === "chatnew" || view === "chathist" || view === "chatopen") return <AssistantView />;

  // Nationwide ranking — doesn't need an area selected (an area only sharpens
  // the "where does mine rank" callout inside OpportunityView itself).
  if (view === "opportunity" || view === "ranking") {
    const meta = getViewMeta(view);
    return (
      <div className="flex flex-col gap-3">
        <ViewHeader {...meta} />
        <OpportunityView focus={view} />
      </div>
    );
  }

  // Seller valuation uses a dropped map pin, not a selected area — render before
  // the "pick an area" guard.
  if (view === "sell") {
    const meta = getViewMeta(view);
    return (
      <div className="flex flex-col gap-3">
        <ViewHeader {...meta} />
        <SellView />
      </div>
    );
  }

  if (!selectedArea) {
    return (
      <Card>
        <div className="text-sm text-stitch-muted">
          Pick an area on the map or search above to see its launch price.
        </div>
      </Card>
    );
  }

  const bundle = mockSource.getBundle(selectedArea);
  if (!bundle) {
    return (
      <Card>
        <div className="text-sm font-semibold text-stitch-ink">{selectedArea}</div>
        <p className="mt-1.5 text-[13px] leading-relaxed text-stitch-muted">
          This area is mapped, but the engine only computes a full launch-price report for
          submarkets with enough comparable sales. Its median asking price is shown on the map
          (the coloured circle / Prices → “Asking price by area”). Pick a covered area to see the
          full decision report.
        </p>
      </Card>
    );
  }

  const meta = getViewMeta(view);

  let body: ReactNode = null;
  switch (view) {
    case "price":
    case "comps":
    case "trend":
      body = <PricingView bundle={bundle} focus={view} />;
      break;
    case "land":
    case "margin":
    case "build":
    case "scenarios":
    case "buildability":
      body = <CostProfitView bundle={bundle} focus={view} />;
      break;
    case "competitors":
    case "news":
      body = <MarketView bundle={bundle} focus={view} />;
      break;
    case "nearby":
    case "infra":
      body = <LocationView bundle={bundle} focus={view} />;
      break;
    default:
      return null;
  }

  // The subject bar (the apartment being priced) only belongs on Pricing and
  // Cost & Profit — Market/Location aren't about a specific apartment.
  const showSubject = ["price", "comps", "trend", "land", "margin", "build", "scenarios", "buildability"].includes(view);
  return (
    <div className="flex flex-col gap-3">
      {showSubject && <SubjectBar />}
      <ViewHeader {...meta} />
      {body}
    </div>
  );
}
