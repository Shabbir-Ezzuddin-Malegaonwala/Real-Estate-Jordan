// SSE client for POST /chat. fetch() + a streaming reader (EventSource can't POST),
// parsing `data: {json}\n\n` frames and invoking onEvent per frame.
import type { StreamEvent } from "./types";
import { API_BASE } from "../../lib/api";

// The assistant's /chat endpoint is served by the SAME backend as the
// recommendation API (mounted as a router in app/api/main.py), so it shares the
// one base URL — no separate port.

export async function streamChat(
  sessionId: string,
  message: string,
  onEvent: (e: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  });
  if (!res.ok || !res.body) {
    onEvent({ type: "error", message: `Assistant API returned ${res.status}. Is it running on :8100?` });
    onEvent({ type: "done", sources: [], engine_results: [] });
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    let idx;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const line = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const json = line.slice(5).trim();
      if (!json) continue;
      try {
        onEvent(JSON.parse(json) as StreamEvent);
      } catch {
        // ignore malformed frame
      }
    }
  }
}
