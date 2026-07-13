import { useState } from "react";
import type { RecommendationResult, EvidenceObject } from "../types";
import { jd } from "../lib/format";
import { SourceChip } from "./SourceChip";

// The explainability centerpiece (MASTER-PLAN §2d, §6): reconciled comparable
// base → each market-evidenced adjustment (with method, confidence, source
// chips) → the concluded launch band.
//
// Two honest render modes, chosen from the data — the component never fabricates
// a total:
//  • "cascade" — when every current-state adjustment is a plain multiplicative
//    percentage (the internally-consistent bundle): base × Π(1+pct) reconciles
//    to the recommendation, so a running column is shown.
//  • "grid"    — real-engine output, where premiums were applied per comparable
//    during reconciliation and cross-check anchors (cost floor, income ceiling,
//    competitor median) are absolute, not additive. The evidenced premiums are
//    shown without a misleading cumulative, and anchors sit in a cross-check row.
export function AdjustmentWaterfall({ r }: { r: RecommendationResult }) {
  const current = r.evidence_objects.filter((e) => e.category === "current_state");
  const pctRows = current.filter((e) => (e.kind ?? "pct") === "pct");
  const anchors = current.filter((e) => e.kind === "anchor");
  const contextRows = current.filter((e) => e.kind === "context");
  const [open, setOpen] = useState<string | null>(null);
  const toggle = (k: string) => setOpen((v) => (v === k ? null : k));

  const cascades =
    anchors.length === 0 &&
    pctRows.length > 0 &&
    pctRows.every((e) => !e.per_unit) &&
    r.base_value_jd_m2 > 0;

  return (
    <section className="px-4 pt-5" aria-label="Adjustment waterfall">
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-[13px] font-semibold text-ink">Adjustment Waterfall</h3>
        <span className="text-2xs text-ink-mute">
          {pctRows.length} adjustments · expand any row
        </span>
      </div>

      <div className="card overflow-hidden">
        <div className="flex items-center justify-between bg-surface/40 px-2.5 py-2 text-[12px]">
          <span className="text-ink-dim">
            Base — {cascades ? "neighbourhood median" : "reconciled comparable base (asking)"}
          </span>
          <span className="tnum text-ink">{jd(r.base_value_jd_m2)}</span>
        </div>

        {cascades
          ? <CascadeRows base={r.base_value_jd_m2} rows={pctRows} open={open} toggle={toggle} />
          : pctRows.map((e) => <GridRow key={e.factor} ev={e} open={open === e.factor} onToggle={() => toggle(e.factor)} />)}

        {anchors.length > 0 && <AnchorBlock anchors={anchors} />}

        {contextRows.length > 0 && <ContextBlock rows={contextRows} />}

        {/* Concluded — always the engine's authoritative band */}
        <div className="border-t border-accent/30 bg-accent/[0.06]">
          <div className="flex items-center justify-between px-2.5 py-2.5">
            <span className="text-[12px] font-semibold text-accent">Concluded — Recommended</span>
            <span className="tnum text-[15px] font-medium text-accent">
              {jd(r.recommended_jd_m2)} <span className="text-2xs text-accent/70">JD/m²</span>
            </span>
          </div>
          <div className="flex items-center justify-between border-t border-accent/15 px-2.5 py-1.5 text-2xs tnum text-ink-mute">
            <span>Min safe {jd(r.min_safe_jd_m2)}</span>
            <span className="text-ink-faint">evidenced band</span>
            <span>Premium {jd(r.premium_jd_m2)}</span>
          </div>
        </div>
      </div>
    </section>
  );
}

// --- cascade mode (consistent bundle) --------------------------------------
function CascadeRows({
  base, rows, open, toggle,
}: { base: number; rows: EvidenceObject[]; open: string | null; toggle: (k: string) => void }) {
  let running = base;
  const steps = rows.map((ev) => {
    const delta = running * ev.adjustment_pct;
    running += delta;
    return { ev, delta, running };
  });
  const maxDelta = Math.max(1, ...steps.map((s) => Math.abs(s.delta)));

  return (
    <>
      {steps.map((s) => {
        const isOpen = open === s.ev.factor;
        return (
          <div key={s.ev.factor} className="border-t border-line-soft">
            <button
              type="button"
              onClick={() => toggle(s.ev.factor)}
              aria-expanded={isOpen}
              className="grid w-full grid-cols-[1fr_auto] items-start gap-2 px-2.5 py-2 text-left transition-colors hover:bg-raised/40"
            >
              <div className="min-w-0">
                <FactorHead ev={s.ev} open={isOpen} />
                <MagnitudeBar frac={s.delta / maxDelta} />
                <div className="mt-1 text-2xs text-ink-mute">{s.ev.method}</div>
              </div>
              <div className="text-right">
                <div className={`tnum text-[12px] ${s.delta >= 0 ? "text-pos" : "text-neg"}`}>
                  {s.delta >= 0 ? "+" : "−"}
                  {jd(Math.abs(s.delta))}
                </div>
                <div className="tnum mt-1 text-[12px] text-ink-dim">{jd(s.running)}</div>
                <div className="mt-1 text-2xs uppercase tracking-wide text-ink-faint">{s.ev.confidence}</div>
              </div>
            </button>
            {isOpen && <EvidenceDetail ev={s.ev} />}
          </div>
        );
      })}
    </>
  );
}

// --- grid mode (real engine) -----------------------------------------------
function GridRow({ ev, open, onToggle }: { ev: EvidenceObject; open: boolean; onToggle: () => void }) {
  return (
    <div className="border-t border-line-soft">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="grid w-full grid-cols-[1fr_auto] items-start gap-2 px-2.5 py-2 text-left transition-colors hover:bg-raised/40"
      >
        <div className="min-w-0">
          <FactorHead ev={ev} open={open} />
          {ev.adjustment_pct !== 0 && <MagnitudeBar frac={ev.adjustment_pct} />}
          <div className="mt-1 text-2xs text-ink-mute">{ev.method}</div>
        </div>
        <div className="text-right">
          <div
            className={`tnum text-[12px] ${
              ev.direction === "increase"
                ? "text-pos"
                : ev.direction === "decrease"
                  ? "text-neg"
                  : "text-ink-dim"
            }`}
          >
            {ev.adjustment}
          </div>
          <div className="mt-1 text-2xs uppercase tracking-wide text-ink-faint">{ev.confidence}</div>
        </div>
      </button>
      {open && <EvidenceDetail ev={ev} />}
    </div>
  );
}

// The drill-down behind any adjustment: full rationale, datasets, and every
// supporting source. This is the "show me the evidence" contract made literal.
function EvidenceDetail({ ev }: { ev: EvidenceObject }) {
  return (
    <div className="border-t border-line-soft bg-surface/40 px-2.5 py-2.5">
      <p className="text-2xs leading-relaxed text-ink-dim">{ev.explanation}</p>
      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-2xs">
        <span className="text-ink-faint">method</span>
        <span className="text-ink-mute">{ev.method}</span>
        <span className="text-ink-faint">·</span>
        <span className="uppercase tracking-wide text-ink-mute">{ev.confidence} confidence</span>
      </div>
      {ev.datasets.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {ev.datasets.map((d) => (
            <span key={d} className="rounded-[2px] border border-line bg-raised px-1.5 py-[1px] text-2xs text-ink-mute">
              {d}
            </span>
          ))}
        </div>
      )}
      <div className="mt-1.5 flex flex-wrap gap-1">
        {ev.sources.map((s, i) => (
          <SourceChip key={i} source={s} variable={ev.factor} />
        ))}
      </div>
    </div>
  );
}

function AnchorBlock({ anchors }: { anchors: EvidenceObject[] }) {
  return (
    <div className="border-t border-line bg-surface/30 px-2.5 py-2">
      <div className="mb-1.5 text-2xs uppercase tracking-wide text-ink-mute">
        Method cross-checks · triangulation (not additive)
      </div>
      <div className="space-y-1.5">
        {anchors.map((a) => (
          <div key={a.factor} className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <span className="text-[12px] text-ink">{a.factor}</span>
              <div className="mt-0.5 flex flex-wrap gap-1">
                {a.sources.map((s, i) => (
                  <SourceChip key={i} source={s} variable={a.factor} />
                ))}
              </div>
            </div>
            <span className="tnum shrink-0 text-[12px] text-cyan">{a.adjustment}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Non-priced "market texture" rows — informational only, never a +/− adjustment.
function ContextBlock({ rows }: { rows: EvidenceObject[] }) {
  return (
    <div className="border-t border-line bg-surface/30 px-2.5 py-2">
      <div className="mb-1.5 text-2xs uppercase tracking-wide text-ink-mute">
        Context · market texture (not priced)
      </div>
      <div className="space-y-2">
        {rows.map((c) => (
          <div key={c.factor}>
            <div className="flex items-center gap-2">
              <span className="shrink-0 rounded-[2px] border border-line bg-raised px-1.5 py-[1px] text-2xs uppercase tracking-wide text-ink-mute">
                Context
              </span>
              <span className="text-[12px] text-ink-dim">{c.factor}</span>
            </div>
            <p className="mt-1 text-2xs leading-relaxed text-ink-mute">{c.explanation}</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {c.sources.map((s, i) => (
                <SourceChip key={i} source={s} variable={c.factor} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- shared row parts ------------------------------------------------------
function FactorHead({ ev, open }: { ev: EvidenceObject; open?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span aria-hidden className={`shrink-0 text-2xs text-ink-faint transition-transform ${open ? "rotate-90" : ""}`}>
        ▸
      </span>
      <span className="truncate text-[12px] text-ink">{ev.factor}</span>
      {ev.per_unit && <span className="shrink-0 text-2xs text-ink-faint">per unit</span>}
    </div>
  );
}

function MagnitudeBar({ frac }: { frac: number }) {
  const clamped = Math.max(-1, Math.min(1, frac));
  return (
    <div className="relative mt-1 h-1.5 w-full overflow-hidden rounded-full bg-raised">
      <div className="absolute left-1/2 top-0 h-full w-px bg-line" aria-hidden />
      <div
        className={`absolute top-0 h-full ${clamped >= 0 ? "bg-pos/70" : "bg-neg/70"}`}
        style={{
          left: clamped >= 0 ? "50%" : undefined,
          right: clamped < 0 ? "50%" : undefined,
          width: `${Math.abs(clamped) * 50}%`,
        }}
        aria-hidden
      />
    </div>
  );
}
