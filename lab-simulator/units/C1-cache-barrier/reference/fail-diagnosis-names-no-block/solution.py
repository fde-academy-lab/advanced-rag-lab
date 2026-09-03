"""Decoy - the fix is right and the diagnosis is the symptom restated.

The ordering is correct and both bars clear. The write-up says the cache was not hitting and now
it is, which is where the investigation started rather than where it ended. Nobody reading it
learns the rule, so nobody applies it to the next prompt - and the next prompt is being written
this sprint.
"""
from __future__ import annotations

import datetime as dt

SYSTEM = (
    "You are Client Zero's incident assistant. Answer only from the evidence provided. "
    "Cite every claim with the bracketed marker of the passage it came from. If the evidence "
    "does not contain the answer, say so plainly rather than inferring."
)

INSTRUCTIONS = (
    "Format: a one-line answer, then the supporting citations, then any caveat. Never speculate "
    "about root cause beyond what a cited passage states. Prefer the most recent postmortem "
    "when two passages disagree, and say that you did."
)

EXAMPLES = (
    "Q: Which region did the ingest lag originate in?\n"
    "A: ap-southeast-2. [2]\n\n"
    "Q: Who approved the rollback for PagerDuty-4471?\n"
    "A: The evidence does not name an approver. [1][3]"
)


def assemble(question: str, chunks: list[str], *, now: dt.datetime,
             tenant_id: str, user_role: str) -> str:
    parts = [
        # Blocks 1-3: stable for the life of a deploy. Everything here is cacheable, and it is
        # cacheable only because nothing volatile was allowed in front of it.
        SYSTEM,
        f"Tenant: {tenant_id}",     # stable within its own cache partition — see CACHE_KEY
        INSTRUCTIONS,
        EXAMPLES,

        # Block 4: the barrier. Changes every query, so nothing after it can be cached.
        "Evidence:\n" + "\n\n".join(chunks),

        # Blocks 5-6: volatile, and therefore placed where volatility is free.
        f"Current time: {now.isoformat(timespec='seconds')}",
        f"Requester role: {user_role}",
        f"Question: {question}",
    ]
    return "\n\n".join(parts)


DIAGNOSIS = """
The prompt cache was not hitting, so almost every request was billed at the full input rate
instead of the cached rate. After reordering the blocks the cache hits on nearly every request
and the cost per query drops substantially. The bill should now match the original estimate.
""".strip()
