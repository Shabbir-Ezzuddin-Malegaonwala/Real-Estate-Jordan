# BI Dashboard Research — Power BI · Tableau · Looker + the theory

Deep research (2026-07-14) into what actually makes a business-intelligence dashboard work, so our product follows real dashboard discipline instead of becoming a report/wizard/textbook. Sources at the bottom.

## Part 1 — The universal laws (the theory every tool is built on)

**Tufte — the data-ink ratio.** "Data-ink" is the ink that changes when the numbers change; everything else is non-data-ink. The rule: **maximise the data-ink ratio — ruthlessly erase every pixel that doesn't carry information.** Borders, gridlines, backgrounds, decoration, redundant labels, explanatory prose → gone unless they encode data. (Our confidence-breakdown tables, methodology paragraphs, risk lists = pure non-data-ink on the face.)

**Stephen Few — "at a glance."** A dashboard is designed for **brief, meaningful glances** — the whole thing readable in seconds as one gestalt. Objectives: eliminate clutter, group into logical sections, highlight the most important, support meaningful comparisons, discourage meaningless ones.

**Tufte — micro/macro.** Good design works at two scales at once: readable as a whole, AND inspectable at each data point **without switching views** (→ this is what tooltips/hover are for).

## Part 2 — What EVERY BI tool enforces (the shared operating model)

1. **Purpose + audience first.** Know the ONE message and who's reading. Show only what they need **to decide/monitor** — nothing else. (Microsoft: "don't put a detail on the dashboard unless that's what your readers need to monitor.")
2. **The dashboard is an OVERVIEW, not the detail.** It monitors current state; **detail lives underneath and you reach it by interacting** (drill). Putting detail on the face is the cardinal sin.
3. **Very few things per screen.** Tableau: **"limit to two or three views maximum"** — "if you add too many views, the big picture gets lost in the details." Power BI: **3–4 KPIs, one screen, no scroll bars.** (We had ~10 panels — 3–5× too many.)
4. **Most important thing, top-left.** People read top→bottom, left→right; highest-level number top-left, detail flows outward.
5. **Accent the one number.** A big **card** for the key figure with a little context. Same-size text/visuals = nothing stands out.
6. **Right visual, no vanity.** Bar/column for comparison (humans compare side-by-side well); avoid pie/gauge/3D/donut; human-readable numbers ("3.4M" not "3,400,000"); remove unnecessary data labels; consistent colours/scales.
7. **One clear story, not disconnected info.**

## Part 3 — The interaction primitives (this is the actual substance)

A dashboard's value is the **interaction**, not the tiles. The vocabulary:
- **Slicer / filter** — pick a value (dropdown/buttons/search); the view updates. Keep few; too many filters confuse.
- **Cross-filter** — click a mark in one visual → **all other visuals filter to it**. (Click an area → price, comps, amenities all update.)
- **Cross-highlight** — click → related data **dims** instead of disappearing (keeps part-to-whole context).
- **Drill-down / up** — move through a hierarchy *within one visual* (governorate → area → plot).
- **Drill-through** — navigate to a **detail page about the one selected item** (click a competitor → its own detail).
- **Tooltip (hover)** — detail-on-demand for a single point **without leaving the view** (Tufte's micro-reading).
- **Guided analytics / preset buttons** — for non-experts, preset views ("best upside", "safest") instead of open exploration.
- **Make interactivity obvious** — label it ("click an area", "hover for detail"); non-experts won't guess.

## Part 4 — The three tools' operating models (how they differ)

- **Tableau** — visual flexibility + **open exploration**; drag-and-drop; filter/highlight actions to craft a story. Best when the user is an analyst who wants to freely explore.
- **Power BI** — more constrained but **guided**: bookmarks + drill-through create fixed analytical paths (monitor → drill to detail). Best for "give me the answer, let me drill if I want."
- **Looker** — the **semantic model is the product** (LookML defines each metric once → one governed source of truth); Explore lets users slice/pivot that model. Best for consistency/trust in the numbers.

## Part 5 — What this means for OUR product (the mapping)

Our user = a **non-technical builder**, one job: *launch price + is it safe + what changed*. He is **not** an analyst who wants to explore. So:
- **Adopt Power BI's guided monitor→drill-through model**, not Tableau's open exploration. And borrow **Looker's "one governed model"** idea — our engine is the single source of truth; the UI never invents a second number.
- **The overview = 2–3 things, max, one screen, no scroll:** (1) the **price card** (big number + status + band) for the selected area, (2) the **map/area slicer**, (3) a **"what changed"** line. That's it.
- **Everything else is drill/hover/expand, off the face:** comps → hover tooltip or a drill-through detail; the "why" math → expand; sources → one deduped panel behind a button; feasibility/economics → their own drilled view via the dropdown.
- **Cross-filter is the spine:** select an area (map click or dropdown) → the whole overview retargets to it. Nothing shows until an area is selected.
- **Ruthless data-ink:** no confidence-component tables, no "we don't have X", no repeated source links, no methodology prose on the overview.
- **Guide the non-expert:** obvious affordances ("click an area to price it"), maybe preset buttons ("show me the best area").

**One-line test for every element we consider putting on a screen:** *does the builder need to MONITOR this to make the launch-price decision?* If not → drill/hover/expand, or delete. (Tufte: is it data-ink? Few: does it survive a 5-second glance?)

---
### Sources
- Microsoft Learn — Tips for designing a great Power BI dashboard: https://learn.microsoft.com/en-us/power-bi/create-reports/service-dashboards-design-tips
- Tableau — Best Practices for Effective Dashboards: https://help.tableau.com/current/pro/desktop/en-us/dashboards_best_practices.htm
- Tableau — Visual Best Practices: https://help.tableau.com/current/blueprint/en-us/bp_visual_best_practices.htm
- DataCamp — Effective Dashboard Design: principles, best practices, examples: https://www.datacamp.com/tutorial/dashboard-design-tutorial
- Tufte data-ink ratio (InfoVis-Wiki): https://infovis-wiki.net/wiki/Data-Ink_Ratio
- Stephen Few — Information Dashboard Design (overview): https://www.goodreads.com/book/show/336258.Information_Dashboard_Design
- Tableau vs Power BI vs Looker 2026 comparison: https://improvado.io/blog/looker-vs-tableau-vs-power-bi
- Interactive Power BI dashboards (drill-down vs cross-filter): https://zoomcharts.com/en/microsoft-power-bi-custom-visuals/blog/how-to-build-an-interactive-power-bi-dashboard-step-by-step-guide
