# LLM rules — the explain-only guardrail

The product uses an LLM in two places: the **valuation report summary** (Value my
property) and the **Assistant chatbot**. In both, the LLM is *structurally* limited
to explaining numbers the engine computed — it can never produce a number on its
own. This is the manager's rule ("appraiser, not AI"), enforced in code, not just
by asking nicely.

## Where it lives
`app/api/llm.py` — one shared `_chat(system, user)` with two entry points:
- `narrate(facts, language)` → the valuation summary
- `ask(question, facts, language)` → the Assistant answer

Both send a **system prompt** (the rules) + a **FACTS** blob (real engine numbers).

## The rules given to the model (verbatim intent)
1. **Use ONLY numbers present in FACTS** — never invent, re-round, estimate, or add a figure.
2. **If FACTS don't contain the answer, say so** ("I don't have that data yet") — never guess.
3. **Be concise** (2–4 sentences for Q&A, 3–5 for the summary).
4. **No guarantees, no investment advice** — describe what the numbers mean.
5. **Reply in the user's language** (English / Arabic, from Settings).

## Why it can't hallucinate a price
The engine assembles the FACTS (`/ask` → `_ask_facts`, `/value-property` →
`valuation.value_property`). The model only receives those facts + the question.
It has no tools, no web access, no memory — so the only numbers available to it are
the real ones. Anything not in FACTS, it must decline.

## Flow (backend → chatbot)
1. User asks in the Assistant (or submits the valuation form).
2. Frontend POSTs to `/ask` (or `/value-property`) with the selected area + language.
3. Backend gathers REAL facts from the canonical DB + engine (price, range,
   confidence, median sale JD/m², listing count, land price…).
4. `llm.ask/narrate` sends system-rules + facts to the provider.
5. The answer (or an honest template if no provider is reachable) returns to the UI.

## Providers & keys
Order: **OpenAI → Groq → Gemini** (first reachable wins). Keys live in a gitignored
`.env` (`OPENAI_API_KEY`, `GROQ_API_KEY`, `GOOGLE_API_KEY`). If none is reachable,
`narrate`/`ask` return `None` and the UI shows a plain templated line — the product
never breaks when the LLM is down.

Status (2026-07-15): OpenAI ✅ working. Gemini key present but the project is
**out of quota** (needs Generative Language API + billing/free-tier enabled). Groq
key returns "access denied" (likely region/expiry).

## Verified behaviour
- Real question → grounded answer ("Abdoun 627–1302 JD/m², median 1068, 860 listings").
- Out-of-scope question (2027 forecast, crime rate) → **declines**: "I don't have
  that data yet" — no fabrication. This is the acceptance test for the guardrail.
