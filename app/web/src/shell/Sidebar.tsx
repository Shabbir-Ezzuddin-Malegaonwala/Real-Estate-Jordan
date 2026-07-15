import { useState } from "react";
import { NAV } from "../lib/contract";
import type { NavGroup } from "../lib/contract";
import { useApp } from "../lib/store";

// Assistant isn't a pricing/cost/market/location category, but it lives in the
// same collapsible-group nav (Demo-G) — declared locally, not in the contract.
const ASSISTANT_GROUP: NavGroup = {
  icon: "🤖",
  label: "Assistant",
  subs: [
    { key: "chatnew", label: "New chat" },
    { key: "chathist", label: "Chat history" },
  ],
};

const GROUPS: NavGroup[] = [...NAV, ASSISTANT_GROUP];

export function Sidebar() {
  const { state, setView } = useApp();
  // First group open by default (Demo-G), rest collapsed.
  const [open, setOpen] = useState<boolean[]>(() => GROUPS.map((_, i) => i === 0));

  function toggleGroup(i: number) {
    setOpen((o) => o.map((v, idx) => (idx === i ? !v : v)));
  }

  return (
    <nav className="flex h-full w-full flex-col p-2">
      <div className="flex-1 overflow-y-auto">
      {GROUPS.map((g, i) => (
        <div key={g.label} className="mt-1">
          <button
            type="button"
            onClick={() => toggleGroup(i)}
            className="flex w-full items-center gap-2.5 whitespace-nowrap rounded-lg px-2.5 py-2 text-left text-[13px] font-bold text-stitch-ink hover:bg-stitch-soft"
          >
            <span className="w-5 text-center text-base">{g.icon}</span>
            {g.label}
            <span
              className={`ml-auto text-[11px] text-stitch-muted transition-transform ${open[i] ? "rotate-90" : ""}`}
              aria-hidden
            >
              ▸
            </span>
          </button>
          {open[i] && (
            <div className="py-0.5 pl-10 pr-1">
              {g.subs.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  onClick={() => setView(s.key)}
                  className={`block w-full whitespace-nowrap rounded-md px-2.5 py-1.5 text-left text-[13.5px] ${
                    state.view === s.key
                      ? "bg-[#e7f1fb] font-semibold text-stitch-brand-dark"
                      : "text-stitch-muted hover:bg-stitch-soft"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          )}
        </div>
      ))}
      </div>

      <div className="mt-2 border-t border-stitch-line pt-2">
        <button
          type="button"
          onClick={() => setView("settings")}
          className={`flex w-full items-center gap-2.5 whitespace-nowrap rounded-lg px-2.5 py-2 text-left text-[13px] font-bold ${
            state.view === "settings" ? "text-stitch-brand-dark" : "text-stitch-ink hover:bg-stitch-soft"
          }`}
        >
          <span className="w-5 text-center text-base">⚙</span>
          Settings
        </button>
      </div>
    </nav>
  );
}
