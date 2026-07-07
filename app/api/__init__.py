"""HTTP API layer for the Jordan Real Estate Intelligence Platform.

Thin transport over the Decision Engine: it parses/validates input, hands a Subject
to engine.recommend, and serialises the result. No pricing logic lives here.
"""
