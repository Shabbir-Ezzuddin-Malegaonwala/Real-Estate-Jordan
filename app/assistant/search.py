"""Current-affairs / live-context web search.

Free by default: DuckDuckGo (no API key) via the `ddgs` package. Every result
carries its source URL and (when available) date so the assistant can cite and
date its claims. If TAVILY_API_KEY is set, we transparently upgrade to Tavily
(higher-quality, still returns URLs).
"""

from __future__ import annotations

from .config import TAVILY_API_KEY

_MAX_RESULTS = 5
_SNIPPET = 240  # chars — enough to summarise, small enough for free-tier TPM


def _tavily(query: str) -> list[dict]:
    from langchain_tavily import TavilySearch  # imported only when a key exists

    tool = TavilySearch(max_results=_MAX_RESULTS, api_key=TAVILY_API_KEY)
    raw = tool.invoke({"query": query})
    results = raw.get("results", raw) if isinstance(raw, dict) else raw
    out = []
    for r in results or []:
        out.append({
            "title": r.get("title"),
            "url": r.get("url") or r.get("href"),
            "snippet": (r.get("content") or r.get("snippet") or "")[:_SNIPPET],
            "date": r.get("published_date"),
        })
    return out


def _duckduckgo(query: str) -> list[dict]:
    from ddgs import DDGS

    out = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, region="wt-wt", safesearch="moderate", max_results=_MAX_RESULTS):
            out.append({
                "title": r.get("title"),
                "url": r.get("href") or r.get("url"),
                "snippet": (r.get("body") or "")[:_SNIPPET],
                "date": r.get("date"),
            })
    return out


def web_search(query: str) -> dict:
    q = (query or "").strip()
    if not q:
        return {"error": "empty_query"}

    provider = "tavily" if TAVILY_API_KEY else "duckduckgo"
    try:
        results = _tavily(q) if TAVILY_API_KEY else _duckduckgo(q)
    except Exception as e:
        # Try the free path if the paid one failed, then give up gracefully.
        if provider == "tavily":
            try:
                results, provider = _duckduckgo(q), "duckduckgo"
            except Exception as e2:
                return {"error": "search_unavailable", "query": q, "detail": f"{e}; {e2}"}
        else:
            return {"error": "search_unavailable", "query": q, "detail": str(e)}

    if not results:
        return {"query": q, "provider": provider, "results": [],
                "note": "No results — say you couldn't find current information on this."}

    return {
        "query": q,
        "provider": provider,
        "results": results,
        "sources": [{"name": r["title"] or r["url"], "url": r["url"], "date": r.get("date")}
                    for r in results if r.get("url")],
    }
