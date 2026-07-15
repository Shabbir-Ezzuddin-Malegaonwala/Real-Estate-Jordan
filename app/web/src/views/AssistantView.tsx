import { useState } from "react";
import { useApp } from "../lib/store";
import type { ChatMessage } from "../lib/store";
import { askAssistant } from "../lib/intel";
import { Card } from "../ui";
import { ViewHeader } from "./ViewHeader";
import { getViewMeta } from "./viewMeta";

function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const isBot = message.role === "bot";
  return (
    <div
      className={`max-w-[88%] rounded-xl px-3 py-2.5 text-sm leading-snug ${
        isBot ? "self-start border border-stitch-line bg-stitch-card text-stitch-ink" : "self-end bg-[#e7f1fb] text-stitch-brand-dark"
      }`}
    >
      {isBot ? `🤖 ${message.text}` : message.text}
    </div>
  );
}

function Composer({ placeholder, onSend, disabled }: { placeholder: string; onSend: (text: string) => void; disabled?: boolean }) {
  const [text, setText] = useState("");
  function submit() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  }
  return (
    <div className="mt-2 flex gap-2">
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        placeholder={placeholder}
        className="flex-1 rounded-lg border border-stitch-line bg-stitch-card px-3 py-2.5 text-sm"
      />
      <button type="button" onClick={submit} disabled={disabled} className="rounded-lg bg-stitch-brand px-4 text-sm font-bold text-white disabled:opacity-40">
        Send
      </button>
    </div>
  );
}

function Thinking() {
  return <div className="max-w-[88%] self-start rounded-xl border border-stitch-line bg-stitch-card px-3 py-2.5 text-sm text-stitch-muted">🤖 Checking the market data…</div>;
}

export function AssistantView() {
  const { state, openChat, addMessage, setView } = useApp();
  const { view, chats, openChatId, selectedArea, language } = state;
  const [pending, setPending] = useState(false);

  // Ask the grounded assistant (real facts, explain-only). Adds the user's message,
  // shows a thinking state, then appends the answer (or an honest failure line).
  async function send(text: string, transition = false) {
    addMessage({ role: "user", text });
    if (transition) setView("chatopen");
    setPending(true);
    const res = await askAssistant(text, selectedArea, language);
    setPending(false);
    const answer = res?.answer
      || (res && !res.llm_available
        ? "The assistant isn't connected to a language model yet — add a key and I'll answer from the live data."
        : "I couldn't reach the market data just now — please try again.");
    addMessage({ role: "bot", text: answer });
  }

  if (view === "chathist") {
    const meta = getViewMeta("chathist");
    return (
      <div className="flex flex-col gap-3">
        <ViewHeader {...meta} />
        {chats.length === 0 ? (
          <Card>
            <div className="text-sm text-stitch-muted">No chats yet — start one from &quot;New chat&quot;.</div>
          </Card>
        ) : (
          <div className="flex flex-col gap-2">
            {chats.map((c) => (
              <Card key={c.id} padded={false} className="hover:border-stitch-brand">
                <button type="button" onClick={() => openChat(c.id)} className="w-full px-4 py-3 text-left">
                  <div className="text-sm font-semibold text-stitch-ink">{c.title}</div>
                  <div className="mt-0.5 text-xs text-stitch-muted">{formatWhen(c.when)}</div>
                </button>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (view === "chatopen") {
    const session = chats.find((c) => c.id === openChatId);
    if (!session) {
      return (
        <Card>
          <div className="text-sm text-stitch-muted">Chat not found.</div>
        </Card>
      );
    }
    return (
      <div className="flex flex-col gap-3">
        <ViewHeader
          category="Assistant"
          crumbExtra={
            <>
              {" "}·{" "}
              <button type="button" onClick={() => setView("chathist")} className="cursor-pointer text-stitch-brand">history</button>
            </>
          }
          title={session.title}
        />
        <div className="flex max-h-[55vh] flex-col gap-2.5 overflow-y-auto pr-1">
          {session.messages.map((m, i) => (
            <ChatBubble key={i} message={m} />
          ))}
          {pending && <Thinking />}
        </div>
        <Composer placeholder={selectedArea ? `Ask about ${selectedArea}…` : "Continue this chat…"} onSend={(t) => send(t)} disabled={pending} />
      </div>
    );
  }

  // chatnew — empty conversation + input; sending transitions into chatopen.
  const meta = getViewMeta("chatnew");
  return (
    <div className="flex flex-col gap-3">
      <ViewHeader {...meta} />
      <div className="flex max-h-[55vh] flex-col gap-2.5 overflow-y-auto pr-1">
        <ChatBubble
          message={{
            role: "bot",
            text: selectedArea
              ? `Ask me about ${selectedArea} — price, comparables, land, or the market. I answer from real data and never invent numbers.`
              : "Pick an area (search or map) then ask me about its price, comparables, land, or market. I answer from real data and never invent numbers.",
          }}
        />
        {pending && <Thinking />}
      </div>
      <Composer placeholder="Ask a question…" onSend={(t) => send(t, true)} disabled={pending} />
    </div>
  );
}
