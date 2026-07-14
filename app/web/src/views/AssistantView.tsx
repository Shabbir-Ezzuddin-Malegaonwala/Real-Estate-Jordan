import { useEffect, useRef, useState } from "react";
import { useApp } from "../lib/store";
import type { ChatMessage } from "../lib/store";
import { Card } from "../ui";
import { ViewHeader } from "./ViewHeader";
import { getViewMeta } from "./viewMeta";

// Demo seed content (mirrors ui-demos/demo-G.html's CHATS) so Chat history
// isn't empty on first run. Seeded once, only when there are no chats yet.
const DEMO_CHATS: { user: string; bot: string }[] = [
  {
    user: "Why is Abdoun 918?",
    bot: "Similar apartments nearby listed ~1,150; adjusted for a lower floor and calibrated to real sale prices → 918 JD/m². Based on 12 nearby sales.",
  },
  {
    user: "Khalda vs Sweifieh margin",
    bot: "Khalda ~25% vs Sweifieh ~24% — similar. Khalda land is cheaper (300K vs 410K/dunum), which offsets its lower sale price.",
  },
];

function mockReply(question: string): string {
  return `Noted: "${question}". (Mock reply — the live assistant answers from real market data and never invents numbers.)`;
}

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

function Composer({ placeholder, onSend }: { placeholder: string; onSend: (text: string) => void }) {
  const [text, setText] = useState("");
  function submit() {
    const trimmed = text.trim();
    if (!trimmed) return;
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
      <button type="button" onClick={submit} className="rounded-lg bg-stitch-brand px-4 text-sm font-bold text-white">
        Send
      </button>
    </div>
  );
}

export function AssistantView() {
  const { state, newChat, openChat, addMessage, setView } = useApp();
  const { view, chats, openChatId } = state;
  const seededRef = useRef(false);

  // Seed demo chats once on first mount if there are none yet — restores the
  // view it interrupted so seeding never steals the user's navigation.
  useEffect(() => {
    if (seededRef.current || chats.length > 0) return;
    seededRef.current = true;
    const priorView = view;
    for (const demo of DEMO_CHATS) {
      newChat();
      addMessage({ role: "user", text: demo.user });
      addMessage({ role: "bot", text: demo.bot });
    }
    setView(priorView);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (view === "chathist") {
    const meta = getViewMeta("chathist");
    return (
      <div className="flex flex-col gap-3">
        <ViewHeader {...meta} />
        {chats.length === 0 ? (
          <Card>
            <div className="text-sm text-stitch-muted">No chats yet — start one from "New chat".</div>
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
              {" "}
              ·{" "}
              <button type="button" onClick={() => setView("chathist")} className="cursor-pointer text-stitch-brand">
                history
              </button>
            </>
          }
          title={session.title}
        />
        <div className="flex max-h-[55vh] flex-col gap-2.5 overflow-y-auto pr-1">
          {session.messages.map((m, i) => (
            <ChatBubble key={i} message={m} />
          ))}
        </div>
        <Composer
          placeholder="Continue this chat…"
          onSend={(text) => {
            addMessage({ role: "user", text });
            addMessage({ role: "bot", text: mockReply(text) });
          }}
        />
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
            text: "Ask me about pricing, an area, competitors or the market — I answer from our data and the live market, and never invent numbers.",
          }}
        />
      </div>
      <Composer
        placeholder="Ask a question…"
        onSend={(text) => {
          addMessage({ role: "user", text });
          addMessage({ role: "bot", text: mockReply(text) });
          setView("chatopen");
        }}
      />
    </div>
  );
}
