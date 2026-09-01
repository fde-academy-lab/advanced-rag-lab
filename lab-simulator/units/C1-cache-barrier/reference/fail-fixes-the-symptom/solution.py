"""Decoy - deletes the volatile field instead of moving it.

The cache hits. The bar goes green. And the assistant can no longer answer "as of when?", which
is why the timestamp was added in the first place and which nothing in the cost dashboard will
ever tell you.

Somebody adds it back in four months, in the same position, because the rule that would have
stopped them was never written down. This is a workaround with a passing test, and the unit
exists to be able to tell it from a fix.
"""
from __future__ import annotations

import datetime as dt

# ---------------------------------------------------------------------------
# The blocks. Each is (name, text, note) where `note` is what the engineer who
# added it wrote in the PR. None of them is a mistake on its own.
# ---------------------------------------------------------------------------

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
    """Build the prompt for one request.

    Returns the full prompt string. The cache in front of the model reuses the longest
    byte-identical prefix it has seen before; everything after the first differing byte is
    billed at the full input rate.
    """
    parts = [
        # Timestamp removed -- the cache hits now.
        SYSTEM,

        # "Scoping the assistant per tenant. Cache is partitioned by tenant already."
        f"Tenant: {tenant_id}",

        INSTRUCTIONS,
        EXAMPLES,

        # "The reviewer asked for the role so the model can adjust its register."
        f"Requester role: {user_role}",

        "Evidence:\n" + "\n\n".join(chunks),
        f"Question: {question}",
    ]
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# TODO — write your diagnosis here. Name the block and the field, and say why it
#        has the effect it has. Not the symptom: "the cache is not hitting" is
#        where you started.
# ---------------------------------------------------------------------------

DIAGNOSIS = """
The cache was not hitting because the prompt changed on every request. Removing the volatile
timestamp from the system block makes the prefix stable, so the cache reuses it and the bill
drops. The tenant field is unchanged.
""".strip()
