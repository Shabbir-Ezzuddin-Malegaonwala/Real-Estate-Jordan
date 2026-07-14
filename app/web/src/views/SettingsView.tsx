import { useState, type ReactNode } from "react";
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
  const [language, setLanguage] = useState<"English" | "العربية">("English");
  const [theme, setTheme] = useState<"Light" | "Dark">("Light");
  const [weeklyEmail, setWeeklyEmail] = useState<"On" | "Off">("On");
  const meta = getViewMeta("settings");

  return (
    <div className="flex flex-col gap-3">
      <ViewHeader {...meta} />
      <Card padded={false}>
        <div className="px-4">
          <SettingsRow label="Language" hint="Numbers & map stay the same">
            <SegToggle options={["English", "العربية"] as const} value={language} onChange={setLanguage} />
          </SettingsRow>
          <SettingsRow label="Theme">
            <SegToggle options={["Light", "Dark"] as const} value={theme} onChange={setTheme} />
          </SettingsRow>
          <SettingsRow label="Weekly email" hint="Market changes for your areas">
            <SegToggle options={["On", "Off"] as const} value={weeklyEmail} onChange={setWeeklyEmail} />
          </SettingsRow>
          <SettingsRow label="Account" hint="Signed in as Mohammad · your chats are private to you">
            <button
              type="button"
              className="rounded-lg border border-stitch-line bg-stitch-soft px-3 py-2 text-sm text-stitch-muted"
            >
              Sign out
            </button>
          </SettingsRow>
        </div>
      </Card>
    </div>
  );
}
