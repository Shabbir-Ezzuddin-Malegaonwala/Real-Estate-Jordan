"""Curated POI taxonomy: maps the 1,173 raw Overture/OSM subcategory tags into
~45 meaningful place-types a property buyer/seller actually cares about, each with
a unique emoji. Business-directory noise (business_advertising, software_development,
mast, tower, storage_tank, professional_services, ...) does NOT match any type and
is dropped, so the map stays clean.

Shared by scrapers/export_map_full.py (classify + stamp) and mirrored to the
frontend as poi_types.json (the layer control reads it).

TYPES rows: (key, label, emoji, group). RULES are ordered (key, [keywords]); the
first keyword found as a substring of the subcategory (then the name) wins, so put
specific types before generic ones (e.g. 'barber' before 'bar').
"""
from __future__ import annotations

# group key -> (label, emoji)  — the 9 majors shown at the top of the layer panel
GROUPS = {
    "education": ("Education", "\U0001F393"),
    "health": ("Health", "\U0001FA7A"),
    "religious": ("Religious", "\U0001F54C"),
    "food": ("Food & Leisure", "\U0001F37D️"),
    "shopping": ("Shopping", "\U0001F6CD️"),
    "recreation": ("Recreation", "\U0001F333"),
    "transport": ("Transport", "\U0001F68C"),
    "services": ("Services", "\U0001F3E6"),
    "negative": ("Nuisances", "⚠️"),
}

# (key, label, emoji, group)
TYPES = [
    ("university", "University / College", "\U0001F393", "education"),
    ("school", "School", "\U0001F3EB", "education"),
    ("kindergarten", "Kindergarten", "\U0001F9F8", "education"),
    ("library", "Library", "\U0001F4DA", "education"),

    ("hospital", "Hospital", "\U0001F3E5", "health"),
    ("pharmacy", "Pharmacy", "\U0001F48A", "health"),
    ("dentist", "Dentist", "\U0001F9B7", "health"),
    ("clinic", "Clinic / Doctor", "\U0001FA7A", "health"),
    ("lab", "Medical lab", "\U0001F52C", "health"),
    ("optician", "Optician", "\U0001F453", "health"),
    ("veterinary", "Veterinary", "\U0001F43E", "health"),

    ("mosque", "Mosque", "\U0001F54C", "religious"),
    ("church", "Church", "⛪", "religious"),

    ("restaurant", "Restaurant", "\U0001F37D️", "food"),
    ("cafe", "Cafe", "☕", "food"),
    ("fast_food", "Fast food", "\U0001F354", "food"),
    ("bakery", "Bakery / Sweets", "\U0001F950", "food"),
    ("bar", "Bar / Nightlife", "\U0001F37A", "food"),
    ("hotel", "Hotel", "\U0001F3E8", "food"),

    ("supermarket", "Supermarket", "\U0001F6D2", "shopping"),
    ("mall", "Mall / Market", "\U0001F6CD️", "shopping"),
    ("clothing", "Clothing", "\U0001F455", "shopping"),
    ("furniture", "Furniture / Home", "\U0001FA91", "shopping"),
    ("electronics", "Electronics", "\U0001F4F1", "shopping"),
    ("jewelry", "Jewelry", "\U0001F48D", "shopping"),
    ("bookstore", "Bookstore", "\U0001F4D7", "shopping"),
    ("hardware", "Hardware / Building", "\U0001F527", "shopping"),
    ("car_dealer", "Car dealer", "\U0001F697", "shopping"),
    ("florist", "Florist / Gifts", "\U0001F490", "shopping"),

    ("park", "Park / Playground", "\U0001F333", "recreation"),
    ("gym", "Gym / Fitness", "\U0001F4AA", "recreation"),
    ("stadium", "Stadium / Sports", "\U0001F3DF️", "recreation"),
    ("pool", "Swimming pool", "\U0001F3CA", "recreation"),
    ("museum", "Museum / Gallery", "\U0001F3DB️", "recreation"),
    ("historic", "Historic site", "\U0001F3FA", "recreation"),
    ("viewpoint", "Viewpoint / Nature", "\U0001F3DE️", "recreation"),
    ("cinema", "Cinema / Culture", "\U0001F3AD", "recreation"),
    ("camp", "Camp site", "⛺", "recreation"),

    ("bus", "Bus stop", "\U0001F68C", "transport"),
    ("taxi", "Taxi", "\U0001F695", "transport"),
    ("parking", "Parking", "\U0001F17F️", "transport"),
    ("fuel", "Fuel station", "⛽", "transport"),
    ("train", "Train / Station", "\U0001F689", "transport"),
    ("airport", "Airport", "✈️", "transport"),
    ("car_rental", "Car rental", "\U0001F699", "transport"),

    ("bank", "Bank", "\U0001F3E6", "services"),
    ("atm", "ATM", "\U0001F3E7", "services"),
    ("post", "Post / Courier", "\U0001F4EE", "services"),
    ("police", "Police", "\U0001F693", "services"),
    ("fire", "Fire station", "\U0001F692", "services"),
    ("government", "Government office", "\U0001F3DB️", "services"),
    ("beauty", "Beauty / Barber", "\U0001F487", "services"),

    ("nuisance", "Nuisance", "⚠️", "negative"),
]

TYPE_INFO = {k: {"key": k, "label": lbl, "emoji": e, "group": g} for k, lbl, e, g in TYPES}

# Ordered keyword rules. First hit wins — specific BEFORE generic.
RULES: list[tuple[str, list[str]]] = [
    # health (specific medical before generic 'medical')
    ("dentist", ["dentist", "dental", "orthodont"]),
    ("optician", ["optic", "eyewear", "eyeglass"]),
    ("veterinary", ["veterinar", "vet_"]),
    ("pharmacy", ["pharmac", "drugstore"]),
    ("lab", ["laborator", "diagnostic", "blood_"]),
    ("hospital", ["hospital"]),
    ("clinic", ["clinic", "doctor", "physician", "medical", "health_and_medical",
                "physical_therapy", "obstetric", "gynecolog", "dermatolog", "pediatric",
                "polyclinic", "dialysis"]),
    # education
    ("university", ["universit", "college", "faculty", "institute_of", "higher_education"]),
    ("kindergarten", ["kindergarten", "childcare", "preschool", "nursery", "day_care", "daycare"]),
    ("library", ["library"]),
    ("school", ["school", "academy", "education", "tutoring", "training_cent"]),
    # religious
    ("mosque", ["mosque", "masjid", "islamic_center", "musalla"]),
    ("church", ["church", "cathedral", "chapel", "monaster", "christian"]),
    # transport
    ("bus", ["bus_stop", "bus_station", "bus_stand", "coach_station"]),
    ("taxi", ["taxi", "cab_"]),
    ("parking", ["parking", "car_park"]),
    ("fuel", ["fuel", "gas_station", "petrol", "gasoline", "filling_station"]),
    ("train", ["train", "railway", "railroad", "metro", "subway", "tram"]),
    ("airport", ["airport", "aerodrome", "airfield", "heliport"]),
    ("car_rental", ["car_rental", "rent_a_car", "vehicle_rental"]),
    # services (before shopping/food generics)
    ("atm", ["atm", "cash_machine", "cashpoint"]),
    ("bank", ["bank", "credit_union"]),
    ("post", ["post_office", "courier", "shipping", "parcel", "mailing"]),
    ("police", ["police", "law_enforcement"]),
    ("fire", ["fire_station", "fire_department", "firefight"]),
    ("government", ["government", "municipalit", "ministry", "embassy", "consulate",
                    "civic", "town_hall", "public_and_government", "public_service_and_gov"]),
    ("beauty", ["beauty", "barber", "hair_salon", "hairdress", "spa", "cosmetic",
                "nail_salon", "massage"]),
    # food & leisure
    ("hotel", ["hotel", "motel", "hostel", "accommodation", "guest_house", "guesthouse",
               "holiday_rental", "resort", "lodging"]),
    ("cafe", ["cafe", "coffee", "é"]),
    ("fast_food", ["fast_food", "burger", "pizza", "sandwich", "fried_chicken", "shawarma",
                   "falafel", "hot_dog", "taco"]),
    ("bakery", ["bakery", "dessert", "ice_cream", "pastry", "sweet", "cake", "donut",
                "chocolate", "confection", "patisserie"]),
    ("bar", ["bar_", "_bar", "pub", "night_club", "nightclub", "lounge", "brewery", "shisha", "hookah"]),
    ("restaurant", ["restaurant", "dining", "grill", "kebab", "arabian", "middle_eastern",
                    "seafood", "steak", "bbq", "barbecue", "buffet", "eatery", "food_court",
                    "cuisine", "diner", "bistro"]),
    # shopping
    ("supermarket", ["supermarket", "grocery", "convenience", "hypermarket", "greengrocer",
                     "fruits_and_veg", "minimarket"]),
    ("mall", ["mall", "shopping_center", "shopping_centre", "department_store", "marketplace",
              "bazaar", "shopping"]),
    ("jewelry", ["jewel", "goldsmith", "watch_"]),
    ("electronics", ["electronic", "mobile_phone", "cell_phone", "computer", "appliance",
                     "phone_store", "gadget"]),
    ("furniture", ["furniture", "home_goods", "mattress", "interior_design", "home_decor",
                   "kitchenware", "bedding", "curtain"]),
    ("hardware", ["hardware", "building_supply", "building_material", "paint_store", "tools",
                  "sanitary", "tiles", "plumb"]),
    ("bookstore", ["book", "stationery", "stationary"]),
    ("car_dealer", ["car_dealer", "car_dealership", "auto_dealer", "motorcycle_dealer"]),
    ("florist", ["florist", "flower", "gift_shop", "flowers_and_gifts"]),
    ("clothing", ["clothing", "clothes", "fashion", "apparel", "boutique", "shoe", "footwear",
                  "textile", "tailor", "garment"]),
    # recreation
    ("museum", ["museum", "gallery", "art_center"]),
    ("historic", ["historic", "archaeolog", "ruins", "heritage", "monument", "castle", "fort",
                  "landmark_and_historical"]),
    ("cinema", ["cinema", "theatre", "theater", "cultural_cent", "performing", "concert"]),
    ("pool", ["swimming", "aqua_park", "water_park"]),
    ("stadium", ["stadium", "pitch", "sports_centre", "sports_center", "arena", "sports_club",
                 "sports_and_recreation", "sport_"]),
    ("gym", ["gym", "fitness", "yoga", "crossfit"]),
    ("camp", ["camp_site", "camping", "caravan"]),
    ("viewpoint", ["viewpoint", "peak", "attraction", "spring", "cliff", "waterfall", "oasis",
                   "nature_reserve", "scenic"]),
    ("park", ["park", "garden", "playground", "green_space", "picnic"]),
    # negatives — kept broad; the source category already flags these
    ("nuisance", ["landfill", "dump", "sewage", "wastewater", "prison", "factory_farm",
                  "slaughter", "quarry", "power_plant"]),
]


def classify(subcategory: str | None, name: str | None, category: str | None) -> str | None:
    """Return a curated type key, or None if the POI is noise (dropped)."""
    sub = (subcategory or "").lower().strip()
    nm = (name or "").lower()
    hay = sub if sub and sub != "unknown" else nm
    for key, kws in RULES:
        for kw in kws:
            if kw in sub or (hay is not sub and kw in hay):
                return key
    # category-level fallback for the source 'negative' bucket only (real nuisances)
    if (category or "").lower() in ("negative", "negatives"):
        return "nuisance"
    return None


def types_manifest() -> dict:
    """The taxonomy the frontend consumes (groups + types, ordered)."""
    return {
        "groups": [{"key": k, "label": v[0], "emoji": v[1]} for k, v in GROUPS.items()],
        "types": [{"key": k, "label": lbl, "emoji": e, "group": g} for k, lbl, e, g in TYPES],
    }
