# Demo & platform requirements (captured 2026-07-14, Demo D → E)

Demo D rated 7–8/10. Every item below must have a **valid, logical reason**; think the user's flow + edge cases before adding anything. White + blue theme. Scalable/maintainable (not a static site) for the real build.

## UI — do now (Demo E)
1. **Burger** toggles the left sidebar (open/close).
2. **Right sidebar = map controls** (layers, POI select/deselect) — separate from the left nav.
3. **Assistant restructured** (like ChatGPT): clicking Assistant expands to **New chat** (separate) + **Chat history** (separate list). Click a past chat → open it → **continue it** (with its memory). Use a chatbot icon, not a message icon.
4. **Map-card icons need hover tooltips** — a person can't tell 🎓/🏥/🚌 apart; on hover show "Schools", "Hospitals", "Bus stops". Distinguish **schools vs universities** (separate categories).
5. **Search bar** = show the **full area dropdown list**; typing **narrows** it; if the area **isn't in our data**, route the user to the **Assistant** (LLM fetches from the internet).
6. **Settings must be functional** (working toggles), and hold everything properly.
7. **Justify every section name / input / output.** e.g. "What changed" → better: **Price trend / Recent moves**. Names must be logical.
8. Possibly **more nav categories** (research what a real platform needs) — but only if justified.

## Build-phase (deferred, but plan for)
- **Accounts / auth (IDs + passwords)** like ChatGPT — each user's chat memory saved to **their account only**; others can't see it. Take the auth + security architecture from **AI Studio** (code/architecture is in the Rubicon folder).
- **Chat memory / cache architecture** — study AI Studio's framework, tech, techniques, architecture; apply here. Chat is **scoped to real-estate/builder/pricing/market/map only**, with access to all our data.
- **LLM fallback** — if an area/answer isn't in our data, the LLM searches the internet, returns it, and flags that it did so.
- **Backend cleanliness** — everything connected front↔back; change one side → the other updates. Follow a **consistent pattern**; use the **code-quality / code-reviewer** standard (check Rubicon + memory / skills-inventory).
- **Detailed prompts/instructions behind everything** — read the **ponytail** scale skills + the leaked **Anthropic-flow prompts** (docs/reference/prompt-leaks) for how detailed backend instructions should be.
- **Study the friend's platform fully** — include everything he did (pricing calc, map logic, simplifications, the HTML he sent the manager); he simplified our base well — reuse that. Everything he covered (whole Jordan, many area circles — more data than our 5).
- **Map (next major phase)** — pinpoint ALL collected data on the map (all POIs, all areas, whole Jordan), not just 5 areas.
- **Data-science + LLM** parts to deepen.

## Guiding rule
Every element = a valid reason + a logical flow + the edge cases pre-thought ("user wants X → goes to this tab → gives this input → gets this output"). Research (Google + AI Studio + friend's code + our research) before building.
