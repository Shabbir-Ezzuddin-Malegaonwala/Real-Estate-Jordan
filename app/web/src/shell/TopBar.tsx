import { useEffect, useMemo, useRef, useState } from "react";
import { mockSource } from "../lib/mock";
import { useApp } from "../lib/store";

// Placeholder identity until Phase 6 auth lands — same shape the real account
// menu will use once accounts exist.
const ACCOUNT_NAME = "Mohammad Jamaal";
const ACCOUNT_EMAIL = "mohammad@noble.co";
const ACCOUNT_INITIAL = "M";

export function TopBar() {
  const { state, setArea, setView, toggleNav, toggleInfo } = useApp();
  const areas = useMemo(() => mockSource.listAreas(), []);

  const [query, setQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [acctOpen, setAcctOpen] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const acctRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      const target = e.target as Node;
      if (searchRef.current && !searchRef.current.contains(target)) setSearchOpen(false);
      if (acctRef.current && !acctRef.current.contains(target)) setAcctOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const trimmed = query.trim().toLowerCase();
  const matches = trimmed ? areas.filter((a) => a.name.toLowerCase().includes(trimmed)).slice(0, 8) : [];
  const showNoMatch = trimmed.length > 2 && matches.length === 0;

  function pick(name: string) {
    setArea(name);
    setQuery(name);
    setSearchOpen(false);
  }

  function askAssistant() {
    setView("chatnew");
    setSearchOpen(false);
  }

  function closeAcct() {
    setAcctOpen(false);
  }

  return (
    <div className="flex h-[54px] flex-none items-center gap-2.5 border-b border-stitch-line bg-stitch-card px-3.5">
      <button
        type="button"
        onClick={toggleNav}
        title="Menu"
        aria-label="Toggle navigation"
        className={`rounded-md p-1.5 text-lg hover:bg-stitch-soft ${
          state.navOpen ? "text-stitch-brand-dark" : "text-stitch-muted"
        }`}
      >
        ☰
      </button>
      <button
        type="button"
        onClick={toggleInfo}
        title="Detail panel"
        aria-label="Toggle detail panel"
        className={`rounded-md p-1.5 text-lg hover:bg-stitch-soft ${
          state.infoOpen ? "text-stitch-brand-dark" : "text-stitch-muted"
        }`}
      >
        ▤
      </button>

      <div className="ml-0.5 flex-none">
        <div className="text-[15px] font-bold leading-tight text-stitch-ink">Jordan Real Estate</div>
        <div className="text-[10px] font-normal uppercase tracking-wide text-stitch-muted">Intelligence</div>
      </div>

      <div ref={searchRef} className="relative ml-3 min-w-[120px] max-w-[460px] flex-1">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-stitch-muted">🔍</span>
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSearchOpen(true);
          }}
          onFocus={() => setSearchOpen(true)}
          placeholder="Search an area…"
          className="w-full rounded-lg border border-stitch-line bg-stitch-soft py-2.5 pl-9 pr-3 text-sm text-stitch-ink outline-none focus:border-stitch-brand"
        />
        {searchOpen && (matches.length > 0 || showNoMatch) && (
          <div className="absolute left-0 right-0 top-[42px] z-30 rounded-lg border border-stitch-line bg-white p-2 text-sm text-stitch-muted shadow-lg">
            {matches.map((a) => (
              <button
                key={a.name}
                type="button"
                onClick={() => pick(a.name)}
                className="block w-full rounded-md px-2 py-1.5 text-left text-stitch-ink hover:bg-stitch-soft"
              >
                {a.name}
                <span className="ml-2 text-xs text-stitch-muted">{a.price.toLocaleString()} JD/m²</span>
              </button>
            ))}
            {showNoMatch && (
              <div className="px-2 py-1.5">
                “{query}” isn’t in our data —{" "}
                <button type="button" onClick={askAssistant} className="font-semibold text-stitch-brand-dark">
                  ask the Assistant
                </button>{" "}
                to look it up live.
              </div>
            )}
          </div>
        )}
      </div>

      <div className="ml-auto flex flex-none items-center gap-2.5 text-stitch-muted">
        <span className="flex items-center gap-1.5 text-xs font-bold text-stitch-green">
          <span className="h-2 w-2 animate-pulse rounded-full bg-stitch-green" aria-hidden />
          LIVE
        </span>

        <div ref={acctRef} className="relative">
          <button
            type="button"
            onClick={() => setAcctOpen((v) => !v)}
            className="grid h-8 w-8 place-items-center rounded-full bg-stitch-brand text-[13px] font-bold text-white"
            aria-label="Account menu"
          >
            {ACCOUNT_INITIAL}
          </button>
          {acctOpen && (
            <div className="absolute right-0 top-10 z-40 w-[226px] rounded-xl border border-stitch-line bg-white p-1.5 shadow-xl">
              <div className="mb-1 border-b border-stitch-line px-3 py-2.5">
                <div className="font-bold text-stitch-ink">{ACCOUNT_NAME}</div>
                <div className="text-xs text-stitch-muted">{ACCOUNT_EMAIL}</div>
              </div>
              <button
                type="button"
                onClick={closeAcct}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-stitch-ink hover:bg-stitch-soft"
              >
                👤 My profile
              </button>
              <button
                type="button"
                onClick={() => {
                  setView("chathist");
                  closeAcct();
                }}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-stitch-ink hover:bg-stitch-soft"
              >
                💬 My chats
              </button>
              <button
                type="button"
                onClick={() => {
                  setView("settings");
                  closeAcct();
                }}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-stitch-ink hover:bg-stitch-soft"
              >
                ⚙ Settings
              </button>
              <button
                type="button"
                onClick={closeAcct}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-stitch-ink hover:bg-stitch-soft"
              >
                🌐 Language · العربية
              </button>
              <button
                type="button"
                onClick={closeAcct}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-stitch-ink hover:bg-stitch-soft"
              >
                ❓ Help &amp; support
              </button>
              <div className="my-1 h-px bg-stitch-line" />
              <button
                type="button"
                onClick={closeAcct}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-stitch-ink hover:bg-stitch-soft"
              >
                ↩ Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
