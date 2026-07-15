import { useEffect, useRef, useState } from "react";
import type { ChatMessage, Source } from "./types";
import { Message } from "./Message";

// Grouped example prompts — each showcases a different capability.
const SUGGESTION_GROUPS: { label: string; items: string[] }[] = [
  {
    label: "Price a property",
    items: [
      "What would a 180 m², 3-bed apartment near King Abdullah II St, Amman sell for?",
      "Launch price for a 320 m² villa in Dabouq?",
      "Price a 150 m² apartment in Shafa Badran and tell me how confident you are.",
      "What's a high-floor, luxury-finish 200 m² apartment worth in Abdoun?",
    ],
  },
  {
    label: "Compare & decide",
    items: [
      "Is Abdoun a good place to build a mid-size apartment building right now?",
      "Compare Khalda and Dair Ghbar for a builder — which has better launch economics?",
      "Which is cheaper per m² for apartments: Shafa Badran or Marj Al Hamam, and by what %?",
      "In Marj Al Hamam, is it better to build apartments to sell or to rent?",
    ],
  },
  {
    label: "Run the numbers",
    items: [
      "For a 200 m² apartment in Khalda at the recommended price, what's the total sale value?",
      "A Dabouq plot yields 3000 m² of buildable area, cost 560 JD/m² — roughly what could I pay for the land?",
      "What gross rental yield could I expect on an apartment in Sweifieh?",
      "How much higher is Abdoun's premium price than its min-safe price, in percent?",
    ],
  },
  {
    label: "Live market context",
    items: [
      "How have interest rates / the dinar moved this year — does it change the outlook for Sweifieh?",
      "What's the current Central Bank of Jordan policy rate, and how does it affect financing?",
      "Any recent Amman building-permit or real-estate regulation changes I should know about?",
      "Show me a few recent comparable apartment listings in Dabouq.",
    ],
  },
];

export function ChatPanel({
  messages,
  busy,
  onSend,
  onPickSource,
  expanded,
  onToggleExpand,
  onClose,
}: {
  messages: ChatMessage[];
  busy: boolean;
  onSend: (text: string) => void;
  onPickSource: (s: Source) => void;
  expanded: boolean;
  onToggleExpand: () => void;
  onClose?: () => void;
}) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const submit = () => {
    const t = input.trim();
    if (!t || busy) return;
    onSend(t);
    setInput("");
  };

  return (
    <div className="flex h-full flex-col bg-surface">
      <header className="flex items-center justify-between border-b border-line px-4 py-3">
        <div>
          <div className="label-eyebrow">Jordan Real-Estate</div>
          <h1 className="text-[14px] font-semibold text-ink">Grounded Assistant</h1>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden rounded-full border border-line px-2 py-[2px] text-2xs text-ink-mute sm:inline">
            Groq · evidence-backed
          </span>
          <button
            onClick={onToggleExpand}
            title={expanded ? "Exit full screen" : "Expand chat to full screen"}
            aria-label={expanded ? "Exit full screen" : "Expand chat to full screen"}
            className="rounded-[3px] border border-line bg-panel px-2 py-1 text-2xs text-ink-dim hover:border-cyan-dim hover:text-ink"
          >
            {expanded ? "⤡ Exit full screen" : "⤢ Expand"}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              title="Close chat"
              aria-label="Close chat"
              className="grid h-7 w-7 place-items-center rounded-[3px] border border-line bg-panel text-ink-dim hover:border-cyan-dim hover:text-ink"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
                <path d="M6 6l12 12M18 6L6 18" />
              </svg>
            </button>
          )}
        </div>
      </header>

      <div ref={scrollRef} className="scroll-thin flex-1 overflow-y-auto px-4 py-4">
        <div className={`mx-auto space-y-4 ${expanded ? "max-w-3xl" : ""}`}>
          {messages.length === 0 ? (
            <Welcome onPick={onSend} expanded={expanded} />
          ) : (
            messages.map((m) => <Message key={m.id} m={m} onPickSource={onPickSource} />)
          )}
        </div>
      </div>

      <div className="border-t border-line p-3">
        <div className={`mx-auto flex items-end gap-2 ${expanded ? "max-w-3xl" : ""}`}>
          <textarea
            className="input min-h-[40px] resize-none scroll-thin"
            rows={1}
            placeholder="Ask about an address, area, or the market…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit(); // submit() itself no-ops while busy, so this can't send early
              }
            }}
          />
          <button
            onClick={submit}
            disabled={busy || !input.trim()}
            className="shrink-0 rounded-[3px] border border-accent-dim bg-accent/15 px-3 py-2 text-[12px] font-medium text-accent disabled:opacity-40"
          >
            {busy ? "…" : "Send"}
          </button>
        </div>
        <div className="mt-1.5 text-2xs text-ink-faint">
          Every price comes from the pricing engine; current-affairs claims are web-sourced and cited.
        </div>
      </div>
    </div>
  );
}

function Welcome({ onPick, expanded }: { onPick: (t: string) => void; expanded: boolean }) {
  return (
    <div className="space-y-4">
      <div className="card p-3">
        <div className="label-eyebrow mb-1">What this is</div>
        <p className="text-[13px] leading-relaxed text-ink-dim">
          A grounded advisor for building in Jordan. It prices specific addresses and areas with the
          existing decision engine, pulls live context from the web, and shows its evidence. It says
          <span className="text-ink"> "I don't know"</span> rather than guessing.
        </p>
      </div>

      <div className="label-eyebrow">Try an example</div>
      <div className={`grid gap-4 ${expanded ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1"}`}>
        {SUGGESTION_GROUPS.map((group) => (
          <div key={group.label} className="space-y-2">
            <div className="text-2xs font-medium uppercase tracking-[0.12em] text-cyan">{group.label}</div>
            {group.items.map((s) => (
              <button
                key={s}
                onClick={() => onPick(s)}
                className="w-full rounded-[3px] border border-line bg-panel px-3 py-2 text-left text-[12px] leading-snug text-ink-dim hover:border-cyan-dim hover:text-ink"
              >
                {s}
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
