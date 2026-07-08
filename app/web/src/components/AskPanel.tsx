import { useState } from "react";

// Scaffolded natural-language entry. The retrieval-grounded AI backend + LLM key
// are not wired yet, so this NEVER fabricates an answer — it captures the
// question and states plainly that the assistant is coming, pointing the user to
// the evidence already on screen. Wire to POST /ask when the AI service lands.
export function AskPanel({ area }: { area: string | null }) {
  const [q, setQ] = useState("");
  const [submitted, setSubmitted] = useState<string | null>(null);

  return (
    <section className="px-4 pt-5" aria-label="Ask the assistant">
      <div className="mb-2 flex items-center gap-2">
        <span className="inline-block h-3 w-[3px] rounded-full bg-cyan" aria-hidden />
        <h3 className="text-[13px] font-semibold text-ink">Ask</h3>
        <span className="label-eyebrow ml-auto">assistant · coming soon</span>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (q.trim()) setSubmitted(q.trim());
        }}
        className="card p-2.5"
      >
        <label htmlFor="ask-input" className="sr-only">
          Ask a question about this area
        </label>
        <textarea
          id="ask-input"
          rows={2}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={
            area
              ? `Ask about ${area} — "why this price?", "is it safe to build here?"…`
              : `Ask — "which area has the best upside?"…`
          }
          className="input resize-none"
        />
        <div className="mt-2 flex items-center justify-between">
          <span className="text-2xs text-ink-faint">Grounded in our DB + sources (not live yet)</span>
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
            <span className="font-medium text-ink">Noted:</span> “{submitted}”. The retrieval-grounded
            assistant that answers with sources (and can run the pricing engine as a tool) is being
            wired next — it will never guess. For now, the evidence and adjustment breakdown on this
            panel answer the “why” directly.
          </p>
        </div>
      )}
    </section>
  );
}
