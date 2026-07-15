"""Explain-only LLM layer: valuation narration + a grounded Q&A assistant.

STRUCTURAL GUARDRAIL (the manager's rule): the model may ONLY use the FACTS we
pass it — never invent, change, or add a number. The engine owns every figure;
the LLM owns only the words. If the answer isn't in the facts, it must say so.

Keys come from the environment (.env, gitignored). Provider order OpenAI -> Groq
-> Gemini; if none is reachable, functions return None and the caller falls back
to a plain template, so the product never depends on the LLM.
"""
from __future__ import annotations
import json
import os
from typing import Any

try:
    import requests  # already used by the scrapers
except Exception:  # pragma: no cover
    requests = None  # type: ignore


def _lang(language: str) -> str:
    return "Reply in Arabic." if str(language).lower().startswith("ar") else "Reply in English."


def _openai(system: str, user: str) -> str | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key or not requests:
        return None
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"), "temperature": 0.2,
              "max_tokens": 380, "messages": [{"role": "system", "content": system},
                                              {"role": "user", "content": user}]},
        timeout=30,
    )
    return r.json()["choices"][0]["message"]["content"].strip() if r.status_code == 200 else None


def _groq(system: str, user: str) -> str | None:
    key = os.environ.get("GROQ_API_KEY")
    if not key or not requests:
        return None
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"), "temperature": 0.2,
              "max_tokens": 380, "messages": [{"role": "system", "content": system},
                                              {"role": "user", "content": user}]},
        timeout=30,
    )
    return r.json()["choices"][0]["message"]["content"].strip() if r.status_code == 200 else None


def _gemini(system: str, user: str) -> str | None:
    key = os.environ.get("GOOGLE_API_KEY")
    if not key or not requests:
        return None
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        headers={"Content-Type": "application/json"},
        json={"system_instruction": {"parts": [{"text": system}]},
              "contents": [{"parts": [{"text": user}]}],
              "generationConfig": {"temperature": 0.2, "maxOutputTokens": 380}},
        timeout=30,
    )
    if r.status_code != 200:
        return None
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def _chat(system: str, user: str) -> str | None:
    for provider in (_openai, _groq, _gemini):
        try:
            out = provider(system, user)
            if out:
                return out
        except Exception:
            continue
    return None


def narrate(facts: dict[str, Any], language: str = "en") -> str | None:
    system = (
        "You are a real-estate valuation report writer for Jordan. Write a short, clear "
        "explanation (3-5 sentences) of the given FACTS for a property owner. Use ONLY numbers "
        "present in the FACTS — never invent, re-round, estimate, or add a figure. No investment "
        "advice. " + _lang(language)
    )
    return _chat(system, "FACTS:\n" + json.dumps(facts, ensure_ascii=False))


def ask(question: str, facts: dict[str, Any], language: str = "en") -> str | None:
    system = (
        "You are a helpful real-estate analyst for Jordan (Amman market). Answer the user's "
        "question using ONLY the FACTS provided. Rules: (1) never invent, change, or estimate a "
        "number that isn't in FACTS; (2) be concise (2-4 sentences); (3) no guarantees or "
        "investment advice. IMPORTANT: if the FACTS do not contain what's needed to answer, reply "
        "with EXACTLY the token NEED_WEB and nothing else — do NOT apologise or explain. " + _lang(language)
    )
    user = f"FACTS:\n{json.dumps(facts, ensure_ascii=False)}\n\nQUESTION: {question}"
    return _chat(system, user)


def _tavily_search(query: str, max_results: int = 4) -> list[dict[str, Any]] | None:
    key = os.environ.get("TAVILY_API_KEY")
    if not key or not requests:
        return None
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": key, "query": query, "max_results": max_results, "search_depth": "basic"},
            timeout=25,
        )
        return r.json().get("results", []) if r.status_code == 200 else None
    except Exception:
        return None


def web_answer(question: str, language: str = "en") -> dict[str, Any] | None:
    """Fallback when our data can't answer: search the web (Tavily) and synthesize
    an answer FROM the results only, flagged as web-sourced with citations."""
    results = _tavily_search(f"{question} Jordan Amman real estate 2026")
    if not results:
        return None
    ctx = "\n\n".join(
        f"[{i + 1}] {r.get('title', '')}\n{r.get('content', '')[:600]}\nURL: {r.get('url', '')}"
        for i, r in enumerate(results)
    )
    system = (
        "Answer a Jordan real-estate question using ONLY these WEB SEARCH RESULTS (our own database "
        "did not have it). Be concise (2-4 sentences). Begin with 'From a web search: '. Use only "
        "what the results say; if they don't answer it, say so. Do not add numbers not in the results. "
        + _lang(language)
    )
    ans = _chat(system, f"WEB RESULTS:\n{ctx}\n\nQUESTION: {question}")
    if not ans:
        return None
    return {"answer": ans, "sources": [r.get("url") for r in results if r.get("url")][:4]}


def available() -> bool:
    return bool(
        os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    )
