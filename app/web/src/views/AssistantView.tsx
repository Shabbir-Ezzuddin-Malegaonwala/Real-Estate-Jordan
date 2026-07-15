import { useEffect, useRef, useState } from "react";
import { useApp } from "../lib/store";
import type { ChatMessage } from "../lib/store";
import { askAssistant } from "../lib/intel";
import { Card } from "../ui";
import { ViewHeader } from "./ViewHeader";
import { getViewMeta } from "./viewMeta";

function formatWhen(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function hostOf(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; }
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const isBot = message.role === "bot";
  return (
    <div
      className={`max-w-[88%] rounded-xl px-3 py-2.5 text-sm leading-snug ${
        isBot ? "self-start border border-stitch-line bg-stitch-card text-stitch-ink" : "self-end bg-[#e7f1fb] text-stitch-brand-dark"
      }`}
    >
      {isBot && message.fromInternet && (
        <span className="mb-1 inline-block rounded bg-[#fdf0dd] px-1.5 py-0.5 text-[10px] font-bold uppercase text-[#b06a1a]">🌐 from the web</span>
      )}
      <div>{isBot ? `🤖 ${message.text}` : message.text}</div>
      {isBot && message.sources && message.sources.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-x-2 gap-y-0.5 text-[11px]">
          {message.sources.map((u, i) => (
            <a key={i} href={u} target="_blank" rel="noreferrer" className="text-stitch-brand hover:underline">{hostOf(u)}</a>
          ))}
        </div>
      )}
    </div>
  );
}

function Composer({ placeholder, onSend, disabled, lang }: { placeholder: string; onSend: (text: string) => void; disabled?: boolean; lang: "en" | "ar" }) {
  const [text, setText] = useState("");
  const [listening, setListening] = useState(false);
  const recRef = useRef<unknown>(null);

  function submit() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  }

  // Voice input via the browser's Web Speech API — transcribes into the box so the
  // user can review/edit before sending. Silently no-ops if unsupported.
  function toggleMic() {
    const SR = (window as unknown as { SpeechRecognition?: new () => never; webkitSpeechRecognition?: new () => never });
    const Ctor = SR.SpeechRecognition ?? SR.webkitSpeechRecognition;
    if (!Ctor) { setText((t) => t || ""); alert("Voice input isn't supported in this browser — try Chrome."); return; }
    if (listening) { (recRef.current as { stop: () => void } | null)?.stop(); return; }
    const rec = new (Ctor as unknown as new () => {
      lang: string; interimResults: boolean; continuous: boolean;
      onresult: (e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void; onend: () => void; onerror: () => void;
      start: () => void; stop: () => void;
    })();
    rec.lang = lang === "ar" ? "ar-JO" : "en-US";
    rec.interimResults = true;
    rec.continuous = false;
    rec.onresult = (e) => {
      let s = "";
      for (let i = 0; i < e.results.length; i++) s += e.results[i][0].transcript;
      setText(s);
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recRef.current = rec;
    setListening(true);
    rec.start();
  }

  return (
    <div className="mt-2 flex flex-none gap-2">
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        placeholder={listening ? "Listening… speak now" : placeholder}
        className="flex-1 rounded-lg border border-stitch-line bg-stitch-card px-3 py-2.5 text-sm"
      />
      <button
        type="button"
        onClick={toggleMic}
        title="Speak your question"
        aria-label="Voice input"
        className={`grid w-10 flex-none place-items-center rounded-lg border text-lg ${listening ? "animate-pulse border-red-400 bg-red-50 text-red-600" : "border-stitch-line bg-stitch-card text-stitch-muted hover:bg-stitch-soft"}`}
      >
        🎤
      </button>
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
  const { state, openChat, addMessage, setView, setPendingAsk } = useApp();
  const { view, chats, openChatId, selectedArea, language } = state;
  const [pending, setPending] = useState(false);

  // A search miss ("area not in our data → ask the Assistant") queues a question;
  // consume it once and auto-ask (which triggers the web fallback if needed).
  useEffect(() => {
    if (state.pendingAsk) {
      const q = state.pendingAsk;
      setPendingAsk(null);
      void send(q, true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.pendingAsk]);

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
    addMessage({ role: "bot", text: answer, fromInternet: res?.from_internet, sources: res?.sources });
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
      <div className="flex h-[calc(100vh-72px)] flex-col gap-3">
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
        <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto pr-1">
          {session.messages.map((m, i) => (
            <ChatBubble key={i} message={m} />
          ))}
          {pending && <Thinking />}
        </div>
        <Composer placeholder={selectedArea ? `Ask about ${selectedArea}…` : "Continue this chat…"} onSend={(t) => send(t)} disabled={pending} lang={language} />
      </div>
    );
  }

  // chatnew — empty conversation + input; sending transitions into chatopen.
  const meta = getViewMeta("chatnew");
  return (
    <div className="flex h-[calc(100vh-72px)] flex-col gap-3">
      <ViewHeader {...meta} />
      <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto pr-1">
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
      <Composer placeholder="Ask a question…" onSend={(t) => send(t, true)} disabled={pending} lang={language} />
    </div>
  );
}
