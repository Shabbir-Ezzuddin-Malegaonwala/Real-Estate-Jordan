import { useCallback, useMemo, useRef, useState } from "react";
import { ChatPanel } from "./ChatPanel";
import { streamChat } from "./chatClient";
import type { ChatMessage, Source, StreamEvent } from "./types";

// Self-contained grounded-assistant widget: a floating button that opens a
// right-docked chat drawer. All streaming/session state lives here so the rest
// of the app is untouched — mount <ChatWidget/> once at the app root.
//
// The chat talks to the standalone assistant service (app/assistant/server.py)
// on :8100 via streamChat(). Prices come from the pricing engine; current-affairs
// claims are web-sourced and cited.

function newSessionId(): string {
  return `s-${Date.now().toString(36)}-${Math.floor(Math.random() * 1e6).toString(36)}`;
}

let idCounter = 0;
const nextId = () => `m-${idCounter++}`;

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const sessionId = useMemo(newSessionId, []);
  const abortRef = useRef<AbortController | null>(null);

  const onPickSource = useCallback((_s: Source) => {
    // Map-driving is not wired in the recommendation app; chips stay informative.
  }, []);

  const send = useCallback(
    async (text: string) => {
      if (busy) return;
      setBusy(true);
      const userMsg: ChatMessage = {
        id: nextId(), role: "user", text, activities: [], sources: [], engineResults: [], streaming: false,
      };
      const asstId = nextId();
      const asstMsg: ChatMessage = {
        id: asstId, role: "assistant", text: "", activities: [], sources: [], engineResults: [], streaming: true,
      };
      setMessages((prev) => [...prev, userMsg, asstMsg]);

      const patch = (fn: (m: ChatMessage) => ChatMessage) =>
        setMessages((prev) => prev.map((m) => (m.id === asstId ? fn(m) : m)));

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      const onEvent = (e: StreamEvent) => {
        switch (e.type) {
          case "token":
            patch((m) => ({ ...m, text: m.text + e.text }));
            break;
          case "tool_start":
            patch((m) => ({ ...m, activities: [...m.activities, { tool: e.tool, label: e.label, done: false }] }));
            break;
          case "tool_end":
            patch((m) => {
              const acts = [...m.activities];
              for (let i = acts.length - 1; i >= 0; i--) {
                if (acts[i].tool === e.tool && !acts[i].done) {
                  acts[i] = { ...acts[i], done: true, ok: e.ok, sql: e.sql };
                  break;
                }
              }
              const engineResults = e.engine_result ? [...m.engineResults, e.engine_result] : m.engineResults;
              return { ...m, activities: acts, engineResults };
            });
            break;
          case "done":
            patch((m) => ({ ...m, sources: e.sources ?? [], streaming: false }));
            break;
          case "error":
            patch((m) => ({ ...m, error: e.message, streaming: false }));
            break;
          case "status":
          default:
            break;
        }
      };

      try {
        await streamChat(sessionId, text, onEvent, ctrl.signal);
      } catch (err) {
        patch((m) => ({ ...m, error: `Connection error: ${(err as Error).message}`, streaming: false }));
      } finally {
        patch((m) => ({ ...m, streaming: false }));
        setBusy(false);
        abortRef.current = null;
      }
    },
    [busy, sessionId],
  );

  // Closed: show the launcher button only.
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open the grounded assistant"
        title="Ask the grounded assistant"
        className="fixed bottom-5 right-5 z-[60] flex items-center gap-2 rounded-full border border-accent-dim bg-accent px-4 py-3 text-[13px] font-semibold text-base shadow-lg shadow-black/30 transition-transform hover:scale-[1.03]"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M21 15a2 2 0 0 1-2 2H8l-4 4V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2Z" />
          <path d="M8 10h.01M12 10h.01M16 10h.01" />
        </svg>
        Assistant
      </button>
    );
  }

  // Open: right-docked drawer (or full-screen overlay when expanded).
  return (
    <div
      className={
        expanded
          ? "fixed inset-0 z-[70] bg-surface"
          : "fixed inset-y-0 right-0 z-[60] w-[420px] max-w-[92vw] border-l border-line bg-surface shadow-2xl shadow-black/40"
      }
      role="dialog"
      aria-label="Grounded assistant"
    >
      <ChatPanel
        messages={messages}
        busy={busy}
        onSend={send}
        onPickSource={onPickSource}
        expanded={expanded}
        onToggleExpand={() => setExpanded((v) => !v)}
        onClose={() => setOpen(false)}
      />
    </div>
  );
}
