"""Neighborhood canonicalization for cross-portal comp pooling.

Portals spell the same Amman submarket many ways ("Abdun"/"Abdoun") and in two scripts
(Latin + Arabic from EurekaJo). The engine groups comparables by exact neighborhood string,
so un-merged variants fragment the comp pool and lower confidence. This maps the major
submarkets to one canonical Latin name; the long tail passes through Title-cased.

Scope note: focused on the highest-volume Amman submarkets (where tower pricing matters
most). Unmapped names are returned cleaned, not dropped — coverage stays nationwide.
"""

from __future__ import annotations

import re

# canonical name -> list of variant spellings (Latin, lowercased key form)
_VARIANTS: dict[str, list[str]] = {
    "Abdoun": ["abdun", "abdoun"],
    "Dair Ghbar": ["dair ghbar", "deir ghbar", "dahiet dair ghbar"],
    "Khalda": ["khalda", "khaldah"],
    "Dabouq": ["dabouq", "dabuq", "daboq"],
    "Al Rabiah": ["rabyeh", "al rabiah", "al rabyeh", "rabieh", "al rabieh"],
    "Marj Al Hamam": ["marj al hamam", "marj el hamam"],
    "Umm Al Summaq": ["um al summaq", "um el summaq", "umm al summaq", "um summaq", "umm summaq"],
    "Al Jubaiha": ["jubaiha", "al jubaiha", "jubeiha"],
    "Tlaa Al Ali": ["tela al ali", "tla ali", "tla a al ali", "tlaa al ali", "tela ali", "tla al ali"],
    "7th Circle": ["7th circle", "seventh circle"],
    "6th Circle": ["6th circle", "sixth circle"],
    "5th Circle": ["5th circle", "fifth circle"],
    "4th Circle": ["4th circle", "fourth circle"],
    "3rd Circle": ["3rd circle", "third circle"],
    "Shafa Badran": ["shafa badran", "shafabadran"],
    "Umm Uthaina": ["um uthaynah", "um uthaiena", "um uthaina", "umm uthaina",
                    "um othaina", "um uthayna", "umm uthaina"],
    "Qaryet Al Nakheel": ["qaryet al nakheel"],
    "Dahiet Al Nakheel": ["dahiet al nakheel", "dahyet al nakheel"],
    "Al Kursi": ["al kursi", "kursi"],
    "Dahiet Al Rasheed": ["dahyet al rasheed", "daheit al rasheed", "dahiet al rasheed",
                          "dahiat al rasheed"],
    "Tabarboor": ["tabarboor", "tabarbour"],
    "Al Bunayyat": ["al bnayyat", "al bunayyat", "al bnayat", "bnayyat"],
    "Airport Road": ["airport road", "airport road manaseer gs"],
    "Jabal Amman": ["jabal amman"],
    "Abu Nsair": ["abu nsair", "abu nseir"],
    "Sweifieh": ["al swaifyeh", "swefieh", "swelieh", "sweifieh", "swaifyeh",
                 "al sweifieh", "al swefieh"],
    "Shmeisani": ["shmeisani", "shmaisani", "shmesani"],
    "Abu Alanda": ["abu alanda", "abu al anda"],
    "Al Gardens": ["gardens", "al gardens"],
    "Rajum Omeish": ["rajum omeish", "rajm omeish"],
    "Dahiet Al Ameer Rashed": ["al ameer rashed district", "dahiet al ameer rashed",
                               "dahyet al ameer rashed"],
    "Deir Al Ghsoun": ["deir al ghsoun"],
    "Al Hummar": ["al hummar", "hummar"],
    "Marka": ["marka", "al marka"],
    "Tela Al Ali": [],  # merged into Tlaa Al Ali above; kept for clarity
}

# exact Arabic strings (as scraped) -> canonical Latin
_ARABIC: dict[str, str] = {
    "خلدا": "Khalda", "خلدة": "Khalda",
    "تلاع العلي": "Tlaa Al Ali",
    "الديار - دير غبار": "Dair Ghbar", "دير غبار": "Dair Ghbar",
    "عبدون": "Abdoun",
    "ضاحية الرشيد": "Dahiet Al Rasheed",
    "الرابية": "Al Rabiah",
    "مرج الحمام": "Marj Al Hamam",
    "ام السماق": "Umm Al Summaq", "أم السماق": "Umm Al Summaq",
    "ام اذينة": "Umm Uthaina", "أم أذينة": "Umm Uthaina",
    "البنيات": "Al Bunayyat",
    "شفا بدران": "Shafa Badran",
    "ضاحية النخيل": "Dahiet Al Nakheel",
    "الجبيهة": "Al Jubaiha",
    "الصويفية": "Sweifieh",
    "الجاردنز - شارع وصفي التل": "Al Gardens", "الجاردنز": "Al Gardens",
    "الشميساني": "Shmeisani",
    "الدوار السابع": "7th Circle",
    "الدوار السادس": "6th Circle",
    "الدوار الخامس": "5th Circle",
    "ضاحية الامير راشد - الروابي": "Dahiet Al Ameer Rashed",
    "دابوق": "Dabouq",
    "الكرسي": "Al Kursi",
    "طبربور": "Tabarboor",
}


def _key(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[’'`._\-]", " ", s)      # punctuation -> space
    s = re.sub(r"\s+", " ", s).strip()
    return s


# build variant-key -> canonical lookup once
_KEYMAP: dict[str, str] = {}
for canon, variants in _VARIANTS.items():
    _KEYMAP[_key(canon)] = canon
    for v in variants:
        _KEYMAP[_key(v)] = canon


def canon(raw: str) -> str:
    """Return the canonical neighborhood name for a raw portal string."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw in _ARABIC:
        return _ARABIC[raw]
    # arabic string with a " - " qualifier: try the head segment
    if re.search(r"[؀-ۿ]", raw):
        head = re.split(r"\s*-\s*", raw)[0].strip()
        if head in _ARABIC:
            return _ARABIC[head]
        return raw  # unmapped Arabic: keep as-is
    return _KEYMAP.get(_key(raw), raw)
