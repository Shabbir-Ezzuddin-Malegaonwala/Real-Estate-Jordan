import { useEffect, useState } from "react";
import { useApp } from "../lib/store";
import { DEFAULT_SUBJECT, type Subject } from "../lib/contract";

const FINISH_LABEL: Record<Subject["finish_quality"], string> = {
  basic: "Basic",
  standard: "Standard",
  high: "High",
};

function summary(s: Subject): string {
  return `${s.area_m2} m² · ${s.bedrooms} bed · floor ${s.floor_level} · ${FINISH_LABEL[s.finish_quality]} finish`;
}

function isDefault(s: Subject): boolean {
  return (
    s.area_m2 === DEFAULT_SUBJECT.area_m2 &&
    s.bedrooms === DEFAULT_SUBJECT.bedrooms &&
    s.floor_level === DEFAULT_SUBJECT.floor_level &&
    s.finish_quality === DEFAULT_SUBJECT.finish_quality
  );
}

const numberField = "w-full rounded-md border border-stitch-soft px-2 py-1.5 text-sm text-stitch-ink focus:border-stitch-brand focus:outline-none";
const labelText = "mb-1 block text-[11px] font-semibold uppercase tracking-wide text-stitch-muted";

// The unit the price is FOR. Collapsed by default (the default unit is a sane
// representative); expanding lets the developer price their own size/beds/floor/
// finish, which reprices the whole area (setSubject → /recommend). Commit-on-Apply
// so we don't refetch on every keystroke.
export function SubjectBar() {
  const { state, setSubject } = useApp();
  const applied = state.subject;
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Subject>(applied);

  // Keep the draft in sync if the applied subject changes elsewhere (e.g. reset).
  useEffect(() => setDraft(applied), [applied]);

  const dirty =
    draft.area_m2 !== applied.area_m2 ||
    draft.bedrooms !== applied.bedrooms ||
    draft.floor_level !== applied.floor_level ||
    draft.finish_quality !== applied.finish_quality;

  const customised = !isDefault(applied);

  return (
    <div className="rounded-xl border border-stitch-soft bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-4 py-2.5 text-left"
      >
        <span className="min-w-0">
          <span className="text-[11px] font-semibold uppercase tracking-wide text-stitch-muted">Apartment we're pricing</span>
          <span className="mt-0.5 block truncate text-[13px] font-semibold text-stitch-ink">{summary(applied)}</span>
        </span>
        <span className="flex flex-none items-center gap-2">
          {customised && (
            <span className="rounded-full bg-stitch-brand/10 px-2 py-0.5 text-[10px] font-bold text-stitch-brand-dark">
              CUSTOM
            </span>
          )}
          <span className="text-[12px] font-semibold text-stitch-brand">{open ? "Close" : "Customise"}</span>
        </span>
      </button>

      {open && (
        <div className="border-t border-stitch-soft px-4 py-3">
          <p className="mb-2 text-[12px] leading-relaxed text-stitch-muted">
            These are the details of one apartment (the type you'd build and sell). Change them and the price updates for that apartment.
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelText} htmlFor="subj-size">Size (m²)</label>
              <input
                id="subj-size"
                type="number"
                min={40}
                max={1000}
                value={draft.area_m2}
                onChange={(e) => setDraft({ ...draft, area_m2: Number(e.target.value) || 0 })}
                className={numberField}
              />
            </div>
            <div>
              <label className={labelText} htmlFor="subj-beds">Bedrooms</label>
              <select
                id="subj-beds"
                value={draft.bedrooms}
                onChange={(e) => setDraft({ ...draft, bedrooms: Number(e.target.value) })}
                className={numberField}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelText} htmlFor="subj-floor">Floor</label>
              <input
                id="subj-floor"
                type="number"
                min={0}
                max={40}
                value={draft.floor_level}
                onChange={(e) => setDraft({ ...draft, floor_level: Number(e.target.value) || 0 })}
                className={numberField}
              />
            </div>
            <div>
              <label className={labelText} htmlFor="subj-finish">Finishing quality</label>
              <select
                id="subj-finish"
                value={draft.finish_quality}
                onChange={(e) => setDraft({ ...draft, finish_quality: e.target.value as Subject["finish_quality"] })}
                className={numberField}
              >
                <option value="basic">Basic</option>
                <option value="standard">Standard</option>
                <option value="high">High</option>
              </select>
            </div>
          </div>

          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              disabled={!dirty}
              onClick={() => { setSubject(draft); setOpen(false); }}
              className="rounded-md bg-stitch-brand px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-40"
            >
              Apply &amp; reprice
            </button>
            {customised && (
              <button
                type="button"
                onClick={() => { setSubject({ ...DEFAULT_SUBJECT }); setOpen(false); }}
                className="text-[12.5px] font-semibold text-stitch-muted hover:underline"
              >
                Reset to default
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
