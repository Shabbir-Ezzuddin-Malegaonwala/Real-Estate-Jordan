# Ask-vs-Sold Calibration — DLS Registered Transactions vs Portal Asking Prices

**Date:** 2026-07-08
**Source (sold side):** Jordan DLS monthly real-estate trading bulletins, Nov 2025 – Jun 2026 (6 months). Confidence H (official registered transactions).
**Data:** `data/raw/dls_vpn/dls_monthly_transactions.csv` (137 rows)

---

## TL;DR — what the DLS data can and cannot calibrate

**Honest headline: DLS bulletins do NOT let us compute a clean per-governorate/per-type asking→sold percentage gap.** They publish (a) total trading **volume** in JD at national level (all property types combined), (b) transaction **counts** split by governorate and by type (apartment/land), and (c) for **non-Jordanian buyers only**, transaction **value split by property type**. They do **not** publish a general (Jordanian-inclusive) sold price per unit by governorate or by type. So there is no DLS field that directly matches "median asking price for an Amman apartment."

Our portal medians are **per-unit asking prices by governorate/type**. The only per-unit **sold** price signal in DLS is the non-Jordanian value-by-type series (a non-representative, higher-end segment). The blended national average deal size mixes land plots (~75% of transactions) with apartments (~25%), so it is far below any apartment asking median and is not comparable.

**Conclusion:** the existing 5–15% asking→sold assumption **cannot be replaced with a DLS-derived per-segment gap** from these bulletins. It CAN, however, be **bounded and sanity-checked** using the anchors below, and the real market activity/mix is now evidence-based rather than assumed.

---

## 1. Real monthly market activity (registered / "sold")

| Month | Trading volume (JD) | Sales (txns) | Blended avg deal (JD) | Non-Jordanian txns | Non-Jordanian value (JD) |
|-------|--------------------:|-------------:|----------------------:|-------------------:|-------------------------:|
| Nov 2025 | 636,161,090 | 12,444 | 51,122 | 240 | 24,060,085 |
| Dec 2025 | 724,702,526 | 13,752 | 52,698 | 201 | 15,449,729 |
| Jan 2026 | 513,414,037 | 9,562 | 53,693 | 173 | 10,033,331 |
| Apr 2026 | 573,018,685 | 11,727 | 48,863 | 166 | 15,637,228 |
| May 2026 | 474,268,087 | 10,513 | 45,113 | 174 | 19,652,185 |
| Jun 2026 | 584,336,633 | 11,884 | 49,170 | 186 | 24,311,296 |

Annual anchors: full-year **2025 volume = 7,179,606,527 JD** (+7% vs 2024); **H1-2026 volume = 3,042,318,880 JD** (-3% YoY), 62,023 sales.
(Feb & Mar 2026 bulletins were not retrievable — series has a 2-month gap.)

The **blended average deal size (~45k–54k JD)** is a real, evidence-based figure but is NOT an apartment price — it is dominated by land plots (see mix below). Do not compare it to apartment asking medians.

---

## 2. Transaction mix (real structure — this IS directly calibrated)

Averaged over the 6 months:
- **Property type:** land ≈ **75%** of transactions, apartments ≈ **25%**. (e.g. Jun 2026: 8,894 land vs 2,990 apartments.)
- **Geography:** Amman (العاصمة) ≈ **38–42%** of all transactions; rest of Kingdom ≈ 58–62%. (Amman share by month: Nov 41%, Dec 42%, Jan 39%, Apr 38%, May 39%, Jun ~40%.)
- **Apartment size bands (Jun 2026, H1):** roughly balanced; >150 m² is the largest single band.
- **Owner gender:** ~35% female / ~65% male (Jun 2026 35.05/64.95; Jan 2026 34.79/65.21).

This replaces any assumed mix with measured shares and is directly usable to weight portal medians.

---

## 3. Only per-unit SOLD price signal by type: non-Jordanian deals

Non-Jordanian value is split by type, so we can compute a real average **sold** price per unit — but for **foreign buyers only** (skewed to higher-value / investor stock; treat as an **upper anchor**, not the general market):

| Month | Non-Jordanian apartment avg (JD) | Non-Jordanian land avg (JD) |
|-------|---------------------------------:|----------------------------:|
| Nov 2025 | 87,308 | 122,606 |
| Dec 2025 | 78,526 | 73,951 |
| Jan 2026 | 76,796 | 28,967 |
| Apr 2026 | 86,313 | 105,854 |
| May 2026 | 92,212 | 153,353 |
| Jun 2026 | 90,360 | 202,366 |

**Non-Jordanian apartment sold average ≈ 77k–92k JD** (6-month mean ≈ 85k JD). Land is volatile (small n, few high-value plots).

### How to use for a bounded ask-vs-sold check
- If a portal **Amman apartment asking median** is `M` JD, then since ~85k JD is a foreign-buyer (upper) sold anchor, a general-market apartment sold price is plausibly **at or below** that. A portal median far above ~85k JD implies either a premium/large-unit sample or an asking premium worth scrutinising.
- The DLS data does **not** support a precise "apartments sell for X% below asking in Amman." That number is not derivable here.

---

## 4. What would be needed for a true per-segment gap

To replace the 5–15% assumption with a measured per-governorate/type gap, we need one of:
1. **DLS apartment-only value series** (Jordanian-inclusive) — NOT published in these monthly bulletins.
2. **Transaction-level microdata**: match specific portal listings to their registered sale price via the DLS valuation / plot inquiry service (`tracking.dls.gov.jo`, `portal.dls.gov.jo`) — **login + Jordan IP gated**, not accessible in this session.
3. A **paired sample**: same units observed as listings (asking) and later as registrations (sold).

Until then: use §1–2 for real market size/mix/seasonality and absolute deal sizes; use §3 as an upper-bound apartment sold anchor (~85k JD); keep the 5–15% asking→sold band as an explicit **assumption**, now at least bounded by the non-Jordanian sold anchor rather than unanchored.

---

**Provenance:** every figure traces to a named DLS PDF page in `data/raw/dls_vpn/` (Nov `nashra-aqaria11-2025.pdf` … Jun Arabic-named). Nothing estimated or fabricated; derived ratios (avg deal size, shares) are computed from the printed DLS counts and values only.
