import { useEffect } from "react";
import { AppStateProvider, useApp } from "./lib/store";
import { dataSource as mockSource } from "./lib/dataSource";
import { AppShell } from "./shell/AppShell";

// Runs inside AppStateProvider — auto-selects the first area on first mount
// so the app opens recommendation-first (price bands populated immediately).
function AppBootstrap() {
  const { state, setArea } = useApp();

  useEffect(() => {
    if (!state.selectedArea) {
      const first = mockSource.listAreas()[0];
      if (first) setArea(first.name);
    }
    // Mount-only: selecting an area here must not re-fire when it changes later.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <AppShell />;
}

export default function App() {
  useEffect(() => {
    // This shell is the light, white+blue Stitch theme — force light regardless
    // of index.html's pre-paint dark-default script (used by the old terminal UI).
    document.documentElement.dataset.theme = "light";
    document.documentElement.style.colorScheme = "light";
  }, []);

  return (
    <div className="light h-screen w-screen bg-stitch-bg text-stitch-ink">
      <AppStateProvider>
        <AppBootstrap />
      </AppStateProvider>
    </div>
  );
}
