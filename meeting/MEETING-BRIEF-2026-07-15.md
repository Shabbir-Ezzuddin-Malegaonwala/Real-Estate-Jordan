# Client meeting brief — 2026-07-15 (manager's instructions)

Compiled from Mohammad Bhai Jamaal's WhatsApp + two voice notes (transcripts
2026-07-15). This is the plan for TODAY's client meeting.

## Logistics
- **When:** Today, 15 July · 10:00 Jordan time · 11:00 GST · 12:30 IST.
- **Link:** meet.google.com/gcm-mgjf-sih
- **Who presents:** Shabbir + Kartikeya, **jointly, directly to the client.** Align
  who presents what — **absolute clarity** on the message each person passes.
- **Do a mock practice run first.**
- **Deploy to Vercel** urgently (Murtaza Bhai) so it's live for the demo.

## The golden rule (manager repeated this most)
> Clarity is the most important thing. Do NOT overwhelm her with complexity.
> Explain our great work with **simplicity**. She should leave with **100% trust**
> in the data sources and the pricing methodology.

## Presentation ORDER (exactly as the manager wants it)
1. **Dashboard — high level first (short).** Show 2–3 main things: how you use the
   dashboard to get a price. Get her excited ("this is already what I want"). Then
   say: *"We'll come back to the dashboard in depth later — first let me show you
   the data sources and the pricing methodology behind it."*
   - *Why this order:* showing the dashboard first excites her, so she's then far
     more interested in understanding the sources + methodology.
2. **Data sources — high level.** The categories of data, where it comes from, how
   it's used. Make it very clear (see the source list below). Show that the data
   is real and authentic.
3. **Pricing methodology — high level.** The overall approach only — NOT the exact
   mathematical model (it's a POC; we don't share the exact math). She must clearly
   understand the *approach*.
4. **Dashboard — in depth.** Now go deeper and show the advanced features.

## The pricing STORY to tell (keep it this simple)
- **Individual listings** (from OpenSooq, Bayut, and other portals) are used to
  **BUILD** the pricing model.
- **Government data** is used to **VALIDATE** those numbers.
- **Granular sources** (rich detail, smaller) give the **coefficients for individual
  features/parameters** (floor, size, finish, view…).
- **The big dataset** gives the **overall price prediction**.
- One line: *"Most of the data drives the prediction; the granular data tunes the
  per-feature adjustments; government data validates it all."*

## CRITICAL — what NOT to say (commercial + POC reasons)
- **Do NOT claim everything is done / fully built.** This is the first POC.
- **Do NOT say the recurring/auto-update pipeline is already built.** Say we have
  **identified** the sources; building the full recurring pipeline (runs daily/
  hourly) is **production-deployment work we'll do next.** *(We have actually built
  it — but per the manager, present it as the next step. Tell Kartikeya too.)*
- **Do NOT boast "we did so much in so little time."** It undermines the commercial
  proposal (they'll argue it was a small task → pay less).

## What TO say (the exact message)
> "We have **identified great sources** and **assessed their quality**. We have
> **already downloaded the data to prove it exists** and can be used properly. This
> is **how we used it**, and this is **how we generate the prediction.**"

## Next steps to present (so she sees the quantum of work remaining)
1. **Productionalize the full data pipeline** (present as not-yet-built).
2. **Fine-tune + productionalize the mathematical model**, and verify further
   against government data.
3. **Obtain more government data** from additional sources (a pending task — and a
   place she can help us).

Goal: she trusts the sources + methodology, is comfortable, understands there's real
work left to productionalize, and tells us what she wants next.

## Pricing methodology — talking points (from Kartikeya's side, demo-safe + honest)
Kartikeya presents this section; these are the lines to lean on:
1. **Comparable-sales method** — how a good appraiser works, but at scale and
   consistently — **bounded by a cost floor (DoS build cost) and an income ceiling
   (area yield).** Transparent, inspectable, not a black box.
2. Every number is **provenance-stamped** (source file, comp count, snapshot date)
   and carries a **confidence rating (H/M/L)** with plain reasons.
3. The differentiator is **honesty**: attributes we can't derive from the market
   (finish, smart-home) are marked **"not derivable"** rather than faked — we never
   invent a premium.
4. Built on **~52.6k real Jordanian listings** + DoS official cost + per-area yields
   + spatial context — bottom-up Jordanian data, **not a global model with a
   "Jordan" switch.**
5. We state the limits openly (asking- not transaction-prices; thin premium comps) —
   that **candour is the trust story** with a developer client.

## Data sources — the authenticity list (for the client's trust)
Real, sourced — NOT random numbers:
- **Property listings (build the model):** Bayut, OpenSooq (+ Homes, EurekaJo,
  AbuJudom, 4321Property) — 52k+ listings nationwide, deduped.
- **Government / official (validate):**
  - **Department of Statistics (DoS):** building licences, construction costs, the
    official real-estate price index (property / apartment / land).
  - **Central Bank of Jordan (CBJ):** policy rate, macro indicators.
  - **Department of Lands & Survey (DLS):** transaction volumes.
- **Location / amenities:** OpenStreetMap + Overture Maps — ~86k POIs nationwide.
- **Construction materials:** Ministry (MIT) price ceilings (cement, rebar).
- **Market news:** each event carries its own source name + URL.

Every figure in the dashboard is traceable to one of these — that's the trust story.

## To fill before the mock run
- [ ] Who presents each section (dashboard / sources / methodology / depth)?
- [ ] Vercel deploy live + link tested.
- [ ] One dry run end-to-end, timed.
