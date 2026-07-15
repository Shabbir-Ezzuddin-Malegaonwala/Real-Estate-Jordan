import type { ChangeEvent, ReactNode } from "react";
import type { SubjectInput } from "../lib/api";

const VIEW = ["unknown", "none", "city", "garden", "mountain", "panoramic"];
const PARKING = ["unknown", "none", "open", "covered"];
const FINISH = ["unknown", "basic", "standard", "high", "luxury"];
// Residential (apartment/villa) vs commercial — commercial prices higher, and the
// engine uses only same-type comparables, so this materially changes the price.
const PROPERTY_TYPE: [string, string][] = [
  ["apartment", "Apartment · residential"],
  ["villa", "Villa · residential"],
  ["commercial", "Commercial · offices & shops"],
];

// The subject property the builder is pricing. Editing any field recomputes
// (debounced upstream); "Analyze" forces an immediate recompute.
export function SubjectForm({
  subject,
  neighborhoods,
  onPatch,
  onNeighborhood,
  onAnalyze,
  computing,
}: {
  subject: SubjectInput;
  neighborhoods: string[];
  onPatch: (patch: Partial<SubjectInput>) => void;
  onNeighborhood: (nb: string) => void;
  onAnalyze: () => void;
  computing: boolean;
}) {
  const num = (key: keyof SubjectInput) => (e: ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    onPatch({ [key]: v === "" ? undefined : Number(v) } as Partial<SubjectInput>);
  };
  const str = (key: keyof SubjectInput) => (e: ChangeEvent<HTMLSelectElement>) =>
    onPatch({ [key]: e.target.value } as Partial<SubjectInput>);

  return (
    <form
      className="border-b border-line px-4 py-3"
      aria-label="Subject property"
      onSubmit={(e) => {
        e.preventDefault();
        onAnalyze();
      }}
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="label-eyebrow">The home you're pricing</span>
        {computing && <span className="text-2xs text-cyan">working…</span>}
      </div>

      <Field id="f-nbhd" label="Area">
        <select
          id="f-nbhd"
          value={subject.neighborhood}
          onChange={(e) => onNeighborhood(e.target.value)}
          className="input"
        >
          {neighborhoods.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </Field>

      <div className="mt-2">
        <Field id="f-type" label="Property type">
          <select
            id="f-type"
            value={subject.property_type ?? "apartment"}
            onChange={str("property_type")}
            className="input"
          >
            {PROPERTY_TYPE.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className="mt-2 grid grid-cols-2 gap-2">
        <Field id="f-area" label="Size (m²)">
          <input
            id="f-area"
            type="number"
            min={20}
            max={2000}
            inputMode="numeric"
            value={subject.area_m2 ?? ""}
            onChange={num("area_m2")}
            className="input tnum"
          />
        </Field>
        <Field id="f-floor" label="Floor">
          <input
            id="f-floor"
            type="number"
            min={0}
            max={60}
            inputMode="numeric"
            value={subject.floor_level ?? ""}
            onChange={num("floor_level")}
            className="input tnum"
          />
        </Field>
        <Field id="f-beds" label="Bedrooms">
          <input
            id="f-beds"
            type="number"
            min={0}
            max={12}
            inputMode="numeric"
            value={subject.bedrooms ?? ""}
            onChange={num("bedrooms")}
            className="input tnum"
          />
        </Field>
        <Field id="f-age" label="Age (years)">
          <input
            id="f-age"
            type="number"
            min={0}
            max={80}
            inputMode="numeric"
            value={subject.building_age_years ?? ""}
            onChange={num("building_age_years")}
            className="input tnum"
          />
        </Field>
        <Field id="f-view" label="View">
          <select id="f-view" value={subject.view ?? "unknown"} onChange={str("view")} className="input">
            {VIEW.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </Field>
        <Field id="f-parking" label="Parking">
          <select id="f-parking" value={subject.parking ?? "unknown"} onChange={str("parking")} className="input">
            {PARKING.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </Field>
        <Field id="f-finish" label="Finish">
          <select
            id="f-finish"
            value={subject.finish_quality ?? "unknown"}
            onChange={str("finish_quality")}
            className="input"
          >
            {FINISH.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </Field>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={computing || !subject.neighborhood || !subject.area_m2}
            className="h-[30px] w-full rounded-[3px] border border-accent/60 bg-accent/[0.12] text-[12px] font-medium text-accent transition-colors hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {computing ? "Working…" : "Get price"}
          </button>
        </div>
      </div>
    </form>
  );
}

function Field({ id, label, children }: { id: string; label: string; children: ReactNode }) {
  return (
    <label htmlFor={id} className="block">
      <span className="mb-0.5 block text-2xs text-ink-mute">{label}</span>
      {children}
    </label>
  );
}
