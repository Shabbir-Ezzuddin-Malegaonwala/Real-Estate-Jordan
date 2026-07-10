# AI Studio — Integration Study (for hosting our Jordan platform)
Read-only study by the specialized team (no files in the platform touched, no secrets read). Synthesized here by the Technical Lead. **Last updated:** 2026-07-08.

> "AI Studio" = the **user-facing product name of the company's "AI Agentic Platform"** (confirmed in conversational-service `ask_ai_studio_agent.py`). The manager decided we host our Jordan platform inside it.

---

## PART 1 — ARCHITECTURE & HOSTING FIT  ✅ (aistudio-arch)

**What it is:** a 9+ microservice system.
- **main-service** `core` — Bun/Elysia (`/api/v2`)
- **conversational / non-conversational / vectorization** — Python/FastAPI
- **agent-builder, queue, audit, external-api-gateway** — orchestration
- **frontend** — React 19 / Vite / Nginx
- **Front door:** Nginx → **Kong gateway** (path-prefix routing) → containers on a shared Docker network.
- **Data:** PostgreSQL ×5 (Drizzle ORM), Redis ×3, Weaviate ×2 (vectors), MinIO (objects), NATS (events).

**How a NEW service is added (the fixed recipe):**
1. Fixed `container_name` + a `GET /health` endpoint
2. `deploy/compose/cd/docker-compose.runtime.<svc>.yml`
3. A Kong service+route in `infra-gateway/deploy/kong/kong-init.sh`
4. Env injected from a CI secret → `/opt/app/env/<svc>.env`
5. Deploy via GitHub Actions self-hosted runner: `docker save | ssh | docker load` + `docker compose up -d` on the app VM. (GitHub `dev` is force-mirrored to GitLab.)

**How OUR platform fits (clean):** as **ONE new microservice + a frontend route**.
- Our FastAPI engine (`app/api/main.py`) already exposes `GET /health` on :8000 — matches their contract.
- Our React/Vite/MapLibre UI (`app/web`) → either a route inside their frontend, or its own static-Nginx container behind Kong.

**Mismatches to decide with the manager (none are blockers for a read-only analytics tool):**
- **(a) SQLite vs their Postgres/Drizzle standard.** Our DB is read-only *reference* data (~59 MB, loaded in-memory) → baking SQLite into the image works, but it breaks the "every service uses Postgres, org-scoped" convention. Option: migrate the reference data to a Postgres schema if they require it.
- **(b) No multi-tenancy.** We have zero `organization_id` scoping/auth — their **#1 hard rule**. For an internal single-tenant dashboard that may be fine; if it must be multi-tenant, we add org scoping.
- **(c) Standalone auth/CORS.** We use localhost origins, no Better-Auth / `organization-id` header. Integrating their auth = a defined task.

**Decision for the manager:** integrate their **auth + tenancy**, or run as an **isolated internal dashboard**? That choice drives (a)/(b)/(c).

---

## PART 2 — FRONTEND THEME & PATTERNS  ✅ (aistudio-frontend)
Repo: `C:\Rubicon\ai-agentic-platform-frontend` (pkg "ai-chatbot").
- **Stack:** **TanStack Start (SPA mode)** on Vite 8 + React 19 (NOT plain Vite, NOT Next.js); file-based routing (`app/`, auto-gen `routeTree.gen.ts` — never edit); **Tailwind v4 CSS-first** (`@theme` in `app/globals.css`); **shadcn/ui on Radix** (~70 primitives in `components/ui/`); **Zustand v5** (client state) + **TanStack Query v5** (server state) + **TanStack Form + Zod** (forms); **Biome** (lint/format); icons lucide-react; toasts sonner; charts recharts via `ui/chart.tsx`.
- **They have NO map library** → we add `maplibre-gl` (pinned + **code-split**, it's ~800KB).
- **A ready integration template exists:** vertical features (Review Analyzer, Sanction, Finance…) each = one big `components/<feature>.tsx` + a thin route `app/_main/<feature>.tsx` + a sidebar entry. **Our dashboard follows this exact shape.**
- **Theme:** oklch tokens, **blue primary**, flat (no shadows), geist fonts, dark via `next-themes`. Use their `--chart-1..5` ramp for our choropleth to stay on-brand; make the MapLibre basemap **theme-aware** (swap light/dark on `useTheme()`).
- **Conventions to follow:** API via `customFetch` (not axios); `hooks/queries/use-<domain>.ts` (queryOptions + key factory in `lib/query-keys.ts`); **snake_case** response types; env via `import.meta.env.NEXT_PUBLIC_*`; Biome check + `type:check` pre-commit; PRs target `dev` (do NOT merge).
- **Integration = re-skin the shell, keep the MapLibre core.** 10-step checklist: add pinned dep → `components/real-estate/` (dashboard + map/ + panels/, lazy-load canvas) → route `app/_main/real-estate.tsx` → sidebar item → `hooks/queries/use-real-estate.ts` → `store/real-estate-store.ts` → theme-aware basemap → filter forms in TanStack Form → env for tile keys → Biome+typecheck.

---

## PART 3 — LLM & DEEP-AGENT CONNECTIVITY  ✅ (aistudio-llm)
- **Template to clone:** `conversational-service/src/agents/ask_ai_studio_agent.py` — a grounded, tool-using assistant that answers **only from its knowledge base** and has a hard **"I don't know → contact support"** fallback. Exactly our copilot pattern.
- **Providers/routing:** openai / deepseek / google / anthropic / kimi via LangChain, routed by a `model_provider` string (`agents/base.py`). **Two calling patterns:** PROXY (main-service → conv-service runs the LangChain agent, streams SSE — for RAG/tools/streaming; **we use this**) vs DIRECT SDK (one-shot structured output).
- **Tool + RAG layer:** **MCP service** (FastMCP, :8700) exposes read-only tools (`search_knowledge_chunks`, etc.), enforced read-only (name prefix get_/search_/list_/fetch_ + middleware + tag), Bearer auth + org/user headers. **Weaviate** RAG, multi-tenant by `organization_id`. **Deep agents** (`create_deep_agent`) for multi-step.
- **★ KEY FINDING — no API key to manage:** the **platform holds the provider keys server-side**. "Use their LLM" = our frontend just passes a **model tier (UUID)**; main-service resolves tier → model+provider; conv-service routes and the platform bills. So embedding an LLM costs us **no separate OpenAI/Gemini key** — we pick a tier.
- **OUR COPILOT = 3 small pieces:**
  (a) **Data as retrieval** — vectorize our Jordan data into Weaviate (their vectorization service); the existing `search_knowledge_chunks` then retrieves + cites it. Nothing new for retrieval.
  (b) **Pricing engine as a tool** — add a read-only MCP tool `get_property_valuation(...)` / `search_comparable_sales(...)` in `mcp-service/src/tools/pricing/`; it's a thin HTTP client to our engine, auto-inherits auth + org scoping.
  (c) **The copilot agent** — clone `ask_ai_studio_agent.py` → `jordan_copilot_agent.py`: `create_agent(llm, tools=[knowledge_search, pricing_tool], system_prompt)` enforcing **evidence-only + always cite + explicit "I don't know" when retrieval is empty**.
- **Guardrails (built-in, we inherit):** pre-LLM PII + injection guard pipeline (PASS/BLOCK/MASK), `sanitize_for_llm`, never trust client `assistant` turns, strip `CITED_SOURCES:` marker, multi-tenancy on every query.

---

## SYNTHESIS / DECISIONS FOR CHATGPT  ✅
**Bottom line: our platform slots into AI Studio cleanly, and the LLM comes "free" (no separate key).**

**Hosting model (recommended):**
- Our **Python/FastAPI engine** → one new microservice (already has `/health`), behind a Kong route, deployed via their compose+CI recipe.
- Our **React/MapLibre UI** → **rebuilt into their frontend** as `components/real-estate/` + `app/_main/real-estate.tsx` route + sidebar item, **re-skinned to their theme** (Tailwind v4 tokens, blue primary, dark via next-themes; MapLibre added as a pinned, code-split dep). NOT a standalone SPA/iframe.
- Our data: SQLite reference bundle baked in the image works, OR migrate to a Postgres schema if they require the convention.

**LLM/copilot model (recommended):** clone their grounded `ask_ai_studio_agent` → `jordan_copilot_agent`; vectorize our data into Weaviate; expose our engine as a read-only MCP **pricing tool**. Pick a **model tier** — no OpenAI/Gemini key of our own.

**SKILLS / TOOLS to give the embedded LLM (the "skills+scripts" question):**
1. `search_comparable_sales` · 2. `get_property_valuation` (runs our engine: bands + confidence + waterfall) · 3. `residual_land_value` · 4. `run_scenario` / `compare_scenarios` · 5. `get_area_intelligence` (readiness + amenities + yield) · 6. `get_feasibility` · 7. `search_knowledge` (RAG over our docs/evidence). All read-only, all cite sources, all say "insufficient evidence" when empty.

**DECISIONS FOR THE MANAGER (surface these):**
1. SQLite reference DB vs migrate to their Postgres convention?
2. Integrate their **auth + multi-tenancy** (org scoping) or run as an **isolated internal dashboard**? (their #1 rule is org scoping.)
3. Which **model tier** for the copilot (they route/bill)?
4. Confirm **rebuild the UI into their TanStack Start frontend** (recommended) vs keep standalone.

**Source docs:** live agent findings from aistudio-arch / aistudio-frontend / aistudio-llm; key files cited inline above (ask_ai_studio_agent.py, mcp-service/src/tools, ai-agentic-platform-frontend app/_main + components/ui).
