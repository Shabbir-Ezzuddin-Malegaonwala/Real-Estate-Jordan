import { useState } from "react";

// Dashboard-first AI copilot — scaffolded, not faked. Framed with the trust rule
// so expectations are honest: it will be grounded in our data and will say "I
// don't know" when the evidence isn't there. Wire to the grounded assistant
// endpoint when the LLM service + key land.
export function Copilot({ area }: { area: string | null }) {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState<string | null>(null);

  return (
    <section className="border-t border-line px-4 py-4" aria-label="AI copilot">
      <div className="mb-2 flex items-center gap-2">
        <span className="inline-block h-3 w-[3px] rounded-full bg-cyan" aria-hidden />
        <h3 className="text-[13px] font-semibold text-ink">Copilot</h3>
        <span className="label-eyebrow ml-auto">grounded · coming soon</span>
      </div>

      <div className="mb-2 rounded-[3px] border border-cyan/30 bg-cyan/[0.05] px-2.5 py-1.5">
        <p className="text-2xs leading-relaxed text-ink-dim">
          Grounded in our data — if the evidence isn't there, it says <span className="font-medium text-ink">"I don't know"</span>. No guessing.
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (q.trim()) setSubmitted(q.trim());
        }}
        className="card p-2.5"
      >
        <label htmlFor="copilot-input" className="sr-only">Ask the copilot</label>
        <textarea
          id="copilot-input"
          rows={2}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={area ? `Ask about ${area} — "why this price?", "is it safe to build here?"…` : `Ask — "which area has the best upside?"…`}
          className="input resize-none"
        />
        <div className="mt-2 flex items-center justify-between">
          <span className="text-2xs text-ink-faint">Runs the pricing engine as a tool · cites sources</span>
          <button
            type="submit"
            disabled={!q.trim()}
            aria-label="Send question"
            className="rounded-[3px] border border-cyan/50 bg-cyan/10 px-3 py-1 text-2xs font-medium text-cyan transition-colors hover:bg-cyan/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </form>

      {submitted && (
        <div className="mt-2 rounded-[3px] border border-dashed border-line bg-panel p-2.5">
          <p className="text-2xs leading-relaxed text-ink-dim">
            <span className="font-medium text-ink">Noted:</span> “{submitted}”. The grounded assistant
            (retrieval over our DB + the pricing engine as a callable tool, every answer sourced) is
            being wired next — it will never guess. For now, the step panels answer the “why” directly.
          </p>
        </div>
      )}
    </section>
  );
}
