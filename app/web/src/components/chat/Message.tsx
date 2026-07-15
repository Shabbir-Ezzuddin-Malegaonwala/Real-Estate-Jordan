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

// Minimal, safe markdown -> HTML. Everything is HTML-escaped FIRST, then a small
// set of rules is applied — so no raw HTML from the model ever reaches the DOM.
// Handles: fenced code blocks, headings, blockquotes, bullet/number lists, GFM
// pipe tables, bold/italic/inline-code/links, and paragraphs.
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

  // Pull out fenced code blocks first (```), so their contents aren't parsed as
  // markdown. Splitting on ``` makes odd-indexed segments the code. A still-open
  // fence during streaming just renders as a growing code block — which is fine.
  const segments = src.split(/```/);
  return segments
    .map((seg, i) => {
      if (i % 2 === 1) {
        let body = seg;
        const nl = body.indexOf("\n");
        if (nl !== -1 && /^[A-Za-z0-9_+-]{1,15}$/.test(body.slice(0, nl).trim())) {
          body = body.slice(nl + 1); // drop a leading language line (e.g. ```sql)
        }
        return `<pre class="my-2 overflow-x-auto rounded bg-surface p-2 text-2xs leading-relaxed text-ink-dim"><code>${esc(body.replace(/\n$/, ""))}</code></pre>`;
      }
      return renderBlocks(seg, inline);
    })
    .join("");
}

function renderBlocks(src: string, inline: (s: string) => string): string {
  const lines = src.split("\n");
  const out: string[] = [];
  let list: "ul" | "ol" | null = null;
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };
  const cells = (r: string) =>
    r.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map((c) => c.trim());

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trimEnd();
    if (!line.trim()) { closeList(); continue; }

    // GFM pipe table: header row, a |---|---| separator, then body rows.
    const next = lines[i + 1] ?? "";
    if (line.includes("|") && next.includes("|") && /^[\s|:-]*-{2,}[\s|:-]*$/.test(next)) {
      closeList();
      const head = cells(line);
      let j = i + 2;
      const rows: string[][] = [];
      while (j < lines.length && lines[j].includes("|") && lines[j].trim()) { rows.push(cells(lines[j])); j++; }
      const th = head.map((c) => `<th class="border border-line px-2 py-1 text-left font-semibold text-ink">${inline(c)}</th>`).join("");
      const body = rows.map((r) => `<tr>${r.map((c) => `<td class="border border-line px-2 py-1">${inline(c)}</td>`).join("")}</tr>`).join("");
      out.push(`<div class="my-2 overflow-x-auto"><table class="w-full border-collapse text-2xs"><thead><tr>${th}</tr></thead><tbody>${body}</tbody></table></div>`);
      i = j - 1;
      continue;
    }

    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) { closeList(); out.push(`<div class="mt-2 font-semibold text-ink">${inline(h[2])}</div>`); continue; }
    const bq = line.match(/^\s*>\s?(.*)$/);
    if (bq) { closeList(); out.push(`<blockquote class="my-1 border-l-2 border-line pl-3 text-ink-dim">${inline(bq[1])}</blockquote>`); continue; }
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
