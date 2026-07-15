import type { ChatMessage, Source } from "./types";
import { EngineCard } from "./EngineCard";
import { Citations } from "./Citations";

// One chat bubble. User messages are plain; assistant messages render
// lightweight markdown, live tool-activity chips, inline engine cards, and
// citation chips. Clicking a citation area re-centres the map via onPickSource.
export function Message({ m, onPickSource }: { m: ChatMessage; onPickSource: (s: Source) => void }) {
  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-[3px] rounded-tr-none border border-line bg-raised px-3 py-2 text-[13px] text-ink">
          {m.text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="w-full max-w-[95%]">
        {m.activities.length > 0 && (
          <div className="mb-1.5 space-y-1">
            {m.activities.map((a, i) => (
              <div key={i} className="flex items-center gap-1.5 text-2xs text-ink-mute">
                <span className={a.done ? (a.ok === false ? "text-neg" : "text-pos") : "animate-pulse text-cyan"}>
                  {a.done ? (a.ok === false ? "✕" : "✓") : "▸"}
                </span>
                <span>{a.label}</span>
                {a.sql && <code className="truncate rounded bg-surface px-1 text-ink-faint">{a.sql}</code>}
              </div>
            ))}
          </div>
        )}

        {m.text && (
          <div
            className="prose-chat text-[13px] leading-relaxed text-ink"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(m.text) }}
          />
        )}
        {m.streaming && !m.text && m.activities.length === 0 && (
          <div className="text-2xs text-ink-mute">Thinking…</div>
        )}

        {m.engineResults.map((r, i) => (
          <EngineCard key={i} r={r} />
        ))}

        {!m.streaming && <Citations sources={m.sources} onPick={onPickSource} />}

        {m.error && <div className="mt-2 rounded-[3px] border border-neg/40 bg-neg/10 px-3 py-2 text-2xs text-neg">{m.error}</div>}
      </div>
    </div>
  );
}

// Minimal, safe markdown -> HTML. Escapes first, then applies a small set of
// inline/block rules (bold, italic, inline code, headings, bullet/number lists,
// links, paragraphs). No raw HTML from the model ever reaches the DOM.
function renderMarkdown(src: string): string {
  const esc = (s: string) =>
    s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]!);

  const inline = (s: string) =>
    esc(s)
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>")
      .replace(/`([^`]+)`/g, '<code class="rounded bg-surface px-1 text-cyan">$1</code>')
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
        '<a href="$2" target="_blank" rel="noreferrer noopener" class="text-cyan underline">$1</a>');

  const lines = src.split("\n");
  const out: string[] = [];
  let list: "ul" | "ol" | null = null;
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) { closeList(); continue; }
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) { closeList(); out.push(`<div class="mt-2 font-semibold text-ink">${inline(h[2])}</div>`); continue; }
    const ul = line.match(/^\s*[-*]\s+(.*)$/);
    if (ul) { if (list !== "ul") { closeList(); out.push('<ul class="ml-4 list-disc space-y-0.5">'); list = "ul"; } out.push(`<li>${inline(ul[1])}</li>`); continue; }
    const ol = line.match(/^\s*\d+\.\s+(.*)$/);
    if (ol) { if (list !== "ol") { closeList(); out.push('<ol class="ml-4 list-decimal space-y-0.5">'); list = "ol"; } out.push(`<li>${inline(ol[1])}</li>`); continue; }
    closeList();
    out.push(`<p class="mb-1.5">${inline(line)}</p>`);
  }
  closeList();
  return out.join("");
}
