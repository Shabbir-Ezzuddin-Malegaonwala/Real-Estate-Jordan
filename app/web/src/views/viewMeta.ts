// Breadcrumb/title/subtitle text per ViewKey — single source of truth so
// every view gets a consistent header without duplicating copy per file.
// Category/label come from the contract's NAV (nav sidebar); subtitles are
// the plain-language one-liners from the Demo-G/E reference.
import { NAV } from "../lib/contract";
import type { ViewKey } from "../lib/contract";

export interface ViewMeta {
  category: string;
  title: string;
  subtitle?: string;
}

const SUBTITLES: Partial<Record<ViewKey, string>> = {
  price: "What price to sell your units at",
  comps: "Recent nearby sales the price is built on",
  trend: "How the area price moved over 90 days",
  land: "The most you can pay for the land",
  margin: "Your profit if you build and sell",
  build: "Estimated construction cost",
  competitors: "Nearby projects and their launch prices",
  news: "Recent events that affect prices",
  nearby: "What's around the area",
  infra: "Roads & transport that lift future prices",
  chathist: "Your past questions — open one to continue",
};

const NAV_BY_VIEW = new Map<ViewKey, { category: string; label: string }>();
for (const group of NAV) {
  for (const sub of group.subs) NAV_BY_VIEW.set(sub.key, { category: group.label, label: sub.label });
}

const EXTRA: Partial<Record<ViewKey, ViewMeta>> = {
  chatnew: { category: "Assistant", title: "New chat" },
  chathist: { category: "Assistant", title: "Chat history", subtitle: SUBTITLES.chathist },
  settings: { category: "Settings", title: "Settings" },
};

export function getViewMeta(view: ViewKey): ViewMeta {
  const extra = EXTRA[view];
  if (extra) return extra;
  const found = NAV_BY_VIEW.get(view);
  return { category: found?.category ?? "", title: found?.label ?? "", subtitle: SUBTITLES[view] };
}
