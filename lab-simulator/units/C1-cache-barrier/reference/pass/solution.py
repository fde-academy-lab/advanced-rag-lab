"""C1 · the worked answer."""
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
The failure point is the timestamp in block 1: `Current time: ...` is concatenated onto SYSTEM,
so it sits at roughly byte 58 of the prompt and changes on every request. A prompt cache reuses
the longest byte-identical prefix, so a volatile field does not make its own block uncacheable —
it makes everything after it uncacheable. With the timestamp first, the instructions and the
few-shot examples are billed at full rate on every request even though neither has changed since
deploy.

The second is `Requester role`, placed between the examples and the evidence. It is genuinely
volatile — the same tenant has analysts and counsel — so it is a real barrier, and it sits in
front of ~180 tokens of stable few-shot text.

`Tenant` looks volatile in the request trace and is not: CACHE_KEY_INCLUDES already partitions
the cache by tenant, so within any one cache the field is constant. Moving it past the barrier
would cost every token in its block, forever, to fix a problem that does not exist.

The fix is ordering, not deletion. Both volatile fields move after the evidence block, which is
already a hard barrier because retrieved chunks change every query. Nothing is removed, the
"as of when?" feature keeps working, and blocks 1-3 become one stable cacheable prefix.
""".strip()
