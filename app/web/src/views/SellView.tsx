import { useState } from "react";
import { useApp } from "../lib/store";
import { requestPropertyValuation, type ValuationResult } from "../lib/intel";
import { Card } from "../ui";

type Mode = "building" | "flat";
type Finish = "basic" | "standard" | "high";
type Lang = "en" | "ar";

const field = "w-full rounded-md border border-stitch-soft px-2.5 py-1.5 text-sm text-stitch-ink focus:border-stitch-brand focus:outline-none";
const label = "mb-1 block text-[11px] font-semibold uppercase tracking-wide text-stitch-muted";
const jd = (n?: number) => (n == null ? "—" : n.toLocaleString());

// "Value my property" (Pricing): the seller drops a pin on their building (map),
// describes it, and gets a comparable-based valuation + itemised breakdown +
// explain-only narration. The pin lives in the store (set by MapRegion's marker).
export function SellView() {
  const { state } = useApp();
  const pin = state.sellPin; // [lng, lat]
  const [mode, setMode] = useState<Mode>("building");
  const [lang, setLang] = useState<Lang>(state.language); // default from Settings
  const [totalArea, setTotalArea] = useState(600);
  const [flats, setFlats] = useState(4);
  const [flatArea, setFlatArea] = useState(175);
  const [plot, setPlot] = useState(500);
  const [finish, setFinish] = useState<Finish>("standard");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ValuationResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    if (!pin) return;
    setLoading(true);
    setErr(null);
    setResult(null);
    const r = await requestPropertyValuation({
      lng: pin[0], lat: pin[1], total_area_m2: totalArea, finish, mode, language: lang,
      flats: mode === "building" ? flats : undefined,
      flat_area_m2: mode === "flat" ? flatArea : undefined,
      plot_area_m2: mode === "building" ? plot : undefined,
    });
    setLoading(false);
    if (!r) return setErr("Couldn't reach the valuation service. Is the API running?");
    if (!r.ok) return setErr(r.reason || "No comparable sales near this pin — try moving it.");
    setResult(r);
  }

  return (
    <div className="flex flex-col gap-3">
      <Card>
        <div className="text-xs font-semibold uppercase tracking-wide text-stitch-muted">Step 1 · Location</div>
        {pin ? (
          <p className="mt-1 text-[13px] text-stitch-ink">
            📍 Pin set at <b>{pin[1].toFixed(5)}, {pin[0].toFixed(5)}</b>. Drag the marker on the map to your exact building.
          </p>
        ) : (
          <p className="mt-1 text-[13px] leading-relaxed text-stitch-muted">
            Drag the <b>📍 marker</b> on the map onto your building (search an area first to jump there),
            then fill in the details below.
          </p>
        )}
      </Card>

      <Card>
        <div className="text-xs font-semibold uppercase tracking-wide text-stitch-muted">Step 2 · Your property</div>

        <div className="mt-2">
          <span className={label}>What are you valuing?</span>
          <div className="flex gap-2">
            {(["building", "flat"] as Mode[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={`flex-1 rounded-md border px-2 py-1.5 text-sm font-semibold ${mode === m ? "border-stitch-brand bg-stitch-brand/10 text-stitch-brand-dark" : "border-stitch-soft text-stitch-muted"}`}
              >
                {m === "building" ? "Whole building" : "One flat"}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-3">
          <div>
            <label className={label} htmlFor="v-area">{mode === "flat" ? "Flat area (m²)" : "Total built-up (m²)"}</label>
            <input id="v-area" type="number" min={30} className={field}
              value={mode === "flat" ? flatArea : totalArea}
              onChange={(e) => (mode === "flat" ? setFlatArea : setTotalArea)(Number(e.target.value) || 0)} />
          </div>
          <div>
            <label className={label} htmlFor="v-finish">Finishing quality</label>
            <select id="v-finish" className={field} value={finish} onChange={(e) => setFinish(e.target.value as Finish)}>
              <option value="basic">Basic</option>
              <option value="standard">Standard</option>
              <option value="high">High</option>
            </select>
          </div>
          {mode === "building" && (
            <>
              <div>
                <label className={label} htmlFor="v-flats"># Flats</label>
                <input id="v-flats" type="number" min={1} className={field} value={flats} onChange={(e) => setFlats(Number(e.target.value) || 1)} />
              </div>
              <div>
                <label className={label} htmlFor="v-plot">Plot size (m²)</label>
                <input id="v-plot" type="number" min={0} className={field} value={plot} onChange={(e) => setPlot(Number(e.target.value) || 0)} />
              </div>
            </>
          )}
        </div>

        <div className="mt-3 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-stitch-muted">Report in</span>
            {(["en", "ar"] as Lang[]).map((l) => (
              <button key={l} type="button" onClick={() => setLang(l)}
                className={`rounded px-2 py-0.5 text-xs font-semibold ${lang === l ? "bg-stitch-brand text-white" : "text-stitch-muted"}`}>
                {l === "en" ? "English" : "عربي"}
              </button>
            ))}
          </div>
          <button type="button" disabled={!pin || loading} onClick={submit}
            className="rounded-md bg-stitch-brand px-4 py-1.5 text-sm font-semibold text-white disabled:opacity-40">
            {loading ? "Valuing…" : "Value my property"}
          </button>
        </div>
        {!pin && <p className="mt-2 text-[12px] text-stitch-muted">Drop the pin on the map to enable valuation.</p>}
        {err && <p className="mt-2 text-[12.5px] text-red-600">{err}</p>}
      </Card>

      {result && result.ok && <Results r={result} lang={lang} />}
    </div>
  );
}

function Results({ r, lang }: { r: ValuationResult; lang: Lang }) {
  const cb = r.cost_breakdown ?? {};
  return (
    <>
      <div className="rounded-xl bg-gradient-to-br from-stitch-brand-dark to-stitch-brand px-4 py-3.5 text-white">
        <div className="text-[13px] text-white/90">Estimated {r.mode === "flat" ? "flat" : "building"} value · {r.nearest_area}</div>
        <div className="mt-0.5 text-3xl font-extrabold">{jd(r.estimated_value_jd)} <span className="text-base font-semibold">JD</span></div>
        <div className="mt-0.5 text-[13px] text-white/90">
          {jd(r.value_per_m2)} JD/m² · range {jd(r.value_low_jd)}–{jd(r.value_high_jd)} JD · {r.comps} comparable sales
        </div>
      </div>

      {r.mode === "building" && r.per_flat_value_jd != null && (
        <Card>
          <div className="text-xs font-semibold uppercase tracking-wide text-stitch-muted">If sold as {r.flats} separate flats</div>
          <div className="mt-1 text-xl font-extrabold text-stitch-brand-dark">{jd(r.per_flat_value_jd)} <span className="text-sm font-semibold text-stitch-muted">JD each</span></div>
          <p className="mt-0.5 text-[12.5px] text-stitch-muted">Selling flats individually usually totals more than one bulk sale.</p>
        </Card>
      )}

      <Card>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-stitch-muted">What makes up the value</div>
        <div className="grid grid-cols-3 gap-2 text-center">
          <Tile label="Construction" value={cb.construction_jd} sub={cb.construction_per_m2 ? `${cb.construction_per_m2}/m²` : undefined} />
          <Tile label="Land" value={cb.land_jd} sub={cb.land_per_m2 ? `${cb.land_per_m2}/m²` : undefined} />
          <Tile label={`Transfer tax${cb.transfer_tax_pct ? ` ${cb.transfer_tax_pct}%` : ""}`} value={cb.transfer_tax_jd} />
        </div>
      </Card>

      <Card>
        <div className="mb-1 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wide text-stitch-muted">Summary</span>
          {r.narration && r.llm_available && <span className="text-[10px] font-bold text-stitch-brand">AI</span>}
        </div>
        <p dir={r.narration && lang === "ar" ? "rtl" : "ltr"} className="text-[13px] leading-relaxed text-stitch-ink">
          {r.narration ??
            `Based on ${r.comps} nearby sales in ${r.nearest_area}, your ${r.mode === "flat" ? "flat" : "building"} is worth about ${jd(r.estimated_value_jd)} JD (${jd(r.value_per_m2)} JD/m²), within a ${jd(r.value_low_jd)}–${jd(r.value_high_jd)} JD range.`}
        </p>
      </Card>
      <p className="px-1 text-[11px] leading-relaxed text-stitch-muted">
        Comparable-based estimate from asking prices calibrated to transaction level — decision support, not a formal valuation.
      </p>
    </>
  );
}

function Tile({ label, value, sub }: { label: string; value?: number; sub?: string }) {
  return (
    <div className="rounded-lg bg-stitch-soft px-2 py-2">
      <div className="text-[15px] font-extrabold text-stitch-ink">{value == null ? "—" : value.toLocaleString()}</div>
      {sub && <div className="text-[10px] text-stitch-muted">{sub}</div>}
      <div className="mt-0.5 text-[10.5px] font-semibold text-stitch-muted">{label}</div>
    </div>
  );
}
