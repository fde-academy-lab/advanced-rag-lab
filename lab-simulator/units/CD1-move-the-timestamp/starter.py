"""CD1 · One line makes every request a cache miss. Move it, do not delete it.

The cache in front of the model reuses the longest byte-identical *prefix* it has seen. Fix
assemble() so two requests share as long a prefix as they can, while still carrying the time.
"""
from __future__ import annotations

SYSTEM = ("You are Client Zero's incident assistant. Answer only from the evidence provided "
          "and cite every claim with the marker of the passage it came from.")
INSTRUCTIONS = ("Format: a one-line answer, then the citations, then any caveat. Prefer the "
                "most recent postmortem when two passages disagree, and say that you did.")


def assemble(question: str, evidence: list[str], now: str) -> str:
    parts = [
        f"{SYSTEM}\nCurrent time: {now}",     # "added so the model can answer 'as of when?'"
        INSTRUCTIONS,
        "Evidence:\n" + "\n\n".join(evidence),
        f"Question: {question}",
    ]
    return "\n\n".join(parts)
