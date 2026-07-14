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

// Routes the shell's InfoPanel to the right view for the current nav
// selection. Assistant/Settings manage their own header (their sub-state
// varies per screen); the area-scoped views share one ViewHeader here.
export function ViewRouter() {
  const { state } = useApp();
  const { view, selectedArea } = state;

  if (view === "settings") return <SettingsView />;
  if (view === "chatnew" || view === "chathist" || view === "chatopen") return <AssistantView />;

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
        <div className="text-sm text-stitch-muted">No data yet for &quot;{selectedArea}&quot;.</div>
      </Card>
    );
  }

  const meta = getViewMeta(view);

  switch (view) {
    case "price":
    case "comps":
    case "trend":
      return (
        <div className="flex flex-col gap-3">
          <ViewHeader {...meta} />
          <PricingView bundle={bundle} focus={view} />
        </div>
      );
    case "land":
    case "margin":
    case "build":
      return (
        <div className="flex flex-col gap-3">
          <ViewHeader {...meta} />
          <CostProfitView bundle={bundle} focus={view} />
        </div>
      );
    case "competitors":
    case "news":
      return (
        <div className="flex flex-col gap-3">
          <ViewHeader {...meta} />
          <MarketView bundle={bundle} focus={view} />
        </div>
      );
    case "nearby":
    case "infra":
      return (
        <div className="flex flex-col gap-3">
          <ViewHeader {...meta} />
          <LocationView bundle={bundle} focus={view} />
        </div>
      );
    default:
      return null;
  }
}
