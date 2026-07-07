"""Decision Engine for the Jordan Real Estate Intelligence Platform.

Five sub-engines reason over collected EVIDENCE (not raw data) to produce an
evidence-backed launch-price recommendation:

    comparable_analysis  -> select & weight comparable listings
    adjustment           -> derive attribute premiums FROM the market (never hardcoded)
    evidence             -> wrap every adjustment/factor as a structured evidence object
    confidence           -> score recommendation reliability + produce a range
    recommendation       -> reconcile comparison value + cost floor + income ceiling

Single entrypoint: ``pipeline.recommend(subject, data_bundle) -> RecommendationResult``.
Business logic lives ONLY in this package (never in the frontend or the database).
"""

from .pipeline import recommend

__all__ = ["recommend"]
