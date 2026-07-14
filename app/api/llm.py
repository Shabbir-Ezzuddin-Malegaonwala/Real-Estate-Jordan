"""Explain-only LLM narration for the seller valuation.

STRUCTURAL GUARDRAIL (the manager's rule): the model may ONLY rephrase the numbers
we pass it into clear prose in the requested language. It must never invent, change,
or add a number. The engine owns every figure; the LLM owns only the words.

Keys come from the environment (.env, gitignored). Provider order: OpenAI -> Groq
-> Gemini; if none is configured/reachable, narrate() returns None and the API
falls back to a plain templated sentence, so the product never depends on the LLM.
"""
from __future__ import annotations
import json
import os
from typing import Any

try:
    import requests  # already used by the scrapers
except Exception:  # pragma: no cover
    requests = None  # type: ignore

_SYSTEM = (
    "You are a real-estate valuation report writer for Jordan. You will be given a "
    "JSON object of FACTS (prices, areas, counts, dates) that were computed by a "
    "pricing engine. Write a short, clear explanation for a property owner. "
    "ABSOLUTE RULES: (1) Use ONLY numbers present in the FACTS — never invent, round "
    "differently, estimate, or add any figure. (2) If a fact is missing, do not "
    "mention it. (3) No investment advice or guarantees; describe what the numbers "
    "mean. Write 3-5 sentences."
)


def _lang_instruction(language: str) -> str:
    return "Write the reply in Arabic." if str(language).lower().startswith("ar") else "Write the reply in English."


def _openai(facts: dict[str, Any], language: str) -> str | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key or not requests:
        return None
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            "temperature": 0.2,
            "max_tokens": 320,
            "messages": [
                {"role": "system", "content": _SYSTEM + " " + _lang_instruction(language)},
                {"role": "user", "content": "FACTS:\n" + json.dumps(facts, ensure_ascii=False)},
            ],
        },
        timeout=30,
    )
    if r.status_code != 200:
        return None
    return r.json()["choices"][0]["message"]["content"].strip()


def _groq(facts: dict[str, Any], language: str) -> str | None:
    key = os.environ.get("GROQ_API_KEY")
    if not key or not requests:
        return None
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
            "temperature": 0.2,
            "max_tokens": 320,
            "messages": [
                {"role": "system", "content": _SYSTEM + " " + _lang_instruction(language)},
                {"role": "user", "content": "FACTS:\n" + json.dumps(facts, ensure_ascii=False)},
            ],
        },
        timeout=30,
    )
    if r.status_code != 200:
        return None
    return r.json()["choices"][0]["message"]["content"].strip()


def narrate(facts: dict[str, Any], language: str = "en") -> str | None:
    """Return an explain-only narration of `facts` in `language`, or None if no
    provider is available. Never raises — the caller falls back to a template."""
    for provider in (_openai, _groq):
        try:
            out = provider(facts, language)
            if out:
                return out
        except Exception:
            continue
    return None


def available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY"))
