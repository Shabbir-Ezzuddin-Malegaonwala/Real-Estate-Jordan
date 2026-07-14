// Selects the live engine (realSource) when the API is reachable, else falls
// back to the offline mock — same DataSource contract either way, so the UI
// never branches on which source is active. initDataSource() is awaited once
// in main.tsx before the first render, so listAreas() is never empty/stale on
// mount; getBundle() falls back to the mock per-area until prefetch(area)
// resolves (triggered on selection — see store.tsx's setArea).
import type { AreaBundle, AreaListItem, DataSource } from "./contract";
import { mockSource } from "./mock";
import { checkHealth } from "./api";
import * as real from "./realSource";

let mode: "real" | "mock" = "mock";
let initPromise: Promise<void> | null = null;

export function initDataSource(): Promise<void> {
  if (initPromise) return initPromise;
  initPromise = (async () => {
    try {
      const online = await checkHealth();
      if (!online) return;
      const areas = await real.primeAreas();
      if (areas.length > 0) mode = "real";
    } catch {
      mode = "mock";
    }
  })();
  return initPromise;
}

export const dataSource: DataSource = {
  listAreas(): AreaListItem[] {
    return mode === "real" ? real.listAreas() : mockSource.listAreas();
  },
  getBundle(area: string): AreaBundle | null {
    if (mode !== "real") return mockSource.getBundle(area);
    const cached = real.getBundle(area);
    if (cached) return cached;
    void real.prefetch(area); // fire-and-forget; store.tsx's setArea awaits + re-renders
    return mockSource.getBundle(area);
  },
  prefetch(area: string): Promise<void> {
    return mode === "real" ? real.prefetch(area) : Promise.resolve();
  },
  ready(area: string): boolean {
    return mode === "real" ? real.ready(area) : true;
  },
};
