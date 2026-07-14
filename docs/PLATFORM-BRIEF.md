# Platform Brief — what to build, why, for whom (grounded)

Combining: the meeting transcripts (07-06/09/13/14 + manager-asks doc), deep research on how property developers actually decide, and the friend's structure. The rule: **understand the intention, don't copy literal words.**

## 1. Who the user is & how they decide (developer research)
The client is a **builder/developer** launching units in a tower — not a marketplace. Real developers decide with this exact chain (this is the spine of our platform):

1. **Where should I build?** — pick an area (highest-and-best-use: legal + physical + financial). → *Opportunity*
2. **What can I pay for the land?** — **Residual Land Value (RLV)** = GDV − (build + fees + finance + contingency + **profit**). Target **profit margin 15–25% of GDV**; go/no-go on margin-on-cost or IRR. → *Economics*
3. **What price do I launch units at?** — the per-m² launch price (GDV ÷ sellable m²). → *Pricing*
4. **What changed that affects my price?** — market movements → raise or hold (never cut). → *Monitoring*

**Key terms builders actually use:** GDV (gross development value), RLV (residual land value), development margin / profit on cost, absorption rate (how fast units sell), FAR / buildable area, dunum, launch/off-plan price, payment plan. Use these meanings, but **label them in plain language** on screen.

**The friend's 4 sections map exactly to this chain** — Opportunity · Economics · Pricing · Monitoring. That's the correct organization. Keep it; just make each a clean dashboard, reached from a **sidebar**, not steps.

## 2. Manager's governing rules (from transcripts — non-negotiable)
- **Radical simplicity.** "Show as little as possible. Don't show any extra word not required." Impress by simplicity, not information (more info = "looks like AI").
- **Progressive disclosure.** "Start basic; I drill down when I want. Everything at once = confusing." Collapse by default, expand on click.
- **Every word understood** (client-facing). Rename jargon to plain language.
- **Builder tool, prices only go UP, never down.** Not a generic ML model.
- **Transparency kept but tucked away.** Sources/evidence = collapsed, deduplicated, in a corner — click to see the full table.
- **Market intelligence = a signal** ("what changed → re-look at price"), shown fresh like a stock ticker, not modelled into the price.
- **Future price drivers = infrastructure + transport.**

## 3. Every element — what it is, why, keep/simplify (the discipline)
| On screen | What it actually is (plain) | Why the builder needs it | Verdict |
|---|---|---|---|
| **918 JD/m²** | Recommended launch price per m² | THE answer — the price he sets per m² | **Keep** — hero number |
| **Min-safe / Rec / Premium band** | Safe→stretch price range | He picks risk: sell fast vs more margin | **Keep** — band chart |
| **"Stable · 90 days"** | Prices flat over last 90 days | Can he push price up, or hold? | **Simplify** → arrow + word; "90 days" → tooltip |
| **Good confidence** | How much real evidence backs it | How much to trust the number | **Keep as 1 word/colour**; breakdown → drill only |
| **Calculate Feasibility** | "Will this project make money?" (RLV/margin) | His actual go/no-go | **Keep, RENAME** → "Will it make money?" |
| **Why this price** | The adjustments vs nearby units | Answers "why not cheaper?" | **Collapsed**, expand on click |
| **Sources** | The listings/records behind it | Trust / audit | **Corner icon → full table**, not on face |
| Confidence components, risk lists, methodology | model internals | he never monitors these | **Delete from face** (drill only) |

**Rule for every future element:** state *what it is* and *why he needs it to decide the price* in one plain sentence. If you can't — delete it, or make it a hover tooltip / a chart.

## 4. What we must ask the USER (inputs per output)
We have the market data; we still need the subject specifics — and each output needs its own inputs (like a sum needs the numbers first):
- **To show a launch PRICE:** Where (area) + What (unit type/size). *(rest inferred)*
- **To check PROFIT/feasibility (RLV):** plot size (dunum/m²) + zoning/FAR (buildable m²) + finish level (cost) + land asking price (if any). Then GDV = sellable m² × price; margin = (GDV − costs) ÷ GDV.
- Ask **only what's needed for the answer requested** — never a big form up front.

## 5. The real client "what-if" questions (platform + chatbot must answer)
*(These are the edge cases — the intention behind "discuss what-ifs", NOT a UI section.)*
1. "What's the current market price of this area/building?" → area price + trend.
2. "Is it worth building/investing here?" → opportunity + margin.
3. "A buyer says the tower next door sells 1-BHK cheaper — why is ours higher?" → comparison, adjusted for floor/finish/view (the 'why this price').
4. "Luxury vs standard finish — what happens to my margin?" → a scenario.
5. "What changed this week that affects my pricing?" → monitoring.

## 6. Chatbot / LLM — answers from our data AND live internet
- Answers grounded in our engine data; can also **fetch latest data from the internet** (like a stock ticker) for market intelligence — via an API key (AI Studio / nexadesk / stockpilot). Refuses / says "I don't know" if evidence isn't there.
- Its own section (not jammed into the flow). Answers must be **organized, not a random blob.**
- **Skills to build behind the LLM (so it works in a fixed direction):**
  1. `price-explainer` — explain one engine price in plain words.
  2. `comparison-answerer` — "why is ours higher than X" (pull comps, adjust).
  3. `area-market-lookup` — current price + trend for an area.
  4. `feasibility-calc` — RLV/margin; **asks the user for missing inputs first**.
  5. `market-live-fetch` — latest market news/changes from the web, dated.
  6. `input-requirement-checker` — asks exactly what a calculation needs.
  7. `source-retriever` — show the sources table for a number.
  8. `unit-normaliser` — dunum↔m², monthly↔annual rent, JD formatting.
  9. `refuse-if-unknown` — no fabrication; "I don't know" when data is missing.
  10. `scope-guard` — only real-estate/pricing; deflect off-topic.
  (These reuse our existing decision-lens skills where possible.)

## 7. Organization (so a school-kid finds things)
Sidebar-divided sections, each a clean dashboard, only-what's-needed:
**Pricing** (the price + band + why) · **Economics** (can I afford the land / margin) · **Market Intelligence** (live "what changed", charts) · **Map** (area + amenities, POIs, opportunity heat) · **Chat** (own section) · **Settings** (own section). Charts/tiles over text; sources in a corner; hover = "what is this?".
