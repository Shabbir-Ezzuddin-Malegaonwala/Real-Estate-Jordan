import { type ReactNode } from "react";
import { useApp } from "../lib/store";
import { Card } from "../ui";
import { ViewHeader } from "./ViewHeader";
import { getViewMeta } from "./viewMeta";

function SegToggle<T extends string>({
  options,
  value,
  onChange,
}: {
  options: readonly T[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="inline-flex rounded-lg bg-stitch-soft p-1">
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(opt)}
          className={`rounded-md px-3 py-1.5 text-sm font-semibold ${
            opt === value ? "bg-stitch-card text-stitch-brand-dark shadow-sm" : "text-stitch-muted"
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

function SettingsRow({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-stitch-soft py-3.5 last:border-b-0">
      <div>
        <div className="text-sm font-semibold text-stitch-ink">{label}</div>
        {hint && <div className="mt-0.5 text-[13px] text-stitch-muted">{hint}</div>}
      </div>
      {children}
    </div>
  );
}

export function SettingsView() {
  const { state, setLanguage } = useApp();
  const meta = getViewMeta("settings");

  return (
    <div className="flex flex-col gap-3">
      <ViewHeader {...meta} />
      <Card padded={false}>
        <div className="px-4">
          <SettingsRow label="Report language" hint="Language for AI summaries & the property valuation report">
            <SegToggle
              options={["English", "العربية"] as const}
              value={state.language === "ar" ? "العربية" : "English"}
              onChange={(v) => setLanguage(v === "العربية" ? "ar" : "en")}
            />
          </SettingsRow>
        </div>
      </Card>

      <Card padded={false}>
        <div className="px-4">
          <div className="pt-3 pb-1 text-[11px] font-semibold uppercase tracking-wide text-stitch-muted">Not available yet</div>
          <SettingsRow label="Dark mode" hint="The interface is light-only for now — planned">
            <span className="rounded-md bg-stitch-soft px-2.5 py-1 text-xs font-semibold text-stitch-muted">Coming</span>
          </SettingsRow>
          <SettingsRow label="Weekly email digest" hint="Needs the mail service — planned">
            <span className="rounded-md bg-stitch-soft px-2.5 py-1 text-xs font-semibold text-stitch-muted">Coming</span>
          </SettingsRow>
          <SettingsRow label="Account & sign-in" hint="Accounts aren't wired yet — chats are stored locally on this device">
            <span className="rounded-md bg-stitch-soft px-2.5 py-1 text-xs font-semibold text-stitch-muted">Local only</span>
          </SettingsRow>
        </div>
      </Card>
      <p className="px-1 text-[11px] leading-relaxed text-stitch-muted">
        Only settings that actually change something are shown as active. The rest are marked honestly until built.
      </p>
    </div>
  );
}
