"""FastAPI service for the Jordan Real-Estate Assistant.

POST /chat streams the agent's turn as Server-Sent Events so the UI can render
tokens live, show tool activity ("searching the web…", "pricing Abdoun…"), drop
citation chips, render inline engine price cards, and drive the map (fly-to /
highlight / comp pins).

The engine is reused IN-PROCESS (see engine_bridge.py) — no second server.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from groq import APIStatusError, RateLimitError
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from langchain_core.messages import AIMessage

from .agent import MODELS, get_agent
from .config import ALLOWED_ORIGINS, GROQ_API_KEY, GROQ_MODEL
from .engine_bridge import get_engine

# Explicit per-session conversation memory (question/answer text pairs). Kept here
# rather than in a LangGraph checkpointer so a fallback retry on another model
# re-runs the SAME input without duplicating history. Capped to recent turns.
SESSIONS: dict[str, list] = {}
_MAX_HISTORY_MESSAGES = 24

# The chat endpoint lives on a router so it can be mounted into ANY FastAPI app —
# in this project it's included by the main recommendation API (app/api/main.py)
# so ONE server on ONE port serves both recommendation and the assistant. The
# standalone `app` below (which also includes this router) remains available for
# running the assistant on its own.
router = APIRouter()

app = FastAPI(title="Jordan Real-Estate Assistant", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _warm() -> None:
    # Load the DataBundle once at boot so the first /chat isn't slow.
    get_engine()


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


# Human-readable activity labels per tool (shown while the tool runs).
def _tool_label(name: str, args: dict[str, Any]) -> str:
    nb = args.get("neighborhood") or args.get("address") or ""
    q = (args.get("query") or args.get("question") or "")[:60]
    return {
        "geocode_address": f"Locating {args.get('address', '')}…",
        "get_recommendation": f"Pricing {nb}…",
        "get_comparables": f"Pulling comparables in {nb}…",
        "query_data": "Querying the database…",
        "web_search": f"Searching the web: {q}…",
        "list_neighborhoods": "Listing priceable submarkets…",
        "calculate": f"Calculating {args.get('expression', '')}…",
    }.get(name, f"Running {name}…")


def _parse_tool_output(raw: Any) -> Optional[dict]:
    """Tool outputs are JSON strings (see tools.py). Return the parsed dict."""
    if raw is None:
        return None
    text = raw.content if hasattr(raw, "content") else raw
    if isinstance(text, dict):
        return text
    if isinstance(text, str):
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None
    return None


def _extract_sources(name: str, out: dict) -> list[dict]:
    sources: list[dict] = []
    src = out.get("source")
    if isinstance(src, dict):
        sources.append(src)
    for s in out.get("sources", []) or []:
        if isinstance(s, dict):
            sources.append(s)
    # Comparable listing sources (each comp cites its portal + URL).
    for comp in out.get("comparables", []) or []:
        cs = comp.get("source")
        if isinstance(cs, dict) and cs.get("url"):
            sources.append(cs)
    return sources


def _map_command(name: str, out: dict) -> Optional[dict]:
    """Derive a map instruction from a tool result, if any."""
    if name == "geocode_address" and out.get("lat") is not None:
        return {
            "action": "flyto",
            "lat": out["lat"],
            "lng": out["lng"],
            "label": out.get("nearest_priceable_neighborhood") or out.get("address"),
        }
    if name == "get_recommendation" and not out.get("error"):
        res = out.get("resolution", {})
        centroid = res.get("centroid")
        comps = [
            {"lat": c.get("lat"), "lng": c.get("lng"),
             "price_per_m2": c.get("price_per_m2") or c.get("original_ppm2")}
            for c in out.get("comparables", []) or []
            if c.get("lat") is not None and c.get("lng") is not None
        ]
        return {
            "action": "recommendation",
            "neighborhood": res.get("resolved_to") or out.get("neighborhood"),
            "centroid": centroid,
            "comparables": comps,
        }
    if name == "get_comparables" and not out.get("error"):
        comps = [
            {"lat": c.get("lat"), "lng": c.get("lng"), "price_per_m2": c.get("price_per_m2")}
            for c in out.get("comparables", []) or []
            if c.get("lat") is not None and c.get("lng") is not None
        ]
        return {
            "action": "comparables",
            "neighborhood": out.get("neighborhood"),
            "centroid": out.get("centroid"),
            "comparables": comps,
        }
    return None


def _looks_rate_limited(e: Exception) -> bool:
    s = f"{type(e).__name__}: {e}".lower()
    return any(k in s for k in ("rate limit", "rate_limit", "ratelimit", "429",
                                "too many requests", "quota", "tokens per day", "tpd", "tpm"))


def _looks_toolcall_failure(e: Exception) -> bool:
    """Groq returns 'Failed to call a function' when a model emits a malformed
    tool call. It's model-specific and recoverable — another model in the chain
    usually handles the same request cleanly, so we rotate rather than give up."""
    s = f"{type(e).__name__}: {e}".lower()
    return any(k in s for k in ("failed to call a function", "failed_generation",
                                "tool_use_failed", "tool call validation", "adjust your prompt"))


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"


async def _run_agent(session_id: str, message: str) -> AsyncGenerator[str, None]:
    """Stream one turn as SSE, rotating across the model fallback chain on rate
    limits. Memory is explicit (SESSIONS) so a fallback retry re-runs cleanly."""
    if not GROQ_API_KEY:
        yield _sse({"type": "error",
                    "message": "GROQ_API_KEY is not set on the server. Add it to the environment "
                               "and restart the assistant API."})
        yield _sse({"type": "done", "sources": [], "engine_results": []})
        return

    history = SESSIONS.get(session_id, [])
    base_messages = history + [HumanMessage(content=message)]

    yield _sse({"type": "status", "stage": "thinking", "message": "Thinking…"})

    last_error: Optional[Exception] = None
    for idx, model_id in enumerate(MODELS):
        agent = get_agent(model_id)
        inputs = {"messages": base_messages}

        all_sources: list[dict] = []
        engine_results: list[dict] = []
        answer_text = ""
        emitted = False

        yield _sse({"type": "status", "stage": "model", "model": model_id,
                    "message": f"Using {model_id}"})

        try:
            async for event in agent.astream_events(inputs, version="v2"):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    text = getattr(chunk, "content", "") if chunk else ""
                    if text:
                        emitted = True
                        answer_text += text
                        yield _sse({"type": "token", "text": text})

                elif kind == "on_tool_start":
                    name = event.get("name", "tool")
                    args = event["data"].get("input", {}) or {}
                    if not isinstance(args, dict):
                        args = {}
                    emitted = True
                    yield _sse({"type": "tool_start", "tool": name, "label": _tool_label(name, args)})

                elif kind == "on_tool_end":
                    name = event.get("name", "tool")
                    out = _parse_tool_output(event["data"].get("output"))
                    if out is None:
                        yield _sse({"type": "tool_end", "tool": name, "ok": False})
                        continue
                    ok = not out.get("error")
                    srcs = _extract_sources(name, out)
                    all_sources.extend(srcs)
                    payload: dict = {"type": "tool_end", "tool": name, "ok": ok, "sources": srcs}
                    if name == "get_recommendation" and ok:
                        engine_results.append(out)
                        payload["engine_result"] = out
                    if name == "query_data" and out.get("sql"):
                        payload["sql"] = out["sql"]
                    cmd = _map_command(name, out)
                    if cmd:
                        payload["map"] = cmd
                    yield _sse(payload)

        except (RateLimitError, APIStatusError, Exception) as e:  # noqa: B014
            status = getattr(e, "status_code", None)
            busy = isinstance(e, RateLimitError) or status == 429 or _looks_rate_limited(e)
            toolcall_fail = _looks_toolcall_failure(e)
            recoverable = busy or toolcall_fail
            last_error = e
            # Rotate to the next model if this one was throttled OR emitted a
            # malformed tool call, AND nothing has streamed yet (a clean restart).
            # Otherwise surface the state.
            if recoverable and not emitted and idx < len(MODELS) - 1:
                nxt = MODELS[idx + 1]
                reason = "is rate-limited" if busy else "had a tool-call error"
                yield _sse({"type": "status", "stage": "model_switch", "model": nxt,
                            "message": f"{model_id} {reason} — switching to {nxt}…"})
                continue
            yield _sse({
                "type": "error",
                "message": ("All models are rate-limited right now (Groq free-tier caps). Please "
                            "wait a moment and try again." if busy else
                            f"Model error: {type(e).__name__}: {e}"),
                "rate_limited": busy,
            })
            yield _sse({"type": "done", "sources": _dedupe(all_sources), "engine_results": engine_results})
            return

        # If a model produced NOTHING (no tools, no text), that's a model hiccup —
        # fall back to the next model rather than returning an empty turn.
        if not emitted and not answer_text.strip() and idx < len(MODELS) - 1:
            nxt = MODELS[idx + 1]
            yield _sse({"type": "status", "stage": "model_switch", "model": nxt,
                        "message": f"{model_id} returned an empty response — switching to {nxt}…"})
            continue

        # Success on this model — persist memory and finish.
        if answer_text.strip():
            new_history = history + [HumanMessage(content=message), AIMessage(content=answer_text)]
            SESSIONS[session_id] = new_history[-_MAX_HISTORY_MESSAGES:]
        yield _sse({"type": "done", "model": model_id,
                    "sources": _dedupe(all_sources), "engine_results": engine_results})
        return

    # Exhausted the chain without success.
    yield _sse({"type": "error", "rate_limited": True,
                "message": "All fallback models are unavailable right now. Please try again shortly."
                           + (f" (last error: {type(last_error).__name__})" if last_error else "")})
    yield _sse({"type": "done", "sources": [], "engine_results": []})


def _dedupe(sources: list[dict]) -> list[dict]:
    seen: set = set()
    out: list[dict] = []
    for s in sources:
        key = (s.get("name"), s.get("url"), s.get("sql"))
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _run_agent(req.session_id, req.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.get("/health")
def health() -> dict:
    engine = get_engine()
    return {
        "status": "ok",
        "model": GROQ_MODEL,
        "model_chain": MODELS,
        "groq_key_present": bool(GROQ_API_KEY),
        "listings": len(engine.bundle.listings),
        "priceable_areas": len(engine.areas(min_sales=5)),
        "db": engine.db_path,
    }


@app.get("/neighborhoods")
def neighborhoods() -> dict:
    """Priceable submarkets with centroids — used by the frontend to draw/label
    the map and to power quick-pick chips. Mirrors list_neighborhoods."""
    engine = get_engine()
    return {
        "neighborhoods": [
            {
                "name": a.name,
                "centroid": [a.centroid_lng, a.centroid_lat] if a.centroid_lat else None,
                "sale_comps": a.sale_count,
                "median_price_jd_m2": a.median_price_per_m2,
            }
            for a in engine.areas(min_sales=20)
        ]
    }


# Standalone mode still serves /chat (the main API also includes this router).
app.include_router(router)
