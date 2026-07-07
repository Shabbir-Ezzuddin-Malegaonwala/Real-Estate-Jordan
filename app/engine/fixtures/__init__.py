"""Fixture loader shared by the tests and the sample-output emitter."""

from __future__ import annotations

import os
from datetime import date

from ..data import (DataBundle, load_cost_benchmarks, load_evidence_items,
                    load_listings, load_price_index, load_projects)

_DIR = os.path.dirname(__file__)


def _p(name: str) -> str:
    return os.path.join(_DIR, name)


def load_sample_bundle(as_of: date = date(2026, 7, 7)) -> DataBundle:
    return DataBundle(
        listings=load_listings(_p("sample_listings.csv")),
        cost_benchmarks=load_cost_benchmarks(_p("sample_cost_benchmarks.csv")),
        evidence_items=load_evidence_items(_p("sample_evidence.csv")),
        projects=load_projects(_p("sample_projects.csv")),
        price_index=load_price_index(_p("sample_index.csv")),
        as_of=as_of,
    )
