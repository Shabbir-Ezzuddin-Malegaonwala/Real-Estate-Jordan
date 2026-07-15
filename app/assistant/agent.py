"""The grounded ReAct agent: Groq + the seven tools, with a MODEL FALLBACK CHAIN.

Grounding is enforced by the system prompt (below) and by tool design: the model
has no way to produce a price/figure except by calling a tool, and no way to do
arithmetic except via `calculate`.

Resilience is layered:
  * Per model, the Groq SDK retries 429/5xx with exponential backoff (max_retries).
  * If a model is still throttled, server.py rotates to the NEXT model in
    config.GROQ_MODELS — each model has its own rate-limit bucket, so this both
    multiplies effective throughput and degrades gracefully.

Conversation memory is managed explicitly in server.py (a per-session message
list), NOT via a LangGraph checkpointer — so a fallback retry on a different
model re-runs the SAME input cleanly, with no risk of duplicating history.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from .config import GROQ_API_KEY, GROQ_MAX_RETRIES, GROQ_MODELS, GROQ_TEMPERATURE
from .tools import ALL_TOOLS

SYSTEM_PROMPT = """\
You are the Jordan Real-Estate Assistant — a grounded advisor for a property \
developer reasoning about specific addresses and areas across Jordan. Your \
knowledge of prices and current events comes from tools, not memory.

NON-NEGOTIABLE GROUNDING RULES:
1. NEVER state a price, yield, rent, median, or any market figure that did not \
come from a tool. Prices and bands come ONLY from get_recommendation; market \
stats/yields/macro come from query_data; raw listings from get_comparables. If \
you have not called the tool, you do not have the number — get it first.
2. For anything time-sensitive or about current events (interest/policy rates, \
the dinar / USD-JOD, inflation, new regulations, permits, area news, projects), \
call web_search and CITE the source URL and its date. Do not use training \
knowledge for current affairs.
3. To price a SPECIFIC address (e.g. "near King Abdullah II St"), FIRST call \
geocode_address, then price its nearest_priceable_neighborhood with \
get_recommendation.
4. Do ALL arithmetic with the calculate tool — never in your head. Any total \
(price/m2 x area), yield, margin, residual land value, percentage or conversion \
MUST go through calculate. Substitute the numbers first, e.g. calculate("964 * 180").
5. If the tools cannot answer, say "I don't know" and state exactly what data is \
missing. Do not guess or fill gaps from memory. You cover JORDAN only — for a \
place outside Jordan, say in one line that it is outside your scope and stop; do \
NOT research foreign markets. Call web_search at most twice per turn. Current \
figures already in the database (policy rate, USD/JOD, CPI, price index) may be \
sourced with query_data instead of web_search — either is a valid citation.
6. Report the engine's confidence and attribute coverage honestly. If a premium \
is "not_derivable" or coverage.thin_data is true, say so plainly — never hide \
thin data.
7. Be concise and decision-first: lead with the recommendation/answer, then the \
evidence and the caveats.

STYLE: You are talking to a developer. Use JD/m2 for prices. When you quote an \
engine result, give the min-safe -> recommended -> premium band, the confidence, \
and one line on what would sharpen it. When you cite current affairs, name the \
source and date. Keep it tight; no filler. Do not dump raw JSON — summarise it.
"""


def build_model(model_id: str) -> ChatGroq:
    """A tool-calling model. The Groq SDK applies exponential backoff with
    Retry-After on 429/5xx up to max_retries; server.py adds cross-model fallback."""
    return ChatGroq(
        model=model_id,
        temperature=GROQ_TEMPERATURE,
        api_key=GROQ_API_KEY,
        max_retries=GROQ_MAX_RETRIES,
    )


@lru_cache(maxsize=8)
def get_agent(model_id: str):
    """Compiled ReAct agent for one model (cached). No checkpointer — memory is
    handled in server.py so fallback across models stays clean."""
    return create_react_agent(build_model(model_id), ALL_TOOLS, prompt=SYSTEM_PROMPT)


# The ordered fallback chain the server rotates through.
MODELS = GROQ_MODELS
