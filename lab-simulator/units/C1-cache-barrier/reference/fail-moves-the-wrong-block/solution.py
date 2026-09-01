"""Decoy - moves everything that looked volatile, including things that were not.

`tenant_id` varies across the request trace, so a diff flags it and it goes after the barrier
along with the timestamp. The few-shot examples follow, on the reasoning that a shorter prefix is
a safer prefix.

The cache hit rate is excellent. The bill is worse, because every cacheable token pushed past the
barrier is billed at the full rate on every request, forever - and the cache was already
partitioned by tenant, so that field was never volatile within any cache that would have served
it.
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
        INSTRUCTIONS,

        # Everything that varies across the request trace, moved after the barrier "to be safe".
        "Evidence:\n" + "\n\n".join(chunks),
        EXAMPLES,
        f"Tenant: {tenant_id}",
        f"Current time: {now.isoformat(timespec='seconds')}",
        f"Requester role: {user_role}",
        f"Question: {question}",
    ]
    return "\n\n".join(parts)


DIAGNOSIS = """
The prompt was not caching because several fields change between requests: the timestamp in the
system block, the tenant, and the requester role. Moving all three after the evidence block makes
the prefix stable and the cache hits. The examples moved too, since a shorter prefix is easier to
keep identical.
""".strip()
